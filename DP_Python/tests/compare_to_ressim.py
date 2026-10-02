# -*- coding: utf-8 -*-
"""
Compares DP_Python's result tables with the ResSim process's for the same run.

    python tests/compare_to_ressim.py [python results folder] [ResSim results folder]

Defaults: out/Results and tests/ResSimDP_Results (the validated WY2025 run).
Prints every value that differs, with the percent difference, and a summary.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def read(path, skip=0):
    with open(path) as f:
        rows = list(csv.reader(f))
    return rows[skip], rows[skip + 1:]


def num(v):
    try:
        return float(v)
    except ValueError:
        return None


def compare(name, py_dir, rs_dir, key_cols, skip=0, ignore=()):
    hp, py = read(os.path.join(py_dir, name), skip)
    hr, rs = read(os.path.join(rs_dir, name), skip)
    py = {tuple(r[i] for i in key_cols): r for r in py}
    rs = {tuple(r[i] for i in key_cols): r for r in rs}
    n_vals = n_diff = 0
    lines = []
    for key, rr in rs.items():
        pr = py.get(key)
        if pr is None:
            lines.append(f"  missing in DP_Python: {key}")
            continue
        for j, col in enumerate(hr):
            if j in key_cols or col in ignore or j >= len(pr):
                continue
            a, b = num(pr[j]), num(rr[j])
            n_vals += 1
            if a is None or b is None:
                if pr[j].strip() != rr[j].strip():
                    n_diff += 1
                    lines.append(f"  {' / '.join(key)} | {col}: python {pr[j]!r}  ressim {rr[j]!r}")
            elif a != b:
                n_diff += 1
                pct = (a - b) / abs(b) * 100 if b else float("inf")
                lines.append(f"  {' / '.join(key)} | {col}: python {a:.0f}  ressim {b:.0f}  ({a - b:+.0f}, {pct:+.1f}%)")
    for key in py:
        if key not in rs:
            lines.append(f"  extra in DP_Python: {key}")
    print(f"\n== {name}: {n_vals - n_diff} of {n_vals} values identical")
    for line in lines:
        print(line)
    return n_diff


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    py_dir = args[0] if len(args) > 0 else os.path.join(ROOT, "out", "Results")
    rs_dir = args[1] if len(args) > 1 else os.path.join(HERE, "ResSimDP_Results")
    total = 0
    total += compare("CP_Peaks.csv", py_dir, rs_dir, [0])
    total += compare("Resv_Peaks.csv", py_dir, rs_dir, [0])
    total += compare("Preliminary_per_project.csv", py_dir, rs_dir, [0], skip=3)
    total += compare("Mini-Simulations.csv", py_dir, rs_dir, [0, 1])
    print(f"\n{total} value(s) differ in all")
