# -*- coding: utf-8 -*-
"""
Calculates Salem and Albany deficits and allocates the deficits to other reservoirs
based on their "conservation" storage.

Conservation storage, in this context, will be calculated between the top of the
authorized rule curve and a definable lower elevation limit which could be a timeseries.
Mini simulations will predict elevations for April through October, starting with the
storage at each reservoir on 01-April. Reservoirs can be excluded from the calculation.

Final reservoir minimum-flow requirement is the max of the Salem-driven and Albany-driven
augmentation requirements.

This script is intended to be run after a simulation has already been computed that has no flow-aug.
"""

import pandas as pd
from pydsstools.heclib.dss import HecDss
from pydsstools.core import TimeSeriesContainer
import numpy as np
import os
import time
import pathlib
import datetime
from datetime import timedelta
from pathlib import Path
import pickle
import cProfile
import RunControlConfig as cfg
# reload
import importlib
importlib.reload(cfg)
# =====================================================================
# CONFIG / PATHS
# =====================================================================

# externalSVs directory: ../externalSVs from this script
CUR_DIR = Path(__file__).resolve().parent
PARENT_PATH = Path(__file__).resolve().parent.parent
PKL_PATH = CUR_DIR / "median_remaining_by_day.pkl"
EXTERNAL_SV_DIR = PARENT_PATH / "externalSVs"

MINFLOW_CONFIG_CSV = EXTERNAL_SV_DIR / "MinFlowSalemAlbanyConfig.csv"

# WY-type flow target tables (Salem and Albany)
WY_TYPE_FLOW_SALEM_CSV  = EXTERNAL_SV_DIR / "MinFlowSalem_2008BiOp.csv"
WY_TYPE_FLOW_ALBANY_CSV = EXTERNAL_SV_DIR / "MinFlowAlbany_2008BiOp.csv"

# =====================================================================
# HELPER FUNCTIONS
# =====================================================================

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
    Ensure date columns look like '1Jan', '16Apr', etc.
    If you get '01-Jun' out of Excel, this will convert to '1Jun'.
    Non-date columns (e.g. 'WY_type') are passed through.
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
    return f"{day_int}{month}"


def load_wy_type_flow_dict(csv_path: Path) -> dict[float, dict[str, int]]:
    """
    Reads a CSV of the form:

        # comment...
        WY_type,1-Jan,1-Apr,16-Apr,1-May,1-Jun,16-Jun,1-Jul,1-Aug,16-Aug,1-Sep,1-Oct,1-Nov
        0,0,15000,15000,15000,11000,5500,5000,5000,5000,5000,5000,0
        0.9, ...

    and returns:

        {
          0: {"1-Jan": 0, "1-Apr": 15000, ..., "1-Nov": 0, "31-Dec": 0},
          0.9: {...},
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

    wy_type_flow_dict: dict[float, dict[str, int]] = {}

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
        # Ensure '31-Dec' is present; default 0
        if "31-Dec" not in inner:
            inner["31-Dec"] = 0

        wy_type_flow_dict[float(wy_type)] = inner

    return wy_type_flow_dict


# =====================================================================
# 1) Load MinFlowSalemAlbanyConfig.csv (skip first 3 lines)
# =====================================================================

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

# Separate support flags for Salem and Albany
AUG_SALEM_RESERVOIRS_DICT = {
    res: _to_bool(minflow_df.loc["SupportsSalem", res])
    for res in reservoir_names
}

AUG_ALBANY_RESERVOIRS_DICT = {
    res: _to_bool(minflow_df.loc["SupportsAlbany", res])
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

# MinConStor (AF) from config (used to compute usable storage on Apr 1)
MIN_CON_STOR_DICT = {}
if "MinConStor" in minflow_df.index:
    for res in reservoir_names:
        val = minflow_df.loc["MinConStor", res]
        if pd.notna(val) and str(val).strip() != "":
            MIN_CON_STOR_DICT[res] = float(val)

# =====================================================================
# 2) Load RunControl config
# =====================================================================

SIM_NAME = cfg.SIM_NAME
ALTERNATIVE_NAME_STEP1 = cfg.ALTERNATIVE_NAME_STEP1
FORECAST_DAYS = cfg.FORECAST_DAYS
PERIOD_START = cfg.PERIOD_START
PERIOD_END = cfg.PERIOD_END

# Additional CONFIG
AF_PER_CFS_DAY = 24 * 60 * 60 / 43560.0

# Get watershed directory relative to this script's location
WATERSHED_DIR = pathlib.Path(__file__).resolve().parent.parent.parent

# Build CWMS specific path
sim_dir = SIM_NAME.replace(" ", "_")

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent

# ============================================================
# BUILD RELATIVE PATH FROM SCRIPT LOCATION
# Go up one directory from script, then:
#    rss/<simulation_name>/simulation.dss
# ============================================================

DSS_PATH = (
    WATERSHED_DIR
    / "rss"
    / sim_dir
    / "simulation.dss"
).resolve()

DSS_FILE_OUT = str(DSS_PATH)
DSS_FILE_IN = DSS_FILE_OUT  # same file for read/write in this script

print("DSS_FILE_OUT:", DSS_FILE_OUT)

# =====================================================================
# PRINT STATEMENTS
# =====================================================================

print("MinFlowSalemAlbanyConfig.csv:", str(MINFLOW_CONFIG_CSV))
print("WY_TYPE_FLOW_SALEM_CSV:", str(WY_TYPE_FLOW_SALEM_CSV))
print("WY_TYPE_FLOW_ALBANY_CSV:", str(WY_TYPE_FLOW_ALBANY_CSV))
print("DSS In/Out File:", str(DSS_FILE_IN))
print("Simulation Name", SIM_NAME)
print("Alternative name", ALTERNATIVE_NAME_STEP1)
print("Salem Aug Reservoirs:", AUG_SALEM_RESERVOIRS_DICT)
print("Albany Aug Reservoirs:", AUG_ALBANY_RESERVOIRS_DICT)

# =====================================================================
# FUNCTIONS
# =====================================================================

def readallpaths(dss_file, path_dict, fid=None):
    _opened_here = False
    if fid is None:
        fid = HecDss.Open(dss_file, version=6)
        _opened_here = True

    dflist = []
    try:
        for alias, path in path_dict.items():
            try:
                ts = fid.read_ts(path, trim_missing=True)
                df = pd.DataFrame(ts.values, columns=[alias], index=np.array(ts.pytimes))
                dflist.append(df.copy())
            except Exception as e:
                msg = f"[DSS] Failed '{alias}' -> {path} in {os.path.basename(dss_file)}: {e}"
                print(msg)
    finally:
        if _opened_here:
            fid.close()

    if not dflist:
        return pd.DataFrame()

    data = pd.concat(dflist, axis=1)
    data.index = pd.to_datetime(data.index)
    data = data[~data.index.duplicated(keep="last")]
    return data


def calculate_storage_on_date(data, date, minConStor):
    """
    Calculate usable storage (STOR - minConStor) on a given month/day for each year.
    Returns DataFrame indexed by year, columns for each reservoir's storage column.
    """
    month, day = date
    stor_cols = [c for c in data.columns if c.endswith("_stor")]
    storage_on_date = data[stor_cols].copy()
    storage_on_date = storage_on_date[
        (storage_on_date.index.month == month) & (storage_on_date.index.day == day)
    ]
    storage_on_date.index = storage_on_date.index.year
    for res, short in ALIAS_DICT.items():
        col = f"{short}_stor"
        if col in storage_on_date.columns and res in minConStor:
            storage_on_date[col] = storage_on_date[col] - minConStor[res]
    return storage_on_date


def create_gauge_minflow_ts(wtTypeFlowTable, data, gauge_prefix: str):
    """
    Create a time series for the minimum flow at a downstream gauge
    (e.g. SLM or ALB) based on the water year type stored for the baseline simulation.

    gauge_prefix: 'SLM', 'ALB', etc.
    Output column: f"{gauge_prefix}_minflow"
    """
    daily_wy_type = data[['WY_type']].copy()

    # May 16 WY_type (same logic as before)
    May16_sys_storage = daily_wy_type[daily_wy_type.index.month == 5]
    May16_sys_storage = May16_sys_storage[May16_sys_storage.index.day == 16]
    May16_sys_storage.index = May16_sys_storage.index.year

    flow_list = []
    for year, row in May16_sys_storage.iterrows():
        storage = row['WY_type']  # MAF
        if storage <= 0:
            wt_type = 0
        elif storage <= 0.9:
            wt_type = 0.9
        elif storage <= 1.2:
            wt_type = 1.2
        else:
            wt_type = 1.48

        flow_schedule = wtTypeFlowTable[wt_type]
        for date_str, flow in flow_schedule.items():
            date = pd.to_datetime(f"{date_str}{year}")  # date_str like "01Apr"
            flow_list.append({'Date': date, f'{gauge_prefix}_minflow': flow})

    minflow_df = pd.DataFrame(flow_list)
    minflow_df.set_index('Date', inplace=True)
    minflow_df.sort_index(inplace=True)
    minflow_df = minflow_df.resample('D').ffill()

    data = data.copy()
    data = data.join(minflow_df, how='left')
    col = f"{gauge_prefix}_minflow"
    data[col] = data[col].fillna(0)
    return data


def compute_net_inflows(data, alias):
    """Compute net inflows (inflow - minflow) for each reservoir. Units CFS."""
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


def create_net_inflow_pivot_tables(data, alias, Period_Start, Period_End):
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
        idx = df.index
        mask = (
            ((idx.month > start_month) | ((idx.month == start_month) & (idx.day >= start_day))) &
            ((idx.month < end_month)   | ((idx.month == end_month)   & (idx.day <= end_day)))
        )
        df = df[mask]
        df['Year'] = df.index.year
        df['Month-Day'] = df.index.strftime('%m-%d')
        pivot_table = df.pivot_table(
            index='Month-Day',
            columns='Year',
            values=net_col,
            aggfunc='sum',
            fill_value=0.0,
        )
        month_days = pd.date_range(
            f"2001-{start_month:02d}-{start_day:02d}",
            f"2001-{end_month:02d}-{end_day:02d}",
            freq='D'
        ).strftime('%m-%d')
        pivot_table = pivot_table.reindex(month_days, fill_value=0.0)
        net_inflow_pivot_tables[short] = pivot_table
    return net_inflow_pivot_tables


def create_remaining_volume_pivot_tables(pivot_tables, AF_PER_CFS_DAY):
    """
    Create remaining volume tables from pivot tables.
    Each table has years as columns and month-day as index.
    Values are cumulative forward sums (AF).
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
    Returns {short: Series}.
    """
    median_remaining_by_day = {}
    for short, rem_table in remaining_volume_pivot_tables.items():
        if rem_table is None or rem_table.empty:
            continue
        median_series = rem_table.median(axis=1)
        median_series.name = f"{short}_median_remaining_AF"
        median_remaining_by_day[short] = median_series
    return median_remaining_by_day


def create_short_forecast_volume_pivot_tables(pivot_tables, forecast_days, AF_PER_CFS_DAY):
    """
    Create forecast volume tables from pivot tables.
    Each table has years as columns and month-day as index.
    Values are forward-looking rolling sums (AF).
    """
    short_forecast_volume_pivot_tables = {}
    for res, pivot_table in pivot_tables.items():
        forecast_table = pivot_table.iloc[::-1].rolling(
            window=forecast_days, min_periods=1
        ).sum().iloc[::-1]
        forecast_table = forecast_table * AF_PER_CFS_DAY
        short_forecast_volume_pivot_tables[res] = forecast_table
    return short_forecast_volume_pivot_tables


def create_total_available_volume_pivot_tables(
    short_forecast_volume_pivot_tables,
    Forecast_Days_Assumption,
    April01_conStorage,
    median_remaining_by_day,
):
    """
    Total available (for augmentation) =

        short_forecast_volume (AF over next k days, per year)
      + median remaining seasonal volume AFTER the forecast window (AF)
      + Apr01 usable storage (AF) for that year

    Returns {short: DataFrame}
    """
    total_available_volume_pivot_tables = {}
    k = Forecast_Days_Assumption

    for short, fct_table in short_forecast_volume_pivot_tables.items():
        if fct_table is None:
            continue

        if isinstance(fct_table, pd.Series):
            col_name = fct_table.name if fct_table.name is not None else "Year"
            fct_table = fct_table.to_frame(name=col_name)

        if fct_table.empty:
            continue

        fct_table = fct_table.copy()
        fct_table = fct_table.sort_index()
        fct_table = fct_table.fillna(0.0)

        med_series = median_remaining_by_day.get(short)
        if med_series is None or med_series.empty:
            med_series = pd.Series(0.0, index=fct_table.index)

        med_series = med_series.reindex(fct_table.index, fill_value=0.0)
        median_matrix = pd.DataFrame(
            {year: med_series.values for year in fct_table.columns},
            index=fct_table.index,
        )

        rem_after = median_matrix.shift(-k)
        combined = rem_after.add(fct_table, fill_value=0.0)

        colname = f"{short}_stor"
        for year in combined.columns:
            add_stor = 0.0
            if year in April01_conStorage.index and colname in April01_conStorage.columns:
                add_stor = float(April01_conStorage.loc[year, colname])
            combined[year] = combined[year] + add_stor

        total_available_volume_pivot_tables[short] = combined.fillna(0.0)

    return total_available_volume_pivot_tables


def create_gauge_deficit_pivot_table(data, gauge_prefix: str, Period_Start, Period_End):
    """
    Create a pivot table for deficit at a given gauge (e.g. Salem or Albany).
    Uses columns:
      - f"{gauge_prefix}_flow"
      - f"{gauge_prefix}_minflow"
    Returns a pivot table (index='MM-DD', columns=Year).
    Units are CFS (minflow - actual).
    """
    start_month, start_day = Period_Start
    end_month, end_day = Period_End

    flow_col    = f"{gauge_prefix}_flow"
    minflow_col = f"{gauge_prefix}_minflow"
    deficit_col = f"{gauge_prefix}_deficit"

    df = data[[flow_col, minflow_col]].copy()
    df[deficit_col] = df[minflow_col] - df[flow_col]

    idx = df.index
    mask = (
        ((idx.month > start_month) | ((idx.month == start_month) & (idx.day >= start_day))) &
        ((idx.month < end_month)   | ((idx.month == end_month)   & (idx.day <= end_day)))
    )
    df = df[mask]

    df['Year'] = df.index.year
    df['Month-Day'] = df.index.strftime('%m-%d')

    deficit_pivot_table = df.pivot_table(
        index='Month-Day',
        columns='Year',
        values=deficit_col,
        aggfunc='sum',
        fill_value=0.0,
    )

    month_days = pd.date_range(
        f"2001-{start_month:02d}-{start_day:02d}",
        f"2001-{end_month:02d}-{end_day:02d}",
        freq='D'
    ).strftime('%m-%d')
    deficit_pivot_table = deficit_pivot_table.reindex(month_days, fill_value=0.0)

    return deficit_pivot_table


def create_augmentation_proportion_tables(total_available_volume_pivot_tables, AugReservoirs, alias):
    """
    Compute daily proportions of total available system storage for the reservoirs selected
    in AugReservoirs. Accepts either:
      - dict: { "Detroit": True/False, ... } (truthy means include)
      - iterable/list: ["Detroit", "Lookout Point", ...]
    Assumes identical index/columns across tables.
    Negatives are clipped to 0 before summing/dividing.
    Returns: {short: proportion_table_df}
    """
    if isinstance(AugReservoirs, dict):
        selected = [res for res, use in AugReservoirs.items() if use]
    else:
        selected = list(AugReservoirs)

    tables = {
        alias[res]: total_available_volume_pivot_tables[alias[res]].clip(lower=0.0)
        for res in selected
        if res in alias and alias[res] in total_available_volume_pivot_tables
    }
    if not tables:
        return {}

    iter_tables = iter(tables.values())
    first = next(iter_tables)
    total = first.copy() * 0.0
    total += first
    for t in iter_tables:
        total += t

    denom = total.replace(0.0, np.nan)
    augmentation_proportion_pivot_tables = {
        short: (tbl / denom).fillna(0.0) for short, tbl in tables.items()
    }
    return augmentation_proportion_pivot_tables


def create_agumentation_flow_pivot_tables(
    augmentation_proportion_pivot_tables,
    deficit_pivot_table
):
    """
    Create augmentation flow pivot tables by multiplying the gauge deficit pivot table
    with each reservoir's augmentation proportion pivot table.
    Returns: {short: augmentation_flow_table_df}
    Units are CFS.
    """
    augmentation_flow_pivot_tables = {}
    for short, prop_table in augmentation_proportion_pivot_tables.items():
        aligned_deficit = deficit_pivot_table.reindex(
            index=prop_table.index,
            columns=prop_table.columns,
            fill_value=0.0,
        )
        aug_flow_table = aligned_deficit * prop_table
        augmentation_flow_pivot_tables[short] = aug_flow_table
    return augmentation_flow_pivot_tables


def melt_pivot_to_series(pivot_table, new_name, start_dt, end_dt, fill_value=0.0):
    """
    Convert a pivot table (index='MM-DD', columns=Year) to a single time series.
    The index is a DatetimeIndex with full dates, and the values are from the pivot table.
    Missing dates are filled with fill_value.
    The series is trimmed to [start_dt, end_dt].
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
    full_series = full_series[
        (full_series.index >= pd.to_datetime(start_dt)) &
        (full_series.index <= pd.to_datetime(end_dt))
    ]
    full_series.name = new_name
    return full_series


def add_augmentation_to_outflows(
    data,
    alias,
    Period_Start,
    Period_End,
    TravelTimeDays=None,
    aug_suffix="_augmentation_flow",
    out_suffix="_min_flow_with_aug",
):
    """
    Add augmentation flows (shifted by travel time) to original outflows to create
    new minimum outflow series for each reservoir.

    aug_suffix: suffix of augmentation column name (e.g. '_augmentation_SLM_flow')
    out_suffix: suffix of output column name (e.g. '_min_flow_with_aug_SLM')
    """
    df = data.copy()
    TravelTimeDays = TravelTimeDays or {}

    sm, sd = Period_Start
    # start two days earlier to account for travel time.
    startDT = datetime.datetime(2001, sm, sd) - timedelta(days=2)
    sm = startDT.month
    sd = startDT.day
    em, ed = Period_End
    idx = df.index

    period_mask = (
        ((idx.month > sm) | ((idx.month == sm) & (idx.day >= sd))) &
        ((idx.month < em) | ((idx.month == em) & (idx.day <= ed)))
    )
    apply_mask = period_mask

    for res, short in alias.items():
        out_col = f"{short}_outflow"
        aug_col = f"{short}{aug_suffix}"
        new_col = f"{short}{out_suffix}"

        df[new_col] = 0.0
        if aug_col not in df.columns:
            continue

        tt_days = int(TravelTimeDays.get(res, 0))
        aug_shift = pd.to_numeric(df[aug_col], errors='coerce').shift(-tt_days)

        max_flow = MAX_FLOW_DICT.get(res, np.inf)
        df.loc[apply_mask, new_col] = (
            df.loc[apply_mask, out_col] +
            aug_shift.loc[apply_mask]
        ).clip(upper=max_flow)

    return df


def write_outflows_to_dss(
    data: pd.DataFrame,
    alias: dict,
    dss_file_write: str,
    c_part_out: str,
    f_part_out: str,
    col_ext: str,
    decimals: int = 1,
    fid=None,  # optional open HecDss handle
) -> int:
    """
    Write series to a DSS-6 file.

    If `fid` is provided, it is reused and NOT closed here.
    If `fid` is None, the function opens/closes the DSS file internally.

    For each (long, short) in alias, writes column f"{short}{col_ext}" if present.

    Pathname: //{RES}/{c_part_out}//1DAY/{f_part_out}/
    Units: CFS, Type: PER-AVER, Interval: 1440 minutes (daily).
    Values are rounded to `decimals` places.
    Returns: count of series written.
    """
    def _dss_datetime(ts: pd.Timestamp) -> str:
        return ts.strftime("%d%b%Y %H%M")

    if not isinstance(data.index, pd.DatetimeIndex):
        raise TypeError("`data` must have a DatetimeIndex.")
    if data.index.empty:
        raise ValueError("`data.index` is empty; nothing to write.")

    out_dir = os.path.dirname(dss_file_write)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

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

        pathname = f"//{long.upper()}/{c_part_out}//1DAY/{f_part_out}/"
        to_write.append((pathname, series))

    if not to_write:
        print("No series to write.")
        return 0

    written = 0
    _opened_here = False
    if fid is None:
        fid = HecDss.Open(dss_file_write, version=6)
        _opened_here = True

    try:
        for pathname, series in to_write:
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

            fid.put_ts(tsc)
            written += 1
            print(f"[write_outflows_v6] Wrote: {tsc.pathname}")
    finally:
        if _opened_here:
            fid.close()

    print(f"[write_outflows_v6] Wrote {written} series to DSS.")
    return written


# =====================================================================
# MAIN PROCESSING
# =====================================================================

prof = cProfile.Profile()
prof.enable()

start_time = time.time()
total_written = 0

enesemble_years = list(range(1981, 2029))
#make the alternative name the ALTERNATIVE_NAME_STEP1 with the last digit 0 and any spaces inbetween filled with -. The full formatted alternative name must be 11 digits long.
FORMATTED_ALT_NAME = ALTERNATIVE_NAME_STEP1

# If FORMATTED_ALT_NAME is less than 10 charactars, add dashes until it is 10 cahracters and then add a 0 at the end.
FORMATTED_ALT_NAME = FORMATTED_ALT_NAME.replace(" ", "-")
if len(FORMATTED_ALT_NAME) < 10:
    FORMATTED_ALT_NAME = FORMATTED_ALT_NAME.ljust(10, "-")
    FORMATTED_ALT_NAME = FORMATTED_ALT_NAME + "0"
else:
    FORMATTED_ALT_NAME = FORMATTED_ALT_NAME + "0"

fparts = [f"C:00{year}|{FORMATTED_ALT_NAME}" for year in enesemble_years]

# ---------------------------------------------------------
# Load static inputs ONCE (not per ensemble year)
# ---------------------------------------------------------

with open(PKL_PATH, "rb") as f:
    MEDIAN_REMAINING_BY_DAY = pickle.load(f)

WY_TYPE_FLOW_SLM = load_wy_type_flow_dict(WY_TYPE_FLOW_SALEM_CSV)
WY_TYPE_FLOW_ALB = load_wy_type_flow_dict(WY_TYPE_FLOW_ALBANY_CSV)

# ---------------------------------------------------------
# Open DSS OUT ONCE (reused for all ensemble years)
# ---------------------------------------------------------
fid_in = HecDss.Open(DSS_FILE_IN, version=6)
fid_out = HecDss.Open(DSS_FILE_OUT, version=6)
try:
    # Do the flow aug for each alternative (f-part)
    for fpart in fparts:

        # All necessary inflows, outflows, storages, etc.
        path_dict = {
            "LOP_stor": f"//LOOKOUT POINT-POOL/STOR//1DAY/{fpart}/",
            "LOP_inflow": f"//LOOKOUT POINT-POOL/FLOW-IN//1DAY/{fpart}/",
            "LOP_outflow": f"//LOOKOUT POINT-POOL/FLOW-OUT//1DAY/{fpart}/",
            "LOP_rcStor": f"//LOOKOUT POINT-RULE CURVE/STOR-ZONE//1DAY/{fpart}/",

            "DET_stor": f"//DETROIT-POOL/STOR//1DAY/{fpart}/",
            "DET_inflow": f"//DETROIT-POOL/FLOW-IN//1DAY/{fpart}/",
            "DET_outflow": f"//DETROIT-POOL/FLOW-OUT//1DAY/{fpart}/",
            "DET_rcStor": f"//DETROIT-RULE CURVE/STOR-ZONE//1DAY/{fpart}/",

            "GPR_stor": f"//GREEN PETER-POOL/STOR//1DAY/{fpart}/",
            "GPR_inflow": f"//GREEN PETER-POOL/FLOW-IN//1DAY/{fpart}/",
            "GPR_outflow": f"//GREEN PETER-POOL/FLOW-OUT//1DAY/{fpart}/",
            "GPR_rcStor": f"//GREEN PETER-RULE CURVE/STOR-ZONE//1DAY/{fpart}/",

            "CGR_stor": f"//COUGAR-POOL/STOR//1DAY/{fpart}/",
            "CGR_inflow": f"//COUGAR-POOL/FLOW-IN//1DAY/{fpart}/",
            "CGR_outflow": f"//COUGAR-POOL/FLOW-OUT//1DAY/{fpart}/",
            "CGR_rcStor": f"//COUGAR-RULE CURVE/STOR-ZONE//1DAY/{fpart}/",

            "BLU_stor": f"//BLUE RIVER-POOL/STOR//1DAY/{fpart}/",
            "BLU_inflow": f"//BLUE RIVER-POOL/FLOW-IN//1DAY/{fpart}/",
            "BLU_outflow": f"//BLUE RIVER-POOL/FLOW-OUT//1DAY/{fpart}/",
            "BLU_rcStor": f"//BLUE RIVER-RULE CURVE/STOR-ZONE//1DAY/{fpart}/",

            "FAL_stor": f"//FALL CREEK-POOL/STOR//1DAY/{fpart}/",
            "FAL_inflow": f"//FALL CREEK-POOL/FLOW-IN//1DAY/{fpart}/",
            "FAL_outflow": f"//FALL CREEK-POOL/FLOW-OUT//1DAY/{fpart}/",
            "FAL_rcStor": f"//FALL CREEK-RULE CURVE/STOR-ZONE//1DAY/{fpart}/",

            "HCR_stor": f"//HILLS CREEK-POOL/STOR//1DAY/{fpart}/",
            "HCR_inflow": f"//HILLS CREEK-POOL/FLOW-IN//1DAY/{fpart}/",
            "HCR_outflow": f"//HILLS CREEK-POOL/FLOW-OUT//1DAY/{fpart}/",
            "HCR_rcStor": f"//HILLS CREEK-RULE CURVE/STOR-ZONE//1DAY/{fpart}/",

            "DOR_stor": f"//DORENA-POOL/STOR//1DAY/{fpart}/",
            "DOR_inflow": f"//DORENA-POOL/FLOW-IN//1DAY/{fpart}/",
            "DOR_outflow": f"//DORENA-POOL/FLOW-OUT//1DAY/{fpart}/",
            "DOR_rcStor": f"//DORENA-RULE CURVE/STOR-ZONE//1DAY/{fpart}/",

            "COT_stor": f"//COTTAGE GROVE-POOL/STOR//1DAY/{fpart}/",
            "COT_inflow": f"//COTTAGE GROVE-POOL/FLOW-IN//1DAY/{fpart}/",
            "COT_outflow": f"//COTTAGE GROVE-POOL/FLOW-OUT//1DAY/{fpart}/",
            "COT_rcStor": f"//COTTAGE GROVE-RULE CURVE/STOR-ZONE//1DAY/{fpart}/",

            "FRN_stor": f"//FERN RIDGE-POOL/STOR//1DAY/{fpart}/",
            "FRN_inflow": f"//FERN RIDGE-POOL/FLOW-IN//1DAY/{fpart}/",
            "FRN_outflow": f"//FERN RIDGE-POOL/FLOW-OUT//1DAY/{fpart}/",
            "FRN_rcStor": f"//FERN RIDGE-RULE CURVE/STOR-ZONE//1DAY/{fpart}/",

            "FOS_stor": f"//FOSTER-POOL/STOR//1DAY/{fpart}/",
            "FOS_rcStor": f"//FOSTER-RULE CURVE/STOR-ZONE//1DAY/{fpart}/",

            "ALB_flow": f"//WILLAMETTE_AT ALBANY/FLOW//1DAY/{fpart}/",
            "SLM_flow": f"//WILLAMETTE_AT SALEM/FLOW//1DAY/{fpart}/",

            "WY_type": f"//WATERYEARTYPEVARIABLE/STOR-MAF//1DAY/{fpart}/",

            "FRN_minflow": f"//FERN RIDGE-DAM-BIOP MINTRIB AND WITHDRAWALS BY WY/FLOW-MIN//1DAY/{fpart}/",
            "DOR_minflow": f"//DORENA-DAM-BIOP MINTRIB AND WITHDRAWALS BY WY/FLOW-MIN//1DAY/{fpart}/",
            "COT_minflow": f"//COTTAGE GROVE-DAM-BIOP MINTRIB AND WITHDRAWALS BY WY/FLOW-MIN//1DAY/{fpart}/",
            "FAL_minflow": f"//FALL CREEK-DAM-BIOP MINTRIB AND WITHDRAWALS BY WY/FLOW-MIN//1DAY/{fpart}/",
            "HCR_minflow": f"//HILLS CREEK-DAM-BIOP MINTRIB AND WITHDRAWALS BY WY/FLOW-MIN//1DAY/{fpart}/",
            "LOP_minflow": f"//LOOKOUT POINT-DAM-BIOP MINTRIB AND WITHDRAWALS BY WY/FLOW-MIN//1DAY/{fpart}/",
            "CGR_minflow": f"//COUGAR-DAM-BIOP MINTRIB AND WITHDRAWALS BY WY/FLOW-MIN//1DAY/{fpart}/",
            "BLU_minflow": f"//BLUE RIVER-DAM-BIOP MINTRIB AND WITHDRAWALS BY WY/FLOW-MIN//1DAY/{fpart}/",
            "GPR_minflow": f"//BIOP MINTRIB AND WITHDRAWAL BY WY FOR FOS/FLOW-MIN//1DAY/{fpart}/",
            "DET_minflow": f"//DETROIT-DAM-BIOP MINTRIB AND WITHDRAWALS BY WY/FLOW-MIN//1DAY/{fpart}/",
        }

        # Read DSS data
        # --- FILTER: keep only reservoirs used in flow aug (plus HCR for LOP merge) ---
        salem_selected = {res for res, use in AUG_SALEM_RESERVOIRS_DICT.items() if use}
        alb_selected   = {res for res, use in AUG_ALBANY_RESERVOIRS_DICT.items() if use}
        selected = (salem_selected | alb_selected)

        # Convert to short codes (e.g., "LOP")
        keep_shorts = {ALIAS_DICT[res] for res in selected if res in ALIAS_DICT}

        # Always keep HCR because you merge it into LOP later
        keep_shorts.add("HCR")

        # Always keep these non-reservoir series
        always_keys = {"ALB_flow", "SLM_flow", "WY_type"}

        filtered_path_dict = {}
        for k, v in path_dict.items():
            if k in always_keys:
                filtered_path_dict[k] = v
                continue

            # Keys like "LOP_inflow", "DET_rcStor", etc.
            if "_" not in k:
                continue

            short, _suffix = k.split("_", 1)
            if short in keep_shorts:
                # Skip rule-curve storage records (minConStor is hard-coded from config)
                if _suffix == "rcStor":
                    continue
                filtered_path_dict[k] = v

        data = readallpaths(DSS_FILE_IN, filtered_path_dict, fid=fid_in)

        # Compute minConStor_dict from rule curve storages on 01Jan
        minConStor_dict = dict(MIN_CON_STOR_DICT)

        # Modify LOP record to be a super-reservoir (LOP + HCR)
        data["LOP_stor"] = data["LOP_stor"] + data["HCR_stor"]
        data["LOP_inflow"] = data["LOP_inflow"] + data["HCR_inflow"] - data["HCR_outflow"]
        minConStor_dict["Lookout Point"] = (
            minConStor_dict.get("Lookout Point", 0.0) + minConStor_dict.get("Hills Creek", 0.0)
        )

        START_DT = data.index[0].strftime("%Y-%m-%d")
        END_DT = data.index[-1].strftime("%Y-%m-%d")

        # Compute net inflows (inflow - local minflow)
        data = compute_net_inflows(data, ALIAS_DICT)

        # April 1 storage and usable storage
        April01_storage = calculate_storage_on_date(data, PERIOD_START, minConStor_dict)
        April01_conStorage = April01_storage.copy()
        for res, short in ALIAS_DICT.items():
            colname = f"{short}_stor"
            if colname in April01_conStorage.columns:
                con_stor = minConStor_dict.get(res, 0.0)
                April01_conStorage[colname] = April01_storage[colname] - con_stor

        # Net inflow pivot tables for deficit period
        net_inflow_pivot_tables = create_net_inflow_pivot_tables(
            data, ALIAS_DICT, PERIOD_START, PERIOD_END
        )

        # Median remaining seasonal volume loaded from PKL
        short_forecast_volume_pivot_tables = create_short_forecast_volume_pivot_tables(
            net_inflow_pivot_tables, FORECAST_DAYS, AF_PER_CFS_DAY
        )
        total_available_volume_pivot_tables = create_total_available_volume_pivot_tables(
            short_forecast_volume_pivot_tables,
            FORECAST_DAYS,
            April01_conStorage,
            MEDIAN_REMAINING_BY_DAY,
        )

        # ---------------------------------------------------------
        # Salem augmentation pass
        # ---------------------------------------------------------
        data = create_gauge_minflow_ts(WY_TYPE_FLOW_SLM, data, gauge_prefix="SLM")

        augmentation_proportion_pivot_tables_SLM = create_augmentation_proportion_tables(
            total_available_volume_pivot_tables,
            AUG_SALEM_RESERVOIRS_DICT,
            ALIAS_DICT,
        )

        salem_deficit_pivot_table = create_gauge_deficit_pivot_table(
            data,
            gauge_prefix="SLM",
            Period_Start=PERIOD_START,
            Period_End=PERIOD_END,
        )

        augmentation_flow_pivot_tables_SLM = create_agumentation_flow_pivot_tables(
            augmentation_proportion_pivot_tables_SLM,
            salem_deficit_pivot_table,
        )

        for short, aug_flow_table in augmentation_flow_pivot_tables_SLM.items():
            series = melt_pivot_to_series(
                aug_flow_table,
                new_name=f"{short}_augmentation_SLM_flow",
                start_dt=START_DT,
                end_dt=END_DT,
                fill_value=0.0,
            )
            data[series.name] = series

        salem_deficit_series = melt_pivot_to_series(
            salem_deficit_pivot_table,
            new_name="SLM_deficit",
            start_dt=START_DT,
            end_dt=END_DT,
            fill_value=0.0,
        )
        data["SLM_deficit"] = salem_deficit_series

        data = add_augmentation_to_outflows(
            data,
            ALIAS_DICT,
            PERIOD_START,
            PERIOD_END,
            TravelTimeDays=TRAVEL_TIME_DAYS_DICT,
            aug_suffix="_augmentation_SLM_flow",
            out_suffix="_min_flow_with_aug_SLM",
        )

        # ---------------------------------------------------------
        # Albany augmentation pass
        # ---------------------------------------------------------
        data = create_gauge_minflow_ts(WY_TYPE_FLOW_ALB, data, gauge_prefix="ALB")

        augmentation_proportion_pivot_tables_ALB = create_augmentation_proportion_tables(
            total_available_volume_pivot_tables,
            AUG_ALBANY_RESERVOIRS_DICT,
            ALIAS_DICT,
        )

        albany_deficit_pivot_table = create_gauge_deficit_pivot_table(
            data,
            gauge_prefix="ALB",
            Period_Start=PERIOD_START,
            Period_End=PERIOD_END,
        )

        augmentation_flow_pivot_tables_ALB = create_agumentation_flow_pivot_tables(
            augmentation_proportion_pivot_tables_ALB,
            albany_deficit_pivot_table,
        )

        for short, aug_flow_table in augmentation_flow_pivot_tables_ALB.items():
            series = melt_pivot_to_series(
                aug_flow_table,
                new_name=f"{short}_augmentation_ALB_flow",
                start_dt=START_DT,
                end_dt=END_DT,
                fill_value=0.0,
            )
            data[series.name] = series

        albany_deficit_series = melt_pivot_to_series(
            albany_deficit_pivot_table,
            new_name="ALB_deficit",
            start_dt=START_DT,
            end_dt=END_DT,
            fill_value=0.0,
        )
        data["ALB_deficit"] = albany_deficit_series

        data = add_augmentation_to_outflows(
            data,
            ALIAS_DICT,
            PERIOD_START,
            PERIOD_END,
            TravelTimeDays=TRAVEL_TIME_DAYS_DICT,
            aug_suffix="_augmentation_ALB_flow",
            out_suffix="_min_flow_with_aug_ALB",
        )

        # ---------------------------------------------------------
        # Final reservoir min flow = max(Salem-driven, Albany-driven)
        # ---------------------------------------------------------
        for res, short in ALIAS_DICT.items():
            col_salem = f"{short}_min_flow_with_aug_SLM"
            col_alb   = f"{short}_min_flow_with_aug_ALB"
            col_final = f"{short}_min_flow_with_aug"

            s_salem = pd.to_numeric(
                data[col_salem] if col_salem in data.columns else 0.0,
                errors="coerce",
            ).fillna(0.0)

            s_alb = pd.to_numeric(
                data[col_alb] if col_alb in data.columns else 0.0,
                errors="coerce",
            ).fillna(0.0)

            data[col_final] = np.maximum(s_salem, s_alb)

        # =====================================================================
        # WRITE TO DSS (reuse fid_out)
        # =====================================================================

        written_count = 0

        # 1) Final min flows (max(Salem, Albany)) – what ResSim should use
        written_count += write_outflows_to_dss(
            data,
            ALIAS_DICT,
            DSS_FILE_OUT,
            c_part_out="FLOW-MIN-EXTERNALFLOWAUG",
            f_part_out=fpart,
            col_ext="_min_flow_with_aug",
            decimals=1,
            fid=fid_out,
        )

        # Salem-driven min flows
        written_count += write_outflows_to_dss(
            data,
            ALIAS_DICT,
            DSS_FILE_OUT,
            c_part_out="FLOW-MIN-EXTERNALFLOWAUG-SLM",
            f_part_out=fpart,
            col_ext="_min_flow_with_aug_SLM",
            decimals=1,
            fid=fid_out,
        )

        # Albany-driven min flows
        written_count += write_outflows_to_dss(
            data,
            ALIAS_DICT,
            DSS_FILE_OUT,
            c_part_out="FLOW-MIN-EXTERNALFLOWAUG-ALB",
            f_part_out=fpart,
            col_ext="_min_flow_with_aug_ALB",
            decimals=1,
            fid=fid_out,
        )

        # Salem deficit and minflow
        written_count += write_outflows_to_dss(
            data[['SLM_deficit']],
            {'Salem': 'SLM'},
            DSS_FILE_OUT,
            c_part_out="FLOW-DEFICIT-EXTERNALFLOWAUG",
            f_part_out=fpart,
            col_ext="_deficit",
            decimals=1,
            fid=fid_out,
        )

        written_count += write_outflows_to_dss(
            data[['SLM_minflow']],
            {'Salem': 'SLM'},
            DSS_FILE_OUT,
            c_part_out="FLOW-MIN-EXTERNALFLOWAUG",
            f_part_out=fpart,
            col_ext="_minflow",
            decimals=1,
            fid=fid_out,
        )

        # Albany deficit and minflow
        written_count += write_outflows_to_dss(
            data[['ALB_deficit']],
            {'Albany': 'ALB'},
            DSS_FILE_OUT,
            c_part_out="FLOW-DEFICIT-EXTERNALFLOWAUG",
            f_part_out=fpart,
            col_ext="_deficit",
            decimals=1,
            fid=fid_out,
        )

        written_count += write_outflows_to_dss(
            data[['ALB_minflow']],
            {'Albany': 'ALB'},
            DSS_FILE_OUT,
            c_part_out="FLOW-MIN-EXTERNALFLOWAUG",
            f_part_out=fpart,
            col_ext="_minflow",
            decimals=1,
            fid=fid_out,
        )

        total_written += written_count
        print(f"[{fpart}] Wrote {written_count} series.")

finally:
    fid_in.close()
    fid_out.close()

prof.disable()
stats_path = Path(__file__).with_suffix(".pstats")
prof.dump_stats(str(stats_path))

# Human-readable summary in console (top 40)
ps = pstats.Stats(prof).strip_dirs().sort_stats("cumtime")
ps.print_stats(40)

print(f"[PROFILE] Wrote profile to: {stats_path}")


elapsed = time.time() - start_time
elapsed_min = elapsed / 60
print(f"Done. Wrote {total_written} series in {elapsed_min:0.1f} minutes.")
