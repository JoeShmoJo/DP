###############################################################################
# DP Menu
# Author: Ryan Cahill 
# This script launches a selection menu from which the user can perform
# any step in the damages prevented process
# Intended to be run from the simulation module, with a simulation defined
###############################################################################

from hec.script import Constants, MessageBox
#ClientAppWrapper moved to hec.rss.script in ResSim 4.1. 4.1 still accepts the old
#path but warns that support will be removed. Import both ways so this
#file runs under 4.1 and 3.5 alike.
try:
    from hec.rss.script import ClientAppWrapper        #ResSim 4.1
except ImportError:
    from hec.script import ClientAppWrapper            #ResSim 3.5
#ClientApp moved from hec.client to hec.clientapp.client in ResSim 4.1. Import it
#both ways so this file runs under 4.1 and 3.5 alike.
try:
    from hec.clientapp.client import ClientApp       #ResSim 4.1
except ImportError:
    from hec.client import ClientApp                 #ResSim 3.5
import os, sys
print "\nStarting Script..."

# First, make sure the necessary jars are installed in ResSim jars/sys directory
try:
	from jxl import Workbook
except ImportError:
	jarPath = r"X:\CRT2014\PDT\WAT\DamagesPrevented\ResSim\Required extra jar files\Excel (put in sys folder)"
	raise AssertionError( "Put the jxl.jar file into the ResSim installation. Files located here:\n%s" %jarPath)

# Import custom modules
# Add the custom module locations to sys.path
# The modules do not need to individually check sys.path if it is done here
modulePath = os.path.join(ClientAppWrapper.getWatershed().getWkspDir(), "scripts")
#modulePath = r"C:\Watersheds\CRT\base\CRT_DamagesPrevented_2014-09-09\scripts"
if not modulePath in sys.path:
	sys.path.append(modulePath)
	sys.path.append(os.path.join(modulePath, "AFDR")) 
	sys.path.append(os.path.join(modulePath, "DSS")) 
	sys.path.append(os.path.join(modulePath, "ResSim")) 
	sys.path.append(os.path.join(modulePath, "Utils")) 

#import nwdlib
from NWDJyLib import cRouting, cFile
from NWDJyLib.AFDR import DPMenuGUI, cDamPrev, cExcel, cLocFlows
from NWDJyLib.ResSim import cResSim
from NWDJyLib.DSS import cTsUtils
#reloading the modules makes sure that any changes to the .py scripts are incorporated
reload(cRouting)
reload(cResSim)
reload(cDamPrev)
reload(cFile)
reload(cExcel)
reload(cTsUtils)
reload(DPMenuGUI)
reload(cLocFlows)

# Create and display the GUI
gui = DPMenuGUI.frameMainSelector()

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
