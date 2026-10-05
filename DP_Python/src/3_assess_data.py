"""STEP 3 - Data-management QA/QC of archived source data only.

    python src/3_assess_data.py [config.ini]

Reports are separate from the original and cleaned Damages Prevented DSS files.
"""
import os
import runpy
import sys

DP_PYTHON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULES_DIR = os.path.join(DP_PYTHON_DIR, 'modules')
sys.path.insert(0, MODULES_DIR)
from dp.config import Config, DEFAULT_CONFIG


def main(config_file=DEFAULT_CONFIG):
    cfg = Config(config_file)
    previous = os.environ.get('DP_CONFIG')
    os.environ['DP_CONFIG'] = os.path.abspath(config_file)
    try:
        print(f'STEP 3 - Assess archived source data for {cfg.year_label}')
        runpy.run_path(os.path.join(MODULES_DIR, 'download', 'dp_qaqc.py'),
                       run_name='__main__')
    finally:
        if previous is None:
            os.environ.pop('DP_CONFIG', None)
        else:
            os.environ['DP_CONFIG'] = previous


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    main(args[0] if args else DEFAULT_CONFIG)
