# DON'T FORGET TO SAVE
SIM_NAME="2026.04.30-2400"
ALTERNATIVE_NAME_STEP1 = "Con_Season"
# SINGLE TRIAL FOR ENSEMBLE PLOTS
TRIAL = 1
# TRIALS FOR ALT_COMPARISON PLOTS
TRIAL_SUFFIXES = [0,1]
# TRIAL PLOT HORIZONTAL LINES
H_LINE_DICT = {
    "DET": {"Spillway": 1541, "IRRM": 1558.5},
}
# ENSEMBLE YEAR FOR OSI RUN
# This ensemble year's inputs will be assigned to ensemble year 2029
# which will be run when simulation is switched from ensemble to standard
# which will allow it to be edited with the OSI.
# 2026, 2027, and 2028 are the daily non-exceedance 25%, 50%, and 75% runs.
# OSI mods are tied to the ensemble year so changing this won't reset them.

ENSEMBLE_YEAR_TO_COPY = 2011




