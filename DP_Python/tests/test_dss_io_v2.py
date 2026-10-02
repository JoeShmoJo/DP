# -*- coding: utf-8 -*-
"""
dp.dss_io with the pydsstools 2.x interface (Windows): getPathnameList for the
catalog, ts.pytimes for the times and ts.type for the data type. Wraps the
installed pydsstools so only those 2.x names exist, and checks every record in
Data/obsData.dss reads the same as through the native interface.

    python tests/test_dss_io_v2.py
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from dp import dss_io

OBS = os.path.join(ROOT, "Data", "obsData.dss")
START, END = pd.Timestamp("2024-09-30 23:00"), pd.Timestamp("2025-10-01 00:00")


class V2TS:
    """A 2.x-style time series: values, pytimes, type (no times / data_type)"""
    def __init__(self, ts):
        self.values = np.array(ts.values, dtype=float)   # copy before pydsstools frees its buffer
        self.pytimes = dss_io._times(ts)
        self.type = ts.data_type


class V2Open:
    """A 2.x-style open file: getPathnameList and read_ts, no search_path"""
    def __init__(self, fid):
        self._fid = fid
    def getPathnameList(self, pattern, sort=0):
        return sorted(self._fid.search_path(pattern)) if sort else list(self._fid.search_path(pattern))
    def read_ts(self, pathname, window=None, trim_missing=False):
        return V2TS(self._fid.read_ts(pathname, window=window))
    def close(self):
        self._fid.close()


f = dss_io.DssFile(OBS)          # one handle: opening a DSS file twice in a process fails
keys = sorted(f.catalog())
native = {k: f.read(k, START, END) for k in keys}
native_find = f.find("14202000", "FLOW", "1HOUR")
f._fid = V2Open(f._fid)           # same file, now only the 2.x names
f._catalog = None
assert not hasattr(f._fid, "search_path")
fails = 0
same_cat = keys == sorted(f.catalog())
fails += not same_cat
print(("  ok    " if same_cat else "  FAIL  ") + f"catalog via getPathnameList: {len(keys)} records")
bad = []
for k in keys:
    a, b = native[k], f.read(k, START, END)
    if not (a.index.equals(b.index) and np.allclose(a.values, b.values, equal_nan=True) and a.attrs["type"] == b.attrs["type"]):
        bad.append(k)
fails += bool(bad)
print(("  ok    " if not bad else "  FAIL  ") + f"every record reads the same (values, times, type); {len(bad)} differ {bad[:3]}")
found = f.find("14202000", "FLOW", "1HOUR")
ok = found == native_find and len(found) == 1
fails += not ok
print(("  ok    " if ok else "  FAIL  ") + f"find by station: {found}")
f.close()
print("\n" + (f"{fails} FAILED" if fails else "ALL PASSED"))
sys.exit(1 if fails else 0)
