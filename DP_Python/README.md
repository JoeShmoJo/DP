# Willamette Damages Prevented (Python)

Computes the flood damages prevented by the 13 Willamette Valley Project
reservoirs for one water year. It works out how much each reservoir lowered
the peak flow at each damage control point, and what that is worth in dollars.

This is the USACE Damages Prevented method: mini-simulations run with and
without each reservoir. It runs entirely in Python. ResSim is only used once,
to export the river network. On WY2025 it reproduces the ResSim 4.1 process:
the total damages prevented match exactly, and every peak is within one
100-cfs rounding step.

---

## Every year: the checklist

Run the commands from the `DP_Python` folder, with the Python environment
active (see [One-time setup](#one-time-setup)). The example is WY2026; use
your water year.

| # | Do this | Command / where |
|---|---|---|
| 1 | Set the water year | `config/config.ini` -> `water_year = 2026` |
| 2 | Download the data and run the data checks | `python src/1_download_data.py` |
| 3 | Send the review folder to data management | `output/WY2026/1_download_for_data_management_review/` |
| 4 | Clean the data in DSSVue | `output/WY2026/2_edited_data/obsData.dss` |
| 5 | Run Damages Prevented | `python src/2_run_damages_prevented.py` |
| 6 | Look at the plots and the log; any pink means data is still missing | `output/WY2026/3_damages_prevented/` |
| 7 | Repeat 4 and 5 until there's no pink left and the results look right | |

Example on Windows:

    conda activate dp_python
    cd C:\Projects\DP\DP_Python
    python src\1_download_data.py
    python src\2_run_damages_prevented.py

The scripts also run from VS Code or Spyder ("Run Python File"); they find
their files on their own, whatever the working folder.

```
 config/config.ini                    water_year = 2026
        |
 src/1_download_data.py      STEP 1   -> output/WY2026/1_download_for_data_management_review/
        |                             -> output/WY2026/2_edited_data/obsData.dss (first time only)
        |
 you, in DSSVue                       clean 2_edited_data/obsData.dss
        |          ^
        v          |  edit and rerun
 src/2_run_damages_prevented.py  STEP 2  -> output/WY2026/3_damages_prevented/  (replaced each run)
                                         -> output/WY2026/run_history.csv       (a line per run)
```

---

## One-time setup

1. **Python environment.** See [`environment/`](environment/README.md):

       conda env create -f environment/environment.yml
       conda activate dp_python

2. **USGS API key** (for step 1). Request one at
   <https://api.waterdata.usgs.gov/signup/>. Save it, alone on one line, as
   `config/records/usgs_api_key.txt`. That file is never committed.

3. **CWMS access** (for step 1). The CWMS data API must be reachable from your
   machine (USACE network or VPN). Corporate certificates are picked up from
   the Windows certificate store automatically.

4. **HEC-DSSVue**, for cleaning the data.

The ResSim network is already exported (`config/network/network.json`). You
only need to export it again if the ResSim model changes; see
[When the ResSim model changes](#when-the-ressim-model-changes).

---

## The water-year folder

Everything for a water year is in `output/WY<year>/`:

```
output/WY2026/
  1_download_for_data_management_review/   the data exactly as downloaded, and its checks.
      FOR DATA MANAGEMENT REVIEW.txt          Never edit anything in here.
      obsData_raw.dss
      Combined_Summary_Stats.csv
      QAQC/  (tables, and plots/)
  2_edited_data/
      obsData.dss                           THE file you clean. Step 2 reads it.
  3_damages_prevented/                      the results of the latest step 2 run
  run_history.csv                           a line for every step 2 run
```

---

## Step 1: download and check the data

    python src/1_download_data.py

It does the following:

- Downloads every USGS gage and CWMS reservoir record the process needs, hourly,
  for the water year. The records are listed in
  `config/records/RequiredRecordsDictWIL.csv`. They are saved to
  `1_download_for_data_management_review/obsData_raw.dss`.
- Saves each record as soon as it finishes downloading, and reuses records it
  already has. **If the download stops part way, run it again**: it picks up
  where it stopped.
- **The first time only**, copies `obsData_raw.dss` to
  `2_edited_data/obsData.dss`, the copy you will clean.
- Runs the data checks and writes them to `QAQC/`. It also writes a
  `FOR DATA MANAGEMENT REVIEW.txt` note explaining the folder.

**Downloading again is safe.** It replaces `obsData_raw.dss` and the checks,
but **never your edited copy**. To start your edits over from a new download,
delete `2_edited_data/obsData.dss` and run step 1 again. It reuses what it
already downloaded, so this is quick.

### What the checks show

| File (in the review folder) | What to look for |
|---|---|
| `Combined_Summary_Stats.csv` | missing hours, longest gap and % complete for every record |
| `QAQC/Redundant_Pair_Summary.csv` and `QAQC/plots/pair_*.png` | CWMS and USGS records that should agree (pool elevations, project outflow vs the gage below the dam): bias, % of hours out of tolerance, datum offsets, time lags |
| `QAQC/Redundant_Pair_Events.csv`, `Redundant_Pair_Monthly.csv` | when and where they disagree |
| `QAQC/Inflow_Spike_Summary.csv`, `Inflow_Spike_Flags.csv`, `QAQC/plots/inflow_*.png` | spikes, one-hour jumps, negatives and flat lines in the CWMS reservoir inflows |
| `QAQC/Inflow_Despiked.csv` | what the inflows look like with the flagged hours replaced |

This folder is what to send to data management: it shows the problems in the
source data as it came from USGS and CWMS. The check settings (tolerances,
spike thresholds) are at the top of `modules/download/dp_qaqc.py`. The records
that are compared are listed in `config/records/RedundantPairs_WIL.csv`.

---

## Clean the data in DSSVue

Open **`output/WY<year>/2_edited_data/obsData.dss`** in DSSVue. Do not open
the raw file in the review folder. Using the checks and step 2's plots as a
guide:

- **Fill the gaps.** `Combined_Summary_Stats.csv` lists every record with
  missing hours. Check the reservoir inflows first, because they drive the
  unregulated flows.
- **Fix the spikes** and other bad values the inflow checks flag.
- **Save** in DSSVue, then run step 2.

---

## Step 2: run Damages Prevented

    python src/2_run_damages_prevented.py

It takes about a minute. It reads `2_edited_data/obsData.dss` and writes
`3_damages_prevented/`, **replacing the previous run**. You can edit and
rerun as often as you like. Close any of its files you have open (Excel, an
image viewer) before running.

### Check that it used your edits

The top of `run_log.txt` shows which DSS file was read and **when it was last
saved**. If that time isn't your last save in DSSVue, the edits weren't saved.

### Missing data is shaded pink

Step 2 can't run with holes in the data. It fills any hour still missing in
obsData.dss with a straight line between the values on either side. Filled
hours are reported in three places:

- **pink in the plots**:
  - **solid pink**: the plotted record itself was missing there (the gage at a
    control point, a reservoir's release or pool elevation);
  - **hatched pink**: a record the modeled flows are built from was missing
    there (an upstream gage, a reservoir inflow or release, a local);
  - the legend gives the number of hours. In the whole-year panels a short
    gap is drawn about a day wide so it can be seen. The hatching isn't
    shifted for travel time down the river.
- **the end of `run_log.txt`**: every record with filled hours, and how many;
- **`obsData_records_used.csv`**: every record step 2 read, and its filled hours.

A straight line across a gap can miss a peak entirely, so **a final run
should have no pink**.

### The results

| Folder / file in `3_damages_prevented/` | Contents |
|---|---|
| `Results/CP_Peaks.csv` | unregulated vs regulated peak flow at each control point, and the flow reduction |
| `Results/Preliminary_per_project.csv` | the reduction at each control point credited to each reservoir |
| `Results/Mini-Simulations.csv` | the WITHOUT / WITH ONLY peaks behind every credited reduction |
| `Results/Resv_Peaks.csv` | each reservoir's peak inflow and its outflow at that time |
| `Damages/damages_prevented.csv` | dollars of damage prevented at each control point (from the damage curves) |
| `Damages/damages_prevented_ByProject.csv` | those dollars shared out to the reservoirs |
| `Plots/ControlPoints/*.png` | unregulated and regulated flow at each control point, for the whole year and around the peak |
| `Plots/Reservoirs/*.png` | unregulated flow, regulated outflow and pool elevation at each reservoir |
| `TimeSeries/` | every hourly series behind the results, including each WITHOUT / WITH ONLY run (not committed to git; rebuilt every run) |
| `obsData_records_used.csv` | every record read from obsData.dss, and its filled hours |
| `run_log.txt`, `config_used.ini` | what ran, and with which settings |

**`run_history.csv`** in the water-year folder gets a line for every run. Each
line has when it ran, when obsData.dss was last saved, the total damages
prevented, and how many hours were filled. It shows how each round of edits
changed the answer.

---

## Settings

| File | What it sets |
|---|---|
| `config/config.ini` | **the water year**, the ResSim alternatives, plots on/off. Optional: `start`/`end` for a shorter period, and `obsdata_dss` to point step 2 at a different DSS file; both are normally left blank |
| `config/records/RequiredRecordsDictWIL.csv` | the records to download, and their DSS pathnames |
| `config/records/QAQC_RecordsWIL.csv`, `RedundantPairs_WIL.csv` | the extra records and record pairs for the data checks |
| `config/damage_points/ControlPoints.txt` | the control points to report |
| `config/damage_points/Reservoirs.txt` | the reservoirs to credit |
| `config/damage_points/TransformedLocals.csv` | locals computed from a gage x a ratio |
| `config/damage_points/AddedFlowPoints.csv` | control points beyond the network (a junction + a gage) |
| `config/network/network.json` | the ResSim network and the alternatives' record mappings |
| `config/damage_curves/regulated_damage_curves.pkl` | the damage curves |

---

## How it works

Step 2 does what the ResSim Damages Prevented menu does, then works out the dollars:

1. **Transformed locals.** The ungaged local inflow above Willamette Falls =
   1.5 x the Pudding River at Aurora.
2. **Water-balance locals.** At each gaged junction, local inflow = observed
   flow - the flow routed down from upstream, so the model reproduces the
   gages.
3. **Observed and Unregulated runs.** The flows are routed through the network
   twice. In the first, every reservoir releases its observed outflow. In the
   second, every reservoir passes its inflow.
4. **Mini-simulations.** For each reservoir, the flows are routed again
   WITHOUT that reservoir (it passes inflow; the others operate as observed),
   and WITH ONLY that reservoir (only it operates). The reduction credited to
   it at a control point is the average of (unregulated peak - WITH ONLY peak)
   and (WITHOUT peak - observed peak), with peaks rounded to 100 cfs. Big
   Cliff runs with Detroit, and Dexter with Lookout Point (re-regulating
   dams).
5. **Damages.** Peak flows are converted to dollars with the damage curves.
   The reductions are grouped and shared by flood storage, as in the original
   Calculate_DP method (`modules/damages/calculate_damages.py`).

Willamette+Clackamas is beyond the network. Its flow is the Willamette above
the Falls plus the Clackamas gage. Diversions are ignored.

---

## When the ResSim model changes

Export the network again only when the ResSim network, the reach routing, or
the Observed / Unregulated alternative mappings change. See
[`ressim/README.md`](ressim/README.md). Then check the export with:

    python src/check_network.py

---

## Folder layout

```
DP_Python/
  README.md                       this file
  config/                         every setting and input that isn't data
    config.ini                    the settings to edit (the water year)
    records/                      records to download, QA/QC pairs, USGS key
    damage_points/                control points, reservoirs, transformed / added-flow points
    network/network.json          the network exported from ResSim
    damage_curves/                the damage curves
  src/                            the scripts you run
    1_download_data.py            STEP 1
    2_run_damages_prevented.py    STEP 2
    check_network.py              checks network.json after a re-export
  modules/                        the code the scripts use (no need to open)
    download/                     download and data checks
    dp/                           Damages Prevented: routing, mini-simulations, plots
    damages/                      the dollars calculation
  ressim/                         ExportNetwork.py (runs inside ResSim, not Python)
  environment/                    the Python environment (environment.yml)
  output/                         one folder per water year (WY2025, WY2026, ...)
```

---

## Relationship to the ResSim process

The ResSim 4.1 version of this process
(`data/ResSim41ExampleScripts/DamagesPrevented` at the repo root) still works
and is unchanged. The Python version was validated against it on WY2025
(`output/WY2025/2_edited_data/obsData.dss`):

- the reservoir peaks are identical;
- every control point and per-project value is within one rounding step;
- the total damages prevented match exactly ($268,854,856).

The small differences come from ResSim's internal routing engine. The Python
routing is a line-for-line port of the routing the ResSim scripts use
(NWDJyLib/cRouting).

---

## Troubleshooting

| Message or problem | What to do |
|---|---|
| `obsData.dss not found` | Run step 1, which makes `2_edited_data/obsData.dss`. Check `water_year` in `config.ini`. |
| My DSSVue edits don't show up | Save in DSSVue. Then check the file name and "last saved" time at the top of `run_log.txt`. |
| Pink in the plots / `missing hours ... were filled` | Data is still missing in obsData.dss. Fill those records in DSSVue (listed at the end of `run_log.txt`). |
| `Could not replace ...3_damages_prevented` | A results file is open in another program. Close it and rerun. |
| `... is not in obsData.dss` | A record the network uses is missing. Check `Combined_Summary_Stats.csv`, or the pathname in `RequiredRecordsDictWIL.csv`. |
| `Alternative ... is not in network.json` | The names in `config.ini [alternatives]` must match the export. |
| Step 1 can't reach CWMS / USGS | Check VPN/network access, the USGS key file, or certificates (see the notes at the top of `modules/download/dp_download.py`). |
| Step 1 stopped part way | Run it again. It reuses what it already downloaded. |
