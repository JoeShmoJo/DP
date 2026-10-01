"""
Offline test that the storage-correcting rules behave the same on a daily and a
sub-daily (hourly) timestep: IRRM, HCR_LOP_Balance, SpringSpill, DeepDrawdown
and DraftToRC.

Stubs the hec.* Java classes and the NWDJyLib modules that import Java. The
HecTime stub keeps minutes and follows HEC's 24:00 convention: midnight belongs
to the day that is ending, so 01Jan 24:00 reports day 1, not day 2.

Run it with either Python 2.7 or Python 3 from anywhere:
    python test_TimestepScaling.py

This does NOT test anything ResSim-side. In particular it cannot prove the real
HecTime compares and shifts times the way the stub does; it tests the logic
that is ours.
"""
import sys, os, types, datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
RULES_DIR = os.path.dirname(_HERE)
SCRIPTS_DIR = os.path.dirname(RULES_DIR)
sys.path.insert(0, SCRIPTS_DIR)
sys.path.insert(0, RULES_DIR)
SPRING_CSV = os.path.join(_HERE, "_fixture_springspill_tmp.csv")
DRAWDOWN_CSV = os.path.join(_HERE, "_fixture_deepdrawdown_tmp.csv")

def writeFixtures():
    fh = open(SPRING_CSV, "w")
    fh.write("# generated fixture\n"
             "RESERVOIR,START_MONTH,START_DAY,END_MONTH,END_DAY,DURATION_DAYS,TARGET_ELEV,ACTIVE\n"
             "Lookout Point,3,15,4,30,30,890,TRUE\n")
    fh.close()
    fh = open(DRAWDOWN_CSV, "w")
    fh.write("# generated fixture\n"
             "RESERVOIR,START_MONTH,START_DAY,TARGET_MONTH,TARGET_DAY,END_MONTH,END_DAY,DURATION_DAYS,TARGET_ELEV,ACTIVE\n"
             "Lookout Point,10,1,11,15,12,31,30,750,TRUE\n")
    fh.close()

writeFixtures()

# ---- stub hec.heclib.util.HecTime -------------------------------------------
class HecTime(object):
    MINUTE_INCREMENT = 1
    def __init__(self, dt=None):
        self._dt = dt
    def set(self, other):
        self._dt = other._dt
    def setYearMonthDay(self, y, m, d, minutes):
        self._dt = datetime.datetime(y, m, d) + datetime.timedelta(minutes=minutes)
    def clone(self):
        return HecTime(self._dt)
    def addMinutes(self, n):
        self._dt = self._dt + datetime.timedelta(minutes=n)
    def addDays(self, n):
        self._dt = self._dt + datetime.timedelta(days=n)
    def subtractDays(self, n):
        self._dt = self._dt - datetime.timedelta(days=n)
    def _label(self):
        # 00:00 is reported as 24:00 of the day before
        if self._dt.hour == 0 and self._dt.minute == 0:
            return self._dt - datetime.timedelta(days=1)
        return self._dt
    def year(self):
        return self._label().year
    def month(self):
        return self._label().month
    def day(self):
        return self._label().day
    def lessThan(self, o):
        return self._dt < o._dt
    def lessThanEqualTo(self, o):
        return self._dt <= o._dt
    def greaterThan(self, o):
        return self._dt > o._dt
    def greaterThanEqualTo(self, o):
        return self._dt >= o._dt
    def equalTo(self, o):
        return self._dt == o._dt
    def computeNumberIntervals(self, o, minutes):
        return int((o._dt - self._dt).total_seconds() // 60 // minutes)
    def dateAndTime(self):
        return self._dt.isoformat()

class OpRule(object):
    RULETYPE_MIN = "MIN"
    RULETYPE_MAX = "MAX"

class OpValue(object):
    def __init__(self):
        self.type = None
        self.value = None
    def init(self, t, v):
        self.type, self.value = t, v

class RunTimeStep(object):
    def __init__(self, rts):
        pass
    def setStep(self, step):
        pass

class _NeverActiveRule(object):
    def getOpValue(self, rts):
        return None

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
_mod("hec.model", RunTimeStep=RunTimeStep)

import NWDJyLib  # real package, harmless __init__
_mod("NWDJyLib.cTimes", getHecTimeFromRuntimestep=lambda rts: rts.getHecTime())
_mod("NWDJyLib.ResSim")
_mod("NWDJyLib.ResSim.cResSim",
     getElevationStorageTable=lambda n, net: ElevStorTable(),
     getRule=lambda resv, name, net: _NeverActiveRule())
sys.modules["NWDJyLib.ResSim"].cResSim = sys.modules["NWDJyLib.ResSim.cResSim"]

import IRRM, HCR_LOP_Balance, SpringSpill, DeepDrawdown, DraftToRC  # noqa: E402

# ---- fake ResSim objects -----------------------------------------------------
CFSDAY_TO_AF = (60 * 60 * 24) / 43560.0

class ElevStorTable(object):
    """Straight-line elev->storage: 1000 ac-ft per foot above elev 0."""
    def interpolate(self, elev):
        return elev * 1000.0

class TS(object):
    """prev/cur may be a number or a function of the runtimestep."""
    def __init__(self, prev=None, cur=None, at=None):
        self._prev, self._cur, self._at = prev, cur, at
    def _v(self, v, rts):
        if callable(v):
            return v(rts)
        return v
    def getPreviousValue(self, rts):
        return self._v(self._prev, rts)
    def getCurrentValue(self, rts):
        return self._v(self._cur, rts)
    def getValue(self, hTime):
        return self._at(hTime)

class AltSetup(object):
    def __init__(self, vals):
        self.vals = vals
    def varGet(self, k):
        return self.vals[k]
    def varExists(self, k):
        return k in self.vals

class Network(object):
    def __init__(self, ts=None, byResv=None, alt=None):
        self.ts = ts or {}
        self.byResv = byResv or {}
        self.alt = AltSetup(alt or {})
        self.messages = []
    def getTimeSeries(self, a, resv, group, param):
        key = (resv, group, param)
        if key in self.byResv:
            return self.byResv[key]
        return self.ts[(group, param)]
    def getStateVariable(self, name):
        return self.alt
    def makeAbsolutePathFromWatershed(self, rel):
        return rel
    def printMessage(self, m):
        self.messages.append(m)

class ResvElement(object):
    def __init__(self, name):
        self._name = name
    def toString(self):
        return self._name

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
    def __init__(self, dt, minutes):
        self._dt, self._min = dt, minutes
    def getHecTime(self):
        return HecTime(self._dt)
    def getTimeStepMinutes(self):
        return self._min
    def getPrevStep(self):
        return None

def at(y, m, d, hour=24):
    """A timestamp; hour=24 is the end of the day, HEC style."""
    return datetime.datetime(y, m, d) + datetime.timedelta(hours=hour)

DAILY, HOURLY = 1440, 60

# ---- tiny assertion harness --------------------------------------------------
PASS = [0]
FAIL = []

def check(label, got, want, tol=1e-6):
    ok = (got == want) if not isinstance(want, float) else abs(got - want) <= tol
    if ok:
        PASS[0] += 1
    else:
        FAIL.append("%s\n    got  %r\n    want %r" % (label, got, want))

def section(title):
    print("\n-- %s" % title)

# ---- IRRM --------------------------------------------------------------------
section("IRRM pulls back over a day, whatever the step")
def irrm(minutes):
    net = Network(ts={("Pool", "Stor"): TS(prev=100100.0),
                      ("Pool", "Flow-IN"): TS(cur=500.0)},
                  alt={"irrmTargetElevs": {"Detroit": 100.0},
                       "irrmActive": {"Detroit": True}})
    rule = Rule("Detroit")
    IRRM.initRuleScript(rule, net)
    return IRRM.runRuleScript(rule, net, RTS(at(2023, 1, 15), minutes)).value
want = 500.0 + 100.0 / CFSDAY_TO_AF
check("daily: 100 AF over target adds ~50 cfs", irrm(DAILY), want)
check("hourly: same flow, not 24x", irrm(HOURLY), want)

# ---- HCR_LOP_Balance ---------------------------------------------------------
section("HCR_LOP_Balance correction is the same on either step")
def hcr(minutes):
    minCon = {"Hills Creek": 1448000.0, "Lookout Point": 825000.0}
    net = Network(byResv={
        ("Lookout Point", "Pool", "Stor"): TS(prev=minCon["Lookout Point"] + 50000.0),
        ("Hills Creek", "Pool", "Stor"): TS(prev=minCon["Hills Creek"] + 47000.0),
        ("Hills Creek", "Pool", "Flow-IN"): TS(cur=1000.0)})
    rule = Rule("Hills Creek")
    HCR_LOP_Balance.initRuleScript(rule, net)
    return HCR_LOP_Balance.runRuleScript(rule, net, RTS(at(2023, 7, 1), minutes)).value
check("daily and hourly releases match", hcr(HOURLY), hcr(DAILY))
check("and the release is not pinned at the cap", hcr(DAILY) < HCR_LOP_Balance.HIGHEST_MIN_FLOW, True)

# ---- SpringSpill window ------------------------------------------------------
section("SpringSpill window opens at the start of the start day")
def springNet(elevPrev):
    return Network(ts={("Pool", "Elev"): TS(prev=elevPrev),
                       ("Pool", "Stor"): TS(prev=elevPrev * 1000.0),
                       ("Pool", "Flow-IN"): TS(cur=2000.0)},
                   alt={"SpringSpillConfigCSV": SPRING_CSV})
def springRun(rule, net, dt, minutes):
    return SpringSpill.runRuleScript(rule, net, RTS(dt, minutes)).value

net = springNet(900.0)
rule = Rule("Lookout Point")
SpringSpill.initRuleScript(rule, net)
check("daily: 14Mar is outside", springRun(rule, net, at(2023, 3, 14), DAILY), 0.0)
check("daily: 15Mar (stamped 24:00) is inside",
      springRun(rule, net, at(2023, 3, 15), DAILY) > 0.0, True)

rule = Rule("Lookout Point")
SpringSpill.initRuleScript(rule, net)
check("hourly: 15Mar 00:00 (= 14Mar 24:00) is outside",
      springRun(rule, net, at(2023, 3, 15, 0), HOURLY), 0.0)
check("hourly: 15Mar 01:00 is inside",
      springRun(rule, net, at(2023, 3, 15, 1), HOURLY) > 0.0, True)
check("hourly: 30Apr 23:00 is still inside",
      springRun(rule, net, at(2023, 4, 30, 23), HOURLY) > 0.0, True)
check("hourly: 01May 01:00 is outside",
      springRun(rule, net, at(2023, 5, 1, 1), HOURLY), 0.0)

section("SpringSpill hourly: the success trigger is not reset later in the start day")
net = springNet(893.0)   # already within TARGET_BUFFER of 890
rule = Rule("Lookout Point")
SpringSpill.initRuleScript(rule, net)
springRun(rule, net, at(2023, 3, 15, 1), HOURLY)
firstEnd = rule.varGet("endDate")._dt
springRun(rule, net, at(2023, 3, 15, 5), HOURLY)
check("end date still counts from 15Mar 01:00",
      rule.varGet("endDate")._dt, firstEnd)
check("which is 01:00 + 30 days", firstEnd, at(2023, 4, 14, 1))

section("SpringSpill pull-back is the same on either step")
net = springNet(890.1)   # 100 AF above target
rule = Rule("Lookout Point")
SpringSpill.initRuleScript(rule, net)
d = springRun(rule, net, at(2023, 3, 20), DAILY)
rule = Rule("Lookout Point")
SpringSpill.initRuleScript(rule, net)
h = springRun(rule, net, at(2023, 3, 20, 12), HOURLY)
check("daily ~ inflow + 50 cfs", d, 2000.0 + 100.0 / CFSDAY_TO_AF, tol=1e-3)
check("hourly matches daily", h, d, tol=1e-3)

# ---- DeepDrawdown ------------------------------------------------------------
section("DeepDrawdown window and glide")
def ddNet(elevPrev):
    return Network(ts={("Pool", "Elev"): TS(prev=elevPrev),
                       ("Pool", "Stor"): TS(prev=elevPrev * 1000.0),
                       ("Pool", "Flow-IN"): TS(cur=1000.0)},
                   alt={"DeepDrawdownConfigCSV": DRAWDOWN_CSV})
def ddRun(rule, net, dt, minutes):
    return DeepDrawdown.runRuleScript(rule, net, RTS(dt, minutes)).value

net = ddNet(800.0)
rule = Rule("Lookout Point")
DeepDrawdown.initRuleScript(rule, net)
check("hourly: 01Oct 00:00 is outside", ddRun(rule, net, at(2023, 10, 1, 0), HOURLY), 0.0)
h = ddRun(rule, net, at(2023, 10, 1, 1), HOURLY)
rule = Rule("Lookout Point")
DeepDrawdown.initRuleScript(rule, net)
check("daily: 30Sep is outside", ddRun(rule, net, at(2023, 9, 30), DAILY), 0.0)
d = ddRun(rule, net, at(2023, 10, 1), DAILY)
check("both steps glide to the same average release on the first day", h, d, tol=d * 0.03)

net = ddNet(750.1)   # after the target date, 100 AF above target
rule = Rule("Lookout Point")
DeepDrawdown.initRuleScript(rule, net)
d = ddRun(rule, net, at(2023, 11, 20), DAILY)
rule = Rule("Lookout Point")
DeepDrawdown.initRuleScript(rule, net)
h = ddRun(rule, net, at(2023, 11, 20, 12), HOURLY)
check("after target: daily ~ inflow + 50 cfs", d, 1000.0 + 100.0 / CFSDAY_TO_AF, tol=1e-3)
check("after target: hourly matches daily", h, d, tol=1e-3)

# ---- DraftToRC ---------------------------------------------------------------
section("DraftToRC lookahead is in cfs")
def draft(minutes, inflow=1000.0, excessAF=3000.0, rcNow=400000.0, storPrev=None):
    rc = 400000.0
    if storPrev is None:
        storPrev = rc + excessAF
    net = Network(ts={("Pool", "Flow-IN"): TS(cur=inflow, at=lambda t: inflow),
                      ("Pool", "Stor"): TS(prev=storPrev),
                      ("Rule Curve", "Stor-ZONE"): TS(cur=rcNow, at=lambda t: rc)})
    return DraftToRC.runRuleScript(Rule("Detroit"), net, RTS(at(2023, 1, 15), minutes)).value
# The lookahead aims BUFFER below the rule curve
want = 1000.0 + (3000.0 + DraftToRC.BUFFER) / (DraftToRC.DAYS_LOOKAHEAD * CFSDAY_TO_AF)
check("daily: inflow + excess spread over the lookahead", draft(DAILY), want, tol=1e-6)
check("hourly: the same", draft(HOURLY), want, tol=1e-6)
check("daily: below the land-on-the-curve-now release, so it binds",
      draft(DAILY) < 1000.0 + 3000.0 / CFSDAY_TO_AF, True)

section("DraftToRC can be switched off per reservoir")
def draftWith(alt):
    net = Network(ts={("Pool", "Flow-IN"): TS(cur=1000.0, at=lambda t: 1000.0),
                      ("Pool", "Stor"): TS(prev=403000.0),
                      ("Rule Curve", "Stor-ZONE"): TS(cur=400000.0, at=lambda t: 400000.0)}, alt=alt)
    rule = Rule("Detroit")
    DraftToRC.initRuleScript(rule, net)
    return DraftToRC.runRuleScript(rule, net, RTS(at(2023, 1, 15), DAILY))
check("no draftToRCActive: on", draftWith({}) is not None, True)
check("true: on", draftWith({"draftToRCActive": True}) is not None, True)
check("false: no effect", draftWith({"draftToRCActive": False}), None)
check("reservoir not listed: on", draftWith({"draftToRCActive": {"Cougar": False}}) is not None, True)
check("listed true: on", draftWith({"draftToRCActive": {"Detroit": True}}) is not None, True)
check("listed false: no effect", draftWith({"draftToRCActive": {"Detroit": False}}), None)

for path in (SPRING_CSV, DRAWDOWN_CSV):
    if os.path.exists(path):
        os.remove(path)

print("\n%d checks passed, %d failed" % (PASS[0], len(FAIL)))
for f in FAIL:
    print("\nFAIL: %s" % f)
sys.exit(1 if FAIL else 0)
