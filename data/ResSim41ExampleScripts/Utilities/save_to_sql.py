'''
Save CWMS forecast.dss to sql
 - must have a forecast open
 - need the sqlite jar in your CWMS install or have the 'load_ExternalModules.py' script set up
 
This script was modified from example here:
	https://stackoverflow.com/questions/3277743/reading-an-sqlite-database-from-jython
	
Got sqlite jar file here, also dropped copy here on NWW drive (N:\EC-H\HYDROLOGY SECTION\Wickham\Scripts\Jython\HecMath_to_sql),.
	and is available from the '.../cwms_esp/for_cwms_watershed/ExternalModules':
	http://www.java2s.com/Code/Jar/s/Downloadsqlitejdbc054jar.htm
	
If haven't set up 'load_ExternalModules.py', jar referenced above needs to be placed with the other CAVI jar files:
	<CAVI install>/CAVI/jar
Note: you may need to open-close the CAVI if it's open since the jars are loaded on startup
	
'''
from __future__     import with_statement
from hec.heclib.dss import *
from com.rma.client import Browser
import sys, time
from com.ziclix.python.sql import zxJDBC
from hec.heclib.dss import HecDss
from hec.hecmath import HecMath
import re
#
#
#### Config #################################
#
#A list of regular expressions defining the paths to be saved - modify as needed
#Some hints on regular expressions:
#  '.*' defines any character from 0-n times
# python reg expr cheat sheet is here: https://www.debuggex.com/cheatsheet/regex/python
#Note: exporting lots of data to sqlite will slow down compute times
regExprToSave = ["/.*/DETROIT - FLOW-RES IN/FLOW/.*/6HOUR/.*/",
				 "/.*/DETROIT-POOL/ELEV/.*/6HOUR/.*/"]
#
#Output sqlite file to be saved in same directory as forecast.dss
dbFileName    = "forecast.db"
#
#Values will be rounded prior to save
sigFigs = 6 #significant digits
decPrec = -1 #decimal precision (-1 = 0.1 precision)
#
#### Functions #############################
def output(msg="") :
	'''
	Output to console log
	'''
	Browser.getBrowserFrame().addMessage("%s" %  msg)
#
#
def chktab(tab) :
	'''
	Checks that the "Modeling" tab is selected
	'''
	if tab.getTabTitle() != "Modeling" : 
		msg = "The Modeling tab must be selected"
		output("ERROR : %s" % msg)
		raise Exception(msg)
#
#
def chkfcst(fcst) :
	'''
	Checks that a forecast is open
	'''
	if fcst is None : 
		msg = "A forecast must be open"
		output("ERROR : %s" % msg)
		raise Exception(msg)
#
#
def stripPathDPart(path):
	'''
	Takes out the D part of a DSS path and
	returns a qualified DSS path
	'''
	pathSplit = path.split("/")
	return "/".join(pathSplit[0:4])+"//"+"/".join(pathSplit[5:7])+"/"
#
#
def stripPathDParts(stringList):
	'''
	wrapper to remove D parts from DSS path
	'''
	return [stripPathDPart(e) for e in stringList]
#
#
def removePathCatalogID(stringList):
	'''
	Removes the catalog ID from a DSS path (including pipe)
	  and replaces with wildcard operator for regular expression search
	e.g., if input is '//ANAW/FLOW-LOCAL/01AUG2019/6HOUR/C:001957|NATURAL/'
	      output is '//ANAW/FLOW-LOCAL/01AUG2019/6HOUR/.*NATURAL/'
	'''	
	return [re.sub("C:.*\|",".*",e) for e in stringList]
#
#
def groupEnsemblePaths(stringList):
	'''
    Input is a list of ensemble DSS paths without F parts
    Output is a dictionary where each element is a list
      of ensemble paths from the same location
      The name of dictionary elements is the DSS path
      without the catalog ID.  e.g., if the name is 
	'''
	uniqueEnsemblePaths = list(set(removePathCatalogID(stringList)))
	out = dict()
	#Iterating through the unique ensemble paths and matching with
	#  regular expression. Dumping regular expression into 
	#  dictionary element as a list
	for regExpr in uniqueEnsemblePaths:
		#Removing wildcard search operator for dictionary key name
		dictKey = re.sub("\.\*","",regExpr)
		regex = re.compile(regExpr)
		out[dictKey] = list(filter(regex.search,stringList))
	return out
#
#
def hmToTuple(hm):
	#returns a tuple of the HecMath object with the format:
	# (<float datetime>, <string DSS F part>, <float value>)
	tsc = hm.getContainer() #convert to tsc for pulling vales and times
	nValues = tsc.numberValues
	fPart = tsc.version
	tscTimes = [e for e in tsc.times] #pulling out times and values as lists
	tscValues = [e for e in tsc.values]
	return zip(tscTimes, [fPart for e in range(nValues)], tscValues)
#
#
def writeEnsembleDSSToSQLite(pathList, dssFile, jdbcURL,sigFigs, decPrec):
	'''
	Given a list of fully qualified DSS paths to write to SQL (pathList),
	  the dssFile object (as HecDSS object), and the JDBC URL to write to
	   (e.g., "jdbc:sqlite:<folder location>/<database file>.db"), writes
	   the paths to sql
	sigFigs is the number of significant digits
	decPrec is the decimal precision (-1 = 0.1 precision)
	'''
	#SQLite connection and driver setup
	jdbcDriver = "org.sqlite.JDBC"
	dbConn = getConnection(jdbcURL, jdbcDriver)
	cursor = dbConn.cursor()
	#Grouping path by ensemble into a dictionary
	ensemblePathGroups = groupEnsemblePaths(pathList)
	output("\nSaving %g unique paths" % len(ensemblePathGroups))
    #Iterating through each dictionary element
	for key in ensemblePathGroups.keys():
		#table will be named after path with catalog ID stripped
		TABLE_DROPPER   = "drop table if exists '%s';"                      % str(key)
		TABLE_CREATOR   = "create table '%s' (date, fPart, value);" 		% str(key)
		RECORD_INSERTER = "insert into '%s' values (?, ?, ?);"              % str(key)
    	#compiling all associated data for path
		hmTupleData=list()
		output("\t%s\t# of paths:\t%g" % (str(key),len(ensemblePathGroups[key])) )
		
		for path in ensemblePathGroups[key]:
			tsc = forecastDSS.get(str(path),True) #reading in 
			if tsc is None or tsc.values is None:
				output("\t\tfound bad data")
				continue
			hm = HecMath.createInstance(tsc) #create HecMath
			hm = hm.roundOff(sigFigs,decPrec)
			hmTupleData = hmTupleData+hmToTuple(hm)
			#output("processing %s\tlength of hmTupleData:\t%g\tlength of hmToTuple:\t%g" % (path, len(hmTupleData), len(hmToTuple(hm))))
		
		try:
			cursor.execute(TABLE_DROPPER)
			cursor.execute(TABLE_CREATOR)
		except zxJDBC.DatabaseError, msg:
			output( msg)
			cursor.close()
			dbConn.close()
			sys.exit(1)
		try:
			cursor.executemany(RECORD_INSERTER, hmTupleData)
			dbConn.commit()
		except zxJDBC.DatabaseError, msg:
			output( msg )
			cursor.close()
			dbConn.close()
			sys.exit(2)
	cursor.close()
	dbConn.close()
#
#
def getConnection(jdbc_url, driverName):
    """
        Given the name of a JDBC driver class and the url to be used 
        to connect to a database, attempt to obtain a connection to 
        the database.
    """
    try:
        # no user/password combo needed here, hence the None, None
        dbConn = zxJDBC.connect(jdbc_url, None, None, driverName)
    except zxJDBC.DatabaseError, msg:
        output( msg)
        sys.exit(-1)
    return dbConn
#
#
def filterWithRegExpr(regExprs,stringList):
	out = list()
	for regExpr in regExprs:
		regex = re.compile(regExpr)
		out = out + list( filter(regex.search,stringList))
	return list(set(out))
#
#
## Get the current forecast info ###########
output("\n\n--- SAVING TO SQL ------------")
output("Start Time:\t%s" % str(time.ctime()))
#open forecast DSS file
frame = Browser.getBrowser().getBrowserFrame()
proj = frame.getCurrentProject()
pane = frame.getTabbedPane()
tab = pane.getSelectedComponent()
chktab(tab)
fcst = tab.getForecast()
chkfcst(fcst) #checks that a forecast is actually open
fcstTimeWindowString = str(fcst.getRunTimeWindow())
#These strings aren't needed, but may be helpful later
fcstNames = fcst.getForecastRunNames()
fcstRun = fcst.getForecastRun(fcstNames[0])
fcstRunKey = fcstRun.getKey()
#forecast DSS file path
fcstDssFileName = fcst.getOutDssPath()
forecastDSS = HecDss.open(fcstDssFileName) #opening
### SQL Connection ######################
#where te save the sqlite file, setup jdbc string
sqlSaveDir = os.path.dirname(os.path.abspath(fcstDssFileName))
jdbcURL   = "jdbc:sqlite:%s\%s"  % (sqlSaveDir, dbFileName) #this is fed to the 'WriteHecMathToSQLite' function
#
output("\nApplying the following filters to paths:\n\t%s" % "\n\t".join(regExprToSave))
#
#filtering DSS paths using regular expression list
allPaths = forecastDSS.getCatalogedPathnames(True)
pathsWithoutDPart = stripPathDParts(allPaths)
uniquePathsWithoutDPart = [str(e) for e in list(set(pathsWithoutDPart))]
selectedPaths = filterWithRegExpr(regExprToSave, uniquePathsWithoutDPart)
#
#
writeEnsembleDSSToSQLite(selectedPaths, forecastDSS, jdbcURL,sigFigs, decPrec)
#
output( "\nWrote new SQLite db here: %s/%s"  % (sqlSaveDir, dbFileName))
forecastDSS.done()
#
#
output("End Time:\t%s" % str(time.ctime()))
output("--- FINISHED SAVING TO SQL ---\n\n")
