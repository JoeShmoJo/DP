'''
cResSim Module
Contains code to manipulate ResSim
'''
from hec.script import Constants, MessageBox, ClientAppWrapper, ResSim, Plot
from hec.client import ClientApp
from hec.heclib.dss import HecDss
from hec.heclib.util import HecTime
from hec.hecmath import DSS, DSSFileException, HecMathException, TimeSeriesMath
from hec.lang import DSSPathString
from hec.model import PairedValuesExt
from hec.rss.model import ReservoirElement, JunctionElement, ReachElement, DiversionElement
from hec.rss.model import SsarrRouting, NullRouting, PulsChannelRoutingWithLosses
from hec.rss.model import RssModelVariableConstants
from hec.rss.model import SpecifiedRelease, DiversionRule, TimeSeries, ConstantRelease, MonthlyRelease
from hec.rss.model import ReservoirDamElement, DivertedOutletElement, ReservoirOutletElement
from hec.model import RunTimeStep, RunTimeWindow, SeasonalValue
from hec.io import TimeSeriesContainer
import os, sys, logging

#Custom modules
import cRouting, cFile, cExcel, cTsUtils

################################################################################
# STATIC INPUT
naturalLakes = ["Corra Linn", "Arrow Lakes", "Kerr", "Albeni Falls", "Post Falls"] #ALERT, hard coded!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

################################################################################
# CLASS DEFINITIONS
class tsMapping:
	'''
	DEPRECATED
	Class that holds all information about a particular timeseries mapping location
	(one line in the alternative editor TimeSeries or ObservedData tab)
	Simple class that just has attributes corresponding to the information in .fits file
	Similar in concept to a TSRecord
	'''
	def __init__(self, idx = None, name = None, variableID = None, paramName = None, DssPathname = None, DssFilename = None):
		self.idx = idx		
		self.name = name #e.g. "Hills Creek - Flow-Res In" or "~N89" for observed data
		self.variableID = variableID #see hec.rss.model.RssModelVariableConstants 
		self.paramName = paramName # e.g. "Flow"
		self.DssFilename = DssFilename #should be the full dss filepath, not just the stub
		self.DssPathname = DssPathname #pathname mapped in
		self.tsm = None #TimeSeriesMath of the data (not initially defined, but can be populated)
	def getName(self):
		return self.name
	def getParam(self):
		return self.paramName
	def getPathname(self):
		return self.DssPathname
	def getDssFilename(self):
		return self.DssFilename
		
class tsmBank:
	'''
	Class that holds a bank of read Time series
	Assumes that the time series have been checked that they are all defined for the 
	correct time window
	Each entry in the bank is defined by the Dss file name from which it came from, 
	as well as the pathname that is read (no D part defined)
	This can be helpful to do all of the reading of timeseries at the outset, rather
	than getting to 90% and then finding that a time series doesn't exist
	Typically populated from data in .fits files
	If the time series are extremely large, there might not be enough memory to store
	these
	Should close the bank after finished to release memory
	'''
	def __init__(self):
		self.tsmDict = {} #first index is the dss file, 2nd is the pathname
	def containsTS(self, dssFileName, pathname):
		#Returns true if the time series exists in the bank
		#Returns false otherwise
		if self.tsmDict.has_key(dssFileName):
			if self.tsmDict[dssFileName].has_key(pathname):
				return True
		return False
	def withdrawTS(self, dssFileName, pathname):
		#Returns the TimeSeriesMath object that was stored
		#@dssFileName   string  the dssFile from which the ts comes from
		#@pathname      string  the pathname to retrieve
		if self.tsmDict.has_key(dssFileName):
			if self.tsmDict[dssFileName].has_key(pathname):
				#The data exists, get it
				return self.tsmDict[dssFileName][pathname]
		#otherwise, return nothing
		return None
	def depositTS(self, dssFileName, pathname, tsm):
		#@dssFileName   string  the dssFile from which the ts comes from
		#@pathname      string  the pathname to retrieve
		#@tsm   TimeSeriesMath  the TimeSeriesMath object to store
		if not self.tsmDict.has_key(dssFileName):
			#create a new dictionary that will have pathnames as keys and tsms as values
			self.tsmDict[dssFileName] = {}
		#Add the time series to the bank
		self.tsmDict[dssFileName][pathname] = tsm
		return True
	def close(self):
		#clears out all data
		del self.tsmDict
		self.tsmDict = {}
	def checkInTimeSeries(self, dssDict, tsDataSetObj, beginTime, endTime, ignoreDssFile = None, rssConstant = None, tsInt = None):
		'''
		Function to read in all input time series and make sure they are fully defined
		For the whole time window
		Adds all read time series to the bank to be withdrawn later if required
		@dssDict	Dictionary of DssFiles that have already been opened with a predefined time window
							keys are the dss file name (string), values are the DssFile objects
		@tsDataSetObj	A TSDataSet object that contains all time series mappings
								keys are data location names, values are tsMapping objects
		@beginTime  HecTime or string   The start time to check
		@endTime    HecTime or string   The end time to check
		@ignoreDssFile string     If supplied, the method won't check time series from this file
		@rssConstant integer      If supplied, then only time series with this variable will be checked
		                          otherwise, all time series will be processed
		                          typically RssModelVariableConstants.VID_NODE_FLOW
		@tsInt       string       The time interval
		                          If supplied, all time series will be converted to this interval
		                          If not supplied, the time series will not be converted at all
		Modifies this tsmBank object with the TimeSeriesMath objects that were read
		Returns a message with all of the errors
		The message will be blank if there are no issues
		'''
		beginHecTime = HecTime(beginTime)
		endHecTime = HecTime(endTime)
		#Loop through all tsMapping objects
		msg = ""
		tsRecsMissing = [] # list of TSRecord objects that had no data
		tsRecsTruncated = [] #list of TSRecord objects that didn't have the whole time window
		for tsRec in tsDataSetObj.getTSRecords():
			name = tsRec.getName()
			param = tsRec.getParamName()
			varID = tsRec.getVariableId() #RssModelVariableConstants ID 
			dssName = tsRec.getDSSFilename()
			dssName = ClientApp.Workspace().makeAbsolutePath(dssName)
			pathname = tsRec.getDSSPathname()
			#skip if the variable ID isn't what is desired
			if rssConstant: #the argument was supplied
				if varID != rssConstant: continue
			#skip if time series already stored in the bank
			if self.containsTS(dssName, pathname): continue
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
				tsRecsMissing.append(tsRec)
				continue
			#check the start date and end date
			tsmFirstTime = HecTime(tsm.firstValidDate(), HecTime.MINUTE_INCREMENT)
			tsmLastTime  = HecTime(tsm.lastValidDate(), HecTime.MINUTE_INCREMENT) 
			if tsmFirstTime.notEqualTo(beginHecTime):
				tsRecsTruncated.append(tsRec)
			elif tsmLastTime.notEqualTo(endHecTime):
				tsRecsTruncated.append(tsRec)
			else:
				#it's good, Add the time series to the bank
				if tsInt:
					# the output is desired to be changed to a uniform timestep
					# Convert it, but deposit it with the original pathname
					tsm = cTsUtils.transformTSM(tsm, tsInt)
				self.depositTS(dssName, pathname, tsm)
		# Prepare a nice, organized output message:
		if len(tsRecsMissing) > 0:
			msg += "\n\nTime Series that do not exist:"
			for tsRec in tsRecsMissing:
				msg += "\n\tName:     %s" %tsRec.getName()
				msg += "\n\tDss File: %s" %tsRec.getDSSFilename()
				msg += "\n\tPathname: %s\n" %tsRec.getDSSPathname()
		if len(tsRecsTruncated) > 0:
			msg += "\n\nTime Series not defined over the full time window:"
			for tsRec in tsRecsTruncated:
				msg += "\n\tName:     %s" %tsRec.getName()
				msg += "\n\tDss File: %s" %tsRec.getDSSFilename()
				msg += "\n\tPathname: %s\n" %tsRec.getDSSPathname()
		return msg
# END OF CLASS DEFINITIONS
################################################################################
# FUNCTION DEFINITIONS

def getSimulation() :
	'''
	Verify that ResSim is in the correct module and has simulation open
	@return SimulationPeriod   The currently active simulation
	'''
	module = ClientAppWrapper.getCurrentModule() #hec.rss.client.RSimSimulationMode
	#module = ResSim.getCurrentModule() #alternately
	if module.getName() != "Simulation" : 
		raise AssertionError, "ResSim is in %s module, Simulation module is required" % `module`
	simulation = module.getSimulation()
	if not simulation :
		raise AssertionError, "Must have a simulation open."
	return simulation

def getResSimTimewindow(simulation) :
	runTimeWindow = simulation.getRunTimeWindow()
	startTime = runTimeWindow.getStartTimeString()
	endTime = runTimeWindow.getEndTimeString()
	lookbackTime = runTimeWindow.getLookbackTimeString()
	return startTime, endTime, lookbackTime	
	
def getActiveRun(simulation):
	#@simulation SimulationPeriod The input SimulationPeriod object to search
	# returns the active RssSimRun object
	activeRun = None
	for run in simulation.getSimulationRuns():
		if run.isActiveRun() :
			activeRun = run
			activeFpart = run.getKey().split(":")[0]
			activeAlternativeName = run.getUserName()
			hasActive = Constants.TRUE	
	if activeRun is None:
		msg = "Must have one alternative 'active', exiting."
		raise AssertionError, msg
	return activeRun

def getRssRun(rssRunName):
	# returns the RssRun of the simulation
	#@rssRunName String       the name of the alternative to retrieve (e.g. "Test-----0", not "Test")
	# Will return None if the name isn't found
	getSimulation() #just do the check to see we're in the right place
	module = ClientAppWrapper.getCurrentModule() #hec.rss.client.RSimSimulationMode
	rssRunObj = module.getRssRun(rssRunName)
	return rssRunObj

def getListOfOutputFParts(simulation):
	# retuns a list of strings corresponding to the output FParts for the simulation (SimulationPeriod)
	fParts=[]
	for run in simulation.getSimulationRuns(): 
		fPart = run.getKey().split(":")[0]
		fParts.append(fPart)	
	return fParts	

def getListOfAltNames(simulation):
	# returns a list of strings with all of the alternatives in the simulation (SimulationPeriod)
	altNames = []
	for run in simulation.getSimulationRuns():
		altNames.append(run.getUserName())
	return altNames
	
def getSpecificRun(simulation, rssRunName):
	# returns the RssSimRun of the simulation
	#@simulation SimulationPeriod The input SimulationPeriod object to search
	#@rssRunName String           the name of the alternative to retrieve (e.g. "Test", not "Test-----0")
	# Will return None if the name isn't found
	return simulation.getSimulationRun(rssRunName)
	
def getNetwork(run):
	# returns the network (RssSystem) for the given run (RssSimRun)
	return run.getRssSystem()

def getOutputFpart(run):
	# returns the output FPart for the provided run (RssSimRun)
	fPart = run.getKey().split(":")[0]
	return fPart
	
def getCurrentNetwork():
	#@simulation SimulationPeriod The input SimulationPeriod object to search
	# returns the currently active network (RssSystem)
	simulation = getSimulation()
	run = getActiveRun(simulation)
	return run.getRssSystem()

def getCurrentRssAlt():
	#@simulation SimulationPeriod The input SimulationPeriod object to search
	# returns the currently active RssAlt
	simulation = getSimulation()
	run = getActiveRun(simulation)
	return run.getRssAlt()
	
def getCurrentRssAltName():
	#@simulation SimulationPeriod The input SimulationPeriod object to search
	# returns the short name of the currently active RssAlt (e.g. "Test", not "Test-----0")
	simulation = getSimulation()
	run = getActiveRun(simulation)
	return run.getUserName()

def getTSDictFromFITSfile(network, altName, isObs=False, typeToRead = "Flow"):
	'''
	Function to read the observed data .fits file for a particular alternative
	network = RssSystem
	altName = string (e.g. "Observed" or "Observed--", not "Observed--0": no number)
	isObs = boolean, whether or not to get the observed data TS mapping or the regular
	typeToRead = string (e.g. "Flow", "Elev", "" to get all types), the types of observed data to get
	Returns a dictionary with the keys as the data location names, 
	and the values are tsMapping objects
	If it can't find or process the .fits file, it will return None
	If isObs is True, the keys will be something like "~N86"
	If isObs is False, the keys will be something like "Hills Creek - Flow-Res In"
	
	'''
	# Find the .fits file
	obsStr = "Obs.fits"
	runDir = network.getBaseDirectory() + "/"
	altStr = altName.replace(" ", "_") # if the alt has a space in the name, ResSim puts an underscore
	for f in os.listdir(runDir):
		ext = f.split(".")[-1]
		if isObs: #obsStr will exist in the .fits file name
			if ext == "fits" and f.startswith(altStr) and obsStr in f:
				rf = runDir+f
				break
		else:
			if ext == "fits" and f.startswith(altStr) and obsStr not in f:
				rf = runDir+f
				break		
	try: lines = cFile.fileOpenReadClose(rf)
	except: 
		m = "Could not find TS data .fits file for: '%s' in directory:\n %s" %(altName, runDir)
		logging.error(m)
		raise AssertionError, m
	logging.debug("Successfully read .fits file: %s" %f)
	tsDataDict = {}	
	idx, name, varID, param, path, dssFileName = None, None, None, None, None, None
	for line in lines:
		if "TSrecord=" in line: idx = line.split("TSRecord=")[-1].strip()
		elif "TSRecord Name=" in line: name = line.split("TSRecord Name=")[-1].strip()
		elif "VariableID=" in line: varID = line.split("VariableID=")[-1].strip()
		elif "ParamName=" in line: param = line.split("ParamName=")[-1].strip()
		elif "DssPathname=" in line and name: path = line.split("DssPathname=")[-1].strip().upper()
		elif "DssFilename=" in line: 
			dssFileName = line.split("DssFilename=")[-1].strip() #e.g. shared/test.dss
			dssFileName = network.makeAbsolutePathFromWatershed(dssFileName)
			#dssFileName = ClientApp.Workspace().makeAbsolutePath(dssFileName)
		elif "End=" in line:
			#if "Flow" not in param: continue #Only get flow data
			if typeToRead not in param: continue #Only get specified data types (if "", will get all)
			#Create the tsMapping object
			mapObj = tsMapping(idx, name, varID, param, path, dssFileName)
			#Add the tsMapping object to the dictionary
			tsDataDict[name] = mapObj
	return tsDataDict
	
def getConnectedReaches(element):
	# Function to return a list of all the reach element objects connected to "element"
	# element = any element (e.g. JunctionElement)
	connectedElems = list(element.getConnectedElements())
	reachElems = []
	for elem in connectedElems:
		if isinstance(elem, ReachElement):
			reachElems.append(elem)
	return reachElems
	
def getConnectedDiversions(juncElem):
	# Function to return the diversion element objects connected to juncElem
	# element = any JunctionElement
	# There can be multiple diversions connected to the junction
	# Returns a list of DiversionElement objects, or None if there is no diversion
	divElems = []
	connectedElems = list(juncElem.getConnectedElements())
	for elem in connectedElems:
		if isinstance(elem, DiversionElement):
			divElems.append(elem)
	if divElems == []: #never found a diversion
		return None
	else:
		return divElems

def getRealHeadwaterJunctions(network):
	# Function to return a list of all the headwater junctions in the model
	# list of JunctionElement objects
	# the native ResSim rule kind of screws it up sometimes, including non-headwater
	juncs = network.getHeadwaterJunctions()
	hwJuncs = []
	for junc in juncs:
		element = network.findJunction(junc.toString())
		connectedElems = element.getConnectedElements()
		# Remove any diversion elements
		nonDivElems = []
		for elem in connectedElems:
			if not isinstance(elem, DiversionElement):
				nonDivElems.append(elem)
		if len(nonDivElems) == 1: #No upstream and downstream connection
			hwJuncs.append(junc)
	return hwJuncs
	
def getConfluenceJunctions(network):
	# Function to return a list of all the confluence junctions in the model
	# list of JunctionElement objects
	juncs = network.getJunctionNames()
	confJuncs = []
	for junc in juncs:
		element = network.findJunction(str(junc))
		connectedReaches = getConnectedReaches(element)
		dsElem = element.getDownstreamNode().getDownstreamElement()
		if len(connectedReaches) >= 3 or \
		 (len(connectedReaches)>=2 and dsElem==None) or \
		 (len(connectedReaches)>=2 and str(dsElem)=="Pool"): 
			#At least 3 connected reaches or at the mouth and 2 connected reaches
			#Or two upstream reaches and the downstream connection is a pool
			#confJuncs.append(junc)
			confJuncs.append(element)
	return confJuncs
	
def getConfluenceResvPoolDict(network):
	# Function to return a dictionary:
	# 	keys = all the confluence reservoirs in the model (the "pool" element, not ReservoirElement)
	# 	values = list of all JunctionElements that flow into the reservoir
	# Loop through all junctions first to see what their downstream element is
	juncs = network.getJunctionNames()
	dsResvDict = {}
	confResvDict = {}
	for junc in juncs:
		juncElem = network.findJunction(str(junc))
		#To get to the ReservoirElement, we need to go twice downstream elements
		#This first Downstream Element is the "Pool" (general Element)
		#To get the ReservoirElement, need to do a .getParent() call
		dsElem = juncElem.getDownstreamNode().getDownstreamElement() #"Pool" element
		if dsElem == None: continue #last junction in the model
		resvElem = dsElem.getParent()
		if not isinstance(resvElem, ReservoirElement): continue #only get reservoir elements
		if dsElem not in dsResvDict.keys(): 
			#1st time we encounter it
			dsResvDict[dsElem] = [juncElem] 
		else: 
			#This is the 2nd or 3rd time we've encountered it
			dsResvDict[dsElem].append(juncElem)
	#Only keep reservoirs with more than one upstream junction
	for poolElem in dsResvDict.keys():
		if len(dsResvDict[poolElem]) > 1: #more than one
			confResvDict[poolElem] = dsResvDict[poolElem]
	return confResvDict
	
def getConfluenceResvNames(network):
	# Function to return a list of reservoir names that have more than one inflow junction:
	# 	values = all the confluence reservoir names in the model (strings, e.g. "Bonneville")
	# 	values = list of all JunctionElements that flow into the reservoir
	confResvPoolDict = getConfluenceResvPoolDict(network) #Keys are "Pool" elements
	resvNames = []
	for poolElem in confResvPoolDict.keys():
		resvName = poolElem.getParent().toString()
		resvNames.append(resvName)
	return resvNames
	
def getPoolElemFromResvElem(resvElem):
	#Returns the "Pool" element for a provided resvElem (ReservoirElement)
	#The "Pool" element is a generic hec.rss.model.Element
	#"Pool" is typically used when ordering the network
	for childElem in resvElem.children(): #includes pool, dams, diverted outlets
		if childElem.toString() == "Pool": #always named "Pool"
			return childElem
	# Never found it
	return None
	
def orderElementsFromUpstream(network):
	# Function to return a list of ordered elements from headwater to the mouth
	hwJuncs = getRealHeadwaterJunctions(network)
	hwJuncsLeft = []
	for junc in hwJuncs:
		hwJuncsLeft.append(junc) 
	confJuncs = getConfluenceJunctions(network)
	confElemsLeft = []
	for junc in confJuncs:
		confElemsLeft.append(junc)
	# Add in confluence reservoirs (multiple inflows)
	confResvDict = getConfluenceResvPoolDict(network)
	for poolElem in confResvDict:
		confElemsLeft.append(poolElem)
	# Initialize the looping to figure out the compute order
	done = False
	elemList = []
	confInflowCount = dict.fromkeys(confElemsLeft,0)
	while not done:
		hwJuncsNew = []
		for hwJunc in hwJuncsLeft:
			# get downstream elements up to the next confluence point
			#element = network.findJunction(str(hwJunc))
			element = hwJunc
			elemList.append(element)
			atConfluence = False
			while not atConfluence:
				try:
					element = element.getDownstreamNode().getDownstreamElement()
					if element in confElemsLeft:
						# at a confluence point, done with this headwater loop
						atConfluence = True
						confInflowCount[element] += 1
						# check to see if the other inflows to the confluence have come in yet
						if isinstance(element, JunctionElement):
							# first need to see how many upstream reaches there are
							dsElem = element.getDownstreamNode().getDownstreamElement()
							upstreamElems = list(getConnectedReaches(element))
							try: # the last point doesn't have a downstream element
								upstreamElems.remove(dsElem) # only keep upstream elements
							except:
								pass
							numUpstrmElems = len(upstreamElems)
						else: #a "pool" element
							#Get the number of upstream JunctionElements
							numUpstrmElems = len(confResvDict[element])
						if confInflowCount[element] == numUpstrmElems:
							# all the inflows have come in--this is a new "headwater" element
							hwJuncsNew.append(element)
					else:
						# keep going downstream
						elemList.append(element)
				except:
					# No downstream element, stop
					atConfluence = True
		hwJuncsLeft = hwJuncsNew
		if len(hwJuncsLeft) == 0:
			done = True
			#Remove the last entry (should be None)
			elemList = elemList[:-1]
	return elemList

def getElevationStorageTable(reservoirName, network):
  # Returns a table as a PairedValuesExt class that inputs elevation and returns storage
  # reservoirName = string
  # network = rssSystem
	reservoirObj = network.findReservoir(reservoirName)
	storageElement = reservoirObj.getStorageFunction()
	storageTable = storageElement.getElevationStorageValues()
	pairedDataContainer = storageTable.getPairedDataContainer()
	elevStorTable = PairedValuesExt() 
	elevStorTable.setData(pairedDataContainer)
	return elevStorTable

def getStorageElevationTable(reservoirName, network):
  # Returns a table as a PairedValuesExt class that inputs storage and returns elevation
  # reservoirName = string
  # network = rssSystem
	reservoirElement = network.findReservoir(reservoirName)
	storageElement = reservoirElement.getStorageFunction()
	storageTable = storageElement.getElevationStorageValues()
	pairedDataContainer = storageTable.getPairedDataContainer()
	storElevTable = PairedValuesExt() 
	storElevTable.setData(pairedDataContainer)
	elevations = storElevTable.getXArray()
	storages = storElevTable.getYArray()
	storElevTable.setArrays(storages,elevations)
	return storElevTable

def getElevationReleaseTable(resvName, outletName, network):
	'''
	Returns a PairedValuesExt object that represents the elevation vs. release capacity table
	This only works for controlled outlets
	@resvName   string  The name of the reservoir to retrieve
	@outletName string  The exact name of the controlled outlet to retrieve
	@network    rssSystem
	'''
	resv = network.findReservoir(resvName)
	if not resv: return None
	outletElem = resv.getElementByName(outletName)
	if not outletElem: return None
	adjFlow = outletElem.getFunction() #AdjustableFlow
	if adjFlow.hasMultipleGateSettings():
		# The x-values are the elevations, the y-values are always flows, the z-curves are gate settings
		elevRelTable = adjFlow.getCapacityValuesBySetting() # hec.rss.model.PairedValuesExt
	else: # normal elev v. flow data
		# The x-values are actually the elev, the y-values are flow in cfs, which is why shiftMV is backwards
		dataVec = adjFlow.getCapacityValues().getDataVector() # vector of hec.model.ValueSet
		elevRelTable = PairedValuesExt()
		elevs = []
		rels = []
		for vs in dataVec:
			elevs.append(vs.xval)
			rels.append(vs.yval)
		elevRelTable.setArrays(elevs, rels)
	return elevRelTable

def getLookback(resvName, rssAlt, paramName = None):
	'''
	Returns the lookback parameter for a reservoir
	Only works if the the lookback is defined as a constant
	@resvName  string  The reservoir name to retrieve
	@rssAlt    RssAlt  The alternative with the lookback data
	@paramName string  Either "Release", "Elevation", or "Storage"
	'''
	#Need to find the 
	network = rssAlt.getSystem()
	resvElem = network.findReservoir(resvName)
	if not resvElem: return None
	inputTSDataSet = rssAlt.getInputTSDataSet()
	if "ELEV" in paramName.upper():
		rssConstant = RssModelVariableConstants.VID_POOL_ELEV
	elif "RELEASE" in paramName.upper():
		#come back here!
		pass
	else:
		return None
	tsrp = resvElem.getTSRecordProxy(rssConstant)
	if tsrp is None: return None
	tsName = tsrp.getName() # e.g. ~E468:F
	hindcastList = rssAlt.getHindcastData() #list of hec.rss.model.HindcastData
	for hd in hindcastList:
		varID = hd.getVariableId()
		objKey = hd.getObjectKey() #e.g. "~E2394:F"
		if objKey == tsName and varID == RssModelVariableConstants.VID_POOL_HINDELEV:
			#Found the entry
			#Check to make sure the lookback is a constant
			if hd.getTypeName() != "Constant": return None
			return hd.getValue()
	return None

def getHecTimeFromRuntimestep(rtsObj):
	# Returns an HecTime object that reflects the true time of the step (2400 hours)
	# rtsObj = RunTimeStep class
	currentDate = rtsObj.getHecTime().clone()
	# If the hecTime object returned is daily granularity, subtract a day due to midnight shift
	if currentDate.getTimeGranularity() == HecTime.DAY_INCREMENT: # days
		currentDate.subtractDays(1) # Midnight shift
	currentMonth = currentDate.month()  
	currentDay = currentDate.day()
	currentYear = currentDate.year()
	# If the daily hecTime object does not have a granularity of minutes, 
	# Set the current date to a granularity of minutes (2400 hours at the end of the day)
	if currentDate.getTimeGranularity() == HecTime.DAY_INCREMENT: 
		currentDate.setTimeGranularity(HecTime.MINUTE_INCREMENT) #granularity of minutes
		currentDate.setYearMonthDay(currentYear, currentMonth, currentDay, 1440)
	return currentDate

def readObservedData(simDss, junc, obsTSDataDict, fPartObs, tsInterval):
	'''Attempts to retrieve the data for observed flow for a junction
	If it doesn't exist, returns the data from the ResSim run that echoed observed releases
	@param DssFile          simDss        already opened simulation.dss file
	@param JunctionElement  junc          the desired junction
	@param dict             obsTSDataDict dict of tsMapping object (observed data paths)
	@param tsInterval				string				time step "1HOUR" or "1DAY"
	@return TimeSeriesMath                dict of JuncPeaks objects'''
	obsVec = junc.getObsDataVector() # vector of strings (e.g. "~N36")
	useObsData = False
	if obsVec:
		obsCode = obsVec[0].split(":")[0] # obsVec[0] is something like "~N175:0"
		obsPath = obsTSDataDict[obsCode].getPathname()
		if len(obsPath) == obsPath.count("/"): #blank pathname
			useObsData = False 
		else: #Good to go
			useObsData = True
	if useObsData:
		isGaged = True
	else:
		obsPath = "//%s/FLOW//%s/%s/" %(junc.toString(), tsInterval, fPartObs)
		isGaged = False
		logging.info('\t\tNo true "observed data", using ResSim output: %s' %fPartObs)
	try: obsTSM = simDss.read(obsPath)
	except:
		logging.error("Could not read observed flow pathname:\n\t%s\nFrom file:\n\t%s" %(obsPath, simDss))
		return None, None
	return obsTSM, isGaged
	
def getTSRecord(tsDataSetObj, rssLocation, rssConstant, txtArea, 
	isStrict = True, displayMessages = True):
	'''
	Attempts to retrieve a TSRecord object from the ResSim network that corresponds
	The TSRecord object will have the dss file and pathname defined, but no Container data
	
	an retrieve either simulated or observed data for any element
	Will return None if the time series is not well defined to let the calling
	 function decide what to do with it
	If the time series is well defined, but it just doesn't exist in the dss file,
	 it will throw an error
	@tsDataSetObj    TSDataSet      The TSDataSet to retrieve from (observed, input, regulated output)
	@rssLocation     Element/RssNode the element to retrieve output from
	                                 can be an RssNode, JunctionElement, ReservoirElement, etc.
	@rssConstant     Integer        the parameter to retrieve, e.g.
	                                RssModelVariableConstants.VID_POOL_ELEV
	                                RssModelVariableConstants.VID_NODE_FLOW
	                                RssModelVariableConstants.VID_JUNC_STAGE
	@txtArea         JTextArea      must have a "printToGUI" method defined
	@isStrict        Boolean        if true, then errors stop the compute immediately
	                                if false and an error comes up, will just return None
	@displayMessages Boolean        if true, then warning messages will be pumped out
	Return value:
	@tsRec           TSRecord       Data about the time series desired. If None, the data didn't exist
	'''
	elemName = rssLocation._name
	#Get the TSRecordProxy that contains information about which timeseries is linked
	if rssConstant == RssModelVariableConstants.VID_NODE_FLOW and \
	 (isinstance(rssLocation, JunctionElement) or isinstance(rssLocation, ReachElement)): 
		#Flow, have to do it the hard way. Need to get it from the outflow node, not the element
		node = rssLocation.getDownstreamNode() #RssNode
		tsrp = node.getTSRecordProxy(rssConstant)
	elif rssConstant == RssModelVariableConstants.VID_NODE_KNOWNFLOW:
		#Known inflow (local flow) (only works for input/observed TSDataSets, not regOutput)
		#Must be retrieved from the upstream node, not the junction element itself
		#If getting output local flows, the parameter is actually just flow
		tsrp = rssLocation.getTSRecordProxy(rssConstant)
	else:
		#Can get data easily (e.g. pool elevation, stage)
		tsrp = rssLocation.getTSRecordProxy(rssConstant)
	if tsrp is None:
		errMsg = "\nCouldn't locate a ResSim model variable for: %s" %elemName
		errMsg += "\nThat corresponds to the RssModelVariableConstant: %s" %rssConstant
		errMsg += "\nShouldn't even be asking for this variable at this location"
		errMsg += "\nCheck the RssModelVariableConstants.java file to see the codes"
		if displayMessages: 
			txtArea.printToGUI(errMsg)
			logging.error(errMsg)
		if isStrict: #need to stop at any error here
			raise AssertionError, errMsg
		else: 
			return None
	tsName = tsrp.getName() # e.g. New York Irrigation Diversion, or ~E468:F
	tsRec = tsDataSetObj.getTSRecord(tsName, rssConstant)
	return tsRec
	
def getTSMFromSimulationDSS(simDss, rssLocation, run, rssConstant, txtArea, 
	useObsData, isStrict = True, displayMessages = True):
	'''
	Attempts to retrieve a TimeSeriesMath object from the simulation.dss file
	Can retrieve either simulated or observed data for any element
	Will return None if the time series is not well defined to let the calling
	 function decide what to do with it
	If the time series is well defined, but it just doesn't exist in the dss file,
	 it will throw an error
	@simDss          DssFile        already opened simulation.dss file
	@rssLocation     Element/RssNode the element to retrieve output from
	                                 can be an RssNode, JunctionElement, ReservoirElement, etc.
	@run             RssRun         the RssRun to retrieve data from
	                                has to be an RssRun because an RssAlt can only
	                                get input and observed TS Mapping, not output
	@rssConstant     Integer        the parameter to retrieve, e.g.
	                                RssModelVariableConstants.VID_POOL_ELEV
	                                RssModelVariableConstants.VID_NODE_FLOW
	                                RssModelVariableConstants.VID_JUNC_STAGE
	@useObsData      Boolean        if true, then "observed data" will be retrieved, not modeled data
	@txtArea         JTextArea      must have a "printToGUI" method defined
	@isStrict        Boolean        if true, then errors stop the compute immediately
	                                if false and an error comes up, will just return None
	@displayMessages Boolean        if true, then warning messages will be pumped out
	Return value:
	@tsm             TimeSeriesMath The time series that was retrieved
	'''
	#Figure out with TSDataSet to use
	if useObsData:
		#tsDataSetObj = alt.getObservedTSDataSet()
		tsDataSetObj = run.getObservedTSData() #TSDataSet
	else: #use simulated output data
		#tsDataSetObj = run.getOutputTSDataSet() #doesn't work
		tsDataSetObj = run.getRegOutputTSData()
		#tsDataSetObj = run.getCumLocOutputTSData()
		#tsDataSetObj = run.getUnregOutputTSData()
	elemName = rssLocation._name
	#Get the TSRecord object for the variable
	tsRec = getTSRecord(tsDataSetObj, rssLocation, rssConstant, txtArea, isStrict, displayMessages)
	if tsRec is None:
		if useObsData:
			errMsg = "\nCouldn't locate observed data for: %s" %elemName
			errMsg += "\nShould have the box checked in the 'Observed Data'"
			errMsg += "\n tab of the Reservoir Editor or Junction Editor"
		else:
			errMsg = "\nFailed to find time series for: %s" %elemName
			errMsg += "\nMight be mixing up observed/modeled data?"
		if displayMessages: 
			txtArea.printToGUI(errMsg)
			logging.error(errMsg)
		return None
	path = tsRec.getDSSPathname()
	if len(path) == path.count("/"): #blank pathname
		errMsg = "\tBlank Pathname mapped in at: %s,%s" %(elemName, tsRec.getName())
		if displayMessages: 
			txtArea.printToGUI(errMsg)
			logging.error(errMsg)
		return None
	#should be able to read the timeseries
	try:
		tsm = simDss.read(path)
	except (DSSFileException, HecMathException): # Couldn't find the DSS path
		errMsg =  "ERROR IN READING DATA: COULD NOT READ PATHNAME:"
		errMsg += "\n%s\nFROM DSS FILE: %s\n" %(path, simDss.getFilename())
		errMsg += "\nProbably need to retrieve/map in the correct data"
		errMsg += "\nOr rerun the time-series extract, or re-run the alternative"
		if displayMessages: 
			txtArea.printToGUI(errMsg)
			logging.error(errMsg)
		raise AssertionError, errMsg 
	return tsm

def routeDirectTSC(network, tsc, startJuncName, endJuncName):
	'''
	Function to route flow from one junction to another
	It will not add any local flows in--just a pure and simple direct routing
	@network				rssSystem						the network to use for the routing parameters
	@tsc						TimeSeriesContainer	the input time series at startJuncName
	@startJuncName	string							Exact name of the junction to start routing from in the network
	@endJuncName		string							Exact name of the junction to finish routing at in the network
	returns a TimeSeriesContainer
	'''
	if network is None:
		logging.error("Need to pass in a valid network (RssSystem)")
		return None
	startJunc = network.findJunction(startJuncName)
	endJunc = network.findJunction(endJuncName)			
	if startJunc is None: 
		logging.error("The start Junction doesn't exist in the network: '%s'" %startJuncName)
		return None
	elif endJunc is None:
		logging.error("The end Junction doesn't exist in the network: '%s'" %endJuncName)
		return None
	#Check to see if the endJunction is downstream of the startJunction
	if endJunc not in network.getDownstreamElements(startJunc):
		logging.error("The end Junction: '%s' is not downstream of the start Junction: '%s'" %(endJuncName, startJuncName))
		return None
	#We are reasonably sure we can route the flows--let's do it
	element = startJunc
	flowTSC = tsc.clone()
	count = 0
	while element._name != endJuncName:
		count += 1
		# Get the next downstream element
		dsNode = element.getDownstreamNode()
		element = dsNode.getDownstreamElement()
		elemName = element._name
		# If the element is a reach, route the flow to the next junction
		if isinstance(element, ReachElement):
			# If the element is a reach, route the flow to the next junction
			routingObj = element.getFunction()
			logging.debug("Reach : %s" %elemName)
			routeReach = cRouting.buildReach(routingObj)
			if routeReach is None:
				errMsg = "The Script cannot handle any routing methods besides SSARR, Muskingum, ModPuls, or Null:"
				errMsg += "\n%s has routing of: %s" %(elemName, routingObj.__class__)
				logging.error(errMsg)
				return None
			logging.debug("\tRouting Type: %s" %routingObj.__class__)
			flowTSC = routeReach.routeTSC(flowTSC)
		# Break loop if the downstream location is never found
		if count > 500:
			logging.error(endJuncName + " does not exist in routing computations")
			return None				
	return flowTSC

def getDiversionTSC(divElem, rtw, inputTSDataSet):
	'''
	Function to retrieve the flows at a diversion
	Can only handle the following types of diversions
		-Constant
		-Time series
		-Seasonal
	#ALERT! DSS File opening is a bit inefficient here
	@divElem        DiversionElement    The Diversion to get the flows for
	@rtw            RunTimeWindow       The ResSim time window to compute
	@inputTSDataSet TSDataSet           The input time series mapping ("time-series" tab)
	returns:        TimeSeriesContainer Time Series of diversion flows for the whole window
	'''
	lookbackTime = rtw.getLookbackTimeString()
	endTime = rtw.getEndTimeString()
	#Get the diversion type (Rule)
	ctrl = divElem.getController() #hec.rss.model.Controller
	rule = ctrl.getRuleVector()[0] #there is only one rule in a diversion
	network = rule.getSystem()
	#Set up the output TimeSeriesContainer
	#populate the times first--populate the values later
	rts = RunTimeStep(rtw)
	divTSC = TimeSeriesContainer()
	times = []
	#Loop through all time steps, getting the diversion amount
	for step in range(rts.getTotalNumSteps()+1):
		rts.setStep(step)
		#divTime = rts.getHecTime() #problem with daily granularity
		divTime = getHecTimeFromRuntimestep(rts)
		times.append(divTime.value())
	divTSC.times = times
	values = None #to be filled in if necessary--divTSC might get overwritten
	if isinstance(rule, TimeSeries):
		# Diversion is a simple function of an external time series
		logging.debug("\tTime Series Diversion")
		tsrp = rule.getTSRecordProxies()[0] #there is only one time series in a diversion
		tsName = tsrp.getName() #e.g. "New York Irrigation Diversion"
		#Get the input pathname and dss file
		tsRec = inputTSDataSet.getTSRecord(tsName, RssModelVariableConstants.VID_OPRULETS_TSINPUT)
		if tsRec is None:
			errMsg = "No matching Diversion time series found: %s" %tsName
			logging.error(errMsg)
			return None
		path = tsRec.getDSSPathname()
		dssFilename = tsRec.getDSSFilename()
		dssFilename = network.makeAbsolutePathFromWatershed(dssFilename)
		if len(path) == path.count("/") or dssFilename == "": #blank pathname
			errMsg = "\tBlank Pathname--need to map in a diversion pathname at: %s" %divElem
			logging.error(errMsg)
			return None
		else: #should be able to read the timeseries
			#Open the file and add it to the dictionary
			logging.info("Opening Dss File: %s" %dssFilename)
			openedDssFile = DSS.open(dssFilename, lookbackTime, endTime)
			obsDss = openedDssFile
			try:
				tsm = obsDss.read(path)
			except (DSSFileException, HecMathException): # Couldn't find the DSS path
				errMsg =  "ERROR IN READING OBSERVED DATA: COULD NOT READ PATHNAME:"
				errMsg += "\n%s\nFROM DSS FILE: %s\n" %(path, obsDss.getFilename())
				errMsg += "\nProbably need to retrieve/map in the correct observed data"
				logging.error(errMsg)
				return None 
			divTSC = tsm.getData()
	elif isinstance(rule, SpecifiedRelease):
		#Diversion is a seasonal value
		#The public methods in the Java code for seasonal diversions is sorely lacking
		logging.debug("\tSpecifiedRelease Diversion")
		#No direct method to get SeasonalValue object from SpecifiedRelease Rule
		#Have to get it as a string, then convert it back
		seasonVal = SeasonalValue()
		seasonVal.parseString(rule.getReleaseValues())
		#SeasonalValue objects only support interpolation on a RunTimeStep object
		values = []
		#Loop through all time steps, getting the diversion amount
		for step in range(rts.getTotalNumSteps()+1):
			rts.setStep(step)
			divVal = seasonVal.interpolateStepValue(rts) #this is the one
			#divVal = rule.getValue(None, rts, 0)#alternately (looks like RMA doesn't want to maintain this)
			values.append(divVal)
	elif isinstance(rule, ConstantRelease):
		logging.debug("\tConstant Diversion Release")
		divVal = rule.getReleaseValue()
		values = [divVal for i in range(rts.getTotalNumSteps()+1)]
	elif isinstance(rule, MonthlyRelease):
		logging.debug("\tMonthly Diversion Release")
		#MonthlyRelease objects only support interpolation on a RunTimeStep object
		values = []
		#Loop through all time steps, getting the diversion amount
		for step in range(rts.getTotalNumSteps()+1):
			rts.setStep(step)
			divVal = rule.getValue(None, rts, 0) #looks like RMA doesn't want to maintain this
			values.append(divVal)
	elif isinstance(rule, DiversionRule):
		logging.debug("\tCannot handle Flexible Diversion Rules!")
		return None
	else:
		logging.debug("\tUnknown diversion type: %s" %rule.__class__)
		return None
	if values: #if not None, then divTSC wasn't overwritten by another TimeSeriesCont
		#set the values of the time series
		divTSC.values = values
	
	return divTSC

def computeInflowTSC(network, resvName, outflowTSC, elevTSC, minFlow = -9999999, initFlow = None):
	'''
	Function to compute the inflow to a reservoir, given a timeseries of
	known reservoir elevation and known outflows. 
	@network    rssSystem    the network to use stor-elev tables from
	@resvName   string       the exact name of the reservoir (case-sensitive)
	@outflowTSC TimeSeriesContainer  the TSC with reservoir outflows
	@elevTSC    TimeSeriesContainer  the TSC with reservoir elevs
	@minFlow    double       If specified, then calculated inflow will be at least this large
	returns:    TimeSeriesContainter Calculated TSC of reservoir inflow
	'''
	#Check that resv exists
	resvElem = network.findReservoir(resvName)
	if resvElem is None: 
		logging.error("Error: Failed to find the case-sensitive reservoir: %s" %resvName)
		return None
	#Get elev-stor table
	elevStorTable = getElevationStorageTable(resvName, network)
	#Check to see the length of TSC is the same
	if elevTSC.numberValues != outflowTSC.numberValues: 
		logging.error("Error: Reservoir outflows and elevations don't span the same time window")
		return None
	#Find the timeseries interval in seconds
	if outflowTSC.interval <= 0: 
		logging.error("Error: Data must be regular interval!")
		return None #can't handle irregular data
	stepSeconds = outflowTSC.interval*60.       # interval is in minutes
	acFtTocfs = 43560./stepSeconds #conversion factor
	#Loop through all timesteps, calculating the inflow
	outflows = outflowTSC.values
	elevs = elevTSC.values
	stors = [] #list of resv storage corresponding to elevations
	inflows = []
	for i in range(len(elevTSC.times)):
		stors.append(elevStorTable.interpolate(elevs[i]))
		if outflows[i] == Constants.UNDEFINED or elevs[i] == Constants.UNDEFINED:
			logging.error("Error: Undefined value for outflow or elevation at index: %s" %i)
			return None
		if i == 0 :
			if initFlow == None: #no default defined, use the input data
				inflow = outflows[i]
			else: #use the default defined
				inflow = initFlow
		else: #actually compute using mass balance
			inflow = outflows[i] + (stors[i] - stors[i-1])*acFtTocfs
		inflow = max(inflow, minFlow) #cap to a minimum amount if desired
		inflows.append(inflow)
	inflowTSC = outflowTSC.clone() #keep all the metadata consistent
	inflowTSC.fileName = ""
	inflowTSC.values = inflows
	return inflowTSC
	
def recomputeResvInflows(altName, csvFile, outDssFile, tsInt, bar, txtArea):
	'''
	Function to recompute the inflow data for selected reservoirs, using the
	known outflow and elevations (as mapped in the ResSim Observed Data)
	@altName    altName the currently open network
	@param altName    string    The alternative to use to get the time series mapping (e.g "Observed")
	@param csvFile    string    The CSV file that contains which projects to do this for
	@param outDssFile string    Pathname to the desired output file
	@param tsInt      string    Desired output time step (e.g. "1HOUR" or "1DAY")
	@param bar        JProgressBar
	@param txtArea    JTextArea Must have a function defined called "printToGUI"
	'''
	fPart = "Calculated Inflow" #alert!
	msg = "----------------------------------------------------------------------"
	msg += "\nComputing Selected Reservoir Inflows"
	msg += "\nInput CSV File:  %s" %csvFile 
	msg += "\nOutput DSS File: %s\n" %outDssFile
	txtArea.printToGUI(msg)
	logging.info(msg)
	
	#Open up the reservoir network
	simPeriod = getSimulation()
	startTime, endTime, lookbackTime = getResSimTimewindow(simPeriod)
	run = simPeriod.getSimulationRun(altName) #RssSimRun
	if run is None:
		errMsg = "No alternative exists named: %s" %altName
		txtArea.printToGUI(errMsg)
		logging.error(errMsg)
		return None
	alt = run.getRssAlt() #RssAlt
	#tsInt = alt.getTimeStepString() #e.g. 1HOUR, 1DAY
	network = getNetwork(run)
	# Get the locations where observed data is defined (all types)
	obsTSDataSet = alt.getObservedTSDataSet()
	#open output files
	outDss = DSS.open(outDssFile, lookbackTime, endTime)
	######################
	##Process the CSV file
	msg = "Processing file: " + csvFile + "\n"
	logging.info(msg)
	lines = cFile.fileOpenReadClose(csvFile)
	lines = cFile.stripOutCommentLines(lines)
	#Create a dictionary to save all opened DSS files so we don't have to close/reopen
	dssDict = {}
	#OK, now actually process the csv file
	currentTSM = None
	for i in range(len(lines)): 
		fields = lines[i].split(",")
		resvName = fields[0].strip()
		minFlow = fields[1].strip()
		bar.setValue(int(float(i)/len(lines)*100))
		msg = "Processing: %s, MinFlow: %s" %(resvName, minFlow)
		logging.info(msg)
		txtArea.printToGUI(msg)
		try:
			minFlow = float(minFlow)
		except ValueError:
			minFlow = ""
		if minFlow == "": minFlow = -9999999
		################################################
		#Attempt to locate the observed elevation data
		resvElem = network.findReservoir(resvName)
		if resvElem is None:
			errMsg = "No Reservoir in the network named: %s" %resvName
			txtArea.printToGUI(errMsg)
			logging.error(errMsg)
			return None
		#obsVec = resvElem.getObsDataVector() # vector of strings (e.g. "~E2903:F:10")
		#The key value stored in the Observed .fits file is something like "~E2903:F"
		rssConstant = RssModelVariableConstants.VID_POOL_ELEV
		#Get the TSRecord object for the variable
		tsRec = getTSRecord(obsTSDataSet, resvElem, rssConstant, txtArea, isStrict=True, displayMessages=True)
		if tsRec is None:
			errMsg = "\nCouldn't locate observed elevations for: %s" %resvName
			errMsg += "\nMust have Pool Elevation checked in the 'Observed Data'"
			errMsg += "\n tab of the Reservoir Editor"
			txtArea.printToGUI(errMsg)
			logging.error(errMsg)
			return None
		obsPath = tsRec.getDSSPathname() #pathname of observed data
		obsDssFilename = tsRec.getDSSFilename()
		obsDssFilename = network.makeAbsolutePathFromWatershed(obsDssFilename)
		if len(obsPath) == obsPath.count("/") or obsDssFilename == "": #blank pathname
			errMsg = "\tBlank Pathname--need to map in an observed elevation pathname at: %s" %resvName
			txtArea.printToGUI(errMsg)
			logging.error(errMsg)
			return None
		else: #should be able to read the timeseries
			if not dssDict.has_key(obsDssFilename): #open and add to the list
				#Open the file and add it to the dictionary
				logging.info("Opening Dss File: %s" %obsDssFilename)
				openedDssFile = DSS.open(obsDssFilename, lookbackTime, endTime)
				dssDict[obsDssFilename] = openedDssFile
			#Grab the opened DSS file
			obsDss = dssDict[obsDssFilename]
			try:
				obsElevTSM = obsDss.read(obsPath)
			except (DSSFileException, HecMathException): # Couldn't find the DSS path
				errMsg =  "ERROR IN READING OBSERVED DATA: COULD NOT READ PATHNAME:"
				errMsg += "\n%s\nFROM DSS FILE: %s\n" %(obsPath, obsDss.getFilename())
				errMsg += "\nProbably need to retrieve/map in the correct observed data"
				logging.error(errMsg)
				txtArea.printToGUI(errMsg)
				return None 
		#Convert to the alternative timestep (observed data may not be consistent timestep)
		obsElevTSM = cTsUtils.transformTSM(obsElevTSM, tsInt)
		###########################################
		#We now have the elevation time series--now get the outflow time series
		#It should be mapped at the downstream junction
		juncElem = resvElem.getDownstreamNode().getDownstreamElement()
		juncName = str(juncElem)
		logging.debug("Looking for observed outflow at: %s" %juncName)
		#obsVec = juncElem.getObsDataVector() # vector of strings (e.g. "~N36")
		rssConstant = RssModelVariableConstants.VID_NODE_FLOW
		tsRec = getTSRecord(obsTSDataSet, juncElem, rssConstant, txtArea, isStrict=True, displayMessages=True)
		if tsRec is None:
			errMsg = "\nCouldn't locate observed outflows for: %s" %resvName
			errMsg += "\nMust have 'Observed Data' defined at the outflow Junction: %s" %juncName
			txtArea.printToGUI(errMsg)
			logging.error(errMsg)
			return None
		obsPath = tsRec.getDSSPathname() #pathname of observed data
		obsDssFilename = tsRec.getDSSFilename()
		obsDssFilename = network.makeAbsolutePathFromWatershed(obsDssFilename)
		if len(obsPath) == obsPath.count("/") or obsDssFilename == "": #blank pathname
			errMsg = "\tBlank Pathname--need to map in an observed outflow pathname at: %s" %juncName
			txtArea.printToGUI(errMsg)
			logging.error(errMsg)
			return None
		else: #should be able to read the timeseries
			if not dssDict.has_key(obsDssFilename): #open and add to the list
				#Open the file and add it to the dictionary
				logging.info("Opening Dss File: %s" %obsDssFilename)
				openedDssFile = DSS.open(obsDssFilename, lookbackTime, endTime)
				dssDict[obsDssFilename] = openedDssFile
			#Grab the opened DSS file
			obsDss = dssDict[obsDssFilename]
			try:
				obsOutflowTSM = obsDss.read(obsPath)
			except (DSSFileException, HecMathException): # Couldn't find the DSS path
				errMsg =  "ERROR IN READING OBSERVED DATA: COULD NOT READ PATHNAME:"
				errMsg += "\n%s\nFROM DSS FILE: %s\n" %(obsPath, obsDss.getFilename())
				errMsg += "\nProbably need to retrieve/map in the correct observed data"
				logging.error(errMsg)
				txtArea.printToGUI(errMsg)
				return None 
		#Convert to the alternative timestep (observed data may not be consistent timestep)
		obsOutflowTSM = cTsUtils.transformTSM(obsOutflowTSM, tsInt)
		####################################################
		#We have observed elevation and outflow--calculate the inflow
		inflowTSC = computeInflowTSC(network, resvName, obsOutflowTSM.getData(), \
		 obsElevTSM.getData(), minFlow = minFlow, initFlow = None)
		inflowTSM = TimeSeriesMath(inflowTSC)
		bPart = resvName
		cPart = "FLOW-IN"
		#tsInt = DSSPathString(obsOutflowTSM.getPath()).getEPart() #e.g. 1HOUR
		# Set up the output timeseries pathname and write it out
		outputPath = "//%s/%s//%s/%s/" %(bPart, cPart, tsInt, fPart)
		inflowTSM.setPathname(outputPath)
		outDss.write(inflowTSM) 
		msg = "\tOutput path: %s" %outputPath
		logging.info(msg)
		inflowTSM = None
	#Close all DSS Files
	outDss.close()
	for dssFile in dssDict.values(): dssFile.close()
	#Print out final messages
	msg = "\nDONE CALCULATING RESERVOIR INFLOWS!"	
	logging.info(msg)
	txtArea.printToGUI(msg)
	bar.setValue(100)
	return None
	
def computeLocalFlows(network, altName, simDssFile, outDssFile, negs, bar, txtArea):
	'''
	Function to compute the incremental local flows, provided only observed flows
	Will use the pathnames mapped in as "observed flows" to calculate the locals
	Assumes all local flows are mapped to the same input dss file (outDssFile)
	The local flows/observed flows can have variable time intervals (EParts), no problem
	@param network    rssSystem the currently open network
	@param altName    string    The alternative to use to get the time series mapping (e.g "Observed")
	@param simDssfile string    Pathname to simulation.dss
	@param outDssFile string    Pathname to the desired output file
	@param negs       boolean   True if negatives are allowed, false if negatives are not allowed
	@param bar        JProgressBar
	@param txtArea    JTextArea Must have a function defined called "printToGUI"
	'''
	isStrict = False #possibly an input parameter later, whether we need all observed flows mapped in
	msg = "----------------------------------------------------------------------"
	msg += "\nComputing Incremental Local Flows"
	msg += "\nOutput DSS File:                       %s" %outDssFile
	msg += "\nNegative Locals allowed (1 if true)? : %s" %negs
	txtArea.printToGUI("Computing Incremental Local Flows...")
	logging.info(msg)

	confJuncs = getConfluenceJunctions(network)
	confResvDict = getConfluenceResvPoolDict(network)
	confResvs = confResvDict.keys() #pool Element, not ReservoirElement
	hwJuncs = getRealHeadwaterJunctions(network)
	orderedElements = orderElementsFromUpstream(network)
	simPeriod = getSimulation() #SimulationPeriod
	alt = getSpecificRun(simPeriod, altName).getRssAlt() #RssAlt
	tsInt = alt.getTimeStepString() #e.g. 1HOUR, 1DAY
	rtw = simPeriod.getRunTimeWindow()
	startTime, endTime, lookbackTime = getResSimTimewindow(simPeriod)
	# Get the observed data mapping 
	obsTSDataSet = alt.getObservedTSDataSet() #TSDataSet
	# Get the input time series mapping
	inputTSDataSet = alt.getInputTSDataSet() #TSDataSet
		
	#Open up all input DSS Files first--create a dictionary of opened DSS Files
	dssDict = {}
	for tsRec in list(obsTSDataSet.getTSRecords()) + list(inputTSDataSet.getTSRecords()):
		dssFile = tsRec.getDSSFilename()
		dssFile = network.makeAbsolutePathFromWatershed(dssFile)
		if dssFile != "" and dssFile not in dssDict.keys():
			#Open the file and add it to the dictionary
			logging.info("Opening Dss File: %s" %dssFile)
			openedDssFile = DSS.open(dssFile, lookbackTime, endTime)
			dssDict[dssFile] = openedDssFile
	
	#Check out all input time series to make sure they are fully defined
	#Get a "bank" of time series math objects that have been read from DSS--don't have to read twice
	#Need to convert everything into a consistent time interval (alternative timestep)
	#Input data can be mapped as anything (1HOUR, 1DAY, 30MIN)--need to convert
	txtArea.printToGUI("Loading input timeseries...")
	tsBank = tsmBank()
	obsMsg = tsBank.checkInTimeSeries(dssDict, obsTSDataSet, lookbackTime, endTime, 
	 ignoreDssFile = outDssFile, rssConstant = RssModelVariableConstants.VID_NODE_FLOW, tsInt = tsInt)
	stdMsg = tsBank.checkInTimeSeries(dssDict, inputTSDataSet, lookbackTime, endTime, 
	 ignoreDssFile = outDssFile, rssConstant = RssModelVariableConstants.VID_NODE_KNOWNFLOW, tsInt = tsInt)
	if obsMsg != "" or stdMsg != "":
		tsBank.close()
		errMsg = "ERROR: Not all time series are fully defined!"
		errMsg +="\nNeed to go back and check the data"
		if obsMsg != "":
			errMsg +="\nObserved Time Series Mapping problems:"
			errMsg += obsMsg
		if stdMsg != "":
			errMsg +="\nNormal Time Series Mapping problems:"
			errMsg += stdMsg
		logging.error(errMsg)
		txtArea.printToGUI(errMsg)
		return None
	txtArea.printToGUI("All input timeseries look good!")
	#open output files
	simDss = DSS.open(simDssFile, lookbackTime, endTime) 
	outDss = DSS.open(outDssFile, lookbackTime, endTime)
	# dictionary of timeseries containers for tributary regulated flows
	tribFlows = {} #keys are Elements of some sort (e.g. Reach), values are TSCs 
	
	#Proceed through all elements, saving "regTSM" as the current state of the routed flow
	for i in range(len(orderedElements)):
		bar.setValue(int(float(i)/len(orderedElements)*100))
		element = orderedElements[i]
		if element == None: continue
		elemName = str(element)
		nodes = element.getNodeVector()
		if isinstance(element, ReservoirElement):
			pass #do nothing for reservoirs
		if elemName == "Pool": #reservoir pool element
			if element in confResvs:
				# If the junction is a confluence reservoir, add in the flow from upstrm junctions
				logging.debug("\tIt's a confluence reservoir")
				upstreamJunctions = confResvDict[element]
				for juncElem in upstreamJunctions:
					if tribFlows.has_key(juncElem):
						regTSM = regTSM.add(tribFlows[juncElem])  #timewindow previously checked
						logging.debug("added %s" %juncElem)
					else:
						# The upstream junction flow should already exist
						errMsg = "ERROR: At confluence reservoir: %s" %element.getParent()
						errMsg +="\nCouldn't locate input flow time series for Junction: %s" %juncElem
						logging.error(errMsg)
						txtArea.printToGUI(errMsg)
						return None
		if isinstance(element, JunctionElement):
			logging.info("Junction: %s" %elemName)
			divElems = getConnectedDiversions(element)
			if divElems: #there is a diversion, deduct it
				for divElem in divElems:
					logging.info("\tDiversion found: %s" %divElem)
					divTSC = getDiversionTSC(divElem, rtw, inputTSDataSet)
					if divTSC is None:
						errMsg = "\tCouldn't retrieve a time series for Diversion: %s" %divElem
						logging.warning(errMsg)
					else:
						#deduct the diversion
						logging.debug("\tSubtracting diversion flows")
						#Convert to the alternative time step
						divTSM = TimeSeriesMath(divTSC)
						divTSM = cTsUtils.transformTSM(divTSM, tsInt)
						regTSMVals = len(regTSM.getContainer().values)
						divTSC = divTSM.getData()
						'''
						Now that TSM are used instead of TSC, don't need to be as careful with time window
						if regTSMVals != len(divTSC.values):
							errMsg = "\tIncomplete time series defined for diversion: %s" %divElem
							logging.error(regTSMVals)
							logging.error(len(divTSC.values))
							logging.error(errMsg)
							txtArea.printToGUI(errMsg)
							return None
						'''
						regTSM = regTSM.subtract(divTSM)
				divTSC = None
			if element in confJuncs:
				# If the junction is a confluence junction, add in the flow from upstrm reaches	
				logging.debug("\tIt's a confluence junction")
				upstreamReaches = list(getConnectedReaches(element))
				for rch in upstreamReaches:
					if tribFlows.has_key(rch):
						regTSM = regTSM.add(tribFlows[rch])  #timewindow previously checked
						logging.debug("added %s" %rch)
					else:
						# probably the downstream reach, skip it
						logging.debug("%s: Downstream reach" %rch)
						continue
			#########################################################
			#Read observed flow data, if it exists
			# Script ASSUMES THERE IS ONLY ONE OBSERVED DATASET PER LOCATION (total flow)
			obsTSM = None #will get defined if observed data is read
			#obsVec = element.getObsDataVector() # vector of strings (e.g. "~N36:0")
			rssConstant = RssModelVariableConstants.VID_NODE_FLOW
			# get the total observed flow at the junction
			tsRecObs = getTSRecord(obsTSDataSet, element, rssConstant, txtArea, isStrict=True, displayMessages=False)
			logging.debug("\tTSRecord: %s" %tsRecObs)
			if tsRecObs: #the box is checked in the Junction Editor
				obsPath = tsRecObs.getDSSPathname()
				obsDssFilename = tsRecObs.getDSSFilename()
				obsDssFilename = network.makeAbsolutePathFromWatershed(obsDssFilename)
				if len(obsPath) == obsPath.count("/") or obsDssFilename == "": #blank pathname
					msg = "\tBlank Pathname--not using an observed flow TS at: %s" %elemName
					logging.warning(msg)
					txtArea.printToGUI(msg)
					if isStrict: 
						errMsg = "Observed flow is expected, but there is no input pathname at: %s" %elemName
						errMsg += "\nThere must be no blank lines in the 'Observed Data' tab!"
						logging.error(errMsg)
						txtArea.printToGUI(errMsg)
						return None
				else: #should be able to read the timeseries
					#withdraw from the bank instead of reading again
					obsTSM = tsBank.withdrawTS(obsDssFilename, obsPath)
			##########################################################################
			# We have retrieved the observed flow if it exists (obsTSM is None otherwise)
			# Now cycle through the local flows defined 
			# Can handle multiple local flows, but only at locations without observed flows
			#In ResSim, there is a separate node for each local flow
			factor = 1. # default, inflow multiplier factor
			rssConstant = RssModelVariableConstants.VID_NODE_KNOWNFLOW
			for node in nodes: #One local flow per node in ResSim
				# skip downstream elements
				if str(node.getDownstreamElement()) != elemName: continue
				#Local flow nodes have no upstream element
				if node.getUpstreamElement(): continue #must be a connected element, skip it
				logging.debug("\tNode: %s" %node)
				#tsrps = node.getTSRecordProxies() 
				tsrp = node.getTSRecordProxy(RssModelVariableConstants.VID_NODE_KNOWNFLOW)
				if tsrp:
					# The TSRecordProxy corresponds to a local inflow location
					# Retrieve the input pathname of the local flow record so that if
					# we write out the local flow, it will have the right pathname
					logging.debug("\t\tTSRP: %s" %tsrp.getName())
					tsRec = getTSRecord(inputTSDataSet, node, rssConstant, txtArea, isStrict=False, displayMessages=False)
					if not tsRec:
						#It hasn't been properly saved to the network--it doesn't exist, even though it should
						errMsg = "Failed to locate local inflow information for: %s" %tsrp.getName()
						errMsg += "\nMap a fake time series in here, save the time series mapping,"
						errMsg += "\n and then clear out the fake time series. The network just needs"
						errMsg += "\n to be reconfigured at this location"
						logging.error(errMsg)
						txtArea.printToGUI(errMsg)
						return None
					locFlowPath = tsRec.getDSSPathname()
					locFlowTsInt = DSSPathString(locFlowPath).getEPart()
					locFlowDssFilename = tsRec.getDSSFilename()
					locFlowDssFilename = network.makeAbsolutePathFromWatershed(locFlowDssFilename)
					factor = tsrp.getFactor() # local inflow multiplier is attached to the proxy
					if obsTSM: #observed data exists--use it
						# EXPECTING ONLY ONE LOCAL FLOW AT LOCATIONS WITH OBSERVED FLOW, NOT MULTIPLE!!!!
						obsTSM.setType("PER-AVER") #not INST-VAL
						if len(locFlowPath) == locFlowPath.count("/"):
							#blank pathname, just reset flow to observed flow
							msg = "\t\tBlank Local Flow Pathname--not calculating local flow"
							logging.warning(msg)
							txtArea.printToGUI(msg)
							obsTSC = obsTSM.getData()
						elif element in hwJuncs:
							# if the junction is a headwater junction, just write out the observed flow as local
							logging.debug("\t It's a headwater junction")
							# Need to echo the input before we apply the local inflow factor
							# Convert back to the input pathname timestep for writing
							obsTSMToWrite = cTsUtils.transformTSM(obsTSM, locFlowTsInt)
							obsTSCToWrite = obsTSM.getData()
							cTsUtils.writeTSC(obsTSCToWrite, simDss, locFlowPath)
							cTsUtils.writeTSC(obsTSCToWrite, outDss, locFlowPath) #alert! do I want to do this?
							# Now that we've written it out, we can apply inflow factor
							obsTSC = obsTSM.getData()
							obsTSC = obsTSM.multiply(factor).getData()
						else:
							# the junction is not a headwater junction
							# subtract off the routed regulated flow from the observed flow 
							# at this location, and that's your local
							msg = "Local Flow at: %s" %elemName
							txtArea.printToGUI(msg)
							logging.info(msg)
							obsTSC = obsTSM.getData()
							locTSC = obsTSM.subtract(regTSM).getData()
							if not negs: # negative flows not allowed, need to apportion the negative flows
								# Don't write out the negative flows--if the user wants, they can recompute
								'''
								negLocFlowPath = DSSPathString(locFlowPath)
								negLocFlowPath.setFPart(negLocFlowPath.getFPart() + "-WITH_NEGATIVES_ALLOWED")
								cTsUtils.writeTSC(locTSC, outDss, negLocFlowPath.getPathname())
								'''
								locTSC = cTsUtils.removeNegativeLocals(locTSC)
							# Convert back to the input pathname timestep for writing
							locTSM = TimeSeriesMath(locTSC)
							locTSM = cTsUtils.transformTSM(locTSM, locFlowTsInt)
							locTSCToWrite = locTSM.getData()
							cTsUtils.writeTSC(locTSCToWrite, simDss, locFlowPath)
							cTsUtils.writeTSC(locTSCToWrite, outDss, locFlowPath) #alert! do I want to do this?
						regTSM = obsTSM.copy() 
					elif tsRecObs:
						#There is a blank entry for this observed flow location
						#Do not add in any local flow, because all of the local should go downstream!
						logging.info("\t\tNormally there is observed flow at %s, but not mapped in. Not adding local flow" % elemName)
						pass
					else: 
						#There truly is no observed data expected at this location
						#Attempt to add in the local flow from the input dss file, if it exists
						msg = "\t\tNo Observed Data found for %s" %tsrp.getName() 
						logging.info(msg)
						txtArea.printToGUI(msg)
						if len(locFlowPath) == locFlowPath.count("/"): #blank pathname
							msg = "\t\tBlank Local Flow Pathname--not adding local flow"
							logging.warning(msg)
							txtArea.printToGUI(msg)
						else: #should be able to read the timeseries
							#withdraw from the bank instead of reading again
							locFlowTSM = tsBank.withdrawTS(locFlowDssFilename, locFlowPath)
							if locFlowTSM is None: #couldn't find the DSS path
								errMsg =  "ERROR IN READING LOCAL FLOW DATA: COULD NOT READ PATHNAME:"
								errMsg += "\n%s\nFROM DSS FILE: %s\n" %(locFlowPath, locFlowDssFilename)
								errMsg += "\nSince there is no observed flow defined here, assuming this local flow has already been defined"
								logging.error(errMsg)
								txtArea.printToGUI(errMsg)
								return None
							locFlowTSM = locFlowTSM.multiply(factor)
							locFlowTSC = locFlowTSM.getData()
							if element in hwJuncs: #use the data directly
								msg = "\t\tUsing input local flow: %s" %locFlowPath
								regTSM = locFlowTSM.copy()
							else: #add to the existing flows
								msg = "\t\tAdding input local flow to the total flow: %s" %locFlowPath
								regTSM = regTSM.add(locFlowTSM) #timewindow previously checked
							logging.info(msg)
							txtArea.printToGUI(msg)
			#########################################################################
			# If there is an observed flow mapped in at a point, "reset" the regulated flow record
			# This occurs at all points that have observed flow defined (e.g. even those withouta local defined (e.g. outlet of a dam)
			if obsTSM:
				msg = "\tObserved flow exists at %s: Resetting flow..." %elemName
				logging.info(msg)
				txtArea.printToGUI(msg)
				obsTSC = obsTSM.getData()
				print "RYANHELLO"
				print len(obsTSC.values)
				#if element._name == "Fall Creek_OUT":
					#fdsljk.ljkdf = fdsljk.dfs
				regTSM = obsTSM.copy()
		elif isinstance(element, ReachElement):
			# If the element is a reach, route the flow to the next junction
			routingObj = element.getFunction()
			logging.info("Reach : %s" %elemName)
			routeReach = cRouting.buildReach(routingObj)
			if routeReach is None:
				errMsg = "The Script cannot handle any routing methods besides SSARR, Muskingum, ModPuls, or Null:"
				errMsg += "\n%s has routing of: %s" %(elemName, routingObj.__class__)
				logging.error(errMsg)
				txtArea.printToGUI(errMsg)
				return None
			logging.debug("\tRouting Type: %s" %routingObj.__class__)
			regTSC = routeReach.routeTSC(regTSM.getData())
			regTSM = TimeSeriesMath(regTSC)
			
		# Need to check if the next point is a confluence
		# If so, need to save off the time series so the confluence can retrieve it
		dsNode = element.getDownstreamNode()
		dsElem = dsNode.getDownstreamElement()
		if dsElem in confJuncs or dsElem in confResvs:
			logging.debug("Saving to Tributary Flow dictionary: %s" %element)
			# Save the flows to the tribFlows dictionary
			tribFlows[element] = regTSM.copy()			
			# Reset the regTSM variable to 0
			regTSM = regTSM.multiply(0)
	
	tsBank.close()
	#Close all DSS Files
	simDss.close()
	outDss.close()
	for dssFile in dssDict.values(): dssFile.close()
	msg = "\nCompute Complete!"
	txtArea.printToGUI(msg)
	logging.info(msg)
	bar.setValue(100)
	
def exportRASdataToDss(altName, resvFile, juncFile, dShiftFile, outDssFile, useObsData, bar, txtArea, ratingDssFile = None):
	'''
	Function to export data that RAS wants out to an external DSS File
	RAS doesn't want all of the data, just at selected reservoirs and junctions
	For reservoirs, RAS wants one of 2 options:
		1. The forebay elevation (from observed data, not modeled)
		2. The "natural" elevation at the forebay location, assuming the dam isn't there (uses rating curve)
	For junctions, RAS wants the total flow and any local flows
	The FPart needs to be consistent as well, since the idea is to just swap out
	one of these exported DSS files for another one without having to do re-linking in RAS
	@altName       string    The alternative to use to get the output and time series mapping (e.g "Observed")
	@resvFile      string    Pathname to the input text file with list of reservoirs (case-sensitive)
	@juncFile      string    Pathname to the input text file with list of junctions (case-sensitive)
	@dShiftFile    string    Pathname to tab-delimited text file with datum shifts
	@outDssFile    string    Pathname to the desired output file
	@useObsData    Boolean   If true, then "Observed" data will be retrieved when possible
	                                 and converted to the alternative timestep.
	                                 When it doesn't exist, ResSim output is used
	                         If false, then ResSim output is always used
	@bar           JProgressBar
	@txtArea       JTextArea Must have a function defined called "printToGUI"
	@ratingDssFile string    Optional Pathname to dss file with rating curves as paired data
	                         Rating curves at reservoir locations to simulate "natural" conditions
	                         If not supplied, then rating curves will not be applied
	'''
	fPart = "To RAS" #alert, hard coded
	msg = "----------------------------------------------------------------------"
	msg += "\nExporting Data to DSS for RAS"
	msg += "\nOutput DSS File:                       %s" %outDssFile
	msg += "\nAlternative Name:                      %s" %altName
	msg += "\nInput Reservoir List:                  %s" %resvFile
	msg += "\nInput Junction List:                   %s" %juncFile
	msg += "\nInput Datum Shift List:                %s" %dShiftFile
	msg += "\nUsing Observed Data when possible?     %s" %useObsData
	if ratingDssFile:
		msg += "\nRating Curve DSS File:                 %s" %ratingDssFile
	else:
		msg += "\nNot using any external Rating Curves"
	txtArea.printToGUI("Exporting Data to DSS for RAS...")
	logging.info(msg)
	#########################################
	#Open and process the reservoir, junction, and datum shift files
	#Reservoirs
	msg = "Processing file: " + resvFile + "\n"
	logging.info(msg)
	lines = cFile.fileOpenReadClose(resvFile)
	lines = cFile.stripOutCommentLines(lines)
	resvList = [l.strip() for l in lines]
	#Junctions
	msg = "Processing file: " + juncFile + "\n"
	logging.info(msg)
	lines = cFile.fileOpenReadClose(juncFile)
	lines = cFile.stripOutCommentLines(lines)
	juncList = [l.strip() for l in lines]
	#Datum shifts
	#1st field is CBT code, 2nd field is datum shift from 29 to 88, 3rd field is ResSim name
	msg = "Processing file: " + dShiftFile + "\n"
	logging.info(msg)
	lines = cFile.fileOpenReadClose(dShiftFile)
	lines = cFile.stripOutCommentLines(lines)
	dShiftDict = {} #keys are ResSim names, values are datum shifts
	for l in lines:
		fields = l.strip().split("\t")
		elemName = fields[2].strip() #3rd field
		dShiftStr = fields[1].strip() #2nd field
		try:
			dShift = float(dShiftStr)
		except ValueError:
			errMsg = "%s: Could not convert \"%s\" to a number." %(elemName, dShiftStr)
			logging.error(errMsg)
			txtArea.printToGUI(errMsg)
			return None
		dShiftDict[elemName] = dShift
	###################################
	#Open up the alternative information
	simPeriod = getSimulation() #SimulationPeriod
	simDssFile = simPeriod.getOutputDSSFilePath()
	run = getSpecificRun(simPeriod, altName) #RssSimRun
	network = getNetwork(run)
	alt = run.getRssAlt() #RssAlt
	tsInt = alt.getTimeStepString() #e.g. 1HOUR, 1DAY
	startTime, endTime, lookbackTime = getResSimTimewindow(simPeriod)
	#To get regulated output TSDataSet, need to get at the RssRun object (RssAlt doesn't work)
	rssRunName = run.getKey() #e.g. Test-----0
	#Loading this the first time can take a while...
	rssRunObj = getRssRun(rssRunName) 
	
	####################################
	# Before we go too far, check the input text files to make sure all elements exist
	failElems = []
	for resvName in resvList:
		if network.findReservoir(resvName) is None: failElems.append(resvName)
	for juncName in juncList:
		if network.findJunction(juncName) is None: failElems.append(juncName)
	if failElems != []:
		msg += "\nThe following elements specified in the text files do not exist in the model:"
		for failElem in failElems: msg += "\n\t%s" %failElem
		logging.error(msg)
		txtArea.printToGUI(msg)
		return None
	# Before we go too far, check to see datum shifts defined at all locations
	for resvName in resvList:
		if not dShiftDict.has_key(resvName): failElems.append(resvName)
	if failElems != []:
		msg += "\nThe following elements specified in the text files"
		msg += "\ndo not have a datum shift properly defined:"
		for failElem in failElems: msg += "\n\t%s" %failElem
		mgs += "\nThese elements must be present in the datum shifts file (case-sensitive)!"
		logging.error(msg)
		txtArea.printToGUI(msg)
		return None
		#OK, all elements should exist in the model
	#Open output files
	msg = "Opening Dss Files:\n  %s\n  %s" %(simDssFile, outDssFile)
	logging.info(msg)
	simDss = DSS.open(simDssFile, lookbackTime, endTime) 
	outDss = DSS.open(outDssFile, lookbackTime, endTime)
	if ratingDssFile: ratingDss = DSS.open(ratingDssFile)
	barCounter = 0
	barDenom = len(resvList) + len(juncList)
	##################################################################
	#Loop through all reservoirs
	msg = "\nProcessing Reservoirs:"
	txtArea.printToGUI(msg)
	logging.info(msg)
	modeledElevResvs = [] # list to hold reservoirs that we wanted observed data, but used modeled instead
	modeledOutflowResvs = [] # list to hold reservoirs that we wanted observed data, but used modeled instead
	noRatingCurveResvs = [] # list to hold reservoirs that we wanted to use a rating curve, but didn't have one
	for resvName in resvList:
		msg = "  %s" %resvName
		txtArea.printToGUI(msg)
		logging.info(msg)
		bar.setValue(int(float(barCounter)/barDenom*100))
		barCounter += 1
		###################################
		#Start with reservoir outflow
		#Observed flows are actually mapped in at the outflow junction--get it
		element = network.findReservoir(resvName).getDownstreamNode().getDownstreamElement() #e.g. Kerr_OUT
		rssConstant = RssModelVariableConstants.VID_NODE_FLOW
		tsm = getTSMFromSimulationDSS(simDss, element, rssRunObj, rssConstant, txtArea, 
		 useObsData = useObsData, isStrict = False, displayMessages = False)
		if tsm is None and useObsData: 
			#Wanted to get "Observed Data", but it didn't exist
			#Get modeled data instead (but make a note of it)
			tsm = getTSMFromSimulationDSS(simDss, element, rssRunObj, rssConstant, txtArea,
			 useObsData = False, isStrict = True, displayMessages = True)
			modeledOutflowResvs.append(element._name)
		if tsm is None: #failed to retrieve the data
			errMsg = "Failed to retrieve data at: %s" %element
			errMsg = "\nSee the log file for more details"
			txtArea.printToGUI(errMsg)
			logging.error(errMsg)
			return None
		#Convert to the alternative timestep (observed data may not be consistent timestep)
		tsm = cTsUtils.transformTSM(tsm, tsInt)
		path = tsm.getPath()
		tsc = tsm.getData()
		outPath = DSSPathString(path)
		outPath.setBPart(element._name)
		outPath.setCPart("FLOW")
		outPath.setFPart(fPart)
		cTsUtils.writeTSC(tsc, outDss, outPath.getPathname())
		#Save a copy for later use if necessary--(rating curve interpolation)
		outflowTSM = tsm.copy()
		#######################################
		#Done with reservoir outflow--move to pool elevations
		element = network.findReservoir(resvName)
		rssConstant = RssModelVariableConstants.VID_POOL_ELEV
		ratingTbl = None
		if ratingDssFile:
			#Want to use rating curves
			#Try to get the rating curve as a table
			#If it fails, it will return None and modeled elevations will be used (with a note of it)
			ratingPath = "//%s/FLOW-ELEV//NAVD88/NATURAL/" %resvName
			ratingTbl = cTsUtils.readPairedDataFromDSS(ratingPath, ratingDss)
			#Don't apply the natural rating curve for natural lakes--use the modeled data
			if resvName in naturalLakes:
				ratingTbl = None
			#if no rating table is being used, save it to the "naughty" list
			if ratingTbl is None: noRatingCurveResvs.append(element._name)
		if ratingTbl: #a rating table is defined--use it
			#Apply the rating curve to the previously retrieved outflow data
			#Outflow is okay to use because typically in these runs, inflow=outflow
			#  and the rating curves are defined right at the dam location
			tsm = outflowTSM.copy()
			tsm.setUnits("ft")
			tsm.setType("INST-VAL")
			tsc = tsm.getData()
			tsc.values = [ratingTbl.interpolate(v) for v in tsc.values]
			tsm.setData(tsc)
		else:
			#Don't use rating curves, use modeled data
			#retrieve the time series
			tsm = getTSMFromSimulationDSS(simDss, element, rssRunObj, rssConstant, txtArea,
			 useObsData = useObsData, isStrict = False, displayMessages = False)
			if tsm is None and useObsData: 
				#Wanted to get "Observed Data", but it didn't exist
				#Get modeled data instead (but make a note of it)
				#Check to see if forebay headloss is defined. If it is defined, don't want
				# the "pool" elevations--we want the "forebay" after headloss deducted
				#The headloss must belong to the dam itself, not to a powerplant within the dam
				#Assumes that if observed data is defined at these locations, it is mapped to forebay, not pool
				# so no transformation is appropriate to the observed data
				#This is how to get at the forebay head loss if it is attached to the dam itself
				#Not sure how to access it if it is attached to the powerplant in the dam... (tried lots of things)
				resvDamElem = element.getElementsByClass(ReservoirDamElement, None)[0] # vector of # hec.rss.model.ReservoirDamElement
				fbHeadLoss = resvDamElem.getForebayHeadLoss() # hec.rss.model.ForebayHeadLoss
				if fbHeadLoss: #there is forebay head loss defined
					fbTs = fbHeadLoss.getTSRecordProxy(143) #Forebay (after headloss deducted from pool)
					hlTs = fbHeadLoss.getTSRecordProxy(144) #Headloss (ft)
					fbTsName = fbTs.getName() #e.g. Albeni Falls-Dam at Pend Oreille River-FOREBAY
					fbTsVarID = fbTs.getVariableId()
					#tsRec = getTSRecord(tsDataSetObj, fbHeadLoss, 143, txtArea, isStrict = True, displayMessages=True)
					tsm = getTSMFromSimulationDSS(simDss, fbHeadLoss, rssRunObj, fbTsVarID, txtArea, 
					 useObsData = False, isStrict = True, displayMessages = True)
				else: #no forebay headloss, just get pool elev
					tsm = getTSMFromSimulationDSS(simDss, element, rssRunObj, rssConstant, txtArea,
					 useObsData = False, isStrict = True, displayMessages = True)
				modeledElevResvs.append(element._name)
			if tsm is None: #failed to retrieve the data
				errMsg = "Failed to retrieve data at: %s" %element
				errMsg = "\nSee the log file for more details"
				txtArea.printToGUI(errMsg)
				logging.error(errMsg)
				return None
			path = tsm.getPath()
			#Add in the datum shift
			dShift = dShiftDict[resvName]
			tsm = tsm.add(dShift)
		#Convert to the alternative timestep (observed data may not be consistent timestep)
		tsm = cTsUtils.transformTSM(tsm, tsInt)
		tsc = tsm.getData()
		outPath = DSSPathString(path)
		outPath.setBPart(resvName)
		outPath.setCPart("ELEV-FOREBAY-NAVD88")
		outPath.setFPart(fPart)
		cTsUtils.writeTSC(tsc, outDss, outPath.getPathname())
		####################################
		#Alert! Special Logic for Corra Linn (Queens Bay)
		#The downstream boundary condition of the RAS model is a time series
		#that is the Queens Bay elevation plus a half a foot
		#The Queens Bay elevation is equivalent to the ResSim pool
		if element._name == "Corra Linn":
			msg = "     Adding a half foot to Corra Linn pool and saving as Queens Bay+0.5"
			txtArea.printToGUI(msg)
			logging.info(msg)
			tsm = tsm.add(0.5) #half a foot
			outPath.setBPart("Queens Bay+0.5")
			outPath.setCPart("ELEV-NAVD88")
			tsc = tsm.getData()
			cTsUtils.writeTSC(tsc, outDss, outPath.getPathname())
	########################################################################
	#Done with reservoirs, move to junctions
	#Need to write out any local flows at the junction, as well as total flow
	msg = "\nProcessing Junctions:"
	txtArea.printToGUI(msg)
	logging.info(msg)
	modeledFlowJuncs = [] # list to hold Junctions that we wanted observed data, but used modeled instead
	for juncName in juncList:
		msg = "  %s" %juncName
		txtArea.printToGUI(msg)
		logging.info(msg)
		bar.setValue(int(float(barCounter)/barDenom*100))
		barCounter += 1
		element = network.findJunction(juncName)
		############################
		#Write out all local flows associated with this junction
		#locFlows = element.getLocalFlowTimeSeries() #doesn't work
		nodes = element.getNodeVector()
		for node in nodes: #One local flow per node in ResSim
			#Local flow nodes have no upstream element
			if node.getUpstreamElement(): continue #must be a connected element, skip it
			logging.debug("\tNode: %s" %node)
			rssConstant = RssModelVariableConstants.VID_NODE_FLOW
			#Local flows aren't typically given the observed data check-box
			#Don't retrieve true "Observed Data", just get the local flow time series
			#Output local flows are stored to the node as FLOW, not KNOWNFLOW
			#They will always have the same timestep as the alternative
			tsm = getTSMFromSimulationDSS(simDss, node, rssRunObj, rssConstant, txtArea, 
			 useObsData = False, isStrict = True, displayMessages = True)
			if tsm is None: #failed to retrieve the data
				errMsg = "Failed to retrieve data at: %s" %element
				errMsg = "\nSee the log file for more details"
				txtArea.printToGUI(errMsg)
				logging.error(errMsg)
				return None
			path = tsm.getPath()
			tsc = tsm.getData()
			outPath = DSSPathString(path)
			#Check to make sure the local flow is spit out in a nice form for RAS
			#In later versions of ResSim 3.2.1197 at least, when a new local flow is created,
			#the default is to name it "%s %s" %(junctionName, localFlowName)
			#But we just want to print out the localFlowName, not the junctionName too
			bPart = outPath.getBPart()
			badBpart = "%s %s" %(juncName, juncName)
			if bPart.upper().startswith(badBpart.upper()):
				#replace the b part with just the local flow name
				bPart = bPart[len(juncName)+1:] #get it to "xx FLOW-LOC"
				outPath.setBPart(bPart)
			#ResSim outputs all local flows as just "FLOW"
			#outPath.setCPart("FLOW-LOC") 
			outPath.setFPart(fPart)
			cTsUtils.writeTSC(tsc, outDss, outPath.getPathname())
		############################
		#Write out the total flow at this junction
		rssConstant = RssModelVariableConstants.VID_NODE_FLOW
		#suppress messages out to the txtArea, since many locations will not have obsData
		tsm = getTSMFromSimulationDSS(simDss, element, rssRunObj, rssConstant, txtArea,
		 useObsData = useObsData, isStrict = True, displayMessages = False)
		if tsm is None and useObsData: 
			#Wanted to get "Observed Data", but it didn't exist
			#Get modeled data instead (but make a note of it)
			tsm = getTSMFromSimulationDSS(simDss, element, rssRunObj, rssConstant, txtArea,
			 useObsData = False, isStrict = True, displayMessages = True)
			modeledFlowJuncs.append(element._name)
		if tsm is None: #failed to retrieve the data
			errMsg = "Failed to retrieve data at: %s" %element
			errMsg = "\nSee the log file for more details"
			txtArea.printToGUI(errMsg)
			logging.error(errMsg)
			return None
		#Convert to the alternative timestep (observed data may not be consistent timestep)
		tsm = cTsUtils.transformTSM(tsm, tsInt)
		path = tsm.getPath()
		tsc = tsm.getData()
		outPath = DSSPathString(path)
		outPath.setAPart("")
		outPath.setBPart(element._name)
		outPath.setCPart("FLOW")
		outPath.setFPart(fPart)
		cTsUtils.writeTSC(tsc, outDss, outPath.getPathname())
		#############################
		#Write out the observed elevation at this junction if it exists
		#e.g. Mouth of Columbia River input elevation data may be finer than timestep
		rssConstant = RssModelVariableConstants.VID_JUNC_ELEV
		#suppress messages out to the txtArea, since many locations will not have obsData
		tsm = getTSMFromSimulationDSS(simDss, element, rssRunObj, rssConstant, txtArea,
		 useObsData = True, isStrict = False, displayMessages = False)
		if tsm: 
			#Observed data exists! Write it out
			msg = "     Echoing observed elevation data"
			txtArea.printToGUI(msg)
			logging.info(msg)
			path = tsm.getPath()
			tsc = tsm.getData()
			outPath = DSSPathString(path)
			outPath.setAPart("")
			outPath.setBPart(element._name)
			outPath.setFPart(fPart)
			cTsUtils.writeTSC(tsc, outDss, outPath.getPathname())
	#Close all DSS Files
	simDss.close()
	outDss.close()
	msg = "\nCompute Complete!"
	txtArea.printToGUI(msg)
	logging.info(msg)
	bar.setValue(100)
	#Print out any warning messages
	msg = ""
	if len(modeledElevResvs) > 0 and useObsData:
		msg += "\nUsed modeled elevation data (not actual observed data) for:"
		for resv in modeledElevResvs: msg += "\n\t%s" %resv
	if len(noRatingCurveResvs) > 0:
		msg += "\nUsed modeled elevation data (not 'natural' rating curve) for:"
		for resv in noRatingCurveResvs: msg += "\n\t%s" %resv
	if len(modeledOutflowResvs) > 0 and useObsData:
		msg += "\nUsed modeled outflow data (not actual observed data) for:"
		for resv in modeledOutflowResvs: msg += "\n\t%s" %resv
	if len(modeledFlowJuncs) > 0 and useObsData:
		msg += "\nUsed modeled flow data (not actual observed data) for:"
		for junc in modeledFlowJuncs: msg += "\n\t%s" %junc
	logging.warning(msg)
	txtArea.printToGUI(msg)
	
def createVerfPlots (obsAltName, unrAltName, resvFile, juncFile, bar, txtArea) :
	'''
	John McCoskery
	Method to create plots in JPEG format for model review and verification.  Plots
	will contain data for "observed-observed", "modeled-observed", and unregulated
	conditions w/in the model.  Reservoirs will plot ELEV, FLOW-IN, and FLOW-OUT.
	Junctions will plot FLOW.  
	
	All reservoirs and junctions are defined in input files, resvFile and juncFile.
	If a reservoir or junction element is not defined in network, then a note is created
	in the log file and the element is skipped.
	
	@obsAltName		String		Name of "observed" alternative
	@unrAltName		String		Name of unregulated alternative
	@resvFile		String		Pathname to input text file containing list of reservoirs
	@juncFile		String		Pathname to input text file containing list of junctions
	
	@bar			JProgressBar
	@txtArea		JTextArea
	'''
	msg =  "----------------------------------------------------------------------"
	msg += "\nCreating Verification Plots."
	msg += "\nModeled-Observed Alternative Name 			%s" %obsAltName
	msg += "\nModeled-Unregulated Alternative Name			%s" %unrAltName
	msg += "\nInput Reservoir List							%s" %resvFile
	msg += "\nInput Junction List							%s" %juncFile
	msg += "\n----------------------------------------------------------------------\n"
	
	txtArea.printToGUI("Creating Verification Plots...")
	logging.info(msg)
	
	#Open and process the reservoir and junction lists
	#Reservoirs
	msg = "Processing file: " + resvFile + "\n"
	logging.info(msg)
	lines = cFile.fileOpenReadClose(resvFile)
	lines = cFile.stripOutCommentLines(lines)
	resvList = [l.strip() for l in lines]
	#Junctions
	msg = "Processing file: " + juncFile + "\n"
	logging.info(msg)
	lines = cFile.fileOpenReadClose(juncFile)
	lines = cFile.stripOutCommentLines(lines)
	juncList = [l.strip() for l in lines]
	
	# get simulation information
	simPeriod = getSimulation()
	startTime, EndTime, LookbackTime = getResSimTimewindow(simPeriod)	# run times
	simDssFile = simPeriod.getOutputDSSFilePath()						# DSS filename
	# 
	obsRun = getSpecificRun(simPeriod, obsAltName)
	obsAlt = obsRun.getRssAlt()
	obsRssRunName = obsRun.getKey()
	obsRunObj = getRssRun(obsRssRunName)
	# 
	unrRun = getSpecificRun(simPeriod, unrAltName)
	unrAlt = unrRun.getRssAlt()
	unrRssRunName = unrRun.getKey()
	unrRunObj = getRssRun(unrRssRunName)
	#
	network = getNetwork(obsRun)										# same network for both Alts??
	
	# open simulation DSS file
	msg = "\nOpening DSS File:\n    %s\n" %simDssFile
	logging.info(msg)
	simDSS = DSS.open(simDssFile, LookbackTime, EndTime)
	
	barCounter = 0
	barDenom = len(resvList) + len(juncList)
	
	# loop through reservoirs and build plots
	for rn in resvList :
		msg = "\nCreating Reservoir Plot\n%s" % rn.upper()
		txtArea.printToGUI(msg)
		logging.info(msg)
		
		bar.setValue(int(float(barCounter) / barDenom*100))
		barCounter += 1
		
		# verify that reservoir exists in network
		if network.findReservoir(rn) is None :
			msg = "WARNING reservoir does not exist in network."
			logging.info(msg)
			txtArea.printToGUI(msg)
			continue													# if reservoir not in network, go to next item in list
			
		# use modeled-observed alternative to get real-observed data
		# flow-IN
		element = network.findReservoir(rn).getUpstreamNode().getUpstreamElement()
		rssConstant = RssModelVariableConstants.VID_NODE_FLOW
		obsFlowIN = getTSMFromSimulationDSS(simDSS, element, obsRunObj, rssConstant, txtArea, 
			useObsData = True, isStrict = False, displayMessages = False)
		if obsFlowIN is None :
			msg = "Observed FLOW-IN timeseries not found."
			logging.info(msg)
			txtArea.printToGUI(msg)
		else :
			msg = "Observed FLOW-IN:             %s" %obsFlowIN.getPath()
			logging.info(msg)
		# flow-OUT
		element = network.findReservoir(rn).getDownstreamNode().getDownstreamElement()
		rssConstant = RssModelVariableConstants.VID_NODE_FLOW
		obsFlowOUT = getTSMFromSimulationDSS(simDSS, element, obsRunObj, rssConstant, txtArea, 
			useObsData = True, isStrict = False, displayMessages = False)
		if obsFlowOUT is None :
			msg = "Observed FLOW-OUT timeseries not found."
			logging.info(msg)
			txtArea.printToGUI(msg)
		else :
			msg = "Observed FLOW-OUT:            %s" %obsFlowOUT.getPath()
			logging.info(msg)
		# Elev
		element = network.findReservoir(rn)
		rssConstant = RssModelVariableConstants.VID_POOL_ELEV
		obsELEV = getTSMFromSimulationDSS(simDSS, element, obsRunObj, rssConstant, txtArea, 
			useObsData = True, isStrict = False, displayMessages = False)
		if obsELEV is None :
			msg = "Observed ELEV timeseries not found."
			logging.info(msg)
			txtArea.printToGUI(msg)
		else :
			msg = "Observed ELEV:                %s" %obsELEV.getPath()
			logging.info(msg)
		# now get "modeled"-observed data
		# flow-IN
		element = network.findReservoir(rn).getUpstreamNode().getUpstreamElement()
		rssConstant = RssModelVariableConstants.VID_NODE_FLOW
		mObsFlowIN = getTSMFromSimulationDSS(simDSS, element, obsRunObj, rssConstant, txtArea, 
			useObsData = False, isStrict = True, displayMessages = True)
		if mObsFlowIN is None :
			msg = "Modeled-Observed FLOW-IN timeseries not found."
			logging.info(msg)
			txtArea.printToGUI(msg)
		else :
			msg = "Modeled-Observed FLOW-IN:     %s" %mObsFlowIN.getPath()
			logging.info(msg)
		# flow-OUT
		element = network.findReservoir(rn).getDownstreamNode().getDownstreamElement()
		rssConstant = RssModelVariableConstants.VID_NODE_FLOW
		mObsFlowOUT = getTSMFromSimulationDSS(simDSS, element, obsRunObj, rssConstant, txtArea, 
			useObsData = False, isStrict = True, displayMessages = True)
		if mObsFlowOUT is None :
			msg = "Modeled-Observed FLOW-OUT timeseries not found."
			logging.info(msg)
			txtArea.printToGUI(msg)
		else :
			msg = "Modeled-Observed FLOW-OUT:    %s" %mObsFlowOUT.getPath()
			logging.info(msg)
		# Elev
		element = network.findReservoir(rn)
		rssConstant = RssModelVariableConstants.VID_POOL_ELEV
		mObsELEV = getTSMFromSimulationDSS(simDSS, element, obsRunObj, rssConstant, txtArea, 
			useObsData = False, isStrict = True, displayMessages = True)
		if mObsELEV is None :
			msg = "Modeled-Observed ELEV timeseries not found."
			logging.info(msg)
			txtArea.printToGUI(msg)
		else :
			msg = "Modeled-Observed ELEV:        %s" %mObsELEV.getPath()
			logging.info(msg)
		# now get "modeled"-unregulated data
		# flow-IN
		element = network.findReservoir(rn).getUpstreamNode().getUpstreamElement()
		rssConstant = RssModelVariableConstants.VID_NODE_FLOW
		mUnrFlowIN = getTSMFromSimulationDSS(simDSS, element, unrRunObj, rssConstant, txtArea, 
			useObsData = False, isStrict = True, displayMessages = True)
		if mUnrFlowIN is None :
			msg = "Modeled-Unregulated FLOW-IN timeseries not found."
			logging.info(msg)
			txtArea.printToGUI(msg)
		else :
			msg = "Modeled-Unregulated FLOW-IN:  %s" %mUnrFlowIN.getPath()
			logging.info(msg)
		# flow-OUT
		element = network.findReservoir(rn).getDownstreamNode().getDownstreamElement()
		rssConstant = RssModelVariableConstants.VID_NODE_FLOW
		mUnrFlowOUT = getTSMFromSimulationDSS(simDSS, element, unrRunObj, rssConstant, txtArea, 
			useObsData = False, isStrict = True, displayMessages = True)
		if mUnrFlowOUT is None :
			msg = "Modeled-Unregulated FLOW-OUT timeseries not found."
			logging.info(msg)
			txtArea.printToGUI(msg)
		else :
			msg = "Modeled-Unregualted FLOW-OUT: %s" %mUnrFlowOUT.getPath()
			logging.info(msg)
		# Elev
		element = network.findReservoir(rn)
		rssConstant = RssModelVariableConstants.VID_POOL_ELEV
		mUnrELEV = getTSMFromSimulationDSS(simDSS, element, unrRunObj, rssConstant, txtArea, 
			useObsData = False, isStrict = True, displayMessages = True)
		if mUnrELEV is None :
			msg = "Modeled-Unregulated ELEV timeseries not found."
			logging.info(msg)
			txtArea.printToGUI(msg)
		else :
			msg = "Modeled-Unregulated ELEV:     %s" %mUnrELEV.getPath()
			logging.info(msg)
		# build plot object; elevations in top view, flows in bottom view
		plot = Plot.newPlot()
		layout = Plot.newPlotLayout()
		topview = layout.addViewport(50)						# top view for elevations
		botview = layout.addViewport(50)						# bottom view for flows
		# add elevation data
		#if a timeseries is None it just will not show up on plot
		# pass in timeseries at TimeSeriesContaienr.
		try :
			topview.addCurve("Y1", obsELEV.getData())
		except :
			topview.addCurve("Y1", None)
		try :
			topview.addCurve("Y1", mObsELEV.getData())
		except :
			topview.addCurve("Y1", None)
		try :
			topview.addCurve("Y1", mUnrELEV.getData())
		except :
			topview.addCurve("Y1", None)
		# add flow data
		try :
			botview.addCurve("Y1", obsFlowIN.getData())
		except :
			botview.addCurve("Y1", None)
		try :
			botview.addCurve("Y1", mObsFlowIN.getData())
		except :
			botview.addCurve("Y1", None)
		try :
			botview.addCurve("Y1", mUnrFlowIN.getData())
		except :
			botview.addCurve("Y1", None)
		try :
			botview.addCurve("Y1", obsFlowOUT.getData())
		except :
			botview.addCurve("Y1", None)
		try :
			botview.addCurve("Y1", mObsFlowOUT.getData())
		except :
			botview.addCurve("Y1", None)
		try :
			botview.addCurve("Y1", mUnrFlowOUT.getData())
		except :
			botview.addCurve("Y1", None)
		# build plot and show - need to "show" in order to adjust things...
		plot.configurePlotLayout(layout)
		plot.showPlot()
		# make adjustments to viewport 1 
		vp = plot.getViewport(0)
		vp.setMinorGridXVisible(Constants.TRUE)
		vp.setDrawMinorXGridOn()
		vp.setBorderColor("gray")
		# change colors for obsELEV TSC
		try :
			plot.getCurve(obsELEV).setLineColor("black")
			plot.getCurve(obsELEV).setLineStyle("Solid")
			plot.getCurve(obsELEV).setLineStepStyle("linear")
			plot.getCurve(obsELEV).setLineWidth(1.0)
			plot.setLegendLabelText(obsELEV.getData(), "Obsv-HF")
		except :
			msg = "WARNING could not complete Obs-ELEV formatting."
			logging.info(msg)
			txtArea.printToGUI(msg)
		# change colors for mObsELEV TSC
		try :
			plot.getCurve(mObsELEV).setLineColor("darkgreen")
			plot.getCurve(mObsELEV).setLineStyle("Dash")
			plot.getCurve(mObsELEV).setLineStepStyle("linear")
			plot.getCurve(mObsELEV).setLineWidth(2.)
			plot.setLegendLabelText(mObsELEV.getData(), "Mod-HF")
		except :
			msg = "WARNING could not complete Mod-Obs-ELEV formatting."
			logging.info(msg)
			txtArea.printToGUI(msg)
		# change colors for mUnrELEV TSC
		try :
			plot.getCurve(mUnrELEV).setLineColor("darkgreen")
			plot.getCurve(mUnrELEV).setLineStyle("Dash")
			plot.getCurve(mUnrELEV).setLineStepStyle("linear")
			plot.getCurve(mUnrELEV).setLineWidth(2.)
			plot.setLegendLabelText(mUnrELEV.getData(), "Unreg-HF")
		except :
			msg = "WARNING could not complete Unreg-ELEV formatting."
			logging.info(msg)
			txtArea.printToGUI(msg)			
		# make adjustments to viewport 1 
		vp = plot.getViewport(1)
		vp.setMinorGridXVisible(Constants.TRUE)
		vp.setDrawMinorXGridOn()
		vp.setBorderColor("gray")
		# change colors for obsFlowIN TSC
		if not obsFlowIN is None :
			plot.getCurve(obsFlowIN).setLineColor("black")
			plot.getCurve(obsFlowIN).setLineStyle("Solid")
			plot.getCurve(obsFlowIN).setLineStepStyle("step")
			plot.getCurve(obsFlowIN).setLineWidth(1.0)
			plot.setLegendLabelText(obsFlowIN.getData(), "Obsv-QI")
		else :
			msg = "WARNING could not complete Obs-FlowIN formatting."
			logging.info(msg)
			txtArea.printToGUI(msg)			
		# change colors for mObsFlowIN TSC
		if not mObsFlowIN is None :
			plot.getCurve(mObsFlowIN).setLineColor("red")
			plot.getCurve(mObsFlowIN).setLineStyle("Dash")
			plot.getCurve(mObsFlowIN).setLineStepStyle("step")
			plot.getCurve(mObsFlowIN).setLineWidth(2.)
			plot.setLegendLabelText(mObsFlowIN.getData(), "Mod-QI")
		else :
			msg = "WARNING could not complete Mod-Obs-FlowIN formatting."
			logging.info(msg)
			txtArea.printToGUI(msg)			
		# change colors for mUnrFlowIN TSC
		if not mUnrFlowIN is None :
			plot.getCurve(mUnrFlowIN).setLineColor("darkred")
			plot.getCurve(mUnrFlowIN).setLineStyle("Dash")
			plot.getCurve(mUnrFlowIN).setLineStepStyle("step")
			plot.getCurve(mUnrFlowIN).setLineWidth(2.)
			plot.setLegendLabelText(mUnrFlowIN.getData(), "Unreg-QI")
		else :
			msg = "WARNING could not complete Unreg-FlowIN formatting."
			logging.info(msg)
			txtArea.printToGUI(msg)			
		# change colors for obsFlowOUT TSC
		if not obsFlowOUT is None :
			plot.getCurve(obsFlowOUT).setLineColor("black")
			plot.getCurve(obsFlowOUT).setLineStyle("Solid")
			plot.getCurve(obsFlowOUT).setLineStepStyle("step")
			plot.getCurve(obsFlowOUT).setLineWidth(1.0)
			plot.setLegendLabelText(obsFlowOUT.getData(), "Obsv-QR")
		else :
			msg = "WARNING could not complete Obs-FlowOUT formatting."
			logging.info(msg)
			txtArea.printToGUI(msg)			
		# change colors for mObsFlowOUT TSC
		if not mObsFlowOUT is None :
			plot.getCurve(mObsFlowOUT).setLineColor("blue")
			plot.getCurve(mObsFlowOUT).setLineStyle("Dash")
			plot.getCurve(mObsFlowOUT).setLineStepStyle("step")
			plot.getCurve(mObsFlowOUT).setLineWidth(2.)
			plot.setLegendLabelText(mObsFlowOUT.getData(), "Mod-QR")
		else :
			msg = "WARNING could not complete Mod-Obs-FlowOUT formatting."
			logging.info(msg)
			txtArea.printToGUI(msg)			
		# change colors for mUnrFlowOUT TSC
		if not mUnrFlowOUT is None :
			plot.getCurve(mUnrFlowOUT).setLineColor("darkblue")
			plot.getCurve(mUnrFlowOUT).setLineStyle("Dash")
			plot.getCurve(mUnrFlowOUT).setLineStepStyle("step")
			plot.getCurve(mUnrFlowOUT).setLineWidth(2.)
			plot.setLegendLabelText(mUnrFlowOUT.getData(), "Unreg-QR")
		else :
			msg = "WARNING could not complete Unreg-FlowOUT formatting."
			logging.info(msg)
			txtArea.printToGUI(msg)			
		
		# save plot to JPEG file
		pltFile = ClientApp.Workspace().makeAbsolutePath("shared/Plots/Reservoirs/%s.png" %rn)
		cFile.ensure_dir(pltFile)
		plot.setSize(1600, 1040)
		plot.saveToPng(pltFile)
		plot.close()
	# loop through junctions and build plots
	for jn in juncList :
		msg = "\nCreating Junction Plot\n%s" % jn.upper()
		txtArea.printToGUI(msg)
		logging.info(msg)
		
		bar.setValue(int(float(barCounter) / barDenom*100))
		barCounter += 1
		
		# verify that junction exists in network
		if network.findJunction(jn) is None :
			msg = "WARNING junction does not exist in network."
			logging.info(msg)
			txtArea.printToGUI(msg)
			continue													# if junction not in network, go to next item in list
			
		# use modeled-observed alternative to get real-observed data
		# flow
		element = network.findJunction(jn)
		rssConstant = RssModelVariableConstants.VID_NODE_FLOW
		obsFlow = getTSMFromSimulationDSS(simDSS, element, obsRunObj, rssConstant, txtArea, 
			useObsData = True, isStrict = False, displayMessages = False)
		if obsFlow is None :
			msg = "Observed FLOW timeseries not found."
			logging.info(msg)
			txtArea.printToGUI(msg)
		else :
			msg = "Observed FLOW:                %s" %obsFlow.getPath()
			logging.info(msg)
		# now get "modeled"-observed data
		# flow-IN
		rssConstant = RssModelVariableConstants.VID_NODE_FLOW
		mObsFlow = getTSMFromSimulationDSS(simDSS, element, obsRunObj, rssConstant, txtArea, 
			useObsData = False, isStrict = True, displayMessages = True)
		if mObsFlow is None :
			msg = "Modeled-Observed FLOW timeseries not found."
			logging.info(msg)
			txtArea.printToGUI(msg)
		else :
			msg = "Modeled-Observed FLOW:        %s" %mObsFlow.getPath()
			logging.info(msg)
		# now get "modeled"-unregulated data
		# flow
		rssConstant = RssModelVariableConstants.VID_NODE_FLOW
		mUnrFlow = getTSMFromSimulationDSS(simDSS, element, unrRunObj, rssConstant, txtArea, 
			useObsData = False, isStrict = True, displayMessages = True)
		if mUnrFlow is None :
			msg = "Modeled-Unregulated FLOW timeseries not found."
			logging.info(msg)
			txtArea.printToGUI(msg)
		else :
			msg = "Modeled-Unregulated FLOW:     %s" %mUnrFlow.getPath()
			logging.info(msg)
		# build plot object; elevations in top view, flows in bottom view
		plot = Plot.newPlot()
		layout = Plot.newPlotLayout()
		topview = layout.addViewport(50)						# top view for elevations
		# add elevation data
		#if a timeseries is None it just will not show up on plot
		# pass in timeseries at TimeSeriesContaienr.
		try :
			topview.addCurve("Y1", obsFlow.getData())
		except :
			topview.addCurve("Y1", None)
		try :
			topview.addCurve("Y1", mObsFlow.getData())
		except :
			topview.addCurve("Y1", None)
		try :
			topview.addCurve("Y1", mUnrFlow.getData())
		except :
			topview.addCurve("Y1", None)
		# build plot and show - need to "show" in order to adjust things...
		plot.configurePlotLayout(layout)
		plot.showPlot()
		# make adjustments to viewport 1 
		vp = plot.getViewport(0)
		vp.setMinorGridXVisible(Constants.TRUE)
		vp.setDrawMinorXGridOn()
		vp.setBorderColor("gray")
		# change colors for obsFlow TSC
		try :
			plot.getCurve(obsFlow).setLineColor("black")
			plot.getCurve(obsFlow).setLineStyle("Solid")
			plot.getCurve(obsFlow).setLineStepStyle("linear")
			plot.getCurve(obsFlow).setLineWidth(1.0)
			plot.setLegendLabelText(obsFlow.getData(), "Obsv-QR")
		except :
			msg = "WARNING could not complete Obs-Flow formatting."
			logging.info(msg)
			txtArea.printToGUI(msg)
		# change colors for mObsFlow TSC
		try :
			plot.getCurve(mObsFlow).setLineColor("red")
			plot.getCurve(mObsFlow).setLineStyle("Dash")
			plot.getCurve(mObsFlow).setLineStepStyle("linear")
			plot.getCurve(mObsFlow).setLineWidth(2.)
			plot.setLegendLabelText(mObsFlow.getData(), "Mod-QR")
		except :
			msg = "WARNING could not complete Mod-Obs-Flow formatting."
			logging.info(msg)
			txtArea.printToGUI(msg)
		# change colors for mUnrFlow TSC
		try :
			plot.getCurve(mUnrFlow).setLineColor("blue")
			plot.getCurve(mUnrFlow).setLineStyle("Dash")
			plot.getCurve(mUnrFlow).setLineStepStyle("linear")
			plot.getCurve(mUnrFlow).setLineWidth(2.)
			plot.setLegendLabelText(mUnrELEV.getData(), "Unreg-QR")
		except :
			msg = "WARNING could not complete Unreg-Flow formatting."
			logging.info(msg)
			txtArea.printToGUI(msg)			
		
		# save plot to PNG file
		pltFile = ClientApp.Workspace().makeAbsolutePath("shared/Plots/Junctions/%s.png" %jn)
		cFile.ensure_dir(pltFile)
		plot.setSize(1600, 1040)
		plot.saveToPng(pltFile)
		plot.close()
	# close DSS file
	simDSS.close()
	# print in file messages
	msg = "\nCompute Complete!"
	txtArea.printToGUI(msg)
	logging.info(msg)
	bar.setValue(100)