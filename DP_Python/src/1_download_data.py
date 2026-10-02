# -*- coding: utf-8 -*-
"""
STEP 1 - Download and check the observed data.

    python src/1_download_data.py

Everything goes in output/WY<year>/ (the water year in config/config.ini):

1_download_for_data_management_review/
    obsData_raw.dss             every USGS and CWMS record the process needs, hourly,
                                exactly as downloaded (rewritten on every download)
    QAQC/                       data checks: USGS vs CWMS records that should match,
                                and spikes / jumps / negatives / flat lines in the
                                CWMS reservoir inflows (tables, and plots in QAQC/plots)
    Combined_Summary_Stats.csv  missing hours and % complete for every record
    FOR DATA MANAGEMENT REVIEW.txt
2_edited_data/obsData.dss       a copy of the raw file, made on the first download
                                only. This is the file you clean in DSSVue and step 2
                                reads; a later download never replaces it.

Records already downloaded for the same period are reused, so an interrupted
download picks up where it stopped (modules/download/dp_download.py,
ReuseDownloaded).

Needs a USGS Water Data API key in config/records/usgs_api_key.txt (one line,
never committed) and access to the CWMS data API.
"""
import datetime
import os
import runpy
import sys

DP_PYTHON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULES_DIR = os.path.join(DP_PYTHON_DIR, "modules")
sys.path.insert(0, MODULES_DIR)
from dp.config import Config, DEFAULT_CONFIG

REVIEW_NOTE = """FOR DATA MANAGEMENT REVIEW
==========================

{label} ({start:%d%b%Y} - {end:%d%b%Y}), downloaded {now:%d%b%Y %H:%M}.

This folder holds the observed data for the Damages Prevented analysis exactly
as it came from the USGS Water Data API and the CWMS data API, and the checks
run on it. It is for reviewing the source data and reporting problems to data
management. Nothing in this folder is edited.

  obsData_raw.dss              every record, hourly, as downloaded
  Combined_Summary_Stats.csv   missing hours, longest gap and % complete per record
  QAQC/Redundant_Pair_*.csv    CWMS records compared with the USGS record that
                               should match them (pool elevations, project outflow
                               vs the gage below the dam): bias, % of hours out of
                               tolerance, datum offsets, time lags, and when
  QAQC/Inflow_Spike_*.csv      spikes, one-hour jumps, negatives and flat lines in
                               the CWMS reservoir inflows
  QAQC/Inflow_Despiked.csv     the inflows with the flagged hours replaced
  QAQC/plots/                  a plot for every pair and every inflow

The data actually used for Damages Prevented is the edited copy in
../2_edited_data/obsData.dss.
"""


def write_review_note(cfg):
    path = os.path.join(cfg.download_dir, "FOR DATA MANAGEMENT REVIEW.txt")
    with open(path, "w") as f:
        f.write(REVIEW_NOTE.format(label=cfg.year_label, start=cfg.start, end=cfg.end,
                                   now=datetime.datetime.now()))
    return path


def main(config_file=DEFAULT_CONFIG):
    os.environ["DP_CONFIG"] = os.path.abspath(config_file)
    cfg = Config(config_file)
    print("=" * 78 + f"\nSTEP 1a - Download {cfg.year_label}\n" + "=" * 78)
    runpy.run_path(os.path.join(MODULES_DIR, "download", "dp_download.py"), run_name="__main__")
    print("\n" + "=" * 78 + "\nSTEP 1b - Data checks (QAQC)\n" + "=" * 78)
    runpy.run_path(os.path.join(MODULES_DIR, "download", "dp_qaqc.py"), run_name="__main__")
    write_review_note(cfg)
    print(f"\nFor data management review: {cfg.download_dir}"
          f"\nNext: clean {cfg.edited_dss} in DSSVue,"
          "\nthen run:  python src/2_run_damages_prevented.py")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    main(args[0] if args else DEFAULT_CONFIG)
