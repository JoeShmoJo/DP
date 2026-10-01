import os
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd
from pydsstools.heclib.dss import HecDss
from pydsstools.core import TimeSeriesContainer

import CONFIG as cfg
import importlib
importlib.reload(cfg)

# =====================================================================
# CONFIG / PATHS
# =====================================================================

SIM_NAME = cfg.SIM_NAME
SOURCE_ENSEMBLE_YEAR = int(cfg.ENSEMBLE_YEAR_TO_COPY)
TARGET_ENSEMBLE_YEAR = 2029

sim_dir = SIM_NAME.replace(" ", "_")

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent

DSS_PATH = (
    SCRIPT_DIR.parent.parent
    / "rss"
    / sim_dir
    / "simulation.dss"
).resolve()

DSS_FILE = str(DSS_PATH)

print("DSS_FILE:", DSS_FILE)
print("SOURCE_ENSEMBLE_YEAR:", SOURCE_ENSEMBLE_YEAR)
print("TARGET_ENSEMBLE_YEAR:", TARGET_ENSEMBLE_YEAR)

# =====================================================================
# RFC GROUP / SITE DEFINITIONS
# Keep these aligned with the RFC loading script
# =====================================================================

SITES_3XE_SQIN = [
    "ALBO", "EUGO", "GOSO", "HARO", "JASO",
    "JFFO", "LOPO", "MCMO", "MCZO", "MEHO", "MNRO",
    "JFFO", "LOPO", "MCMO", "MCZO", "MEHO", "MNRO",
    "SLMO", "VIDO", "WLSO", "WTLO",
    "FOSO", "CORO"
]
SITES_3_QINE = ["AURO", "CANO", "LSMO", "PHIO", "TRSO", "TRBO", "SUVO", "SPRO", "MCMO"]
SITES_3I_QINE = ["DETO", "GPRO", "BLUO", "CGRO", "HCRO", "FALO", "COTO", "DORO", "FRNO"]
SLMO_UNREG_CHECK = ["SLMO"]

GROUP_TO_BPART = {
    "unadjusted_3XE_SQIN": "FLOW-LOC",
    "unadjusted_3_QINE": "FLOW-UNREG",
    "unadjusted_3I_QINE": "FLOW-UNREG",
    "SalemUnregCheck": "FLOW-UNREG",
}

GROUP_TO_SITES = {
    "unadjusted_3XE_SQIN": SITES_3XE_SQIN,
    "unadjusted_3_QINE": SITES_3_QINE,
    "unadjusted_3I_QINE": SITES_3I_QINE,
    "SalemUnregCheck": SLMO_UNREG_CHECK,
}

# =====================================================================
# HELPERS
# =====================================================================

def _member_to_fpart(member_year: int) -> str:
    y = int(member_year)
    return f"C:{y:06d}|"


def _build_path(site: str, bpart: str, epart: str, fpart: str) -> str:
    return f"//{site}3/{bpart}//{epart}/{fpart}/"


def _clean_series_from_tsc(tsc) -> pd.Series:
    vals = np.asarray(tsc.values, dtype="float64")
    idx = pd.to_datetime(np.array(tsc.pytimes))

    if len(vals) != len(idx):
        raise ValueError(
            f"Value/time length mismatch: {len(vals)} values vs {len(idx)} times"
        )

    s = pd.Series(vals, index=idx)
    s = s[~s.index.duplicated(keep="last")]
    s = s.sort_index()

    return s


def _write_series_daily_v6(fid, pathname: str, series: pd.Series, decimals: int = 1) -> None:
    if series is None or series.empty:
        return

    if not isinstance(series.index, pd.DatetimeIndex):
        raise TypeError("Series index must be DatetimeIndex")

    if not series.index.is_monotonic_increasing:
        series = series.sort_index()

    start_dt = pd.Timestamp(series.index[0]).strftime("%d%b%Y %H:%M")

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


# =====================================================================
# MAIN COPY LOGIC
# =====================================================================

def copy_ensemble_year_to_1980(
    dss_file: str,
    source_year: int,
    target_year: int = 1980,
    decimals: int = 1,
    debug: bool = True,
) -> Tuple[int, List[Tuple[str, str, str]]]:
    if source_year == target_year:
        raise ValueError("source_year and target_year cannot be the same")

    out_dir = os.path.dirname(dss_file)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    copied = 0
    misses: List[Tuple[str, str, str]] = []

    source_fpart = _member_to_fpart(source_year)
    target_fpart = _member_to_fpart(target_year)

    fid = HecDss.Open(dss_file, version=6)
    try:
        for group, sites in GROUP_TO_SITES.items():
            bpart = GROUP_TO_BPART[group]

            seen = set()
            unique_sites = []
            for site in sites:
                if site not in seen:
                    seen.add(site)
                    unique_sites.append(site)

            for site in unique_sites:
                src_path = _build_path(site=site, bpart=bpart, epart="1Day", fpart=source_fpart)
                dst_path = _build_path(site=site, bpart=bpart, epart="1Day", fpart=target_fpart)

                try:
                    tsc = fid.read_ts(src_path, trim_missing=True)
                    if tsc is None or getattr(tsc, "values", None) is None:
                        raise ValueError("No time series returned")

                    s = _clean_series_from_tsc(tsc)
                    s = s.replace([np.inf, -np.inf], np.nan).dropna()

                    if s.empty:
                        raise ValueError("Source series is empty after cleaning")

                    _write_series_daily_v6(fid, dst_path, s, decimals=decimals)
                    copied += 1

                    if debug:
                        print(f"[COPY] {src_path}  ->  {dst_path}")

                except Exception as e:
                    misses.append((group, site, str(e)))
                    if debug:
                        print(f"[MISS] {group} {site}: {e}")

    finally:
        fid.close()

    return copied, misses


if __name__ == "__main__":
    copied, misses = copy_ensemble_year_to_1980(
        dss_file=DSS_FILE,
        source_year=SOURCE_ENSEMBLE_YEAR,
        target_year=TARGET_ENSEMBLE_YEAR,
        decimals=1,
        debug=True,
    )

    print("\n--- Summary ---")
    print(f"DSS file: {DSS_FILE}")
    print(f"Source ensemble year: {SOURCE_ENSEMBLE_YEAR}")
    print(f"Target ensemble year: {TARGET_ENSEMBLE_YEAR}")
    print(f"Copied records: {copied}")
    print(f"Misses: {len(misses)}")

    if misses:
        print("\nMisses (group, site, reason):")
        for g, s, reason in misses:
            print(f"  {g} {s}: {reason}")