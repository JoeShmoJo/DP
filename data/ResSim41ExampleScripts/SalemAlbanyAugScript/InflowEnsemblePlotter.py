# rfc_reservoir_inflow_dashboard.py
import os
import numpy as np
import pandas as pd
import requests
from io import StringIO
from pathlib import Path
from typing import Dict, List, Tuple

import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ============================================================
# CONFIG
# ============================================================

BASE_URL_UNADJUSTED = "https://www.nwrfc.noaa.gov/chpsesp/ensemble/unadjusted/"
PATTERN_3I_QINE = "{site}3I_QINE.ESPF10.csv"

# Salem unregulated seasonal ranking source (natural)
BASE_URL_NATURAL = "https://www.nwrfc.noaa.gov/chpsesp/ensemble/natural/"
SALEM_SITE = "SLMO"
SALEM_PATTERN_NATURAL_UNREG = "{site}3N_SQIN.ESPF10.csv"

# Define seasonal window used ONLY for ranking at Salem
# Set these to match your seasonal volume definition.
SEASON_START = "2026-02-13"
SEASON_END   = "2026-06-30"

# Plotting position for percent rank:
#   "N_PLUS_1" => rank/(N+1) avoids exact 0% and 100%
#   "N"        => rank/N
PLOTTING_POSITION = "N_PLUS_1"

# Reservoir inflow site codes (RFC uses the O suffix)
RESERVOIR_SITES = {
    "DET": "DETO",
    "GPR": "GPRO",
    "BLU": "BLUO",
    "FAL": "FALO",
    "HCR": "HCRO",
    "FRN": "FRNO",
    "DOR": "DORO",
    "COT": "COTO",
}

# Output
OUT_DIR = Path(__file__).resolve().parent / "rfc_plots"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_HTML = OUT_DIR / "rfc_reservoir_inflow_dashboard.html"

# Optional: trim plotted period (leave as None to use all RFC rows)
PLOT_START = "2026-02-13"
PLOT_END   = "2026-11-30"

# Conversion: 1 CFS sustained for 1 day = 1.983471074 acre-feet
CFS_DAY_TO_ACREFT = 1.983471074

REQUEST_TIMEOUT = 30
DEBUG = True

# Start with locked axes? (you can toggle in the UI)
DEFAULT_AXES_LOCKED = True


# ============================================================
# RFC PARSER
# ============================================================

def parse_nwrfc_espf_csv_to_cfs(text: str) -> pd.DataFrame:
    """
    Returns DataFrame:
      index: tz-aware UTC timestamps
      columns: ensemble member years (int when possible)
      values: CFS (converted from KCFS)
    """
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

    # KCFS -> CFS
    df = df.apply(pd.to_numeric, errors="coerce") * 1000.0
    return df.round(2)


def download_site_espf10_unadjusted_3I_QINE(site_code: str, session: requests.Session) -> pd.DataFrame:
    url = BASE_URL_UNADJUSTED + PATTERN_3I_QINE.format(site=site_code)
    r = session.get(url, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return parse_nwrfc_espf_csv_to_cfs(r.text)


def download_salem_unreg_natural(session: requests.Session) -> pd.DataFrame:
    """
    Salem unregulated (natural) SQIN ensemble used for ranking
    """
    url = BASE_URL_NATURAL + SALEM_PATTERN_NATURAL_UNREG.format(site=SALEM_SITE)
    r = session.get(url, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return parse_nwrfc_espf_csv_to_cfs(r.text)

def apply_locked_x_ranges(fig, grid, plot_start=None, plot_end=None):
    """
    Lock x-axis range for all subplots if plot_start and plot_end are provided.
    """
    if plot_start is None or plot_end is None:
        return

    x0 = pd.to_datetime(plot_start)
    x1 = pd.to_datetime(plot_end)

    # 9 subplots => xaxis..xaxis9 in layout
    n_panels = len([c for row in grid for c in row])
    for i in range(1, n_panels + 1):
        k = "xaxis" if i == 1 else f"xaxis{i}"
        fig.update_layout(**{k: {"autorange": False, "range": [x0, x1]}})

# ============================================================
# TIME / DAILY AGGREGATION (mirrors your -6hr shift approach)
# ============================================================

def normalize_index_naive_utc_clock(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert tz-aware UTC index to tz-naive without shifting the clock.
    """
    df = df.copy()
    idx = pd.to_datetime(df.index, errors="coerce")
    if isinstance(idx, pd.DatetimeIndex) and idx.tz is not None:
        idx = idx.tz_localize(None)
    df.index = idx
    df = df[~df.index.isna()].sort_index()
    return df


def rfc_6h_to_daily_mean(df6: pd.DataFrame) -> pd.DataFrame:
    """
    RFC 6-hour values are typically at 06,12,18,00. Shift -6h -> 00,06,12,18 then resample daily mean,
    then shift +6h back.
    """
    df6 = normalize_index_naive_utc_clock(df6).apply(pd.to_numeric, errors="coerce")

    df_shift = df6.copy()
    df_shift.index = df_shift.index - pd.Timedelta(hours=6)

    df1d = df_shift.resample("1D").mean()

    df1d.index = df1d.index + pd.Timedelta(hours=6)
    df1d = df1d.dropna(how="all")
    return df1d


# ============================================================
# VOLUME COMPUTATION
# ============================================================

def daily_cfs_to_daily_acreft(df_cfs_1d: pd.DataFrame) -> pd.DataFrame:
    return df_cfs_1d * CFS_DAY_TO_ACREFT


def cumulative_acreft(df_acreft_per_day: pd.DataFrame) -> pd.DataFrame:
    return df_acreft_per_day.cumsum()


# ============================================================
# SALEM RANKING (percent rank of seasonal unreg volume)
# ============================================================

def seasonal_volume_af_by_member(df_daily_cfs: pd.DataFrame, season_start: str, season_end: str) -> pd.Series:
    """
    Daily mean CFS -> seasonal volume (acre-ft) by ensemble member.
    """
    s0 = pd.to_datetime(season_start)
    s1 = pd.to_datetime(season_end)

    df = df_daily_cfs.copy()
    df = df.loc[(df.index >= s0) & (df.index <= s1)].apply(pd.to_numeric, errors="coerce")

    df_af_day = df * CFS_DAY_TO_ACREFT
    vol_af = df_af_day.sum(axis=0, min_count=1)  # all-NaN stays NaN
    return vol_af


def build_member_rank_index(vol_af: pd.Series) -> pd.DataFrame:
    """
    Returns DataFrame with columns: member, vol_af, rank, pct
    Sorted ascending by vol_af (dry -> wet). Stable tie-break by member.
    """
    df = vol_af.dropna().to_frame("vol_af").reset_index().rename(columns={"index": "member"})
    df = df.sort_values(["vol_af", "member"], ascending=[True, True]).reset_index(drop=True)

    N = len(df)
    df["rank"] = np.arange(1, N + 1)

    if PLOTTING_POSITION == "N_PLUS_1":
        df["pct"] = (df["rank"] / (N + 1)) * 100.0
    else:
        df["pct"] = (df["rank"] / N) * 100.0

    return df


# ============================================================
# AXIS RANGE COMPUTATION + LOCK/UNLOCK UI SUPPORT
# ============================================================

def compute_panel_axis_ranges(
    daily_cfs: Dict[str, pd.DataFrame],
    cum_af: Dict[str, pd.DataFrame],
    grid: List[List[str]],
    plot_start=None,
    plot_end=None,
) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """
    Returns list length 9 (panels in row-major order):
      panel_ranges[i] = ( (0, max_cfs), (0, max_cum_af) )
    For empty panel, returns ((0,1),(0,1))
    """
    def trim(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        if plot_start is not None:
            df = df[df.index >= pd.to_datetime(plot_start)]
        if plot_end is not None:
            df = df[df.index <= pd.to_datetime(plot_end)]
        return df

    panel_ranges = []
    for res in [c for row in grid for c in row]:
        if res is None:
            panel_ranges.append(((0.0, 1.0), (0.0, 1.0)))
            continue

        df_d = trim(daily_cfs.get(res, pd.DataFrame()))
        df_c = trim(cum_af.get(res, pd.DataFrame()))

        max_cfs = 0.0
        max_af = 0.0

        if df_d is not None and not df_d.empty:
            arr = df_d.to_numpy(dtype=float)
            if arr.size:
                max_cfs = float(np.nanmax(arr))
                if not np.isfinite(max_cfs):
                    max_cfs = 0.0

        if df_c is not None and not df_c.empty:
            arr = df_c.to_numpy(dtype=float)
            if arr.size:
                max_af = float(np.nanmax(arr))
                if not np.isfinite(max_af):
                    max_af = 0.0

        # pad so line isn't glued to top
        max_cfs = max_cfs * 1.05 if max_cfs > 0 else 1.0
        max_af  = max_af  * 1.05 if max_af  > 0 else 1.0

        panel_ranges.append(((0.0, max_cfs), (0.0, max_af)))

    return panel_ranges


def build_axis_toggle_layout_updates(panel_ranges: List[Tuple[Tuple[float, float], Tuple[float, float]]]) -> Tuple[Dict, Dict]:
    """
    Create relayout update dicts for:
      - lock_layout_update: fixed ranges
      - auto_layout_update: autorange
    Assumes 9 panels and secondary y for each => 18 y-axes in layout.
    """
    lock_layout_update = {}
    auto_layout_update = {}

    axis_id = 1
    for i in range(9):
        cfs_rng, af_rng = panel_ranges[i]

        k1 = "yaxis" if axis_id == 1 else f"yaxis{axis_id}"
        lock_layout_update[k1] = {"autorange": False, "range": list(cfs_rng)}
        auto_layout_update[k1] = {"autorange": True, "range": None}
        axis_id += 1

        k2 = "yaxis" if axis_id == 1 else f"yaxis{axis_id}"
        lock_layout_update[k2] = {"autorange": False, "range": list(af_rng)}
        auto_layout_update[k2] = {"autorange": True, "range": None}
        axis_id += 1

    return lock_layout_update, auto_layout_update


# ============================================================
# DASHBOARD BUILD (indexed by Salem percent-rank label + axis lock toggle)
# ============================================================

def build_3x3_dashboard(
    daily_cfs: Dict[str, pd.DataFrame],
    cum_af: Dict[str, pd.DataFrame],
    out_html: Path,
    rank_index: List[Dict],
    plot_start=None,
    plot_end=None,
) -> None:
    """
    rank_index: list of dicts like:
      {"member": 1981, "pct": 12.3, "label": "12.3% (1981)"}
    """
    # 3x3 layout (9 panels). We have 8 reservoirs; last panel left blank.
    grid = [
        ["DET", "GPR", "BLU"],
        ["FAL", "HCR", "FRN"],
        ["DOR", "COT", None],
    ]

    fig = make_subplots(
        rows=3, cols=3,
        subplot_titles=[c if c is not None else "" for row in grid for c in row],
        specs=[[{"secondary_y": True}, {"secondary_y": True}, {"secondary_y": True}],
               [{"secondary_y": True}, {"secondary_y": True}, {"secondary_y": True}],
               [{"secondary_y": True}, {"secondary_y": True}, {"secondary_y": True}]],
        horizontal_spacing=0.06,
        vertical_spacing=0.10,
    )

    # Compute axis ranges + build toggle layout updates
    panel_ranges = compute_panel_axis_ranges(
        daily_cfs=daily_cfs,
        cum_af=cum_af,
        grid=grid,
        plot_start=plot_start,
        plot_end=plot_end,
    )
    lock_layout_update, auto_layout_update = build_axis_toggle_layout_updates(panel_ranges)
    apply_locked_x_ranges(fig, grid, plot_start=plot_start, plot_end=plot_end)
    def rc(i: int) -> Tuple[int, int]:
        return (i // 3 + 1, i % 3 + 1)

    def trim(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        if plot_start is not None:
            df = df[df.index >= pd.to_datetime(plot_start)]
        if plot_end is not None:
            df = df[df.index <= pd.to_datetime(plot_end)]
        return df

    # Trace metadata: (member, reservoir, kind)
    trace_meta: List[Tuple[int, str, str]] = []

    if not rank_index:
        raise RuntimeError("rank_index is empty. Salem ranking failed or seasonal window produced no data.")

    default_member = int(rank_index[0]["member"])
    default_label = str(rank_index[0]["label"])

    for item in rank_index:
        member = int(item["member"])

        for panel_idx, res in enumerate([c for row in grid for c in row]):
            row, col = rc(panel_idx)

            if res is None:
                fig.add_trace(go.Scatter(x=[], y=[], name="", showlegend=False, visible=False),
                              row=row, col=col, secondary_y=False)
                trace_meta.append((member, "EMPTY", "daily"))

                fig.add_trace(go.Scatter(x=[], y=[], name="", showlegend=False, visible=False),
                              row=row, col=col, secondary_y=True)
                trace_meta.append((member, "EMPTY", "cum"))
                continue

            df_d = trim(daily_cfs.get(res, pd.DataFrame()))
            df_c = trim(cum_af.get(res, pd.DataFrame()))

            if df_d is None or df_d.empty or member not in df_d.columns:
                x_daily, y_daily = [], []
            else:
                s = df_d[member]
                x_daily = s.index
                y_daily = s.values

            if df_c is None or df_c.empty or member not in df_c.columns:
                x_cum, y_cum = [], []
            else:
                s = df_c[member]
                x_cum = s.index
                y_cum = s.values

            visible_default = (member == default_member)

            fig.add_trace(
                go.Scatter(
                    x=x_daily,
                    y=y_daily,
                    mode="lines",
                    name=f"{res} Daily (CFS)",
                    showlegend=False,
                    visible=visible_default,
                ),
                row=row, col=col, secondary_y=False
            )
            trace_meta.append((member, res, "daily"))

            fig.add_trace(
                go.Scatter(
                    x=x_cum,
                    y=y_cum,
                    mode="lines",
                    name=f"{res} Cum (AF)",
                    showlegend=False,
                    visible=visible_default,
                ),
                row=row, col=col, secondary_y=True
            )
            trace_meta.append((member, res, "cum"))

    # Axis labels
    for i in range(9):
        row, col = rc(i)
        fig.update_yaxes(title_text="CFS", row=row, col=col, secondary_y=False)
        fig.update_yaxes(title_text="Acre-ft (cum)", row=row, col=col, secondary_y=True)

    fig.update_xaxes(title_text="Date", row=3, col=1)
    fig.update_xaxes(title_text="Date", row=3, col=2)
    fig.update_xaxes(title_text="Date", row=3, col=3)

    def visibility_for_member(target_member) -> List[bool]:
        return [(m == target_member) for (m, _res, _k) in trace_meta]

    # Dropdown / slider labels are percent-rank + year
    dropdown_buttons = []
    slider_steps = []

    for item in rank_index:
        member = int(item["member"])
        label = str(item["label"])

        dropdown_buttons.append(
            dict(
                label=label,
                method="update",
                args=[
                    {"visible": visibility_for_member(member)},
                    {"title": f"RFC Reservoir Inflow — Ranked by Salem Seasonal Unreg Volume: {label}"}
                ],
            )
        )

        slider_steps.append(
            dict(
                method="update",
                label=label,
                args=[
                    {"visible": visibility_for_member(member)},
                    {"title": f"RFC Reservoir Inflow — Ranked by Salem Seasonal Unreg Volume: {label}"}
                ],
            )
        )

    # Apply default axis mode
    if DEFAULT_AXES_LOCKED:
        fig.update_layout(**lock_layout_update)
        axis_button_active = 1  # second button
    else:
        fig.update_layout(**auto_layout_update)
        axis_button_active = 0  # first button

    fig.update_layout(
        title=f"RFC Reservoir Inflow — Ranked by Salem Seasonal Unreg Volume: {default_label}",
        height=1050,
        width=1500,
        margin=dict(l=40, r=40, t=80, b=40),
        updatemenus=[
            # (1) Ensemble selector (ranked)
            dict(
                type="dropdown",
                x=0.01, y=1.08,
                xanchor="left", yanchor="top",
                buttons=dropdown_buttons,
                direction="down",
            ),
            # (2) Axis scale toggle (Auto vs Locked)
            dict(
                type="buttons",
                x=0.01, y=1.02,
                xanchor="left", yanchor="top",
                direction="right",
                showactive=True,
                active=axis_button_active,
                buttons=[
                    dict(
                        label="Axes: Auto",
                        method="relayout",
                        args=[auto_layout_update],
                    ),
                    dict(
                        label="Axes: Locked",
                        method="relayout",
                        args=[lock_layout_update],
                    ),
                ],
            ),
        ],
        sliders=[
            dict(
                x=0.20, y=1.06,
                len=0.78,
                xanchor="left", yanchor="top",
                steps=slider_steps,
                active=0,
            )
        ],
    )

    out_html.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out_html), include_plotlyjs="cdn")
    if DEBUG:
        print(f"[OK] Wrote dashboard: {out_html}")


# ============================================================
# MAIN
# ============================================================

def main():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    daily_cfs: Dict[str, pd.DataFrame] = {}
    daily_af: Dict[str, pd.DataFrame] = {}
    cum_af: Dict[str, pd.DataFrame] = {}

    misses: List[Tuple[str, str]] = []

    # ---------------------------
    # 1) Download reservoir inflows
    # ---------------------------
    for res, site_code in RESERVOIR_SITES.items():
        try:
            if DEBUG:
                print(f"[DL] {res} <- {site_code}")
            df6 = download_site_espf10_unadjusted_3I_QINE(site_code, session)

            df1d_cfs = rfc_6h_to_daily_mean(df6)
            daily_cfs[res] = df1d_cfs

            df1d_af = daily_cfs_to_daily_acreft(df1d_cfs)
            daily_af[res] = df1d_af

            cum_af[res] = cumulative_acreft(df1d_af)

            if DEBUG:
                print(f"[OK] {res}: 6h {df6.shape} -> 1d {df1d_cfs.shape} members={df1d_cfs.shape[1]}")

        except Exception as e:
            misses.append((res, str(e)))
            if DEBUG:
                print(f"[MISS] {res}: {e}")

    if misses:
        print("\n--- Reservoir download/process misses ---")
        for res, reason in misses:
            print(f"  {res}: {reason}")

    # Ensure all reservoirs exist (even empty) so plot builder doesn't crash
    for res in RESERVOIR_SITES.keys():
        if res not in daily_cfs:
            daily_cfs[res] = pd.DataFrame()
            cum_af[res] = pd.DataFrame()

    # ---------------------------
    # 2) Build Salem unreg seasonal volume ranking
    # ---------------------------
    if DEBUG:
        print(f"[DL] Salem unreg ranking <- {SALEM_SITE} (natural)")

    salem6 = download_salem_unreg_natural(session)
    salem1d = rfc_6h_to_daily_mean(salem6)

    salem_vol_af = seasonal_volume_af_by_member(salem1d, SEASON_START, SEASON_END)
    rank_df = build_member_rank_index(salem_vol_af)

    rank_index: List[Dict] = []
    for _, r in rank_df.iterrows():
        member = int(r["member"])
        pct = float(r["pct"])
        rank_index.append({"member": member, "pct": pct, "label": f"{pct:0.1f}% ({member})"})

    if DEBUG:
        print(f"[OK] Salem ranking members: {len(rank_index)}  (season {SEASON_START} to {SEASON_END})")
        for item in rank_index[:5]:
            print(f"  {item['label']}")

    # ---------------------------
    # 3) Build dashboard indexed by percent-rank label
    # ---------------------------
    build_3x3_dashboard(
        daily_cfs=daily_cfs,
        cum_af=cum_af,
        out_html=OUT_HTML,
        rank_index=rank_index,
        plot_start=PLOT_START,
        plot_end=PLOT_END,
    )


if __name__ == "__main__":
    main()
