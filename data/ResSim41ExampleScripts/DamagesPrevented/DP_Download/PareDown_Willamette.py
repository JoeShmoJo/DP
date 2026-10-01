# -*- coding: utf-8 -*-
"""
Created 30Sep2026

Pares RequiredRecordsDictNWP.csv (Willamette + Columbia) down to the
Willamette records only and writes RequiredRecordsDictWIL.csv, which
DP_Download.py reads. Both files are in config/ next to this script.

A row is kept when any of these are true (see willamette_projects.py):
  - USGS: site number is in the Willamette basin range (1414xxxx-1421xxxx)
  - CWMS: tsid location is a Willamette project (DET, FOS, LOP, ...)
  - ResSimPath contains a Willamette project or river name
Kept and dropped rows are both printed so you can confirm the split.

@author: g2encjer
"""
#%%
import os

import pandas as pd

from willamette_projects import is_willamette, project_for_record, param_class

try:
    ScriptDir = os.path.dirname(os.path.abspath(__file__))
except NameError:  # running cell-by-cell without __file__ - run from the DP_Download folder
    ScriptDir = os.getcwd()
InPath = os.path.join(ScriptDir, 'config', 'RequiredRecordsDictNWP.csv')
OutPath = os.path.join(ScriptDir, 'config', 'RequiredRecordsDictWIL.csv')

#%%
# utf-8-sig strips the byte-order mark Excel puts on CSVs
records = pd.read_csv(InPath, encoding='utf-8-sig', dtype={'Download_Key': str})
records.columns = records.columns.str.strip()

keep = records.apply(lambda r: is_willamette(r['ResSimPath'], r['Download_Key'], r['Source']), axis=1)
wil = records[keep].copy()
dropped = records[~keep]

pd.set_option('display.width', 250, 'display.max_colwidth', 90, 'display.max_rows', 500)
print(f"Kept {len(wil)} Willamette rows, dropped {len(dropped)} of {len(records)}.\n")
print("---- DROPPED ----")
print(dropped[['ResSimPath', 'Download_Key', 'Source']].to_string(index=False))

# Show the kept rows grouped by project/parameter so redundant USGS/CWMS
# records for the same project are easy to spot.
wil['Project'] = wil.apply(lambda r: project_for_record(r['ResSimPath'], r['Download_Key'], r['Source']), axis=1)
wil['Parameter'] = wil.apply(lambda r: param_class(r['ResSimPath'], r['Download_Key']), axis=1)
print("\n---- KEPT ----")
print(wil.sort_values(['Project', 'Parameter', 'Source'])[['Project', 'Parameter', 'Source', 'Download_Key', 'ResSimPath']].to_string(index=False))

#%%
records[keep].to_csv(OutPath, index=False)
print(f"\nWrote {OutPath}")
