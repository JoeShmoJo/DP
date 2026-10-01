

import os
import urllib3
import requests
import numpy as np
import pandas as pd
from datetime import timezone

import cwms
from pydsstools.heclib.dss import HecDss
from pydsstools.core import TimeSeriesContainer

import CONFIG as cfg
from pathlib import Path
from typing import Dict, Tuple, List
# reload CONFIG to pick up changes without restarting kernel (optional, for interactive dev)
import importlib
importlib.reload(cfg)

# ============================================================
# DEFINE SIMULATION NAME (explicit override)
# ============================================================

SIM_NAME = cfg.SIM_NAME          # <-- set your simulation name here



sim_dir = SIM_NAME.replace(" ", "_")

# ============================================================
# SCRIPT LOCATION
# ============================================================

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent

# ============================================================
# BUILD RELATIVE PATH FROM SCRIPT LOCATION
# Go up one directory from script, then:
#    rss/<simulation_name>/simulation.dss
# ============================================================

DSS_PATH = (
    SCRIPT_DIR.parent.parent
    / "rss"
    / sim_dir
    / "simulation.dss"
).resolve()   # <-- forces full absolute path

DSS_FILE_OUT = str(DSS_PATH)

print("DSS_FILE_OUT:", DSS_FILE_OUT)


def _write_series_v6(fid, pathname: str, series: pd.Series, units: str, interval_min: int, dss_type: str, decimals: int = 2):
    if series is None or series.empty:
        return False

    series = series.sort_index()
    start_dt = series.index[0].strftime("%d%b%Y %H%M").upper()

    tsc = TimeSeriesContainer()
    tsc.pathname = pathname
    tsc.startDateTime = start_dt
    tsc.numberValues = len(series)
    tsc.units = units
    tsc.type = dss_type
    tsc.interval = interval_min
    tsc.values = np.round(series.to_numpy(dtype="float64"), decimals)


    fid.put_ts(tsc)
    return True

# =====================================================================
# WRITE DUMMY RECORDS TO forecast.dss
# =====================================================================

def write_dummy_records():
    # Use your already constructed DSS_FILE_OUT
    dss_path = DSS_FILE_OUT

    # Anchor at UTC midnight, strip timezone for DSS
    today = pd.Timestamp.utcnow().normalize()
    start = (today - pd.Timedelta(days=365)).tz_localize(None)
    end   = (today + pd.Timedelta(days=365)).tz_localize(None)

    # -----------------------------------------------------------------
    # 1) Daily WY_TYPE record (all values = 4)
    # Path: /ALL_ABUNDANT//STOR//1DAY/WY_TYPE/
    # -----------------------------------------------------------------
    
    
    wy_path = "/ALL_ABUNDANT//STOR//1DAY/WY_TYPE/"
    daily_index = pd.date_range(start=start, end=end, freq="D")
    wy_series = pd.Series(4.0, index=daily_index)

    # -----------------------------------------------------------------
    # 2) Hourly ZERO flow record (all values = 0)
    # Path: /ZERO/ZERO/FLOW//1HOUR/DUMMY/
    # -----------------------------------------------------------------
    zero_path = "/ZERO/ZERO/FLOW//1DAY/DUMMY/"
    daily_index = pd.date_range(start=start, end=end, freq="D")
    zero_series = pd.Series(0.0, index=daily_index)

    # -----------------------------------------------------------------
    # Write to DSS
    # -----------------------------------------------------------------
    with HecDss.Open(dss_path) as fid:
        _write_series_v6(
            fid,
            pathname=wy_path,
            series=wy_series,
            units="UNSPEC",
            interval_min=1440,   # 1DAY
            dss_type="INST-VAL",
            decimals=0,
        )

        _write_series_v6(
            fid,
            pathname=zero_path,
            series=zero_series,
            units="CFS",
            interval_min=1440  ,     # 1HOUR
            dss_type="INST-VAL",
            decimals=0,
        )

    print("Dummy records written to:")
    print(dss_path)
    print(f"{wy_path}  ({start.date()} -> {end.date()})")
    print(f"{zero_path} ({start.date()} -> {end.date()})")

if __name__ == "__main__":
    write_dummy_records()