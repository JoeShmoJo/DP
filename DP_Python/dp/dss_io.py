"""
Reading time series from DSS with pydsstools (2.x on Windows, 3.x elsewhere).

Every series comes back as a pandas Series of floats on an hourly
DatetimeIndex (naive, the times stored in the file), with DSS missing values
(-901, -902, UNDEFINED) as NaN.
"""
import re
import numpy as np
import pandas as pd

try:
    from pydsstools.heclib.dss import HecDss
except ImportError:  # pragma: no cover - reported when a DSS file is opened
    HecDss = None


def _hec_window(t):
    """'30Sep2024 2300' style window string; midnight written as 2400 of the day before"""
    t = pd.Timestamp(t)
    if t.hour == 0 and t.minute == 0:
        d = t - pd.Timedelta(days=1)
        return d.strftime("%d%b%Y") + " 2400"
    return t.strftime("%d%b%Y %H%M")


def parse_hec_time(text):
    """'30Sep2024 2400' / '30Sep2024, 24:00' -> Timestamp (2400 = midnight of the next day)"""
    m = re.match(r"^\s*(\d{1,2}[A-Za-z]{3}\d{4})[ ,]+(\d{1,2}):?(\d{2})\s*$", text)
    if not m:
        raise ValueError(f"Not a HEC time: {text!r}")
    day = pd.Timestamp(pd.to_datetime(m.group(1), format="%d%b%Y"))
    return day + pd.Timedelta(hours=int(m.group(2)), minutes=int(m.group(3)))


def format_hec_time(t):
    """Timestamp -> '29Dec2024, 24:00' (HecTime.toString(4): midnight shown as 24:00)"""
    t = pd.Timestamp(t)
    if t.hour == 0 and t.minute == 0:
        d = t - pd.Timedelta(days=1)
        return d.strftime("%d%b%Y") + ", 24:00"
    return t.strftime("%d%b%Y, %H:%M")


def _times(ts):
    if hasattr(ts, "pytimes"):            # pydsstools 2.x
        return list(ts.pytimes)
    out = []
    for t in ts.times:                    # pydsstools 3.x HecTime
        dt = t.datetime() if callable(getattr(t, "datetime", None)) else t.datetime
        out.append(dt)
    return out


class DssFile:
    """A DSS file opened for reading, with a case-insensitive catalog (D part ignored)."""

    def __init__(self, filename):
        if HecDss is None:
            raise ImportError("pydsstools is not installed (pip install pydsstools)")
        self.filename = filename
        self._fid = HecDss.Open(filename)
        self._catalog = None

    def close(self):
        self._fid.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    @staticmethod
    def _key(pathname):
        parts = pathname.strip().upper().split("/")
        if len(parts) >= 7:
            parts[4] = ""
        return "/".join(parts)

    def catalog(self):
        """{condensed upper-case pathname (no D part): a stored pathname}"""
        if self._catalog is None:
            self._catalog = {}
            if hasattr(self._fid, "search_path"):                 # pydsstools 3.x
                paths = self._fid.search_path("/*/*/*/*/*/*/")
            else:                                                  # pydsstools 2.x
                paths = self._fid.getPathnameList("/*/*/*/*/*/*/", sort=1)
            for p in paths:
                self._catalog.setdefault(self._key(p), p)
        return self._catalog

    def has(self, pathname):
        return self._key(pathname) in self.catalog()

    def find(self, b_part, c_contains="FLOW", e_part=None):
        """Condensed pathnames whose B part is b_part and C part contains c_contains"""
        out = []
        for key in sorted(self.catalog()):
            p = key.split("/")
            if p[2] == b_part.upper() and c_contains.upper() in p[3] and (e_part is None or p[5] == e_part.upper()):
                out.append(key)
        return out

    def read(self, pathname, start, end):
        """pandas Series for pathname between start and end (inclusive), or None if absent"""
        if not self.has(pathname):
            return None
        stored = self.catalog()[self._key(pathname)]
        parts = stored.split("/")
        parts[4] = ""
        ts = self._fid.read_ts("/".join(parts), window=(_hec_window(start), _hec_window(end)))
        values = np.array(ts.values, dtype=float)
        values[(values <= -900.0) & (values >= -903.0)] = np.nan
        values[np.abs(values) > 1e30] = np.nan
        s = pd.Series(values, index=pd.DatetimeIndex(_times(ts)), name=self._key(pathname))
        s = s[(s.index >= pd.Timestamp(start)) & (s.index <= pd.Timestamp(end))]
        dtype = getattr(ts, "data_type", None) or getattr(ts, "type", None) or ""   # 3.x / 2.x
        s.attrs["type"] = str(dtype).upper()
        return s
