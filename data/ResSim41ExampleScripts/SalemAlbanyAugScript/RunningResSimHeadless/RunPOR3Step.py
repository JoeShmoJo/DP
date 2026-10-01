# coding: ascii
# Minimal, short-line Jython script to run ResSim headless.

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

# -------- defaults if no args are passed --------
DFLT_DIR  = r"C:\CWMS\watershed\Willamette2026"
DFLT_WSN  = "Willamette2026"
DFLT_WKSP = "Willamette2026.wksp"
DFLT_SIM  = "13Feb2026"
DFLT_ALT  = "Temp1Day"
# -----------------------------------------------

def echo_inputs(d, w, f, s, a, mode):
    print '#===================================================='
    print '#=== Headless Inputs (%s) ===========================' % mode
    print 'Watershed Dir  =', d
    print 'Watershed Name =', w
    print 'Workspace File =', f
    print 'Simulation     =', s
    print 'Alternative    =', a
    print '#===================================================='

def main():
    try:
        if len(sys.argv) >= 6:
            d = os.path.realpath(sys.argv[1])
            w = sys.argv[2]
            f = sys.argv[3]
            s = sys.argv[4]
            a = sys.argv[5]
            mode = 'ARGS'
        else:
            d = DFLT_DIR
            w = DFLT_WSN
            f = DFLT_WKSP
            s = DFLT_SIM
            a = DFLT_ALT
            mode = 'FALLBACK'

        echo_inputs(d, w, f, s, a, mode)

        wksp = os.path.join(d, f).replace(os.sep, '/')

        # Open watershed
        ResSim.openWatershed(wksp)
        print '#===================================================='
        actual = ResSim.getWatershedName()
        print 'ResSim Watershed Name:', actual
        print '#===================================================='

        # Compare names with short vars (avoid long wrapped lines)
        exp = w
        if actual != exp:
            raise Exception("Watershed name mismatch. Expected '%s' got '%s'." %
                            (exp, actual))

        # Open Simulation module
        ResSim.selectModule('Simulation')
        sm = ResSim.getCurrentModule()
        sm.resetWorkspace()

        print '#===================================================='
        print '#=== Opening simulation ============================='
        print '#===================================================='
        sm.openSimulation(s)

        # Optional extract
        sm.runSimulationExtract()

        # Compute
        sim = sm.getSimulation()
        try:
            sim.setComputeAll(1)
        except:
            pass

        run = sim.getSimulationRun(a)
        if run is None:
            try:
                names = list(sim.getSimulationRunNames())
            except:
                names = []
            raise Exception("Run '%s' not found. Available: %s" %
                            (a, ', '.join(names) if names else '<none>'))

        print '#===================================================='
        print '#=== Computing simulation ==========================='
        print '#===================================================='
        sm.computeRun(run, -1, Constants.TRUE, Constants.TRUE)

        print '#===================================================='
        print '#=== Saving simulation =============================='
        print '#===================================================='
        ResSim.getCurrentModule().saveSimulation()

        print '#===================================================='
        print '#=== Closing watershed =============================='
        print '#===================================================='
        ResSim.closeWatershed()
        print '#======================== DONE ======================'
        return 0

    except:
        traceback.print_exc()
        try:
            ResSim.closeWatershed()
        except:
            pass
        return 1

if __name__ == '___main___':  # Jython ignores this; keep next line too
    pass
if __name__ == '__main__':
    sys.exit(main())
