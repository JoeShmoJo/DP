"""
Script to set the release to stay above the "No Draft" zone.
Never go below a certain level.
This can happen at some projects with deep drawdowns, where a min flow rule might want to cause the reservoir to keep drafting
This rule is meant to be at the very top of the stack.

Essentially the same thing as an inactive zone, except it can be varied here instead of locked in the operation set

Config CSV (path from alt_config key NoDraftConfigCSV):
    Project,Month,Day,Elevation

Author: Josh Roach
"""

from hec.rss.model import OpValue
from hec.rss.model import OpRule
from hec.heclib.util import HecTime

from NWDJyLib.cFile import fileOpenReadClose, stripOutCommentLines, getCSVDictReader, convertCSVDictReaderToListDict
from NWDJyLib.cTimes import getHecTimeFromRuntimestep
from NWDJyLib.Utils.SimplePy import Interpolate

################################################################################
# FUNCTION DEFINITIONS

def loadZoneConfig(configCSV):
    """
    Reads in the zone config file.
    Returns {reservoir name: Interpolate object}, e.g. "Lookout Point", NOT "LOP".
    x-values are julian dates and y-values are elevations.
    """
    lines = fileOpenReadClose(configCSV)
    lines = stripOutCommentLines(lines)
    csvDict = getCSVDictReader(lines)
    csvListDict = convertCSVDictReaderToListDict(csvDict)
    zoneConfig = {} #reservoir name: list of (julian date, elevation)
    for rowDict in csvListDict:
        resvName = rowDict["Project"]
        hTime = HecTime()
        hTime.setYearMonthDay(2001, int(rowDict["Month"]), int(rowDict["Day"]), 1440) #1440=2400 hours. 2001 is arbitrary non-leap year
        if not resvName in zoneConfig:
            zoneConfig[resvName] = []
        zoneConfig[resvName].append((float(hTime.dayOfYear()), float(rowDict["Elevation"])))
    userZoneDict = {}
    for resvName, dataList in zoneConfig.items():
        julianDays, elevs = zip(*dataList)
        julianDays = list(julianDays)
        elevs = list(elevs)
        #Add +/- 1 year so that interpolation will always work from 1-365
        julianDaysMinus1Yr = [jInt - 365 for jInt in julianDays]
        julianDaysPlus1Yr =  [jInt + 365 for jInt in julianDays]
        userZoneDict[resvName] = Interpolate(julianDaysMinus1Yr + julianDays + julianDaysPlus1Yr, elevs + elevs + elevs)
    return userZoneDict

def getZoneElev(userZoneDict, resvName, hTime):
    '''
    Returns a zone elevation for a given reservoir and date.
    The date is projected onto 2001 to match the Interpolate object.
    '''
    date = HecTime()
    date.setYearMonthDay(2001, hTime.month(), hTime.day(), 1440)
    return userZoneDict[resvName].interp(date.dayOfYear())

def initRuleScript(currentRule, network):
    altSetupSV = network.getStateVariable("Alternative_Setup")
    csvFileName = network.makeAbsolutePathFromWatershed(altSetupSV.varGet("NoDraftConfigCSV"))
    currentRule.varPut("userZoneDict", loadZoneConfig(csvFileName))
    return True

def runRuleScript(currentRule, network, currentRuntimestep):
    resvName = currentRule.getReservoirElement()._name
    userZoneDict = currentRule.varGet("userZoneDict")
    elevPrev = network.getTimeSeries("Reservoir", resvName, "Pool", "Elev").getPreviousValue(currentRuntimestep)
    inflow   = network.getTimeSeries("Reservoir", resvName, "Pool", "Flow-IN").getCurrentValue(currentRuntimestep)
    zoneElev = getZoneElev(userZoneDict, resvName, getHecTimeFromRuntimestep(currentRuntimestep))
    # Below the zone, pass inflow. Otherwise no limit (a very high release).
    ruleValue = 1000000.0
    if elevPrev < zoneElev:
        ruleValue = inflow
    opValue = OpValue()
    opValue.init(OpRule.RULETYPE_MAX, ruleValue)
    return opValue
