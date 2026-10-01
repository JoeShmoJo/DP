"""

 Generic base external state variable class

 Useful Methods:
  # Print statements - Use python logging library and levels print messages
   self.printDebugMessage("<msg>")
   self.printMessage("<msg>")
   self.printLogMessage("<msg>")

   self.printWarningMessage("<msg>")  Also prints message using network.Warning in addition to logging module.
   self.printErrorMessage("<msg>")    Also prints message using network.Error in addition to logging module.

  # Storing values, use dictionary methods
  self["newKey"] = value
  
  # Handling HecTime objects, corrects time granularity
  self.convertToHecTime(runTimestep)


 Useful Attributes

 # Turns off compute of main function
 self.computeSV = False
 
"""

from hec.heclib.util import HecTime
from hec.io import PairedDataContainer, TimeSeriesContainer, TextContainer
from hec.model import PairedValuesExt, RunTimeStep, RunTimeWindow, TSRecord
#LocalTSRecordImpl moved from hec.model to hec.rss.model in ResSim 4.1. Import it
#both ways so this file runs under 4.1 and 3.5 alike.
#TSDataSet moved to hec.clientapp.model in the same release. It was imported here
#but never used, so it is dropped rather than followed.
try:
    from hec.rss.model import LocalTSRecordImpl      #ResSim 4.1
except ImportError:
    from hec.model import LocalTSRecordImpl          #ResSim 3.5
from hec.hecmath import TextMath, TimeSeriesMath, HecMath
from hec.model import RunTimeStep
from hec.script import Constants
from hec.lang import DSSPathString
import bisect
import calendar
import string

from hec.rss.model import RssModelVariableConstants

# Custom imports
from NWDJyLib.cTimes import getHecTimeFromRuntimestep
from NWDJyLib.DSS import cDSS
from NWDJyLib import rLogging
import NWDJyLib.FixedData.NameAlias as NameAlias
import NWDJyLib.ResSim.cResSim as cResSim
import java.lang

class ExternalSV(dict):
    '''
    This is the base external variable class
    '''
    
    def __setitem__(self, key, value):
        self.__dict__[key] = value
        
    def __getitem__(self, key):
        return self.__dict__[key]
        
    def clone(self):
        # Creates a copy of the class
        return copy.copy(self)
        
    def __init__(self, network, currentVariable):
        '''
        Initializes the state variable with basic attributes and methods
        '''
        # State variable and full module names
        self.svName = currentVariable.getName()
        self.moduleName = "externalSVs.implementations.%s" % self.svName
        logModelSystem = "ExternalSV"
        self._logger = rLogging.getLogger(self.svName, logModelSystem)
        self._network = network
        self._currentVariable = currentVariable
        self._thisRun = network.getRssRun()

        self.AF_PER_CFSD = 86400./43560.
        self.CFSD_PER_AF = 43560./86400.
        
        altSetupSV = network.getStateVariable("Alternative_Setup")
        
        if altSetupSV is not None:
            self.fileNameSimulation = altSetupSV.varGet("fileNameSimulation")
            self.fPart = altSetupSV.varGet("dssOutputFpart")
        
        self.runName = network.getAlternative().getName()
        self.altName = network.getAlternative().getName().split(":")[-1]
        
        #Clearing any local timeseries left in memory from previous models
        if currentVariable.localTimeSeriesList().size() > 0:
            currentVariable.localTimeSeriesClear()
        
        # Setting default option
        self.computeSV = True
        
        # Extracting start and end times
        tw = network.getRssRun().getRunTimeWindow()
        self.timeWindow = tw
        self.startTime = tw.getStartTime()
        self.endTime = tw.getEndTime()
        # Getting additional run info
        self.dPart = "%s%s" % (tw.timeStep, tw.timeIncrementString)
        self.timeStepMinutes = tw.timeStepMinutes
        self.numSteps = tw.numSteps

        self.debug = False
        
    def initializeDicts(self, dictNames):
        '''
        Initialize dictionaries in current state variable class object
        
        Args:
          dictNames (list of strings):  the names of the dictionaries to initializeDicts
          
        Return:
            None
        '''
        for dictName in dictNames:
            self[dictName] = {}
        return None
        
    def printDebugMessage(self, msg):
        self._logger.debug(msg)
        print("%s:\t%s" % (self.svName, msg))
            
    def printMessage(self, msg):
        self._logger.info(msg)
        self._network.printMessage("%s:\t%s" % (self.svName, msg))
    
    def printLogMessage(self, msg):
        self._logger.info(msg)
        self._network.printLogMessage("%s:\t%s" % (self.svName, msg))

    def printWarningMessage(self, msg):
        self._logger.warning(msg)
        self._network.printWarningMessage("%s:\t%s" % (self.svName, msg))

    def printErrorMessage(self, msg):
        self._logger.error(msg)
        self._network.printErrorMessage("%s:\t%s" % (self.svName, msg))
        
    #--------------------#
    # Default SV Scripts #
    #--------------------#
    
    def initialization(self, network, currentVariable):
        '''
        Called during the Initialization script of the state variable
        '''
        return Constants.TRUE
        
    def main(self, network, currentVariable, runTimestep):
        '''
        Called during the Main script of the state variable
        '''
        return Constants.TRUE
        
    def compute(self, network, currentVariable, runTimestep):
        '''
        (Optionally) called during the Main script of the state variable
        '''
        return Constants.TRUE
        
    def cleanup(self, network, currentVariable):
        '''
        Called during the Cleanup script of the state variable
        '''
        # Retrieve list of local time series
        try:
            localList = currentVariable.localTimeSeriesListKeys()
        except:
            localList = []
        
        # If local time series exists write to DSS
        if len(localList) > 0:
            currentVariable.localTimeSeriesWriteAll()
        return Constants.TRUE
        
    #-------------#
    # DSS Methods #
    #-------------#
    
    def writeToSimDss(self, containerObj):
        '''
        Writes a time series object (TimSeriesContainer or TimeSeriesMath) to the
          the simulation DSS
        '''
        
        dssSimFile = cDSS.openDSSFile(self.fileNameSimulation)
        # PairedDataContainer, TimeSeriesContainer, TextContainer
        if isinstance(containerObj, TimeSeriesContainer) or \
            isinstance(containerObj, PairedDataContainer) or \
            isinstance(containerObj, TextContainer):
            dssSimFile.put(containerObj)
        # TextMath, TimeSeriesMath, HecMath
        elif isinstance(containerObj, TimeSeriesMath) or \
            isinstance(containerObj, TextMath):
            dssSimFile.write(containerObj)
        else:
            self.printWarningMessage("Unable to save time series object")
        dssSimFile.done()
        
    def readFromSimDSS(self, dssPath, getEntireDataSet = True):
        '''
        Reads TSC path from simulation DSS
        '''
        try:
            dssSimFile = cDSS.openDSSFile(self.fileNameSimulation)
            tsc = dssSimFile.get(dssPath, getEntireDataSet)
        except:
            return None
        finally:
            dssSimFile.done()
        return tsc
    
    def getPairedValuesExt(self, dssFileName, dssPath):
        '''
        Retrieves a PairedDataContainer from a DSS file and places the container inside of a PairedValuesExt object
        '''
        pairedValuesExtObj = PairedValuesExt()
        try:
            dssFile = cDSS.openDSSFile(dssFileName)
            pdc = dssFile.get(dssPath)
            pairedValuesExtObj.setData(pdc)
        except:
            return None
        finally:
            dssFile.done()
        return pairedValuesExtObj
        
    
    #---------------#
    # Time Handling #
    #---------------#
    
    def monthAbbrFromInt(self, m):
        '''
        Converts an integer value to the month abbreviation (e.g., "Jan")
        '''
        return calendar.month_abbr[m]
    
    def convertMonthNameOrAbbrToInt(self, mVal):
        '''
        Converts from a month string (e.g., 'Apr' or 'April') to integer (e.g., 4)
        If value is already an integer (1,12), then return the integer value
        '''
        badValMessage = "Unable to specify month value for '%s', passed to"+\
                            "'convertMonthNameOrAbbrToInt' function.  Expecting integer, "+\
                            " name, or abbreviation (e.g., 4, 'Apr', 'April')"
        # Convert from month abbreviation or name to integer if needed
        if isinstance(mVal, str):
            mName = mVal
            m = None
            # First, check if it's a month abbreviation
            m = [e for e in range(1,13) if calendar.month_abbr[e].upper() == mName.upper()]
            # Then, check if it's a month name if needed
            if len(m) == 0:
                m = [e for e in range(1,13) if calendar.month_name[e].upper() == mName.upper()]
            if len(m) == 0:
                self.printErrorMessage(badValMessage % str(m))
            m = m[0]
        else:
            m = int(mVal)
            if m not in range(1,13):
                self.printErrorMessage(badValMessage % str(m))
        return m
    
    def getMonthlyIntFromTWString(self, twStr):
        '''Splits a monthly time window string into separate monthys,
           then returns the corresponding integer values as a tuple
           @param twStr  string, time window definition.  e.g., "Jan-Jul"
           @return       tuple, integer values of months. e.g., 1, 7'''
        twStrSplit = twStr.split("-")
        return self.convertMonthNameOrAbbrToInt(twStrSplit[0]),\
            self.convertMonthNameOrAbbrToInt(twStrSplit[1])
    
    def isBeginningOf14Period(self, cTime):
        '''
        Checks whether a HecTime object is the first day
          of a 14-period time window.  i.e., first of month
          or Apr15, Aug15
        '''
        cDay = cTime.day()
        cMonth = cTime.month()
        if cDay == 1:
            return Constants.TRUE
        elif cDay == 15 and cMonth in [4,8]:
            return Constants.TRUE
        else:
            return Constants.FALSE
            
    def hecTimeEqualsMMMDD(self, hTime, mmmdd):
        '''
        Checks if a HecTime object has the same month and day
          corresponding to string of format: mmmdd (e.g., "Apr01")
        '''
        return ("%s%02g" % (calendar.month_abbr[hTime.month()],hTime.day())).upper() == mmmdd.upper()
        
    def convertToHecTime(self, dtObj):
        '''
        Modified from 'getHecTimeFromRuntimestep' function NWDJyLib.cTimes module
        Converts date object to HecTime if not already and modifies the
          time granularity to be minutes for proper calls to <TimeSeriesContainer>.get
          function.
          
        @param dtObj       HecTime or RunTimeStep object to be converted 
                            to HecTime with minute granularity
        '''
        try:
            if isinstance(dtObj, HecTime):
                # Check time granularity and set to minutes for more robust 
                #   *.getValue(<HecTime>) calls to time series objects
                currentDate = dtObj.clone()
            elif isinstance(dtObj, RunTimeStep):
                currentDate = dtObj.getHecTime().clone()
            else:
                self.printErrorMessage("Need to pass either RunTimeStep or HecTime object to function 'convertToHecTime'")
                return None
                
                
            # If the hecTime object returned is daily granularity, subtract a day due to midnight shift #midnight sift not needed in ResSim 3.5
            #if currentDate.getTimeGranularity() == HecTime.DAY_INCREMENT: # days
            #    currentDate.subtractDays(1) # Midnight shift
            currentMonth = currentDate.month()  
            currentDay = currentDate.day()
            currentYear = currentDate.year()
            # If the daily hecTime object does not have a granularity of minutes, 
            # Set the current date to a granularity of minutes (2400 hours at the end of the day)
            #if currentDate.getTimeGranularity() == HecTime.DAY_INCREMENT: 
            # 2020-04-29, Ross W: Used to modify only if at day granularity,
            #   but this did not produce desired behavior. Always resetting time granularity.
            #   HecTime.MINUTE_INCREMENT is 1, and time granularity of HecTime object 
            #   initialized as, e.g.,  HecTime("01Jan1943") is also 1.
            currentDate.setTimeGranularity(HecTime.MINUTE_INCREMENT) #granularity of minutes
            currentDate.setYearMonthDay(currentYear, currentMonth, currentDay, 1440)

            return currentDate
                
        except Exception, exception:
                self.printErrorMessage(exception.message)
        
    def needToCompute(self, network, currentVariable, runTimestep,\
        computeIterOption, computePassOption):
        '''
        Interprets the state variable's compute pass settings, and determines
        whether the variable needs to be computed.  This is done by checking against and
        internal tracker so that the state variable is only evaluated once per timestep.
        '''
        
        #computePassOption = currentVariable.varGet("computePassOption")
        #computeIterOption = currentVariable.varGet("computeIterOption")
        skip = currentVariable.varGet("skip")
        
        if skip:
            return False
        
        if hasattr(self, "computeSV") and not self.computeSV:
            return False
        
        # Get current HecTime for eval with compute date option
        cTime = getHecTimeFromRuntimestep(runTimestep)
        
        # make sure computePassOption is list
        if not isinstance(computePassOption,list):
            computePassOption=[computePassOption]
        
        if not computeIterOption in ["first","ignore","every"]:
            self.printErrorMessage("needToComputeMain evalulation - 'computeIterOption' set to '%s' with no \
                 current options for interpretation.  Expecting 'first','ignore', or 'every'" % computeIterOption)
            return Constants.FALSE
                 
        if not all([e in range(10) for e in computePassOption]):
            self.printErrorMessage("needToCompute evalulation - 'computePassOption' set to '%s' with no \
                 current options for interpretation.  Expecting integer(s) less than 9 as list or atomic." % \
                 str(computePassOption))
            return Constants.FALSE
                
        #---------------------#
        # Compute Pass Option #
        #---------------------#                

        if network.getComputePassCounter() in computePassOption:
            returnVal = Constants.TRUE
        else:
            returnVal = Constants.FALSE
            
        #---------------------#
        # Compute Iter Option #
        #---------------------#
        
        # Compute pass option set to ignore during main, return False
        if isinstance(computeIterOption,str) and \
            computeIterOption.lower() == "ignore":
            return Constants.FALSE
        # Compute pass option set to compute every pass, return True
        if isinstance(computeIterOption,str) and \
            computeIterOption == "every":
            return Constants.TRUE and returnVal
            
        # This is the very first time the 'needToCompute' function is being evaluated:
        #    initialize and return True for evaluation
        if not "prevTimestep" in dir(self):
            self.prevTimestep = runTimestep.dateTimeString()
            self.tracker = 1
            returnVal = Constants.TRUE and returnVal
            
        # If only need to compute on the first iteration
        if computeIterOption=="first":
            # If previous timestep is the same, and tracker is greater than one
            if self.prevTimestep == runTimestep.dateTimeString() and self.tracker > 1:
                returnVal = Constants.FALSE
            else: # If either of the above isn't true, then should eval (new timestep or on first pass)
                self.tracker = 1
                returnVal = Constants.TRUE and returnVal
                
        self.prevTimestep = runTimestep.dateTimeString()
        self.tracker += 1
        
        #---------------------#
        # Compute Date Option #
        #---------------------#
        
        # Run every timestep
        returnVal = Constants.TRUE
        
        return returnVal

    #----------------#
    # Time Functions #
    #----------------#
    def extractCurrentTimeInfo(self, runTimestep):
        '''
        Assign current date information to this class object
        
        Args:
          runTimestep (hec.model.RunTimeStep): The current run timestep object
          
        Returns:
          None
        '''
        # Get the current date info
        self.currentStep = runTimestep.getStep()
        self.currentDate = getHecTimeFromRuntimestep(runTimestep)
        self.currentMonth = self.currentDate.month()  
        self.currentDay = self.currentDate.day()
        self.currentYear = self.currentDate.year()
        self.prevDate = HecTime()
        self.prevDate.set(self.currentDate.value())
        self.prevDate.subtractDays(1)
        return None
    
    #-----------------------#
    # Time Series Functions #
    #-----------------------#
    
    def getLocalTS(self, tsName):
        '''
        Return a currently store TSRecord object by name
        '''
        return self._currentVariable.localTimeSeriesGet(tsName)
    
    def getLocalTSValue(self, tsName, runTimestep):
        '''
        Return a currently store TSRecord's value at the provided run timestep
        '''
        tsRecord = self.getLocalTS(tsName)
        return tsRecord.getValue(runTimestep.getStep())

    def setLocalTSValue(self, tsName, runTimestep, value):
        '''
        Set the value of a local TS record
        '''
        localTS = self.getLocalTS(tsName)
        if localTS:
            localTS.setCurrentValue(runTimestep, value)
        return None
        
        
    def storeTSC(self, tsName, tsc):
        '''
        Store TSRecord to SV
        '''
        self._currentVariable.localTimeSeriesNew(tsName, tsc)
    
    def makeConstantValueTSC(self, aPart = "", bPart = "dummy", cPart = "FLOW", \
        fPart = "", units = "CFS", valueType = "PER-AVER", value = 0.):
        '''
        Create a zero-valued TimeSeriesContainer object witht the same time window
          and time step as simulation and alternative, respectively.
        '''
        
        tsc = TimeSeriesContainer()
        # Form DSS path name
        tsc.watershed = aPart
        tsc.location = bPart
        tsc.parameter = cPart
        tsc.version = fPart
        tsc.fullName = "/%s/%s/%s/%s//%s/" % (aPart, bPart, cPart, self.dPart, fPart)
        tsc.interval = self.timeStepMinutes
        # Establish times and values
        times = []
        values = []
        hTime = self.startTime.clone()
        while hTime.compareTo(self.endTime) <= 0:
            times.append(hTime.value())
            values.append(value)
            hTime.addMinutes(self.timeStepMinutes)
        tsc.times = times
        tsc.values = values
        tsc.numberValues = len(values)
        # Set units and time series type
        tsc.units = units
        tsc.type = valueType
        return tsc
    
    def makeConstantValueTSM(self, bPart = "DUMMY", cPart = "FLOW", value = 0.):
        '''
        Create a new, constant-valued TSC
        '''
        tsc = self.makeConstantValueTSC(value = value)
        blankTSM = self.tscToHecMath(tsc)
        blankTSM.setLocation(bPart)
        blankTSM.setParameterPart(cPart)
        return blankTSM
        
    def createBlankLocalTS(self, tsNames, defaultValue = Constants.UNDEFINED):
        '''
        Create a new, constant-valued TSC and store to current SV
        '''
        for tsName in tsNames:
            self._currentVariable.localTimeSeriesNew(tsName, defaultValue)
        return Constants.TRUE
        
        
    def checkOrMakeLocalTS(self, tsNames):
        '''
        Checks that a local time series exists in a SV and creates
          a new time series if not. 
        '''
        for tsName in tsNames:
            if not self._currentVariable.localTimeSeriesExists(tsName):
                self.createBlankLocalTS(tsName)
        return None
        
    
    def tscToHecMath(self, tsc):
        '''
        Returns the TimeSeriesContainer object as HecMath object
        '''
        return HecMath.createInstance(tsc)

        
    def hecMathToTSC(self, tsm):
        '''
        Returns the HecMath object as a TimeSeriesContainer object
        '''
        return tsm.getData()
        
    def tscToTSRecord(self, tsc):
        '''
        Converts TimeSeriesContainer object to TSRecord
        '''
        return LocalTSRecordImpl(tsc)
        
    def hecMathToTSRecord(self, tsm):
        '''
        Converts TimeSeriesMath object to TSRecord
        '''
        return LocalTSRecordImpl(tsm.getData())
        
    def getClosestTimeIndex(self, tsc, hTime):
        """
        Returns the closest time index (relative to tsc.times[<x>])
          relative to the given HecTime
        Args:
            tsc (TimeSeriesContainer): A timeseries.
            hTime (HecTime): The time to match.
        
        Returns:
            An integer index.
        """
        if not isinstance(hTime, HecTime):
            raise TypeError("Argument 'hTime' must be an HecTime object.")
        elif not hTime.toString():
            raise ValueError("Argument 'hTime' must be a valid timestamp.")
        time_ints = tsc.getTimes().getIntArray()
        search_int = hTime.value()
        b_idx = bisect.bisect_left(time_ints, search_int)        
        lower = max([0, b_idx - 1])
        upper = min([b_idx + 1, len(time_ints)])
        diffs = [abs(i - search_int) for i in time_ints[lower:upper]]
        if diffs.index(min(diffs)) > 0:
            idx = upper - 1
        else:
            idx = lower        
        return(idx)
        
    def getClosestValue(self, tsc, hTime):
        '''
        Returns the closest tsc.values element relative to the
          provided HecTime object
        @param tsc   TimeSeriesContainer to pull value from
        @param hTime HecTime object to compare to tsc.times
        '''
        index = self.getClosestTimeIndex(tsc, hTime)
        if index is not None:
            return tsc.values[index]
        else:
            return None
            
            
    def makeDailyTSC(self, times, values, pathName = None, \
            aPart = None, bPart = None, cPart = None, \
            fPart = None, type="INST-VAL"):
        '''
        Returns a daily TimeSeriesContainer object with the designated
          DSS pathname.  Either specify the 'aPart', 'bPart', and 'cPart', or
          specify the full pathname. Default data type is INST-VAL
          
        @param times     list of either integers or HecTime objects
        @param values    list of numeric values
        @param pathName  string of the full DSS path
        @param aPart,
               bPart,
               fPart     strings defining the DSS path parts.  Need to at least
                         specify the A, B, and C parts.  If F part unspecified, will
                         default to the F part for the ResSim model
        @param type      string of either "PER-CUM", "INST-VAL", "PER-AVER",
                         or "INST-CUM" default is "INST-VAL"
        @return TimeSeriesContainer object, 1DAY time interval
        '''
        tsc = TimeSeriesContainer()
        tsc.times = times
        tsc.values = values
        if pathName:
            pass
        elif fPart:
            pathName = "/%s/%s/%s//1DAY/%s" % \
                (aPart, bPart, cPart, fPart)
        elif aPart and bPart and cPart:
            pathName = "/%s/%s/%s//1DAY/%s" % \
                (aPart, bPart, cPart, self.fPart)
        else:
            self.printErrorMessage("makeDailyTSC: Need to at least specify the \
                    aPart, bPart, and cPart arguments.")
        tsc.fullName = pathName
        tsc.interval = 1440
        tsc.startTime = times[0]
        tsc.endTime = times[-1]
        tsc.numberValues = len(times)
        tsc.type = "INST-VAL"
        return tsc


    def firstOfMonth(self, hTime):
        """
        Get the first datetime of the input time's month.

        Args:
           hTime (HecTime): A datetime.
        
        Returns:
            A HecTime, day 1 and time 0001 of input time's month and year
        """
        if not isinstance(hTime, HecTime):
            raise TypeError("hTime is not an HecTime object")
        outTime = HecTime()
        outTime.setYearMonthDay(hTime.year(), hTime.month(), 1, 1)
        return outTime
        

    def lastOfMonth(self, hTime):
        """
        Get the last datetime of the input time's month.

        Args:
           hTime (HecTime): A datetime.
        
        Returns:
            A HecTime, day 1 and time 0000 of the month following the input time
            (equivalent to 2400 on the last day of the current month).
        """
        if not isinstance(hTime, HecTime):
            raise TypeError("hTime is not an HecTime object")
        outTime = HecTime()
        outTime.setYearMonthDay(hTime.year(), hTime.month() + 1, 1, 0)
        return outTime
    
    def initializeLocalTSCs(self, currentVariable, tsNames, autoDetectParam=True):
        """
        Initializes local time series so that they are correctly established 
          with valid times attributes.
          
        Args:
          currentVariable (hec.rss.model.StateVariable) The ResSim state 
                             variable in which to store the time series.
          tsNames (list of strings) Names of new time series to initialize
          autoDetectParam: (boolean) if true, will try to change the c-part based on the name of timeseries
        """
        # Valid time series spanning the full simulation time window, populated
        # with defined values.
        defaultValue = java.lang.Double.NEGATIVE_INFINITY
        dummyTSC = currentVariable.getTimeSeries().getTimeSeriesContainer()
        dummyTSC.values = [defaultValue for v in dummyTSC.values]
        # Create DSSPathString object for path manipulation
        dssPath = DSSPathString(dummyTSC.fullName)
        svName = dssPath.getBPart()
        
        for tsName in tsNames:
            dssPath.setBPart(svName + "-" + tsName)
            tsNameUppercase = tsName.upper()
            if autoDetectParam:
                #defaults
                cPart = dssPath.getCPart()
                unitStr = dummyTSC.units
                typeStr = dummyTSC.type
                if "SPACE" in tsNameUppercase:
                    cPart = "SPACE"
                    unitStr = "ac-ft"
                    typeStr = "INST-VAL"
                elif "VOL" in tsNameUppercase or "STOR" in tsNameUppercase:
                    cPart = "STOR"
                    unitStr = "ac-ft"
                    typeStr = "INST-VAL"
                elif "RELEASE" in tsNameUppercase or "FLOW" in tsNameUppercase or "UNREG" in tsNameUppercase:
                    cPart = "FLOW"
                    unitStr = "cfs"
                    typeStr = "PER-AVER"
                elif "RATIO" in tsNameUppercase or "IS" in tsNameUppercase or "SGC" in tsNameUppercase or "PCT" in tsNameUppercase:
                    cPart = "CODE"
                    unitStr = "Code"
                    typeStr = "INST-VAL"
                #reset the c-part/units
                dssPath.setCPart(cPart)
                dummyTSC.units = unitStr
                dummyTSC.type = typeStr
            dummyTSC.fullName = dssPath.getPathname()
            currentVariable.localTimeSeriesNew(tsName, dummyTSC.clone())
        
        return Constants.TRUE

    #----------------#
    # Text Functions #
    #----------------#
    
    def formDSSPath(self,a,b,c,d,e,f):
        '''
        Returns a string of DSS path given individual
          strings of the path parts
        '''
        return str("/"+"/".join([a,b,c,d,e,f])+"/")
        
    def getPathPart(self, partLetter, path):
        '''
        Returns the DSS path part specified by partLetter (A-F)
        '''
        intValOfPart = self.intValOfLetter(partLetter) # 0-5
        splitPath = path.split("/") # First element is blank, 
                                    #   total length is 7
        return splitPath[intValOfPart+1]
        
    def intValOfLetter(self,l):
        '''
        Given a single letter, returns the float value of
          the letter's location in the alphabet (0-25)
        '''
        return [e for e in range(26) if \
                        l.upper() == string.ascii_uppercase[e] ][0]
    
    def replacePathPart(self, partLetter,  newPart, path):
        '''
        Replaces a specific path part in a DSS path
        @param partLetter string, the letter of the DSS path to be replaced
                            (A through F)
        @param newPart    string, the new part to replace the old with
        @param path       string, the DSS path
        @return           string with the path part replaced
        '''
        intValOfPart = self.intValOfLetter(partLetter) # 0-5
        splitPath = path.split("/") # First element is blank, 
                                    #   total length is 7
        splitPath[intValOfPart+1] = newPart
        
        return self.formDSSPath(splitPath[1], splitPath[2], \
                splitPath[3], splitPath[4], \
                splitPath[5], splitPath[6])
                
               
    #----------------#
    # Save Functions #
    #----------------#
    
    def saveTextToSimDss(self, path, textStr):
        '''
        Saves a string to a specified path in the output DSS file
        @param path    string, full DSS path of output, F part is optional
        @param textStr string, the text to write to DSS
        '''
        
        # Initialize DSS output file, TextContainer, and TextMath object
        dssSimFile = cDSS.openDSSFile(self.fileNameSimulation)
        tc=TextContainer()
        tm=TextMath()
        
        tc.text = str(textStr)
        tm.setData(tc)
        # Set DSS path parts
        tm.setLocation(self.getPathPart("b",path))
        tm.setLocation(self.getPathPart("b",path))
        tm.setParameterPart(self.getPathPart("c",path))
        dPart = self.getPathPart("d",path)
        if dPart == "": dPart = "1900"
        tm.setDPart(dPart)
        ePart = self.getPathPart("e",path)
        if ePart == "": ePart = "1900"
        tm.setEPart(self.getPathPart("e",path))
        fPart = self.getPathPart("f",path)
        if fPart == "":
            tm.setVersion(self.fPart) # from AltSetup
        else:
            tm.setVersion(fPart) # from input string
        
        dssSimFile.write(tm)
        dssSimFile.done()
        
        pass
        
    def getReservoirName(self, reservoir):
        """
        Convert CBT code to reservoir name.
        
        Args:
            reservoir (string): A reservoir name or CBT code.
        
        Returns:
           The reservoir name.
        
        Raises:
            KeyError: Could not find reservoir name or CBT code.
        """
        if NameAlias.myLocationAlias.nameExists(reservoir, "CBT_CODE"):
            return(NameAlias.myLocationAlias.lookup(reservoir, "CBT_CODE", "RESSIM_NAME"))
        elif NameAlias.myLocationAlias.nameExists(reservoir, "RESSIM_NAME"):
            # get correct case
            return(NameAlias.myLocationAlias.lookup(reservoir, "RESSIM_NAME", "RESSIM_NAME"))
        else:        
            raise KeyError("Could not find reservoir name or CBT code \"%s\"" % reservoir)
        
    def getReservoirRatingTable(self, reservoir, ratingType):
        """
        Get reservoir rating table.

        Args:
            reservoir (string): A reservoir name or CBT code.
            ratingType (string): The rating table type. Can be one of "StorageElevation",
              "ElevationStorage", or "ElevationRelease".
        
        Returns:
            A rating table object.
        
        Raises:
            ValueError: Rating table type not recognized.
        """
        if ratingType.lower() == "elevationstorage":
            return(cResSim.getElevationStorageTable(self.getReservoirName(reservoir), self._network))
        elif ratingType.lower() == "storageelevation":
            return(cResSim.getStorageElevationTable(self.getReservoirName(reservoir), self._network))
        elif ratingType.lower() == "elevationrelease":
            return(cResSim.getElevationReleaseTable(self.getReservoirName(reservoir), self._network))
        else:
            raise ValueError("Could not recognize rating table type \"%s\"." % ratingType)
