"""
Code to generate a minimum release at Hills Creek
that attempts to keep it balanced with Lookout Point.
Intended to be a low priority rule, to be overriden by other
operations, such as "Fill LOP first" or IRRMs.
Balancing is based on trying to have LOP and HCR at the same % full,
with % full being calculated as between min conservation and max conservation

"""

from hec.rss.model import OpValue
from hec.rss.model import OpRule
from hec.model import RunTimeStep

from NWDJyLib.ResSim.cResSim import getElevationStorageTable, getRule

################################################################################
# USER INPUT

#Only run this May-October
#mainstem flow targets technically start on April 1
#but LOP is sometimes on a spring spill operation, and HCR shouldn't be balancing during this time.
#should be plenty of time after May to get re-balanced
START_MONTH = 5 #inclusive
END_MONTH = 10 #inclusive

minConElev = {"Hills Creek":1448., "Lookout Point":825.}
#This is true max con, not including any IRRM
maxConElev = {"Hills Creek":1541., "Lookout Point":926.}

#Don't go above a given flow just for the sake of balancing HCR/LOP.
#Limit necessary to avoid HCR dumping a bunch of water to get balanced
#Limit is fairly arbitrary, higher than min flow of 400
HIGHEST_MIN_FLOW = 1800. #cfs

#How much flow above inflow we would allow.
#e.g. if inflow is 1000, don't want to dump 1800 cfs.
#e.g. want it to release 1000 + x, where x is this variable
#Just let it release a bit above inflow so the pool doesn't drop too fast
#Could have done something like x ft/day instead, but this works
RELEASE_ABOVE_INFLOW = 300. #cfs

#If inflows are really low, the above variable won't do great.
#If inflows are only 200 cfs, we still want to be able to release more.
#Specifiy a lower limit to be used in these low flow scenarios
#This is fairly arbitrary, but higher than 400 cfs min flow
MIN_FLOW_LOW_LIMIT = 800. #cfs

#The exact name of the deep drawdown rule at Lookout Point
#This balancing rule needs it to know if deep drawdown has kicked in.
LOP_DRAWDOWN_RULE_NAME = "Deep Drawdown"

# Spread a storage correction over this many days rather than demanding the
# whole thing in one timestep. 1.0 matches a daily model exactly. On an hourly
# step, without it the same storage error would ask for 24 times the flow.
GLIDE_DAYS = 1.0

CFSDAY_TO_AF = (60*60*24)/43560.0 #Multiply a daily CFS by this constant to get acre-feet. It's about 2

################################################################################
# FUNCTION DEFINITIONS

def isLOPInDeepDrawdown(network, currentRuntimestep):
    """Returns True if Lookout Point is currently doing deep drawdown, False if not.
    It's lagged by one time step (like .getPreviousValue),
    so if the drawdown is just starting on the current time step, this will return False."""
    prevRTS = RunTimeStep(currentRuntimestep)
    prevRTS.setStep(currentRuntimestep.getPrevStep())
    rule = getRule("Lookout Point", LOP_DRAWDOWN_RULE_NAME, network) #should throw an error if it doesn't exist
    ruleOpVal = rule.getOpValue(prevRTS)
    if ruleOpVal is None: #Happens the 1st timestep when the rule hasn't been run at all
        return False
    return ruleOpVal.value > 0

def initRuleScript(currentRule, network):
    minConStorDict = {}
    conStorDict = {}
    for resvName in ["Hills Creek", "Lookout Point"]:
        elevStorTable = getElevationStorageTable(resvName, network) #input elevation, get storage
        minConStor = elevStorTable.interpolate(minConElev[resvName])
        minConStorDict[resvName] = minConStor
        conStorDict[resvName] = elevStorTable.interpolate(maxConElev[resvName]) - minConStor
    currentRule.varPut("minConStorDict", minConStorDict)
    currentRule.varPut("conStorDict", conStorDict)
    return True

def runRuleScript(currentRule, network, currentRuntimestep):
    """
    Calculates minimum flow to try to balance with Lookout Point.
    To make sure Hills Creek isn't just hanging out near full while LOP is drafting for flow aug
    """
    currentMonth = currentRuntimestep.getHecTime().month()
    if currentMonth < START_MONTH or currentMonth > END_MONTH:
        return None
    opValue = OpValue()
    if isLOPInDeepDrawdown(network, currentRuntimestep):
        #If Lookout Point is doing a deep drawdown, don't try to balance
        #Otherwise HCR will dump too
        #HCR should be storing as much as possible
        opValue.init(OpRule.RULETYPE_MIN, 0)
        return opValue
    resvName = currentRule.getReservoirElement()._name
    minConStorDict = currentRule.varGet("minConStorDict")
    conStorDict = currentRule.varGet("conStorDict")
    timeStepMinutes = currentRuntimestep.getTimeStepMinutes()
    cfsToAcFt = CFSDAY_TO_AF*timeStepMinutes/1440.
    stepsInGlide = GLIDE_DAYS*1440./timeStepMinutes
    if stepsInGlide < 1.0:
        stepsInGlide = 1.0
    #Get previous storage, relative to min con
    storPrevLOP = network.getTimeSeries("Reservoir", "Lookout Point", "Pool", "Stor").getPreviousValue(currentRuntimestep)
    storPrevHCR = network.getTimeSeries("Reservoir", "Hills Creek", "Pool", "Stor").getPreviousValue(currentRuntimestep)
    minConStorLOP_HCR = minConStorDict["Lookout Point"] + minConStorDict["Hills Creek"]
    conStorLOP_HCR = conStorDict["Lookout Point"] + conStorDict["Hills Creek"]
    #Target pct full is the previous timestep's value to avoid looking at this one.
    #HCR and LOP probably aren't perfectly balanced, so being behind a step isn't a big deal
    #Using the combined LOP+HCR is more stable than just looking at LOP
    pctFullTarget = (storPrevLOP + storPrevHCR - minConStorLOP_HCR)/conStorLOP_HCR
    storTargetHCR = minConStorDict["Hills Creek"] + pctFullTarget*conStorDict["Hills Creek"]
    inflow = network.getTimeSeries("Reservoir", resvName, "Pool", "Flow-IN").getCurrentValue(currentRuntimestep)
    release = inflow + (storPrevHCR-storTargetHCR)/(cfsToAcFt*stepsInGlide)
    #Apply limits
    ruleValue = max(0, min(HIGHEST_MIN_FLOW, max(MIN_FLOW_LOW_LIMIT, inflow+RELEASE_ABOVE_INFLOW), release))
    opValue.init(OpRule.RULETYPE_MIN, ruleValue)
    return opValue
