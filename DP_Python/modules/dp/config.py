"""
Reads DP_Python/config/config.ini and works out every file and folder the two
steps use. Relative paths in config.ini are relative to the DP_Python folder.

Each water year gets its own folder, output/WY<year>/:

  1_download_for_data_management_review/   step 1: the raw download and the data checks
      obsData_raw.dss
      QAQC/  Combined_Summary_Stats.csv  Hourly_*.csv  FOR DATA MANAGEMENT REVIEW.txt
  2_edited_data/obsData.dss                 copied from the raw file once; you edit it
  3_damages_prevented/                      step 2, replaced on every run
  run_history.csv                           one line per step 2 run
"""
import configparser
import os
import re

import pandas as pd

DP_PYTHON_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_DIR = os.path.join(DP_PYTHON_DIR, "config")
DEFAULT_CONFIG = os.path.join(CONFIG_DIR, "config.ini")

DOWNLOAD_FOLDER = "1_download_for_data_management_review"
EDITED_FOLDER = "2_edited_data"
RESULTS_FOLDER = "3_damages_prevented"


class Config:
    def __init__(self, config_file=DEFAULT_CONFIG):
        self.file = os.path.abspath(config_file)
        parser = configparser.ConfigParser()
        if not parser.read(self.file):
            raise FileNotFoundError(f"Config file not found: {self.file}")
        self.parser = parser

        wy = parser.get("water_year", "water_year", fallback="").strip()
        start = parser.get("water_year", "start", fallback="").strip()
        end = parser.get("water_year", "end", fallback="").strip()
        self.water_year = int(wy) if wy else None
        if self.water_year is None and not (start and end):
            raise ValueError(f"Set [water_year] water_year (or both start and end) in {self.file}")
        self.start = pd.Timestamp(start) if start else pd.Timestamp(f"{self.water_year - 1}-10-01")
        self.end = pd.Timestamp(end) if end else pd.Timestamp(f"{self.water_year}-09-30")
        if self.end < self.start:
            raise ValueError(f"end {self.end:%Y-%m-%d} is before start {self.start:%Y-%m-%d} in {self.file}")

        self.output_dir = self._path(parser.get("paths", "output_dir", fallback="output"))
        self.year_dir = os.path.join(self.output_dir, self.year_label)
        self.download_dir = os.path.join(self.year_dir, DOWNLOAD_FOLDER)
        self.raw_dss = os.path.join(self.download_dir, "obsData_raw.dss")
        self.raw_archive_dir = os.path.join(self.download_dir, "raw_archive")
        self.qaqc_dir = os.path.join(self.download_dir, "QAQC")
        self.edited_dss = os.path.join(self.year_dir, EDITED_FOLDER, "obsData.dss")
        self.results_dir = os.path.join(self.year_dir, RESULTS_FOLDER)
        self.history_csv = os.path.join(self.year_dir, "run_history.csv")
        #The file step 2 reads: the edited copy, unless config.ini points somewhere else
        self.obsdata_dss = self._path(parser.get("paths", "obsdata_dss", fallback="")) or self.edited_dss

        self.network_json = self._path(parser.get("paths", "network_json", fallback="config/network/network.json"))
        self.records_dir = os.path.join(CONFIG_DIR, "records")
        self.damage_points_dir = os.path.join(CONFIG_DIR, "damage_points")
        self.damage_curves_pkl = os.path.join(CONFIG_DIR, "damage_curves", "regulated_damage_curves.pkl")
        self.observed_alt = parser.get("alternatives", "observed", fallback="Obs_NWP_H").strip()
        self.unregulated_alt = parser.get("alternatives", "unregulated", fallback="UnregNWP_H").strip()
        self.make_plots = parser.getboolean("outputs", "make_plots", fallback=True)

    @property
    def year_label(self):
        """WY2025, or start_end for a period set without a water year"""
        if self.water_year is not None:
            return f"WY{self.water_year}"
        return self.period_label

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
            value = os.path.join(DP_PYTHON_DIR, value)
        return os.path.normpath(value)
