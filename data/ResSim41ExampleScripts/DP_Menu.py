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

#ClientAppWrapper moved to hec.rss.script in ResSim 4.1. 4.1 still accepts the old
#path but warns that support will be removed. Import both ways so this
#file runs under 4.1 and 3.5 alike.
try:
    from hec.rss.script import ClientAppWrapper        #ResSim 4.1
except ImportError:
    from hec.script import ClientAppWrapper            #ResSim 3.5
import os, sys
print "\nStarting Damages Prevented menu..."

#ClientApp moved from hec.client to hec.clientapp.client in ResSim 4.1
try:
    from hec.clientapp.client import ClientApp       #ResSim 4.1
except ImportError:
    from hec.client import ClientApp                 #ResSim 3.5

# The scripts folder must be on sys.path for "NWDJyLib" and "DamagesPrevented" to
# import. Try every way of finding it and use the first that holds both packages.
def _candidateScriptDirs():
    dirs = []
    try:
        dirs.append(ClientApp.Workspace().makeAbsolutePath("scripts"))
    except:
        pass
    try:
        dirs.append(os.path.join(ClientAppWrapper.getWatershed().getWkspDir(), "scripts"))
    except:
        pass
    try:
        dirs.append(os.path.dirname(os.path.abspath(__file__)))
    except:
        pass
    return dirs

def _hasPackages(d):
    return os.path.isfile(os.path.join(d, "NWDJyLib", "__init__.py")) and \
           os.path.isfile(os.path.join(d, "DamagesPrevented", "__init__.py"))

modulePath = None
triedDirs = _candidateScriptDirs()
for d in triedDirs:
    if _hasPackages(str(d)):
        modulePath = str(d)
        break
if modulePath is None:
    msg = "Could not find the scripts folder holding NWDJyLib and DamagesPrevented.\nLooked in:"
    for d in triedDirs:
        msg += "\n   %s   (NWDJyLib/__init__.py: %s, DamagesPrevented/__init__.py: %s)" %(d,
               os.path.isfile(os.path.join(str(d), "NWDJyLib", "__init__.py")),
               os.path.isfile(os.path.join(str(d), "DamagesPrevented", "__init__.py")))
    msg += "\nBoth folders must be directly inside <watershed>/scripts, each with an __init__.py."
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
