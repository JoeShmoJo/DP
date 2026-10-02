"""Time series of a run, as CSV: one file per control point and per reservoir."""
import os

import pandas as pd

from .plots import safe_name


def write_timeseries(ts_dir, jp, cps, reservoirs, run_obs, run_unreg, elevations):
    cp_dir = os.path.join(ts_dir, "ControlPoints")
    rv_dir = os.path.join(ts_dir, "Reservoirs")
    os.makedirs(cp_dir, exist_ok=True)
    os.makedirs(rv_dir, exist_ok=True)
    for i, cp in enumerate(cps, 1):
        p = jp[cp]
        cols = {"Unregulated (cfs)": p.series["UNREGULATED"], "Regulated modeled (cfs)": p.series["MODELED OBSERVED"]}
        if "OBSERVED" in p.series:
            cols["Regulated gage (cfs)"] = p.series["OBSERVED"]
        for label in sorted(k for k in p.series if k.startswith("WITHOUT ") or k.startswith("WITH ONLY ")):
            cols[label + " (cfs)"] = p.series[label]
        df = pd.DataFrame(cols)
        df.index.name = "time"
        df.round(1).to_csv(os.path.join(cp_dir, f"{i:02d}_{safe_name(cp)}.csv"))
    for i, r in enumerate(reservoirs, 1):
        df = pd.DataFrame({"Inflow (cfs)": run_obs.inflow[r],
                           "Regulated outflow, observed (cfs)": run_obs.outflow[r],
                           "Unregulated inflow (cfs)": run_unreg.inflow[r],
                           "Unregulated outflow (cfs)": run_unreg.outflow[r]})
        if elevations.get(r) is not None:
            df["Pool elevation, observed (ft)"] = elevations[r]
        df.index.name = "time"
        df.round(2).to_csv(os.path.join(rv_dir, f"{i:02d}_{safe_name(r)}.csv"))
    return cp_dir, rv_dir
