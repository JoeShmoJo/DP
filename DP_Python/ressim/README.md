# ResSim network export

`config/network/network.json` is the ResSim network the Python process routes flows through:
junctions, reaches and their routing, reservoirs, local inflows, the compute
order, and the Observed / Unregulated alternatives' time series mappings. It
was exported from the ResSim 4.1 Willamette watershed with `ExportNetwork.py` (this folder). ExportNetwork.py is a ResSim (Jython)
script: it runs inside ResSim, not with Python.

It only needs to be re-exported when the ResSim network, the reach routing, or
the alternative mappings change:

1. In ResSim, Simulation module, open the simulation holding the Observed and
   Unregulated alternatives.
2. Scripts pane: paste **all** of `ExportNetwork.py` into a script, save, run.
   (It only reads the model.)
3. Copy `<watershed>/DP_Python_export/network.json` over `config/network/network.json`.
4. Check it:  `python src/check_network.py`
