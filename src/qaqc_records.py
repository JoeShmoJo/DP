# -*- coding: utf-8 -*-
"""
Created 30Sep2026

Builds the list of extra records DP_QAQC.py needs to check USGS against CWMS
for each Willamette project:
  - CWMS Elev-Forebay and Flow-Out for every project (picked from the CWMS
    catalog by DP_DL_28Aug2026.py, or pinned via 'cwms_outflow' in
    willamette_projects.py), except where RequiredRecordsDict already has one
  - USGS forebay/outflow gages in willamette_projects.py that aren't already
    in RequiredRecordsDict (e.g. the Foster outflow gage)
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
# (Willamette outflow is stored as e.g. DEX.Flow-Out.Inst.0.0.MIXED-COMPUTED-REV,
# forebay elevation like MAY.Elev-Forebay.Inst.0.0.MIXED-REV.)
VERSION_PREF = {
    'ELEV': ['CBT-REV', 'MIXED-REV', 'MIXED-COMPUTED-REV', 'CBT-COMPUTED-REV', 'GDACS-COMPUTED-REV'],
    'FLOW': ['CBT-REV', 'MIXED-COMPUTED-REV', 'MIXED-REV', 'CBT-COMPUTED-REV', 'GDACS-COMPUTED-REV'],
}
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
    vpref = next((i for i, pref in enumerate(VERSION_PREF[param]) if v == pref), len(VERSION_PREF[param]))
    ipref = INTERVAL_PREF.index(interval) if interval in INTERVAL_PREF else len(INTERVAL_PREF)
    return (stale, raw, vpref, ipref, tsid)


def prune_qaqc_records(records):
    """Drop QA/QC records willamette_projects.py no longer calls for (e.g. a
    gage removed from the table, or an outflow for a project whose outflow
    isn't compared). Returns (kept, dropped)."""
    usgs_sites = {p[k] for p in PROJECTS.values() for k in ('usgs_elev', 'usgs_outflow') if p[k]}
    keep = []
    for _, r in records.iterrows():
        if str(r['Source']).upper() == 'USGS':
            keep.append(usgs_site(r['Download_Key']) in usgs_sites)
        else:
            loc = cwms_location(r['Download_Key'])
            param = param_class(r['ResSimPath'], r['Download_Key'])
            keep.append(not (param == 'FLOW' and loc in PROJECTS and not PROJECTS[loc]['usgs_outflow']))
    keep = pd.Series(keep, index=records.index, dtype=bool)
    return records[keep], records[~keep]


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
            # No outflow gage to compare against -> don't download a QA/QC outflow
            if param == 'FLOW' and not proj['usgs_outflow']:
                continue
            ranked = []
            for tsid, latest in entries:
                key = rank_tsid(tsid, param, latest, period_start)
                if key is not None:
                    ranked.append((key, tsid, latest))
            ranked.sort()
            already = (loc, param) in req_cwms
            chosen = None if already or not ranked else ranked[0][1]
            # A tsid pinned in willamette_projects.py wins over the catalog pick
            pinned = proj.get('cwms_outflow') if param == 'FLOW' else None
            if pinned and not already:
                chosen = pinned
                if pinned not in [t for _k, t, _l in ranked]:
                    candidates.append({'Project': loc, 'Parameter': param, 'Rank': 0, 'Download_Key': pinned,
                                       'Latest Time': pd.NaT, 'Chosen': True,
                                       'Note': 'pinned in willamette_projects.py'})
            for i, (_key, tsid, latest) in enumerate(ranked):
                candidates.append({'Project': loc, 'Parameter': param, 'Rank': i + 1, 'Download_Key': tsid,
                                   'Latest Time': latest, 'Chosen': tsid == chosen,
                                   'Note': 'RequiredRecordsDict already has this parameter' if already else ''})
            if not ranked and not already and not pinned:
                candidates.append({'Project': loc, 'Parameter': param, 'Rank': None, 'Download_Key': '',
                                   'Latest Time': pd.NaT, 'Chosen': False,
                                   'Note': f'nothing in catalog matching {catalog_regex(loc)}'})
            if chosen:
                records.append({'ResSimPath': f'//{loc}/{DSS_C_PART[param]}//1HOUR/CWMS-QAQC/',
                                'Download_Key': chosen, 'Source': 'CWMS'})

        for param, site in (('ELEV', proj['usgs_elev']), ('FLOW', proj['usgs_outflow'])):
            if site and site not in req_usgs and not any(r['Download_Key'] == site for r in records):
                c_part = 'ELEV-FOREBAY' if param == 'ELEV' else 'FLOW'
                records.append({'ResSimPath': f"/{proj['name'].upper()} QAQC/{site}/{c_part}//1HOUR/USGS-QAQC/",
                                'Download_Key': site, 'Source': 'USGS'})
    return pd.DataFrame(records, columns=['ResSimPath', 'Download_Key', 'Source']), pd.DataFrame(candidates)
