"""
There are many processes that require looping through DSS files and performing
various modifications/calculations. 
This often includes reading a .csv or .txt file for instructions or a list of 
pathnames, and then performing some analysis with it.
While these tasks could be stored in :any:`cDSS`, this would clog up that module.
Rather, they are stored here and access many of the functionality in :any:`cDSS`
and :any:`cTsUtils`.
This module contains many of these "higher level" functions.
"""

from hec.heclib.dss import DSSPathname
from hec.heclib.dss import HecDss
from hec.heclib.util import HecTime
from hec.script import Constants
from java.lang import Math
from hec.hecmath import TimeSeriesMath

import logging
import os

from NWDJyLib import cFile
from NWDJyLib.ResSim import cResSim
from NWDJyLib.DSS import cDSS
from NWDJyLib.DSS import cTsUtils
from NWDJyLib.DSS import cCollections

################################################################################
# STATIC INPUT

################################################################################
# CLASS DEFINITIONS

# END OF CLASS DEFINITIONS
################################################################################
# FUNCTION DEFINITIONS
def mergePathnames(obsvDssFile, fcstDssFile, pathCSVFile, outDssFile, 
                      beginTimeStr=None, endTimeStr=None, extraSuffixList=[]):
    """Merges many pairs of DSS pathnames together and writes to an output dss file.
    The input .csv file provides the input on what pathnames should be merged together.
    This is used to mush together observed data and forecasted data, which typically
    have a bit of overlap. Currently used in the esp and dambreak data processing. 
    It also fills in up to 4 consecutive data points (if forecast and observed
    aren't perfectly aligned).
    If the forecast pathname provided in the csv file is a DSS collection (ensemble),
    this script will merge the observed data with every sequence in the ensemble.
    
    :param str obsvDssFile: The full path of the dss file with observed data
    :param str fcstDssFile: The full path of the dss file with forecast data
    :param str pathCSVFile: The full path of the input csv file with a list of pathnames to process
                            Should have headers of obsPathname, fcstPathname, outputPathname
    :param str outDssFile: The full path of the dss file for output
    :param str beginTimeStr: If supplied, the timewindow to extract the data. 
                             e.g. "02Jun1985 2400"
                             If not supplied, the entire timewindow will be done
    :param list extraSuffixList: (Optional). If supplied, must be a list of strings.
        Only applies when the forecast pathname is a collection or ensemble. 
        Each string supplied must appear as a suffix to the forecast F-part. 
        These additional pathnames will be merged with the observed data. 
        For instance, if the f part of the forecast pathname is 
        "C:001949|WATERBALANCE", and "MAX" is supplied in the extraSuffixList,
        the script will search for a pathname called "WATERBALANCE-MAX" in addition
        to all of collection pathnames.
        Typically only used for ensemble processing where summary hydrographs 
        have been generated, and it's a bit clunky to put it here.
    """
    logging.info("extraction start date         %20s" % beginTimeStr)
    logging.info("extraction end date           %20s" % endTimeStr)
    logging.info("Observed Dss File: %s" %obsvDssFile)
    logging.info("Forecast Dss File: %s" %fcstDssFile)
    logging.info("Input pathname file: %s" %pathCSVFile)
    logging.info("Output Dss File: %s" %outDssFile)
    
    if beginTimeStr:
        #Time window specified, only use the time window
        readWholeWindow = False
        dssObsv = cDSS.openDSSFile(obsvDssFile, beginTimeStr, endTimeStr)
        dssFcst = cDSS.openDSSFile(fcstDssFile, beginTimeStr, endTimeStr)
    else:
        #No time window specified
        readWholeWindow = True
        dssObsv = HecDss.open(obsvDssFile)
        dssFcst = HecDss.open(fcstDssFile)
    dssOut = HecDss.open(outDssFile)
    lines = cFile.fileOpenReadClose(pathCSVFile)
    lines = cFile.stripOutCommentLines(lines)
    csvDictReader = cFile.getCSVDictReader(lines)
    failPaths = [] #List of pathnames that failed to process
    for i, lineDict in enumerate(csvDictReader): 
        logging.info("%s of %s" %(i+1, len(lines)-1))
        pathObsv = lineDict["obsPathname"].upper()
        logging.info("\tReading: %s" %pathObsv)
        tsmObsv = cDSS.readTSM(dssObsv, pathObsv, readWholeWindow=readWholeWindow, isStrict=False)
        if not tsmObsv:
            failPaths.append(pathObsv)
            continue
        pathFcst = lineDict["fcstPathname"].upper()
        logging.info("\tReading: %s" %pathFcst)
        #If the forecast path is a collection, assume we want to read all of them (esp)
        sequenceNums = [None] #initialize it to be of length 1 so it will work if not a collection
        if DSSPathname.isaCollectionPath(pathFcst):
            logging.info("\tLooks like a collection pathname, processing all")
            dssPathFcst = DSSPathname(pathFcst)
            sequenceNums = cCollections.getCollectionSequences(dssFcst, pathFcst)
            if sequenceNums is None or sequenceNums == []:
                errMsg = "No ensemble pathnames detected in dss file."
                errMsg += "\nLooked in the following DSS file: %s" %fcstDssFile
                errMsg += "\nWith the following DSS pathname: %s" %pathFcst
                raise AssertionError, errMsg
            logging.info("\tDetected the following ensemble range: %s-%s" %(sequenceNums[0],sequenceNums[-1]))
        pathOut = lineDict["outputPathname"]
        dssPathOut = DSSPathname(pathOut)
        outEPart = dssPathOut.getEPart().upper()
        for sequenceNum in sequenceNums:
            if sequenceNum:
                #Reset the pathname f part to the current sequenceNum
                dssPathFcst.setCollectionSequence(sequenceNum)
                pathFcst = dssPathFcst.getPathname()
                #Reset the output path as well
                if DSSPathname.isaCollectionPath(dssPathOut.getPathname()):
                    dssPathOut.setCollectionSequence(sequenceNum)
                else:
                    #The original desired output f-part did not have a collection identifier--make one
                    origFPart = dssPathOut.getFPart()
                    newFPart = "C:%s|%s" %(sequenceNum, origFPart)
                    dssPathOut.setFPart(newFPart)
                pathOut = dssPathOut.getPathname()
            else: #must not be a collection, use original pathname
                pass
            tsmFcst = cDSS.readTSM(dssFcst, pathFcst, readWholeWindow=readWholeWindow, isStrict=False)
            if not tsmFcst:
                failPaths.append(pathFcst)
                continue
            tsmOut = cTsUtils.mergeAndRename(tsmObsv, tsmFcst, pathOut)
            #There may be a slight gap between the data--go ahead and fill in up to 4 holes
            tsmOut.estimateForMissingValues(4)
            #If the output timestep was specified in the pathname, convert the data
            if outEPart != "":
                tsmOut = cTsUtils.transformTSM(tsmOut, outEPart)
            logging.info("\tOutput:  %s" %tsmOut.getPath())
            dssOut.write(tsmOut)
        #Process any additional pathnames, if supplied (typically summary hydrographs)
        #Strip out the collection identifier if it exists
        dssPathFcst = DSSPathname(dssPathFcst.getPathname(True))
        fcstFPartOrig = dssPathFcst.getFPart()
        dssPathOut = DSSPathname(dssPathOut.getPathname(True))
        outFPartOrig = dssPathOut.getFPart()
        for suffixStr in extraSuffixList:
            #Extra data to process, set up the fcst and output pathnames
            if fcstFPartOrig == "":
                fcstFPart = suffixStr
            else:
                fcstFPart = "%s-%s" %(fcstFPartOrig, suffixStr)
            dssPathFcst.setFPart(fcstFPart)
            pathFcst = dssPathFcst.getPathname()
            tsmFcst = cDSS.readTSM(dssFcst, pathFcst, readWholeWindow=readWholeWindow, isStrict=False)
            if not tsmFcst:
                failPaths.append(pathFcst)
                continue
            if outFPartOrig == "":
                outFPart = suffixStr
            else:
                outFPart = "%s-%s" %(outFPartOrig, suffixStr)
            dssPathOut.setFPart(outFPart)
            pathOut = dssPathOut.getPathname()
            tsmOut = cTsUtils.mergeAndRename(tsmObsv, tsmFcst, pathOut)
            #If the output timestep was specified in the pathname, convert the data
            if outEPart != "":
                tsmOut = cTsUtils.transformTSM(tsmOut, outEPart)
            logging.info("\tOutput:  %s" %tsmOut.getPath())
            dssOut.write(tsmOut)
    if len(failPaths) > 0:
        logging.warning("Failed to extract the following paths:")
        for failPath in failPaths: logging.warning("\t%s" %failPath)
    dssObsv.close()
    dssFcst.close()
    dssOut.close()
    return True

def duplicatePathnames(inputDssFile, outDssFile, pathCSVFile=None, 
                      beginTimeStr=None, endTimeStr=None):
    """Duplicates a list of pathnames, renames them, and writes to an output dss file.
    The input .csv file provides the pathnames. Useful for bulk renaming.
    Currently used in the esp and dambreak data processing. Very similar to 
    :func:`mergePathnames`, it might be possible to combine the code here.
    
    :param str inputDssFile: The full path of the input dss file
    :param str outDssFile: The full path of the dss file for output
    :param str pathCSVFile: (Optional) The full path of the input csv file 
                            with a list of pathnames to process.
                            Should have headers of "inputPathname", "outputPathname".
                            If not supplied, all pathnames in the inputDssFile
                            will be duplicated with exactly the same pathname.
    :param str beginTimeStr: If supplied, the timewindow to extract the data. 
                             e.g. "02Jun1985 2400"
                             If not supplied, the entire timewindow will be done
    """
    logging.info("Duplicating pathnames")
    logging.info("extraction start date         %20s" % beginTimeStr)
    logging.info("extraction end date           %20s" % endTimeStr)
    logging.info("Input Dss File: %s" %inputDssFile)
    logging.info("Input pathname file: %s" %pathCSVFile)
    logging.info("Output Dss File: %s" %outDssFile)
    
    if beginTimeStr:
        #Time window specified, only use the time window
        readWholeWindow = False
        dssIn = cDSS.openDSSFile(inputDssFile, beginTimeStr, endTimeStr)
    else:
        #No time window specified
        readWholeWindow = True
        dssIn = HecDss.open(obsvDssFile)
    dssOut = HecDss.open(outDssFile)
    if pathCSVFile:
        lines = cFile.fileOpenReadClose(pathCSVFile)
        lines = cFile.stripOutCommentLines(lines)
        lineDicts = cFile.getCSVDictReader(lines)
        numLines = len(lines)
    else:
        #CSV not provided--use all pathnames in the file
        #Get all pathnames in the DSS file
        pathnames = cDSS.getAllPathnames(dssIn)
        #create a fake-out object that looks like what we'd get from a csv
        lineDicts = []
        for pathname in pathnames:
            lineDicts.append({"inputPathname":pathname, "outputPathname":pathname})
        numLines = len(pathnames)
    failPaths = [] #List of pathnames that failed to process
    for i, lineDict in enumerate(lineDicts): 
        logging.info("%s of %s" %(i+1, numLines-1))
        pathIn = lineDict["inputPathname"]
        logging.info("\tReading: %s" %pathIn)
        tsmIn = cDSS.readTSM(dssIn, pathIn, readWholeWindow=readWholeWindow, isStrict=False)
        if not tsmIn:
            failPaths.append(pathIn)
            continue
        pathOut = lineDict["outputPathname"]
        #Reset pathname and write it out
        tsmIn.setPathname(pathOut)
        logging.info("\tOutput:  %s" %tsmIn.getPath())
        dssOut.write(tsmIn)
    if len(failPaths) > 0:
        logging.warning("Failed to extract the following paths:")
        for failPath in failPaths: logging.warning("\t%s" %failPath)
    dssIn.close()
    dssOut.close()
    return True
    
def pushTSCsToCSV(tscList, outCSVPath):
    """
    Writes a bunch of Timeseries to a .csv file with a consistent format.
    TODO it might be nice to make this a class at some point.
    Assumes all time series have the same timestep and timewindow, and is geared
    toward daily data (14-period/monthly will work, but hourly won't work).
    If the timeseries don't have same timewindow, that's okay, 
    but missing values will be output (-901s).
    Will use the first time series mapped in as a template for which times to include.
    
    It has dates along the top, and each time series provided is a row.
    The output should look something like::
        
        SITE,PARAM,VERSION,UNITS,TYPE,11Jan2005,12Jan2006
        LIB,QR,OBSERVED-REV,CFS,PER-AVER,4000.23,4200.79
    
    :param list tscList: A list of TimeSeriesContainer objects to be written
    :param str outCSVPath: The filename of the output CSV file
    """
    #Define the headers first (each column is a date, each row is a location)
    outLines = []
    headerStr = "SITE,PARAM,VERSION,UNITS,TYPE"
    #Assume the first time series has the appropriate times defined
    templateTimes = tscList[0].times
    for time in templateTimes:
        hTime = HecTime(time, HecTime.MINUTE_INCREMENT)
        headerStr += ",%s" % hTime.date(4) #01Jan2005
    #Done with headers, move to the meat
    outLines.append(headerStr)
    for i, tsc in enumerate(tscList):
        dssPath = DSSPathname(tsc.fullName)
        bPart = dssPath.getBPart().upper()
        cPart = dssPath.getCPart().upper()
        fPart = dssPath.getFPart().upper()
        unitStr = tsc.units.upper()
        typeStr = tsc.type.upper()
        lineStr = "\n%s,%s,%s,%s,%s" %(bPart, cPart, fPart, unitStr, typeStr)
        #for val in tsc.values: doesn't work if timewindows aren't exactly aligned
        for templateTime in templateTimes:
            try :
                #times may not match up exactly--need to see if the time exists
                idx = tsc.times.index(templateTime) #gives ValueError if time not defined
                val = tsc.values[idx]
                if Math.abs(val - Constants.UNDEFINED_DOUBLE) <= 0.1 :
                    #If very close to undefined, set it to undefined
                    val = -901.
                elif val < -100000. :
                    val = -901.
            except ValueError:
                #Time did not exist in this timeseries
                val = -901.
            lineStr += ",%.2f" %val
        outLines.append(lineStr)
    cFile.writeTextToFile(outLines, outCSVPath)
    logging.info("Created .csv file at: %s" %outCSVPath)
    
def mergeTSCsToDSS(tscList, outDssFile, beginTimeStr, endTimeStr, useExistingData):
    """
    Takes the time series defined in tscList and pushes them to the output DSS file.
    Has the option of overwriting the old data or not. Currently used in the
    Observed Data Processing by RCC.
    
    :param list tscList: a list of TimeSeriesContainer to write
    :param str outDssFile: the output DSS file
    :param str beginTimeStr: the timewindow with which to open the dss file (e.g. "01Aug1988 2400")
    :param str endTimeStr: end of time window
    :param boolean useExistingData: If true, the existing data in the DSS file
                   with the same pathname will be given 1st priority and the data
                   in tscList will be merged with it. 
                   If false, the data in tscList will overwrite any existing data.
    :return list: a list of all the TimeSeriesContainer objects that were successful
    """
    logging.info("Merging TimeSeries into DSS file")
    logging.info("Time Window start date         %20s" % beginTimeStr)
    logging.info("Time Window end date           %20s" % endTimeStr)
    logging.info("Output Dss File: %s" %outDssFile)
    logging.info("Use Existing Data where available?: %s" %useExistingData)
    outDss = cDSS.openDSSFile(outDssFile, beginTimeStr, endTimeStr)
    failPaths = []
    outTSCs = []
    for tsc in tscList:
        outTSC = tsc
        outPath = outTSC.fullName
        logging.info("Merging pathname: %s" %outPath)
        if useExistingData:
            #Want to maintain the existing data (has data corrections already)
            # and simply add on the new data
            #Read the existing data (should have the same pathname)
            tsmExisting = cDSS.readTSM(outDss, outPath, readWholeWindow=False, isStrict=False)
            if tsmExisting is None:
                #Pathname doesn't exist in the file.
                msg = "Failed to read pathname: %s" %outPath
                logging.error(msg)
                failPaths.append(outPath)
                #Still want to write out the new, shiny pathname to the output DSS
                #continue
            else:
                #Since the existing data may have corrections already, it takes precedence over the new data
                tsmNew = TimeSeriesMath(outTSC)
                outTSM = cTsUtils.mergeAndRename(tsmExisting, tsmNew, outPath)
                outTSC = outTSM.getData()
        cDSS.writeTSC(outTSC, outDss)
        outTSCs.append(outTSC)
    outDss.close()
    if len(failPaths) > 0:
        msg = "Failed to find existing data in the DSS file for the following paths:"
        msg += "\nStill wrote the new data to DSS of these paths, but there was"
        msg += "\nnothing to merge it with:"
        logging.error(msg)
        for failPath in failPaths:
            logging.error("\t%s" %failPath)
    return outTSCs
    
def getTSCsfromCSV(csvFile):
    """
    Takes an input CSV file and converts all the data in it into multiple 
    TimeSeriesContainer objects. 
    It is imperative that the header names don't get changed--the script will
    look for information based on the header name.
    
    It is assumed that the CSV file is arranged as follows::
    
        SITE,PARAM,VERSION,UNITS,TYPE,30Sep2015 2400,01Oct2015 2400,02Oct2015 2400
        FSTB,QR,CFS,PER-AVER,OBSERVED-REV,3805,3671.25,3538.75
        LIB,HF,FT,INST-VAL,OBSERVED-REV,2440.17,2440.18,2440.2
    
    :param str csvFile: The full pathname of the CSV file to be processed
    :return: A list of TimeSeriesContainer objects (one for each row of data)
    """
    #Assume the first time is in the 6th row (index 5)
    startIndexOfData = 5
    logging.info("Input csv file: %s" %csvFile)
    lines = cFile.fileOpenReadClose(csvFile)
    csvDictReader = cFile.getCSVDictReader(lines)
    times = [] #list to store all times of the data
    outTSCs = [] #list to store output TimeSeriesContainer objects
    for i, lineDict in enumerate(csvDictReader): 
        logging.debug("%2.0f of %2.0f" %(i+1, len(lines)-1))
        if i == 0: 
            #first line of data, can use .fieldnames now
            #Detect the times and populate the times array
            fieldNames = csvDictReader.fieldnames #e.g. SITE,PARAM ...
            timeHeaders = fieldNames[startIndexOfData:] #e.g. 30Sep2015 2400,01Oct2015 2400
            for timeStr in timeHeaders:
                if timeStr == "": continue #sometimes blank stuff at the end of the csv
                hTime = HecTime(timeStr, HecTime.MINUTE_INCREMENT)
                times.append(hTime.value())
            #Detect the time interval from the difference of the first 2 times
            intMinutes = times[1] - times[0]
            ePart = cTsUtils.getDSSEPartFromIntervalInMinutes(intMinutes)
            startTime = HecTime(times[0], HecTime.MINUTE_INCREMENT) 
            endTime = HecTime(times[-1], HecTime.MINUTE_INCREMENT) 
            logging.info("Data start date: %s" %startTime.dateAndTime())
            logging.info("Data end date:   %s" %endTime.dateAndTime())
            logging.info("Data timestep:   %s" %ePart)
        #Done processing the headers, now the times are known
        #Process each row of data
        #Get the parameter outputs
        try:
            bPart = lineDict["SITE"]
            cPart = lineDict["PARAM"]
            fPart = lineDict["VERSION"]
            unitStr = lineDict["UNITS"]
            typeStr = lineDict["TYPE"]
        except KeyError, e:
            errMsg = "No column header in the CSV file named: '%s'" %e
            errMsg +="\nMake sure the columns are named exactly right"
            raise KeyError, errMsg
        logging.info("Reading %s,%s,%s,%s,%s" %(bPart,cPart,fPart,unitStr,typeStr))
        #Add the values to the list
        values = []
        for timeHeader in timeHeaders:
            if timeStr == "": continue #sometimes blank stuff at the end of the csv
            values.append(float(lineDict[timeHeader]))
        #Create the TimeSeriesContainer
        tsc = cTsUtils.prepareTSCont(values, times,
            bPart, cPart, ePart, fPart, unitStr, typeStr
            )
        outTSCs.append(tsc)
    return outTSCs
    
def DSSFileToCSV(inputDssFile, outCSVPath, beginTimeStr="01Jan1910 2400",
    endTimeStr="01Jan2050 2400"):
    """
    Write out an entire DSS file to a CSV file, with each record as a row and dates as columns.
    See :func:`pushTSCsToCSV` for more details--this script runs that function.
    Assumes all data is in the same timestep.
    Assumes the DSS file is not incredibly large--all time series data will be
    stored in local memory, which will not work for big DSS files.
    
    :param str inputDssFile: The full path of the input dss file
    :param str outCSVPath: The filename of the output CSV file
    :param str beginTimeStr: If supplied, the timewindow to extract the data. 
                             e.g. "02Jun1985 2400"
                             If not supplied, the entire timewindow will be done
    """
    
    inDss = cDSS.openDSSFile(inputDssFile, beginTimeStr, endTimeStr)
    #Get all pathnames in the DSS file
    pathnames = cDSS.getAllPathnames(inDss)
    #Read all pathnames in the DSS file
    tscList = []
    for i, pathname in enumerate(pathnames):
        logging.info("Reading %s of %s: %s" %(i+1,len(pathnames), pathname))
        #If a pathname can't be read, it must span a different time window
        tsm = cDSS.readTSM(inDss, pathname, isStrict=False)
        if tsm is None:
            continue
        tscList.append(tsm.getData())
    inDss.close()
    #Finished reading the data--now write it all out
    pushTSCsToCSV(tscList, outCSVPath)
    return True
    
def transformGageData(obsDssFile, outDssFile, csvFile, tsInt, startDateStr = "01Jan1910 2400", \
 endDateStr = "01Jan2050 2400", bar = None, txtArea = None):
    """
    This function performs tributary local flow calculations
    based on observed gage data only.
    It can handle area ratio and Move.1.
    If both Move.1 and area ratio are defined, it will do the Move.1, then apply the area ratio.
    It is not intended to be used to break apart existing local flows, but rather
    to manipulate gage data directly.
    To calculate local flows based on observed flows using a ResSim network, see the
    :any:`ResSimTasks` module.
    
    :param str obsDssFile: filename of dss file with observed data (CWMS and USGS)
    :param str outDssFile: output DSS file to write to
    :param str csvFile: csv file with instructions
    :param startDateStr: (string or HecTime) start time of transformation
    :param endDateStr: (string or HecTime) end time of transformation
    :param str tsInt: timeseries interval ("1HOUR" or "1DAY")
    :param JProgressBar bar: JProgressBar
    :param JTextArea txtArea: must have "printToGUI" method defined 
    """
    fPart = "COMPUTED" #alert todo!
    #Open up the instructions text file
    msg = "----------------------------------------------------------------------"
    msg += "\nTRANSFORMING TRIBUTARY FLOWS"
    msg += "\nInput File  : %s" %csvFile
    msg += "\nObserved DSS: %s" %outDssFile
    msg += "\nOutput DSS  : %s" %outDssFile
    msg += "\nStart Date  : %s" %startDateStr
    msg += "\nEnd Date    : %s" %endDateStr
    msg += "\nTime Step   : %s" %tsInt
    txtArea.printToGUI("Transforming Tributary flows...")
    logging.info(msg)
    sTime = HecTime(startDateStr)
    eTime = HecTime(endDateStr)
    obsDss = cDSS.openDSSFile(obsDssFile, sTime.toString(), eTime.toString())
    outDss = HecDss.open(outDssFile)
    msg = "Processing file: " + csvFile + "\n"
    logging.info(msg)
    lines = cFile.fileOpenReadClose(csvFile)
    lines = cFile.stripOutCommentLines(lines)
    failPaths = []
    prevTSM = None
    for i in range(len(lines)): 
        fields = lines[i].split(",")
        outBPart = fields[0].strip()
        outCPart = fields[1].strip()
        inputStation = fields[2].strip()
        #some values may not be defined--set to None
        try: areaRatio = float(fields[3].strip())
        except ValueError: areaRatio = None
        ''' old way of doing it-still accurate, but eqns come in different format now 2/9/2015
        try:
            yBarMove1 = float(fields[4].strip())
            xBarMove1 = float(fields[5].strip())
            slopeMove1 = float(fields[6].strip())
        except ValueError:
            yBarMove1 = None
            xBarMove1 = None
            slopeMove1 = None
        '''
        try:
            aMove1 = float(fields[4].strip())
            bMove1 = float(fields[5].strip())
        except ValueError:
            aMove1 = None
            bMove1 = None
        try: bcfMove1 = float(fields[6].strip()) #optional parameter
        except: bcfMove1 = None
        bar.setValue(int(float(i)/len(lines)*100))
        msg = "Processing: %s" %outBPart
        logging.info(msg)
        txtArea.printToGUI(msg)
        newTSM = None
        #Read in the input station time series
        obsTSM = cDSS.readTSMfromPathnameParts(obsDss, bPart=inputStation, cPart="*FLOW*", ePart=tsInt)
        if obsTSM is None: #it failed
            failPaths.append(inputStation)
            continue
        # Now manipulate the data (if both Move.1 and area ratio defined, do Move.1 first)
        if aMove1:
            #Move1 is defined
            tsc = obsTSM.getData()
            tscNew = cTsUtils.move1TransformEqn2(tsc, aMove1, bMove1, bcfMove1)
            if tscNew is None:
                errMsg = "Failed to perform MOVE.1 transformation...\nSee console log for details"
                logging.error(errMsg)
                txtArea.printToGUI(errMsg)
                return None
            newTSM = TimeSeriesMath(tscNew)
        if areaRatio:
            #areaRatio is defined
            logging.info("\tArea Ratio: %s" %areaRatio)
            if newTSM: #MOVE.1 already applied
                newTSM = newTSM.multiply(areaRatio)
            else: #regular area ratio, not on top of MOVE.1
                newTSM = obsTSM.multiply(areaRatio)
        if (not aMove1) and (not areaRatio):
            logging.warning("\tNo transformation defined!")
            newTSM = obsTSM

        if prevTSM:
            # The previous step was an intermediate calculation--incorporate it
            newTSM = newTSM.add(prevTSM)
                    
        if outBPart.upper() == "ADD":
            # Don't write out the times series yet--save for later
            prevTSM = newTSM
            continue
        else: prevTSM = None
        # Set up the output timeseries pathname and write it out
        outputPath = "//%s/%s//%s/%s/" %(outBPart, outCPart, tsInt, fPart)
        newTSM.setPathname(outputPath)
        outDss.write(newTSM) 
        msg = "\tOutput path: %s" %outputPath
        logging.info(msg)

    msg = "\nDONE TRANSFORMING TRIBUTARY LOCALS!"
    obsDss.close()
    outDss.close()
    logging.info(msg)
    txtArea.printToGUI(msg)
    bar.setValue(100)
    if len(failPaths) > 0:
        msg = "\nFailed to calculate the following paths:"
        for failPath in failPaths: msg += "\n\t%s" %failPath
        logging.warning(msg)
        txtArea.printToGUI(msg)
    return None 
    
def disaggregateLocals(network, outDssFile, csvFile, tsInt, startDateStr = "01Jan1910 2400", \
 endDateStr = "01Jan2050 2400",bar = None, txtArea = None):
    """
    This function performs disaggregated local flow calculations.
    Based on previously calculated local flows.
    It can handle area ratio and Move.1.
    It is not intended to be used to break apart existing local flows, but rather
    to manipulate gage data directly.
    To calculate local flows based on observed flows using a ResSim network, see the
    :any:`ResSimTasks` module.
    
    :param RssSystem network: The currently opened ResSim network (for routing)
    :param str outDssFile: output DSS file to write to
    :param str csvFile: csv file with instructions
    :param startDateStr: (string or HecTime) start time of transformation
    :param endDateStr: (string or HecTime) end time of transformation
    :param str tsInt: timeseries interval ("1HOUR" or "1DAY")
    :param JProgressBar bar: JProgressBar
    :param JTextArea txtArea: must have "printToGUI" method defined 
    """
    fPart = "COMPUTED" #alert todo!
    #Open up the instructions text file
    msg = "----------------------------------------------------------------------"
    msg += "\nCALCULATING DISAGGREGATED TRIBUTARY FLOWS"
    msg += "\nInput File  : %s" %csvFile
    msg += "\nOutput DSS  : %s" %outDssFile
    msg += "\nStart Date  : %s" %startDateStr
    msg += "\nEnd Date    : %s" %endDateStr
    msg += "\nTime Step   : %s" %tsInt
    txtArea.printToGUI("Calculating Disaggregated Tributary flows...")
    logging.info(msg)
    sTime = HecTime(startDateStr)
    eTime = HecTime(endDateStr)
    outDss = HecDss.open(outDssFile)
    msg = "Processing file: " + csvFile + "\n"
    logging.info(msg)
    lines = cFile.fileOpenReadClose(csvFile)
    lines = cFile.stripOutCommentLines(lines)
    #Open up all input DSS Files first--create a dictionary of opened DSS Files
    dssDict = {}
    for i in range(len(lines)):
        fields = lines[i].split(",")
        dssFile = fields[1].strip().upper()
        if dssFile != "" and dssFile not in dssDict.keys():
            #Open the file and add it to the dictionary
            #Assume the input and output files are based from the same directory
            dssDir = os.path.dirname(outDssFile)
            fullDssFile = os.path.join(dssDir, dssFile)
            #fullDssFile = ClientApp.Workspace().makeAbsolutePath("shared/%s" %dssFile)
            logging.info("Opening Dss File: %s" %fullDssFile)
            #openedDssFile = HecDss.open(fullDssFile)
            openedDssFile = cDSS.openDSSFile(fullDssFile, sTime.toString(), eTime.toString())
            dssDict[dssFile] = openedDssFile

    #OK, now actually process the csv file
    currentTSM = None
    for i in range(len(lines)): 
        fields = lines[i].split(",")
        command = fields[0].strip().upper() 
        dssFileName = fields[1].strip().upper()
        bPart = fields[2].strip()
        cPart = fields[3].strip()
        constant = fields[4].strip()
        us_JuncName = fields[5].strip()
        ds_JuncName = fields[6].strip() 
        try:
            yBarMove1 = float(fields[7].strip())
            xBarMove1 = float(fields[8].strip())
            slopeMove1 = float(fields[9].strip())
        except ValueError:
            yBarMove1 = None
            xBarMove1 = None
            slopeMove1 = None
        #some values may not be defined--set to None
        try: constant = float(constant)
        except ValueError: constant = None
        bar.setValue(int(float(i)/len(lines)*100))
        msg = "Processing: %s" %fields
        logging.info(msg)
        txtArea.printToGUI(msg)
        #If an input flow is defined, get it
        inputTSM = None
        if dssFileName != "":
            # It should be in the dssFile dictionary
            try: dssFile = dssDict[dssFileName]
            except KeyError:
                errMsg = "ERROR! This dss file has not been opened!"
                logging.error(errMsg)
                return None
            #Read in the input time series
            inputTSM = cDSS.readTSMfromPathnameParts(dssFile, bPart, cPart, ePart=tsInt)
            if inputTSM is None: #it failed
                errMsg = "ERROR: Failed on the following line:\n%s" %lines[i]
                errMsg += "Could not read any pathnames with:\n\tBPart=%s\n\tCPart=%s" %(bPart, cPart)
                errMsg += "\nFrom DSS File: %s" %dssFile.getDataManager().DSSFileName()
                logging.error(errMsg)
                txtArea.printToGUI(errMsg)
                return None
        #See what the command is
        if command == "START":
            if dssFileName == "":
                errMsg = "ERROR: A DSS file must be specified on any 'START' line"
                errMsg += "\nFailed on the following line:\n%s" %lines[i]
                logging.error(errMsg)
                txtArea.printToGUI(errMsg)
                return None
            currentTSM = inputTSM
        elif command == "ADD": #Add a timeseries
            if inputTSM == None: #must be a constant defined
                if constant == None:
                    errMsg = "ERROR: Need to specify either a constant value or a Dss File"
                    logging.error(errMsg)
                    txtArea.printToGUI(errMsg)
                    return None
                currentTSM = currentTSM.add(constant)
            else: #Time Series
                currentTSM = currentTSM.add(inputTSM)
        elif command == "SUBTRACT": #Subtract a timeseries
            if inputTSM == None: #must be a constant defined
                if constant == None:
                    errMsg = "ERROR: Need to specify either a constant value or a Dss File"
                    logging.error(errMsg)
                    txtArea.printToGUI(errMsg)
                    return None
                currentTSM = currentTSM.subtract(constant)
            else: #Time Series
                currentTSM = currentTSM.subtract(inputTSM)
        elif command == "MULTIPLY": #Multiply by a constant
            currentTSM = currentTSM.multiply(constant)
        elif command == "FLOOR": #cap to a minimum amount
            currentTSM = currentTSM.screenWithMaxMin(constant, 999999999, 999999999, True, constant, None)
        elif command == "CEILING": #cap to a maximum amount
            currentTSM = currentTSM.screenWithMaxMin(-999999999, constant, 999999999, True, constant, None)
        elif command == "SHIFTHRS": #shift data by specified number of hours
            currentTSM = currentTSM.shiftInTime(int(constant*60)) #function works in minutes
        elif command == "INDEX": #index the time series to the pattern in another timeseries
            currentTSM = TimeSeriesMath(cTsUtils.flowIndex(currentTSM.getData(), inputTSM.getData(), -901, -901))
        elif command == "MOVE1": #do a Move.1 transformation
            tsc = currentTSM.getData()
            tscNew = cTsUtils.move1Transform(tsc, yBarMove1, xBarMove1, slopeMove1, True)
            if tscNew is None:
                errMsg = "Failed to perform MOVE.1 transformation...\nSee console log for details"
                logging.error(errMsg)
                txtArea.printToGUI(errMsg)
                return None
            currentTSM = TimeSeriesMath(tscNew) 
        elif command == "ROUTE": #Route the timeseries using the ResSim parameters
            tsc = cResSim.routeDirectTSC(network, currentTSM.getData(), us_JuncName, ds_JuncName)
            if tsc is None:
                errMsg = "Failed to route flows from: %s to: %s" %(us_JuncName, ds_JuncName)
                errMsg += "\nSee the log file for more details"
                logging.error(errMsg)
                txtArea.printToGUI(errMsg)
                return None
            currentTSM = TimeSeriesMath(tsc)
        elif command == "WRITE": #Write out the timeseries
            # Set up the output timeseries pathname and write it out
            outputPath = "//%s/%s//%s/%s/" %(bPart, cPart, tsInt, fPart)
            currentTSM.setPathname(outputPath)
            outDss.write(currentTSM) 
            msg = "\tOutput path: %s" %outputPath
            logging.info(msg)           
            currentTSM = None
        else:
            errMsg = "Invalid Command: %s" %command
            logging.error(errMsg)
            txtArea.printToGUI(errMsg)
            return None
            
    #Close all DSS Files
    outDss.close()
    for dssFile in dssDict.values(): dssFile.close()
    #Print out final messages
    msg = "\nDONE CALCULATING DISAGGREGATED TRIBUTARY LOCALS!"
    logging.info(msg)
    txtArea.printToGUI(msg)
    bar.setValue(100)
    return None

def flowIndexing(inDssFile, outDssFile, csvFile, tsInt, startDateStr = "01Jan1910 2400", \
 endDateStr = "01Jan2050 2400", bar = None, txtArea = None):
    """
    This function performs flow indexing.
    Sometimes, calculated local flows can have large unrealistic swings.
    This function smooths out this data by applying the pattern of another 
    nearby gage with higher quality data.
    This may mess up the timing a bit, but the resulting flow will look much smoother.
    It smooths the data on tha monthly basis. 
    It calls the function :any:`cTsUtils.flowIndex` function for each row in the CSV.
    
    The CSV file must be formatted as follows::
    
        BPART_FLOW, CPART_FLOW, FPART_FLOW, BPART_INDEX, CPART_INDEX, FPART_INDEX, START_EXCLUSION_MONTH, END_EXCLUSION_MONTH, FPART_OUT
        LIB, FLOW-IN, WATERBALANCE, FSTB, FLOW, OBSERVED-REV, 4, 7, WATERBALANCE-INDEXED
    
    The first 3 columns specify the pathname of the data that may have the screwy shape, but the correct volume.
    The second 3 columns specify the pathname of the flow to be used for indexing.
    Sometimes there are periods of time that we want to use the raw data and
    not the calculated data--this is specified in the next 2 columns.
    It is assumed that the A-part of all DSS pathnames is blank.
    
    :param str inDssFile: filename of dss file with input data to read
    :param str outDssFile: output DSS file to write to
    :param str csvFile: csv file with instructions (see above format)
    :param startDateStr: (string or HecTime) start time of analysis.
                        Best to be at the start of a month, since indexing works monthly
    :param endDateStr: (string or HecTime) end time of analysis.
    :param str tsInt: timeseries interval ("1HOUR" or "1DAY")
    :param JProgressBar bar: JProgressBar
    :param JTextArea txtArea: must have "printToGUI" method defined 
    """
    #Open up the instructions text file
    msg = "----------------------------------------------------------------------"
    msg += "\nPERFORMING FLOW INDEXING"
    msg += "\nInput File  : %s" %csvFile
    msg += "\nInput DSS   : %s" %inDssFile
    msg += "\nOutput DSS  : %s" %outDssFile
    msg += "\nStart Date  : %s" %startDateStr
    msg += "\nEnd Date    : %s" %endDateStr
    msg += "\nTime Step   : %s" %tsInt
    txtArea.printToGUI("FLOW INDEXING...")
    logging.info(msg)
    sTime = HecTime(startDateStr)
    eTime = HecTime(endDateStr)
    inDss = cDSS.openDSSFile(inDssFile, sTime.toString(), eTime.toString())
    outDss = HecDss.open(outDssFile)
    msg = "Processing file: " + csvFile + "\n"
    logging.info(msg)
    lines = cFile.fileOpenReadClose(csvFile)
    lines = cFile.stripOutCommentLines(lines)
    csvReader = cFile.getCSVReader(lines)
    failPaths = []
    for i, fields in enumerate(csvReader): 
        if i == 0: continue #first row is headers
        if len(fields) < 7: 
            errMsg = "The input CSV has less than 7 fields defined"
            logging.error(errMsg)
            raise AssertionError, errMsg
        inBPart = fields[0].strip()
        inCPart = fields[1].strip()
        inFPart = fields[2].strip()
        indexBPart = fields[3].strip()
        indexCPart = fields[4].strip()
        indexFPart = fields[5].strip()
        #some values may not be defined--set to default if blank
        try:
            startExclusionMonth = int(fields[6].strip())
            endExclusionMonth = int(fields[7].strip())
        except ValueError:
            startExclusionMonth = 0
            endExclusionMonth = 0
        outFPart = fields[8].strip()
        #Build the input/output pathnames
        inPathname = cDSS.buildDSSPathFromPartList(["",inBPart,inCPart,"",tsInt,inFPart])
        indexPathname = cDSS.buildDSSPathFromPartList(["",indexBPart,indexCPart,"",tsInt,indexFPart])
        msg = "\nProcessing: %s of %s" %(i, len(lines)-1)
        msg += "\nFlow pathname : %s" %inPathname
        msg += "\nIndex pathname: %s" %indexPathname
        msg += "\nStart, End Exclusion Months: %s, %s" %(startExclusionMonth, endExclusionMonth)
        logging.info(msg)
        txtArea.printToGUI(msg)
        #Read in the input time series
        inTSM = cDSS.readTSM(inDss, inPathname, isStrict=False)
        indexTSM = cDSS.readTSM(inDss, indexPathname, isStrict=False)
        if inTSM is None: #it failed
            failPaths.append(inPathname)
            continue
        if indexTSM is None:
            failPaths.append(indexPathname)
            continue
        #Perform the flow indexing
        newTSC = cTsUtils.flowIndex(inTSM.getData(), indexTSM.getData(), startExclusionMonth, endExclusionMonth)
        # Set up the output timeseries pathname and write it out
        outputPath = "//%s/%s//%s/%s/" %(inBPart, inCPart, tsInt, outFPart)
        newTSC.fullName = outputPath
        cDSS.writeTSC(newTSC, outDss)
        msg = "\tOutput path: %s" %outputPath
        logging.info(msg)
        txtArea.printToGUI(msg)
        bar.setValue(int(float(i)/len(lines)*100))
    msg = "\nDONE FLOW INDEXING!"
    inDss.close()
    outDss.close()
    logging.info(msg)
    txtArea.printToGUI(msg)
    bar.setValue(100)
    if len(failPaths) > 0:
        msg = "\nFailed to read the following paths:"
        for failPath in failPaths: msg += "\n\t%s" %failPath
        logging.warning(msg)
        txtArea.printToGUI(msg)
    return True 