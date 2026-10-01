'''
cLocFlows Module
Contains code to deal with local flow computations
'''

from hec.heclib.util import HecTime
from hec.heclib.dss import HecDss
from hec.hecmath import DSS, TimeSeriesMath, DSSFileException
from hec.lang import DSSPathString 
from hec.client import ClientApp
import logging

import cFile, cTsUtils, cResSim

################################################################################
# STATIC INPUT

################################################################################
# CLASS DEFINITIONS

# END OF CLASS DEFINITIONS
################################################################################
# FUNCTION DEFINITIONS
def transformGageData(obsDssFile, outDssFile, csvFile, tsInt, startDateStr = "01Jan1910", \
 endDateStr = "01Jan2050", bar = None, txtArea = None):
	'''
	This function performs tributary local flow calculations
	based on observed gage data only
	It can handle area ratio and Move.1
	If both Move.1 and area ratio are defined, it will do the Move.1, then apply the area ratio
	It is not intended to be used to break apart existing local flows, but rather
	to manipulate gage data directly
	@obsDssFile      string     	filename of dss file with observed data (CWMS and USGS)
	@outDssFile      string				output DSS file to write to
	@csvFile         string				csv file with instructions
	@startDateStr    string or HecTime 			start time of transformation
	@endDateStr      string or HecTime			end time of transformation
	@tsInt           string 			timeseries interval ("1HOUR" or "1DAY")
	@bar						JProgressBar
	@txtArea				JTextArea			must have "printToGUI" method defined 
	'''
	fPart = "COMPUTED" #alert!
	#Open up the instructions text file
	msg = "----------------------------------------------------------------------"
	msg += "\nTRANSFORMING TRIBUTARY FLOWS"
	msg += "\nInput File  : %s" %csvFile
	msg += "\nObserved DSS: %s" %outDssFile
	msg += "\nOutput DSS  : %s" %outDssFile
	msg += "\nStart Date  : %s" %startDateStr
	msg += "\nEnd Date    : %s" %endDateStr
	msg += "\nTime Step   : %s" %tsInt
	txtArea.printToGUI("Transforming Tributary flows...")
	logging.info(msg)
	sTime = HecTime(startDateStr)
	eTime = HecTime(endDateStr)
	#obsDss = HecDss.open(obsDssFile)
	obsDss = DSS.open(obsDssFile, sTime.toString(), eTime.toString())
	outDss = HecDss.open(outDssFile)
	msg = "Processing file: " + csvFile + "\n"
	logging.info(msg)
	lines = cFile.fileOpenReadClose(csvFile)
	lines = cFile.stripOutCommentLines(lines)
	failPaths = []
	prevTSM = None
	for i in range(len(lines)): 
		fields = lines[i].split(",")
		outBPart = fields[0].strip()
		outCPart = fields[1].strip()
		inputStation = fields[2].strip()
		#some values may not be defined--set to None
		try: areaRatio = float(fields[3].strip())
		except ValueError: areaRatio = None
		''' old way of doing it-still accurate, but eqns come in different format now 2/9/2015
		try:
			yBarMove1 = float(fields[4].strip())
			xBarMove1 = float(fields[5].strip())
			slopeMove1 = float(fields[6].strip())
		except ValueError:
			yBarMove1 = None
			xBarMove1 = None
			slopeMove1 = None
		'''
		try:
			aMove1 = float(fields[4].strip())
			bMove1 = float(fields[5].strip())
		except ValueError:
			aMove1 = None
			bMove1 = None
		try: bcfMove1 = float(fields[6].strip()) #optional parameter
		except: bcfMove1 = None
		bar.setValue(int(float(i)/len(lines)*100))
		msg = "Processing: %s" %outBPart
		logging.info(msg)
		txtArea.printToGUI(msg)
		newTSM = None
		#Read in the input station time series
		obsTSM = cTsUtils.readTSMfromPathnameParts(obsDss, bPart=inputStation, cPart="*FLOW*", ePart=tsInt)
		if obsTSM is None: #it failed
			failPaths.append(inputStation)
			continue
		# Now manipulate the data (if both Move.1 and area ratio defined, do Move.1 first)
		if aMove1:
			#Move1 is defined
			tsc = obsTSM.getData()
			tscNew = cTsUtils.move1TransformEqn2(tsc, aMove1, bMove1, bcfMove1)
			if tscNew is None:
				errMsg = "Failed to perform MOVE.1 transformation...\nSee console log for details"
				logging.error(errMsg)
				txtArea.printToGUI(errMsg)
				return None
			newTSM = TimeSeriesMath(tscNew)
		if areaRatio:
			#areaRatio is defined
			logging.info("\tArea Ratio: %s" %areaRatio)
			if newTSM: #MOVE.1 already applied
				newTSM = newTSM.multiply(areaRatio)
			else: #regular area ratio, not on top of MOVE.1
				newTSM = obsTSM.multiply(areaRatio)
		if (not aMove1) and (not areaRatio):
			logging.warning("\tNo transformation defined!")
			newTSM = obsTSM

		if prevTSM:
			# The previous step was an intermediate calculation--incorporate it
			newTSM = newTSM.add(prevTSM)
					
		if outBPart.upper() == "ADD":
			# Don't write out the times series yet--save for later
			prevTSM = newTSM
			continue
		else: prevTSM = None
		# Set up the output timeseries pathname and write it out
		outputPath = "//%s/%s//%s/%s/" %(outBPart, outCPart, tsInt, fPart)
		newTSM.setPathname(outputPath)
		outDss.write(newTSM) 
		msg = "\tOutput path: %s" %outputPath
		logging.info(msg)

	msg = "\nDONE TRANSFORMING TRIBUTARY LOCALS!"
	obsDss.close()
	outDss.close()
	logging.info(msg)
	txtArea.printToGUI(msg)
	bar.setValue(100)
	if len(failPaths) > 0:
		msg = "\nFailed to calculate the following paths:"
		for failPath in failPaths: msg += "\n\t%s" %failPath
		logging.warning(msg)
		txtArea.printToGUI(msg)
	return None	
	
def disaggregateLocals(network, outDssFile, csvFile, tsInt, startDateStr = "01Jan1910", \
 endDateStr = "01Jan2050",bar = None, txtArea = None):
	'''
	This function performs disaggregated local flow calculations
	Based on previously calculated local flows
	It can handle area ratio and Move.1
	It is not intended to be used to break apart existing local flows, but rather
	to manipulate gage data directly
	@network         RssSystem		The currently opened ResSim network (for routing)
	@outDssFile      string				output DSS file to write to
	@csvFile         string				csv file with instructions
	@startDateStr    string or HecTime 			start time of transformation
	@endDateStr      string or HecTime			end time of transformation
	@tsInt           string 			timeseries interval ("1HOUR" or "1DAY")
	@bar						JProgressBar
	@txtArea				JTextArea			must have "printToGUI" method defined 
	'''
	fPart = "COMPUTED" #alert!
	#Open up the instructions text file
	msg = "----------------------------------------------------------------------"
	msg += "\nCALCULATING DISAGGREGATED TRIBUTARY FLOWS"
	msg += "\nInput File  : %s" %csvFile
	msg += "\nOutput DSS  : %s" %outDssFile
	msg += "\nStart Date  : %s" %startDateStr
	msg += "\nEnd Date    : %s" %endDateStr
	msg += "\nTime Step   : %s" %tsInt
	txtArea.printToGUI("Calculating Disaggregated Tributary flows...")
	logging.info(msg)
	sTime = HecTime(startDateStr)
	eTime = HecTime(endDateStr)
	outDss = HecDss.open(outDssFile)
	msg = "Processing file: " + csvFile + "\n"
	logging.info(msg)
	lines = cFile.fileOpenReadClose(csvFile)
	lines = cFile.stripOutCommentLines(lines)
	#Open up all input DSS Files first--create a dictionary of opened DSS Files
	dssDict = {}
	for i in range(len(lines)):
		fields = lines[i].split(",")
		dssFile = fields[1].strip().upper()
		if dssFile != "" and dssFile not in dssDict.keys():
			#Open the file and add it to the dictionary
			fullDssFile = ClientApp.Workspace().makeAbsolutePath("shared/%s" %dssFile)
			logging.info("Opening Dss File: %s" %fullDssFile)
			#openedDssFile = HecDss.open(fullDssFile)
			openedDssFile = DSS.open(fullDssFile, sTime.toString(), eTime.toString())
			dssDict[dssFile] = openedDssFile

	#OK, now actually process the csv file
	currentTSM = None
	for i in range(len(lines)): 
		fields = lines[i].split(",")
		command = fields[0].strip().upper()	
		dssFileName = fields[1].strip().upper()
		bPart = fields[2].strip()
		cPart = fields[3].strip()
		constant = fields[4].strip()
		us_JuncName = fields[5].strip()
		ds_JuncName = fields[6].strip() 
		try:
			yBarMove1 = float(fields[7].strip())
			xBarMove1 = float(fields[8].strip())
			slopeMove1 = float(fields[9].strip())
		except ValueError:
			yBarMove1 = None
			xBarMove1 = None
			slopeMove1 = None
		#some values may not be defined--set to None
		try: constant = float(constant)
		except ValueError: constant = None
		bar.setValue(int(float(i)/len(lines)*100))
		msg = "Processing: %s" %fields
		logging.info(msg)
		txtArea.printToGUI(msg)
		#If an input flow is defined, get it
		inputTSM = None
		if dssFileName != "":
			# It should be in the dssFile dictionary
			try: dssFile = dssDict[dssFileName]
			except KeyError:
				errMsg = "ERROR! This dss file has not been opened!"
				logging.error(errMsg)
				return None
			#Read in the input time series
			inputTSM = cTsUtils.readTSMfromPathnameParts(dssFile, bPart, cPart, ePart=tsInt)
			if inputTSM is None: #it failed
				errMsg = "ERROR: Failed on the following line:\n%s" %lines[i]
				errMsg += "Could not read any pathnames with:\n\tBPart=%s\n\tCPart=%s" %(bPart, cPart)
				errMsg += "\nFrom DSS File: %s" %dssFile.getDataManager().DSSFileName()
				logging.error(errMsg)
				txtArea.printToGUI(errMsg)
				return None
		#See what the command is
		if command == "START":
			if dssFileName == "":
				errMsg = "ERROR: A DSS file must be specified on any 'START' line"
				errMsg += "\nFailed on the following line:\n%s" %lines[i]
				logging.error(errMsg)
				txtArea.printToGUI(errMsg)
				return None
			currentTSM = inputTSM
		elif command == "ADD": #Add a timeseries
			if inputTSM == None: #must be a constant defined
				if constant == None:
					errMsg = "ERROR: Need to specify either a constant value or a Dss File"
					logging.error(errMsg)
					txtArea.printToGUI(errMsg)
					return None
				currentTSM = currentTSM.add(constant)
			else: #Time Series
				currentTSM = currentTSM.add(inputTSM)
		elif command == "SUBTRACT": #Subtract a timeseries
			if inputTSM == None: #must be a constant defined
				if constant == None:
					errMsg = "ERROR: Need to specify either a constant value or a Dss File"
					logging.error(errMsg)
					txtArea.printToGUI(errMsg)
					return None
				currentTSM = currentTSM.subtract(constant)
			else: #Time Series
				currentTSM = currentTSM.subtract(inputTSM)
		elif command == "MULTIPLY": #Multiply by a constant
			currentTSM = currentTSM.multiply(constant)
		elif command == "FLOOR": #cap to a minimum amount
			currentTSM = currentTSM.screenWithMaxMin(constant, 999999999, 999999999, True, constant, None)
		elif command == "CEILING": #cap to a maximum amount
			currentTSM = currentTSM.screenWithMaxMin(-999999999, constant, 999999999, True, constant, None)
		elif command == "SHIFTHRS": #shift data by specified number of hours
			currentTSM = currentTSM.shiftInTime(int(constant*60)) #function works in minutes
		elif command == "INDEX": #index the time series to the pattern in another timeseries
			currentTSM = TimeSeriesMath(cTsUtils.index(currentTSM.getData(), inputTSM.getData(), -901, -901))
		elif command == "MOVE1": #do a Move.1 transformation
			tsc = currentTSM.getData()
			tscNew = cTsUtils.move1Transform(tsc, yBarMove1, xBarMove1, slopeMove1, True)
			if tscNew is None:
				errMsg = "Failed to perform MOVE.1 transformation...\nSee console log for details"
				logging.error(errMsg)
				txtArea.printToGUI(errMsg)
				return None
			currentTSM = TimeSeriesMath(tscNew)	
		elif command == "ROUTE": #Route the timeseries using the ResSim parameters
			tsc = cResSim.routeDirectTSC(network, currentTSM.getData(), us_JuncName, ds_JuncName)
			if tsc is None:
				errMsg = "Failed to route flows from: %s to: %s" %(us_JuncName, ds_JuncName)
				errMsg += "\nSee the log file for more details"
				logging.error(errMsg)
				txtArea.printToGUI(errMsg)
				return None
			currentTSM = TimeSeriesMath(tsc)
		elif command == "WRITE": #Write out the timeseries
			# Set up the output timeseries pathname and write it out
			outputPath = "//%s/%s//%s/%s/" %(bPart, cPart, tsInt, fPart)
			currentTSM.setPathname(outputPath)
			outDss.write(currentTSM) 
			msg = "\tOutput path: %s" %outputPath
			logging.info(msg)			
			currentTSM = None
		else:
			errMsg = "Invalid Command: %s" %command
			logging.error(errMsg)
			txtArea.printToGUI(errMsg)
			return None
			
	#Close all DSS Files
	outDss.close()
	for dssFile in dssDict.values(): dssFile.close()
	#Print out final messages
	msg = "\nDONE CALCULATING DISAGGREGATED TRIBUTARY LOCALS!"
	logging.info(msg)
	txtArea.printToGUI(msg)
	bar.setValue(100)
	return None
	
