# -*- coding: utf-8 -*-
"""
STEP 1 - Download and check the observed data.

    python 1_download_data.py

1. Downloads every USGS and CWMS record the Damages Prevented process needs for
   the [period] in config.ini, hourly, and writes them to obsData.dss
   ([paths] obsdata_dss). An existing obsData.dss is moved to data/backup first.
   Records already downloaded for the same period are reused (see
   download/dp_download.py, ReuseDownloaded).
2. Runs the data checks (download/dp_qaqc.py) and writes the tables and plots
   to QAQC/:
     - USGS vs CWMS records that should match (elevations, outflows)
     - spikes, jumps, negatives and flat lines in the CWMS reservoir inflows
   plus data/download/Combined_Summary_Stats.csv (missing hours per record).

Then review QAQC/ and clean obsData.dss in DSSVue (fill gaps, fix spikes)
before step 2.

Needs a USGS Water Data API key in download/config/usgs_api_key.txt (one line,
never committed) and access to the CWMS data API.
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if args:
        os.environ["DP_CONFIG"] = os.path.abspath(args[0])
    print("=" * 78 + "\nSTEP 1a - Download\n" + "=" * 78)
    runpy.run_path(os.path.join(HERE, "download", "dp_download.py"), run_name="__main__")
    print("\n" + "=" * 78 + "\nSTEP 1b - Data checks (QAQC)\n" + "=" * 78)
    runpy.run_path(os.path.join(HERE, "download", "dp_qaqc.py"), run_name="__main__")
    print("\nNext: review QAQC/ and data/download/Combined_Summary_Stats.csv, clean obsData.dss in DSSVue,"
          "\nthen run:  python 2_run_damages_prevented.py")
