# Imports
#ResSim moved to hec.rss.script in ResSim 4.1. 4.1 still accepts the old
#path but warns that support will be removed. Import both ways so this
#file runs under 4.1 and 3.5 alike.
try:
    from hec.rss.script import ResSim        #ResSim 4.1
except ImportError:
    from hec.script import ResSim            #ResSim 3.5
from hec.script import Constants
import os

# User inputs: watershed directory, watershed name, watershed .wksp file, simulation name, alternative name
watershedDir = os.path.realpath(sys.argv[0])
watershedName = sys.argv[1]
watershedWkspName = sys.argv[2]
simName = sys.argv[3]
altName = sys.argv[4]

# watershedDir = r'C:\Data\Tasks\District Models\NWS_VA\NWS_VA_HAH\test\debug_externalModules\NWS_Green'
# watershedName = "NWS_Green"
# watershedWkspName = "NWS_Green.wksp"
# simName = "2017.10.25-1200"
# altName = "Test Run2"

print '#===================================================='
print '#=== User inputs: =================================='
print "Argument 1 -> Watershed Directory =", watershedDir
print "Argument 2 -> Watershed Name =", watershedName
print "Argument 3 -> Watershed .wksp Name =", watershedWkspName
print "Argument 4 -> Simulation Name =", simName
print "Argument 5 -> Alternative Name =", altName
print '#===================================================='

# ResSim only likes unix-style path
watershedWkspFile = os.path.join(watershedDir, watershedWkspName).replace(os.sep, "/")

# Open the watershed
ResSim.openWatershed(watershedWkspFile)
print '#===================================================='
print 'ResSim Watershed Name:', ResSim.getWatershedName()
print '#===================================================='

# If watershed name doesn't match what is expected, raise exception
if ResSim.getWatershedName() != watershedName :
    raise Exception("Unable to open watershed %s" % watershedWkspFile)

# Open the simulation module
ResSim.selectModule('Simulation')

# Get the current module
print '#===================================================='
print '#=== Opening simulation module ======================'
print '#===================================================='
simMode = ResSim.getCurrentModule()
simMode.resetWorkspace()
# Print the type and name of the simMode object (not necessary, but useful syntax for debugging)
print '#=== simMode type ==='
print type(simMode)
print '#=== simMode name ==='
print simMode.getName()

# Open the target simulation
print '#===================================================='
print '#=== Opening simulation ============================='
print '#===================================================='
simMode.openSimulation(simName)
simMode.runSimulationExtract()
simulation = simMode.getSimulation()
simulation.setComputeAll(1)
simRun = simulation.getSimulationRun(altName)
print '#===================================================='
print 'Simulation Name:', simName
print '#===================================================='

# Compute and save the target simulation, then close the watershed
print '#===================================================='
print '#=== Computing simulation ==========================='
print '#===================================================='
simMode.computeRun(simRun, -1, Constants.TRUE, Constants.TRUE)
print '#===================================================='
print '#=== Saving simulation =============================='
print '#===================================================='
ResSim.getCurrentModule().saveSimulation()
print '#===================================================='
print '#=== Closing watershed =============================='
print '#===================================================='
ResSim.closeWatershed()
print '#===================================================='