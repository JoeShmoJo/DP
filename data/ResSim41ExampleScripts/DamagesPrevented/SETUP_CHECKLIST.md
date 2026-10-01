# Damages Prevented: setup checklist for the new Willamette model (ResSim 4.1)

Work top to bottom. Paths are relative to the watershed folder unless they
start with `DP_REPO/`. `README.md` in this folder explains what each step does;
this file is only what to do.

---

## A. Put the files in place

- [ ] **Back up** the watershed's current `scripts/DP_Menu.py` (it opens the old AFDR menu).
- [ ] **Copy** `DP_REPO/data/ResSim41ExampleScripts/DamagesPrevented/` to `scripts/DamagesPrevented/`.
- [ ] **Copy** `DP_REPO/data/ResSim41ExampleScripts/DP_Menu.py` to `scripts/DP_Menu.py` (replaces the old one).
- [ ] **Check** `scripts/NWDJyLib/` is the ResSim 4.1 version (it already is if the scripts
      folder came from `ResSim41ExampleScripts`). Nothing in it needs changing.
- [ ] **Put your USGS key** in `scripts/DamagesPrevented/DP_Download/config/usgs_api_key.txt`
      (one line, the key only). It is git-ignored.
- [ ] **Optional - reuse your last download:** copy your existing
      `Hourly_2025-10-01_2026-09-30.csv` into `scripts/DamagesPrevented/DP_Download/out/`.
      Then the next download only fetches what's missing (the two Scoggins records).
- [ ] **Zero-flow record:** copy `shared/DamagesPrevented/Zero Flow record.dss` to
      `scripts/DamagesPrevented/DPdata/Zero_Flow_record.dss` (underscores; the repointed tables use that name).

## B. Download the observed data (desktop Python, not ResSim)

- [ ] Close `obsData.dss` in ResSim and DSSVue (the download deletes and rewrites it).
- [ ] Run `scripts/DamagesPrevented/DP_Download/DP_Download.py`. Set `startDate` / `endDate`
      at the top first if the period changes.
- [ ] Confirm `scripts/DamagesPrevented/DP_Download/out/obsData.dss` opens in DSSVue 7
      (it is written as DSS 7). If it doesn't, send the error.
- [ ] Optional: run `DP_Download/QAQC/DP_QAQC.py` and look at `QAQC/out/`.

## C. Clean the data in DSSVue

ResSim needs specified releases, lookbacks and inflows without gaps over the
simulation window, and gaps in a gage carry straight into the water-balance
locals. Missing hours are stored as -902. From the last download's
`out/Combined_Summary_Stats.csv`, the worst records:

| Record | Hours missing | Longest gap (h) | Used for |
|---|---|---|---|
| Willamette R at Newberg 14197900 | 225 | 200 | Observed, water balance |
| Pudding R at Aurora 14202000 | 178 | 165 | Known flow, Willamette Falls local |
| Fern Ridge inflow `//FRN/FLOW-IN` | 169 | 40 | Known flow (reservoir inflow) |
| S Yamhill R at McMinnville 14194150 | 145 | 8 | Known flow |
| Coast Fork nr Goshen 14157500 | 130 | 125 | Observed, water balance |
| Long Tom R nr Alvadore 14169000 | 130 | 0.4 | **Fern Ridge specified release** |
| Willamette R at Salem 14191000 | 94 | 95 | Observed, water balance |
| CWMS inflows (COT, GPR, LOP, DET, DOR, BLU, ...) | ~40 each | ~40 | Known flow (reservoir inflows) |

- [ ] Fill or estimate the gaps in DSSVue, at least for everything used as a specified
      release, lookback or known flow.
- [ ] The ~40-hour CWMS gaps are most likely the end of the water year (downloaded on
      30 Sep). Either end the simulation before the data ends, or re-download later with
      `ReuseDownloaded = False` in `DP_Download.py` (reused records are not refreshed).
- [ ] Times in `obsData.dss` are UTC clock times. All inputs share that, so the method is
      consistent, but peak times in the results are UTC.

## D. Update the model

### D1. Simulation
- [ ] One simulation holding both alternatives (`Obs_NWP_H`, `Unreg_NWP_H`), same network,
      both on a 1-hour time step.
- [ ] Lookback start and end inside the downloaded period (and before any gap at the end).
- [ ] Unregulated alternative: every reservoir passes inflow.

### D2. Repoint DSS files (alternative editors)

Change only the **DSS file** column; leave the A-F parts as they are. Save each alternative.

Ready-made tables: `DP_REPO/data/NewResSimPaths/*_DP.csv` (Obs Observed tab, Obs Timeseries
tab, Unreg Timeseries tab). Open in Excel, copy all rows, paste over the table. For a new
export, run `DP_Download/RepointAlternativeTables.py <export.csv>`. The rows listed below
are what those tables change.

**Observed alternative, Observed Data tab - 39 rows**
`shared/DamagesPrevented/obsData.dss` -> `scripts/DamagesPrevented/DP_Download/out/obsData.dss`

Willamette_at Albany, Willamette_at Newberg, Willamette_at Salem, So Santiam_at Waterloo,
No Santiam_at Mehama, Santiam_at Jefferson, Long Tom_at Monroe, Willamette_at Harrisburg,
McKenzie_at Vida, Willamette_at Eugene, CF WIllamette_nr Goshen, MF Willamette_at Jasper,
Big Cliff_OUT, Detroit_OUT, Foster_OUT, Green Peter_OUT, Fern Ridge_OUT, Blue River_OUT,
Cougar_OUT, Cottage Grove_OUT, Dorena_OUT, Fall Creek_OUT, Dexter_OUT, Lookout Point_OUT,
Hills Creek_OUT, Foster_IN, Lookout Point_IN, and the 12 `-Pool` elevations (Big Cliff,
Detroit, Green Peter, Fern Ridge, Blue River, Cougar, Cottage Grove, Dorena, Fall Creek,
Dexter, Lookout Point, Hills Creek).

**Observed alternative, Timeseries tab - 53 rows**
`shared/DamagesPrevented/obsData.dss` -> `scripts/DamagesPrevented/DP_Download/out/obsData.dss`

- Reservoir inflows: Detroit Inflow, Green Peter Inflow, Fern Ridge Inflow, Blue River Inflow,
  Cougar Inflow, Cottage Grove Inflow, Dorena Inflow, Fall Creek Inflow, Hills Creek Inflow
- Gaged tributaries: CANO_Molalla River at Canby, SUVO_Suver (Luckiamute), AURO_Pudding River
  nr Aurora, MCMO_McMinnville (S Yamhill), WSLO_West Linn (Tualatin)
- For each of the 13 reservoirs: `-Pool` Lookback Elevation, the outlet Lookback Release,
  and `(XXX) Specified Release` (39 rows)

**Observed alternative, Timeseries tab - 15 rows** -> `scripts/DamagesPrevented/DPdata/DPcalc.dss`

- From `Locals-Transformed.dss`: OCUO_Oregon City_HMSsub_WillametteRv_S30 (`WILLAMETTE FALLS`)
- From `Locals-FinalWaterBalance.dss`: ALBO_ Albany, NBGO_Newberg, SLMO_Salem,
  WTLO_Waterloo, MEHO_Mehama, JFFO Santiam_at Jefferson loc, MNRO_Monroe, HARO_Harrisburg,
  VIDO_Vida, EUGO_Willamette at Eugene, GOSO_Goshen, JASO_Jasper,
  Foster Local Inflow_HMSsub_SSantiamRv_S20, Lookout Point Local Inflow_HMSsub_MFWillametteRV_S60

**Unregulated alternative, Timeseries tab**
- [ ] The same 14 inflow / gaged-tributary rows -> `.../DP_Download/out/obsData.dss`
- [ ] The same 15 calculated rows -> `.../DPdata/DPcalc.dss`
- [ ] (The Unregulated alternative has no specified releases, lookbacks or Observed tab rows.)

`DPcalc.dss` doesn't have to exist yet; step 1 creates it.

### D3. Check the network matches what the scripts assume
- [ ] Each of the 14 water-balance locals is attached to the junction that has the matching
      observed flow (e.g. ALBO at Willamette_at Albany, Foster Local Inflow at Foster_IN).
      A water-balance local on a junction **without** observed flow makes step 2 stop.
- [ ] The Willamette Falls local (OCUO) is on a junction **without** observed flow.
- [ ] Reach routing is SSARR, Muskingum, Modified Puls or Null. Steps 2 and 3 check this
      first and name any reach that isn't.

## E. Configure Damages Prevented

- [ ] `scripts/DamagesPrevented/config/ControlPoints.txt`: junction names to report at. All 22
      are checked against the new network's node list (`DP_REPO/data/node _list`). Three old
      names were changed: McKenzie R. NR Walterville -> `Mkenzie_nr Walterville`,
      MF Willamette_blw NFork nr Oakridge -> `MF Willamette NR Oakridge`, and
      Willamette+Clackamas dropped (the network ends at Willamette Falls).
- [ ] `config/Reservoirs.txt`: the 13 projects, spelled as in the network.
- [ ] `DPSettings.py`: only if you want different file locations. `REREG` pairs Big Cliff
      with Detroit and Dexter with Lookout Point.

## F. Run

- [ ] Open the Simulation module with the simulation from D1.
- [ ] **Scripts pane entry (once):** ResSim 4.1 keeps its own copy of a Scripts-pane script and
      runs that copy from `AppData/.../CWMS/<watershed>/scripts/Modules/Simulation/`, so copying
      files into `scripts/` never changes it. Open the "DamagesPrevented" script in the script
      editor, replace **all** its text with `scripts/DamagesPrevented_PasteIntoResSim.txt`, save.
      That launcher runs `scripts/DP_Menu.py` from the watershed every time, so later updates
      need no re-paste. It prints `Running .../scripts/DP_Menu.py`, then `Scripts folder: ...`.
- [ ] Run it. Pick the Observed and Unregulated alternatives.
- [ ] **1. Transform gage data** -> writes `WILLAMETTE FALLS` to `DPdata/DPcalc.dss`.
- [ ] **2. Compute water-balance locals** -> writes the 14 locals to `DPdata/DPcalc.dss`.
      Warnings about short records are OK unless the step stops.
- [ ] **Compute** the Observed and Unregulated alternatives in ResSim. Check that the Observed
      run matches the gages at the control points (if it doesn't, the locals or data are off).
- [ ] **3. Run mini-simulations** -> `DPdata/MiniSimulations.dss` and `DPdata/Results/*.csv`.

## G. If something stops

- [ ] Each step logs to `scripts/DamagesPrevented/DPdata/logs/<step>.log`.
- [ ] Unknown names (control points, reservoirs) are listed - fix the config file and rerun.
- [ ] Anything else: send the log or the error text from the progress window.
