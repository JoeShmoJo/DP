import os
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from pydsstools.heclib.dss import HecDss

import CONFIG as cfg

import plotly.io as pio
pio.renderers.default = "browser"

# -----------------------------------------------------------------------------
# USER CONTROL
# -----------------------------------------------------------------------------
# Year range for ensembles for testing. Use range(1981, 2026) for full set, etc.
YearRange = range(1981, 2026)

# Shaded band quantiles (row-wise across ensembles)
BAND_Q = {
    "low_outer": 0.05,
    "low_inner": 0.25,
    "median":    0.50,
    "high_inner": 0.75,
    "high_outer": 0.95,
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


def create_rcelev_paths(fpart):
    return {f"{s}_rcElev": f"//{l}-RULE CURVE/ELEV-ZONE//1DAY/{fpart}/" for s, l in RESERVOIR_NAME_MAP.items()}


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


def create_observed_elev_paths() -> Dict[str, str]:
    return {f"{k}_obsElev": v for k, v in OBS_ELEV_PATHS.items()}


def create_observed_outflow_paths() -> Dict[str, str]:
    return {f"{k}_obsOutflow": v for k, v in OBS_OUTFLOW_PATHS.items()}


# -----------------------------------------------------------------------------
# CONFIG / PATHS
# -----------------------------------------------------------------------------
SIM_NAME = getattr(cfg, "SIM_NAME", "2026.02.24-2400")
ALTERNATIVE_NAME_STEP1 = getattr(cfg, "ALTERNATIVE_NAME_STEP1", "ConSeson")

# Format ALT name to match your DSS F-part scheme (pad to 10, then add trailing "0")
FORMATTED_ALT_NAME = ALTERNATIVE_NAME_STEP1.replace(" ", "-")
if len(FORMATTED_ALT_NAME) < 10:
    FORMATTED_ALT_NAME = FORMATTED_ALT_NAME.ljust(10, "-")
FORMATTED_ALT_NAME = FORMATTED_ALT_NAME + "0"

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

# Model outputs use ALT-suffixed F-part
ensemble_fparts_model = [f"C:00{year}|{FORMATTED_ALT_NAME}" for year in ensemble_years]

# Salem UNREG uses ONLY year F-part (ends with a pipe)
ensemble_fparts_unreg = [f"C:00{year}|" for year in ensemble_years]

# -----------------------------------------------------------------------------
# READ DSS (ensembles + rule/obs + salem unreg)
# -----------------------------------------------------------------------------
path_dict = {}

# Model outputs
for fpart in ensemble_fparts_model:
    path_dict.update(with_fpart_suffix(create_elev_paths(fpart), fpart))
    path_dict.update(with_fpart_suffix(create_outflow_paths(fpart), fpart))
    path_dict.update(with_fpart_suffix(create_flow_paths(fpart), fpart))

# Rule curve elev & minflows: typically invariant across ensembles; read once using first model fpart
rc_fpart = ensemble_fparts_model[0]
path_dict.update(create_rcelev_paths(rc_fpart))
# path_dict.update(create_min_mainstem_flow_paths(rc_fpart))

# Observed (single traces)
path_dict.update(create_observed_elev_paths())
path_dict.update(create_observed_outflow_paths())

# Salem UNREG (year-only fparts); alias by year
for unreg_fp in ensemble_fparts_unreg:
    yr = fpart_to_year(unreg_fp)
    path_dict[f"salem_unreg__{yr}"] = create_salem_unreg_path(unreg_fp)["salem_unreg"]

data_ens = readallpaths(DSS_FILE_IN, path_dict)

# -----------------------------------------------------------------------------
# SALEM UNREG PERCENTILES (non-exceedance), keyed by YEAR
# -----------------------------------------------------------------------------
salem_unreg_cols = [f"salem_unreg__{y}" for y in ensemble_years if f"salem_unreg__{y}" in data_ens.columns]
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

# Sort MODEL fparts by Salem UNREG percentile (legend/traces ordered by percentile)
ensemble_fparts_sorted = sorted(
    ensemble_fparts_model,
    key=lambda fp: salem_unreg_pct_by_year.get(fpart_to_year(fp), np.nan),
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
    Where 42% = non-exceedance percentile (0–100) rounded, based on Salem UNREG summed volume.
    """
    try:
        year = fpart.split("|")[0].replace("C:", "")[-4:]
        pct = float(pct_by_year.loc[int(year)])
        pct_int = int(round(pct))
        return f"{year} ({pct_int:02d}%)"
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
    q["q5"]  = x.quantile(BAND_Q["low_outer"],  axis=1)
    q["q25"] = x.quantile(BAND_Q["low_inner"],  axis=1)
    q["q50"] = x.quantile(BAND_Q["median"],     axis=1)
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


def _add_dropdown_show_all_none(fig: go.Figure, ensemble_trace_idxs: list):
    n_total = len(fig.data)

    def visible_mask(show_ens: bool) -> list:
        vis = [True] * n_total
        for tidx in ensemble_trace_idxs:
            vis[tidx] = show_ens
        return vis

    buttons = [
        {"label": "Bands only", "method": "update", "args": [{"visible": visible_mask(False)}]},
        {"label": "Show all ensembles", "method": "update", "args": [{"visible": visible_mask(True)}]},
    ]

    fig.update_layout(
        updatemenus=[{
            "type": "dropdown",
            "x": 1.02, "y": 1.0,
            "xanchor": "left", "yanchor": "top",
            "buttons": buttons,
        }]
    )


# -----------------------------------------------------------------------------
# PLOTLY: Reservoir Elevation + Outflow (bands + ensembles sorted by percentile)
# -----------------------------------------------------------------------------
for res_abbr, res_name in RESERVOIR_NAME_MAP.items():

    # ---------------- Elevation ----------------
    elev_cols = _get_ensemble_cols(data_ens, f"{res_abbr}_elev__", ensemble_fparts_sorted)
    if elev_cols:
        x = data_ens.index
        q = _row_quantiles(data_ens, elev_cols)

        fig = go.Figure()
        _add_bands(fig, x, q)

        rc_col = f"{res_abbr}_rcElev"
        if rc_col in data_ens.columns:
            fig.add_trace(go.Scatter(
                x=x, y=data_ens[rc_col],
                mode="lines",
                line=dict(width=3, color="black"),
                name="Rule Curve"
            ))

        obs_col = f"{res_abbr}_obsElev"
        if obs_col in data_ens.columns:
            fig.add_trace(go.Scatter(
                x=x, y=data_ens[obs_col],
                mode="lines",
                line=dict(width=3, color="red"),
                name="Observed"
            ))

        ensemble_trace_idxs = []
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
                visible=False,
                hovertemplate=f"{label}<br>%{{x|%Y-%m-%d}}<br>%{{y:.2f}}<extra></extra>",
            ))
            ensemble_trace_idxs.append(len(fig.data) - 1)

        fig.update_layout(
            title=f"{res_name} Reservoir Elevation (Bands + Ensembles)",
            xaxis_title="Date",
            yaxis_title="Elevation (ft)",
            hovermode="x unified",
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(l=60, r=220, t=60, b=50),
        )

        _add_dropdown_show_all_none(fig, ensemble_trace_idxs)
        file_path = dated_folder / f"{res_abbr}_elevation_ensemble.html"
        fig.write_html(file_path, include_plotlyjs="cdn")

    # ---------------- Outflow ----------------
    out_cols = _get_ensemble_cols(data_ens, f"{res_abbr}_outflow__", ensemble_fparts_sorted)
    if out_cols:
        x = data_ens.index
        q = _row_quantiles(data_ens, out_cols)

        fig = go.Figure()
        _add_bands(fig, x, q)

        obs_out_col = f"{res_abbr}_obsOutflow"
        if obs_out_col in data_ens.columns:
            fig.add_trace(go.Scatter(
                x=x, y=data_ens[obs_out_col],
                mode="lines",
                line=dict(width=3, color="red"),
                name="Observed"
            ))

        ensemble_trace_idxs = []
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
                visible=False,
                hovertemplate=f"{label}<br>%{{x|%Y-%m-%d}}<br>%{{y:.2f}}<extra></extra>",
            ))
            ensemble_trace_idxs.append(len(fig.data) - 1)

        fig.update_layout(
            title=f"{res_name} Reservoir Outflow (Bands + Ensembles)",
            xaxis_title="Date",
            yaxis_title="Outflow (cfs)",
            hovermode="x unified",
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(l=60, r=220, t=60, b=50),
        )

        _add_dropdown_show_all_none(fig, ensemble_trace_idxs)
        # Create a dated folder inside the plotly output directory


        # Save the plot in the dated folder
        file_path = dated_folder / f"{res_abbr}_outflow_ensemble.html"
        fig.write_html(file_path, include_plotlyjs="cdn")


# -----------------------------------------------------------------------------
# PLOTLY: Salem Flow (bands + ensembles sorted by percentile)
# -----------------------------------------------------------------------------
salem_cols = _get_ensemble_cols(data_ens, "SLMO_flow__", ensemble_fparts_sorted)
if salem_cols:
    x = data_ens.index
    q = _row_quantiles(data_ens, salem_cols)

    fig = go.Figure()
    _add_bands(fig, x, q)

    # if "salem_minflow" in data_ens.columns:
    #     fig.add_trace(go.Scatter(
    #         x=x, y=data_ens["salem_minflow"],
    #         mode="lines",
    #         line=dict(width=3, color="black"),
    #         name="Salem Min Flow"
    #     ))

    ensemble_trace_idxs = []
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
            visible=False,
            hovertemplate=f"{label}<br>%{{x|%Y-%m-%d}}<br>%{{y:.2f}}<extra></extra>",
        ))
        ensemble_trace_idxs.append(len(fig.data) - 1)

    fig.update_layout(
        title="Willamette River at Salem Flow (Bands + Ensembles)",
        xaxis_title="Date",
        yaxis_title="Flow (cfs)",
        hovermode="x unified",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=60, r=220, t=60, b=50),
    )

    _add_dropdown_show_all_none(fig, ensemble_trace_idxs)
    
    file_path = dated_folder / "SLMO_flow_ensemble.html"
    fig.write_html(file_path, include_plotlyjs="cdn")
    fig.show()