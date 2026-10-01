'''

Utility to dump all variables at each time step from a scripted
  rule or state variable as json file. See R code at bottom for further
  processing to csv.
  
Usage:
    Import (assuming script in .../scripts/NWDJyLib/ResSim folder):
    
    from NWDJyLib.ResSim import cVariableTracking 
    
    Add to Scripted rule script in runRuleScript prior to any returns:
    
    cVariableTracking.writeParameters(network, currentRule, currentRunTimestep)
    
    Add to state variable scripts (external or ResSim) prior to any returns:
    
    cVariableTracking.writeParameters(network, currentVariable, runTimestep)
    
'''

import os, json

def writeParameters(network, writeObj, runTimestep):
    # Get the object name, parameter names, and time step string
    varNames = writeObj.varsListKeys()
    hTime = runTimestep.getHecTime()
    timeString = hTime.toString()
    # Initialize an empty dictionary into the rule/SV
    if not writeObj.varExists("trackingDict"):
        writeObj.varPut("trackingDict", {})
    trackingDict = writeObj.varGet("trackingDict")
    # Add a new element in tracking dictionary for current timestep
    trackingDict[timeString] = {}
    # Iterate through each variable, store in dictionary
    for n in varNames:
        if n == "trackingDict": continue
        trackingDict[timeString][n] = str(writeObj.varGet(n))
    # If the object to write is an external SV, write out dictionary keys too
    if writeObj.varExists("thisSV"):
        svObj = writeObj.varGet("thisSV")
        for n in svObj.keys():
            if n == "trackingDict": continue
            trackingDict[timeString][n] = str(svObj[n])
    # Put the tracking dictionary back in rule/SV object
    writeObj.varPut("trackingDict", trackingDict)
    # If this is the last timestep, then write to file
    endTime = network.getRssRun().getRunTimeWindow().getEndTime()
    if endTime.compareTimes(hTime) == 0:
        # Store a *.txt file with same name of <obj name>_<alt name>.txt 
        #   in simulation dir
        # Get simulation dir
        altSetupSV = network.getStateVariable("Alternative_Setup")
        fileNameSimulation = altSetupSV.varGet("fileNameSimulation")
        simDir = os.path.dirname(fileNameSimulation)
        # Pull alternative and object name, form *.txt save path
        altName = network.getAlternative().getName().split(":")[-1]
        objName = writeObj.getName()
        jsonFilePath = os.path.join(simDir, objName+"_"+altName+".txt")
        # Serializing json and saving to file
        jsonString = json.dumps(trackingDict, indent = 4)
        with open(jsonFilePath, "w") as f:
            f.write(jsonString)
    return None
    


#--------------------------------------------#
# R Code to format from json *.txt to *.csv: #
#--------------------------------------------#
'''

library(rjson)
library(tidyverse)
library(tools)

fNames = c(
        <file 1>,
        <file 2>,
        <file 3>,
        ...
        )

#' Convert nested, time-indexed json text file to csv
jsonTimeIndexFileToCSV <- function(fName){
  fromJSON(file = fName) %>% 
    map(as.data.frame) %>%
    bind_rows(.id = "time") %>%
    mutate(time = as.Date(time, format = "%d %B %Y")) %>%
    arrange(time) %>%
    write_csv(sprintf("c:/temp/%s.csv", basename(file_path_sans_ext(fName))))
  return(NULL)
}

fNames %>% map(jsonTimeIndexFileToCSV)

'''








