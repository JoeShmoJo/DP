# -*- coding: utf-8 -*-
"""
Offline test of ExportNetwork.py under Jython 2.7 with the HEC classes stubbed
(the fake_hec.py the Damages Prevented tests use). From the repo root:

    java -jar jython-standalone-2.7.3.jar DP_Python/export/_offline_tests/test_ExportNetwork.py

Toy network (one reach of each routing method, a reservoir, a confluence,
an inflow multiplier and a diversion):

    J1 (local x1.2) -R1 SSARR-> Res_IN -> [Res] -> Res_OUT -R2 Muskingum-> Conf -R4 Null-> Mouth
    T1 (local)      -R3 Puls--------------------------------------------^  (Div1 at Conf)

Checks the JSON against the network built here, and saves the export as
DP_Python/tests/fixtures/toy_network.json for the CPython tests. This proves the export logic
and that it runs under Jython 2.7; only ResSim proves the real API calls.
"""
import os, sys, json, shutil, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SCRIPTS = os.path.join(REPO, "data", "ResSim41ExampleScripts")
sys.path.insert(0, os.path.join(SCRIPTS, "DamagesPrevented", "_offline_tests"))
sys.path.insert(0, SCRIPTS)

import fake_hec as F

WS = tempfile.mkdtemp(prefix="export_ws_")
F.install(WS)
F.RssModelVariableConstants.VID_OPRULETS_TSINPUT = 5
VF = F.RssModelVariableConstants.VID_NODE_FLOW
VK = F.RssModelVariableConstants.VID_NODE_KNOWNFLOW

FAILS = []
def check(cond, msg):
    if cond:
        print "  ok    %s" %msg
    else:
        print "  FAIL  %s" %msg
        FAILS.append(msg)

################################################################################
# Routing stubs with the getters ResSim's classes have

class Ssarr(F.SsarrRouting):
    def getNumberReaches(self): return 3
    def getKTS(self): return 12.5
    def getNCoefficient(self): return -0.2
class PulsRec(object):
    def __init__(self, s, q): self.stor, self.outflow = s, q
class Puls(F.PulsChannelRoutingWithLosses):
    def getnumberReaches(self): return 2
    def getPulsVector(self): return [PulsRec(0., 0.), PulsRec(100., 1000.), PulsRec(500., 8000.)]
    def getHasChannelLosses(self): return False
class Musk(F.MuskingumRouting):
    def getnumberReaches(self): return 4
    def getmuskingumK(self): return [2.5]
    def getmuskingumX(self): return [0.2]

################################################################################
# Build the network (same construction as the Damages Prevented tests)

class Net(F.Network):
    def getJunctionNames(self): return list(self.junctions.keys())
    def getReachNames(self): return list(self.reaches.keys())
    def getReservoirNames(self): return list(self.reservoirs.keys())

NET = Net(WS)
def junction(name):
    j = F.JunctionElement(name)
    j.system = NET
    j.dsNode = F.Node(name + "_dsnode", up=j)
    j.dsNode.proxies[VF] = F.TSRecordProxy("~%s:flow" %name)
    NET.junctions[name] = j
    return j
def local(j, locName, factor=1.0):
    n = F.Node(locName, up=None, down=j)
    n.proxies[VK] = F.TSRecordProxy("~%s:known" %locName, factor)
    n.proxies[VF] = F.TSRecordProxy("~%s:flow" %locName)
    j.nodes.append(n)
    return n
def reach(name, up, down, function):
    r = F.ReachElement(name)
    r.system = NET
    r.function = function
    r.dsNode = F.Node(name + "_dsnode", up=r, down=down)
    r.dsNode.proxies[VF] = F.TSRecordProxy("~%s:flow" %name)
    up.dsNode.down = r
    up.connected.append(r)
    down.connected.append(r)
    NET.reaches[name] = r
    return r
def reservoir(name, inJ, outJ):
    res = F.ReservoirElement(name)
    res.system = NET
    pool = F.Element("Pool")
    pool.parent = res
    pool.system = NET
    res.kids = [pool]
    res.proxies[F.RssModelVariableConstants.VID_POOL_INFLOW] = F.TSRecordProxy("~%s:in" %name)
    res.proxies[F.RssModelVariableConstants.VID_POOL_OUTFLOW] = F.TSRecordProxy("~%s:out" %name)
    inJ.dsNode.down = pool
    inJ.connected.append(res)
    pool.dsNode = F.Node(name + "_pooldsnode", up=pool, down=outJ)
    res.dsNode = pool.dsNode
    outJ.connected.append(res)
    NET.reservoirs[name] = res
    return res

J = {}
for n in ("J1", "Res_IN", "Res_OUT", "T1", "Conf", "Mouth"):
    J[n] = junction(n)
local(J["J1"], "J1 Local", 1.2)
local(J["T1"], "T1 Local")
local(J["Conf"], "Conf Local")
reach("R1", J["J1"], J["Res_IN"], Ssarr())
reservoir("Res", J["Res_IN"], J["Res_OUT"])
reach("R2", J["Res_OUT"], J["Conf"], Musk())
reach("R3", J["T1"], J["Conf"], Puls())
reach("R4", J["Conf"], J["Mouth"], F.NullRouting())
J["Mouth"].dsNode.down = None
div = F.DiversionElement("Div1")
J["Conf"].connected.append(div)
NET.headwaters = [J["J1"], J["T1"]]

################################################################################
# Alternatives and the open simulation

obsSet = F.TSDataSet()
obsSet.put(F.TSRecord("~Conf:flow", VF, "scripts/x/obsData.dss", "/G/CONF/FLOW//1HOUR/USGS/"))
inSet = F.TSDataSet()
inSet.put(F.TSRecord("~J1 Local:known", VK, "scripts/x/obsData.dss", "//J1/FLOW-IN//1HOUR/CWMS/"))
inSet.put(F.TSRecord("Res (RES) Specified Release", 5, "scripts/x/obsData.dss", "//RES/FLOW-OUT//1HOUR/CWMS/", "Input Time Series"))
altObs = F.RssAlt("1HOUR", obsSet, inSet)
altUnreg = F.RssAlt("1HOUR", F.TSDataSet(), inSet)
sim = F.Simulation(F.RunTimeWindow("01Oct2024 0000", "01Oct2024 0100", "30Sep2025 2400"), os.path.join(WS, "sim.dss"))
sim.runs["Obs_NWP_H"] = F.SimRun("Obs_NWP_H", "Obs_NWP_H-----0", NET, altObs)
sim.runs["UnregNWP_H"] = F.SimRun("UnregNWP_H", "UnregNWP_H----0", NET, altUnreg)
F.Module.sim = sim

################################################################################
print "\n== Export"
exportFile = os.path.join(REPO, "DP_Python", "export", "ExportNetwork.py")
code = compile(open(exportFile).read(), "<string>", "exec")
exec code in {"__name__": "__main__"}
outFile = os.path.join(WS, "DP_Python_export", "network.json")
check(os.path.exists(outFile), "network.json written under the watershed")
data = json.load(open(outFile))
E = data["network"]["elements"]
#Keep this export as the fixture the DP_Python (CPython) tests load
fixture = os.path.join(REPO, "DP_Python", "tests", "fixtures", "toy_network.json")
if not os.path.exists(os.path.dirname(fixture)):
    os.makedirs(os.path.dirname(fixture))
shutil.copyfile(outFile, fixture)

check(data["exportVersion"] == 1 and data["simulationWindow"]["start"] == "01Oct2024 0100", "header and simulation window")
check(data["variableIds"]["NODE_KNOWNFLOW"] == VK and data["variableIds"]["OPRULETS_TSINPUT"] == 5, "variable ids")
check(sorted([k for k in E.keys() if E[k]["type"] == "junction"]) == sorted(["junction:%s" %n for n in J.keys()]), "all junctions")
check(E["junction:J1"]["locals"] == [{"node": "J1 Local", "knownFlowProxy": "~J1 Local:known", "factor": 1.2,
                                      "flowProxy": "~J1 Local:flow"}], "local with its inflow multiplier")
check(E["junction:Res_OUT"]["locals"] == [], "a junction with no local")
check(E["junction:J1"]["downstream"] == "reach:R1" and E["junction:Res_IN"]["downstream"] == "pool:Res"
      and E["junction:Mouth"]["downstream"] is None, "downstream links (junction -> reach / pool / none)")
check(E["junction:Conf"]["flowProxy"] == "~Conf:flow", "junction flow proxy")
check("diversion:Div1" in E["junction:Conf"]["connected"] and E["diversion:Div1"]["junction"] == "Conf", "diversion recorded")
check(E["reach:R1"]["routing"] == {"method": "SSARR", "supported": True, "subreaches": 3, "kts": 12.5, "n": -0.2}, "SSARR parameters")
check(E["reach:R2"]["routing"] == {"method": "Muskingum", "supported": True, "subreaches": 4, "k": [2.5], "x": [0.2]}, "Muskingum parameters")
check(E["reach:R3"]["routing"] == {"method": "Modified Puls", "supported": True, "subreaches": 2,
                                   "storage": [0., 100., 500.], "outflow": [0., 1000., 8000.], "hasChannelLosses": False},
      "Modified Puls table")
check(E["reach:R4"]["routing"] == {"method": "Null", "supported": True} and E["reach:R4"]["downstream"] == "junction:Mouth", "Null reach")
res = E["reservoir:Res"]
check(res["pool"] == "pool:Res" and res["downstream"] == "junction:Res_OUT" and res["inflowProxy"] == "~Res:in"
      and res["outflowProxy"] == "~Res:out", "reservoir links and proxies")
check(res["downstreamElements"] == ["junction:Res_OUT", "reach:R2", "junction:Conf", "reach:R4", "junction:Mouth"],
      "reservoir downstream path")
order = data["network"]["orderFromUpstream"]
check(order.index("junction:J1") < order.index("reach:R1") < order.index("pool:Res") < order.index("junction:Res_OUT")
      < order.index("junction:Conf") < order.index("junction:Mouth") and order.index("reach:R3") < order.index("junction:Conf"),
      "compute order from upstream")
check(sorted(data["network"]["headwaterJunctions"]) == ["junction:J1", "junction:T1"], "headwaters")
check(data["network"]["confluenceJunctions"] == ["junction:Conf"], "confluences")
alts = data["alternatives"]
check(sorted(alts.keys()) == ["Obs_NWP_H", "UnregNWP_H"] and alts["Obs_NWP_H"]["timeStep"] == "1HOUR", "both alternatives")
check({"name": "Res (RES) Specified Release", "variableId": 5, "param": "Input Time Series",
       "dssFile": "scripts/x/obsData.dss", "pathname": "//RES/FLOW-OUT//1HOUR/CWMS/"} in alts["Obs_NWP_H"]["input"],
      "Time-Series tab records")
check(alts["Obs_NWP_H"]["observed"][0]["pathname"] == "/G/CONF/FLOW//1HOUR/USGS/", "Observed Data tab records")

class Odd(object): pass
NET.reaches["R4"].function = Odd()   #same topology, a routing type DP_Python can't reproduce
exec code in {"__name__": "__main__"}
data = json.load(open(outFile))
check(data["network"]["elements"]["reach:R4"]["routing"] == {"method": "Odd", "supported": False}, "unsupported routing flagged")

shutil.rmtree(WS)
print
if FAILS:
    print "%d FAILED" %len(FAILS)
    sys.exit(1)
print "ALL PASSED"
