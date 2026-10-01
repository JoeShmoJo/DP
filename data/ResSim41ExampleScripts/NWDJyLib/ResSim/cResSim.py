"""
Contains code that taps into ResSim model information.
Mostly contains code on how to access information about a reservoir network
and tap into timeseries mapping and alternative information.
A bit jumbled at this point--might be nice to rename or clean up a bit.
Scripted rules and state variables are not really tackled in this module.
For details on how to programatically control ResSim (e.g. open watersheds, run
simulations), see :any:`ResSimController`
"""
from hec.script import Constants, Plot
#ClientApp moved from hec.client to hec.clientapp.client in ResSim 4.1. Import it
#both ways so this file runs under 4.1 and 3.5 alike.
try:
    from hec.clientapp.client import ClientApp       #ResSim 4.1
except ImportError:
    from hec.client import ClientApp                 #ResSim 3.5
from hec.heclib.dss import HecDss
from hec.heclib.util import HecTime
from hec.hecmath import DSS, DSSFileException, HecMathException, TimeSeriesMath
from hec.lang import DSSPathString
from hec.model import PairedValuesExt
from hec.rss.model import ReservoirElement, JunctionElement, ReachElement, DiversionElement
from hec.rss.model import SsarrRouting, NullRouting, PulsChannelRoutingWithLosses
from hec.rss.model import RssModelVariableConstants
from hec.rss.model import SpecifiedRelease, DiversionRule, TimeSeries, ConstantRelease, MonthlyRelease
from hec.rss.model import ReservoirDamElement, DivertedOutletElement, ReservoirOutletElement
from hec.rss.model import Dam, ControlStructure
from hec.model import RunTimeStep, RunTimeWindow, SeasonalValue
from hec.io import TimeSeriesContainer
import os, sys, logging

#Custom modules
from NWDJyLib import cRouting
from NWDJyLib import cFile
from NWDJyLib import cTimes
#from NWDJyLib import cExcel
from NWDJyLib.ResSim import ResSimController
from NWDJyLib.DSS import cTsUtils
from NWDJyLib.DSS import cDSS

################################################################################
# STATIC INPUT

################################################################################
# CLASS DEFINITIONS
        
class tsmBank:
    """
    Holds a bank of read Time series.
    Assumes that the time series have been checked that they are all defined for the 
    correct time window.
    Each entry in the bank is defined by the Dss file name from which it came from, 
    as well as the pathname that is read (no D part defined).
    This can be helpful to do all of the reading of timeseries at the outset, rather
    than getting to 90% and then finding that a time series doesn't exist.
    Often populated from data in .fits files or a ResSim TSDataSet.
    If the time series are extremely large, there might not be enough memory to store
    these.
    Should close the bank after finished to release memory.
    
    TODO This should really get moved to :any:`cDSS`, but there is a "ClientApp"
    statement in here that is specific to ResSim. Would be good to change this.
    """
    def __init__(self):
        self.tsmDict = {} #first index is the dss file, 2nd is the pathname
    def containsTS(self, dssFileName, pathname):
        """Returns True if the time series exists in the bank, False otherwise"""
        if self.tsmDict.has_key(dssFileName):
            if self.tsmDict[dssFileName].has_key(pathname):
                return True
        return False
    def withdrawTS(self, dssFileName, pathname):
        """
        Returns a TimeSeriesMath object that was previously stored
        
        :param str dssFileName: the dssFile from which the ts comes from
        :param str pathname:  the pathname to retrieve
        """
        if self.tsmDict.has_key(dssFileName):
            if self.tsmDict[dssFileName].has_key(pathname):
                #The data exists, get it
                return self.tsmDict[dssFileName][pathname]
        #otherwise, return nothing
        return None
    def depositTS(self, dssFileName, pathname, tsm):
        """
        
        :param str dssFileName: the dssFile from which the ts comes from
        :param str pathname:  the pathname to retrieve
        :param TimeSeriesMath tsm: the TimeSeriesMath object to store
        """
        if not self.tsmDict.has_key(dssFileName):
            #create a new dictionary that will have pathnames as keys and tsms as values
            self.tsmDict[dssFileName] = {}
        #Add the time series to the bank
        self.tsmDict[dssFileName][pathname] = tsm
        return True
    def close(self):
        """clears out all data and releases memory"""
        del self.tsmDict
        self.tsmDict = {}
    def checkInTimeSeries(self, dssDict, tsDataSetObj, beginTime, endTime, ignoreDssFile = None, rssConstant = None, tsInt = None):
        """
        Function to read in all input time series and make sure they are fully defined
        For the whole time window.
        Adds all read time series to the bank to be withdrawn later if required.
        Modifies this tsmBank object with the TimeSeriesMath objects that were read.
        If "COMPUTE_ME" is mapped in as the "dss file", that record will be skipped
        
        :param dict dssDict: Dictionary of DssFiles that have already been opened with a predefined time window
                            keys are the dss file name (string), values are the DssFile objects
        :param TSDataSet tsDataSetObj:   A TSDataSet object that contains all time series mappings
                            keys are data location names, values are tsMapping objects
        :param beginTime: (HecTime or string)   The start time to check
        :param endTime:   (HecTime or string)   The end time to check
        :param str ignoreDssFile: If supplied, the method won't load in time series from this file.
                                  This is typically the output file that the local flows are mapped to
        :param int rssConstant:   If supplied, then only time series with this variable will be checked
                                  otherwise, all time series will be processed
                                  typically RssModelVariableConstants.VID_NODE_FLOW
        :param str tsInt:   The time interval (e.g. "1DAY")
                            If supplied, all time series will be converted to this interval
                            If not supplied, the time series will not be converted at all
        :return msg: Returns a message with all of the errors
                    The message will be blank if there are no issues
        """
        beginHecTime = HecTime(beginTime)
        endHecTime = HecTime(endTime)
        #Loop through all tsMapping objects
        msg = ""
        tsRecsMissing = [] # list of TSRecord objects that had no data
        tsRecsTruncated = [] #list of TSRecord objects that didn't have the whole time window
        timesTruncated = [] #list of tuples that show the start/end times of the truncated tsRecs
        for tsRec in tsDataSetObj.getTSRecords():
            name = tsRec.getName()
            param = tsRec.getParamName()
            varID = tsRec.getVariableId() #RssModelVariableConstants ID 
            dssName = tsRec.getDSSFilename()
            dssName = ClientApp.Workspace().makeAbsolutePath(dssName)
            pathname = tsRec.getDSSPathname()
            #skip if the variable ID isn't what is desired
            if rssConstant: #the argument was supplied
                if varID != rssConstant: continue
            #skip if time series already stored in the bank
            if self.containsTS(dssName, pathname): continue
            #skip if the dss file is the one to ignoreDssFile
            if str(dssName).upper() == str(ignoreDssFile).upper(): continue
            #skip of the dss file signals the user not to use it
            if "COMPUTE_ME" in str(dssName).upper(): continue
            #skip time series with blank pathnames
            if len(pathname) == pathname.count("/"): #blank pathname
                continue
            if dssName == "" and not dssDict.has_key(""):
                #Only skip blank DSS filename if there is no dictionary key 
                # for "" (possibly an override)
                continue
            #make sure the dss file is in the dictionary--if not, return None
            if not dssDict.has_key(dssName):
                errMsg = "ERROR! the dss file is not defined in the dictionary!"
                raise AssertionError, errMsg 
            openDssFile = dssDict[dssName]
            #try to read the time series
            try:
                tsm = openDssFile.read(pathname)
            except (DSSFileException, HecMathException): # Couldn't find the DSS path
                tsRec.setDSSFilename(openDssFile.getFilename()) #For debug msg
                tsRecsMissing.append(tsRec)
                continue
            #check the start date and end date
            tsmFirstTime = HecTime(tsm.firstValidDate(), HecTime.MINUTE_INCREMENT)
            tsmLastTime  = HecTime(tsm.lastValidDate(), HecTime.MINUTE_INCREMENT) 
            if tsmFirstTime.notEqualTo(beginHecTime):
                tsRec.setDSSFilename(openDssFile.getFilename()) #For debug msg
                tsRecsTruncated.append(tsRec)
                timesTruncated.append((tsmFirstTime.dateAndTime(),tsmLastTime.dateAndTime()))
            elif tsmLastTime.notEqualTo(endHecTime):
                tsRec.setDSSFilename(openDssFile.getFilename()) #For debug msg
                tsRecsTruncated.append(tsRec)
                timesTruncated.append((tsmFirstTime.dateAndTime(),tsmLastTime.dateAndTime()))
            else:
                #it's good, Add the time series to the bank
                if tsInt:
                    # the output is desired to be changed to a uniform timestep
                    # Convert it, but deposit it with the original pathname
                    tsm = cTsUtils.transformTSM(tsm, tsInt)
                self.depositTS(dssName, pathname, tsm)
        # Prepare a nice, organized output message:
        if len(tsRecsMissing) > 0:
            msg += "\n\nTime Series that do not exist:"
            for tsRec in tsRecsMissing:
                msg += "\n  Name:       %s" %tsRec.getName()
                msg += "\n  Dss File:   %s" %tsRec.getDSSFilename()
                msg += "\n  Pathname:   %s\n" %tsRec.getDSSPathname()
        if len(tsRecsTruncated) > 0:
            msg += "\n\nTime Series not defined over the full time window:"
            msg += "\nFull time window: %s, %s" %(beginHecTime.dateAndTime(), endHecTime.dateAndTime())
            for i, tsRec in enumerate(tsRecsTruncated):
                msg += "\n  Name:       %s" %tsRec.getName()
                msg += "\n  Dss File:   %s" %tsRec.getDSSFilename()
                msg += "\n  Pathname:   %s" %tsRec.getDSSPathname()
                msg += "\n  Start Time: %s" %timesTruncated[i][0]
                msg += "\n  End Time:   %s\n" %timesTruncated[i][1]
        return msg
# END OF CLASS DEFINITIONS
################################################################################
# MIGRATED FUNCTIONS (IF MOVED TO ANOTHER MODULE, FOR BACKWARD COMPATIBILITY)
# theOldFunctionThatWasHere = newModule.theReplacementFunction
getHecTimeFromRuntimestep = cTimes.getHecTimeFromRuntimestep
################################################################################
# FUNCTION DEFINITIONS

def exportTStoSlaveSV(SV, TS):
    """
    Export a whole time series to a state variable. Meant to be run inside a 
    ResSim simulation. Returns True.
    This function doesn't belong in this module and should be moved--TODO.
    
    :param StateVariable SV: The slave state variable to receive the time-series
    :param TimeSeriesContainer TS: The time series to copy into the slave 
    """
    tsObj = SV.getTimeSeries()
    values = TS.values
    for i in range(len(values)):
        tsObj.setCurrentValue(i, values[i])
    return True
    
def _getTSDictFromFITSfile(network, altName, isObs=False, typeToRead = "Flow"):
    """
    DEPRECATED-load a tsBank object with a TSDataSet instead
    Function to read the observed data .fits file for a particular alternative
    network = RssSystem
    altName = string (e.g. "Observed" or "Observed--", not "Observed--0": no number)
    isObs = boolean, whether or not to get the observed data TS mapping or the regular
    typeToRead = string (e.g. "Flow", "Elev", "" to get all types), the types of observed data to get
    Returns a dictionary with the keys as the data location names, 
    and the values are tsMapping objects
    If it can't find or process the .fits file, it will return None
    If isObs is True, the keys will be something like "~N86"
    If isObs is False, the keys will be something like "Hills Creek - Flow-Res In"
    
    """
    # Find the .fits file
    obsStr = "Obs.fits"
    runDir = network.getBaseDirectory() + "/"
    altStr = altName.replace(" ", "_") # if the alt has a space in the name, ResSim puts an underscore
    for f in os.listdir(runDir):
        ext = f.split(".")[-1]
        if isObs: #obsStr will exist in the .fits file name
            if ext == "fits" and f.startswith(altStr) and obsStr in f:
                rf = runDir+f
                break
        else:
            if ext == "fits" and f.startswith(altStr) and obsStr not in f:
                rf = runDir+f
                break       
    try: lines = cFile.fileOpenReadClose(rf)
    except: 
        m = "Could not find TS data .fits file for: '%s' in directory:\n %s" %(altName, runDir)
        logging.error(m)
        raise AssertionError, m
    logging.debug("Successfully read .fits file: %s" %f)
    tsDataDict = {} 
    idx, name, varID, param, path, dssFileName = None, None, None, None, None, None
    for line in lines:
        if "TSrecord=" in line: idx = line.split("TSRecord=")[-1].strip()
        elif "TSRecord Name=" in line: name = line.split("TSRecord Name=")[-1].strip()
        elif "VariableID=" in line: varID = line.split("VariableID=")[-1].strip()
        elif "ParamName=" in line: param = line.split("ParamName=")[-1].strip()
        elif "DssPathname=" in line and name: path = line.split("DssPathname=")[-1].strip().upper()
        elif "DssFilename=" in line: 
            dssFileName = line.split("DssFilename=")[-1].strip() #e.g. shared/test.dss
            dssFileName = network.makeAbsolutePathFromWatershed(dssFileName)
            #dssFileName = ClientApp.Workspace().makeAbsolutePath(dssFileName)
        elif "End=" in line:
            #if "Flow" not in param: continue #Only get flow data
            if typeToRead not in param: continue #Only get specified data types (if "", will get all)
            #Create the tsMapping object
            mapObj = tsMapping(idx, name, varID, param, path, dssFileName)
            #Add the tsMapping object to the dictionary
            tsDataDict[name] = mapObj
    return tsDataDict
    
def getConnectedReaches(element):
    """
    Function to return a list of all the reach element objects connected to "element"
    
    :param Element element: any element (e.g. JunctionElement)
    """
    connectedElems = list(element.getConnectedElements())
    reachElems = []
    for elem in connectedElems:
        if isinstance(elem, ReachElement):
            reachElems.append(elem)
    return reachElems
    
def getConnectedDiversions(juncElem):
    """
    Function to return the diversion element objects connected to juncElem.
    There can be multiple diversions connected to the junction.
    
    :param JunctionElement element: any JunctionElement
    :return: A list of DiversionElement objects, or None if there is no diversion
    """
    divElems = []
    connectedElems = list(juncElem.getConnectedElements())
    for elem in connectedElems:
        if isinstance(elem, DiversionElement):
            divElems.append(elem)
    if divElems == []: #never found a diversion
        return None
    else:
        return divElems

def getRealHeadwaterJunctions(network):
    """
    Function to return a list of all the headwater junctions in the model.
    Returns a list of JunctionElement objects.
    The native ResSim function kind of screws it up sometimes, 
    including non-headwater spots, which is why this function is necessary.
    """
    juncs = network.getHeadwaterJunctions()
    hwJuncs = []
    for junc in juncs:
        element = network.findJunction(junc.toString())
        connectedElems = element.getConnectedElements()
        # Remove any diversion elements
        nonDivElems = []
        for elem in connectedElems:
            if not isinstance(elem, DiversionElement):
                nonDivElems.append(elem)
        if len(nonDivElems) == 1: #No upstream and downstream connection
            hwJuncs.append(junc)
    return hwJuncs
    
def getConfluenceJunctions(network):
    """
    Function to return a list of all the confluence junctions in the model.
    Returns a list of JunctionElement objects.
    """
    juncs = network.getJunctionNames()
    confJuncs = []
    for junc in juncs:
        element = network.findJunction(str(junc))
        connectedReaches = getConnectedReaches(element)
        dsElem = element.getDownstreamNode().getDownstreamElement()
        if len(connectedReaches) >= 3 or \
         (len(connectedReaches)>=2 and dsElem==None) or \
         (len(connectedReaches)>=2 and str(dsElem)=="Pool"): 
            #At least 3 connected reaches or at the mouth and 2 connected reaches
            #Or two upstream reaches and the downstream connection is a pool
            #confJuncs.append(junc)
            confJuncs.append(element)
    return confJuncs
    
def getConfluenceResvPoolDict(network):
    """
    Some reservoirs can have more than one inflow point (e.g. Arrowrock).
    This function returns a dictionary:
    
        keys = all the confluence reservoirs in the model (the "pool" element, not ReservoirElement)
        values = list of all JunctionElements that flow into the reservoir
    """
    # Loop through all junctions first to see what their downstream element is
    juncs = network.getJunctionNames()
    dsResvDict = {}
    confResvDict = {}
    for junc in juncs:
        juncElem = network.findJunction(str(junc))
        #To get to the ReservoirElement, we need to go twice downstream elements
        #This first Downstream Element is the "Pool" (general Element)
        #To get the ReservoirElement, need to do a .getParent() call
        dsElem = juncElem.getDownstreamNode().getDownstreamElement() #"Pool" element
        if dsElem == None: continue #last junction in the model
        resvElem = dsElem.getParent()
        if not isinstance(resvElem, ReservoirElement): continue #only get reservoir elements
        if dsElem not in dsResvDict.keys(): 
            #1st time we encounter it
            dsResvDict[dsElem] = [juncElem] 
        else: 
            #This is the 2nd or 3rd time we've encountered it
            dsResvDict[dsElem].append(juncElem)
    #Only keep reservoirs with more than one upstream junction
    for poolElem in dsResvDict.keys():
        if len(dsResvDict[poolElem]) > 1: #more than one
            confResvDict[poolElem] = dsResvDict[poolElem]
    return confResvDict
    
def getConfluenceResvNames(network):
    """
    Function to return a list of reservoir names that have more than one inflow junction
    
    :return: all the confluence reservoir names in the model (strings, e.g. "Bonneville")
    """
    confResvPoolDict = getConfluenceResvPoolDict(network) #Keys are "Pool" elements
    resvNames = []
    for poolElem in confResvPoolDict.keys():
        resvName = poolElem.getParent().toString()
        resvNames.append(resvName)
    return resvNames
    
def getPoolElemFromResvElem(resvElem):
    """
    Returns the "Pool" element for a provided resvElem (ReservoirElement).
    The "Pool" element is a generic hec.rss.model.Element.
    "Pool" is typically used when ordering the network.
    """
    for childElem in resvElem.children(): #includes pool, dams, diverted outlets
        if childElem.toString() == "Pool": #always named "Pool"
            return childElem
    # Never found it
    return None
    
def orderElementsFromUpstream(network):
    """
    Function to return a list of ordered elements from headwater to the mouth.
    This can be used for routing of unregulated flows, local flows, etc.
    Reservoir elements encountered are stored as the "Pool" element, not a true
    ReservoirElement.
    Does not include DiversionElement objects.
    
    :return: List of Element (or subclass of Element) objects in order
    """
    hwJuncs = getRealHeadwaterJunctions(network)
    hwJuncsLeft = []
    for junc in hwJuncs:
        hwJuncsLeft.append(junc) 
    confJuncs = getConfluenceJunctions(network)
    confElemsLeft = []
    for junc in confJuncs:
        confElemsLeft.append(junc)
    # Add in confluence reservoirs (multiple inflows)
    confResvDict = getConfluenceResvPoolDict(network)
    for poolElem in confResvDict:
        confElemsLeft.append(poolElem)
    # Initialize the looping to figure out the compute order
    done = False
    elemList = []
    confInflowCount = dict.fromkeys(confElemsLeft,0)
    while not done:
        hwJuncsNew = []
        for hwJunc in hwJuncsLeft:
            # get downstream elements up to the next confluence point
            #element = network.findJunction(str(hwJunc))
            element = hwJunc
            elemList.append(element)
            atConfluence = False
            while not atConfluence:
                try:
                    element = element.getDownstreamNode().getDownstreamElement()
                    if element in confElemsLeft:
                        # at a confluence point, done with this headwater loop
                        atConfluence = True
                        confInflowCount[element] += 1
                        # check to see if the other inflows to the confluence have come in yet
                        if isinstance(element, JunctionElement):
                            # first need to see how many upstream reaches there are
                            dsElem = element.getDownstreamNode().getDownstreamElement()
                            upstreamElems = list(getConnectedReaches(element))
                            try: # the last point doesn't have a downstream element
                                upstreamElems.remove(dsElem) # only keep upstream elements
                            except:
                                pass
                            numUpstrmElems = len(upstreamElems)
                        else: #a "pool" element
                            #Get the number of upstream JunctionElements
                            numUpstrmElems = len(confResvDict[element])
                        if confInflowCount[element] == numUpstrmElems:
                            # all the inflows have come in--this is a new "headwater" element
                            hwJuncsNew.append(element)
                    else:
                        # keep going downstream
                        elemList.append(element)
                except:
                    # No downstream element, stop
                    atConfluence = True
        hwJuncsLeft = hwJuncsNew
        if len(hwJuncsLeft) == 0:
            done = True
            #Remove the last entry (should be None)
            elemList = elemList[:-1]
    return elemList

def getElevationStorageTable(reservoirName, network):
    """
    Returns a table that inputs elevation and returns storage
    
    :param str reservoirName: The reservoir name as it exists in ResSim
    :param RssSystem network:
    :return elevStorTable: Can use .interpolate on this object
    :rtype: PairedValuesExt
    """
    reservoirObj = network.findReservoir(reservoirName)
    storageElement = reservoirObj.getStorageFunction()
    storageTable = storageElement.getElevationStorageValues()
    pairedDataContainer = storageTable.getPairedDataContainer()
    elevStorTable = PairedValuesExt() 
    elevStorTable.setData(pairedDataContainer)
    return elevStorTable

def getStorageElevationTable(reservoirName, network):
    """
    Returns a table that inputs storage and returns elevation
    
    :param str reservoirName: The reservoir name as it exists in ResSim
    :param RssSystem network:
    :return storElevTable: Can use .interpolate on this object
    :rtype: PairedValuesExt
    """
    reservoirElement = network.findReservoir(reservoirName)
    storageElement = reservoirElement.getStorageFunction()
    storageTable = storageElement.getElevationStorageValues()
    pairedDataContainer = storageTable.getPairedDataContainer()
    storElevTable = PairedValuesExt() 
    storElevTable.setData(pairedDataContainer)
    elevations = storElevTable.getXArray()
    storages = storElevTable.getYArray()
    storElevTable.setArrays(storages,elevations)
    return storElevTable

def getElevationReleaseTable(resvName, outletName, network):
    """
    Returns a table that represents the elevation vs. release capacity table.
    This only works for controlled outlets.
    
    :param str reservoirName: The reservoir name as it exists in ResSim
    :param str outletName: The exact name of the controlled outlet to retrieve
    :param RssSystem network:
    :return storElevTable: Can use .interpolate on this object
    :rtype: PairedValuesExt
    """
    resv = network.findReservoir(resvName)
    if not resv: return None
    outletElem = resv.getElementByName(outletName)
    if not outletElem: return None
    adjFlow = outletElem.getFunction() #AdjustableFlow
    if adjFlow.hasMultipleGateSettings():
        # The x-values are the elevations, the y-values are always flows, the z-curves are gate settings
        elevRelTable = adjFlow.getCapacityValuesBySetting() # hec.rss.model.PairedValuesExt
    else: # normal elev v. flow data
        # The x-values are actually the elev, the y-values are flow in cfs, which is why shiftMV is backwards
        dataVec = adjFlow.getCapacityValues().getDataVector() # vector of hec.model.ValueSet
        elevRelTable = PairedValuesExt()
        elevs = []
        rels = []
        for vs in dataVec:
            elevs.append(vs.xval)
            rels.append(vs.yval)
        elevRelTable.setArrays(elevs, rels)
    return elevRelTable

def getRule(resvName, ruleName, network):
    """
    Returns the OpRule object for a given rule name for a given reservoir
    """
    ruleObj = None
    rules = network.findReservoir(resvName).getReservoirOp().getRules()
    for rule in rules:
        if ruleName in rule.toString():
            ruleObj = rule
            break
    if ruleObj is None:
        raise AssertionError("Trying to get rule %s at %s, couldn't find it" %(ruleName, resvName))
    return ruleObj

def getLookback(resvName, rssAlt, paramName = None):
    """
    Returns the lookback parameter for a reservoir.
    Only works if the the lookback is defined as a constant.
    Currently only functional for "Elevation" lookbacks.
    
    :param str resvName: The reservoir name to retrieve
    :param RssAlt rssAlt: The alternative with the lookback data
    :param str paramName: Either "Release", "Elevation", or "Storage"
    """
    network = rssAlt.getSystem()
    resvElem = network.findReservoir(resvName)
    if not resvElem: return None
    inputTSDataSet = rssAlt.getInputTSDataSet()
    if "ELEV" in paramName.upper():
        rssConstant = RssModelVariableConstants.VID_POOL_ELEV
    elif "RELEASE" in paramName.upper():
        #TODO come back here!
        pass
    else:
        return None
    tsrp = resvElem.getTSRecordProxy(rssConstant)
    if tsrp is None: return None
    tsName = tsrp.getName() # e.g. ~E468:F
    hindcastList = rssAlt.getHindcastData() #list of hec.rss.model.HindcastData
    for hd in hindcastList:
        varID = hd.getVariableId()
        objKey = hd.getObjectKey() #e.g. "~E2394:F"
        if objKey == tsName and varID == RssModelVariableConstants.VID_POOL_HINDELEV:
            #Found the entry
            #Check to make sure the lookback is a constant
            if hd.getTypeName() != "Constant": return None
            return hd.getValue()
    return None

def getLookbackVals(resvName, rssRun, paramName, simDssFile = None): 
    """
    Retrieves the list of lookback values for the lookback period from Alternative Editor input.
    TODO enhancement: it doesn't currently work if lookback is time-series and simDssFile not provided.
    
    :param str resvName: The reservoir name to retrieve
    :param RssAlt rssAlt: The alternative with the lookback data
    :param str paramName: Either "Release", "Elevation", or "Storage" (could also be a specific outlet name)
    :param DSSFile simDssFile: (optional) The already opened simulation.dss file.
        Not necessary if you know the lookback is a constant
    :return list: list of lookback values for a reservoir (index 0 is the first one)
        Will return a list of constant numbers if lookback is constant
    """
    #Need to find the reservoir network & alternative
    rssAlt = rssRun.getAlternative()
    numLookbackSteps = rssRun.getRunTimeWindow().getNumLookbackSteps()
    network = rssAlt.getSystem()
    resvElem = network.findReservoir(resvName)
    if not resvElem: return None
    #identify the right RssModelVariableConstant to use (tsrp name should be the same for both)
    if "ELEV" in paramName.upper():
        rssConstant = RssModelVariableConstants.VID_POOL_ELEV
        rssConstantLookback = RssModelVariableConstants.VID_POOL_HINDELEV
        elemsToLoop = [resvElem]
    elif "RELEASE" in paramName.upper():
        rssConstant = RssModelVariableConstants.VID_CTRLOUT_HINDFLW
        rssConstantLookback = RssModelVariableConstants.VID_CTRLOUT_HINDFLW
        #Lookback is separate for each outlet--get them all
        #This command even gets the Dam L&O, which has no lookback...
        elemsToLoop = resvElem.getElementsByClass(ControlStructure, None) #generic Element
    else:
        return None
    valsToReturn = [0 for i in range(numLookbackSteps+1)] #initialize
    for elem in elemsToLoop: # if doing total lookback release, there are multiple elements to look at
        func = elem.getFunction() #often an AdjustableFlow, PowerPlant, or Spillway object
        #skip any control structures that don't actually have lookback data
        if isinstance(func, Dam): # L&O
            continue
        tsrp = elem.getTSRecordProxy(rssConstant)
        if tsrp is None: return None
        tsName = tsrp.getName() # e.g. ~E468:F
        hindcastList = rssAlt.getHindcastData() #list of hec.rss.model.HindcastData
        for hd in hindcastList:
            varID = hd.getVariableId()
            objKey = hd.getObjectKey() #e.g. "~E2394:F"
            if objKey == tsName and varID == rssConstantLookback:
                #Found the entry
                if hd.getTypeName() == "Constant":
                    valsToReturn = [valsToReturn[i] + hd.getValue() for i in range(numLookbackSteps+1)]
                elif hd.getTypeName() == "Time-Series":
                    #Need to read in the pathname
                    inputTSDataSet = network.getInputTSDataSet()
                    tsRec = inputTSDataSet.getTSRecord(tsName, rssConstantLookback)
                    lookbackPath = tsRec.getDSSPathname()
                    if not simDssFile: 
                        #the lookback is a time-series, but no DSS file was given
                        #Need to open/close the file here
                        dssFileNameSimulation = thisRun.getDSSOutputFile()
                        fileNameSimulation = network.makeAbsolutePathFromWatershed(dssFileNameSimulation)
                        simDssObj = DSS.open(fileNameSimulation, rssRun.getRunTimeWindow().getTimeWindowString())
                    else: #use the previously provided input DSS file
                        simDssObj = simDssFile
                    lookbackTSM = simDssObj.read(lookbackPath)
                    if not simDssFile: simDssObj.close() #done reading, close the file
                    lookbackVals = lookbackTSM.getContainer().values
                    valsToReturn = [valsToReturn[i] + lookbackVals[i] for i in range(numLookbackSteps+1)]
                else: #computed
                    return None
    return valsToReturn
    
def getTSRecord(tsDataSetObj, rssLocation, rssConstant, txtArea, 
    isStrict = True, displayMessages = True):
    """
    Attempts to retrieve a TSRecord object from the ResSim network.
    The TSRecord object will have the dss file and pathname defined, but no Container data.
    Can retrieve either simulated or observed data for any element.
    Will return None if the time series is not well defined to let the calling
    function decide what to do with it.
    If the time series is well defined, but it just doesn't exist in the dss file,
    it will throw an error.
    
    :param TSDataSet tsDataSetObj: The TSDataSet to retrieve from (observed, input, regulated output)
    :param Element/RssNode rssLocation: The element to retrieve output from
                                     can be an RssNode, JunctionElement, ReservoirElement, etc.
    :param int rssConstant:         the parameter to retrieve, e.g.
                                    RssModelVariableConstants.VID_POOL_ELEV
                                    RssModelVariableConstants.VID_NODE_FLOW
                                    RssModelVariableConstants.VID_JUNC_STAGE
    :param JTextArea txtArea:       must have a "printToGUI" method defined
    :param boolean isStrict:        if true, then errors stop the compute immediately
                                    if false and an error comes up, will just return None
    :param boolean displayMessages: if true, then warning messages will be pumped out
    :return tsRec: Data about the time series desired. If None, the data didn't exist
    :rtype: TSRecord
    """
    elemName = rssLocation._name
    #Get the TSRecordProxy that contains information about which timeseries is linked
    if rssConstant == RssModelVariableConstants.VID_NODE_FLOW and \
     (isinstance(rssLocation, JunctionElement) or isinstance(rssLocation, ReachElement)): 
        #Flow, have to do it the hard way. Need to get it from the outflow node, not the element
        node = rssLocation.getDownstreamNode() #RssNode
        tsrp = node.getTSRecordProxy(rssConstant)
    elif rssConstant == RssModelVariableConstants.VID_NODE_KNOWNFLOW:
        #Known inflow (local flow) (only works for input/observed TSDataSets, not regOutput)
        #Must be retrieved from the upstream node, not the junction element itself
        #If getting output local flows, the parameter is actually just flow
        tsrp = rssLocation.getTSRecordProxy(rssConstant)
    else:
        #Can get data easily (e.g. pool elevation, stage)
        tsrp = rssLocation.getTSRecordProxy(rssConstant)
    if tsrp is None:
        errMsg = "\nCouldn't locate a ResSim model variable for: %s" %elemName
        errMsg += "\nThat corresponds to the RssModelVariableConstant: %s" %rssConstant
        errMsg += "\nShouldn't even be asking for this variable at this location"
        errMsg += "\nCheck the RssModelVariableConstants.java file to see the codes"
        if displayMessages: 
            txtArea.printToGUI(errMsg)
            logging.error(errMsg)
        if isStrict: #need to stop at any error here
            raise AssertionError, errMsg
        else: 
            return None
    tsName = tsrp.getName() # e.g. New York Irrigation Diversion, or ~E468:F
    tsRec = tsDataSetObj.getTSRecord(tsName, rssConstant)
    return tsRec
    
def getTSMFromSimulationDSS(simDss, rssLocation, run, rssConstant, txtArea, 
    useObsData, isStrict = True, displayMessages = True):
    """
    Attempts to retrieve a TimeSeriesMath object from the simulation.dss file.
    Can retrieve either simulated or observed data for any element.
    Will return None if the time series is not well defined to let the calling
    function decide what to do with it.
    If the time series is well defined, but it just doesn't exist in the dss file,
    it will throw an error. Uses :func:`getTSRecord`.
    
    :param DssFile simDss: already opened simulation.dss file
    :param Element/RssNode rssLocation: the element to retrieve output from
                                     can be an RssNode, JunctionElement, ReservoirElement, etc.
    :param RssRun run:              the RssRun to retrieve data from
                                    has to be an RssRun because an RssAlt can only
                                    get input and observed TS Mapping, not output
    :param int rssConstant:         the parameter to retrieve, e.g.
                                    RssModelVariableConstants.VID_POOL_ELEV
                                    RssModelVariableConstants.VID_NODE_FLOW
                                    RssModelVariableConstants.VID_JUNC_STAGE
    :param boolean useObsData:      if true, then "observed data" will be retrieved, not modeled data
    :param JTextArea txtArea:       must have a "printToGUI" method defined
    :param boolean isStrict:        if true, then errors stop the compute immediately
                                    if false and an error comes up, will just return None
    :param boolean displayMessages: if true, then warning messages will be pumped out
    :return tsm: The time series that was retrieved
    :rtype: TimeSeriesMath
    """
    #Figure out with TSDataSet to use
    if useObsData:
        #tsDataSetObj = alt.getObservedTSDataSet()
        tsDataSetObj = run.getObservedTSData() #TSDataSet
    else: #use simulated output data
        #tsDataSetObj = run.getOutputTSDataSet() #doesn't work
        tsDataSetObj = run.getRegOutputTSData()
        #tsDataSetObj = run.getCumLocOutputTSData()
        #tsDataSetObj = run.getUnregOutputTSData()
    elemName = rssLocation._name
    #Get the TSRecord object for the variable
    tsRec = getTSRecord(tsDataSetObj, rssLocation, rssConstant, txtArea, isStrict, displayMessages)
    if tsRec is None:
        if useObsData:
            errMsg = "\nCouldn't locate observed data for: %s" %elemName
            errMsg += "\nShould have the box checked in the 'Observed Data'"
            errMsg += "\n tab of the Reservoir Editor or Junction Editor"
        else:
            errMsg = "\nFailed to find time series for: %s" %elemName
            errMsg += "\nMight be mixing up observed/modeled data?"
        if displayMessages: 
            txtArea.printToGUI(errMsg)
            logging.error(errMsg)
        return None
    path = tsRec.getDSSPathname()
    if len(path) == path.count("/"): #blank pathname
        errMsg = "\tBlank Pathname mapped in at: %s,%s" %(elemName, tsRec.getName())
        if displayMessages: 
            txtArea.printToGUI(errMsg)
            logging.error(errMsg)
        return None
    #should be able to read the timeseries
    try:
        tsm = simDss.read(path)
    except (DSSFileException, HecMathException): # Couldn't find the DSS path
        errMsg =  "ERROR IN READING DATA: COULD NOT READ PATHNAME:"
        errMsg += "\n%s\nFROM DSS FILE: %s\n" %(path, simDss.getFilename())
        errMsg += "\nProbably need to retrieve/map in the correct data"
        errMsg += "\nOr rerun the time-series extract, or re-run the alternative"
        if displayMessages: 
            txtArea.printToGUI(errMsg)
            logging.error(errMsg)
        raise AssertionError, errMsg 
    return tsm

def getLocalFlowTSM(juncElem, simDssFile):
    """
    Function to return a TimeSeriesMath object that is the sum of all local flows at a junction.
    Assumes the data has already been extracted to simulation.dss.
    Typically run in initialization scripts--not scripts outside a compute or runRuleScripts.
    
    :param JunctionElement juncElem: The junction at which to retrieve locals
    :param DSSFile simDssFile: The already opened simulation.dss file (with a time window)
    :return tsm: TimeSeriesMath representing sum of all local flows
    """
    factor = 1. # default, inflow multiplier factor
    elemName = str(juncElem)
    rssConstant = RssModelVariableConstants.VID_NODE_KNOWNFLOW
    inputTSDataSet = juncElem.getSystem().getInputTSDataSet()
    #In ResSim, there is a separate node for each local flow.
    nodes = juncElem.getNodeVector()
    totalLocalTSM = None
    for node in nodes: #One local flow per node in ResSim
        # skip downstream elements
        if str(node.getDownstreamElement()) != elemName: continue
        #Local flow nodes have no upstream element
        if node.getUpstreamElement(): continue #must be a connected element, skip it
        tsrp = node.getTSRecordProxy(rssConstant)
        if tsrp:
            # The TSRecordProxy corresponds to a local inflow location
            # Retrieve the input pathname of the local flow record
            factor = tsrp.getFactor() # local inflow multiplier is attached to the proxy
            tsRec = getTSRecord(inputTSDataSet, node, rssConstant, txtArea=None, isStrict=False, displayMessages=False)
            pathname = tsRec.getDSSPathname()
            locFlowTSM = simDssFile.read(tsRec.getDSSPathname())
            locFlowTSM = locFlowTSM.multiply(factor)
            if not totalLocalTSM: #first local flow
                totalLocalTSM = locFlowTSM
            else: # not the first--add it in
                totalLocalTSM = totalLocalTSM.add(locFlowTSM)
    return totalLocalTSM
    
def routeDirectTSC(network, tsc, startJuncName, endJuncName):
    """
    Function to route flow from one junction to another.
    It will not add any local flows in--just a pure and simple direct routing.
    
    :param RssSystem network: the network to use for the routing parameters
    :param TimeSeriesContainer tsc: the input time series at startJuncName
    :param str startJuncName: Exact name of the junction to start routing from in the network
    :param str endJuncName: Exact name of the junction to finish routing at in the network
    :return: A TimeSeriesContainer of the routed flow
    """
    if network is None:
        logging.error("Need to pass in a valid network (RssSystem)")
        return None
    startJunc = network.findJunction(startJuncName)
    endJunc = network.findJunction(endJuncName)         
    if startJunc is None: 
        logging.error("The start Junction doesn't exist in the network: '%s'" %startJuncName)
        return None
    elif endJunc is None:
        logging.error("The end Junction doesn't exist in the network: '%s'" %endJuncName)
        return None
    #Check to see if the endJunction is downstream of the startJunction
    if endJunc not in network.getDownstreamElements(startJunc):
        logging.error("The end Junction: '%s' is not downstream of the start Junction: '%s'" %(endJuncName, startJuncName))
        return None
    #We are reasonably sure we can route the flows--let's do it
    element = startJunc
    flowTSC = tsc.clone()
    count = 0
    while element._name != endJuncName:
        count += 1
        # Get the next downstream element
        dsNode = element.getDownstreamNode()
        element = dsNode.getDownstreamElement()
        elemName = element._name
        # If the element is a reach, route the flow to the next junction
        if isinstance(element, ReachElement):
            # If the element is a reach, route the flow to the next junction
            routingObj = element.getFunction()
            logging.debug("Reach : %s" %elemName)
            routeReach = cRouting.buildReach(routingObj)
            if routeReach is None:
                errMsg = "The Script cannot handle any routing methods besides SSARR, Muskingum, ModPuls, or Null:"
                errMsg += "\n%s has routing of: %s" %(elemName, routingObj.__class__)
                logging.error(errMsg)
                return None
            logging.debug("\tRouting Type: %s" %routingObj.__class__)
            flowTSC = routeReach.routeTSC(flowTSC)
        # Break loop if the downstream location is never found
        if count > 500:
            logging.error(endJuncName + " does not exist in routing computations")
            return None             
    return flowTSC

def getDiversionTSC(divElem, rtw, inputTSDataSet, overrideInputDSSFile=None):
    """
    Function to retrieve the flows at a diversion.
    Can only handle the following types of diversions:
    
    * Constant
    * Time series
    * Seasonal
        
    TODO DSS File opening is a bit inefficient here
    
    :param DiversionElement divElem: The Diversion to get the flows for
    :param RunTimeWindow rtw: The ResSim time window to compute
    :param TSDataSet inputTSDataSet: The input time series mapping ("time-series" tab)
    :param str overrideInputDSSFile: If supplied, the diversion time series will
          attempt to be read from this file, rather than the dss file that is mapped
          in the Time Series tab
    :return: A TimeSeriesContainer of diversion flows for the whole window
    """
    lookbackTime = rtw.getLookbackTimeString()
    endTime = rtw.getEndTimeString()
    #Get the diversion type (Rule)
    ctrl = divElem.getController() #hec.rss.model.Controller
    rule = ctrl.getRuleVector()[0] #there is only one rule in a diversion
    network = rule.getSystem()
    #Set up the output TimeSeriesContainer
    #populate the times first--populate the values later
    rts = RunTimeStep(rtw)
    divTSC = TimeSeriesContainer()
    times = []
    #Loop through all time steps, getting the diversion amount
    for step in range(rts.getTotalNumSteps()+1):
        rts.setStep(step)
        #divTime = rts.getHecTime() #problem with daily granularity
        divTime = getHecTimeFromRuntimestep(rts)
        times.append(divTime.value())
    divTSC.times = times
    values = None #to be filled in if necessary--divTSC might get overwritten
    if isinstance(rule, TimeSeries):
        # Diversion is a simple function of an external time series
        logging.debug("\tTime Series Diversion")
        tsrp = rule.getTSRecordProxies()[0] #there is only one time series in a diversion
        tsName = tsrp.getName() #e.g. "New York Irrigation Diversion"
        #Get the input pathname and dss file
        tsRec = inputTSDataSet.getTSRecord(tsName, RssModelVariableConstants.VID_OPRULETS_TSINPUT)
        if tsRec is None:
            errMsg = "No matching Diversion time series found: %s" %tsName
            logging.error(errMsg)
            return None
        path = tsRec.getDSSPathname()
        dssFilename = tsRec.getDSSFilename()
        dssFilename = network.makeAbsolutePathFromWatershed(dssFilename)
        if overrideInputDSSFile:
            #Use the manual input override instead
            dssFilename = overrideInputDSSFile
        if len(path) == path.count("/") or dssFilename == "": #blank pathname
            errMsg = "\tBlank Pathname--need to map in a diversion pathname at: %s" %divElem
            logging.error(errMsg)
            return None
        else: #should be able to read the timeseries
            #Open the file and add it to the dictionary
            logging.info("Opening Dss File: %s" %dssFilename)
            openedDssFile = DSS.open(dssFilename, lookbackTime, endTime)
            obsDss = openedDssFile
            try:
                tsm = obsDss.read(path)
            except (DSSFileException, HecMathException): # Couldn't find the DSS path
                errMsg =  "ERROR IN READING OBSERVED DATA: COULD NOT READ PATHNAME:"
                errMsg += "\n%s\nFROM DSS FILE: %s\n" %(path, obsDss.getFilename())
                errMsg += "\nProbably need to retrieve/map in the correct observed data"
                logging.error(errMsg)
                return None 
            divTSC = tsm.getData()
    elif isinstance(rule, SpecifiedRelease):
        #Diversion is a seasonal value
        #The public methods in the Java code for seasonal diversions is sorely lacking
        logging.debug("\tSpecifiedRelease Diversion")
        #No direct method to get SeasonalValue object from SpecifiedRelease Rule
        #Have to get it as a string, then convert it back
        seasonVal = SeasonalValue()
        seasonVal.parseString(rule.getReleaseValues())
        #SeasonalValue objects only support interpolation on a RunTimeStep object
        values = []
        #Loop through all time steps, getting the diversion amount
        for step in range(rts.getTotalNumSteps()+1):
            rts.setStep(step)
            divVal = seasonVal.interpolateStepValue(rts) #this is the one
            #divVal = rule.getValue(None, rts, 0)#alternately (looks like RMA doesn't want to maintain this)
            values.append(divVal)
    elif isinstance(rule, ConstantRelease):
        logging.debug("\tConstant Diversion Release")
        divVal = rule.getReleaseValue()
        values = [divVal for i in range(rts.getTotalNumSteps()+1)]
    elif isinstance(rule, MonthlyRelease):
        logging.debug("\tMonthly Diversion Release")
        #MonthlyRelease objects only support interpolation on a RunTimeStep object
        values = []
        #Loop through all time steps, getting the diversion amount
        for step in range(rts.getTotalNumSteps()+1):
            rts.setStep(step)
            divVal = rule.getValue(None, rts, 0) #looks like RMA doesn't want to maintain this
            values.append(divVal)
    elif isinstance(rule, DiversionRule):
        logging.debug("\tCannot handle Flexible Diversion Rules!")
        return None
    else:
        logging.debug("\tUnknown diversion type: %s" %rule.__class__)
        return None
    if values: #if not None, then divTSC wasn't overwritten by another TimeSeriesCont
        #set the values of the time series
        divTSC.values = values
    return divTSC

def computeInflowTSC(network, resvName, outflowTSC, elevTSC, minFlow = -9999999, initFlow = None):
    """
    Function to compute the inflow to a reservoir, given a timeseries of
    known reservoir elevation and known outflows. Outflows should be period-average
    and elevations should be instantaneous values, and should be of exactly the
    same length. The very first value of inflow is impossible to compute, since
    we would need to know the initial reservoir elevation prior to the beginning
    of the time window.  
    
    :param RssSystem network: the network to use stor-elev tables from
    :param str resvName: the exact name of the reservoir (case-sensitive)
    :param TimeSeriesContainer outflowTSC: the TSC with reservoir outflows
    :param TimeSeriesContainer elevTSC:    the TSC with reservoir elevs
    :param float minFlow: (Optional) If specified, then calculated inflow will be at least this large
    :param float initFlow: (Optional) If specified, the inflow for the first timestep to use. 
                     If omitted, the first value from outflowTSC will be used. 
    :return: Calculated TimeSeriesContainter of reservoir inflow
    """
    #Check that resv exists
    resvElem = network.findReservoir(resvName)
    if resvElem is None: 
        logging.error("Error: Failed to find the case-sensitive reservoir: %s" %resvName)
        return None
    #Get elev-stor table
    elevStorTable = getElevationStorageTable(resvName, network)
    #Check to see the length of TSC is the same
    if elevTSC.numberValues != outflowTSC.numberValues: 
        logging.error("Error: Reservoir outflows and elevations don't span the same time window")
        return None
    #Find the timeseries interval in seconds
    if outflowTSC.interval <= 0: 
        logging.error("Error: Data must be regular interval!")
        return None #can't handle irregular data
    stepSeconds = outflowTSC.interval*60.       # interval is in minutes
    acFtTocfs = 43560./stepSeconds #conversion factor
    #Loop through all timesteps, calculating the inflow
    outflows = outflowTSC.values
    elevs = elevTSC.values
    stors = [] #list of resv storage corresponding to elevations
    inflows = []
    for i in range(len(elevTSC.times)):
        stors.append(elevStorTable.interpolate(elevs[i]))
        if outflows[i] == Constants.UNDEFINED or elevs[i] == Constants.UNDEFINED:
            logging.error("Error: Undefined value for outflow or elevation at index: %s" %i)
            return None
        if i == 0 :
            if initFlow == None: #no default defined, use the input data
                inflow = outflows[i]
            else: #use the default defined
                inflow = initFlow
        else: #actually compute using mass balance
            inflow = outflows[i] + (stors[i] - stors[i-1])*acFtTocfs
        inflow = max(inflow, minFlow) #cap to a minimum amount if desired
        inflows.append(inflow)
    inflowTSC = outflowTSC.clone() #keep all the metadata consistent
    inflowTSC.fileName = ""
    inflowTSC.values = inflows
    return inflowTSC
