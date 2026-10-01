# -*- coding: utf-8 -*-
"""
Created 01Oct2026

Repoints the DSS file column of ResSim alternative tables (Observed Data and
Time-Series tabs, copied into Excel and saved as CSV) to the Damages
Prevented files under scripts/DamagesPrevented. Only the DSS file column
changes; the A-F pathname parts are left exactly as they are.

    *obsData.dss                    -> scripts/DamagesPrevented/DP_Download/out/obsData.dss
    *Zero Flow record.dss           -> scripts/DamagesPrevented/DPdata/Zero_Flow_record.dss
    *Locals-FinalWaterBalance.dss   -> scripts/DamagesPrevented/DPdata/DPcalc.dss
    *Locals-Transformed.dss         -> scripts/DamagesPrevented/DPdata/DPcalc.dss

Usage: python RepointAlternativeTables.py <table.csv> [<table.csv> ...]
Writes <table>_DP.csv next to each input and prints what changed. Open the
output in Excel, copy the rows, and paste them over the table in the
alternative editor.

@author: g2encjer
"""
import csv
import os
import sys

OBSDATA = 'scripts/DamagesPrevented/DP_Download/out/obsData.dss'
ZERO = 'scripts/DamagesPrevented/DPdata/Zero_Flow_record.dss'
DPCALC = 'scripts/DamagesPrevented/DPdata/DPcalc.dss'


def new_dss_file(dss):
    """The DSS file a row should point to, or None to leave it alone."""
    name = os.path.basename(dss.strip().replace('\\', '/')).lower().replace('_', ' ')
    if name == 'obsdata.dss':
        return OBSDATA
    if name == 'zero flow record.dss':
        return ZERO
    if name in ('locals-finalwaterbalance.dss', 'locals-transformed.dss'):
        return DPCALC
    return None


def repoint(in_file):
    with open(in_file, encoding='utf-8-sig', newline='') as f:
        text = f.read()
    delim = '\t' if text.count('\t') > text.count(',') else ','
    rows = list(csv.reader(text.splitlines(), delimiter=delim))
    changes = {}
    for row in rows:
        if len(row) < 3 or not row[2].strip():
            continue
        new = new_dss_file(row[2])
        if new and row[2].strip() != new:
            key = (row[2].strip(), new)
            changes[key] = changes.get(key, 0) + 1
            row[2] = new
    stem, ext = os.path.splitext(in_file)
    out_file = stem + '_DP' + ext
    with open(out_file, 'w', encoding='utf-8-sig', newline='') as f:
        csv.writer(f, delimiter=delim, lineterminator='\n').writerows(rows)
    print(f'{in_file} -> {out_file} ({len(rows)} rows)')
    for (old, new), n in sorted(changes.items()):
        print(f'   {n:3d} rows  {old}  ->  {new}')
    unchanged = sorted({r[2].strip() for r in rows if len(r) > 2 and r[2].strip() and new_dss_file(r[2]) is None})
    for dss in unchanged:
        print(f'          left as is: {dss}')
    return out_file


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for path in sys.argv[1:]:
        repoint(path)
