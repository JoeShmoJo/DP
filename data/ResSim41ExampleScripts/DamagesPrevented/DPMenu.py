"""
Damages Prevented menu for the Willamette watershed in ResSim 4.1.

Launched by scripts/DP_Menu.py from the Simulation module, with the simulation
holding the Observed and Unregulated alternatives open. One window, three
steps, run in order:

  1. Transform gage data        Willamette Falls local -> DPcalc.dss
  2. Water-balance locals       locals at gaged junctions (Observed alternative) -> DPcalc.dss
     (then compute the Observed and Unregulated alternatives in ResSim)
  3. Mini-simulations           MiniSimulations.dss and Results/*.csv

The window stays open between steps. Each step opens a progress window and
writes a log to shared/DamagesPrevented/logs/. File locations are in DPSettings.py.

Adapted from the AFDR DPMenuGUI (Ryan Cahill): same progress window and
background task, without the Columbia, RAS, Chart 80 and plotting steps.
"""
from javax.swing import JProgressBar, JPanel, JFrame, JTextArea, JScrollPane, JLabel, JButton, JComboBox
from javax.swing import SwingWorker, BorderFactory
from java.awt.event import ActionListener
from java.awt import BorderLayout, GridLayout, Insets, Font
from java.util.concurrent import ExecutionException

from hec.script import Constants, MessageBox
import os, logging

from NWDJyLib import cFile
from NWDJyLib.ResSim import ResSimController
from DamagesPrevented import DPSettings, cTransform, cWaterBalance, cMiniSims

################################################################################
# STEPS (run in a background thread)

def _altTimeStep(simulation, altName):
    run = ResSimController.getSpecificRun(simulation, altName)
    return run.getRssAlt().getTimeStepString()

def runTransformStep(altNameObs, bar, txtArea):
    simulation = ResSimController.getSimulation()
    startTime, endTime, lookbackTime = ResSimController.getSimulationTimes(simulation)
    tsInt = _altTimeStep(simulation, altNameObs)
    cTransform.transformGageData(DPSettings.absPath(DPSettings.OBSDATA_DSS),
                                 DPSettings.absPath(DPSettings.DPCALC_DSS),
                                 DPSettings.absPath(DPSettings.TRANSFORM_CSV),
                                 tsInt, lookbackTime, endTime, DPSettings.TRANSFORM_FPART, bar, txtArea)

def runWaterBalanceStep(altNameObs, bar, txtArea):
    cWaterBalance.computeWaterBalanceLocals(altNameObs, DPSettings.absPath(DPSettings.DPCALC_DSS),
                                            DPSettings.NEGATIVE_LOCALS_ALLOWED, bar, txtArea)

def runMiniSimsStep(altNameObs, altNameUnreg, bar, txtArea):
    cMiniSims.runMiniSimulations(altNameObs, altNameUnreg,
                                 DPSettings.absPath(DPSettings.MINISIM_DSS),
                                 DPSettings.absPath(DPSettings.RESULTS_DIR),
                                 DPSettings.absPath(DPSettings.CONTROL_POINTS_TXT),
                                 DPSettings.absPath(DPSettings.RESERVOIRS_TXT),
                                 DPSettings.REREG, bar, txtArea)

################################################################################
# CLASS DEFINITIONS

class TaskBackground(SwingWorker):
    """Runs func(*args) in a background thread so the progress window updates."""
    def __init__(self, func, args):
        SwingWorker.__init__(self)
        self.func = func
        self.args = args
    def doInBackground(self):
        self.func(*self.args)
    def done(self):
        try:
            self.get() #raises if the step threw an exception
        except ExecutionException, e:
            logging.error(e.getCause())
            MessageBox.showError(str(e.getCause()), "Error!")
        msg = "\nFinished logging to:\n%s" %getCurrentLogFile()
        logging.info(msg)
        for a in self.args:
            if isinstance(a, JTextAreaAutoScroll):
                a.printToGUI(msg)
        closeLogging()

class frameMainSelector(JFrame):
    """The Damages Prevented window: pick the alternatives, run the steps in order."""
    def __init__(self):
        self.simulation = ResSimController.getSimulation() #also checks we are in the Simulation module
        self.startTime, self.endTime, self.lookbackTime = ResSimController.getSimulationTimes(self.simulation)
        altNames = ResSimController.getListOfAltNames(self.simulation)
        altNameObs = None
        altNameUnreg = None
        for nm in altNames:
            if altNameUnreg is None and DPSettings.UNREG_ALT_HINT in nm.upper(): altNameUnreg = nm
            if altNameObs is None and DPSettings.OBS_ALT_HINT in nm.upper(): altNameObs = nm

        JFrame.__init__(self, "Damages Prevented")
        pane = JPanel(BorderLayout(10,10), border = BorderFactory.createEmptyBorder(20,20,20,20))
        title = JLabel("Damages Prevented - Willamette", JLabel.CENTER)
        title.setFont(Font("Dialog", Font.BOLD, 22))
        pane.add(title, BorderLayout.NORTH)

        center = JPanel(BorderLayout(5,5))
        altP = JPanel(GridLayout(3,1))
        altP.add(JLabel("Simulation window: %s to %s (lookback %s)" %(self.startTime, self.endTime, self.lookbackTime)))
        obsP = panelDropDownBox("Observed Alternative:", altNames, altNameObs)
        unregP = panelDropDownBox("Unregulated Alternative:", altNames, altNameUnreg)
        self.obsAltBox = obsP.box
        self.unregAltBox = unregP.box
        altP.add(obsP)
        altP.add(unregP)
        center.add(altP, BorderLayout.NORTH)
        fileP = JPanel(GridLayout(5,1), border = BorderFactory.createTitledBorder("Files (set in scripts/DamagesPrevented/DPSettings.py)"))
        fileP.add(JLabel("Observed data:        %s" %DPSettings.OBSDATA_DSS))
        fileP.add(JLabel("Computed locals:      %s" %DPSettings.DPCALC_DSS))
        fileP.add(JLabel("Mini-simulations:     %s" %DPSettings.MINISIM_DSS))
        fileP.add(JLabel("Result tables:        %s" %DPSettings.RESULTS_DIR))
        fileP.add(JLabel("Config:               %s" %DPSettings.CONFIG_DIR))
        center.add(fileP, BorderLayout.CENTER)
        pane.add(center, BorderLayout.CENTER)

        butP = JPanel(GridLayout(4,1,5,5))
        butP.add(JButton("1. Transform gage data (Willamette Falls)", actionPerformed = self.transformBUT))
        butP.add(JButton("2. Compute water-balance locals (Observed alternative)", actionPerformed = self.waterBalanceBUT))
        butP.add(JLabel("    Then compute the Observed and Unregulated alternatives in ResSim.", JLabel.LEFT))
        butP.add(JButton("3. Run mini-simulations", actionPerformed = self.miniSimsBUT))
        pane.add(butP, BorderLayout.SOUTH)

        self.contentPane = pane
        self.pack()
        self.setLocationRelativeTo(None)
        self.setVisible(True)

    def _start(self, logName, func, args):
        initializeLogging(DPSettings.absPath("%s/%s.log" %(DPSettings.LOG_DIR, logName)))
        frame = frameProgress()
        tsk = TaskBackground(func, args + [frame.bar, frame.txtArea])
        tsk.execute()

    def transformBUT(self, e):
        self._start("TransformGageData", runTransformStep, [self.obsAltBox.getSelectedItem()])
    def waterBalanceBUT(self, e):
        self._start("WaterBalanceLocals", runWaterBalanceStep, [self.obsAltBox.getSelectedItem()])
    def miniSimsBUT(self, e):
        self._start("MiniSimulations", runMiniSimsStep,
                    [self.obsAltBox.getSelectedItem(), self.unregAltBox.getSelectedItem()])

class frameProgress(JFrame):
    """Progress window: messages on top, progress bar, OK button"""
    def __init__(self):
        JFrame.__init__(self, "Computation Progress")
        self.bar = JProgressBar(0,100, value=0, stringPainted=Constants.TRUE)
        self.txtArea = JTextAreaAutoScroll()
        pane = JPanel(BorderLayout(5,5), border = BorderFactory.createEmptyBorder(20,20,20,20))
        pane.add(JScrollPane(self.txtArea), BorderLayout.NORTH)
        pane.add(self.bar, BorderLayout.CENTER)
        butOK = JButton("OK")
        butOK.addActionListener(listenerCancel(self))
        pane.add(butOK, BorderLayout.SOUTH)
        self.contentPane = pane
        self.pack()
        self.setLocationRelativeTo(None)
        self.getRootPane().setDefaultButton(butOK)
        self.setVisible(True)

class panelDropDownBox(JPanel):
    """A label on the left and a drop-down on the right"""
    def __init__(self, promptText, itemList, defaultItem):
        JPanel.__init__(self, BorderLayout(), border = BorderFactory.createEmptyBorder(5,0,5,0))
        self.add(JLabel(promptText, JLabel.LEFT), BorderLayout.WEST)
        self.box = JComboBox(itemList)
        if defaultItem is not None:
            self.box.setSelectedItem(defaultItem)
        self.add(self.box, BorderLayout.EAST)

class JTextAreaAutoScroll(JTextArea):
    """A JTextArea that scrolls to the bottom when text is added"""
    def __init__(self):
        JTextArea.__init__(self, 20,70, margin = Insets(5,5,5,5), editable=Constants.FALSE)
    def printToGUI(self, msg):
        self.append("%s\n" %msg)
        self.setCaretPosition(self.getDocument().getLength()-1)

class listenerCancel(ActionListener):
    """Closes the given frame when its button is clicked"""
    def __init__(self, frameToRemove):
        self.frameToRemove = frameToRemove
    def actionPerformed(self, e):
        self.frameToRemove.dispose()

################################################################################
# LOGGING (to the console and to a file per step)

def initializeLogging(logFile):
    cFile.ensure_dir(logFile)
    logging.getLogger('').handlers = []
    logLevel = logging.INFO
    logging.basicConfig(level=logLevel, format='%(message)s', filename=logFile, filemode='w')
    console = logging.StreamHandler()
    console.setLevel(logLevel)
    console.setFormatter(logging.Formatter('%(message)s'))
    logging.getLogger('').addHandler(console)
    return logging.getLogger('')

def getCurrentLogFile():
    try:
        return logging.getLogger('').handlers[0].baseFilename
    except:
        return "Unknown File"

def closeLogging():
    l = logging.getLogger('')
    for handler in list(l.handlers):
        handler.close()
        l.removeHandler(handler)
