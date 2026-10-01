'''
Initialization function for preparing data needed by scripts in the model
Script Name = Alternative_Setup
Parameter Name = Code; Parameter Type = Code

Do not reference this script in the model or set its "Always Compute" option.
This script reads in all the alt_config inputs from .json and stores them to local variables.
Then, other scripts can grab these variables at will.

typical usage:
    altSetupSV = network.getStateVariable("Alternative_Setup")
    someVariable = altSetupSV.varGet("someVariable")
'''


from hec.hecmath import DSS
from hec.rss.model import ScriptOpRule

# Imports for .xml parsing
import re

# custom CRT code, stored in $WATERSHED/scripts/NWDJyLib
from NWDJyLib import cLoadModules
from NWDJyLib.DSS.cDSS import writeTextToDss
from externalSVs.baseExternalSV import ExternalSV

# JSON parsing libs for alt_config
from com.xhaus.jyson import JysonCodec as json
from org.hjson import JsonValue

# filesystem utilities
import os, sys
import shutil
import time

class Alternative_Setup(ExternalSV):
    def initialization(self, network, currentVariable):
        #Jul2020, RSW: Load or reload modules. Append folder names in 'scripts' to list argument as needed
        cLoadModules.loadWatershedModules(network, ["NWDJyLib","externalSVs"])
        
        timeWindowStrComputeBlock = network.getRssRun().getCurrentComputeBlockRunTimeWindow().getTimeWindowString()
        timeWindowStr = network.getRssRun().getRunTimeWindow().getTimeWindowString()
        numStepsComputeBlock = network.getRssRun().getCurrentComputeBlockRunTimeWindow().getNumSteps()
        # Make sure no time blocking is occurring--stop the compute if it is happening
        if timeWindowStrComputeBlock != timeWindowStr:
            msg = "Stopping the Compute--this compute is time blocking"
            msg+= "\nThe model cannot run properly with time blocking"
            msg+= "\nEither reduce your compute time window or"
            msg+= "\nAllocate more memory to ResSim in the HEC-ResSim.config file"
            msg+= "\nFor a 64-bit machine, the line should read 'vmparam -mx6400' if you have that much RAM"
            msg+= "\nTo see how ResSim split up the time window, look at the top of the console log"
            msg+= "\nTime Window:   %s" % timeWindowStr
            msg+= "\nCompute Block: %s" % timeWindowStrComputeBlock
            network.printLogMessage(msg)
            network.printErrorMessage(msg)
            # Stop the compute if it is occurring
            return False
        
        #  Added .split(":")[-1] for ResSim standalone compatibility.
        thisRun = network.getRssRun()
        #  Added .split(":")[-1] for ResSim standalone compatibility.
        fullAltName = network.getAlternative().getName() #e.g. if running the 2nd trial of an alternative, "_Temp1Day2-:Temp1Day--0:Temp1Day"
        altName = fullAltName.split(":")[-1] #e.g. "Temp1Day"
        runName = thisRun.getRunId()  # includes dash padding, e.g. "Temp1Day--2"
        currentVariable.varPut("altName", altName)
        
        ## Check the type of run
        dssOutputFpart = thisRun.getOutputFPart()
        dssFileNameSimulation = thisRun.getDSSOutputFile()
        currentVariable.varPut("dssOutputFpart", dssOutputFpart)
        currentVariable.varPut("dssFileNameSimulation", dssFileNameSimulation)
        fileNameSimulation = network.makeAbsolutePathFromWatershed(dssFileNameSimulation)
        if fileNameSimulation.find("forecast") > 0: # CWMS compute
            cwmsCompute = True
        else:
            cwmsCompute = False
        currentVariable.varPut("cwmsCompute", cwmsCompute)
        currentVariable.varPut("fileNameSimulation", fileNameSimulation)
        
        #########################################################
        ## Start of AltConfig file reader section
        ## - EAH
        ##
        ## New Hjson based method to parse alt_config files
        #  Supports Hjson format, which allows for key:value pairs written without required quotes,
        #  commas at the end of lines, root level braces, but also lists.
        
        ## read watershed defaults file
        wsDefaultSetupConfig = network.makeAbsolutePathFromWatershed("scripts/alt_config/_default.txt")
        network.printMessage("Watershed Default Setup File: %s" % wsDefaultSetupConfig)
        self.printLogMessage("Watershed Default Setup File: %s" % wsDefaultSetupConfig)
        wsDefaults = open(wsDefaultSetupConfig, 'r')
        wsConfigList = wsDefaults.readlines()
        wsDefaults.close()
        
        ## read alternative-specific file
        currentVariable.varPut("altConfigAltName", altName)
        altSetupConfig = network.makeAbsolutePathFromWatershed("scripts/alt_config/%s.txt" % (altName))
        network.printMessage("Alt Setup File: %s" % altSetupConfig)
        self.printLogMessage("Alt Setup File: %s" % altSetupConfig)
        altConfigList = []  # defaults to empty list
        if os.path.exists(altSetupConfig):
            altConfig = open(altSetupConfig, 'r')
            altConfigList = altConfig.readlines()
            altConfig.close()
            # check if aliased alternative, if so go read the other file.
            if altConfigList[0][0:6] == "@alias":
                aliasAlt = altConfigList[0].split(" ")[1].strip()
                altSetupConfig = network.makeAbsolutePathFromWatershed("scripts/alt_config/%s.txt" % (aliasAlt))
                network.printMessage("Using aliased alternative file: %s" % altSetupConfig)
                self.printLogMessage("Using aliased alternative file: %s" % altSetupConfig)
                altConfig = open(altSetupConfig, 'r')
                altConfigList = altConfig.readlines()
            altConfig.close()
        else:
            network.printWarningMessage("Unable to open file %s - check alternative name.  Using default only." % altSetupConfig)
            raise AssertionError("You must create an alt config file in scripts/alt_config corresponding exactly to the Alternative name, even if just a blank text file: %s" %altName)
        currentVariable.varPut("altSetupConfig", altSetupConfig) # for use in cleanup script

        disclaimer = " "
        altConfigMsg = disclaimer + "\n" + \
                        "AltConfig Information\n" + \
                        "Watershed default File:       %s\n" % wsDefaultSetupConfig + \
                        "Alternative File:             %s\n" % altSetupConfig
        ## parse the configList and set local vars
        #  Choose either the old method or the new method to process files
        #
        network.printWarningMessage("Processing watershed default config...")
        self.printLogMessage("Processing watershed default config...")
        configDict = parseConfigListJSON(wsConfigList)
        network.printWarningMessage("Processing alternative config...")
        self.printLogMessage("Processing alternative config...")
        configDict.update(parseConfigListJSON(altConfigList))
        configKeys = configDict.keys()
        configKeys.sort() # This way it comes in alphabetical.  Not the best order, but it'll work.
        for k in configKeys:
            dv = configDict[k] #dValue
            currentVariable.varPut(k, dv)
            network.printMessage("\tSet Alternative_Setup variable %s to %s" % (k, dv))
            self.printLogMessage("\tSet Alternative_Setup variable %s to %s" % (k, dv))
            altConfigMsg += "\t%s: %s\n" % (k, dv)
        ##
        ## End of AltConfig file reader section
        #########################################################
        
        #######################################################################################
        ## Check Scripts against resv network to make sure current scripts being used.
        #  
        DEVEL_CHECK_SCRIPTS = currentVariable.varGet("DEVEL_CHECK_SCRIPTS")
        if DEVEL_CHECK_SCRIPTS and DEVEL_CHECK_SCRIPTS.upper() != "OFF":
            network.printWarningMessage("Checking scripts for differences...")
            self.printLogMessage("Checking scripts for differences...")
            failedList = checkScripts(network)
            if len(failedList) > 0:
                msg = "Scripts failed to check:\n"
                for s in failedList:
                    msg += "\t%s\n" % s
                if DEVEL_CHECK_SCRIPTS.upper() == "WARNING":
                    # warning message only
                    network.printWarningMessage(msg)
                elif DEVEL_CHECK_SCRIPTS.upper() == "ERROR":
                    # fail.
                    network.printErrorMessage(msg)
                    return False
            else:
                network.printWarningMessage("Scripts passed.")
                self.printLogMessage("Scripts passed.")
        #######################################################################################
        
        # Assign these after alt_config to ensure they cannot be overwritten by an alt_config file.
        # commented out until new alt names are in place.

        ######################################################
        # Save alt_config dictionary to dssFileNameSimulation
        pathname = "//ALT CONFIG INFORMATION/TEXT///%s/" %dssOutputFpart
        simulationFile = DSS.open(fileNameSimulation)
        writeTextToDss(simulationFile, pathname, altConfigMsg)
        simulationFile.close()
        
        #################################################
        # Finish storing variables into memory                  #
        #################################################
        # return True if the initialization is successful and False if it failed.
        # Returning False will halt the compute.
        self.printLogMessage("Alternative_Setup Init Done")
        
        return True
        
    def cleanup(self, network, currentVariable):
        if len(currentVariable.localTimeSeriesList()) > 0:
            currentVariable.localTimeSeriesWriteAll()

        runTimeWindow = network.getRssRun().getRunTimeWindow()
        endTimeString = runTimeWindow.getEndTimeString()
        endDate = endTimeString.split(" ")[0]
        thisWY = int(endDate[-4:])
        nextWY = thisWY + 1

        ## Create modelReport.json file
        ''' Data file that contains the modelvariables stored from this state variable, computer info,
                pathnames for altconfig files, ResSim/Wat Alt data, and reservoir operations/zones '''
        # Create compdata subdictionary
        ''' Added 6/29/2020 '''
        userID = os.environ["USERNAME"]
        compValues = {
            "UserID": userID,
            "Machine": os.environ["COMPUTERNAME"],
            "Compute Time": time.strftime("%d %b %Y %H:%M")}
        # Create disclaimer
        disclaimer = " "
        altName = currentVariable.varGet("altConfigAltName") # Base ResSim Alt name
        # Pathnames subdictionary
        pathDict = {
            "wsDefaultSetupConfig" :    network.makeAbsolutePathFromWatershed("scripts/alt_config/_default.txt"),
            "altSetupConfig" :          currentVariable.varGet("altSetupConfig")} # if aliased
        # Add in variables stored to the current State Variable
        # Base data can only be stored as [str, int, float] otherwise unreadable by json compiler
        variableList = []
        for entry in currentVariable.varsListKeys(): # keys
            entryvalue = currentVariable.varGet(entry) # values
            # Add if values are stored as a string, list, int, or float 
            if type(entryvalue) in [str, list, int, float]: 
                tempVariableList = [{str(entry):entryvalue}]
                variableList += tempVariableList # add key:value pair to list
            # Add in dictionaries and make sure they are not empty
            elif type(entryvalue) == dict and len(entryvalue) > 0: # exclude empty dictionaries
                # Include only subdictionaries with values stored as string, int, float, list
                # Excludes HecTime objects/PairedValuesDataTables -> just a spot check of first entry
                if type(entryvalue.values()[0]) in [str,list,int,float]: 
                    tempVariableList = [{str(entry):entryvalue}]
                    variableList += tempVariableList # add key:value pair to list
        # Reservoir Data
        # For each Reservoir save name, active operation set, storage zones, active rules for each zone
        resvList = []
        for resv in network.getReservoirNames(): # iterate through the reservoirs
            curResElement = network.findReservoir(resv) # returns a class ReservoirElement object
            curResActiveOpSet = curResElement.getReservoirOp().getActiveOpSet() # Returns a class OpSet object
            #curResAllRules = [] # make a blank vector needed for next line
            #curResAllRules = curResActiveOpSet.getRules(curResAllRules) # vector of all active rules for this resv
            curResStorageZones = curResActiveOpSet.getZoneVector() # returns list of all storage zones for resv in active OpSet
            zoneList = [] # blank list for zones in current reservoir
            for zone in curResStorageZones: # iterate through the storage zones
                curZone = curResActiveOpSet.getZone(str(zone)) # returns a class StorageZone object
                tempRules = [] # blank list needed for next line
                curZoneRules = curZone.getRules(tempRules) # Create list of StorageZoneRules objects
                # Convert list items to string for JSON encoder
                curZoneRules2 = []
                for rule in curZoneRules: curZoneRules2.append(str(rule))
                # Add individual zone data to zones list
                tempZoneList = [{
                    "zone_name": str(curZone), # to string
                    "rules": curZoneRules2}] 
                zoneList += tempZoneList
            # Add zones data to current reservoir data
            tempResvList = [{
                "reservoir": str(curResElement), # to string
                "operation_set": str(curResActiveOpSet), # to string
                "zones": zoneList}]
            # Add current reservoir data to reservoir list
            resvList += tempResvList
        # Add all subdictionaries/lists to dictionary to be encoded to JSON file
        modelReportValues = {
            "compInfo": compValues,
            "disclaimer": disclaimer,
            "pathnames": pathDict,
            "modelVariables": variableList,
            "operations": resvList}
        # Create location to save modelReport.json file
        fileNameSimulation = currentVariable.varGet("fileNameSimulation")
        reportLocation = os.path.dirname(fileNameSimulation)
                                                                                                            
        reportName = os.path.join(reportLocation, "modelReport_%s.json" % (altName))

        # Write output to JSON file
        try:
            reportFile = open(reportName, 'wb')
            modelReportValues = json.dumps(modelReportValues, sort_keys = True, indent = 4, separators=(',',':'))
            reportFile.write(modelReportValues)
            reportFile.close()
        except:
            network.printErrorMessage("Unable to write modelReport file: %s" %reportName)

def fileToString(fName):
    if os.path.exists(fName):
        f = open(fName,'r')
        string = f.read()
        f.close()
        return string
    else:
        return ""
            
def parseConfigListJSON(configList):
    if len(configList) == 0:
        return dict()
    configList = "\n".join(configList)
    # add curley braces if required
    if configList[0] != "{" and configList[-1] != "}":
        configList = "{\n%s\n}" % configList
    # parse with Hjson and then with jyson to get python structure.
    jsonText = JsonValue.readHjson(configList).toString()
    return json.loads(jsonText)
    
def checkScripts(network):
    failedList = []
    networkName = network.getName().split(":")[-1]
    ##############################################################################
    # Process State Variables
    loadPath = network.makeAbsolutePathFromWatershed("scripts")
    loadPath += "/" + networkName+ "/StateVars"
    for sv in network.getStateVariableList():
        # note - "in ResSim Only" checks turned off because of blank scripts reporting false positives. 
        if sv.isSlave(): continue
        initFileName = loadPath+"/"+sv.toString()+"_Init.py"
        mainFileName = loadPath+"/"+sv.toString()+"_Main.py"
        cleanupFileName = loadPath+"/"+sv.toString()+"_Cleanup.py"
        if os.path.exists(initFileName):
            initScriptText = fileToString(initFileName)
            if str(sv.getInitScript()) != initScriptText:
                failedList.append(sv.toString() + " init different")
        else:
            pass
            #failedList.append(sv.toString() + " init in ResSim only")
        if os.path.exists(mainFileName):
            mainScriptText = fileToString(mainFileName)
            if str(sv.getScript()) != mainScriptText:
                failedList.append(sv.toString() + " main different")
        else:
            pass
            #failedList.append(sv.toString() + " main in ResSim only")
        if os.path.exists(cleanupFileName):
            cleanupScriptText = fileToString(cleanupFileName)
            if str(sv.getCleanupScript()) != cleanupScriptText:
                failedList.append(sv.toString() + " cleanup different")
        else:
            pass
            #failedList.append(sv.toString() + " cleanup in ResSim only")
    ##############################################################################
    # Process Scripted Rules
    loadPath = network.makeAbsolutePathFromWatershed("scripts")
    loadPath += "/" + networkName + "/ScriptedRules"
    for resvName in network.getReservoirNames():
        resv = network.findReservoir(resvName)
        rules = resv.getReservoirOp().getRules()
        for rule in rules:
            if isinstance(rule, ScriptOpRule):
                scriptFileName = loadPath+"/"+resvName+"/"+rule.toString()+".py"
                if os.path.exists(scriptFileName):
                    ruleScriptText = fileToString(scriptFileName)
                    if str(rule.getScriptText()) != ruleScriptText:
                        failedList.append(resvName + " rule: " + rule.toString() + " different")
                else:
                    failedList.append(resvName + " rule " + rule.toString() + " in ResSim only")
    return failedList
