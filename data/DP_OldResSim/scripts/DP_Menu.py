###############################################################################
# DP Menu
# Author: Ryan Cahill 
# This script launches a selection menu from which the user can perform
# any step in the damages prevented process
# Intended to be run from the simulation module, with a simulation defined
###############################################################################

from hec.script import Constants, MessageBox, ClientAppWrapper
from hec.client import ClientApp
import os, sys
print "\nStarting Script..."

# First, make sure the Oracle jars are installed in ResSim jars/sys directory
try:
	import oracle
	#from oracle.jdbc import OracleTypes, OracleDriver
except ImportError:
	print "Put the ojdbc14.jar and orai18n.jar files into the ResSim installation" #alert!
	sys.exit()

# Next, make sure the Apache jars (xlsx files) are installed in ResSim jars/ext directory
# Don't need these, actually--using the built in jxl jars to produce a .xls file
'''
try:
	from org.apache.poi.xssf.usermodel import XSSFWorkbook
except ImportError:
	print "Put the apache .jar files into the ResSim installation" #alert!
	sys.exit()
'''

# Import custom modules
# Add the custom module locations to sys.path
# The modules do not need to individually check sys.path if it is done here
modulePath = os.path.join(ClientAppWrapper.getWatershed().getWkspDir(), "scripts")
#modulePath = r"C:\Watersheds\CRT\base\CRT_DamagesPrevented_2014-09-09\scripts"
if not modulePath in sys.path:
	sys.path.append(modulePath)
	sys.path.append(os.path.join(modulePath, "Modules")) #for nwdlib
	#Can't seem to load .jar files on the fly--they are in the ResSim program folder instead...
	#sys.path.append(os.path.join(modulePath, "Modules", "poi-3.9-20121203.jar")) #apache xlsx
	#sys.path.append(os.path.join(modulePath, "Modules", "ojdbc14.jar")) #oracle (should be in ResSim)
	#sys.path.append(os.path.join(modulePath, "Modules", "orai18n.jar")) #oracle	

#import nwdlib
from Modules import cRouting, cResSim, cDamPrev, cFile, cExcel, cTsUtils, cCWMS, cGUI, cUSGS, cLocFlows, cNatLakeARDB
#reloading the modules makes sure that any changes to the .py scripts are incorporated
reload(cRouting)
reload(cResSim)
reload(cDamPrev)
reload(cFile)
reload(cExcel)
reload(cTsUtils)
reload(cCWMS)
reload(cGUI)
reload(cUSGS)
reload(cLocFlows)
reload(cNatLakeARDB)

# Create and display the GUI
gui = cGUI.frameMainSelector()

#### The below lines are for testing purposes only
'''
csvFile = r"C:\Watersheds\CRT\base\CRT_DamagesPrevented_RC_Working\shared\reservoirInflows.csv"
outDssFile = r"C:\Watersheds\CRT\base\CRT_DamagesPrevented_RC_Working\shared\testing.dss"
resvFile = r"C:\Watersheds\CRT\base\CRT_DamagesPrevented_RC_Working\shared\RAS-Reservoirs.list"
juncFile = r"C:\Watersheds\CRT\base\CRT_DamagesPrevented_RC_Working\shared\RAS-Junctions.list"
dShiftFile = r"C:\Watersheds\CRT\base\CRT_DamagesPrevented_RC_Working\shared\datumShifts.dat"
ratingFile = r"C:/Watersheds/CRT/base/CRT_DamagesPrevented_RC_Working/shared/NaturalRatingCurves.dss"
#frame = cGUI.frameProgress()

#cResSim.exportRASdataToDss("Observed", resvFile, juncFile, dShiftFile, outDssFile, True, frame.bar, frame.txtArea, ratingFile)
#cResSim.recomputeResvInflows("Observed", csvFile, outDssFile, frame.bar, frame.txtArea)
'''
