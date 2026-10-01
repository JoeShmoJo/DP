#Ensemble_Plots_Paralell

# -*- coding: utf-8 -*-
"""
parallel_dss_test.py

Standalone test of parallelized DSS reads for Script 2 (ensemble plot script).
Tries parallel reads against the same file. If that causes issues, switch
USE_FILE_CLONE = True to copy the file once per worker into a temp directory.

Run this independently to verify correctness and measure speedup before
integrating into the main script.
"""

# ============================================================
# USER SETTINGS — edit these to match your environment
# ============================================================
import os
from pathlib import Path

DSS_FILE_IN = r"C:\Projects\BA_UPDATE_09Mar2026\BA_ReEval_11Mar2026\rss\BA_07APR2026\simulation.dss"

# Alt name formatting — must match what your main script produces
ALTERNATIVE_NAME_STEP1 = "ConSeson"   # <-- update to match cfg.ALTERNATIVE_NAME_STEP1
TRIAL = 0                              # <-- update to match cfg.TRIAL

FORMATTED_ALT_NAME = ALTERNATIVE_NAME_STEP1.replace(" ", "-")
if len(FORMATTED_ALT_NAME) < 10:
    FORMATTED_ALT_NAME = FORMATTED_ALT_NAME.ljust(10, "-")
FORMATTED_ALT_NAME = FORMATTED_ALT_NAME + str(TRIAL)

# Year range — match your main script
YearRange = range(1981, 2029)

# Number of parallel workers. Start with 4, increase if you have more cores.
N_WORKERS = 4

# Set True to copy DSS file once per worker into temp dir instead of reading
# the same file from all workers simultaneously.
USE_FILE_CLONE = False

# ============================================================
# RESERVOIR / CONTROL POINT MAPS — copied from main script
# ============================================================
RESERVOIR_NAME_MAP = {
    "LOP": "LOOKOUT POINT",
    "DET": "DETROIT",
    "GPR": "GREEN PETER",
    "CGR": "COUGAR",
    "BLU": "BLUE RIVER",
    "FAL": "FALL CREEK",
    "HCR": "HILLS CREEK",
    "DOR": "DORENA",
    "COT": "COTTAGE GROVE",
    "FRN": "FERN RIDGE",
    "FOS": "FOSTER",
}

CONTROL_POINT_MAP = {
    "ALBO": "Willamette_at Albany",
    "NBGO": "Willamette_at Newberg",
    "SLMO": "Willamette_at Salem",
    "WTLO": "So Santiam_at Waterloo",
    "MEHO": "No Santiam_at Mehama",
    "JFFO": "Santiam_at Jefferson",
    "MNRO": "Long Tom_at Monroe",
    "HARO": "Willamette_at Harrisburg",
    "VIDO": "McKenzie_at Vida",
    "EUGO": "Willamette_at Eugene",
    "GOSO": "CF WIllamette_nr Goshen",
    "JASO": "MF Willamette_at Jasper",
}

# ============================================================
# PATH BUILDERS — copied from main script
# ============================================================
def create_elev_paths(fpart):
    return {f"{s}_elev": f"//{l}-POOL/ELEV//1DAY/{fpart}/" for s, l in RESERVOIR_NAME_MAP.items()}

def create_outflow_paths(fpart):
    return {f"{s}_outflow": f"//{l}-POOL/FLOW-OUT//1DAY/{fpart}/" for s, l in RESERVOIR_NAME_MAP.items()}

def create_flow_paths(fpart):
    return {f"{s}_flow": f"//{l}/FLOW//1DAY/{fpart}/" for s, l in CONTROL_POINT_MAP.items()}

def create_salem_unreg_path(unreg_fpart):
    return {"salem_unreg": f"//SLMO3/FLOW-UNREG//1DAY/{unreg_fpart}/"}

def with_fpart_suffix(d, fpart):
    return {f"{k}__{fpart}": v for k, v in d.items()}

def fpart_to_year(fp):
    cpart = fp.split("|")[0]
    return int(cpart.replace("C:", "")[-4:])

OBS_ELEV_PATHS = {
    "BLU": "//BLU/ELEV-FOREBAY//1DAY/MIXED-REV/",
    "COT": "//COT/ELEV-FOREBAY//1DAY/MIXED-REV/",
    "DOR": "//DOR/ELEV-FOREBAY//1DAY/MIXED-REV/",
    "FAL": "//FAL/ELEV-FOREBAY//1DAY/MIXED-REV/",
    "FRN": "//FRN/ELEV-FOREBAY//1DAY/MIXED-REV/",
    "CGR": "//CGR/ELEV-FOREBAY//1DAY/CBT-REV/",
    "DET": "//DET/ELEV-FOREBAY//1DAY/CBT-REV/",
    "FOS": "//FOS/ELEV-FOREBAY//1DAY/CBT-REV/",
    "GPR": "//GPR/ELEV-FOREBAY//1DAY/CBT-REV/",
    "HCR": "//HCR/ELEV-FOREBAY//1DAY/CBT-REV/",
    "LOP": "//LOP/ELEV-FOREBAY//1DAY/CBT-REV/",
}

OBS_OUTFLOW_PATHS = {
    "BLU": "//BLU/FLOW-OUT//1DAY/MIXED-COMPUTED-REV/",
    "COT": "//COT/FLOW-OUT//1DAY/MIXED-COMPUTED-REV/",
    "DOR": "//DOR/FLOW-OUT//1DAY/MIXED-COMPUTED-REV/",
    "FAL": "//FAL/FLOW-OUT//1DAY/MIXED-COMPUTED-REV/",
    "FRN": "//FRN/FLOW-OUT//1DAY/MIXED-COMPUTED-REV/",
    "CGR": "//CGR/FLOW-OUT//1DAY/CBT-REV/",
    "DET": "//DET/FLOW-OUT//1DAY/CBT-REV/",
    "FOS": "//FOS/FLOW-OUT//1DAY/CBT-REV/",
    "GPR": "//GPR/FLOW-OUT//1DAY/CBT-REV/",
    "HCR": "//HCR/FLOW-OUT//1DAY/CBT-REV/",
    "LOP": "//LOP/ELEV-FOREBAY//1DAY/CBT-REV/",
}

# ============================================================
# WORKER FUNCTION
# Must be defined at module level for multiprocessing on Windows
# ============================================================
def _worker(args):
    """
    Each worker receives a chunk of (alias, path) pairs and a DSS file path.
    Returns a dict of {alias: pd.Series} for all successfully read paths.
    """
    import numpy as np
    import pandas as pd
    from pydsstools.heclib.dss import HecDss

    worker_id, dss_path, path_chunk = args
    results = {}

    try:
        fid = HecDss.Open(dss_path)
        for alias, path in path_chunk:
            try:
                ts = fid.read_ts(path, trim_missing=True)
                s = pd.Series(
                    ts.values,
                    index=pd.to_datetime(np.array(ts.pytimes)),
                    name=alias
                )
                results[alias] = s
            except Exception as e:
                print(f"  [Worker {worker_id}] Failed '{alias}': {e}")
        fid.close()
    except Exception as e:
        print(f"  [Worker {worker_id}] Could not open DSS file: {e}")

    print(f"  [Worker {worker_id}] Done — {len(results)}/{len(path_chunk)} paths read")
    return results


# ============================================================
# PARALLEL READ ORCHESTRATOR
# ============================================================
def parallel_readallpaths(dss_file, path_dict, n_workers=4, use_clone=False):
    """
    Split path_dict across n_workers processes, read in parallel,
    concatenate results into a single DataFrame matching the original
    readallpaths() output format.
    """
    import shutil
    import tempfile
    import time
    import multiprocessing
    import pandas as pd

    dss_file = str(dss_file)
    items = list(path_dict.items())  # [(alias, path), ...]

    # Split into N roughly equal chunks
    chunks = [items[i::n_workers] for i in range(n_workers)]
    print(f"\nSplitting {len(items)} paths across {n_workers} workers "
          f"({'file clone mode' if use_clone else 'shared file mode'})")
    for i, c in enumerate(chunks):
        print(f"  Worker {i}: {len(c)} paths")

    # Optionally clone DSS file once per worker
    tmp_dir = None
    worker_dss_paths = []
    if use_clone:
        tmp_dir = tempfile.mkdtemp(prefix="dss_parallel_")
        print(f"\nCloning DSS file {n_workers}x into: {tmp_dir}")
        clone_start = time.perf_counter()
        for i in range(n_workers):
            dst = os.path.join(tmp_dir, f"worker_{i}.dss")
            shutil.copy2(dss_file, dst)
            worker_dss_paths.append(dst)
        clone_elapsed = time.perf_counter() - clone_start
        print(f"  Clone complete in {clone_elapsed:.1f}s")
    else:
        # All workers read from the same file
        worker_dss_paths = [dss_file] * n_workers

    # Build worker args
    worker_args = [
        (i, worker_dss_paths[i], chunks[i])
        for i in range(n_workers)
    ]

    # Run workers
    t_start = time.perf_counter()
    with multiprocessing.Pool(processes=n_workers) as pool:
        worker_results = pool.map(_worker, worker_args)
    t_elapsed = time.perf_counter() - t_start
    print(f"\nParallel read complete in {t_elapsed:.1f}s")

    # Clean up clones
    if use_clone and tmp_dir:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print(f"Temp clones cleaned up")

    # Merge all worker result dicts into one DataFrame
    all_series = {}
    for d in worker_results:
        all_series.update(d)

    if not all_series:
        return pd.DataFrame()

    data = pd.concat(all_series.values(), axis=1)
    data.index = pd.to_datetime(data.index)
    data = data[~data.index.duplicated(keep="last")]
    return data.sort_index()


# ============================================================
# SEQUENTIAL BASELINE (for timing comparison)
# ============================================================
def sequential_readallpaths(dss_file, path_dict):
    """Original sequential read — used for timing comparison."""
    import numpy as np
    import pandas as pd
    import time
    from pydsstools.heclib.dss import HecDss

    dss_file = str(dss_file)
    items = list(path_dict.items())
    dflist = []

    print(f"\nSequential read of {len(items)} paths...")
    t_start = time.perf_counter()

    fid = HecDss.Open(dss_file)
    for alias, path in items:
        try:
            ts = fid.read_ts(path, trim_missing=True)
            df_s = pd.DataFrame(
                ts.values,
                columns=[alias],
                index=pd.to_datetime(np.array(ts.pytimes))
            )
            dflist.append(df_s)
        except Exception as e:
            print(f"  Failed '{alias}': {e}")
    fid.close()

    t_elapsed = time.perf_counter() - t_start
    print(f"Sequential read complete in {t_elapsed:.1f}s")

    if not dflist:
        return pd.DataFrame()

    data = pd.concat(dflist, axis=1)
    data.index = pd.to_datetime(data.index)
    data = data[~data.index.duplicated(keep="last")]
    return data.sort_index()


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    import time
    import pandas as pd

    print("=" * 60)
    print("PARALLEL DSS READ TEST")
    print("=" * 60)
    print(f"DSS file : {DSS_FILE_IN}")
    print(f"Alt name : {FORMATTED_ALT_NAME}")
    print(f"Workers  : {N_WORKERS}")
    print(f"Clone    : {USE_FILE_CLONE}")

    # --- Build the same path_dict as the main script ---
    ensemble_years = list(YearRange)
    synthetic_years = [2026, 2027, 2028]

    ensemble_fparts_model = [f"C:00{year}|{FORMATTED_ALT_NAME}" for year in ensemble_years]
    ensemble_fparts_unreg = [f"C:00{year}|" for year in ensemble_years]

    path_dict = {}

    for fpart in ensemble_fparts_model:
        path_dict.update(with_fpart_suffix(create_elev_paths(fpart), fpart))
        path_dict.update(with_fpart_suffix(create_outflow_paths(fpart), fpart))
        path_dict.update(with_fpart_suffix(create_flow_paths(fpart), fpart))

    path_dict.update({f"{k}_obsElev": v for k, v in OBS_ELEV_PATHS.items()})
    path_dict.update({f"{k}_obsOutflow": v for k, v in OBS_OUTFLOW_PATHS.items()})

    for unreg_fp in ensemble_fparts_unreg:
        yr = fpart_to_year(unreg_fp)
        path_dict[f"salem_unreg__{yr}"] = create_salem_unreg_path(unreg_fp)["salem_unreg"]

    print(f"\nTotal paths to read: {len(path_dict)}")

    # -------------------------------------------------------
    # STEP 1: Run sequential read for baseline timing
    # Comment this out once you've confirmed the parallel
    # result is correct and you just want speed.
    # -------------------------------------------------------
    print("\n--- SEQUENTIAL BASELINE ---")
    t0 = time.perf_counter()
    data_seq = sequential_readallpaths(DSS_FILE_IN, path_dict)
    seq_time = time.perf_counter() - t0
    print(f"Sequential result shape: {data_seq.shape}")

    # -------------------------------------------------------
    # STEP 2: Run parallel read
    # -------------------------------------------------------
    print("\n--- PARALLEL READ ---")
    t0 = time.perf_counter()
    data_par = parallel_readallpaths(
        DSS_FILE_IN,
        path_dict,
        n_workers=N_WORKERS,
        use_clone=USE_FILE_CLONE
    )
    par_time = time.perf_counter() - t0
    print(f"Parallel result shape : {data_par.shape}")

    # -------------------------------------------------------
    # STEP 3: Verify results match
    # -------------------------------------------------------
    print("\n--- VALIDATION ---")
    seq_cols = set(data_seq.columns)
    par_cols = set(data_par.columns)

    missing_in_par = seq_cols - par_cols
    extra_in_par   = par_cols - seq_cols

    if missing_in_par:
        print(f"  WARNING: {len(missing_in_par)} columns in sequential but NOT in parallel:")
        for c in sorted(missing_in_par)[:10]:
            print(f"    {c}")
    if extra_in_par:
        print(f"  WARNING: {len(extra_in_par)} extra columns in parallel not in sequential")
    if not missing_in_par and not extra_in_par:
        print("  Column sets match exactly.")

    # Check a sample of values
    common_cols = list(seq_cols & par_cols)
    if common_cols:
        sample_cols = common_cols[:5]
        print(f"\n  Spot-checking {len(sample_cols)} columns for value agreement...")
        for col in sample_cols:
            s = data_seq[col].dropna()
            p = data_par[col].dropna()
            common_idx = s.index.intersection(p.index)
            if len(common_idx) == 0:
                print(f"    {col}: no overlapping index!")
                continue
            max_diff = (s.loc[common_idx] - p.loc[common_idx]).abs().max()
            print(f"    {col}: max abs diff = {max_diff:.6f}")

    # -------------------------------------------------------
    # STEP 4: Timing summary
    # -------------------------------------------------------
    print("\n--- TIMING SUMMARY ---")
    print(f"  Sequential : {seq_time:.1f}s")
    print(f"  Parallel   : {par_time:.1f}s")
    if par_time > 0:
        print(f"  Speedup    : {seq_time / par_time:.2f}x")

    print("\nDone. If results match and speedup looks good, set USE_FILE_CLONE = True")
    print("if you saw any errors, then re-run to test the clone approach.")