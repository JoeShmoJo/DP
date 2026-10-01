"""
Script intended to be run in regular python, not Jython
When an ensemble compute is run in multi-thread, often some of the simulations
will fail inexplicably, with nonsensical error messages.
When this happens, we need to kick off another comput for just the events that failed.
This script detects which events failed, and prints out a string of these events
that can be copied directly into the "Ensemble" tab of the simulation in ResSim
to get these stragglers run.
"""
import pandas as pd
import numpy as np
import os, sys, csv

################################################################################
# USER INPUT
SIMULATION_NAME = "Ensemble_Synthetics" #simulation name in ResSim
MAX_ENSEMBLE_MEMBER = 2454 #The number of ensemble members (1 through this number will be checked)

################################################################################
# FUNCTION DEFINITIONS
def createReadableYearRange(yearList):
    """
    Takes a list of events, 
    e.g. [1945, 1946, 1947, 1970]
    
    and converts it to a human-readable string with 6 digits for input to ResSim
    e.g. "001945-001947, 001970"
    
    """
    years = sorted(yearList)
    outStr = str(years[0]).zfill(6)
    prevYear = years[0]
    inRange = False #running variable to keep track of if we are running up a range like 1945-xxxx
    for i in range(1, len(yearList)):
        prevYear = years[i-1]
        curYear = years[i]
        if curYear == prevYear+1 and i == len(yearList)-1: 
            outStr += "-%s" %str(curYear).zfill(6)
        elif curYear == prevYear+1:
            inRange = True
            continue
        elif curYear > prevYear+1:
            if inRange: 
                #We had been running up a range, need to end that one first
                outStr += "-%s" %str(prevYear).zfill(6)
            outStr += ", %s" %str(curYear).zfill(6)
            inRange = False
    return outStr

#####  Main  ###################################################################
# MAIN CODE
outCSVFile = "../../rss/%s/PeakExtract_FRM_Base_E.csv" %SIMULATION_NAME
dfResults = pd.read_csv(outCSVFile)
dfIdeal = pd.DataFrame(data=np.arange(1,MAX_ENSEMBLE_MEMBER+1), columns=["ResSimID"])
dfMerge = pd.merge(dfIdeal, dfResults, how="left", on="ResSimID")
dfIncomplete = dfMerge.loc[dfMerge.isna().any(axis=1)]
outStr = createReadableYearRange(dfIncomplete["ResSimID"].to_list())
print(outStr)
