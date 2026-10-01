"""
Damages Prevented settings: where every input and output lives, and which
reservoirs are paired with a re-regulating dam.

Every path is relative to the watershed folder. The menu shows them, and each
step writes one line to its log saying which files it used.

Everything Damages Prevented uses lives under scripts/DamagesPrevented:
    DP_Download/out/obsData.dss   downloaded USGS/CWMS data (DP_Download/DP_Download.py, desktop Python)
    DPdata/DPcalc.dss             computed locals the alternatives read
                                  (Willamette Falls + water-balance locals)
    DPdata/MiniSimulations.dss    mini-simulation time series
    DPdata/Results/*.csv          flow reduction tables
    DPdata/logs/*.log             one log per step
"""
try:
    from hec.clientapp.client import ClientApp       #ResSim 4.1
except ImportError:
    from hec.client import ClientApp                 #ResSim 3.5

################################################################################
# USER INPUT
DP_DIR = "scripts/DamagesPrevented"
OBSDATA_DSS = DP_DIR + "/DP_Download/out/obsData.dss"    #downloaded USGS/CWMS data (DP_Download.py)
DATA_DIR = DP_DIR + "/DPdata"                            #everything the ResSim steps write
DPCALC_DSS = DATA_DIR + "/DPcalc.dss"                    #computed locals the Obs/Unreg alternatives read
MINISIM_DSS = DATA_DIR + "/MiniSimulations.dss"          #mini-simulation output time series
RESULTS_DIR = DATA_DIR + "/Results"                      #mini-simulation CSV tables
LOG_DIR = DATA_DIR + "/logs"                             #one log file per step

CONFIG_DIR = DP_DIR + "/config"
TRANSFORM_CSV = CONFIG_DIR + "/TransformedLocals.csv"    #gage transformations (Willamette Falls)
CONTROL_POINTS_TXT = CONFIG_DIR + "/ControlPoints.txt"   #junctions to report flow reductions at
RESERVOIRS_TXT = CONFIG_DIR + "/Reservoirs.txt"          #reservoirs to run with/without

#Reservoirs that release into a re-regulating reservoir. The pair is treated as
#one project in the mini-simulations, credited to the upstream reservoir.
REREG = {"Detroit": "Big Cliff", "Lookout Point": "Dexter"}

#Allow negative water-balance locals? Normally yes, so the Observed
#alternative reproduces the observed flows.
NEGATIVE_LOCALS_ALLOWED = True

#F part of the transformed gage records (must match the Timeseries tab)
TRANSFORM_FPART = "COMPUTED"

#The menu pre-selects the first alternative whose name contains these (any case)
OBS_ALT_HINT = "OBS"
UNREG_ALT_HINT = "UNR"

################################################################################

def absPath(relPath):
    """Absolute path of a file given relative to the watershed folder."""
    return ClientApp.Workspace().makeAbsolutePath(relPath)
