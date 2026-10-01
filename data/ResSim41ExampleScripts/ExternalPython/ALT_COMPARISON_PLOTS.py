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
TRIAL_SUFFIXES = cfg.TRIAL_SUFFIXES
H_LINE_DICT = cfg.H_LINE_DICT

RULE_CURVE_CSV = "RULE_CURVES.csv"

SYNTHETIC_ENSEMBLE_LABELS = {
    2026: "D%25",
    2027: "D%50",
    2028: "D%75",
}

SYNTHETIC_YEARS = [2026, 2027, 2028]

SYNTHETIC_COLORS = {
    2026: "red",
    2027: "blue",
    2028: "green",
}

TRIAL_DASH_PATTERNS = [
    "solid",
    "dash",
    "dot",
    "dashdot",
    "longdash",
    "longdashdot",
]

# D-part block start dates covering the simulation period.
# Each ensemble member's data is split across these calendar-year blocks.
# Extend this list if the simulation spans additional calendar blocks.
DPART_STARTS = ["01JAN2026", "01JAN2027"]

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


def _build_dpart_path_dict(base_path_dict: dict, dpart: str) -> dict:
    """
    Given a base path_dict whose paths have an empty D-part slot:
        //A/B//1DAY/{fpart}/
    Return a new dict with keys suffixed __{dpart} and D-part filled:
        //A/B/{dpart}/1DAY/{fpart}/

    DSS pathname split on '/' gives:
        ['', '', 'A', 'B', 'D', 'E', 'F', '']
    Index 4 is the D-part slot.
    """
    result = {}
    for alias, path in base_path_dict.items():
        parts = path.split("/")
        if len(parts) >= 7:
            parts[4] = dpart
        new_path = "/".join(parts)
        result[f"{alias}__{dpart}"] = new_path
    return result


def readallpaths_dpart(dss_file, base_path_dict: dict, dparts: list) -> pd.DataFrame:
    """
    Read all paths for every D-part in `dparts`, then splice each
    (alias, dpart) pair back to a single alias column.

    Steps:
      1. Build combined path dict with keys like alias__{dpart}
      2. Read all paths in one HecDss session
      3. For each alias, concat the dpart series after dropna() so that
         NaN-padded rows from the shared DataFrame index don't mask real
         values from the other D-part chunk. Deduplicate and sort.

    Returns a DataFrame with original alias names as columns.
    """
    # Step 1: combined path dict across all dparts
    combined_path_dict = {}
    for dpart in dparts:
        combined_path_dict.update(_build_dpart_path_dict(base_path_dict, dpart))

    # Step 2: read everything in one session
    fid = HecDss.Open(os.fspath(dss_file))
    dflist = []
    for alias, path in combined_path_dict.items():
        try:
            ts = fid.read_ts(path, trim_missing=True)
            df = pd.DataFrame(ts.values, columns=[alias], index=np.array(ts.pytimes))
            dflist.append(df.copy())
        except Exception as e:
            print(f"[DSS] Failed '{alias}' -> {path} in {os.path.basename(os.fspath(dss_file))}: {e}")
    fid.close()

    if not dflist:
        return pd.DataFrame()

    data_raw = pd.concat(dflist, axis=1)
    data_raw.index = pd.to_datetime(data_raw.index)
    data_raw = data_raw[~data_raw.index.duplicated(keep="last")].sort_index()

    # Step 3: splice dpart columns back to base alias names.
    # dropna() before concat so NaN-padded rows from the shared index
    # don't overwrite real values from the other D-part chunk.
    spliced_frames = []
    for alias in base_path_dict:
        dpart_cols = [
            f"{alias}__{d}" for d in dparts
            if f"{alias}__{d}" in data_raw.columns
        ]
        if not dpart_cols:
            continue
        pieces = [data_raw[c].dropna().rename(alias) for c in dpart_cols]
        combined = pd.concat(pieces)
        combined = combined[~combined.index.duplicated(keep="last")].sort_index()
        spliced_frames.append(combined)

    if not spliced_frames:
        return pd.DataFrame()

    return pd.concat(spliced_frames, axis=1)


def with_fpart_suffix(d, fpart):
    """Make alias keys unique per fpart so dict.update doesn't overwrite."""
    return {f"{k}__{fpart}": v for k, v in d.items()}


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
    Parse strings like:
      01Dec2025 0800
    Excel may display the same value as:
      12/1/2025 8:00:00 AM
    but the CSV text is expected to be in ddMMMyyyy HHMM form.
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
    rc["DATE"] = pd.to_datetime(rc["DATE"])
    rc = rc.set_index("DATE").sort_index()
    rc = rc[~rc.index.duplicated(keep="last")]

    for c in rc.columns:
        rc[c] = pd.to_numeric(rc[c], errors="coerce")

    return rc


def build_rule_curve_series_for_index(target_index, template_series: pd.Series) -> pd.Series:
    """
    Repeat a one-year rule curve across all years in target_index.

    Matching is done by month/day, ignoring the template year.
    If Feb 29 is needed in a leap year but missing from the template,
    fill it by interpolation between Feb 28 and Mar 1.
    """
    target_index = pd.to_datetime(target_index)
    out = pd.Series(index=target_index, dtype=float)

    s = pd.to_numeric(template_series, errors="coerce").dropna().copy()
    if s.empty:
        return out

    s.index = pd.to_datetime(s.index)
    s = s[~s.index.duplicated(keep="last")]
    s = s.sort_index()

    # Build month-day lookup from the template year
    md_lookup = {
        (ts.month, ts.day): float(val)
        for ts, val in s.items()
    }

    # If template actually contains Feb 29, keep it; otherwise interpolate it
    if (2, 29) not in md_lookup:
        if (2, 28) in md_lookup and (3, 1) in md_lookup:
            md_lookup[(2, 29)] = 0.5 * (md_lookup[(2, 28)] + md_lookup[(3, 1)])

    values = []
    for ts in target_index:
        key = (ts.month, ts.day)
        if key in md_lookup:
            values.append(md_lookup[key])
        else:
            values.append(np.nan)

    out[:] = values

    # Fill any remaining gaps by interpolation over the time axis
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


def create_elev_paths(fpart):
    return {f"{s}_elev": f"//{l}-POOL/ELEV//1DAY/{fpart}/" for s, l in RESERVOIR_NAME_MAP.items()}


def create_outflow_paths(fpart):
    return {f"{s}_outflow": f"//{l}-POOL/FLOW-OUT//1DAY/{fpart}/" for s, l in RESERVOIR_NAME_MAP.items()}


def create_flow_paths(fpart):
    return {f"{s}_flow": f"//{l}/FLOW//1DAY/{fpart}/" for s, l in CONTROL_POINT_MAP.items()}


# -----------------------------------------------------------------------------
# OBSERVED PATHS
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

sim_dir = SIM_NAME.replace(" ", "_")

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent

# Assumes script is in: <watershed>\scripts\...
WATERSHED_DIR = SCRIPT_DIR.parent.parent

DSS_PATH = (WATERSHED_DIR / "rss" / sim_dir / "simulation.dss").resolve()
DSS_FILE_IN = str(DSS_PATH)
print("DSS_FILE_IN:", DSS_FILE_IN)

plotly_output_dir = WATERSHED_DIR / "output_plots" / "plotly_html_trials"
plotly_output_dir.mkdir(parents=True, exist_ok=True)

dated_folder = plotly_output_dir / pd.Timestamp.now().strftime("%Y-%m-%d_%H%M")
dated_folder.mkdir(parents=True, exist_ok=True)

RULE_CURVE_CSV_PATH = (SCRIPT_DIR / RULE_CURVE_CSV).resolve()
print("RULE_CURVE_CSV_PATH:", RULE_CURVE_CSV_PATH)

rule_curve_df = load_rule_curve_csv(RULE_CURVE_CSV_PATH)

# -----------------------------------------------------------------------------
# ALT / F-PART HELPERS
# -----------------------------------------------------------------------------
def format_alt_with_trial(alt_name: str, trial_suffix: int) -> str:
    """
    ResSim F-part style:
      ALTERNATIVE_NAME_STEP1 -> pad to 10 chars with '-'
      then append trial suffix
    Example:
      Con_Season -> Con_Season0, Con_Season1, ...
    """
    formatted = alt_name.replace(" ", "-")
    if len(formatted) < 10:
        formatted = formatted.ljust(10, "-")
    return f"{formatted}{trial_suffix}"


def build_trial_model_fparts(trial_suffixes: List[int], synthetic_years: List[int]) -> Dict[int, List[str]]:
    out = {}
    for trial in trial_suffixes:
        alt_fpart = format_alt_with_trial(ALTERNATIVE_NAME_STEP1, trial)
        out[trial] = [f"C:00{year}|{alt_fpart}" for year in synthetic_years]
    return out


trial_fparts = build_trial_model_fparts(TRIAL_SUFFIXES, SYNTHETIC_YEARS)

# -----------------------------------------------------------------------------
# READ DSS
# -----------------------------------------------------------------------------
# Build base path dict with empty D-part slots.
# readallpaths_dpart will fill in each D-part and splice back.
base_path_dict = {}

for trial, fparts in trial_fparts.items():
    for fpart in fparts:
        base_path_dict.update(with_fpart_suffix(create_elev_paths(fpart), fpart))
        base_path_dict.update(with_fpart_suffix(create_outflow_paths(fpart), fpart))
        base_path_dict.update(with_fpart_suffix(create_flow_paths(fpart), fpart))

# Observed traces have no D-part splitting needed; read them separately.
obs_path_dict = {}
obs_path_dict.update(create_observed_elev_paths())
obs_path_dict.update(create_observed_outflow_paths())

data_model = readallpaths_dpart(DSS_FILE_IN, base_path_dict, DPART_STARTS)
data_obs   = readallpaths(DSS_FILE_IN, obs_path_dict)

# Combine into a single DataFrame matching the original `data` variable name
data = pd.concat([data_model, data_obs], axis=1)
data = data[~data.index.duplicated(keep="last")].sort_index()

if data.empty:
    raise RuntimeError("No data were read from DSS. Check paths and F-parts.")

# -----------------------------------------------------------------------------
# PLOT HELPERS
# -----------------------------------------------------------------------------
def synthetic_label_from_year(year: int) -> str:
    return SYNTHETIC_ENSEMBLE_LABELS.get(year, str(year))


def get_trial_dash(trial: int) -> str:
    try:
        idx = TRIAL_SUFFIXES.index(trial)
    except ValueError:
        idx = 0
    return TRIAL_DASH_PATTERNS[idx % len(TRIAL_DASH_PATTERNS)]


def add_observed_trace(fig, series, name, color="red", width=3, dash="dot"):
    s = _clean_daily_series(series)
    if s.empty:
        return
    fig.add_trace(go.Scatter(
        x=s.index,
        y=s.values,
        mode="lines",
        line=dict(width=width, color=color, dash=dash),
        name=name,
        hovertemplate=f"{name}<br>%{{x|%Y-%m-%d}}<br>%{{y:.2f}}<extra></extra>",
    ))


def add_rule_curve_trace(fig, series, name, showlegend, color="black", width=3, dash="solid"):
    s = _clean_daily_series(series)
    if s.empty:
        return
    fig.add_trace(go.Scatter(
        x=s.index,
        y=s.values,
        mode="lines",
        line=dict(width=width, color=color, dash=dash),
        name=name,
        showlegend=showlegend,
        hovertemplate=f"{name}<br>%{{x|%Y-%m-%d}}<br>%{{y:.2f}}<extra></extra>",
    ))


def add_trial_synthetic_traces(fig, df, prefix: str):
    """
    Add D%25, D%50, D%75 for each requested trial.
    Color = synthetic member
    Dash = trial suffix order
    """
    for trial in TRIAL_SUFFIXES:
        dash_style = get_trial_dash(trial)

        for year in SYNTHETIC_YEARS:
            fpart = f"C:00{year}|{format_alt_with_trial(ALTERNATIVE_NAME_STEP1, trial)}"
            col = f"{prefix}__{fpart}"
            if col not in df.columns:
                print(f"[WARN] Missing column: {col}")
                continue

            label = synthetic_label_from_year(year)
            display_name = f"{label} Trial {trial}"
            color = SYNTHETIC_COLORS[year]

            fig.add_trace(go.Scatter(
                x=df.index,
                y=pd.to_numeric(df[col], errors="coerce"),
                mode="lines",
                line=dict(width=2, color=color, dash=dash_style),
                name=display_name,
                legendgroup=f"{label}",
                hovertemplate=f"{display_name}<br>%{{x|%Y-%m-%d}}<br>%{{y:.2f}}<extra></extra>",
            ))


# -----------------------------------------------------------------------------
# PLOT: Reservoir Elevation + Outflow
# -----------------------------------------------------------------------------
for res_abbr, res_name in RESERVOIR_NAME_MAP.items():

    # ---------------- Elevation ----------------
    fig = go.Figure()

    if res_abbr in rule_curve_df.columns:
        rc_series = build_rule_curve_series_for_index(data.index, rule_curve_df[res_abbr])
        rc_series.index = rc_series.index - pd.Timedelta(hours=8)
        add_rule_curve_trace(
            fig,
            rc_series,
            "Rule Curve",
            showlegend=True,
            color="black",
            width=3,
            dash="solid",
        )
    else:
        print(f"[WARN] Reservoir {res_abbr} not found in rule curve csv columns.")

    obs_col = f"{res_abbr}_obsElev"
    if obs_col in data.columns:
        add_observed_trace(
            fig,
            data[obs_col],
            "Observed",
            color="black",
            width=3,
            dash="dot",
        )

    if res_abbr in H_LINE_DICT:
        for label, elev in H_LINE_DICT[res_abbr].items():
            fig.add_trace(go.Scatter(
                x=data.index,
                y=[elev] * len(data.index),
                mode="lines",
                line=dict(width=2, color="black", dash="dash"),
                name=label,
                hovertemplate=f"{label}<br>Elevation: {elev:.2f}<extra></extra>",
            ))

    add_trial_synthetic_traces(fig, data, f"{res_abbr}_elev")

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
            x=1.02,
        ),
        margin=dict(l=60, r=260, t=60, b=50),
    )

    file_path = dated_folder / f"{res_abbr}_elevation_trials.html"
    fig.write_html(
        file_path,
        include_plotlyjs="cdn",
        full_html=True,
        post_script="""
        document.documentElement.lang = 'en';
        """
    )

    # ---------------- Outflow ----------------
    fig = go.Figure()

    obs_out_col = f"{res_abbr}_obsOutflow"
    if obs_out_col in data.columns:
        add_observed_trace(
            fig,
            data[obs_out_col],
            "Observed",
            color="red",
            width=3,
            dash="solid",
        )

    add_trial_synthetic_traces(fig, data, f"{res_abbr}_outflow")

    fig.update_layout(
        title=f"{res_name} Reservoir Outflow",
        xaxis_title="Date",
        yaxis_title="Outflow (cfs)",
        hovermode="closest",
        template="plotly_white",
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
        ),
        margin=dict(l=60, r=260, t=60, b=50),
    )

    file_path = dated_folder / f"{res_abbr}_outflow_trials.html"
    fig.write_html(
        file_path,
        include_plotlyjs="cdn",
        full_html=True,
        post_script="""
        document.documentElement.lang = 'en';
        """
    )

# -----------------------------------------------------------------------------
# PLOT: Control Point Flows
# -----------------------------------------------------------------------------
for cp_abbr, cp_name in CONTROL_POINT_MAP.items():
    fig = go.Figure()

    add_trial_synthetic_traces(fig, data, f"{cp_abbr}_flow")

    fig.update_layout(
        title=f"{cp_name} Flow",
        xaxis_title="Date",
        yaxis_title="Flow (cfs)",
        hovermode="closest",
        template="plotly_white",
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
        ),
        margin=dict(l=60, r=260, t=60, b=50),
    )

    file_path = dated_folder / f"{cp_abbr}_flow_trials.html"
    fig.write_html(
        file_path,
        include_plotlyjs="cdn",
        full_html=True,
        post_script="""
        document.documentElement.lang = 'en';
        """
    )

    if cp_abbr == "SLMO":
        fig.show()

print("Wrote plots to:", dated_folder)