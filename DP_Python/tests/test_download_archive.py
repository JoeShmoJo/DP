"""Offline integration tests using source fixtures and real DSS7 files.

Run: python -m unittest discover -s tests
"""
import configparser
import contextlib
import hashlib
import io
import os
from pathlib import Path
import runpy
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'modules'))
sys.path.insert(0, str(ROOT / 'modules' / 'download'))
from dp.config import Config
from dp.dss_io import DssFile
from raw_archive import archive_path, read_raw, save_raw


class DownloadArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        parser = configparser.ConfigParser()
        parser.read(ROOT / 'config' / 'config.ini')
        parser['water_year']['start'] = '2025-01-01'
        parser['water_year']['end'] = '2025-01-01'
        parser['paths']['output_dir'] = str(self.directory / 'output')
        self.ini = self.directory / 'config.ini'
        with self.ini.open('w') as f:
            parser.write(f)
        self.cfg = Config(self.ini)
        records = self.directory / 'records'
        records.mkdir()
        self.cfg.records_dir = str(records)
        self.usgs_path = '/RIVER/14162200/FLOW//1HOUR/USGS/'
        self.cwms_path = '//BLU/FLOW-OUT//1HOUR/CWMS/'
        self.inflow_path = '//BLU/FLOW-IN//1HOUR/CWMS/'
        pd.DataFrame([
            [self.usgs_path, '14162200', 'USGS'],
            [self.cwms_path, 'BLU.Flow-Out.Inst.15Minutes.TEST', 'CWMS'],
            [self.inflow_path, 'BLU.Flow-In.Inst.15Minutes.TEST', 'CWMS'],
        ], columns=['ResSimPath', 'Download_Key', 'Source']).to_csv(
            records / 'RequiredRecordsDictWIL.csv', index=False)
        pd.DataFrame(columns=['ResSimPath', 'Download_Key', 'Source']).to_csv(
            records / 'QAQC_RecordsWIL.csv', index=False)
        pd.DataFrame([dict(Project='BLU', Parameter='FLOW',
                           CWMS_Key='BLU.Flow-Out.Inst.15Minutes.TEST', USGS_Key='14162200',
                           Matched_By='fixture')]).to_csv(records / 'RedundantPairs_WIL.csv', index=False)
        times = pd.date_range('2025-01-01', periods=96, freq='15min', tz='UTC')
        self.usgs = pd.DataFrame(dict(time=times, value=np.arange(96.) + 100,
                                     qualifier=['P'] * 96, monitoring_location_id=['USGS-14162200'] * 96))
        self.cwms = pd.DataFrame(dict(value=np.arange(96.) + 100, quality=[0] * 96), index=times)
        self.patchers = [
            patch('dp.config.Config', return_value=self.cfg),
            patch.dict(os.environ, {'MPLBACKEND': 'Agg', 'MPLCONFIGDIR': str(self.directory / 'mpl')}),
            patch('dataretrieval.waterdata.get_continuous', return_value=(self.usgs.copy(), None)),
            patch('cwms.api.init_session'),
            patch('cwms.get_timeseries', side_effect=lambda *a, **kw: SimpleNamespace(df=self.cwms.copy())),
        ]
        self.mocks = [p.start() for p in self.patchers]
        for p in self.patchers:
            self.addCleanup(p.stop)

    def run_script(self, name):
        with contextlib.redirect_stdout(io.StringIO()):
            script = runpy.run_path(str(ROOT / 'src' / name))
            script['main'](str(self.ini))

    def test_download_archive_resume_and_assessment_isolation(self):
        self.run_script('1_download_data.py')
        self.assertFalse(Path(self.cfg.qaqc_dir).exists())
        self.assertFalse((Path(self.cfg.download_dir) / 'Combined_Summary_Stats.csv').exists())
        path = archive_path(self.cfg.raw_archive_dir, 'USGS', '14162200', self.usgs_path)
        metadata, raw = read_raw(path)
        self.assertEqual(metadata['source'], 'USGS')
        self.assertEqual(len(raw), 96)
        self.assertEqual(raw['qualifier'].tolist(), ['P'] * 96)
        np.testing.assert_array_equal(raw['value'], np.arange(96.) + 100)
        self.assertEqual(pd.to_datetime(raw.index, utc=True)[1].minute, 15)
        with DssFile(self.cfg.raw_dss) as dss:
            hourly = dss.read(self.usgs_path, '2025-01-01', '2025-01-01 23:00')
        np.testing.assert_allclose(hourly.values, np.arange(24.) * 4 + 101.5)

        # A manually edited file must survive downloading again, byte for byte.
        Path(self.cfg.edited_dss).write_bytes(b'manually cleaned DSS fixture')
        self.mocks[2].reset_mock()
        self.mocks[4].reset_mock()
        self.run_script('1_download_data.py')
        self.mocks[2].assert_not_called()
        self.mocks[4].assert_not_called()
        self.assertEqual(Path(self.cfg.edited_dss).read_bytes(), b'manually cleaned DSS fixture')

        # Remove the hourly cache: assessment must still succeed from raw ZIPs.
        for csv in Path(self.cfg.download_dir).glob('Hourly_*.csv'):
            csv.unlink()
        def fingerprints():
            return {p: (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
                    for p in [Path(self.cfg.raw_dss), Path(self.cfg.edited_dss),
                              *Path(self.cfg.raw_archive_dir).glob('*.zip')]}
        before = fingerprints()
        self.run_script('3_assess_data.py')
        self.assertEqual(before, fingerprints())
        summary = pd.read_csv(Path(self.cfg.qaqc_dir) / 'Redundant_Pair_Summary.csv')
        self.assertEqual(summary['Hours Both'].iloc[0], 24)
        self.assertEqual(summary['Bias (CWMS-USGS)'].iloc[0], 0)
        self.assertTrue((Path(self.cfg.qaqc_dir) / 'Inflow_Spike_Summary.csv').exists())

    def test_missing_source_values_are_archived_and_assessed_separately(self):
        self.usgs.loc[:7, 'value'] = -902
        self.mocks[2].return_value = (self.usgs.copy(), None)
        self.cwms.iloc[:8, 0] = -902
        self.run_script('1_download_data.py')
        path = archive_path(self.cfg.raw_archive_dir, 'USGS', '14162200', self.usgs_path)
        _, raw = read_raw(path)
        self.assertEqual(raw['value'].iloc[:8].tolist(), [-902] * 8)
        self.run_script('3_assess_data.py')
        summary = pd.read_csv(Path(self.cfg.qaqc_dir) / 'Combined_Summary_Stats.csv')
        self.assertEqual(summary['Hours Missing'].tolist(), [2, 2, 2])
        self.assertEqual(summary['Longest Missing Gap Hours'].tolist(), [2, 2, 2])

    def test_legacy_hourly_cache_does_not_skip_raw_download(self):
        self.run_script('1_download_data.py')
        for archive in Path(self.cfg.raw_archive_dir).glob('*.zip'):
            archive.unlink()
        self.mocks[2].reset_mock()
        self.mocks[4].reset_mock()
        self.run_script('1_download_data.py')
        self.assertEqual(self.mocks[2].call_count, 1)
        self.assertEqual(self.mocks[4].call_count, 2)
        self.assertEqual(len(list(Path(self.cfg.raw_archive_dir).glob('*.zip'))), 3)

    def test_archive_failure_does_not_replace_dss(self):
        self.run_script('1_download_data.py')
        before = Path(self.cfg.raw_dss).read_bytes()
        for csv in Path(self.cfg.download_dir).glob('Hourly_*.csv'):
            csv.unlink()
        with patch('raw_archive.save_raw', side_effect=OSError('archive storage failure')):
            with self.assertRaisesRegex(RuntimeError, 'Raw archive missing'):
                self.run_script('1_download_data.py')
        self.assertEqual(Path(self.cfg.raw_dss).read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
