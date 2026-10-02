# -*- coding: utf-8 -*-
"""
Damages Prevented without ResSim: one script from cleaned obsData.dss to the
result tables.

    python run_dp.py [config.ini]

Steps (the same as the ResSim menu, in order):
  1. Transformed locals (Willamette Falls = 1.5 x Pudding R at Aurora)
  2. Water-balance locals for the Observed alternative
  3. Observed run (Specified Releases) and Unregulated run (pass inflow)
  4. Mini-simulations, reductions, and the four result CSVs in out/Results
  5. Damages prevented in dollars (damages/calculate_damages.py) in out/Damages

Settings are in config.ini; the network is network/network.json (exported
from ResSim with export/ExportNetwork.py); control points, reservoirs and the
transformed / added-flow points are in config/.
"""
import os
import sys
import time

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dp.config import Config, DEFAULT_CONFIG
from dp.network import Network
from dp.dss_io import DssFile, parse_hec_time
from dp import model, results
from damages import calculate_damages


def main(config_file=DEFAULT_CONFIG, out_dir=None, log=print):
    t0 = time.time()
    cfg = Config(config_file)
    net = Network.load(cfg.network_json)
    if not cfg.obsdata_dss or not os.path.exists(cfg.obsdata_dss):
        raise model.DPError(f"obsdata_dss in {cfg.file} not set or not found: {cfg.obsdata_dss}")
    bad = net.unsupported_reaches()
    if bad:
        raise model.DPError(f"Reaches with routing DP_Python can't reproduce: {bad}")
    if net.confluence_reservoirs:
        raise model.DPError("Reservoirs with more than one inflow junction are not supported yet")
    w = cfg.window or net.simulation_window
    index = pd.date_range(parse_hec_time(w["lookback"]), parse_hec_time(w["end"]), freq="h")
    obs_alt, unreg_alt = cfg.observed_alt, cfg.unregulated_alt
    time_step = net.alternatives[obs_alt].time_step
    out_dir = out_dir or os.path.join(HERE, "out", "Results")
    log(f"Window: {index[0]} to {index[-1]} ({len(index)} hours), alternatives {obs_alt} / {unreg_alt}")

    with DssFile(cfg.obsdata_dss) as obs:
        inputs = model.Inputs(obs, index, log=log)
        walk = model.Walk(net)
        log("\n1. Transformed locals")
        model.transform_gage_data(inputs, os.path.join(HERE, "config", "TransformedLocals.csv"), time_step, log=log)
        log("\n2. Water-balance locals")
        n = model.water_balance_locals(net, walk, obs_alt, inputs, negs=True, log=log)
        log(f"   {n} locals computed")
        log("\n3. Observed and Unregulated runs")
        run_obs = model.simulate(net, walk, obs_alt, inputs, release="specified", log=log)
        run_unreg = model.simulate(net, walk, unreg_alt, inputs, release="inflow", log=log)
        log("\n4. Mini-simulations")
        cps = model.read_name_list(os.path.join(HERE, "config", "ControlPoints.txt"))
        resvs = model.read_name_list(os.path.join(HERE, "config", "Reservoirs.txt"))
        added = model.read_added_points(os.path.join(HERE, "config", "AddedFlowPoints.csv"))
        jp, rp, cps, resvs_run = model.mini_simulations(net, walk, inputs, obs_alt, run_obs, run_unreg,
                                                        cps, resvs, added, time_step, log=log)
        if inputs.gaps:
            log("\nWARNING - missing hours in obsData.dss (fill them in DSSVue):")
            for k, v in sorted(inputs.gaps.items()):
                log(f"   {v:5d}  {k}")
    files = results.export_csv(out_dir, cps, resvs_run, jp, rp)
    log("\nWrote:\n   " + "\n   ".join(files))
    log("\n5. Damages prevented")
    calculate_damages.main(out_dir, os.path.join(os.path.dirname(out_dir), "Damages"))
    log(f"Done in {time.time() - t0:.0f} s")
    return files


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    try:
        main(args[0] if args else DEFAULT_CONFIG)
    except model.DPError as e:
        print(f"\nSTOPPED: {e}")
        sys.exit(1)
