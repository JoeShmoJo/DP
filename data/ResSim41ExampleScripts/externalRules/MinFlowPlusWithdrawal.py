# -*- coding: utf-8 -*-
"""
MinFlowPlusWithdrawal
Sets the minimum release to a minimum flow requirement plus a withdrawal demand,
both read from generic-year daily CSVs in the FIRO_SPACEConfig.csv layout.

Green Peter is a special case. Its target is met at Foster, with the South
Santiam arriving in between, so its release is backed out of a mass balance on
Foster instead:

    release = target + Foster rule curve fill rate - Foster local inflow

Config CSV format (one row per day of a generic year):
    Month,Day,Detroit,Hills Creek,Lookout Point,...
    1,1,1200,400,1200,...

A BLANK cell means that file asks for nothing that day, and contributes zero to
the sum. Only when BOTH files are blank does the rule stand down. Blank is not
the same as 0: a 0 binds at zero, two blanks do not bind at all.

Author: Josh Roach
"""

from hec.rss.model import OpValue
from hec.rss.model import OpRule
from hec.heclib.util import HecTime

from NWDJyLib.cFile import fileOpenReadClose, stripOutCommentLines, \
    getCSVDictReader, convertCSVDictReaderToListDict
from NWDJyLib.cTimes import getHecTimeFromRuntimestep

################################################################################
# USER INPUT

#alt_config keys holding the config paths, and the defaults used if absent
MIN_FLOW_KEY = "minFlowConfigCSV"
DEFAULT_MIN_FLOW_CSV = "scripts/externalRules/MinFlowConfig.csv"
WITHDRAWAL_KEY = "withdrawalConfigCSV"
DEFAULT_WITHDRAWAL_CSV = "scripts/externalRules/WithdrawalConfig.csv"

#Reservoirs whose target is met at a DOWNSTREAM project, keyed by the reservoir
#this rule is attached to. The fill rate is read from the downstream RULE CURVE,
#not from where its pool actually sits, so the term is feedforward and cannot
#oscillate. Local flow pathname is the one from Cumloc_Jefferson_Init.py.
TARGET_MET_AT = {"Green Peter": {"reservoir": "Foster",
                                 "localFlowElement": "Foster_IN",
                                 "localFlowParameter": "FLOW-CUMLOC"}}

#0 disables. Days over which to refill a downstream pool that has drifted BELOW
#its rule curve. One-sided, so it only ever raises the minimum and cannot fight
#the rules that push the pool back down from above.
DOWNSTREAM_REFILL_DAYS = 0

DEBUG = False

################################################################################
# CONSTANTS
CFSDAY_TO_AF = (60*60*24)/43560.0 #Multiply a daily CFS by this constant to get acre-feet. It's about 2

NON_RESERVOIR_COLUMNS = ["MONTH", "DAY", "NOTES", ""]

DAYS_IN_YEAR = 365

################################################################################
# FUNCTION DEFINITIONS


def _ok(v):
    """Return float(v) if it is usable; None if missing/NaN/a DSS sentinel."""
    try:
        f = float(v)
    except:
        return None
    if f != f: #NaN is the only value not equal to itself
        return None
    if abs(f) > 1e30: #HEC/DSS missing-value sentinels are around 1e38
        return None
    return f


def _getResvName(currentRule):
    """Reservoir name as ResSim knows it, e.g. "Lookout Point" (not "LOP")."""
    resvElement = currentRule.getReservoirElement()
    try:
        return resvElement._name
    except:
        return resvElement.toString()


def _genericDayOfYear(hTime):
    """
    Day of year (Jan 1 = 1), projected onto a non-leap year.
    Projecting onto 2001 first matters: calling dayOfYear() on a real leap-year
    date shifts everything after Feb 28 by a day. Feb 29 is treated as Feb 28.
    """
    month = hTime.month()
    day = hTime.day()
    if month == 2 and day == 29:
        day = 28
    probe = HecTime()
    probe.setYearMonthDay(2001, month, day, 1440)
    return int(probe.dayOfYear())


def _findColumnForReservoir(resvName, columnNames):
    """Match a reservoir name to a column, tolerating spaces and case."""
    for col in columnNames:
        if col == resvName:
            return col
    wanted = resvName.strip().upper()
    for col in columnNames:
        if col.strip().upper() == wanted:
            return col
    return None


def countDefinedDays(dayTable):
    """How many days of the year this reservoir has a number."""
    total = 0
    for day in range(1, DAYS_IN_YEAR+1):
        if dayTable[day] is not None:
            total = total + 1
    return total


def loadDailyConfig(configCSV, label):
    """
    Read a generic-year daily config CSV.
    Returns {columnName: 365-entry day table}, including all-blank columns.
    """
    lines = fileOpenReadClose(configCSV)
    lines = stripOutCommentLines(lines)
    csvDict = getCSVDictReader(lines)
    csvListDict = convertCSVDictReaderToListDict(csvDict)

    #.fieldnames is only populated after iterating, which the line above did
    fieldNames = []
    for f in list(csvDict.fieldnames):
        if f is not None:
            fieldNames.append(f)
    resvNames = []
    for f in fieldNames:
        if f.strip().upper() not in NON_RESERVOIR_COLUMNS:
            resvNames.append(f)
    if len(resvNames) == 0:
        raise AssertionError("No reservoir columns found in the %s file %s. "
            "Expected headers like 'Month,Day,Detroit,Hills Creek,...'. "
            "Headers actually read: %s" %(label, configCSV, str(fieldNames)))

    tables = {}
    for resvName in resvNames:
        tables[resvName] = [None]*(DAYS_IN_YEAR+1) #index 0 is unused

    for rowNum, rowDict in enumerate(csvListDict):
        try:
            month = int(rowDict["Month"])
            day = int(rowDict["Day"])
        except:
            raise AssertionError("Bad or missing Month/Day on data row %d of "
                "the %s file %s" %(rowNum+1, label, configCSV))
        hTime = HecTime()
        hTime.setYearMonthDay(2001, month, day, 1440) #2001 is a non-leap year
        dayOfYear = int(hTime.dayOfYear())
        for resvName in resvNames:
            cell = rowDict.get(resvName)
            if cell is None:
                continue
            text = str(cell).strip()
            if text == "": #blank means this file asks for nothing today
                continue
            try:
                flow = float(text)
            except:
                raise AssertionError("Could not read '%s' as a %s for %s on row "
                    "%d of %s. Use a number, or leave the cell blank to ask for "
                    "nothing that day." %(text, label, resvName, rowNum+1, configCSV))
            if tables[resvName][dayOfYear] is not None:
                raise AssertionError("Duplicate entry for %s on month %d day %d "
                    "in the %s file %s" %(resvName, month, day, label, configCSV))
            tables[resvName][dayOfYear] = flow
    return tables


def _total(minFlowTable, withdrawalTable, dayOfYear):
    """
    The two components added together for one day.
    A blank component contributes zero. Returns None only when BOTH are blank,
    which means the rule should not bind at all.
    """
    minFlow = minFlowTable[dayOfYear]
    withdrawal = withdrawalTable[dayOfYear]
    if minFlow is None and withdrawal is None:
        return None
    if minFlow is None:
        minFlow = 0.0
    if withdrawal is None:
        withdrawal = 0.0
    return minFlow + withdrawal


def getTotalMinFlow(minFlowTable, withdrawalTable, hTime):
    """Today's minimum release, or None if neither file asks for anything."""
    return _total(minFlowTable, withdrawalTable, _genericDayOfYear(hTime))


def _fmtFlow(flow):
    """Format a flow for the log, showing days with no requirement plainly."""
    if flow is None:
        return "no requirement"
    return "%.0f" %flow


def _resolveConfigPath(network, key, default):
    """Full path to a config CSV: the alt_config entry, or the default."""
    configCSV = default
    try:
        #bare except: varGet raises a Java exception if the key is absent, and
        #scripted rules may initialize before state variables do
        altSetupSV = network.getStateVariable("Alternative_Setup")
        configFromAlt = altSetupSV.varGet(key)
        if configFromAlt:
            configCSV = configFromAlt
    except:
        pass
    return network.makeAbsolutePathFromWatershed(configCSV)


def _columnTable(configPath, resvName, label):
    """This reservoir's 365-entry table from one config file, blanks if absent."""
    tables = loadDailyConfig(configPath, label)
    column = _findColumnForReservoir(resvName, tables.keys())
    if column is None:
        return [None]*(DAYS_IN_YEAR+1)
    return tables[column]


def _findLocalFlowRecord(network, spec):
    """
    The downstream project's local inflow series. Looked up once per compute:
    the lookup searches the run's records and cost seconds when made every step.
    A missing series is a hard error. Defaulting it to zero would under-release
    by exactly the local inflow and still look plausible.
    """
    try:
        return network.getRssRun().getTSRecordByPathParts(
            spec["localFlowElement"], spec["localFlowParameter"])
    except:
        raise AssertionError("MinFlowPlusWithdrawal could not read the local "
            "inflow series '%s' / '%s' needed to balance releases through %s. "
            "Check the element name, or remove the entry from TARGET_MET_AT to "
            "release the target directly." %(spec["localFlowElement"],
            spec["localFlowParameter"], spec["reservoir"]))


def releaseForDownstreamTarget(network, currentRuntimestep, spec, localTS, target):
    """
    Back the release out of a mass balance on the downstream project:
        release = target + rule curve fill rate - local inflow
    Filling raises the release, drafting lowers it.
    """
    downstreamName = spec["reservoir"]
    timeStepMinutes = currentRuntimestep.getTimeStepMinutes()
    cfsToAcFt = CFSDAY_TO_AF*timeStepMinutes/1440.

    #Stor-ZONE gives the rule curve directly as storage, same read as DraftToRC.py
    rcStorTS = network.getTimeSeries("Reservoir", downstreamName, "Rule Curve", "Stor-ZONE")
    rcStorNow = _ok(rcStorTS.getCurrentValue(currentRuntimestep))
    rcStorPrev = _ok(rcStorTS.getPreviousValue(currentRuntimestep))
    fillCfs = 0.0
    if rcStorNow is not None and rcStorPrev is not None:
        fillCfs = (rcStorNow-rcStorPrev)/cfsToAcFt

    localCfs = _ok(localTS.getCurrentValue(currentRuntimestep))
    if localCfs is None:
        localCfs = 0.0

    #Optional one-sided pull back onto the curve. Only ever adds.
    if DOWNSTREAM_REFILL_DAYS > 0 and rcStorNow is not None:
        storTS = network.getTimeSeries("Reservoir", downstreamName, "Pool", "Stor")
        actualStor = _ok(storTS.getPreviousValue(currentRuntimestep))
        if actualStor is not None and actualStor < rcStorNow:
            stepsInGlide = DOWNSTREAM_REFILL_DAYS*1440./timeStepMinutes
            if stepsInGlide < 1.0:
                stepsInGlide = 1.0
            fillCfs = fillCfs + (rcStorNow-actualStor)/(cfsToAcFt*stepsInGlide)

    if DEBUG:
        network.printMessage("MinFlowPlusWithdrawal via %s: target=%.0f "
            "fill=%.0f local=%.0f release=%.0f"
            %(downstreamName, target, fillCfs, localCfs, target+fillCfs-localCfs))
    return target + fillCfs - localCfs


def _initialize(currentRule, network):
    """Read both config CSVs and stash what the rule needs on the rule object."""
    resvName = _getResvName(currentRule)
    minFlowPath = _resolveConfigPath(network, MIN_FLOW_KEY, DEFAULT_MIN_FLOW_CSV)
    withdrawalPath = _resolveConfigPath(network, WITHDRAWAL_KEY, DEFAULT_WITHDRAWAL_CSV)

    minFlowTable = _columnTable(minFlowPath, resvName, "minimum flow")
    withdrawalTable = _columnTable(withdrawalPath, resvName, "withdrawal")
    minFlowDays = countDefinedDays(minFlowTable)
    withdrawalDays = countDefinedDays(withdrawalTable)

    currentRule.varPut("minFlowTable", minFlowTable)
    currentRule.varPut("withdrawalTable", withdrawalTable)

    #Only set when there is one. varPut of a None goes through Java, so ask with
    #varExists instead, which is how cNatLakeARDB.py asks.
    spec = TARGET_MET_AT.get(resvName)
    if spec is not None:
        currentRule.varPut("downstreamSpec", spec)
        currentRule.varPut("localFlowTS", _findLocalFlowRecord(network, spec))

    if minFlowDays == 0 and withdrawalDays == 0:
        #Not an error: one pair of files can serve a whole watershed
        network.printMessage("MinFlowPlusWithdrawal: %s has no numbers in "
            "either config file, so this rule will not control it. Looked in "
            "%s and %s" %(resvName, minFlowPath, withdrawalPath))
        return
    #One line per load, so the log always shows which numbers are in play
    via = ""
    if spec is not None:
        via = ", released through %s" %spec["reservoir"]
    network.printMessage("MinFlowPlusWithdrawal: loaded %s%s. Minimum flow on "
        "%d of %d days, withdrawal on %d of %d days. 01Jan target=%s, "
        "01Jul target=%s" %(resvName, via, minFlowDays, DAYS_IN_YEAR,
        withdrawalDays, DAYS_IN_YEAR,
        _fmtFlow(_total(minFlowTable, withdrawalTable, 1)),
        _fmtFlow(_total(minFlowTable, withdrawalTable, 182))))


def initRuleScript(currentRule, network):
    """
    Runs at the start of every compute, so an edited CSV is picked up at the
    next compute. The file is not checked again while the compute runs: a
    check on every call was a large share of compute time.
    """
    _initialize(currentRule, network)
    return True


def runRuleScript(currentRule, network, currentRuntimestep):
    """Runs every timestep of the compute."""
    opValue = OpValue()
    minFlowTable = currentRule.varGet("minFlowTable")
    withdrawalTable = currentRule.varGet("withdrawalTable")

    hTime = getHecTimeFromRuntimestep(currentRuntimestep)
    totalFlow = getTotalMinFlow(minFlowTable, withdrawalTable, hTime)
    if totalFlow is None:
        #Nothing asked for today, let the rest of the stack operate the project
        opValue.init(OpRule.RULETYPE_MIN, 0.0)
        return opValue

    #Green Peter meets its target at Foster, so back its release out of a mass
    #balance there rather than releasing the target itself
    if currentRule.varExists("downstreamSpec"):
        spec = currentRule.varGet("downstreamSpec")
        totalFlow = releaseForDownstreamTarget(network, currentRuntimestep,
            spec, currentRule.varGet("localFlowTS"), totalFlow)

    #Local inflow larger than the target already satisfies it downstream
    totalFlow = max(totalFlow, 0.0)

    if DEBUG:
        dayOfYear = _genericDayOfYear(hTime)
        network.printMessage("MinFlowPlusWithdrawal %s %s: minFlow=%s "
            "withdrawal=%s MIN=%.0f" %(_getResvName(currentRule),
            hTime.dateAndTime(), _fmtFlow(minFlowTable[dayOfYear]),
            _fmtFlow(withdrawalTable[dayOfYear]), totalFlow))

    opValue.init(OpRule.RULETYPE_MIN, totalFlow)
    return opValue
