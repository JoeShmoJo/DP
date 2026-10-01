"""
Code to calculate the maximum draft rate limit for projects with secondary flood storage.
Detroit, Green Peter, and Lookout Point
Refer to the 2024 Willamette Flow Frequency Report, Appendix E (ResSim) for more details
as well as Water Control Manuals and the Willamette SOP
Typically, the draft in the secondary flood storage is tried to limit to powerhouse capacity
But the details are slightly different from project to project.
This code works for any reservoir with secondary flood storage (see config file)

Config CSV (path from alt_config key secondaryDraftConfigCSV):
    Variable,Detroit,Green Peter,Lookout Point
    SecondaryFloodElev,...
    LimitDrafts,TRUE,...
    MinDraftRate,...
    PhCap,...
"""

from hec.rss.model import OpValue
from hec.rss.model import OpRule
from hec.script import Constants

from NWDJyLib.cFile import fileOpenReadClose, stripOutCommentLines, getCSVDictReader, convertCSVDictReaderToListDict
from NWDJyLib.ResSim.cResSim import getElevationStorageTable

################################################################################
# USER INPUT
# All input in the config csv file

CFSDAY_TO_AF = (60*60*24)/43560.0 #Multiply a daily CFS by this constant to get acre-feet. It's about 2

################################################################################
# FUNCTION DEFINITIONS

def loadReservoirConfig(configCSV):
    """
    Reads in the reservoir config file, then saves to a nested dictionary
    1st level key is variable name (e.g. "MaxConElev")
    2nd level key is reservoir name (e.g. "Lookout Point". NOT "LOP")
    """
    lines = fileOpenReadClose(configCSV)
    lines = stripOutCommentLines(lines)
    csvDict = getCSVDictReader(lines)
    csvListDict = convertCSVDictReaderToListDict(csvDict)
    resvNames = list(csvDict.fieldnames)
    resvNames.remove("Variable")
    resvConfig = {}
    for rowDict in csvListDict:
        varName = rowDict["Variable"]
        resvConfig[varName] = {}
        for resvName in resvNames:
            try:
                val = float(rowDict[resvName])
            except ValueError:
                val = rowDict[resvName]
            resvConfig[varName][resvName] = val
    return resvConfig

def initRuleScript(currentRule, network):
    resvName = currentRule.getReservoirElement()._name
    altSetupSV = network.getStateVariable("Alternative_Setup")
    csvFileName = network.makeAbsolutePathFromWatershed(altSetupSV.varGet("secondaryDraftConfigCSV"))
    resvConfig = loadReservoirConfig(csvFileName)
    if resvName not in resvConfig.values()[0]:
        raise AssertionError("%s is trying to use a secondary flood rule, but it isn't in the config file: %s" %(resvName, csvFileName))
    if "FALSE" in resvConfig["LimitDrafts"][resvName].upper(): #"TRUE" or "FALSE"
        raise AssertionError("%s is trying to use a secondary flood rule, but the config file says it doesn't apply: %s" %(resvName, csvFileName))
    secondaryElev = float(resvConfig["SecondaryFloodElev"][resvName])
    elevStorTable = getElevationStorageTable(resvName, network) #input elevation, get storage
    currentRule.varPut("secondaryStor", elevStorTable.interpolate(secondaryElev))
    currentRule.varPut("minDraftRate", float(resvConfig["MinDraftRate"][resvName]))
    currentRule.varPut("phCap", float(resvConfig["PhCap"][resvName])) #powerhouse capacity
    return True

def runRuleScript(currentRule, network, currentRuntimestep):
    """
    Calculates maximum flow when at or below the secondary pool elevation
    """
    opValue = OpValue()
    resvName = currentRule.getReservoirElement()._name
    secondaryStor = currentRule.varGet("secondaryStor")
    storPrev = network.getTimeSeries("Reservoir", resvName, "Pool", "Stor").getPreviousValue(currentRuntimestep)
    if storPrev > secondaryStor:
        #No max limit when above the secondary pool
        opValue.init(OpRule.RULETYPE_MAX, Constants.UNDEFINED)
        return opValue
    cfsToAcFt = CFSDAY_TO_AF*currentRuntimestep.getTimeStepMinutes()/1440.
    inflow = network.getTimeSeries("Reservoir", resvName, "Pool", "Flow-IN").getCurrentValue(currentRuntimestep)
    #set maximum release to the highest of 3 things:
    #1. release to keep pool just at secondary pool elevation
    #2. powerhouse capacity
    #3. Inflow + minimum draft rate (ac-ft/day)
    relAtSecondaryElev = inflow + (storPrev-secondaryStor)/cfsToAcFt
    relMinDraft = inflow + currentRule.varGet("minDraftRate")/CFSDAY_TO_AF
    opValue.init(OpRule.RULETYPE_MAX, max(relAtSecondaryElev, currentRule.varGet("phCap"), relMinDraft))
    return opValue
