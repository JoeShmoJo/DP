"""
Plots of every control point and reservoir for a run.

Control points: unregulated flow (Unregulated run), regulated flow (the gage
where there is one, else the Observed run) and the modeled regulated flow,
over the whole period and zoomed on the unregulated peak, with the peak
reduction in the title.

Reservoirs: the unregulated flow (inflow passed through), the regulated
outflow (the observed release, hourly and daily mean, since power peaking
makes the hourly release hard to read) and the observed pool elevation.

Hours that were missing in obsData.dss and filled by straight-line
interpolation are shaded: orange where the plotted record itself was filled,
grey where a record the modeled flows are built from (upstream gages,
reservoir inflows and releases, locals) was filled at that hour (not lagged
for routing). In the whole-period panels short gaps are drawn at least about
a day wide so they can be seen.
"""
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from .model import r100

COLORS = {"unreg": "#c0392b", "reg": "#1f4e9a", "modeled": "#7fa7d9", "inflow": "#7f7f7f", "elev": "#2e7d32"}
ZOOM_DAYS = 7
FILLED = {"own": ("#f39c12", 0.30), "inputs": ("#8c8c8c", 0.28)}


def safe_name(text):
    return re.sub(r"[^A-Za-z0-9_.+-]+", "_", text).strip("_")


def _style(ax, ylabel):
    ax.set_ylabel(ylabel)
    ax.grid(True, color="#dddddd", linewidth=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d%b\n%Y"))


def _flow_lines(ax, series, zoom=None):
    for label, s, color, kw in series:
        if s is None:
            continue
        if zoom is not None:
            s = s[zoom[0]:zoom[1]]
        ax.plot(s.index, s.values, color=color, label=label, **kw)


def _runs(mask):
    """(first, last) timestamps of each run of True hours"""
    m = mask.fillna(False).astype(bool).values
    idx = mask.index
    out = []
    i, n = 0, len(m)
    while i < n:
        if m[i]:
            j = i
            while j + 1 < n and m[j + 1]:
                j += 1
            out.append((idx[i], idx[j]))
            i = j + 1
        else:
            i += 1
    return out


def _shade(ax, mask, kind, label, zoom=None):
    """Shade the filled hours of mask (bool Series) on ax; returns True if anything was drawn"""
    if mask is None:
        return False
    if zoom is not None:
        mask = mask[zoom[0]:zoom[1]]
    runs = _runs(mask)
    if not runs:
        return False
    color, alpha = FILLED[kind]
    half = _hours(0.5)
    min_w = _days(1) if zoom is None else _hours(1)
    hours = int(mask.sum())
    for k, (a, b) in enumerate(runs):
        a, b = a - half, b + half
        if b - a < min_w:
            mid = a + (b - a) / 2
            a, b = mid - min_w / 2, mid + min_w / 2
        ax.axvspan(a, b, color=color, alpha=alpha, linewidth=0, zorder=0,
                   label=f"{label} ({hours:,} h)" if k == 0 else "_nolegend_")
    return True


def _only(mask, other):
    """mask without the hours already in other"""
    if mask is None or other is None:
        return mask
    out = mask & ~other.reindex(mask.index, fill_value=False)
    return out if out.any() else None


def control_point(png, name, jp, period_label):
    """jp: a model.JuncPeaks"""
    unreg = jp.series["UNREGULATED"]
    modeled = jp.series["MODELED OBSERVED"]
    gage = jp.series.get("OBSERVED")
    series = [("Unregulated", unreg, COLORS["unreg"], {"linewidth": 1.2}),
              ("Regulated (gage)" if gage is not None else None, gage, COLORS["reg"], {"linewidth": 1.4}),
              ("Regulated (modeled)", modeled, COLORS["modeled"] if gage is not None else COLORS["reg"],
               {"linewidth": 1.0, "linestyle": "--" if gage is not None else "-"})]
    unreg_pk, t_pk = jp.unreg
    reg_pk = jp.obs[0] if jp.is_gaged else jp.modeled_obs[0]
    reduction = r100(unreg_pk) - r100(reg_pk)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7.5), gridspec_kw={"height_ratios": [1, 1]})
    filled_gage = jp.filled_gage
    filled_inputs = _only(jp.filled_inputs, filled_gage)
    shades = [(filled_gage, "own", "Filled: gage record"),
              (filled_inputs, "inputs", "Filled: records the modeled flows use")]
    for mask, kind, label in shades:
        _shade(ax1, mask, kind, label)
    _flow_lines(ax1, series)
    _style(ax1, "Flow (cfs)")
    ax1.set_title(f"{name}  |  {period_label}\n"
                  f"Unregulated peak {r100(unreg_pk):,.0f} cfs, regulated peak {r100(reg_pk):,.0f} cfs, "
                  f"reduction {reduction:,.0f} cfs", fontsize=11)
    ax1.legend(loc="upper right", frameon=False, fontsize=9)
    zoom = (t_pk - _days(ZOOM_DAYS), t_pk + _days(ZOOM_DAYS))
    zoom_shaded = any([_shade(ax2, mask, kind, label, zoom) for mask, kind, label in shades])
    _flow_lines(ax2, series, zoom)
    if zoom_shaded:
        ax2.legend(loc="upper right", frameon=False, fontsize=8)
    ax2.axvline(t_pk, color=COLORS["unreg"], linewidth=0.6, linestyle=":")
    _style(ax2, "Flow (cfs)")
    ax2.set_title(f"Around the unregulated peak ({t_pk:%d%b%Y %H:%M})", fontsize=10)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%d%b"))
    fig.tight_layout()
    fig.savefig(png, dpi=110)
    plt.close(fig)


def reservoir(png, name, inflow, outflow, unreg_outflow, elevation, period_label, filled=None):
    """
    Unregulated flow (inflow passed through), regulated outflow (observed; hourly + daily mean), pool elevation.
    filled: {"release", "inflow", "elevation"} -> bool Series of filled hours (or None)
    """
    filled = filled or {}
    has_elev = elevation is not None and elevation.notna().any()
    fig, axes = plt.subplots(2 if has_elev else 1, 1, figsize=(11, 7.5 if has_elev else 4.5), sharex=True)
    ax1 = axes[0] if has_elev else axes
    _shade(ax1, filled.get("release"), "own", "Filled: release record")
    _shade(ax1, _only(filled.get("inflow"), filled.get("release")), "inputs", "Filled: records the inflow is built from")
    ax1.plot(outflow.index, outflow.values, color=COLORS["modeled"], linewidth=0.5, alpha=0.7,
             label="Regulated outflow, hourly (observed)")
    daily = outflow.resample("D").mean()
    ax1.plot(daily.index + _days(0.5), daily.values, color=COLORS["reg"], linewidth=1.4,
             label="Regulated outflow, daily mean")
    ax1.plot(unreg_outflow.index, unreg_outflow.values, color=COLORS["unreg"], linewidth=1.0,
             label="Unregulated flow (inflow passed through)")
    _style(ax1, "Flow (cfs)")
    i_pk = inflow.idxmax()
    ax1.set_title(f"{name}  |  {period_label}\nPeak unregulated flow {r100(unreg_outflow.max()):,.0f} cfs, "
                  f"peak inflow as regulated {r100(inflow.max()):,.0f} cfs ({i_pk:%d%b%Y %H:%M}), "
                  f"peak regulated daily-mean outflow {r100(daily.max()):,.0f} cfs", fontsize=10.5)
    ax1.legend(loc="upper right", frameon=False, fontsize=9)
    if has_elev:
        ax2 = axes[1]
        _shade(ax2, filled.get("elevation"), "own", "Filled: elevation record")
        ax2.plot(elevation.index, elevation.values, color=COLORS["elev"], linewidth=1.2, label="Regulated pool elevation (observed)")
        _style(ax2, "Elevation (ft)")
        ax2.legend(loc="upper right", frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(png, dpi=110)
    plt.close(fig)


def _days(n):
    return pd.Timedelta(days=n)


def _hours(n):
    return pd.Timedelta(hours=n)


def make_all(plot_dir, jp, cps, reservoirs, run_obs, run_unreg, elevations, period_label, log=print, filled=None):
    """filled: reservoir -> {"release", "inflow", "elevation"} filled-hour masks (control points carry theirs in jp)"""
    filled = filled or {}
    cp_dir = os.path.join(plot_dir, "ControlPoints")
    rv_dir = os.path.join(plot_dir, "Reservoirs")
    os.makedirs(cp_dir, exist_ok=True)
    os.makedirs(rv_dir, exist_ok=True)
    for i, cp in enumerate(cps, 1):
        control_point(os.path.join(cp_dir, f"{i:02d}_{safe_name(cp)}.png"), cp, jp[cp], period_label)
    for i, r in enumerate(reservoirs, 1):
        reservoir(os.path.join(rv_dir, f"{i:02d}_{safe_name(r)}.png"), r, run_obs.inflow[r], run_obs.outflow[r],
                  run_unreg.outflow[r], elevations.get(r), period_label, filled.get(r))
    log(f"   {len(cps)} control point and {len(reservoirs)} reservoir plots")
    return cp_dir, rv_dir
