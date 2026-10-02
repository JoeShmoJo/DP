# -*- coding: utf-8 -*-
"""
dp.routing against NWDJyLib/cRouting.py: the same hydrograph routed by the
original Jython code (saved in fixtures/routing_cRouting.json) and by the port.

    python tests/test_routing.py
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from dp.routing import ModPulsReach, MuskingumReach, SsarrReach, NullReach, build_reach

data = json.load(open(os.path.join(HERE, "fixtures", "routing_cRouting.json")))
q = data["inflow"]
reaches = {
    "puls": ModPulsReach([0., 500., 3000., 9000., 20000.], [0., 800., 15000., 40000., 90000.], 3),
    "musk": MuskingumReach(6.0, 0.2, 3),
    "ssarr": SsarrReach(4, kts=40., n=-0.2),
    "ssarr_tbl": SsarrReach(3, table={"outflow": [1., 1000., 10000., 50000.], "timeOfStorage": [30., 12., 4., 2.]}),
}
fails = 0
for name, reach in reaches.items():
    diff = float(np.max(np.abs(reach.route(q) - np.array(data["cRouting"][name]))))
    ok = diff < 1e-6
    fails += not ok
    print(("  ok    " if ok else "  FAIL  ") + f"{name}: max difference from cRouting {diff:.2e} cfs")
ok = np.array_equal(NullReach().route(q), np.array(q))
fails += not ok
print(("  ok    " if ok else "  FAIL  ") + "Null routing returns the inflow")
ok = build_reach({"method": "Lag"}) is None and isinstance(build_reach({"method": "Null"}), NullReach)
fails += not ok
print(("  ok    " if ok else "  FAIL  ") + "build_reach: unsupported -> None")
print("\n" + (f"{fails} FAILED" if fails else "ALL PASSED"))
sys.exit(1 if fails else 0)
