# -*- coding: utf-8 -*-
"""
Created 30Sep2026

Builds the list of extra records DP_QAQC.py needs to check USGS against CWMS
for each Willamette project:
  - CWMS Elev-Forebay and Flow-Out for every project (picked from the CWMS
    catalog by DP_DL_28Aug2026.py), except where RequiredRecordsDict already
    has one
  - USGS forebay/outflow gages in willamette_projects.py that aren't already
    in RequiredRecordsDict (e.g. Green Peter and Foster outflow gages)
These are downloaded and QA'd but never written to the DSS file. Their
ResSimPaths end in /CWMS-QAQC/ or /USGS-QAQC/ so they're easy to tell apart.

No network calls here - DP_DL_28Aug2026.py does the catalog query and passes
the results in.

@author: g2encjer
"""
import pandas as pd

from willamette_projects import PROJECTS, param_class, cwms_location, usgs_site

# CWMS parameter for each QA/QC parameter class
CWMS_PARAMS = {'ELEV': 'Elev-Forebay', 'FLOW': 'Flow-Out'}
DSS_C_PART = {'ELEV': 'ELEV-FOREBAY', 'FLOW': 'FLOW-OUT'}

# When a project has several versions of a record, prefer (in order) these
# versions and intervals. Anything not listed ranks after the listed ones.
VERSION_PREF = ['CBT-REV', 'MIXED-REV', 'MIXED-COMPUTED-REV', 'CBT-COMPUTED-REV', 'GDACS-COMPUTED-REV']
INTERVAL_PREF = ['1Hour', '15Minutes', '30Minutes', '10Minutes', '5Minutes', '6Minutes', '0']
DAILY_OR_LONGER = ('DAY', 'WEEK', 'MONTH', 'YEAR')


def catalog_regex(loc):
    """Catalog 'like' regex for a project's forebay elevation and outflow."""
    return rf"{loc}\.({'|'.join(CWMS_PARAMS.values())})\..*"


def catalog_entries(cat_df):
    """[(tsid, latest_time or NaT), ...] from a cwms.get_timeseries_catalog().df"""
    if cat_df is None or cat_df.empty:
        return []
    name_col = 'name' if 'name' in cat_df.columns else cat_df.columns[0]
    entries = []
    for _, r in cat_df.iterrows():
        latest = pd.NaT
        ext = r.get('extents')
        if isinstance(ext, list) and ext and isinstance(ext[0], dict):
            latest = pd.to_datetime(ext[0].get('latest-time'), utc=True, errors='coerce')
        entries.append((str(r[name_col]), latest))
    return entries


def rank_tsid(tsid, param, latest=pd.NaT, period_start=None):
    """Sort key for a candidate tsid (lower is better), or None if it isn't a
    usable hourly-or-finer record of the right parameter."""
    parts = str(tsid).split('.')
    if len(parts) != 6:
        return None
    _loc, p, _type, interval, _duration, version = parts
    if p.lower() != CWMS_PARAMS[param].lower():
        return None
    if any(u in interval.upper() for u in DAILY_OR_LONGER):
        return None
    stale = 0
    if period_start is not None and pd.notna(latest):
        stale = int(latest < pd.Timestamp(period_start, tz='UTC'))
    v = version.upper()
    raw = 2 if 'RAW' in v else (0 if 'REV' in v else 1)
    vpref = next((i for i, pref in enumerate(VERSION_PREF) if v == pref), len(VERSION_PREF))
    ipref = INTERVAL_PREF.index(interval) if interval in INTERVAL_PREF else len(INTERVAL_PREF)
    return (stale, raw, vpref, ipref, tsid)


def build_qaqc_records(required, catalog, period_start):
    """
    required : RequiredRecordsDict DataFrame (ResSimPath, Download_Key, Source)
    catalog  : {cwms_location: [(tsid, latest_time), ...]}
    Returns (records, candidates): records to download for QA/QC, and every
    catalog candidate with its rank so the choices can be reviewed.
    """
    req = required.copy()
    req['Source'] = req['Source'].str.upper().str.strip()
    req_cwms = {(cwms_location(k), param_class(p, k))
                for p, k in zip(req.loc[req['Source'] == 'CWMS', 'ResSimPath'], req.loc[req['Source'] == 'CWMS', 'Download_Key'])}
    req_usgs = {usgs_site(k) for k in req.loc[req['Source'] == 'USGS', 'Download_Key']}

    records, candidates = [], []
    for loc, proj in PROJECTS.items():
        entries = catalog.get(loc, [])
        for param in CWMS_PARAMS:
            ranked = []
            for tsid, latest in entries:
                key = rank_tsid(tsid, param, latest, period_start)
                if key is not None:
                    ranked.append((key, tsid, latest))
            ranked.sort()
            already = (loc, param) in req_cwms
            chosen = None if already or not ranked else ranked[0][1]
            for i, (_key, tsid, latest) in enumerate(ranked):
                candidates.append({'Project': loc, 'Parameter': param, 'Rank': i + 1, 'Download_Key': tsid,
                                   'Latest Time': latest, 'Chosen': tsid == chosen,
                                   'Note': 'RequiredRecordsDict already has this parameter' if already else ''})
            if not ranked and not already:
                candidates.append({'Project': loc, 'Parameter': param, 'Rank': None, 'Download_Key': '',
                                   'Latest Time': pd.NaT, 'Chosen': False,
                                   'Note': f'nothing in catalog matching {catalog_regex(loc)}'})
            if chosen:
                records.append({'ResSimPath': f'//{loc}/{DSS_C_PART[param]}//1HOUR/CWMS-QAQC/',
                                'Download_Key': chosen, 'Source': 'CWMS'})

        for param, site in (('ELEV', proj['usgs_elev']), ('FLOW', proj['usgs_outflow']), ('FLOW', proj['usgs_rereg'])):
            if site and site not in req_usgs and not any(r['Download_Key'] == site for r in records):
                c_part = 'ELEV-FOREBAY' if param == 'ELEV' else 'FLOW'
                records.append({'ResSimPath': f"/{proj['name'].upper()} QAQC/{site}/{c_part}//1HOUR/USGS-QAQC/",
                                'Download_Key': site, 'Source': 'USGS'})
    return pd.DataFrame(records, columns=['ResSimPath', 'Download_Key', 'Source']), pd.DataFrame(candidates)
