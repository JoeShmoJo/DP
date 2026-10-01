# -*- coding: utf-8 -*-
"""
Draft-to-rule-curve MAX rule.
When the pool is above the rule curve, sets the MAX release to the lower of:
- the release that lands the pool on the rule curve this timestep
- the release that reaches (rule curve - BUFFER) DAYS_LOOKAHEAD days from now

Switched on or off by draftToRCActive in alt_config: true or false for every
reservoir, or one true/false per reservoir:
    draftToRCActive: true
    draftToRCActive: {"Detroit":true, "Cougar":false}
_default.txt sets it true. Off, the rule returns None and has no effect. With
no setting, or a reservoir missing from the list, the rule stays on and the
compute log says so.
"""

from hec.rss.model import OpValue, OpRule
from hec.heclib.util import HecTime
from NWDJyLib.cTimes import getHecTimeFromRuntimestep

################################################################################
# USER INPUT

DAYS_LOOKAHEAD = 3
BUFFER = 50  # AF buffer below RC to aim for, avoids asymptoting forever

CFSDAY_TO_AF = (60*60*24)/43560.0 #Multiply a daily CFS by this constant to get acre-feet. It's about 2

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

def initRuleScript(currentRule, network):
    resvName = currentRule.getReservoirElement().toString()
    active = True
    altSetupSV = network.getStateVariable("Alternative_Setup")
    if not altSetupSV.varExists("draftToRCActive"):
        network.printMessage("Draft to RC is on at %s: no draftToRCActive in alt_config" % resvName)
    else:
        setting = altSetupSV.varGet("draftToRCActive")
        if isinstance(setting, dict):
            if resvName in setting:
                active = setting[resvName]
            else:
                network.printMessage("Draft to RC is on at %s: not listed in draftToRCActive" % resvName)
        else:
            active = setting
    currentRule.varPut("active", active)
    if not active:
        network.printMessage("Draft to RC is off at %s (draftToRCActive in alt_config)" % resvName)
    return True

def runRuleScript(currentRule, network, currentRuntimestep):
    if currentRule.varExists("active") and not currentRule.varGet("active"):
        return None
    resvName = currentRule.getReservoirElement().toString()
    inflowTS = network.getTimeSeries("Reservoir", resvName, "Pool", "Flow-IN")
    storTS   = network.getTimeSeries("Reservoir", resvName, "Pool", "Stor")
    rcStorTS = network.getTimeSeries("Reservoir", resvName, "Rule Curve", "Stor-ZONE")
    if storTS is None or rcStorTS is None or inflowTS is None:
        return None
    storPrev = _ok(storTS.getPreviousValue(currentRuntimestep))
    if storPrev is None:
        return None

    timeStepMinutes = currentRuntimestep.getTimeStepMinutes()
    steps = int((DAYS_LOOKAHEAD * 1440) // timeStepMinutes)
    if steps <= 0:
        return None
    cfsToAcFt = CFSDAY_TO_AF*timeStepMinutes/1440.

    # Inflow volume (AF) from the current time forward through the lookahead
    curHT = getHecTimeFromRuntimestep(currentRuntimestep)
    probe = HecTime()
    probe.set(curHT)
    inflowSumAF = 0.0
    for i in range(steps):
        v = _ok(inflowTS.getValue(probe))
        if v is not None:
            inflowSumAF += v * cfsToAcFt
        probe.addMinutes(timeStepMinutes)

    # Rule-curve storage at the end of the lookahead
    futureHT = HecTime()
    futureHT.set(curHT)
    futureHT.addDays(DAYS_LOOKAHEAD)
    rcLookahead = _ok(rcStorTS.getValue(futureHT) - BUFFER)
    if rcLookahead is None:
        return None

    # Max flow to hit the target on the lookahead day: the average release, in
    # cfs, that moves the lookahead's inflow volume plus the excess storage
    qLookahead = (inflowSumAF + storPrev - rcLookahead) / (float(DAYS_LOOKAHEAD) * CFSDAY_TO_AF)
    # Don't overshoot: release that lands exactly on the rule curve this timestep
    inflow = inflowTS.getCurrentValue(currentRuntimestep)
    ruleCurveStor = rcStorTS.getCurrentValue(currentRuntimestep)
    qRuleCurve = inflow + (storPrev - ruleCurveStor) / cfsToAcFt
    # Take the lower of the two
    opValue = OpValue()
    opValue.init(OpRule.RULETYPE_MAX, max(0, min(qRuleCurve, qLookahead)))
    return opValue
