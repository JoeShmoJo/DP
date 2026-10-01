"""
Offline test of the three Damages Prevented steps on a toy network, under
Jython 2.7 with the HEC classes stubbed (fake_hec.py).

    java -jar jython-standalone-2.7.3.jar DamagesPrevented/_offline_tests/test_DamagesPrevented.py

(run from the scripts folder; ResSim's own jython.jar works too)

Toy network (all reaches Null routing, hourly):

    Res1_IN -> [Res1] -> Res1_OUT -R1-----------------------\\
                                                              Conf -R4- Mouth
    Res2_IN -> [Res2] -> Res2_OUT -R2- Rereg2_IN -> [Rereg2] -> Rereg2_OUT -R3-/

Res2 releases into the re-regulating reservoir Rereg2 (like Detroit and Big
Cliff). Locals: Res1_IN, Res2_IN (headwater inflows), Conf (water-balance
local), Mouth (the transformed local, like Willamette Falls).

What this checks: config parsing, the transform, the water-balance arithmetic
and its DPcalc.dss handling, the mini-simulation routing walk, the
re-reg pairing, the reduction formula and the CSV tables. Expected values are
computed here by hand from the same input series, not by calling the modules.
What it cannot check: that the ResSim 4.1 Java methods behave like the stubs.
"""
import os, sys, shutil, tempfile, csv

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, SCRIPTS)

import fake_hec as F

WS = tempfile.mkdtemp(prefix="dp_ws_")
F.install(WS)
#ResSim 4.1's ClientApp.Workspace() is the AppData workspace, not the watershed.
#Point the fake one somewhere else so nothing can rely on it.
F._ClientApp.ws = F.Workspace(os.path.join(WS, "NOT_THE_WATERSHED_AppData"))

from DamagesPrevented import DPSettings, cTransform, cWaterBalance, cMiniSims

FAILS = []
def check(cond, msg):
    if cond:
        print "  ok    %s" %msg
    else:
        print "  FAIL  %s" %msg
        FAILS.append(msg)

class Bar(object):
    def __init__(self): self.v = 0
    def setValue(self, v): self.v = v
    def getValue(self): return self.v

class Txt(object):
    def __init__(self): self.lines = []
    def printToGUI(self, msg): self.lines.append(str(msg))
    def text(self): return "\n".join(self.lines)

################################################################################
# Input series (hourly, 8 values). Peaks are at different hours on purpose.
TIMES = [60*i for i in range(8)]
I1  = [100., 400., 1500., 2600., 1800., 900., 500., 300.]   #Res1 inflow
Q1  = [100., 300., 600., 900., 1000., 900., 700., 500.]     #Res1 outflow
I2  = [200., 800., 2400., 3100., 2000., 1000., 600., 400.]  #Res2 inflow
Q2  = [200., 500., 900., 1200., 1300., 1100., 900., 700.]   #Res2 outflow = Rereg2 inflow
QR  = [250., 450., 950., 1150., 1350., 1150., 850., 650.]   #Rereg2 outflow
L   = [50., 120., 400., 700., 500., 300., 150., 100.]       #Conf local
PUD = [100., 200., 300., 400., 300., 200., 150., 120.]      #Pudding R gage -> Mouth local x1.5
M   = [1.5*v for v in PUD]

def plus(*series):
    return [sum(vals) for vals in zip(*series)]

CONF_OBS = plus(Q1, QR, L)
MOUTH_OBS = plus(CONF_OBS, M)

OBSDATA = os.path.join(WS, DPSettings.OBSDATA_DSS)
DPCALC = os.path.join(WS, DPSettings.DPCALC_DSS)
SIMDSS = os.path.join(WS, "rss", "simulation.dss")

################################################################################
# Build the toy network

def build():
    net = F.Network(WS)
    VF = F.RssModelVariableConstants.VID_NODE_FLOW
    VK = F.RssModelVariableConstants.VID_NODE_KNOWNFLOW
    def junction(name):
        j = F.JunctionElement(name)
        j.system = net
        j.dsNode = F.Node(name + "_dsnode", up=j)
        j.dsNode.proxies[VF] = F.TSRecordProxy("~%s:flow" %name)
        net.junctions[name] = j
        return j
    def local(j, locName):
        n = F.Node(locName, up=None, down=j)
        n.proxies[VK] = F.TSRecordProxy("~%s:known" %locName)
        n.proxies[VF] = F.TSRecordProxy("~%s:flow" %locName)
        j.nodes.append(n)
        return n
    def reach(name, up, down):
        r = F.ReachElement(name)
        r.system = net
        r.function = F.NullRouting()
        r.dsNode = F.Node(name + "_dsnode", up=r, down=down)
        r.dsNode.proxies[VF] = F.TSRecordProxy("~%s:flow" %name)
        up.dsNode.down = r
        up.connected.append(r)
        down.connected.append(r)
        net.reaches[name] = r
        return r
    def reservoir(name, inJ, outJ):
        res = F.ReservoirElement(name)
        res.system = net
        pool = F.Element("Pool")
        pool.parent = res
        pool.system = net
        res.kids = [pool]
        res.proxies[F.RssModelVariableConstants.VID_POOL_INFLOW] = F.TSRecordProxy("~%s:in" %name)
        res.proxies[F.RssModelVariableConstants.VID_POOL_OUTFLOW] = F.TSRecordProxy("~%s:out" %name)
        inJ.dsNode.down = pool
        inJ.connected.append(res)
        pool.dsNode = F.Node(name + "_pooldsnode", up=pool, down=outJ)
        res.dsNode = pool.dsNode
        outJ.connected.append(res)
        net.reservoirs[name] = res
        return res
    J = {}
    for n in ("Res1_IN", "Res1_OUT", "Res2_IN", "Res2_OUT", "Rereg2_IN", "Rereg2_OUT", "Conf", "Mouth"):
        J[n] = junction(n)
    loc = {}
    loc["Res1"] = local(J["Res1_IN"], "Res1 Inflow")
    loc["Res2"] = local(J["Res2_IN"], "Res2 Inflow")
    loc["Conf"] = local(J["Conf"], "Conf Local")
    loc["Mouth"] = local(J["Mouth"], "Mouth Local")
    R = {}
    R["Res1"] = reservoir("Res1", J["Res1_IN"], J["Res1_OUT"])
    R["Res2"] = reservoir("Res2", J["Res2_IN"], J["Res2_OUT"])
    R["Rereg2"] = reservoir("Rereg2", J["Rereg2_IN"], J["Rereg2_OUT"])
    reach("R1", J["Res1_OUT"], J["Conf"])
    reach("R2", J["Res2_OUT"], J["Rereg2_IN"])
    reach("R3", J["Rereg2_OUT"], J["Conf"])
    reach("R4", J["Conf"], J["Mouth"])
    J["Mouth"].dsNode.down = None   #end of the network
    net.headwaters = [J["Res1_IN"], J["Res2_IN"]]
    return net, J, R, loc

NET, J, R, LOC = build()
VF = F.RssModelVariableConstants.VID_NODE_FLOW
VK = F.RssModelVariableConstants.VID_NODE_KNOWNFLOW
VIN = F.RssModelVariableConstants.VID_POOL_INFLOW
VOUT = F.RssModelVariableConstants.VID_POOL_OUTFLOW

################################################################################
# Alternative mappings (Observed tab, Timeseries tab) and data files

OBS_REL = DPSettings.OBSDATA_DSS
CALC_REL = DPSettings.DPCALC_DSS
CONF_LOCAL_PATH = "//CONF/FLOW-LOC//1HOUR/NWP/"
WF_PATH = "//WILLAMETTE FALLS/FLOW-LOC//1HOUR/COMPUTED/"

obsSet = F.TSDataSet()
for name, path in (("Res1_OUT", "/G/RES1 OUT GAGE/FLOW//1HOUR/USGS/"),
                   ("Rereg2_OUT", "/G/REREG2 OUT GAGE/FLOW//1HOUR/USGS/"),
                   ("Conf", "/G/CONF GAGE/FLOW//1HOUR/USGS/")):
    obsSet.put(F.TSRecord("~%s:flow" %name, VF, OBS_REL, path))
inputSet = F.TSDataSet()
inputSet.put(F.TSRecord("~Res1 Inflow:known", VK, OBS_REL, "//RES1/FLOW-IN//1HOUR/CWMS/"))
inputSet.put(F.TSRecord("~Res2 Inflow:known", VK, OBS_REL, "//RES2/FLOW-IN//1HOUR/CWMS/"))
inputSet.put(F.TSRecord("~Conf Local:known", VK, CALC_REL, CONF_LOCAL_PATH))
inputSet.put(F.TSRecord("~Mouth Local:known", VK, CALC_REL, WF_PATH))

F.putRecord(OBSDATA, "/G/RES1 OUT GAGE/FLOW//1HOUR/USGS/", Q1, TIMES)
F.putRecord(OBSDATA, "/G/REREG2 OUT GAGE/FLOW//1HOUR/USGS/", QR, TIMES)
F.putRecord(OBSDATA, "/G/CONF GAGE/FLOW//1HOUR/USGS/", CONF_OBS, TIMES)
F.putRecord(OBSDATA, "//RES1/FLOW-IN//1HOUR/CWMS/", I1, TIMES)
F.putRecord(OBSDATA, "//RES2/FLOW-IN//1HOUR/CWMS/", I2, TIMES)
F.putRecord(OBSDATA, "/PUDDING RIVER AT AURORA, OR/14202000/FLOW//1HOUR/USGS/", PUD, TIMES)

altObs = F.RssAlt("1HOUR", obsSet, inputSet)
altUnreg = F.RssAlt("1HOUR", F.TSDataSet(), inputSet)
rtw = F.RunTimeWindow(TIMES[0], TIMES[1], TIMES[-1])
sim = F.Simulation(rtw, SIMDSS)

def outputSet(fPart, series):
    """Regulated output mapping + simulation.dss records for one computed run"""
    ds = F.TSDataSet()
    for proxyName, vid, values in series:
        path = "//%s/V%d//1HOUR/%s/" %(proxyName.strip("~").replace(":", "-"), vid, fPart)
        ds.put(F.TSRecord(proxyName, vid, "", path))
        F.putRecord(SIMDSS, path, values, TIMES)
    return ds

obsOut = outputSet("OBS", [
    ("~Res1:in", VIN, I1), ("~Res1:out", VOUT, Q1),
    ("~Res2:in", VIN, I2), ("~Res2:out", VOUT, Q2),
    ("~Rereg2:in", VIN, Q2), ("~Rereg2:out", VOUT, QR),
    ("~Res1_OUT:flow", VF, Q1), ("~Rereg2_OUT:flow", VF, QR),
    ("~Conf:flow", VF, CONF_OBS), ("~Mouth:flow", VF, MOUTH_OBS),
    ("~R1:flow", VF, Q1), ("~R3:flow", VF, QR),
    ("~Res1 Inflow:flow", VF, I1), ("~Res2 Inflow:flow", VF, I2),
    ("~Conf Local:flow", VF, L), ("~Mouth Local:flow", VF, M)])
UNREG_CONF = plus(I1, I2, L)
unregOut = outputSet("UNREG", [
    ("~Res1:in", VIN, I1), ("~Res1:out", VOUT, I1),
    ("~Res2:in", VIN, I2), ("~Res2:out", VOUT, I2),
    ("~Rereg2:in", VIN, I2), ("~Rereg2:out", VOUT, I2),
    ("~Res1_OUT:flow", VF, I1), ("~Rereg2_OUT:flow", VF, I2),
    ("~Conf:flow", VF, UNREG_CONF), ("~Mouth:flow", VF, plus(UNREG_CONF, M)),
    ("~R1:flow", VF, I1), ("~R3:flow", VF, I2),
    ("~Res1 Inflow:flow", VF, I1), ("~Res2 Inflow:flow", VF, I2),
    ("~Conf Local:flow", VF, L), ("~Mouth Local:flow", VF, M)])
#the observed data ResSim copies into simulation.dss
for path, values in (("/G/RES1 OUT GAGE/FLOW//1HOUR/USGS/", Q1), ("/G/CONF GAGE/FLOW//1HOUR/USGS/", CONF_OBS),
                     ("/G/REREG2 OUT GAGE/FLOW//1HOUR/USGS/", QR)):
    F.putRecord(SIMDSS, path, values, TIMES)
obsSetSim = F.TSDataSet()
for rec in obsSet.getTSRecords():
    obsSetSim.put(F.TSRecord(rec.getName(), rec.getVariableId(), "", rec.getDSSPathname()))
altObsRun = F.RssAlt("1HOUR", obsSetSim, inputSet)

sim.runs["Obs_NWP_H"] = F.SimRun("Obs_NWP_H", "Obs_NWP_H-----0", NET, altObs)
sim.runs["Unreg_NWP_H"] = F.SimRun("Unreg_NWP_H", "Unreg_NWP_H---0", NET, altUnreg)
F.Module.sim = sim
F.Module.rssRuns = {"Obs_NWP_H-----0": F.RssRun(NET, altObsRun, obsOut),
                    "Unreg_NWP_H---0": F.RssRun(NET, altUnreg, unregOut)}

print "\n== File locations resolve against the watershed, not ClientApp.Workspace()"
check(DPSettings.absPath(DPSettings.DPCALC_DSS) == os.path.abspath(os.path.join(WS, DPSettings.DPCALC_DSS)),
      "DPSettings.absPath uses the network's watershed folder")

def writeText(fileName, text):
    handle = open(fileName, "w")
    handle.write(text)
    handle.close()

def series(fileName, path):
    rec = F.getRecord(fileName, path)
    if rec is None: return None
    return [round(v, 6) for v in rec.values]

################################################################################
print "\n== Config files"
cfg = os.path.join(SCRIPTS, "DamagesPrevented", "config")
rows = cTransform.parseTransformCSV(os.path.join(cfg, "TransformedLocals.csv"))
check(len(rows) == 1 and rows[0]["bPart"] == "WILLAMETTE FALLS" and rows[0]["station"] == "14202000"
      and rows[0]["areaRatio"] == 1.5 and rows[0]["aMove1"] is None, "TransformedLocals.csv: Willamette Falls = 1.5 x 14202000")
cps = cMiniSims.readNameList(os.path.join(cfg, "ControlPoints.txt"))
check(len(cps) == 22 and "CF WIllamette_nr Goshen" in cps and "Mkenzie_nr Walterville" in cps
      and "MF Willamette NR Oakridge" in cps and "Willamette+Clackamas" not in cps,
      "ControlPoints.txt: 22 names, inline comments stripped")
rs = cMiniSims.readNameList(os.path.join(cfg, "Reservoirs.txt"))
check(len(rs) == 13 and "Big Cliff" in rs and "Dexter" in rs, "Reservoirs.txt: 13 reservoirs")
check(DPSettings.REREG == {"Detroit": "Big Cliff", "Lookout Point": "Dexter"}, "re-reg pairs")

################################################################################
print "\n== Diversions whose rule can't be read (no rule on the controller, as in the new watershed)"
class _NoRuleCtrl(object):
    def getRuleVector(self): return []
class _NoRuleDiv(F.DiversionElement):
    def getController(self): return _NoRuleCtrl()
    def getUpstreamNode(self): return "Div1 node"
div = _NoRuleDiv("Div1")
txtD = Txt()
check(cWaterBalance._diversionTSM(div, None, None, "1HOUR", None, None, txtD) is None,
      "no rule and no previous compute: not deducted (None), no crash")
_origGet = cWaterBalance.cResSim.getTSMFromSimulationDSS
_origTr = cWaterBalance.cTsUtils.transformTSM
cWaterBalance.cResSim.getTSMFromSimulationDSS = lambda *a, **k: "computed div flow"
cWaterBalance.cTsUtils.transformTSM = lambda tsm, tsInt: (tsm, tsInt)
got = cWaterBalance._diversionTSM(div, None, None, "1HOUR", None, None, txtD)
cWaterBalance.cResSim.getTSMFromSimulationDSS = _origGet
cWaterBalance.cTsUtils.transformTSM = _origTr
check(got == ("computed div flow", "1HOUR"), "no rule but a previous compute: uses the computed diversion flow")

print "\n== Step 2 before step 1: the missing transformed local stops the compute with a pointer to step 1"
txt = Txt()
res = cWaterBalance.computeWaterBalanceLocals("Obs_NWP_H", DPCALC, True, Bar(), txt)
check(res is None, "compute stopped")
check("run step 1" in txt.text() and "Mouth" in txt.text(), "message names the junction and step 1")

################################################################################
print "\n== Step 1: transform"
transformCSV = os.path.join(WS, "TransformedLocals.csv")
shutil.copy(os.path.join(cfg, "TransformedLocals.csv"), transformCSV)
written = cTransform.transformGageData(OBSDATA, DPCALC, transformCSV, "1HOUR", "0", "420", "COMPUTED", Bar(), Txt())
check(written == [WF_PATH], "wrote %s" %WF_PATH)
check(series(DPCALC, WF_PATH) == [round(v, 6) for v in M], "Willamette Falls = 1.5 x Pudding")

################################################################################
print "\n== Step 2: water-balance locals"
txt = Txt()
res = cWaterBalance.computeWaterBalanceLocals("Obs_NWP_H", DPCALC, True, Bar(), txt)
check(res == 1, "one local computed (Conf); got %s" %res)
check(series(DPCALC, CONF_LOCAL_PATH) == [round(v, 6) for v in L],
      "Conf local = Conf gage - (Res1 gage + Rereg2 gage), routed")
check(series(DPCALC, WF_PATH) == [round(v, 6) for v in M], "Willamette Falls left as is in DPcalc.dss")
check(series(SIMDSS, CONF_LOCAL_PATH) == [round(v, 6) for v in L], "local also written to simulation.dss")

print "\n== Step 2 with negative locals not allowed"
F.putRecord(OBSDATA, "/G/CONF GAGE/FLOW//1HOUR/USGS/", plus(Q1, QR, [-30.] + L[1:]), TIMES)
res = cWaterBalance.computeWaterBalanceLocals("Obs_NWP_H", DPCALC, False, Bar(), Txt())
loc = F.getRecord(DPCALC, CONF_LOCAL_PATH).values
check(min(loc) >= 0 and abs(sum(loc) - (sum(L[1:]) - 30.)) < 1e-6, "negative local removed, volume kept")
F.putRecord(OBSDATA, "/G/CONF GAGE/FLOW//1HOUR/USGS/", CONF_OBS, TIMES)

################################################################################
print "\n== Step 3: mini-simulations"
cpFile = os.path.join(WS, "cp.txt")
rsFile = os.path.join(WS, "rs.txt")
writeText(cpFile, "#test\nRes1_OUT\nConf\nMouth  # the mouth\n")
writeText(rsFile, "Res1\nRes2\nRereg2\n")
outDir = os.path.join(WS, "Results")
miniDss = os.path.join(WS, "MiniSimulations.dss")
rereg = {"Res2": "Rereg2"}

txt = Txt()
writeText(os.path.join(WS, "bad.txt"), "Conf\nNo Such Junction\n")
res = cMiniSims.runMiniSimulations("Obs_NWP_H", "Unreg_NWP_H", miniDss, outDir, os.path.join(WS, "bad.txt"), rsFile, rereg, Bar(), txt)
check(res is None and "junction: No Such Junction" in txt.text(), "unknown control point stops the run and is named")

txt = Txt()
files = cMiniSims.runMiniSimulations("Obs_NWP_H", "Unreg_NWP_H", miniDss, outDir, cpFile, rsFile, rereg, Bar(), txt)
check(files is not None and len(files) == 4, "4 CSV tables written")
if files is None:
    print txt.text()

def capMin(vals):
    return [max(v, 0.) for v in vals]
def storageChange(flow, inflow, outflow):
    """flow + outflow - inflow, negatives made up from later values (volume kept)"""
    vals = [f + o - i for f, i, o in zip(flow, inflow, outflow)]
    out, run = [], 0.
    for v in vals:
        nv = max(v - run, 0.)
        run += nv - v
        out.append(nv)
    return out

#Expected flows, worked out by hand from the inputs
expect = {}
#WITHOUT Res1: Res1 passes inflow; trib (R3) and Conf local from the Observed run
expect[("Res1_OUT", "WITHOUT Res1")] = I1
expect[("Conf", "WITHOUT Res1")] = plus(I1, QR, L)
expect[("Mouth", "WITHOUT Res1")] = plus(I1, QR, L, M)
#WITH ONLY Res1: Res1 applies its observed storage change; trib (R3) from the Unregulated run
w1 = storageChange(I1, I1, Q1)
expect[("Res1_OUT", "WITH ONLY Res1")] = w1
expect[("Conf", "WITH ONLY Res1")] = plus(w1, I2, L)
expect[("Mouth", "WITH ONLY Res1")] = plus(w1, I2, L, M)
#WITHOUT Res2 (and its re-reg): both pass inflow; R1 from the Observed run
expect[("Conf", "WITHOUT Res2")] = plus(I2, Q1, L)
expect[("Mouth", "WITHOUT Res2")] = plus(I2, Q1, L, M)
#WITH ONLY Res2: Res2 and Rereg2 both apply their storage change; R1 from Unregulated
w2 = storageChange(storageChange(I2, I2, Q2), Q2, QR)
expect[("Conf", "WITH ONLY Res2")] = plus(w2, I1, L)
expect[("Mouth", "WITH ONLY Res2")] = plus(w2, I1, L, M)
for (cp, run), vals in sorted(expect.items()):
    got = series(miniDss, "//%s/FLOW//1HOUR/%s/" %(cp, run))
    check(got == [round(v, 6) for v in vals], "%s at %s" %(run, cp))
check(series(miniDss, "//Res1_OUT/FLOW//1HOUR/WITHOUT Res2/") is None, "Res1_OUT is not below Res2: no Res2 run there")
check(series(miniDss, "//Conf/FLOW//1HOUR/UNREGULATED/") == [round(v, 6) for v in UNREG_CONF], "UNREGULATED written")
check(series(miniDss, "//Conf/FLOW//1HOUR/OBSERVED/") == [round(v, 6) for v in CONF_OBS], "OBSERVED written")
check(series(miniDss, "//Mouth/FLOW//1HOUR/MODELED OBSERVED/") == [round(v, 6) for v in MOUTH_OBS], "MODELED OBSERVED written")
check(series(miniDss, "//Conf/FLOW//1HOUR/WITHOUT Rereg2/") is None, "the re-reg gets no runs of its own")

def r100(v): return round(v, -2)
def expectedReduction(cp, resv):
    unreg = r100(max({"Res1_OUT": I1, "Conf": UNREG_CONF, "Mouth": plus(UNREG_CONF, M)}[cp]))
    obs = r100(max({"Res1_OUT": Q1, "Conf": CONF_OBS, "Mouth": MOUTH_OBS}[cp]))
    withPk = r100(max(expect[(cp, "WITH ONLY %s" %resv)]))
    withoutPk = r100(max(expect[(cp, "WITHOUT %s" %resv)]))
    return ((unreg - withPk) + (withoutPk - obs))/2.

def readCSV(name):
    return list(csv.reader(open(os.path.join(outDir, name))))
pre = readCSV("Preliminary_per_project.csv")
header = pre[3]
check(header == ["Control Point", "Total Flow Reduction", "Res1", "Res2"], "reduction matrix header")
table = dict((row[0], row) for row in pre[4:])
for cp in ("Res1_OUT", "Conf", "Mouth"):
    for j, resv in ((2, "Res1"), (3, "Res2")):
        if cp == "Res1_OUT" and resv == "Res2":
            check(table[cp][j] == "x", "Res1_OUT / Res2 marked x (not downstream)")
            continue
        check(float(table[cp][j]) == round(expectedReduction(cp, resv)),
              "reduction %s at %s = %.0f (got %s)" %(resv, cp, expectedReduction(cp, resv), table[cp][j]))
cpPeaks = dict((row[0], row) for row in readCSV("CP_Peaks.csv")[1:])
check(cpPeaks["Conf"][6] == "gaged" and cpPeaks["Mouth"][6].startswith("ResSim simulated"), "CP_Peaks: gaged vs simulated")
resvPeaks = dict((row[0], row) for row in readCSV("Resv_Peaks.csv")[1:])
check(resvPeaks["Res2"][3] == "%.0f" %r100(QR[I2.index(max(I2))]) and "Rereg2" in resvPeaks["Res2"][5],
      "Resv_Peaks: Res2 outflow taken below its re-reg")
check(len(readCSV("Mini-Simulations.csv")) == 1 + 3 + 2, "Mini-Simulations.csv: one row per reservoir x downstream control point")

shutil.rmtree(WS)
print
if FAILS:
    print "%d FAILED" %len(FAILS)
    sys.exit(1)
print "ALL PASSED"
