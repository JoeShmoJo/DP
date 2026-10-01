###############################################################################
# DP Menu
# Author: Ryan Cahill
# Opens the Damages Prevented menu (scripts/DamagesPrevented/DPMenu.py).
# Run from the Simulation module, with the simulation holding the Observed and
# Unregulated alternatives open.
#
# Oct 2026: rewritten for the Willamette-only watershed in ResSim 4.1. The old
# menu imported NWDJyLib.AFDR (now zipped as NWDJyLib/AFDR.7z) and needed the
# jxl Excel jar, which ResSim 4.1 does not ship. The new steps live in
# scripts/DamagesPrevented and write CSV files instead of .xls.
###############################################################################

import os, sys
print "\nStarting Damages Prevented menu..."

#ResSim moved from hec.script to hec.rss.script in ResSim 4.1
try:
    from hec.rss.script import ResSim                  #ResSim 4.1
except ImportError:
    from hec.script import ResSim                      #ResSim 3.5

# The scripts folder must be on sys.path for "NWDJyLib" and "DamagesPrevented" to
# import. ResSim 4.1 runs this file from a copy in the user's AppData workspace
# (...AppData/Roaming/HEC/HEC-ResSim/4.1/CWMS/<watershed>/scripts/Modules/...),
# and getWkspDir() points there too. The open simulation's network knows the real
# watershed folder, the same way the scripted rules find it.
def _watershedScriptsDir():
    module = ResSim.getCurrentModule()
    if module.getName() != "Simulation":
        raise AssertionError("Damages Prevented runs from the Simulation module. ResSim is in the %s module." %module.getName())
    simulation = module.getSimulation()
    if not simulation:
        raise AssertionError("Open the simulation holding the Observed and Unregulated alternatives, then run Damages Prevented again.")
    for run in simulation.getSimulationRuns():
        return str(run.getRssSystem().makeAbsolutePathFromWatershed("scripts"))
    raise AssertionError("The open simulation has no alternatives.")

def _hasPackage(d, pkg):
    return os.path.isfile(os.path.join(d, pkg, "__init__.py"))

modulePath = _watershedScriptsDir()
if not (_hasPackage(modulePath, "NWDJyLib") and _hasPackage(modulePath, "DamagesPrevented")):
    msg = "The watershed scripts folder is\n   %s\n" %modulePath
    msg += "   NWDJyLib/__init__.py found: %s\n" %_hasPackage(modulePath, "NWDJyLib")
    msg += "   DamagesPrevented/__init__.py found: %s\n" %_hasPackage(modulePath, "DamagesPrevented")
    msg += "Both folders must be directly inside that scripts folder, each with an __init__.py."
    raise AssertionError(msg)
print "Scripts folder: %s" %modulePath
if not modulePath in sys.path:
    sys.path.append(modulePath)

from NWDJyLib import cRouting, cFile
from NWDJyLib.ResSim import cResSim, ResSimController
from NWDJyLib.DSS import cDSS, cTsUtils
from DamagesPrevented import DPSettings, cTransform, cWaterBalance, cMiniSims, DPMenu
#reload so edits to the scripts take effect without restarting ResSim
reload(cRouting)
reload(cFile)
reload(cDSS)
reload(cTsUtils)
reload(cResSim)
reload(ResSimController)
reload(DPSettings)
reload(cTransform)
reload(cWaterBalance)
reload(cMiniSims)
reload(DPMenu)

gui = DPMenu.frameMainSelector()
