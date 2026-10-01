#Faster_DSS_Read_Plotly.py

import os
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from pydsstools.heclib.dss import HecDss

import CONFIG as cfg
import importlib
importlib.reload(cfg)

import plotly.io as pio
pio.renderers.default = "browser"
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# USER CONTROL
# -----------------------------------------------------------------------------
# Include synthetic daily-percentile members 2026–2028.
YearRange = range(1981, 2029)

TRIAL = cfg.TRIAL
H_LINE_DICT = cfg.H_LINE_DICT
RULE_CURVE_CSV = "RULE_CURVES.csv"
RULE_CURVE_SHIFT_HOURS = -8  # shift 0800 csv timestamps back to 0000

# D-part block start dates that cover the simulation period.
# Each ensemble member's data is split across these calendar-year blocks.
# Add more entries here if the simulation spans additional blocks.
DPART_STARTS = ["01JAN2026", "01JAN2027"]

# Shaded band quantiles (row-wise across base ensembles only)
BAND_Q = {
    "low_outer": 0.05,
    "low_inner": 0.25,
    "median": 0.50,
    "high_inner": 0.75,
    "high_outer": 0.95,
}

SYNTHETIC_ENSEMBLE_LABELS = {
    2026: "D%25",
    2027: "D%50",
    2028: "D%75",
}

# -----------------------------------------------------------------------------
# DSS READ HELPERS
# -----------------------------------------------------------------------------
def readallpaths(dss_file, path_dict):
    """Read multiple DSS paths into a single dataframe (columns=aliases)."""
    fid = HecDss.Open(os.fspath(dss_file))
    dflist = []

    for alias, path in path_dict.items():
        try:
            ts = fid.read_ts(path, trim_missing=True)
            df = pd.DataFrame(ts.values, columns=[alias], index=np.array(ts.pytimes))
            dflist.append(df.copy())
        except Exception as e:
            msg = f"[DSS] Failed '{alias}' -> {path} in {os.path.basename(os.fspath(dss_file))}: {e}"
            print(msg)

    fid.close()

    if not dflist:
        return pd.DataFrame()

    data = pd.concat(dflist, axis=1)
    data.index = pd.to_datetime(data.index)
    data = data[~data.index.duplicated(keep="last")]
    return data.sort_index()


def with_fpart_suffix(d, fpart):
    """Make alias keys unique per ensemble member so dict.update doesn't overwrite."""
    return {f"{k}__{fpart}": v for k, v in d.items()}


def fpart_to_year(fp: str) -> int:
    # fp like "C:001987|ConSeson0" OR "C:001987|"
    cpart = fp.split("|")[0]
    return int(cpart.replace("C:", "")[-4:])


def _clean_daily_series(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").dropna().copy()
    if s.empty:
        return s

    s.index = pd.to_datetime(s.index)
    s = s[~s.index.duplicated(keep="last")]
    return s.sort_index()


# -----------------------------------------------------------------------------
# RULE CURVE CSV HELPERS
# -----------------------------------------------------------------------------
def _parse_rule_curve_datetime(val):
    """
    Parse csv timestamps like:
      01Dec2025 0800

    Excel may display the same value differently, but the CSV text should be
    read in this form.
    """
    s = str(val).strip()

    for fmt in ("%d%b%Y %H%M", "%m/%d/%Y %I:%M:%S %p"):
        try:
            return pd.to_datetime(s, format=fmt)
        except Exception:
            pass

    return pd.to_datetime(s, errors="coerce")


def load_rule_curve_csv(csv_path: Path) -> pd.DataFrame:
    rc = pd.read_csv(csv_path)

    if "DATE" not in rc.columns:
        raise ValueError(f"DATE column not found in rule curve csv: {csv_path}")

    rc["DATE"] = rc["DATE"].apply(_parse_rule_curve_datetime)
    rc = rc.dropna(subset=["DATE"]).copy()

    rc["DATE"] = pd.to_datetime(rc["DATE"]) + pd.Timedelta(hours=RULE_CURVE_SHIFT_HOURS)

    rc = rc.set_index("DATE").sort_index()
    rc = rc[~rc.index.duplicated(keep="last")]

    for c in rc.columns:
        rc[c] = pd.to_numeric(rc[c], errors="coerce")

    return rc


def build_rule_curve_series_for_index(target_index, template_series: pd.Series) -> pd.Series:
    """
    Repeat a one-year rule curve across all years in target_index.

    Matching is by month/day. If Feb 29 is needed in a leap year and is not
    present in the template, fill it by interpolation between Feb 28 and Mar 1.
    """
    target_index = pd.to_datetime(target_index)
    out = pd.Series(index=target_index, dtype=float)

    s = pd.to_numeric(template_series, errors="coerce").dropna().copy()
    if s.empty:
        return out

    s.index = pd.to_datetime(s.index)
    s = s[~s.index.duplicated(keep="last")]
    s = s.sort_index()

    md_lookup = {(ts.month, ts.day): float(val) for ts, val in s.items()}

    if (2, 29) not in md_lookup and (2, 28) in md_lookup and (3, 1) in md_lookup:
        md_lookup[(2, 29)] = 0.5 * (md_lookup[(2, 28)] + md_lookup[(3, 1)])

    values = []
    for ts in target_index:
        key = (ts.month, ts.day)
        values.append(md_lookup.get(key, np.nan))

    out[:] = values
    out = out.interpolate(method="time", limit_direction="both")
    return out


# -----------------------------------------------------------------------------
# MAPS / PATH BUILDERS
# -----------------------------------------------------------------------------
RESERVOIR_NAME_MAP = {
    "LOP": "LOOKOUT POINT",
    "DET": "DETROIT",
    "GPR": "GREEN PETER",
    "CGR": "COUGAR",
    "BLU": "BLUE RIVER",
    "FAL": "FALL CREEK",
    "HCR": "HILLS CREEK",
    "DOR": "DORENA",
    "COT": "COTTAGE GROVE",
    "FRN": "FERN RIDGE",
    "FOS": "FOSTER",
}

CONTROL_POINT_MAP = {
    "ALBO": "Willamette_at Albany",
    "NBGO": "Willamette_at Newberg",
    "SLMO": "Willamette_at Salem",
    "WTLO": "So Santiam_at Waterloo",
    "MEHO": "No Santiam_at Mehama",
    "JFFO": "Santiam_at Jefferson",
    "MNRO": "Long Tom_at Monroe",
    "HARO": "Willamette_at Harrisburg",
    "VIDO": "McKenzie_at Vida",
    "EUGO": "Willamette_at Eugene",
    "GOSO": "CF WIllamette_nr Goshen",
    "JASO": "MF Willamette_at Jasper",
}


# -----------------------------------------------------------------------------
# D-PART AWARE PATH BUILDERS
# Each function returns a flat dict keyed as:
#   {alias}__{fpart}__{dpart}
# so that multiple D-part blocks for the same (alias, fpart) pair can be read
# independently and then spliced together.
# -----------------------------------------------------------------------------

def create_elev_paths_dpart(fpart: str, dpart: str) -> Dict[str, str]:
    return {
        f"{s}_elev__{fpart}__{dpart}": f"//{l}-POOL/ELEV/{dpart}/1DAY/{fpart}/"
        for s, l in RESERVOIR_NAME_MAP.items()
    }


def create_outflow_paths_dpart(fpart: str, dpart: str) -> Dict[str, str]:
    return {
        f"{s}_outflow__{fpart}__{dpart}": f"//{l}-POOL/FLOW-OUT/{dpart}/1DAY/{fpart}/"
        for s, l in RESERVOIR_NAME_MAP.items()
    }


def create_flow_paths_dpart(fpart: str, dpart: str) -> Dict[str, str]:
    return {
        f"{s}_flow__{fpart}__{dpart}": f"//{l}/FLOW/{dpart}/1DAY/{fpart}/"
        for s, l in CONTROL_POINT_MAP.items()
    }


def create_salem_unreg_path_dpart(unreg_fpart: str, dpart: str) -> Dict[str, str]:
    yr = fpart_to_year(unreg_fpart)
    return {
        f"salem_unreg__{yr}__{dpart}": f"//SLMO3/FLOW-UNREG/{dpart}/1DAY/{unreg_fpart}/"
    }


# -----------------------------------------------------------------------------
# D-PART SPLICE HELPER
# After reading all (fpart, dpart) combos, collapse the two D-part columns
# back into a single column per (base_alias, fpart), which is what the rest
# of the script expects: e.g. "DET_elev__C:001987|CON_SEASON0"
# -----------------------------------------------------------------------------

def splice_dpart_columns(
    df: pd.DataFrame,
    base_alias: str,
    fparts: List[str],
    dparts: List[str],
) -> pd.DataFrame:
    """
    For each fpart, find all columns named  {base_alias}__{fpart}__{dpart},
    concatenate them (union of time indices), deduplicate, sort, and return
    a DataFrame whose columns are named  {base_alias}__{fpart}.

    Any (fpart, dpart) combination that was not found in `df` is silently
    skipped; if NO dpart columns exist for a given fpart the fpart is omitted
    from the output.
    """
    result_frames = []

    for fpart in fparts:
        dpart_cols = [
            f"{base_alias}__{fpart}__{d}"
            for d in dparts
            if f"{base_alias}__{fpart}__{d}" in df.columns
        ]
        if not dpart_cols:
            continue

        # Stack all D-part slices vertically under the target alias name
        target_col = f"{base_alias}__{fpart}"
        pieces = [df[c].rename(target_col) for c in dpart_cols]
        combined = pd.concat(pieces)
        combined = combined[~combined.index.duplicated(keep="last")].sort_index()
        result_frames.append(combined)

    if not result_frames:
        return pd.DataFrame()

    return pd.concat(result_frames, axis=1)


def splice_salem_unreg(
    df: pd.DataFrame,
    years: List[int],
    dparts: List[str],
) -> pd.DataFrame:
    """
    Splice D-part columns for Salem UNREG.
    Raw column names: salem_unreg__{year}__{dpart}
    Target column names: salem_unreg__{year}
    """
    result_frames = []

    for yr in years:
        dpart_cols = [
            f"salem_unreg__{yr}__{d}"
            for d in dparts
            if f"salem_unreg__{yr}__{d}" in df.columns
        ]
        if not dpart_cols:
            continue

        target_col = f"salem_unreg__{yr}"
        pieces = [df[c].rename(target_col) for c in dpart_cols]
        combined = pd.concat(pieces)
        combined = combined[~combined.index.duplicated(keep="last")].sort_index()
        result_frames.append(combined)

    if not result_frames:
        return pd.DataFrame()

    return pd.concat(result_frames, axis=1)


def create_min_mainstem_flow_paths(fpart):
    return {
        "salem_minflow": f"//SALEM/FLOW-MIN-EXTERNALFLOWAUG//1Day/{fpart}/",
        "albany_minflow": f"//ALBANY/FLOW-MIN-EXTERNALFLOWAUG//1Day/{fpart}/",
    }


def build_seasonal_step_series(index, schedule_rows, value_col):
    """
    Build a forward-filled seasonal step series on the provided datetime index.

    schedule_rows: list of (month, day, low, high)
    value_col: "Low" or "High"
    """
    schedule_df = pd.DataFrame(schedule_rows, columns=["month", "day", "Low", "High"])

    s = pd.Series(index=pd.to_datetime(index), dtype=float)

    years = sorted(pd.to_datetime(index).year.unique())
    for yr in years:
        year_mask = s.index.year == yr
        year_index = s.index[year_mask]

        dt_idx = pd.to_datetime(
            {
                "year": [yr] * len(schedule_df),
                "month": schedule_df["month"],
                "day": schedule_df["day"],
            }
        )
        vals = schedule_df[value_col].to_numpy(dtype=float)
        year_series = pd.Series(vals, index=dt_idx)

        s.loc[year_mask] = year_series.reindex(year_index, method="ffill")

    return s


SALEM_MINFLOW_SCHEDULE = [
    (1, 1, 0, 0),
    (4, 1, 15000, 17800),
    (4, 16, 15000, 17800),
    (5, 1, 15000, 15000),
    (6, 1, 11000, 13000),
    (6, 16, 5500, 8700),
    (7, 1, 5000, 6000),
    (8, 1, 5000, 6000),
    (8, 16, 5000, 6500),
    (9, 1, 5000, 7000),
    (10, 1, 5000, 7000),
    (11, 1, 0, 0),
    (12, 31, 0, 0),
]

# -----------------------------------------------------------------------------
# OBSERVED PATHS
# Observed records are typically stored as a single multi-year DSS block so
# they do NOT need D-part splitting.  They are read with a wildcard D-part
# (empty string in the path) just as before.
# -----------------------------------------------------------------------------
OBS_ELEV_PATHS = {
    "BLU": "//BLU/ELEV-FOREBAY//1DAY/MIXED-REV/",
    "COT": "//COT/ELEV-FOREBAY//1DAY/MIXED-REV/",
    "DOR": "//DOR/ELEV-FOREBAY//1DAY/MIXED-REV/",
    "FAL": "//FAL/ELEV-FOREBAY//1DAY/MIXED-REV/",
    "FRN": "//FRN/ELEV-FOREBAY//1DAY/MIXED-REV/",
    "CGR": "//CGR/ELEV-FOREBAY//1DAY/CBT-REV/",
    "DET": "//DET/ELEV-FOREBAY//1DAY/CBT-REV/",
    "FOS": "//FOS/ELEV-FOREBAY//1DAY/CBT-REV/",
    "GPR": "//GPR/ELEV-FOREBAY//1DAY/CBT-REV/",
    "HCR": "//HCR/ELEV-FOREBAY//1DAY/CBT-REV/",
    "LOP": "//LOP/ELEV-FOREBAY//1DAY/CBT-REV/",
}

OBS_OUTFLOW_PATHS = {
    "BLU": "//BLU/FLOW-OUT//1DAY/MIXED-COMPUTED-REV/",
    "COT": "//COT/FLOW-OUT//1DAY/MIXED-COMPUTED-REV/",
    "DOR": "//DOR/FLOW-OUT//1DAY/MIXED-COMPUTED-REV/",
    "FAL": "//FAL/FLOW-OUT//1DAY/MIXED-COMPUTED-REV/",
    "FRN": "//FRN/FLOW-OUT//1DAY/MIXED-COMPUTED-REV/",
    "CGR": "//CGR/FLOW-OUT//1DAY/CBT-REV/",
    "DET": "//DET/FLOW-OUT//1DAY/CBT-REV/",
    "FOS": "//FOS/FLOW-OUT//1DAY/CBT-REV/",
    "GPR": "//GPR/FLOW-OUT//1DAY/CBT-REV/",
    "HCR": "//HCR/FLOW-OUT//1DAY/CBT-REV/",
    "LOP": "//LOP/FLOW-OUT//1DAY/CBT-REV/",
}


def create_observed_elev_paths() -> Dict[str, str]:
    return {f"{k}_obsElev": v for k, v in OBS_ELEV_PATHS.items()}


def create_observed_outflow_paths() -> Dict[str, str]:
    return {f"{k}_obsOutflow": v for k, v in OBS_OUTFLOW_PATHS.items()}


# -----------------------------------------------------------------------------
# CONFIG / PATHS
# -----------------------------------------------------------------------------
SIM_NAME = cfg.SIM_NAME
ALTERNATIVE_NAME_STEP1 = cfg.ALTERNATIVE_NAME_STEP1

# Format ALT name to match your DSS F-part scheme (pad to 10, then add trailing trial)
FORMATTED_ALT_NAME = ALTERNATIVE_NAME_STEP1.replace(" ", "-")
if len(FORMATTED_ALT_NAME) < 10:
    FORMATTED_ALT_NAME = FORMATTED_ALT_NAME.ljust(10, "-")
FORMATTED_ALT_NAME = FORMATTED_ALT_NAME + str(TRIAL)

sim_dir = SIM_NAME.replace(" ", "_")

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent

# Assumes script is in: <watershed>\scripts\...
WATERSHED_DIR = SCRIPT_DIR.parent.parent

DSS_PATH = (WATERSHED_DIR / "rss" / sim_dir / "simulation.dss").resolve()
DSS_FILE_IN = str(DSS_PATH)
print("DSS_FILE_IN:", DSS_FILE_IN)

plotly_output_dir = WATERSHED_DIR / "output_plots" / "plotly_html"
plotly_output_dir.mkdir(parents=True, exist_ok=True)

dated_folder = plotly_output_dir / pd.Timestamp.now().strftime("%Y-%m-%d_%H%M")
dated_folder.mkdir(parents=True, exist_ok=True)

RULE_CURVE_CSV_PATH = (SCRIPT_DIR / RULE_CURVE_CSV).resolve()
print("RULE_CURVE_CSV_PATH:", RULE_CURVE_CSV_PATH)

rule_curve_df = load_rule_curve_csv(RULE_CURVE_CSV_PATH)

# -----------------------------------------------------------------------------
# ENSEMBLE F-PARTS
# -----------------------------------------------------------------------------
ensemble_years = list(YearRange)
synthetic_years = [2026, 2027, 2028]
base_ensemble_years = [y for y in ensemble_years if y not in synthetic_years]

# Model outputs use ALT-suffixed F-part
ensemble_fparts_model = [f"C:00{year}|{FORMATTED_ALT_NAME}" for year in ensemble_years]
ensemble_fparts_model_base = [f"C:00{year}|{FORMATTED_ALT_NAME}" for year in base_ensemble_years]

# Salem UNREG uses ONLY year F-part (ends with a pipe)
ensemble_fparts_unreg = [f"C:00{year}|" for year in ensemble_years]
ensemble_fparts_unreg_base = [f"C:00{year}|" for year in base_ensemble_years]

# -----------------------------------------------------------------------------
# READ DSS — build path_dict with explicit D-parts
# -----------------------------------------------------------------------------
path_dict = {}

# --- Model outputs (elevation, outflow, flow) — one entry per (fpart, dpart) ---
for fpart in ensemble_fparts_model:
    for dpart in DPART_STARTS:
        path_dict.update(create_elev_paths_dpart(fpart, dpart))
        path_dict.update(create_outflow_paths_dpart(fpart, dpart))
        path_dict.update(create_flow_paths_dpart(fpart, dpart))

# --- Observed single traces (no D-part splitting needed) ---
path_dict.update(create_observed_elev_paths())
path_dict.update(create_observed_outflow_paths())

# --- Salem UNREG — year-only fparts, one entry per (year, dpart) ---
for unreg_fp in ensemble_fparts_unreg:
    for dpart in DPART_STARTS:
        path_dict.update(create_salem_unreg_path_dpart(unreg_fp, dpart))

# Read everything in one pass
data_raw = readallpaths(DSS_FILE_IN, path_dict)

# -----------------------------------------------------------------------------
# SPLICE D-PART COLUMNS → rebuild data_ens with original column naming
# -----------------------------------------------------------------------------
splice_frames = []

# Elevation, outflow, flow for each reservoir / control point
for res_abbr in RESERVOIR_NAME_MAP:
    for base_alias in (f"{res_abbr}_elev", f"{res_abbr}_outflow"):
        chunk = splice_dpart_columns(data_raw, base_alias, ensemble_fparts_model, DPART_STARTS)
        if not chunk.empty:
            splice_frames.append(chunk)

for cp_abbr in CONTROL_POINT_MAP:
    chunk = splice_dpart_columns(data_raw, f"{cp_abbr}_flow", ensemble_fparts_model, DPART_STARTS)
    if not chunk.empty:
        splice_frames.append(chunk)

# Salem UNREG splice (keyed by year, not fpart)
salem_unreg_spliced = splice_salem_unreg(data_raw, ensemble_years, DPART_STARTS)
if not salem_unreg_spliced.empty:
    splice_frames.append(salem_unreg_spliced)

# Pass observed columns through unchanged
obs_cols = [
    c for c in data_raw.columns
    if c.endswith(("_obsElev", "_obsOutflow"))
]
if obs_cols:
    splice_frames.append(data_raw[obs_cols])

# Assemble final DataFrame — same shape / naming as the original data_ens
data_ens = pd.concat(splice_frames, axis=1)
data_ens = data_ens[~data_ens.index.duplicated(keep="last")].sort_index()

# -----------------------------------------------------------------------------
# SALEM UNREG PERCENTILES (non-exceedance), keyed by YEAR
# Base years only; synthetic years are excluded from period-of-record stats.
# -----------------------------------------------------------------------------
salem_unreg_cols = [
    f"salem_unreg__{y}" for y in base_ensemble_years
    if f"salem_unreg__{y}" in data_ens.columns
]
if not salem_unreg_cols:
    raise RuntimeError(
        "No Salem UNREG series found. Expected paths like //SLMO3/FLOW-UNREG/{dpart}/1DAY/C:00YYYY|/"
    )

salem_unreg_df = data_ens[salem_unreg_cols].apply(pd.to_numeric, errors="coerce")
salem_unreg_sum = salem_unreg_df.sum(axis=0, skipna=True)

# non-exceedance: rank(pct=True)*100 (low volume => low percentile)
salem_unreg_percentiles = salem_unreg_sum.rank(pct=True) * 100.0

# YEAR -> percentile
salem_unreg_pct_by_year = pd.Series(
    {int(c.replace("salem_unreg__", "")): float(p) for c, p in salem_unreg_percentiles.items()}
)

# Sort base MODEL fparts by Salem UNREG percentile, then append synthetic percentile traces
ensemble_fparts_sorted = (
    sorted(
        ensemble_fparts_model_base,
        key=lambda fp: salem_unreg_pct_by_year.get(fpart_to_year(fp), np.nan),
    )
    + [f"C:00{year}|{FORMATTED_ALT_NAME}" for year in synthetic_years]
)

# -----------------------------------------------------------------------------
# PLOTLY HELPERS
# -----------------------------------------------------------------------------
def _fpart_to_clean_label(fpart: str, pct_by_year: pd.Series) -> str:
    """
    Convert:
        C:001987|ConSeson0
    To:
        1987 (42%)

    Synthetic daily-percentile members are labeled:
        2026 -> D%25
        2027 -> D%50
        2028 -> D%75
    """
    try:
        year_int = int(fpart.split("|")[0].replace("C:", "")[-4:])

        if year_int in SYNTHETIC_ENSEMBLE_LABELS:
            return SYNTHETIC_ENSEMBLE_LABELS[year_int]

        pct = float(pct_by_year.loc[year_int])
        pct_int = int(round(pct))
        return f"{year_int} ({pct_int:02d}%)"
    except Exception:
        return fpart


def _get_ensemble_cols(df: pd.DataFrame, prefix: str, fparts: list) -> list:
    cols = []
    for fp in fparts:
        c = f"{prefix}{fp}"
        if c in df.columns:
            cols.append(c)
    return cols


def _row_quantiles(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    x = df[cols].apply(pd.to_numeric, errors="coerce")
    q = pd.DataFrame(index=df.index)
    q["q5"] = x.quantile(BAND_Q["low_outer"], axis=1)
    q["q25"] = x.quantile(BAND_Q["low_inner"], axis=1)
    q["q50"] = x.quantile(BAND_Q["median"], axis=1)
    q["q75"] = x.quantile(BAND_Q["high_inner"], axis=1)
    q["q95"] = x.quantile(BAND_Q["high_outer"], axis=1)
    return q


def _add_bands(fig: go.Figure, x, q: pd.DataFrame):
    # 5–25
    fig.add_trace(go.Scatter(
        x=x, y=q["q5"], mode="lines", line=dict(width=0),
        name="5–25%", showlegend=False, hoverinfo="skip"
    ))
    fig.add_trace(go.Scatter(
        x=x, y=q["q25"], mode="lines", line=dict(width=0),
        fill="tonexty", fillcolor="rgba(160,160,160,0.25)",
        name="5–25%", hoverinfo="skip"
    ))

    # 25–75
    fig.add_trace(go.Scatter(
        x=x, y=q["q25"], mode="lines", line=dict(width=0),
        name="25–75%", showlegend=False, hoverinfo="skip"
    ))
    fig.add_trace(go.Scatter(
        x=x, y=q["q75"], mode="lines", line=dict(width=0),
        fill="tonexty", fillcolor="rgba(90,90,90,0.35)",
        name="25–75%", hoverinfo="skip"
    ))

    # 75–95
    fig.add_trace(go.Scatter(
        x=x, y=q["q75"], mode="lines", line=dict(width=0),
        name="75–95%", showlegend=False, hoverinfo="skip"
    ))
    fig.add_trace(go.Scatter(
        x=x, y=q["q95"], mode="lines", line=dict(width=0),
        fill="tonexty", fillcolor="rgba(160,160,160,0.25)",
        name="75–95%", hoverinfo="skip"
    ))

    # median
    fig.add_trace(go.Scatter(
        x=x, y=q["q50"], mode="lines",
        line=dict(width=2),
        name="Median (50%)"
    ))


# -----------------------------------------------------------------------------
# PLOTLY: Reservoir Elevation + Outflow
# Bands use base ensembles only.
# Individual traces use sorted base ensembles + grouped synthetic traces at end.
# -----------------------------------------------------------------------------
for res_abbr, res_name in RESERVOIR_NAME_MAP.items():

    # ---------------- Elevation ----------------
    elev_cols = _get_ensemble_cols(data_ens, f"{res_abbr}_elev__", ensemble_fparts_model_base)
    if elev_cols:
        x = data_ens.index
        q = _row_quantiles(data_ens, elev_cols)

        fig = go.Figure()
        _add_bands(fig, x, q)

        if res_abbr in rule_curve_df.columns:
            rc_series = build_rule_curve_series_for_index(x, rule_curve_df[res_abbr])
            rc_series = _clean_daily_series(rc_series)

            if not rc_series.empty:
                fig.add_trace(go.Scatter(
                    x=rc_series.index, y=rc_series.values,
                    mode="lines",
                    line=dict(width=3, color="black"),
                    name="Rule Curve"
                ))
        else:
            print(f"[WARN] Reservoir {res_abbr} not found in rule curve csv columns.")

        obs_col = f"{res_abbr}_obsElev"
        if obs_col in data_ens.columns:
            obs_s = pd.to_numeric(data_ens[obs_col], errors="coerce").dropna()
            if not obs_s.empty:
                fig.add_trace(go.Scatter(
                    x=obs_s.index, y=obs_s.values,
                    mode="lines",
                    line=dict(width=3, color="black", dash="dot"),
                    name="Observed"
                ))

        if res_abbr in H_LINE_DICT:
            for label, elev in H_LINE_DICT[res_abbr].items():
                fig.add_trace(go.Scatter(
                    x=x,
                    y=[elev] * len(x),
                    mode="lines",
                    line=dict(width=2, color="black", dash="dash"),
                    name=label,
                    hovertemplate=f"{label}<br>Elevation: {elev:.2f}<extra></extra>",
                ))

        for fp in ensemble_fparts_sorted:
            col = f"{res_abbr}_elev__{fp}"
            if col not in data_ens.columns:
                continue

            label = _fpart_to_clean_label(fp, salem_unreg_pct_by_year)

            fig.add_trace(go.Scatter(
                x=x, y=data_ens[col],
                mode="lines",
                line=dict(width=1),
                name=label,
                hovertemplate=f"{label}<br>%{{x|%Y-%m-%d}}<br>%{{y:.2f}}<extra></extra>",
            ))

        fig.update_layout(
            title=f"{res_name} RESERVOIR",
            xaxis_title="Date",
            yaxis_title="Elevation (ft)",
            hovermode="closest",
            template="plotly_white",
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02
            ),
            margin=dict(l=60, r=260, t=60, b=50),
        )

        file_path = dated_folder / f"{res_abbr}_elevation_ensemble.html"
        fig.write_html(
            file_path,
            include_plotlyjs="cdn",
            full_html=True,
            post_script="""
            document.documentElement.lang = 'en';
            """
        )

    # ---------------- Outflow ----------------
    out_cols = _get_ensemble_cols(data_ens, f"{res_abbr}_outflow__", ensemble_fparts_model_base)
    if out_cols:
        x = data_ens.index
        q = _row_quantiles(data_ens, out_cols)

        fig = go.Figure()
        _add_bands(fig, x, q)

        obs_out_col = f"{res_abbr}_obsOutflow"
        if obs_out_col in data_ens.columns:
            obs_out_s = pd.to_numeric(data_ens[obs_out_col], errors="coerce").dropna()
            if not obs_out_s.empty:
                fig.add_trace(go.Scatter(
                    x=obs_out_s.index, y=obs_out_s.values,
                    mode="lines",
                    line=dict(width=3, color="red"),
                    name="Observed"
                ))

        for fp in ensemble_fparts_sorted:
            col = f"{res_abbr}_outflow__{fp}"
            if col not in data_ens.columns:
                continue

            label = _fpart_to_clean_label(fp, salem_unreg_pct_by_year)

            fig.add_trace(go.Scatter(
                x=x, y=data_ens[col],
                mode="lines",
                line=dict(width=1),
                name=label,
                hovertemplate=f"{label}<br>%{{x|%Y-%m-%d}}<br>%{{y:.2f}}<extra></extra>",
            ))

        fig.update_layout(
            title=f"{res_name} Reservoir Outflow (Bands + Ensembles)",
            xaxis_title="Date",
            yaxis_title="Outflow (cfs)",
            hovermode="closest",
            template="plotly_white",
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02
            ),
            margin=dict(l=60, r=260, t=60, b=50),
        )

        file_path = dated_folder / f"{res_abbr}_outflow_ensemble.html"
        fig.write_html(file_path, include_plotlyjs="cdn")

# -----------------------------------------------------------------------------
# PLOTLY: Salem Flow
# Bands use base ensembles only.
# Individual traces use sorted base ensembles + grouped synthetic traces at end.
# -----------------------------------------------------------------------------
salem_cols = _get_ensemble_cols(data_ens, "SLMO_flow__", ensemble_fparts_model_base)
if salem_cols:
    x = data_ens.index
    q = _row_quantiles(data_ens, salem_cols)

    fig = go.Figure()
    _add_bands(fig, x, q)

    salem_min_low = build_seasonal_step_series(x, SALEM_MINFLOW_SCHEDULE, "Low")
    salem_min_high = build_seasonal_step_series(x, SALEM_MINFLOW_SCHEDULE, "High")

    fig.add_trace(go.Scatter(
        x=x, y=salem_min_low,
        mode="lines",
        line=dict(width=3, color="black", dash="dash"),
        name="Salem Min Flow Low"
    ))

    fig.add_trace(go.Scatter(
        x=x, y=salem_min_high,
        mode="lines",
        line=dict(width=3, color="black"),
        name="Salem Min Flow High"
    ))

    for fp in ensemble_fparts_sorted:
        col = f"SLMO_flow__{fp}"
        if col not in data_ens.columns:
            continue

        label = _fpart_to_clean_label(fp, salem_unreg_pct_by_year)

        fig.add_trace(go.Scatter(
            x=x, y=data_ens[col],
            mode="lines",
            line=dict(width=1),
            name=label,
            hovertemplate=f"{label}<br>%{{x|%Y-%m-%d}}<br>%{{y:.2f}}<extra></extra>",
        ))

    fig.update_layout(
        title="Willamette River at Salem Flow (Bands + Ensembles)",
        xaxis_title="Date",
        yaxis_title="Flow (cfs)",
        hovermode="closest",
        template="plotly_white",
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        ),
        margin=dict(l=60, r=260, t=60, b=50),
    )

    file_path = dated_folder / "SLMO_flow_ensemble.html"
    fig.write_html(file_path, include_plotlyjs="cdn")
    fig.show()