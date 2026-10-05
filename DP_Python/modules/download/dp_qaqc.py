# -*- coding: utf-8 -*-
"""
Created 30Sep2026

QA/QC of the hourly Willamette records written by DP_Download.py.

1. Redundant USGS vs CWMS records
   Pairs a CWMS record with the USGS record that should match it
   (forebay elevation vs the USGS lake gage, project outflow vs the USGS gage
   just downstream) and reports where they disagree:
     - bias / MAE / RMSE / max difference over the hours both have data
     - hours only one source has
     - % of hours outside tolerance, and each run of such hours as an "event"
     - a constant offset (usually a datum difference) for elevations
     - the time shift (lag) that best lines up flows, which shows up when the
       downstream gage lags the project release
   Pairs come from DP_Python/config/records/RedundantPairs_WIL.csv. If that file doesn't exist,
   a draft is built from RequiredRecordsDictWIL.csv + QAQC_RecordsWIL.csv
   using the gages in willamette_projects.py and written there for you to
   check/edit. Edit it and rerun to change pairs. Detroit, Lookout Point and
   Green Peter outflows aren't compared (they release into Big Cliff, Dexter
   and Foster Lakes and power peaking keeps them from matching the gage
   below the downstream dam).

2. Inflow spikes (CWMS computed inflow)
   Flags hours that are
     - SPIKE   : far from the rolling median (Hampel filter)
     - JUMP    : a one-hour jump that immediately reverses
     - NEGATIVE: below zero
     - FLAT    : the same value repeated for FLAT_HOURS or more
   Writes the flagged hours and a de-spiked copy (flagged hours replaced
   with the rolling median) so you can see what a cleaned record looks like.

Run independently with DP_Python/src/3_assess_data.py. Inputs are native-resolution
ZIP source archives and record/pair configuration. Hourly means are derived in
memory for the existing checks. Reports go to QAQC/; neither original nor edited
DSS files are read or written. No inflow recalculation is performed in this iteration.

@author: g2encjer
"""
#%%
import os
import sys

import numpy as np
import pandas as pd

# This script lives in DP_Python/modules/download; every path comes from config/config.ini
try:
    DownloadDir = os.path.dirname(os.path.abspath(__file__))
except NameError:  # running cell-by-cell without __file__ - run from the modules/download folder
    DownloadDir = os.getcwd()
ModulesDir = os.path.dirname(DownloadDir)
for d in (DownloadDir, ModulesDir):
    if d not in sys.path:
        sys.path.insert(0, d)
from dp.config import Config, DEFAULT_CONFIG
from raw_archive import load_hourly
cfg = Config(os.environ.get('DP_CONFIG', DEFAULT_CONFIG))

from willamette_projects import (PROJECTS, param_class, project_for_record,
                                 usgs_site, cwms_location)

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
    print('[WARNING] matplotlib not installed - skipping plots.')

startDate = f'{cfg.start:%Y-%m-%d}'
endDate = f'{cfg.end:%Y-%m-%d}'
RawArchiveDir = cfg.raw_archive_dir
# Records dictionary + the QA/QC-only records built by DP_Download.py
RecordsPaths = [os.path.join(cfg.records_dir, 'RequiredRecordsDictWIL.csv'),
                os.path.join(cfg.records_dir, 'QAQC_RecordsWIL.csv')]
PairsPath = os.path.join(cfg.records_dir, 'RedundantPairs_WIL.csv')
# output/WY<year>/1_download_for_data_management_review/QAQC
OutDir = cfg.qaqc_dir
MakePlots = True

# --- Redundant record tolerances (hourly means) ---
ELEV_TOL_FT = 0.10      # |CWMS - USGS| elevation difference allowed, ft
FLOW_TOL_PCT = 5.0      # flow difference allowed, % of the USGS value ...
FLOW_TOL_CFS = 50.0     # ... but never less than this many cfs
MAX_LAG_HOURS = 6       # search +/- this many hours for the best flow alignment

# --- Inflow spike detection ---
HAMPEL_WINDOW_HOURS = 25   # centered rolling window (odd)
HAMPEL_K = 4.0             # flag when |x - median| > K * 1.4826 * MAD ...
SPIKE_MIN_CFS = 250.0      # ... and the departure is at least this many cfs
SPIKE_MIN_PCT = 25.0       # ... and at least this % of the rolling median
JUMP_MIN_CFS = 500.0       # one-hour up-and-back jump size that gets flagged
FLAT_HOURS = 12            # identical values this many hours in a row


#%% Load
def norm_key(source, key):
    key = str(key).strip()
    return usgs_site(key) if str(source).upper() == 'USGS' else key


def load_records(paths):
    rec = pd.concat([pd.read_csv(p, encoding='utf-8-sig', dtype={'Download_Key': str})
                     for p in paths if os.path.exists(p)], ignore_index=True)
    rec.columns = rec.columns.str.strip()
    rec['Source'] = rec['Source'].str.upper().str.strip()
    rec['Key'] = [norm_key(s, k) for s, k in zip(rec['Source'], rec['Download_Key'])]
    rec['Project'] = [project_for_record(p, k, s) for p, k, s in zip(rec['ResSimPath'], rec['Download_Key'], rec['Source'])]
    rec['Parameter'] = [param_class(p, k) for p, k in zip(rec['ResSimPath'], rec['Download_Key'])]
    return rec


#%% Pairing
def draft_pairs(rec):
    """Guess CWMS/USGS pairs. One row per CWMS ELEV/FLOW record; USGS_Key is
    blank where no match was found so it's obvious what to fill in."""
    # Only reservoir projects - river gages like EUGO have no USGS twin here
    cwms = rec[(rec['Source'] == 'CWMS') & rec['Parameter'].isin(['ELEV', 'FLOW']) & rec['Project'].notna()]
    usgs = rec[rec['Source'] == 'USGS']
    rows = []
    for _, c in cwms.iterrows():
        how = ''
        # 1) same ResSimPath in both sources
        match = usgs[usgs['ResSimPath'] == c['ResSimPath']]
        if len(match):
            how = 'same ResSimPath'
        # 2) known USGS gage for the project
        if not len(match) and c['Project'] in PROJECTS:
            p = PROJECTS[c['Project']]
            site = p['usgs_elev'] if c['Parameter'] == 'ELEV' else p['usgs_outflow']
            match = usgs[usgs['Key'] == str(site)] if site else usgs.iloc[0:0]
            if len(match):
                how = 'willamette_projects.py gage'
        # 3) same project + parameter
        if not len(match) and c['Project']:
            match = usgs[(usgs['Project'] == c['Project']) & (usgs['Parameter'] == c['Parameter'])]
            if len(match):
                how = 'same project + parameter'
        if len(match) > 1:
            how += f' ({len(match)} candidates, using first - check)'
        if (not len(match) and c['Parameter'] == 'FLOW' and c['Project'] in PROJECTS
                and not PROJECTS[c['Project']]['usgs_outflow']):
            how = 'not compared - no outflow gage (see willamette_projects.py)'
        rows.append({
            'Project': c['Project'] or cwms_location(c['Key']),
            'Parameter': c['Parameter'],
            'CWMS_Key': c['Key'],
            'USGS_Key': match['Key'].iloc[0] if len(match) else '',
            'Matched_By': how or 'NO MATCH - fill in USGS_Key',
            'CWMS_ResSimPath': c['ResSimPath'],
            'USGS_ResSimPath': match['ResSimPath'].iloc[0] if len(match) else '',
        })
    return pd.DataFrame(rows).sort_values(['Project', 'Parameter'])


def tolerance(param, usgs):
    if param == 'ELEV':
        return pd.Series(ELEV_TOL_FT, index=usgs.index)
    return np.maximum(usgs.abs() * FLOW_TOL_PCT / 100.0, FLOW_TOL_CFS)


def runs(mask):
    """Start/end index positions of each run of True in a boolean array."""
    m = np.concatenate([[False], np.asarray(mask, bool), [False]])
    d = np.diff(m.astype(int))
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0] - 1))


def best_lag(cwms, usgs, max_lag):
    """Lag (hours) of USGS behind CWMS that minimizes MAE."""
    best = (0, np.nan)
    for lag in range(-max_lag, max_lag + 1):
        mae = (cwms.shift(lag) - usgs).abs().mean()
        if np.isfinite(mae) and (np.isnan(best[1]) or mae < best[1] - 1e-9):
            best = (lag, mae)
    return best


def compare_pair(row, cwms, usgs):
    idx = cwms.index.union(usgs.index)
    cwms, usgs = cwms.reindex(idx), usgs.reindex(idx)
    both = cwms.notna() & usgs.notna()
    diff = (cwms - usgs).where(both)
    tol = tolerance(row['Parameter'], usgs)
    exceed = (diff.abs() > tol) & both
    d = diff.dropna()
    stats = {
        'Project': row['Project'], 'Parameter': row['Parameter'],
        'CWMS_Key': row['CWMS_Key'], 'USGS_Key': row['USGS_Key'],
        'Hours CWMS': int(cwms.notna().sum()), 'Hours USGS': int(usgs.notna().sum()),
        'Hours Both': int(both.sum()),
        'Hours CWMS Only': int((cwms.notna() & usgs.isna()).sum()),
        'Hours USGS Only': int((usgs.notna() & cwms.isna()).sum()),
        'Bias (CWMS-USGS)': d.mean(), 'Median Diff': d.median(),
        'MAE': d.abs().mean(), 'RMSE': np.sqrt((d ** 2).mean()),
        'Max Abs Diff': d.abs().max() if len(d) else np.nan,
        'Max Abs Diff Time': d.abs().idxmax() if len(d) else pd.NaT,
        'Hours Outside Tol': int(exceed.sum()),
        'Pct Outside Tol': 100.0 * exceed.sum() / both.sum() if both.sum() else np.nan,
    }
    flags = []
    if row['Parameter'] == 'ELEV' and len(d) and abs(stats['Median Diff']) > ELEV_TOL_FT:
        # A constant offset with little scatter points at a datum difference
        spread = (d - d.median()).abs().median()
        flags.append(f"constant offset {stats['Median Diff']:+.2f} ft (datum?)" if spread <= ELEV_TOL_FT
                     else f"median diff {stats['Median Diff']:+.2f} ft")
    if row['Parameter'] == 'FLOW':
        lag, lag_mae = best_lag(cwms, usgs, MAX_LAG_HOURS)
        stats['Best Lag Hours (USGS behind CWMS)'] = lag
        stats['MAE at Best Lag'] = lag_mae
        if lag != 0 and lag_mae < 0.8 * stats['MAE']:
            flags.append(f'USGS lines up better shifted {lag:+d} h')
    if stats['Pct Outside Tol'] and stats['Pct Outside Tol'] > 5:
        flags.append(f"{stats['Pct Outside Tol']:.1f}% of hours outside tolerance")
    missing = max(stats['Hours CWMS Only'], stats['Hours USGS Only'])
    if missing > 24:
        flags.append(f'{missing} h only in one source')
    stats['Flags'] = '; '.join(flags)

    events = []
    for s, e in runs(exceed.to_numpy()):
        seg = slice(idx[s], idx[e])
        events.append({
            'Project': row['Project'], 'Parameter': row['Parameter'],
            'CWMS_Key': row['CWMS_Key'], 'USGS_Key': row['USGS_Key'],
            'Start': idx[s], 'End': idx[e], 'Hours': e - s + 1,
            'Mean Diff': diff[seg].mean(), 'Max Abs Diff': diff[seg].abs().max(),
            'CWMS Mean': cwms[seg].mean(), 'USGS Mean': usgs[seg].mean(),
        })

    monthly = pd.DataFrame({'absdiff': diff.abs(), 'exceed': exceed.where(both)})
    monthly = monthly.groupby(monthly.index.to_period('M')).agg(
        MAE=('absdiff', 'mean'), Hours_Both=('absdiff', 'count'), Hours_Outside_Tol=('exceed', 'sum'))
    monthly.insert(0, 'USGS_Key', row['USGS_Key'])
    monthly.insert(0, 'CWMS_Key', row['CWMS_Key'])
    monthly.insert(0, 'Parameter', row['Parameter'])
    monthly.insert(0, 'Project', row['Project'])
    return stats, events, monthly.reset_index(names='Month'), (cwms, usgs, diff, tol)


#%% Inflow spikes
def inflow_flags(s):
    s = s.astype(float)
    med = s.rolling(HAMPEL_WINDOW_HOURS, center=True, min_periods=HAMPEL_WINDOW_HOURS // 2).median()
    mad = (s - med).abs().rolling(HAMPEL_WINDOW_HOURS, center=True, min_periods=HAMPEL_WINDOW_HOURS // 2).median()
    dep = s - med
    thresh = np.maximum.reduce([HAMPEL_K * 1.4826 * mad.fillna(0),
                                pd.Series(SPIKE_MIN_CFS, index=s.index),
                                SPIKE_MIN_PCT / 100.0 * med.abs().fillna(0)])
    spike = dep.abs() > thresh

    up = s.diff()
    down = s.shift(-1) - s
    jump = (up.abs() >= JUMP_MIN_CFS) & (down.abs() >= JUMP_MIN_CFS) & (np.sign(up) == -np.sign(down))

    negative = s < 0

    same = s.diff().eq(0) & s.notna()
    flat = pd.Series(False, index=s.index)
    for a, b in runs(same.to_numpy()):
        if b - a + 2 >= FLAT_HOURS:           # run of zero diffs covers b-a+2 values
            flat.iloc[a - 1 if a > 0 else a:b + 1] = True

    flags = pd.DataFrame({'SPIKE': spike, 'JUMP': jump, 'NEGATIVE': negative, 'FLAT': flat}).fillna(False)
    flagged = flags.any(axis=1)
    reason = flags.apply(lambda r: ','.join(c for c in flags.columns if r[c]), axis=1)
    detail = pd.DataFrame({'value': s, 'rolling_median': med, 'departure': dep, 'Flags': reason})[flagged]
    cleaned = s.where(~(flags['SPIKE'] | flags['JUMP'] | flags['NEGATIVE']), med)
    return flags, detail, cleaned, med


#%% Plots
BLUE, ORANGE, INK, MUTED = '#2a78d6', '#eb6834', '#1f1f1e', '#8a897f'


def style(ax):
    ax.grid(True, color='#e6e5df', linewidth=0.6)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    ax.spines['left'].set_color(MUTED)
    ax.spines['bottom'].set_color(MUTED)
    ax.tick_params(colors=INK, labelsize=8)


def plot_pair(stats, cwms, usgs, diff, tol, units, png):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 7), sharex=True,
                                   gridspec_kw={'height_ratios': [2, 1]})
    ax1.plot(cwms.index, cwms, color=BLUE, lw=1.2, label=f"CWMS {stats['CWMS_Key']}")
    ax1.plot(usgs.index, usgs, color=ORANGE, lw=1.2, label=f"USGS {stats['USGS_Key']}")
    ax1.set_ylabel(units, color=INK)
    ax1.legend(frameon=False, fontsize=8, ncol=2, loc='lower right', bbox_to_anchor=(1, 1))
    ax1.set_title(f"{stats['Project']} {stats['Parameter']}: CWMS vs USGS", loc='left', fontsize=11, color=INK)
    ax2.fill_between(tol.index, -tol, tol, color='#e6e5df', label='Tolerance', step='mid')
    ax2.plot(diff.index, diff, color=INK, lw=0.9, label='CWMS - USGS')
    ax2.set_ylabel(f'Diff ({units})', color=INK)
    ax2.legend(frameon=False, fontsize=8, ncol=2, loc='lower right', bbox_to_anchor=(1, 1))
    for ax in (ax1, ax2):
        style(ax)
    fig.tight_layout()
    fig.savefig(png, dpi=120)
    plt.close(fig)


def plot_inflow(key, s, med, flags, png):
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.plot(s.index, s, color=BLUE, lw=1.0, label=f'CWMS inflow {key}')
    ax.plot(med.index, med, color=MUTED, lw=1.0, label=f'{HAMPEL_WINDOW_HOURS} h rolling median')
    f = flags.any(axis=1)
    ax.scatter(s.index[f], s[f], marker='x', s=36, color=INK, lw=1.2, label=f'Flagged ({int(f.sum())} h)', zorder=3)
    ax.set_ylabel('CFS', color=INK)
    ax.set_title(f'{key}: inflow spike check', loc='left', fontsize=11, color=INK)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc='lower right', bbox_to_anchor=(1, 1))
    style(ax)
    fig.tight_layout()
    fig.savefig(png, dpi=120)
    plt.close(fig)


def safe_name(text):
    return ''.join(ch if ch.isalnum() or ch in '-_.' else '_' for ch in str(text))


#%% Run
if __name__ == '__main__':
    os.makedirs(OutDir, exist_ok=True)
    plot_dir = os.path.join(OutDir, 'plots')
    if MakePlots and plt is not None:
        os.makedirs(plot_dir, exist_ok=True)

    if not os.path.isdir(RawArchiveDir):
        sys.exit(f'No raw source archive: {RawArchiveDir}. Run src/1_download_data.py first.')
    series, paths = load_hourly(RawArchiveDir, startDate, endDate)
    completeness_rows = []
    for identity, values in series.items():
        valid = values.dropna()
        gaps = runs(values.isna())
        completeness_rows.append({
            'Source': identity[0], 'Download_Key': identity[1],
            'DataFrame': paths[identity],
            'First Timestamp': valid.index.min() if len(valid) else None,
            'Last Timestamp': valid.index.max() if len(valid) else None,
            'Hours Expected': len(values), 'Hours Missing': int(values.isna().sum()),
            'Longest Missing Gap Hours': max((end - start + 1 for start, end in gaps), default=0),
            'Pct Complete': 100.0 * len(valid) / len(values) if len(values) else np.nan,
        })
    pd.DataFrame(completeness_rows).to_csv(os.path.join(OutDir, 'Combined_Summary_Stats.csv'), index=False)
    rec = load_records(RecordsPaths)

    # ---- Redundant records ----
    if os.path.exists(PairsPath):
        pairs = pd.read_csv(PairsPath, dtype={'CWMS_Key': str, 'USGS_Key': str}).fillna('')
        print(f'Using pairs from {PairsPath}')
    else:
        pairs = draft_pairs(rec)
        draft_path = os.path.join(OutDir, 'RedundantPairs_draft.csv')
        pairs.to_csv(draft_path, index=False)
        print(f'Drafted {draft_path} - review before adding to config/records.')
    print(pairs[['Project', 'Parameter', 'CWMS_Key', 'USGS_Key', 'Matched_By']].to_string(index=False))

    all_stats, all_events, all_monthly = [], [], []
    for _, row in pairs.iterrows():
        ckey, ukey = str(row['CWMS_Key']).strip(), usgs_site(row['USGS_Key'])
        if not ckey or not ukey:
            continue
        if ('CWMS', ckey) not in series or ('USGS', ukey) not in series:
            print(f"[WARNING] No hourly data for pair {ckey} / {ukey}")
            continue
        row = row.copy()
        row['CWMS_Key'], row['USGS_Key'] = ckey, ukey
        stats, events, monthly, (c, u, d, t) = compare_pair(row, series[('CWMS', ckey)], series[('USGS', ukey)])
        all_stats.append(stats)
        all_events += events
        all_monthly.append(monthly)
        if MakePlots and plt is not None:
            units = 'FEET' if row['Parameter'] == 'ELEV' else 'CFS'
            plot_pair(stats, c, u, d, t, units,
                      os.path.join(plot_dir, safe_name(f"pair_{row['Project']}_{row['Parameter']}_{ckey}_{ukey}.png")))

    if all_stats:
        pair_summary = pd.DataFrame(all_stats).sort_values('Pct Outside Tol', ascending=False)
        pair_summary.to_csv(os.path.join(OutDir, 'Redundant_Pair_Summary.csv'), index=False, float_format='%.3f')
        pd.DataFrame(all_events).to_csv(os.path.join(OutDir, 'Redundant_Pair_Events.csv'), index=False, float_format='%.3f')
        pd.concat(all_monthly).to_csv(os.path.join(OutDir, 'Redundant_Pair_Monthly.csv'), index=False, float_format='%.3f')
        print('\n---- Redundant pair summary ----')
        print(pair_summary[['Project', 'Parameter', 'Hours Both', 'Bias (CWMS-USGS)', 'MAE',
                            'Max Abs Diff', 'Pct Outside Tol', 'Flags']].round(2).to_string(index=False))
    else:
        print('No redundant pairs compared.')

    # ---- Inflow spikes ----
    inflow_keys = [(s, k) for (s, k), p in paths.items() if param_class(p, k) == 'INFLOW']
    spike_summary, spike_detail, cleaned_all = [], [], []
    for source, key in inflow_keys:
        s = series[(source, key)]
        flags, detail, cleaned, med = inflow_flags(s)
        spike_summary.append({
            'Download_Key': key, 'ResSimPath': paths[(source, key)],
            'Hours With Data': int(s.notna().sum()),
            **{f'Hours {c}': int(flags[c].sum()) for c in flags.columns},
            'Hours Flagged': int(flags.any(axis=1).sum()),
            'Min': s.min(), 'Max': s.max(),
        })
        detail.insert(0, 'Download_Key', key)
        spike_detail.append(detail.reset_index(names='time_utc'))
        cleaned_all.append(pd.DataFrame({'time_utc': cleaned.index, 'Download_Key': key,
                                         'ResSimPath': paths[(source, key)],
                                         'value': s.to_numpy(), 'despiked': cleaned.to_numpy()}))
        if MakePlots and plt is not None:
            plot_inflow(key, s, med, flags, os.path.join(plot_dir, safe_name(f'inflow_{key}.png')))

    if spike_summary:
        summary = pd.DataFrame(spike_summary).sort_values('Hours Flagged', ascending=False)
        summary.to_csv(os.path.join(OutDir, 'Inflow_Spike_Summary.csv'), index=False, float_format='%.2f')
        pd.concat(spike_detail).to_csv(os.path.join(OutDir, 'Inflow_Spike_Flags.csv'), index=False, float_format='%.2f')
        pd.concat(cleaned_all).to_csv(os.path.join(OutDir, 'Inflow_Despiked.csv'), index=False, float_format='%.2f')
        print('\n---- Inflow spike summary ----')
        print(summary.drop(columns='ResSimPath').round(1).to_string(index=False))
    else:
        print('No inflow records found (ResSimPath C part FLOW-IN or tsid .Flow-In).')

    print(f'\nOutputs written to {os.path.abspath(OutDir)}')
