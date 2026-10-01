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

simName = "forCHPS"
altName = "InitCond"
watershedWkspFile = "/awips/chps_share/sa/20151021_ressim_jmp/ncrfc_sa/Models/hec/ressim/baldhill/base/Baldhill_for_CHPS/Sheyenne.wksp"
watershedDir = "/awips/chps_share/sa/20151021_ressim_jmp/ncrfc_sa/Models/hec/ressim/baldhill/base/Baldhill_for_CHPS"
lookBackTime =  "10OCT2015,12:00"
forecastTime = "11OCT2015,06:00"
endTime = "04NOV2015,12:00"
overridesDir = "/awips/chps_share/sa/20151021_ressim_jmp/ncrfc_sa/Models/hec/ressim/baldhill/overrides"
# false will not run from a hotstart file
#loadHotstart = True
loadHotstart = False
createHotstart = False
lookBackHours = 18

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
# Need to pass another variable to set the timestep if we need too.
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
opts.setCreateHotstart(createHotstart)
opts.setHoursToSave(lookBackHours)
# .. turn on save of a hotstart file at end of simulation
opts.setSaveAtEndofSim(createHotstart)
# .. turn on save of a hotstart file at end of lookback period
opts.setSaveAtLookback(createHotstart)

# .. turn on save of a hotstart file at specified intervals...
#opts.setSaveAtInterval(true)
# .. create an HecTime object to be the start time of the intervals at which you save hotstart files
#myHecTime = HecTime()
#myHecTime.set("10OCT2015,12:00")
#opts.setIntervalDateTime(myHecTime)
# .. specify the interval.  Defining the interval is a little weird.  It's a two-step process
# .. In the example below, I'm getting it to save every 12 hours.

#opts.setTimeStep(12)
#opts.setTimeIncrement(HecTime.HOUR_INCREMENT)

# .. turn on save of a hotstart file at a specific date and time
#opts.setSaveAtDateTime(true)
#myHecTime2 = HecTime()
#myHecTime2.set("04Jul2009,18:00")
#opts.setSaveAtDateTime(myHecTime2)

# .. turn on "use hotstart" and identify the alternative that wrote the hotstart to use.  
# ..   ResSim will figure out which file to use based on the simulation timewindow and the alternative name
opts.setLoadHotstart(loadHotstart);
opts.setLoadAltName(altName);
rssAlt.setModified(true)

# .. since we are making the changes to the alternative after it is already in the simulation, then the 
# hotstart files will not have been extracted when the simulation was created, so we must run the extract again.  Grrr.
simPeriod=simRun.getSimulation()
simPeriod.runExtract(simPeriod.getSimulationExtract(ClientApp.Workspace()))

# Commented out this portion from CNRFC because it didn't work, not sure why it is needed anyway. -- gks 5/16/13
#if (loadHotstart):
#    shutil.copytree(watershedDir + "/rss/hotstarts", watershedDir + "/rss/" + simName+ "/rss/hotstarts")

#end of state handling

#Set the Log Level, normally it is 3, range 1-10, added by gks, mbrfc
#Uncomment when needed.
#LogLevel = 10
#rssAlt.setLogLevel(LogLevel)

simModule.computeRun(simRun, -1, Constants.TRUE, Constants.TRUE)

#save the workspace
ClientApp.Workspace().saveWorkspace()

ClientApp.frame().exitApplication()