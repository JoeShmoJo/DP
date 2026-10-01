# -*- coding: ascii -*-
#ResSim moved to hec.rss.script in ResSim 4.1. 4.1 still accepts the old
#path but warns that support will be removed. Import both ways so this
#file runs under 4.1 and 3.5 alike.
try:
    from hec.rss.script import ResSim        #ResSim 4.1
except ImportError:
    from hec.script import ResSim            #ResSim 3.5
from hec.script import Constants
import os
import sys
import traceback
import time

def _write_log(log_path, msg):
    try:
        f = open(log_path, "a")
        f.write(msg + "\n")
        f.close()
    except:
        pass

def _stamp():
    try:
        y, mo, d, h, mi, s = time.localtime()[:6]
        return "%04d-%02d-%02d %02d:%02d:%02d" % (y, mo, d, h, mi, s)
    except:
        return ""

def parse_args(argv):
    """
    Supports both of these launch styles:

    A) BAT/normal style (script path is argv[0]):
       argv = [script.py, watershedDir, watershedName, wkspFileOrPath, simName, runName]

    B) ResSim-driver style (script path NOT passed; argv[0] is watershedDir):
       argv = [watershedDir, watershedName, wkspFileOrPath, simName, runName]
    """
    # Determine if argv[0] looks like a .py file path
    a0 = argv[0] if len(argv) > 0 else ""
    ext = os.path.splitext(a0)[1].lower()

    if ext == ".py":
        # Style A
        if len(argv) < 6:
            raise Exception("Expected 5 args after script: watershedDir, watershedName, wkspFile, simName, runName")
        watershedDir  = os.path.realpath(argv[1])
        watershedName = argv[2]
        wksp_in       = argv[3]
        simName       = argv[4]
        runName       = argv[5]
        script_dir    = os.path.dirname(os.path.abspath(argv[0]))
    else:
        # Style B
        if len(argv) < 5:
            raise Exception("Expected args: watershedDir, watershedName, wkspFile, simName, runName")
        watershedDir  = os.path.realpath(argv[0])
        watershedName = argv[1]
        wksp_in       = argv[2]
        simName       = argv[3]
        runName       = argv[4]
        # Best guess for script dir if script path isn't provided
        script_dir    = os.getcwd()

    # Resolve workspace path:
    # - If wksp_in is already a path to a file, use it.
    # - Else treat it as a filename inside watershedDir.
    wksp_candidate = os.path.realpath(wksp_in)
    if os.path.isfile(wksp_candidate):
        wkspFile = wksp_candidate
    else:
        wkspFile = os.path.realpath(os.path.join(watershedDir, wksp_in))

    return script_dir, watershedDir, watershedName, wkspFile, simName, runName

def main():
    script_dir = os.getcwd()
    log_path = os.path.join(script_dir, "RunResSim_Headless.log")

    try:
        # Parse
        script_dir, watershedDir, watershedName, wkspFile, simName, runName = parse_args(sys.argv)
        log_path = os.path.join(script_dir, "RunResSim_Headless.log")

        _write_log(log_path, "%s ENTER" % _stamp())
        _write_log(log_path, "ARGV=%s" % str(sys.argv))
        _write_log(log_path, "watershedDir=%s" % watershedDir)
        _write_log(log_path, "watershedName=%s" % watershedName)
        _write_log(log_path, "wkspFile=%s" % wkspFile)
        _write_log(log_path, "simName=%s" % simName)
        _write_log(log_path, "runName=%s" % runName)

        if not os.path.isfile(wkspFile):
            raise Exception("Workspace file not found: %s" % wkspFile)

        # ResSim prefers forward slashes
        wkspFile_unix = wkspFile.replace(os.sep, "/")

        # Open watershed
        ResSim.openWatershed(wkspFile_unix)
        actual = ResSim.getWatershedName()
        _write_log(log_path, "Opened watershed, ResSim.getWatershedName()=%s" % actual)

        if actual != watershedName:
            raise Exception("Watershed name mismatch. Expected '%s' got '%s'." % (watershedName, actual))

        # Simulation module
        ResSim.selectModule("Simulation")
        simMode = ResSim.getCurrentModule()
        simMode.resetWorkspace()

        # Open simulation
        simMode.openSimulation(simName)
        simulation = simMode.getSimulation()

        # Compute run
        try:
            simulation.setComputeAll(1)
        except:
            pass

        simRun = simulation.getSimulationRun(runName)
        if simRun is None:
            try:
                names = list(simulation.getSimulationRunNames())
            except:
                names = []
            raise Exception("Run '%s' not found. Available: %s" % (runName, ", ".join(names) if names else "<none>"))

        _write_log(log_path, "Computing run...")
        simMode.computeRun(simRun, -1, Constants.TRUE, Constants.TRUE)

        _write_log(log_path, "Saving simulation...")
        ResSim.getCurrentModule().saveSimulation()

        _write_log(log_path, "Closing watershed...")
        ResSim.closeWatershed()

        _write_log(log_path, "%s DONE OK" % _stamp())
        return 0

    except:
        _write_log(log_path, "%s ERROR" % _stamp())
        _write_log(log_path, traceback.format_exc())
        try:
            ResSim.closeWatershed()
        except:
            pass
        return 1

if __name__ == "__main__":
    sys.exit(main())