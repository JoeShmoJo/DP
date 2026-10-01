"""
This module contains code to control ResSim in an automated fashion.
With the functionality here, you can programmatically control ResSim without
actually being in the ResSim GUI. This functionality is used in the AFDR 
"damages prevented" processing and NWD ESP and observed data processing, 
see :any:`DPMenuGUI`, :any:`cDamPrev`, :any:`ResSimTasks` for applications.
Almost all of the functionality here assumes you are operating in the "Simulation" module.
Note that to use most of the functionality here, you need to launch the jython
script from within ResSim, or pass the script as an argument to the ResSim.exe
file. Running straight up Jython or this script from within DSS-VUE won't work,
as the ClientApp and  ResSim classes won't be defined properly.
"""
from hec.script import Constants
#ClientAppWrapper moved to hec.rss.script in ResSim 4.1. 4.1 still accepts the old
#path but warns that support will be removed. Import both ways so this
#file runs under 4.1 and 3.5 alike.
try:
    from hec.rss.script import ClientAppWrapper        #ResSim 4.1
except ImportError:
    from hec.script import ClientAppWrapper            #ResSim 3.5
#ResSim moved to hec.rss.script in ResSim 4.1. 4.1 still accepts the old
#path but warns that support will be removed. Import both ways so this
#file runs under 4.1 and 3.5 alike.
try:
    from hec.rss.script import ResSim        #ResSim 4.1
except ImportError:
    from hec.script import ResSim            #ResSim 3.5
#ClientApp moved from hec.client to hec.clientapp.client in ResSim 4.1. Import it
#both ways so this file runs under 4.1 and 3.5 alike.
try:
    from hec.clientapp.client import ClientApp       #ResSim 4.1
except ImportError:
    from hec.client import ClientApp                 #ResSim 3.5
from hec.model import RunTimeStep, RunTimeWindow
from java.lang import System
import os, sys, logging

#Custom modules
from NWDJyLib import cTimes

################################################################################
# STATIC INPUT

################################################################################
# CLASS DEFINITIONS

# END OF CLASS DEFINITIONS
################################################################################
# FUNCTION DEFINITIONS

def openWatershed(watershed, watershedDir = None) :
    """
    Opens a specified watershed in ResSim. Adapted from Mike Perryman of HEC.
    
    :param str watershed: The directory name or the .wksp file
    :return watershed: The watershed
    :rtype: hec.rss.client.ClientWorkspace
    """
    # determine watershed info from the parameters
    if watershedDir is not None :
        openWatershed(os.path.join(watershedDir, watershed))
    if os.path.exists(watershed) :
        if os.path.isfile(watershed) :
            # watershed param is workspace filename
            watershedName = os.path.basename(os.path.dirname(watershed))
            wkspFileName = watershed
        else :
            # watershed param is watershed directory
            watershedName = os.path.basename(watershed)
            wkspFileName = os.path.join(watershed, "%s.wksp" % watershedName)
    else :
        newWatershed = os.path.join(
            ClientApp.app().getAppStartDir(), 
            "watershed", 
            "base", 
            watershed)
        if os.path.exists(newWatershed) :
            return openWatershed(newWatershed)
        else :
            raise Exception("Unable to open watershed %s" % newWatershed)
    # open the watershed and verify we were sucessful
    ResSim.openWatershed(wkspFileName.replace(os.sep, "/"))
    if ResSim.getWatershedName() != watershedName :
        raise Exception("Unable to open watershed %s" % wkspFileName)
    return ResSim.getWatershed()

def saveWatershed():
    """Saves the watershed that is currently open"""
    ClientApp.Workspace().saveWorkspace()
    return True
    
def closeResSim():
    """
    Shuts down ResSim, closing down any watershed that happens to be open.
    Typically used when running a Jython script via the ResSim executable.
    If this isn't used, ResSim will just hang out and the calling batch file
    will stall.
    """
    #This closes down the watershed, but doesn't exit ResSim
    #This line really screws things up when running on the server--better just to exit
    #ResSim.closeWatershed() 
    #To exit ResSim, must close the Java Virtual Machine (sys.exit() doesn't work)
    System.exit(0)
    #The below line should work if the GUI is open
    #ClientApp.frame().exitApplication()
    return True
    
def setModule(moduleName):
    """
    Sets ResSim to the specified module, and returns the module.
    Acceptable input are "Simulation", "Reservoir Network", and "Watershed Setup"
    
    :return currentModule: The module it got set to (None if unsuccessful)
    :rtype: RSimSimulationMode
    """
    if `ResSim.getCurrentModule()` != moduleName : 
        ResSim.selectModule(moduleName)
    currentModule = ResSim.getCurrentModule()
    if `currentModule` != moduleName :
        raise Exception( "Unable to switch to %s module." % moduleName)
    return currentModule

def get10CharAltName(altName):
    """
    In ResSim simulations, sometimes the alternative name needs to be 10 characters.
    This function returns the 10-character equivalent, with hyphens appeneded
    to the end. E.g. "Test" becomes "Test------"
    """
    #pad the alternative name with dashes to 10 characters
    altNamePadded = altName
    altNamePadded = altNamePadded.replace(' ', '$')
    altNamePadded = altNamePadded.ljust(10)
    altNamePadded = altNamePadded.replace(' ', '-')
    altNamePadded = altNamePadded.replace('$', ' ')
    return altNamePadded

def getSimulation(simulationName=None) :
    """
    Verify that ResSim is in the correct module and has simulation open
    
    :param str simulationName: (Optional) If supplied, the name of the simulation to open.
                        If omitted, the currently open simulation will be returned.
    :return simulation:   The currently active simulation
    :rtype: SimulationPeriod
    """
    module = ResSim.getCurrentModule() #hec.rss.client.RSimSimulationMode
    #module = ClientAppWrapper.getCurrentModule() #alternately, ResSim simply extends ClientAppWrapper
    if module.getName() != "Simulation" : 
        raise AssertionError, "ResSim is in %s module, Simulation module is required" % `module`
    if simulationName:
        if not module.openSimulation(simulationName):
            raise Exception('Could not open simulation "%s".' % simulationName)
    simulation = module.getSimulation()
    if not simulation :
        raise AssertionError, "Must have a simulation open."
    return simulation

def createSimulation(simName, altNames, lookbackTimeStr, startTimeStr, endTimeStr):
    """
    Creates a simulation in ResSim. Need to do :func:`rerunExtract` before computing.
    
    :param str simName: The name you want the simulation to be called
    :param list altNames: A list of strings of the alternatives to include
                         (e.g. ["alt1", "alt2"])
    :param str time: time strings in any valid format with times.
                     e.g. "01Jan2004 1200" or "01JAN2004,12:00"
    :return: The SimulationPeriod object that is created
    """
    #First need to convert the alternative names into their 10-character equivalent
    altNames10 = [get10CharAltName(nm) for nm in altNames]
    simModule = setModule("Simulation")
    simulation = simModule.createSimulation(
        simName,"descrip", lookbackTimeStr, startTimeStr, endTimeStr, 1,
        HecTime.HOUR_INCREMENT, altNames10
        )
    return simulation

def deleteSimulation(simulationName):
    """
    Deletes a simulation if it exists. If it doesn't exist, will return None.
    
    :param str simulationName: The name of the simulation (case-sensitive)
    """
    if simModule.simulationExists(simulationName):
        simModule.deleteSimulation(simulationName)
        return True
    else:
        return None

def getSimulationTimes(simulation):
    """
    Gets the timewindow of the provided simulation
    
    :param SimulationPeriod simulation: The simulation to check output
    :return startTime, endTime, lookbackTime: HecTime objects of the simulation window
    """
    runTimeWindow = simulation.getRunTimeWindow()
    startTime = runTimeWindow.getStartTimeString()
    endTime = runTimeWindow.getEndTimeString()
    lookbackTime = runTimeWindow.getLookbackTimeString()
    return startTime, endTime, lookbackTime 
    
def setSimulationTimes(simulation, startTime, endTime, lookbackTime):
    """
    Sets the timewindow of the provided simulation (reverse of :func:`getSimulationTimes`)
    It doesn't actually get saved to disk, and you can set the times
    to whatever you like. Any future calls of :func:`getSimulationTimes` will now reflect
    the changes you make here.
    
    :param SimulationPeriod simulation: The simulation to modify
    :param startTime,endTime,lookbackTime: HecTime or string (e.g. "01Jan2005 0000"). 
                      If time not supplied, it will be inferred
    """
    #The times need to have dates in the form of "01Aug2005 0000"
    startTimeStr = cTimes.getStandardTimeStr(startTime, endOfDay=False)
    endTimeStr = cTimes.getStandardTimeStr(endTime, endOfDay=True)
    lookbackTimeStr = cTimes.getStandardTimeStr(lookbackTime, endOfDay=False)
    simulation.setStartDate(startTimeStr)
    simulation.setEndDate(endTimeStr)
    simulation.setLookbackDate(lookbackTimeStr)
    return True
    
def getActiveRun(simulation):
    """
    Returns the active RssSimRun object
    
    :param SimulationPeriod simulation: The input SimulationPeriod object to search
    """
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
    """
    Returns the RssRun of the simulation. Will return None if the name isn't found.
    
    :param str rssRunName: The name of the alternative to retrieve (e.g. "Test-----0", not "Test")
    """
    getSimulation() #just do the check to see we're in the right place
    module = ResSim.getCurrentModule() #hec.rss.client.RSimSimulationMode
    rssRunObj = module.getRssRun(rssRunName)
    return rssRunObj

def getListOfOutputFParts(simulation):
    """
    Returns a list of strings corresponding to the output FParts for the 
    simulation (SimulationPeriod)
    """
    fParts=[]
    for run in simulation.getSimulationRuns(): 
        fPart = run.getKey().split(":")[0]
        fParts.append(fPart)    
    return fParts   

def getListOfAltNames(simulation):
    """
    Returns a list of strings with all of the alternatives in the 
    simulation (SimulationPeriod)
    """
    altNames = []
    for run in simulation.getSimulationRuns():
        altNames.append(run.getUserName())
    return altNames
    
def getSpecificRun(simulation, rssRunName):
    """
    Returns the RssSimRun of the simulation. Will return None if the name isn't found
    
    :param SimulationPeriod simulation: The input SimulationPeriod object to search
    :param str rssRunName: The name of the alternative to retrieve (e.g. "Test", not "Test-----0")
    """
    return simulation.getSimulationRun(rssRunName)
    
def getNetwork(run):
    """Returns the network (RssSystem) for the given run (RssSimRun)"""
    return run.getRssSystem()

def getOutputFpart(run):
    """Returns the output FPart for the provided run (RssSimRun)"""
    fPart = run.getKey().split(":")[0]
    return fPart
    
def getCurrentNetwork():
    """Returns the currently active network (RssSystem)"""
    simulation = getSimulation()
    run = getActiveRun(simulation)
    return run.getRssSystem()

def getCurrentRssAlt():
    """Returns the currently active RssAlt"""
    simulation = getSimulation()
    run = getActiveRun(simulation)
    return run.getRssAlt()
    
def getCurrentRssAltName():
    """
    Returns the short name of the currently active RssAlt 
    (e.g. "Test", not "Test-----0")
    """
    simulation = getSimulation()
    run = getActiveRun(simulation)
    return run.getUserName()

def rerunExtract(simulation):
    """
    Reruns the time series extract of a simulation.
    Equivalent to going to the Simulation dropdown menu and hitting "Rerun Extract"
    
    :param SimulationPeriod simulation:
    """
    simulation.runExtract(simulation.getSimulationExtract(ClientApp.Workspace()))
    return True

def computeAlt(simulation, altName):
    """
    Computes an alternative
    
    :param SimulationPeriod simulation:
    :param str altName: The name of the alternative (e.g. "Test", not "Test-----0")
    """
    module = ResSim.getCurrentModule() #hec.rss.client.RSimSimulationMode
    simRun = getSpecificRun(simulation, altName)
    #rssAlt.setModified(true)
    simModule.computeRun(simRun, -1, Constants.TRUE, Constants.TRUE)
    return True
    
