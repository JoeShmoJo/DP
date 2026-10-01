'''
Creates new flows given equation parameters from a config csv file
This script was developed for the Lower Snake River CWMS implementation in FY 2019
  to create boundary condition data from ESP traces.  There were some locations
  that needed to be functions of flow from other locations.  This script provides
  a flexible, modular way to do that with a single set of input files that explicitly defines
  the manipulations.
 
Hecmath functions are applied to route, add, and substract flows, but any 
  hecmath function may be used provided that the syntax and definition is correct
See readme_flowmodifier documentation for more info
Author: Ross Wickham, NWW
Date: April 30, 2019
'''
from __future__ import with_statement # must be run first
from hec.heclib.util   import HecTime
from hec2.rts.client   import RTS
from hec2.rts.script   import Forecast
from java.awt          import Frame
from java.awt          import Container
import threading, time
from com.rma.client import Browser
import  hec.script.Constants as constants
from javax.swing import JOptionPane
from hec.dataTable import *
from hec.script import *
from hec.heclib.dss import *
from hec.hecmath import *
from hec.heclib import grid
from hec.heclib.grid import *
from hec.heclib.util import HecTime
import re, csv, time, sys
wshed = "lsr_fullrouting" #routes between every single CCP, much more complex but exactly mimics ResSim routing
#wshed = "lsr_rfcrouting"  #only routes between RFC locations, simpler but might not match ResSim routing - need to check
#Name of the csv file that has formatted RAS boundary condition equations
eqnCsvFileName = "flow_modifier/flow_eqn_config_%s.csv" % wshed
#
#Mod puls configuration file that links a string to a DSS path
modPulsConfigFileName = "flow_modifier/mod_puls_config_%s.csv"  % wshed
#
#Contains PDCs of storage-discharge Mod Puls table
modPulsTblFileName = "flow_modifier/mod_puls_tables_%s.dss" % wshed
#
#DSS File in shared directory containing the raw ESP traces
espDssFileName = "columbia10_6hr.dss"
### Functions --------------------------------------------------------------------------
def output(msg="") :
	'''
	Output to console log
	'''
	Browser.getBrowserFrame().addMessage(" %s" %  msg)
def warning(msg="") :
	'''
	Output to console log
	'''
	Browser.getBrowserFrame().addMessage(Message(" %s" %  msg),"red")
	
def getDictListFromCSV(csvFileName):
    """
  Reads a csv file as a dictionary, naming the keys 
    the same as the column headers
  """    
    out = dict()    
    with open(csvFileName, "r") as readTable:
        reader = csv.DictReader(readTable)
        for row in reader:
            for key in row.keys():
                #Adding key if needed
                 if not out.has_key(key):
                     out[key] = list()
                 #Assigning data
                 out[key].append( row[key] )
    return out
    
def getNVarColumns(eqnDict):
	'''
	From the input data dictionary, returns the number
	  of POSSIBLE input variables by returning the number 
	  of unique numbers in the column names.
	'''
	return len(set(re.findall(r"\d+", "".join(eqnDict.keys()) )))
	
def getNVars(configRow):
	'''
	Number of input variables for specific row in config csv
	'''
	out = 0
	while True:
		if configRow.has_key("var%g" % (out)) and len(configRow["var%g" % (out)][0]) > 0:
			out=out+1
		else:
			break
	return out
	
	
def getKeyValue(eqnDict, key, defaultValue=0,outType="int"):
	'''
	Checks that a value exists in a dictionary
	If not, returns a default value
	Assumes that each key in dictionary is
	  a list and each list element in dictionary
	  is of length 1
	'''
	if eqnDict.has_key(key):
		if len(eqnDict[key]) > 1:
			output("\n\tDictionary element length is longer than one:\t%s" % key)
		out = eqnDict[key][0]
		#output("\t\tout = %s  type = %s\tlength = %g\ttype = %s" % (str(out), type(out), len(out), str(type(out)) ))
		#If csv cell is blank, returns a zero
		if len(out) == 0 or out == 0 or type(out) == "<type 'NoneType'>":
			return defaultValue
		else:
			#return(out)
			if outType == "int":
				return int(out)
			elif outType == "float":
				return float(out)
			elif outType == "string":
				return str(out)
			else:
				output("\tNo default output type set for %s, returning as string" % key)
				return str(out)
	else:
		return defaultValue
		
def extractDictRow(eqnDict,rowNo):
	'''
	Pulls a row from the dictionary assuming each key is
	  a list and all lists have the same length
	'''
	out = dict()
	
	for key in eqnDict.keys():
		#Adding key and extracting row value
		if not out.has_key(key):
			out[key] = list()
			out[key].append(eqnDict[key][rowNo])
	return out
def getGlobalOperations(configRow):
	'''
	Given a single row from the equation dictionary,
	  (as a dictionary), returns the numeric values to
	  be used for the global time series manipuation.
	'''
	return getKeyValue(configRow,"global_multiplier",-999,"int"), getKeyValue(configRow,"global_arithmetic",0,"int")
	
def getVariableConfig(configRow, varNo):
	'''
	Given a single row from the equation dictionary,
	  (as a dictionary), returns the numeric values to
	  be used for the time series manipuation.  Also needed
	  to provide the variable number as an int (e.g., 1 through 3)
	Returns (in this order):
		<smoothing hours>, <lag hours>, <multiplier>, <arithmetic operator>
	
	e.g., if varNo = 1, returns these columns for the given row:
		var1_smoothHrs,	var1_lag,	var1_multiplier,	var1_arithmetic
	'''
	
	#key names
	pathKey =  "var%g" % varNo
	smoothKey = "var%g_smoothHrs" % varNo
	lagKey = "var%g_lag" % varNo
	multKey = "var%g_multiplier" % varNo
	arithKey = "var%g_arithmetic" % varNo
	constantKey = "var%g_constant" % varNo
	fnStringKey = "var%g_fns" % varNo
	
	#Check that key exists in dictionary
	#If not, default value to be returned for all output parameters is zero
	return getKeyValue(configRow,pathKey,0,"string"), getKeyValue(configRow,smoothKey,0,"int"), getKeyValue(configRow,lagKey,0,"int"), \
	             getKeyValue(configRow,multKey,-999,"float"),     getKeyValue(configRow,arithKey,-999,"string"), getKeyValue(configRow,constantKey,0,"float"), \
	              getKeyValue(configRow,fnStringKey,"","string")
	
def parseCheckFnEval(rawFnString):
	'''
	From the string that is read in for the 'varX_fns' argument in config,
	  parses into the various components for the functions
	  and arguments to be passed to the eval statement, respecting
	  the definitions for the argument data type (i.e., logical, int, float)
	Inputs are chained functions to be evaluated on a given HecMath object in
	  the sequence they are entered (left to right). The arguments need to have the
	  data type specified in the argument definition
	e.g., "shiftInTime str 3H; add float 4"
	  
	Returns a list of function templates to be evaluated, given the HecMath
	  object name
	e.g., fnStringList = ["%s.shiftInTime('3H')", "%s.add(4)]
	To be used:	
	
	for fnString in fnStringList:
		varHM = eval(fnString % "varHM")
	'''
	#Create an empty HecMath object to use as reference to determine available functions and extract
	#  available function attributes
	dummyHM = TimeSeriesMath()
	#Parse string by semicolon (function and arguments)
	fnSplit = rawFnString.split(";") #now have a list
	fnSplit = [e.lstrip(" ").rstrip(" ") for e in fnSplit] #removing any trailing or leading spacing
	#Iterate through, parsing the arguments
	fnStringList = list()
	for k in range(len(fnSplit)):
		argSplit = fnSplit[k].split(" ") #parse the function arguments
		argSplit = [e for e in argSplit if len(e) > 0] #removing any extra spaces interpretted as arguments
		
		fnName = [argSplit[e] for e in [0]][0] #first component is function name
		#If even length, then improper definition
		if (len(argSplit) % 2) == 0 and fnName != "modifiedPulsRouting":
			output("\n\nEscaping compute. Function and argument definitions in config file need to have the "+ \
			  "following format:\n\n\t<function> <argument data type> <argument value> ...\n\n and be separated by semicolons. e.g.:\n\n\t" + \
			  "\tshiftInTime str 3H; add float 4")
			sys.exit()
		
		del argSplit[0] #removing first element, i.e., function name - already extracted to 'fnName' string
		if len(argSplit) == 0:
			output("\n\n\nError in parsing function string %s:\n"+\
			"  Need to specify arguments" % rawFnString )
			sys.exit()
		#output("\t\t\tfnName = %s\targList = %s" % (fnName, ", ".join(argStringList)))
		
		if fnName == "modifiedPulsRouting":
			'''
			Required input is:
				modifiedPulsRouting(TimeSeriesMath tsFlow, integer numberSubreaches, floating-point muskingumX)
				
			Applied ON A TABLE OF THE storage-dischage relationships:
				routedFlow = storDischargeCurve.modifiedPulsRouting(tsFlow, reachCount, coefficient)
			'''
			#These can be chained if separated by spaces
			for l in range(len(argSplit)):
				tblName = argSplit[l] #Extracting the name of the table
				fnStringList.append( modPuls[tblName]["eqnTemplate"] )
		#
		#Checking that function exists and can be applied to HecMath object. i.e., isn't an attribute
		elif hasattr(dummyHM,fnName) and str(type(eval("dummyHM.%s" % fnName))) == "<type 'instancemethod'>":
			#Next arguments are <argument data type> <argument value> ...(repeating as needed)
			argStringList = list() #empty list to define arguments
			for l in xrange(0,len(argSplit),2): #Iterating by two b/c expecting 1) data type (int, str,...) and 2) value, repeated
				argDataType = argSplit[l]
				argValue = argSplit[l+1]
				acceptedDataTypes = ["str","int","float", "bool"]
				if not argDataType in acceptedDataTypes:
					output("Error when interpreting function definition for '%s'."+\
					      	" Argument data type '%s' is not a valid data type for conversion.\n\tMust be of type:\t%s" \
							% (rawFnString, argDataType, ",".join(acceptedDataTypes)))
					sys.exit()
					
			argStringList.append("%s('%s')" % (argDataType, argValue))
			#form function string to eval and add to list
			fnString = "%s."+"%s(%s)" % (fnName, ",".join(argStringList))
			fnStringList.append(fnString)
			
		else:
			output("\n\nFunction '%s' is not recognized as a valid HecMath attribute\n\n" % fnName)
			sys.exit()
	
	return fnStringList
def extractPathPart(path, pathPart):
	'''
	From a string , extracts the desired path part
	e.g., A through F
	Returns a string of extracted part
	'''
	pathPartNo = [k for k in range(6) if pathPart == ["A","B","C","D","E","F"][k]][0]
	return splitPathParts(path)[pathPartNo]
	
def extractPathParts(pathList, pathPart):
	'''
	From a list of paths, extracts the desired path part
	e.g., A through F
	Returns a list of extracted part
	'''
	pathPartNo = [k for k in range(6) if pathPart == ["A","B","C","D","E","F"][k]][0]
	out = list()
	for path in pathList:
		out.append( splitPathParts(path)[pathPartNo] )
	return out
def formPath(pathList):
	'''
	Input is a list of all six components of DSS path (A-F)
	Output is atomic character string of merged path parts into
	  fully qualified DSS path
	'''
	return "/" + "/".join(pathList) + "/"
def setPathPart(path, pathPart, replacement):
	'''
	From a fully qualified DSS path string, returns the same string
	  with the specified path part ("A" through "F") changed to the
	  string specified in 'replacement' argument
	'''
	pathPartNo = [k for k in range(6) if pathPart == ["A","B","C","D","E","F"][k]][0]
	splitPath = splitPathParts(path)
	splitPath[pathPartNo] = replacement
	return formPath(splitPath)
	 
def splitPathParts(string):
	'''
	Splits a fully qualified DSS path into its various components
	'''
	strsplit = string.split("/")
	return [strsplit[1], strsplit[2], strsplit[3], strsplit[4], strsplit[5], strsplit[6]]
	
def getConfigPaths(configRow,nVars):
	'''
	Returns a list of the DSS paths associated with the current
	  equation (row) in csv config file.
	'''
	out = list()
	for e in range(nVars):
		temp = configRow["var%g" % e][0] #returns atomic string
		if len(temp) == 0: break #If blank, assume at end of variable definitions
		out.append(temp)
	return out
	
def getUniqueDandFparts(configRow, dssFile, nVars):
	'''
	Gets the unique D and F parts associated with the input variables
	  given the config row in the csv
	'''
	variableConfigDssPaths = getConfigPaths(configRow, nVars)
	#output("\t\t\tMerging data for the following paths:\n\t\t\t\t%s" % str("\n\t\t\t\t".join(variableConfigDssPaths)))
	out = dict()
	#All the paths for all input variable DSS files
	variableDSSPaths = dssFile.getCatalogedPathnames("|".join(variableConfigDssPaths))
	#Get all unique D parts associated with current paths to be analyzed
	allDparts = extractPathParts(variableDSSPaths, "D")
	uniqueDParts = set(allDparts)
	allFparts =  extractPathParts(variableDSSPaths, "F")
	uniqueFParts = set(allFparts)
	#Converting all to string from unicode
	uniqueDParts = [str(s) for s in uniqueDParts]
	uniqueFParts = [str(s) for s in uniqueFParts]
	return uniqueDParts, uniqueFParts
def convertToTSC(hm,outpath):
	#Converting to TSC for save, assigning required path parts
	outTSC = outHM.getData()
	outTSC.watershed = extractPathPart(outpath,"A")  #A part
	outTSC.location =  extractPathPart(outpath,"B")  #B part
	outTSC.parameter = extractPathPart(outpath,"C")  #C part
	outTSC.fullName = "/%s/%s/%s//%s/%s/" % \
		(outTSC.watershed, outTSC.location, outTSC.parameter, extractPathPart(outpath,"E"), \
			outTSC.version)
	return(outTSC)
def loadModPulsTbls(modPulsDSS,modPulsDict):
	'''
	Each row in the mod Puls csv config defines the
	  key to assign the PDC to (tblName), and the DSS
	  path.  Output is a nested dictionary, where each
	  element contains a PDC and an equation template to
	  evaluate as:
	  varHM = eval(modPuls[tblName]["eqnTemplate"] % varHM)
	'''
	out = dict()
	for rowNo in range(len(modPulsDict["tblName"])):
		tblName = modPulsDict["tblName"][rowNo]
		path = modPulsDict["dssPath"][rowNo]
		nSubreaches = modPulsDict["nSubreaches"][rowNo]
		out[tblName] = dict()
		#Check that DSS path exists and load
		if modPulsDSS.recordExists(path):
			#Reading in as a paired Math table - not at all obvious from CH 8 notes on mod Puls function
			out[tblName]["tbl"] = modPulsDSS.read(path) 
		else:
			output("Could not find Mod Puls table '%s' in DSS. Skipping load" % path)
			continue
		#building the equation template so that the only thing needed for the eval 
		#  statement is the name of the HecMath object as a string
		out[tblName]["eqnTemplate"] = "modPuls['"+tblName+"']['tbl'].modifiedPulsRouting(%s,"+nSubreaches+",0.0)"
	return out
output("\n\n--- Flow Manipulation Processing --------------")
output("Start time:\t%s\n\n" % time.ctime())
	
### Loading Config File ---------------------------------------------------------------
output("--- Loading Config --------------------")
frame = Browser.getBrowser().getBrowserFrame()
proj = frame.getCurrentProject()
shdir    = os.path.join(proj.getProjectDirectory(), "shared")
#Equation dictionary of arithmetic to compute 
eqnDict = getDictListFromCSV(shdir+"/"+eqnCsvFileName)
modPulsDict = getDictListFromCSV(shdir+"/"+modPulsConfigFileName)
output("\tEqn CSV file:\t%s" % shdir+"/"+eqnCsvFileName)
output("\tMod Puls Config CSV file:\t%s" % shdir+"/"+modPulsConfigFileName)
### Laading Forecast DSS File ------------------------------------------------------------
#Need to have the same F part as ResSim
output("--- Loading Forecast DSS File ----------")
# Open the DSS File
#forecast = RTS.getBrowserFrame().getForecastTab().getForecast()
#if forecast is None:
#	output("\t\tOpen a forecast to execute script")
#	sys.exit()
#forecastDSSFilePath = forecast.getForecastDSSFilename()
#rtw = forecast.getRunTimeWindow()
#rtwString = str(rtw)
#startTime = rtw.getLookbackTimeString()
#endTime = rtw.getEndTimeString()
dssFile = HecDss.open(shdir+"/"+espDssFileName)
### Laading Forecast DSS File ------------------------------------------------------------
#Need to have the same F part as ResSim
output("--- Loading Mod Puls Tables ----------")
modPulsDSS = HecDss.open(shdir+"/"+modPulsTblFileName)
modPuls = loadModPulsTbls(modPulsDSS, modPulsDict)
output("\tMod Puls DSS file:\t%s" % shdir+"/"+modPulsTblFileName)
### Get F part from ResSim ------------------------------------------------------------
#Need to have the same F part as ResSim
output("--- Getting ResSim F Part --------------")
### Processing TSCs -------------------------------------------------------------------
output("--- Processing Equations ---------------")
nEqn = len(eqnDict["outpath"])
output("\n\tProcessing %g equations" % nEqn)
nVarColumns = getNVarColumns(eqnDict)
output("\tDetected column labels for up to %g variables per equation" % nVarColumns)
	
for rowNo in range(nEqn):
	outpath = eqnDict["outpath"][rowNo] 
	configRow = extractDictRow(eqnDict, rowNo)
	output("\n\t\tpath %g:\t%s\t%s" % (rowNo+1,outpath, getKeyValue(configRow,"notes","","string")) )
	if len(getKeyValue(configRow,"skip","","string"))>0:
		output("\t\t\tSkipping, skip flag set to string with length > 0")
		continue #Skip if anything defined in 'skip' column
	
	
	# %% TODO 
	#wrap this section below in function like this:
	#outTSC = computePath(configRow)
	gMult, gArithmetic = getGlobalOperations(configRow)
	
	nVars = getNVars(configRow) #Number of variables in current equation
	output("\t\t\tRow %g:\t%g Input Variables" % (rowNo+1, nVars) )
	
	uniqueDParts, uniqueFParts = getUniqueDandFparts(configRow, dssFile, nVars)
	
	#output("\t\t\t\tFound %g unique D parts and %g unique F parts\n" % (len(uniqueDParts),len(uniqueFParts)) )
	#Retrieving all of the matched paths
	allVarPaths = list()
	for varNo in range(nVars):
		allVarPaths.append(list())
		#retieving operators and the variable's path name in forecast DSS
		pathExpr, smoothHrs, lagHrs, multiplier, arithmetic, constant,rawFnString = getVariableConfig(configRow, varNo)
		matchedPaths = dssFile.getCatalogedPathnames(pathExpr)
		output("\t\t\tInput Path:\t%s\tnumber of matched paths:\t%g\n\t\t\t\tEquation String(s) to Parse:\t%s" % (pathExpr, len(matchedPaths),rawFnString ))
		#output("matched paths:\n\t%s" % "\n\t".join(matchedPaths) )
		allVarPaths[varNo]= matchedPaths
		
	#Checking that there are an equal number of paths for each variable
	if len(set(map(len,allVarPaths))) != 1:
		output("\t\t\tMismatch between number of paths for variables (e.g., one variable has 1000 associated paths, another has 0). Skipping eqn eval.")
		continue
		
	#Operating on each unique F part since it will be a unique DSS path and a separate write call to DSS file
	skipFPart = False
	for fPart in uniqueFParts:
		outHM = None #Initializing output object to eventually be assigned HecMath
		for varNo in range(nVars):
			
			#retieving operators and the variable's path name in forecast DSS
			pathExpr, smoothHrs, lagHrs, multiplier, arithmetic, constant,rawFnString = getVariableConfig(configRow, varNo)
			#output("Raw string length:\t%s" % str(len(rawFnString)))
	
			path = setPathPart(pathExpr, "F",fPart) #adjusting the path's F and D parts
			path = setPathPart(path, "D","") #Setting to blank
			varHM = dssFile.read(path) #Reading in data
			initialTSC = varHM.getContainer()
			fnStringList = None
			if isinstance(rawFnString,basestring) and len(rawFnString) != 0:
				fnStringList = parseCheckFnEval(rawFnString)
				#Performing functional evaluation
				for fnString in fnStringList:
					evalString = fnString % "varHM"
					#output("\t\t\tevalString = %s" % evalString)
					varHM = eval(evalString)
			#output("\t\t\t\tgot here")
					
			#TODO ###
			#Replace missing values with values from the initial dataset
			newTSC = varHM.getContainer().clone()
			### CONTINUE HERE ####
			#use count missing function to chekc if loop is needed
			#if varHM.numberMissingValues() > 0:
			#	for i in range(len(newTSC.values)):
			#		if newTSC.values[i] == constants.UNDEFINED:
			#			#output("Found undefined values. Replacing")
			#			newTSC.values[i] = initialTSC.values[i]
					
			#Storing to output HecMath object, or performing arithmetic operation on previous and current variable
			if outHM is None:
				outHM = varHM.copy()
			else:
				#Performing arithmetic operation on currently stored TSC and one just created
				if arithmetic == "subtract":
					outHM = outHM.subtract(varHM)
				elif arithmetic == "add":
					outHM = outHM.add(varHM)
				else:
					output("\t\t\t\tNo arithmetic assigned for variable %g, row %g in config csv. Skipping eval." % (varNo, (rowNo+1)))
					skipFPart = True
					break
				
		if skipFPart: #resetting logical and advancing to next F part
				skipFPart = False 
				continue
				
		#Performing global multiplication and arithmetic
		#output("\n\t\t\tApplying global operations. Multiplier = %0.2f, Arithmetic = %0.2f" % (gMult, gArithmetic))
		if not gMult == -999:	outHM = outHM.multiply(gMult)
		if not gArithmetic == 0:	outHM = outHM.add(gArithmetic)
			
		#ensuring there are no negative flows
		#screenWithMaxMin(floating-point minValueLimit,
		#					floating-point maxValueLimit,
		#					floating-point changeLimit,
		#					boolean setInvalidToSpecified,
		#					floating-point invalidValueReplacement,
		#					string qualityFlagForInvalidValue) Q=Questionable, R=Rejected, M=Missing, Blank=Okay(disables quality flags)
		outHM = outHM.screenWithMaxMin(0.0,1E10,1E10,True,0.0,"")
		
		outTSC = convertToTSC(outHM,outpath) #handles conversion to TSC and renames path parts
		#output("\t\t\tSaving to new path = %s\tFile = \t%s" % (outTSC.fullName, dssFile.filename))
		#TODO ##
		#replace missing with zero
		#replaceSpecificValues(HecDouble from, HecDouble to)
		
		#Saving output
		dssFile.put(outTSC)
			
dssFile.done()
output("\n\nEnd time:\t%s" % time.ctime())
output(" --- Done Flow Manipulation Processing ---------\n\n")
