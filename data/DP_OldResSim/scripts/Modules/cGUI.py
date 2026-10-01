'''
cGUI Module
Contains code regarding GUIs
'''
from java.io import File
from java.lang import Runtime
from javax.swing import JProgressBar, JPanel, JFrame, JTextField, JTextArea, JScrollPane, JLabel, ButtonGroup, JRadioButton, JButton, JOptionPane, JFileChooser, JComboBox
from javax.swing import SwingWorker, SwingUtilities, AbstractAction
from javax.swing import BorderFactory, ImageIcon
from javax.swing.filechooser import FileNameExtensionFilter
from java.awt.event import ActionEvent, ActionListener
from java.awt import BorderLayout, GridLayout, Insets, Font, Dimension, Desktop
from java.util.concurrent import ExecutionException

from hec.script import Constants, MessageBox, ClientAppWrapper
from hec.client import ClientApp
from hec.heclib.util import HecTime
import os, sys, logging

#Custom imports
import cResSim, cCWMS, cUSGS, cDamPrev, cLocFlows, cFile


################################################################################
# STATIC INPUT
class TaskBackground(SwingWorker):
	# This class gets fed a function (func) and arguments (args) that it will run in a background thread
	# necessary for progress bars if you want them to update on the screen
	# Instantiate the class, and then do the ".execute()" function to run "doInBackground"
	# Does the "done()" method when doInBackground is finished
	def __init__(self, func, args):
		SwingWorker.__init__(self)
		self.func = func
		self.args = args
	def doInBackground(self):
		self.func(*self.args) # * unwraps the list into separate arguments
	def done(self):
		print "Done with TaskBackground"
		try:
			self.get() # raise exception if abnormal completion
		except ExecutionException, e: 
			logging.error(e.getCause())
			MessageBox.showError(str(e.getCause()), "Error!")                    
		#Print out where the logging went
		logFile = getCurrentLogFile()
		msg = "\nFinished logging to:\n%s" %logFile
		logging.info(msg)
		#If the task involved a JTextAreaAutoScroll, let the user know where the log went
		for a in self.args: 
			if isinstance(a, JTextAreaAutoScroll):
				a.printToGUI(msg)
				a.printToGUI("\n") #set the horizontal scroll back to the first line
		closeLogging()		
		
################################################################################
# CLASS DEFINITIONS
class frameMainSelector(JFrame):
	'''
	Class to provide a frame that allows any option to be computed
	Simply consists of buttons that will launch other frames, but they are in
	order so that the user knows the general order of the Damages Prevented process
	'''
	def __init__(self):
		# Retrieve all necessary ResSim simulation data
		self.simulation = cResSim.getSimulation()  # this makes the simulation object available and makes sure we are in the simulation module
		self.startTime, self.endTime, self.lookbackTime = cResSim.getResSimTimewindow(self.simulation)
		self.activeRun = cResSim.getActiveRun(self.simulation)
		self.simDssFile = self.simulation.getOutputDSSFilePath()
		self.network = self.activeRun.getRssSystem()
		self.allFparts = cResSim.getListOfOutputFParts(self.simulation)
		self.altNames = cResSim.getListOfAltNames(self.simulation) 
		
		# Set up the GUI Frame
		JFrame.__init__(self, "Selection Menu")
		pane = JPanel(BorderLayout(), border = BorderFactory.createEmptyBorder(20,20,20,20))
		title = JLabel("Damages Prevented", JLabel.CENTER)
		title.setFont(Font("Impact", Font.PLAIN, 36))		
		subtitle = JLabel("Selection Menu", JLabel.CENTER)
		subtitle.setFont(Font("Impact", Font.PLAIN, 36))
		pane.add(title, BorderLayout.NORTH)	
		pane.add(subtitle, BorderLayout.CENTER)	
		butP = JPanel(GridLayout(11,1))
		# Add all of the buttons that launch other menus
		but1 = buttonClose(self, "Extract CWMS Data", actionPerformed = self.cwmsBUT)
		but2 = buttonClose(self, "Extract USGS Data", actionPerformed = self.usgsBUT)
		but3 = buttonClose(self, "Recompute Reservoir Inflows", actionPerformed = self.recomputeInflowsBUT)
		but4 = buttonClose(self, "Transform Gage Data", actionPerformed = self.transformLocalBUT)
		but5 = buttonClose(self, "Compute Water Balance Locals at Modified Flow Points", actionPerformed = self.modFlowLocalBUT)
		but6 = buttonClose(self, "Disaggregate Modified Flow Point Locals", actionPerformed = self.disaggregateLocalBUT)
		but7 = buttonClose(self, "Compute Final Water Balance Locals", actionPerformed = self.localFlowBUT)
		but8 = buttonClose(self, "Create Verification Plots", actionPerformed = self.createVerfPlotsBUT)
		but9 = buttonClose(self, "Export To RAS", actionPerformed = self.RASExportBUT)
		but10 = buttonClose(self, "Run Mini-Simulations", actionPerformed = self.miniSimsBUT)
		but11 = buttonClose(self, "Generate Chart 80", actionPerformed = self.chart80BUT)
		butP.add(but1)
		butP.add(but2)
		butP.add(but3)
		butP.add(but4)
		butP.add(but5)
		butP.add(but6)
		butP.add(but7)
		butP.add(but8)
		butP.add(but9)
		butP.add(but10)
		butP.add(but11)
		
		pane.add(butP, BorderLayout.SOUTH)
		self.contentPane = pane
		self.pack()
		self.setLocationRelativeTo(None)
		self.getRootPane().setDefaultButton(but1)
		self.setVisible(True)
	
	def cwmsBUT(self, e):
		# Opens up another window to extract CWMS data
		extractFile = ClientApp.Workspace().makeAbsolutePath("shared/Extract_Lists_CWMS/ExtractList_CWMS.txt")
		outputDss = ClientApp.Workspace().makeAbsolutePath("shared/obsData.dss")
		frame = frameDataExtract(self.lookbackTime, self.endTime, extractFile, outputDss, "CWMS", title = "CWMS Extract")
		return frame
	def usgsBUT(self, e):
		# Opens up another window to extract USGS data
		extractFile = ClientApp.Workspace().makeAbsolutePath("shared/Extract_Lists_USGS/ExtractList_USGS.txt")
		outputDss = ClientApp.Workspace().makeAbsolutePath("shared/obsData.dss")
		frame = frameDataExtract(self.lookbackTime, self.endTime, extractFile, outputDss, "USGS", title = "USGS Extract")
		return frame
	def recomputeInflowsBUT(self,e):
		# Create and display the local flow transformation window
		outDssFile = ClientApp.Workspace().makeAbsolutePath("shared/reservoirInflows.dss")
		csvFile = ClientApp.Workspace().makeAbsolutePath("shared/Inflow_Recalc_Inputs/reservoirInflows.csv")
		frame = frameTransformLocals(self.lookbackTime, self.endTime, csvFile, outDssFile, 
		 "Reservoir", title = "Reservoir Inflows", obsDssFile = None)
		return frame
	def modFlowLocalBUT(self, e):
		# Create and display the local flowinator GUI
		outDssFile = ClientApp.Workspace().makeAbsolutePath("shared/Locals-ModifiedFlowPts.dss")
		frame = frameLocalFlowinator(simPeriod = self.simulation, altName=str(self.activeRun), dssFile=outDssFile)
		return frame
	def localFlowBUT(self, e):
		# Create and display the local flowinator GUI for the final compute
		#Get the default output dss file to pre-populate the GUI
		inflowDssFile = ClientApp.Workspace().makeAbsolutePath("shared/Locals-FinalWaterBalance.dss")
		frame = frameLocalFlowinator(simPeriod = self.simulation, altName=str(self.activeRun), dssFile=inflowDssFile)
		return frame
	def transformLocalBUT(self, e):
		# Create and display the local flow transformation window
		obsDssFile = ClientApp.Workspace().makeAbsolutePath("shared/obsData.dss")
		outDssFile = ClientApp.Workspace().makeAbsolutePath("shared/Locals-Transformed.dss")
		csvFile = ClientApp.Workspace().makeAbsolutePath("shared/Locals_Transformed_Inputs/Locals-Transformed.csv")
		frame = frameTransformLocals(self.lookbackTime, self.endTime, csvFile, outDssFile, 
		 "Transform", title = "Transformed Locals", obsDssFile = obsDssFile)
		return frame
	def disaggregateLocalBUT(self, e):
		# Create and display the local flow transformation window
		obsDssFile = ClientApp.Workspace().makeAbsolutePath("shared/obsData.dss")
		outDssFile = ClientApp.Workspace().makeAbsolutePath("shared/Locals-Disaggregated.dss")
		csvFile = ClientApp.Workspace().makeAbsolutePath("shared/Locals_Disaggregated_Inputs/Locals-Disaggregated.csv")
		frame = frameTransformLocals(self.lookbackTime, self.endTime, csvFile, outDssFile, 
		 "Disaggregated", title = "Disaggregated Locals", network = self.network)
		return frame
	def RASExportBUT(self, e):
		#Create and display the RAS export window
		resvDefaultFile = ClientApp.Workspace().makeAbsolutePath("shared/RAS_Export_Inputs/RAS-Reservoirs.list")
		juncDefaultFile = ClientApp.Workspace().makeAbsolutePath("shared/RAS_Export_Inputs/RAS-Junctions.list")
		dShiftDefaultFile = ClientApp.Workspace().makeAbsolutePath("shared/RAS_Export_Inputs/datumShifts.dat")
		outDssFile = ClientApp.Workspace().makeAbsolutePath("shared/RAS_Export.dss")
		ratingDssFile = ClientApp.Workspace().makeAbsolutePath("shared/RAS_Export_Inputs/NaturalRatingCurves.dss")
		frame = frameExportRAS(simPeriod=self.simulation, altName=str(self.activeRun), 
		 resvFile=resvDefaultFile, juncFile=juncDefaultFile, dShiftFile=dShiftDefaultFile, 
		 outputDss=outDssFile, ratingDss = ratingDssFile)
		return frame
	def miniSimsBUT(self, e):
		# Create and display the mini-simulations window
		txtDefaultFile = ClientApp.Workspace().makeAbsolutePath("shared/MiniSimulation_Inputs/outputJunctions.txt")
		rtxtDefaultFile = ClientApp.Workspace().makeAbsolutePath("shared/MiniSimulation_Inputs/outputReservoirs.txt")
		dssDefaultFile = ClientApp.Workspace().makeAbsolutePath("shared/MiniSimulations.dss")
		xlsDefaultFile = ClientApp.Workspace().makeAbsolutePath("shared/FlowReductions.xls")
		frame = frameMiniSimulations(self.altNames, txtDefaultFile, rtxtDefaultFile, dssDefaultFile, xlsDefaultFile)
		return frame
	def chart80BUT(self, e):
		# Create and display the Chart 80 window
		csvDefaultFile = ClientApp.Workspace().makeAbsolutePath("shared/Chart80/Chart80Input.csv")
		dssDefaultFile = ClientApp.Workspace().makeAbsolutePath("shared/Chart80/outputChart80.dss")
		frame = frameChart80(self.altNames, csvDefaultFile, dssDefaultFile)
		return frame
	def createVerfPlotsBUT(self, e) :
		# create and display the verification plots window
		resvDefaultFile = ClientApp.Workspace().makeAbsolutePath("shared/Plots/Plots-Reservoirs.list")
		juncDefaultFile = ClientApp.Workspace().makeAbsolutePath("shared/Plots/Plots-Junctions.list")
		frame = frameCreateVerfPlots(self.altNames, resvDefaultFile, juncDefaultFile)
		return frame

class frameDataExtract(JFrame):
	'''
	Class to provide a consistent frame for data extracts
	That holds the start/end times, text file with data to extract
	Output DSS File
	Need to implement an ActionListener on the "computeBUT" JButton to respond
	when the button is clicked
	'''
	def __init__(self, startTime, endTime, extractFile, outputDss, dataSource, title = "Data Extract"):
		'''
		@startTime		HecTime		The start time of the extract
		@endTime			HecTime		The end time of the extract
		@extractFile	String		Filename with data to extract
		@outputDss		String		output DSS filename
		@dataSource		String    The data source (CWMS or USGS)--governs what is launched
		@title				String		The title of this frame
		'''
		frame = JFrame.__init__(self, title)
		timeP = JPanel(GridLayout(5,1), border = BorderFactory.createEtchedBorder())
		timeP.add(JLabel("Extract time window (1 day buffer recommended)"))
		timeP.add(JLabel("Start Time"))
		startHTime = HecTime(startTime)
		startHTime.subtractDays(2)
		self.startTimeT = JTextField(startHTime.toString())
		timeP.add(self.startTimeT)
		timeP.add(JLabel("End Time"))
		endHTime = HecTime(endTime)
		endHTime.addDays(2)
		self.endTimeT = JTextField(endHTime.toString())
		timeP.add(self.endTimeT)
		# txt file with data to extract
		title = "Select TXT File with data to extract"
		browseTitle = "File with the data to extract:"
		txtFileP = panelTxtBrowseOpen(title, extractFile, browseTitle, "txt")
		self.txtFileT = txtFileP.txtT
		# output dss file
		title = "Output DSS File:"
		browseTitle = "Select output DSS file:"
		dssP = panelTxtBrowseOpen(title, outputDss, browseTitle, "dss")
		self.outDssT = dssP.txtT	
		# output timestep
		timeStepOptions = ["1HOUR","1DAY"]
		defaultStep = "1DAY"
		displayTxt = "Output Time Step:"
		timeStepP = panelDropDownBox(promptText=displayTxt, itemList=timeStepOptions, defaultItem=defaultStep)
		self.timeStepBox = timeStepP.box
		# buttons and frame setup
		if dataSource.upper() == "CWMS":
			func = self.runCWMSExtract
		else:
			func = self.runUSGSExtract
		butP = panelComputeCancel(self, func = func, buttonTitle = "Run Extract")
		cpane = JPanel(BorderLayout(5,5), border = BorderFactory.createEmptyBorder(20,20,20,20))
		cpane.add(timeP, BorderLayout.NORTH)
		cp = JPanel(BorderLayout())
		cp.add(txtFileP, BorderLayout.NORTH)		
		cp.add(dssP, BorderLayout.CENTER)
		cp.add(timeStepP, BorderLayout.SOUTH)
		cpane.add(cp, BorderLayout.CENTER)
		cpane.add(butP, BorderLayout.SOUTH)
		self.contentPane = cpane
		self.pack()
		self.setLocationRelativeTo(None)
		self.getRootPane().setDefaultButton(butP.computeBUT)
		self.visible = True
	def runCWMSExtract(self,e):
		# User wants to run a CWMS extract--let's do it
		# Formerly did it in a subprocess by launching a batch file		
		txtFile = self.txtFileT.getText()
		dssFile = self.outDssT.getText()
		startTime = self.startTimeT.getText().strip()
		endTime = self.endTimeT.getText().strip()
		timeStep = self.timeStepBox.getSelectedItem()
		self.dispose()
		# Make a new window with the progress
		frame = frameProgress()
		# Get the start time and end time of the extract in proper oracle format (25Dec2012 0000)
		startTimeStr = cCWMS.getOracleTimeString(HecTime(startTime))
		endTimeStr = cCWMS.getOracleTimeString(HecTime(endTime))
		# Set up the logging
		logFile = ClientApp.Workspace().makeAbsolutePath("logs/extract_CWMS.log")
		initializeLogging(logFile)
		# Launch the Extract
		args = [txtFile, dssFile, startTimeStr, endTimeStr, timeStep, frame.bar, frame.txtArea]
		tsk = TaskBackground(cCWMS.processCWMSPaths, args)
		tsk.execute()
	def runUSGSExtract(self,e):
		# User wants to run a CWMS extract--let's do it
		# Formerly did it in a subprocess by launching a batch file		
		txtFile = self.txtFileT.getText()
		dssFile = self.outDssT.getText()
		startTime = self.startTimeT.getText().strip()
		endTime = self.endTimeT.getText().strip()
		timeStep = self.timeStepBox.getSelectedItem()
		self.dispose()		
		# Make a new window with the progress
		frame = frameProgress()
		# Get the start time and end time of the extract in proper oracle format (25Dec2012 0000)
		startTimeStr = HecTime(startTime).date(4) #02Jun1985
		endTimeStr = HecTime(endTime).date(4)
		# Set up the logging
		logFile = ClientApp.Workspace().makeAbsolutePath("logs/extract_USGS.log")
		initializeLogging(logFile)
		# Launch the Extract
		args = [txtFile, dssFile, startTimeStr, endTimeStr, timeStep, frame.bar, frame.txtArea]
		tsk = TaskBackground(cUSGS.importUSGSData, args)
		tsk.execute()	

class frameLocalFlowinator(JFrame):
	# Class to pop up the main GUI and launch the compute of the local flows
	def __init__(self, simPeriod, altName, dssFile):
		'''
		@param simPeriod	SimulationPeriod	The currently active simulation
		@param altName		String						Name of the current alternative (e.g. "Observed", not "Observed--0")
		@param dssFile		String						Full path of the output dss file
		'''
		self.simPeriod = simPeriod
		self.startTime, self.endTime, self.lookbackTime = cResSim.getResSimTimewindow(simPeriod)
		JFrame.__init__(self, "Local Flow Computation")
		# Define the layout of the GUI and populate it with default things
		self.titleText = JLabel("Local Flow Calculator", JLabel.CENTER)
		self.titleText.setFont(Font("Old English Text MT", Font.PLAIN, 36))
		self.subtitle = JPanel(GridLayout(3,1))
		self.subtitle.add(JLabel("Version 2.0", JLabel.CENTER))
		self.subtitle.add(JLabel("February 2015", JLabel.CENTER))
		self.subtitle.add(JLabel("Ryan Cahill", JLabel.CENTER))
		titleP = JPanel(GridLayout(2,1))
		titleP.add(self.titleText)
		titleP.add(self.subtitle)
		altNames = cResSim.getListOfAltNames(simPeriod) 
		altTxt = "Alternative with Time Series Mapping to use:"
		altP = panelDropDownBox(promptText=altTxt, itemList=altNames, defaultItem=altName)
		self.altNameBox = altP.box
		#allowing negative locals
		negP = JPanel(BorderLayout())
		negP.add(JLabel("Allow negative locals? (typically YES to match observed)", JLabel.LEFT), BorderLayout.WEST)
		bg = ButtonGroup()
		self.yesBUT = JRadioButton("Yes", actionPerformed = self.radioButtonChange)
		self.noBUT = JRadioButton("No", actionPerformed = self.radioButtonChange)
		self.yesBUT.setSelected(True)
		self.allowNegatives = True # default is to allow negatives
		bg.add(self.yesBUT)
		bg.add(self.noBUT)
		radioP = JPanel(GridLayout(2,1))
		radioP.add(self.yesBUT)
		radioP.add(self.noBUT)
		radioP.setBorder(BorderFactory.createEtchedBorder())
		negP.add(radioP, BorderLayout.EAST)
		#output DSS File
		title = "Output DSS File:"
		browseTitle = "Select Text File with Output Reservoir Names"
		dssP = panelTxtBrowseOpen(title, dssFile, browseTitle, "dss")
		self.dssT = dssP.txtT
		self.helpBUT = JButton("Help")
		helpFile = ClientApp.Workspace().makeAbsolutePath("shared/LocalFlowCalculator.pdf")
		self.helpBUT.addActionListener(listenerOpenFile(fileToOpen=helpFile))
		#Add button panel
		butP = panelComputeCancel(self, func = self.runCompute)
		# add all the panels to the main panel
		pane = JPanel(BorderLayout(), border = BorderFactory.createEmptyBorder(20,20,20,20))
		pane.add(titleP, BorderLayout.NORTH)
		cP = JPanel(BorderLayout())
		cP.add(altP, BorderLayout.NORTH)
		cP2 = JPanel(BorderLayout())
		cP2.add(negP, BorderLayout.NORTH)
		cP2.add(dssP, BorderLayout.SOUTH)
		cP.add(cP2)
		pane.add(cP)
		pane.add(butP, BorderLayout.SOUTH)
		# Creates the GUI and shows it
		self.contentPane = pane
		imgFile = ClientApp.Workspace().makeAbsolutePath("images/rts24.gif")
		self.setIconImage(ImageIcon(imgFile).getImage())
		self.pack()
		self.setLocationRelativeTo(None) # Center of the screen
		self.getRootPane().setDefaultButton(butP.computeBUT)
		self.visible = True
	def runCompute(self, e):
		# compute the local flows, saving results to simulation.dss and inflow dss file
		altName = self.altNameBox.getSelectedItem() #get the desired alternative from user
		dssFile = self.dssT.getText() # get the desired dss file from user
		self.dispose() # get rid of the old GUI window
		# Make a new window with the progress
		frame = frameProgress()
		run = self.simPeriod.getSimulationRun(altName) #RssSimRun
		network = run.getRssSystem()
		simDssFile = self.simPeriod.getOutputDSSFilePath()
		# Set up the logging
		logFile = ClientApp.Workspace().makeAbsolutePath("logs/LocalFlows.log")
		initializeLogging(logFile)
		# launch the compute
		args = [network, altName, simDssFile, dssFile, self.allowNegatives, frame.bar, frame.txtArea]
		tsk = TaskBackground(cResSim.computeLocalFlows, args)
		tsk.execute()
	def radioButtonChange(self, e):
		if e.getSource().getText() == "Yes":
			self.allowNegatives = True
		else:
			self.allowNegatives = False

class frameTransformLocals(JFrame):
	'''
	Class to provide a consistent frame for transformation of local flows
	That holds the output Dss File, csv file, and timestep
	Need to implement an ActionListener on the "computeBUT" JButton to respond
	when the button is clicked
	'''
	def __init__(self, startTime, endTime, csvFile, outputDss, localType, title, obsDssFile = None, network = None):
		'''
		@startTime		HecTime		The start time of the extract
		@endTime			HecTime		The end time of the extract
		@extractFile	String		Filename with data to extract
		@outputDss		String		output DSS filename
		@localType    String    "TRANSFORM" or "DISAGGREGATE" or "RESERVOIR"--the local flow type to use
		@title				String		The title of this frame
		@obsDssFile   String    If provided, the DSS File with observed DSS. If omitted, not included in GUI
		@network      RssSystem The reservoir network to use
		'''
		self.network = network
		frame = JFrame.__init__(self, title)
		#time panel (not always used)
		timeP = JPanel(GridLayout(5,1), border = BorderFactory.createEtchedBorder())
		timeP.add(JLabel("Analysis time window"))
		timeP.add(JLabel("Start Time"))
		startHTime = HecTime(startTime)
		self.startTimeT = JTextField(startHTime.toString())
		timeP.add(self.startTimeT)
		timeP.add(JLabel("End Time"))
		endHTime = HecTime(endTime)
		self.endTimeT = JTextField(endHTime.toString())
		timeP.add(self.endTimeT)
		#alternative drop down (not always used)
		altNames = cResSim.getListOfAltNames(cResSim.getSimulation()) 
		altName = cResSim.getCurrentRssAltName()
		altTxt = "Alternative with Time Series Mapping to use:"
		altP = panelDropDownBox(promptText=altTxt, itemList=altNames, defaultItem=altName)
		self.altNameBox = altP.box
		# Observed data file:
		if obsDssFile:
			title = "DSS File with observed (gaged) data"
			browseTitle = "Select observed DSS file:"
			obsDssP = panelTxtBrowseOpen(title, obsDssFile, browseTitle, "dss")
			self.obsDssT = obsDssP.txtT
		# txt file with data to extract
		title = "CSV File with instructions for flow calculations:"
		browseTitle = "File with the instructions:"
		txtFileP = panelTxtBrowseOpen(title, csvFile, browseTitle, "csv")
		self.txtFileT = txtFileP.txtT
		# output dss file
		title = "Output DSS File:"
		browseTitle = "Select output DSS file:"
		dssP = panelTxtBrowseOpen(title, outputDss, browseTitle, "dss")
		self.outDssT = dssP.txtT	
		# output timestep
		timeStepOptions = ["1HOUR","1DAY"]
		defaultStep = "1DAY"
		displayTxt = "Output Time Step:"
		timeStepP = panelDropDownBox(promptText=displayTxt, itemList=timeStepOptions, defaultItem=defaultStep)
		self.timeStepBox = timeStepP.box
		# buttons and frame setup
		if localType.upper() == "TRANSFORM": 
			butP = panelComputeCancel(self, func = self.runTransformLocals)
		elif localType.upper() == "DISAGGREGATED": 
			butP = panelComputeCancel(self, func = self.runDisaggregatedLocals) 
		else: 
			butP = panelComputeCancel(self, func = self.runReservoirInflows) 
		cpane = JPanel(BorderLayout(5,5), border = BorderFactory.createEmptyBorder(20,20,20,20))
		#cpane.add(timeP, BorderLayout.NORTH)
		cp = JPanel(BorderLayout())
		cp.add(txtFileP, BorderLayout.NORTH)
		cp.add(dssP, BorderLayout.CENTER)
		bottomP = JPanel(BorderLayout())
		bottomP.add(timeStepP, BorderLayout.CENTER)
		if localType.upper() == "RESERVOIR":
			bottomP.add(altP, BorderLayout.SOUTH)
		cp.add(bottomP, BorderLayout.SOUTH)
		if obsDssFile: cpane.add(obsDssP,BorderLayout.NORTH)
		cpane.add(cp, BorderLayout.CENTER)
		cpane.add(butP, BorderLayout.SOUTH)
		self.contentPane = cpane
		self.pack()
		self.setLocationRelativeTo(None)
		self.getRootPane().setDefaultButton(butP.computeBUT)
		self.visible = True
	def runTransformLocals(self,e):
		# Launch the compute of "transformed" locals
		txtFile = self.txtFileT.getText()
		obsDssFile = self.obsDssT.getText()
		dssFile = self.outDssT.getText()
		timeStep = self.timeStepBox.getSelectedItem()
		startTime = self.startTimeT.getText()
		endTime = self.endTimeT.getText()
		self.dispose()
		# Make a new window with the progress
		frame = frameProgress()
		# Set up the logging
		logFile = ClientApp.Workspace().makeAbsolutePath("logs/locals_transformed.log")
		initializeLogging(logFile)
		# Launch the Extract
		args = [obsDssFile, dssFile, txtFile, timeStep, startTime, endTime, frame.bar, frame.txtArea]
		tsk = TaskBackground(cLocFlows.transformGageData, args)
		tsk.execute()
	def runDisaggregatedLocals(self,e):
		# Launch the compute of "disaggregated" locals
		txtFile = self.txtFileT.getText()
		dssFile = self.outDssT.getText()
		timeStep = self.timeStepBox.getSelectedItem()
		startTime = self.startTimeT.getText()
		endTime = self.endTimeT.getText()
		self.dispose()
		# Make a new window with the progress
		frame = frameProgress()
		# Set up the logging
		logFile = ClientApp.Workspace().makeAbsolutePath("logs/locals_disaggregated.log")
		initializeLogging(logFile)
		# Launch the Extract
		args = [self.network, dssFile, txtFile, timeStep, startTime, endTime, frame.bar, frame.txtArea]
		tsk = TaskBackground(cLocFlows.disaggregateLocals, args)
		tsk.execute()
	def runReservoirInflows(self,e):
		# Launch the compute of reservoir inflows
		txtFile = self.txtFileT.getText()
		dssFile = self.outDssT.getText()
		timeStep = self.timeStepBox.getSelectedItem()
		altName = self.altNameBox.getSelectedItem()
		startTime = self.startTimeT.getText()
		endTime = self.endTimeT.getText()
		self.dispose()
		# Make a new window with the progress
		frame = frameProgress()
		# Set up the logging
		logFile = ClientApp.Workspace().makeAbsolutePath("logs/reservoirInflows.log")
		initializeLogging(logFile)
		# Launch the Extract
		args = [altName, txtFile, dssFile, timeStep, frame.bar, frame.txtArea]
		tsk = TaskBackground(cResSim.recomputeResvInflows, args)
		tsk.execute()

class frameCreateVerfPlots(JFrame):
	# Class to pop up the main GUI and launch the compute of the with/without simulations
	def __init__(self, altNames, rFile, jFile):
		# save the input arguments
		self.resvFile = rFile
		self.juncFile = jFile
		JFrame.__init__(self, "Create Verification Plots")
		# Define the layout of the GUI and populate it with default things
		self.titleText = JLabel("Create Verification Plots", JLabel.CENTER)
		self.titleText.setFont(Font("Magneto", Font.PLAIN, 36))
		titleP = JPanel(BorderLayout())
		titleP.add(self.titleText)
		# Alternative combo boxes
		# try to find defaults based on name
		#altNameObs = cResSim.getCurrentRssAltName()
		altNameObs = None
		altNameUnreg = None
		for nm in altNames:
			if "UNR" in nm.upper(): altNameUnreg = nm
			if "OBS" in nm.upper(): altNameObs = nm
		altTxt = "Observed Alternative:"
		obsvAltP = panelDropDownBox(promptText=altTxt, itemList=altNames, defaultItem=altNameObs)
		self.obsvAltBox = obsvAltP.box
		altTxt = "Unregulated Alternative:"
		unregAltP = panelDropDownBox(promptText=altTxt, itemList=altNames, defaultItem=altNameUnreg)
		self.unregAltBox = unregAltP.box
		# text file with reservoirs list to plot
		title = "Text File with Reservoirs to Plot:"
		browseTitle = "Select Text File with Reservoirs to Plot:"
		resvFileP = panelTxtBrowseOpen(title, self.resvFile, browseTitle, "list")
		self.resvFileT = resvFileP.txtT
		# text file with junctions list to plot
		title = "Text File with Junctions to Plot:"
		browseTitle = "Select Text File with Junctions to Plot:"
		juncFileP = panelTxtBrowseOpen(title, self.juncFile, browseTitle, "list")
		self.juncFileT = juncFileP.txtT
		# frame setup
		butP = panelComputeCancel(self, func = self.runCreateVerfPlots, buttonTitle = "Create Plots")
		cpane = JPanel(BorderLayout(5,5), border = BorderFactory.createEmptyBorder(20,20,20,20))
		cp = JPanel(BorderLayout())
		altsP = JPanel(BorderLayout())
		altsP.add(obsvAltP, BorderLayout.NORTH)
		altsP.add(unregAltP, BorderLayout.CENTER)
		fileP = JPanel(GridLayout(2,1))
		fileP.add(resvFileP)
		fileP.add(juncFileP)
		cp.add(altsP, BorderLayout.NORTH)
		cp.add(fileP, BorderLayout.CENTER)
		cp.add(butP, BorderLayout.SOUTH)
		#cp.add(bottomP, BorderLayout.SOUTH)
		#cpane.add(titleP, BorderLayout.NORTH)
		cpane.add(cp, BorderLayout.CENTER)
		self.contentPane = cpane
		#imgFile = ClientApp.Workspace().makeAbsolutePath("shared/Jython/ras18.gif")
		#self.setIconImage(ImageIcon(imgFile).getImage())
		self.pack()
		self.setLocationRelativeTo(None)
		self.getRootPane().setDefaultButton(butP.computeBUT)
		self.visible = True
	def runCreateVerfPlots(self, e) :
		# set arguments
		obsvAltName = self.obsvAltBox.getSelectedItem()
		unregAltName = self.unregAltBox.getSelectedItem()
		resvFile = self.resvFileT.getText()
		juncFile = self.juncFileT.getText()
		self.dispose()
		# make a new window w/ progress
		frame = frameProgress()
		# set up a log file
		logFile = ClientApp.Workspace().makeAbsolutePath("logs/VerfPlots.log")
		initializeLogging(logFile)
		# launch plot maker
		args = [obsvAltName, unregAltName, resvFile, juncFile, frame.bar, frame.txtArea]
		tsk = TaskBackground(cResSim.createVerfPlots, args)
		tsk.execute()
		
class frameExportRAS(JFrame):
	'''
	Class to provide a consistent frame for transformation of local flows
	That holds the output Dss File, csv file, and timestep
	Need to implement an ActionListener on the "computeBUT" JButton to respond
	when the button is clicked
	'''
	def __init__(self, simPeriod, altName, resvFile, juncFile, dShiftFile, outputDss, ratingDss):
		'''
		@simPeriod	SimulationPeriod	The currently active simulation
		@altName		String						Name of the current alternative (e.g. "Observed", not "Observed--0")
		@resvFile		String						.list file with list of reservoirs to export
		@juncFile		String						.list file with list of Junctions to export
		@dShiftFile	String						tab-delimited .dat file with Datum shifts
		@outputDss	String						output DSS filename
		@ratingDss	String						DSS filename with 'natural' rating curves in it
		'''
		#Title
		title = "Export Data to RAS"
		frame = JFrame.__init__(self, title)
		self.titleText = JLabel("RAS Export", JLabel.CENTER)
		self.titleText.setFont(Font("Stencil", Font.PLAIN, 36))
		titleP = JPanel(BorderLayout())
		titleP.add(self.titleText)
		#alternative drop down
		altNames = cResSim.getListOfAltNames(simPeriod) 
		altTxt = "Alternative to Export:"
		altP = panelDropDownBox(promptText=altTxt, itemList=altNames, defaultItem=altName)
		self.altNameBox = altP.box
		# text file with reservoir data to extract
		title = "Text File with reservoirs to export (outflow and elevation):"
		browseTitle = "Select Text File with Reservoirs to export:"
		resvFileP = panelTxtBrowseOpen(title, resvFile, browseTitle, "list")
		self.resvFileT = resvFileP.txtT
		# text file with junction data to extract
		title = "Text File with junctions to export (local flows and total flow):"
		browseTitle = "Select Text File with Junctions to export:"
		juncFileP = panelTxtBrowseOpen(title, juncFile, browseTitle, "list")
		self.juncFileT = juncFileP.txtT
		# text file with datum shifts to apply
		title = "Text File with datum shifts from NGVD29 to NAVD88:"
		browseTitle = "Select Text File with Datum Shifts:"
		dShiftFileP = panelTxtBrowseOpen(title, dShiftFile, browseTitle, "dat")
		self.dShiftFileT = dShiftFileP.txtT
		# output dss file
		title = "Output DSS File:"
		browseTitle = "Select output DSS file:"
		dssP = panelTxtBrowseOpen(title, outputDss, browseTitle, "dss")
		self.outDssT = dssP.txtT
		# radio buttons controlling which type of export is desired
		bg = ButtonGroup()
		ratingCurveTxt = "Use 'natural' rating curves instead of modeled elevations (not often used)"
		obsDataTxt = "Use 'Observed Data' when available (typ. used with Observed run)"
		modelDataTxt = "Use modeled data only (typ. used with Unreg run)"
		self.useObsDataBUT = JRadioButton(obsDataTxt, actionPerformed = self.radioButtonChange)
		self.ratingCurveBUT = JRadioButton(ratingCurveTxt, actionPerformed = self.radioButtonChange)
		self.useModelDataBUT = JRadioButton(modelDataTxt, actionPerformed = self.radioButtonChange)
		#self.ratingCurveBUT.setHorizontalTextPosition(JRadioButton.LEFT)
		#self.useObsDataBUT.setHorizontalTextPosition(JRadioButton.LEFT)
		#self.useModelDataBUT.setHorizontalTextPosition(JRadioButton.LEFT)
		self.useObsData = True #defaults
		self.useObsDataBUT.setSelected(True)
		bg.add(self.useObsDataBUT)
		bg.add(self.useModelDataBUT)
		bg.add(self.ratingCurveBUT)
		radioP = JPanel(GridLayout(3,1))
		radioP.add(self.useObsDataBUT)
		radioP.add(self.useModelDataBUT)
		radioP.add(self.ratingCurveBUT)
		radioP.setBorder(BorderFactory.createEtchedBorder())
		optionP = JPanel(BorderLayout())
		optionP.add(JLabel("Options:"), BorderLayout.NORTH)
		optionP.add(radioP, BorderLayout.CENTER)
		#Rating Curve DSS file (only need this if the "Rating Curve" option is chosen)
		title = "DSS File with Rating Curves:"
		browseTitle = "Select rating curve DSS file:"
		RCdssP = panelTxtBrowseOpen(title, ratingDss, browseTitle, "dss")
		self.RCDssT = RCdssP.txtT
		self.RCDssT.setEnabled(False) #default is greyed out
		# buttons and frame setup
		butP = panelComputeCancel(self, func = self.runRASExport)
		cpane = JPanel(BorderLayout(5,5), border = BorderFactory.createEmptyBorder(20,20,20,20))
		cp = JPanel(BorderLayout())
		fileP = JPanel(GridLayout(4,1))
		fileP.add(resvFileP)
		fileP.add(juncFileP)
		fileP.add(dShiftFileP)
		fileP.add(dssP)
		bottomP = JPanel(BorderLayout())
		bottomP.add(optionP, BorderLayout.WEST)
		bottomP.add(RCdssP, BorderLayout.SOUTH)
		cp.add(altP, BorderLayout.NORTH)
		cp.add(fileP, BorderLayout.CENTER)
		cp.add(bottomP, BorderLayout.SOUTH)
		cpane.add(titleP, BorderLayout.NORTH)
		cpane.add(cp, BorderLayout.CENTER)
		cpane.add(butP, BorderLayout.SOUTH)
		self.contentPane = cpane
		imgFile = ClientApp.Workspace().makeAbsolutePath("images/ras18.gif")
		self.setIconImage(ImageIcon(imgFile).getImage())
		self.pack()
		self.setLocationRelativeTo(None)
		self.getRootPane().setDefaultButton(butP.computeBUT)
		self.visible = True
	def runRASExport(self,e):
		# Launch the compute of reservoir inflows
		altName = self.altNameBox.getSelectedItem()
		resvFile = self.resvFileT.getText()
		juncFile = self.juncFileT.getText()
		dShiftFile = self.dShiftFileT.getText()
		outDssFile = self.outDssT.getText()
		ratingDssFile = self.RCDssT.getText()
		#if rating curve option not selected, don't use rating curves
		if not self.ratingCurveBUT.isSelected(): ratingDssFile = None
		self.dispose()
		# Make a new window with the progress
		frame = frameProgress()
		# Set up the logging
		logFile = ClientApp.Workspace().makeAbsolutePath("logs/RASExport.log")
		initializeLogging(logFile)
		# Launch the Extract
		args = [altName, resvFile, juncFile, dShiftFile, outDssFile, self.useObsData, frame.bar, frame.txtArea, ratingDssFile]
		tsk = TaskBackground(cResSim.exportRASdataToDss, args)
		tsk.execute()
	def radioButtonChange(self, e):
		if e.getSource() == self.useObsDataBUT:
			self.useObsData = True
			self.RCDssT.setEnabled(False)
		elif e.getSource() == self.ratingCurveBUT:
			self.useObsData = False
			self.RCDssT.setEnabled(True)
		elif e.getSource() == self.useModelDataBUT:
			self.useObsData = False
			self.RCDssT.setEnabled(False)
		else:
			print "something is wrong..."
			self.useObsData = False

class frameMiniSimulations(JFrame):
	# Class to pop up the main GUI and launch the compute of the with/without simulations
	def __init__(self, altNames, txtFile, rtxtFile, dssFile, xlsFile):
		# save the input arguments
		self.txtFile = txtFile
		self.rtxtFile = rtxtFile
		self.dssFile = dssFile
		self.xlsFile = xlsFile
		JFrame.__init__(self, "Mini-Simulations")
		# Define the layout of the GUI and populate it with default things
		self.titleText = JLabel("Flow Reduction by Reservoir", JLabel.CENTER)
		self.titleText.setFont(Font("Magneto", Font.PLAIN, 36))
		self.subtitle = JPanel(GridLayout(4,1))
		self.subtitle.add(JLabel("Runs 'mini-simulations' with/without each reservoir", JLabel.CENTER))
		self.subtitle.add(JLabel("Version 2.0", JLabel.CENTER))
		self.subtitle.add(JLabel("January 2015", JLabel.CENTER))
		self.subtitle.add(JLabel("Ryan Cahill", JLabel.CENTER))
		titleP = JPanel(GridLayout(2,1))
		titleP.add(self.titleText)
		titleP.add(self.subtitle)
		# Alternative combo boxes
		# try to find defaults based on name
		#altNameObs = cResSim.getCurrentRssAltName()
		altNameObs = None
		altNameUnreg = None
		for nm in altNames:
			if "UNR" in nm.upper(): altNameUnreg = nm
			if "OBS" in nm.upper(): altNameObs = nm
		altTxt = "Observed Alternative:"
		altP = panelDropDownBox(promptText=altTxt, itemList=altNames, defaultItem=altNameObs)
		self.obsAltBox = altP.box
		altTxt = "Unregulated Alternative:"
		unregAltP = panelDropDownBox(promptText=altTxt, itemList=altNames, defaultItem=altNameUnreg)
		self.unregAltBox = unregAltP.box
		# junction TXT input
		title = "Input TXT File with Junction Names for Output:"
		browseTitle = "Select Text File with Output Junction Names"
		txtP = panelTxtBrowseOpen(title, txtFile, browseTitle, "txt")
		self.txtT = txtP.txtT
		# reservoir TXT input
		title = "Input TXT File with Reservoir Names for Output:"
		browseTitle = "Select Text File with Output Reservoir Names"
		rtxtP = panelTxtBrowseOpen(title, rtxtFile, browseTitle, "txt")
		self.rtxtT = rtxtP.txtT
		# DSS output
		title = "Output DSS File:"
		browseTitle = "Select DSS output File:"
		dssP = panelTxtBrowseOpen(title, dssFile, browseTitle, "dss")
		self.dssT = dssP.txtT
		# XLS output
		title = "Output XLS File:"
		browseTitle = "Select Excel output File:"
		xlsP = panelTxtBrowseOpen(title, xlsFile, browseTitle, "xls")
		self.xlsT = xlsP.txtT
		# bottom buttons
		butP = panelComputeCancel(self, func = self.runCompute)
		# add all the panels to the main panel
		pane = JPanel(BorderLayout(), border = BorderFactory.createEmptyBorder(20,20,20,20))
		pane.add(titleP, BorderLayout.NORTH)
		cP = JPanel(BorderLayout())
		altsP = JPanel(BorderLayout())
		altsP.add(altP, BorderLayout.NORTH)
		altsP.add(unregAltP, BorderLayout.CENTER)
		cP.add(altsP, BorderLayout.NORTH)
		cP2 = JPanel(GridLayout(4,1), border = BorderFactory.createEmptyBorder(10,10,10,10))
		cP2.add(txtP)
		cP2.add(rtxtP)
		cP2.add(dssP)
		cP2.add(xlsP)
		cP.add(cP2, BorderLayout.CENTER)
		pane.add(cP)
		pane.add(butP, BorderLayout.SOUTH)
		# Creates the GUI and shows it
		self.contentPane = pane
		imgFile = ClientApp.Workspace().makeAbsolutePath("images/dam.gif")
		self.setIconImage(ImageIcon(imgFile).getImage())
		self.pack()
		self.setLocationRelativeTo(None) # Center of the screen
		self.getRootPane().setDefaultButton(butP.computeBUT)
		self.visible = True
	def runCompute(self, e):
		# compute the with/without simulations, saving results to output DSS and xls
		altNameObs = self.obsAltBox.getSelectedItem()
		altNameUnreg = self.unregAltBox.getSelectedItem()
		txtFile = self.txtT.getText() # get the input txt from user entry
		rtxtFile = self.rtxtT.getText() # get the input txt from user entry
		dssFile = self.dssT.getText() # get the desired dss file from user
		xlsFile = self.xlsT.getText() # get the desired xls file from user
		self.dispose() # get rid of the old GUI window
		# Set up the logging
		logFile = ClientApp.Workspace().makeAbsolutePath("logs/MiniSimulations.log")
		initializeLogging(logFile)
		# Make a new window with the progress
		frame = frameProgress()
		args = [altNameObs, altNameUnreg, dssFile, xlsFile, txtFile, rtxtFile, frame.bar, frame.txtArea]
		tsk = TaskBackground(cDamPrev.runMiniSimulations, args)
		tsk.execute()

class frameChart80(JFrame):
	# Class to pop up the main GUI and launch the compute of the Chart80 simulations
	def __init__(self, altNames, csvFile, dssFile):
		# save the input arguments
		self.csvFile = csvFile
		self.dssFile = dssFile
		JFrame.__init__(self, "Chart 80")
		# Define the layout of the GUI and populate it with default things
		self.titleText = JLabel("Chart 80 Flow Reductions", JLabel.CENTER)
		self.titleText.setFont(Font("Lucida Console", Font.PLAIN, 36))
		self.subtitle = JPanel(GridLayout(4,1))
		self.subtitle.add(JLabel("Runs simulations with groups of projects added to unreg run", JLabel.CENTER))
		self.subtitle.add(JLabel("Version 1.0", JLabel.CENTER))
		self.subtitle.add(JLabel("October 2015", JLabel.CENTER))
		self.subtitle.add(JLabel("Ryan Cahill", JLabel.CENTER))
		titleP = JPanel(GridLayout(2,1))
		titleP.add(self.titleText)
		titleP.add(self.subtitle)
		# Alternative combo boxes
		# try to find defaults based on name
		#altNameObs = cResSim.getCurrentRssAltName()
		altNameObs = None
		altNameUnreg = None
		for nm in altNames:
			if "UNR" in nm.upper(): altNameUnreg = nm
			if "OBS" in nm.upper(): altNameObs = nm
		altTxt = "Observed Alternative:"
		altP = panelDropDownBox(promptText=altTxt, itemList=altNames, defaultItem=altNameObs)
		self.obsAltBox = altP.box
		altTxt = "Unregulated Alternative:"
		unregAltP = panelDropDownBox(promptText=altTxt, itemList=altNames, defaultItem=altNameUnreg)
		self.unregAltBox = unregAltP.box
		# Chart80 CSV input
		title = "Input CSV File with simulations to run:"
		browseTitle = "Select CSV File with Chart 80 input simulations"
		txtP = panelTxtBrowseOpen(title, csvFile, browseTitle, "csv")
		self.txtT = txtP.txtT
		# DSS output
		title = "Output DSS File:"
		browseTitle = "Select DSS output File:"
		dssP = panelTxtBrowseOpen(title, dssFile, browseTitle, "dss")
		self.dssT = dssP.txtT
		# bottom buttons
		butP = panelComputeCancel(self, func = self.runChart80)
		# add all the panels to the main panel
		pane = JPanel(BorderLayout(), border = BorderFactory.createEmptyBorder(20,20,20,20))
		pane.add(titleP, BorderLayout.NORTH)
		cP = JPanel(BorderLayout())
		altsP = JPanel(BorderLayout())
		altsP.add(altP, BorderLayout.NORTH)
		altsP.add(unregAltP, BorderLayout.CENTER)
		cP.add(altsP, BorderLayout.NORTH)
		cP2 = JPanel(GridLayout(2,1), border = BorderFactory.createEmptyBorder(10,10,10,10))
		cP2.add(txtP)
		cP2.add(dssP)
		cP.add(cP2, BorderLayout.CENTER)
		pane.add(cP)
		pane.add(butP, BorderLayout.SOUTH)
		# Creates the GUI and shows it
		self.contentPane = pane
		#imgFile = ClientApp.Workspace().makeAbsolutePath("images/80.gif")
		#self.setIconImage(ImageIcon(imgFile).getImage())
		self.pack()
		self.setLocationRelativeTo(None) # Center of the screen
		self.getRootPane().setDefaultButton(butP.computeBUT)
		self.visible = True
	def runChart80(self, e):
		# compute the Chart 80 simulations, saving results to output DSS
		altNameObs = self.obsAltBox.getSelectedItem()
		altNameUnreg = self.unregAltBox.getSelectedItem()
		txtFile = self.txtT.getText() # get the input txt from user entry
		dssFile = self.dssT.getText() # get the desired dss file from user
		self.dispose() # get rid of the old GUI window
		# Set up the logging
		logFile = ClientApp.Workspace().makeAbsolutePath("logs/Chart80.log")
		initializeLogging(logFile)
		# Make a new window with the progress
		frame = frameProgress()
		args = [altNameObs, altNameUnreg, dssFile, txtFile, frame.bar, frame.txtArea]
		tsk = TaskBackground(cDamPrev.runAllChart80Simulations, args)
		tsk.execute()

class frameProgress(JFrame):
	'''
	Class to provide a consistent frame for compute progress
	With a JTextArea on top and a JProgressBar on bottom
	'''
	def __init__(self):
		JFrame.__init__(self, "Computation Progress")
		bar = JProgressBar(0,100, value=0, stringPainted=Constants.TRUE)
		#txtArea = JTextArea(15,50, margin = Insets(5,5,5,5), editable=Constants.FALSE)
		#use a custom class with "printToGUI" defined
		txtArea = JTextAreaAutoScroll()
		self.txtArea = txtArea
		pane = JPanel(BorderLayout(5,5), border = BorderFactory.createEmptyBorder(20,20,20,20))
		pane.add(JScrollPane(self.txtArea), BorderLayout.NORTH)		
		pane.add(bar, BorderLayout.CENTER)
		butOK = JButton("OK")
		butOK.addActionListener(listenerCancel(self))
		pane.add(butOK, BorderLayout.SOUTH)
		self.contentPane = pane
		self.pack()
		self.setLocationRelativeTo(None)
		self.getRootPane().setDefaultButton(butOK)
		#custom attributes
		self.bar = bar
		self.txtArea = txtArea
		#set default to visible
		self.setVisible(True)
		
class panelTxtBrowseOpen(JPanel):
	'''
	Class to provide a "canned" panel that is used often
	With a JLabel on left (file), and "browse" and "open" buttons on the right
	User will typically create and then grab hold of the txtT JLabel
	'''
	def __init__(self, title, defaultTextFile, browseTitle, extension):
		JPanel.__init__(self, BorderLayout(), border = BorderFactory.createEmptyBorder(0,0,5,0))
		self.add(JLabel(title, JLabel.LEFT), BorderLayout.NORTH)
		self.txtT = JTextField(defaultTextFile)
		self.add(self.txtT, BorderLayout.CENTER)
		browseBUT = JButton("...")
		browseBUT.addActionListener(listenerBrowseFile(self.txtT, extension, browseTitle))
		viewBUT = JButton("View")
		viewBUT.addActionListener(listenerOpenFile(txtFld = self.txtT))
		viewP = JPanel(BorderLayout())
		viewP.add(browseBUT, BorderLayout.WEST)
		viewP.add(viewBUT, BorderLayout.EAST)
		self.add(viewP, BorderLayout.EAST)
		
class panelDropDownBox(JPanel):
	'''
	Class to provide a "canned" panel that is used often
	With a JLabel on the left, and a JComboBox on the right (drop-down)
	Often used when selecting which alternative or timestep to use
	User will typically create and then grab hold of the "box" JComboBox
	'''
	def __init__(self, promptText, itemList, defaultItem):
		#promptText = the text to display at the right to explain what to select
		#itemList = list of items that are selectable
		#defaultItem = an item in "itemList" that should be the default
		JPanel.__init__(self, BorderLayout(), border = BorderFactory.createEmptyBorder(5,0,5,0))
		self.add(JLabel(promptText, JLabel.LEFT), BorderLayout.WEST)
		self.box = JComboBox(itemList)
		self.box.setSelectedItem(defaultItem)
		self.add(self.box, BorderLayout.EAST)
		
class panelComputeCancel(JPanel):
	'''
	Class to provide a "canned" panel that is used often
	With two buttons on the right--"Compute" and "Cancel"
	User will specify what function should run when the compute button is pressed
	Or add an ActionListener to the button later
	User can access either button (computeBUT or cancelBUT)
	'''
	def __init__(self, frame, func = None, buttonTitle = "Compute"):
		'''
		@frame       JFrame   The parent frame that will hold these buttons
		@func        function Function to be executed when "Compute" is pressed
		@buttonTitle string   The title of the compute button
		'''
		# buttons and frame setup
		JPanel.__init__(self, BorderLayout())
		if func:
			self.computeBUT = JButton(buttonTitle, actionPerformed = func) #set the action
		else:
			self.computeBUT = JButton(buttonTitle) #set action listener later
		self.cancelBUT = JButton("Cancel")
		self.cancelBUT.addActionListener(listenerCancel(frame))
		butP2 = JPanel(GridLayout(1,2))
		butP2.add(self.computeBUT)
		butP2.add(self.cancelBUT)
		self.add(butP2,BorderLayout.EAST)		

class JTextAreaAutoScroll(JTextArea):
	'''
	Class to create a JTextArea that will automatically scroll to the bottom
	when new text is appended.
	Useful for compute displays to the user 
	'''
	def __init__(self):
		JTextArea.__init__(self, 15,50, margin = Insets(5,5,5,5), editable=Constants.FALSE)
		
	def printToGUI(self, msg):
		# print a message to the JTextArea and scroll to the bottom
		self.append("%s\n" %msg)
		self.setCaretPosition(self.getDocument().getLength()-1) #scroll to bottom

class listenerCancel(ActionListener):
	'''
	ActionListener for "cancel" buttons that get rid of a frame upon clicking
	Feed in the frame that will be removed on initialization
	'''
	def __init__(self, frameToRemove):
		#frameToRemove = JFrame
		self.frameToRemove = frameToRemove
	def actionPerformed(self, e):
		# when the button is clicked, get rid of the frame
		self.frameToRemove.dispose()
		
class buttonClose(JButton):
	'''
	A button that will close it's parent frame when clicked
	'''
	def __init__(self, frame, title, actionPerformed = None):
		if actionPerformed:
			JButton.__init__(self, title, actionPerformed = actionPerformed)
		else:
			JButton.__init__(self, title)
		self.addActionListener(listenerCancel(frame))

class listenerBrowseFile(ActionListener):
	'''
	ActionListener for buttons that prompt for a file
	Feed in the JTextField that will get the selected file and file extension
	'''
	def __init__(self, txtFld, extension, title = "Select File"):
		'''
		@param txtFld = JTextField that will get the browse output
		@param extension = String 3-digit string for file extension (e.g. dss)
		@param title = optional String to override the title of the dialog box
		'''
		self.txtFld = txtFld
		self.extension = extension
		self.title = title
	def actionPerformed(self, e):
		# prompt the user to select a file
		JC = JFileChooser()
		fil = FileNameExtensionFilter("%s Files" %self.extension, [self.extension])
		JC.setCurrentDirectory(File(self.txtFld.getText()))
		JC.setSelectedFile(File(""))
		JC.setDialogTitle(self.title)
		JC.setFileFilter(fil)
		JC.setAcceptAllFileFilterUsed(False)
		if JC.showOpenDialog(JC) == JC.APPROVE_OPTION:
			selectFile = JC.getSelectedFile().toString()
			if not selectFile.endswith(self.extension): #need to fill in the extension
				selectFile = selectFile + "." + self.extension
			self.txtFld.setText(selectFile)
			
class listenerOpenFile(ActionListener):
	'''
	ActionListener for buttons that open a file using the user settings
	Feed in the JTextField that holds the file to be opened
	or alternately a "hardcoded" predefined file path
	'''
	def __init__(self, txtFld = None, fileToOpen = None):
		'''
		@param txtFld = JTextField that holds the file to be opened
		@param fileToOpen = String (optional) that holds the specified file to open 
		'''
		self.txtFld = txtFld
		self.fileToOpen = fileToOpen
	def actionPerformed(self, e):
		# Tries to open up the file with whatever the defined default program is
		if Desktop.isDesktopSupported():
			if self.fileToOpen is None: #using the text field, not a hardcode file
				fileToOpen = self.txtFld.getText()
			else:
				fileToOpen = self.fileToOpen
			try:
				Desktop.getDesktop().open(File(fileToOpen))
			except:
				logging.error("Failed to open file:\n%s" %fileToOpen)
						

# END OF CLASS DEFINITIONS
################################################################################
# FUNCTION DEFINITIONS
	
def initializeLogging(logFile):
	'''
	Function to initialize the logging
	Need to log to the console window as well as a text file
	Default is to log all messages of INFO or higher to console and file
	After running this function, you can just do: logging.info("Hello"), etc.
	@param logFile	string	filename of text file to log to
	'''
	#if the logging directory hasn't been built, do it
	cFile.ensure_dir(logFile)
	#reset the base logger--basicConfig only works if not already defined
	logging.getLogger('').handlers = [] 
	#logLevel = logging.DEBUG
	logLevel = logging.INFO
	# set up logging to file
	logging.basicConfig(level=logLevel,
	                    format='%(message)s',
	                    filename=logFile,
	                    filemode='w')
	# define a Handler which writes messages to the sys.stderr (console)
	console = logging.StreamHandler()
	console.setLevel(logLevel)
	formatter = logging.Formatter('%(message)s') # set a simple format
	console.setFormatter(formatter) # tell the handler to use this format
	logging.getLogger('').addHandler(console) # add the handler to the root logger
	return logging.getLogger('')

def getCurrentLogFile():
	'''
	Function to return the current file being logged to
	Assumes the root logger is a FileHandler
	If it's not, this function will return "Unknown File"
	'''
	try:
		return logging.getLogger('').handlers[0].baseFilename
	except AttributeError:
		return "Unknown File"
	
def closeLogging():
	'''
	Function to close down the logging (release the log file)
	Just closes the default ("root") logger
	Assumes the root logger is a FileHandler
	'''
	l = logging.getLogger('')
	for handler in l.handlers:
		handler.close() #get the root logger and close the file
		l.removeHandler(handler)