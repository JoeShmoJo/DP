import os
import time
import numpy as np
import pandas as pd
import requests
from io import StringIO
from pathlib import Path
from datetime import date
from typing import Dict, Tuple, List

from pydsstools.heclib.dss import HecDss
from pydsstools.core import TimeSeriesContainer
import CONFIG as cfg
# reload CONFIG to pick up changes without restarting kernel (optional, for interactive dev)
import importlib
importlib.reload(cfg)
# =====================================================================
# CONFIG / PATHS
# =====================================================================

SIM_NAME = cfg.SIM_NAME          # <-- set your simulation name here
sim_dir = SIM_NAME.replace(" ", "_")

# ============================================================
# SCRIPT LOCATION
# ============================================================

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent

# ============================================================
# RAW RFC CSV ARCHIVE (one set per day)
# Saves raw CSV text only once per day; still downloads/processes every run.
# ============================================================
TODAY_STR = date.today().isoformat()  # e.g., 2026-02-24
RAW_CSV_DIR = SCRIPT_DIR / "raw_rfc_csv" / TODAY_STR
RAW_DONE_FLAG = RAW_CSV_DIR / "_raw_csv_saved.txt"

def _save_raw_csv(group: str, filename: str, text: str) -> None:
    out_dir = RAW_CSV_DIR / group
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    out_path.write_text(text, encoding="utf-8", errors="replace")

# ============================================================
# BUILD RELATIVE PATH FROM SCRIPT LOCATION
# Go up two directories from script dir, then:
#    rss/<simulation_name>/simulation.dss
# ============================================================

DSS_PATH = (
    SCRIPT_DIR.parent.parent
    / "rss"
    / sim_dir
    / "simulation.dss"
).resolve()

DSS_FILE_OUT = str(DSS_PATH)
print("DSS_FILE_OUT:", DSS_FILE_OUT)

# =====================================================================
# RFC URLS / SPECS
# =====================================================================

BASE_URL_UNADJUSTED = "https://www.nwrfc.noaa.gov/chpsesp/ensemble/unadjusted/"
BASE_URL_NATURAL    = "https://www.nwrfc.noaa.gov/chpsesp/ensemble/natural/"

SITES_3XE_SQIN = [
    "ALBO","EUGO","GOSO","HARO","JASO",
    "JFFO","LOPO","MCMO","MCZO","MEHO","MNRO",
    "JFFO","LOPO","MCMO","MCZO","MEHO","MNRO",
    "SLMO","VIDO","WLSO","WTLO",
    "FOSO","CORO"
]
SITES_3_QINE   = ["AURO","CANO","LSMO","PHIO","TRSO","TRBO","SUVO","SPRO","MCMO"]
SITES_3I_QINE  = ["DETO","GPRO","BLUO","CGRO","HCRO","FALO","COTO","DORO","FRNO"]
SLMO_UNREG_CHECK = ["SLMO"]

SPECS = [
    {"name": "unadjusted_3XE_SQIN", "base_url": BASE_URL_UNADJUSTED, "pattern": "{site}3XE_SQIN.ESPF10.csv", "sites": SITES_3XE_SQIN},
    {"name": "unadjusted_3_QINE",   "base_url": BASE_URL_UNADJUSTED, "pattern": "{site}3_QINE.ESPF10.csv",   "sites": SITES_3_QINE},
    {"name": "unadjusted_3I_QINE",  "base_url": BASE_URL_UNADJUSTED, "pattern": "{site}3I_QINE.ESPF10.csv",  "sites": SITES_3I_QINE},
    {"name": "SalemUnregCheck",     "base_url": BASE_URL_NATURAL,    "pattern": "{site}3N_SQIN.ESPF10.csv",  "sites": SLMO_UNREG_CHECK},
]

GROUP_TO_BPART = {
    "unadjusted_3XE_SQIN": "FLOW-LOC",
    "unadjusted_3_QINE":   "FLOW-UNREG",
    "unadjusted_3I_QINE":  "FLOW-UNREG",
    "SalemUnregCheck":     "FLOW-UNREG",
}

# =====================================================================
# RFC PARSER
# =====================================================================

def _parse_nwrfc_espf_csv_to_cfs(text: str) -> pd.DataFrame:
    df = pd.read_csv(StringIO(text), skiprows=5, header=[0, 1])

    t = pd.to_datetime(df.iloc[:, 0], errors="coerce", utc=True)
    m = t.notna()
    df = df.loc[m].copy()
    df.index = t[m]
    df.index.name = "FCST_VALID_TIME_GMT"

    df = df.iloc[:, 1:]  # ensemble columns

    years = []
    for c in df.columns:
        y = c[1]
        try:
            years.append(int(y))
        except Exception:
            years.append(str(y))
    df.columns = years

    df = df.apply(pd.to_numeric, errors="coerce") * 1000.0  # KCFS -> CFS
    df = df.round(2)
    return df


def load_espf10(specs=SPECS, debug=True, timeout=30) -> Tuple[Dict[str, Dict[str, pd.DataFrame]], List[Tuple[str, str, str, str]]]:
    out: Dict[str, Dict[str, pd.DataFrame]] = {}
    misses: List[Tuple[str, str, str, str]] = []

    save_raw_today = not RAW_DONE_FLAG.exists()
    if debug:
        if save_raw_today:
            print(f"[RAW] Will save raw CSVs to: {RAW_CSV_DIR}")
        else:
            print(f"[RAW] Raw CSVs already saved today ({TODAY_STR}); not saving again.")

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    for spec in specs:
        group = spec["name"]
        base_url = spec["base_url"]
        pattern = spec["pattern"]
        sites = spec["sites"]

        out[group] = {}

        for site in sites:
            url = base_url + pattern.format(site=site)

            try:
                r = session.get(url, timeout=timeout)
            except requests.RequestException as e:
                misses.append((group, site, url, f"REQUEST_ERROR: {e}"))
                if debug:
                    print(f"[ERR] {group} {site}: {e}")
                continue

            if r.status_code != 200:
                misses.append((group, site, url, f"HTTP_{r.status_code}"))
                if debug:
                    print(f"[MISS] {group} {site}: {r.status_code} -> {url}")
                continue

            if save_raw_today:
                raw_name = pattern.format(site=site)
                _save_raw_csv(group=group, filename=raw_name, text=r.text)

            try:
                df = _parse_nwrfc_espf_csv_to_cfs(r.text)
            except Exception as e:
                misses.append((group, site, url, f"PARSE_ERROR: {e}"))
                if debug:
                    print(f"[PARSE] {group} {site}: {e} -> {url}")
                continue

            out[group][site] = df
            if debug:
                print(f"[OK] {group} {site}: {df.shape[0]} x {df.shape[1]}")

    if save_raw_today:
        RAW_CSV_DIR.mkdir(parents=True, exist_ok=True)
        RAW_DONE_FLAG.write_text(f"Raw CSV saved on {TODAY_STR}\n", encoding="utf-8")
        if debug:
            print(f"[RAW] Wrote flag: {RAW_DONE_FLAG}")

    return out, misses

# =====================================================================
# TIME / AGG HELPERS
# =====================================================================

def _normalize_index_naive(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    idx = pd.to_datetime(df.index, errors="coerce")

    if isinstance(idx, pd.DatetimeIndex) and idx.tz is not None:
        idx = idx.tz_localize(None)

    df.index = idx
    df = df[~df.index.isna()].sort_index()
    return df


def _member_to_fpart(member_year) -> str:
    y = int(member_year)
    return f"C:{y:06d}|"


def _build_path(site: str, bpart: str, epart: str, fpart: str) -> str:
    return f"//{site}3/{bpart}//{epart}/{fpart}/"

# =====================================================================
# DSS WRITE
# =====================================================================

def _write_series_daily_v6(fid, pathname: str, series: pd.Series, decimals: int = 1) -> None:
    if series is None or series.empty:
        return

    if not isinstance(series.index, pd.DatetimeIndex):
        raise TypeError("Series index must be DatetimeIndex")

    if not series.index.is_monotonic_increasing:
        series = series.sort_index()

    start_dt = series.index[0].strftime("%d%b%Y %H%M")

    vals = series.to_numpy(dtype="float64")
    vals = np.round(vals, decimals)

    tsc = TimeSeriesContainer()
    tsc.pathname = pathname
    tsc.startDateTime = start_dt
    tsc.numberValues = len(vals)
    tsc.units = "CFS"
    tsc.type = "PER-AVER"
    tsc.interval = 1440
    tsc.values = vals

    fid.put_ts(tsc)


def write_rfc_to_dss(
    rfc_data: Dict[str, Dict[str, pd.DataFrame]],
    dss_file_out: str,
    decimals: int = 1,
    debug: bool = True,
) -> Tuple[int, List[Tuple[str, str, str]]]:
    out_dir = os.path.dirname(dss_file_out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    written = 0
    write_misses: List[Tuple[str, str, str]] = []

    fid = HecDss.Open(dss_file_out, version=6)
    try:
        for group, site_dict in rfc_data.items():
            bpart = GROUP_TO_BPART.get(group)
            if bpart is None:
                write_misses.append((group, "", "Unknown group->FLOW mapping"))
                continue

            for site, df in site_dict.items():
                try:
                    df = _normalize_index_naive(df)
                    df = df.apply(pd.to_numeric, errors="coerce")

                    df_shift = df.copy()
                    df_shift.index = df_shift.index - pd.Timedelta(hours=6)
                    df1d = df_shift.resample("1D").mean()
                    df1d = df1d.dropna(how="all")
                    
                                        # Add daily row-wise percentile members across the original ensemble years
                    # 2026 = 25th percentile, 2027 = 50th percentile, 2028 = 75th percentile
                    base_cols = list(df1d.columns)
                    if base_cols:
                        pct = df1d[base_cols].apply(pd.to_numeric, errors="coerce")
                        df1d[2026] = pct.quantile(0.25, axis=1, interpolation="linear")
                        df1d[2027] = pct.quantile(0.50, axis=1, interpolation="linear")
                        df1d[2028] = pct.quantile(0.75, axis=1, interpolation="linear")

                    if df1d.empty:
                        continue

                    for member in df1d.columns:
                        s = df1d[member].astype("float64")
                        s = s.replace([np.inf, -np.inf], np.nan).dropna()
                        if s.empty:
                            continue
                        s = s.mask(np.isclose(s, -902.0, atol=1.0), -903.0)
                        s = s.mask(np.isclose(s, -901.0, atol=1.0), -900.0)
                        s = s.mask(np.isclose(s, -999.0, atol=1.0), -1000.0)

                        fpart = _member_to_fpart(member)
                        pathname = _build_path(site=site, bpart=bpart, epart="1Day", fpart=fpart)

                        _write_series_daily_v6(fid, pathname, s, decimals=decimals)
                        written += 1

                    if debug:
                        print(f"[WRITE] {group} {site}: wrote {df1d.shape[1]} members ")

                except Exception as e:
                    write_misses.append((group, site, f"Exception: {e}"))
                    if debug:
                        print(f"[FAIL] {group} {site}: {e}")

    finally:
        fid.close()

    return written, write_misses


if __name__ == "__main__":
    t0 = time.time()

    rfc_data, dl_misses = load_espf10(SPECS, debug=True)

    written, wr_misses = write_rfc_to_dss(
        rfc_data=rfc_data,
        dss_file_out=DSS_FILE_OUT,
        decimals=1,
        debug=True,
    )

    print("\n--- Summary ---")
    print(f"DSS out: {DSS_FILE_OUT}")
    print(f"RFC download misses: {len(dl_misses)}")
    print(f"DSS write misses: {len(wr_misses)}")
    print(f"Series written: {written}")
    print(f"Runtime: {time.time() - t0:.2f} s")

    if dl_misses:
        print("\nDownload misses (group, site, reason):")
        for g, s, url, reason in dl_misses[:25]:
            print(f"  {g} {s}: {reason}")

    if wr_misses:
        print("\nWrite misses (group, site, reason):")
        for g, s, reason in wr_misses[:25]:
            print(f"  {g} {s}: {reason}")