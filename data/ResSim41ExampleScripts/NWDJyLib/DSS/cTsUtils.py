"""
Contains code with various utilities regarding timeseries data. 
It deals with manipulation of timeseries data. 
This module doesn't deal with reading/writing to DSS files. 
For that, see the :any:`cDSS` module, which should never be imported or used here
due to circularity.
It gets really tricky to keep timezones of TimeSeriesContainer objects straight,
so they are not defined anywhere here--any timezone issues should be taken care
of upfront using functions in the :any:`cTimes` module.
"""
from hec.script import MessageBox
from hec.script import Constants
from hec.hecmath import TimeSeriesMath
from hec.heclib.util import HecTime
from hec.lang import DSSPathString
from hec.io import TimeSeriesContainer

import bisect
import math

#Custom Imports--THIS MODULE SHOULD NEVER NEED ANY CUSTOM IMPORTS (especially cDSS)!

################################################################################
# STATIC INPUT
maxMissingDaily = 5 # Max. number of missing values to still allow interpolation
maxMissingHourly = 24 # Max. number of missing values to still allow interpolation

INTERVAL_DICT = {"15MIN" :   15,
                 "1HOUR" :   60, 
                 "4HOUR" :  240,
                 "6HOUR" :  360,
                 "12HOUR":  720,
                 "1DAY"  : 1440
                 }

################################################################################
# CLASS DEFINITIONS

# END OF CLASS DEFINITIONS
################################################################################
# MIGRATED FUNCTIONS (IF MOVED TO ANOTHER MODULE, FOR BACKWARD COMPATIBILITY)
# theOldFunctionThatWasHere = newModule.theReplacementFunction

################################################################################
# FUNCTION DEFINITIONS

def getTimeSeriesContainer(tsObj):
    """
    Get a TimeSeriesContainer object from whatever object you happen to throw in.
    Use this when you need a TimeSeriesContainer for a function but aren't totally
    sure what you have already.
    tsObj is typically a TimeSeriesContainer, TimeSeriesMath, or a TSRecord
    """
    if isinstance(tsObj, TimeSeriesContainer):
        tsc = tsObj
    elif isinstance(tsObj, TimeSeriesMath):
        tsc = tsObj.getData()
    else:
        #not sure, probably a TSRecord
        tsc = tsObj.getTimeSeriesContainer()
    return tsc

def getDSSEPartFromIntervalInMinutes(intervalMinutes):
    """
    The E-part of DSS files is in the format "1DAY", "30MIN", etc.
    But it's hard to get this information if all you have is a number that represents
    the timestep interval in minutes. 
    This function does not cover all possible time intervals, just the most
    commonly used ones in modeling
    
    :param int intervalMinutes: The time step in minutes
    :return str: A string representing the corresponding DSS E part (e.g. "1DAY")
                 Returns None if no match was found
    """
    #First, reverse the dictionary
    revDict = {}
    for k in INTERVAL_DICT.keys():
        v = INTERVAL_DICT[k]
        revDict[v] = k
    #Now do the lookup
    if intervalMinutes in revDict:
        dssEPart = revDict[intervalMinutes]
    else:
        return None
    return dssEPart

def getIntervalInMinutesFromDSSEPart(dssEPart):
    """
    The reverse of :func:`getDSSEPartFromIntervalInMinutes`
    
    :param str dssEPart: A string representing the corresponding DSS E part (e.g. "1DAY")
    :return: The time step in minutes
             Returns None if no match was found
    """
    if dssEPart.upper() in INTERVAL_DICT:
        intervalMinutes = INTERVAL_DICT[dssEPart.upper()]
    else:
        return None
    return intervalMinutes

def printTSC(tsc) :
    """Print out a TimeSeriesContainer"""
    for i in range(len(tsc.values)) :
        dateValue = HecTime()
        dateValue.set(tsc.times[i])
        print "  ", dateValue.toString(), int(tsc.values[i])
        
def prepareTSCont(vals, tims, bpart, cpart, epart, fpart, unitStr, typeStr):
    """
    Fully prepare a TimeSeriesContainer object for output, populating nearly all
    fields in the object. 
    
    :param list vals: A list of values to be stored
    :param list tims: A list of times to be stored
           Format of each time is an integer representing time in minutes 
           past 1900 (can use HecTime.value())
    :param str bpart: The b-part ("location")
    :param str cpart: The c-part ("parameter")
    :param str epart: The time interval (e.g. "1DAY")
    :param str fpart: The f-part ("version")
    :param str unitStr: e.g. ft or cfs
    :param str typeStr: e.g. INST-VAL or PER-AVER
    """
    tsc = TimeSeriesContainer()
    tsc.numberValues = len(vals)
    tsc.values = vals
    tsc.times = tims
    tsc.startTime = tims[0]
    tsc.endTime = tims[-1]
    tsc.fullName = ("//%s/%s//%s/%s/" % (bpart, cpart, epart, fpart))
    tsc.units = unitStr
    tsc.type = typeStr
    tsc.location = bpart
    tsc.parameter = cpart
    tsc.version = fpart
    #Deal with the interval (defined in minutes)
    if "IR" in epart.upper(): #irregular data
        tsc.interval = 0
    tsInterval = getIntervalInMinutesFromDSSEPart(epart)
    if tsInterval:
        tsc.interval = tsInterval
    else: # leave it blank--let DSS sort it out
        pass
    return tsc
        
def addTSC(tsc1,tsc2) :
    """
    Add values of two time series containers. 
    tsc1, tsc2 = TimeSeriesContainers
    if they are not of the same length, return none
    """
    if len(tsc1.values) != len(tsc2.values): return None
    tsc = tsc1.clone()
    for i in range(len(tsc1.values)) :
        tsc.values[i] = tsc1.values[i] + tsc2.values[i]
    return tsc
    
def subtractTSC(tsc1,tsc2) :
    """
    Subtract values of two timeseries (tsc1-tsc2). 
    tsc1, tsc2 = TimeSeriesContainers. 
    If they are not of the same length, return none
    """
    if len(tsc1.values) != len(tsc2.values): return None
    tsc = tsc1.clone()
    for i in range(len(tsc1.values)) :
        tsc.values[i] = tsc1.values[i] - tsc2.values[i] + 2
        #if tsc.values[i] == -901: tsc.values[i] = -901.01 #-901 is "missing" 
    return tsc
    
def addConstToTSC(tsc1, const):
    """
    Add a constant value to a time series container, returns TimeSeriesContainer.
    tsc1 = TimeSeriesContainer, 
    const = number
    """
    tsc = tsc1.clone()
    for i in range(len(tsc1.values)):
        tsc.values[i] = tsc1.values[i] + const
    return tsc

def multiplyTSC(tsc1, const):
    """
    Multiply a constant value to a time series container, returns TimeSeriesContainer.
    tsc1 = TimeSeriesContainer,
    const = number
    """
    tsc = tsc1.clone()
    for i in range(len(tsc1.values)):
        tsc.values[i] = tsc1.values[i] * const
    return tsc
    
def extendTSC(tsc, endDate):
    """
    Exends a time series through time, holding the last value until the specified
    ending date. If the input endDate is equal to or less than the last date in
    the timeseries, then the original timeseries will be returned. This function
    is often used in observed data processing to ensure that all time series
    exist up to a certain date.
    
    Note that when adding values to a TimeSeriesContainer, using .append(val)
    directly on .values will not work. You need to convert the .values and .times to a list,
    then append data, then put the lists back in the TimeSeriesContainer
    
    :param TimeSeriesContainer tsc: The input timeseries to be extended.
                                    Must have the .interval field defined.
    :param HecTime endDate: The time to extend the data to
    :return: The extended TimeSeriesContainer
    """
    lastVal = tsc.values[-1]
    #This If block shouldn't be necessary--if the last value is invalid, it should be fixed before this
    #if lastVal == -901 or lastVal == Constants.UNDEFINED:
        #Find the last valid value
    #    lastVal = TimeSeriesMath(tsc).lastValidValue()
    lastTime = tsc.times[-1]
    endTime = endDate.value()
    if lastTime >= endTime: return tsc
    timeInterval = tsc.interval
    if timeInterval <= 0:
        msg = "The input Timeseries has no time interval defined, can't extend it"
        raise AssertionError, msg
    #Add in the same value up until the endTime is reached
    extendTSC = tsc.clone()
    extendTimes = list(tsc.times)
    extendVals = list(tsc.values)
    while lastTime < endTime:
        nextTime = lastTime + timeInterval
        extendTimes.append(nextTime)
        extendVals.append(lastVal)
        lastTime = nextTime
    extendTSC.times = extendTimes
    extendTSC.values = extendVals
    extendTSC.numberValues = len(extendTSC.values) 
    extendTSC.endTime = extendTSC.times[-1] 
    return extendTSC
    
def averageWhileMaintainingOrigTimes(tsc, tsIntStr):
    """
    Compute an average of the input timeseries, but instead of returning
    a timeseries in "1MON" interval, return the timeseries with exactly the 
    same times as the input timeseries. The averaging period must
    be larger than the timestep of the input data. 
    
    :param TimeSeriesContainer tsc: The input time series to be averaged
    :param str tsIntStr: The time interval string to average over (e.g. "1DAY", "30MIN", etc.)
    :return: A TimeSeriesContainer with all the average values stuffed
             into the original timeslots of the input
    """
    tsmIn = TimeSeriesMath(tsc)
    #can't use .transformTSM because we need to make sure to average it
    tsmAvg = tsmIn.transformTimeSeries(tsIntStr, "0M", "AVE")
    tscAvg = tsmAvg.getData()
    #.transformTimeSeries often yields an undefined number for the final month
    #Need to set that value manually
    tsmInVals = tsmIn.getData().values
    if tsmInVals[-1] < 1000000 or tsmInVals[-1] == -901: #undefined
        tsmInTimes = tsmIn.getData().times
        #Loop backwards from the last time until the time is the 1st day of a month
        runningSum = 0.
        found = False
        idx = -1
        while not found:
            hTime = HecTime(tsmInTimes[idx], HecTime.MINUTE_INCREMENT)
            runningSum += tsmInVals[idx]
            if hTime.day() == 1:
                found = True
                avgVal = runningSum/(-idx)
                tscAvg.values[-1] = avgVal
            idx -= 1
    tscOut = tsmIn.copy().getData()
    outVals = list(tscOut.values)
    avgTimeIndex = 0
    numAvgTimes = len(tscAvg.times)
    #Loop through all times in the input timeseries
    #Use the average value of the next period (Per-aver is backwards step)
    #Until the time of the next definition is reached--then look ahead again
    for curIndex, time in enumerate(tscOut.times):
        if time > tscAvg.times[avgTimeIndex]:
            #Look at the next period now, we are past the old period
            avgTimeIndex = min(avgTimeIndex + 1, numAvgTimes-1)
        avgVal = tscAvg.values[avgTimeIndex]
        outVals[curIndex] = avgVal
    tscOut.values = outVals
    return tscOut
    
def flowIndex(tscFlow, tscIndex, startMonthExclude=0, endMonthExclude=0):
    """
    Performs flow indexing to smooth out bumpy flow patterns. This is often used
    if the inflow to a reservoir has been calculated via known release and change
    in storage. That method produces inflows that are a bit erratic. To combat this,
    the flows from an upstream gage can be used to provide a nicer pattern
    for the inflows, while maintaining the volume of flow. When this method is used,
    the resulting indexed flow may look nicer and volume is conserved, but the 
    total flow pattern will not match the observed flow pattern on a daily basis. 
    
    This indexing occurs on a monthly basis--the "reset" button is pressed each
    month, so there can be some discontinuities from month to month.
    The ratio of the average flow over each month is used to factor the flows.
    If the ratio is negative (irrigation, etc.), return the original values for the month.
    
    The flow dataset used for indexing (tscIndex) should never have any negative values.
    Otherwise, the resulting volume will not match the original volume.
    The flow and indexing timeseries must have exactly the same timewindow/timestep
    
    :param TimeSeriesContainer tscFlow: Has the flow volume to be used in the indexing
                                        e.g. calculated reservoir inflow
    :param TimeSeriesContainer tscIndex: Has the pattern to be used for shaping
                                        e.g. upstream inflow gage
    :param int startMonthExclude: (optional). If supplied, these exclusion months
            will maintain the original flow timeseries. Typically, the period where
            indexing is not applied is in the spring when runoff is high.
            The start/end month integers (e.g. 2 for February) are inclusive of the month.
            If not supplied, indexing will be done for every month
    :return: TimeSeriesContainer with the indexed flows 
             (same atributes as tscFlow except for the data values)
    """
    if tscFlow.numberValues != tscIndex.numberValues:
        errMsg = "Flow indexing requires the time series be of exactly the same length"
        errMsg += "\nNumber of values: %s, %s" %(tscFlow.numberValues, tscFlow.fullName)
        errMsg += "\nNumber of values: %s, %s" %(tscIndex.numberValues, tscIndex.fullName)
        raise AssertionError, errMsg
    # compute monthly average flows
    monthAvgFlowVals = averageWhileMaintainingOrigTimes(tscFlow, "1MON").values
    monthAvgIndexVals = averageWhileMaintainingOrigTimes(tscIndex, "1MON").values
    #set up output values
    indexedVals = list(tscFlow.values)
    hTime = HecTime()
    for i, indexFlow in enumerate(tscIndex.values) :
        hTime.set(tscIndex.times[i])
        if hTime.month() >= startMonthExclude and hTime.month() <= endMonthExclude:
            #Inside the exclusion period--keep the original values as-is
            continue
        monthAvgFlowVal = monthAvgFlowVals[i]
        monthAvgIndexVal = monthAvgIndexVals[i]
        if monthAvgIndexVal <= 0 or monthAvgFlowVal <=0: 
            #Either the flow or the indexing flow has a negative average
            #Keep the original values
            continue
        ratio = monthAvgFlowVal/monthAvgIndexVal
        indexedVals[i] = indexFlow * ratio
    tscIndexed = tscFlow.clone()
    tscIndexed.values = indexedVals
    return tscIndexed
    
def transformTSM(tsm, tsIntStr):
    """
    Transform a time series to a different interval of time.
    Uses the .type of the tsm to determine the method of tranformation 
    (e.g. interpolation for INST-VAL or period averaging for PER-AVER).
    If the time series already is the desired interval, will return the basic time series.
    
    :param TimeSeriesMath tsm: The time series to transform
    :param str tsIntStr: The time interval string (e.g. "1DAY", "30MIN", etc.)
    :return TimeSeriesMath:
    """
    try:
        existingEPart = DSSPathString(tsm.getPath()).getEPart()
    except: #java.util.NoSuchElementException, occurs if no pathname defined for tsm
        existingEPart = ""
    if existingEPart == tsIntStr: #already the right interval
        return tsm
    tsType = tsm.getType()
    if tsType == "PER-AVER":
        newTSM = tsm.transformTimeSeries(tsIntStr, "0M", "AVE")
        #newTSM = tsm.interpolateDataAtRegularInterval("1DAY", "0MINUTES")
        # If "interpolateDataAtRegularInterval" is used, the first value will be lost
        # because the data is period average--use the EOP value for interpolation
    else: #assume INST-VAL
        newTSM = tsm.transformTimeSeries(tsIntStr, "0M", "INT")
    newTSM.setEPart(tsIntStr)
    return newTSM
    
def convertToInterval(tsc, intStr, cPart=None, msg=""):
    """
    Convert a time series container object to a regular interval. 
    This function will detect the parameter (e.g. flow) from the cPart, and choose
    an interpolation routine appropriate for the parameter (per-aver or inst-val). 
    The maximum allowable number of missing values to interpolate for is a global
    constant in this module (maxMissingDaily, maxMissingHourly)
    
    :param TimeSeriesContainer tsc: Input timeseries
    :param str intStr: Output time interval e.g. "1DAY", "30MIN", etc.
    :param str cPart: If supplied, this parameter name will be used to determine
                      the interpolation type, e.g. "FLOW"
                      If not, the default interpolation type will occur based on the tsc
    :param str msg: If supplied, the output messages will be appended to this
    :return TimeSeriesContainer,msg:
    """
    tsm = TimeSeriesMath(tsc)
    timeIntervalString = intStr
    if timeIntervalString == "1DAY":
        maxMissing = maxMissingDaily
    else:
        maxMissing = maxMissingHourly
    #If supplied, detect the parameter interpolation type from the C-part
    if cPart:
        if "FLOW" in cPart.upper(): 
            # do a period average
            tsm.setType("PER-AVER")
        elif "ELEV" in cPart.upper() or "STOR" in cPart.upper() or "STAGE" in cPart.upper(): 
            # do an end of period lookup
            tsm.setType("INST-VAL")
        else:
            print "Invalid CPart in convertToInterval"
            return None
    tsm = transformTSM(tsm, timeIntervalString)
    msg += "%s\t%s" %(tsm.numberValidValues(), tsm.numberMissingValues())
    if len(tsc.times) > 1: #throws an error if only one value in the timeseries
        if tsm.numberMissingValues() > 0:
            #Make sure the last value isn't undefined, otherwise the whole window won't be interpolated
            lastVal = tsm.getContainer().values[-1]
            if lastVal == -901 or lastVal == -902 or lastVal == Constants.UNDEFINED:
                #Set the last valid value
                lastValidVal = tsm.lastValidValue()
                newtsc = tsm.getContainer()
                vals = list(newtsc.values)
                vals[-1] = lastValidVal
                newtsc.values = vals
                tsm.setData(newtsc)
            tsm = tsm.estimateForMissingValues(maxMissing) #if not missing for > x days
    return tsm.getContainer(), msg
    
def getTSSlice(startDate, endDate, ts):
    """
    Returns a slice of the input timeseries data (from startDate to endDate, inclusive).
    ts is a TimeSeriesContainer, TimeSeriesMath, or TSRecord
    Returns time series data between the start and end dates
    Returns a list object
    """
    tscObj = getTimeSeriesContainer(ts)
    daysOfSlice = startDate.computeNumberIntervals(endDate, 1440) + 1
    times = tscObj.times
    #get the inflow volume
    # Perform binary search to find the index of the date
    index = bisect.bisect_left(times, startDate.value())

    # Check if the date exists in the list
    if index < len(times) and times[index] == startDate.value():
        # If it exists, get its index
        startIdx = index
    else:
        # Handle the case when the date is not found
        msg = "date: %s not found in times" %(startDate)
        raise Exception(msg) 
    
    endIdx = startIdx + daysOfSlice
    valList = list(tscObj.values[startIdx:endIdx])
    return valList
    
def getVolume(beginDate, endDate, flowTS):
    """
    Returns the sum of flow volume (maf) from beginDate to endDate.
    Assumes the data is daily timestep. 
    flowTS can be a TimeSeriesContainer or a TSRecord or TimeSeriesMath. 
    """
    CFSDAY_TO_AF = (60*60*24)/43560.0
    
    if beginDate.greaterThan(endDate): return 0.0
    flowTSC = getTimeSeriesContainer(flowTS)
    flows = getTSSlice(beginDate, endDate, flowTSC)
    vol = sum(flows)*CFSDAY_TO_AF/1000000.
    return vol
    
def mergeAndRename(tsm1, tsm2, outPath) :
    """
    Merge two timeseries into one DSS record, and 
    return the output timeseries with a different pathname, ready to be written. 
    If the timeseries are different timesteps, the data will be output as IR-MONTH.
    Otherwise, it will be output as the input timestep.
    Values in the first timeseries will overwrite values in the 2nd timeseries,
    unless there is a missing value in the first timeseries. In that case, the
    value from the 2nd timeseries will be used.
    
    :param TimeSeriesMath tsm1: 1st priority timeseries (typ observed flows)
    :param TimeSeriesMath tsm2: 2nd priority timeseries (typ forecast flows)
    :param str outPath: Pathname to output the data as
    :return TimeSeriesMath tsm: The merged timeseries
    """
    path1 = DSSPathString(tsm1.getPath())
    path2 = DSSPathString(tsm2.getPath())
    ePart1 = path1.getEPart()
    ePart2 = path2.getEPart()
    #merge data, give priority to the first data (typically observed flows)
    #If timesteps of data are different, and irregular record will result
    tsmMerge = tsm2.mergeTimeSeries(tsm1)
    tsmMerge.setPathname(outPath)
    #Make sure the pathname shows irregular data if the inputs had different timesteps
    if ePart1 == ePart2:
        tsmMerge.setEPart(ePart1)
    else:
        tsmMerge.setEPart("IR-MONTH")
    return tsmMerge
    
def removeNegativeLocals(origTSC):
    """
    Take a times series container, set the negative entries to 0, and
    apportion that negative volume to all of the positive values (multiply the
    positive values by a correction factor, NOT add a constant)
    The resulting sum of values of the time series container will be the same as input
    """
    tsc = origTSC.clone()
    negVol = 0. # the accumulated negative flows
    posVol = 0. # the accumulated positive flows
    for i in range(len(tsc.values)):
        if tsc.values[i] < 0: 
            negVol += tsc.values[i]*-1 # deal in positive numbers
            tsc.values[i] = 0
        else:
            posVol += tsc.values[i]
    if posVol < negVol:
        # There is more negative volume than positive volume in the input time series
        # Just return the original time series
        msg = "More negative flow than positive flow, not removing negative locals for : %s" %tsc.location
        #MessageBox.showInformation(msg, "Alert")
        return origTSC
    # now that we have the negative and positive volumes, apply the correction factor
    corr = (posVol-negVol)/posVol
    for i in range(len(tsc.values)):
        tsc.values[i] = tsc.values[i]*corr
    return tsc
    
def move1Transform(tsc, yBar, xBar, slope, isLog, bcf = None):
    """
    Apply the MOVE.1 transformation to extend streamflow data.
    MOVE = Maintenance of Variance Extension 1 (Hirsch 1982).
    This method is also known as the Line of Organic Correlatio.n
    It provides a nearly unbiased variance of estimates.
    xData = flow data of the predictor station during period of concurrent data
    yData = flow data of the predicted station during period of concurrent data
    
        Yhat = Ybar + Sy/Sx(X-Xbar)
    
    :param TimeSeriesContainer tsc: input timeseries with data from the base station
    :param float yBar: average of the yData
    :param float xBar: average of the xData
    :param float slope: Sy/Sx (std dev of y-data divided by std dev of x-data)
    :param boolean isLog: if True, then the coeffiecients are based on the logarithm of the data
           Log base 10 has been used to develop coefficients, not the natural log
    :param float bcf: Bias Correction Factor. If supplied, a bias correction from transforming
           from log space to linear space will be applied. Should only be supplied
           if "isLog" is True, and not mandatory even then
    :return TimeSeriesContainer: the transformed data
    """
    tscOut = tsc.clone()
    for i in range(len(tsc.values)):
        x = tsc.values[i]
        #if isLog: x = math.log(tsc.values[i])
        if isLog: 
            if x <= 0: #Can't do a log of a negative number
                print "ERROR: cannot do a logarithm of non-positive number: %s" %x
                hTime = HecTime(tsc.times[i], HecTime.MINUTE_INCREMENT)
                print "problem occurred at: %s" %hTime.toString()
                return None
            x = math.log10(x)
        y = yBar + slope*(x - xBar)
        #if isLog: y = math.exp(y)
        if isLog: 
            y = math.pow(10, y)
            if bcf: #apply Bias Correction Factor
                y = y*bcf
        tscOut.values[i] = y
    return tscOut
    
def move1TransformEqn2(tsc, a, b, bcf = None):
    """
    Apply the MOVE.1 transformation to extend streamflow data.
    MOVE = Maintenance of Variance Extension 1 (Hirsch 1982).
    This method is also known as the Line of Organic Correlation.
    It provides a nearly unbiased variance of estimates.
    xData = flow data of the predictor station during period of concurrent data
    yData = flow data of the predicted station during period of concurrent data
    If the MOVE.1 regression was done in log space, the result in linear space
    can be shown as:
    
        Yhat = a*x^b
    
    :param TimeSeriesContainer tsc: input timeseries with data from the base station
    :param float a: = number, the parameter in the above eqn
    :param float b: = number, the parameter in the above eqn
    :param float bcf: Bias Correction Factor. If supplied, a bias correction from transforming
           from log space to linear space will be applied.
    :return TimeSeriesContainer: the transformed data
    """
    tscOut = tsc.clone()
    for i in range(len(tsc.values)):
        x = tsc.values[i]
        y = a * pow(x,b)
        if bcf: #apply Bias Correction Factor
            y = y*bcf
        tscOut.values[i] = y
    return tscOut
    