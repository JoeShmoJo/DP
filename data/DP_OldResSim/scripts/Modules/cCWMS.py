'''
cCWMS Module
Contains code to interact with the CWMS database
'''
from java.text import SimpleDateFormat
from java.sql import DriverManager
from hec.script import Constants, MessageBox
from hec.heclib.util import HecTime
from hec.heclib.dss import HecDss
from hec.hecmath import TimeSeriesMath
from hec.io import TimeSeriesContainer
import sys, logging

from oracle.jdbc import OracleTypes, OracleDriver 
import cTsUtils, cFile

################################################################################
# STATIC INPUT

################################################################################
# CLASS DEFINITIONS

# END OF CLASS DEFINITIONS
################################################################################
# FUNCTION DEFINITIONS
def connectToCWMSDatabase(dsn, usr, pwd):
	# Establishes a connection to the CWMS database
	# dsn, usr, pwd = strings
	DriverManager.registerDriver(OracleDriver())
	#if len(DriverManager.getDrivers()) <= 1: #alert!
	#	MessageBox.showError("Unable to properly load the Oracle Driver! Needs to be in classpath!", "Error")
	#	return None
	try: 
		dbc = DriverManager.getConnection("jdbc:oracle:thin:@" + dsn, usr, pwd)
	except:
		errM = "Failed to log on to CWMS server with the following information:"
		errM += "\ndsn = %s" %dsn
		errM += "\nUser = %s" %usr
		errM += "\nPassword = %s" %pwd
		errM += "\n\nThe login information may have changed, or you are not connected to the internet"
		MessageBox.showError(errM, "Error") 
		logging.error(errM)
		return None
	return dbc	

def getCWMSData(dbc, tsid, startDateStr, endDateStr):
	'''
	Extracts data from the CWMS database and shoves it into a TimeSeriesContainer
	@param  dbc 					Oracle Database connection
	@param  tsid 					String 	CWMS pathname (string), e.g. "BCL.Elev-Forebay.Inst.0.0.MIXED-REV"
	@param  startDateStr	String	start date of extract (e.g. 01Jan1900 0000)
	@param  endDateStr		String	end date of extract
	@return tsc						TimeSeriesContainer raw values (irregular timeseries)
	'''
	if "FLOW" in tsid.upper(): units = "cfs"
	elif "ELEV" in tsid.upper() or "STAGE" in tsid.upper(): units = "ft"
	elif "STOR" in tsid.upper(): units = "ac-ft" #alternately, can get kaf
	else: return None
	office = "NWDP"
	tz = "US/Pacific"
	call = "begin cwms_ts.retrieve_ts("":1, :2, :3, :4, to_date(:5, 'dd-mon-yyyy hh24mi'), to_date(:6, 'dd-mon-yyyy hh24mi'), :7); end;"
	cs = dbc.prepareCall (call)	# OracleCallableStatement
	cs.registerOutParameter (1, OracleTypes.CURSOR)
	cs.setString(2, units)
	cs.setString(3, office)
	cs.setString(4, tsid)
	cs.setString(5, startDateStr)
	cs.setString(6, endDateStr)
	cs.setString(7, tz)
	cs.execute()
	rs = cs.getCursor(1)
	dtf = SimpleDateFormat ("ddMMMyyyy HHmm")
	vals = []
	tims = []
	hTime = HecTime("01Jan1900 2400")
	while (rs.next()) :
		date_time = rs.getTimestamp(1)
		if HecTime(dtf.format(date_time)) < hTime: continue # daylight savings
		hTime = HecTime(dtf.format(date_time), HecTime.MINUTE_INCREMENT)
		if rs.getInt("QUALITY_CODE") == 5: continue # 5 indicates missing data
		tims.append(hTime.value())
		val = rs.getDouble(2)
		if round(val,0) == -901 or round(val,0) == -902: #DSS will interpret as undefined
			#Need to modify the value ever so slightly, just add a pinch
			val += .001
			#val = Constants.UNDEFINED
		vals.append(val)
	tsc = TimeSeriesContainer()
	tsc.numberValues = len(vals)
	tsc.values = vals
	tsc.times = tims
	if "AVE" in tsid.split(".")[2].upper(): # data is period average
		tsc.type = "PER-AVER"
	else: # assume inst-val
		tsc.type = "INST-VAL"
	return tsc

def processCWMSPaths(pathTXTFile, outDssFile, startDateStr, endDateStr, outTimeStep, bar = None, txtArea = None):
	'''
	Function to read in a list of CWMS paths, convert them to regular interval
	records and and store to outDssFile
		pathTXTFile = string, filename with CWMS paths (e.g. "BCL.Elev-Forebay.Inst.0.0.MIXED-REV")
		outDssFile = string, dss filename to store extracted CWMS data
		startDateStr = string, beginning day for the extract (e.g. "01Oct2012 0000")
		endDateStr = string, ending day for the extract
		outTimeStep = string, the desired output timestep ("1HOUR" or "1DAY")
		bar = JProgressBar for status %
		txtArea = JTextArea for status text (with a method defined called "printToGUI"
	'''
	msg = "----------------------------------------------------------------------"
	msg += "\nEXTRACTING CWMS DATA FROM SERVER"
	msg += "\nInput Paths: %s" %pathTXTFile
	msg += "\nOutput DSS : %s" %outDssFile
	msg += "\nStart Date : %s" %startDateStr
	msg += "\nEnd Date   : %s" %endDateStr
	msg += "\nTime Step  : %s" %outTimeStep
	txtArea.printToGUI("Extracting CWMS Data...")
	logging.info(msg)
	startDate = HecTime(startDateStr, HecTime.MINUTE_INCREMENT)
	endDate = HecTime(endDateStr, HecTime.MINUTE_INCREMENT)
	outDss = HecDss.open(outDssFile)
	# Establish a database connection
	#dbc = connectToCWMSDatabase("137.161.202.29:1521:G2CWMSP1", "cwmsview", "cwmsview") #No longer supported as of 10/29/2014
	dbc = connectToCWMSDatabase("nwp-cwmsdb2.nwp.usace.army.mil:1521:G2CWMSP2", "cwmsview", "CwmsView-26-CWMSVIEW") #IP address: 137.161.67.103
	if dbc is None:
		txtArea.printToGUI("Failure to establish connection to server...")
		return None
	msg  = "\nESTABLISHED CONNECTION TO SERVER"
	txtArea.printToGUI(msg)
	logging.info(msg)
	msg  = "Processing file: " + pathTXTFile + "\n"
	msg += "\nNumVals\tNumMissing"
	logging.info(msg)
	lines = cFile.fileOpenReadClose(pathTXTFile)
	lines = cFile.stripOutCommentLines(lines)
	failPaths = [] #List of pathnames that fail to extract at all
	incompleteDict = {} #Dictionary that will hold TS that don't span the whole time window
	for i in range(len(lines)): 
		path = lines[i].strip()		
		txtArea.printToGUI("Processing: %s" %path)
		fields = path.split(".") # CWMS paths use periods as separators
		loc = fields[0]
		param = fields[1]
		if "FLOW" in param.upper():
			unitStr = "cfs"
			typeStr = "PER-AVER"
		elif "ELEV" in param.upper():
			unitStr = "ft"
			typeStr = "INST-VAL"
		elif "STAGE" in param.upper():
			unitStr = "ft"
			typeStr = "INST-VAL"
		elif "STOR" in param.upper():
			unitStr = "ac-ft" #alternately, can get kaf
			typeStr = "INST-VAL"
		else:
			unitStr = "unknown"
			typeStr = "INST-VAL"
		#if 1==1:
		try:
			# get the raw data and write it to DSS
			tscRaw = getCWMSData(dbc, path, startDateStr, endDateStr)
			cTsUtils.zrits(outDss, tscRaw.values, tscRaw.times, loc, param, "IR-MONTH", fields[-1], unitStr, typeStr)
			# convert the raw data to the desired interval and write it to DSS
			values, times, msg = cTsUtils.convertToInterval(tscRaw, param, outTimeStep, "")
			msg += "\t   %s" %path
			logging.info(msg)
			cTsUtils.zrits(outDss, values, times, loc, param, outTimeStep, fields[-1], unitStr, typeStr)
			#Check data to see if it spans the whole length
			dataStartDate = HecTime(tscRaw.times[0], HecTime.MINUTE_INCREMENT)
			dataEndDate = HecTime(tscRaw.times[-1], HecTime.MINUTE_INCREMENT)
			#The end date of the data will be 15 minutes prior to the actual desired end date
			if (dataStartDate.value() - startDate.value()) > 1440 or (endDate.value() - dataEndDate.value()) > 1440:
				#1440 is minutes in a day, if more than a day before, then it's a problem
				#Didn't get the whole time window, save it to spit out later
				incompleteDict[path] = {}
				incompleteDict[path]["Start"] = dataStartDate.clone()
				incompleteDict[path]["End"] = dataEndDate.clone()
		#else:
		except: 
			logging.info("Unable to extract: %s" %path)
			txtArea.printToGUI("\tCouldn't extract above path")
			failPaths.append(path) 
		bar.setValue(int(float(i+1)/len(lines)*100))
	msg = "\nDONE EXTRACTING CWMS DATA FROM SERVER!"
	outDss.close()
	dbc.close()
	logging.info(msg)
	txtArea.printToGUI(msg)
	bar.setValue(100)
	msg = ""
	if len(failPaths) > 0:
		msg += "\nFailed to extract the following paths:"
		for failPath in failPaths: msg += "\n\t%s" %failPath
	if len(incompleteDict.keys()) > 0:
		msg += "\nFailed to extract complete time window for the following paths:"
		msg += "\n\tData Begin Date    Data End Date    Path"
		for path in incompleteDict.keys():
			dataStartDate = incompleteDict[path]["Start"].toString(14) #02Jun85
			dataEndDate = incompleteDict[path]["End"].toString(14)
			msg += "\n\t%s     %s   %s" %(dataStartDate, dataEndDate, path)
	logging.warning(msg)
	txtArea.printToGUI(msg)
	return None

def getOracleTimeString(hTime):
	'''
	Function to return a time string that Oracle will accept from a HecTime object
	Oracle does not think in terms of 2400 hours like HecTime
	return value is a string that should look like: "25Dec2012 0000"
	'''	
	hTimeClone = hTime.clone()
	if hTimeClone.time() == "24:00": hTimeClone.addDays(1)
	timeStr = hTimeClone.toString(5).replace(",","").replace(":","").replace("2400","0000")
	return timeStr
