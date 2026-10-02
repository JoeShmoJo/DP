"""Reads DP_Python/config.ini. Relative paths are relative to the config file's folder."""
import configparser
import os
import re

DP_PYTHON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(DP_PYTHON_DIR, "config.ini")


class Config:
    def __init__(self, config_file=DEFAULT_CONFIG):
        self.file = os.path.abspath(config_file)
        self.dir = os.path.dirname(self.file)
        parser = configparser.ConfigParser()
        if not parser.read(self.file):
            raise FileNotFoundError(f"Config file not found: {self.file}")
        self.obsdata_dss = self._path(parser.get("paths", "obsdata_dss", fallback=""))
        self.network_json = self._path(parser.get("paths", "network_json", fallback="network/network.json"))
        self.observed_alt = parser.get("alternatives", "observed", fallback="Obs_NWP_H").strip()
        self.unregulated_alt = parser.get("alternatives", "unregulated", fallback="UnregNWP_H").strip()

    def _path(self, value):
        value = value.strip().strip('"')
        if not value:
            return None
        #A Windows drive path (C:/...) is absolute even when this runs on another OS
        if not os.path.isabs(value) and not re.match(r"^[A-Za-z]:[\\/]", value):
            value = os.path.join(self.dir, value)
        if re.match(r"^[A-Za-z]:[\\/]", value):
            return value
        return os.path.normpath(value)
