# name=test
# description=test
# displaytouser=true
from hec.script import *
from hec.script import ClientAppWrapper
from hec.script import ResSim
from hec.script import MessageBox
from hec.hecmath import DisplayUtilities
from hec.hecmath import *
from hec.client import ClientApp
from hec.heclib.util import HecTime
from java.lang import String
import jarray
import shutil


simName = "yubafeather_rs"
altName = "AltA"
watershedWkspFile = "/home/hec/fews-tests/YubaFeatherFCO/base/YubaFeatherFCO/YubaFeatherFCO.wksp"
watershedDir = "/home/hec/fews-tests/YubaFeatherFCO/base/YubaFeatherFCO"
lookBackTime =  "29JUN2009,12:00"
forecastTime = "30JUN2009,12:00"
endTime = "05JUL2009,12:00"
overridesDir = "null"

#pad the alternative name with dashes to 10 characters
altNamePadded = altName
altNamePadded = altNamePadded.replace(' ', '$')
altNamePadded = altNamePadded.ljust(10)
altNamePadded = altNamePadded.replace(' ', '-')
altNamePadded = altNamePadded.replace('$', ' ')

# open the watershed
ResSim.openWatershed(watershedWkspFile)
# to set the main application window visible
#ClientApp.frame().setVisible(1)
# select the simulation module
ResSim.selectModule("Simulation")
# get the simulation module
simModule = ResSim.getCurrentModule()
#if the simulation exists, delete it. does not remove its directory
#if os.path.exists(watershedDir + "/rss/" + simName):
if simModule.simulationExists(simName):
	simModule.deleteSimulation(simName)

alts = jarray.array([altNamePadded], String)
#create the simulation 1 hour time step
simulation = simModule.createSimulation(simName,"test simulation", lookBackTime, forecastTime, endTime, 1, HecTime.HOUR_INCREMENT, alts)
#moves the overrides files into the new simulation
overrideName = altNamePadded + "0.dss"
if os.path.exists(overridesDir + "/" + overrideName):
	shutil.copy(overridesDir + "/" + overrideName, watershedDir + "/rss/" + simName+ "/rss/" + overrideName)

simRun = simModule.getSimulationRun(altName)

true, false = 1, 0
print "About to hit hotstart stuff..."
#set hotstart options
# .. get the alternative
rssAlt = simRun.getRssAlt()
# .. get the options spec
print "Before getHotstartOptions"
opts = rssAlt.getHotstartOptions()
# .. turn on option to write hotstart files and define length of "lookback" to be saved with hotstart.
opts.setCreateHotstart(false)
opts.setHoursToSave(24)
# .. turn on save of a hotstart file at end of simulation
opts.setSaveAtEndofSim(true)
# .. turn on save of a hotstart file at end of lookback period
opts.setSaveAtLookback(true)

# .. turn on save of a hotstart file at specified intervals...
opts.setSaveAtInterval(true)
# .. create an HecTime object to be the start time of the intervals at which you save hotstart files
myHecTime = HecTime()
myHecTime.set("30Jun2009,24:00")
opts.setIntervalDateTime(myHecTime)
# .. specify the interval.  Defining the interval is a little weird.  It's a two-step process
# .. In the example below, I'm getting it to save every 12 hours.
opts.setTimeStep(12)
opts.setTimeIncrement(HecTime.HOUR_INCREMENT)

# .. turn on save of a hotstart file at a specific date and time
opts.setSaveAtDateTime(true)
myHecTime2 = HecTime()
myHecTime2.set("04Jul2009,18:00")
opts.setSaveAtDateTime(myHecTime2)

# .. turn on "use hotstart" and identify the alternative that wrote the hotstart to use.  
# ..   ResSim will figure out which file to use based on the simulation timewindow and the alternative name
opts.setLoadHotstart(true);
opts.setLoadAltName(altName);
rssAlt.setModified(true)

print "About to computeRun..."
simModule.computeRun(simRun, -1, Constants.TRUE, Constants.TRUE)
#save the workspace
print "We're above the save workspace now."
ClientApp.Workspace().saveWorkspace()
print "We're done saving? Maybe."
ClientApp.frame().exitApplication()
