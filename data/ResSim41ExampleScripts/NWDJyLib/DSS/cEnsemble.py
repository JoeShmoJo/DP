"""
This code deals with ensemble streamflow predictions (ESP) data. 
The NWRFC produces ESP data and publishes to their website in .csv files.
These files need to be ingested and pumped out to standardized .dss and .csv files.
For details on DSS-VUE "collection" objects, see the :any:`cCollections` module.
Note that the input data is typically UTC--this will convert to PST always.
TODO This might be an issue, but PST is better than UTC for modeling
"""

from hec.heclib.dss import HecDss
from hec.heclib.dss import DSSPathname
from hec.heclib.util import HecTime
from hec.hecmath import TimeSeriesMath

import logging
import datetime
import os

#Custom imports
from NWDJyLib import cFile
from NWDJyLib import cTimes
from NWDJyLib.DSS import cDSS
from NWDJyLib.DSS import cTsUtils
from NWDJyLib.DSS import cCollections
from NWDJyLib.FixedData import NameAlias

################################################################################
# STATIC INPUT
CSV_NUM_FIELD_LINES = 6 #There should be 6 lines of header fields in the CSV file (e.g. UNITS:KCFS)
CSV_TIME_INTERVAL = "6HOUR" #NWRFC CSV files should be in 6-hour intervals

################################################################################
# CLASS DEFINITIONS
class Ensemble:
    """Class that represents an ensemble dataset.
    Includes code to read in the NWRFC .csv files and output to DSS and CSV.
    Performing cyclic analysis for summary statistics is done via the 
    :class:`cCollections` object in the :any:`cCollections` module. 
    General usage is to construct the object, then load data via 
    :meth:`loadNWRFC_CSV`, and then output the data using any of the following:
    :meth:`writeESPtoDSS`, :meth:`writeOutSummaryHydrographs`, :meth:`writeCSV`
    """
    def __init__(self):
        self.espYears = [] # stores the list of esp years e.g. [1949,1950...]
        self.unitMulitplier = 1 #Any multiplier needed (e.g. KCFS to CFS)
        self.units = None #e.g. CFS, FT
        self.type = None #e.g. PER-AVER, INST-VAL
        self.deterministicDays = 0 #The length of the forecast (days) the STP is used
        self.issuanceDate = None #Forecast issuance date, string (e.g. "ISSUED:2016-01-13_17:00GMT")
        self.location = "" #e.g. "LYDM8"
        self.parameter = "" #e.g. "FLOW-UNREG"
        self.espConfig = "" #e.g. "Water Supply", "Natural"
        self.rawTSCs = [] # list of TimeSeriesContainers
        self.dailyTSCs = [] #list of TimeSeriesContainers with daily data
    
    def renameLocation(self, fromCodeStr, toCodeStr):
        """
        Renames the location attribute of the object to a different code.
        Oftentimes the basic RFC code is not desired.
        For a list of valid code strings, see :any:`NameAlias`
        
        :param str fromCodeStr: The existing location code string (e.g. "NWRFC_CODE")
        :param str toCodeStr:   The location code desired (e.g. "CBT_CODE")
        :return: true if successful, false if no match was found
        """
        newLocation = NameAlias.myLocationAlias.lookup(self.location, fromCodeStr, toCodeStr)
        if newLocation:
            self.location = newLocation
            return True
        else: #Failed to find a match--don't reset the location
            return False
    
    def setAttributesFromTSC(self, tsc):
        """
        Sets atrribute values for this object from an input TimeSeriesContainer.
        Sets the .location, .parameter, .units, .type attributes
        """
        #Could use the .location field of the tsc, but using the pathname is more reliable
        dssPath = DSSPathname(tsc.fullName)
        #self.location = tsc.location
        #self.parameter = tsc.parameter
        self.location = dssPath.getBPart()
        self.parameter = dssPath.getCPart()
        self.units = tsc.units
        self.type = tsc.type
        return True
        
    def getOutputCSVFilename(self):
        """
        Return the standardized name of the CSV file for this ensemble based on
        the location, parameter, espConfig, and deterministicDays.
        e.g. "GCL_FLOW-UNREG_W_5.csv"
        """
        
        #Set up the output .csv filename
        espConfigAbbr = self.espConfig[0].upper() #e.g. N, U, W, C
        #Old way of doing it e.g. "WGCM8.QA_5.csv"
        #csvParam = NameAlias.myLocationAlias.lookup(espObj.parameter, "CWMS_PARAM", "SHEF_CODE")
        #outputCSVName = "%s.%s_%d.csv" %(espObj.location, csvParam, espObj.deterministicDays) 
        #New way of doing it e.g. "WGCM_FLOW_N_5.csv
        outputCSVName = "%s_%s_%s_%d.csv" %(self.location, self.parameter,
            espConfigAbbr, self.deterministicDays) 
        return outputCSVName
        
    def processCSVHeaders(self, lines):
        """
        In January 2015, NWRFC changed the file format of the ESP CSV files.
        The first few lines are now metadata lines.
        This method processes the lines and stores relevant information to the object.
        It finds units, parameters, etc. 
        Set the object's unitMulitplier attribute if a unit conversion will need
        to occur (e.g. KCFS to CFS).
        
        :param list lines: The read lines of the csv file
        :return boolean val: Should return True if successful, False if not
        """
        #Process the first few lines that have field values (e.g. UNITS:KCFS)
        for line in lines[0:CSV_NUM_FIELD_LINES]:
            lineVal = line.split(":")[-1].strip()
            if line.startswith("FILE:"): #e.g. FILE:WTLO3W_SQIN.ESPF10
                self.location = lineVal[0:5] #e.g. CONW1
                if "SSTG" in lineVal:
                    dssCPart = "STAGE"
                elif "N_" in lineVal:
                    #dssCPart = "FLOW-NATURAL"
                    #dssCPart = "FLOW-UNREG"
                    dssCPart = "FLOW"
                elif "W_" in lineVal:
                    #dssCPart = "FLOW-UNREG"
                    dssCPart = "FLOW"
                elif "XE_" in lineVal:
                    dssCPart = "FLOW-LOCAL"
                else:
                    dssCPart = "FLOW"
                self.parameter = dssCPart
            elif line.startswith("CONFIGURATION:"): #e.g. CONFIGURATION:UNADJUSTED
                self.espConfig = lineVal
            elif line.startswith("UNITS:"): #e.g. UNITS:KCFS
                units = lineVal
                if "KCFS" in units.upper():
                    #If units are in kcfs, convert to cfs to be standard
                    units = "CFS"
                    self.unitMulitplier = 1000.
                elif "FEET" in units.upper():
                    #convert to FT for DSS-world
                    units = "FT"
                self.units = units
            elif line.startswith("QPFDAYS:"): #e.g. QPFDAYS:10, LYDM8W, LYDM8W, ...
                self.deterministicDays = int(lineVal.split(",")[0])
            elif line.startswith("ISSUED:"): #e.g. ISSUED:2016-01-13_17:00GMT
                self.issuanceDate = line.split("ISSUED:")[-1].strip()
        if self.units is None or self.parameter == "":
            errMsg = "Failed to detect units in CSV file"
            for l in lines[0:CSV_NUM_FIELD_LINES]:
                errMsg += "\n%s" %l
            errMsg += "\nExpected a line in the file like 'UNITS:KCFS'"
            errMsg += "\nAnd 'FILE:CONW1_QINE.ESPF10'"
            errMsg += "\nRFC may have changed their file format..."
            logging.error(errMsg)
            raise AssertionError, errMsg
        return True
    
    def detectTypeFromUnits(self, units):
        """
        Gives the default data type for a given unit (e.g. PER-AVER for CFS).
        
        :param str units: The units (e.g. "CFS", "FEET")
        :return str typeStr: The output DSS-type (e.g. PER-AVER, INST-VAL)
                Defaults to INST-VAL if the units aren't recognized
        """
        if "CFS" in units.upper():
            typeStr = "PER-AVER"
        else:
            #Assume all other data is inst-val
            typeStr = "INST-VAL"
        return typeStr

    def _deriveDailyTSCs(self):
        """
        Takes the raw input TimeSeriesContainers and converts them to daily
        Takes an average for flows, and interpolates for elevations
        Assumes self.rawTSCs has already been populated
        """
        self.dailyTSCs = []
        for rawTSC in self.rawTSCs:
            tsm = TimeSeriesMath(rawTSC)
            dailyTSM = cTsUtils.transformTSM(tsm, "1DAY")
            self.dailyTSCs.append(dailyTSM.getData())
    
    def loadNWRFC_CSV(self, pathCSVFile):
        """
        Method to read in a .csv file from the NWRFC and prepare it for processing.
        CSV files from the NWRFC have a specific file format, with headers in the
        first 6 lines. The columns in line 7 are the water years, and the rows
        are the dates of occurrence (e.g. 2016-01-07 18:00:00).
        Changes the naming convention of the output as well here via :meth:`renameLocation`
        The F-part will include the configuration of the ESP data (e.g. WATERSUPPLY)
        
        :param str pathCSVFile: a pathname to the .csv file (absolute)
        :return list tscList: a list of TimeSeriesContainers, one for each year
        """
        lines = cFile.fileOpenReadClose(pathCSVFile)
        self.processCSVHeaders(lines)
        #Convert the RFC code names to CBT code names (e.g. "LIB") and parameters (e.g. "FLOW")
        success = self.renameLocation("NWRFC_CODE", "CBT_CODE")
        if not success:
            logging.warning("Failed to rename this location: %s" %self.location)
        self.type = self.detectTypeFromUnits(self.units)
        logging.info("BPart: %s" %self.location)
        logging.info("CPart: %s" %self.parameter)
        logging.info("Units: %s" %self.units)
        logging.info("Type:  %s" %self.type)
        logging.info("Deterministic Days: %s" %self.deterministicDays)
        logging.info("ESP Config: %s" %self.espConfig)
        #When processing the csv, we don't want to include the header field lines
        #Just grab the meat of the CSV
        csvLines = lines[CSV_NUM_FIELD_LINES:]
        csvLines = cFile.stripOutCommentLines(csvLines)
        csvDictReader = cFile.getCSVDictReader(csvLines)
        times = [] #list to store all times of the data
        for i, lineDict in enumerate(csvDictReader): 
            logging.debug("%2.0f of %2.0f" %(i+1, len(csvLines)-1))
            if i == 0: 
                #first line of data, can use .fieldnames now
                fieldNames = csvDictReader.fieldnames #e.g. FCST_VALID_TIME_GMT, 1949, 1950 ...
                timeHeader = fieldNames[0] #e.g. "FCST_VALID_TIME_GMT"
                #Get a list of all ensemble years as integers
                espYears = [int(i) for i in fieldNames[1:]]
                self.espYears = espYears
                #Create an empty dictionary to be populated with data
                #keys as ESP years, values as list of numbers corresponding to each time
                valueDict = {}
                for espYear in espYears: valueDict[espYear] = []
                logging.info("Number of Ensembles: %s" %len(espYears))
                logging.info("Ensemble Range: %s to %s" %(espYears[0], espYears[-1]))
            #Add the time to the list
            csvTime = lineDict[timeHeader] #typically "2015-09-22 12:00:00"
            espHecTime = HecTime(csvTime) #HecTime should be smart enough to interpret it
            #Apply a timezone shift--always put data in PST for now
            hrOffset = cTimes.getHoursOffsetFromUTC("PST") #typically negative
            espHecTime.addHours(hrOffset)
            times.append(espHecTime.value())
            #Add the values to the list
            for espYear in espYears:
                valueDict[espYear].append(float(lineDict[str(espYear)])*self.unitMulitplier)
        startTime = HecTime(times[0], HecTime.MINUTE_INCREMENT) 
        endTime = HecTime(times[-1], HecTime.MINUTE_INCREMENT) 
        logging.info("Forecast start date: %s" %startTime.dateAndTime())
        logging.info("Forecast end date:   %s" %endTime.dateAndTime())
        #Done processing through the CSV file, now create TimeSeriesContainer objects
        self.rawTSCs = []
        for espYear in espYears:
            fPart = "C:%06d|%s" %(espYear, self.espConfig) #e.g. C:001949|WATERSUPPLY
            tsc = cTsUtils.prepareTSCont(valueDict[espYear], times,
                self.location, self.parameter, CSV_TIME_INTERVAL, fPart, self.units, self.type
                )
            #tsc.timeZoneID = "UTC" #the forecast timezone is UTC, but DSS timezones are difficult to manage
            self.rawTSCs.append(tsc)
        #Derive daily estimates as well
        self._deriveDailyTSCs()
        return self.rawTSCs
        
    def addDailyTSC(self, dailyTSC):
        """
        Load a time series object of daily timestep into the ensemble collection.
        This is useful if the data already exists in a DSS file.
        This is typically used in combo with :meth:`writeOutSummaryHydrographs`
        If all we want to do is load up daily data and compute summary statistics
        
        :param TimeSeriesContainer dailyTSC: time series of daily data
        :return list tscList: the current list of daily TimeSeriesContainer objects
        """
        return self.dailyTSCs.append(dailyTSC)
        
    def writeESPtoDSS(self, outDss, typeToWrite="RAW"):
        """
        Writes all of the ensemble data from the RFC CSV file to DSS
        
        :param outDss: already opened Dss file (HecDss or DSSFile)
        :param str typeToWrite: The type of ESP data to be written
                               "RAW" or "DAILY" are allowed arguments
        """
        if typeToWrite == "DAILY":
            tscs = self.dailyTSCs
        else: #use the raw
            tscs = self.rawTSCs
        for tsc in tscs:
            outDss.write(TimeSeriesMath(tsc))
        return True
    
    def writeOutSummaryHydrographs(self, outDss, percentiles, typeToWrite="RAW"):
        """
        Take the timeseries ensemble data and compute summary hydrographs from it.
        
        :param outDss: Already opened DssFile or HecDss for output
        :param list percentiles: desired percentiles in decimal form e.g. [.05,.95]
                 can have "MEAN", "MAX", "MIN" as well
        :param str typeToWrite: The type of ESP data to be written
                       "RAW" or "DAILY" are allowed arguments
        """
        if typeToWrite == "DAILY":
            tscs = self.dailyTSCs
        else:
            tscs = self.rawTSCs
        #Create an object to calculate the statistics
        cycColl = cCollections.CyclicCollection(percentiles)
        #Stuff the CyclicCollection object with data for each sequence in the collection
        cycColl.addAllData(tscs)
        #Compute the statistics and write out the summary hydrographs
        cycColl.runCyclicAnalysis()
        cycColl.writeAll(outDss)
        return True
    
    def writeCSV(self, outCSVPath, typeToWrite="RAW"):
        """
        Output the ensemble data to a .csv file in a standard format so that
        other programs can pick it up reliably. If the NWRFC changes the file format, 
        this output should remain steady. It has dates along the top, and ESP
        years along the rows. :meth:`loadNWRFC_CSV` should be run before this.
        The output should look something like:
        
            LOCATION,PARAMETER,UNITS,ESP_YEAR,1/11/2016,1/12/2016
            LIB,FLOW,CFS,1949,1964.23,3201.79
        
        :param str outCSVPath: The pathname of the output CSV file
        :param str typeToWrite: The type of ESP data to be written
                               "RAW" or "DAILY" are allowed arguments
        """
        outLines = []
        #get the proper tscs to write
        if typeToWrite == "RAW":
            tscsToWrite = self.rawTSCs
        else:
            tscsToWrite = self.dailyTSCs
        if tscsToWrite == []: 
            errMsg = "Need to populate this object with data first, use 'loadNWRFC_CSV()' or 'addDailyTSC'"
            raise AssertionError, errMsg
        #Check if the data is daily or not. If so, need to format the dates slightly different
        usingDaily = False
        if tscsToWrite[0].interval == 1440: 
            usingDaily = True
        #Build the header line
        lineStr = "LOCATION,PARAMETER,UNITS,ESP_YEAR"
        for time in tscsToWrite[0].times:
            hTime = HecTime(time, HecTime.MINUTE_INCREMENT)
            if usingDaily:
                lineStr += ",%04d-%02d-%02d" %(hTime.year(), hTime.month(), hTime.day())
            else:
                #Show the hours and minutes
                hTime.showTimeAsBeginningOfDay(True) #csv files don't like 24:00
                lineStr += ",%04d-%02d-%02d %02d:%02d" %(hTime.year(), hTime.month(), hTime.day(), hTime.hour(), hTime.minute())
        outLines.append(lineStr)
        #Done with header line: process the rest of the file
        for i, espYear in enumerate(self.espYears):
            lineStr = "\n%s,%s,%s,%s" %(self.location, self.parameter, self.units, espYear)
            tsc = tscsToWrite[i]
            for val in tsc.values:
                lineStr += ",%.2f" %val
            outLines.append(lineStr)
        cFile.writeTextToFile(outLines, outCSVPath)
        
        
# END OF CLASS DEFINITIONS
################################################################################
# MIGRATED FUNCTIONS (IF MOVED TO ANOTHER MODULE, FOR BACKWARD COMPATIBILITY)
# theOldFunctionThatWasHere = newModule.theReplacementFunction
################################################################################
# FUNCTION DEFINITIONS

def processCSVs_NWRFC(listFile, rawInputDir, outputDir, mirrorDir, outputPercentiles):
    """
    Main subroutine to refresh the ESP data, as provided by the NWRFC in CSV files. 
    For each .csv file, will create a :class:`Ensemble` object. This will then
    write the output to DSS (6-hour and daily), as well as a standard CSV format.
    The output DSS and .summary files will have the same file stub as the input listFile
    e.g. if listFile is "C:/temp/Col.list", the output DSS files will be
    Col_6hr.dss and Col_1day.dss, and the summary will be Col.summary.
    The .summary file shows when the forecast for each file was last issued.
    
    The output .csv files will be renamed from the RFC codes here
    e.g. RFC code "LYDM" gets converted to the CBT code "LIB".
    Output name format of .csv file:
    
        (CBTcode)_(ParamName)_(EnsembleType)_(ForecastLength).csv
    
    where (ParamName) is a human readable parameter (e.g. "FLOW").
    where (EnsembleType) is the version:
    
    -N natural
    -W water supply
    -U unadjusted
        
    where (ForecastLength) is number of deterministic forecast days (e.g. 0, 5, 10)
    
    :param str listFile: pathname to a simple text file with the .csv files to process
    :param str rawInputDir: pathname to the directory of the input .csv files
    :param str outputDir: pathname to the directory to store the output
    :param str mirrorDir: pathname to the directory where to mirror the output
    :param list outputPercentiles: list of decimal numbers to compute statistics 
                on the ESP for. e.g. [.05,.95]
    """
    
    # Determine the names of the output files--use the listFile as a template
    listFileStub = os.path.basename(listFile).split(".")[0] #returns "Columbia5"
    # Define the dss output name as the same as the stub
    outDssFile6hr = listFileStub + "_6hr.dss"
    outDssFileDaily = listFileStub + "_1day.dss"
    #The summary file to record the condensed summary to 
    summaryOutFile = listFileStub + ".summary"
    outDssFile6hr = os.path.join(outputDir, outDssFile6hr)
    outDssFileDaily = os.path.join(outputDir, outDssFileDaily)
    summaryOutFile = os.path.join(outputDir, summaryOutFile)
    logging.info("Output Dss File (6Hour): %s" %outDssFile6hr)
    logging.info("Output Dss File (Daily): %s" %outDssFileDaily)
    logging.info("Text file with list of .csv files: %s" %listFile)
    logging.info("Desired output percentiles: %s" %outputPercentiles)
    outDss6hr = HecDss.open(outDssFile6hr)
    outDssDaily = HecDss.open(outDssFileDaily)
    lines = cFile.fileOpenReadClose(listFile)
    csvFileNames = cFile.stripOutCommentLines(lines)
    nowDT = datetime.datetime.now()
    summaryStr =  "  %s\n\n" % nowDT.strftime("%d-%b-%Y %H:%M:%S")
    summaryStr += "         ENSEMBLE FORECAST FILENAME  FORECAST ISSUANCE DATE\n"
    summaryStr += "  =================================  ======================\n"
    failPaths = []
    for i, csvFileStr in enumerate(csvFileNames):
        #Create a new Ensemble object and populate with information
        logging.info("\n%s of %s: %s" %(i+1, len(csvFileNames), csvFileStr))
        summaryStr += "  %33s" % csvFileStr
        #Assume the input files are in the rawInputDir
        csvFileName = os.path.join(rawInputDir, csvFileStr)
        if not cFile.doesFileExist(csvFileName):
            logging.warning("File does not exist")
            failPaths.append(csvFileName)
            summaryStr += "  File does not exist\n"
            continue
        espObj = Ensemble()
        espObj.loadNWRFC_CSV(csvFileName)
        summaryStr += "  %s\n" %espObj.issuanceDate
        #Write the data to DSS
        espObj.writeESPtoDSS(outDss6hr, typeToWrite="RAW")
        espObj.writeESPtoDSS(outDssDaily, typeToWrite="DAILY")
        #espObj.writeCSV("test.csv", typeToWrite="RAW") #no use for 6-hour csvs currently
        #Set up the output .csv filename
        outputCSVName = espObj.getOutputCSVFilename()
        #Export the csvs to the same directory as the output daily dss file
        outputCSVName = os.path.join(os.path.dirname(outDssFileDaily), outputCSVName)
        espObj.writeCSV(outputCSVName, typeToWrite="DAILY")
        espObj.writeOutSummaryHydrographs(
            outDss6hr, percentiles=outputPercentiles, typeToWrite="RAW")
        espObj.writeOutSummaryHydrographs(
            outDssDaily, percentiles=outputPercentiles, typeToWrite="DAILY")
    if len(failPaths) > 0:
        logging.warning("Failed to process the following files:")
        for failPath in failPaths: logging.warning("\t%s" %failPath)
    cFile.writeTextToFile(summaryStr, summaryOutFile)
    outDss6hr.close()
    outDssDaily.close()
    
    