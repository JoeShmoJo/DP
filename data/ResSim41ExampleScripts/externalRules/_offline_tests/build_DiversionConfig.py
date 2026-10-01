# -*- coding: utf-8 -*-
"""
Build the DiversionFromCSV config file from the raw diversion/return data.

This runs on a DESKTOP Python (2 or 3), not inside ResSim. It exists so the
generated config is reproducible: when data/daily_diversions_returns_ALT.csv is
updated, rerun this instead of editing the generated file by hand.

    python data/scripts/externalRules/_offline_tests/build_DiversionConfig.py

Source
------
data/daily_diversions_returns_ALT.csv
    Wide format, one row per day from 1934-10-01 to 2020-10-01. Columns are DSS
    pathnames such as //DIVERSION 1B/FLOW//1DAY/BA_ALT. The values are MONTHLY:
    every day in a month carries the same number, because DivAndReturnDSS.py
    broadcast a 12-value monthly table across the period of record. This script
    checks that is still true and fails if it is not.

    Diversions are positive. Returns are negative.

Output (in the FIRO_SPACEConfig.csv layout: Month,Day,<element names>)
    data/scripts/externalRules/DiversionConfig_ALT.csv
"""

import os
import csv
import calendar

# DSS B-part suffix -> the tail of the ResSim element name. Everything not
# listed here keeps its own suffix, so "DIVERSION 4" -> "Diversion 4".
# Supplied by Josh Roach: 1 up is 1C, 1 down is 1B.
SUFFIX_TO_NAME = {
    "1B": "1 down",
    "1C": "1 up",
}

# DSS B-part prefix -> the head of the ResSim element name, from
# data/ReSimDiversionReturn_Names.csv
PREFIX_TO_NAME = {
    "DIVERSION": "Diversion",
    "RETURN": "Return",
}

DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

SOURCE_CSV = os.path.join(REPO, "data", "daily_diversions_returns_ALT.csv")
NAMES_CSV = os.path.join(REPO, "data", "ReSimDiversionReturn_Names.csv")
OUTPUT_CSV = os.path.join(REPO, "data", "scripts", "externalRules",
                          "DiversionConfig_ALT.csv")


def elementNameFromPathname(pathname):
    """//DIVERSION 1B/FLOW//1DAY/BA_ALT -> "Diversion 1 down"."""
    bPart = pathname.split("/")[2].strip()
    prefix, suffix = bPart.split(" ", 1)
    if prefix.upper() not in PREFIX_TO_NAME:
        raise AssertionError("Unknown pathname prefix %r in %r. Expected one of "
                             "%s." % (prefix, pathname,
                                      sorted(PREFIX_TO_NAME.keys())))
    head = PREFIX_TO_NAME[prefix.upper()]
    tail = SUFFIX_TO_NAME.get(suffix.upper(), suffix)
    return "%s %s" % (head, tail)


def readMonthlyValues(sourceCSV):
    """
    Collapse the daily source to {elementName: {month: value}}.

    Fails loudly if any month holds more than one distinct value, because then
    the data is not really monthly and a 365-row generic year would lose
    information rather than just restating it.
    """
    handle = open(sourceCSV)
    try:
        reader = csv.reader(handle)
        header = next(reader)
        names = [elementNameFromPathname(p) for p in header[1:]]

        seen = {}
        for name in names:
            seen[name] = {}

        for row in reader:
            if not row or not row[0].strip():
                continue
            month = int(row[0].split("-")[1])
            for name, cell in zip(names, row[1:]):
                text = cell.strip()
                if text == "":
                    continue
                value = float(text)
                # -0.0 and 0.0 are equal but print differently; normalize
                if value == 0.0:
                    value = 0.0
                bucket = seen[name].setdefault(month, set())
                bucket.add(value)
    finally:
        handle.close()

    monthly = {}
    for name in names:
        monthly[name] = {}
        for month in range(1, 13):
            values = seen[name].get(month)
            if not values:
                raise AssertionError("%s has no value at all in month %d of %s"
                                     % (name, month, sourceCSV))
            if len(values) > 1:
                raise AssertionError(
                    "%s is not monthly: month %d holds %s in %s. This script "
                    "collapses the source to 12 values per element, which "
                    "would silently drop the variation."
                    % (name, month, sorted(values), sourceCSV))
            monthly[name][month] = values.pop()
    return names, monthly


def readExpectedNames(namesCSV):
    """The element names ResSim actually has, one per line."""
    handle = open(namesCSV)
    try:
        text = handle.read()
    finally:
        handle.close()
    # The file is written by Windows and starts with a UTF-8 byte order mark
    text = text.replace("﻿", "").replace("\xef\xbb\xbf", "")
    names = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            names.append(line)
    return names


def checkAgainstResSimNames(names, namesCSV):
    """Every column must be an element ResSim has, and the other way round."""
    expected = readExpectedNames(namesCSV)
    missingFromData = sorted(set(expected) - set(names))
    missingFromResSim = sorted(set(names) - set(expected))
    if missingFromData or missingFromResSim:
        raise AssertionError(
            "The data and %s do not describe the same elements.\n"
            "  In ResSim but not in the data: %s\n"
            "  In the data but not in ResSim: %s"
            % (namesCSV, missingFromData or "none", missingFromResSim or "none"))
    print("  all %d element names match %s" % (len(names), os.path.basename(namesCSV)))


def checkSigns(names, monthly):
    """
    Diversions take water out, returns put it back. Warn on any value whose
    sign disagrees with its name -- a flipped column would otherwise look fine.
    """
    problems = []
    for name in names:
        for month in range(1, 13):
            value = monthly[name][month]
            if name.startswith("Diversion") and value < 0.0:
                problems.append("%s is negative (%g) in month %d" % (name, value, month))
            if name.startswith("Return") and value > 0.0:
                problems.append("%s is positive (%g) in month %d" % (name, value, month))
    if problems:
        print("  WARNING: sign looks wrong on %d entries:" % len(problems))
        for problem in problems[:10]:
            print("    %s" % problem)
    else:
        print("  signs are consistent: diversions >= 0, returns <= 0")


def writeConfig(names, monthly, outputCSV, sourceCSV):
    """Write one row per day of a generic non-leap year."""
    handle = open(outputCSV, "w")
    try:
        handle.write("# Diversion and return flows, cfs. One row per day of a "
                     "generic (non-leap) year.\n")
        handle.write("# Read by scripts/externalRules/DiversionFromCSV.py\n")
        handle.write("#\n")
        handle.write("# Column headers are ResSim element names. A positive "
                     "number takes water out of the\n")
        handle.write("# network, a negative number puts it back, so the Return "
                     "columns are negative.\n")
        handle.write("#\n")
        handle.write("# GENERATED from data/%s by\n" % os.path.basename(sourceCSV))
        handle.write("# scripts/externalRules/_offline_tests/build_DiversionConfig.py\n")
        handle.write("# Do not edit by hand -- rerun that script instead.\n")
        handle.write("#\n")
        handle.write("# The source holds one value per MONTH, repeated across "
                     "every day of that month.\n")
        handle.write("# It is written out day by day only to match the layout "
                     "the other config files use.\n")

        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["Month", "Day"] + names)
        for month in range(1, 13):
            for day in range(1, DAYS_IN_MONTH[month - 1] + 1):
                row = [month, day]
                for name in names:
                    value = monthly[name][month]
                    # Whole numbers throughout; keep them looking that way
                    if value == int(value):
                        row.append(int(value))
                    else:
                        row.append(value)
                writer.writerow(row)
    finally:
        handle.close()


def main():
    print("Reading %s" % SOURCE_CSV)
    names, monthly = readMonthlyValues(SOURCE_CSV)
    print("  %d elements, collapsed to 12 monthly values each" % len(names))

    checkAgainstResSimNames(names, NAMES_CSV)
    checkSigns(names, monthly)

    writeConfig(names, monthly, OUTPUT_CSV, SOURCE_CSV)
    print("Wrote %s" % OUTPUT_CSV)
    print("  %d data rows" % sum(DAYS_IN_MONTH))

    # Show July, the peak month, so a bad mapping is visible at a glance
    print("\n  July:")
    for name in names:
        print("    %-20s %8g" % (name, monthly[name][7]))


if __name__ == "__main__":
    main()
