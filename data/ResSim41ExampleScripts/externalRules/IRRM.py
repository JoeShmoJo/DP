'''
Interim Risk Reduction Measure (IRRM)
for maximum pool elevation reductions.
FRM rules go above this rule, if not, probably also need to change special curves.

Reads irrmTargetElevs and irrmActive from alt_config, both keyed by reservoir name.
'''

from hec.rss.model import OpValue
from hec.rss.model import OpRule
from NWDJyLib.ResSim import cResSim

################################################################################
# USER INPUT

# Spread a storage correction over this many days rather than demanding the
# whole thing in one timestep. 1.0 matches a daily model exactly. On an hourly
# step, without it the same storage error would ask for 24 times the flow.
GLIDE_DAYS = 1.0

CFSDAY_TO_AF = (60*60*24)/43560.0 #Multiply a daily CFS by this constant to get acre-feet. It's about 2

################################################################################
# FUNCTION DEFINITIONS

def initRuleScript(currentRule, network):
    resvName = currentRule.getReservoirElement().toString()
    altSetupSV = network.getStateVariable("Alternative_Setup")
    targetElev = altSetupSV.varGet("irrmTargetElevs")[resvName]
    # Storage at the IRRM elevation
    storTable = cResSim.getElevationStorageTable(resvName, network)
    currentRule.varPut("targetStor", storTable.interpolate(targetElev))
    return True

def runRuleScript(currentRule, network, currentRuntimestep):
    resvName = currentRule.getReservoirElement().toString()
    altSetupSV = network.getStateVariable("Alternative_Setup")
    irrmActive = altSetupSV.varGet("irrmActive")[resvName]
    opValue = OpValue()
    if irrmActive == False:
        opValue.init(OpRule.RULETYPE_MIN, 0)
        return opValue

    targetStor = currentRule.varGet("targetStor")
    storPrev = network.getTimeSeries("Reservoir", resvName, "Pool", "Stor").getPreviousValue(currentRuntimestep)
    inflow = network.getTimeSeries("Reservoir", resvName, "Pool", "Flow-IN").getCurrentValue(currentRuntimestep)
    timeStepMinutes = currentRuntimestep.getTimeStepMinutes()
    cfsToAcFt = CFSDAY_TO_AF*timeStepMinutes/1440.
    stepsInGlide = GLIDE_DAYS*1440./timeStepMinutes
    if stepsInGlide < 1.0:
        stepsInGlide = 1.0
    # Release required to get back to the IRRM storage over GLIDE_DAYS.
    # If negative (storage well below IRRM elev) the min is 0.
    minFlow = inflow + (storPrev - targetStor) / (cfsToAcFt*stepsInGlide)
    opValue.init(OpRule.RULETYPE_MIN, max(minFlow, 0))
    return opValue
