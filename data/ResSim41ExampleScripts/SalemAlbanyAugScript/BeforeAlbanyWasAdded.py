# -*- coding: utf-8 -*-
"""
Calculates Salem Deficit and allocates the deficit to other reservoirs based on their "conservation" storage.
Conservation storage, in this context, will be caucluated between the top of the authorized rule curve and a definable lower elevation limit which could be a timeseries.
Mini simulations will predict elevations for April through October, starting with the storage at each reservoir on 01-April. Reservoirs can be excluded from the calculation.

"""

import pandas as pd
from pydsstools.heclib.dss import HecDss
import numpy as np
import os
from pydsstools.core import TimeSeriesContainer
import time
import pathlib
import datetime
from datetime import timedelta
from pathlib import Path
import pickle


#### LOAD CONFIGURATION FROM CSVs (MinFlowSalemAlbanyConfig + RunControl) ####

# externalSVs directory: ../externalSVs from this script
PARENT_PATH = Path(__file__).resolve().parent.parent
PKL_PATH = PARENT_PATH / "median_remaining_by_day.pkl"
EXTERNAL_SV_DIR = PARENT_PATH / "externalSVs"

MINFLOW_CONFIG_CSV = EXTERNAL_SV_DIR / "MinFlowSalemAlbanyConfig.csv"
RUNCONTROL_CSV = EXTERNAL_SV_DIR / "RunControl.csv"

# NEW: path to the WY-type flow target table
# (Adjust file name to whatever you actually use.)
WY_TYPE_FLOW_CSV = EXTERNAL_SV_DIR / "MinFlowSalem_2008BiOp.csv"

WY_CLASSIFICAION_DSS = EXTERNAL_SV_DIR / "WY_Classification.dss"


# -------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------
def _to_bool(x):
    if isinstance(x, bool):
        return x
    s = str(x).strip().lower()
    if s in {"true", "t", "yes", "y", "1"}:
        return True
    if s in {"false", "f", "no", "n", "0"}:
        return False
    raise ValueError(f"Cannot interpret '{x}' as boolean.")


def _parse_month_day(s):
    s = str(s).strip()
    parts = s.split("-")

    # Format: 1-Apr
    if len(parts) == 2 and parts[1].isalpha():
        day = int(parts[0])
        month_str = parts[1][:3].title()
        MONTH_MAP = {
            "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
            "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
        }
        return (MONTH_MAP[month_str], day)

    # Numeric fallback: 4-1, 10-31
    return (int(parts[0]), int(parts[1]))


def _normalize_date_column(col: str) -> str:
    """
    Ensure date columns look like '1-Jan', '16-Apr', etc.
    If you get '01-Jun' out of Excel, this will convert to '1-Jun'.
    Non date columns (e.g. 'WY_type') are passed through.
    """
    col = str(col).strip()
    if "-" not in col:
        return col
    day_str, month = col.split("-", 1)
    try:
        day_int = int(day_str)
    except ValueError:
        # Not a day-month format; return as-is
        return col
    return f"{day_int}-{month}"


# -------------------------------------------------------------
# 1) Load MinFlowSalemAlbanyConfig.csv (skip first 3 lines)
# -------------------------------------------------------------
minflow_df = pd.read_csv(MINFLOW_CONFIG_CSV, skiprows=3)
minflow_df.columns = [c.strip() for c in minflow_df.columns]
minflow_df.set_index("Variable", inplace=True)

# Identify reservoir names (all columns except the index)
reservoir_names = [c for c in minflow_df.columns if c and not pd.isna(c)]

# Basic dictionaries
ALIAS_DICT = {
    res: str(minflow_df.loc["Abbreviation", res]).strip()
    for res in reservoir_names
}

AUG_RESERVOIRS_DICT = {
    res: _to_bool(minflow_df.loc["SupportsSalemAlbany", res])
    for res in reservoir_names
}

TRAVEL_TIME_DAYS_DICT = {
    res: int(minflow_df.loc["TravelTimeDays", res])
    for res in reservoir_names
    if not pd.isna(minflow_df.loc["TravelTimeDays", res])
}

# Optional: MaxRelease (not all reservoirs have values)
MAX_FLOW_DICT = {}
if "MaxReleaseCFS" in minflow_df.index:
    for res in reservoir_names:
        val = minflow_df.loc["MaxReleaseCFS", res]
        if pd.notna(val) and str(val).strip() != "":
            MAX_FLOW_DICT[res] = float(val)
elif "MaxRelease" in minflow_df.index:
    for res in reservoir_names:
        val = minflow_df.loc["MaxRelease", res]
        if pd.notna(val) and str(val).strip() != "":
            MAX_FLOW_DICT[res] = float(val)


# -------------------------------------------------------------
# 2) Load RunControl.csv
# -------------------------------------------------------------
run_df = pd.read_csv(RUNCONTROL_CSV)
run_df.columns = [c.strip() for c in run_df.columns]

RUNCONTROL = {
    str(row["Name"]).strip(): str(row["Value"]).strip()
    for _, row in run_df.iterrows()
}

def _get_required(key):
    if key not in RUNCONTROL:
        raise KeyError(f"Missing required run control parameter '{key}'")
    return RUNCONTROL[key]

SIM_NAME = _get_required("SIM_NAME")
ALTERNATIVE_NAME_STEP1 = _get_required("ALTERNATIVE_NAME_STEP1")
FORECAST_DAYS = int(_get_required("FORECAST_DAYS"))
PERIOD_START = _parse_month_day(_get_required("PERIOD_START"))
PERIOD_END = _parse_month_day(_get_required("PERIOD_END"))







# Additional CONFIG

AF_PER_CFS_DAY = 24*60*60/43560
#Get the dss output f-part for step one. It is 10 characters plus a 0 at the end. e.g. "Default---0"
extraDashes = "-" * (10-len(ALTERNATIVE_NAME_STEP1))
FPART_STEP1 = ALTERNATIVE_NAME_STEP1 + extraDashes + "0"
#Get watershed directory relative to this script's location
WATERSHED_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
# DSS_FILE_IN should be down a directory from the ResSim wksp file in the rss folder then in the SIM_NAME folder
DSS_FILE_IN = os.path.join(WATERSHED_DIR, "rss", SIM_NAME, "simulation.dss")
# Output to the same file, just the b-part and c-part will be changed
DSS_FILE_OUT = os.path.join(WATERSHED_DIR, "rss", SIM_NAME, "simulation.dss")
# Salem min flows based on system storage on May 16 (WY Type) from 2008 BiOp.
WY_TYPE_FLOW_DICT = {
    0: {
        "1-Jan": 0, "1-Apr": 15000, "16-Apr": 15000, "1-May": 15000,
        "1-Jun": 11000, "16-Jun": 5500, "1-Jul": 5000, "1-Aug": 5000,
        "1-Sep": 5000, "1-Oct": 5000, "1-Nov": 0, "31-Dec": 0
    },
    900000: {
        "1-Jan": 0, "1-Apr": 15000, "16-Apr": 15000, "1-May": 15000,
        "1-Jun": 11000, "16-Jun": 5500, "1-Jul": 5000, "1-Aug": 5000,
        "1-Sep": 5000, "1-Oct": 5000, "1-Nov": 0, "31-Dec": 0
    },
    1200000: {
        "1-Jan": 0, "1-Apr": 17800, "16-Apr": 17800, "1-May": 15000,
        "1-Jun": 13000, "16-Jun": 8700, "1-Jul": 6000, "1-Aug": 6000,
        "1-Sep": 6500, "1-Oct": 7000, "1-Nov": 0, "31-Dec": 0
    },
    1480000: {
        "1-Jan": 0, "1-Apr": 17800, "16-Apr": 17800, "1-May": 15000,
        "1-Jun": 13000, "16-Jun": 8700, "1-Jul": 6000, "1-Aug": 6000,
        "1-Sep": 6500, "1-Oct": 7000, "1-Nov": 0, "31-Dec": 0
    }
}

# ==== Functions ==== #

# -------------------------------------------------------------
# 3) Load WY-type flow table -> WY_TYPE_FLOW_DICT
# -------------------------------------------------------------
def load_wy_type_flow_dict(csv_path: Path) -> dict[int, dict[str, int]]:
    """
    Reads a CSV of the form:

        # comment...
        WY_type,1-Jan,1-Apr,16-Apr,1-May,1-Jun,16-Jun,1-Jul,1-Aug,16-Aug,1-Sep,1-Oct,1-Nov
        0,0,15000,15000,15000,11000,5500,5000,5000,5000,5000,5000,0
        900000, ...

    and returns:

        {
          0: {"1-Jan": 0, "1-Apr": 15000, ..., "1-Nov": 0, "31-Dec": 0},
          900000: {...},
          ...
        }

    - Comment lines beginning with '#' are ignored.
    - Date columns are normalized to 'd-Mon' (no leading zero on the day).
    - If '31-Dec' is not present, it is added with value 0.
    """
    df = pd.read_csv(csv_path, comment="#")

    # Normalize column names (fix '01-Jun' style headers, etc.)
    df.columns = [_normalize_date_column(c) for c in df.columns]

    if "WY_type" not in df.columns:
        raise KeyError(f"'WY_type' column not found in {csv_path}")

    # Set WY_type as index but keep the normalized date columns
    df = df.set_index("WY_type")

    wy_type_flow_dict: dict[int, dict[str, int]] = {}

    # All date columns (everything except the index)
    date_cols = [c for c in df.columns]

    for wy_type, row in df.iterrows():
        inner: dict[str, int] = {}
        for col in date_cols:
            val = row[col]
            # Coerce to int, treating NaN/blank as 0
            if pd.isna(val) or str(val).strip() == "":
                inner[col] = 0
            else:
                inner[col] = int(val)
        # Ensure '31-Dec' is present; your examples always use 0
        if "31-Dec" not in inner:
            inner["31-Dec"] = 0

        wy_type_flow_dict[int(wy_type)] = inner

    return wy_type_flow_dict

# Reads all paths from a DSS file into a single DataFrame.
def readallpaths(dss_file, path_dict):
    fid = HecDss.Open(dss_file)
    dflist = []
    for alias, path in path_dict.items():
        try:
            ts = fid.read_ts(path, trim_missing=True)
            df = pd.DataFrame(ts.values, columns=[alias], index=np.array(ts.pytimes))
            dflist.append(df.copy())
        except Exception as e:
            msg = f"[DSS] Failed '{alias}' -> {path} in {os.path.basename(dss_file)}: {e}"
    fid.close()
    if not dflist:
        return pd.DataFrame()
    data = pd.concat(dflist, axis=1)
    data.index = pd.to_datetime(data.index)
    # (rare) guard
    data = data[~data.index.duplicated(keep="last")]
    return data


# Calculates storage on a date defined as total storage minus minconstor.
# result is a the storage value for each reservoir and for the system as a whole on that day'
# for each year.
# date is defined as month and day (e.g. May 16 is 5, 16)
def calculate_storage_on_date(data, date, minConStor):
    '''
    make a dataframe from data that only has columns that end with _stor
    and rows where the month and day match the input month and day and the index is the year.
    Then, subtract the minConStor values from the storage values for each reservoir.
    '''
    month, day = date
    stor_cols = [c for c in data.columns if c.endswith("_stor")]
    storage_on_date = data[stor_cols].copy()
    storage_on_date = storage_on_date[(storage_on_date.index.month == month) & (storage_on_date.index.day == day)]
    storage_on_date.index = storage_on_date.index.year
    for res, short in ALIAS_DICT.items():
        col = f"{short}_stor"
        if col in storage_on_date.columns and res in minConStor:
            storage_on_date[col] = storage_on_date[col] - minConStor[res]
    return storage_on_date


def create_salem_minflow_ts( wtTypeFlowTable, data):
    '''
    Create a time series for the minimum flow at Salem based on the water year type stored for the baseline simulation.
    This can be updated by calling the calculate_storage_on_date for 16-May using the baseline simulation and copying those results
    to the WY_Classification.dss file in the shared folder. 
    '''
    daily_wy_type = data[['WY_type']].copy()
    # filter daily_wy_type to only include rows where month and day match May 16 and then replace the index with the year
    May16_sys_storage = daily_wy_type[daily_wy_type.index.month == 5]
    May16_sys_storage = May16_sys_storage[May16_sys_storage.index.day == 16]
    May16_sys_storage.index = May16_sys_storage.index.year

    flow_list = []
    for year, row in May16_sys_storage.iterrows():
        storage = row['WY_type'] * 1000000  # convert MAF to AF
        if storage <= 0:
            wt_type = 0
        elif storage <= 900000:
            wt_type = 900000
        elif storage <= 1200000:
            wt_type = 1200000
        else:
            wt_type = 1480000
        flow_schedule = wtTypeFlowTable[wt_type]
        for date_str, flow in flow_schedule.items():
            date = pd.to_datetime(f"{year}-{date_str}")
            flow_list.append({'Date': date, 'SLM_minflow': flow})
    minflow_df = pd.DataFrame(flow_list)
    minflow_df.set_index('Date', inplace=True)
    minflow_df.sort_index(inplace=True)
    minflow_df = minflow_df.resample('D').ffill()
    data = data.copy()
    data = data.join(minflow_df, how='left')
    data['SLM_minflow'] = data['SLM_minflow'].fillna(0)
    return data


def compute_net_inflows(data, alias):
    """ 
    Units are CFS
    """
    data = data.copy()
    for res, short in alias.items():
        inflow_col = f"{short}_inflow"
        minflow_col = f"{short}_minflow"
        net_col = f"{short}_netflow"
        if inflow_col in data.columns and minflow_col in data.columns:
            data[net_col] = data[inflow_col].fillna(0.0) - data[minflow_col].fillna(0.0)
        else:
            data[net_col] = np.nan
    return data

# Create a dicitonary with pivot tables for net inflows. The columns are years and the index is month-day.
# Rows start at the period start and end at period end as defined at the top of the script.
def create_net_inflow_pivot_tables(data, alias,Period_Start,Period_End):
    """
    Create a dictionary of pivot tables for net inflows.
    Each pivot table has years as columns and month-day as index.
    Units are CFS.
    """
    net_inflow_pivot_tables = {}
    start_month, start_day = Period_Start
    end_month, end_day = Period_End
    for res, short in alias.items():
        net_col = f"{short}_netflow"
        if net_col not in data.columns:
            continue
        df = data[[net_col]].copy()
        df = df[(df.index.month > start_month) | ((df.index.month == start_month) & (df.index.day >= start_day)) &
                (df.index.month < end_month) | ((df.index.month == end_month) & (df.index.day <= end_day))]
        df['Year'] = df.index.year
        df['Month-Day'] = df.index.strftime('%m-%d')
        pivot_table = df.pivot_table(index='Month-Day', columns='Year', values=net_col, aggfunc='sum', fill_value=0.0)
        # Reindex to ensure all month-days are present
        month_days = pd.date_range(f"2001-{start_month:02d}-{start_day:02d}", f"2001-{end_month:02d}-{end_day:02d}", freq='D').strftime('%m-%d')
        pivot_table = pivot_table.reindex(month_days, fill_value=0.0)
        net_inflow_pivot_tables[short] = pivot_table
    return net_inflow_pivot_tables

# Create "remaining_volume" tables from the pivot tables. These are cumulative forward sums for each year.
# For example, the value for April 1 is the sum of all net inflows from April 1 to October 31 for that year
# (assuming the period is April 1 to October 31). The value for April 2 is the sum from April 2 to October 31, etc.
def create_remaining_volume_pivot_tables(pivot_tables,AF_PER_CFS_DAY):
    """
    Create remaining volume tables from pivot tables.
    Each table has years as columns and month-day as index.
    The values are cumulative forward sums for each year.
    Units are ACRE-FEET.
    """
    remaining_volume_pivot_tables = {}
    for short, pivot_table in pivot_tables.items():
        rem_table = pivot_table.iloc[::-1].cumsum().iloc[::-1]
        rem_table = rem_table * AF_PER_CFS_DAY
        remaining_volume_pivot_tables[short] = rem_table
    return remaining_volume_pivot_tables

def create_median_remaining_volume_by_day(remaining_volume_pivot_tables):
    """
    For each reservoir's remaining-volume pivot table (AF),
    compute the row-wise median across years.

    Input:
        remaining_volume_pivot_tables: {short: DataFrame}
             index: 'MM-DD'
             columns: years
             values: remaining volume (AF) from that day to end of period

    Returns:
        {short: Series}
             index: 'MM-DD'
             values: median remaining volume (AF) across years
    """
    median_remaining_by_day = {}
    for short, rem_table in remaining_volume_pivot_tables.items():
        if rem_table is None or rem_table.empty:
            continue
        # median across years for each day-of-year
        median_series = rem_table.median(axis=1)  # index: 'MM-DD'
        median_series.name = f"{short}_median_remaining_AF"
        median_remaining_by_day[short] = median_series
    return median_remaining_by_day

# Create Forecast Period forward looking rolling sums for each net inflow pivot tables.
# For example, the value for April 1 is the sum of net inflows from April 1 to April 10 (assuming a 10-day forecast period).
def create_short_forecast_volume_pivot_tables(pivot_tables, forecast_days, AF_PER_CFS_DAY):
    """
    Create forecast volume tables from pivot tables.
    Each table has years as columns and month-day as index.
    The values are forward looking rolling sums for each year.
    units are ACRE-FEET.
    """
    short_forecast_volume_pivot_tables = {}
    for res, pivot_table in pivot_tables.items():
        forecast_table = pivot_table.iloc[::-1].rolling(window=forecast_days, min_periods=1).sum().iloc[::-1]
        forecast_table = forecast_table * AF_PER_CFS_DAY
        short_forecast_volume_pivot_tables[res] = forecast_table
    return short_forecast_volume_pivot_tables

#Create pivot tables that add the storage calculated for the next ten days from the short forecast
# to the remaining volume after the forecast period.
def create_total_available_volume_pivot_tables(
    short_forecast_volume_pivot_tables,
    Forecast_Days_Assumption,
    April01_conStorage,
    median_remaining_by_day,
):
    """
    Total available (for Salem Augmentation) =

        short_forecast_volume (AF over next k days, per year)
      + median remaining seasonal volume AFTER the forecast window (AF)
      + Apr01 usable storage (AF) for that year

    Inputs
    -------
    short_forecast_volume_pivot_tables : dict[str, pd.DataFrame or pd.Series]
        {short: DataFrame or Series}
        - If DataFrame:
            index: 'MM-DD'
            columns: Year
            values: AF over next Forecast_Days_Assumption days, per year.
        - If Series:
            index: 'MM-DD'
            name: Year (or some label); will be converted to a 1-column DataFrame.

    Forecast_Days_Assumption : int
        k = number of days in the forecast window (same as FORECAST_DAYS).

    April01_conStorage : pd.DataFrame
        Index: Year (int)
        Columns: f"{short}_stor" (usable con storage in AF on April 1).

    median_remaining_by_day : dict[str, pd.Series]
        {short: Series}
        index: 'MM-DD'
        values: median remaining AF from that date through the
                end of the deficit period across the POR.

    Returns
    -------
    total_available_volume_pivot_tables : dict[str, pd.DataFrame]
        {short: DataFrame}
        index: 'MM-DD'
        columns: Year
        values: total available volume (AF).
    """
    total_available_volume_pivot_tables = {}
    k = Forecast_Days_Assumption

    for short, fct_table in short_forecast_volume_pivot_tables.items():
        if fct_table is None:
            continue

        # ----------------------------------------------------------
        # Coerce forecast table to a 2D DataFrame
        # ----------------------------------------------------------
        if isinstance(fct_table, pd.Series):
            # 1-column DataFrame; column name is the Series name or a default
            col_name = fct_table.name if fct_table.name is not None else "Year"
            fct_table = fct_table.to_frame(name=col_name)

        if fct_table.empty:
            continue

        fct_table = fct_table.copy()
        fct_table = fct_table.sort_index()
        fct_table = fct_table.fillna(0.0)

        # ----------------------------------------------------------
        # 1. Get median remaining series for this reservoir
        # ----------------------------------------------------------
        med_series = median_remaining_by_day.get(short)
        if med_series is None or med_series.empty:
            # If no median provided, treat remaining as zero
            med_series = pd.Series(0.0, index=fct_table.index)

        # Align median series index to the forecast pivot index ('MM-DD')
        med_series = med_series.reindex(fct_table.index, fill_value=0.0)

        # Broadcast median series across all years in the forecast table
        median_matrix = pd.DataFrame(
            {year: med_series.values for year in fct_table.columns},
            index=fct_table.index,
        )

        # ----------------------------------------------------------
        # 2. Remaining AFTER the forecast window: shift median by k days
        # ----------------------------------------------------------
        rem_after = median_matrix.shift(-k)

        # ----------------------------------------------------------
        # 3. Combine: forecast volume (per year) + median remaining after-k
        # ----------------------------------------------------------
        combined = rem_after.add(fct_table, fill_value=0.0)

        # ----------------------------------------------------------
        # 4. Add April 1 usable storage per year
        # ----------------------------------------------------------
        colname = f"{short}_stor"
        for year in combined.columns:
            add_stor = 0.0
            if year in April01_conStorage.index and colname in April01_conStorage.columns:
                add_stor = float(April01_conStorage.loc[year, colname])
            combined[year] = combined[year] + add_stor

        total_available_volume_pivot_tables[short] = combined.fillna(0.0)

    return total_available_volume_pivot_tables



# Create salem deficit pivot table
def create_salem_deficit_pivot_table(data,Period_Start,Period_End):
    """
    Create a pivot table for Salem deficit during the deficit period.
    The columns are years and the rows are month-day.
    Accomplish this by subtracting the minimum flow at Salem from the actual flow at Salem in 
    the data dataframe, then creating a pivot table from the result, where
    the index is month-day, the columns are years, and the rows start and month day Period_Start
    and end at Period_End as defined at the top of the script.
    Positive deficit values mean that more flow is required out of reservoirs to meet min flow.
    Negative deficit values mean that reservoirs can drop releases a bit and still meet the min.
    Uses non leap year which is fine because salem aug only happens April 1 to October 31.
    Returns: salem_deficit_pivot_table
    Units are CFS.
    """
    start_month, start_day = Period_Start
    end_month, end_day = Period_End
    df = data[['SLM_flow', 'SLM_minflow']].copy()
    df['SLM_deficit'] = df['SLM_minflow'] - df['SLM_flow']
    #Allow negatives, don't cap to 0
    #df['SLM_deficit'] = df['SLM_deficit'].clip(lower=0.0)
    df = df[(df.index.month > start_month) | ((df.index.month == start_month) & (df.index.day >= start_day)) &
            (df.index.month < end_month) | ((df.index.month == end_month) & (df.index.day <= end_day))]
    df['Year'] = df.index.year
    df['Month-Day'] = df.index.strftime('%m-%d')
    salem_deficit_pivot_table = df.pivot_table(index='Month-Day', columns='Year', values='SLM_deficit', aggfunc='sum', fill_value=0.0)
    # Reindex to ensure all month-days are present
    month_days = pd.date_range(f"2001-{start_month:02d}-{start_day:02d}", f"2001-{end_month:02d}-{end_day:02d}", freq='D').strftime('%m-%d')
    salem_deficit_pivot_table = salem_deficit_pivot_table.reindex(month_days, fill_value=0.0)
    return salem_deficit_pivot_table

# Create pivot tables that are the proportion of total available deficit period
# system storage for each reservoir in AugReservoirs.

def create_augmentation_proportion_tables(total_available_volume_pivot_tables, AugReservoirs, alias):
    """
    Compute daily proportions of total available system storage for the reservoirs selected
    in AugReservoirs. Accepts either:
      - dict: { "Detroit": True/False, ... }  (truthy means include)
      - iterable/list: ["Detroit", "Lookout Point", ...]
    Assumes identical index/columns across tables.
    Negatives are clipped to 0 before summing/dividing.
    Returns: {short: proportion_table_df}
    """
    # Normalize selection to a list of reservoir long names
    if isinstance(AugReservoirs, dict):
        selected = [res for res, use in AugReservoirs.items() if use]
    else:
        selected = list(AugReservoirs)

    # Keep only requested reservoirs (by short code) and clip negatives once
    tables = {
        alias[res]: total_available_volume_pivot_tables[alias[res]].clip(lower=0.0)
        for res in selected
        if res in alias and alias[res] in total_available_volume_pivot_tables
    }
    if not tables:
        return {}

    # Elementwise total system storage
    iter_tables = iter(tables.values())
    first = next(iter_tables)
    total = first.copy() * 0.0
    total += first
    for t in iter_tables:
        total += t

    # Proportions (avoid div-by-zero -> 0.0)
    denom = total.replace(0.0, np.nan)
    augmentation_proportion_pivot_tables = {short: (tbl / denom).fillna(0.0) for short, tbl in tables.items()}
    return augmentation_proportion_pivot_tables


# Calculate additional releases from each reservoir for Salem augmentation 
# by multiplying the Salem deficit pivot table by each reservoir's augmentation proportion pivot table.
def create_agumentation_flow_pivot_tables(
    augmentation_proportion_pivot_tables,salem_deficit_pivot_table
):
    """
    Create augmentation flow pivot tables by multiplying the Salem deficit pivot table
    with each reservoir's augmentation proportion pivot table.
    Returns: {short: augmentation_flow_table_df}
    Units are CFS.
    """
    augmentation_flow_pivot_tables = {}
    for short, prop_table in augmentation_proportion_pivot_tables.items():
        # Align shapes/index/columns defensively
        aligned_deficit = salem_deficit_pivot_table.reindex(index=prop_table.index, columns=prop_table.columns, fill_value=0.0)
        aug_flow_table = aligned_deficit * prop_table
        augmentation_flow_pivot_tables[short] = aug_flow_table
    return augmentation_flow_pivot_tables

# Metl the pivot tables back to single time-series with a DatetimeIndex that matches the big original dataframe
def melt_pivot_to_series(pivot_table, new_name, start_dt, end_dt, fill_value=0.0):
    """
    Convert a pivot table (index='MM-DD', columns=Year) to a single time series.
    The index is a DatetimeIndex with full dates, and the values are from the pivot table.
    Missing dates are filled with 0.0.
    The series is trimmed to start_dt and end_dt.
    """
    df = pivot_table.copy()
    df.index = pd.to_datetime("2000-" + df.index.astype(str), format="%Y-%m-%d")
    years = df.columns.astype(int)
    pieces = []
    for year in years:
        ser = pd.Series(
            df[year].values,
            index=pd.to_datetime(f"{year}-" + df.index.strftime("%m-%d"))
        )
        pieces.append(ser)
    full_series = pd.concat(pieces).sort_index()
    full_series = full_series.reindex(
        pd.date_range(full_series.index.min(), full_series.index.max(), freq='D'),
        fill_value=fill_value
    )
    full_series = full_series[(full_series.index >= pd.to_datetime(start_dt)) & (full_series.index <= pd.to_datetime(end_dt))]
    full_series.name = new_name
    return full_series

# Add the agumentation flows to the original outflows to create the new minimum outflow series.
# There are two ways to do this, defining flows for the entire augmentation period or just when there is a deficit.
# step = 1 means only when there is a deficit, step = 2 means always during the period.
# Just doing step 1 or step 2 provides decent results, but step one on first iteration of simulation then 
# step 2 on the second iteration provides the best results.
# augmentation flow always defaults back to minflow to prevent occilations.
def add_augmentation_to_outflows(data, alias, Period_Start, Period_End, TravelTimeDays=None):
    df = data.copy()
    TravelTimeDays = TravelTimeDays or {}

    sm, sd = Period_Start
    #start two days earlier to account for travel time.
    #simply subtracting 2 from the sd won't work because it could be the 1st
    startDT = datetime.datetime(2001,sm,sd) - timedelta(days=2)
    sm = startDT.month
    sd = startDT.day
    em, ed = Period_End
    idx = df.index

    period_mask = (
        ((idx.month > sm) | ((idx.month == sm) & (idx.day >= sd))) &
        ((idx.month < em) | ((idx.month == em) & (idx.day <= ed)))
    )
    #deficit_mask = pd.to_numeric(df.get('SLM_deficit', 0.0), errors='coerce').fillna(0.0) > 0.0
    #apply_mask = (period_mask & deficit_mask)
    #Apply it for all dates in the window, not just when deficits are positive
    apply_mask = (period_mask)

    for res, short in alias.items():
        out_col = f"{short}_outflow"
        aug_col = f"{short}_augmentation_flow"
        new_col = f"{short}_min_flow_with_aug"

        df[new_col] = 0.0 # Initialize new min flow with augmentation to 0 cfs
        if aug_col not in df.columns: #e.g. Hills Creek, where we never calculated augmentation flow
            continue
        # <<< minimal change: shift ONLY augmentation by travel time >>>
        tt_days = int(TravelTimeDays.get(res, 0))
        aug_shift = pd.to_numeric(df[aug_col], errors='coerce').shift(-tt_days)

        # cap final outflow + augmentation to max flow
        max_flow = MAX_FLOW_DICT.get(res, np.inf)
        df.loc[apply_mask, new_col] = (
            df.loc[apply_mask, out_col] +
            aug_shift.loc[apply_mask]
        ).clip(upper=max_flow)

    return df


# DSS write function. 
def write_outflows_to_dss(
    data: pd.DataFrame,          # source data
    alias: dict,                 # reservoir name to short code mapping
    dss_file_write: str,         # target DSS file path
    c_part_out: str,             # C-Part for write
    f_part_out: str,             # F-Part for write
    col_ext: str,                # suffix added to res short name to identify column in data
    decimals: int = 1,           # number of decimal places to KEEP via TRUNCATION
) -> int:
    """
    Write ONLY the '{stem}_new_outflow' series for each reservoir in alias to a DSS-6 file.

    Pathname: //{RES}-POOL/FLOW-OUT//1DAY/{f_part_out}/
    Units: CFS, Type: PER-AVER, Interval: 1440 minutes (daily).
    Values are truncated (not rounded) to decimals places.
    Returns: count of series written.
    """
    def _dss_datetime(ts: pd.Timestamp) -> str:
        """Return DSS-6 style start datetime (e.g., '01Jan2000 0000')."""
        return ts.strftime("%d%b%Y %H%M")
    
    if not isinstance(data.index, pd.DatetimeIndex):
        raise TypeError("data must have a DatetimeIndex.")
    if data.index.empty:
        raise ValueError("data.index is empty; nothing to write.")

    # Ensure target directory exists
    out_dir = os.path.dirname(dss_file_write)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # Ensure sorted index
    if not data.index.is_monotonic_increasing:
        data = data.sort_index()

    to_write = []
    for long, short in alias.items():
        col_new = f"{short}{col_ext}"
        if col_new not in data.columns:
            print(f"[WARN] Missing column '{col_new}' for {long}; skipping.")
            continue

        series = (
            data[col_new]
            .astype("float64")
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0.0)
        )

        if series.empty:
            print(f"[WARN] Empty series for {long}; skipping.")
            continue
        if c_part_out in ["FLOW-OUT", "FLOW-IN","ELEV","STOR"]:
            #pathname = f"//{long.upper()}-POOL/{c_part_out}//1DAY/{f_part_out}/"
            pathname = f"//{long.upper()}/{c_part_out}//1DAY/{f_part_out}/"
        else:
            pathname = f"//{long.upper()}/{c_part_out}//1DAY/{f_part_out}/"
        to_write.append((pathname, series))

    if not to_write:
        print("No series to write.")
        return 0

    written = 0
    fid = HecDss.Open(dss_file_write, version=6)
    try:
        for pathname, series in to_write:
            # TRUNCATE (not round) to the requested decimals
            vals = series.to_numpy(dtype="float64")
            vals = np.round(vals, decimals)
            tsc = TimeSeriesContainer()
            tsc.pathname = pathname
            tsc.startDateTime = _dss_datetime(series.index[0])
            tsc.numberValues = series.shape[0]
            tsc.units = "CFS"
            tsc.type = "PER-AVER"
            tsc.interval = 1440
            tsc.values = vals
            try:
                fid.deletePathname(tsc.pathname)  # overwrite if exists
            except Exception:
                pass
            fid.put_ts(tsc)
            written += 1
    finally:
        fid.close()
    print(f"[write_outflows_v6] Wrote {written} series to DSS.")
    return written

# ==== Main Processing ==== #

start_time = time.time()

# All of the necesarry inflows, outflows, and storages. LOP and GPR will use Unreg flow as inflow
# As such, Foster and Hills Creek cannot be used in AugReservoirs.
path_dict = {
    "LOP_stor": f"//LOOKOUT POINT-POOL/STOR//1DAY/{FPART_STEP1}/",
    "LOP_inflow": f"//LOOKOUT POINT-POOL/FLOW-IN//1DAY/{FPART_STEP1}/",
    # "LOP_inflow": f"//LOOKOUT POINT_OUT/FLOW-UNREG//1DAY/{FPART_STEP1}/",
    "LOP_outflow": f"//LOOKOUT POINT-POOL/FLOW-OUT//1DAY/{FPART_STEP1}/",
    "LOP_rcStor": f"//LOOKOUT POINT-RULE CURVE/STOR-ZONE//1DAY/{FPART_STEP1}/",
    "DET_stor": f"//DETROIT-POOL/STOR//1DAY/{FPART_STEP1}/",
    "DET_inflow": f"//DETROIT-POOL/FLOW-IN//1DAY/{FPART_STEP1}/",
    "DET_outflow": f"//DETROIT-POOL/FLOW-OUT//1DAY/{FPART_STEP1}/",
    "DET_rcStor": f"//DETROIT-RULE CURVE/STOR-ZONE//1DAY/{FPART_STEP1}/",
    "GPR_stor": f"//GREEN PETER-POOL/STOR//1DAY/{FPART_STEP1}/",
    "GPR_inflow": f"//GREEN PETER-POOL/FLOW-IN//1DAY/{FPART_STEP1}/",
    # "GPR_inflow": f"//FOSTER_OUT/FLOW-UNREG//1DAY/{FPART_STEP1}/",
    "GPR_outflow": f"//GREEN PETER-POOL/FLOW-OUT//1DAY/{FPART_STEP1}/",
    "GPR_rcStor": f"//GREEN PETER-RULE CURVE/STOR-ZONE//1DAY/{FPART_STEP1}/",
    "CGR_stor": f"//COUGAR-POOL/STOR//1DAY/{FPART_STEP1}/",
    "CGR_inflow": f"//COUGAR-POOL/FLOW-IN//1DAY/{FPART_STEP1}/",
    "CGR_outflow": f"//COUGAR-POOL/FLOW-OUT//1DAY/{FPART_STEP1}/",
    "CGR_rcStor": f"//COUGAR-RULE CURVE/STOR-ZONE//1DAY/{FPART_STEP1}/",
    "BLU_stor": f"//BLUE RIVER-POOL/STOR//1DAY/{FPART_STEP1}/",
    "BLU_inflow": f"//BLUE RIVER-POOL/FLOW-IN//1DAY/{FPART_STEP1}/",
    "BLU_outflow": f"//BLUE RIVER-POOL/FLOW-OUT//1DAY/{FPART_STEP1}/",
    "BLU_rcStor": f"//BLUE RIVER-RULE CURVE/STOR-ZONE//1DAY/{FPART_STEP1}/",
    "FAL_stor": f"//FALL CREEK-POOL/STOR//1DAY/{FPART_STEP1}/",
    "FAL_inflow": f"//FALL CREEK-POOL/FLOW-IN//1DAY/{FPART_STEP1}/",
    "FAL_outflow": f"//FALL CREEK-POOL/FLOW-OUT//1DAY/{FPART_STEP1}/",
    "FAL_rcStor": f"//FALL CREEK-RULE CURVE/STOR-ZONE//1DAY/{FPART_STEP1}/",
    "HCR_stor": f"//HILLS CREEK-POOL/STOR//1DAY/{FPART_STEP1}/",
    "HCR_inflow": f"//HILLS CREEK-POOL/FLOW-IN//1DAY/{FPART_STEP1}/",
    "HCR_outflow": f"//HILLS CREEK-POOL/FLOW-OUT//1DAY/{FPART_STEP1}/",
    "HCR_rcStor": f"//HILLS CREEK-RULE CURVE/STOR-ZONE//1DAY/{FPART_STEP1}/",
    "DOR_stor": f"//DORENA-POOL/STOR//1DAY/{FPART_STEP1}/",
    "DOR_inflow": f"//DORENA-POOL/FLOW-IN//1DAY/{FPART_STEP1}/",
    "DOR_outflow": f"//DORENA-POOL/FLOW-OUT//1DAY/{FPART_STEP1}/",
    "DOR_rcStor": f"//DORENA-RULE CURVE/STOR-ZONE//1DAY/{FPART_STEP1}/",
    "COT_stor": f"//COTTAGE GROVE-POOL/STOR//1DAY/{FPART_STEP1}/",
    "COT_inflow": f"//COTTAGE GROVE-POOL/FLOW-IN//1DAY/{FPART_STEP1}/",
    "COT_outflow": f"//COTTAGE GROVE-POOL/FLOW-OUT//1DAY/{FPART_STEP1}/",
    "COT_rcStor": f"//COTTAGE GROVE-RULE CURVE/STOR-ZONE//1DAY/{FPART_STEP1}/",
    "FRN_stor": f"//FERN RIDGE-POOL/STOR//1DAY/{FPART_STEP1}/",
    "FRN_inflow": f"//FERN RIDGE-POOL/FLOW-IN//1DAY/{FPART_STEP1}/",
    "FRN_outflow": f"//FERN RIDGE-POOL/FLOW-OUT//1DAY/{FPART_STEP1}/",
    "FRN_rcStor": f"//FERN RIDGE-RULE CURVE/STOR-ZONE//1DAY/{FPART_STEP1}/",
    "FOS_stor": f"//FOSTER-POOL/STOR//1DAY/{FPART_STEP1}/",
    # "FOS_inflow": f"//FOSTER-POOL/FLOW-IN//1DAY/{F_Part}/",
    # "FOS_outflow": f"//FOSTER-POOL/FLOW-OUT//1DAY/{F_Part}/",
    "FOS_rcStor": f"//FOSTER-RULE CURVE/STOR-ZONE//1DAY/{FPART_STEP1}/",
    "SLM_flow": f"//WILLAMETTE_AT SALEM/FLOW//1DAY/{FPART_STEP1}/",
    "ALB_flow": f"//WILLAMETTE_AT ALBANY/FLOW//1DAY/{FPART_STEP1}/",
    "SLM_flow": f"//WILLAMETTE_AT SALEM/FLOW//1DAY/{FPART_STEP1}/",
    "WY_type": f"//WATERYEARTYPEVARIABLE/STOR-MAF//1DAY/{FPART_STEP1}/",
    "FRN_minflow": f"//FERN RIDGE-DAM-BIOP MINTRIB AND WITHDRAWALS BY WY/FLOW-MIN//1DAY/{FPART_STEP1}/",
    "DOR_minflow": f"//DORENA-DAM-BIOP MINTRIB AND WITHDRAWALS BY WY/FLOW-MIN//1DAY/{FPART_STEP1}/",
    "COT_minflow": f"//COTTAGE GROVE-DAM-BIOP MINTRIB AND WITHDRAWALS BY WY/FLOW-MIN//1DAY/{FPART_STEP1}/",
    "FAL_minflow": f"//FALL CREEK-DAM-BIOP MINTRIB AND WITHDRAWALS BY WY/FLOW-MIN//1DAY/{FPART_STEP1}/",
    "HCR_minflow": f"//HILLS CREEK-DAM-BIOP MINTRIB AND WITHDRAWALS BY WY/FLOW-MIN//1DAY/{FPART_STEP1}/",
    "LOP_minflow": f"//LOOKOUT POINT-DAM-BIOP MINTRIB AND WITHDRAWALS BY WY/FLOW-MIN//1DAY/{FPART_STEP1}/",
    "CGR_minflow": f"//COUGAR-DAM-BIOP MINTRIB AND WITHDRAWALS BY WY/FLOW-MIN//1DAY/{FPART_STEP1}/",
    "BLU_minflow": f"//BLUE RIVER-DAM-BIOP MINTRIB AND WITHDRAWALS BY WY/FLOW-MIN//1DAY/{FPART_STEP1}/",
    "GPR_minflow": f"//BIOP MINTRIB AND WITHDRAWAL BY WY FOR FOS/FLOW-MIN//1DAY/{FPART_STEP1}/",
    "DET_minflow": f"//DETROIT-DAM-BIOP MINTRIB AND WITHDRAWALS BY WY/FLOW-MIN//1DAY/{FPART_STEP1}/",
}


# Create paths for dss files, read dss data, add minflows, create net flows (inflow - minflow), and combine.
data = readallpaths(DSS_FILE_IN, path_dict)

minConStor_dict = {}
# calculate MIN_CON_STOR_DICT from the rule curve storages on 01Jan of any year. 
# min con storage is the same in every year. downloading all the data for that one value is overkill, but 
# but maybe faster than closing and opening the dss to read just that one value in a seperate function.
for res, short in ALIAS_DICT.items():
    rc_stor_col = f"{short}_rcStor"
    if rc_stor_col in data.columns:
        jan01_stor = data[data.index.month == 1]
        jan01_stor = jan01_stor[jan01_stor.index.day == 1]
        if not jan01_stor.empty:
            min_con_storage = jan01_stor[rc_stor_col].iloc[0]
            minConStor_dict[res] = min_con_storage

# Modify LOP record to be a Super reservoir (LOP + HCR) 
# because HCR does not directly augment Salem and instead supplements LOP.
data["LOP_stor"] = data["LOP_stor"] + data["HCR_stor"]
data["LOP_inflow"] = data["LOP_inflow"] + data["HCR_inflow"]
minConStor_dict["Lookout Point"] = minConStor_dict.get("Lookout Point",0.0) + minConStor_dict.get("Hills Creek",0.0)

START_DT = data.index[0].strftime("%Y-%m-%d")
END_DT = data.index[-1].strftime("%Y-%m-%d")
# data = trib_minflow_ts(TRIB_MINFLOW_DICT, START_DT, END_DT, data)
data = compute_net_inflows(data, ALIAS_DICT)
# Calculate storage on April 1 (deficit season start con storage) and May 16 (for WY type designation) for each year
April01_storage = calculate_storage_on_date(data, PERIOD_START, minConStor_dict)
# subtract the minConStor from the April 1 storage to get usable storage for augmentation.
April01_conStorage = April01_storage.copy()
for res, short in ALIAS_DICT.items():
    colname = f"{short}_stor"
    if colname in April01_conStorage.columns:
        con_stor = minConStor_dict.get(res, 0.0)
        April01_conStorage[colname] = April01_conStorage[colname] - con_stor
# Create Salem min flow time series using WY type and add to data dataframe
# load the WY type from the CSV
WY_TYPE_FLOW_DICT = load_wy_type_flow_dict(WY_TYPE_FLOW_CSV)
data = create_salem_minflow_ts( WY_TYPE_FLOW_DICT, data)
# Create the net inflow pivot table for the deficit period
net_inflow_pivot_tables = create_net_inflow_pivot_tables(data, ALIAS_DICT,PERIOD_START,PERIOD_END)

'''
# create the remaining volume, short forecast volume and total available volume pivot tables as Median forward cumulative sums of the remaining season or forcast period.
# This calculation relies on a POR calculation, so it was done once and the results saved to a .pkl file. 
# If you want to recalculate the median based on a different POR, use a simulation with the desired POR and uncomment the calculation and saving of the .pkl below.
remaining_volume_pivot_tables = create_remaining_volume_pivot_tables(net_inflow_pivot_tables, AF_PER_CFS_DAY)
median_remaining_by_day = create_median_remaining_volume_by_day(remaining_volume_pivot_tables)
with open(PKL_PATH, "wb") as f:
    pickle.dump(median_remaining_by_day, f, protocol=pickle.HIGHEST_PROTOCOL)
'''

with open(PKL_PATH, "rb") as f:
    median_remaining_by_day = pickle.load(f)
short_forecast_volume_pivot_tables = create_short_forecast_volume_pivot_tables(net_inflow_pivot_tables, FORECAST_DAYS, AF_PER_CFS_DAY)
total_available_volume_pivot_tables = create_total_available_volume_pivot_tables(short_forecast_volume_pivot_tables,FORECAST_DAYS,April01_conStorage,median_remaining_by_day)
# determine proportional avialability of seasonal volume for mainstem augmentation using starting storage, ten day true forecast, and median remaining seasonal volume.
augmentation_proportion_pivot_tables = create_augmentation_proportion_tables(total_available_volume_pivot_tables, AUG_RESERVOIRS_DICT, ALIAS_DICT)
# Calculate the Salem deficit and distribute it to reservoirs based on augmentation capacity.
salem_deficit_pivot_table = create_salem_deficit_pivot_table(data,PERIOD_START,PERIOD_END)
augmentation_flow_pivot_tables = create_agumentation_flow_pivot_tables(augmentation_proportion_pivot_tables, salem_deficit_pivot_table)
# Melt augmentation flow pivot tables to series and add to data
for short, aug_flow_table in augmentation_flow_pivot_tables.items():
    series = melt_pivot_to_series(
        aug_flow_table,
        new_name=f"{short}_augmentation_flow",
        start_dt=START_DT,
        end_dt=END_DT,
        fill_value=0.0
    )
    data[series.name] = series
# Melt salem deficit pivot table to series and add to data
salem_deficit_series = melt_pivot_to_series(
    salem_deficit_pivot_table,
    new_name="SLM_deficit",
    start_dt=START_DT,
    end_dt=END_DT,
    fill_value=0.0)
data["SLM_deficit"] = salem_deficit_series
# add augmentation flows to original outflows
    # step = 1 means only when there is a deficit, 
    # step = 2 means always during the period.
data = add_augmentation_to_outflows(data, ALIAS_DICT, PERIOD_START, PERIOD_END , TravelTimeDays=TRAVEL_TIME_DAYS_DICT)
# Write new outflows and Salem deficit to a new DSS file
written_count = write_outflows_to_dss(data, ALIAS_DICT, DSS_FILE_OUT,c_part_out="FLOW-MIN-EXTERNALFLOWAUG", f_part_out=FPART_STEP1,col_ext="_min_flow_with_aug" , decimals=1)
written_count += write_outflows_to_dss(data[['SLM_deficit']], {'Salem': 'SLM'}, DSS_FILE_OUT,c_part_out="FLOW-DEFICIT-EXTERNALFLOWAUG", f_part_out=FPART_STEP1,col_ext="_deficit", decimals=1)
# write salem min flow for reference
written_count += write_outflows_to_dss(data[['SLM_minflow']], {'Salem': 'SLM'}, DSS_FILE_OUT,c_part_out="FLOW-MIN-EXTERNALFLOWAUG", f_part_out=FPART_STEP1,col_ext="_minflow", decimals=1)

'''
# ONLY NEEDED TO UPDATE WY TYPE USING UPDATED POR BASELINE RUN
# MUST COMMENT OUT lines 716,717,718 -  "data["LOP_stor"] = data["LOP_stor"] + data["HCR_stor"]
#data["LOP_inflow"] = data["LOP_inflow"] + data["HCR_inflow"]
#minConStor_dict["Lookout Point"] = minConStor_dict.get("Lookout Point",0.0) + minConStor_dict.get("Hills Creek",0.0)" 
#or HCR stor will be counted twice.
updateWYTypeSeries_DF = calculate_storage_on_date(data, (5,16), minConStor_dict)
updateWYTypeSeries_yearly_series = updateWYTypeSeries_DF.sum(axis=1)
# add 1935 and copy value from 1936 since 1935 is missing in the storage data.
updateWYTypeSeries_yearly_series.loc[1935] = updateWYTypeSeries_yearly_series.loc[1936]
# make updateWYTypeSeries_yearly_series a daily series sarting 01Jan of the first year.
# fill each day of a year with the corresponding value for that year.
daily_wytype_values = []
for year in updateWYTypeSeries_yearly_series.index:
    date_range = pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31", freq='D')
    yearly_value = updateWYTypeSeries_yearly_series.loc[year]
    yearly_series = pd.Series(yearly_value, index=date_range)
    daily_wytype_values.append(yearly_series)
daily_wytype_series = pd.concat(daily_wytype_values).sort_index()
daily_wytype_series_MAF = daily_wytype_series/1000000  # convert from ACRE-FEET to MAF
df_wy = daily_wytype_series_MAF.to_frame(name="WYTypeStorage")
#write the daily series to dss
wy_path = str((PARENT_PATH / ".." / "shared" / "WY_Classification.dss").resolve())
print(df_wy.columns)
written_count += write_outflows_to_dss(
    df_wy,
    {"WY_Type_Storage": "WYTypeStorage"},
    wy_path,
    c_part_out="STOR-MAF",
    f_part_out="Baseline09Dec2025",
    col_ext="",
    decimals=6,
)
'''