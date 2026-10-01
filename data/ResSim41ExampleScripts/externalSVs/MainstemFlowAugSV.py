'''
Code to figure out minimum releases to meet minimum flow targets at Salem/Albany.
This module is typically called by scripted rules at the contributing projects.
This method is not quite as precise as native downstream control rules in ResSim.
But it is a lot faster and easier to understand.
Solely a function of unregulated flows. 
The necessary flow augmentation is derived by proportioning the shortfall based on conservation storage. 
This code should work for timesteps from 1HOUR to 1DAY

This is implemented as an external state variable that computes the operation
for all reservoirs for the entire compute window at once.
Other scripts can access variables/timeseries/methods as needed by calling:
    mainstemFlowAugSV = network.getStateVariable("MainstemFlowAugSV").varGet("thisSV")
'''

#The name of the time series in the TimeSeries tab of the alternative editor with the water year type mapped in
WY_TYPE_TS_NAME = "Water Year Type"

#The "official" short names for the locations to do flow augmentation.
SALEM_NAME = "Salem"
ALBANY_NAME = "Albany"
MAINSTEM_LOCATIONS = [SALEM_NAME, ALBANY_NAME]
#The ResSim name for the Salem and Albany junctions
RESSIM_JUNCTION_NAMES = {"Salem":"Willamette_at Salem",
                         "Albany":"Willamette_at Albany"}

DAYS_AVERAGE = 3 #Number of days to use when averaging inflows/releases to keep things smooth

DEBUG = False #If True, debug statements will be printed out

from hec.rss.model import RssModelVariableConstants
from hec.heclib.util import HecTime
from hec.model import PairedValuesExt
from hec.model import RunTimeStep
from hec.rss.model import OpValue
from hec.rss.model import OpRule
from hec.script import Constants

from externalSVs.baseExternalSV import ExternalSV


from NWDJyLib.DSS import cDSS
from NWDJyLib.cFile import fileOpenReadClose, stripOutCommentLines, getCSVDictReader, convertCSVDictReaderToListDict, getListOfDictsFromCSV
from NWDJyLib.cTimes import getHecTimeFromRuntimestep
from NWDJyLib.ResSim.cResSim import getElevationStorageTable

CFSDAY_TO_AF = (60*60*24)/43560.0 #Multiply a daily CFS by this constant to get acre-feet. It's about 2

class MainstemFlowAugSV(ExternalSV):
    '''
    State variable that does the compute and holds all needed variables and timeseries
    '''
    def initialization(self, network, currentVariable):
        '''
        Called during the initialization script of the state variable.
        One-time setup things. 
        '''
        altSetupSV = network.getStateVariable("Alternative_Setup")
        self.mainstemFlowAugMethod = altSetupSV.varGet("mainstemFlowAugMethod")
        if self.mainstemFlowAugMethod == "NoFlowAug": #Don't compute mainstem flow aug, skip everything else
            self.computeSV = False
            return True
        self.computeSV = True
        self.hasComputed = False
        self.useExternalTS = False
        #Config file that shows which reservoirs are used to support the min flow target, their storage capacity, etc.
        resvConfigCSV = altSetupSV.varGet("mainstemFlowAugReservoirConfigCSV") #e.g. "scripts/someCSV.csv"
        self.resvConfig = loadReservoirConfig(network.makeAbsolutePathFromWatershed(resvConfigCSV))
        self.resvNamesAll = list(self.resvConfig.values()[0].keys()) #all reservoirs in config file
        #list of reservoirs in config file that directly operate for mainsteam flow targets
        self.resvNamesSupporting = list(self.resvNamesAll) 
        #list of reservoirs in config file that do not directly operate for mainstem flow targets
        self.resvNamesNonSupporting = list(self.resvNamesAll) 
        for resvName in self.resvNamesAll:
            supports = self.resvConfig["SupportsSalem"][resvName]
            if supports.upper() == "FALSE": 
                self.resvNamesSupporting.remove(resvName)
            else:
                self.resvNamesNonSupporting.remove(resvName)
        
        # #If applicable, read in the external time series of min flow target that serves as an override:
        # if self.mainstemFlowAugMethod in ["AutoDetect", "ReadExternalFlowAugTS"]:
        #     fPartInput = altSetupSV.varGet("dssOutputFpart")
        #     if not fPartInput.endswith("0"): #If we are running a trial, read in the external TS from the original alternative
        #         fPartInput = fPartInput[:-1] + "0" #e.g. "Default---0" instead of "Default---1"
        #     ePart = currentVariable.getTimeSeries().getTimeSeriesContainer().fullName.split("/")[5] #e.g. "3HOUR"
        #     templatePath = altSetupSV.varGet("flowAugRuleTSPathTemplate") # "//%RESV_NAME%-FLOWAUG/FLOW-MIN//%TIMESTEP%/%FPART%/"
        #     #Fill in timestep and f-part of the external TS to read
        #     templatePath = templatePath.replace("%TIMESTEP%",ePart).replace("%FPART%",fPartInput)
        #     dssFile = cDSS.openDSSFile(altSetupSV.varGet("fileNameSimulation")) # hec.heclib.dss.HecDss class
        #     for resvName in self.resvNamesSupporting:
        #         #Fill in the pathname for a given reservoir
        #         pathname = templatePath.replace("%RESV_NAME%", resvName)
        #         #Try to read the pathname. Should return an empty eturns None if pathname doesn't exist.
        #         #.get requires all uppercase path and 1 forces the whole timewindow
        #         tsc = dssFile.get(pathname.upper(), 1) #hec.io.TimeSeriesContainer class
        #         if tsc is None or tsc.times is None:
        #             if self.mainstemFlowAugMethod == "AutoDetect":
        #                 #This is OK, probably the first of the two-step process.
        #                 #Don't do flow-aug
        #                 network.printMessage("Auto-detect for mainstem flow-aug couldn't locate external TS, not doing flow-aug")
        #                 dssFile.close()
        #                 self.computeSV = False
        #                 return True
        #             else:
        #                 #Not OK, there really should be valid data
        #                 dssFile.close()
        #                 raise AssertionError("Mainstem flow aug expecting an external time series in simulation.dss, but not present:\n%s" %pathname)
        #         currentVariable.localTimeSeriesNew(resvName+"-FLOW-AUG-EXTERNAL", tsc)
        #         self.useExternalTS = True
        #     dssFile.close()
        if self.mainstemFlowAugMethod in ["AutoDetect", "ReadExternalFlowAugTS"]:
            fPartInput = altSetupSV.varGet("dssOutputFpart")

            # Optional: omit flow-aug for specific trial numbers (e.g. "3,4,5")
            omitRaw = altSetupSV.varGet("omitTrialsFromFlowAug")
            omitTrials = set()
            if omitRaw:
                for tok in str(omitRaw).replace(",", " ").split():
                    if tok.isdigit():
                        omitTrials.add(int(tok))

            trialDigit = None
            if fPartInput and len(fPartInput) > 0 and fPartInput[-1].isdigit():
                trialDigit = int(fPartInput[-1])

            # If this is a trial alt and its digit is in omit list, skip flow-aug entirely
            if trialDigit is not None and trialDigit in omitTrials:
                network.printMessage(
                    "MainstemFlowAugSV: omitting flow-aug for trial %s (F-part=%s)" % (trialDigit, fPartInput)
                )
                self.computeSV = False
                return True

            if not fPartInput.endswith("0"): #If we are running a trial, read in the external TS from the original alternative
                fPartInput = fPartInput[:-1] + "0" #e.g. "Default---0" instead of "Default---1"
            ePart = currentVariable.getTimeSeries().getTimeSeriesContainer().fullName.split("/")[5] #e.g. "3HOUR"
            templatePath = altSetupSV.varGet("flowAugRuleTSPathTemplate") # "//%RESV_NAME%-FLOWAUG/FLOW-MIN//%TIMESTEP%/%FPART%/"
            #Fill in timestep and f-part of the external TS to read
            templatePath = templatePath.replace("%TIMESTEP%",ePart).replace("%FPART%",fPartInput)
            dssFile = cDSS.openDSSFile(altSetupSV.varGet("fileNameSimulation")) # hec.heclib.dss.HecDss class
            for resvName in self.resvNamesSupporting:
                #Fill in the pathname for a given reservoir
                pathname = templatePath.replace("%RESV_NAME%", resvName)
                #Try to read the pathname. Should return an empty returns None if pathname doesn't exist.
                #.get requires all uppercase path and 1 forces the whole timewindow
                tsc = dssFile.get(pathname.upper(), 1) #hec.io.TimeSeriesContainer class
                if tsc is None or tsc.times is None:
                    if self.mainstemFlowAugMethod == "AutoDetect":
                        #This is OK, probably the first of the two-step process.
                        #Don't do flow-aug
                        network.printMessage("Auto-detect for mainstem flow-aug couldn't locate external TS, not doing flow-aug")
                        dssFile.close()
                        self.computeSV = False
                        return True
                    else:
                        #Not OK, there really should be valid data
                        dssFile.close()
                        raise AssertionError("Mainstem flow aug expecting an external time series in simulation.dss, but not present:\n%s" %pathname)
                currentVariable.localTimeSeriesNew(resvName+"-FLOW-AUG-EXTERNAL", tsc)
                self.useExternalTS = True
            dssFile.close()
        
        
        #CSV files with min flow target at Salem and Albany as a function of water year type
        minFlowTargetCSV_Salem = altSetupSV.varGet("minFlowTargetCSV_Salem") #relative path to CSV file from watershed folder
        minFlowTargetCSV_Albany = altSetupSV.varGet("minFlowTargetCSV_Albany")
        self.minFlowTableDict = {}
        self.minFlowTableDict["Salem"] = loadMinFlowTable(network.makeAbsolutePathFromWatershed(minFlowTargetCSV_Salem))
        self.minFlowTableDict["Albany"] = loadMinFlowTable(network.makeAbsolutePathFromWatershed(minFlowTargetCSV_Albany))
        
        #Load up the water year type time series(Abundant, Adequate, Insufficient, Deficit)
        self.wyTypeTS = getWYTypeTS(network)
        
        #Load up conservation storage (kaf) for each reservoir, regardless of whether supporting the operation
        self.conStorDictAll = getResvConStorage(self.resvConfig, network)
        #Trim the dictionary down to just those reservoirs that are supporting the operation. 
        self.conStorDict = dict(self.conStorDictAll)
        #If only Lookout Point is listed as augmenting flows and not Hills Creek separately,
        #The idea is to treat Lookout Point/Hills Creek as a unit (single reservoir)
        if "Lookout Point" in self.resvNamesSupporting and not "Hills Creek" in self.resvNamesSupporting:
            self.conStorDict["Lookout Point"] = self.conStorDict["Lookout Point"] + self.conStorDict["Hills Creek"]
        for resvName in self.resvNamesNonSupporting:
            #Remove the non-supporting reservoirs
            self.conStorDict.pop(resvName)
        
        self.conStorTotal = sum(self.conStorDict.values())
        #Initialize the dictionary of percent allocations for what
        #portion of total flow aug volume (deficit) each project should take.
        self.pctAllocationDict = {} #Keys=reservoir names, values=pct (between 0 and 1)
        for resvName, conStor in self.conStorDict.items():
            self.pctAllocationDict[resvName] = conStor/self.conStorTotal
        
        #Load up unregulated flows
        self.unregFlowTSDict = {} #keys = names (e.g. "Salem", "Cougar"), values = TSRecord
        for locName in MAINSTEM_LOCATIONS+self.resvNamesAll:
            if locName in RESSIM_JUNCTION_NAMES:
                junctionName = RESSIM_JUNCTION_NAMES[locName]
            else:
                #Probably a reservoir, just append "_IN" to the end of the reservoir name
                junctionName = locName + "_IN"
            self.unregFlowTSDict[locName] = network.getRssRun().getTSRecordByPathParts(junctionName,"FLOW-UNREG")
        
        #Initialize local time series that may eventually get written to DSS
        #Helpful for debugging/diagnostic purposes after a simulation has completed
        tsNames = []
        for locName in MAINSTEM_LOCATIONS:
            tsNames.append("MinFlowTarget-%s" %locName)
            tsNames.append("Deficit-%s" %locName)
            tsNames.append("IncidentalFlowAugFromOthers-%s" %locName)
        for resvName in self.resvNamesAll:
            tsNames.append("PctAllocation-%s" %resvName)
            tsNames.append("BufferStor-%s" %resvName)
            for locName in MAINSTEM_LOCATIONS:
                tsNames.append("MinReleaseFor_%s-%s" %(locName, resvName))
        self.initializeLocalTSCs(currentVariable, tsNames)
        
        return True
        
    def main(self, network, currentVariable, currentRuntimestep):
        '''
        Called during the Main script of the state variable
        This .main function is called natively by ResSim when executing state variables
        Can actually be triggered multiple times on the same compute time step.
        Just make it a pass-through to call the real compute function
        '''
        return compute(network, currentVariable, currentRuntimestep)
        
    def compute(self, network):
        '''
        This is the main compute function.
        It is called at least once per compute time step
        It can be triggered either by the .main() function of this state variable,
        or by any of the scripted rules that are doing flow-aug.
        We don't have control over which computes first, so any of them can trigger it.
        Calculates the min flow requirements at all projects
        to support minimum flow targets.
        
        It does this at the very beginning of the compute, and does the whole
        time window at once. It needs to do this because there are different 
        compute blocks for reservoirs in each subbasin. For example, 
        Cottage Grove and Dorena may compute their entire simulation before
        ResSim moves to Blue River/Cougar (or vice versa). 
        So this script cannot look at basin-wide modeled reservoir operations 
        (e.g. previous day's storage at all reservoirs), since there will be missing values
        Script is formulated to come up with decent estimates of flow-aug for the whole
        compute time window based on unregulated flows, which are known everywere at the start.
        Then, when each scripted rule fires at each reservoir, we have full knowledge of the 
        reservoir conditions on the previous timestep and can take that into account. 
        '''
        
        #Check up front to see if this has already been calculated before, and skip if so. 
        if self.hasComputed: return None
        self.hasComputed = True
        #Loop through each timestep and do the computations
        rtw = network.getRssRun().getCurrentComputeBlockRunTimeWindow()
        rts = RunTimeStep(rtw)
        numStepsComputeBlock = rtw.getNumSteps()
        for k in range(numStepsComputeBlock+1):
            rts.setStep(k)
            if DEBUG: print(rts.getHecTime())
            curDate = getHecTimeFromRuntimestep(rts) #Gets date at 2400 hours of the current day
            if DEBUG: print("2400 date:", curDate)
            date3Days = curDate.clone()
            date3Days.addDays(3)
            #Get the water year type
            wyType = self.wyTypeTS.getCurrentValue(rts)
            #Set the pct allocation and the buffer zone for each reservoir
            for resvName, pctAllocation in self.pctAllocationDict.items():
                self.setLocalTSValue("PctAllocation-%s" %resvName, rts, pctAllocation)
                bufferElevMax = self.resvConfig["SummerBufferElev"][resvName] #This used to be called the "buffer" zone in ResSim
                minConElev = self.resvConfig["MinConElev"][resvName]
                poolElem = network.findReservoir(resvName).getStorageFunction()
                bufferStor = getBufferZoneStor(poolElem, curDate, bufferElevMax, minConElev) #aka "buffer" zone
                self.setLocalTSValue("BufferStor-%s" %resvName, rts, bufferStor)
            for locName in MAINSTEM_LOCATIONS:
                #Get the min flow target and set timeseries value
                minFlowTable = self.minFlowTableDict[locName]
                minFlowTarget = interpTbl(minFlowTable, wyType, curDate)
                if DEBUG: print("target", minFlowTarget)
                network.getStateVariable("Min_Flow_Target_%s" %locName).setValue(rts, minFlowTarget)
                self.setLocalTSValue("MinFlowTarget-%s" %locName, rts, minFlowTarget)
                #Use the max over the next 3 days to be a little conservative when figuring releases
                minFlowTarget = max(minFlowTarget, interpTbl(minFlowTable, wyType, date3Days))
                #If min flow is 0, set min release to 0 to save time and move to next timestep. 
                if minFlowTarget == 0:
                    for resvName in self.resvNamesSupporting:
                        self.setLocalTSValue("MinReleaseFor_%s-%s" %(locName, resvName), rts, 0)
                    continue
                #Get the unreg flow at the downstream location 
                #Use an average of a few days to smooth things out
                unregTS_DS = self.unregFlowTSDict[locName]
                timeStepMinutes = unregTS_DS.getTimeStepMinutes()
                numStepsToAvg = int(round(DAYS_AVERAGE*1440./timeStepMinutes,0))
                unregFlow = unregTS_DS.getPeriodAverage(int(min(numStepsComputeBlock, k+numStepsToAvg)), numStepsToAvg)
                if DEBUG: print("Unreg", unregFlow)
                #Calculate deficit (the amount of flow augmentation needed)
                deficit = minFlowTarget - unregFlow
                self.setLocalTSValue("Deficit-%s" %locName, rts, deficit)
                if DEBUG: print("Deficit", deficit)
                #Deduct assumed contribution from non-contributors, like Detroit
                #These projects don't operate directly for the downstream location, but still help
                helpFromOthers = 0 #cfs, the assumed flow aug from these reservoirs (above unreg inflow)
                for resvName in self.resvNamesNonSupporting:
                    #Skip Fern Ridge, it's not worth accounting for
                    if resvName == "Fern Ridge": continue
                    #Skip Santiam projects if doing Albany, since they are downstream
                    if "ALBANY" in locName.upper():
                        if resvName in ["Detroit", "Foster", "Green Peter"]:
                            continue
                    unregFlowResv = self.unregFlowTSDict[resvName].getPeriodAverage(int(min(numStepsComputeBlock, k+numStepsToAvg)), numStepsToAvg)
                    minFlowTypical = 0.
                    if resvName == "Detroit":
                        #Min flow varies by date, per BiOp
                        minFlowTypical = 1050. #1050 assumed min flow to avoid cavitation at BCL
                    elif resvName == "Foster":
                        #Don't do Green Peter and Foster separately
                        #Just look at unreg flow at Foster vs typical min flow target at Foster
                        #Min flow varies by date, per BiOp
                        minFlowTypical = 1000. #1000 somewhere in the middle of Foster min flows
                    helpFromOthers += max(0, minFlowTypical - unregFlowResv)
                self.setLocalTSValue("IncidentalFlowAugFromOthers-%s" %locName, rts, helpFromOthers)
                if DEBUG: print("help", helpFromOthers)
                deficit = deficit - helpFromOthers
                #Split the deficit by percent allocation (conservation storage)
                deficitByProject = {}
                for resvName in self.resvNamesSupporting:
                    deficitByProject[resvName] = deficit*self.pctAllocationDict[resvName]
                #Set minimum flow at each individual project, based on inflow
                #Have to be careful about order, need to do Hills Creek before Lookout Point
                #It's first alphabetically, so we'll sort it that way
                if DEBUG: print(deficitByProject)
                resvNamesABC = sorted(self.resvNamesSupporting)
                minFlowByProject = {}
                for resvName in resvNamesABC:
                    unregTS = self.unregFlowTSDict[resvName]
                    inflow = unregTS.getCurrentValue(rts)
                    #inflow = unregTS.getPeriodAverage(int(min(numStepsComputeBlock, k+numStepsToAvg)), numStepsToAvg)
                    flowAug = deficitByProject[resvName]
                    if resvName == "Lookout Point":
                        if "Hills Creek" in deficitByProject:
                            #Include effects of Hills Creek (neglect routing times)
                            flowAug = deficitByProject["Lookout Point"] + deficitByProject["Hills Creek"]
                        # If Hills Creek isn't in deficitByProject, Hills Creek isn't directly operating to augment flow.
                        # But the value for Lookout Point should already account for Hills Creek (treat them as a unit)
                    minFlow = max(0, inflow + flowAug)
                    #Can't be any more than the max release
                    maxRel = self.resvConfig["MaxRelease"][resvName]
                    minFlow = min(minFlow, maxRel)
                    minFlowByProject[resvName] = minFlow
                    self.setLocalTSValue("MinReleaseFor_%s-%s" %(locName, resvName), rts, minFlow)
        return True
    
    def cleanup(self, network, currentVariable):
        '''
        Runs after the simulation has completed
        Typically diagnostic messages and DSS timeseries writing
        '''
        if len(currentVariable.localTimeSeriesList()) > 0:
            currentVariable.localTimeSeriesWriteAll()
    
    def initRuleScript(self, currentRule, network):
        """
        Called by a scripted rule at each reservoir
        Intended to do nothing, all initialization action is done in the .initialization method of the SV
        """
        return True
        
    def runRuleScript(self, currentRule, network, currentRuntimestep):
        """
        Called by a scripted rule at each reservoir
        This will run every time step of the compute. 
        At this point, the storage/release at a previous timestep is known,
        as well as the current timestep inflow. 
        """
        opValue = OpValue()
        if not self.computeSV:
            opValue.init(OpRule.RULETYPE_MIN, 0)
            return opValue
        resvName = currentRule.getReservoirElement()._name
        if not resvName in self.resvNamesSupporting:
            #This reservoir isn't supporting, don't do anything.
            opValue.init(OpRule.RULETYPE_MIN, 0)
            return opValue
        #If using an external time series, apply it now
        if self.useExternalTS:
            tsName = resvName+"-FLOW-AUG-EXTERNAL"
            ts = self.getLocalTS(tsName)
            if ts is None:
                raise AssertionError("Expecting to use an external time series for flow-aug, but doesn't exist: %s" %tsName)
            tsCur = ts.getCurrentValue(currentRuntimestep)
            opValue.init(OpRule.RULETYPE_MIN, tsCur)
            return opValue
        
        #Not using external TS.
        #Want to do the computations here
        #Compute the whole system operation if it hasn't been done already
        self.compute(network)
        ruleValue = 0.
        #Take the higher of the min release for Salem or Albany
        for locName in MAINSTEM_LOCATIONS:
            ruleValue = max(ruleValue, self.getLocalTSValue("MinReleaseFor_%s-%s" %(locName, resvName), currentRuntimestep))
        if ruleValue == 0: #don't waste any more time, just return 0
            opValue.init(OpRule.RULETYPE_MIN, 0)
            return opValue
        storPrev = network.getTimeSeries("Reservoir",resvName, "Pool", "Stor").getPreviousValue(currentRuntimestep)
        inflow = network.getTimeSeries("Reservoir",resvName, "Pool", "Flow-IN").getCurrentValue(currentRuntimestep)
        timeStepMinutes = currentRuntimestep.getTimeStepMinutes()
        cfsToAcFt = CFSDAY_TO_AF*timeStepMinutes/1440.
        #Don't go below the buffer elevation/storage to support these min flows.
        bufferStor = self.getLocalTSValue("BufferStor-%s" %(resvName), currentRuntimestep)
        relForBuffer = inflow + (storPrev-bufferStor)/cfsToAcFt
        ruleValue = max(0, min(ruleValue, relForBuffer))
        opValue.init(OpRule.RULETYPE_MIN, ruleValue)
        return opValue

def getWYTypeTS(network):
    """ Get WY type time series for interpolating the min flow target"""
    inputTSDataSet = network.getInputTSDataSet()
    wyTypeTS = inputTSDataSet.getTSRecord(WY_TYPE_TS_NAME, RssModelVariableConstants.VID_OPRULETS_TSINPUT)
    if wyTypeTS is None:
        errMsg = "Failed computing Salem/Albany min flow"
        errMsg += "\nLooking for '%s' external time series,but it doesn't exist in this alternative." %WY_TYPE_TS_NAME
        errMsg += "\nMake sure there is a dummy rule to bring in this timeseries (usually at Hills Creek)"
        raise AssertionError(errMsg)
    #Have to load it up. I'm sure there's another way to get at this directly, but I'm not sure
    loaded = wyTypeTS.loadTSData()
    wyTypeTS.setInterpUnitsType("PER-AVER")
    wyTypeTS.setUnitsType("PER-AVER")
    return wyTypeTS

def loadMinFlowTable(minFlowCSVFullPath):
    """Returns the min flow table as a two-variable lookup.
    Function of WY type and date.
    X values are WY
    columns are the number of days after April 1 (integer)
    the meat of the table are the min flows.
    To interpolate on this table, call interpTbl"""
    #Read in the CSV file
    lines = fileOpenReadClose(minFlowCSVFullPath)
    lines = stripOutCommentLines(lines)
    csvDict = getCSVDictReader(lines)
    csvListDict = convertCSVDictReaderToListDict(csvDict)
    #Deal with the date headers. The below line keeps them in order, which is good
    dateStrList = list(csvDict.fieldnames)
    dateStrList.remove("WY_type")
    #Convert the text dates into number of days after 01Apr (01Apr 2400 is a value of 0) 
    numDaysList = []
    apr1Date = HecTime("01Apr2000 2400")
    for dateStr in dateStrList:
        hTime = HecTime("%s2000 2400" %dateStr)
        numDaysSinceApr1 = apr1Date.computeNumberIntervals(hTime, 1440)
        #if numDaysSinceApr1 < 0: raise AssertionError("Invalid CSV file, has dates before 01Apr: %s" %minFlowCSVFullPath)
        numDaysList.append(numDaysSinceApr1)
    numDaysStrList = [str(n) for n in numDaysList]
    #Now, actually process through the table
    wyTypeList = []
    dataArray = [[] for ii in range(len(csvListDict))] #Each list has values for all columns (horizontal, not vertical)
    for i, rowDict in enumerate(csvListDict):
        wyTypeList.append(float(rowDict["WY_type"]))
        for j, dateStr in enumerate(dateStrList):
            dataArray[i].append(float(rowDict[dateStr]))
    #Create an object that allows for interpolation
    minFlowTable = PairedValuesExt()
    minFlowTable.setNumY(len(dateStrList))
    minFlowTable.setArrays(wyTypeList, dataArray)
    minFlowTable.setCurveLabels(numDaysStrList)
    minFlowTable.setInterpolationType(PairedValuesExt.INTERP_LINEAR_ID)
    return minFlowTable

def interpTbl(minFlowTable, wyType, hTime):
    """
    Does 2-variable interpolation as a function of wy type and date.
    Step interpolation for date.
    linear interpolation for wy type. 
    """
    #Get the number of days past Apr 1
    apr1Date = HecTime("01Apr%s 2400" %hTime.year())
    numDaysSinceApr1 = apr1Date.computeNumberIntervals(hTime, 1440)
    #Want to do step interpolation by date.
    #Find the date in the table just before or equal to the current date 
    tblDates = minFlowTable.getCurveLabelValues()
    tblDate = -999
    for d in tblDates:
        if d > tblDate and d <= numDaysSinceApr1: 
            tblDate = d
    #Needs to be a double/float, not an integer for the 2-variable interp to work
    minFlow = minFlowTable.interpolate(wyType,float(tblDate))
    '''
    Validation tests
    print("test, 15000", minFlowTable.interpolate(0,float(0)))
    print("test, 17800", minFlowTable.interpolate(2,float(0)))
    print("test, 5000", minFlowTable.interpolate(0,float(213)))
    print("test, 7000", minFlowTable.interpolate(2,float(213)))
    print("test, 17123", minFlowTable.interpolate(0,float(1.1)))
    print("test, 16123", minFlowTable.interpolate(1.5,float(23)))
    '''
    return minFlow

def loadReservoirConfig(configCSV):
    """
    Reads in the reservoir config file, then saves to a nested dictionary
    1st level key is variable name (e.g. "MaxConElev")
    2nd level key is reservoir name (e.g. "Lookout Point". NOT "LOP")
    """
    #Read in the CSV file
    lines = fileOpenReadClose(configCSV)
    lines = stripOutCommentLines(lines)
    csvDict = getCSVDictReader(lines)
    csvListDict = convertCSVDictReaderToListDict(csvDict)
    resvNames = list(csvDict.fieldnames)
    resvNames.remove("Variable")
    resvConfig = {}
    for i, rowDict in enumerate(csvListDict):
        varName = rowDict["Variable"]
        resvConfig[varName] = {}
        for j, resvName in enumerate(resvNames):
            try:
                val = float(rowDict[resvName])
            except ValueError:
                val = rowDict[resvName]
            resvConfig[varName][resvName] = val
    return resvConfig

def getResvConStorage(resvConfig, network):
    """
    Get the max amount of conservation storage available at each reservoir in the config
    This includes all reservoirs in the config file, not just those that support the operation.
    
    Returns a dictionary where the keys are the reservoirs.
    The values are the conservation usable storage (in kaf)
    """
    conStorDict = {}
    for resvName in resvConfig.values()[0].keys():
        elevStorTable = getElevationStorageTable(resvName, network) #input elevation, get storage
        minConStor = elevStorTable.interpolate(resvConfig["MinConElev"][resvName])
        maxConStor = elevStorTable.interpolate(resvConfig["MaxConElev"][resvName])
        conStor = (maxConStor - minConStor)/1000.
        conStorDict[resvName] = conStor
    return conStorDict
    
def getBufferZoneStor(poolElem, currentDate, bufferElevMax, minConElev):
    """
    When pool drops below buffer zone, 
    Salem/Albany rule typically shuts off
    This could introduce some oscillations, but this would only occur in late summer
    when inflows are low and the at-site minimum flows will continue drafting the project when Salem/Albany is shut off.
    "pool" variable is a hec.rss.model.Storage (used to interpolate storage to elevation
    Returns buffer zone storage for a given day (ac-ft)
    """
    #Assume a linear interpolation of the buffer elevation from a max on 31July to a min on 31Oct
    bufferStorMax = poolElem.elevationToStorage(bufferElevMax)
    minConStor = poolElem.elevationToStorage(minConElev)
    if currentDate.month() < 6:
        bufferStor = 0
    elif currentDate.month() < 8:
        bufferStor = bufferStorMax
    elif currentDate.month() > 10:
        bufferStor = minConStor
    else:
        jul31Date = HecTime()
        jul31Date.setYearMonthDay(currentDate.year(), 7, 31, 1440)
        hoursAfterJul31 = jul31Date.computeNumberIntervals(currentDate, 60)
        hoursJul31_Oct31 = 92.*24.
        bufferStor = bufferStorMax - (bufferStorMax - minConStor)*hoursAfterJul31/hoursJul31_Oct31
    return bufferStor
    

