# -*- coding: utf-8 -*-
"""
STEP 2 - Damages Prevented: from the edited obsData.dss to the flow reductions,
the dollars, and plots.

    python src/2_run_damages_prevented.py

Settings come from config/config.ini. It reads
output/WY<year>/2_edited_data/obsData.dss (or [paths] obsdata_dss) and writes
output/WY<year>/3_damages_prevented/, replacing what the last run wrote there,
so you can edit the data and rerun as often as you like:

  Results/       CP_Peaks, Preliminary_per_project, Mini-Simulations, Resv_Peaks (CSV)
  Damages/       damages_prevented.csv, damages_prevented_ByProject.csv
  Plots/         ControlPoints/ and Reservoirs/ (PNG); filled hours are shaded
  TimeSeries/    every series behind the results (CSV per control point / reservoir)
  obsData_records_used.csv   every record read from obsData.dss, and its filled hours
  run_log.txt    everything printed during the run
  config_used.ini

and adds a line to output/WY<year>/run_history.csv (time, total damages
prevented, hours filled) so you can see how each round of edits moved the result.

What it does (the same steps as the ResSim Damages Prevented menu):
  1. Transformed locals (Willamette Falls = 1.5 x Pudding R at Aurora)
  2. Water-balance locals for the Observed alternative
  3. Observed run (each reservoir releases its observed outflow) and
     Unregulated run (each reservoir passes inflow), routed through the network
     exported from ResSim (config/network/network.json)
  4. Mini-simulations with and without each reservoir, and the reductions
  5. Damages prevented in dollars (modules/damages/calculate_damages.py)
  6. Plots and time series
"""
import contextlib
import datetime
import io
import os
import re
import shutil
import sys
import time

import pandas as pd

DP_PYTHON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(DP_PYTHON_DIR, "modules"))
from dp.config import Config, DEFAULT_CONFIG
from dp.network import Network
from dp.dss_io import DssFile
from dp import model, results, outputs
from damages import calculate_damages


class Log:
    """Prints and keeps every line for run_log.txt"""
    def __init__(self):
        self.lines = []

    def __call__(self, *parts):
        text = " ".join(str(p) for p in parts)
        print(text)
        self.lines.append(text)

    def save(self, path):
        with open(path, "w") as f:
            f.write("\n".join(self.lines) + "\n")


def main(config_file=DEFAULT_CONFIG):
    t0 = time.time()
    log = Log()
    cfg = Config(config_file)
    run_dir = cfg.results_dir
    try:
        _clear(run_dir)
    except model.DPError as e:
        print(f"\nSTOPPED: {e}")
        return None
    shutil.copy(cfg.file, os.path.join(run_dir, "config_used.ini"))
    try:
        summary = _run(cfg, run_dir, log)
    except model.DPError as e:
        log(f"\nSTOPPED: {e}")
        log.save(os.path.join(run_dir, "run_log.txt"))
        return None
    _add_to_history(cfg, summary)
    log(f"\nDone in {time.time() - t0:.0f} s. Everything is in:\n   {run_dir}")
    log(f"Run history: {cfg.history_csv}")
    log.save(os.path.join(run_dir, "run_log.txt"))
    return run_dir


def _clear(run_dir):
    """Empty the results folder so nothing from the last run is left behind"""
    if os.path.exists(run_dir):
        try:
            shutil.rmtree(run_dir)
        except OSError as e:
            raise model.DPError(f"Could not replace {run_dir}: {e}\n"
                                "Close any of its files that are open (Excel, an image viewer) and run again.")
    os.makedirs(run_dir)


def _short(path):
    """path relative to DP_Python when it's inside it"""
    rel = os.path.relpath(path, DP_PYTHON_DIR) if os.path.splitdrive(path)[0] == os.path.splitdrive(DP_PYTHON_DIR)[0] else path
    return path if rel.startswith("..") else rel


def _add_to_history(cfg, summary):
    """One line per run in output/WY<year>/run_history.csv"""
    row = pd.DataFrame([summary])
    new = not os.path.exists(cfg.history_csv)
    row.to_csv(cfg.history_csv, mode="a", header=new, index=False)


def _run(cfg, run_dir, log):
    log("=" * 78 + f"\nDamages Prevented  {cfg.start:%d%b%Y} - {cfg.end:%d%b%Y}\n" + "=" * 78)
    log(f"Config:      {cfg.file}")
    if not cfg.obsdata_dss or not os.path.exists(cfg.obsdata_dss):
        raise model.DPError(f"obsData.dss not found: {cfg.obsdata_dss}\n"
                            "Run step 1 (it makes the edited copy), or fix [paths] obsdata_dss in config.ini.")
    dss_saved = datetime.datetime.fromtimestamp(os.path.getmtime(cfg.obsdata_dss))
    log(f"obsData.dss: {cfg.obsdata_dss}")
    log(f"             last saved {dss_saved:%d%b%Y %H:%M}")
    net = Network.load(cfg.network_json)
    log(f"Network:     {cfg.network_json} (exported {net.exported})")
    for alt in (cfg.observed_alt, cfg.unregulated_alt):
        if alt not in net.alternatives:
            raise model.DPError(f"Alternative {alt} (config.ini) is not in network.json: {sorted(net.alternatives)}")
    bad = net.unsupported_reaches()
    if bad:
        raise model.DPError(f"Reaches with routing DP_Python can't reproduce: {bad}")
    if net.confluence_reservoirs:
        raise model.DPError("Reservoirs with more than one inflow junction are not supported yet")
    index = pd.date_range(cfg.lookback, cfg.run_end, freq="h")
    obs_alt, unreg_alt = cfg.observed_alt, cfg.unregulated_alt
    time_step = net.alternatives[obs_alt].time_step
    cdir = cfg.damage_points_dir
    log(f"Window:      {index[0]:%d%b%Y %H:%M} to {index[-1]:%d%b%Y %H:%M} ({len(index)} hours)")

    with DssFile(cfg.obsdata_dss) as obs:
        inputs = model.Inputs(obs, index, log=log)
        walk = model.Walk(net)
        log("\n1. Transformed locals")
        model.transform_gage_data(inputs, os.path.join(cdir, "TransformedLocals.csv"), time_step, log=log)
        log("\n2. Water-balance locals")
        n = model.water_balance_locals(net, walk, obs_alt, inputs, negs=True, log=log)
        log(f"   {n} locals computed")
        log("\n3. Observed and Unregulated runs")
        run_obs = model.simulate(net, walk, obs_alt, inputs, release="specified", log=log)
        run_unreg = model.simulate(net, walk, unreg_alt, inputs, release="inflow", log=log)
        log("   done")
        log("\n4. Mini-simulations")
        cps = model.read_name_list(os.path.join(cdir, "ControlPoints.txt"))
        resvs = model.read_name_list(os.path.join(cdir, "Reservoirs.txt"))
        added = model.read_added_points(os.path.join(cdir, "AddedFlowPoints.csv"))
        jp, rp, cps, resvs_run = model.mini_simulations(net, walk, inputs, obs_alt, run_obs, run_unreg,
                                                        cps, resvs, added, time_step, log=lambda *a: None)
        log(f"   {len(resvs_run)} reservoirs with/without at {len(cps)} control points")
        elevations = {r: model.reservoir_elevation(net, obs_alt, inputs, r) for r in resvs}
        # Hours filled by interpolation, shaded in the reservoir plots
        filled = {r: {"release": inputs.filled_mask(run_obs.outflow_keys.get(r, ())),
                      "inflow": inputs.filled_mask(run_obs.inflow_keys.get(r, set()) | run_unreg.inflow_keys.get(r, set())),
                      "elevation": inputs.filled_mask(inputs.record_keys(model.reservoir_elevation_record(net, obs_alt, r)))}
                  for r in resvs}
        gaps = dict(inputs.gaps)
        records_used = inputs.records_read()

    res_dir = os.path.join(run_dir, "Results")
    files = results.export_csv(res_dir, cps, resvs_run, jp, rp)
    log("   wrote Results/: " + ", ".join(os.path.basename(f) for f in files))

    log("\n5. Damages prevented")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        calculate_damages.main(res_dir, os.path.join(run_dir, "Damages"), damage_curves_pkl=cfg.damage_curves_pkl)
    for line in buf.getvalue().splitlines():
        if line.strip() and not line.startswith("Results:"):
            log("   " + line.replace(run_dir + os.sep, ""))

    pd.DataFrame({"obsData.dss record": records_used,
                  "Hours filled by interpolation": [gaps.get(k, 0) for k in records_used]}
                 ).to_csv(os.path.join(run_dir, "obsData_records_used.csv"), index=False)
    log(f"   {len(records_used)} records read from obsData.dss (obsData_records_used.csv)")

    log("\n6. Time series and plots")
    outputs.write_timeseries(os.path.join(run_dir, "TimeSeries"), jp, cps, resvs, run_obs, run_unreg, elevations)
    log("   wrote TimeSeries/")
    if cfg.make_plots:
        from dp import plots
        plots.make_all(os.path.join(run_dir, "Plots"), jp, cps, resvs, run_obs, run_unreg, elevations,
                       f"{cfg.start:%d%b%Y} - {cfg.end:%d%b%Y}", log=log, filled=filled)

    if gaps:
        log("\nWARNING - missing hours in obsData.dss were filled by straight-line interpolation")
        log("(shaded in the plots). Clean these records in DSSVue for a final run:")
        for k, v in sorted(gaps.items()):
            log(f"   {v:5d} h  {k}")
    else:
        log("\nNo missing hours in the records read from obsData.dss.")

    m = re.search(r"Total damages prevented: \$([\d,]+)", buf.getvalue())
    total = int(m.group(1).replace(",", "")) if m else None
    return {"Run": f"{datetime.datetime.now():%Y-%m-%d %H:%M}",
            "obsData.dss": _short(cfg.obsdata_dss),
            "obsData.dss last saved": f"{dss_saved:%Y-%m-%d %H:%M}",
            "Total damages prevented": total,
            "Records with filled hours": len(gaps),
            "Hours filled": sum(gaps.values())}


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    # Exit with an error code only when the run stopped. (A plain sys.exit(0) on
    # success shows up as "SystemExit: 0" in VS Code's interactive window / Spyder.)
    if not main(args[0] if args else DEFAULT_CONFIG):
        sys.exit(1)
