# -*- coding: utf-8 -*-
"""
Build FIRO_SPACEConfig.csv from the rule curves of a daily ResSim run.

For each reservoir the FIRO_SPACE target is the rule curve plus a fraction of
the flood space above it:

    FIRO = Rule Curve + FLOOD_SPACE_FRACTION * (max con - Rule Curve)

max con is the top of that reservoir's rule curve (full pool). So in winter,
with the rule curve at min con, FIRO sits FLOOD_SPACE_FRACTION of the
conservation band above it, and it meets the rule curve when the pool is full.

The rule curves come from the "<reservoir>-Rule Curve Elev-ZONE" columns of a
model_check extract (reservoirs.csv) of a DAILY run. Leap years are skipped:
ResSim shifts the curve a day after 29 Feb in them, so they do not match a
generic-year Month/Day table.

Standard library only. ResSim's module loader imports every .py under
externalRules, this folder included, so a desktop-only import such as pandas
here fails the compute. Runs on desktop Python 2 or 3:

    python build_FIRO_SPACEConfig.py <run folder>

<run folder> is a model_check output folder of a daily run, e.g.
data/Check/Flood_64_Temp1Day_2026-09-28. Writes FIRO_SPACEConfig.csv next to
FIRO_SPACE.py, keeping the reservoir columns and their order from the file
already there.
"""

import os
import sys
import csv
import io
import calendar

################################################################################
# USER INPUT

# Share of the flood space (max con minus rule curve) FIRO may hold above the
# rule curve. 0.10 = 10%.
FLOOD_SPACE_FRACTION = 0.10

DECIMALS = 2

################################################################################

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(os.path.dirname(HERE), "FIRO_SPACEConfig.csv")
ZONE_SUFFIX = "-Rule Curve Elev-ZONE"
DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def _genericDays():
    """(month, day) for every day of a non-leap year, in order."""
    days = []
    for month in range(1, 13):
        for day in range(1, DAYS_IN_MONTH[month - 1] + 1):
            days.append((month, day))
    return days


def existingColumns():
    """Reservoir columns of the current config, in order, or [] if none."""
    if not os.path.exists(OUTPUT):
        return []
    handle = open(OUTPUT)
    try:
        for line in handle:
            if line.startswith("#") or not line.strip():
                continue
            cols = [c.strip() for c in line.strip().split(",")]
            return [c for c in cols[2:] if c]
    finally:
        handle.close()
    return []


def ruleCurves(runFolder):
    """{reservoir: {(month, day): elevation}} for a generic non-leap year."""
    handle = open(os.path.join(runFolder, "reservoirs.csv"))
    try:
        rows = list(csv.reader(handle))
    finally:
        handle.close()
    header = rows[0]
    columns = {}
    for i in range(len(header)):
        if header[i].endswith(ZONE_SUFFIX):
            columns[header[i][:-len(ZONE_SUFFIX)]] = i
    values = {}
    for resv in columns:
        values[resv] = {}
    for row in rows[1:]:
        # Dates are written as YYYY-MM-DD, possibly with a time after them
        date = row[0][:10]
        year, month, day = int(date[0:4]), int(date[5:7]), int(date[8:10])
        if calendar.isleap(year):
            continue
        for resv in columns:
            cell = row[columns[resv]].strip()
            if cell == "":
                continue
            elev = float(cell)
            key = (month, day)
            if key in values[resv] and abs(values[resv][key] - elev) > 0.005:
                raise SystemExit(
                    "%s rule curve differs between years on %d/%d, so it is "
                    "not a generic-year curve." % (resv, month, day))
            values[resv][key] = elev
    for resv in values:
        missing = [k for k in _genericDays() if k not in values[resv]]
        if missing:
            raise SystemExit(
                "The run does not cover every date of a non-leap year for %s "
                "(first missing: %d/%d). Use a daily run that does."
                % (resv, missing[0][0], missing[0][1]))
    return values


def build(curves, names):
    """{reservoir: {(month, day): FIRO elevation}}"""
    firo = {}
    for resv in names:
        rc = curves[resv]
        maxCon = max(rc.values())
        firo[resv] = {}
        for key in _genericDays():
            firo[resv][key] = round(
                rc[key] + FLOOD_SPACE_FRACTION * (maxCon - rc[key]), DECIMALS)
    return firo


def check(firo, curves, names):
    """FIRO never below the rule curve and never above max con."""
    tol = 0.5 * 10 ** -DECIMALS + 1e-9
    for resv in names:
        maxCon = max(curves[resv].values())
        for key in _genericDays():
            assert firo[resv][key] >= curves[resv][key] - tol, (resv, key)
            assert firo[resv][key] <= maxCon + tol, (resv, key)


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    runFolder = sys.argv[1]
    curves = ruleCurves(runFolder)
    if not curves:
        raise SystemExit("No '*%s' columns in %s" % (ZONE_SUFFIX, runFolder))
    names = existingColumns()
    if not names:
        names = sorted(curves.keys())
    missing = [n for n in names if n not in curves]
    if missing:
        raise SystemExit("No rule curve in %s for: %s"
                         % (runFolder, ", ".join(missing)))
    firo = build(curves, names)
    check(firo, curves, names)

    pct = int(round(FLOOD_SPACE_FRACTION * 100))
    lines = [
        "# FIRO_SPACE rule curve. One row per day of a generic (non-leap) year.",
        "# Read by scripts/externalRules/FIRO_SPACE.py",
        "#",
        "# GENERATED by externalRules/_offline_tests/build_FIRO_SPACEConfig.py",
        "# from the rule curves of %s." % os.path.basename(os.path.normpath(runFolder)),
        "# Rerun the generator rather than editing by hand.",
        "#",
        "#   FIRO = Rule Curve + %d%% x (max con - Rule Curve)" % pct,
        "#",
        "# max con is the top of each reservoir's rule curve. In winter FIRO sits",
        "# %d%% of the conservation band above the rule curve, and it meets the" % pct,
        "# rule curve when the pool is full.",
        "#",
        "# A BLANK cell means NO TARGET that day: the rule stands down and the rest",
        "# of the rule stack operates the project. A project with no column here is",
        "# never controlled. Column headers are matched to ResSim reservoir names",
        "# ignoring surrounding spaces and capitalization.",
        ",".join(["Month", "Day"] + names),
    ]
    fmt = "%." + str(DECIMALS) + "f"
    for key in _genericDays():
        cells = ["%d" % key[0], "%d" % key[1]]
        for resv in names:
            cells.append(fmt % firo[resv][key])
        lines.append(",".join(cells))

    # newline="" writes "\n" as is, so the file is the same on Windows
    handle = io.open(OUTPUT, "w", encoding="utf-8", newline="")
    try:
        handle.write(u"\n".join(lines) + u"\n")
    finally:
        handle.close()
    print("Wrote %d days x %d reservoirs to %s"
          % (len(_genericDays()), len(names), OUTPUT))


if __name__ == "__main__":
    main()
