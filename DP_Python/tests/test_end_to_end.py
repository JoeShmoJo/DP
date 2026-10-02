# -*- coding: utf-8 -*-
"""
The whole DP_Python run on the WY2025 data (Data/obsData.dss, network/network.json)
against the validated ResSim results in tests/ResSimDP_Results. Needs pydsstools.

    python tests/test_end_to_end.py

Passes when every value in the four result tables is within one rounding step
of ResSim's (peaks are rounded to 100 cfs, reductions to 50; ResSim's own
routing engine in its Observed/Unregulated computes differs slightly from the
cRouting routing DP uses, so values near a rounding boundary can flip), no
more values differ than in the validated run (Oct 2026: CP_Peaks 6 of 69,
Resv_Peaks 0, per-project 51 of 120, Mini-Simulations 202 of 776) plus a
small margin, and the total damages prevented are within 0.01%.
"""
import csv
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import run_dp
from damages import calculate_damages

RESSIM = os.path.join(HERE, "ResSimDP_Results")
fails = []


def check(cond, msg):
    print(("  ok    " if cond else "  FAIL  ") + msg)
    if not cond:
        fails.append(msg)


def table(path, skip, key):
    rows = list(csv.reader(open(path)))[skip + 1:]
    return {tuple(r[:key]): r for r in rows}


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config.ini")
with open(cfg, "w") as f:
    f.write(f"[paths]\nobsdata_dss = {os.path.join(ROOT, 'Data', 'obsData.dss')}\n"
            f"network_json = {os.path.join(ROOT, 'network', 'network.json')}\n"
            "[alternatives]\nobserved = Obs_NWP_H\nunregulated = UnregNWP_H\n")
out = os.path.join(tmp, "Results")
run_dp.main(cfg, out_dir=out, log=lambda *a: None)

print("\n== Result tables vs ResSim")
for name, skip, key, step, max_diff in (("CP_Peaks.csv", 0, 1, 100, 10), ("Resv_Peaks.csv", 0, 1, 100, 2),
                                        ("Preliminary_per_project.csv", 3, 1, 100, 60),
                                        ("Mini-Simulations.csv", 0, 2, 200, 230)):
    py, rs = table(os.path.join(out, name), skip, key), table(os.path.join(RESSIM, name), skip, key)
    check(sorted(py) == sorted(rs), f"{name}: same rows")
    n = n_diff = worst = 0
    for k, r in rs.items():
        for a, b in zip(py[k][key:], r[key:]):
            try:
                d = abs(float(a) - float(b))
            except ValueError:
                continue
            n += 1
            n_diff += d > 0
            worst = max(worst, d)
    check(worst <= step, f"{name}: largest difference {worst:.0f} cfs (limit {step})")
    check(n_diff <= max_diff, f"{name}: {n - n_diff} of {n} values identical (at most {max_diff} may differ)")

print("\n== Damages prevented vs ResSim")
calculate_damages.main(out, os.path.join(tmp, "Damages"))
calculate_damages.main(RESSIM, os.path.join(tmp, "DamagesRS"))
tp = sum(float(r[-1]) for r in list(csv.reader(open(os.path.join(tmp, "Damages", "damages_prevented.csv"))))[1:] if r[-1])
tr = sum(float(r[-1]) for r in list(csv.reader(open(os.path.join(tmp, "DamagesRS", "damages_prevented.csv"))))[1:] if r[-1])
check(abs(tp - tr) <= 0.0001 * tr, f"total ${tp:,.0f} vs ResSim ${tr:,.0f}")

print("\n" + (f"{len(fails)} FAILED" if fails else "ALL PASSED"))
sys.exit(1 if fails else 0)
