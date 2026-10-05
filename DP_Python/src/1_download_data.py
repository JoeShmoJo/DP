# -*- coding: utf-8 -*-
"""
STEP 1 - Download source data, archive it, and create hourly DSS inputs.

    python src/1_download_data.py [config.ini]

Native-resolution source tables are saved as ZIP-compressed CSVs with metadata
in 1_download_for_data_management_review/raw_archive/. Hourly averages go to
obsData_raw.dss; 2_edited_data/obsData.dss is created once and never overwritten.
No data-management QA/QC runs here. Run src/3_assess_data.py separately.
"""
import datetime
import os
import runpy
import sys

DP_PYTHON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULES_DIR = os.path.join(DP_PYTHON_DIR, "modules")
sys.path.insert(0, MODULES_DIR)
from dp.config import Config, DEFAULT_CONFIG

REVIEW_NOTE = """SOURCE DATA ARCHIVE
===================

{label} ({start:%d%b%Y} - {end:%d%b%Y}), downloaded {now:%d%b%Y %H:%M}.

raw_archive/ contains one ZIP per source record: data.csv preserves the source
columns and native timestamps; metadata.json identifies the source, record,
requested period and download time. These are not hourly averages.

obsData_raw.dss contains hourly means for Damages Prevented. The editable copy
is ../2_edited_data/obsData.dss and is never replaced by a later download.

Run python src/3_assess_data.py separately for data-management checks. It reads
only raw_archive/ and writes reports under QAQC/. Neither DSS file is touched.
Existing QAQC reports are not refreshed by a download.
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
    print("=" * 78 + f"\nSTEP 1 - Download {cfg.year_label}\n" + "=" * 78)
    runpy.run_path(os.path.join(MODULES_DIR, "download", "dp_download.py"), run_name="__main__")
    write_review_note(cfg)
    print(f"\nFor data management review: {cfg.download_dir}"
          f"\nNext: clean {cfg.edited_dss} in DSSVue,"
          "\nthen run:  python src/2_run_damages_prevented.py")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    main(args[0] if args else DEFAULT_CONFIG)
