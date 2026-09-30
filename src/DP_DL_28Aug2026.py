# -*- coding: utf-8 -*-
"""
Created on Wed Oct  2 13:00:45 2024
# Change Log
- 04Oct2024
Removed Timestep as a variable and now resample to hourly or daily based on defined ResSim path in the process USGS and process CWMS functions 
Added df = df.apply(pd.to_numeric,errors='coerce') to process CWMS function to catch odd format values downloading from CWMS 
- 04May2026
Removed SSL verify=False monkey-patch. Now uses pip-system-certs to pull certs from
the Windows certificate store. Run: pip install pip-system-certs
- 28Aug2026
USGS is decommissioning the legacy WaterServices API (waterservices.usgs.gov) in
Q1 2027 in favor of the modernized USGS Water Data API (api.waterdata.usgs.gov).
The dataretrieval.nwis module (nwis.get_record) is now deprecated and talks to the
legacy API that USGS is actively winding down, which is why downloads that worked
in May stopped working. Rewrote NWIS_dl to use dataretrieval.waterdata.get_continuous
/get_daily instead. This changes site IDs to the "USGS-#######" monitoring_location_id
format and returns a 'value' column instead of a numeric-named column, so
process_usgs_data was updated to read 'value' (with a fallback to the old numeric
column heuristic for anyone still on the legacy nwis module).
Requires dataretrieval>=1.3.0 (pip install -U dataretrieval).
Fixed: waterdata.get_continuous() has no skip_geometry argument (it never
returns geometry to begin with, unlike get_daily()) - removed it from the
'iv' branch of NWIS_dl, which was raising a TypeError.
Tried changing CWMS_Download's office_id from 'NWDP' to office.upper() to
match Modules/cwms_io.py in the Cowlitz_FF repo - didn't fix it. Reverted:
office_id='NWDP' back to match CAS_Unreg_FF/src/#DataDownload.py (the
Cowlitz initial data download script) exactly, and brought over that
script's SSL cert handling too. That script builds its own combined CA
bundle (certifi + the Windows ROOT store) and points REQUESTS_CA_BUNDLE
at it directly, instead of relying on pip-system-certs's global
monkey-patch, which doesn't survive every environment/upgrade (e.g. it can
get silently undone when certifi itself gets reinstalled/upgraded - which
`pip install -U dataretrieval` does). That silent TLS failure is the more
likely reason CWMS was still failing after the office_id change.
- 30Sep2026
Pointed at RequiredRecordsDictWIL.csv (Willamette only, made from
RequiredRecordsDictNWP.csv by PareDown_Willamette.py) and set the period to
WY2026 (01Oct2025 - 30Sep2026). CWMS_Download now pulls through the end of
EndDate instead of stopping at midnight. Hourly records are reindexed to the
full requested period so gaps at either end are counted, and the summary stats
gained 'Hours Expected', 'Hours Missing' and 'Pct Complete'. All hourly data
is also written to ../out/Hourly_<startDate>_<endDate>.csv (long format:
time_utc, Source, Download_Key, ResSimPath, value), which DP_QAQC.py reads.
Reads a USGS Water Data API key from ../data/usgs_api_key.txt (git-ignored)
and sets API_USGS_PAT, which dataretrieval sends with every request. Without
a key the API's anonymous rate limit is easy to hit on a full year of
instantaneous data for this many gages. Request a key at
https://api.waterdata.usgs.gov/signup/

@author: g2encjer
"""
#%%

import os
import tempfile

import pandas as pd
from dataretrieval import waterdata
import datetime
import cwms
from pydsstools.heclib.dss import HecDss
from pydsstools.core import TimeSeriesContainer
import numpy as np
import time
import pdb
import requests

import ssl
import certifi

# --- SSL Certificate Setup ---
# Build a combined CA bundle (public CAs from certifi + the Windows ROOT
# store) and point REQUESTS_CA_BUNDLE at it so requests/cwms/dataretrieval
# trust USACE's internally-issued certs. This must run before any network
# calls (CWMS_Download, NWIS_dl) below. On non-Windows platforms,
# ssl.enum_certificates doesn't exist and this falls back to certifi alone.
pem_path = os.path.join(tempfile.gettempdir(), "corp_plus_certifi.pem")


def build_windows_ca_bundle(target_pem: str) -> str:
    base_bundle = certifi.where()
    with open(base_bundle, "rb") as src, open(target_pem, "wb") as dst:
        dst.write(src.read())
        try:
            for cert_tuple in ssl.enum_certificates("ROOT"):
                der_bytes = cert_tuple[0]
                pem_str = ssl.DER_cert_to_PEM_cert(der_bytes)
                dst.write(pem_str.encode("ascii"))
        except AttributeError:
            print("[WARNING] ssl.enum_certificates not available; using certifi only.")
        except Exception as e:
            print(f"[WARNING] Error reading Windows ROOT store: {e}")
    return target_pem


if not os.path.exists(pem_path):
    try:
        bundle_path = build_windows_ca_bundle(pem_path)
        print(f"[INFO] Built combined CA bundle: {bundle_path}")
    except Exception as e:
        print(f"[WARNING] Failed to build combined CA bundle: {e}")
        bundle_path = certifi.where()
else:
    bundle_path = pem_path

os.environ["REQUESTS_CA_BUNDLE"] = bundle_path
print(f"[INFO] Using CA bundle: {bundle_path}")
# --- End SSL Setup ---

# --- USGS API Key ---
# dataretrieval sends API_USGS_PAT as the X-Api-Key header on Water Data API
# requests. The key lives in a text file that is git-ignored - never commit it.
UsgsApiKeyPath = r'../data/usgs_api_key.txt'
if os.path.exists(UsgsApiKeyPath):
    with open(UsgsApiKeyPath, encoding='utf-8-sig') as f:
        usgs_api_key = f.read().strip()
    if usgs_api_key:
        os.environ['API_USGS_PAT'] = usgs_api_key
        print(f"[INFO] USGS API key loaded from {UsgsApiKeyPath}")
    else:
        print(f"[WARNING] {UsgsApiKeyPath} is empty; USGS requests will be anonymous and rate limited.")
elif os.environ.get('API_USGS_PAT'):
    print("[INFO] Using USGS API key from the API_USGS_PAT environment variable.")
else:
    print(f"[WARNING] No USGS API key ({UsgsApiKeyPath} not found); USGS requests will be anonymous and rate limited.")
# --- End USGS API Key ---


RequiredRecordsDictPath = r'../data/RequiredRecordsDictWIL.csv'

# Start and end date, probably water year
startDate = '2025-10-01'
endDate = '2026-09-30'
# Output folder for the summary stats, hourly csv, and DSS file
OutDir = r'../out'
os.makedirs(OutDir, exist_ok=True)
# DSS file with final results
ObsDataWrite = os.path.join(OutDir, 'obsData')
HourlyCsv = os.path.join(OutDir, f'Hourly_{startDate}_{endDate}.csv')


#Functions
def NWIS_dl(sites_dict, service, startDate, endDate, parameterCD):
    """
    Downloads USGS data via the modernized USGS Water Data API
    (dataretrieval.waterdata), which replaces the legacy WaterServices API
    formerly accessed through dataretrieval.nwis.get_record.

    service: 'iv' for continuous/instantaneous values, 'dv' for daily values
    (reported as the daily mean, statistic_id '00003').
    """
    NWIS = {}
    # ISO 8601 interval covering the full start/end days, as required by the
    # 'time' parameter of the waterdata getters. Parse with pandas first so a
    # loosely-formatted date (e.g. '2024-1-02') still produces a valid,
    # zero-padded RFC3339 string instead of getting interpolated as-is.
    start_dt = pd.to_datetime(startDate)
    end_dt = pd.to_datetime(endDate) + pd.Timedelta(hours=23, minutes=59, seconds=59)
    time_range = f"{start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}/{end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    for site, name in sites_dict.items():
        # The new API keys sites as "USGS-#######" (agency-siteno) rather than
        # the bare site number used by the old nwis module.
        monitoring_location_id = site if str(site).upper().startswith('USGS-') else f"USGS-{site}"
        try:
            if service == 'iv':
                # get_continuous has no skip_geometry kwarg - it never returns
                # geometry to begin with.
                data, _ = waterdata.get_continuous(
                    monitoring_location_id=monitoring_location_id,
                    parameter_code=parameterCD,
                    time=time_range,
                )
            elif service == 'dv':
                data, _ = waterdata.get_daily(
                    monitoring_location_id=monitoring_location_id,
                    parameter_code=parameterCD,
                    statistic_id='00003',
                    time=time_range,
                    skip_geometry=True,
                )
            else:
                raise ValueError(f"Unsupported service '{service}'. Use 'iv' or 'dv'.")
            if data.empty:
                print(f"Downloaded data for {site} is empty.")
            else:
                data['time'] = pd.to_datetime(data['time'])
                data = data.set_index('time').sort_index()
                NWIS[name] = data
        except Exception as e:
            print(f"Failed to download data for {site}: {e}")
    return NWIS

def CWMS_Download(sites_dict, StartDate, EndDate, office='nws'):
    # Convert StartDate and EndDate to datetime objects. EndDate is pushed to
    # the end of that day so the last day isn't dropped.
    StartDate = pd.to_datetime(StartDate)
    EndDate = pd.to_datetime(EndDate) + pd.Timedelta(hours=23, minutes=59, seconds=59)

    # Initialize CWMS API session
    apiRoot = "https://wm." + office + ".ds.usace.army.mil:8243/nwdp-data/"
    api = cwms.api.init_session(api_root=apiRoot)

    # Initialize empty dictionary to store data for each tsid
    CWMS_data = {}
    # Loop through each tsid
    for site, name in sites_dict.items():
        try:
            # Try to download data and store the dataframe for the tsid
            data = cwms.get_timeseries(site, office_id='NWDP', begin=StartDate, end=EndDate).df
            # Check if the data is empty
            if data.empty:
                print(f"Downloaded data for {site} is empty.")
            else:
                CWMS_data[name] = data
        except Exception as e:
            # Print the failed tsid and the error message
            print(f"Failed to download data for {site}: {e}")
    return CWMS_data

def full_period_resample(df, t, startDate, endDate):
    """Resample to hourly/daily means and reindex to the whole requested
    period so missing time at the start or end shows up as gaps."""
    df = df.resample(t).mean()
    tz = df.index.tz
    start = pd.Timestamp(startDate)
    end = pd.Timestamp(endDate) + pd.Timedelta(days=1) - pd.Timedelta(1, unit=t)
    if tz is not None:
        start, end = start.tz_localize(tz), end.tz_localize(tz)
    return df.reindex(pd.date_range(start, end, freq=t, name=df.index.name))

def completeness(df, t):
    """Count expected/missing timesteps of a resampled (NaN-gapped) record."""
    missing = int(df.isna().to_numpy().sum())
    expected = int(df.shape[0])
    label = 'Hours' if t == 'h' else 'Days'
    return {f'{label} Expected': expected,
            f'{label} Missing': missing,
            'Pct Complete': round(100.0 * (expected - missing) / expected, 2) if expected else np.nan}

def process_usgs_data(DataDict, startDate, endDate):
    # Create an empty list to store the summary stats
    results = []
    for df_name, df in DataDict.items():
        if not df.empty and df.shape[1] > 0:
            # The modernized waterdata API returns the observation in a 'value'
            # column. Fall back to the old numeric-named-column heuristic for
            # anyone still downloading via the legacy dataretrieval.nwis module.
            if 'value' in df.columns:
                df = df['value'].copy()
            else:
                valid_columns = [col for col in df.columns if col.replace('_', '').isdigit()]
                if len(valid_columns) == 1:
                    df = df[valid_columns[0]].copy()
                elif len(valid_columns) > 1:
                    print(f"Warning: Multiple valid columns found in {df_name}. Using the first one: {valid_columns[0]}")
                    df = df[valid_columns[0]].copy()
                else:
                    raise ValueError("No valid columns found that contain only numbers or underscores.")
            df = pd.to_numeric(df, errors='coerce')
            df[df < -9000] = np.nan
            df[df==-902]=np.nan
            df[df==-901]=np.nan
            df = df.dropna()
            #Create SummaryStats
            first_timestamp = df.index.min().strftime('%Y-%m-%d %H:%M')
            last_timestamp = df.index.max().strftime('%Y-%m-%d %H:%M')
            # Calculate the maximum gap between consecutive timestamps
            time_diffs = df.index.to_series().diff().dropna()
            max_gap = time_diffs.max()
            max_gap_hours=max_gap.total_seconds()/3600.0
            # Resample to hourly (or daily) over the full period
            if '1HOUR' in df_name:
                t = 'h'
            elif '1DAY' in df_name:
                t = 'D'
            else:
                print('timestep of ResSim path not 1HOUR or 1DAY')
            df = full_period_resample(df, t, startDate, endDate)
            # Append the results for this dataframe to the list
            results.append({
                'DataFrame': df_name,
                'First Timestamp': first_timestamp,
                'Last Timestamp': last_timestamp,
                'Max Gap': max_gap,
                'Max Gap Hours': max_gap_hours,
                **completeness(df, t)
            })
            # Replace nan with dss nan
            df = df.fillna(-902)
            DataDict[df_name] = df
        else:
            print(f"DataFrame {df_name} is either empty or does not have any columns.")
    results_df = pd.DataFrame(results)
    return results_df

def process_cwms_data(DataDict, startDate, endDate):
    # Create an empty list to store the summary stats
    results = []
    for df_name, df in DataDict.items():
        # Set 'date-time' as index if it exists
        if 'date-time' in df.columns:
            df = df.set_index('date-time')
            DataDict[df_name] = df
        if not df.empty and df.shape[1] > 0:
            # Keep only the first column and clean missing value standins
            df = df.iloc[:, [0]].copy()
            df = df.apply(pd.to_numeric,errors='coerce')
            df[df < -9000] = np.nan
            df[df==-902]=np.nan
            df[df==-901]=np.nan
            df = df.dropna()
            #Create SummaryStats
            first_timestamp = df.index.min().strftime('%Y-%m-%d %H:%M')
            last_timestamp = df.index.max().strftime('%Y-%m-%d %H:%M')
            # Calculate the maximum gap between consecutive timestamps
            time_diffs = df.index.to_series().diff().dropna()
            max_gap = time_diffs.max()
            max_gap_hours = max_gap.total_seconds()/3600.0
            # Resample to hourly (or daily) over the full period
            if '1HOUR' in df_name:
                t = 'h'
            elif '1DAY' in df_name:
                t = 'D'
            else:
                print('timestep of ResSim path not 1HOUR or 1DAY')
            df = full_period_resample(df, t, startDate, endDate)
            # Append the results for this dataframe to the list
            results.append({
                'DataFrame': df_name,
                'First Timestamp': first_timestamp,
                'Last Timestamp': last_timestamp,
                'Max Gap': max_gap,
                'Max Gap Hours': max_gap_hours,
                **completeness(df, t)
            })
            # Replace nan with dss nan
            df = df.fillna(-902)
            DataDict[df_name] = df
        else:
            print(f"DataFrame {df_name} is either empty or does not have any columns.")
    # Convert the list of results into a DataFrame
    results_df = pd.DataFrame(results)
    return results_df

def write_hourly_csv(csv_file, DataDicts):
    """Write every processed record to one long-format csv (-902 -> blank).
    DataDicts: {source: (DataDict, {ResSimPath: Download_Key})}"""
    frames = []
    for source, (DataDict, keys) in DataDicts.items():
        for pathname, df in DataDict.items():
            s = df.iloc[:, 0] if isinstance(df, pd.DataFrame) else df
            s = s.replace(-902, np.nan)
            idx = s.index.tz_convert('UTC') if s.index.tz is not None else s.index
            frames.append(pd.DataFrame({
                'time_utc': idx.strftime('%Y-%m-%d %H:%M'),
                'Source': source,
                'Download_Key': keys.get(pathname, ''),
                'ResSimPath': pathname,
                'value': s.to_numpy(),
            }))
    if frames:
        pd.concat(frames, ignore_index=True).to_csv(csv_file, index=False)
        print(f"Wrote {csv_file}")

def write_to_dss(dss_file, DataDict):
    for pathname, df in DataDict.items():
        # Debugging statements
        print(f"Processing pathname: {pathname}")
        # Ensure df is a DataFrame
        if isinstance(df, pd.Series):
            df = df.to_frame()
        # Create the time series container
        tsc = TimeSeriesContainer()
        tsc.pathname = pathname
        tsc.startDateTime = str(df.index[0])
        tsc.numberValues = df.shape[0]
        # Check if df has the expected structure
        if df.shape[1] > 0:
            tsc.values = df.iloc[:, 0].copy().to_numpy()
        else:
            print(f"DataFrame {pathname} does not have any columns.")
            continue
        tsc.interval = 1  # Assuming this is the interval
        # Set units based on the path
        if "ELEV" in pathname:
            tsc.units = "FEET"
        elif "FLOW" in pathname:
            tsc.units = "CFS"
        else:
            tsc.units = 'Unknown'
            print('Not Flow or Elev!')
        # Set the type
        tsc.type = "INST-VAL"  # Assuming this is always the type
        # Write the data to the DSS file to the out folder

        with HecDss.Open(dss_file, version=6) as fid:
            fid.put_ts(tsc)
        
#%%
# Read in the CSV that maps required Damages Prevented inputs with download keys (USGS or CWMS).
# Create this csv with the CreateRequiredRecordsDict.py script.
RequiredRecordsDict = pd.read_csv(RequiredRecordsDictPath)

# Create the required USGS and CWMS dictionaries. USGS needs one for Elev and one for Flow
# because the parameterCD code for each is different.
USGS_df = RequiredRecordsDict[RequiredRecordsDict['Source']=='USGS']

USGS_Elev_df = USGS_df[USGS_df['ResSimPath'].str.contains('ELEV', na=False)]
USGS_Elev_dict = dict(zip(USGS_Elev_df['Download_Key'],USGS_Elev_df['ResSimPath']))

USGS_Flow_df = USGS_df[USGS_df['ResSimPath'].str.contains('FLOW', na=False)]
USGS_Flow_dict = dict(zip(USGS_Flow_df['Download_Key'],USGS_Flow_df['ResSimPath']))

CWMS_df = RequiredRecordsDict[RequiredRecordsDict['Source']=='CWMS']
CWMS_dict = dict(zip(CWMS_df['Download_Key'],CWMS_df['ResSimPath']))

#%%
# Download the data. All data is downloaded as instant. The processing later makes it hourly
# or daily. You could also set the service to 'dv' for daily if you don't need hourly.

USGS_Elev_Data_Dict = NWIS_dl(sites_dict = USGS_Elev_dict, service = 'iv', startDate = startDate, endDate = endDate, parameterCD = '62614')

USGS_Flow_Data_Dict = NWIS_dl(sites_dict = USGS_Flow_dict, service = 'iv', startDate = startDate, endDate = endDate, parameterCD = '00060')

CWMS_Data_Dict = CWMS_Download(sites_dict=CWMS_dict, StartDate = startDate, EndDate = endDate)

#%%
# Process Data and create summary stats - this process gets rid of all the metadata that comes
# in with the data, and also creates summary stats that are written to a csv.
CWMS_Summary_Stats = process_cwms_data(CWMS_Data_Dict, startDate, endDate)
USGS_Flow_Summary_Stats = process_usgs_data(USGS_Flow_Data_Dict, startDate, endDate)
USGS_Elev_Summary_Stats = process_usgs_data(USGS_Elev_Data_Dict, startDate, endDate)

#%%
Combined_Summary_Stats = pd.concat([CWMS_Summary_Stats,USGS_Flow_Summary_Stats,USGS_Elev_Summary_Stats], ignore_index= True)
Combined_Summary_Stats['Max Gap Hours'] = Combined_Summary_Stats['Max Gap Hours'].astype(float).round(2)
Combined_Summary_Stats.sort_values(by='Max Gap Hours', ascending=False, inplace=True)
Combined_Summary_Stats.reset_index(drop=True, inplace=True)
Combined_Summary_Stats.to_csv(os.path.join(OutDir, 'Combined_Summary_Stats.csv'), index=None)

#%%
# Hourly data for QA/QC (DP_QAQC.py). Keys map ResSimPath back to the download key.
write_hourly_csv(HourlyCsv, {
    'USGS': ({**USGS_Flow_Data_Dict, **USGS_Elev_Data_Dict},
             {v: k for k, v in {**USGS_Flow_dict, **USGS_Elev_dict}.items()}),
    'CWMS': (CWMS_Data_Dict, {v: k for k, v in CWMS_dict.items()}),
})

#%%
# Write obsdata. This writes the final dss file your ResSim alternatives will reference.
# Written to the out folder (OutDir)
write_to_dss(dss_file = ObsDataWrite, DataDict=USGS_Flow_Data_Dict)
write_to_dss(dss_file = ObsDataWrite, DataDict=USGS_Elev_Data_Dict)
write_to_dss(dss_file = ObsDataWrite, DataDict=CWMS_Data_Dict)

# %%