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
 config.ini                set the water year (once per year)
     |
 1_download_data.py        STEP 1  download USGS + CWMS data -> data/obsData.dss
     |                             data checks               -> QAQC/
     |
 (you)                     review QAQC/, clean data/obsData.dss in DSSVue
     |
 2_run_damages_prevented.py STEP 2 flow reductions, dollars, plots
                                   -> output/<date_time>_<water year>/
```

---

## One-time setup

1. **Python environment.** See [`environment/`](environment/README.md):

       conda env create -f environment/environment.yml
       conda activate dp_python

2. **USGS API key** (for step 1). Request one at
   <https://api.waterdata.usgs.gov/signup/> and put it, alone on one line, in
   `download/config/usgs_api_key.txt`. That file is never committed.

3. **CWMS access** (for step 1): the CWMS data API must be reachable from
   your machine (USACE network). Corporate certificates are picked up from the
   Windows certificate store automatically.

4. **DSSVue** for cleaning the data.

The network (`network/network.json`) is already exported; see
[When the ResSim model changes](#when-the-ressim-model-changes).

---

## Every year

### 1. Set the water year

Edit `config.ini`:

```ini
[period]
start = 2025-10-01
end = 2026-09-30
```

Everything else in `config.ini` can usually stay as it is.

### 2. Download and check the data (step 1)

    python 1_download_data.py

- Downloads the hourly USGS gage and CWMS reservoir records listed in
  `download/config/RequiredRecordsDictWIL.csv`, and writes them to
  `data/obsData.dss`. If `data/obsData.dss` already exists, it is first moved
  to `data/backup/` with a timestamp, so a cleaned file is never lost.
- Records already downloaded for the same period are reused, so re-running
  after a failure only downloads what is missing.
- Runs the data checks and writes them to **`QAQC/`**:

| File | What to look for |
|---|---|
| `QAQC/Redundant_Pair_Summary.csv` and `plots/pair_*.png` | USGS and CWMS records that should agree (pool elevations, project outflow vs the gage below the dam): bias, % of hours out of tolerance, datum offsets, time lags |
| `QAQC/Redundant_Pair_Events.csv`, `Redundant_Pair_Monthly.csv` | when and where they disagree |
| `QAQC/Inflow_Spike_Summary.csv`, `Inflow_Spike_Flags.csv`, `plots/inflow_*.png` | spikes, one-hour jumps, negatives and flat lines in the CWMS reservoir inflows |
| `QAQC/Inflow_Despiked.csv` | what the inflows look like with the flagged hours replaced |
| `data/download/Combined_Summary_Stats.csv` | missing hours, longest gap and % complete for every record |

The check settings (tolerances, spike thresholds) are at the top of
`download/dp_qaqc.py`. Which USGS/CWMS records are compared is in
`download/config/RedundantPairs_WIL.csv`.

### 3. Clean the data in DSSVue

Open `data/obsData.dss` in DSSVue and fix what the checks found. Fill gaps,
remove spikes, and check the reservoir inflows above all, because they drive
the unregulated flows. Step 2 fills any gap still left with a straight line
and lists those records in its log, but a final run should have none.

### 4. Run Damages Prevented (step 2)

    python 2_run_damages_prevented.py

It takes about a minute. Each run writes a new folder,
`output/<date_time>_<start>_<end>/`:

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
| `TimeSeries/ControlPoints/*.csv` | every hourly series behind the results, including each WITHOUT / WITH ONLY run |
| `TimeSeries/Reservoirs/*.csv` | inflow, outflows and pool elevation |
| `run_log.txt`, `config_used.ini` | what ran, with which settings |

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
   (`damages/regulated_damage_curves.pkl`). The reductions are grouped and
   shared by flood storage, as in the original Calculate_DP method
   (`damages/calculate_damages.py`).

Willamette+Clackamas is beyond the network. It is the Willamette above the
Falls plus the Clackamas gage (`config/AddedFlowPoints.csv`). Diversions are
ignored.

### Settings

| File | What |
|---|---|
| `config.ini` | water year, file locations, alternatives, output folder, plots on/off |
| `config/ControlPoints.txt` | control points to report |
| `config/Reservoirs.txt` | reservoirs to credit |
| `config/TransformedLocals.csv` | locals computed from a gage x ratio |
| `config/AddedFlowPoints.csv` | control points beyond the network (junction + gage) |
| `download/config/RequiredRecordsDictWIL.csv` | records to download (and their DSS pathnames) |
| `download/config/QAQC_RecordsWIL.csv`, `RedundantPairs_WIL.csv` | extra records and pairs for the checks |

---

## When the ResSim model changes

Re-export the network only when the ResSim network, reach routing, or the
Observed / Unregulated alternative mappings change. See
[`network/README.md`](network/README.md).

## Folder layout

```
DP_Python/
  README.md                     this file
  config.ini                    the settings to edit
  1_download_data.py            STEP 1
  2_run_damages_prevented.py    STEP 2
  environment/                  Python environment (environment.yml)
  download/                     download + data-check code and their config
  data/                         obsData.dss (+ download/ working files, backup/)
  QAQC/                         data-check tables and plots (written by step 1)
  network/                      network.json, ExportNetwork.py (ResSim), check_network.py
  config/                       control points, reservoirs, transformed / added-flow points
  dp/                           the Damages Prevented code
  damages/                      the dollars calculation and damage curves
  output/                       one timestamped folder per run of step 2
```

## Relationship to the ResSim process

The ResSim 4.1 version of this process (`data/ResSim41ExampleScripts/DamagesPrevented`)
still works and is unchanged. The Python version was validated against it on
WY2025 (the `data/obsData.dss` in this folder):

- reservoir peaks are identical;
- every control point and per-project value is within one rounding step;
- total damages prevented match exactly ($268,854,856).

The small differences come from ResSim's internal routing engine. The Python
routing is a line-for-line port of the routing the ResSim scripts use
(NWDJyLib/cRouting).

## Troubleshooting

| Message | Fix |
|---|---|
| `obsData.dss not found` | run step 1, or point `[paths] obsdata_dss` at your file |
| `... is not in obsData.dss` | a record the network maps is missing: check the download summary, or the pathname in `RequiredRecordsDictWIL.csv` |
| `missing hours ... were filled` | gaps left in obsData.dss; clean them in DSSVue |
| `Alternative ... is not in network.json` | the names in `config.ini [alternatives]` must match the export |
| step 1 cannot reach CWMS / USGS | VPN/network access, the USGS key file, or certificates (see the notes at the top of `download/dp_download.py`) |
