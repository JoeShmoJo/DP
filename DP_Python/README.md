# DP_Python: Damages Prevented without ResSim

The Willamette Damages Prevented process in plain Python, isolated from the
working ResSim 4.1 process in `data/ResSim41ExampleScripts/DamagesPrevented`.

**Yearly workflow:** download the data (`DamagesPrevented/DP_Download`), clean it
in DSSVue, set `obsdata_dss` in `config.ini`, then

    python run_dp.py

ResSim is only needed to re-export the network when the network, routing or
alternative mappings change (`export/ExportNetwork.py`).

## What run_dp.py does

The same steps as the ResSim menu, then the damages:

1. Transformed locals: Willamette Falls = 1.5 x Pudding R at Aurora (`config/TransformedLocals.csv`)
2. Water-balance locals for the Observed alternative
3. Observed run (each reservoir releases its Specified Release record) and
   Unregulated run (each reservoir passes inflow), replacing the ResSim computes
4. Mini-simulations and reductions -> `out/Results/` (the same four CSVs as the
   ResSim menu: CP_Peaks, Preliminary_per_project, Mini-Simulations, Resv_Peaks)
5. Damages prevented in dollars -> `out/Damages/` (`damages/calculate_damages.py`,
   a copy of the ResSim folder's Calculate_DP.py, with its damage curves)

About 45 seconds for a water year. Diversions are ignored, as in the ResSim process.

As ResSim does in its computes, INST-VAL inputs (local inflows, specified
releases) are converted to hourly period averages, (previous + current) / 2,
in the Observed and Unregulated runs; the water balance and the gage peaks
use the records as stored, as the ResSim scripts do.

## Validation against ResSim (WY2025, Oct 2026)

Same obsData.dss (`Data/obsData.dss`) and network as the validated ResSim run
(`tests/ResSimDP_Results`):

| Table | Identical | Largest difference |
|---|---|---|
| Resv_Peaks | 33 of 33 | 0 |
| CP_Peaks | 63 of 69 (every unregulated peak) | 100 cfs |
| Preliminary_per_project | 69 of 120 | 50-100 cfs (one rounding step) |
| Mini-Simulations | 574 of 776 | 100 cfs (one 200) |
| **Total damages prevented** | **$268,854,856 both** | per project within 0.12% |

The remaining differences are all one rounding step (peaks are rounded to
100 cfs, reductions to 50). They come from ResSim's own routing engine in its
Observed/Unregulated computes versus the cRouting routing the scripts use; the
underlying flows differ by much less than 100 cfs.

## Layout

```
DP_Python/
  run_dp.py               the one script
  config.ini              obsdata_dss path, network.json path, alternative names, optional [window]
  check_network.py        checks network.json + config.ini and reports what it found
  config/                 ControlPoints.txt, Reservoirs.txt, TransformedLocals.csv, AddedFlowPoints.csv
  network/network.json    the network exported from ResSim
  export/ExportNetwork.py ResSim Scripts-pane tool that writes network.json (Jython)
  dp/                     config, network, dss_io (pydsstools 2.x or 3.x), routing (port of
                          NWDJyLib/cRouting.py), model (the steps), results (the CSVs)
  damages/                calculate_damages.py + regulated_damage_curves.pkl
  Data/obsData.dss        WY2025 data used for validation
  tests/                  test_routing, test_network, test_end_to_end, compare_to_ressim,
                          ResSimDP_Results (validated ResSim output), fixtures
  out/                    Results/ and Damages/ (written by run_dp.py; not committed)
```

## Re-exporting the network

1. In ResSim, Simulation module, open the simulation with the Observed and
   Unregulated alternatives.
2. Scripts pane: paste **all** of `export/ExportNetwork.py` into a script, save, run.
3. Copy `<watershed>/DP_Python_export/network.json` to `network/network.json`.
4. `python check_network.py`

The simulation window in network.json is the default run window; set
`[window]` in config.ini to run a different period.

## Tests

    python tests/test_routing.py        port vs cRouting (fixture from Jython)
    python tests/test_network.py        loader, config, check_network
    python tests/test_end_to_end.py     full WY2025 run vs ResSim (needs pydsstools)
    python tests/compare_to_ressim.py   prints every value that differs
    java -jar jython-standalone-2.7.3.jar DP_Python/export/_offline_tests/test_ExportNetwork.py   (from the repo root)
