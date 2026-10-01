'''
cDamPrev Module
Contains code to do Damages Prevented
'''
from java.io import File
from hec.script import MessageBox
from hec.hecmath import DSS
from hec.hecmath import TimeSeriesMath
from hec.lang import DSSPathString
from hec.model import PairedValuesExt
from hec.heclib.util import HecTime
from hec.rss.model import ReservoirElement, JunctionElement, ReachElement, DiversionElement
from hec.rss.model import SsarrRouting, NullRouting, PulsChannelRoutingWithLosses
from hec.rss.model import RssModelVariableConstants
from jxl import Workbook
import os, sys, logging

#Custom imports
import cResSim, cFile, cRouting, cExcel, cTsUtils, cNatLakeARDB
reload(cExcel)
insertCell = cExcel.insertCell
################################################################################
# STATIC INPUT
reregDict = {"Detroit":"Big Cliff", "Lookout Point":"Dexter", "Pelton":"Pelton ReReg"}
naturalLakes = ["Corra Linn", "Kerr", "Albeni Falls", "Post Falls", "Arrow Lakes"]
naturalOutletName = "Natural Lake" #the exact name of all natural lake outlets in ResSim
arrowName = "Arrow Lakes" #the reservoir name of Arrow in ResSim

################################################################################
# CLASS DEFINITIONS

class JuncPeaks:
	'''Class to store all types of peak flows for a junction (e.g. obs, unreg, one resv. missing)'''
	def __init__(self, name):
		self._name = name
		self.obsPeak = None #actual "Observed Data"
		self.obsPeakTime = None
		self.modeledObsPeak = None #ResSim run mimicking observed conditions
		self.modeledObsPeakTime = None
		self.isGaged = False # boolean to store whether "Observed Flow" exists at this location
		self.unregPeak = None
		self.unregPeakTime = None
		self.rPeakDict = {} # dictionary to hold the peaks corresponding to adding/subtracting resvs
		self.rPeakTimeDict = {}
	def getPeakWith(self, rName):
		if rName in self.rPeakDict.keys(): return self.rPeakDict[rName]["WITH"]
	def getPeakWithout(self, rName):
		if rName in self.rPeakDict.keys(): return self.rPeakDict[rName]["WITHOUT"]
	def getTimeOfPeak(self, rName):
		if rName in self.rPeakTimeDict.keys(): return self.rPeakTimeDict[rName]
	def getObsPeak(self):
		return self.obsPeak
	def getObsTimeOfPeak(self):
		return self.obsPeakTime
	def getModeledObsPeak(self):
		return self.modeledObsPeak
	def getModeledObsTimeOfPeak(self):
		return self.modeledObsPeakTime
	def getUnregPeak(self):
		return self.unregPeak
	def getUnregTimeOfPeak(self):
		return self.unregPeakTime
	def getContributingResvs(self):
		return self.rPeakDict.keys()
	def setPeakInfo(self, rName, peak, TOP, isWith):
		'''Sets the peak info for a reservoir, string, double, HecTime
		isWith = boolean, if true, this is a simulation that only includes the reservoir'''
		if not rName in self.rPeakDict.keys(): 
			self.rPeakDict[rName] = {}
			self.rPeakTimeDict[rName] = {}
		if isWith: withType = "WITH"
		else:      withType = "WITHOUT"
		self.rPeakDict[rName][withType] = peak
		self.rPeakTimeDict[rName][withType] = TOP
	def setFlowReduction(self, rName, reduction):
		'''Sets the average flow reduction at this junction due to the reservoir'''
		self.rPeakDict[rName]["reduction"] = reduction
	def getFlowReduction(self, rName):
		return self.rPeakDict[rName]["reduction"]
	def setModeledObsPeakInfo(self, peak, TOP):
		self.modeledObsPeak = peak
		self.modeledObsPeakTime = TOP
	def setObsPeakInfo(self, peak, TOP):
		self.obsPeak = peak
		self.obsPeakTime = TOP
	def setUnregPeakInfo(self, peak, TOP):
		self.unregPeak = peak
		self.unregPeakTime = TOP
	def setGaged(self, isGaged):
		#Set whether Observed Data exists here
		self.isGaged = isGaged
	
class ResvPeaks:
	'''Class to store all types of peak flows for a reservoir (e.g. inflow, time of inflow, outflow'''
	def __init__(self, name):
		self._name = name
		self.inflowPeak = None
		self.inflowPeakTime = None
		self.outflowPeak = None  # outflow at time of peak inflow
	def getInflowPeak(self):
		return self.inflowPeak
	def getInflowTimeOfPeak(self):
		return self.inflowPeakTime
	def getOutflowAtInflowPeakTime(self):
		return self.outflowPeak	
	def setInflowPeakInfo(self, peak, TOP):
		self.inflowPeak = peak
		self.inflowPeakTime = TOP
	def setOutflowAtInflowPeakTime(self, peak):
		self.outflowPeak = peak
		
# END OF CLASS DEFINITIONS
################################################################################
# FUNCTION DEFINITIONS
def getJuncPeakFlows(rssRunObs, rssRunUnreg, simDss, outDss, outputJuncs, bar, txtArea):
	'''
	Retrieves the observed and unregulated flows for all output junctions, stores
	the peak flow data, and writes out the timeseries to the output dss file
	@rssRunObs			rssRun				the modeled Observed RssRun (with observed data defined)
	@rssrunUnreg		rssRun				the modeled Unregulated Rssrun (with natural lake effects)
	@simDss					DssFile     	already opened simulation.dss file
	@outDss					DssFil      	already opened output DSS file
	@outputJuncs		list					list of JunctionElements to retrieve
	@bar						JProgressBar
	@txtArea				JTextArea			must have "printToGUI" method defined 
	return dict     dict of JuncPeaks objects, keys are junction names
	'''
	juncPeakDict = {}
	initialBar = bar.getValue()
	for i in range(len(outputJuncs)):
		junc = outputJuncs[i]
		bar.setValue(initialBar + int(float(i)/len(outputJuncs)*10))
		msg = "\tJunction: "+junc._name
		logging.info(msg)
		txtArea.printToGUI(msg)
		juncName = junc.toString()
		jp = JuncPeaks(juncName)
		# Do the unreg flows first
		rssConstant = RssModelVariableConstants.VID_NODE_FLOW
		unregTSM = cResSim.getTSMFromSimulationDSS(simDss, junc, rssRunUnreg, rssConstant, txtArea, 
		 useObsData=False, isStrict = True, displayMessages = True)
		jp.setUnregPeakInfo(unregTSM.max(), HecTime(unregTSM.maxDate(), HecTime.MINUTE_INCREMENT))
		unregTSM.setLocation(juncName)
		unregTSM.setParameterPart("FLOW")
		unregTSM.setVersion("UNREGULATED")
		outDss.write(unregTSM)
		# Do ResSim modeled observed flows from the simulation
		modeledObsTSM = cResSim.getTSMFromSimulationDSS(simDss, junc, rssRunObs, rssConstant, txtArea,
		 useObsData = False, isStrict = True, displayMessages = True)
		jp.setModeledObsPeakInfo(modeledObsTSM.max(), HecTime(modeledObsTSM.maxDate(), HecTime.MINUTE_INCREMENT))
		modeledObsTSM.setLocation(juncName)
		modeledObsTSM.setParameterPart("FLOW")
		modeledObsTSM.setVersion("MODELED OBSERVED")
		outDss.write(modeledObsTSM)
		# Finally, do the "Observed Data" if it exists
		obsTSM = cResSim.getTSMFromSimulationDSS(simDss, junc, rssRunObs, rssConstant, txtArea, 
		 useObsData=True, isStrict = False, displayMessages = False)
		if obsTSM: 
			#"Observed Data" exists at this spot
			isGaged = True
			jp.setObsPeakInfo(obsTSM.max(), HecTime(obsTSM.maxDate(), HecTime.MINUTE_INCREMENT))
			obsTSM.setWatershed("")
			obsTSM.setLocation(juncName)
			obsTSM.setParameterPart("FLOW")
			obsTSM.setVersion("OBSERVED")
			outDss.write(obsTSM)
		else:
			#no "Observed Data" found here
			isGaged = False
		jp.setGaged(isGaged)
		juncPeakDict[juncName] = jp
	return juncPeakDict

def getResvPeakFlows(rssRunObs, simDss, resvElems, bar, txtArea):
	'''
	Retrieves the observed peak inflow and time, and outflow at that time for all resvs
	@rssRunObs			rssRun  			the modeled Observed RssRun (with observed data defined)
	@simDss					DssFile     	already opened simulation.dss file
	@resvElems			list          List of ReservoirElements to process
	@bar						JProgressBar
	@txtArea				JTextArea			must have "printToGUI" method defined 
	return dict     dict of ResvPeaks objects, keys are reservoir names
	'''
	resvPeakDict = {}
	network = rssRunObs.getNetwork()
	resvNames = network.getReservoirNames() 
	initialBar = bar.getValue()
	for i in range(len(resvElems)):
		resvElem = resvElems[i]
		resvName = resvElem.toString()
		if resvName in reregDict.values(): continue
		bar.setValue(initialBar + int(float(i)/len(resvElems)*10))
		txtArea.printToGUI("\tReservoir: %s" %resvName)
		logging.info("\tReservoir: %s" %resvName)
		rp = ResvPeaks(resvName)
		# get observed inflows (modeled inflow)
		rssConstant = RssModelVariableConstants.VID_POOL_INFLOW
		inTSM = cResSim.getTSMFromSimulationDSS(simDss, resvElem, rssRunObs, rssConstant, txtArea, 
		 useObsData=False, isStrict = True, displayMessages = True)
		if not inTSM: #failed to retrieve the data
			errMsg = "Failed to retrieve inflow data at: %s" %resvElem
			errMsg = "\nSee the log file for more details"
			txtArea.printToGUI(errMsg)
			logging.error(errMsg)
			return None
		# get observed outflows
		# For the reservoirs with reregs, use the rereg outflow, not the resv outflow
		dsResvElem = resvElem
		if resvName in reregDict.keys(): 
			dsResvElem = network.findReservoir(reregDict[resvName])
		#Observed flows are actually mapped in at the outflow junction--get it
		outJunc = dsResvElem.getDownstreamNode().getDownstreamElement() #e.g. Kerr_OUT
		rssConstant = RssModelVariableConstants.VID_NODE_FLOW
		outTSM = cResSim.getTSMFromSimulationDSS(simDss, outJunc, rssRunObs, rssConstant, txtArea, 
		 useObsData = True, isStrict = False, displayMessages = False)
		if outTSM is None: 
			#Wanted to get "Observed Data", but it didn't exist
			#Get modeled data instead
			outTSM = cResSim.getTSMFromSimulationDSS(simDss, outJunc, rssRunObs, rssConstant, txtArea,
			 useObsData = False, isStrict = True, displayMessages = True)
		if outTSM is None: #failed to retrieve the data
			errMsg = "Failed to retrieve data at: %s" %element
			errMsg = "\nSee the log file for more details"
			txtArea.printToGUI(errMsg)
			logging.error(errMsg)
			return None
		#Identify the peak flow, time of peak, and save to the ResvPeaks object
		timeOfPeakInflow = HecTime(inTSM.maxDate(), HecTime.MINUTE_INCREMENT)
		outTSC = outTSM.getData()
		outflowAtPeakInflowTime = outTSC.values[outTSC.times.index(timeOfPeakInflow.value())]
		rp.setInflowPeakInfo(inTSM.max(), timeOfPeakInflow)
		rp.setOutflowAtInflowPeakTime(outflowAtPeakInflowTime)
		resvPeakDict[resvName] = rp
	return resvPeakDict
		
def forceMinRelease(outflowTSM, minRel, conserveVolume=True):
	'''
	This function will take an input time series and make sure it is capped to a minimum flow
	The volume lost from manually changing values can be tracked and made up in future time steps
	 as quickly as possible (similar to how ResSim would do it at a reservoir)
	This is useful when running scenarios when there is only one reservoir active in a simulation
	If the flow difference was applied directly, it would result in some negative outflows
	This often happens at Revelstoke, since Mica is propping up flows in the winter
	It conserves volume (the sum of the corrected dataset is the same as the sum of the input)
	@outflowTSM  TimeSeriesMath The time-series of outflows to be corrected (regular interval)
	@minRel      number         The minimum release to force on the outflowTSM
	@conserveVolume boolean     If true, volume will be conserved. If false, flows will simply be capped to the minimum
	'''
	correctedTSM = outflowTSM.copy()
	correctedTSC = correctedTSM.getData()
	values = correctedTSC.values
	runningVolDiff = 0
	for i in range(len(values)):
		if conserveVolume:
			#Make sure the corrected value is at least minimum release, and apply any previous volume adjustments
			newVal = max(values[i] - runningVolDiff, minRel)
			volDiff = newVal - values[i]
			runningVolDiff += volDiff
		else:
			#simply cap to the minimum flow
			newVal = max(values[i], minRel)
		values[i] = newVal
	correctedTSC.values = values
	correctedTSM.setData(correctedTSC)
	return correctedTSM
	
def computeNatLakeOps(startElev, numLookbackSteps, elevStorTbl, elevRelTbl, inflowTSM):
	'''
	Model a simple natural lake over the time window given in the input inflow time series
	Simply release exactly what the elev-release table shows
	The release and elevation during the lookback period will remain constant
	@startElev   double          The lake elevation to initialize to
	@elevStorTbl PairedValuesExt Elevation-Storage table of the natural lake
	@elevRelTbl  PairedValuesExt Elevation-Release capacity table of the natural lake
	@inflowTSM   TimeSeriesMath  Inflow time series to the lake (must have regular interval)
	@numLookback
	returns:
	@outflowTSM   TimeSeriesMath  The outflow time series from this natural lake
	@elevTSM      TimeSeriesMath  The modeled elevation for this natural lake
	'''
	#Flip around the elev-stor table
	storElevTable = PairedValuesExt() 
	storElevTable.setData(elevStorTbl.getPairedDataContainer())
	elevations = storElevTable.getXArray()
	storages = storElevTable.getYArray()
	storElevTable.setArrays(storages,elevations)
	#Prepare the input parameters
	inflowTSC = inflowTSM.getData()
	stepSeconds = inflowTSC.interval*60 #interval is in minutes
	acFtTocfs = 43560./stepSeconds #conversion factor
	inflows = inflowTSC.values
	elevs = [0 for i in range(len(inflows))]
	outflows = [0 for i in range(len(inflows))]
	stors = [0 for i in range(len(inflows))]
	prevElev = startElev #initialize elevation
	prevStor = elevStorTbl.interpolate(startElev) #initialize storage
	for i in range(len(inflows)):
		#Set outflow to the release capacity, using the previous day's elevation
		#Assumes that the inflow/outflow are period average (apply for the previous time period)
		inflow = inflows[i]
		outflow = elevRelTbl.interpolate(prevElev)
		outflows[i] = outflow
		#compute the resulting pool elevation/storage
		stors[i] = prevStor + (inflow - outflow)/acFtTocfs
		elevs[i] = storElevTable.interpolate(stors[i])
		if i <= numLookbackSteps: #override--maintain a constant pool during lookback
			stors[i] = elevStorTbl.interpolate(startElev)
			elevs[i] = startElev
		prevElev = elevs[i]
		prevStor = stors[i]
	#Set up the output elevation TimeSeriesMath
	outflowTSM = inflowTSM.copy()
	outflowTSM.setParameterPart("Flow-Out-Natural Lake")
	outflowTSM.getContainer().values = outflows
	elevTSM = inflowTSM.copy()
	elevTSM.setParameterPart("Elev-Natural Lake")
	elevTSM.setUnits("ft")
	elevTSM.setType("INST-VAL")
	elevTSM.getContainer().values = elevs
	return outflowTSM, elevTSM
	
def computeArrowLakeOps(rssRunObj, simDss, outDss, inflowTSM, outFPart, txtArea):
	'''
	Model Arrow Lakes as a natural lake for a whole time window
	Returns a TimeSeries Math that represents the outflow out of Arrow
	Launches a compute that is quasi-ResSim: the operation is defined as a rule
	Interim output is saved to simDss with an output of outFpart
	@startElev   double          The lake elevation to initialize to
	@simDss      DssFile         Already opened Dss file to read input from
	@outDss      DssFile         Already opened Dss file to save output to
	@inflowTSM   TimeSeriesMath  Inflow time series to the lake (must have regular interval)
	@outFPart    string          The desired fpart of the natural lake operation output
	@txtArea     JTextArea       must have "printToGUI" defined
	returns:
	@outflowTSM   TimeSeriesMath  The outflow time series from Arrow
	'''
	network = rssRunObj.getNetwork()
	tsDataSetObj = rssRunObj.getRegOutputTSData()
	###################
	#Get Kootenai flows
	kootReachName = "Brilliant_OUT to Columbia+Kootenai" #must be hardcoded...
	kootReach = network.findReach(kootReachName)
	if not kootReach:
		errMsg = "Failed to find Kootenai reach named: %s" %kootReachName
		logging.error(errMsg)
		txtArea.printToGUI(errMsg)
		return None
	rssConstant = RssModelVariableConstants.VID_NODE_FLOW
	kootFlowTSM = cResSim.getTSMFromSimulationDSS(simDss, kootReach, rssRunObj, rssConstant, txtArea, 
	 useObsData=False, isStrict = True, displayMessages = True)
	##################
	#Get local flow
	ardbInJuncName = "Arrow Lakes_IN"
	inflowJunc = network.findJunction(ardbInJuncName) #must be hardcoded...
	if not inflowJunc:
		errMsg = "Failed to find Arrow Lakes Inflow Junction: %s" %ardbInJuncName
		logging.error(errMsg)
		txtArea.printToGUI(errMsg)
		return None
	nodes = inflowJunc.getNodeVector()
	locFlowTSM = None
	for node in nodes: #One local flow per node in ResSim
		#Local flow nodes have no upstream element
		if node.getUpstreamElement(): continue #must be a connected element, skip it
		rssConstant = RssModelVariableConstants.VID_NODE_FLOW
		#Output local flows are stored to the node as FLOW, not KNOWNFLOW
		locFlowTSM = cResSim.getTSMFromSimulationDSS(simDss, node, rssRunObj, rssConstant, txtArea, 
		 useObsData = False, isStrict = True, displayMessages = True)
	if not locFlowTSM:
		errMsg = "Failed to find Arrow Lakes Local Flow at: %s" %ardbInJuncName
		logging.error(errMsg)
		txtArea.printToGUI(errMsg)
		return None
	#run the natural lake operation
	outflows = cNatLakeARDB.computeNatLakeArrow(rssRunObj, outDss, inflowTSM.getData(), \
	 locFlowTSM.getData(), kootFlowTSM.getData(), outFPart)
	#Create the output time series math object
	outflowTSM = inflowTSM.copy()
	outflowTSC = outflowTSM.getContainer()
	outflowTSC.values = outflows
	outflowTSM.setData(outflowTSC)
	return outflowTSM
		
def runResvSimulations(rssRunObs, rssRunUnreg, simDss, outDss, resvsToRun, outputJuncs, juncPeakDict, isWith, bar, txtArea):
	'''
	Run all possible mini-simulations in one of 2 possible ways:
	if isWith = True,  each individual reservoir is added to the unreg system
	if isWith = False, each individual reservoir is taken out of the observed system
	if doing "with only" runs, this will account for downstream natural lake operations
	Save the results to the juncPeakDict
	rssRunObs and rssRunUnreg must be based off the same network for this to work!
	@rssRunObs		rssRun   the modeled Observed RssRun (with observed data defined)
	@rssRunUnreg  rssRun   the modeled Unregulated Rssrun (with natural lake effects)
	@simDss 			DssFile  already opened simulation.dss file
	@outDss 			DssFile  already opened output.dss file
	@resvsToRun 	list     list of ReservoirElements to do with/without simulations for
	@outputJuncs 	list     list of JunctionElements where to save detailed output
	@juncPeakDict dict     dict of JuncPeaks objects at the junctions to add on to
	@isWith 			boolean  boolean showing whether to do "with" or "without" simulations
	return dict   juncPeakDict
	'''
	debug = True
	simDssFile = simDss.getFilename()
	#Set the rssRun to use for the whole basin
	rssAltUnreg = rssRunUnreg.getAlternative() #need this for lookback natural lake elevs
	if isWith: rssRunObj = rssRunUnreg #no reservoirs except one
	else: rssRunObj = rssRunObs
	numLookbackSteps = rssRunObj.getRunTimeWindow().getNumLookbackSteps()
	network = rssRunObj.getNetwork()
	# Get reservoirs with more than one inflow
	# Need to get the elements in the same network as the "resvsToRun" for identity testing
	confResvDict = cResSim.getConfluenceResvPoolDict(resvsToRun[0].getSystem())
	confResvs = confResvDict.keys() #pool Element, not ReservoirElement
	#Need to deal with junction names as strings, since "network" may be different
	#  than the network that "resvsToRun" were based off of
	confJuncNames = [j.toString() for j in cResSim.getConfluenceJunctions(network)]
	#Set up the time series bank that will hold read time series so we don't have to read/write continually
	tsBank = cResSim.tsmBank()
	# Get the normal output time series mapping
	tsDataSetObj = rssRunObj.getRegOutputTSData()
	initialBar = bar.getValue()
	#Loop for all reservoirs desired
	for i in range(len(resvsToRun)):
		resvElem = resvsToRun[i] #use the network associated with these reservoirs
		#the following line isn't necessary (rjc 1/12/15)
		#resvElem = network.findReservoir(elem.toString()) #must be in the proper network
		resvName = resvElem.toString()
		if resvName in reregDict.values(): continue # skip the rereg projects     
		msg = "\tReservoir: %s" %resvName
		logging.info(msg)
		txtArea.printToGUI(msg)
		bar.setValue(initialBar + int(float(i)/len(resvsToRun)*40))
		#Set output fpart
		if isWith: fPartOut = "WITH ONLY %s" %resvName
		else: fPartOut = "WITHOUT %s" %resvName
		# get the reservoir inflow to start the journey downstream (assume resv passes inflow)
		rssConstant = RssModelVariableConstants.VID_POOL_INFLOW
		flowTSM = cResSim.getTSMFromSimulationDSS(simDss, resvElem, rssRunObj, rssConstant, txtArea, 
		 useObsData=False, isStrict = True, displayMessages = True)
		# Proceed downstream, stopping along the way at pleasant little junctions
		dsElems = network.getDownstreamElements(resvElem)
		dsNodes = []
		network.getDownstreamNodeList(resvElem, dsNodes) #adds the downstream nodes to "dsNodes"
		dsElems.add(0, resvElem) # pop in the reservoir element as the first element
		for elem in dsElems:
			elemName = elem.toString()
			##########################################################################
			if isinstance(elem, JunctionElement):
				# If the junction is a confluence junction, add in the flow from upstrm reaches
				logging.debug("  Junction: %s" %elemName)
				if elemName in confJuncNames:
					logging.debug("    Confluence Junction!")
					upstreamReaches = cResSim.getConnectedReaches(elem)
					for rch in upstreamReaches:
						if rch in dsElems: continue # It's in the flow path, we only want tribs
						logging.debug("    Adding reach: %s" %rch)
						rchNode = rch.getDownstreamNode()
						tsName = "%s Flow" %rchNode.toString()
						reachTSM = tsBank.withdrawTS(simDssFile, tsName) #will return None if doesn't exist yet
						if not reachTSM: #need to read it for the first time
							rssConstant = RssModelVariableConstants.VID_NODE_FLOW
							reachTSM = cResSim.getTSMFromSimulationDSS(simDss, rchNode, rssRunObj, rssConstant, txtArea, 
								useObsData=False, isStrict = True, displayMessages = True)
							tsBank.depositTS(simDssFile, tsName, reachTSM)
						flowTSM = flowTSM.add(reachTSM)
				# Add in any local flows
				nodes = elem.getNodeVector()
				for node in nodes: #One local flow per node in ResSim
					#Local flow nodes have no upstream element
					if node.getUpstreamElement(): continue #must be a connected element, skip it
					logging.debug("    Local Flow Node: %s" %node)
					tsName = "%s Local Flow" %node.toString()
					locFlowTSM = tsBank.withdrawTS(simDssFile, tsName) #will return None if doesn't exist yet
					if not locFlowTSM: #need to read it for the first time
						rssConstant = RssModelVariableConstants.VID_NODE_FLOW
						#Output local flows are stored to the node as FLOW, not KNOWNFLOW
						#Any inflow multipliers are already accounted for
						locFlowTSM = cResSim.getTSMFromSimulationDSS(simDss, node, rssRunObj, rssConstant, txtArea, 
						 useObsData = False, isStrict = True, displayMessages = True)
						tsBank.depositTS(simDssFile, tsName, locFlowTSM)
					flowTSM = flowTSM.add(locFlowTSM)
				# Account for diversions
				divElems = cResSim.getConnectedDiversions(elem)
				if divElems:
					for divElem in divElems:
						#There is a diversion--take it out (should be set to 0 if that's expected in unreg)
						logging.debug("    Diversion found: %s" %divElem)
						divNode = divElem.getUpstreamNode() #flow being taken out to a diversion is in upstream node
						tsName = "%s Diversion Flow" %divNode.toString()
						divTSM = tsBank.withdrawTS(simDssFile, tsName) #will return None if doesn't exist yet
						if not divTSM: #need to read it for the first time
							rssConstant = RssModelVariableConstants.VID_NODE_FLOW
							#rssConstant = RssModelVariableConstants.VID_ADJPARAM_FLOW
							divTSM = cResSim.getTSMFromSimulationDSS(simDss, divNode, rssRunObj, rssConstant, txtArea, 
								useObsData=False, isStrict = True, displayMessages = True)
							tsBank.depositTS(simDssFile, tsName, divTSM)
						flowTSM = flowTSM.subtract(divTSM) #divTSM are positive numbers
						flowTSM = forceMinRelease(flowTSM, 0, conserveVolume=False) #ResSim won't draw out flows below 0
						divTSM = None
			##########################################################################
			elif isinstance(elem, ReachElement):
				# If the element is a reach, route the flow to the next junction
				#ResSim reaches cannot accept any negative flow--it violates conservation of mass and caps to 0
				flowTSM = forceMinRelease(flowTSM, 0, conserveVolume=False)
				routingObj = elem.getFunction()
				logging.debug("  Reach: %s" %elemName)
				routeReach = cRouting.buildReach(routingObj)
				if routeReach is None:
					errMsg = "The Script cannot handle any routing methods besides SSARR, Muskingum, ModPuls, or Null:"
					errMsg += "\n%s has routing of: %s" %(elemName, routingObj.__class__)
					logging.error(errMsg)
					txtArea.printToGUI(errMsg)
					return None
				logging.debug("\tRouting Type: %s" %routingObj.__class__)
				flowTSC = routeReach.routeTSC(flowTSM.getData())
				flowTSM = TimeSeriesMath(flowTSC)
			##########################################################################
			elif isinstance(elem, ReservoirElement): 
				# If the element is a reservoir, account for any storage or draft this time step for the "without" runs
				# For the "With" runs, only account for the project under analysis and its rereg (if applicable) and natural lakes
				logging.debug("  Reservoir: %s" %elemName)
				poolElem = cResSim.getPoolElemFromResvElem(elem)
				# First, add in any additional inflows (some reservoirs have multiple inflow junctions, e.g. Arrowrock)
				if poolElem in confResvs and elem != resvElem:
					# If the junction is a confluence reservoir, add in the flow from upstream junctions
					logging.debug("\tIt's a confluence reservoir")
					upstreamJunctions = confResvDict[poolElem]
					for juncElem in upstreamJunctions:
						if juncElem in dsElems: continue # It's in the flow path, we only want tribs
						logging.debug("    Adding junction: %s" %juncElem)
						tsName = "%s Junction Flow" %juncElem.toString()
						juncTSM = tsBank.withdrawTS(simDssFile, tsName) #will return None if doesn't exist yet
						if not juncTSM: #need to read it for the first time
							rssConstant = RssModelVariableConstants.VID_NODE_FLOW
							juncTSM = cResSim.getTSMFromSimulationDSS(simDss, juncElem, rssRunObj, rssConstant, txtArea, 
								useObsData=False, isStrict = True, displayMessages = True)
							tsBank.depositTS(simDssFile, tsName, juncTSM)
						flowTSM = flowTSM.add(juncTSM)
				# Now, deal with the reservoir itself
				reregName = ""
				if resvName in reregDict.keys(): reregName = reregDict[resvName]
				if elemName in naturalLakes and ((isWith and elem != resvElem) or (not isWith and elem == resvElem)):
					#Account for the attenuation effects here
					logging.debug(" Natural Lake modeled at: %s" %elemName)
					if elemName == arrowName:
						#Arrow Lake natural lake operations need to be done specially
						logging.debug("Arrow Lakes logic is computing")
						flowTSM = computeArrowLakeOps(rssRunObj, simDss, outDss, flowTSM, fPartOut, txtArea)
					else: #not Arrow
						elevStorTbl = cResSim.getElevationStorageTable(elemName, network)
						elevRelTbl = cResSim.getElevationReleaseTable(elemName, naturalOutletName, network)
						startElev = cResSim.getLookback(elemName, rssAltUnreg, "ELEV") #unreg alt has lookback info
						if not elevRelTbl:
							errMsg = "Failed to find an outlet at: %s  named: %s" %(elemName, naturalOutletName)
							logging.error(errMsg)
							txtArea.printToGUI(errMsg)
							return None
						if not startElev:
							errMsg = "Failed to retrieve lookback elevation at: %s for alternative: %s" %(elemName, rssAltUnreg)
							errMsg += "\nIt must be specified as a constant"
							logging.error(errMsg)
							txtArea.printToGUI(errMsg)
							return None
						flowTSM, elevTSM = computeNatLakeOps(startElev, numLookbackSteps, elevStorTbl, elevRelTbl, flowTSM)
						if debug: #write out to DSS can be useful for verification
							elevTSM.setLocation(elemName)
							flowTSM.setLocation(elemName)
							elevTSM.setVersion(fPartOut)
							flowTSM.setVersion(fPartOut)
							outDss.write(flowTSM)
							outDss.write(elevTSM)
				elif isWith and not (elem == resvElem or elem._name == reregName): 
					logging.debug("  Assume passes inflow: %s" %elemName)
					#not the resv or its rereg--just assume it passes inflow
				elif not isWith and (elem == resvElem or elem._name == reregName): 
					logging.debug("  Don't do the reservoir or rereg itself: %s" %elemName)
					# don't do the reservoir or rereg if a "without" run
				else:
					# get outflow minus inflow from observed run and add it to the incoming flow
					logging.debug("  Accounting for change in storage at: %s" %elemName)
					# Note: I originally used the pool storage difference, but this does not work
					# for the lookback, when ResSim violates conservation of mass. 
					# Use inflow minus outflow instead
					'''
					storPath = "//%s-POOL/STOR//%s/%s/" %(elem.toString(), tsInt, fPartObs)
					storTSC = simDss.read(storPath).getData()
					flowTSC = flowTSM.getData()
					# Find the amount the reservoir is expected to draft or refill and apply it to the flow
					for i in range(1, len(flowTSC.values)): # don't change the first flow value
						storPrev = storTSC.values[i-1]
						storCur = storTSC.values[i]
						flowEquivalent = (storCur-storPrev)*43560./(flowTSC.interval*60.)
						flowTSC.values[i] = flowTSC.values[i] - flowEquivalent
					flowTSM = TimeSeriesMath(flowTSC)
					'''
					tsName = "%s Inflow" %elemName
					inflowTSM = tsBank.withdrawTS(simDssFile, tsName) #will return None if doesn't exist yet
					if not inflowTSM: #need to read it for the first time
						rssConstant = RssModelVariableConstants.VID_POOL_INFLOW
						inflowTSM = cResSim.getTSMFromSimulationDSS(simDss, elem, rssRunObs, rssConstant, txtArea, 
							useObsData=False, isStrict = True, displayMessages = True)
						tsBank.depositTS(simDssFile, tsName, inflowTSM)
					tsName = "%s Outflow" %elemName
					outflowTSM = tsBank.withdrawTS(simDssFile, tsName) #will return None if doesn't exist yet
					if not outflowTSM: #need to read it for the first time
						rssConstant = RssModelVariableConstants.VID_POOL_OUTFLOW
						outflowTSM = cResSim.getTSMFromSimulationDSS(simDss, elem, rssRunObs, rssConstant, txtArea, 
							useObsData=False, isStrict = True, displayMessages = True)
						tsBank.depositTS(simDssFile, tsName, outflowTSM)
					flowTSM = flowTSM.add(outflowTSM)
					flowTSM = flowTSM.subtract(inflowTSM)
					#Sometimes the storage difference approach will cause the reservoir to release less than 0
					#Correct for any negative outflows
					flowTSM = forceMinRelease(flowTSM, 0, conserveVolume=True)
			if elem in outputJuncs:
				#We are at a detailed output location--write out to DSS
				#Tell whether hourly or daily
				flowPath = DSSPathString(flowTSM.getPath())
				tsInt = flowPath.getEPart()
				outputPath = "//%s/FLOW//%s/%s/" %(elem.toString(), tsInt, fPartOut)
				flowTSM.setPathname(outputPath)
				outDss.write(flowTSM)
				juncPeakDict[elem.toString()].setPeakInfo(resvName, flowTSM.max(), HecTime(flowTSM.maxDate(), HecTime.MINUTE_INCREMENT), isWith)
	tsBank.close()
	return juncPeakDict
	
def runChart80Simulation(rssRunObs, rssRunUnreg, simDss, outDss, resvList, diversionList, outputJuncs, fPartOut, tsBank, bar, txtArea):
	'''
	This function is quite similar to the "runResvSimulations" and the "computeLocalFlows" function
	If I had time, I would have made one function that would do both--rjc, Oct 2015
	Chart 80 is produced by NWD, and shows the flow reduction at TDA as a time series from separate groups of projects
	The approach to generate Chart 80 is to incrementally add in projects to the unregulated run
	This is very similar to the "isWith=True" simulations of the "runResvSimulations", except there is more than one project at a time
	Natural lake operations will be modeled if the project isn't in the selected list

	rssRunObs and rssRunUnreg must be based off the same network for this to work!
	@rssRunObs		rssRun   the modeled Observed RssRun (with observed data defined)
	@rssRunUnreg  rssRun   the modeled Unregulated Rssrun (with natural lake effects)
	@simDss 			DssFile  already opened simulation.dss file
	@outDss 			DssFile  already opened output dss file
	@resvList			list     list of ReservoirElements to include in the simulation
	@diversionList list    list of DiversionElements to include in the simulation
	@outputJuncs	list     list of JunctionElements where to save detailed output
	@fPartOut			string   f-part to set the output time series to
	@tsBank				tsmBank  The bank of time series to draw from
	returns the tsBank if successful
	'''

	simDssFile = simDss.getFilename()
	rssRunObj = rssRunUnreg # base rssRun can be the unregulated run (doesn't really matter)
	rssAltUnreg = rssRunUnreg.getAlternative() #need this for lookback natural lake elevs
	numLookbackSteps = rssRunObj.getRunTimeWindow().getNumLookbackSteps()
	network = rssRunObj.getNetwork()
	confJuncs = cResSim.getConfluenceJunctions(network)
	hwJuncs = cResSim.getRealHeadwaterJunctions(network)
	orderedElements = cResSim.orderElementsFromUpstream(network)
	# Get reservoirs with more than one inflow
	# Need to get the elements in the same network as the "resvList" for identity testing
	confResvDict = cResSim.getConfluenceResvPoolDict(resvList[0].getSystem())
	confResvs = confResvDict.keys() #pool Element, not ReservoirElement
	#Need to deal with junction names as strings, since "network" may be different
	#  than the network that "resvList" were based off of
	confJuncNames = [j.toString() for j in cResSim.getConfluenceJunctions(network)]
	initialBar = bar.getValue()
	# dictionary of timeseries containers for tributary regulated flows
	tribFlows = {} #keys are Elements of some sort (e.g. Reach), values are TSCs 
	#Proceed through all elements, saving "flowTSM" as the current state of the routed flow
	for i in range(len(orderedElements)):
		bar.setValue(int(float(i)/len(orderedElements)*100))
		elem = orderedElements[i]
		if elem == None: continue
		elemName = elem.toString()
		if isinstance(elem, JunctionElement):
			# If the junction is a confluence junction, add in the flow from upstrm reaches
			logging.debug("  Junction: %s" %elemName)
			if elemName in confJuncNames:
				logging.debug("    Confluence Junction!")
				upstreamReaches = cResSim.getConnectedReaches(elem)
				for rch in upstreamReaches:
					if tribFlows.has_key(rch):
						flowTSM = flowTSM.add(tribFlows[rch])  #timewindow previously checked
						logging.debug("added %s" %rch)
					else:
						# probably the downstream reach, skip it
						logging.debug("%s: Downstream reach" %rch)
						continue
			# Add in any local flows
			nodes = elem.getNodeVector()
			for node in nodes: #One local flow per node in ResSim
				#Local flow nodes have no upstream element
				if node.getUpstreamElement(): continue #must be a connected element, skip it
				logging.debug("    Local Flow Node: %s" %node)
				tsName = "%s Local Flow" %node.toString()
				locFlowTSM = tsBank.withdrawTS(simDssFile, tsName) #will return None if doesn't exist yet
				if not locFlowTSM: #need to read it for the first time
					rssConstant = RssModelVariableConstants.VID_NODE_FLOW
					#Output local flows are stored to the node as FLOW, not KNOWNFLOW
					#Any inflow multipliers are already accounted for
					locFlowTSM = cResSim.getTSMFromSimulationDSS(simDss, node, rssRunObj, rssConstant, txtArea, 
					 useObsData = False, isStrict = True, displayMessages = True)
					tsBank.depositTS(simDssFile, tsName, locFlowTSM)
				locFlowTSC = locFlowTSM.getData()
				if elem in hwJuncs: #use the data directly
					logging.debug("\t\tUsing input local flow: %s" %locFlowTSM.getPath())
					flowTSM = locFlowTSM.copy()
				else: #add to the existing flows
					logging.debug("\t\tAdding input local flow to the total flow: %s" %locFlowTSM.getPath())
					flowTSM = flowTSM.add(locFlowTSM) #timewindow previously checked
			# Account for diversions
			divElems = cResSim.getConnectedDiversions(elem)
			if divElems:
				for divElem in divElems:
					#There is a diversion--take it out if it is identified as a diversion to include (should be set to 0 in unreg model)
					logging.debug("    Diversion found: %s" %divElem)
					if divElem in diversionList:
						#The diversion should be included--deduct it from the flow
						divNode = divElem.getUpstreamNode() #flow being taken out to a diversion is in upstream node
						tsName = "%s Diversion Flow" %divNode.toString()
						divTSM = tsBank.withdrawTS(simDssFile, tsName) #will return None if doesn't exist yet
						if not divTSM: #need to read it for the first time
							#read the diversion from the observed run
							rssConstant = RssModelVariableConstants.VID_NODE_FLOW
							divTSM = cResSim.getTSMFromSimulationDSS(simDss, divNode, rssRunObs, rssConstant, txtArea, 
								useObsData=False, isStrict = True, displayMessages = True)
							tsBank.depositTS(simDssFile, tsName, divTSM)
						flowTSM = flowTSM.subtract(divTSM) #divTSM are positive numbers
						flowTSM = forceMinRelease(flowTSM, 0, conserveVolume=False) #ResSim won't draw out flows below 0
		elif isinstance(elem, ReachElement):
			# If the element is a reach, route the flow to the next junction
			#ResSim reaches cannot accept any negative flow--it violates conservation of mass and caps to 0
			flowTSM = forceMinRelease(flowTSM, 0, conserveVolume=False)
			routingObj = elem.getFunction()
			logging.debug("  Reach : %s" %elemName)
			routeReach = cRouting.buildReach(routingObj)
			if routeReach is None:
				errMsg = "The Script cannot handle any routing methods besides SSARR, Muskingum, ModPuls, or Null:"
				errMsg += "\n%s has routing of: %s" %(elemName, routingObj.__class__)
				logging.error(errMsg)
				txtArea.printToGUI(errMsg)
				return None
			logging.debug("\tRouting Type: %s" %routingObj.__class__)
			flowTSC = routeReach.routeTSC(flowTSM.getData())
			flowTSM = TimeSeriesMath(flowTSC)
		elif isinstance(elem, ReservoirElement):
			pass #a ReservoirElement will never be hit--they are stored as "Pool" Elements in orderedElements
		elif elemName == "Pool": #reservoir pool element
			resvElem = elem.getParent() #To get the ReservoirElement, need to do a .getParent() call
			resvName = resvElem.toString()
			if elem in confResvs:
				# If the junction is a confluence reservoir, add in the flow from upstrm junctions
				logging.debug("\tIt's a confluence reservoir")
				upstreamJunctions = confResvDict[elem]
				for juncElem in upstreamJunctions:
					if tribFlows.has_key(juncElem):
						flowTSM = flowTSM.add(tribFlows[juncElem])  #timewindow previously checked
						logging.debug("added %s" %juncElem)
					else:
						# The upstream junction flow should already exist
						errMsg = "ERROR: At confluence reservoir: %s" %resvName
						errMsg +="\nCouldn't locate input flow time series for Junction: %s" %juncElem
						logging.error(errMsg)
						txtArea.printToGUI(errMsg)
						return None
			# If the element is a reservoir, account for any storage or draft this time step if selected
			# Otherwise, pass inflow or do natural lake operation
			logging.debug("  Reservoir: %s" %resvName)
			# Now, deal with the reservoir itself
			if resvName in naturalLakes and (not resvElem in resvList):
				#Account for the attenuation effects here
				logging.debug(" Natural Lake modeled at: %s" %resvName)
				if resvName == arrowName:
					#Arrow Lake natural lake operations need to be done specially
					logging.debug("Arrow Lakes logic is computing")
					flowTSM = computeArrowLakeOps(rssRunObj, simDss, outDss, flowTSM, fPartOut, txtArea)
				else: #not Arrow
					elevStorTbl = cResSim.getElevationStorageTable(resvName, network)
					elevRelTbl = cResSim.getElevationReleaseTable(resvName, naturalOutletName, network)
					startElev = cResSim.getLookback(resvName, rssAltUnreg, "ELEV") #unreg alt has lookback info
					if not elevRelTbl:
						errMsg = "Failed to find an outlet at: %s  named: %s" %(resvName, naturalOutletName)
						logging.error(errMsg)
						txtArea.printToGUI(errMsg)
						return None
					if not startElev:
						errMsg = "Failed to retrieve lookback elevation at: %s for alternative: %s" %(resvName, rssAltUnreg)
						errMsg += "\nIt must be specified as a constant"
						logging.error(errMsg)
						txtArea.printToGUI(errMsg)
						return None
					flowTSM, elevTSM = computeNatLakeOps(startElev, numLookbackSteps, elevStorTbl, elevRelTbl, flowTSM)
			elif not resvElem in resvList: 
				logging.debug("  Assume passes inflow: %s" %resvName)
				#not the resv or its rereg--just assume it passes inflow
			else:
				# get outflow minus inflow from observed run and add it to the incoming flow
				logging.debug("  Accounting for change in storage at: %s" %resvName)
				# Note: I originally used the pool storage difference, but this does not work
				# for the lookback, when ResSim violates conservation of mass. 
				# Use inflow minus outflow instead
				tsName = "%s Inflow" %resvName
				inflowTSM = tsBank.withdrawTS(simDssFile, tsName) #will return None if doesn't exist yet
				if not inflowTSM: #need to read it for the first time
					rssConstant = RssModelVariableConstants.VID_POOL_INFLOW
					inflowTSM = cResSim.getTSMFromSimulationDSS(simDss, resvElem, rssRunObs, rssConstant, txtArea, 
						useObsData=False, isStrict = True, displayMessages = True)
					tsBank.depositTS(simDssFile, tsName, inflowTSM)
				tsName = "%s Outflow" %resvName
				outflowTSM = tsBank.withdrawTS(simDssFile, tsName) #will return None if doesn't exist yet
				if not outflowTSM: #need to read it for the first time
					rssConstant = RssModelVariableConstants.VID_POOL_OUTFLOW
					outflowTSM = cResSim.getTSMFromSimulationDSS(simDss, resvElem, rssRunObs, rssConstant, txtArea, 
						useObsData=False, isStrict = True, displayMessages = True)
					tsBank.depositTS(simDssFile, tsName, outflowTSM)
				flowTSM = flowTSM.add(outflowTSM)
				flowTSM = flowTSM.subtract(inflowTSM)
				#Sometimes the storage difference approach will cause the reservoir to release less than 0
				#Correct for any negative outflows
				flowTSM = forceMinRelease(flowTSM, 0, conserveVolume=True)
		if elem in outputJuncs:
			#We are at a detailed output location--write out to DSS
			#Tell whether hourly or daily
			flowPath = DSSPathString(flowTSM.getPath())
			tsInt = flowPath.getEPart()
			outputPath = "//%s/FLOW//%s/%s/" %(elem.toString(), tsInt, fPartOut)
			flowTSM.setPathname(outputPath)
			outDss.write(flowTSM)
		# Need to check if the next point is a confluence
		# If so, need to save off the time series so the confluence can retrieve it
		dsNode = elem.getDownstreamNode()
		dsElem = dsNode.getDownstreamElement()
		if dsElem in confJuncs or dsElem in confResvs:
			logging.debug("Saving to Tributary Flow dictionary: %s" %elem)
			# Save the flows to the tribFlows dictionary
			tribFlows[elem] = flowTSM.copy()
			# Reset the flowTSM variable to 0
			flowTSM = flowTSM.multiply(0)
	return tsBank
	
def popInProj3Hdrs(sht,resvName,rowNum, colIdx):
	# Puts in the header rows for project3 sheet for the resvName starting at rowNum
	insertCell(sht,rowNum,colIdx+4,"Without "+resvName)
	insertCell(sht,rowNum,colIdx+5,"Without "+resvName)
	insertCell(sht,rowNum,colIdx+6,"With only "+resvName)
	insertCell(sht,rowNum,colIdx+7,"With only "+resvName)
	insertCell(sht,rowNum+1,colIdx,"Control Point")
	insertCell(sht,rowNum+1,colIdx+1,"Unreg Peak Flow")
	insertCell(sht,rowNum+1,colIdx+2,"Modeled Obs Peak Flow")
	insertCell(sht,rowNum+1,colIdx+3,"Flow Reduction")
	insertCell(sht,rowNum+1,colIdx+4,"Peak Flow")
	insertCell(sht,rowNum+1,colIdx+5,"Peak Discharge Increase")
	insertCell(sht,rowNum+1,colIdx+6,"Peak Flow")
	insertCell(sht,rowNum+1,colIdx+7,"Peak Discharge Reduction")
	insertCell(sht,rowNum+2,colIdx+1,"cfs")
	insertCell(sht,rowNum+2,colIdx+2,"cfs")
	insertCell(sht,rowNum+2,colIdx+3,"cfs")
	insertCell(sht,rowNum+2,colIdx+4,"cfs")
	insertCell(sht,rowNum+2,colIdx+5,"cfs")
	insertCell(sht,rowNum+2,colIdx+6,"cfs")
	insertCell(sht,rowNum+2,colIdx+7,"cfs")

def exportToExcel(outExcelFile, outputJuncs, outputResvs, juncPeakDict, resvPeakDict, bar, txtArea):
	'''Push the data about the peak flows out to Excel
	This is a long function because of all the formatting
	@param string outExcelFile
	@param dict   juncPeakDict
	@param dict   resvPeakDict'''
	wkbk = Workbook.createWorkbook(File(outExcelFile))
	shtNames =  wkbk.getSheetNames()
	# Create the empty sheets
	desiredShtNames = ["Preliminary_per_project", "Mini-Simulations", "CP_Peaks", "Resv_Peaks"]
	for desiredShtName in desiredShtNames:
		if desiredShtName in shtNames:
			sht = wkbk.getSheet(desiredShtName)
		else:
			sht = wkbk.createSheet(desiredShtName, 0)
	# Do sheet "Resv_Peaks" This sheet has resv. peak inflow, outflow, and time of peak
	sht = wkbk.getSheet("Resv_Peaks")
	colIdx = 1
	# 1st col is resvName, then peak inflow, time of peak, outflow at that time, and difference
	insertCell(sht,1,colIdx,"Reservoir")
	insertCell(sht,1,colIdx+1,"Peak Inflow")
	insertCell(sht,1,colIdx+2,"Time of Peak")
	insertCell(sht,1,colIdx+3,"Outflow at time of peak")
	insertCell(sht,1,colIdx+4,"Flow Difference")
	insertCell(sht,2,colIdx+1,"cfs")
	insertCell(sht,2,colIdx+3,"cfs")
	insertCell(sht,2,colIdx+4,"cfs")
	# Set the column widths
	for j in range(6): sht.setColumnView(j, 16)
	# Fill in the table
	for i in range(len(outputResvs)):
			resvName = outputResvs[i]._name
			resvPeak = resvPeakDict[resvName]
			inflowPeak = round(resvPeak.getInflowPeak(),-2)
			outflowAtTOP = round(resvPeak.getOutflowAtInflowPeakTime(),-2)
			flowDiff = inflowPeak - outflowAtTOP
 			insertCell(sht,i+3,colIdx,resvName) 
			insertCell(sht,i+3,colIdx+1,inflowPeak)
			insertCell(sht,i+3,colIdx+2,resvPeak.getInflowTimeOfPeak().toString(4))
			insertCell(sht,i+3,colIdx+3,outflowAtTOP)
			insertCell(sht,i+3,colIdx+4,flowDiff)
			if resvName in reregDict.keys(): # it has a rereg, put a note that outflow is from rereg
				insertCell(sht,i+3,colIdx+5,"Note: Outflow is from rereg: "+reregDict[resvName])	
	# Do sheet "CP_Peaks" This sheet has junction unreg peak stage/flow, obs stage/flow, and reduction
	sht = wkbk.getSheet("CP_Peaks")
	# pop in the headers
	insertCell(sht,1,colIdx,"Control Point")
	insertCell(sht,1,colIdx+1,"Unreg Peak Flow")
	insertCell(sht,1,colIdx+2,"Date/Time of peak")
	insertCell(sht,1,colIdx+3,"Regulated Peak Flow")
	insertCell(sht,1,colIdx+4,"Date/Time of peak")
	insertCell(sht,1,colIdx+5,"Flow Reduction")
	insertCell(sht,2,colIdx+1,"cfs")
	insertCell(sht,2,colIdx+3,"cfs")
	insertCell(sht,2,colIdx+5,"cfs")
	# Set the column widths
	for j in range(6): sht.setColumnView(j, 20)
	sht.setColumnView(0,33)
	# Fill in the table
	for i in range(len(outputJuncs)):
			juncName = outputJuncs[i]._name
			juncPeak = juncPeakDict[juncName]
			unregPeak = round(juncPeak.getUnregPeak(),-2)
			if juncPeak.isGaged: #Show pure observed data
				obsPeak = round(juncPeak.getObsPeak(),-2)
				obsTOP = juncPeak.getObsTimeOfPeak()
			else:
				obsPeak = round(juncPeak.getModeledObsPeak(),-2)
				obsTOP = juncPeak.getModeledObsTimeOfPeak()
			flowDiff = unregPeak - obsPeak
			insertCell(sht,i+3,colIdx,juncName)
			insertCell(sht,i+3,colIdx+1,unregPeak)
			insertCell(sht,i+3,colIdx+2,juncPeak.getUnregTimeOfPeak().toString(4))
			insertCell(sht,i+3,colIdx+3,obsPeak)
			insertCell(sht,i+3,colIdx+4,obsTOP.toString(4))
			insertCell(sht,i+3,colIdx+5,flowDiff)
			if not juncPeak.isGaged: # the "observed" flow is the result of the ResSim simulation
				insertCell(sht,i+3,colIdx+6,"Regulated Peak Flow is ResSim simulated, not gaged")
	# Do sheet "Mini-Simulations" This sheet has the results of the with/without simulation
	sht = wkbk.getSheet("Mini-Simulations")
	# Set the column widths
	for j in range(8): sht.setColumnView(j, 20)
	sht.setColumnView(0,33)
	# Fill in the table
	r = 1 # current row number
	for j in range(len(outputResvs)):
		resvName = outputResvs[j]._name
		resvPeak = resvPeakDict[resvName]
		popInProj3Hdrs(sht, resvName, r, colIdx)
		r += 3
		for i in range(len(outputJuncs)):
			juncName = outputJuncs[i]._name
			juncPeak = juncPeakDict[juncName]
			if not resvName in juncPeak.getContributingResvs(): # junction not d/s of resv
				continue
			unregPeak = round(juncPeak.getUnregPeak(),-2)
			#Need to use the modeled observed flow, just in case time step isn't consistent
			#E.g. "Observed Data" is hourly, but simulation timestep is daily
			#The modeled observed flow should match the actual observed anyways
			#obsPeak = round(juncPeak.getObsPeak(),-2)
			obsPeak = round(juncPeak.getModeledObsPeak(),-2)
			flowDiff = unregPeak - obsPeak
			withPeak = round(juncPeak.getPeakWith(resvName), -2)
			withoutPeak = round(juncPeak.getPeakWithout(resvName), -2)
			withDiff = unregPeak - withPeak
			withoutDiff = withoutPeak - obsPeak
			avgDiff = (withDiff+withoutDiff)/2
			juncPeak.setFlowReduction(resvName, avgDiff)
			insertCell(sht,r,colIdx,juncName)
			insertCell(sht,r,colIdx+1,unregPeak)
			insertCell(sht,r,colIdx+2,obsPeak)
			insertCell(sht,r,colIdx+3,flowDiff)
			insertCell(sht,r,colIdx+4,withoutPeak)
			insertCell(sht,r,colIdx+5,withoutDiff)
			insertCell(sht,r,colIdx+6,withPeak)
			insertCell(sht,r,colIdx+7,withDiff)
			r += 1
		r += 1
	# Do sheet "Preliminary_per_project" This sheet has a matrix of flow reduction
	sht = wkbk.getSheet("Preliminary_per_project")
	# pop in the headers
	insertCell(sht,1,colIdx+4,"Preliminary Estimated flow reduction at Control Point per project (in cfs)")
	insertCell(sht,2,colIdx+4,"Average of 2 simulations--one with only the resv and one without")
	insertCell(sht,3,colIdx+4,"These numbers will need to be adjusted--they don't always add up to the total reduction")
	insertCell(sht,4,colIdx,"Control Point")
	insertCell(sht,4,colIdx+1,"Total Flow Reduction")
	for j in range(len(outputResvs)): insertCell(sht,4,colIdx+2+j, outputResvs[j]._name)
	# Set the column widths
	for j in range(13): sht.setColumnView(j, 12)
	sht.setColumnView(0,33)
	sht.setColumnView(1,20)
	# Fill in the table
	for i in range(len(outputJuncs)):
			juncName = outputJuncs[i]._name
			juncPeak = juncPeakDict[juncName]
			unregPeak = round(juncPeak.getUnregPeak(),-2)
			#Need to use the modeled observed flow, just in case time step isn't consistent
			#E.g. "Observed Data" is hourly, but simulation timestep is daily
			#The modeled observed flow should match the actual observed anyways
			#obsPeak = round(juncPeak.getObsPeak(),-2)
			obsPeak = round(juncPeak.getModeledObsPeak(),-2)
			flowDiff = unregPeak - obsPeak
			insertCell(sht,5+i,colIdx, juncName)
			insertCell(sht,5+i,colIdx+1,flowDiff)
			for j in range(len(outputResvs)):
				resvName = outputResvs[j]._name
				if resvName in juncPeak.getContributingResvs():
					flowRed = juncPeak.getFlowReduction(resvName)
					insertCell(sht,5+i,colIdx+2+j, flowRed)
				else:
					insertCell(sht,5+i,colIdx+2+j, "x")
	wkbk.write()
	wkbk.close()
	return None

def runMiniSimulations(altNameObs, altNameUnreg, outDssFile, outExcelFile, outputJuncFile, outputResvFile, bar, txtArea):
	'''
	Runs the simulations with and without each reservoir, saves the results to dss, 
	and then outputs to excel
	It will use the output from the observed and unregulated model runs directly when possible to save time
	It will model natural lake operations at natural lakes that are downstream of
	 other projects (e.g. ALF operation gets adjusted for with/without HGH)
	The Observed and Unregulated alternatives must be based off the same network
	@altNameObs     string    The alternative that models observed flows (e.g "Observed")
	@altNameUnreg   string    The alternative that models unregulated flows (with natural lake effects)
	@outDssFile     string    Pathname to the desired output dss file
	@outExcelFile   string    The XLS file to output to (must be xls)
	@outputJuncFile string    The input txt file with the junctions for detailed output
	@outputResvFile string    The input txt file with the reservoirs for detailed output
	@bar            JProgressBar
	@txtArea        JTextArea Must have a function defined called "printToGUI"
	'''
	
	msg = "----------------------------------------------------------------------"
	msg += "\nComputing Mini-Simulations"
	msg += "\nOutput DSS File:                       %s" %outDssFile
	msg += "\nOutput Excel File:                     %s" %outExcelFile
	msg += "\nObserved Alternative:                  %s" %altNameObs
	msg += "\nUnregulated Alternative:               %s" %altNameUnreg
	txtArea.printToGUI("Computing Mini-Simulations...")
	logging.info(msg)
	simPeriod = cResSim.getSimulation()
	simDssFile = simPeriod.getOutputDSSFilePath()
	startTime, endTime, lookbackTime = cResSim.getResSimTimewindow(simPeriod)
	#Load up the 2 alternatives as RssRun objects
	msg = "Loading alternatives..."
	txtArea.printToGUI(msg)
	logging.info(msg)
	run = cResSim.getSpecificRun(simPeriod, altNameObs) #RssSimRun
	network = cResSim.getNetwork(run)
	#To get regulated output TSDataSet, need to get at the RssRun object (RssAlt doesn't work)
	rssRunName = run.getKey() #e.g. Test-----0
	#Loading this the first time can take a while...
	rssRunObs = cResSim.getRssRun(rssRunName) 
	#repeat for unreg
	run = cResSim.getSpecificRun(simPeriod, altNameUnreg)
	rssRunName = run.getKey() #e.g. Test-----0
	rssRunUnreg = cResSim.getRssRun(rssRunName) 
	#check to make sure the time steps agree
	if rssRunUnreg.getAlternative().getTimestep() != rssRunObs.getAlternative().getTimestep():
		errMsg = "The selected unreg and observed alternatives have different time steps"
		errMsg += "\nThe 2 alternatives must have a consistent time step!"
		txtArea.printToGUI(errMsg)
		logging.error(errMsg)
		return None
	# Check to see if excel file is open
	if os.path.exists(outExcelFile):
		try: os.remove(outExcelFile) # Delete the output file if it exists
		except: # it might be open, check it out; otherwise, don't worry about deleting it
			if not cFile.checkIfFileOpen(outExcelFile):
				txtArea.printToGUI("Could not open file! Please close the file and try again:\n%s" %outExcelFile)
				return None
	#Open up the input text files
	msg = "Processing input text file with junction names..."
	logging.info(msg)
	txtArea.printToGUI(msg)
	logging.info("\t%s" %outputJuncFile)
	juncList = cFile.fileOpenReadClose(outputJuncFile)
	juncList = cFile.stripOutCommentLines(juncList)
	msg = "Processing input text file with reservoir names..."
	logging.info(msg)
	txtArea.printToGUI(msg)
	logging.info("\t%s" %outputResvFile)
	resvList = cFile.fileOpenReadClose(outputResvFile)
	resvList = cFile.stripOutCommentLines(resvList)
	##############################################################################
	# Before we go too far, check the input text files to make sure all elements exist
	failElems = []
	outputJuncs = [] #list of JunctionElements
	resvsToRun = [] #list of ReservoirElements
	for resvName in resvList:
		resvElem = network.findReservoir(resvName)
		if not resvElem: failElems.append(resvName)
		elif resvName in reregDict.values(): continue #don't do reregs
		else: resvsToRun.append(resvElem)
	for juncName in juncList:
		juncElem = network.findJunction(juncName)
		if juncElem is None: failElems.append(juncName)
		else: outputJuncs.append(juncElem)
	if failElems != []:
		msg += "\nThe following elements specified in the text files do not exist in the model:"
		for failElem in failElems: msg += "\n\t%s" %failElem
		logging.error(msg)
		txtArea.printToGUI(msg)
		return None
	#Open up DSS Files
	simDss = DSS.open(simDssFile, lookbackTime, endTime)
	outDss = DSS.open(outDssFile, lookbackTime, endTime)
	##############################################################################
	msg = "Retrieving observed and unreg peak flows for reservoirs..."
	logging.info(msg)
	txtArea.printToGUI(msg) 
	resvPeakDict = getResvPeakFlows(rssRunObs, simDss, resvsToRun, bar, txtArea)
	if not resvPeakDict: 
		logging.error("COMPUTE FAILED")
		txtArea.printToGUI("COMPUTE FAILED")
		return None
	##############################################################################
	msg = "Retrieving observed and unreg peak flows for junctions..."
	logging.info(msg)
	txtArea.printToGUI(msg)
	juncPeakDict = getJuncPeakFlows(rssRunObs, rssRunUnreg, simDss, outDss, outputJuncs, bar, txtArea)
	if not juncPeakDict: 
		logging.error("COMPUTE FAILED")
		txtArea.printToGUI("COMPUTE FAILED")
		return None
	##############################################################################
	# run the "without" simulations
	msg = "Running 'without' simulations..."
	logging.info(msg)
	txtArea.printToGUI(msg)
	juncPeakDict = runResvSimulations(rssRunObs, rssRunUnreg, simDss, outDss, resvsToRun, outputJuncs, juncPeakDict, False, bar, txtArea)
	if not juncPeakDict:
		logging.error("COMPUTE FAILED")
		txtArea.printToGUI("COMPUTE FAILED")
		return None
	##############################################################################
	# run the "with" simulations
	msg = "Running 'with' simulations..."
	logging.info(msg)
	txtArea.printToGUI(msg)
	juncPeakDict = runResvSimulations(rssRunObs, rssRunUnreg, simDss, outDss, resvsToRun, outputJuncs, juncPeakDict, True, bar, txtArea)
	if not juncPeakDict:
		logging.error("COMPUTE FAILED")
		txtArea.printToGUI("COMPUTE FAILED")
		return None
	# export to excel
	exportToExcel(outExcelFile, outputJuncs, resvsToRun, juncPeakDict, resvPeakDict, bar, txtArea)
	bar.setValue(100)
	msg = "Output DSS File: "+outDssFile
	msg +="\nOutput XLS File: "+outExcelFile
	msg +="\nCompute Complete!"
	logging.info(msg)
	txtArea.printToGUI(msg)
	simDss.close()
	outDss.close()
	return None
	
def unpackChart80CSV(chart80CSV):
	'''
	Function to interpret the Chart 80 CSV file
	After comment lines at the top, the first column contains all of the output junctions (typically just TDA)
	Each subsequent column represents a Chart 80 simulation, with the name of the simulation at the top
	The rows under each column contain the list of projects (reservoir or diversion) to include in the simulation 
	@chart80CSV  string  The location of the csv file
	'''
	lines = cFile.fileOpenReadClose(chart80CSV)
	lines = cFile.stripOutCommentLines(lines)
	altNames = []
	outputJuncNames = []
	chart80Dict = {} #key is the alternative name, value is a list of all projects in the alternative
	for i in range(len(lines)):
		fields = lines[i].split(",")
		if i == 0: #1st line has names of alternatives
			for j in range(1, len(fields)):
				altNames.append(fields[j].strip())
				chart80Dict[fields[j].strip()] = []
		else:
			if fields[0].strip() != "":
				outputJuncNames.append(fields[0].strip())
			for j in range(1,len(fields)):
				projName = fields[j].strip()
				if projName != "": #the project is defined
					chart80Dict[altNames[j-1]].append(projName)
	return outputJuncNames, chart80Dict
	
def runAllChart80Simulations(altNameObs, altNameUnreg, outDssFile, inputCSVFile, bar, txtArea):
	'''
	Runs the Chart 80 simulations--each simulation incrementally adds in projects to the unreg run
	Saves the results to dss
	The results from DSS can then be pasted into the spreadsheet that makes the pretty graphs
	It will use the output from the observed and unregulated model runs directly when possible to save time
	It will model natural lake operations at natural lakes that are not in the list of projects
	The Observed and Unregulated alternatives must be based off the same network
	@altNameObs     string    The alternative that models observed flows (e.g "Observed")
	@altNameUnreg   string    The alternative that models unregulated flows (with natural lake effects)
	@outDssFile     string    Pathname to the desired output dss file
	@inputCSVFile   string    The input csv file with the simulation definitions
	@bar            JProgressBar
	@txtArea        JTextArea Must have a function defined called "printToGUI"
	'''
	
	msg = "----------------------------------------------------------------------"
	msg += "\nComputing Chart 80 Simulations"
	msg += "\nOutput DSS File:                       %s" %outDssFile
	msg += "\nObserved Alternative:                  %s" %altNameObs
	msg += "\nUnregulated Alternative:               %s" %altNameUnreg
	txtArea.printToGUI("Computing Chart 80 Simulations...")
	logging.info(msg)
	simPeriod = cResSim.getSimulation()
	simDssFile = simPeriod.getOutputDSSFilePath()
	startTime, endTime, lookbackTime = cResSim.getResSimTimewindow(simPeriod)
	#Load up the 2 alternatives as RssRun objects
	msg = "Loading alternatives..."
	txtArea.printToGUI(msg)
	logging.info(msg)
	run = cResSim.getSpecificRun(simPeriod, altNameObs) #RssSimRun
	#To get regulated output TSDataSet, need to get at the RssRun object (RssAlt doesn't work)
	rssRunName = run.getKey() #e.g. Test-----0
	#Loading this the first time can take a while...
	rssRunObs = cResSim.getRssRun(rssRunName) 
	#repeat for unreg
	run = cResSim.getSpecificRun(simPeriod, altNameUnreg)
	rssRunName = run.getKey() #e.g. Test-----0
	rssRunUnreg = cResSim.getRssRun(rssRunName) 
	network = cResSim.getNetwork(run)
	#check to make sure the time steps agree
	if rssRunUnreg.getAlternative().getTimestep() != rssRunObs.getAlternative().getTimestep():
		errMsg = "The selected unreg and observed alternatives have different time steps"
		errMsg += "\nThe 2 alternatives must have a consistent time step!"
		txtArea.printToGUI(errMsg)
		logging.error(errMsg)
		return None
	#Import the input csv file
	msg = "Processing input csv file with Chart 80 simulation definitions..."
	logging.info(msg)
	txtArea.printToGUI(msg)
	logging.info("\t%s" %inputCSVFile)
	outputJuncNames, chart80Dict = unpackChart80CSV(inputCSVFile)
	chart80AltNames = chart80Dict.keys()
	##############################################################################
	# Before we go too far, check the input files to make sure all elements exist
	failElems = []
	outputJuncs = [] #list of JunctionElements
	resvsToRun = {} #key is alt name, value is list of ReservoirElements
	diversionsToRun = {} #key is alt name, value is list of DiversionElements
	for juncName in outputJuncNames:
		juncElem = network.findJunction(juncName)
		if not juncElem: failElems.append(juncName)
		else: outputJuncs.append(juncElem)
	for altName in chart80AltNames:
		projectList = chart80Dict[altName]
		resvsToRun[altName] = []
		diversionsToRun[altName] = []
		logging.info("\n'%s' Alternative Projects:" %altName)
		for projectName in projectList:
			logging.info("     %s" %projectName)
			#The project can either be a reservoir or a diversion
			resvElem = network.findReservoir(projectName)
			divElem = network.findDiversion(projectName)
			if resvElem:
				resvsToRun[altName].append(resvElem)
			elif divElem:
				diversionsToRun[altName].append(divElem)
			else:
				failElems.append(projectName)
	if failElems != []:
		msg = "\nThe following elements specified in the csv file do not exist in the model:"
		for failElem in failElems: msg += "\n\t%s" %failElem
		logging.error(msg)
		txtArea.printToGUI(msg)
		return None
	#Open up DSS Files
	simDss = DSS.open(simDssFile, lookbackTime, endTime)
	outDss = DSS.open(outDssFile, lookbackTime, endTime)
	##############################################################################
	# run the "without" simulations
	msg = "Running Chart 80 simulations (compute order does not matter)..."
	logging.info(msg)
	txtArea.printToGUI(msg)
	#Set up the time series bank that will hold read time series so we don't have to read/write continually
	tsBank = cResSim.tsmBank()
	for i in range(len(chart80AltNames)):
		altName = chart80AltNames[i]
		txtArea.printToGUI(" Alternative %s of %s: %s" %(i+1, len(chart80AltNames), altName))
		resvList = resvsToRun[altName]
		diversionList = diversionsToRun[altName]
		tsBank = runChart80Simulation(rssRunObs, rssRunUnreg, simDss, outDss, resvList, diversionList, outputJuncs, altName, tsBank, bar, txtArea)
		if not tsBank:
			logging.error("COMPUTE FAILED")
			txtArea.printToGUI("COMPUTE FAILED")
			return None
	tsBank.close()
	bar.setValue(100)
	msg = "Output DSS File: "+outDssFile
	msg +="\nCompute Complete!"
	logging.info(msg)
	txtArea.printToGUI(msg)
	simDss.close()
	outDss.close()
	return None
	
