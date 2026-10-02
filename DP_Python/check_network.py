# -*- coding: utf-8 -*-
"""
Checks network.json (exported from ResSim with export/ExportNetwork.py) and
config.ini before DP_Python uses them, and prints what it found.

    python check_network.py [config.ini]

Reports:
  - element counts and any reach routing DP_Python can't reproduce
  - each reservoir's Specified Release record in the Observed alternative
  - where every local inflow comes from in the Observed alternative
    (obsData.dss, the zero-flow record, computed by DP, or something else)
  - whether obsdata_dss in config.ini is set and exists
Exits with status 1 if anything would stop a run.
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dp.config import Config, DEFAULT_CONFIG
from dp.network import Network


def classify_file(dss_file):
    name = os.path.basename(dss_file.replace("\\", "/")).lower().replace("_", " ")
    if name == "obsdata.dss":
        return "obsData"
    if name == "zero flow record.dss":
        return "zero"
    if name in ("dpcalc.dss", "locals-finalwaterbalance.dss", "locals-transformed.dss"):
        return "computed by DP"
    return "other: " + dss_file


def main(config_file):
    problems = []
    cfg = Config(config_file)
    print(f"Config:  {cfg.file}")
    if not cfg.network_json or not os.path.exists(cfg.network_json):
        print(f"network.json not found: {cfg.network_json}\nRun export/ExportNetwork.py in ResSim and copy its output there.")
        return 1
    net = Network.load(cfg.network_json)
    print(f"Network: {net.source} (exported {net.exported}, export version {net.export_version})")
    w = net.simulation_window
    print(f"         simulation window when exported: {w['lookback']} / {w['start']} to {w['end']}")
    counts = Counter(e["type"] for e in net.elements.values())
    print("         " + ", ".join(f"{k}: {counts[k]}" for k in sorted(counts)))
    passthrough = [e for e in net.order if e and e.startswith("other:")]
    if passthrough:
        print(f"         {len(passthrough)} other elements in the compute order, passed straight through "
              f"(e.g. {passthrough[0].split(':', 1)[1]})")

    bad = net.unsupported_reaches()
    if bad:
        problems.append("reaches with routing DP_Python can't reproduce: " + ", ".join(f"{n} ({m})" for n, m in bad))
    else:
        methods = Counter(r["routing"]["method"] for r in net.reaches.values())
        print("Routing: " + ", ".join(f"{k}: {methods[k]}" for k in sorted(methods)))

    for alt in (cfg.observed_alt, cfg.unregulated_alt):
        if alt not in net.alternatives:
            problems.append(f"alternative '{alt}' (config.ini) is not in network.json: {sorted(net.alternatives)}")
    if cfg.observed_alt in net.alternatives:
        obs = net.alternatives[cfg.observed_alt]
        print(f"\nObserved alternative {obs.name} ({obs.time_step}):")
        print("  Specified releases:")
        for rid, r in sorted(net.reservoirs.items()):
            rec = net.specified_release(obs.name, r["name"])
            if rec is None or rec.is_blank:
                problems.append(f"no Specified Release record for {r['name']} in {obs.name}")
                print(f"    {r['name']:<16} MISSING")
            else:
                print(f"    {r['name']:<16} {rec.pathname}")
        sources = Counter()
        unmapped = []
        others = []
        for jid, j in net.junctions.items():
            for loc in j["locals"]:
                rec = obs.input_record(loc["knownFlowProxy"], net.vid["NODE_KNOWNFLOW"])
                if rec is None or rec.is_blank:
                    unmapped.append(f"{loc['node']} at {j['name']}")
                    continue
                kind = classify_file(rec.dss_file)
                sources[kind.split(":")[0]] += 1
                if kind.startswith("other"):
                    others.append(f"{loc['node']} at {j['name']}: {rec.dss_file}")
        print("  Local inflows by source: " + ", ".join(f"{k}: {v}" for k, v in sorted(sources.items())))
        for o in others:
            problems.append("local inflow mapped to a file DP_Python doesn't read: " + o)
        for u in unmapped:
            print(f"    not mapped (taken as 0): {u}")

    print()
    if not cfg.obsdata_dss:
        problems.append("obsdata_dss is not set in config.ini")
    elif not os.path.exists(cfg.obsdata_dss):
        problems.append(f"obsdata_dss does not exist: {cfg.obsdata_dss}")
    else:
        print(f"obsData: {cfg.obsdata_dss}")

    if problems:
        print("\nPROBLEMS:")
        for p in problems:
            print("  - " + p)
        return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    sys.exit(main(args[0] if args else DEFAULT_CONFIG))
