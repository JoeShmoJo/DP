"""
Offline test harness for externalRules/MinFlowPlusWithdrawal.py.

Stubs the hec.* Java classes and the NWDJyLib module that imports Java, so the
rule's CSV parsing and summing can be exercised on a plain Python interpreter
without launching ResSim. cFile is imported for real.

Run it with either Python 2.7 or Python 3 from anywhere:
    python test_MinFlowPlusWithdrawal.py

This does NOT test anything ResSim-side (rule stack behavior, OpValue handling).
It tests the logic that is ours, plus a sanity check on the shipped configs.
"""
import sys, os, types, datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
RULES_DIR = os.path.dirname(_HERE)
SCRIPTS_DIR = os.path.dirname(RULES_DIR)
sys.path.insert(0, SCRIPTS_DIR)
sys.path.insert(0, RULES_DIR)

SHIPPED_MIN_FLOW = os.path.join(RULES_DIR, "MinFlowConfig.csv")
SHIPPED_WITHDRAWAL = os.path.join(RULES_DIR, "WithdrawalConfig.csv")
FIXTURE_MIN_FLOW = os.path.join(_HERE, "_fixture_minflow_tmp.csv")
FIXTURE_WITHDRAWAL = os.path.join(_HERE, "_fixture_withdrawal_tmp.csv")


def writeFixtures():
    """
    Two small known files, so the behaviour tests do not depend on whatever
    numbers happen to be in the shipped configs.

      Detroit  -- in both files. Min flow 1000 all year. Withdrawal 0 except
                  100 from 01May through 30Sep.
      Foster   -- withdrawal only (50 all year), no min flow column at all.
                  Covers the general "present in one file only" case. Note the
                  SHIPPED Foster is different: its demand is released from Green
                  Peter, so it is blank in both files. Section 9 checks that.
      Cougar   -- min flow only (300 all year), withdrawal column all blank.
      Dorena   -- in both files but blank in both for the whole of February,
                  so the rule should stand down on those days.
    """
    def rows(header, valueFor):
        out = ["# generated fixture", header]
        for n in range(1, 366):
            date = datetime.date(2001, 1, 1) + datetime.timedelta(days=n - 1)
            out.append("%d,%d,%s" % (date.month, date.day, valueFor(date)))
        return "\n".join(out) + "\n"

    def minFlowRow(date):
        dorena = "" if date.month == 2 else "150"
        return "1000,300,%s" % dorena

    def withdrawalRow(date):
        detroit = "100" if 5 <= date.month <= 9 else "0"
        dorena = "" if date.month == 2 else "25"
        return "%s,50,,%s" % (detroit, dorena)

    fh = open(FIXTURE_MIN_FLOW, "w")
    fh.write(rows("Month,Day,Detroit,Cougar,Dorena", minFlowRow))
    fh.close()
    fh = open(FIXTURE_WITHDRAWAL, "w")
    fh.write(rows("Month,Day,Detroit,Foster,Cougar,Dorena", withdrawalRow))
    fh.close()


writeFixtures()

# ---- stub hec.heclib.util.HecTime -------------------------------------------
class HecTime(object):
    def __init__(self, d=None):
        self._d = d
    def setYearMonthDay(self, y, m, d, minutes):
        self._d = datetime.date(y, m, d)
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

import NWDJyLib  # real package, harmless __init__
_mod("NWDJyLib.cTimes", getHecTimeFromRuntimestep=lambda rts: rts.getHecTime())

import MinFlowPlusWithdrawal as M  # noqa: E402

# ---- fake ResSim objects -----------------------------------------------------
class TS(object):
    def __init__(self, prev=None, cur=None):
        self._prev, self._cur = prev, cur
    def getPreviousValue(self, rts):
        return self._prev
    def getCurrentValue(self, rts):
        return self._cur

class RssRun(object):
    def __init__(self, network):
        self.network = network
    def getTSRecordByPathParts(self, element, parameter):
        self.network.lookups += 1
        key = (element, parameter)
        if key not in self.network.records:
            raise RuntimeError("no such record %s" % (key,))
        return self.network.records[key]

class Network(object):
    """Resolves the two config keys to the fixtures unless told to use shipped."""
    def __init__(self, useShipped=False, ts=None, records=None):
        self.useShipped = useShipped
        self.messages = []
        # {(resvName, group, param): TS}
        self.ts = ts or {}
        # {(element, parameter): TS}
        self.records = records if records is not None else {}
        self.lookups = 0
    def getTimeSeries(self, kind, resvName, group, param):
        return self.ts[(resvName, group, param)]
    def getRssRun(self):
        return RssRun(self)
    def getStateVariable(self, name):
        raise RuntimeError("no such state variable")   # exercises the fallback path
    def makeAbsolutePathFromWatershed(self, rel):
        if self.useShipped:
            return os.path.join(RULES_DIR, os.path.basename(rel))
        if "MinFlow" in rel:
            return FIXTURE_MIN_FLOW
        return FIXTURE_WITHDRAWAL
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


def runDay(resvName, date, network=None):
    """Init + run one timestep, returning the OpValue."""
    rule = Rule(resvName)
    net = network or Network()
    M.initRuleScript(rule, net)
    return M.runRuleScript(rule, net, RTS(date)), net


################################################################################
section("1. the sum, on a project that is in both files")
op, _ = runDay("Detroit", datetime.date(2020, 1, 15))
check("Detroit 15Jan is min flow only (1000 + 0)", op.value, 1000.0)
check("Detroit sets a MIN limit", op.type, OpRule.RULETYPE_MIN)

op, _ = runDay("Detroit", datetime.date(2020, 7, 15))
check("Detroit 15Jul adds the withdrawal (1000 + 100)", op.value, 1100.0)

op, _ = runDay("Detroit", datetime.date(2020, 5, 1))
check("Detroit 01May, first day of withdrawal", op.value, 1100.0)
op, _ = runDay("Detroit", datetime.date(2020, 4, 30))
check("Detroit 30Apr, day before", op.value, 1000.0)
op, _ = runDay("Detroit", datetime.date(2020, 9, 30))
check("Detroit 30Sep, last day of withdrawal", op.value, 1100.0)
op, _ = runDay("Detroit", datetime.date(2020, 10, 1))
check("Detroit 01Oct, day after", op.value, 1000.0)


################################################################################
section("2. a project in only one file still gets that one component")
op, _ = runDay("Foster", datetime.date(2020, 7, 15))
check("Foster has no min flow column, withdrawal alone binds", op.value, 50.0)
check("Foster still sets a MIN limit", op.type, OpRule.RULETYPE_MIN)

op, _ = runDay("Cougar", datetime.date(2020, 7, 15))
check("Cougar withdrawal column is blank, min flow alone binds", op.value, 300.0)


################################################################################
section("3. blank in BOTH files means the rule stands down")
op, _ = runDay("Dorena", datetime.date(2020, 2, 15))
check("Dorena 15Feb is blank in both, so MIN 0 does not bind", op.value, 0.0)
check("Dorena 15Feb type", op.type, OpRule.RULETYPE_MIN)
op, _ = runDay("Dorena", datetime.date(2020, 3, 15))
check("Dorena 15Mar has both (150 + 25)", op.value, 175.0)


################################################################################
section("4. a project in neither file is not an error")
op, net = runDay("Blue River", datetime.date(2020, 7, 15))
check("Blue River gets a non-binding MIN 0", op.value, 0.0)
check("the compute is told why", "no numbers in either config file"
      in " ".join(net.messages), True)


################################################################################
section("5. day-of-year handling across a leap year")
tables = M.loadDailyConfig(FIXTURE_MIN_FLOW, "minimum flow")
check("fixture has the three columns",
      sorted(tables.keys()), ["Cougar", "Detroit", "Dorena"])
check("01Jan is day 1", M._genericDayOfYear(HecTime(datetime.date(2021, 1, 1))), 1)
check("01Mar is day 60 on a non-leap year",
      M._genericDayOfYear(HecTime(datetime.date(2021, 3, 1))), 60)
check("01Mar is still day 60 in a LEAP year, not 61",
      M._genericDayOfYear(HecTime(datetime.date(2020, 3, 1))), 60)
check("29Feb is treated as 28Feb (day 59)",
      M._genericDayOfYear(HecTime(datetime.date(2020, 2, 29))), 59)
check("31Dec is day 365",
      M._genericDayOfYear(HecTime(datetime.date(2021, 12, 31))), 365)

# The withdrawal source is a leap year, so a shift here would misalign the whole
# irrigation season. Check the boundary day lands where the CSV says it does.
op, _ = runDay("Detroit", datetime.date(2020, 5, 1))
check("leap-year 01May still reads the 01May row", op.value, 1100.0)


################################################################################
section("6. column matching tolerates whitespace and case")
check("exact", M._findColumnForReservoir("Detroit", ["Detroit", "Cougar"]), "Detroit")
check("trailing space in the header",
      M._findColumnForReservoir("Detroit", ["Detroit ", "Cougar"]), "Detroit ")
check("different case",
      M._findColumnForReservoir("detroit", ["Detroit", "Cougar"]), "Detroit")
check("genuinely absent",
      M._findColumnForReservoir("Foster", ["Detroit", "Cougar"]), None)


################################################################################
section("7. blank is not zero")
mf = M.loadDailyConfig(FIXTURE_MIN_FLOW, "minimum flow")["Dorena"]
wd = M.loadDailyConfig(FIXTURE_WITHDRAWAL, "withdrawal")["Dorena"]
check("a blank cell reads as None, not 0.0", mf[40], None)     # day 40 is 09Feb
check("blank + blank is None (stand down)", M._total(mf, wd, 40), None)

zeroMf = [None] * 366
zeroMf[40] = 0.0
check("an explicit 0 + blank is 0.0, and DOES bind",
      M._total(zeroMf, wd, 40), 0.0)
check("count ignores blanks", M.countDefinedDays(mf), 365 - 28)


################################################################################
section("8. bad data is reported, not silently swallowed")
badPath = os.path.join(_HERE, "_fixture_bad_tmp.csv")
fh = open(badPath, "w")
fh.write("Month,Day,Detroit\n1,1,1000\n1,2,not-a-number\n")
fh.close()
try:
    M.loadDailyConfig(badPath, "minimum flow")
    check("a non-numeric cell raises", False, True)
except AssertionError as exc:
    check("a non-numeric cell names the file, row and value",
          "not-a-number" in str(exc) and "row 2" in str(exc), True)
os.remove(badPath)

dupPath = os.path.join(_HERE, "_fixture_dup_tmp.csv")
fh = open(dupPath, "w")
fh.write("Month,Day,Detroit\n1,1,1000\n1,1,1200\n")
fh.close()
try:
    M.loadDailyConfig(dupPath, "minimum flow")
    check("a duplicated day raises", False, True)
except AssertionError as exc:
    check("a duplicated day is named", "Duplicate" in str(exc), True)
os.remove(dupPath)


################################################################################
section("9. the SHIPPED configs parse and agree with their sources")
shippedMf = M.loadDailyConfig(SHIPPED_MIN_FLOW, "minimum flow")
shippedWd = M.loadDailyConfig(SHIPPED_WITHDRAWAL, "withdrawal")
check("shipped min flow has 10 projects (no Foster)", len(shippedMf), 10)
check("shipped withdrawal has 11 projects", len(shippedWd), 11)
check("Foster is absent from min flow, as in BiOpMINFLOW.csv",
      "Foster" in shippedMf, False)
check("no GPR_FOS column leaked into the withdrawal config",
      [c for c in shippedWd if "_" in c], [])

for name, table in sorted(shippedMf.items()):
    check("shipped min flow %s covers every day" % name,
          M.countDefinedDays(table), 365)
for name, table in sorted(shippedWd.items()):
    if name == "Foster":
        continue          # blank on purpose, checked below
    check("shipped withdrawal %s covers every day" % name,
          M.countDefinedDays(table), 365)

# Green Peter and Foster operate as a system and every release comes out of
# Green Peter, so Foster's demand is rolled into the Green Peter column and
# Foster is blank in both files. Getting this wrong either starves the Foster
# demand or double counts it, so check both halves.
check("shipped Foster withdrawal is blank all year",
      M.countDefinedDays(shippedWd["Foster"]), 0)
check("shipped Green Peter carries both demands on 01May",
      shippedWd["Green Peter"][121], 128.0)      # 116 at GPR + 12 at FOS
check("shipped Green Peter peak carries both",
      max(v for v in shippedWd["Green Peter"][1:] if v is not None), 308.0)

# Foster is in neither file, so the rule must stand down there rather than pin
# it to a minimum of 0.
op, net = runDay("Foster", datetime.date(2020, 7, 15), Network(useShipped=True))
check("shipped Foster gets a non-binding MIN 0", op.value, 0.0)
check("and the compute log says why",
      "no numbers in either config file" in " ".join(net.messages), True)

check("shipped Green Peter 15Jul target = min flow 800 + both demands 308",
      shippedMf["Green Peter"][196] + shippedWd["Green Peter"][196], 1108.0)

# Step-hold expansion of BiOpMINFLOW.csv: DET is 1000 from 01Feb and steps to
# 1500 on 16Mar, so 15Mar must still be 1000.
det = shippedMf["Detroit"]
check("Detroit 01Jan", det[1], 1200.0)
check("Detroit 15Mar is still the 01Feb value", det[74], 1000.0)
check("Detroit 16Mar steps up", det[75], 1500.0)

# The real sum, end to end, for a project that is in both files.
op, _ = runDay("Detroit", datetime.date(2020, 7, 15), Network(useShipped=True))
check("shipped Detroit 15Jul = min flow 1000 + withdrawal 336",
      op.value, det[196] + shippedWd["Detroit"][196])
check("and that is a real number, not zero", op.value > 0, True)


################################################################################
section("10. Green Peter backs its release out of a mass balance on Foster")

# One foot of Foster is 1000 ac-ft in these fixtures. At a daily timestep,
# 1 cfs held for a day is 1.98347 ac-ft, so a rule curve rise of 198.347 ac-ft
# over one step is a fill rate of exactly 100 cfs.
AF_PER_CFS_DAY = M.CFSDAY_TO_AF

def fosterNetwork(fillCfs=0.0, localCfs=0.0, actualStor=None, rcStor=100000.0):
    """A network where Foster's rule curve moves at fillCfs and locals are localCfs."""
    rcPrev = rcStor - fillCfs * AF_PER_CFS_DAY
    ts = {
        ("Foster", "Rule Curve", "Stor-ZONE"): TS(prev=rcPrev, cur=rcStor),
        ("Foster", "Pool", "Stor"): TS(prev=actualStor, cur=actualStor),
    }
    records = {("Foster_IN", "FLOW-CUMLOC"): TS(cur=localCfs)}
    return Network(useShipped=True, ts=ts, records=records)

# Target at Foster on 15Jul is min flow 800 + demand 308 = 1108.
TARGET_15JUL = 1108.0

op, net = runDay("Green Peter", datetime.date(2020, 7, 15),
                 fosterNetwork(fillCfs=0.0, localCfs=0.0))
check("no fill and no local: release is just the target", op.value, TARGET_15JUL)

op, _ = runDay("Green Peter", datetime.date(2020, 7, 15),
               fosterNetwork(fillCfs=0.0, localCfs=200.0))
check("local inflow is credited against the release",
      op.value, TARGET_15JUL - 200.0)

# The worked example: Foster filling at 100 cfs with 200 cfs of local.
op, _ = runDay("Green Peter", datetime.date(2020, 7, 15),
               fosterNetwork(fillCfs=100.0, localCfs=200.0))
check("filling RAISES the release: 1108 + 100 - 200",
      op.value, TARGET_15JUL + 100.0 - 200.0)

op, _ = runDay("Green Peter", datetime.date(2020, 7, 15),
               fosterNetwork(fillCfs=-100.0, localCfs=200.0))
check("drafting LOWERS the release: 1108 - 100 - 200",
      op.value, TARGET_15JUL - 100.0 - 200.0)

# Closing the loop: what Green Peter releases, plus the local, minus what Foster
# keeps, must equal the target passing Foster.
gpr = op.value
check("mass balance closes on Foster",
      gpr + 200.0 - (-100.0), TARGET_15JUL)

op, _ = runDay("Green Peter", datetime.date(2020, 7, 15),
               fosterNetwork(fillCfs=0.0, localCfs=5000.0))
check("local larger than the target does not ask for a negative release",
      op.value, 0.0)

# Missing rule curve data (the first timestep) must not poison the release.
missing = fosterNetwork(fillCfs=0.0, localCfs=100.0)
missing.ts[("Foster", "Rule Curve", "Stor-ZONE")] = TS(prev=None, cur=None)
op, _ = runDay("Green Peter", datetime.date(2020, 7, 15), missing)
check("no rule curve data means no fill term, not a crash",
      op.value, TARGET_15JUL - 100.0)

# The local series is looked up once per compute, not once per timestep.
net = fosterNetwork(localCfs=200.0)
rule = Rule("Green Peter")
M.initRuleScript(rule, net)
for day in (15, 16, 17):
    M.runRuleScript(rule, net, RTS(datetime.date(2020, 7, day)))
check("three timesteps, one lookup of the local series", net.lookups, 1)

# Every other project releases its own total and never touches Foster.
op, _ = runDay("Detroit", datetime.date(2020, 7, 15), Network(useShipped=True))
check("Detroit is unaffected by the Green Peter special case",
      op.value > 0, True)

# A missing local inflow series is a hard error, not a quiet under-release.
# It is looked up once in init, so this surfaces before the first timestep.
noLocal = fosterNetwork()
noLocal.records = {}
try:
    runDay("Green Peter", datetime.date(2020, 7, 15), noLocal)
    check("a missing local inflow series raises", False, True)
except AssertionError as exc:
    check("the error names the pathname it could not read",
          "Foster_IN" in str(exc) and "FLOW-CUMLOC" in str(exc), True)


################################################################################
section("11. the optional one-sided refill toward the curve")

check("refill is off by default", M.DOWNSTREAM_REFILL_DAYS, 0)

M.DOWNSTREAM_REFILL_DAYS = 10
try:
    # Foster 1000 ac-ft below its curve, spread over 10 days at a daily step,
    # is 100 ac-ft/day, or 100/1.98347 = 50.4 cfs added to the release.
    op, _ = runDay("Green Peter", datetime.date(2020, 7, 15),
                   fosterNetwork(localCfs=0.0, rcStor=100000.0,
                                 actualStor=99000.0))
    check("below the curve ADDS to the release",
          op.value, TARGET_15JUL + (1000.0 / 10.0) / AF_PER_CFS_DAY, tol=1e-4)

    op, _ = runDay("Green Peter", datetime.date(2020, 7, 15),
                   fosterNetwork(localCfs=0.0, rcStor=100000.0,
                                 actualStor=101000.0))
    check("above the curve changes nothing, the rest of the stack handles it",
          op.value, TARGET_15JUL)
finally:
    M.DOWNSTREAM_REFILL_DAYS = 0


################################################################################
for path in (FIXTURE_MIN_FLOW, FIXTURE_WITHDRAWAL):
    if os.path.exists(path):
        os.remove(path)

print("\n%d checks passed, %d failed" % (PASS[0], len(FAIL)))
for f in FAIL:
    print("\nFAIL: %s" % f)
sys.exit(1 if FAIL else 0)
