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

# -----------------------------------------------------------------------------
# USER CONTROL
# -----------------------------------------------------------------------------
# Include synthetic daily-percentile members 2026–2028.
YearRange = range(1981, 2029)

TRIAL = cfg.TRIAL
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
    fid = HecDss.Open(os.fspath(dss_file))  # allow Path or str
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
    return data


def with_fpart_suffix(d, fpart):
    """Make alias keys unique per ensemble member so dict.update doesn't overwrite."""
    return {f"{k}__{fpart}": v for k, v in d.items()}


def fpart_to_year(fp: str) -> int:
    # fp like "C:001987|ConSeson0" OR "C:001987|"
    cpart = fp.split("|")[0]  # "C:001987"
    return int(cpart.replace("C:", "")[-4:])


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


def create_rcelev_paths_model(fpart):
    return {f"{s}_rcElev_model": f"//{l}-RULE CURVE/ELEV-ZONE//1DAY/{fpart}/" for s, l in RESERVOIR_NAME_MAP.items()}


def create_flow_paths(fpart):
    return {f"{s}_flow": f"//{l}/FLOW//1DAY/{fpart}/" for s, l in CONTROL_POINT_MAP.items()}


def create_min_mainstem_flow_paths(fpart):
    return {
        "salem_minflow": f"//SALEM/FLOW-MIN-EXTERNALFLOWAUG//1Day/{fpart}/",
        "albany_minflow": f"//ALBANY/FLOW-MIN-EXTERNALFLOWAUG//1Day/{fpart}/",
    }


def create_salem_unreg_path(unreg_fpart: str) -> Dict[str, str]:
    # Salem UNREG uses ONLY the ensemble year F-part, e.g. "C:002025|"
    return {"salem_unreg": f"//SLMO3/FLOW-UNREG//1DAY/{unreg_fpart}/"}


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
# OBSERVED PATHS (single traces; no explicit time window in D-part)
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

OBS_RC_ELEV_PATHS = {
    "BLU": "//BLU/Elev-RuleCurve//1DAY/CENWP-CALC/",
    "COT": "//COT/Elev-RuleCurve//1DAY/CENWP-CALC/",
    "DOR": "//DOR/Elev-RuleCurve//1DAY/CENWP-CALC/",
    "FAL": "//FAL/Elev-RuleCurve//1DAY/CENWP-CALC/",
    "FRN": "//FRN/Elev-RuleCurve//1DAY/CENWP-CALC/",
    "CGR": "//CGR/Elev-RuleCurve//1DAY/CENWP-CALC/",
    "DET": "//DET/Elev-RuleCurve//1DAY/CENWP-CALC/",
    "FOS": "//FOS/Elev-RuleCurve//1DAY/CENWP-CALC/",
    "GPR": "//GPR/Elev-RuleCurve//1DAY/CENWP-CALC/",
    "HCR": "//HCR/Elev-RuleCurve//1DAY/CENWP-CALC/",
    "LOP": "//LOP/Elev-RuleCurve//1DAY/CENWP-CALC/",
}


def create_observed_elev_paths() -> Dict[str, str]:
    return {f"{k}_obsElev": v for k, v in OBS_ELEV_PATHS.items()}


def create_observed_outflow_paths() -> Dict[str, str]:
    return {f"{k}_obsOutflow": v for k, v in OBS_OUTFLOW_PATHS.items()}


def create_observed_rcelev_paths() -> Dict[str, str]:
    return {f"{k}_obsRcElev": v for k, v in OBS_RC_ELEV_PATHS.items()}


# -----------------------------------------------------------------------------
# CONFIG / PATHS
# -----------------------------------------------------------------------------
SIM_NAME = cfg.SIM_NAME
ALTERNATIVE_NAME_STEP1 = cfg.ALTERNATIVE_NAME_STEP1

# Format ALT name to match your DSS F-part scheme (pad to 10, then add trailing "0")
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
# READ DSS (ensembles + rule/obs + salem unreg)
# -----------------------------------------------------------------------------
path_dict = {}

# Model outputs
for fpart in ensemble_fparts_model:
    path_dict.update(with_fpart_suffix(create_elev_paths(fpart), fpart))
    path_dict.update(with_fpart_suffix(create_outflow_paths(fpart), fpart))
    path_dict.update(with_fpart_suffix(create_flow_paths(fpart), fpart))

# Modeled rule curve: read once using first model fpart
rc_fpart = ensemble_fparts_model[0]
path_dict.update(create_rcelev_paths_model(rc_fpart))
# path_dict.update(create_min_mainstem_flow_paths(rc_fpart))

# Observed single traces
path_dict.update(create_observed_elev_paths())
path_dict.update(create_observed_outflow_paths())
path_dict.update(create_observed_rcelev_paths())

# Salem UNREG (year-only fparts); alias by year
for unreg_fp in ensemble_fparts_unreg:
    yr = fpart_to_year(unreg_fp)
    path_dict[f"salem_unreg__{yr}"] = create_salem_unreg_path(unreg_fp)["salem_unreg"]

data_ens = readallpaths(DSS_FILE_IN, path_dict)

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
        "No Salem UNREG series found. Expected paths like //SLMO3/FLOW-UNREG//1DAY/C:00YYYY|/"
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
import plotly.graph_objects as go


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

def _clean_daily_series(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").dropna().copy()
    if s.empty:
        return s

    s.index = pd.to_datetime(s.index).normalize()
    s = s[~s.index.duplicated(keep="last")]
    return s.sort_index()

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

        rc_model_col = f"{res_abbr}_rcElev_model"
        if rc_model_col in data_ens.columns:
            rc_model_s = pd.to_numeric(data_ens[rc_model_col], errors="coerce").dropna()
            if not rc_model_s.empty:
                fig.add_trace(go.Scatter(
                    x=rc_model_s.index, y=rc_model_s.values,
                    mode="lines",
                    line=dict(width=3, color="black"),
                    name="Rule Curve (Modeled)"
                ))

        rc_obs_col = f"{res_abbr}_obsRcElev"
        if rc_obs_col in data_ens.columns:
            rc_obs_s = pd.to_numeric(data_ens[rc_obs_col], errors="coerce").dropna()
            if not rc_obs_s.empty:
                fig.add_trace(go.Scatter(
                    x=rc_obs_s.index, y=rc_obs_s.values,
                    mode="lines",
                    line=dict(width=3, color="black"),
                    name="Rule Curve (Observed Period)"
                ))

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
            title=f"{res_name} Reservoir",
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