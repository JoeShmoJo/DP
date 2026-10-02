# -*- coding: utf-8 -*-
"""
Tests for dp.network, dp.config and check_network.py, using the toy network that
export/_offline_tests/test_ExportNetwork.py exported (tests/fixtures/toy_network.json).

    python tests/test_network.py
"""
import io
import os
import shutil
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from dp.config import Config
from dp.network import Network
import check_network

FIXTURE = os.path.join(HERE, "fixtures", "toy_network.json")
FAILS = []


def check(cond, msg):
    print(("  ok    " if cond else "  FAIL  ") + msg)
    if not cond:
        FAILS.append(msg)


print("\n== Loading the exported network")
net = Network.load(FIXTURE)
check(sorted(net.junctions) == ["junction:Conf", "junction:J1", "junction:Mouth", "junction:Res_IN", "junction:Res_OUT", "junction:T1"],
      "junctions")
check(net.element("reach:R1")["routing"]["method"] == "SSARR" and net.unsupported_reaches() == [], "routing supported")
check(net.reservoir_of_pool("pool:Res") == "reservoir:Res", "pool -> reservoir")
check(net.order[0] in net.headwater_junctions and net.order[-1] == "junction:Mouth", "compute order runs headwater to mouth")
obs = net.alternatives["Obs_NWP_H"]
rec = obs.input_record("~J1 Local:known", net.vid["NODE_KNOWNFLOW"])
check(rec is not None and rec.pathname == "//J1/FLOW-IN//1HOUR/CWMS/" and not rec.is_blank, "local inflow record by proxy name + variable id")
check(net.specified_release("Obs_NWP_H", "Res").pathname == "//RES/FLOW-OUT//1HOUR/CWMS/", "Specified Release found by reservoir name")
check(net.specified_release("Obs_NWP_H", "Nope") is None, "no Specified Release -> None")

print("\n== Config and check_network.py")
tmp = tempfile.mkdtemp()
os.makedirs(os.path.join(tmp, "network"))
shutil.copy(FIXTURE, os.path.join(tmp, "network", "network.json"))
obsdata = os.path.join(tmp, "obsData.dss")
open(obsdata, "w").close()


def write_cfg(obs_line):
    p = os.path.join(tmp, "config.ini")
    with open(p, "w") as f:
        f.write("[paths]\n%s\nnetwork_json = network/network.json\n[alternatives]\nobserved = Obs_NWP_H\nunregulated = UnregNWP_H\n" % obs_line)
    return p


cfg = Config(write_cfg("obsdata_dss = obsData.dss"))
check(cfg.obsdata_dss == obsdata and cfg.network_json == os.path.join(tmp, "network", "network.json"), "relative paths resolve from the config folder")
out = io.StringIO()
with redirect_stdout(out):
    status = check_network.main(cfg.file)
text = out.getvalue()
check(status == 0 and "All checks passed" in text, "check passes on the toy network")
check("Res              //RES/FLOW-OUT//1HOUR/CWMS/" in text, "reports each reservoir's Specified Release")
check("not mapped (taken as 0): T1 Local at T1" in text, "lists locals with no mapping")

out = io.StringIO()
with redirect_stdout(out):
    status = check_network.main(write_cfg("obsdata_dss ="))
check(status == 1 and "obsdata_dss is not set" in out.getvalue(), "unset obsdata_dss is reported")
out = io.StringIO()
with redirect_stdout(out):
    status = check_network.main(write_cfg("obsdata_dss = C:/nowhere/obsData.dss"))
check(status == 1 and "does not exist" in out.getvalue(), "missing obsData.dss is reported")
shutil.rmtree(tmp)

print()
if FAILS:
    print("%d FAILED" % len(FAILS))
    sys.exit(1)
print("ALL PASSED")
