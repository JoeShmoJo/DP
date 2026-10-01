"""
Contains code dealing with reading/writing to DSS Files.  
This module doesn't cover much manipulation of timeseries objects themselves, 
and is more concerned with the reading/writing processes of DSS. 
The :any:`cTsUtils` module has more information on manipulating timeseries data.
For details on how to properly open a DSS file, see :func:`openDSSFile`.
Please close any DSS files you open after you're done via the .close() method.
For higher level functionality thats use the functions defined here to do a
complete process, see the :any:`DSSTasks` module.
Note that the maximum number of curves allowed in a PairedDataContainer is 50.
"""
from hec.hecmath import DSS
from hec.hecmath import DSSFile
from hec.hecmath import DSSFileException
from hec.hecmath import HecMathException
from hec.hecmath import TimeSeriesMath
from hec.hecmath import TextMath
from hec.heclib.util import HecTime
from hec.lang import DSSPathString
from hec.io import TimeSeriesContainer
from hec.io import PairedDataContainer
from hec.io import TextContainer
from hec.model import PairedValuesExt
from hec.heclib.dss import HecDss
from hec.heclib.dss import HecDataManager
from hec.heclib.util import Heclib
from hec.dssgui import HecDssVue
from java.lang import UnsupportedOperationException

import logging

from NWDJyLib import cFile
from NWDJyLib import cTimes
from NWDJyLib.DSS import cTsUtils
################################################################################
# STATIC INPUT
MAX_CURVES_ALLOWED = 50 #PairedDataContainer can't have more curves than this
################################################################################
# CLASS DEFINITIONS

# END OF CLASS DEFINITIONS
################################################################################
# MIGRATED FUNCTIONS (IF MOVED TO ANOTHER MODULE, FOR BACKWARD COMPATIBILITY)
# theOldFunctionThatWasHere = newModule.theReplacementFunction

################################################################################
# FUNCTION DEFINITIONS
def openDSSFile(dssFileStr, startTime=None, endTime=None, timeWindowStr=None):
    """
    There are many ways to open a DSS file, and this function does it the 'right' way.
    For details on reading records after opening the file, see :func:`readTSM`.
    
    It is critical to understand that a DSSFile can be opened with or without 
    a time window defined. If the time window is defined when opening the file,
    all successive read/writes will be subject to this time window. 
    
    When opening with a time window, both date and time 
    must be specified. If time is omitted, any .read statements will fail 
    mysteriously without a good error message::
    
        #Here is one way to open a DSS file with a time window:
        HecDss.open(dssFileStr, startTimeStr, endTimeStr)
        #startTimeStr must be like "29Sep1995 2400"
        #Or you can use this approach to open the file with a timewindow:
        HecDss.open(dssFileStr, timeWindowStr)
        #timeWindowStr like "29Sep1995 2400 30Sep1996 2400"
    
    While it is possible to specify a time window with each read/write statement,
    such an approach is less preferred since the time window is usually consistent.
    
    In newer builds of HEC software, and all versions of DSS-VUE, the preferred method
    of opening a DSS file is as follows::
    
        HecDSS.open(dssFileStr) #or use a timeWindow if desired
    
    Some prior installations of ResSim 3.1 and prior do not have access to the 
    HecDss class, so they had to use the following code::
    
        DSS.open(dssFileStr, network.getRssRun().getRunTimeWindow().getTimeWindowString())
        
    This approach returns a pure DSSFile object, which is a bit more limited.
    DSSFile objects do not have the full functionality of HecDss, and cannot use .put
    or .get commands to read/write TimeSeriesContainer objects directly.
    
    :param str dssFileStr: The full pathname to the DSS File
    :param startTime: If supplied, the start time of the time window. Can be a
                      HecTime object or just a string (e.g. 01Aug1996). If time
                      is not included, that's okay--this function will assume you 
                      want the entire day.
    :param endTime: End time of time window. Must be supplied if startTime is supplied.
    :param timeWindowStr: If supplied, the full time window string to open the file.
                          Yes, it must have dates and times defined. If supplied,
                          startTime and endTime parameters should not be provided.
                          e.g. "29Sep1995 2400 30Sep1996 2400"
    """
    if timeWindowStr: 
        #full time window defined
        dssFile = HecDss.open(dssFileStr, timeWindowStr)
    if startTime: 
        #start and end times defined--open with a time window
        startTimeStr = cTimes.getStandardTimeStr(startTime, endOfDay=False) #e.g. "01Aug1996 2400"
        endTimeStr = cTimes.getStandardTimeStr(endTime, endOfDay=True)
        strTimeWindow = "%s %s" %(startTimeStr, endTimeStr)
        dssFile = HecDss.open(dssFileStr, strTimeWindow)
    else:
        dssFile = HecDss.open(dssFileStr)
    return dssFile

def suppressDSSPrintStatements():
    """
    When Jython is used to run a script, the default is for DSS to print out
    messages for everything it is doing (e.g. ZREAD or ZWRITE). This method will suppress these print
    statements, which makes the console look much cleaner. Invoke this method
    once in your script before doing anything with DSS. This is not necessary
    for scripts run in a ResSim simulation, as this setting is already set by ResSim.
    """
    Heclib.zset("MLVL", " ", 0)
    
def buildDSSPathFromPartList(listParts):
    """
    Return a DSS uppercase pathname string from a list with the desired parts.
    e.g. "//LIBBY/FLOW//1DAY/TESTING/"
    
    :param list listParts: list of strings of length 6 (raises error if not)
    """
    if len(listParts) != 6:
        errMsg = "ERROR! Trying to build a DSS path string but there are more than 6 parts"
        errMsg += "\n%s" %listParts
        raise AssertionError, errMsg
    dssPath = "/"
    for part in listParts:
        dssPath += part.strip().upper() + "/"
    return dssPath
    
def readPairedDataFromDSS(pathString, dssFile, isStrict=True):
    """
    Reads a paired data record from a dss file and saves it as a PairedValuesExt object
    
    :param str pathString: dss pathname to read
    :param dssFile: already opened Dss file (HecDss or DSSFile)
    :param boolean isStrict: If True, an error will be thrown if the path doesn't exist.
                 If False, None will be returned if it doesn't exist
    :return PairedValuesExt pv: An object with interpolation functionality
    """
    try:
        pairedDataMathObj = dssFile.read(pathString)
    except (DSSFileException, HecMathException, UnsupportedOperationException): 
        #couldn't find the DSS path
        if isStrict:
            errMsg =  "ERROR IN READING DATA: COULD NOT READ PATHNAME:"
            errMsg += "\n%s\nFROM DSS FILE: %s\n" %(pathString, dssFile.getFilename())
            raise AssertionError, errMsg
        else:
            return None
    pairedDataContainer = pairedDataMathObj.getData()
    pairedValuesExtObj = PairedValuesExt()
    pairedValuesExtObj.setData(pairedDataContainer)
    return pairedValuesExtObj
    
def readTSM(dssFile, pathname, readWholeWindow=False, isStrict=True):
    """
    Retrieve a time series from DSS file, assuming the pathname is known. 
    This is the most generalized "read" function, and is fairly all-purpose.
    
    :param dssFile: DSSFile or HecDss object. Already opened Dss File 
                   (may have been opened with a time window)
    :param str pathname: The dss pathname to read (e.g. "//Libby/Flow-In//1DAY/TEST/"). 
                The D-part will be ignored, unless readWholeWindow=False 
                and the dssFile was opened without a timewindow. 
    :param boolean readWholeWindow: If True, the whole timewindow existing in 
                the DSS file will be read.
                If False, the dssFile must have been opened with a time window
                (see :func:`openDSSFile`), or the pathname has a well-defined 
                d-part already (e.g. "01Jan1990").
    :param boolean isStrict: If True, an error will be thrown if the path doesn't exist.
                 If False, None will be returned if it doesn't exist
    :return tsm TimeSeriesMath: The read timeseries 
                            (or None if isStrict=True and pathname doesn't exist)
    """
    tsm = None #if it stays None at the end of the script, the retrieval failed
    if readWholeWindow:
        #get the whole time window
        if isinstance(dssFile, HecDss):
            #Only HecDss objects can use .get()
            tsc = dssFile.get(pathname.upper(), 1) #.get requires all uppercase path
            if not tsc:
                tsm = None
            else:
                tsm = TimeSeriesMath(tsc)
        else: 
            #must be a DSSFile, have to do it the hard way
            #If using DSSFile, it's best practice to open the DSS file itself with a timewindow
            #rather than doing it this way
            try: 
                tsm = dssFile.read(pathname, "01JAN1901", "01JAN3001")
            except (HecMathException, DSSFileException, UnsupportedOperationException), e:
                tsm = None
    else:
        #assumes the dssFile has been opened for a time window
        #or the pathnname has a true D-part (e.g. "01Jan2004", not "01JAN1922 - 01JAN2015")
        try: 
            tsm = dssFile.read(pathname)
        except (HecMathException, DSSFileException, UnsupportedOperationException), e:
            tsm = None
    #Raise any errors or warning messages if the read failed
    if tsm is None:
        if isStrict:
            errMsg =  "ERROR IN READING DATA: COULD NOT READ PATHNAME:"
            errMsg += "\n%s\nFROM DSS FILE: %s\n" %(pathname, dssFile.getFilename())
            logging.error(errMsg)
            raise AssertionError, errMsg
        else:
            logging.warning("\tFailed to read: %s" %pathname)
    return tsm
    
def readTSMfromPathnameParts(dssFile, bPart, cPart, ePart="*", fPart="*", readWholeWindow=False):
    """
    Retrieve a DSS time series from just specifying a few pathname parts.
    It scans the DSS file to see if there are any matching.
    It retrieves the entire time window for which it is defined.
    Caution should be used with this, as if there are duplicate pathnames with different
    fParts, there's no way to tell which one this function will retrieve unless you specify it.
    And it's fairly computationally intensives since it has to search the DSS file.
    
    :param dssFile: DSSFile or HecDss. Already opened Dss File 
    :param str bPart: The bPart to match up
    :param str cPart: The cPart to match up
    :param str ePart: The ePart to match up (defaults to any ePart)
    :param str fPart: The fPart to match up (defaults to any fPart)
    :param boolean readWholeWindow: If True, the whole timewindow will be read.
                                    If False, the dssFile must be open with a time window.
    :return TimeSeriesMath tsm: The read timeseries.
                            Returns None if no time series could be found
    """
    #first, check to see it actually exists+
    scanString = "B=%s C=%s E=%s F=%s" %(bPart, cPart, ePart, fPart)
    returnedPaths = dssFile.getCatalogedPathnames(scanString)
    if len(returnedPaths) == 0:
        logging.warning("\tFailed to find any pathnames with BPart of: %s and CPart of: %s" %(bPart,cPart))
        logging.warning("\tAttempting to find 1HOUR data...")
        scanString = "B=%s C=%s E=%s" %(bPart, cPart, "1HOUR")
        returnedPaths = dssFile.getCatalogedPathnames(scanString)
        if len(returnedPaths) == 0:
            logging.warning("\tFailed. Attempting to find 1DAY data...")
            scanString = "B=%s C=%s E=%s" %(bPart, cPart, "1DAY")
            returnedPaths = dssFile.getCatalogedPathnames(scanString)
            if len(returnedPaths) == 0:
                logging.warning("\tCouldn't find any matching data...")
                return None
    #Okay, we have a path, but there are likely are multiple of them because
    #DSS splits up the time window
    pathStringObj = DSSPathString(returnedPaths[0])
    pathStringObj.setDPart("") #clear out the time window
    path = pathStringObj.getPathname()
    logging.info("\tReading: %s" %path)
    tsm = readTSM(dssFile, path, readWholeWindow=readWholeWindow, isStrict=False)
    if not tsm:
        return None
    #Might not have retrieved the proper time interval--convert if necessary
    if ePart != "*": tsm = cTsUtils.transformTSM(tsm, ePart)
    return tsm
    
def readEOMFcstAndInterpolateToDaily(dssFileObj, dssPathname, network=None):
    """
    Returns a TimeSeriesMath object that has been interpolated to daily.
    Assumes that the forecasts are defined at least at end of month .
    EOM stands for end of month.
    Can handle irregular or regular data.
    
    :param DSSFile dssFileObj: already opened dss file (with a time window)
    :param str dssPathname: pathname to read
    """
    try:
        TSContain = dssFileObj.read(dssPathname).getContainer() 
    except HecMathException, e:
        if not network is None:
            network.printErrorMessage("%s: %s in %s" % (e.message, dssPathname, dssFileObj))
        raise e
    TSMathNew = TimeSeriesMath(TSContain)             
    # Tranform into a daily data set
    TSMathNew = TSMathNew.interpolateDataAtRegularInterval("1DAY", "0MINUTES")
    # Set the type and units of the forecast
    TSMathNew.setParameterPart("VOLUME")
    TSMathNew.setUnits("kaf")
    TSMathNew.setType("PER-AVER") 
    return TSMathNew

def readBOMFcstAndInterpolateToDaily(dssFileObj, dssPathname):
    """
    Returns a TimeSeriesMath object that has been interpolated to daily.
    Assumes that the forecasts are defined at 0001 hours at the beginning of the month.
    to which they apply (this was the case for IR-DECADE fcsts for a while).
    BOM stands for Beginning of month.
    Can handle irregular or regular data.
    
    :param DSSFile dssFileObj: already opened dss file (with a time window)
    :param str dssPathname: pathname to read
    """
    TSContain = dssFileObj.read(dssPathname).getContainer() 
    timeCopy = list(TSContain.times)
    for i in range(len(TSContain.times)-1):
        TSContain.times[i] = timeCopy[i+1]-1 # subtract a minute from the next defined time 
    TSMathNew = TimeSeriesMath(TSContain)    
    # Tranform into a daily data set
    TSMathNew = TSMathNew.interpolateDataAtRegularInterval("1DAY", "0MINUTES")
    # Set the type and units
    TSMathNew.setParameterPart("VOLUME")
    TSMathNew.setUnits("kaf")
    TSMathNew.setType("PER-AVER")   
    return TSMathNew
    
def writeTSFromParts(dssFile, vals, tims, bpart, cpart, epart, fpart, unitStr, typeStr):
    """
    DEPRECATED--NO FUNCTIONS/MODULES USE THIS ANYMORE. USE cTsUtils.prepareTSCont
    and writeTSC instead.
    Simple procedure to write data to a DSS file
    
    :param dssFile: the already opened Dss file (DSSFile or HecDSS)
    :param vals: list of values to stor
    :param tims: list of times to stor
    
    The rest of the parameters are strings that specify the output time series
    """
    tsc = cTsUtils.prepareTSCont(vals, tims, bpart, cpart, epart, fpart, unitStr, typeStr)
    dssFile.put(tsc)
    return tsc

def writeTSC(tsc, dssFile, dssPath=None, unitStr=None, typeStr=None, storedAsdoubles=False):
    """
    Writes out a time series container with predefined pathname to dss
    
    :param TimeSeriesContainer tsc: Time series to write
    :param dssFile: the already opened Dss file (DSSFile or HecDSS)
    :param str dssPath: The pathname for the output data (assumed already well defined)
                        If not supplied, the pathname embedded in tsc will be used (.fullName)
    :param str unitStr: If supplied, will override the .units in tsc (e.g. "ft")
    :param str typeStr: If supplied, will override the .type in tsc (e.g. "PER-AVER")
    :param bool storedAsdoubles: If true, store with double precision
    :param TimeSeriesContainer tsc: The output TSC that was written
    """
    #Make sure the input TSC is well defined first
    tsc = tsc.clone()
    tsc.startTime = tsc.times[0]
    tsc.endTime = tsc.times[-1]
    tsc.numberValues = len(tsc.times)
    tsc.fileName = "" #must get rid of the filename that is attached to the TSC
    tsc.storedAsdoubles = storedAsdoubles
    #Create the output TimeSeriesMath and write it out
    tsm = TimeSeriesMath()
    tsm.setData(tsc)
    if dssPath:
        tsm.setPathname(dssPath)
        dssPathS = DSSPathString(dssPath)
        tsm.setWatershed(dssPathS.getAPart())
        tsm.setLocation(dssPathS.getBPart())
        tsm.setParameterPart(dssPathS.getCPart())
        tsm.setVersion(dssPathS.getFPart())
    else:
        tsm.setPathname(tsc.fullName)
    if unitStr: #optional parameter
        tsm.setUnits(unitStr)
    if typeStr: #optional parameter
        tsm.setType(typeStr)
    dssFile.write(tsm)
    return tsm.getData()

def writeTextToDss(dss, path, msg):
    """
    Routine to write text to an already opened DSS file
    
    :param dss: Already open DSSFile
    :param str path: output pathname
    :param str msg: the output message to store
    """
    txc = TextContainer()
    txc.text = msg
    txc.fullName = path
    tm = TextMath()
    tm.setData(txc)
    dss.write(tm)
    return True
    
def getAllPathnames(dssFile):
    """
    Returns a list of all pathnames (string) in a file (similar to what you see in the
    'condensed catalog' view). This is nice because only one pathname is spit out
    for each unique record (not multiple returns just because the date range differs).
    The D-part (date range) for all pathnames is wiped out.
    Forces a recatalog and is fairly intensive, so might take a while for large DSS files.
    
    :param dssFile: the already opened Dss file (DSSFile or HecDSS)
    :return: list of strings, one for each pathname (e.g. "//MICA/FLOW//1DAY/TEST/")
    """
    #Force recatalog
    catalog = dssFile.getCatalogedPathnames("*",1)
    #Get all pathnames
    condensedCat = dssFile.getCondensedCatalog()
    #Read all pathnames in the DSS file
    pathnames = []
    for i, cRef in enumerate(condensedCat):
        #Each pathname contains a date range--wipe it out
        dssPath = DSSPathString(cRef.getNominalPathname())
        dssPath.setDPart("")
        pathname = dssPath.getPathname()
        pathnames.append(pathname)
    return pathnames
    
def getTimeBounds(dssFile, pathname=None):
    """
    Returns the starting and ending times of data in the dss file. Typically
    appropriate for use when nearly all timeseries in a DSS file have the same
    time window.
    
    :param HecDss dssFile: the already opened DSS file (typically without a time window)
    :param str pathname: (Optional) If supplied, this pathname will be used to
           check the time window of data (less computationally intensive). 
           If not supplied, then the first pathname in the DSS file will be used
           to check the timewindow (more computationally intensive due to recatalog). 
    :return: Two return values, both are HecTime. 
             First is the beginning time, second is the ending time of data
             If there are no pathnames in the DSS file or the pathname couldn't 
             be located, return None, None
    """
    if not pathname:
        catalog = dssFile.getCatalogedPathnames()
        if len(catalog) == 0:
            #empty DSS, return None
            return None, None
        pathname = catalog[0]
    #Strip out the d-part
    dssPath = DSSPathString(pathname)
    dssPath.setDPart("")
    path = dssPath.getPathname()
    startTime = HecTime()
    endTime = HecTime()
    #The following method will actually modify the input startTime and endTime objects
    dssFile.getTimeSeriesExtents(path, startTime, endTime)
    #If path does not actually exist, startTime and endTime will be undefined
    if startTime.value() == HecTime.UNDEFINED_VALUE:
        startTime, endTime = None, None
    return startTime, endTime
    
def getActiveDSSVUEFile():
    """Returns a string of the filename of the DSS file currently open in DSSVUE"""
    return HecDataManager().defaultDSSFileName()
    
def getDSSVUESelectedPathnames():
    """
    Returns a hec.dssgui.DataReferenceSet of the pathnames currently highlighted or
    selected down in the pane. You can loop through this DataReferenceSet and use
    .getPathname() to retrieve the pathname of each item.
    """
    return HecDssVue.getMainWindow().getSelectedPathnames()
    