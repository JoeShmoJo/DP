"""
Offline test harness for externalRules/DiversionFromCSV.py.

Stubs the hec.* Java classes and the NWDJyLib module that imports Java, so the
rule's CSV parsing and lookup can be exercised on a plain Python interpreter
without launching ResSim. cFile is imported for real.

Run it with either Python 2.7 or Python 3 from anywhere:
    python test_DiversionFromCSV.py

This does NOT test anything ResSim-side (rule stack behavior, OpValue handling,
whether getReservoirElement actually works at a diversion). It tests the logic
that is ours, plus a sanity check on the shipped config.
"""
import sys, os, types, datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
RULES_DIR = os.path.dirname(_HERE)
SCRIPTS_DIR = os.path.dirname(RULES_DIR)
REPO = os.path.dirname(os.path.dirname(SCRIPTS_DIR))
sys.path.insert(0, SCRIPTS_DIR)
sys.path.insert(0, RULES_DIR)

SHIPPED_CONFIG = os.path.join(RULES_DIR, "DiversionConfig_ALT.csv")
SOURCE_CSV = os.path.join(REPO, "data", "daily_diversions_returns_ALT.csv")
NAMES_CSV = os.path.join(REPO, "data", "ReSimDiversionReturn_Names.csv")
FIXTURE = os.path.join(_HERE, "_fixture_diversion_tmp.csv")


def writeFixture(twoValue=25):
    """
    A small known file, so the behaviour tests do not depend on whatever numbers
    happen to be in the shipped config.

      Diversion 1 down -- 100 May through September, 0 otherwise.
      Diversion 2      -- 25 all year.
      Return 1 down    -- -40 all year, to prove negatives survive the round trip.
      Diversion 9      -- blank for the whole of February, 7 otherwise.
                          Blank must read as 0, not as "do not bind".
    """
    out = ["# generated fixture",
           "Month,Day,Diversion 1 down,Diversion 2,Return 1 down,Diversion 9"]
    for n in range(1, 366):
        date = datetime.date(2001, 1, 1) + datetime.timedelta(days=n - 1)
        one = "100" if 5 <= date.month <= 9 else "0"
        nine = "" if date.month == 2 else "7"
        out.append("%d,%d,%s,%s,-40,%s" % (date.month, date.day, one, twoValue, nine))
    fh = open(FIXTURE, "w")
    fh.write("\n".join(out) + "\n")
    fh.close()


writeFixture()

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
    RULETYPE_SPEC = "SPEC"

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

import DiversionFromCSV as D  # noqa: E402

# ---- fake ResSim objects -----------------------------------------------------
class Element(object):
    """An element that answers to _name, the way ResSim's do."""
    def __init__(self, name):
        self._name = name

class ElementNoUnderscore(object):
    """An element with no _name, to exercise the toString() fallback."""
    def __init__(self, name):
        self._n = name
    def toString(self):
        return self._n

class Rule(object):
    def __init__(self, element):
        self.element = element
        self.vars = {}
    def getReservoirElement(self):
        return self.element
    def varPut(self, k, v):
        self.vars[k] = v
    def varGet(self, k):
        return self.vars[k]
    def varExists(self, k):
        return k in self.vars

class Network(object):
    def __init__(self, useShipped=False):
        self.useShipped = useShipped
        self.messages = []
    def getStateVariable(self, name):
        raise RuntimeError("no such state variable")   # exercises the fallback
    def makeAbsolutePathFromWatershed(self, rel):
        if self.useShipped:
            return SHIPPED_CONFIG
        return FIXTURE
    def printMessage(self, msg):
        self.messages.append(msg)

class RunTimeStep(object):
    def __init__(self, month, day, year=2001):
        self.date = datetime.date(year, month, day)
    def getHecTime(self):
        return HecTime(self.date)

# ---- tiny assertion helpers --------------------------------------------------
CHECKS = [0]
FAILURES = []

def check(label, got, want):
    CHECKS[0] += 1
    if got != want:
        FAILURES.append("%s\n    got  %r\n    want %r" % (label, got, want))

def checkRaises(label, func):
    CHECKS[0] += 1
    try:
        func()
    except Exception:
        return
    FAILURES.append("%s\n    expected an exception, none raised" % label)

def section(title):
    print("\n-- %s" % title)


def runRule(elementName, month, day, useShipped=False):
    """Initialize a rule at one element and step it once. Returns the OpValue."""
    rule = Rule(Element(elementName))
    network = Network(useShipped=useShipped)
    D.initRuleScript(rule, network)
    return D.runRuleScript(rule, network, RunTimeStep(month, day))


# =============================================================================
section("1. element name comes off the element")
check("_name is preferred",
      D._getElementName(Rule(Element("Diversion 1 down"))), "Diversion 1 down")
check("toString() is the fallback",
      D._getElementName(Rule(ElementNoUnderscore("Return 15"))), "Return 15")

# =============================================================================
section("2. generic day of year")
check("01Jan is day 1", D._genericDayOfYear(HecTime(datetime.date(2001, 1, 1))), 1)
check("31Dec is day 365", D._genericDayOfYear(HecTime(datetime.date(2001, 12, 31))), 365)
check("01Jul is day 182", D._genericDayOfYear(HecTime(datetime.date(2001, 7, 1))), 182)
check("29Feb folds onto 28Feb",
      D._genericDayOfYear(HecTime(datetime.date(2004, 2, 29))),
      D._genericDayOfYear(HecTime(datetime.date(2004, 2, 28))))
check("01Mar of a leap year is still day 60",
      D._genericDayOfYear(HecTime(datetime.date(2004, 3, 1))), 60)

# =============================================================================
section("3. column matching")
tables = D.loadDailyConfig(FIXTURE)
names = list(tables.keys())
check("exact match", D._findColumnForElement("Diversion 2", names), "Diversion 2")
check("case insensitive", D._findColumnForElement("DIVERSION 2", names), "Diversion 2")
check("surrounding space ignored", D._findColumnForElement("  Diversion 2 ", names), "Diversion 2")
check("no match returns None", D._findColumnForElement("Diversion 77", names), None)
check("Month and Day are not elements", "Month" in names or "Day" in names, False)
check("fixture has 4 element columns", len(names), 4)

# =============================================================================
section("4. values read back, signs intact")
check("diversion in July", runRule("Diversion 1 down", 7, 15).value, 100.0)
check("diversion in January", runRule("Diversion 1 down", 1, 15).value, 0.0)
check("constant all year", runRule("Diversion 2", 3, 3).value, 25.0)
check("return stays negative", runRule("Return 1 down", 7, 15).value, -40.0)
check("return negative in winter too", runRule("Return 1 down", 1, 15).value, -40.0)

# =============================================================================
section("5. a blank cell diverts nothing")
check("blank reads as 0.0", runRule("Diversion 9", 2, 10).value, 0.0)
check("non-blank in the same column still reads", runRule("Diversion 9", 3, 10).value, 7.0)
check("the table really is blank there", tables["Diversion 9"][41], None)
check("getDiversionFlow turns None into 0.0",
      D.getDiversionFlow(tables["Diversion 9"], HecTime(datetime.date(2001, 2, 10))), 0.0)

# =============================================================================
section("6. the rule type is SPEC")
check("July opValue type", runRule("Diversion 1 down", 7, 15).type, "SPEC")
check("January opValue type", runRule("Diversion 1 down", 1, 15).type, "SPEC")
check("a return is SPEC as well", runRule("Return 1 down", 7, 15).type, "SPEC")

# =============================================================================
section("7. a missing column is an error, not a zero")
checkRaises("element with no column raises",
            lambda: runRule("Diversion 12", 7, 15))
try:
    runRule("Diversion 12", 7, 15)
except Exception as exc:
    msg = str(exc)
    check("the message names the element", "Diversion 12" in msg, True)
    check("the message lists what is available", "Diversion 2" in msg, True)

# =============================================================================
section("8. every day of the year is covered")
for name in ["Diversion 1 down", "Diversion 2", "Return 1 down"]:
    check("%s has all 365 days" % name, D.countDefinedDays(tables[name]), 365)
check("Diversion 9 is blank for all 28 days of February",
      D.countDefinedDays(tables["Diversion 9"]), 365 - 28)

# =============================================================================
section("9. the shipped config")
shipped = D.loadDailyConfig(SHIPPED_CONFIG)
shippedNames = sorted(shipped.keys())

expected = open(NAMES_CSV).read().replace("﻿", "").replace("\xef\xbb\xbf", "")
expected = sorted([l.strip() for l in expected.splitlines() if l.strip()])
check("shipped config covers exactly the ResSim elements", shippedNames, expected)
check("32 elements", len(shippedNames), 32)

for name in shippedNames:
    check("%s has a value every day" % name, D.countDefinedDays(shipped[name]), 365)

# Signs: diversions take water out, returns put it back
for name in shippedNames:
    values = [shipped[name][d] for d in range(1, 366)]
    if name.startswith("Diversion"):
        check("%s is never negative" % name, min(values) >= 0.0, True)
    else:
        check("%s is never positive" % name, max(values) <= 0.0, True)

# =============================================================================
section("10. shipped values match the source data")
# Rebuild July straight from the raw file and compare, so a broken 1B/1C
# mapping or a shifted column is caught rather than assumed correct.
import csv as _csv
handle = open(SOURCE_CSV)
reader = _csv.reader(handle)
header = next(reader)
julyFromSource = {}
for row in reader:
    if not row or not row[0].strip():
        continue
    parts = row[0].split("-")
    if parts[1] != "07":
        continue
    for pathname, cell in zip(header[1:], row[1:]):
        bPart = pathname.split("/")[2].strip()
        julyFromSource[bPart] = float(cell)
    break
handle.close()

B_PART_TO_ELEMENT = {"DIVERSION 1B": "Diversion 1 down",
                     "DIVERSION 1C": "Diversion 1 up",
                     "RETURN 1B": "Return 1 down",
                     "RETURN 1C": "Return 1 up"}

for bPart, value in sorted(julyFromSource.items()):
    element = B_PART_TO_ELEMENT.get(bPart)
    if element is None:
        prefix, suffix = bPart.split(" ", 1)
        element = "%s %s" % (prefix.capitalize(), suffix)
    check("15Jul %s matches the source" % element,
          shipped[element][D._genericDayOfYear(HecTime(datetime.date(2001, 7, 15)))],
          value)

# The two that the mapping could plausibly get backwards
check("Diversion 1 down is the big one (1B)",
      shipped["Diversion 1 down"][182] > shipped["Diversion 1 up"][182], True)
check("Return 1 down is the big one (1B)",
      shipped["Return 1 down"][182] < shipped["Return 1 up"][182], True)

# =============================================================================
section("11. an edited file is picked up at the next compute, not mid-compute")
rule = Rule(Element("Diversion 2"))
network = Network()
D.initRuleScript(rule, network)
check("first read", D.runRuleScript(rule, network, RunTimeStep(3, 3)).value, 25.0)

writeFixture(twoValue=26)
check("not re-read mid-compute", D.runRuleScript(rule, network, RunTimeStep(3, 3)).value, 25.0)
D.initRuleScript(rule, network)   # the next compute
check("picks up the edit at init", D.runRuleScript(rule, network, RunTimeStep(3, 3)).value, 26.0)
writeFixture()   # put it back

# =============================================================================
section("12. bad input is rejected")
BAD = os.path.join(_HERE, "_fixture_bad_tmp.csv")

def writeBad(body):
    fh = open(BAD, "w")
    fh.write(body)
    fh.close()

writeBad("Month,Day,Diversion 2\n1,1,banana\n")
checkRaises("a non-numeric cell raises", lambda: D.loadDailyConfig(BAD))

writeBad("Month,Day,Diversion 2\n1,1,5\n1,1,6\n")
checkRaises("a duplicated day raises", lambda: D.loadDailyConfig(BAD))

writeBad("Month,Day\n1,1\n")
checkRaises("a file with no element columns raises", lambda: D.loadDailyConfig(BAD))

writeBad("Month,Day,Diversion 2\nx,1,5\n")
checkRaises("a bad Month raises", lambda: D.loadDailyConfig(BAD))
os.remove(BAD)

# =============================================================================
os.remove(FIXTURE)
print("\n" + "=" * 62)
if FAILURES:
    print("%d of %d checks FAILED" % (len(FAILURES), CHECKS[0]))
    for f in FAILURES:
        print("\n  " + f)
    sys.exit(1)
print("all %d checks passed" % CHECKS[0])
