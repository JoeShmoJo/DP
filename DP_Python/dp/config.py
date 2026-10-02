"""Reads DP_Python/config.ini. Relative paths are relative to the config file's folder."""
import configparser
import os
import re

import pandas as pd

DP_PYTHON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(DP_PYTHON_DIR, "config.ini")


class Config:
    def __init__(self, config_file=DEFAULT_CONFIG):
        self.file = os.path.abspath(config_file)
        self.dir = os.path.dirname(self.file)
        parser = configparser.ConfigParser()
        if not parser.read(self.file):
            raise FileNotFoundError(f"Config file not found: {self.file}")
        self.parser = parser
        self.start = pd.Timestamp(parser.get("period", "start").strip())
        self.end = pd.Timestamp(parser.get("period", "end").strip())
        if self.end < self.start:
            raise ValueError(f"[period] end {self.end:%Y-%m-%d} is before start {self.start:%Y-%m-%d} in {self.file}")
        self.obsdata_dss = self._path(parser.get("paths", "obsdata_dss", fallback="data/obsData.dss"))
        self.network_json = self._path(parser.get("paths", "network_json", fallback="network/network.json"))
        self.observed_alt = parser.get("alternatives", "observed", fallback="Obs_NWP_H").strip()
        self.unregulated_alt = parser.get("alternatives", "unregulated", fallback="UnregNWP_H").strip()
        self.output_dir = self._path(parser.get("outputs", "output_dir", fallback="output"))
        self.make_plots = parser.getboolean("outputs", "make_plots", fallback=True)

    @property
    def lookback(self):
        """One hour before the period starts (as in the ResSim simulation)"""
        return self.start - pd.Timedelta(hours=1)

    @property
    def run_end(self):
        """24:00 on the last day of the period"""
        return self.end + pd.Timedelta(days=1)

    @property
    def period_label(self):
        return f"{self.start:%Y-%m-%d}_{self.end:%Y-%m-%d}"

    def _path(self, value):
        value = value.strip().strip('"')
        if not value:
            return None
        #A Windows drive path (C:/...) is absolute even when this runs on another OS
        if re.match(r"^[A-Za-z]:[\\/]", value):
            return value
        if not os.path.isabs(value):
            value = os.path.join(self.dir, value)
        return os.path.normpath(value)
