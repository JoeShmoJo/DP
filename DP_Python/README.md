# Willamette Damages Prevented (Python)

Computes the flood damages prevented by the 13 Willamette Valley Project
reservoirs for a water year: how much each reservoir lowered the peak flow at
each damage control point, and what that is worth in dollars.

It is the USACE Damages Prevented method (mini-simulations with and without
each reservoir) run entirely in Python. ResSim is only used once, to export
the river network. On WY2025 it reproduces the ResSim 4.1 process: identical
total damages prevented, with every peak within one 100-cfs rounding step.

---

## The process at a glance

```
 config/config.ini              set the water year (once per year)
     |
 src/1_download_data.py         STEP 1  download USGS + CWMS data and check it
     |                                  -> output/WY2026/1_download_for_data_management_review/
     |                                  -> output/WY2026/2_edited_data/obsData.dss (a copy, first time only)
     |
 (you)                          send the review folder to data management,
     |                          clean 2_edited_data/obsData.dss in DSSVue
     |
 src/2_run_damages_prevented.py STEP 2  flow reductions, dollars, plots
                                        -> output/WY2026/3_damages_prevented/ (replaced each run)
     ^                                  -> output/WY2026/run_history.csv (a line per run)
     |__________________________ edit and rerun until the data is clean
```

Each water year has its own folder:

```
output/WY2026/
  1_download_for_data_management_review/   the data as downloaded, and its checks. Never edited.
      FOR DATA MANAGEMENT REVIEW.txt
      obsData_raw.dss
      Combined_Summary_Stats.csv
      QAQC/  (tables, and plots/)
  2_edited_data/
      obsData.dss                           the copy you clean; step 2 reads it
  3_damages_prevented/                      the latest step 2 results
  run_history.csv                           total damages and filled hours for every step 2 run
```

---

## One-time setup

1. **Python environment.** See [`environment/`](environment/README.md):

       conda env create -f environment/environment.yml
       conda activate dp_python

2. **USGS API key** (for step 1). Request one at
   <https://api.waterdata.usgs.gov/signup/> and put it, alone on one line, in
   `config/records/usgs_api_key.txt`. That file is never committed.

3. **CWMS access** (for step 1): the CWMS data API must be reachable from
   your machine (USACE network). Corporate certificates are picked up from the
   Windows certificate store automatically.

4. **DSSVue** for cleaning the data.

The network (`config/network/network.json`) is already exported; see
[When the ResSim model changes](#when-the-ressim-model-changes).

---

## Every year

### 1. Set the water year

Edit `config/config.ini`:

```ini
[water_year]
water_year = 2026
```

Everything else in `config.ini` can usually stay as it is. (`start` and `end`
there can narrow the period, and `[paths] obsdata_dss` can point step 2 at a
different DSS file, but normally both are left blank.)

### 2. Download and check the data (step 1)

    python src/1_download_data.py

Everything goes in `output/WY<year>/1_download_for_data_management_review/`:

- Downloads the hourly USGS gage and CWMS reservoir records listed in
  `config/records/RequiredRecordsDictWIL.csv` into `obsData_raw.dss`.
- Each record is saved as soon as it finishes downloading, and records already
  downloaded for the same period are reused. So if the download is interrupted
  or fails part way, just run it again: it picks up where it stopped.
- The first time, it copies `obsData_raw.dss` to
  **`2_edited_data/obsData.dss`**, the file you clean. A later download
  replaces the raw file and the checks, but **never your edited copy**. To
  start your edits over from a new download, delete the edited copy and run
  step 1 again (it reuses what's already downloaded).
- Runs the data checks and writes them to **`QAQC/`**, with a
  `FOR DATA MANAGEMENT REVIEW.txt` note explaining the folder. That folder is
  what to send to data management about problems in the source data.

| File | What to look for |
|---|---|
| `QAQC/Redundant_Pair_Summary.csv` and `plots/pair_*.png` | USGS and CWMS records that should agree (pool elevations, project outflow vs the gage below the dam): bias, % of hours out of tolerance, datum offsets, time lags |
| `QAQC/Redundant_Pair_Events.csv`, `Redundant_Pair_Monthly.csv` | when and where they disagree |
| `QAQC/Inflow_Spike_Summary.csv`, `Inflow_Spike_Flags.csv`, `plots/inflow_*.png` | spikes, one-hour jumps, negatives and flat lines in the CWMS reservoir inflows |
| `QAQC/Inflow_Despiked.csv` | what the inflows look like with the flagged hours replaced |
| `Combined_Summary_Stats.csv` | missing hours, longest gap and % complete for every record |

(The `QAQC/` paths in the table are inside the review folder.) The check
settings (tolerances, spike thresholds) are at the top of
`modules/download/dp_qaqc.py`. Which USGS/CWMS records are compared is in
`config/records/RedundantPairs_WIL.csv`.

### 3. Clean the data in DSSVue

Open `output/WY<year>/2_edited_data/obsData.dss` in DSSVue and fix what the
checks found. Fill gaps, remove spikes, and check the reservoir inflows above
all, because they drive the unregulated flows. Save, then run step 2. Repeat
as often as you like: each run replaces the last one's results.

Step 2 fills any gap still left with a straight line so it can run, but it
lists those records in its log and in `obsData_records_used.csv`, and shades
the filled hours in its plots. A final run should have none.

### 4. Run Damages Prevented (step 2)

    python src/2_run_damages_prevented.py

It takes about a minute. It reads `2_edited_data/obsData.dss` (the log shows
the file and when it was last saved, so you can confirm it picked up your
edits) and writes `output/WY<year>/3_damages_prevented/`, replacing the
previous run. Close any of its files you have open first.

| Folder / file | Contents |
|---|---|
| `Results/CP_Peaks.csv` | unregulated vs regulated peak flow at each control point, and the flow reduction |
| `Results/Preliminary_per_project.csv` | reduction at each control point credited to each reservoir |
| `Results/Mini-Simulations.csv` | the WITHOUT / WITH ONLY peaks behind every credited reduction |
| `Results/Resv_Peaks.csv` | each reservoir's peak inflow and the outflow at that time |
| `Damages/damages_prevented.csv` | dollars of damage prevented at each control point (from the damage curves) |
| `Damages/damages_prevented_ByProject.csv` | those dollars shared out to the reservoirs |
| `Plots/ControlPoints/*.png` | unregulated and regulated flow at each control point, whole year and around the peak |
| `Plots/Reservoirs/*.png` | unregulated flow, regulated outflow and pool elevation at each reservoir |
| | In every plot, **orange shading** marks hours where the plotted record itself (gage, release, pool elevation) was missing and filled by step 2; **grey shading** marks hours where a record the modeled flows are built from (upstream gages, reservoir inflows and releases, locals) was filled. The grey is not lagged for routing, and in the whole-year panels short gaps are drawn about a day wide so they show up. The legend gives the number of filled hours. |
| `TimeSeries/ControlPoints/*.csv` | every hourly series behind the results, including each WITHOUT / WITH ONLY run |
| `TimeSeries/Reservoirs/*.csv` | inflow, outflows and pool elevation |
| `obsData_records_used.csv` | every record step 2 read from obsData.dss, and how many of its hours were filled |
| `run_log.txt`, `config_used.ini` | what ran, with which settings |

Every run also adds a line to `output/WY<year>/run_history.csv`: when it ran,
when obsData.dss was last saved, the total damages prevented, and how many
hours were filled. It shows how each round of edits changed the answer.

---

## How it works

Step 2 does what the ResSim Damages Prevented menu does, then the dollars:

1. **Transformed locals.** Ungaged local inflow above Willamette Falls = 1.5 x
   Pudding River at Aurora (`config/TransformedLocals.csv`).
2. **Water-balance locals.** At each gaged junction, the local inflow =
   observed flow - flow routed down from upstream, so the model reproduces the
   gages.
3. **Observed and Unregulated runs.** The flows are routed through the network
   twice: with every reservoir releasing its observed outflow, and with every
   reservoir passing its inflow.
4. **Mini-simulations.** For each reservoir, the flows are re-routed WITHOUT
   that reservoir (it passes inflow, the others operate as observed) and WITH
   ONLY that reservoir (only it operates). The reduction credited to it at a
   control point is the average of (unregulated peak - WITH ONLY peak) and
   (WITHOUT peak - observed peak), with peaks rounded to 100 cfs. Big Cliff
   runs with Detroit and Dexter with Lookout Point (re-regulating dams).
5. **Damages.** Peak flows are converted to dollars with the damage curves
   (`config/damage_curves/regulated_damage_curves.pkl`). The reductions are
   grouped and shared by flood storage, as in the original Calculate_DP method
   (`modules/damages/calculate_damages.py`).

Willamette+Clackamas is beyond the network. It is the Willamette above the
Falls plus the Clackamas gage (`config/damage_points/AddedFlowPoints.csv`). Diversions are
ignored.

### Settings

| File | What |
|---|---|
| `config/config.ini` | water year, alternatives, plots on/off (and optional path overrides) |
| `config/damage_points/ControlPoints.txt` | control points to report |
| `config/damage_points/Reservoirs.txt` | reservoirs to credit |
| `config/damage_points/TransformedLocals.csv` | locals computed from a gage x ratio |
| `config/damage_points/AddedFlowPoints.csv` | control points beyond the network (junction + gage) |
| `config/records/RequiredRecordsDictWIL.csv` | records to download (and their DSS pathnames) |
| `config/records/QAQC_RecordsWIL.csv`, `RedundantPairs_WIL.csv` | extra records and pairs for the checks |
| `config/network/network.json` | the ResSim network and alternative mappings |
| `config/damage_curves/regulated_damage_curves.pkl` | the damage curves |

---

## When the ResSim model changes

Re-export the network only when the ResSim network, reach routing, or the
Observed / Unregulated alternative mappings change. See
[`ressim/README.md`](ressim/README.md).

## Folder layout

```
DP_Python/
  README.md                       this file
  config/                         every setting and input that isn't data
    config.ini                    the settings to edit (water year)
    records/                      records to download, QA/QC pairs, USGS key
    damage_points/                control points, reservoirs, transformed / added-flow points
    network/network.json          the network exported from ResSim
    damage_curves/                the damage curves
  src/                            the scripts you run
    1_download_data.py            STEP 1
    2_run_damages_prevented.py    STEP 2
    check_network.py              checks network.json after a re-export
  modules/                        the code the scripts use
    download/                     download and data checks
    dp/                           Damages Prevented (routing, mini-simulations, plots)
    damages/                      the dollars calculation
  ressim/                         ExportNetwork.py (runs inside ResSim)
  environment/                    Python environment (environment.yml)
  output/                         one folder per water year (WY2025, WY2026, ...)
```

## Relationship to the ResSim process

The ResSim 4.1 version of this process (`data/ResSim41ExampleScripts/DamagesPrevented`
at the repo root) still works and is unchanged. The Python version was
validated against it on WY2025 (`output/WY2025/2_edited_data/obsData.dss`):

- reservoir peaks are identical;
- every control point and per-project value is within one rounding step;
- total damages prevented match exactly ($268,854,856).

The small differences come from ResSim's internal routing engine. The Python
routing is a line-for-line port of the routing the ResSim scripts use
(NWDJyLib/cRouting).

## Troubleshooting

| Message | Fix |
|---|---|
| `obsData.dss not found` | run step 1 (it makes `2_edited_data/obsData.dss`), or point `[paths] obsdata_dss` at your file |
| `Could not replace ...3_damages_prevented` | a results file is open (Excel, an image viewer): close it and rerun |
| my DSSVue edits don't show up | save in DSSVue, then check the "last saved" time and file name at the top of `run_log.txt` |
| `... is not in obsData.dss` | a record the network maps is missing: check the download summary, or the pathname in `RequiredRecordsDictWIL.csv` |
| `missing hours ... were filled` | gaps left in obsData.dss (shaded in the plots); clean them in DSSVue |
| `Alternative ... is not in network.json` | the names in `config.ini [alternatives]` must match the export |
| step 1 cannot reach CWMS / USGS | VPN/network access, the USGS key file, or certificates (see the notes at the top of `modules/download/dp_download.py`) |
