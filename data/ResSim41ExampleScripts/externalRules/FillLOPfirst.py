# -*- coding: utf-8 -*-
'''
Releases additional flow above the tributary min to help LOP fill.
'''

from hec.rss.model import OpValue
from hec.rss.model import OpRule

################################################################################
# USER INPUT

HIGH_FLOW = 800.0  # max rule release cfs
LOW_FLOW = 400.0   # cfs should match min tributary flow. Min trib flow must be defined in another rule - won't be enforced if outside date range.
START_MONTH = 3
START_DAY = 1
END_MONTH = 4
END_DAY = 30
SPILLWAY_ELEV = 890.0  # feet

################################################################################
# FUNCTION DEFINITIONS

def compute_min_flow(guideCurvePrev, elevPrev, currentMonth, currentDay):
    """
    Active only between START_MONTH/START_DAY and END_MONTH/END_DAY.
    diff = guide curve (capped at the spillway) - pool elevation
      - diff >= 10     -> HIGH_FLOW
      - diff <= 0      -> 0
      - 0 < diff < 10  -> linear between LOW_FLOW and HIGH_FLOW
    """
    isActive = ((currentMonth > START_MONTH or (currentMonth == START_MONTH and currentDay >= START_DAY)) and
                (currentMonth < END_MONTH or (currentMonth == END_MONTH and currentDay <= END_DAY)))
    if not isActive:
        return 0.0
    diff = min(float(guideCurvePrev), SPILLWAY_ELEV) - float(elevPrev)
    if diff >= 10:
        return HIGH_FLOW
    if diff <= 0:
        return 0.0
    return LOW_FLOW + (HIGH_FLOW - LOW_FLOW) * diff / 10.0

def initRuleScript(currentRule, network):
    return True

def runRuleScript(currentRule, network, currentRuntimestep):
    elevPrev = network.getTimeSeries("Reservoir", "Lookout Point", "Pool", "Elev").getPreviousValue(currentRuntimestep)
    guideCurvePrev = network.getTimeSeries("Reservoir", "Lookout Point", "Rule Curve", "Elev-ZONE").getPreviousValue(currentRuntimestep)
    currentDate = currentRuntimestep.getHecTime()
    minFlow = compute_min_flow(guideCurvePrev, elevPrev, currentDate.month(), currentDate.day())
    opValue = OpValue()
    opValue.init(OpRule.RULETYPE_MIN, minFlow)
    return opValue
