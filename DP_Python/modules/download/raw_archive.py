"""Source-table CSV archives, independent of hourly DSS inputs."""
import datetime
import hashlib
import io
import json
import os
import tempfile
import zipfile

import pandas as pd


def archive_path(directory, source, key, pathname):
    identity = json.dumps([source, str(key), pathname]).encode('utf-8')
    return os.path.join(directory, hashlib.sha256(identity).hexdigest() + '.zip')


def save_raw(directory, source, key, pathname, data, start, end):
    """Save all returned columns and timestamps before filtering or averaging.

    One ZIP per source record allows interrupted downloads to retain completed
    records without repeatedly rewriting a water year's entire archive.
    """
    os.makedirs(directory, exist_ok=True)
    metadata = dict(source=source, download_key=str(key), ressim_path=pathname,
                    start=start, end=end, format_version=1,
                    downloaded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    row_count=len(data),
                    index_name=data.index.name,
                    column_dtypes={str(c): str(t) for c, t in data.dtypes.items()})
    target = archive_path(directory, source, key, pathname)
    fd, temporary = tempfile.mkstemp(dir=directory, suffix='.tmp')
    os.close(fd)
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr('metadata.json', json.dumps(metadata, indent=2))
            z.writestr('data.csv', data.to_csv(index=True))
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
    return target


def read_raw(path):
    """Read only: return metadata and the source table (index in first column)."""
    with zipfile.ZipFile(path) as z:
        metadata = json.loads(z.read('metadata.json'))
        data = pd.read_csv(io.BytesIO(z.read('data.csv')), index_col=0,
                           dtype={k: str for k, v in metadata['column_dtypes'].items()
                                  if v in ('object', 'string')})
    return metadata, data


def has_raw(directory, source, key, pathname, start, end):
    path = archive_path(directory, source, key, pathname)
    if not os.path.exists(path):
        return False
    with zipfile.ZipFile(path) as z:
        metadata = json.loads(z.read('metadata.json'))
        z.getinfo('data.csv')
    return (metadata['start'] == start and metadata['end'] == end
            and metadata['row_count'] > 0)


def load_hourly(directory, start, end):
    """Derive hourly means in memory for the existing QA/QC algorithms.

    Archives themselves keep native resolution, metadata, and missing values.
    No DSS files or download-cache CSVs are opened or modified here.
    """
    series, paths = {}, {}
    period = pd.date_range(pd.Timestamp(start, tz='UTC'),
                           pd.Timestamp(end, tz='UTC') + pd.Timedelta(hours=23), freq='h')
    files = sorted(p for p in os.listdir(directory) if p.endswith('.zip'))
    if not files:
        raise ValueError(f'No raw source archives in {directory}; run step 1 first.')
    for filename in files:
        metadata, data = read_raw(os.path.join(directory, filename))
        if metadata['start'] != start or metadata['end'] != end:
            continue
        source, key = metadata['source'], metadata['download_key']
        if source == 'USGS':
            from willamette_projects import usgs_site
            key = usgs_site(key)
            columns = [c for c in data if str(c).replace('_', '').isdigit()]
            column = 'value' if 'value' in data else columns[0]
            times = data.index
        else:
            column = 'value' if 'value' in data else next(c for c in data if c != 'date-time')
            times = data['date-time'] if 'date-time' in data else data.index
        values = pd.to_numeric(data[column], errors='coerce').to_numpy()
        s = pd.Series(values, index=pd.to_datetime(times, utc=True))
        s = s.mask((s < -9000) | s.isin([-901, -902]))
        series[(source, key)] = s.sort_index().resample('h').mean().reindex(period)
        paths[(source, key)] = metadata['ressim_path']
    if not series:
        raise ValueError(f'No raw archives match {start} to {end}.')
    return series, paths
