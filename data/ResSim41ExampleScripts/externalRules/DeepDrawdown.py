# -*- coding: utf-8 -*-
"""
Deep Drawdown. Minimum release that glides the pool down to TARGET_ELEV by the
target date, then holds it there until DURATION_DAYS after it first gets within
TARGET_BUFFER of the target, or END_MONTH/END_DAY, whichever is first.
SpringSpill.py is the same rule without the glide.

Config CSV (path from alt_config key DeepDrawdownConfigCSV):
  RESERVOIR,START_MONTH,START_DAY,TARGET_MONTH,TARGET_DAY,END_MONTH,END_DAY,DURATION_DAYS,TARGET_ELEV,ACTIVE
"""

from hec.rss.model import OpValue, OpRule
from hec.heclib.util import HecTime
from NWDJyLib.ResSim import cResSim
from NWDJyLib.cTimes import getHecTimeFromRuntimestep

from NWDJyLib.cFile import fileOpenReadClose, stripOutCommentLines, \
    getCSVDictReader, convertCSVDictReaderToListDict

################################################################################
# USER INPUT

CONFIG_KEY = "DeepDrawdownConfigCSV"
TARGET_BUFFER = 5.0  # feet above target elevation considered "success"

# Spread a storage correction over this many days rather than demanding the
# whole thing in one timestep. 1.0 matches a daily model exactly. On an hourly
# step, without it the same storage error would ask for 24 times the flow.
GLIDE_DAYS = 1.0

CFSDAY_TO_AF = (60*60*24)/43560.0 #Multiply a daily CFS by this constant to get acre-feet. It's about 2

################################################################################
# FUNCTION DEFINITIONS

def loadConfig(configCSV):
    """
    Reads the config CSV and returns {reservoir name: {column: value}}
    """
    lines = fileOpenReadClose(configCSV)
    lines = stripOutCommentLines(lines)
    csvDict = getCSVDictReader(lines)
    csvListDict = convertCSVDictReaderToListDict(csvDict)
    cfg = {}
    for rowDict in csvListDict:
        cfg[rowDict["RESERVOIR"]] = {
            "ACTIVE": rowDict["ACTIVE"].upper() == "TRUE",
            "START_MONTH": int(rowDict["START_MONTH"]),
            "START_DAY": int(rowDict["START_DAY"]),
            "TARGET_MONTH": int(rowDict["TARGET_MONTH"]),
            "TARGET_DAY": int(rowDict["TARGET_DAY"]),
            "END_MONTH": int(rowDict["END_MONTH"]),
            "END_DAY": int(rowDict["END_DAY"]),
            "DURATION_DAYS": int(rowDict["DURATION_DAYS"]),
            "TARGET_ELEV": float(rowDict["TARGET_ELEV"]),
        }
    return cfg

def initRuleScript(currentRule, network):
    resvName = currentRule.getReservoirElement().toString()
    altSetupSV = network.getStateVariable("Alternative_Setup")
    cfgPath = network.makeAbsolutePathFromWatershed(altSetupSV.varGet(CONFIG_KEY))
    Config = loadConfig(cfgPath)
    currentRule.varPut("Config", Config)
    if resvName not in Config:
        network.printMessage("%s is not configured in %s" %(resvName, cfgPath))
        return True

    storTable = cResSim.getElevationStorageTable(resvName, network)
    try:
        targetStor = storTable.interpolate(Config[resvName]["TARGET_ELEV"])
    except:
        targetStor = None
    currentRule.varPut("targetStor", targetStor)
    # Reset rolling end date each init
    currentRule.varPut("endDate", None)
    return True

def runRuleScript(currentRule, network, currentRuntimestep):
    resvName = currentRule.getReservoirElement().toString()
    Config = currentRule.varGet("Config")
    opValue = OpValue()
    if resvName not in Config or not Config[resvName]["ACTIVE"]:
        opValue.init(OpRule.RULETYPE_MIN, 0.0)
        return opValue
    targetStor = currentRule.varGet("targetStor")
    if targetStor is None:
        opValue.init(OpRule.RULETYPE_MIN, 0.0)
        return opValue

    cfg = Config[resvName]
    startMonth  = cfg["START_MONTH"]
    startDay    = cfg["START_DAY"]
    targetMonth = cfg["TARGET_MONTH"]
    targetDay   = cfg["TARGET_DAY"]
    maxEndMonth = cfg["END_MONTH"]
    maxEndDay   = cfg["END_DAY"]

    timeStepMinutes = currentRuntimestep.getTimeStepMinutes()
    cfsToAcFt = CFSDAY_TO_AF*timeStepMinutes/1440.
    stepsInGlide = GLIDE_DAYS*1440./timeStepMinutes
    if stepsInGlide < 1.0:
        stepsInGlide = 1.0
    currentDate = getHecTimeFromRuntimestep(currentRuntimestep)
    year = currentDate.year()

    # Window bounds, 24:00 stamps
    startDate = HecTime(); startDate.setYearMonthDay(year, startMonth, startDay, 1440)
    targetDate = HecTime(); targetDate.setYearMonthDay(year, targetMonth, targetDay, 1440)
    maxEndDate = HecTime(); maxEndDate.setYearMonthDay(year, maxEndMonth, maxEndDay, 1440)
    #Cover the case if target/end date are in a different calendar year
    if targetDate.lessThan(startDate):
        targetDate.setYearMonthDay(year + 1, targetMonth, targetDay, 1440)
    if maxEndDate.lessThan(startDate):
        maxEndDate.setYearMonthDay(year + 1, maxEndMonth, maxEndDay, 1440)

    # The window opens at 00:00 on the start day, the same instant as 24:00 the
    # day before. A daily step stamped 24:00 on the start day is inside it, and
    # so is 01:00 on the start day at an hourly step.
    windowOpen = startDate.clone(); windowOpen.subtractDays(1)
    firstStepEnd = windowOpen.clone(); firstStepEnd.addMinutes(timeStepMinutes)

    # Rolling end date that can define an early end to the deep drawdown (x days after achieve the target)
    # Reset each year on the first step in the window, default to maxEndDate
    endDate = currentRule.varGet("endDate")
    if endDate is None or (currentDate.greaterThan(windowOpen) and
                           currentDate.lessThanEqualTo(firstStepEnd)):
        endDate = maxEndDate.clone()

    elevPrev = network.getTimeSeries("Reservoir", resvName, "Pool", "Elev").getPreviousValue(currentRuntimestep)
    storPrev = network.getTimeSeries("Reservoir", resvName, "Pool", "Stor").getPreviousValue(currentRuntimestep)
    inflow   = network.getTimeSeries("Reservoir", resvName, "Pool", "Flow-IN").getCurrentValue(currentRuntimestep)

    # Trigger rolling end-date the first time we're below (target + buffer) within the window
    if (elevPrev is not None and elevPrev < cfg["TARGET_ELEV"] + TARGET_BUFFER and
        currentDate.greaterThan(windowOpen) and
        currentDate.lessThanEqualTo(maxEndDate) and
        endDate.equalTo(maxEndDate)):
        endDate = currentDate.clone()
        endDate.addDays(cfg["DURATION_DAYS"])
        if endDate.greaterThan(maxEndDate):
            endDate = maxEndDate.clone()

    if currentDate.lessThanEqualTo(windowOpen) or currentDate.greaterThan(endDate):
        #Outside the window of operations
        minFlow = 0.
    elif currentDate.lessThan(targetDate):
        #Trying to draft down to the target
        #Don't just dump storage all at once, try to straight-line it
        timestepsUntilTarget = currentDate.computeNumberIntervals(targetDate, timeStepMinutes)
        minFlow = inflow + (storPrev - targetStor) / timestepsUntilTarget / cfsToAcFt
    else:
        #After the target date but before end
        #Pull back to the target elevation over GLIDE_DAYS
        minFlow = inflow + (storPrev - targetStor) / (cfsToAcFt*stepsInGlide)
    opValue.init(OpRule.RULETYPE_MIN, max(0.0, minFlow))

    currentRule.varPut("endDate", endDate)
    return opValue
