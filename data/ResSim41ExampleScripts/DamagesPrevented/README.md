# Damages Prevented (Willamette, ResSim 4.1)

Mini-simulations that credit each Willamette reservoir with the flow reduction
it produced at each control point. A port of the AFDR damages prevented
scripts (Ryan Cahill) to ResSim 4.1 and the Willamette-only watershed. The
algorithms are unchanged; the Columbia, RAS export, Chart 80, plotting and
Excel parts are gone.

Everything Damages Prevented reads and writes is inside this folder, so the
whole process moves with it.

```
DamagesPrevented/
  DP_Menu entry point is scripts/DP_Menu.py (one level up)
  DPMenu.py, DPSettings.py, cTransform.py, cWaterBalance.py, cMiniSims.py   ResSim side (Jython)
  config/          ControlPoints.txt, Reservoirs.txt, TransformedLocals.csv
  DPdata/          DPcalc.dss, MiniSimulations.dss, Results/*.csv, logs/   (written by the menu)
  DP_Download/     desktop Python 3 - ResSim never loads it
    DP_Download.py         downloads USGS/CWMS data -> out/obsData.dss (DSS 7)
    PareDown_Willamette.py one-time: RequiredRecordsDictNWP.csv -> RequiredRecordsDictWIL.csv
    willamette_projects.py, qaqc_records.py   shared by the scripts here
    config/                RequiredRecordsDictWIL.csv, QAQC_RecordsWIL.csv,
                           RedundantPairs_WIL.csv, usgs_api_key.txt (never committed)
    out/                   obsData.dss, Hourly_<start>_<end>.csv, Combined_Summary_Stats.csv
    QAQC/DP_QAQC.py        USGS vs CWMS comparison + inflow spike check -> QAQC/out/
```

## Run order

1. **Download** with `DP_Download/DP_Download.py` (desktop Python; set the
   period at the top). Then optionally run `DP_Download/QAQC/DP_QAQC.py`.
2. In ResSim, open the Simulation module with the simulation that holds the
   Observed and Unregulated alternatives, and run `scripts/DP_Menu.py` from the
   Scripts pane. Pick the two alternatives in the menu, then:
   1. **Transform gage data**: writes the Willamette Falls local (1.5 x
      Pudding River at Aurora) to `DPcalc.dss`.
   2. **Compute water-balance locals**: for the Observed alternative, the
      local at every gaged junction = observed flow - routed flow from
      upstream, written to `DPcalc.dss`.
3. **Compute** the Observed and Unregulated alternatives in ResSim.
4. Back in the menu: **Run mini-simulations**.

## One-time change in the alternative editors

Change only the DSS file column; the pathnames stay the same. In both the
Observed and Unregulated alternatives:

| Rows | DSS file becomes |
|---|---|
| Every row now on `shared/DamagesPrevented/obsData.dss` (Observed tab, specified releases, lookbacks, reservoir inflows, gaged tributaries) | `scripts/DamagesPrevented/DP_Download/out/obsData.dss` |
| `WILLAMETTE FALLS` FLOW-LOC (OCUO_Oregon City), now on `Locals-Transformed.dss` | `scripts/DamagesPrevented/DPdata/DPcalc.dss` |
| The 14 water-balance locals now on `Locals-FinalWaterBalance.dss` (Albany, Newberg, Salem, Waterloo, Mehama, Jefferson, Monroe, Harrisburg, Vida, Eugene, Goshen, Jasper, Foster_IN, Lookout Point_IN) | `scripts/DamagesPrevented/DPdata/DPcalc.dss` |

The zero-flow rows can stay on `shared/DamagesPrevented/Zero Flow record.dss`,
or move that file into `DPdata/` too and repoint them.

Step 2 writes each local to the pathname it is mapped to. If a local is still
mapped to another file, it is written to `DPcalc.dss` anyway and the log says
which row to repoint.

## Files

| Path | What |
|---|---|
| `scripts/DP_Menu.py` | Scripts-pane entry point; opens the menu |
| `DPSettings.py` | Every file location, the re-reg pairs, negative-local switch |
| `config/TransformedLocals.csv` | Gage transformations (Willamette Falls) |
| `config/ControlPoints.txt` | Junctions to report reductions at |
| `config/Reservoirs.txt` | Reservoirs to run with/without |
| `DP_Download/out/obsData.dss` | Downloaded observed data (DSS 7) |
| `DPdata/DPcalc.dss` | Computed locals the alternatives read |
| `DPdata/MiniSimulations.dss` | Every mini-simulation time series |
| `DPdata/Results/*.csv` | `Preliminary_per_project`, `Mini-Simulations`, `CP_Peaks`, `Resv_Peaks` |
| `DPdata/logs/*.log` | One log per step |

The mini-simulations check every name in `ControlPoints.txt` and
`Reservoirs.txt` against the network before computing and list any that don't
exist. Six control points from the old Willamette list are marked unconfirmed
in that file.

## Method

For each reservoir R (Big Cliff runs with Detroit, Dexter with Lookout Point):

- **WITHOUT R**: R's inflow from the Observed run, routed downstream with
  each reach's own routing; locals and tributaries from the Observed run;
  every other reservoir applies its observed outflow - inflow. R and its
  re-reg pass inflow.
- **WITH ONLY R**: the same from the Unregulated run; only R and its re-reg
  apply their observed storage change.

Reduction credited to R at a control point = average of
(unregulated peak - WITH ONLY R peak) and (WITHOUT R peak - observed peak),
peaks rounded to the nearest 100 cfs.

Supported reach routing: SSARR, Muskingum, Modified Puls, Null. Both steps
that route check every reach first and name any they can't reproduce.

## Testing

`_offline_tests/test_DamagesPrevented.py` runs all three steps on a toy
network (two reservoirs, one with a re-reg, a confluence and a transformed
local) under Jython 2.7.3 with the HEC classes stubbed (`fake_hec.py`), and
checks the results against values worked out by hand. From the scripts folder:

    java -jar jython-standalone-2.7.3.jar DamagesPrevented/_offline_tests/test_DamagesPrevented.py

This proves the Python logic. It does not prove that the ResSim 4.1 Java
methods behave like the stubs; only running in ResSim does that.

## Differences from the AFDR version

- CSV output instead of `.xls` (`jxl` is not in ResSim 4.1).
- Transformed and water-balance locals share `DPcalc.dss`. The water-balance
  step loads the inputs already in that file (Willamette Falls) instead of
  skipping the whole file.
- The water-balance step no longer empties its loaded time series when it
  warns about a short or missing record. The original did, and then failed on
  the next local it needed.
- Natural-lake (Columbia) logic removed.
