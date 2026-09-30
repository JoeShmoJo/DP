# -*- coding: utf-8 -*-
"""
Created 30Sep2026

Makes Willamette-only copies of the ResSim alternative tabs exported to
../data (the *_Observed.csv and *_Timeseries.csv files) and checks that
obsData.dss has every record the Willamette rows point to.

Each row is: location, parameter, DSS file, A, B, C, E, F. For a row outside
the Willamette basin (see location_basin in willamette_projects.py):
  - Timeseries tabs: flow rows (Known Flow, Input Time Series, Lookback
    Release) point to the dummy zero record already used in these tabs
    (shared/Locals-Dummy.dss, B=0 CFS, FLOW, 1DAY). There is no zero-elevation
    dummy, so Lookback Elevation rows are blanked (ResSim then uses the
    alternative's initial conditions).
  - Observed tabs: the path is blanked, which is how these tabs already mark
    'no observed data' (a zero observed record would show up as a bogus
    observed line in the comparisons).
Willamette rows are kept. Those pointing at obsData.dss are checked against
the records in obsData.dss; a path that isn't there is renamed to the
obsData.dss record with the same B and C parts if there's exactly one, and
otherwise reported.

Copies are written next to the originals with NWP replaced by WIL in the
name (Obs_NWP_H_Observed.csv -> Obs_WIL_H_Observed.csv).

@author: g2encjer
"""
#%%
import csv
import glob
import os
import re

from willamette_projects import location_basin

DataDir = r'../data'
ObsDss = r'../out/obsData.dss'
ObsDssInTabs = 'shared/obsData.dss'
DummyRecord = ['shared/Locals-Dummy.dss', ' ', '0 CFS', 'FLOW', '1DAY', ' ']
BlankRecord = [' '] * 6
ELEVATION_PARAMS = {'Elevation', 'Lookback Elevation'}


def dss_records(dss_file):
    """Record pathnames in a DSS file with the D (date) part removed.
    Uses pydsstools on Windows. pydsstools can't open DSS 6 files on Linux,
    so there it falls back to reading the pathnames
    stored as text in the file; keep only records with more than one block to
    skip fragments of the file's internal tables."""
    if os.name == 'nt':
        from pydsstools.heclib.dss import HecDss
        with HecDss.Open(dss_file) as f:
            paths = f.getPathnameList('', sort=1)
        return {re.sub(r'^(/[^/]*/[^/]*/[^/]*/)[^/]*/', r'\1/', p) for p in paths}
    else:
        raw = open(dss_file, 'rb').read()
        blocks = {}
        for m in re.finditer(rb'/[ -.0-~]{0,64}/[ -.0-~]{1,64}/[A-Z0-9 -]{1,32}/\d{2}[A-Z]{3}\d{4}/[0-9A-Za-z]{1,12}/[ -.0-~]{0,32}/', raw):
            a, b, c, d, e, f = m.group(0).decode().split('/')[1:7]
            blocks.setdefault(f'/{a}/{b}/{c}//{e}/{f}/', set()).add(d)
        return {p for p, d in blocks.items() if len(d) > 1}


def row_path(row):
    a, b, c, e, f = (x.strip() for x in (row[3], row[4], row[5], row[6], row[7]))
    return f'/{a}/{b}/{c}//{e}/{f}/'


def path_parts(path):
    a, b, c, _d, e, f = path.split('/')[1:7]
    return [a or ' ', b, c, e, f]


def willamette_copy(in_file, obs_records):
    with open(in_file, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.reader(f))
    is_observed = in_file.lower().endswith('_observed.csv')
    report = []
    for row in rows:
        row += [' '] * (8 - len(row))
        loc, param, dss = row[0], row[1].strip(), row[2].strip()
        if dss in ('', 'shared/Locals-Dummy.dss'):
            continue
        basin = location_basin(loc, row[3], row[4])
        if basin == 'NON':
            if is_observed or param in ELEVATION_PARAMS:
                row[2:8] = BlankRecord
                action = 'blanked'
            else:
                row[2:8] = DummyRecord
                action = 'dummy zero record'
            report.append((loc, param, action, ''))
        elif basin is None:
            report.append((loc, param, 'UNKNOWN BASIN - left as is', row_path(row)))
        elif dss == ObsDssInTabs:
            path = row_path(row)
            if path in obs_records:
                continue
            _, b, c, _, _ = path_parts(path)
            match = [p for p in obs_records if path_parts(p)[1:3] == [b, c]]
            if len(match) == 1:
                row[3:8] = path_parts(match[0])
                report.append((loc, param, 'renamed to obsData.dss record', match[0]))
            else:
                report.append((loc, param, 'MISSING from obsData.dss', path))
    out_file = os.path.join(os.path.dirname(in_file), os.path.basename(in_file).replace('NWP', 'WIL'))
    with open(out_file, 'w', encoding='utf-8-sig', newline='') as f:
        csv.writer(f, lineterminator='\n').writerows(rows)
    return out_file, report


#%%
if __name__ == '__main__':
    obs_records = dss_records(ObsDss)
    print(f'{len(obs_records)} records in {ObsDss}')
    tabs = sorted(p for p in glob.glob(os.path.join(DataDir, '*NWP*.csv'))
                  if re.search(r'_(Observed|Time[sS]eries)\.csv$', p))
    for tab in tabs:
        out_file, report = willamette_copy(tab, obs_records)
        print(f'\n{os.path.basename(tab)} -> {os.path.basename(out_file)}')
        for action in ('dummy zero record', 'blanked', 'renamed to obsData.dss record',
                       'MISSING from obsData.dss', 'UNKNOWN BASIN - left as is'):
            hits = [r for r in report if r[2] == action]
            if hits:
                print(f'  {action} ({len(hits)}):')
                for loc, param, _a, path in hits:
                    print(f'    {loc} [{param}] {path}')
