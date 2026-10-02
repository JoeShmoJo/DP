"""The four result tables, in the same layout as the ResSim menu's CSVs (cMiniSims.exportToCSV)."""
import csv
import os

from .dss_io import format_hec_time
from .model import r100


def _num(v):
    return "%.0f" % v


def _write(path, rows):
    with open(path, "w", newline="") as f:
        csv.writer(f, lineterminator="\n").writerows(rows)


def export_csv(out_dir, cps, resvs, jp, rp):
    os.makedirs(out_dir, exist_ok=True)
    files = []
    rows = [["Preliminary estimated flow reduction at each control point per project (cfs)"],
            ["Average of 2 mini-simulations: WITH ONLY the project and WITHOUT the project"],
            ["The per-project numbers do not always add up to the total reduction and may need adjusting"],
            ["Control Point", "Total Flow Reduction"] + resvs]
    for cp in cps:
        p = jp[cp]
        row = [cp, _num(r100(p.unreg[0]) - r100(p.modeled_obs[0]))]
        for r in resvs:
            row.append(_num(p.peaks[r]["reduction"]) if r in p.peaks else "x")
        rows.append(row)
    files.append(os.path.join(out_dir, "Preliminary_per_project.csv"))
    _write(files[-1], rows)

    rows = [["Reservoir", "Control Point", "Unreg Peak Flow (cfs)", "Modeled Obs Peak Flow (cfs)", "Flow Reduction (cfs)",
             "Without Peak Flow (cfs)", "Peak Discharge Increase (cfs)", "With Only Peak Flow (cfs)",
             "Peak Discharge Reduction (cfs)", "Average Reduction Credited (cfs)"]]
    for r in resvs:
        for cp in cps:
            p = jp[cp]
            if r not in p.peaks:
                continue
            unreg, obs = r100(p.unreg[0]), r100(p.modeled_obs[0])
            w, wo = r100(p.peaks[r]["WITH"][0]), r100(p.peaks[r]["WITHOUT"][0])
            rows.append([r, cp, _num(unreg), _num(obs), _num(unreg - obs), _num(wo), _num(wo - obs), _num(w),
                         _num(unreg - w), _num(p.peaks[r]["reduction"])])
    files.append(os.path.join(out_dir, "Mini-Simulations.csv"))
    _write(files[-1], rows)

    rows = [["Control Point", "Unreg Peak Flow (cfs)", "Date/Time of Unreg Peak", "Regulated Peak Flow (cfs)",
             "Date/Time of Regulated Peak", "Flow Reduction (cfs)", "Regulated Peak Source"]]
    for cp in cps:
        p = jp[cp]
        unreg = r100(p.unreg[0])
        if p.is_gaged:
            reg, t, source = r100(p.obs[0]), p.obs[1], "gaged"
        else:
            reg, t = r100(p.modeled_obs[0]), p.modeled_obs[1]
            source = p.note or "ResSim simulated, not gaged"
        rows.append([cp, _num(unreg), format_hec_time(p.unreg[1]), _num(reg), format_hec_time(t), _num(unreg - reg), source])
    files.append(os.path.join(out_dir, "CP_Peaks.csv"))
    _write(files[-1], rows)

    rows = [["Reservoir", "Peak Inflow (cfs)", "Time of Peak", "Outflow at Time of Peak (cfs)", "Flow Difference (cfs)", "Note"]]
    for r in resvs:
        x = rp[r]
        i, o = r100(x["inflow"]), r100(x["outflow"])
        note = f"Outflow is from re-reg: {x['rereg']}" if x["rereg"] else ""
        rows.append([r, _num(i), format_hec_time(x["time"]), _num(o), _num(i - o), note])
    files.append(os.path.join(out_dir, "Resv_Peaks.csv"))
    _write(files[-1], rows)
    return files
