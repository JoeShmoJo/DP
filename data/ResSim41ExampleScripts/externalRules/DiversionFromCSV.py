# -*- coding: utf-8 -*-
"""
DiversionFromCSV
Sets the flow at a diversion from a generic-year daily CSV in the
FIRO_SPACEConfig.csv layout.

One script serves every diversion. It asks ResSim which element it is attached
to, finds the column with that name, and specifies that day's value.

A RETURN is just a negative diversion, so returns are ordinary columns holding
negative numbers. Nothing in this script treats them as a separate kind of
thing.

Config CSV format (one row per day of a generic year):
    Month,Day,Diversion 1 down,Diversion 1 up,Diversion 2,...,Return 15
    1,1,0,0,0,...,-0

A BLANK cell means no diversion that day, the same as 0. Unlike the minimum
flow rule, this one always specifies a number: a diversion has to be told what
to take, and saying nothing is not an option ResSim offers.

An element with NO column at all is an error, not a zero. Every element is
expected to be in the file, so a name that does not match is a typo worth
stopping for rather than a silent shutoff of that diversion.

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

#alt_config key holding the config path, and the default used if absent. Point
#a different alternative at a different file to swap BASE for ALT.
DIVERSION_KEY = "diversionConfigCSV"
DEFAULT_DIVERSION_CSV = "scripts/externalRules/DiversionConfig_ALT.csv"

DEBUG = False

################################################################################
# CONSTANTS

NON_ELEMENT_COLUMNS = ["MONTH", "DAY", "NOTES", ""]

DAYS_IN_YEAR = 365

################################################################################
# FUNCTION DEFINITIONS


def _getElementName(currentRule):
    """
    The element this rule sits on, as ResSim names it, e.g. "Diversion 1 down".

    getReservoirElement() is named for reservoirs but returns the element of
    whatever kind the rule is attached to, diversions included. Same call the
    reservoir rules in this folder use, so the two stay in step.
    """
    element = currentRule.getReservoirElement()
    try:
        return element._name
    except:
        return element.toString()


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


def _findColumnForElement(elementName, columnNames):
    """Match an element name to a column, tolerating spaces and case."""
    for col in columnNames:
        if col == elementName:
            return col
    wanted = elementName.strip().upper()
    for col in columnNames:
        if col.strip().upper() == wanted:
            return col
    return None


def countDefinedDays(dayTable):
    """How many days of the year this element has a number."""
    total = 0
    for day in range(1, DAYS_IN_YEAR+1):
        if dayTable[day] is not None:
            total = total + 1
    return total


def loadDailyConfig(configCSV):
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
    elementNames = []
    for f in fieldNames:
        if f.strip().upper() not in NON_ELEMENT_COLUMNS:
            elementNames.append(f)
    if len(elementNames) == 0:
        raise AssertionError("No element columns found in %s. Expected headers "
            "like 'Month,Day,Diversion 1 down,Diversion 2,...'. Headers "
            "actually read: %s" %(configCSV, str(fieldNames)))

    tables = {}
    for elementName in elementNames:
        tables[elementName] = [None]*(DAYS_IN_YEAR+1) #index 0 is unused

    for rowNum, rowDict in enumerate(csvListDict):
        try:
            month = int(rowDict["Month"])
            day = int(rowDict["Day"])
        except:
            raise AssertionError("Bad or missing Month/Day on data row %d of %s"
                %(rowNum+1, configCSV))
        hTime = HecTime()
        hTime.setYearMonthDay(2001, month, day, 1440) #2001 is a non-leap year
        dayOfYear = int(hTime.dayOfYear())
        for elementName in elementNames:
            cell = rowDict.get(elementName)
            if cell is None:
                continue
            text = str(cell).strip()
            if text == "": #blank means no diversion that day
                continue
            try:
                flow = float(text)
            except:
                raise AssertionError("Could not read '%s' as a flow for %s on "
                    "row %d of %s. Use a number, or leave the cell blank for no "
                    "diversion that day." %(text, elementName, rowNum+1, configCSV))
            if tables[elementName][dayOfYear] is not None:
                raise AssertionError("Duplicate entry for %s on month %d day %d "
                    "in %s" %(elementName, month, day, configCSV))
            tables[elementName][dayOfYear] = flow
    return tables


def getDiversionFlow(dayTable, hTime):
    """Today's diversion, in cfs. A blank day diverts nothing."""
    flow = dayTable[_genericDayOfYear(hTime)]
    if flow is None:
        return 0.0
    return flow


def _resolveConfigPath(network, key, default):
    """Full path to the config CSV: the alt_config entry, or the default."""
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


def _dayOneOf(month):
    """The first of a month in the generic year, for the load message."""
    hTime = HecTime()
    hTime.setYearMonthDay(2001, month, 1, 1440)
    return hTime


def _initialize(currentRule, network):
    """Read the config CSV and stash what the rule needs on the rule object."""
    elementName = _getElementName(currentRule)
    configPath = _resolveConfigPath(network, DIVERSION_KEY, DEFAULT_DIVERSION_CSV)
    tables = loadDailyConfig(configPath)

    column = _findColumnForElement(elementName, tables.keys())
    if column is None:
        #A missing column is a typo, not an instruction to divert nothing.
        #Sorting makes the near-miss easy to spot in the message.
        available = list(tables.keys())
        available.sort()
        raise AssertionError("DiversionFromCSV found no column for '%s' in %s. "
            "Add a column with that heading, or correct the element name. "
            "Columns in the file: %s" %(elementName, configPath, ", ".join(available)))

    dayTable = tables[column]
    currentRule.varPut("dayTable", dayTable)
    currentRule.varPut("elementName", elementName)

    #One line per load, so the log always shows which numbers are in play
    network.printMessage("DiversionFromCSV: loaded %s from column '%s'. Values "
        "on %d of %d days. 01Jan=%.0f, 01Jul=%.0f"
        %(elementName, column, countDefinedDays(dayTable), DAYS_IN_YEAR,
        getDiversionFlow(dayTable, _dayOneOf(1)), getDiversionFlow(dayTable, _dayOneOf(7))))


def initRuleScript(currentRule, network):
    """
    Runs at the start of every compute, so an edited CSV is picked up at the
    next compute. The file is not checked again while the compute runs: with
    ~30 diversions, a check on every call was a large share of compute time.
    """
    _initialize(currentRule, network)
    return True


def runRuleScript(currentRule, network, currentRuntimestep):
    """Runs every timestep of the compute."""
    opValue = OpValue()
    dayTable = currentRule.varGet("dayTable")

    hTime = getHecTimeFromRuntimestep(currentRuntimestep)
    flow = getDiversionFlow(dayTable, hTime)

    if DEBUG:
        network.printMessage("DiversionFromCSV %s %s: SPEC=%.0f"
            %(currentRule.varGet("elementName"), hTime.dateAndTime(), flow))

    opValue.init(OpRule.RULETYPE_SPEC, flow)
    return opValue
