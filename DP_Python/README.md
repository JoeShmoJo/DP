# DP_Python: Damages Prevented without ResSim

The Willamette Damages Prevented process in plain Python, isolated from the
working ResSim 4.1 process in `data/ResSim41ExampleScripts/DamagesPrevented`.
The goal: download the data, clean it in DSSVue, run one script.

ResSim is only needed to export the network (once, and again when the network,
routing or alternative mappings change).

## Layout

```
DP_Python/
  config.ini              obsdata_dss path (set this), network.json path, alternative names
  check_network.py        checks network.json + config.ini and reports what it found
  export/
    ExportNetwork.py      ResSim Scripts-pane tool: writes network.json (Jython, runs in ResSim)
    _offline_tests/       Jython test of the exporter with stubbed HEC classes
  network/network.json    the exported network (copy it here from the watershed)
  dp/                     the Python package
    config.py, network.py (done)
  tests/                  CPython tests; fixtures/toy_network.json comes from the exporter test
```

## Plan

1. **Export the network from ResSim** (done, this folder):
   `export/ExportNetwork.py` writes junctions, reaches and their routing
   (SSARR, Muskingum, Modified Puls, Null with all parameters), reservoirs,
   local inflows and their multipliers, the compute order, headwaters,
   confluences, each reservoir's downstream path, and the Observed Data and
   Time-Series mappings of every alternative in the simulation.
2. **Python package** (next): read obsData.dss (pydsstools), port the routing
   (`NWDJyLib/cRouting.py`), and the Damages Prevented steps: Willamette Falls
   transformed local, water-balance locals, Observed run (observed releases),
   Unregulated run (pass inflow), mini-simulations, result CSVs, then the
   damages (`calculate_damages/Calculate_DP.py`). One script runs it all.
3. **Validate against ResSim** on the same window: locals vs DPcalc.dss,
   junction flows vs simulation.dss, reductions vs the ResSim result CSVs.
4. **Yearly workflow**: download, clean in DSSVue, `python run_dp.py`.

## Step 1: export the network

1. In ResSim, Simulation module, open the simulation with the Observed and
   Unregulated alternatives.
2. Scripts pane: create a new script (e.g. "ExportNetwork"), paste in **all**
   of `export/ExportNetwork.py`, save, run. It only reads the model.
3. It prints `Exported <watershed>/DP_Python_export/network.json` with element
   counts, and warns about any reach routing DP_Python can't reproduce.
4. Copy that file to `DP_Python/network/network.json` and commit it.

Then set `obsdata_dss` in `config.ini` and run:

    python check_network.py

It lists each reservoir's Specified Release record, where every local inflow
comes from, and anything that would stop a run.

## Tests

    java -jar jython-standalone-2.7.3.jar DP_Python/export/_offline_tests/test_ExportNetwork.py   (from the repo root)
    python DP_Python/tests/test_network.py

The exporter test runs the real ExportNetwork.py and NWDJyLib against stubbed
HEC classes; only ResSim proves the actual API calls.
