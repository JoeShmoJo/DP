"""
Offline test harness for externalRules/FIRO_SPACE.py.

Stubs the hec.* Java classes and the two NWDJyLib modules that import Java, so the
rule's CSV parsing and release math can be exercised on a plain Python interpreter
without launching ResSim. cFile and SimplePy are imported for real.

Run it with either Python 2.7 or Python 3 from anywhere:
    python test_FIRO_SPACE.py

This does NOT test anything ResSim-side (rule stack behavior, OpValue handling,
the real elevation-storage table). It tests the logic that is ours.
"""
import sys, os, types, datetime

# .../scripts/externalRules/_offline_tests/ -> .../scripts/ and .../externalRules/
_HERE = os.path.dirname(os.path.abspath(__file__))
RULES_DIR = os.path.dirname(_HERE)
SCRIPTS_DIR = os.path.dirname(RULES_DIR)
sys.path.insert(0, SCRIPTS_DIR)
sys.path.insert(0, RULES_DIR)
SHIPPED_CSV = os.path.join(RULES_DIR, "FIRO_SPACEConfig.csv")
CONFIG_CSV = os.path.join(_HERE, "_fixture_tmp.csv")   # generated below

def writeFixture():
    """
    A known two-project curve, so the behaviour tests do not depend on whatever
    elevations happen to be in the shipped config file.
    Detroit: 1484.5 through 01Feb, ramp to 1558.5 by 01May, hold to 31Aug,
    ramp back down by 30Nov. Cougar: flat 1600.
    """
    import datetime as _dt
    def doy(m, d):
        return _dt.date(2001, m, d).timetuple().tm_yday
    shape = [(doy(1, 1), 1484.5), (doy(2, 1), 1484.5), (doy(5, 1), 1558.5),
             (doy(8, 31), 1558.5), (doy(11, 30), 1484.5), (doy(12, 31), 1484.5)]
    def interp(x):
        for (x1, y1), (x2, y2) in zip(shape, shape[1:]):
            if x1 <= x <= x2:
                return y1 + (y2 - y1) * (x - x1) / float(x2 - x1)
        return shape[-1][1]
    out = ["# generated fixture", "Month,Day,Detroit,Cougar"]
    for n in range(1, 366):
        date = _dt.date(2001, 1, 1) + _dt.timedelta(days=n - 1)
        out.append("%d,%d,%.4f,1600.0" % (date.month, date.day, interp(n)))
    fh = open(CONFIG_CSV, "w")
    fh.write("\n".join(out) + "\n")
    fh.close()

writeFixture()

# ---- stub hec.heclib.util.HecTime -------------------------------------------
class HecTime(object):
    # minutes since midnight; a daily step is at 2400
    def __init__(self, d=None, minutes=1440):
        self._d = d
        self._minutes = minutes
    def setYearMonthDay(self, y, m, d, minutes):
        self._d = datetime.date(y, m, d)
        self._minutes = minutes
    def hour(self):
        return self._minutes // 60
    def minute(self):
        return self._minutes % 60
    def dayOfYear(self):
        return self._d.timetuple().tm_yday
    def month(self):
        return self._d.month
    def day(self):
        return self._d.day
    def dateAndTime(self):
        return self._d.isoformat()

class OpRule(object):
    RULETYPE_MIN = "MIN"
    RULETYPE_MAX = "MAX"

class OpValue(object):
    def __init__(self):
        self.type = None
        self.value = None
    def init(self, t, v):
        self.type, self.value = t, v

def _mod(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m

for pkg in ("hec", "hec.rss", "hec.heclib", "hec.script"):
    _mod(pkg)
_mod("hec.rss.model", OpValue=OpValue, OpRule=OpRule)
_mod("hec.heclib.util", HecTime=HecTime)

# ---- stub the two NWDJyLib modules that import java --------------------------
import NWDJyLib  # real package, harmless __init__
_mod("NWDJyLib.cTimes", getHecTimeFromRuntimestep=lambda rts: rts.getHecTime())
_mod("NWDJyLib.ResSim")
_mod("NWDJyLib.ResSim.cResSim",
     getElevationStorageTable=lambda n, net: net.elevStorTable)

import FIRO_SPACE as F  # noqa: E402

# ---- fake ResSim objects -----------------------------------------------------
class ElevStorTable(object):
    """Straight-line elev->storage: 1000 ac-ft per foot above elev 0."""
    def interpolate(self, elev):
        return elev * 1000.0

class TS(object):
    def __init__(self, prev=None, cur=None):
        self._prev, self._cur = prev, cur
    def getPreviousValue(self, rts):
        return self._prev
    def getCurrentValue(self, rts):
        return self._cur

class Network(object):
    def __init__(self, ts=None):
        self.ts = ts or {}
        self.elevStorTable = ElevStorTable()
        self.messages = []
    def getTimeSeries(self, a, resv, b, param):
        return self.ts[param]
    def getStateVariable(self, name):
        raise RuntimeError("no such state variable")   # exercises the fallback path
    def makeAbsolutePathFromWatershed(self, rel):
        # Behaviour tests run against the generated fixture, never the shipped
        # config, so editing the real curve cannot break them.
        return CONFIG_CSV
    def printMessage(self, m):
        self.messages.append(m)

class ResvElement(object):
    def __init__(self, name):
        self._name = name

class Rule(object):
    def __init__(self, name):
        self._resv = ResvElement(name)
        self._vars = {}
    def getReservoirElement(self):
        return self._resv
    def varPut(self, k, v):
        self._vars[k] = v
    def varGet(self, k):
        return self._vars[k]
    def varExists(self, k):
        return k in self._vars

class RTS(object):
    def __init__(self, date, minutes=1440):
        self._date, self._min = date, minutes
    def getHecTime(self):
        return HecTime(self._date)
    def getTimeStepMinutes(self):
        return self._min

# ---- tests -------------------------------------------------------------------
fails = []
def check(label, got, want, tol=1e-6):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    print("%-58s %-14s %s" % (label, "OK" if ok else "FAIL",
                              "" if ok else "got %r want %r" % (got, want)))
    if not ok:
        fails.append(label)

print("=== 1. CSV loads and interpolates (generated fixture) ===")
net = Network()
rule = Rule("Detroit")
F.initRuleScript(rule, net)
curve = rule.varGet("firoCurve")
check("Detroit 01Jan (winter)", F.getTargetElev(curve, HecTime(datetime.date(2023,1,1))), 1484.5)

# Sub-daily steps interpolate between the previous day's target and today's
d28, d1 = F.getTargetElev(curve, HecTime(datetime.date(2023,2,28))), F.getTargetElev(curve, HecTime(datetime.date(2023,3,1)))
check("03:00 is 1/8 of the way from yesterday's target", F.getTargetElev(curve, HecTime(datetime.date(2023,3,1), 180)),
      d28 + (d1 - d28) * 0.125)
check("12:00 is halfway", F.getTargetElev(curve, HecTime(datetime.date(2023,3,1), 720)), d28 + (d1 - d28) * 0.5)
check("2400 is today's target", F.getTargetElev(curve, HecTime(datetime.date(2023,3,1), 1440)), d1)
check("00:00 is today's value too (no half-step jump)", F.getTargetElev(curve, HecTime(datetime.date(2023,3,1), 0)), d1)
check("01Jan interpolates from 31Dec", F.getTargetElev(curve, HecTime(datetime.date(2023,1,1), 720)),
      F.getTargetElev(curve, HecTime(datetime.date(2022,12,31))) + (F.getTargetElev(curve, HecTime(datetime.date(2023,1,1)))
      - F.getTargetElev(curve, HecTime(datetime.date(2022,12,31)))) * 0.5)
check("Detroit 01Jun (summer)", F.getTargetElev(curve, HecTime(datetime.date(2023,6,1))), 1558.5)
# 01Mar is 28 days into the 01Feb->01May refill (32->121 doy), 89-day ramp
# 01Mar (doy 60) sits 28 days into the 01Feb (32) -> 01May (121) refill ramp
frac = (60.0 - 32.0) / (121.0 - 32.0)
check("Detroit 01Mar (mid-refill)", F.getTargetElev(curve, HecTime(datetime.date(2023,3,1))),
      1484.5 + frac * (1558.5 - 1484.5), 0.05)  # CSV stores 1 decimal place
check("both fixture projects loaded", len(F.loadFiroConfig(CONFIG_CSV)), 2)

print("\n=== 1b. The shipped config file still loads ===")
shipped = F.loadFiroConfig(SHIPPED_CSV)
check("shipped config has reservoir columns", len(shipped) > 0, True)
thin = []
for name in sorted(shipped.keys()):
    days = F.countTargetDays(shipped[name])
    if days < 365:
        thin.append("%s=%d" % (name, days))
check("every shipped column has most of the year covered",
      [n for n in shipped if F.countTargetDays(shipped[n]) < 300], [])
print("    %d projects; columns not covering all 365 days: %s"
      % (len(shipped), ", ".join(thin) if thin else "none"))

print("\n=== 2. Leap year does not shift the curve ===")
check("01Mar 2024 (leap) == 01Mar 2023",
      F.getTargetElev(curve, HecTime(datetime.date(2024,3,1))),
      F.getTargetElev(curve, HecTime(datetime.date(2023,3,1))))
check("29Feb maps to 28Feb",
      F.getTargetElev(curve, HecTime(datetime.date(2024,2,29))),
      F.getTargetElev(curve, HecTime(datetime.date(2023,2,28))))

print("\n=== 3. Direction of the limit ===")
CFS_TO_AF_DAY = (60*60*24)/43560.0
def run(elevPrev, inflow, date=datetime.date(2023,1,15), glide=3.0):
    F.GLIDE_DAYS = glide
    target = F.getTargetElev(curve, HecTime(date))
    net2 = Network({"Elev": TS(prev=elevPrev),
                    "Stor": TS(prev=elevPrev*1000.0),
                    "Flow-IN": TS(cur=inflow)})
    r = Rule("Detroit")
    F.initRuleScript(r, net2)
    ov = F.runRuleScript(r, net2, RTS(date))
    return ov, target

# A MAX limit everywhere, continuous through the crossing.
ov, target = run(elevPrev=1490.0, inflow=1000.0)   # 5.5 ft above the curve
check("above curve -> MAX", ov.type, "MAX")
check("above curve -> allows release > inflow (draft back down)", ov.value > 1000.0, True)
ov, target = run(elevPrev=1480.0, inflow=1000.0)   # 4.5 ft below the curve
check("below curve -> MAX", ov.type, "MAX")
check("below curve -> release < inflow (fill)", ov.value < 1000.0, True)

# The property that killed the oscillation: no cliff at the crossing.
ov, target = run(elevPrev=1484.5, inflow=1000.0)   # exactly on the curve
check("on curve -> MAX equals inflow (continuous)", ov.value, 1000.0, 1e-6)
above = run(elevPrev=1484.5 + 0.001, inflow=1000.0)[0].value
below = run(elevPrev=1484.5 - 0.001, inflow=1000.0)[0].value
check("no discontinuity across the crossing", abs(above - below) < 1.0, True)
check("a MODE setting no longer exists", hasattr(F, "MODE") or hasattr(F, "MODE_BY_RESERVOIR"), False)

print("\n=== 4. Mass balance: does the release land on target? ===")
# GLIDE_DAYS = 1 asks the pool to land exactly on the curve in one timestep.
for elevPrev, inflow in [(1490.0, 1000.0), (1520.0, 5000.0), (1483.0, 4000.0)]:
    ov, target = run(elevPrev, inflow, glide=1.0)
    storNew = elevPrev * 1000.0 + (inflow - ov.value) * CFS_TO_AF_DAY
    check("elev %.1f in %.0f cfs -> lands on target" % (elevPrev, inflow),
          storNew / 1000.0, target, 1e-6)

# Not reachable: pool is below the curve and inflow alone cannot close the gap,
# so the required release is negative and clamps to 0 -- gates shut, fill as
# fast as physically possible, without overshooting the curve.
ov, target = run(elevPrev=1480.0, inflow=1000.0, glide=1.0)
check("unreachable fill -> MAX clamps to 0", (ov.type, ov.value), ("MAX", 0.0))
storNew = 1480.0 * 1000.0 + (1000.0 - ov.value) * CFS_TO_AF_DAY
check("unreachable fill -> moves toward curve", storNew / 1000.0 > 1480.0, True)
check("unreachable fill -> does not overshoot", storNew / 1000.0 <= target, True)

print("\n=== 5. Guards ===")
net3 = Network({"Elev": TS(prev=1e38), "Stor": TS(prev=1e38), "Flow-IN": TS(cur=1000.0)})
r3 = Rule("Detroit"); F.initRuleScript(r3, net3)
ov = F.runRuleScript(r3, net3, RTS(datetime.date(2023,1,15)))
check("DSS missing sentinel -> does not bind", (ov.type, ov.value), ("MIN", 0.0))

netFC = Network({"Elev": TS(prev=1400.0), "Stor": TS(prev=1400000.0),
                 "Flow-IN": TS(cur=1000.0)})
ruleFC = Rule("Fall Creek")
F.initRuleScript(ruleFC, netFC)          # must NOT raise
ovFC = F.runRuleScript(ruleFC, netFC, RTS(datetime.date(2023, 1, 15)))
check("reservoir absent from config -> no error, no control",
      (ovFC.type, ovFC.value), ("MIN", 0.0))
check("absent reservoir is reported in the log",
      len([m for m in netFC.messages if "will not control" in m]), 1)

F.REQUIRE_RESERVOIR_IN_CONFIG = True
try:
    F.initRuleScript(Rule("Fall Creek"), Network())
    check("REQUIRE_RESERVOIR_IN_CONFIG=True raises", False, True)
except AssertionError as e:
    check("REQUIRE_RESERVOIR_IN_CONFIG=True raises", "Fall Creek" in str(e), True)
F.REQUIRE_RESERVOIR_IN_CONFIG = False

print("\n=== 6. Blank cells and NO-TARGET days ===")
sparse = os.path.join(_HERE, "_sparse_tmp.csv")
open(sparse, "w").write("# sparse test\nMonth,Day,Detroit,Cougar\n1,1,1400,\n"
                        "4,1,1500,1600\n7,1,,1700\n12,31,1400,1600\n")

F.INTERPOLATE_GAPS_UP_TO_DAYS = 0
curves = F.loadFiroConfig(sparse)
check("both columns present", sorted(curves.keys()), ["Cougar", "Detroit"])
check("a day with a number has a target",
      F.getTargetElev(curves["Detroit"], HecTime(datetime.date(2023, 4, 1))), 1500.0)
check("a blank day has NO target",
      F.getTargetElev(curves["Detroit"], HecTime(datetime.date(2023, 2, 1))), None)
check("a blank day mid-file has NO target",
      F.getTargetElev(curves["Detroit"], HecTime(datetime.date(2023, 7, 1))), None)
check("blank first row -> Cougar has no target 01Jan",
      F.getTargetElev(curves["Cougar"], HecTime(datetime.date(2023, 1, 1))), None)
check("Detroit target-day count", F.countTargetDays(curves["Detroit"]), 3)

# Opt back in to bridging gaps, the way a ResSim zone would
F.INTERPOLATE_GAPS_UP_TO_DAYS = 365
curves = F.loadFiroConfig(sparse)
check("with bridging: 01Feb interpolates between 01Jan and 01Apr",
      1400.0 < F.getTargetElev(curves["Detroit"], HecTime(datetime.date(2023, 2, 1))) < 1500.0,
      True)
check("with bridging: every day has a target",
      F.countTargetDays(curves["Detroit"]), 365)
check("with bridging: wraps across 31Dec",
      F.getTargetElev(curves["Cougar"], HecTime(datetime.date(2023, 1, 1))) is not None, True)
F.INTERPOLATE_GAPS_UP_TO_DAYS = 0

print("\n=== 6b. Column-name matching and bad values ===")
ws = os.path.join(_HERE, "_ws_tmp.csv")
open(ws, "w").write("Month,Day,Detroit ,  hills creek\n1,1,1400,900\n12,31,1400,900\n")
wsCurves = F.loadFiroConfig(ws)
cols = list(wsCurves.keys())
check("trailing space in header still matches",
      F._findColumnForReservoir("Detroit", cols), "Detroit ")
check("different capitalization still matches",
      F._findColumnForReservoir("Hills Creek", cols), "  hills creek")
check("a genuinely absent name does not match",
      F._findColumnForReservoir("Cougar", cols), None)
os.remove(ws)

bad = os.path.join(_HERE, "_bad_tmp.csv")
for junk in ["fourteen hundred", "NONE"]:
    open(bad, "w").write("Month,Day,Detroit\n1,1,1400\n1,2,%s\n" % junk)
    try:
        F.loadFiroConfig(bad)
        check("'%s' in a cell raises" % junk, False, True)
    except AssertionError as e:
        check("'%s' in a cell raises, not silently uncontrolled" % junk,
              junk in str(e), True)
os.remove(bad)

os.remove(sparse)

print("\n=== 7. An edited CSV is picked up at the next compute, not mid-compute ===")
reloadCsv = os.path.join(_HERE, "_reload_tmp.csv")

class PinnedNetwork(Network):
    """Points the rule at the temp CSV regardless of the configured path."""
    def makeAbsolutePathFromWatershed(self, rel):
        return reloadCsv

def writeCurve(elev, stamp):
    fh = open(reloadCsv, "w")
    fh.write("Month,Day,Detroit\n1,1,%s\n12,31,%s\n" % (elev, elev))
    fh.close()
    os.utime(reloadCsv, (stamp, stamp))   # force a distinct modified time

netR = PinnedNetwork({"Elev": TS(prev=1450.0), "Stor": TS(prev=1450000.0),
                      "Flow-IN": TS(cur=1000.0)})
ruleR = Rule("Detroit")

F.GLIDE_DAYS = 1.0
F.INTERPOLATE_GAPS_UP_TO_DAYS = 365   # 2-row test files, bridge the year
writeCurve("1400.0", 1000000000)
F.initRuleScript(ruleR, netR)
ov1 = F.runRuleScript(ruleR, netR, RTS(datetime.date(2023, 1, 15)))
check("pool 1450 vs curve 1400 -> MAX above inflow (let it draft)", ov1.value > 1000.0, True)

# Edit the file mid-compute. The file is not checked per step, so nothing changes.
writeCurve("1500.0", 1000000060)
ov2 = F.runRuleScript(ruleR, netR, RTS(datetime.date(2023, 1, 16)))
check("mid-compute edit is not read (no per-step file check)", ov2.value, ov1.value, 1e-6)
check("no reload reported mid-compute",
      len([m for m in netR.messages if "loaded Detroit" in m]), 1)

# The next compute runs init again, on the same rule object ResSim keeps alive.
F.initRuleScript(ruleR, netR)
ov3 = F.runRuleScript(ruleR, netR, RTS(datetime.date(2023, 1, 15)))
check("next compute -> MAX below inflow (fill up), i.e. new values took effect", ov3.value < 1000.0, True)
check("the new load was reported to the compute log",
      len([m for m in netR.messages if "loaded Detroit" in m]), 2)
F.GLIDE_DAYS = 3.0
os.remove(reloadCsv)

print("\n=== 8. Closed-loop stability (regression for the sawtooth) ===")
# Drive the rule in a mass-balance loop with the pool in flood space, where the
# rest of the stack would release up to outlet capacity. That is the situation
# where switching from a MAX to a MIN near the curve gave a release spike and a
# sawtooth; the MAX alone must settle on the curve from either side.
AFPF, CFDAY, CAP = 3500.0, (60 * 60 * 24) / 43560.0, 10000.0
INFLOW, MINFLOW = 3000.0, 1200.0

def closedLoop(glide, steps=40, startErr=5.0):
    """Returns (peak-to-peak pool error over the last 12 steps, final error), ft."""
    F.GLIDE_DAYS = glide
    targetStor = 1500.0 * 1000.0
    err = startErr
    errors = []
    for _ in range(steps):
        stor = targetStor + err * AFPF
        netL = PinnedNetwork({"Elev": TS(prev=1500.0 + err),
                              "Stor": TS(prev=stor),
                              "Flow-IN": TS(cur=INFLOW)})
        netL.elevStorTable = FlatTable(targetStor, AFPF)
        ruleL = Rule("Detroit")
        F.initRuleScript(ruleL, netL)
        ov = F.runRuleScript(ruleL, netL, RTS(datetime.date(2023, 1, 15)))
        actual = min(ov.value, CAP)   # flood ops want CAP; the MAX holds it back
        err += (INFLOW - actual) * CFDAY / AFPF
        errors.append(err)
    tail = errors[-12:]
    return max(tail) - min(tail), err

class FlatTable(object):
    """elev -> storage around the flat 1500 ft test curve."""
    def __init__(self, targetStor, afpf):
        self.targetStor, self.afpf = targetStor, afpf
    def interpolate(self, elev):
        return self.targetStor + (elev - 1500.0) * self.afpf

writeCurve("1500.0", 1000000200)
# Start above the curve (drafting back down) and below it (refilling).
for label, startErr in [("from above", 5.0), ("from below", -5.0)]:
    ringing, final = closedLoop(glide=3.0, startErr=startErr)
    check("%s settles (peak-to-peak < 0.1 ft)" % label, ringing < 0.1, True)
    check("%s ends on the curve (within 0.1 ft)" % label, abs(final) < 0.1, True)
    print("    %-11s peak-to-peak over last 12 days: %.3f ft, final %.3f ft"
          % (label, ringing, final))
F.GLIDE_DAYS = 3.0
F.INTERPOLATE_GAPS_UP_TO_DAYS = 0
os.remove(reloadCsv)

os.remove(CONFIG_CSV)
print("\n" + ("ALL PASSED" if not fails else "FAILURES: %s" % fails))
sys.exit(1 if fails else 0)
