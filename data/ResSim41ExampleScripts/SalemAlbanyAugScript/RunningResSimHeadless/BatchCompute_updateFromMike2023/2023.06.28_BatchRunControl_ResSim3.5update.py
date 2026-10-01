from hec.script           import ResSim
from hec.ui               import CheckTreeManager
from java.awt             import BorderLayout
from java.awt             import Font
from java.awt             import GridLayout
from java.awt.event       import ActionListener
from java.io              import File
from java.io              import FileOutputStream
from java.io              import PrintStream
from java.lang            import String
from java.lang            import System
from java.util.concurrent import LinkedBlockingQueue
from javax.swing          import JButton
from javax.swing          import JCheckBox
from javax.swing          import JFrame
from javax.swing          import JPanel
from javax.swing          import JProgressBar
from javax.swing          import JScrollPane
from javax.swing          import JTextArea
from javax.swing          import JTextField
from javax.swing          import JTree
from javax.swing.border   import TitledBorder
from javax.swing.tree     import DefaultMutableTreeNode
from javax.swing.tree     import TreePath
import copy, glob, os, re, sys, threading, time, traceback


if os.path.splitext(sys.argv[0])[0] == ".py" :
	# Jython driver passes script file name as first argument to script
	programName  = os.path.splitext(os.path.split(sys.argv[0])[1])[0]
	watershedDir = os.path.realpath(sys.argv[1])
else :
	# HEC-ResSim driver doesn't pass script file name to script
	programName  = "BatchRunControl"
	watershedDir = os.path.realpath(sys.argv[0])
outputDir   = watershedDir
statusQueue = None
dataQueue   = None
#=========================================================================
class Logger(PrintStream) :

	def __init__(self, filename) :
		self._can_output = False
		if File(filename).exists() :
			msg = "Resume logging to file %s" % filename
		else :
			msg = "Start logging to file %s" % filename
		fos = FileOutputStream(filename, True)
		PrintStream.__init__(self, fos)
		self.oldOut = System.out
		self.oldErr = System.err
		self.filename = filename
		self._cons = System.console()
		self._file = PrintStream(fos)
		System.setOut(self)
		System.setErr(self)
		self._can_output = True
		self.println(msg)
		self.flush()

	def __del__(self) :
		if self._can_output : self.close()

	def checkAvailability(self) :
		if not self._can_output :
			errmsg = "Logfile %s is not available for output" % self.filename
			raise Exception(errmsg)

	def close(self) :
		self.println("Stop logging to file %s" % self.filename)
		self.flush()
		if self._file : self._file.close()
		System.setOut(self.oldOut)
		System.setErr(self.oldErr)
		self._can_output = False

	def println(self, arg) :
		global logPanel
		self.checkAvailability()
		if self._cons : 
			self._cons.printf("%s\n", [str(arg)])
			self._cons.flush()
		if self._file : self._file.println(arg)
		if logPanel : logPanel.addText("%s\n" % arg)

	def write(self, *args) :
		global logPanel
		self.checkAvailability()
		if len(args) == 1 :
			arg = args[0]
			if self._cons : 
				self._cons.printf("%s", [str(arg)])
				self._cons.flush()
			if self._file : self._file.write(arg)
		else :
			buf, offset, length = args
			arg = String(buf, offset, length)
			if self._cons : 
				self._cons.printf("%s", [str(arg)])
				self._cons.flush()
			if self._file : self._file.write(buf, offset, length)
		if logPanel : logPanel.addText("%s" % arg)
			
	def flush(self) :
		self.checkAvailability()
		if self._cons : self._cons.flush()
		if self._file : self._file.flush()

#=========================================================================
def getLogfileName(id=None, directory=None) :
	yr, mo, da, hr, mi = time.localtime()[:5]
	if directory is None :
		directory = outputDir
	if os.path.isfile(directory) :
		directory = os.path.split(directory)[0]
	if not os.path.exists(directory) or not os.path.isdir(directory) :
		errmsg = "Invalid output directory: %s" %directory
		raise ValueError(errmsg)
	if id : idPart = "_%s" % id
	else  : idPart = ""		
	logfileName   = os.path.join(
		directory, 
		"%s_%4.4d-%2.2d-%2.2d_%2.2d%2.2d%s.log" % (
			programName, yr, mo, da, hr, mi, idPart))
	return logfileName
#=========================================================================
def getLogfile(id=None, directory=None) :
	logfile = Logger(getLogfileName(id, directory))
	return logfile
#=========================================================================
def openWatershed(watershed, watershedDir = None) :
	'''
	Opens a specified watershed in ResSim.
	'''
	#----------------------------------------------#
	# determine watershed info from the parameters #
	#----------------------------------------------#
	if watershedDir is not None :
		openWatershed(os.path.join(watershedDir, watershed))
	if os.path.exists(watershed) :
		if os.path.isfile(watershed) :
			#---------------------------------------#
			# watershed param is workspace filename #
			#---------------------------------------#
			watershedName = os.path.splitext(os.path.basename(watershed))[0]
			wkspFileName = watershed
		else :
			#----------------------------------------#
			# watershed param is watershed directory #
			#----------------------------------------#
			watershedName = os.path.basename(watershed)
			wkspFileName = os.path.join(watershed, "%s.wksp" % watershedName)
			if not os.path.isfile(wkspFileName) :
				wkspFileNames = glob.glob(os.path.join(watershed, "*.wksp"))
				if len(wkspFileNames) == 0 :
					raise Exception("No workspace file in directory %s" % watershed)
				elif len(wkspFileNames) > 1 :
					raise Exception("Multiple workspace files in directory %s" % watershed)
				wkspFileName = wkspFileNames[0];
				watershedName = os.path.splitext(os.path.basename(wkspFileName))[0]
	else :
		newWatershed = os.path.join(
			hec.client.ClientApp.app().getAppStartDir(), 
			"watershed", 
			"base", 
			watershed)
		if os.path.exists(newWatershed) :
			return openWatershed(newWatershed)
		else :
			raise Exception("Unable to open watershed %s" % newWatershed)
	#-------------------------------------------------#
	# open the watershed and verify we were sucessful #
	#-------------------------------------------------#
	ResSim.openWatershed(wkspFileName.replace(os.sep, "/"))
	if ResSim.getWatershedName() != watershedName :
		raise Exception("Unable to open watershed %s\n\t%s != %s" % (wkspFileName, ResSim.getWatershedName(), watershedName))
		
#=========================================================================
def setModule(moduleName) :
	'''
	Sets ResSim to the specified module, and returns the module.
	'''
	if `ResSim.getCurrentModule()` != moduleName : 
		ResSim.selectModule(moduleName)
	
	currentModule = ResSim.getCurrentModule()

	if `currentModule` != moduleName :
		raise Exception( "Unable to switch to %s module." % moduleName)

	return currentModule
#=========================================================================
def openSimulation(simulationName) :
	'''
	Opens the specified simulation and returns it.
	'''
	module = ResSim.getCurrentModule()
	if `module` != "Simulation" : 
		raise Exception("Must be in Simulation module to open a simulation.")
	
	if module.openSimulation(simulationName) :
		return module.getSimulation()
	else :
		raise Exception('Could not open simulation "%s".' % simulationName)
#=========================================================================
def log(string, newLine = True) :
	y, M, d, h, m, s = time.localtime()[:6]
	string = "%4.4d/%2.2d/%2.2d-%2.2d:%2.2d:%2.2d %s" % (y,M,d,h,m,s, string)
	if newLine : System.out.println(string)
	else       : System.out.print(string)
#=========================================================================
class SimulationInfo(object) :
	def __init__(self, watershed) :
		global logPanel
		self.watershed = watershed
		self.simulations = []
		if logPanel : logPanel.setProgressIndeterminate(True)
		self.simulationNames = [sim.getName() for sim in self.watershed.getManagerIDList("rss", "hec.model.SimulationPeriod")]
		self.simulationNames.sort()
		count = len(self.simulationNames)
		if logPanel :
			logPanel.setProgressMinMax(0, 2*count)
			logPanel.setProgressValue(0)
			logPanel.setProgressIndeterminate(False)
		
		for i in range(count) :
			simulationName = self.simulationNames[i]
			if logPanel : 
				logPanel.incrementProgress()
				logPanel.setStatus("Reading Simulation %s" % simulationName)
			simulation = openSimulation(simulationName)
			self.simulations.append({
				"Name"         : simulationName,
				"Lookback"     : simulation.getLookbackDateString(),
				"Start"        : simulation.getStartDateString(),
				"End"          : simulation.getEndDateString(),
				"Alternatives" : []})
			if logPanel : logPanel.incrementProgress()
			simulationRuns = list(simulation.getSimulationRuns())
			for simulationRun in simulationRuns :
				alternativeName = simulationRun.getUserName()
				self.simulations[-1]["Alternatives"].append({"Name" : alternativeName, "Trials" : []})
				trialRuns = simulationRun.getTrials()
				for trialRun in trialRuns :
					trialName = trialRun.getUserName()
					self.simulations[-1]["Alternatives"][-1]["Trials"].append(trialName)

		if logPanel : 
			logPanel.setProgressMinMax(0, 0)
			logPanel.setProgressValue(0)
			logPanel.setStatus("Ready")
	
	def getSimulations(self) :
		return copy.deepcopy(self.simulations)
	
#=========================================================================
class LogPanel(JFrame) :
	def __init__(self, title) :
		JFrame.__init__(self, title)
		self.textArea = JTextArea()
		self.statusArea = JTextField()
		self.progressBar = JProgressBar()
		self.progressBar.setStringPainted(True)
		statusPanel = JPanel(GridLayout(2, 1))
		statusPanel.add(self.progressBar)
		statusPanel.add(self.statusArea)
		mainPanel = JPanel(BorderLayout())
		mainPanel.add(JScrollPane(self.textArea), BorderLayout.CENTER)
		mainPanel.add(statusPanel, BorderLayout.SOUTH)
		self.setContentPane(mainPanel)
		self.textArea.setEditable(False)
		self.textArea.setLineWrap(False)
		self.textArea.setFont(Font("Courier New", Font.PLAIN, 12))
		self.statusArea.setEditable(False)
		self.maxTextSize = 1048576 # 1MB
		self.textSize = 0
		self.dataQueue = LinkedBlockingQueue()
		self.statusQueue = LinkedBlockingQueue()
		threading.Thread(target=self.pollDataQueue).start()
		threading.Thread(target=self.pollStatusQueue).start()
	
	def addText(self, text) :
		self.dataQueue.put(text)
		
	def setStatus(self, text) :
		self.statusQueue.put(text)
		
	def setProgressIndeterminate(self, state) :
		self.progressBar.setIndeterminate(state)
				
	def setProgressMinMax(self, _min, _max) :
		self.progressBar.setMinimum(_min)
		self.progressBar.setMaximum(_max)
		
	def setProgressValue(self, value) :
		self.progressBar.setValue(value)
		try : 
			s = "%.0f%%" % (100. * self.progressBar.getValue() / self.progressBar.getMaximum())
		except :
			s = ""
		self.progressBar.setString(s)
					
	def incrementProgress(self) :
		self.setProgressValue(self.progressBar.getValue() + 1)
							
	def _addText_(self, text) :
		self.textArea.append(text)
		self.textSize += len(text)
		if self.textSize > self.maxTextSize :
			newSize = self.maxTextSize * 3 / 4
			text = self.textArea.getText()[-newSize:]
			text = "\n".join(text.split("\n")[1:])
			self.textArea.setText(text)
			self.textSize = len(text)
		self.textArea.setCaretPosition(self.textSize)
	
	def _setStatus_(self, text) :
		self.statusArea.setText(text)

	def pollDataQueue(self) :
		while True :
			text = self.dataQueue.take()
			self._addText_(text)
			
	def pollStatusQueue(self) :
		while True :
			text = self.statusQueue.take()
			self._setStatus_(text)
			
#=========================================================================
def runSimulations(runPaths, separateLogFiles) :
	global logPanel
	mainLogfile = getLogfile(id="Simulations")
	lastSimulationName = None
	count = len(runPaths)
	i = 0
	if logPanel :
		logPanel.setProgressMinMax(0, count)
		logPanel.setProgressValue(0)
	for runPath in runPaths :
		i += 1
		simulationName, alternativeName = runPath[:2]
		if len(runPath) > 2 : trialName = runPath[2]
		else                : trialName = None
		if lastSimulationName and simulationName != lastSimulationName :
			ResSim.getCurrentModule().saveSimulation()
		lastSimulationName = simulationName
		if logPanel :
			if trialName :
				logPanel.setStatus("Computing simulation %d of %d: %s, alternative %s, trial %s" % (i, count, simulationName, alternativeName, trialName))
			else :
				logPanel.setStatus("Computing simulation %d of %d: %s, alternative %s" % (i, count, simulationName, alternativeName))
		log("")
		log("###")
		if trialName :
			log("### Computing simulation %s, alternative %s, trial %s" % (simulationName, alternativeName, trialName))
		else :
			log("### Computing simulation %s, alternative %s" % (simulationName, alternativeName))
		log("###")
		if separateLogFiles :
			if trialName :
				id = "%s{%s{%s}}" % (simulationName, alternativeName, trialName)
			else : 
				id = "%s{%s}" % (simulationName, alternativeName)
			runLogfile = getLogfile(id)
		simulation = openSimulation(simulationName)
		simRun = simulation.getSimulationRun(alternativeName)
		if trialName :
			for trial in simRun.getTrials() :
				if trial.getUserName() == trialName :
					simRun = trial
					break
			else :
				raise Exception("Cannot find trial %s in alternative %s in simulation %s" % (trialName, alternativeName, simulationName))
		simulation.computeRun(simRun, -1)
		if logPanel : logPanel.incrementProgress()
		if separateLogFiles :
			runLogfile.close()

	ResSim.getCurrentModule().saveSimulation()
	if logPanel :
		logPanel.incrementProgress() 
		logPanel.setStatus("Done")
	mainLogfile.close()
#=========================================================================
def main() :
	global logPanel
	
	class BatchRunControlActionListener(ActionListener) :
		def __init__(self, tree, check_tree) :
			self.tree = tree
			self.check_tree = check_tree
			self.separate_log_files = False
			self.leafPaths = []
			self.topLevelPaths = []

		def enumerateTopLevelPaths(self) :
			self.topLevelPaths = []
			root = self.tree.getModel().getRoot()
			iter1 = root.breadthFirstEnumeration()
			while iter1.hasMoreElements() :
				node = iter1.nextElement()
				if node.getLevel() == 1 :
					self.topLevelPaths.append(TreePath([root, node]))

		def enumerateLeafPaths(self) :
			self.leafPaths = []
			root = self.tree.getModel().getRoot()
			iter1 = root.breadthFirstEnumeration()
			while iter1.hasMoreElements() :
				node = iter1.nextElement()
				iter2 = node.pathFromAncestorEnumeration(root)
				path = []
				while iter2.hasMoreElements() :
					node = iter2.nextElement()
					path.append(node)
				if node.isLeaf() :
					self.leafPaths.append(TreePath(path))
					
		def getTopLevelPaths(self) :
			if not self.topLevelPaths : self.enumerateTopLevelPaths()
			return self.topLevelPaths
					
		def getLeafPaths(self) :
			if not self.leafPaths : self.enumerateLeafPaths()
			return self.leafPaths
						
		def actionPerformed(self, e) :
			actionCommand = e.getActionCommand()
			if actionCommand == "Expand All" :
				i = 0
				while i < self.tree.getRowCount() :
					self.tree.expandRow(i)
					i += 1
			elif actionCommand == "Collapse All" :
				i = self.tree.getRowCount() - 1 
				while i > 0 :
					self.tree.collapseRow(i)
					i -= 1 
			elif actionCommand == "Select All" :
				for path in self.getLeafPaths() : self.check_tree.checkPath(path, True)

			elif actionCommand == "Select None" :
				for path in self.getLeafPaths() : self.check_tree.checkPath(path, False)

			elif actionCommand == "Invert Selections" :
				selectionModel = check_tree.getSelectionModel()
				for path in self.getLeafPaths() :
					selected = selectionModel.isPathSelected(path, True) 
					self.check_tree.checkPath(path, not selected)

			elif actionCommand == "Show Times" :
				simulations = simulationInfo.getSimulations() 
				simulationPaths = self.getTopLevelPaths()
				for i in range(len(simulationPaths)) :
					node = simulationPaths[i].getLastPathComponent()
					if e.getSource().isSelected() :
						node.setUserObject(treeTableTemplate % (
							simulations[i]["Name"],
							simulations[i]["Lookback"],
							simulations[i]["Start"],
							simulations[i]["End"]))
					else :
						node.setUserObject(treeSimpleTemplate % simulations[i]["Name"])
						self.tree.setRowHeight(0)
						self.tree.updateUI()
						
			elif actionCommand == "Cancel" :
				System.exit(1)
				
			elif actionCommand == "Run Selected" :
				global logPanel
				selectionModel = check_tree.getSelectionModel()
				pattern = re.compile(r'^.+<b>([^<]+)</b>.+$')
				runPaths = []
				for path in self.getLeafPaths() :
					selected = selectionModel.isPathSelected(path, True) 
					if selected : 
						nodes = path.getPath()
						simulationName  = pattern.match(nodes[1].getUserObject()).group(1)
						alternativeName = nodes[2].getUserObject()
						if len(nodes) > 3 : trialName = nodes[3].getUserObject()
						else              : trialName = None
						if trialName == "Base Alternative" : trialName = None
						if trialName : runPaths.append([simulationName, alternativeName, trialName])
						else         : runPaths.append([simulationName, alternativeName])
				t = threading.Thread(target=runSimulations, args=(runPaths, self.separate_log_files))
				t.start()
						                        
			elif actionCommand == "Separate Log Files" :
				self.separate_log_files = e.getSource().isSelected()	                        
				
	simModule = setModule("Simulation")
	openWatershed(watershedDir)
	watershed = ResSim.getWatershed()
	watershedName = watershed.getName()
	log("Workspace = %s" % watershedName)

	simulationInfo = SimulationInfo(ResSim.getWatershed())
	
	treeSimpleTemplate = '<html><b>%s</b><html>'
	treeTableTemplate = re.sub(
		r'>\s+<',
		'><',
		''' 				
		<html>
			<table border="1">
				<tr>
					<td rowspan="3"><b>%s</b></td>
					<td>Lookback</td>
					<td>%s</td>
				</tr>
				<tr>
					<td>Start</td>
					<td>%s</td>
				</tr>
				<tr>
				<td>End</td>
					<td>%s</td>
				</tr>
			</table>                                                    
		<html>''').strip()


	tree_root = DefaultMutableTreeNode("Simulations")
	for simulation in simulationInfo.getSimulations() :
		simNode = DefaultMutableTreeNode(
			treeSimpleTemplate % simulation["Name"])
		
		for alternative in simulation["Alternatives"] :
			altNode = DefaultMutableTreeNode(alternative["Name"])
			trials = alternative["Trials"]
			if trials : 
				altNode.add(DefaultMutableTreeNode("Base Alternative"))
				for trial in trials :
					trialNode = DefaultMutableTreeNode(trial)
					altNode.add(trialNode)
			simNode.add(altNode)
		tree_root.add(simNode)				

	tree = JTree(tree_root)
	check_tree = CheckTreeManager(tree)
	tree_pane = JScrollPane(tree)
	
	button_action_listener = BatchRunControlActionListener(tree, check_tree)
	expand_button = JButton("Expand All")
	expand_button.addActionListener(button_action_listener)
	collapse_button = JButton("Collapse All")
	collapse_button.addActionListener(button_action_listener)
	select_all_button = JButton("Select All")
	select_all_button.addActionListener(button_action_listener)
	select_none_button = JButton("Select None")
	select_none_button.addActionListener(button_action_listener)
	invert_selections_button = JButton("Invert Selections")
	invert_selections_button.addActionListener(button_action_listener)
	info_checkbox = JCheckBox("Show Times", False)
	info_checkbox.addActionListener(button_action_listener)
	cancel_button = JButton("Cancel")
	cancel_button.addActionListener(button_action_listener)
	run_selected_button = JButton("Run Selected")
	run_selected_button.addActionListener(button_action_listener)
	separate_logfile_checkbox = JCheckBox("Separate Log Files", False)
	separate_logfile_checkbox.addActionListener(button_action_listener)
	
	upper_right_panel = JPanel(GridLayout(6, 1, 5, 5))
	upper_right_panel.setBorder(TitledBorder("Tree Operations"))
	upper_right_panel.add(expand_button)
	upper_right_panel.add(collapse_button)
	upper_right_panel.add(info_checkbox)
	upper_right_panel.add(select_all_button)
	upper_right_panel.add(select_none_button)
	upper_right_panel.add(invert_selections_button)

	lower_right_panel = JPanel(GridLayout(3, 1, 5, 5))
	lower_right_panel.setBorder(TitledBorder("Actions"))
	lower_right_panel.add(cancel_button)
	lower_right_panel.add(run_selected_button)
	lower_right_panel.add(separate_logfile_checkbox)

	right_panel = JPanel(BorderLayout())
	right_panel.add(upper_right_panel, BorderLayout.NORTH)
	right_panel.add(lower_right_panel, BorderLayout.SOUTH)
	main_panel = JPanel(BorderLayout())
	main_panel.add(tree_pane, BorderLayout.CENTER)
	main_panel.add(right_panel, BorderLayout.EAST)
	
	frame = JFrame("%s Simulations" % watershedName) 
	frame.setLocation(100,100)
	frame.setSize(500, 700)
	frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE)
	frame.setContentPane(main_panel)
	frame.setVisible(True)

#=========================================================================
try :
	try :
		UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName())
	except :
		pass
	logPanel = LogPanel("%s Log" % programName)
	logPanel.setSize(700, 500)
	logPanel.setLocation(100, 300)
	logPanel.setVisible(True)
	logfile = getLogfile("Startup")
	main()
	logfile.close()
except :
	traceback.print_exc()

