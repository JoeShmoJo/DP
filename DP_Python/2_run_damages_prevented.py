# -*- coding: utf-8 -*-
"""
STEP 2 - Damages Prevented: from the cleaned obsData.dss to the flow reductions,
the dollars, and plots.

    python 2_run_damages_prevented.py

Settings come from config.ini. Every run writes a new folder
output/<date_time>_<period>/ with:

  Results/       CP_Peaks, Preliminary_per_project, Mini-Simulations, Resv_Peaks (CSV)
  Damages/       damages_prevented.csv, damages_prevented_ByProject.csv
  Plots/         ControlPoints/ and Reservoirs/ (PNG)
  TimeSeries/    every series behind the results (CSV per control point / reservoir)
  run_log.txt    everything printed during the run
  config_used.ini

What it does (the same steps as the ResSim Damages Prevented menu):
  1. Transformed locals (Willamette Falls = 1.5 x Pudding R at Aurora)
  2. Water-balance locals for the Observed alternative
  3. Observed run (each reservoir releases its observed outflow) and
     Unregulated run (each reservoir passes inflow), routed through the network
     exported from ResSim (network/network.json)
  4. Mini-simulations with and without each reservoir, and the reductions
  5. Damages prevented in dollars (damages/calculate_damages.py)
  6. Plots and time series
"""
import contextlib
import datetime
import io
import os
import shutil
import sys
import time

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
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
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    run_dir = os.path.join(cfg.output_dir, f"{stamp}_{cfg.period_label}")
    os.makedirs(run_dir)
    shutil.copy(cfg.file, os.path.join(run_dir, "config_used.ini"))
    try:
        _run(cfg, run_dir, log)
    except model.DPError as e:
        log(f"\nSTOPPED: {e}")
        log.save(os.path.join(run_dir, "run_log.txt"))
        return None
    log(f"\nDone in {time.time() - t0:.0f} s. Everything is in:\n   {run_dir}")
    log.save(os.path.join(run_dir, "run_log.txt"))
    return run_dir


def _run(cfg, run_dir, log):
    log("=" * 78 + f"\nDamages Prevented  {cfg.start:%d%b%Y} - {cfg.end:%d%b%Y}\n" + "=" * 78)
    log(f"Config:      {cfg.file}")
    log(f"obsData.dss: {cfg.obsdata_dss}")
    if not cfg.obsdata_dss or not os.path.exists(cfg.obsdata_dss):
        raise model.DPError(f"obsData.dss not found: {cfg.obsdata_dss}. Run step 1 or fix [paths] obsdata_dss in config.ini.")
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
    cdir = os.path.join(HERE, "config")
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
        gaps = dict(inputs.gaps)

    res_dir = os.path.join(run_dir, "Results")
    files = results.export_csv(res_dir, cps, resvs_run, jp, rp)
    log("   wrote Results/: " + ", ".join(os.path.basename(f) for f in files))

    log("\n5. Damages prevented")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        calculate_damages.main(res_dir, os.path.join(run_dir, "Damages"))
    for line in buf.getvalue().splitlines():
        if line.strip() and not line.startswith("Results:"):
            log("   " + line.replace(run_dir + os.sep, ""))

    log("\n6. Time series and plots")
    outputs.write_timeseries(os.path.join(run_dir, "TimeSeries"), jp, cps, resvs, run_obs, run_unreg, elevations)
    log("   wrote TimeSeries/")
    if cfg.make_plots:
        from dp import plots
        plots.make_all(os.path.join(run_dir, "Plots"), jp, cps, resvs, run_obs, run_unreg, elevations,
                       f"{cfg.start:%d%b%Y} - {cfg.end:%d%b%Y}", log=log)

    if gaps:
        log("\nWARNING - missing hours in obsData.dss were filled by straight-line interpolation.")
        log("Clean these records in DSSVue for a final run:")
        for k, v in sorted(gaps.items()):
            log(f"   {v:5d} h  {k}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    sys.exit(0 if main(args[0] if args else DEFAULT_CONFIG) else 1)
