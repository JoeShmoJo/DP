# -*- coding: utf-8 -*-
"""
Shared Willamette project metadata used by PareDown_Willamette.py,
DP_DL_28Aug2026.py (via qaqc_records.py) and DP_QAQC.py.

Created 30Sep2026

PROJECTS is keyed by CWMS location ID (the first '.'-separated piece of a
CWMS tsid, e.g. 'DET' in 'DET.Elev-Forebay.Inst.1Hour.0.Best').
  name          : Project name
  keywords      : Upper-case strings that identify the project in a ResSimPath
  usgs_elev     : USGS forebay elevation gage (from data/WIL_ELEV_DICT.csv)
  usgs_outflow  : USGS gage just below the dam, used as the project's outflow
                  record (hourly comparison with CWMS Flow-Out). None where
                  the project releases straight into a re-regulating pool
                  (DET -> Big Cliff Lake, LOP -> Dexter Lake).
  usgs_rereg    : For DET and LOP, the gage below the re-regulating dam
                  (North Santiam at Niagara below Big Cliff, Middle Fork
                  near Dexter). The re-reg dam smooths hourly releases, so
                  these are compared on DAILY means only.
  cwms_outflow  : (optional) CWMS Flow-Out tsid to use for QA/QC. When set it
                  overrides the CWMS catalog search in qaqc_records.py.
  GPR 14186200 (Middle Santiam R blw Green Peter Dam nr Foster) and
  FOS 14187200 (South Santiam R nr Foster) aren't in
  RequiredRecordsDictNWP.csv; they are downloaded for QA/QC only.

@author: g2encjer
"""

PROJECTS = {
    'HCR': {'name': 'Hills Creek',   'keywords': ['HILLS CREEK', 'HILLS CR'],       'usgs_elev': '14145100', 'usgs_outflow': '14145500', 'usgs_rereg': None},
    'LOP': {'name': 'Lookout Point', 'keywords': ['LOOKOUT POINT', 'LOOKOUT PT'],   'usgs_elev': '14149000', 'usgs_outflow': None, 'usgs_rereg': '14150000'},
    'DEX': {'name': 'Dexter',        'keywords': ['DEXTER'],                         'usgs_elev': '14149500', 'usgs_outflow': '14150000', 'usgs_rereg': None,
            'cwms_outflow': 'DEX.Flow-Out.Inst.0.0.MIXED-COMPUTED-REV'},
    'FAL': {'name': 'Fall Creek',    'keywords': ['FALL CREEK', 'FALL CR'],          'usgs_elev': '14150900', 'usgs_outflow': '14151000', 'usgs_rereg': None},
    'COT': {'name': 'Cottage Grove', 'keywords': ['COTTAGE GROVE LAKE', 'COTTAGE GROVE DAM'], 'usgs_elev': '14153000', 'usgs_outflow': '14153500', 'usgs_rereg': None},
    'DOR': {'name': 'Dorena',        'keywords': ['DORENA'],                         'usgs_elev': '14155000', 'usgs_outflow': '14155500', 'usgs_rereg': None},
    'CGR': {'name': 'Cougar',        'keywords': ['COUGAR'],                         'usgs_elev': '14159400', 'usgs_outflow': '14159500', 'usgs_rereg': None},
    'BLU': {'name': 'Blue River',    'keywords': ['BLUE RIVER LAKE', 'BLUE RIVER DAM'], 'usgs_elev': '14162100', 'usgs_outflow': '14162200', 'usgs_rereg': None},
    'FRN': {'name': 'Fern Ridge',    'keywords': ['FERN RIDGE'],                     'usgs_elev': '14168000', 'usgs_outflow': '14169000', 'usgs_rereg': None},
    'GPR': {'name': 'Green Peter',   'keywords': ['GREEN PETER'],                    'usgs_elev': '14186100', 'usgs_outflow': '14186200', 'usgs_rereg': None},
    'FOS': {'name': 'Foster',        'keywords': ['FOSTER'],                         'usgs_elev': '14186600', 'usgs_outflow': '14187200', 'usgs_rereg': None},
    'DET': {'name': 'Detroit',       'keywords': ['DETROIT'],                        'usgs_elev': '14180500', 'usgs_outflow': None, 'usgs_rereg': '14181500'},
    'BCL': {'name': 'Big Cliff',     'keywords': ['BIG CLIFF'],                      'usgs_elev': '14181400', 'usgs_outflow': '14181500', 'usgs_rereg': None,
            'cwms_outflow': 'BCL.Flow-Out.Inst.0.0.MIXED-COMPUTED-REV'},
}

# Willamette CWMS locations that aren't reservoir projects
WILLAMETTE_CWMS_OTHER = {
    'EUGO': 'Willamette River at Eugene',
    'FRMO': 'Willamette basin flow location (in RequiredRecordsDictNWP.csv; confirm)',
}

# USGS site numbers in the Willamette basin (HUC 1709) fall in this range
# (Middle Fork headwaters ~14144900 down to the Willamette at Portland,
# 14211720). Lower Columbia gages are numbered in and around it (14144700
# Columbia R at Vancouver, 1421182x Columbia Slough), so any path that
# mentions the Columbia is excluded regardless of number.
WILLAMETTE_USGS_MIN = 14144900
WILLAMETTE_USGS_MAX = 14211799
EXCLUDE_KEYWORDS = ['COLUMBIA']

# Words in a ResSimPath that mark a Willamette-basin record.
WILLAMETTE_KEYWORDS = [
    'WILLAMETTE', 'SANTIAM', 'MCKENZIE', 'LONG TOM', 'COAST FORK', 'ROW R',
    'CALAPOOIA', 'MOLALLA', 'PUDDING', 'YAMHILL', 'LUCKIAMUTE', 'MARYS R',
    'TUALATIN', 'CLACKAMAS',
] + [kw for p in PROJECTS.values() for kw in p['keywords']]


def cwms_location(download_key):
    """'DET-Outlet.Flow-Out.Ave.1Hour.1Hour.Best' -> 'DET'"""
    return str(download_key).split('.')[0].split('-')[0].upper()


def usgs_site(download_key):
    """'USGS-14181500' or '14181500' -> '14181500'"""
    key = str(download_key).strip().upper()
    return key[5:] if key.startswith('USGS-') else key


def dss_part(path, part):
    """Return a DSS pathname part ('A'..'F') from '/A/B/C/D/E/F/'."""
    parts = str(path).split('/')
    idx = 'ABCDEF'.index(part.upper()) + 1
    return parts[idx].upper() if len(parts) > idx else ''


def param_class(res_sim_path, download_key=''):
    """Classify a record as ELEV, INFLOW, or FLOW (outflow / gage flow)."""
    c = dss_part(res_sim_path, 'C')
    key = str(download_key).upper()
    if c.startswith('ELEV') or '.ELEV' in key:
        return 'ELEV'
    if c.startswith('FLOW-IN') or '.FLOW-IN' in key:
        return 'INFLOW'
    if c.startswith('FLOW') or '.FLOW' in key:
        return 'FLOW'
    return 'OTHER'


def project_for_record(res_sim_path, download_key, source):
    """Best guess at which Willamette project a record belongs to (CWMS ID) or None."""
    source = str(source).upper()
    if source == 'CWMS':
        loc = cwms_location(download_key)
        if loc in PROJECTS:
            return loc
    if source == 'USGS':
        site = usgs_site(download_key)
        for loc, p in PROJECTS.items():
            if site in (p['usgs_elev'], p['usgs_outflow']):
                return loc
    b = dss_part(res_sim_path, 'B')
    for loc, p in PROJECTS.items():
        if any(kw in b for kw in p['keywords']):
            return loc
    return None


def is_willamette(res_sim_path, download_key, source):
    """True if a RequiredRecordsDict row belongs to the Willamette basin."""
    source = str(source).upper()
    text = str(res_sim_path).upper()
    if any(kw in text for kw in EXCLUDE_KEYWORDS):
        return False
    if source == 'USGS':
        site = usgs_site(download_key)
        if site.isdigit() and len(site) == 8:
            return WILLAMETTE_USGS_MIN <= int(site) <= WILLAMETTE_USGS_MAX
    if source == 'CWMS':
        loc = cwms_location(download_key)
        if loc in PROJECTS or loc in WILLAMETTE_CWMS_OTHER:
            return True
    return any(kw in text for kw in WILLAMETTE_KEYWORDS)
