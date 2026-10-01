# Damages Prevented (Willamette, ResSim 4.1)

Mini-simulations that credit each Willamette reservoir with the flow reduction
it produced at each control point. A port of the AFDR damages prevented
scripts (Ryan Cahill) to ResSim 4.1 and the Willamette-only watershed. The
algorithms are unchanged; the Columbia, RAS export, Chart 80, plotting and
Excel parts are gone.

## Run order

1. **Download** `shared/DamagesPrevented/obsData.dss` with the Python
   download script (`src/DP_DL_28Aug2026.py` in the DP repo).
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

The 15 calculated records now live in one file. In the Timeseries tab of
both the Observed and Unregulated alternatives, change the DSS file of these
rows to `shared/DamagesPrevented/DPcalc.dss` (pathnames stay the same):

| From | Records |
|---|---|
| `Locals-Transformed.dss` | `WILLAMETTE FALLS` FLOW-LOC (OCUO_Oregon City) |
| `Locals-FinalWaterBalance.dss` | Albany, Newberg, Salem, Waterloo, Mehama, Jefferson, Monroe, Harrisburg, Vida, Eugene, Goshen, Jasper, Foster_IN, Lookout Point_IN |

Step 2 writes each local to the pathname it is mapped to. If a local is still
mapped to another file, it is written to `DPcalc.dss` anyway and the log says
which row to repoint.

## Files

| Path | What |
|---|---|
| `scripts/DP_Menu.py` | Scripts-pane entry point; opens the menu |
| `scripts/DamagesPrevented/DPSettings.py` | Every file location, the re-reg pairs, negative-local switch |
| `scripts/DamagesPrevented/config/TransformedLocals.csv` | Gage transformations (Willamette Falls) |
| `scripts/DamagesPrevented/config/ControlPoints.txt` | Junctions to report reductions at |
| `scripts/DamagesPrevented/config/Reservoirs.txt` | Reservoirs to run with/without |
| `shared/DamagesPrevented/DPcalc.dss` | Computed locals the alternatives read |
| `shared/DamagesPrevented/MiniSimulations.dss` | Every mini-simulation time series |
| `shared/DamagesPrevented/Results/*.csv` | `Preliminary_per_project`, `Mini-Simulations`, `CP_Peaks`, `Resv_Peaks` |
| `shared/DamagesPrevented/logs/*.log` | One log per step |

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
