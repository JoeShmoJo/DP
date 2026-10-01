'''
Establishes the external state variable names and compute order;
  calls the initialization, main, and cleanup scripts for
  each external SV.
  
The placement of this state variable in the ResSim compute order is critical.
To see the initialization order that ResSim uses, open up any script editor window and
expand the "State Variable" menu item in the API in the pane on the left.
The order shown in that list is the initialization order.
ResSim initializes state variables not alphabetically, but by date created by default.
ControllerExternalSV should be located near the bottom of the stack.
It MUST be below all of the External state variables that it will create.
Otherwise, ControllerExternalSV will initialize the state variable object, but then
    the ResSim program will come in behind it and re-initialize the SV, wiping everything away.

When done this way, you will have full control over the initialization order of the scripts
as specified in the ControllerExternalSV config file
'''

from hec.script import Constants
from hec.heclib.util import HecTime
import fnmatch
import re
import calendar
import os
import time

# Custom imports
from NWDJyLib import cFile
from NWDJyLib import cLoadModules
from externalSVs.baseExternalSV import ExternalSV

class ControllerExternalSV(ExternalSV):

    def initialization(self, currentVariable, network):
        
        self.svName = currentVariable.getName()
        self.lastDateComputed = HecTime()
        self.debugTimeStrTemplate = "%-30s%-35s%-21s%-21s"
        self.debugTimeDataTemplate = "%-30s%-35s%-21.4f%-21.4f"
        self.alwaysComputeStrTemplate =  "%-8s%-35s%10s"
        self.alwaysComputeTimeTemplate = "%-8s%-35s%10.4f" #e.g "MAIN    URC_Master               20.1243"
        
        self.debug = False
        #----------------------------#
        # Establishing Compute Order #
        #----------------------------#
        # State variables script order is defined in the 'svComputeOrderConfigFile' location
        # However, there are some scripts that we don't care about the compute order, so they
        #   should just be computed any time after the state variables with defined compute
        #   orders.  This init script section performs the following tasks:
        #   1) Read in the SV compute config, and establish as initial compute order
        #   2) Next, look at all the scripts defined in the 'svScriptDir' and if not defined in
        #      the compute order, add to a temporary list to be appended to the final
        #   3) Add the final compute order to this state variable as 'svComputeOrder'
        #      for reference in the main script so SV can be called in order.

        svComputeOrderConfigFile = "scripts/externalSVs/_externalSV_Compute_Options.csv"
        svScriptDir = "scripts/externalSVs"
        self.svComputeOrderConfigFile = svComputeOrderConfigFile
        self.svScriptDir = svScriptDir
        self.svScriptDirFullPath = network.makeAbsolutePathFromWatershed(svScriptDir)
        
        #Make a nested dictionary to hold compute times 
        #1st level key = ["INIT","MAIN","CLEANUP"], 2nd level key = SV name
        self.ComputeTimes = {"INIT":{},"MAIN":{},"CLEANUP":{}}

        # 1)
        # Reading in text file defining the external state variable's compute order
        #   - this may not be comprehensive
        svFileName = network.makeAbsolutePathFromWatershed(svComputeOrderConfigFile)
        svComputeOrder = list() # final compute order list
        svDefinedOrderNames = list()
        lines = cFile.fileOpenReadClose(svFileName)
        lines = cFile.stripOutCommentLines(lines)
        for l in lines:
            tupleVals = tuple(l.split(","))
            computeIterOption, computePassOption, svName = tupleVals
            # Check that SV configured properly
            if self.isValidSV(svName, network):
                svDefinedOrderNames.append(svName)
                svComputeOrder.append(tupleVals)
            
        # 2)
        # Retrieve name of each script in the externalSVs module with implementations
        unorderedSV = list() # Holder for SV not defined in config
        svScriptRegEx = "*[!__init__]*.py" # regex defining 'non-init python file'
        allFiles = os.listdir(network.makeAbsolutePathFromWatershed(svScriptDir))
        for fName in allFiles:
            # First, check that the file isn't compiled bytecode or the init file
            isSVScript = fnmatch.fnmatch(fName,svScriptRegEx)
            if not isSVScript:
                continue
            svName = fName.replace(".py","")       
            # Check that SV configured properly            
            if self.isValidSV(svName, network) and not svName in svDefinedOrderNames:
                unorderedSV.append(("first",1,svName))

        # Append state variables that do not have a specific order to the end
        svComputeOrder = svComputeOrder+unorderedSV

        self.printMessage("\nExternal state variables to be force-computed by ControllerExternalSV:\n\n")
        self.printMessage( \
            "%-50s%-30s%-30s" % \
            ("Iter Option", "PassOption", "SV Name"))

        # Creating a regular expression of month abbreviations to match against
        ma = [calendar.month_abbr[e].upper() for e in range(1,13)]
        maRegexPattern = "|".join(ma)
            
        for i in range(len(svComputeOrder)):
            computeIterOption, computePassOption, svName = svComputeOrder[i]

            # Assigning default values
            if computeIterOption == "":
              computeIterOption = "first"
            if computePassOption == "":
              computePassOption = [0,1,2]
            # computePassOption: Expecting integer(s) less than 9 as list or atomic
            elif isinstance(computePassOption, list):
              computePassOption = [int(e) for e in computePassOption]
            else:
              computePassOption = [int(computePassOption)]

            
            self.printMessage( \
                "%-50s%-30s%-30s" % \
                (str(computeIterOption), \
                str(computePassOption), str(svName)))
                
            svComputeOrder[i] = (computeIterOption, \
                computePassOption, str(svName))

        # 3) 
        # Store compute order
        self.svComputeOrder = svComputeOrder
        
        # 4)
        # Initialize all external state variables
        self.initializedSVs = {}
        for i in range(len(svComputeOrder)):
            computeIterOption, computePassOption, svName = svComputeOrder[i]
            sTime = time.time()
            sv = self.createExternalSV(svName, network)
            #Need to keep a copy around so we can restore it if ResSim proper initialization wipes it away
            self.initializedSVs[svName] = sv.clone()
            # Track compute time
            eTime = time.time()
            totTimeSeconds = eTime - sTime
            self.ComputeTimes["INIT"][svName] = totTimeSeconds
        
        # Create list to keep track of the time each SV takes to compute in main
        self.svTimeTrackingList = [self.alwaysComputeStrTemplate % ("Phase","SV Name","Seconds")]
        self.svDebugTimeTrackingList = [self.debugTimeStrTemplate % ("DateTime","SV Name","Total Seconds", "TimeStep Seconds")]
        #Save initialized state of this state variable so it can be reinitialized
        self.initializedSVs[self.svName] = currentVariable.clone()
        return Constants.TRUE
    
    def main(self, currentVariable, network, currentRuntimestep):
        '''
        Iterate through each of the external state variables, and call main scripts
        '''
        svDebugTimeTrackingList = self.svDebugTimeTrackingList
        
        hTime = currentRuntimestep.getHecTime()
        hTime = self.convertToHecTime(hTime)
        timeStr = str(hTime)
        #Only run this once per day
        if self.lastDateComputed.equalTo(hTime):
            return None
        self.lastDateComputed = hTime.clone()
        for tupleVals in self.svComputeOrder:
            # Retrieve compute options and SV name
            computeIterOption, computePassOption, svName = tupleVals
            # Pull SV from network, equivalent to currentVariable object if in 
            #    that SV main script
            svObj = network.getStateVariable(str(svName))
            
            if svObj.varGet("skip"):
                continue
                
            if not svObj.varExists("thisSV"):
                errMsg = "State Variable: %s was not initialized properly." %svName
                errMsg +="\nUsually this is because ResSim initialized it after ControllerExternalSV, resetting all variables."
                raise AssertionError(errMsg)
                #self.printErrorMessage("No external SV object found for %s, skipping." % \
                #    svName)
                #svObj.varPut("skip", True)
                #return Constants.FALSE
            thisSV = svObj.varGet("thisSV")
            
            # Compute main if needed
            if thisSV.needToCompute(network, svObj, currentRuntimestep,\
                computeIterOption, computePassOption):
                sTime = time.time()
                thisSV.main(network, svObj, currentRuntimestep)
                # Track compute time
                eTime = time.time()
                totTimeSeconds = eTime - sTime
                
                if svName in self.ComputeTimes["MAIN"]:
                    self.ComputeTimes["MAIN"][svName] += totTimeSeconds
                else:
                    self.ComputeTimes["MAIN"][svName] = totTimeSeconds
                    
                if self.debug:
                    svDebugTimeTrackingList.append(\
                        self.debugTimeDataTemplate % (timeStr, svName,self.ComputeTimes["MAIN"][svName], totTimeSeconds))
        
        self.svDebugTimeTrackingList = svDebugTimeTrackingList
            
        return Constants.TRUE
            

    '''
    Iterate through each of the external state variables, and call cleanup scripts
    '''
          
    def cleanup(self, currentVariable, network):
        
        #Didn't have access to alternative setup in the init, so get a few things now
        #so that we can write text out to DSS
        altSetupSV = network.getStateVariable("Alternative_Setup")
        self.fileNameSimulation = altSetupSV.varGet("fileNameSimulation")
        self.fPart = altSetupSV.varGet("dssOutputFpart")
        
        for tupleVals in self.svComputeOrder:
            # Retrieve compute options and SV name
            computeIterOption, computePassOption, svName = tupleVals
            
            # Pull SV from network and currentVariable object
            svObj = network.getStateVariable(svName)
            thisSV = svObj.varGet("thisSV")

            # Compute cleanup if needed
            if not svObj.varGet("skip"):
                sTime = time.time()
                thisSV.cleanup(network, svObj)
                eTime = time.time()
                totTimeSeconds = eTime - sTime
                self.ComputeTimes["CLEANUP"][svName] = totTimeSeconds
        
        # Save compute times to text DSS
        svTimeTrackingList = self.svTimeTrackingList
        saveText = " "
        for svPhase in ["INIT","MAIN","CLEANUP"]:
            for tupleVals in self.svComputeOrder:
                # Retrieve compute options and SV name
                computeIterOption, computePassOption, svName = tupleVals
                if svName in self.ComputeTimes[svPhase]:
                    svTimeTrackingList.append(\
                        self.alwaysComputeTimeTemplate % (svPhase,svName,self.ComputeTimes[svPhase][svName]))
        #   F part is optional and will use 
        #   default F part from AltSetup
        saveText = "\n".join(svTimeTrackingList)
        self.saveTextToSimDss("//EXTERNAL SV COMPUTE TIMES/TEXT/1900/1900//", (saveText))

        if self.debug:
            # Get SV compute times, create one string
            svDebugTimeTrackingList = self.svDebugTimeTrackingList
            saveTextFull = "\n".join((svDebugTimeTrackingList))
            # Save to text DSS, F part is optional and will use 
            #   default F part from AltSetup
            self.saveTextToSimDss("//DEBUG EXTERNAL SV COMPUTE TIMES/TEXT/1900/1900//", (saveTextFull))
            
        return Constants.TRUE

    def isValidSV(self, svName, network):
        '''Given a string of the SV's name, checks:
            1) there is a SV by that name in ResSim network and 
            2) there is a script with that name in the external SV script dir
            '''
        if svName == "baseExternalSV" or svName == "ControllerExternalSV": #Don't try to process the base class
            return False
        svInResSim = network.getStateVariable(svName) is not None
        svHasScript = svName+".py" in os.listdir(self.svScriptDirFullPath)
        if svInResSim and svHasScript:
            return True
        elif not svInResSim and svHasScript:
            self.printWarningMessage("Invalid external SV setup.  %s is not defined in ResSim." %(svName))
            return False
        elif svInResSim and not svHasScript:
            self.printWarningMessage("Invalid external SV setup.  %s does not have script in external SV folder:\n\t%s\\%s.py" % \
                (svName, self.svScriptDirFullPath, svName))
            return False
        elif not svInResSim and not svHasScript:
            self.printWarningMessage("Invalid external SV setup.  %s is not defined in ResSim nor has script in external SV folder:\n\t%s\\%s.py." % \
                (svName, self.svScriptDirFullPath, svName))
            return False
    
    def createExternalSV(self, svName, network):
        '''
        Creates a new External State Variable object and saves to the StateVariable object in the network
        This step needs to be done during or after ResSim initializes the state variable,
        otherwise this will get wiped away when ResSim initializes the SV. 
        svName (string): exact match to state variable name in ResSim (e.g. "Alternative_Setup")
        creates an object (thisSV) that is one of the following classes: baseExternalSV, baseInputSV, baseProjectedSV
        '''
        stateVar = network.getStateVariable(svName)
        if stateVar is None:
            raise AssertionError("Tried to initialize external state variable: %s, but it does not exist in ResSim" %svName)
        #Make sure it hasn't already been initialized with a script that populated variables
        #ControllerExternalSV should be fully in charge of the initialization
        #In standalone Ressim, 
        # if you have already run the simulation once and are trying to run it again,
        # it still has all the local variables and local time series from the previous compute
        # Want to force an initialization
        if stateVar.varsSize() > 0:
            stateVar.varsClear()
            #raise AssertionError("State Variable: %s has already been initialized. Please strip away all code in the init script in the ResSim editor!" %svName)
        if len(stateVar.localTimeSeriesList()) > 0:
            stateVar.localTimeSeriesClear()
        stateVar.varPut("debug", False)
        stateVar.varPut("skip", False)
        svName = stateVar.getName()
        #Toggles for debugging and skipping are stored in Alt Setup, which should be the very first one to initialize
        if svName != "Alternative_Setup":
            altSetupSV = network.getStateVariable("Alternative_Setup")
            if not altSetupSV.varExists("DEVEL_CHECK_SCRIPTS"):
                raise AssertionError("Alternative_Setup has not been initialized, it needs to be the very first in the compute order. Currently initializing: %s" %svName)
        thisSV = cLoadModules.getNewExternalSVObj(network, svName, stateVar)
        thisSV.initialization(network, stateVar)
        stateVar.varPut("thisSV", thisSV)
        return stateVar
        
    def reinitializeExternalSV(self, svName, network):
        '''
        All External SVs are initialized during the initialization of ControllerExternalSV
        However, the ResSim compute order may do the true init of each SV after this has occurred.
        If that happens, all the initialization work done here will be wiped away.
        Typical ResSim compute order:
            1. Scripted Rules initialize
                There is a scripted rule initialization that calls the ControllerExternalSV initialization
                This is done so that other scripted rule initializations can access Alternative_Setup
            2. State Variables initialize
                When ResSim initializes Alternative_Setup, it wipes everything away (all variables and timeseries)
                This .reinitializeExternalSV function is then used at this point to "restore" the state variable
                This allows all other scripts to continue accessing Alternative_Setup seamlessly
        '''
        if svName not in self.initializedSVs:
            raise AssertionError("Trying to reinitialize: %s\nBut the only SVs that have initialized are: %s" %(svName, self.initializedSVs))
        svBackup = self.initializedSVs[svName]
        sv = network.getStateVariable(svName)
        if sv.varsSize() > 0:
            #State variable has already been initialized, don't touch it
            return None
        #Restore all local variables
        varNames = svBackup.varsListKeys()
        for varName in varNames:
            sv.varPut(varName, svBackup.varGet(varName))
        #Restore all local time series
        try:
            localList = currentVariable.localTimeSeriesListKeys()
        except:
            localList = []
        for localTSName in localList:
            sv.localTimeSeriesNew(localTSName, svBackup.localTimeSeriesGet(localTSName))

