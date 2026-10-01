import os
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from pydsstools.heclib.dss import HecDss

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import RunControlConfig as cfg
import plotly.io as pio
pio.renderers.default = "browser"


# ============================================================
# USER CONFIG
# ============================================================

# Ranking season window (used ONLY to rank ensembles by Salem unreg volume)
SEASON_START = "2026-02-13"
SEASON_END   = "2026-11-30"

# X-axis lock window (for dashboard viewing). Set both to lock; leave None for auto.
PLOT_START = "2026-02-13"
PLOT_END   = "2026-11-30"

# Default lock states
DEFAULT_Y_LOCKED = True
DEFAULT_X_LOCKED = True

DEBUG = True


# ============================================================
# MAPS / PATH BUILDERS (same as your working script)
# ============================================================

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

def with_fpart_suffix(d: Dict[str, str], fpart: str) -> Dict[str, str]:
    """Make alias keys unique per ensemble member so dict.update doesn't overwrite."""
    return {f"{k}__{fpart}": v for k, v in d.items()}

def create_elev_paths(fpart: str) -> Dict[str, str]:
    # IMPORTANT: keep exactly 1DAY and DO NOT append C0
    return {f"{s}_elev": f"//{l}-POOL/ELEV//1DAY/{fpart}/" for s, l in RESERVOIR_NAME_MAP.items()}

def create_rcelev_paths(fpart: str) -> Dict[str, str]:
    # IMPORTANT: rule curve read once; F-part should match what exists (use same style as elev)
    return {f"{s}_rcElev": f"//{l}-RULE CURVE/ELEV-ZONE//1DAY/{fpart}/" for s, l in RESERVOIR_NAME_MAP.items()}


# ============================================================
# DSS IO (same style; minimal guard to avoid ts.pytimes=None crash)
# ============================================================

def readallpaths(dss_file, path_dict):
    """Read multiple DSS paths into a single dataframe (columns=aliases)."""
    fid = HecDss.Open(os.fspath(dss_file))
    dflist = []

    for alias, path in path_dict.items():
        try:
            ts = fid.read_ts(path, trim_missing=True)

            # Minimal guard: pydsstools can return pytimes=None if trimmed-to-empty
            if ts is None or ts.pytimes is None or ts.values is None:
                continue

            df = pd.DataFrame(ts.values, columns=[alias], index=np.array(ts.pytimes))
            dflist.append(df.copy())

        except Exception as e:
            msg = f"[DSS] Failed '{alias}' -> {path} in {os.path.basename(os.fspath(dss_file))}: {e}"
            print(msg)

    fid.close()

    if not dflist:
        return pd.DataFrame()

    data = pd.concat(dflist, axis=1)
    data.index = pd.to_datetime(data.index, errors="coerce")
    data = data[~data.index.isna()]
    data = data[~data.index.duplicated(keep="last")]
    return data.sort_index()


# ============================================================
# PATHS (forecast.dss) (same as your working script)
# ============================================================

def get_forecast_dss_path() -> str:
    SIM_NAME = cfg.SIM_NAME
    WATERSHED_DIR = Path(__file__).resolve().parent.parent.parent
    sim_dir = SIM_NAME.replace(" ", "_")
    watershed_name = WATERSHED_DIR.name

    forecast_dss_path = (
        WATERSHED_DIR.parents[1]  # C:/CWMS
        / "forecast"
        / sim_dir
        / watershed_name
        / "forecast.dss"
    )
    return str(forecast_dss_path)


# ============================================================
# RANKING (match working script approach; keep season slice)
# ============================================================

def fpart_to_year(fp: str) -> int:
    # Works for "C:001981|" and "C:001981|C0" (we won't use C0 though)
    s = fp.replace("C0", "")
    return int(s.split(":")[1].split("|")[0])

def build_rank_from_salem_unreg(dss_file: str, years: List[int]) -> pd.DataFrame:
    """
    Reads Salem unreg per inputs-style fpart:
      //SLMO3/FLOW-UNREG//1Day/C:00YYYY|/
    Slices SEASON_START..SEASON_END, sums, ranks by percentile.
    Returns fp_in + pct + year + label.
    """
    fp_in_list = [f"C:00{y}|" for y in years]

    salem_unreg_data = pd.DataFrame()
    for fp_in in fp_in_list:
        part = readallpaths(dss_file, {"SLM_unreg": f"//SLMO3/FLOW-UNREG//1Day/{fp_in}/"})
        if not part.empty and "SLM_unreg" in part.columns:
            salem_unreg_data[fp_in] = pd.to_numeric(part["SLM_unreg"], errors="coerce")
        else:
            salem_unreg_data[fp_in] = np.nan

    # seasonal slice
    s0 = pd.to_datetime(SEASON_START)
    s1 = pd.to_datetime(SEASON_END)
    salem_unreg_data = salem_unreg_data.loc[
        (salem_unreg_data.index >= s0) & (salem_unreg_data.index <= s1)
    ].copy()

    # Rank by summed seasonal flow (same spirit as your working script)
    salem_unreg_sum = salem_unreg_data.sum(axis=0, skipna=True)
    salem_unreg_sum_sorted = salem_unreg_sum.sort_values()
    salem_unreg_percentiles = salem_unreg_sum_sorted.rank(pct=True) * 100.0

    rank_df = pd.DataFrame({
        "fp": salem_unreg_percentiles.index,     # <-- THIS is what we will use for ELEV reads
        "pct": salem_unreg_percentiles.values,
    })

    rank_df["year"] = rank_df["fp"].apply(fpart_to_year)
    rank_df["label"] = rank_df.apply(lambda r: f"P{r['pct']:.1f} ({int(r['year'])})", axis=1)

    # dry -> wet
    rank_df = rank_df.sort_values(["pct", "year"], ascending=[True, True]).reset_index(drop=True)
    return rank_df


# ============================================================
# DASHBOARD (4x3, elevations only; member selector)
# ============================================================

def _axis_updates_y(panel_yminmax: List[Tuple[float, float]]) -> Tuple[Dict, Dict]:
    lock = {}
    auto = {}
    for i in range(1, 13):
        k = "yaxis" if i == 1 else f"yaxis{i}"
        ymin, ymax = panel_yminmax[i - 1]
        if not np.isfinite(ymin): ymin = 0.0
        if not np.isfinite(ymax) or ymax <= ymin: ymax = ymin + 1.0
        lock[k] = {"autorange": False, "range": [float(ymin), float(ymax)]}
        auto[k] = {"autorange": True, "range": None}
    return lock, auto

def _axis_updates_x(x0, x1) -> Tuple[Dict, Dict]:
    lock = {}
    auto = {}
    for i in range(1, 13):
        k = "xaxis" if i == 1 else f"xaxis{i}"
        auto[k] = {"autorange": True, "range": None}
        if x0 is not None and x1 is not None:
            lock[k] = {"autorange": False, "range": [pd.to_datetime(x0).isoformat(), pd.to_datetime(x1).isoformat()]}
        else:
            lock[k] = {"autorange": True, "range": None}
    return lock, auto

def build_4x3_dashboard_elev_only(
    data: pd.DataFrame,
    rank_df: pd.DataFrame,
    out_html: Path,
    plot_start=None,
    plot_end=None,
    default_y_locked=True,
    default_x_locked=True,
) -> None:

    grid = [
        ["LOP", "DET", "GPR"],
        ["CGR", "BLU", "FAL"],
        ["HCR", "DOR", "COT"],
        ["FRN", "FOS", None],
    ]
    panels = [c for row in grid for c in row]

    fig = make_subplots(
        rows=4, cols=3,
        subplot_titles=[(f"{k} — {RESERVOIR_NAME_MAP[k]}" if k else "") for k in panels],
        horizontal_spacing=0.06,
        vertical_spacing=0.08,
    )

    def rc(i: int) -> Tuple[int, int]:
        return (i // 3 + 1, i % 3 + 1)

    df = data.copy()
    df.index = pd.to_datetime(df.index, errors="coerce")
    df = df[~df.index.isna()].sort_index()

    if plot_start is not None:
        df = df[df.index >= pd.to_datetime(plot_start)]
    if plot_end is not None:
        df = df[df.index <= pd.to_datetime(plot_end)]

    x = df.index
    fparts = rank_df["fp"].tolist()

    # y-limits per panel across ALL members + rule curve
    panel_yminmax: List[Tuple[float, float]] = []
    for res in panels:
        if res is None:
            panel_yminmax.append((0.0, 1.0))
            continue

        cols = [f"{res}_elev__{fp}" for fp in fparts if f"{res}_elev__{fp}" in df.columns]
        yvals = []

        if cols:
            arr = df[cols].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
            if arr.size:
                yvals.append(np.nanmin(arr))
                yvals.append(np.nanmax(arr))

        rc_col = f"{res}_rcElev"
        if rc_col in df.columns:
            rc_arr = pd.to_numeric(df[rc_col], errors="coerce").to_numpy(dtype=float)
            if rc_arr.size:
                yvals.append(np.nanmin(rc_arr))
                yvals.append(np.nanmax(rc_arr))

        if yvals:
            ymin = float(np.nanmin(yvals))
            ymax = float(np.nanmax(yvals))
            pad = (ymax - ymin) * 0.02 if ymax > ymin else 1.0
            panel_yminmax.append((ymin - pad, ymax + pad))
        else:
            panel_yminmax.append((0.0, 1.0))

    y_lock_update, y_auto_update = _axis_updates_y(panel_yminmax)
    x_lock_update, x_auto_update = _axis_updates_x(plot_start, plot_end)

    # rule curves always visible
    for i, res in enumerate(panels):
        if res is None:
            continue
        row, col = rc(i)
        rc_col = f"{res}_rcElev"
        if rc_col in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=pd.to_numeric(df[rc_col], errors="coerce"),
                    mode="lines",
                    line=dict(width=3, color="black"),
                    name=f"{res} Rule Curve",
                    showlegend=False,
                    hovertemplate=f"{res} Rule Curve<br>%{{x|%Y-%m-%d}}<br>%{{y:.2f}}<extra></extra>",
                ),
                row=row, col=col
            )

    base_trace_count = len(fig.data)

    # member traces (one per panel per member)
    trace_meta: List[int] = []

    for member_idx, r in rank_df.iterrows():
        fp = r["fp"]           # <-- THIS IS THE WHOLE FIX (no C0)
        label = r["label"]

        for i, res in enumerate(panels):
            row, col = rc(i)

            if res is None:
                fig.add_trace(go.Scatter(x=[], y=[], showlegend=False, visible=False), row=row, col=col)
                trace_meta.append(member_idx)
                continue

            colname = f"{res}_elev__{fp}"
            if colname in df.columns:
                y = pd.to_numeric(df[colname], errors="coerce")
            else:
                y = pd.Series(index=x, data=np.nan)

            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=y,
                    mode="lines",
                    line=dict(width=1),
                    showlegend=False,
                    visible=(member_idx == 0),
                    hovertemplate=f"{res} {label}<br>%{{x|%Y-%m-%d}}<br>%{{y:.2f}}<extra></extra>",
                ),
                row=row, col=col
            )
            trace_meta.append(member_idx)

    # y-axis titles
    for i in range(12):
        row, col = rc(i)
        fig.update_yaxes(title_text="Elevation (ft)", row=row, col=col)

    member_trace_count = len(fig.data) - base_trace_count

    def vis_mask(member_idx: int) -> List[bool]:
        vis = [True] * base_trace_count
        for j in range(member_trace_count):
            vis.append(trace_meta[j] == member_idx)
        return vis

    # dropdown + slider
    dropdown_buttons = []
    slider_steps = []
    for member_idx, r in rank_df.iterrows():
        label = r["label"]
        dropdown_buttons.append(
            dict(
                label=label,
                method="update",
                args=[
                    {"visible": vis_mask(member_idx)},
                    {"title": f"Simulation Reservoir Elevations (4×3) — Ranked by Salem Seasonal Unreg Volume: {label}"},
                ],
            )
        )
        slider_steps.append(
            dict(
                method="update",
                label=label,
                args=[
                    {"visible": vis_mask(member_idx)},
                    {"title": f"Simulation Reservoir Elevations (4×3) — Ranked by Salem Seasonal Unreg Volume: {label}"},
                ],
            )
        )

    # apply default locks
    if default_y_locked:
        fig.update_layout(**y_lock_update)
        y_active = 1
    else:
        fig.update_layout(**y_auto_update)
        y_active = 0

    if default_x_locked:
        fig.update_layout(**x_lock_update)
        x_active = 1
    else:
        fig.update_layout(**x_auto_update)
        x_active = 0

    fig.update_layout(
        title=f"Simulation Reservoir Elevations (4×3) — Ranked by Salem Seasonal Unreg Volume: {rank_df.iloc[0]['label']}",
        height=1200,
        width=1500,
        margin=dict(l=40, r=40, t=105, b=40),
        hovermode="x unified",
        updatemenus=[
            # member selector
            dict(
                type="dropdown",
                x=0.01, y=1.11,
                xanchor="left", yanchor="top",
                buttons=dropdown_buttons,
                direction="down",
            ),
            # Y lock toggle
            dict(
                type="buttons",
                x=0.01, y=1.045,
                xanchor="left", yanchor="top",
                direction="right",
                showactive=True,
                active=y_active,
                buttons=[
                    dict(label="Y: Auto",   method="relayout", args=[y_auto_update]),
                    dict(label="Y: Locked", method="relayout", args=[y_lock_update]),
                ],
            ),
            # X lock toggle
            dict(
                type="buttons",
                x=0.20, y=1.045,
                xanchor="left", yanchor="top",
                direction="right",
                showactive=True,
                active=x_active,
                buttons=[
                    dict(label="X: Auto",   method="relayout", args=[x_auto_update]),
                    dict(label="X: Locked", method="relayout", args=[x_lock_update]),
                ],
            ),
        ],
        sliders=[
            dict(
                x=0.01, y=1.02,
                len=0.97,
                xanchor="left", yanchor="top",
                steps=slider_steps,
                active=0,
            )
        ],
    )

    out_html.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out_html), include_plotlyjs="cdn")
    if DEBUG:
        print(f"[OK] Wrote elevation dashboard: {out_html}")


# ============================================================
# MAIN
# ============================================================

def main():
    dss_file = get_forecast_dss_path()
    if DEBUG:
        print(f"[DSS] Reading: {dss_file}")

    years = list(range(1981, 2025))

    # 1) rank ensembles
    rank_df = build_rank_from_salem_unreg(dss_file, years)
    if rank_df.empty:
        raise RuntimeError("Ranking dataframe is empty. Check SLMO3 FLOW-UNREG paths and season window.")

    if DEBUG:
        print(f"[RANK] Members ranked: {len(rank_df)}  Season: {SEASON_START} -> {SEASON_END}")
        print(rank_df.head(5)[['label', 'pct']])

    # 2) build path_dict: ALL elev members + ONE rule curve read (NO C0 ANYWHERE)
    path_dict: Dict[str, str] = {}

    for fp in rank_df["fp"].tolist():
        path_dict.update(with_fpart_suffix(create_elev_paths(fp), fp))

    rc_fpart = rank_df["fp"].iloc[0]
    path_dict.update(create_rcelev_paths(rc_fpart))

    data = readallpaths(dss_file, path_dict)
    if data.empty:
        raise RuntimeError("No simulation elevation data read from DSS. Check pathname patterns and DSS file.")

    # 3) output location (same as your working script)
    WATERSHED_DIR = Path(__file__).resolve().parent.parent.parent
    plotly_output_dir = WATERSHED_DIR / "output_plots" / "plotly_html"
    plotly_output_dir.mkdir(parents=True, exist_ok=True)

    out_html = plotly_output_dir / "SIM_ELEV_4x3_ranked_by_SalemUnreg.html"

    build_4x3_dashboard_elev_only(
        data=data,
        rank_df=rank_df,
        out_html=out_html,
        plot_start=PLOT_START,
        plot_end=PLOT_END,
        default_y_locked=DEFAULT_Y_LOCKED,
        default_x_locked=DEFAULT_X_LOCKED,
    )

if __name__ == "__main__":
    main()
