'''
cTsUtils Module
Contains code with various utilities regarding timeseries data
'''
from hec.script import MessageBox
from hec.hecmath import TimeSeriesMath
from hec.hecmath import DSS, DSSFileException, HecMathException
from hec.model import PairedValuesExt   
from hec.heclib.util import HecTime
from hec.lang import DSSPathString
from hec.io import TimeSeriesContainer
from hec.script import Constants
from java.lang import UnsupportedOperationException
import math, logging

################################################################################
# STATIC INPUT
maxMissingDaily = 5 # Max. number of missing values to still allow interpolation
maxMissingHourly = 24 # Max. number of missing values to still allow interpolation
################################################################################
# CLASS DEFINITIONS

# END OF CLASS DEFINITIONS
################################################################################
# FUNCTION DEFINITIONS
def readPairedDataFromDSS(pathString, dssfile):
	# Reads a paired data record from a dss file and saves it as a PairedValuesExt object
	# pathString = string
	# dssfile = string
	try:
		pairedDataMathObj = dssfile.read(pathString)
	except (DSSFileException, HecMathException, UnsupportedOperationException): #couldn't find the DSS path
		return None
	pairedDataContainer = pairedDataMathObj.getData()
	pairedValuesExtObj = PairedValuesExt()
	pairedValuesExtObj.setData(pairedDataContainer)
	return pairedValuesExtObj

def printTSC(tsc) :
	# Prints out a time series container
	# tsc = TimeSeriesContainer
	for i in range(len(tsc.values)) :
		dateValue = HecTime()
		dateValue.set(tsc.times[i])
		print "  ", dateValue.toString(), int(tsc.values[i])
		
def writeTSC(tsc, dssFile, dssPath):
	# Writes out a time series container to an already opened dss File
	# tsc = TimeSeriesContainer
	# dssFile = already opened DssFile object
	tsc.fileName = ""
	tsc.fullName = dssPath
	tsc.startTime = tsc.times[0]
	tsc.endTime = tsc.times[-1]
	tsc.numberValues = len(tsc.times)
	dssFile.write(TimeSeriesMath(tsc))

def zrits(dssFile, vals, tims, bpart, cpart, epart, fpart, unitStr, typeStr):
	# simple procedure to write data to a DSS file
	# dssFile is the already opened Dssfile (DSS or HecDSS)
	# val and tim are lists of values and times to store
	tsc = TimeSeriesContainer() 
	tsc.numberValues = len(vals) 
	tsc.values = vals 
	tsc.times = tims
	tsc.startTime = tims[0]
	tsc.endTime = tims[-1] 
	tsc.fullName = ("//%s/%s//%s/%s/" % (bpart, cpart, epart, fpart)) 
	tsc.units = unitStr 
	tsc.type = typeStr 
	dssFile.put(tsc)
	return tsc

# **********************************************************************
# method to write data with a predefined pathname to raw DSS file.
# **********************************************************************
def write_data (dss, tsc, path, units, type) :
    tsm = TimeSeriesMath()
    tsm.setData(tsc)
    tsm.setPathname(path)
    tsm.setUnits(units)
    tsm.setType(type)
    dss.write(tsm)

def checkAllTimeSeries(dssDict, tsDataDict, beginTime, endTime, ignoreDssFile = None, tsmBankInit = None):
	'''
	Function to read in all input time series and make sure they are fully defined
	For the whole time window
	@dssDict	Dictionary of DssFiles that have already been opened with a predefined time window
	          keys are the dss file name (string), values are the DssFile objects
	@tsDataDict	A dictionary of time series mappings
              keys are data location names, values are tsMapping objects
	@beginTime  HecTime or string   The start time to check
	@endTime    HecTime or string   The end time to check
	@ignoreDssFile string     If supplied, the method won't check time series from this file
	@tsmBankInit tsmBank      If supplied, then the time series will be added to the supplied bank
	Returns a tsmBank object with the TimeSeriesMath objects that were read
	Also returns a message with all of the errors
	The message will be blank if there are no issues
	'''
	beginHecTime = HecTime(beginTime)
	endHecTime = HecTime(endTime)
	
	#if tsmBankInit is passed in, then we'll start from that
	if tsmBankInit is None:
		#create a new bank
		bank = tsmBank()
	else:
		bank = tsmBankInit
	#Loop through all tsMapping objects
	msg = ""
	mapObjsMissing = [] # list of tsMapping objects that had no data
	mapObjsTruncated = [] #list of tsMapping objects that didn't have the whole time window
	for mapObj in tsDataDict.values():
		name = mapObj.getName()
		param = mapObj.getParam()
		dssName = mapObj.getDssFilename()
		pathname = mapObj.getPathname()
		#skip if time series already stored in the bank
		if bank.containsTS(dssName, pathname): continue
		#skip if the dss file is the one to ignoreDssFile
		if str(dssName).upper() == str(ignoreDssFile).upper(): continue
		#skip time series with blank dss file names or pathnames
		if len(pathname) == pathname.count("/") or dssName == "": #blank pathname
			continue
		#make sure the dss file is in the dictionary--if not, return None
		if not dssDict.has_key(dssName):
			errMsg = "ERROR! the dss file is not defined in the dictionary!"
			raise AssertionError, errMsg 
		openDssFile = dssDict[dssName]
		#try to read the time series
		try:
			tsm = openDssFile.read(pathname)
		except (DSSFileException, HecMathException): # Couldn't find the DSS path
			mapObjsMissing.append(mapObj)
			continue
		#check the start date and end date
		tsmFirstTime = HecTime(tsm.firstValidDate(), HecTime.MINUTE_INCREMENT)
		tsmLastTime  = HecTime(tsm.lastValidDate(), HecTime.MINUTE_INCREMENT) 
		if tsmFirstTime.notEqualTo(beginHecTime):
			mapObjsTruncated.append(mapObj)
		elif tsmLastTime.notEqualTo(endHecTime):
			mapObjsTruncated.append(mapObj)
		else:
			#it's good, Add the time series to the bank
			bank.depositTS(dssName, pathname, tsm)
	# Prepare a nice, organized output message:
	if len(mapObjsMissing) > 0:
		msg += "\n\nTime Series that do not exist:"
		for mapObj in mapObjsMissing:
			msg += "\n\tName:     %s" %mapObj.getName()
			msg += "\n\tDss File: %s" %mapObj.getDssFilename()
			msg += "\n\tPathname: %s\n" %mapObj.getPathname()
	if len(mapObjsTruncated) > 0:
		msg += "\n\nTime Series not defined over the full time window:"
		for mapObj in mapObjsTruncated:
			msg += "\n\tName:     %s" %mapObj.getName()
			msg += "\n\tDss File: %s" %mapObj.getDssFilename()
			msg += "\n\tPathname: %s\n" %mapObj.getPathname()
	
	return bank, msg
		
def readTSMfromPathnameParts(dssFile, bPart, cPart, ePart):
	'''
	Function to retrieve a DSS time series from just specifying a few pathname parts
	It scans the DSS file to see if there are any matching
	It retrieves the entire time window for which it is defined
	Caution should be used with this, as if there are duplicate pathnames with different
	fParts, there's no way to tell which one this method will retrieve
	@dssFile	DSSFile	Already opened Dss File (must be opened with a time window)
	@bPart		string	The bPart to match up
	@cPart		string	The cPart to match up
	@ePart		string	The ePart to match up
	Returns a TimeSeriesMath object of the read timeseries
	Returns None if no time series could be found
	'''
	#first, check to see it actually exists+
	scanString = "B=%s C=%s E=%s" %(bPart, cPart, ePart)
	returnedPaths = dssFile.getCatalogedPathnames(scanString)
	if len(returnedPaths) == 0:
		logging.warning("\tFailed to find any pathnames with BPart of: %s and CPart of: %s" %(bPart,cPart))
		logging.warning("\tAttempting to find 1HOUR data...")
		scanString = "B=%s C=%s E=%s" %(bPart, cPart, "1HOUR")
		returnedPaths = dssFile.getCatalogedPathnames(scanString)
		if len(returnedPaths) == 0:
			logging.warning("\tFailed. Attempting to find 1DAY data...")
			scanString = "B=%s C=%s E=%s" %(bPart, cPart, "1DAY")
			returnedPaths = dssFile.getCatalogedPathnames(scanString)
			if len(returnedPaths) == 0:
				logging.warning("\tCouldn't find any matching data...")
				return None
	#Okay, we have a path, but there are likely are multiple of them because
	#DSS splits up the time window
	pathStringObj = DSSPathString(returnedPaths[0])
	pathStringObj.setDPart("") #clear out the time window
	path = pathStringObj.getPathname()
	logging.info("\tReading: %s" %path)
	try: #assumes the dssFile has been opened for a time window
		obsTSM = dssFile.read(path)
	except (HecMathException, DSSFileException), e:
		logging.warning("\tFailed to read: %s" %path)
		return None
	''' If you want the whole time window...
	tsc = dssFile.get(path, 1) #get the whole time window
	if not tsc:
		logging.warning("\tFailed to read: %s" %path)
		return None
	obsTSM = TimeSeriesMath(tsc)
	'''
	#Might not have retrieved the proper time interval--convert if necessary
	obsTSM = transformTSM(obsTSM, ePart)
	return obsTSM

def addTSC(tsc1,tsc2) :
	# Add values of two time series containers
	# tsc1, tsc2 = TimeSeriesContainers
	# if they are not of the same length, return none
	#if len(tsc1.values) != len(tsc2.values): return None
	tsc = tsc1.clone()
	for i in range(len(tsc1.values)) :
		tsc.values[i] = tsc1.values[i] + tsc2.values[i]
	return tsc
	
def subtractTSC(tsc1,tsc2) :
	# Subtracts values of two time series containers (tsc1-tsc2)
	# tsc1, tsc2 = TimeSeriesContainers
	tsc = tsc1.clone()
	for i in range(len(tsc1.values)) :
		tsc.values[i] = tsc1.values[i] - tsc2.values[i] + 2
		#if tsc.values[i] == -901: tsc.values[i] = -901.01 #-901 is "missing" 
	return tsc

'''
    maverage : monthly averaging of a timeseries
    John McCoskery
    ts = input timeseries
    returns averaged timeseries
'''
def maverage (ts) :
    h = HecTime()
    num = ts.numberValues                               # set the number of values
    aver = []                                           # average array
    
    for x in range(0, num) :
        h.set(ts.times[x])                              # set date/time of current value
        h.showTimeAsBeginningOfDay(Constants.FALSE)     # make sure 2400h is end of day...
        if x == 0 or h.day() == 1 and (h.month() != 4 or h.month() != 8) :  # if at start of tsc or day == 1 but not apr or aug
            average = ts.values[x]
            h.addDays(1)
            n = x + 1
            while h.day() > 1 and n < num :             # compute sum of ts values for month but not past number of values in input
                average += ts.values[n]
                h.addDays(1)
                n += 1
            average = average / (n - x)                 # compute average
            aver.append(average)                        # add average to aver array
        elif h.day() == 1 and (h.month() == 4 or h.month() == 8) :  # split april and august
            average = ts.values[x]
            h.addDays(1)
            n = x + 1
            while h.day() < 16 and n < num :            # compute sum through 15th of month
                average += ts.values[n]
                h.addDays(1)
                n += 1  
            average = average / (n - x)                 # compute average
            aver.append(average)                        # add average to aver array
        elif h.day() == 16 and (h.month() == 4 or h.month() == 8) : # split april and august
            average = ts.values[x]
            h.addDays(1)
            n = x + 1
            while h.day() > 15 and n < num :            # compute sum through end of month
                average += ts.values[n]
                h.addDays(1)
                n += 1
            average = average / (n - x)                 # compute average
            aver.append(average)                        # add average to average array
        else :
            aver.append(aver[x-1])                      # otherwise use previous value
    
    tsc = TimeSeriesContainer()                         # create a return object
    tsc.numberValues = num                              # set number of values
    tsc.times = ts.times                                # set times
    tsc.values = aver                                   # set values
    return tsc                                          # return tsc
    
'''
    index : shape a timeseries using an 'index' location
    John McCoskery
    ts1 = timeSeriesContainer to be 'shaped'
    ts2 = indexing timeseriesContainer
    m1  = start of exclusion period (month)
    m2  = end of exclusion period (month)
    
    returns tsc of shaped flows
'''
def index (ts1, ts2, m1, m2) :
    num = ts1.numberValues                              # set number of values
    
    aver1 = maverage(ts1)                               # compute 14 period average of ts1
    aver2 = maverage(ts2)                               # compute 14 period average of ts2
    
    h = HecTime()
    shaped = []
    for x in range(0, num) :
        h.set(ts1.times[x])
        if h.month() >= m1 and h.month() <= m2 and (m1 != -901 and m2 != -901):
            shaped.append(ts1.values[x])
        else :
            shaped.append(aver1.values[x] / aver2.values[x] * ts2.values[x])  # shape volume of ts1 to ts2
    
    tsc = TimeSeriesContainer()
    tsc.numberValues = num
    tsc.times = ts1.times
    tsc.values = shaped
    return tsc
	
def transformTSM(tsm, tsIntStr):
	'''
	Transforms a time series to a different interval of time
	If the time series already is the desired interval, will return the basic time series
	@tsm    TimeSeriesMath  The time series to transform
	@tsIntStr string          The time interval string (e.g. "1DAY", "30MIN", etc.)
	'''
	if DSSPathString(tsm.getPath()).getEPart() == tsIntStr: #already the right interval
		return tsm
	tsType = tsm.getType()
	if tsType == "PER-AVER":
		newTSM = tsm.transformTimeSeries(tsIntStr, "0M", "AVE")
	else: #assume INST-VAL
		newTSM = tsm.transformTimeSeries(tsIntStr, "0M", "INT")
	return newTSM
	
def convertToInterval(tsc, cpart, intStr, msg):
	# convert a time series container object to a regular interval 
	# intStr = string, e.g. "1DAY", "30MIN", etc.
	tsm = TimeSeriesMath(tsc)
	timeIntervalString = intStr
	if timeIntervalString == "1DAY":
		maxMissing = maxMissingDaily
	else:
		maxMissing = maxMissingHourly
	if "FLOW" in cpart.upper(): 
		# do a period average
		tsm = tsm.transformTimeSeries(timeIntervalString,"0M","AVE")
	elif "ELEV" in cpart.upper() or "STOR" in cpart.upper() or "STAGE" in cpart.upper(): 
		# do an end of period lookup
		tsm = tsm.transformTimeSeries(timeIntervalString,"0M","INT")
	else:
		print "Invalid CPart in convertToInterval"
		return None
	msg += "%s\t%s" %(tsm.numberValidValues(), tsm.numberMissingValues())
	if len(tsc.times) > 1: #throws an error if only one value in the timeseries
		tsm = tsm.estimateForMissingValues(maxMissing) #if not missing for > x days
	#tsm = tsm.interpolateDataAtRegularInterval("1DAY", "0MINUTES")
	# If "interpolateDataAtRegularInterval" is used, the first value will be lost
	# because the data is period average--use the EOP value for interpolation                                       
	val = list(tsm.getData().values)
	tim = list(tsm.getData().times)
	return val, tim, msg

# **********************************************************************
# method to transform data to simulation interval
# **********************************************************************
def transform_to_regular (tsc, simintv, parm) :
    # if raw data was extracted as daily, just snap values
    # estimate if number of sequential missing is l/t/e 5
    tsm = TimeSeriesMath()
    tsm.setData(tsc)
    logging.info("transforming data to          %30s" % simintv)    
    if simintv == "1DAY" :
    	maxMissing = maxMissingDaily
    	if parm.upper() == "FLOW" :
    		tsm.setType("PER-AVER")
    	else :
    		tsm.setType("INST-VAL")
    	tsm = tsm.transformTimeSeries(simintv, "0M", "INT")
    # otherwise transform flows to period average, elevations to 'snap'
    # estimate is number of sequential missing is l/t/e
    else :
        maxMissing = maxMissingHourly
        tsm.setType("INST-VAL")
        if parm.upper() == "FLOW" :
            tsm = tsm.transformTimeSeries(simintv, "0M", "AVE")
            tsm.setType("PER-AVER")
        else :
            tsm = tsm.transformTimeSeries(simintv, "0M", "INT")
    numm = tsm.numberMissingValues()
    if numm != 0 :
        tsm = tsm.estimateForMissingValues(maxMissing)
    numm = tsm.numberMissingValues()
    logging.info("number of missing values      %30i" % numm)
    return tsm.getContainer()

def getCurDayAsHecTime():
	# returns an HecTime object corresponding to 2400 hours on the current date
	curTime = HecTime() 
	curDate = datetime.date.today()
	curTime.setYearMonthDay(curDate.year, curDate.month, curDate.day, 1440)
	return curTime

def getWYear(hTime):
	# returns the water year that hTime (HecTime object) is in
	wYear = hTime.year()
	if hTime.month() >= 10:
		wYear += 1
	return wYear

def removeNegativeLocals(origTSC):
	# Takes a times series container, set the negative entries to 0, and
	# apportion that negative volume to all of the positive values (multiply the
	# positive values by a correction factor, NOT add a constant)
	# The resulting sum of values of the time series container will be the same as input
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
		MessageBox.showInformation(msg, "Alert")
		return origTSC
	# now that we have the negative and positive volumes, apply the correction factor
	corr = (posVol-negVol)/posVol
	for i in range(len(tsc.values)):
		tsc.values[i] = tsc.values[i]*corr
	return tsc
	
def move1Transform(tsc, yBar, xBar, slope, isLog, bcf = None):
	'''
	Function to apply the MOVE.1 transformation to extend streamflow data
	MOVE = Maintenance of Variance Extension 1 (Hirsch 1982)
	This method is also known as the Line of Organic Correlation
	It provides a nearly unbiased variance of estimates
	xData = flow data of the predictor station during period of concurrent data
	yData = flow data of the predicted station during period of concurrent data
	@tsc = input TimeSeriesContainer with data from the base station
	@Yhat = Ybar + Sy/Sx(X-Xbar)
	@slope = Sy/Sx (std dev of y-data divided by std dev of x-data)
	@yBar = average of the yData
	@xBar = average of the xData
	@if isLog is True, then the coeffiecients are based on the logarithm of the data
	@bcf = Bias Correction Factor. If supplied, a bias correction from transforming
	       from log space to linear space will be applied. Should only be supplied
	       if "isLog" is True, and not mandatory even then
	Log base 10 has been used to develop coefficients, not the natural log
	return value is a TimeSeriesContainer with the data for the output location
	'''
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
	'''
	Function to apply the MOVE.1 transformation to extend streamflow data
	MOVE = Maintenance of Variance Extension 1 (Hirsch 1982)
	This method is also known as the Line of Organic Correlation
	It provides a nearly unbiased variance of estimates
	xData = flow data of the predictor station during period of concurrent data
	yData = flow data of the predicted station during period of concurrent data
	If the MOVE.1 regression was done in log space, the result in linear space
	can be shown as:
		yhat = a*x^b
	@tsc = input TimeSeriesContainer with data from the base station
	@a = number, the parameter in the above eqn
	@b = number, the parameter in the above eqn
	@bcf = Bias Correction Factor. If supplied, a bias correction from transforming
	       from log space to linear space will be applied. 
	return value is a TimeSeriesContainer with the data for the output location
	'''
	tscOut = tsc.clone()
	for i in range(len(tsc.values)):
		x = tsc.values[i]
		y = a * pow(x,b)
		if bcf: #apply Bias Correction Factor
			y = y*bcf
		tscOut.values[i] = y
	return tscOut
