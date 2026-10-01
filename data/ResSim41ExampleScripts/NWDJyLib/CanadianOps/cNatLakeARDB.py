"""
    Arrow Lakes Scripted OpRule (cNatLakeARDB module), John McCoskery
    
    OpRule to simulate natural lake storage at Upper and Lower Arrow Lakes.
    This rule works even if time blocking is occurring (verified 4/14/15 by rjc)
    This script can be copy/pasted as a scripted rule, or the "computeNatLakeArrow"
    function can be called to do Arrow's natural lake operation outside of a ResSim run
    
    Assumes Arrow's elev-stor and elev-release tables are stored in shared/fixed.dss
    
    TODO this script needs some serious cleanup and should tap into NWDJyLib functionality
"""

from array import array
from hec.heclib.util import HecTime
from hec.hecmath import DSS, TimeSeriesMath
from hec.io import PairedDataContainer, TimeSeriesContainer
from hec.model import PairedValuesExt, RunTimeStep, RunTimeWindow, TSRecord
#LocalTSRecordImpl moved from hec.model to hec.rss.model in ResSim 4.1. Import it
#both ways so this file runs under 4.1 and 3.5 alike.
#TSDataSet moved to hec.clientapp.model in the same release. It was imported here
#but never used, so it is dropped rather than followed.
try:
    from hec.rss.model import LocalTSRecordImpl      #ResSim 4.1
except ImportError:
    from hec.model import LocalTSRecordImpl          #ResSim 3.5
from hec.rss.model import OpRule, OpValue, ReservoirElement, RssSystem, ScriptOpRule
from hec.script import Constants
from java.lang import Math
import sys


# ------------------------------------------------------------------------------------------
# GLOBAL Variables: variable that do not change during simulation
# ------------------------------------------------------------------------------------------

# jwm - 11/24/14; set conversion as Cf in initRuleScript to deal w/ different compute intervals
#C = 24. * 3600. / 43560.                                                                    # conversion; cfs-day -> acre-ft/day

nakbBackwaterDssPath = "/UPPER ARROW/ARD-UL/ARDLL ELEV.-ARDUL ELEV.//Z CURVES=ARD-UL FLOW/ARD-UL ELEVATION & ARD-LL ELEVATION/"
fqrbBackwaterDssPath = "/LOWER ARROW/ARD-LL/ARDBRI Q-ARD LL ELEV.//Z CURVES=ARD-LL FLOW/ARD-LL ELEVATION & ARDBRI Q/"

nakbElevStorDssPath = "/UPPER ARROW LAKE/NAKB/ELEV-STOR////"
fqrbElevStorDssPath = "/LOWER ARROW LAKE/FQRB/ELEV-STOR////"

# initial conditions (from historic data, per John McCoskery November 2014)
nakbHfInit = 1384.0
nakbQrInit = 29000.

fqrbHfInit = 1379.0
fqrbQrInit = 34000.

# ------------------------------------------------------------------------------------------
# FUNCTION DEFINITIONS
# ------------------------------------------------------------------------------------------
# ======================================================================================
# stlu3y (t, x, z) :
# given a PairedValues object t and dependent values x and z, solve for y-value. x-value
# array is the first column of table (or t.getXArray()), yarr is top row of table (or 
# t.getColumnValues(), and zarr is the multi-dimensional array corresponding to the X-Y
# pairs.
# ======================================================================================
def stlu3y (t, x, z) :
    # set up arrays
    xarr = t.getXArray()
    yarr = t.getCurveLabelValues()
    zarr = t.getYData()
    # index x-value in xarr, set for extrapolation if out of bounds
    if x <= xarr[0] :
        xi = 1
    elif x >= xarr[-1] :
        xi = len(xarr) - 1
    else :
        xi = 0
        while x >= xarr[xi] :
            xi += 1
    # create an interpolated z-array
    xr = (x - xarr[xi-1]) / (xarr[xi] - xarr[xi-1])
    zrr = []
    for x in range(0, len(yarr)) :
        zr = (zarr[x][xi] - zarr[x][xi-1]) * xr + zarr[x][xi-1]
        zrr.append(zr)
    # index z in zrr aray, set for extrapolation is needed
    if z <= zrr[0] :
        xi = 1
    elif z >= zrr[-1] :
        xi = len(zrr) - 1
    else :
        xi = 0
        while z >= zrr[xi] :
            xi += 1
    y = (yarr[xi] - yarr[xi-1]) / (zrr[xi] - zrr[xi-1]) * (z- zrr[xi-1]) + yarr[xi-1]
    return y


def dsswrite (dss, times, values, path, units, type) :
    numv = len(times)
    if numv != len(values) :
        print ("\nERROR writing timeseries for path %s.\nArrays do not match." % path)
        sys.exit()
    tsc = TimeSeriesContainer()
    tsc.numberValues = numv
    tsc.times = times
    tsc.values = values
    tsc.interval = times[1] - times[0]     # assume regular interval...
    
    tsm = TimeSeriesMath()
    tsm.setData(tsc)
    tsm.setPathname(path)
    tsm.setUnits("units")
    tsm.setType(type)
    
    dss.write(tsm)

def writeToDss (dssFile, oprule) :
    #dssFile = already opened DssFile
    dsstimes = oprule.varGet("DSSTIMES")
    timeseries = oprule.varGet("MYTIMESERIES")
    pathnames = oprule.varGet("outputDssPaths")
    units = oprule.varGet("outputDssUnits")
    type = oprule.varGet("outputDssType")
    
    for key in timeseries.keys() :
        values = timeseries[key]
        dsspath = pathnames[key]
        dssunits = units[key]
        dsstype = type[key]
        dsswrite(dssFile, dsstimes, values, dsspath, dssunits, dsstype)
    
# ------------------------------------------------------------------------------------------
# InitRuleScript (oprule, rs)
#
# @param oprule = OpRule (current object)
# @param rs = RssSystem (network)
# @param rssRunObj = RssRun
#     if rssRunObj is specified, then that rssRunObj is used
# @param outFPart = string
#     if outFPart (string) is specified, then the dss write uses it for output
# this optional functionality is useful when computing in a non ResSim compute
# ------------------------------------------------------------------------------------------
def initRuleScript (oprule, rs, rssRunObj = None, outFPart = None) :
    # open fixed.dss; located in watershed shared directory
    fixdssN = "shared\\fixed.dss"
    fixdssN = rs.makeAbsolutePathFromWatershed(fixdssN)
    fixdss = DSS.open(fixdssN)
    
    # upper lake backwater table
    nakbBackwater = PairedValuesExt()
    nakbBackwater.setData(fixdss.read(nakbBackwaterDssPath).getData())
    oprule.varPut("nakbBackwater", nakbBackwater)
    
    # upper lake  elev-stor table
    nakbElevStor = PairedValuesExt()
    nakbElevStor.setData(fixdss.read(nakbElevStorDssPath).getData())
    oprule.varPut("nakbElevStor", nakbElevStor)
    
    # also create an upper lake stor-elev table (switch x-y columns)
    nakbStorElev = PairedValuesExt()
    nakbStorElev.setArrays (nakbElevStor.getYArray(), nakbElevStor.getXArray())
    oprule.varPut("nakbStorElev", nakbStorElev)
    
    # lower lake backwater table
    fqrbBackwater = PairedValuesExt()
    fqrbBackwater.setData(fixdss.read(fqrbBackwaterDssPath).getData())
    oprule.varPut("fqrbBackwater", fqrbBackwater)
    
    # lower lake elev-stor table
    fqrbElevStor = PairedValuesExt()
    fqrbElevStor.setData(fixdss.read(fqrbElevStorDssPath).getData())
    oprule.varPut("fqrbElevStor", fqrbElevStor)
    
    # ... and a lower lake STOR-elev table
    fqrbStorElev = PairedValuesExt()
    fqrbStorElev.setArrays (fqrbElevStor.getYArray(), fqrbElevStor.getXArray())
    oprule.varPut("fqrbStorElev", fqrbStorElev)
    
    # create timeseries objects for writing to DSS file
    if not rssRunObj: #optional argument not supplied, must be a std ResSim compute
      rssRunObj = rs.getRssRun() #only works when doing a classic ResSim compute
      rtw = rssRunObj.getCurrentComputeBlockRunTimeWindow() #need for time-blocking
    else:
      rtw = rssRunObj.getRunTimeWindow()
    
    # get the time step in minutes
    minstep = rtw.getTimeStepMinutes()
    Cf = minstep / 60. * 3600. / 43560.     # compute cfs-period -> acre-ft/period conversion
    oprule.varPut("CF", Cf)
    if minstep == 60: tsInt = "1HOUR"
    elif minstep == 1440: tsInt = "1DAY"
    else: tsInt = "1DAY" #just throw something in for the pathname
    
    nstep = rtw.getNumSteps() + 1
    oprule.varPut("NSTEP", nstep)
    
    ht = HecTime()
    ht.set(rtw.getLookbackDateString() + " 2400")
    
    dsstimes = []
    for x in range(0, nstep) :
        dsstimes.append(ht.value())
        ht.addDays(1)
    oprule.varPut("DSSTIMES", dsstimes)
    
    yoda = {    "NAKBQL" : [-901. for x in range(0, nstep)], 
                "NAKBQI" : [-901. for x in range(0, nstep)], 
                "NAKBQR" : [-901. for x in range(0, nstep)], 
                "NAKBHF" : [-901. for x in range(0, nstep)], 
                "FQRBQL" : [-901. for x in range(0, nstep)], 
                "FQRBQI" : [-901. for x in range(0, nstep)], 
                "FQRBQR" : [-901. for x in range(0, nstep)], 
                "FQRBHF" : [-901. for x in range(0, nstep)]
           }
    oprule.varPut("MYTIMESERIES", yoda)
    
    if not outFPart: #just use simulation output fPart
        outFPart = rssRunObj.getOutputFPart()
    
    outputDssPaths = {  "NAKBQL" : "/upper arrow lake/nakb/flow-loc//%s/%s/" % (tsInt, outFPart), 
                        "NAKBQI" : "/upper arrow lake/nakb/flow-in//%s/%s/" % (tsInt, outFPart), 
                        "NAKBQR" : "/upper arrow lake/nakb/flow-out//%s/%s/" % (tsInt, outFPart), 
                        "NAKBHF" : "/upper arrow lake/nakb/elev//%s/%s/" % (tsInt, outFPart), 
                        "FQRBQL" : "/lower arrow lake/fqrb/flow-loc//%s/%s/" % (tsInt, outFPart),
                        "FQRBQI" : "/lower arrow lake/fqrb/flow-in//%s/%s/" % (tsInt, outFPart), 
                        "FQRBQR" : "/lower arrow lake/fqrb/flow-out//%s/%s/" % (tsInt, outFPart),
                        "FQRBHF" : "/lower arrow lake/fqrb/elev//%s/%s/" % (tsInt, outFPart)
                     }
    oprule.varPut("outputDssPaths", outputDssPaths)
    
    outputDssUnits = {  "NAKBQL" : "cfs",
                        "NAKBQI" : "cfs",
                        "NAKBQR" : "cfs",
                        "NAKBHF" : "ft",
                        "FQRBQL" : "cfs",
                        "FQRBQI" : "cfs",
                        "FQRBQR" : "cfs",
                        "FQRBHF" : "ft"
                     }
    oprule.varPut("outputDssUnits", outputDssUnits)
    
    outputDssType = {   "NAKBQL" : "PER-AVER",
                        "NAKBQI" : "PER-AVER",
                        "NAKBQR" : "PER-AVER",
                        "NAKBHF" : "INST-VAL",
                        "FQRBQL" : "PER-AVER",
                        "FQRBQI" : "PER-AVER",
                        "FQRBQR" : "PER-AVER",
                        "FQRBHF" : "INST-VAL"
                    }
    oprule.varPut("outputDssType", outputDssType)
    
    return Constants.TRUE
    
# ------------------------------------------------------------------------------------------
# runRuleScript (oprule, rs, rts) :
#
# @param oprule = OpRule (currentVariable)
# @param rs = RssSystem (network)
# @param rts = RunTimeStep (currentRuntimestep)
# The following parameters are optional, and are only necessary when doing
#   a non-standard ResSim compute. If supplied, they will override ResSim TS
# @rssRunObj
# @outDss = DssFile, already opened DSS file to write output to
# @param arrTotalFlowInTS = TSRecord (Arrow inflow)
# @param arrTotalFlowLocTS = TSRecord (Arrow local flow)
# @param kootenaiFlowTS = TSRecord (Flow out of Brilliant)
# ------------------------------------------------------------------------------------------
def runRuleScript (oprule, rs, rts, outDss = None, arrTotalFlowInTS=None, arrTotalFlowLocTS=None, kootenaiFlowTS = None) :
    opvalue = OpValue()                                                                     # return variable
    
    Cf = oprule.varGet("CF")                                                                # conv constant    
    
    step = rts.getStep()                                                                    # current step
    if not oprule.varExists("STEP1") :
        step1 = step
        oprule.varPut("STEP1", step1)
    step1 = oprule.varGet("STEP1")
    
    if not arrTotalFlowInTS: #regular ResSim run--need to find the time series
        cpass = rs.getComputePassCounter()                                                      # get compute pass
        # if first pass, do nothing.  Kootenai flows will not be available
        if cpass == 0 :
            opvalue.init(OpRule.RULETYPE_MIN, 0.)
            return opvalue
    
        rn = oprule.getReservoirElement().getName()                                             # get current reservoir's name
    
        # get ResSim TSRecords
        arrTotalFlowInTS = rs.getTimeSeries("Reservoir", rn, "Pool", "Flow-IN")
        arrTotalFlowLocTS = rs.findJunction("Arrow Lakes_IN").getLocalFlowTimeSeries("Arrow Lakes_IN FLOW-LOC")
        kootenaiFlowTS = rs.getTimeSeries("Reach", "Brilliant_OUT to Columbia+Kootenai", "", "Flow")
    else: #assume the time series have already been passed in as input
        pass
    
    # ==================================================================================
    # if at first step, initialize timeseries arrays for lookback period
    # ==================================================================================
    rssRunObj = rs.getRssRun()
    if outDss: #non-standard ResSim compute, get the full window
        rtw = rts.getRunTimeWindow()
    else: #standard ResSim compute, need to get the current time block
        rtw = rssRunObj.getCurrentComputeBlockRunTimeWindow()
    if step == step1 :
        mytimeseries = oprule.varGet("MYTIMESERIES")
        #If the compute has time blocked, need to set initial conditions for 
        #time blocks to the end result of the previous time block
        #each time block actually extends beyond the start of the next block by the number of lookback steps
        #So we can grab the first values from the current time window during lookback
        if rtw.getTimeBlockIndex() > 0: #not the first time block, read previous results from DSS
            outputDssPaths = oprule.varGet("outputDssPaths")
            dssFileObj = DSS.open(rssRunObj.getDSSOutputFile(), rtw.getTimeWindowString())
            nakbQrVals = dssFileObj.read(outputDssPaths["NAKBQR"]).getContainer().values
            nakbHfVals = dssFileObj.read(outputDssPaths["NAKBHF"]).getContainer().values
            fqrbQrVals = dssFileObj.read(outputDssPaths["FQRBQR"]).getContainer().values
            fqrbHfVals = dssFileObj.read(outputDssPaths["FQRBHF"]).getContainer().values
            dssFileObj.close()
        else: #First time block, use the initial values
            nakbQrI = nakbQrInit
            nakbHfI = nakbHfInit
            fqrbQrI = fqrbQrInit
            fqrbHfI = fqrbHfInit
        # from step 0 to previous step (lookback timeframe)
        for x in range(0, step) :
            if rtw.getTimeBlockIndex() > 0: #set the lookback to real values if timeblocking
                nakbQrI = nakbQrVals[x]
                nakbHfI = nakbHfVals[x]
                fqrbQrI = fqrbQrVals[x]
                fqrbHfI = fqrbHfVals[x]
            mytimeseries["NAKBQR"][x] = nakbQrI
            mytimeseries["FQRBQR"][x] = fqrbQrI
            mytimeseries["NAKBHF"][x] = nakbHfI
            mytimeseries["FQRBHF"][x] = fqrbHfI
            mytimeseries["NAKBQL"][x] = arrTotalFlowLocTS.getValue(x) * 0.85
            mytimeseries["FQRBQL"][x] = arrTotalFlowLocTS.getValue(x) * 0.15
            mytimeseries["NAKBQI"][x] = arrTotalFlowInTS.getValue(x) - arrTotalFlowLocTS.getValue(x) * 0.15
            mytimeseries["FQRBQI"][x] = mytimeseries["NAKBQR"][x] + mytimeseries["FQRBQL"][x]
        oprule.varPut("MYTIMESERIES", mytimeseries)
    # ==================================================================================
    
    nakbBackwater = oprule.varGet("nakbBackwater")
    nakbElevStor = oprule.varGet("nakbElevStor")
    nakbStorElev = oprule.varGet("nakbStorElev")
    
    fqrbBackwater = oprule.varGet("fqrbBackwater")
    fqrbElevStor = oprule.varGet("fqrbElevStor")
    fqrbStorElev = oprule.varGet("fqrbStorElev")
    
    # ==================================================================================
    # retrieve model intstantaneous variable for specific time steps
    # ==================================================================================
    mytimeseries = oprule.varGet("MYTIMESERIES")
    
    nakbHf1= mytimeseries["NAKBHF"][step-1]
    nakbLs1 = nakbElevStor.interpolate(nakbHf1)
    
    fqrbHf1 = mytimeseries["FQRBHF"][step-1]
    fqrbLs1 = fqrbElevStor.interpolate(fqrbHf1)
    
    nakbQl = arrTotalFlowLocTS.getValue(step) * 0.85
    nakbQi = arrTotalFlowInTS.getValue(step) - arrTotalFlowLocTS.getValue(step) * 0.15
    
    fqrbQl = arrTotalFlowLocTS.getValue(step) * 0.15
    kootQr = kootenaiFlowTS.getValue(step)
    
    if kootQr == Constants.UNDEFINED :
        print ("\nERROR at time step %d\nColumbia+Kootenai flow not computed yet.\n")
        sys.exit()
    
    nakbQr1 = mytimeseries["NAKBQR"][step-1]
    fqrbQr1 = mytimeseries["FQRBQR"][step-1]
    
    # ==================================================================================
    # solve for NAKB QR; assume FQRB HL is previous value (this is what SSARR does...)
    # ==================================================================================
    x = 0
    while x < 100 :
        # if first iteration, assume previous flow
        if x == 0 :
            nakbQr2 = nakbQr1
        # compute resulting storage and elevation
        nakbDls = (nakbQi - nakbQr2) * Cf
        nakbLsAct = nakbLs1 + nakbDls
        nakbHfAct = nakbStorElev.interpolate(nakbLsAct)
        # compute capacity from backwater table
        nakbQt = stlu3y (nakbBackwater, fqrbHf1, nakbHfAct)
        # compute test variable
        delta = nakbQr2 - nakbQt
        # break if the flow is not changing much
        if Math.abs(delta) <= 0.01 :
            break
        # set some limits on flow changes to keep delta from growing
        if x == 0 :
            if nakbQt > nakbQr2 :
                Qrlo = nakbQr2
                Qrhi = nakbQt
            else :
                Qrlo = nakbQt
                Qrhi = nakbQr2
        else :
            if nakbQt > nakbQr2 :
                Qrlo = Math.max(nakbQr2, Qrlo)
                Qrhi = Math.min(nakbQt, Qrhi)
            else :
                Qrlo = Math.max(nakbQt, Qrlo)
                Qrhi = Math.min(nakbQr2, Qrhi)
        # adjust nakbQr2 and iterate again
        nakbQr2 = (Qrlo + Qrhi) / 2.
        x += 1
        # if x == 100 then set QR2 = QR1 and move on, there isn't a convergence...
        if x == 100 :
            print ("\nWARNING %s. NAKB solver did not converge: %12.2f" % (rts.getHecTime().toString(), delta))
    
    nakbLs2 = (nakbQi - nakbQr2) * Cf + nakbLs1
    nakbHf2 = nakbStorElev.interpolate(nakbLs2)
    
    mytimeseries["NAKBQL"][step] = nakbQl
    mytimeseries["NAKBQI"][step] = nakbQi
    mytimeseries["NAKBQR"][step] = nakbQr2
    mytimeseries["NAKBHF"][step] = nakbHf2
    
    fqrbQi = nakbQr2 + fqrbQl
    
    # ==================================================================================
    # solve for FQRB QR
    # ==================================================================================
    x = 0
    while x < 100 :
        # if at first iteration; assume previous flow
        if x == 0 :
            fqrbQr2 = fqrbQr1
        # compute resulting storage and elevation
        fqrbDls = (fqrbQi - fqrbQr2) * Cf
        fqrbLsAct = fqrbLs1 + fqrbDls
        fqrbHfAct = fqrbStorElev.interpolate(fqrbLsAct)
        # compute capacity from backwater table
        fqrbQt = stlu3y (fqrbBackwater, kootQr, fqrbHfAct)
        # compute test
        delta = fqrbQr2 - fqrbQt        
        # break if flows are close
        if Math.abs(delta) <= 0.01 :
            break
        # set some limits on flow changes to keep delta from growing
        if x == 0 :
            if fqrbQt > fqrbQr2 :
                Qrlo = fqrbQr2
                Qrhi = fqrbQt
            else :
                Qrlo = fqrbQt
                Qrhi = fqrbQr2
        else :
            if fqrbQt > fqrbQr2 :
                Qrlo = Math.max(fqrbQr2, Qrlo)
                Qrhi = Math.min(fqrbQt, Qrhi)
            else :
                Qrlo = Math.max(fqrbQt, Qrlo)
                Qrhi = Math.min(fqrbQr2, Qrhi)
        # adjust nakbQr2 and iterate again
        fqrbQr2 = (Qrlo + Qrhi) / 2.
        x += 1
    
        if x == 100 :
            print ("\nWARNING %s. FQRB solver did not converge: %12.2f" % (rts.getHecTime().toString(), delta))
            sys.exit()
    
    fqrbLs2 = (fqrbQi - fqrbQr2) * Cf + fqrbLs1
    fqrbHf2 = fqrbStorElev.interpolate(fqrbLs2)
    
    mytimeseries["FQRBQL"][step] = fqrbQl
    mytimeseries["FQRBQI"][step] = fqrbQi
    mytimeseries["FQRBQR"][step] = fqrbQr2
    mytimeseries["FQRBHF"][step] = fqrbHf2
    
    oprule.varPut("MYTIMESERIES", mytimeseries)
    
    # write data to simulation.dss if at last step
    if step == oprule.varGet("NSTEP") - 1 :
        # open simulation.dss
        if not outDss: #normal ResSim compute
            simdssF = rs.getRssRun().getDSSOutputFile()
            outDss = DSS.open(simdssF)
        writeToDss(outDss, oprule)
        outDss.close()
        print "\nARDB Natural Lake Data written to DSS file."
    
    opvalue.init(OpRule.RULETYPE_SPEC, fqrbQr2)
    return opvalue

def computeNatLakeArrow(rssRunObj, outDss, arrTotalFlowInTSC, arrTotalFlowLocTSC, kootenaiFlowTSC, outFPart):
    """
    Compute Arrow's natural lake operations for the whole compute window
    This function creates a fake rule and acts like the ResSim computation logic
    Computing once per timestep
    This is done so the scripted rule doesn't need to be modified from the ResSim model
    
    :param RssRun rssRunObj: The RssRun of a run that represents the natural lake operation
    :param DSSFile outDss: Already opened DSS file to store results to
    :param TimeSeriesContainer arrTotalFlowInTSC: Total Arrow inflow
    :param TimeSeriesContainer arrTotalFlowLocTSC: Arrow Local flow (REVB to ARDB)
    :param TimeSeriesContainer kootenaiFlowTSC: Kootenai outflow (Brilliant)
    :return outflows: a list of outflows for Arrow
    """
    network = rssRunObj.getNetwork()
    #Convert the input TimeSeriesContainer objects to TSRecord objects
    arrTotalFlowInTS = LocalTSRecordImpl(arrTotalFlowInTSC)
    arrTotalFlowLocTS = LocalTSRecordImpl(arrTotalFlowLocTSC)
    kootenaiFlowTS = LocalTSRecordImpl(kootenaiFlowTSC)
    #Create a fake rule to compute the release
    fakeRule = ScriptOpRule("dummy")
    returnVal = initRuleScript(fakeRule, network, rssRunObj, outFPart)
    if not returnVal:
        print "Failed to initialize Arrow Scripted Rule..."
        return None
    #Create a fake runtimestep to do what ResSim does
    rtw = rssRunObj.getRunTimeWindow()
    rts = RunTimeStep(rtw)
    #ResSim doesn't run the rule during lookback
    #First time the rule computes in ResSim is the first time after start time
    #e.g. if there are 100 lookback steps, ResSim will start on step 101
    lookbackSteps = rtw.getNumLookbackSteps()
    totalSteps = rtw.getNumSteps()
    for step in range(lookbackSteps+1, totalSteps+1):
        rts.setStep(step)
        opVal = runRuleScript(fakeRule, network, rts, outDss, arrTotalFlowInTS, arrTotalFlowLocTS, kootenaiFlowTS)
        if not opVal:
            print "Failed to compute natural lake operation on step: %s" %rts.getStep()
            return None
    outflows = fakeRule.varGet("MYTIMESERIES")["FQRBQR"] #list of outflows
    return outflows