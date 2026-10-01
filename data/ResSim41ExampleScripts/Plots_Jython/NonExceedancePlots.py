################################################################################
# NonExceedancePlots.py
# Ryan Cahill, Portland District March 2013
# Jython script to prepare exceedance plots from a completed ResSim ensemble run
# Process:
#		1. Retrieve output ResSim ensemble data at specified elements
#		2. Do a cyclic analysis on the data
#		3. Create formatted non-exceedance plots and save to .png files
# Must be launched from within the simulation module of ResSim after a compute!
################################################################################
# IMPORTS
from __future__     import with_statement
from decimal                            import Decimal
from hec.data.cwmsRating       import RatingSet
from hec.hecmath                    import TimeSeriesMath
from hec.io                               import TimeSeriesContainer
from hec.heclib.dss                  import HecDss
from hec.heclib.util                  import HecTime
from hec.dataui.tx                    import TsContainerDataSourceList
from hec.dataui.tx.awt             import VerifyDataDlg
from hec.dataTable                  import HecDataTableToExcel
from hec.data.cwmsRating.io  import TableRatingContainer
from hec.dssgui                       import ListSelection
from hec.script                        import MessageBox, Constants, Plot, Tabulate, AxisMarker
from java.awt                          import BorderLayout, GridLayout, FlowLayout, Toolkit, GraphicsEnvironment, Rectangle, Color, Font
from java.awt.event                import ActionListener, FocusListener
from java.io                            import FileOutputStream, IOException
from java.lang                        import System
from java.text                        import SimpleDateFormat
from java.util                         import TimeZone
from javax.swing                   import JDialog, JCheckBox, JComboBox, JPanel, JButton, JOptionPane, JScrollPane, BoxLayout, JLabel, JTextField, SwingConstants, ScrollPaneConstants
from javax.swing.border       import EmptyBorder
from rma.services                 import ServiceLookup
from rma.swing                    import DateChooser
from time                             import mktime, localtime
from timeit                           import default_timer
from hec.script             import AxisMarker
import DBAPI, datetime, time, calendar, inspect, java, os, sys, traceback, math, shutil, logging, getpass
import javax.swing.JFrame;
import java.lang
from com.rma.client import Browser
from hec.script     import *
from hec.script.Constants import TRUE, FALSE
import os, string, time
print "\nBeginning Script"

# END IMPORTS
def output(msg="") :
	'''
	Output to console log
	'''
	print ("%s : %s" % (progname, msg))
def error(msg) :
	'''
	Outputs an error message and rasies an exception
	'''
	output(msg)
	raise Exception(msg)
	
def chktab(tab) :
	'''
	Checks that the "Modeling" tab is selected
	'''
	if tab.getTabTitle() != "Modeling" : 
		msg = "The Modeling tab must be selected"
		output("ERROR : %s" % msg)
		raise Exception(msg)
	 
def chkfcst(fcst) :
	'''
	Checks that a forecast is open
	'''
	if fcst is None : 
		msg = "A forecast must be open"
		output("ERROR : %s" % msg)
		raise Exception(msg)
try :
	try :
################## Stection-Start ####################################################################
## This section finds the current forecast.dss file (i.e. active forecast) ##
		
		## Get the current forecast ##
		frame = Browser.getBrowser().getBrowserFrame()
		proj = frame.getCurrentProject()
		pane = frame.getTabbedPane()
		tab = pane.getSelectedComponent()
		chktab(tab)
		fcst = tab.getForecast()
		chkfcst(fcst)
		
		fcstTimeWindowString = str(fcst.getRunTimeWindow())
		fcstNames = fcst.getForecastRunNames()
		fcstRun = fcst.getForecastRun(fcstNames[0])
		fcstRunKey = fcstRun.getKey()
		
		dssfile = fcst.getOutDssPath()
		cwmsFile = HecDss.open(dssfile)
		
		#print 'fcstTimeWindowString : %s' %(fcstTimeWindowString)
		important_times = [ i.strip(' ') for i in fcstTimeWindowString.split(';') ]
		start_time, forecast_time, end_time = important_times[0], important_times[1], important_times[2]
		
		cwmsFile.setTimeWindow(start_time, end_time)
################################################################################
# USER INPUT

#curYear = 3000 #override

# END USER INPUT
################################################################################
# CLASS DEFINITIONS

class CyclicCollection:
	# Class that takes a collection dataset and does cyclic analysis on it
	def __init__(self, name, percentiles=[]):
		self.name = name
		self.hasOverride = False # if the values of all percentiles are to be overriden for a period of time (e.g. lookback)
		self.Override = None
		self.hasRC = False # Rule curve zone
		self.RC = None
		self.percentiles = percentiles # intended to be a list like [.05,.95]
		self.rawTSCs = [] # list of timeseries containers
		self.cyclicTimes = [] # list of cyclic analysis times
		self.cyclicData = {} # big data array that has all the values at all times
		self.cyclicTSCs = [] # list of time series containers that have done cyclic analysis
		self.numYears = 0
		self.origPath = ""
	def setPercentiles(self, pcs):
		self.percentiles = pcs
	def addData(self, tsc):
		self.rawTSCs.append(tsc)
		self.numYears += 1
	def addRuleCurve(self, tsc):
		self.RC = tsc
		self.hasRC = True
	def addOverride(self, tsc):
		self.Override = tsc
		self.hasOverride = True
	def applyOverride(self):
		if self.hasOverride:
			# override all the values of the computed cyclic analysis with this time series
			for cyclicTSC in self.cyclicTSCs:
				for i in range(len(cyclicTSC.times)):
					if cyclicTSC.times[i] in self.Override.times:
						idx = self.Override.times.index(cyclicTSC.times[i])
						cyclicTSC.values[i] = self.Override.values[idx] 
	def prepTSC(self, tscTemplate):
		tsc = TimeSeriesContainer()
		tsc.times = self.cyclicTimes
		tsc.numberValues = len(tsc.times)
		tsc.units = tscTemplate.units
		tsc.type = tscTemplate.type
		self.origPath = tscTemplate.fullName
		tsc.fullName = tscTemplate.fullName # should be overriden later
		dssPath = DSSPathString(tscTemplate.fullName)
		dssPath.setFPart("Cyclic Analysis")
		tsc.fullName = dssPath.getPathname()
		return tsc
	def organizeData(self):
		self.cyclicTimes = list(self.rawTSCs[0].times)
		for i in range(len(self.cyclicTimes)):
			self.cyclicData[self.cyclicTimes[i]] = []
			for j in range(len(self.rawTSCs)):
				self.cyclicData[self.cyclicTimes[i]].append(self.rawTSCs[j].values[i])
			self.cyclicData[self.cyclicTimes[i]].sort()						
	def runCyclicAnalysis(self):
		self.organizeData()
		cyclicTSC = self.prepTSC(self.rawTSCs[0])
		dssPathBase = str(cyclicTSC.fullName)
		for k in range(len(self.percentiles)):
			pc = self.percentiles[k]
			idx = int(round(pc*(self.numYears-1),0)) 
			pcVals = []
			for i in range(len(self.cyclicTimes)):
				pcVals.append(self.cyclicData[self.cyclicTimes[i]][idx])
			cyclicTSC.values = pcVals
			dssPath = DSSPathString(dssPathBase)
			dssPath.setCPart("%s-%.0f%s" %(dssPath.getCPart(), pc*100,'%'))
			cyclicTSC.fullName = dssPath.getPathname()
			self.cyclicTSCs.append(cyclicTSC.clone())
		return self.cyclicTSCs
	def getCyclicTSC(self, pct):
		if pct not in self.percentiles: 
			print "ERROR! The percentile specified is not in the list"
			return -1
		idx = self.percentiles.index(pct)
		cyclicTSC = self.cyclicTSCs[idx]
		return cyclicTSC
	def writeAll(self, dssFile):
		# writes all cyclic records to an ALREADY OPEN dssFile (HecDss)
		for cyclicTSC in self.cyclicTSCs:
			dssFile.put(cyclicTSC)	

class CyclicCollectionPlot:
	# Class for generating plots of cyclic collections
	def __init__(self, cc):
		self.cc = cc # Should be a CyclicCollection object
		self.plot = Plot.newPlot("") # hec.gfx2d.G2dDialog
		self.layout = Plot.newPlotLayout() # hec.gfx2d.PlotLayout
		self.view = self.layout.addViewport(100.) #hec.gfx2d.ViewportLayout
		self.lcDict = lcDict # line color dictionary (expected to be defined earlier)
		self.lwStd = 2. # standard line weight
	def setSize(self, x, y):
		self.plot.setSize(x,y)
	def setTitle(self, titleStr):
		self.plot.setPlotTitleText(titleStr)
		title = self.plot.getPlotTitle()
		title.setFont("Arial Black")
		title.setFontSize(18)
		self.plot.setPlotTitleVisible(True)
	def setTimeOfForecast(self, timeStr):
		# sets a vertical line marker for the time of forecast
		# e.g. timeStr = "30Jan3001 2400"
		marker = G2dMarkerProperties()
		marker.setHasLabel(True)
		marker.setLabel("Time of Forecast")
		marker.setLabelPosition(1) # to the right of the vertical line
		marker.setLabelAlignment(1) # right alignment (top of screen)
		marker.setDrawOnAxis(0) # 0 = x axis, 1 = y axis
		marker.setDrawLine(True)
		marker.setDrawLabel(True)
		marker.setLinePattern([10.0,4.0]) # 10 pixels colored followed by 4 uncolored
		hTime = HecTime(timeStr, HecTime.MINUTE_INCREMENT)
		marker.setMarkerValue(hTime.value())
		self.vp.addAxisMarker(marker)			
	def setGrid(self, dotPat):
		# dotPat = list of floats, 1st entry is solid pixes, 2nd entry is empty pixels
		panel = self.plot.getPlotpanel()
		panel.setHorizontalViewportSpacing(0)
		prop = self.vp.getProperties()		
		prop.setMajorXGridStyle(dotPat)
		prop.setMajorYGridStyle(dotPat)		
	def setYAxisTitle(self, yTitle):
		yaxis = self.vp.getAxis("Y1")
		yaxis.setLabel(yTitle)
	def addCurves(self):
		for i in range(len(self.cc.cyclicTSCs)-1,-1,-1): # loop backwards
			self.view.addCurve("Y1", self.cc.cyclicTSCs[i])	
		self.plot.configurePlotLayout(self.layout)
		self.plot.setSize(1000, 800)
		self.vp = self.plot.getViewport(0) # hec.gfx2d.Viewport
	def save(self, fName):
		# must have done "showPlot()" before you can save to file!
		if not os.path.exists(os.path.dirname(fName)):
			os.makedirs(os.path.dirname(fName))
		self.plot.saveToPng(fName)
	def show(self):
		self.plot.showPlot()
	def close(self):
		self.plot.close()	
	def generateCyclicPlot(self, titleString, legendParam, startTimeStr):
		# function to generate a nicely fomatted plot with the non-exceddances
		# startTimeStr = the start time of the simulation
		if self.cc.hasRC:
			self.view.addCurve("Y1", self.cc.RC)
		self.addCurves()
		if self.cc.hasRC:
			rcCurve = self.plot.getCurve(self.cc.RC) # hec.gfx2d.G2dLine
			rcCurve.setLineColor("black")
			rcCurve.setLineWidth(3.)
			#rcCurve.setLineStyle("Dash") # since the parameter is elev-zone, it auto-makes it dashed
			rcLabel = self.plot.getLegendLabel(self.cc.RC)
			rcLabel.setText("Rule Curve")			
		# The easy way of changing legend labels didn't work, so we have to do it the hard way
		legendProps = self.plot.getLegend().getProperties().getLegendItemProperties()#list of hec.gfx2d.G2dLabelDrawProp
		legendIdx = 0
		if self.cc.hasRC: legendIdx +=1
		for i  in range(len(self.cc.percentiles)-1,-1,-1): #loop backwards 
			pc = self.cc.percentiles[i]
			curve = self.plot.getCurve(self.cc.cyclicTSCs[i])
			if not self.lcDict.has_key(pc):
				MessageBox.showError("No line color defined for percentile: %s\nFix the 'lcDict' parameter in the script" %pc, "Error")
				sys.exit()
			curve.setLineColor(self.lcDict[pc])
			curve.setLineWidth(self.lwStd)
			# This approach doesn't work! need to do showPlot() first but I want to wait until the end
			#legendLabel = self.plot.getLegendLabel(self.cc.cyclicTSCs[i]) 
			#legendLabel.setText("%.0f%s %s Non-Exceedance" %(pc*100, '%', legendParam))
			legendProps[legendIdx].text = "%.0f%s %s Non-Exceedance" %(pc*100, '%', legendParam)
			legendIdx += 1
		self.plot.getLegend().refreshLegendItems()
		self.setTitle(titleString)		
		self.setYAxisTitle("%s (%s)" %(legendParam, self.cc.cyclicTSCs[0].units)) 
		self.setGrid([2.,8.])  #  grid pattern - 2 solid pixels followed by 8 blank ones
		self.setTimeOfForecast(startTimeStr)
		return self.plot
		
# END CLASS DEFINITIONS
################################################################################
# FUNCTION DEFINITIONS

def fileOpenReadClose(txtFileName):
	# function that opens a text file and reads the lines
	txtFile = open(txtFileName, 'r') 	 
	txtLines = txtFile.readlines()
	txtFile.close()
	return txtLines

def printMsgToFile(msg, txtFileName):
	# function that saves the text in msg (string) to txtFileName
	outFile = open(txtFileName, 'w')
	outFile.write(msg)
	outFile.close()
	return None
	
def rndStr(number, numDecimals):
	# returns a string of the number that has been rounded to numDecimals
	return str(round(number, numDecimals))
	
def printTSC(tsc) :
	# Prints out a time series container
	# tsc = TimeSeriesContainer
	for i in range(len(tsc.values)) :
		dateValue = HecTime()
		dateValue.set(tsc.times[i])
		print "  ", dateValue.toString(), int(tsc.values[i])
	return
	
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
			
def getResSimTimewindow(simulation) :
	runTimeWindow = simulation.getRunTimeWindow()
	startTime = runTimeWindow.getStartTimeString()
	endTime = runTimeWindow.getEndTimeString()
	lookbackTime = runTimeWindow.getLookbackTimeString()
	return startTime, endTime, lookbackTime

def getSimulation() :
	#Verify that ResSim is in the correct module and has simulation open
	module = ClientAppWrapper.getCurrentModule()
	if module.getName() != "Simulation" : 
		raise AssertionError, "ResSim is %s module, Simulation module is required" % `module`
	simulation = module.getSimulation()
	if not simulation :
		raise AssertionError, "Must have a simulation open."
	return simulation

def getSelectedRunsAndFparts() :
	module = ClientAppWrapper.getCurrentModule()
	if `module` != "Simulation" :
		msg = "ResSim is not in Simulation Module, exiting."
		print msg
		MessageBox.showError(msg, scriptName)
		return -1
	activeRun = None
	runs = module.getSimulationRuns()
	Fparts=[]
	selectedRuns = []
	for run in runs : 
		if run.isActiveRun() :
			activeRun = run
			activeFpart = run.getKey().split(":")[0]
			activeAlternativeName = run.getUserName()
		if run.isSelected() :
			selectedRuns.append(run)
			Fparts.append(run.getKey().split(":")[0])
	return module, activeRun, selectedRuns, Fparts, activeFpart, activeAlternativeName	

def getObservedDataPaths(network, activeFpart, activeAlternativeName):
	# Function to read the observed data .fits file for a particular alternative
	# Returns a dictionary with the keys as the data locations, and the values as the pathnames for the obs. data
	# network = RssSystem
	# activeFpart = string (e.g. IRRMnew_e-0)
	# activeAlternativeName = string (e.g. IRRMnew_e)
	# Find the .fits file
	runDir = network.getBaseDirectory() + "/"
	for root, dirs, files in os.walk(runDir):
		for f in files:
			ext = f.split(".")[-1]
			if ext == "fits" and activeFpart in f and "Obs." in f:
				rf = root+f
				break
	try: lines = fileOpenReadClose(rf)
	except: 
		m = "Could not find observed data .fits file for: %s in directory %s" %(activeFpart, runDir)
		print m
		MessageBox.showError(m, "Error")
		sys.exit()
	obsDataDict = {}	
	name = None
	for line in lines:
		if "TSrecord=" in line: name = None
		elif "TSRecord Name=" in line: name = line.split("=")[-1].strip()
		elif "ParamName=" in line: # Only get flow observed data
			if "Flow" not in line: name = None 
		elif "DssPathname=" in line and name:
			path = line.split("DssPathname=")[-1].strip().upper()
			obsDataDict[name] = path
	return obsDataDict

def getCollections(network, simDssFile):
	# returns a list of all the collections  existing in the output dss file (e.g. 001956, 001957)
	resv = network.getReservoirNames()[0] # random reservoir
	simDss = HecDss.open(simDssFile)
	# ResSim should always spit out pool outflow for a random reservoir
	paths = simDss.getCatalogedPathnames("B=%s-POOL C=FLOW-OUT" %resv)
	simDss.close()
	collectionList = []
	for path in paths:
		collectionNum = DSSPathString(path).getFPart().split("|")[0].split(":")[-1]
		try: float(collectionNum)
		except: continue # can't be coerced to a number
		if not collectionNum in collectionList: collectionList.append(collectionNum)
	return collectionList
	
# END OF FUNCTION DEFINITIONS
################################################################################
# PROCEED THROUGH THE STEPS 

)
# Take a quick detour to figure out which forecast percentile was used (e.g. median, 30%)
# This is looking for an exact pathname, so please don't change the base pathname!
#fcstPCPath = "//FORECAST TYPE/PERCENTILE//1DAY/DUMMY/"
#try:
	#fcstPC = simDss.get(fcstPCPath, True).values[0] # all the values should be equal, get the first one
#	fcstPCTitle = fcstPCDict[round(fcstPC,1)]
#except: fcstPCTitle = "" # Don't know what forecast type it was
# process all elements, but wait to show and save the plots until the very end
resvList = network.getReservoirNames()
juncList = network.getJunctionNames()
elemNames = list(resvList)
elemNames.extend(juncList)
elemNames.append("SYSTEM")
storTSCs = [] # list of time series containers for storage time series, one for each year
ccps = [] # plots to write out at the end
pngPaths = []
for elem in elemNames:
	if elem in resvList:
		elNames = [elem, elem+"_IN", elem+"_OUT"]
		bparts = [elem+"-Pool", elem+"_IN", elem+"_OUT"]
		params = ["ELEV", "FLOW", "FLOW"]
	elif elem in juncList:
		if "_IN" in elem or "_OUT" in elem: continue #deal with those in the reservoir loop
		elNames = [elem]
		bparts = [elem]
		params = ["FLOW"]
	elif elem == "SYSTEM":
		# tricky, deal with it after dealing with all others
		elNames = []
		bpart = []
		params = []
	else:
		MessageBox.showError("The element name: %s does not exist in the model" %elem,"Error")
		sys.exit()
	for elName, bpart, param in zip(elNames, bparts, params):
		el = network.findElement(elName)
		obsVec = el.getObsDataVector() # vector of strings (e.g. "~N36")
		if elem in juncList and not obsVec: continue # it's a junction with no observed data--forget it		
		print "Processing ", bpart
		cycColl = CyclicCollection(bpart+"-"+param, percentiles)
		for colNum in collectionList:
			outputPath = "//%s/%s//1DAY/C:%s|%s/" %(bpart.upper(), param, colNum, activeFpart.upper())
			tsc = simDss.get(outputPath, True) # the whole time window
			cycColl.addData(tsc)
		cycColl.runCyclicAnalysis()
		if "-Pool" in bpart:
			# add rule curve
			# Conservation zone is not equivalent to the rule curve, must read in from dss
			#outputPath =  "//%s-CONSERVATION/ELEV-ZONE//1DAY/C:%s|%s/" %(elem.upper(), collectionList[0], activeFpart.upper())
			# search the dss file for the proper record
			pathnames = rcDss.getCatalogedPathnames("B=%s" %elem.upper())
			if not pathnames: # no matches found
				MessageBox.showError("Could not locate rule curve for location: %s\nin DSS File:%s\nThere must be a record with a matching BPart!" %(elem, ruleCurveDssFile), "Error")
				sys.exit()
			tsc = rcDss.get(pathnames[0], lookbackTime, endTime) # assume there's only one match
			tsc.parameter = "ELEV-ZONE" # fake it out so that it will display a dash-dot line
			cycColl.addRuleCurve(tsc)			
			# save off the storage time series for later
			elevStorTable = getElevationStorageTable(elem, network)
			minActiveStor = elevStorTable.interpolate(min(tsc.values)) # assumes min of con is min of active storage
			for i in range(len(collectionList)):
				colNum = collectionList[i]
				outputPath =  "//%s/STOR//1DAY/C:%s|%s/" %(bpart.upper(), colNum, activeFpart.upper())
				tsc = simDss.get(outputPath, True)
				if i > len(storTSCs)-1: # the collection entry doesn't exist yet
					for j in range(len(tsc.values)):
						tsc.values[j] = (tsc.values[j] - minActiveStor)/1000. #kaf
					tsc.units = "kaf"
					tsc.fullName = "//SYSTEM/STOR//1DAY/C:%s|%s/" %(colNum, activeFpart.upper())
					storTSCs.append(tsc.clone())
				else: # add on the current storages 
					for j in range(len(tsc.values)):
						storTSCs[i].values[j] += (tsc.values[j] - minActiveStor)/1000. #kaf
		if obsVec:
			# next section assumes there is only one observed dataset per location
			obsCode = obsVec[0].split(":")[0] # obsVec[0] is something like "~N175:0"
			if obsCode in obsDataDict:
				#override lookback data
				tsc = simDss.get(obsDataDict[obsCode], lookbackTime, startTime) # only defined for the lookback period
				cycColl.addOverride(tsc)
				cycColl.applyOverride() # overrides the lookback period with the data
		cycColl.writeAll(simDss) # write to DSS
		ccp = CyclicCollectionPlot(cycColl)
		if elem in resvList: 
			if "_OUT" in elName: 
				plotParam = "Outflow"
				pngPath = "%s/Inflow-Outflow/%s_out_%s.png" %(network.getBaseDirectory(), elem, fcstPCTitle)
			elif "_IN" in elName: 
				plotParam = "Inflow"
				pngPath = "%s/Inflow-Outflow/%s_in_%s.png" %(network.getBaseDirectory(), elem, fcstPCTitle)
			else: 
				plotParam = "Elevation"
				pngPath = "%s/Elevation/%s_elev_%s.png" %(network.getBaseDirectory(), elem, fcstPCTitle)
			plotTitle = "%s LAKE %s\nNWRFC %s %s Forecast (%s)" %(elem.upper(), plotParam, startMonthName, curYear, fcstPCTitle)
		elif elem in juncList:
			plotTitle = "%s\nNWRFC %s %s Forecast (%s)" %(elem.upper(), startMonthName, curYear, fcstPCTitle)
			plotParam = "Flow"
			pngPath = "%s/Control_Points/%s_%s.png" %(network.getBaseDirectory(), elem, fcstPCTitle)
		ccp.generateCyclicPlot(plotTitle, plotParam, startTime)
		ccps.append(ccp)
		pngPaths.append(pngPath)
	if elem == "SYSTEM":
		print "Processing System Storage"
		plotTitle = "Total System Storage\nNWRFC %s %s Forecast (%s)" %(startMonthName, curYear, fcstPCTitle)
		plotParam = "Storage"
		pngPath = network.getBaseDirectory() + "/Elevation/syst_stor_%s.png" %fcstPCTitle
		cycColl = CyclicCollection("SYSTEM-STOR", percentiles)
		for storTSC in storTSCs:
			cycColl.addData(storTSC) # add the previously computed sum
		cycColl.runCyclicAnalysis()		
		cycColl.writeAll(simDss) # write to DSS
		ccp = CyclicCollectionPlot(cycColl)
		ccp.generateCyclicPlot(plotTitle, plotParam, startTime)
		ccps.append(ccp)
		pngPaths.append(pngPath)
# Done processing all the plots, now save them out all at once as pngs
print "Saving plots to file..."
for i in range(len(ccps)):
	ccp = ccps[i]
	ccp.show()
	ccp.save(pngPaths[i])
	ccp.close()
simDss.close()
rcDss.close()

msg  = "\nOutput files:"
msg += "\n\t " + network.getBaseDirectory()+"/Elevation"
msg += "\n\t " + network.getBaseDirectory()+"/Inflow-Outflow"
msg += "\n\t " + network.getBaseDirectory()+"/Control_Points"
print "----------------------------------------------------------------------"
print "DONE!"
print msg
print "----------------------------------------------------------------------"
MessageBox.showInformation(msg, "Compute Complete")