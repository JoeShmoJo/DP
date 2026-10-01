"""
This module contains functionality to perform high level tasks that need to  
access to a ResSim watershed for information. 
This often includes reading a .csv or .txt file for instructions or a list of 
pathnames, and then performing some analysis with it.
While these tasks could be stored in :any:`cResSim`, this would clog up that module.
Rather, they are stored here and access much of the functionality in :any:`cResSim`
and :any:`ResSimController`. 
This module contains many of these "higher level" functions.
"""

from hec.script import Plot
from hec.hecmath import DSS, DSSFileException, HecMathException, TimeSeriesMath
from hec.lang import DSSPathString
from hec.heclib.dss import DSSPathname
from hec.rss.model import ReservoirElement, JunctionElement, ReachElement, DiversionElement
from hec.rss.model import RssModelVariableConstants
from hec.rss.model import ReservoirDamElement
import os, sys, logging

#Custom modules
from NWDJyLib import cRouting
from NWDJyLib import cFile
from NWDJyLib.ResSim import cResSim
from NWDJyLib.ResSim import ResSimController
from NWDJyLib.DSS import cTsUtils
from NWDJyLib.DSS import cDSS
from NWDJyLib.DSS import cCollections
from NWDJyLib.FixedData import NameAlias

################################################################################
# STATIC INPUT
naturalLakes = ["Corra Linn", "Arrow Lakes", "SKQ", "Albeni Falls", "Post Falls"] #ALERT, hard coded!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

################################################################################
# CLASS DEFINITIONS

# END OF CLASS DEFINITIONS
################################################################################
# FUNCTION DEFINITIONS

def recomputeResvInflows(altName, csvFile, outDssFile, tsInt, fPart, bar, txtArea,
    overrideObsDssFile=None, omitFirstInflow=False, toAlias=None):
    """
    Function to recompute the inflow data for selected reservoirs, using 
    known outflow and elevations (as mapped in the ResSim Observed Data)
    The output DSS pathnames will have a B-part of the reservoir name in ResSim,
    and a C-part of "FLOW-IN". Uses the :any:`cResSim.computeInflowTSC` function.
    
    :param str altName: The alternative to use to get the time series mapping (e.g "Observed")
    :param str csvFile: The CSV file that contains which projects to do this for
    :param str outDssFile: Pathname to the desired output file
    :param str tsInt: Desired output time step (e.g. "1HOUR" or "1DAY")
    :param str fPart: The f-part to put on the output pathname
    :param JProgressBar bar: 
    :param JTextArea txtArea: Must have a function defined called "printToGUI"
    :param str overrideObsDssFile: If provided, all elevation/outflow data will
           attempt to be read from this file, rather than the DSS file that is
           present in the Observed Data time series mapping tab
    :param boolean omitFirstInflow: If true, the very first value in the inflow
           timeseries will be omitted from the output, since it is not a real
           value anyway. The default is false, which will return an inflow time
           series of exactly the same length as the input.
    :param str toAlias: If specified, the B-part of the output will be renamed
           from the ResSim reservoir to any valid other location code from :any:`NameAlias`
           e.g. "CBT_CODE". If not provided, the ResSim reservoir name will be used.
    :return: A list of TimeSeriesMath objects of all the calculated inflows
    """
    msg = "----------------------------------------------------------------------"
    msg += "\nComputing Selected Reservoir Inflows"
    #The below line throws an error when .printToGUI is called (very mysterious)
    #msg += "\nInput CSV File: %s" %csvFile
    msg += "\nOutput DSS File: %s\n" %outDssFile
    msg += "\nTime step:       %s\n" %tsInt
    msg += "\nOmit first inflow? %s\n" %omitFirstInflow
    if overrideObsDssFile:
        msg += "\nUsing override observed data file: %s\n" %overrideObsDssFile
    if toAlias:
        msg += "\nWill attempt to rename to type: %s\n" %toAlias
    txtArea.printToGUI(msg)
    logging.info(msg)
    #Open up the reservoir network
    simPeriod = ResSimController.getSimulation()
    startTime, endTime, lookbackTime = ResSimController.getSimulationTimes(simPeriod)
    logging.info("Time Window: %s to %s" %(lookbackTime, endTime))
    run = simPeriod.getSimulationRun(altName) #RssSimRun
    if run is None:
        errMsg = "No alternative exists named: %s" %altName
        txtArea.printToGUI(errMsg)
        logging.error(errMsg)
        return None
    alt = run.getRssAlt() #RssAlt
    #tsInt = alt.getTimeStepString() #e.g. 1HOUR, 1DAY
    network = ResSimController.getNetwork(run)
    # Get the locations where observed data is defined (all types)
    obsTSDataSet = alt.getObservedTSDataSet()
    #open output files
    outDss = DSS.open(outDssFile, lookbackTime, endTime)
    ######################
    ##Process the CSV file
    msg = "Processing file: " + csvFile + "\n"
    logging.info(msg)
    lines = cFile.fileOpenReadClose(csvFile)
    lines = cFile.stripOutCommentLines(lines)
    #Create a dictionary to save all opened DSS files so we don't have to close/reopen
    dssDict = {}
    #OK, now actually process the csv file
    currentTSM = None
    inflowTSMs = []
    for i in range(len(lines)): 
        fields = lines[i].split(",")
        resvName = fields[0].strip()
        minFlow = fields[1].strip()
        bar.setValue(int(float(i)/len(lines)*100))
        msg = "Processing: %s" %resvName
        try:
            minFlow = float(minFlow)
            #It really is an input number, show it
            msg +=", MinFlow: %s" %minFlow
        except ValueError:
            minFlow = ""
        if minFlow == "": minFlow = -9999999
        logging.info(msg)
        txtArea.printToGUI(msg)
        ################################################
        #Attempt to locate the observed elevation data
        resvElem = network.findReservoir(resvName)
        if resvElem is None:
            errMsg = "No Reservoir in the network named: %s" %resvName
            txtArea.printToGUI(errMsg)
            logging.error(errMsg)
            return None
        #obsVec = resvElem.getObsDataVector() # vector of strings (e.g. "~E2903:F:10")
        #The key value stored in the Observed .fits file is something like "~E2903:F"
        rssConstant = RssModelVariableConstants.VID_POOL_ELEV
        #Get the TSRecord object for the variable
        tsRec = cResSim.getTSRecord(obsTSDataSet, resvElem, rssConstant, txtArea, isStrict=True, displayMessages=True)
        if tsRec is None:
            errMsg = "\nCouldn't locate observed elevations for: %s" %resvName
            errMsg += "\nMust have Pool Elevation checked in the 'Observed Data'"
            errMsg += "\n tab of the Reservoir Editor"
            txtArea.printToGUI(errMsg)
            logging.error(errMsg)
            return None
        obsPath = tsRec.getDSSPathname() #pathname of observed data
        if overrideObsDssFile:
            #Use the override file instead of the file in the time series mapping
            obsDssFilename = overrideObsDssFile
        else:
            #Use the DSS file specified in the time series mapping
            obsDssFilename = tsRec.getDSSFilename()
            obsDssFilename = network.makeAbsolutePathFromWatershed(obsDssFilename)
        if len(obsPath) == obsPath.count("/") or obsDssFilename == "": #blank pathname
            errMsg = "\tBlank Pathname--need to map in an observed elevation pathname at: %s" %resvName
            txtArea.printToGUI(errMsg)
            logging.error(errMsg)
            return None
        #should be able to read the timeseries
        if not dssDict.has_key(obsDssFilename): #open and add to the list
            #Open the file and add it to the dictionary
            logging.info("Opening Dss File: %s" %obsDssFilename)
            openedDssFile = DSS.open(obsDssFilename, lookbackTime, endTime)
            dssDict[obsDssFilename] = openedDssFile
        #Grab the opened DSS file
        obsDss = dssDict[obsDssFilename]
        try:
            obsElevTSM = obsDss.read(obsPath)
        except (DSSFileException, HecMathException): # Couldn't find the DSS path
            errMsg =  "ERROR IN READING OBSERVED DATA: COULD NOT READ PATHNAME:"
            errMsg += "\n%s\nFROM DSS FILE: %s\n" %(obsPath, obsDss.getFilename())
            errMsg += "\nProbably need to retrieve/map in the correct observed data"
            logging.error(errMsg)
            txtArea.printToGUI(errMsg)
            return None 
        #Convert to the alternative timestep (observed data may not be consistent timestep)
        obsElevTSM = cTsUtils.transformTSM(obsElevTSM, tsInt)
        ###########################################
        #We now have the elevation time series--now get the outflow time series
        #It should be mapped at the downstream junction
        juncElem = resvElem.getDownstreamNode().getDownstreamElement()
        juncName = str(juncElem)
        logging.debug("Looking for observed outflow at: %s" %juncName)
        #obsVec = juncElem.getObsDataVector() # vector of strings (e.g. "~N36")
        rssConstant = RssModelVariableConstants.VID_NODE_FLOW
        tsRec = cResSim.getTSRecord(obsTSDataSet, juncElem, rssConstant, txtArea, isStrict=True, displayMessages=True)
        if tsRec is None:
            errMsg = "\nCouldn't locate observed outflows for: %s" %resvName
            errMsg += "\nMust have 'Observed Data' defined at the outflow Junction: %s" %juncName
            txtArea.printToGUI(errMsg)
            logging.error(errMsg)
            return None
        obsPath = tsRec.getDSSPathname() #pathname of observed data
        if overrideObsDssFile:
            #Use the override file instead of the file in the time series mapping
            obsDssFilename = overrideObsDssFile
        else:
            #Use the DSS file specified in the time series mapping
            obsDssFilename = tsRec.getDSSFilename()
            obsDssFilename = network.makeAbsolutePathFromWatershed(obsDssFilename)
        if len(obsPath) == obsPath.count("/") or obsDssFilename == "": #blank pathname
            errMsg = "\tBlank Pathname--need to map in an observed outflow pathname at: %s" %juncName
            txtArea.printToGUI(errMsg)
            logging.error(errMsg)
            return None
        else: #should be able to read the timeseries
            if not dssDict.has_key(obsDssFilename): #open and add to the list
                #Open the file and add it to the dictionary
                logging.info("Opening Dss File: %s" %obsDssFilename)
                openedDssFile = DSS.open(obsDssFilename, lookbackTime, endTime)
                dssDict[obsDssFilename] = openedDssFile
            #Grab the opened DSS file
            obsDss = dssDict[obsDssFilename]
            try:
                obsOutflowTSM = obsDss.read(obsPath)
            except (DSSFileException, HecMathException): # Couldn't find the DSS path
                errMsg =  "ERROR IN READING OBSERVED DATA: COULD NOT READ PATHNAME:"
                errMsg += "\n%s\nFROM DSS FILE: %s\n" %(obsPath, obsDss.getFilename())
                errMsg += "\nProbably need to retrieve/map in the correct observed data"
                logging.error(errMsg)
                txtArea.printToGUI(errMsg)
                return None 
        #Convert to the alternative timestep (observed data may not be consistent timestep)
        obsOutflowTSM = cTsUtils.transformTSM(obsOutflowTSM, tsInt)
        ####################################################
        #We have observed elevation and outflow--calculate the inflow
        inflowTSC = cResSim.computeInflowTSC(network, resvName, obsOutflowTSM.getData(), \
         obsElevTSM.getData(), minFlow = minFlow, initFlow = None)
        if omitFirstInflow:
            #The first inflow value is wonky since we can't look backwards in
            #time to see the previous reservoir elevation
            #Simply omit the first value
            inflowTSC.times = inflowTSC.times[1:]
            inflowTSC.values = inflowTSC.values[1:]
            inflowTSC.numberValues = len(inflowTSC.values) 
            inflowTSC.startTime = inflowTSC.times[0]
            inflowTSC.endTime = inflowTSC.times[-1] 
        inflowTSM = TimeSeriesMath(inflowTSC)
        bPart = resvName
        if toAlias:
            #Want to convert the B-part 
            bPart = NameAlias.myLocationAlias.lookup(bPart, "RESSIM_NAME", toAlias)
            if bPart is None:
                logging.warning("Failed to rename the b-part: %s" %bPart)
                logging.warning("Make sure the reservoir is defined in LocationAlias.csv")
                bPart = resvName
        cPart = "FLOW-IN"
        #tsInt = DSSPathString(obsOutflowTSM.getPath()).getEPart() #e.g. 1HOUR
        # Set up the output timeseries pathname and write it out
        outputPath = "//%s/%s//%s/%s/" %(bPart, cPart, tsInt, fPart)
        inflowTSM.setPathname(outputPath)
        outDss.write(inflowTSM) 
        msg = "\tOutput path: %s" %outputPath
        logging.info(msg)
        inflowTSMs.append(inflowTSM)
        inflowTSM = None
    #Close all DSS Files
    outDss.close()
    for dssFile in dssDict.values(): dssFile.close()
    #Print out final messages
    msg = "\nDONE CALCULATING RESERVOIR INFLOWS!"   
    logging.info(msg)
    txtArea.printToGUI(msg)
    bar.setValue(100)
    return inflowTSMs
    
def computeFlows(computeMode, network, altName, outDssFile, negs, bar, txtArea,
    overrideObsDssFile=None, outFPart="UNREG"):
    """
    Uses a ResSim network to route flows downstream and calculate some flows.
    
    When the compute mode is "LOCAL":
    
        Compute the incremental local flows, provided only observed flows.
        Will use the pathnames mapped in as "observed flows" to calculate the locals.
        The pathnames specified in the input Time Series mapping tab will be used 
        to figure out what to output the pathnames as.
        Assumes all local flows in the "Time Series" tab of ResSim 
        are mapped to the same input dss file (outDssFile).
        Output will not be echoed to simulation.dss--you need to rerun the extract after this.
        The local flows/observed flows can have variable time intervals (EParts), no problem.
        See the AFDR SOP for more details and a flowchart of the process.
    
    When the compute mode is "UNREG":
    
        Computes unregulated flows for the alternative. This mode does not use
        any data in the "Observed Data" tab. It assumes all local flows are fully
        defined in the Time-Series tab, and is strict about it, throwing an error
        if any are not fully defined. It will skip pathnames that are completely blank, though.
        Returns a list of TimeSeriesContainer objects for unregulated flows
        at all reservoirs and junctions.
        The unreg mode does not actually write the data out to DSS--you must do
        that afterwards using the return value.

    :param str computeMode: The type of compute to perform. Currently the only 
                            supported arguments are "LOCAL" and "UNREG"
    :param RssSystem network: the currently open network
    :param str altName: The alternative to use to get the time series mapping (e.g "Observed")
    :param str outDssFile: Pathname to the desired output file
    :param boolean negs: True if negatives are allowed, false if negatives are not allowed
    :param JProgressBar bar: 
    :param JTextArea txtArea: Must have a function defined called "printToGUI"
    :param str overrideObsDssFile: If provided, all flow data will
        attempt to be read from this file, rather than the DSS file that is
        present in the Observed Data time series mapping tab. If this is supplied,
        the "DSS file" column of the observed data and headwater locations must
        be left blank.
    :param str outFPart: The output f-part for the unregulated flow time series.
        This parameter is not applied if local flows are being calculated.
        Default is "UNREG"
    :return: A list of TimeSeriesContainer objects that were calculated
    """
    isStrict = False #possibly an input parameter later, whether we need all observed flows mapped in
    msg = "----------------------------------------------------------------------"
    if "UNREG" in computeMode.upper():
        computeUnregs = True
        computeLocals = False
        msg += "\nComputing Unregulated Flows"
        txtArea.printToGUI("Computing Unregulated Flows...")
    else:
        #Assume local flow
        computeUnregs = False
        computeLocals = True
        msg += "\nComputing Incremental Local Flows"
        msg += "\nNegative Locals allowed (1 if true)? : %s" %negs
        txtArea.printToGUI("Computing Incremental Local Flows...")
    msg += "\nOutput DSS File:                       %s" %outDssFile
    logging.info(msg)

    confJuncs = cResSim.getConfluenceJunctions(network)
    confResvDict = cResSim.getConfluenceResvPoolDict(network)
    confResvs = confResvDict.keys() #pool Element, not ReservoirElement
    hwJuncs = cResSim.getRealHeadwaterJunctions(network)
    orderedElements = cResSim.orderElementsFromUpstream(network)
    simPeriod = ResSimController.getSimulation() #SimulationPeriod
    alt = ResSimController.getSpecificRun(simPeriod, altName).getRssAlt() #RssAlt
    tsInt = alt.getTimeStepString() #e.g. 1HOUR, 1DAY
    rtw = simPeriod.getRunTimeWindow()
    startTime, endTime, lookbackTime = ResSimController.getSimulationTimes(simPeriod)
    logging.info("Time Window: %s to %s" %(lookbackTime, endTime))
    # Get the observed data mapping
    obsTSDataSet = alt.getObservedTSDataSet() #TSDataSet
    # Get the input time series mapping
    inputTSDataSet = alt.getInputTSDataSet() #TSDataSet
        
    #Open up all input DSS Files first--create a dictionary of opened DSS Files
    dssDict = {}
    if overrideObsDssFile:
        #Want to use an override DSS file for all records where the DSS file is blank
        openedDssFile = cDSS.openDSSFile(overrideObsDssFile, lookbackTime, endTime)
        rootDir = network.makeAbsolutePathFromWatershed("")
        dssDict[""] = openedDssFile
        dssDict[rootDir] = openedDssFile
        dssDict[overrideObsDssFile] = openedDssFile
    #Now loop through all DSS files defined in timeseries mapping
    if computeLocals:
        #If computing locals, need both observed and input timeseries
        tsRecs = list(obsTSDataSet.getTSRecords()) + list(inputTSDataSet.getTSRecords())
    else:
        #Just need input timeseries
        tsRecs = list(inputTSDataSet.getTSRecords())
    for tsRec in tsRecs:
        dssFile = tsRec.getDSSFilename()
        dssFile = network.makeAbsolutePathFromWatershed(dssFile)
        if dssFile != "" and dssFile not in dssDict.keys():
            #Open the file and add it to the dictionary
            logging.info("Opening Dss File: %s" %dssFile)
            openedDssFile = cDSS.openDSSFile(dssFile, lookbackTime, endTime)
            dssDict[dssFile] = openedDssFile
    #Check out all input time series to make sure they are fully defined
    #Get a "bank" of time series math objects that have been read from DSS--don't have to read twice
    #Need to convert everything into a consistent time interval (alternative timestep)
    #Input data can be mapped as anything (1HOUR, 1DAY, 30MIN)--need to convert
    txtArea.printToGUI("Loading input timeseries...")
    tsBank = cResSim.tsmBank()
    obsMsg = ""
    if computeLocals: #Only need to load in observed data if calculating local flows
        obsMsg = tsBank.checkInTimeSeries(dssDict, obsTSDataSet, lookbackTime, endTime, 
         ignoreDssFile = outDssFile, rssConstant = RssModelVariableConstants.VID_NODE_FLOW, tsInt = tsInt)
    stdMsg = tsBank.checkInTimeSeries(dssDict, inputTSDataSet, lookbackTime, endTime, 
     ignoreDssFile = outDssFile, rssConstant = RssModelVariableConstants.VID_NODE_KNOWNFLOW, tsInt = tsInt)
    if obsMsg != "" or stdMsg != "":
        tsBank.close()
        errMsg = "ERROR: Not all time series are fully defined!"
        errMsg +="\nNeed to go back and check the data"
        if obsMsg != "":
            errMsg +="\nObserved Time Series Mapping problems:"
            errMsg += obsMsg
        if stdMsg != "":
            errMsg +="\nNormal Time Series Mapping problems:"
            errMsg += stdMsg
        logging.error(errMsg)
        txtArea.printToGUI(errMsg)
        return None
    txtArea.printToGUI("All input timeseries look good!")
    #open output files
    outDss = cDSS.openDSSFile(outDssFile, lookbackTime, endTime)
    # dictionary of timeseries containers for tributary routed flows
    tribFlows = {} #keys are Elements of some sort (e.g. Reach), values are TSCs 
    #list to store all of the calculated output flows
    outTSCs = []
    #Proceed through all elements, saving "workingTSM" as the current state of the routed flow
    for i in range(len(orderedElements)):
        bar.setValue(int(float(i)/len(orderedElements)*100))
        element = orderedElements[i]
        if element == None: continue
        elemName = str(element)
        nodes = element.getNodeVector()
        if isinstance(element, ReservoirElement):
            pass #do nothing for reservoirs
        if elemName == "Pool": #reservoir pool element
            resvElem = element.getParent() #To get the ReservoirElement, need to do a .getParent() call
            resvName = resvElem.toString()
            if element in confResvs:
                # If the junction is a confluence reservoir, add in the flow from upstrm junctions
                logging.debug("\tIt's a confluence reservoir")
                upstreamJunctions = confResvDict[element]
                for juncElem in upstreamJunctions:
                    if tribFlows.has_key(juncElem):
                        workingTSM = workingTSM.add(tribFlows[juncElem])  #timewindow previously checked
                        logging.debug("added %s" %juncElem)
                    else:
                        # The upstream junction flow should already exist
                        errMsg = "ERROR: At confluence reservoir: %s" %element.getParent()
                        errMsg +="\nCouldn't locate input flow time series for Junction: %s" %juncElem
                        logging.error(errMsg)
                        txtArea.printToGUI(errMsg)
                        return None
            if computeUnregs:
                #If computing unregulated flows, save off the flow
                unregTSC = workingTSM.getData()
                unregTSC = cTsUtils.prepareTSCont(unregTSC.values, unregTSC.times,
                    resvName, "FLOW-UNREG", tsInt, outFPart, unregTSC.units, unregTSC.type)
                #unregTSC = cDSS.writeTSC(unregTSC, outDss)
                outTSCs.append(unregTSC)
        if isinstance(element, JunctionElement):
            logging.info("Junction: %s" %elemName)
            divElems = cResSim.getConnectedDiversions(element)
            if divElems: #there is a diversion, deduct it
                for divElem in divElems:
                    logging.info("\tDiversion found: %s" %divElem)
                    divTSC = cResSim.getDiversionTSC(divElem, rtw, inputTSDataSet, overrideObsDssFile)
                    if divTSC is None:
                        errMsg = "\tCouldn't retrieve a time series for Diversion: %s" %divElem
                        logging.warning(errMsg)
                    else:
                        #deduct the diversion
                        logging.debug("\tSubtracting diversion flows")
                        #Convert to the alternative time step
                        divTSM = TimeSeriesMath(divTSC)
                        divTSM = cTsUtils.transformTSM(divTSM, tsInt)
                        workingTSMVals = len(workingTSM.getContainer().values)
                        divTSC = divTSM.getData()
                        '''
                        Now that TSM are used instead of TSC, don't need to be as careful with time window
                        if workingTSMVals != len(divTSC.values):
                            errMsg = "\tIncomplete time series defined for diversion: %s" %divElem
                            logging.error(workingTSMVals)
                            logging.error(len(divTSC.values))
                            logging.error(errMsg)
                            txtArea.printToGUI(errMsg)
                            return None
                        '''
                        workingTSM = workingTSM.subtract(divTSM)
                divTSC = None
            if element in confJuncs:
                # If the junction is a confluence junction, add in the flow from upstrm reaches 
                logging.debug("\tIt's a confluence junction")
                upstreamReaches = list(cResSim.getConnectedReaches(element))
                for rch in upstreamReaches:
                    if tribFlows.has_key(rch):
                        workingTSM = workingTSM.add(tribFlows[rch])  #timewindow previously checked
                        logging.debug("added %s" %rch)
                    else:
                        # probably the downstream reach, skip it
                        logging.debug("%s: Downstream reach" %rch)
                        continue
            #########################################################
            #Read observed flow data, if it exists
            # Script ASSUMES THERE IS ONLY ONE OBSERVED DATASET PER LOCATION (total flow)
            obsTSM = None #will get defined if observed data is read
            tsRecObs = None
            #obsVec = element.getObsDataVector() # vector of strings (e.g. "~N36:0")
            if computeLocals:
                #Only need to get observed data if calculating locals
                rssConstant = RssModelVariableConstants.VID_NODE_FLOW
                # get the total observed flow at the junction
                tsRecObs = cResSim.getTSRecord(obsTSDataSet, element, rssConstant, txtArea, isStrict=True, displayMessages=False)
                logging.debug("\tTSRecord: %s" %tsRecObs)
                if tsRecObs: #the box is checked in the Junction Editor
                    obsPath = tsRecObs.getDSSPathname()
                    obsDssFilename = tsRecObs.getDSSFilename()
                    obsDssFilename = network.makeAbsolutePathFromWatershed(obsDssFilename)
                    #if overrideObsDssFile:
                    #No need to override the filename, since the tsmBank should have a key in it for an empty string
                    #    obsDssFilename = overrideObsDssFile
                    if len(obsPath) == obsPath.count("/"): #blank pathname
                        msg = "\tBlank Pathname--not using an observed total flow TS at: %s" %elemName
                        logging.warning(msg)
                        txtArea.printToGUI(msg)
                        if isStrict: 
                            errMsg = "Observed flow is expected, but there is no input pathname at: %s" %elemName
                            errMsg += "\nThere must be no blank lines in the 'Observed Data' tab!"
                            logging.error(errMsg)
                            txtArea.printToGUI(errMsg)
                            return None
                    else: #should be able to read the timeseries
                        #withdraw from the bank instead of reading again
                        obsTSM = tsBank.withdrawTS(obsDssFilename, obsPath)
            ##########################################################################
            # We have retrieved the observed flow if it exists (obsTSM is None otherwise)
            # Now cycle through the local flows defined 
            # Can handle multiple local flows, but only at locations without observed flows
            #In ResSim, there is a separate node for each local flow
            factor = 1. # default, inflow multiplier factor
            rssConstant = RssModelVariableConstants.VID_NODE_KNOWNFLOW
            for node in nodes: #One local flow per node in ResSim
                # skip downstream elements
                if str(node.getDownstreamElement()) != elemName: continue
                #Local flow nodes have no upstream element
                if node.getUpstreamElement(): continue #must be a connected element, skip it
                logging.debug("\tNode: %s" %node)
                #tsrps = node.getTSRecordProxies() 
                tsrp = node.getTSRecordProxy(RssModelVariableConstants.VID_NODE_KNOWNFLOW)
                if tsrp:
                    # The TSRecordProxy corresponds to a local inflow location
                    # Retrieve the input pathname of the local flow record so that if
                    # we write out the local flow, it will have the right pathname
                    logging.debug("\t\tTSRP: %s" %tsrp.getName())
                    factor = tsrp.getFactor() # local inflow multiplier is attached to the proxy
                    tsRec = cResSim.getTSRecord(inputTSDataSet, node, rssConstant, txtArea, isStrict=False, displayMessages=False)
                    if not tsRec:
                        #It hasn't been properly saved to the network--it doesn't exist, even though it should
                        errMsg = "Failed to locate local inflow information for: %s" %tsrp.getName()
                        errMsg += "\nMap a fake time series in here, save the time series mapping,"
                        errMsg += "\n and then clear out the fake time series. The network just needs"
                        errMsg += "\n to be reconfigured at this location"
                        logging.error(errMsg)
                        txtArea.printToGUI(errMsg)
                        return None
                    locFlowPath = tsRec.getDSSPathname()
                    locFlowTsInt = DSSPathString(locFlowPath).getEPart()
                    locFlowDssFilename = tsRec.getDSSFilename()
                    locFlowDssFilename = network.makeAbsolutePathFromWatershed(locFlowDssFilename)
                    #Check to see if observed data is defined for this local flow (not the total flow, the local flow)
                    obsLocalTSM = None
                    if computeLocals:
                        #Only necessary to get observed locals if calculating locals
                        #Observed data for local flows is just FLOW, not KNOWNFLOW
                        tsRecObsLocal = cResSim.getTSRecord(obsTSDataSet, node, 
                            RssModelVariableConstants.VID_NODE_FLOW, txtArea, 
                            isStrict=False, displayMessages=False
                            )
                        if tsRecObsLocal:
                            #There is observed data mapped in to the local flow (the box is checked)
                            #Read it in if it exists
                            obsPathLocal = tsRecObsLocal.getDSSPathname()
                            obsLocalDssFilename = tsRecObsLocal.getDSSFilename()
                            obsLocalDssFilename = network.makeAbsolutePathFromWatershed(obsLocalDssFilename)
                            if len(obsPathLocal) == obsPathLocal.count("/"): #blank pathname
                                msg = "\tBlank Pathname--not using an observed local flow TS at: %s" %elemName
                                logging.warning(msg)
                                txtArea.printToGUI(msg)
                                if isStrict: 
                                    errMsg = "Observed local flow is expected, but there is no input pathname at: %s" %elemName
                                    errMsg += "\nThere must be no blank lines in the 'Observed Data' tab!"
                                    logging.error(errMsg)
                                    txtArea.printToGUI(errMsg)
                                    return None
                            else: #should be able to read the timeseries
                                #withdraw from the bank instead of reading again
                                obsLocalTSM = tsBank.withdrawTS(obsLocalDssFilename, obsPathLocal)
                    if obsLocalTSM:
                        #Observed local flow exists here
                        #Add it to the working flow
                        #If there is an entry for the local flow in the inputTSDataSet,
                        #then write out the observed local flow as the input local flow pathname
                        # Try to echo the input before we apply the local inflow factor
                        if len(locFlowPath) == locFlowPath.count("/"):
                            #blank pathname, don't write it out
                            msg = "\t\tBlank Local Flow Pathname--not writing observed local flow"
                            logging.warning(msg)
                            txtArea.printToGUI(msg)
                        else:
                            #Write it out to the local flow
                            # Convert back to the input pathname timestep for writing
                            obsTSMToWrite = cTsUtils.transformTSM(obsLocalTSM, locFlowTsInt)
                            obsTSCToWrite = obsLocalTSM.getData()
                            obsTSCToWrite = cDSS.writeTSC(obsTSCToWrite, outDss, locFlowPath)
                            outTSCs.append(obsTSCToWrite)
                            msg = "Local Flow (observed) at: %s" %tsrp.getName()
                            txtArea.printToGUI(msg)
                            logging.info(msg)
                        # Now that we've written it out, we can apply inflow factor and add it in
                        obsLocalTSM = obsLocalTSM.multiply(factor)
                        workingTSM = workingTSM.add(obsLocalTSM)
                    if obsTSM: #observed data exists for total flow here--use it
                        # EXPECTING ONLY ONE LOCAL FLOW AT LOCATIONS WITH OBSERVED FLOW, NOT MULTIPLE!!!!
                        obsTSM.setType("PER-AVER") #not INST-VAL
                        if len(locFlowPath) == locFlowPath.count("/"):
                            #blank pathname, just reset flow to observed flow
                            msg = "\t\tBlank Local Flow Pathname--not calculating local flow"
                            logging.warning(msg)
                            txtArea.printToGUI(msg)
                            obsTSC = obsTSM.getData()
                        elif element in hwJuncs:
                            # if the junction is a headwater junction, just write out the observed flow as local
                            logging.debug("\t It's a headwater junction, echoing observed flow")
                            # Need to echo the input before we apply the local inflow factor
                            # Convert back to the input pathname timestep for writing
                            obsTSMToWrite = cTsUtils.transformTSM(obsTSM, locFlowTsInt)
                            obsTSCToWrite = obsTSM.getData()
                            obsTSCToWrite = cDSS.writeTSC(obsTSCToWrite, outDss, locFlowPath)
                            outTSCs.append(obsTSCToWrite)
                            # Now that we've written it out, we can apply inflow factor
                            obsTSC = obsTSM.getData()
                            obsTSC = obsTSM.multiply(factor).getData()
                        else:
                            # the junction is not a headwater junction
                            # subtract off the routed working flow from the total observed flow 
                            # at this location, and that's your local
                            msg = "Local Flow at: %s" %elemName
                            txtArea.printToGUI(msg)
                            logging.info(msg)
                            obsTSC = obsTSM.getData()
                            locTSC = obsTSM.subtract(workingTSM).getData()
                            if not negs: # negative flows not allowed, need to apportion the negative flows
                                # Don't write out the negative flows--if the user wants, they can recompute
                                '''
                                negLocFlowPath = DSSPathString(locFlowPath)
                                negLocFlowPath.setFPart(negLocFlowPath.getFPart() + "-WITH_NEGATIVES_ALLOWED")
                                cDSS.writeTSC(locTSC, outDss, negLocFlowPath.getPathname())
                                '''
                                locTSC = cTsUtils.removeNegativeLocals(locTSC)
                            # Convert back to the input pathname timestep for writing
                            locTSM = TimeSeriesMath(locTSC)
                            locTSM = cTsUtils.transformTSM(locTSM, locFlowTsInt)
                            locTSCToWrite = locTSM.getData()
                            locTSCToWrite = cDSS.writeTSC(locTSCToWrite, outDss, locFlowPath)
                            outTSCs.append(locTSCToWrite)
                        workingTSM = obsTSM.copy() 
                    elif tsRecObs:
                        #There is a blank entry for this observed flow location
                        #Do not add in any local flow, because all of the local should go downstream!
                        logging.info("\t\tNormally there is observed total flow at %s, but not mapped in. Not adding local flow" % elemName)
                    elif obsLocalTSM is None: 
                        #There truly is no observed data expected at this location
                        #Attempt to add in the local flow from the input dss file, if it exists
                        msg = "\t\tNo Observed Data found for %s" %tsrp.getName() 
                        logging.info(msg)
                        txtArea.printToGUI(msg)
                        if len(locFlowPath) == locFlowPath.count("/"): #blank pathname
                            msg = "\t\tBlank Local Flow Pathname--not adding local flow"
                            logging.warning(msg)
                            txtArea.printToGUI(msg)
                        else: #should be able to read the timeseries
                            #withdraw from the bank instead of reading again
                            locFlowTSM = tsBank.withdrawTS(locFlowDssFilename, locFlowPath)
                            if locFlowTSM is None: #couldn't find the DSS path
                                errMsg =  "ERROR IN READING LOCAL FLOW DATA: COULD NOT READ PATHNAME:"
                                errMsg += "\n%s\nFROM DSS FILE: %s\n" %(locFlowPath, locFlowDssFilename)
                                errMsg += "\nSince there is no observed flow defined here, assuming this local flow has already been defined"
                                logging.error(errMsg)
                                txtArea.printToGUI(errMsg)
                                return None
                            locFlowTSM = locFlowTSM.multiply(factor)
                            locFlowTSC = locFlowTSM.getData()
                            if element in hwJuncs: #use the data directly
                                msg = "\t\tUsing input local flow: %s" %locFlowPath
                                workingTSM = locFlowTSM.copy()
                            else: #add to the existing flows
                                msg = "\t\tAdding input local flow to the total flow: %s" %locFlowPath
                                workingTSM = workingTSM.add(locFlowTSM) #timewindow previously checked
                            logging.info(msg)
                            txtArea.printToGUI(msg)
            #########################################################################
            # If there is an observed flow mapped in at a point, "reset" the working flow record
            # This occurs at all points that have observed flow defined (e.g. even those withouta local defined (e.g. outlet of a dam)
            if computeLocals:
                #Only necessary when computing local flows
                if obsTSM:
                    msg = "\tObserved flow exists at %s: Resetting flow..." %elemName
                    logging.info(msg)
                    txtArea.printToGUI(msg)
                    obsTSC = obsTSM.getData()
                    workingTSM = obsTSM.copy()
            if computeUnregs:
                #If computing unregulated flows, save off the flow at the junction
                unregTSC = workingTSM.getData()
                unregTSC = cTsUtils.prepareTSCont(unregTSC.values, unregTSC.times,
                    elemName, "FLOW-UNREG", tsInt, outFPart, unregTSC.units, unregTSC.type)
                #unregTSC = cDSS.writeTSC(unregTSC, outDss)
                outTSCs.append(unregTSC)
        elif isinstance(element, ReachElement):
            # If the element is a reach, route the flow to the next junction
            routingObj = element.getFunction()
            logging.info("Reach : %s" %elemName)
            routeReach = cRouting.buildReach(routingObj)
            if routeReach is None:
                errMsg = "The Script cannot handle any routing methods besides SSARR, Muskingum, ModPuls, or Null:"
                errMsg += "\n%s has routing of: %s" %(elemName, routingObj.__class__)
                logging.error(errMsg)
                txtArea.printToGUI(errMsg)
                return None
            logging.debug("\tRouting Type: %s" %routingObj.__class__)
            workingTSM = TimeSeriesMath(routeReach.routeTSC(workingTSM.getData()))
            
        # Need to check if the next point is a confluence
        # If so, need to save off the time series so the confluence can retrieve it
        dsNode = element.getDownstreamNode()
        dsElem = dsNode.getDownstreamElement()
        if dsElem in confJuncs or dsElem in confResvs:
            logging.debug("Saving to Tributary Flow dictionary: %s" %element)
            # Save the flows to the tribFlows dictionary
            tribFlows[element] = workingTSM.copy()          
            # Reset the workingTSM variable to 0
            workingTSM = workingTSM.multiply(0)
    
    tsBank.close()
    #Close all DSS Files
    outDss.close()
    for dssFile in dssDict.values(): dssFile.close()
    msg = "\nCompute Complete!"
    txtArea.printToGUI(msg)
    logging.info(msg)
    bar.setValue(100)
    return outTSCs
    
def computeEnsembleLocalFlows(network, altName, outDssFile, negs, bar, txtArea,
    overrideObsDssFile=None):
    """
    When computing local flows with ensemble data, you need to compute the local
    flows many times (separately for each ensemble year). This function simply
    loops through all ensemble years and calculates local flows using the 
    :meth:`computeFlows` many times. This will manually change the F-part
    of the input time series mapping for each ensemble compute.
    
    :param RssSystem network: the currently open network
    :param str altName: The alternative to use to get the time series mapping (e.g "Observed")
    :param str outDssFile: Pathname to the desired output file
    :param boolean negs: True if negatives are allowed, false if negatives are not allowed
    :param JProgressBar bar: 
    :param JTextArea txtArea: Must have a function defined called "printToGUI"
    :param str overrideObsDssFile: If provided, all flow data will
       attempt to be read from this file, rather than the DSS file that is
       present in the Observed Data time series mapping tab. If this is supplied,
       the "DSS file" column of the observed data and headwater locations must
       be left blank.
    :return: A list of lists of TimeSeriesContainer objects that were calculated locals
             The first list is all of the ensemble TimeSeriesContainer objects for the first local flow location
             The second list is the 2nd location, etc.
    """
    simPeriod = ResSimController.getSimulation() #SimulationPeriod
    alt = ResSimController.getSpecificRun(simPeriod, altName).getRssAlt() #RssAlt
    tsInt = alt.getTimeStepString() #e.g. 1HOUR, 1DAY
    rtw = simPeriod.getRunTimeWindow()
    startTime, endTime, lookbackTime = ResSimController.getSimulationTimes(simPeriod)
    # Get the observed data mapping
    obsTSDataSet = alt.getObservedTSDataSet() #TSDataSet
    # Get the input time series mapping
    inputTSDataSet = alt.getInputTSDataSet() #TSDataSet
    #Detect the ensemble members to be run
    ensembles = None
    for tsRecord in obsTSDataSet.getTSRecords():
        #Loop through all input TS records until one is found that is an ensemble member (e.g. C:001949|)
        dssFileName = tsRecord.getDSSFilename()
        dssFileName = network.makeAbsolutePathFromWatershed(dssFileName)
        if overrideObsDssFile:
            dssFileName = overrideObsDssFile
        path = tsRecord.getDSSPathname()
        if DSSPathname.isaCollectionPath(path):
            dssFile = cDSS.openDSSFile(dssFileName)
            #Retrieve a list of all ensemble members e.g. ["001949", "001950", etc.]
            ensembles = cCollections.getCollectionSequences(dssFile, path)
            dssFile.close()
            break
    if ensembles is None or ensembles == []:
        errMsg = "No ensemble pathnames detected in time series mapping or dss file."
        errMsg += "\nCheck the time series mapping for alternative: %s" %altName
        errMsg += "\nThe F-part of one of the time series should be a DSS collection."
        errMsg += "\nLooked in the following DSS file: %s" %dssFileName
        errMsg += "\nWith the following DSS pathname: %s" %path
        raise AssertionError, errMsg
    #ensembles = ["001949", "001950", "001951"] #for debugging
    logging.info("Detected the following ensemble range: %s-%s" %(ensembles[0],ensembles[-1]))
    ensembleListTSCs = []
    for i, collectionStr in enumerate(ensembles):
        logging.info("Processing Ensemble: %s" %collectionStr)
        #For each ensemble, need to reset the TSDataSet objects f-part
        cCollections.resetTSMappingCollectionFparts(obsTSDataSet, collectionStr)
        cCollections.resetTSMappingCollectionFparts(inputTSDataSet, collectionStr)
        #Now that the input has been reset, calculate the local flows
        outTSCs = computeFlows("LOCAL", network, altName, outDssFile, negs, bar, txtArea,
            overrideObsDssFile)
        if outTSCs is None:
            errMsg = "Failed to calculate local flows..."
            raise AssertionError, errMsg
        if i == 0:
            #First time, need to create a list of the proper length
            ensembleListTSCs = [[] for j in range(len(outTSCs))]
        for j, outTSC in enumerate(outTSCs):
            ensembleListTSCs[j].append(outTSC)
    return ensembleListTSCs
    
def exportRASdataToDss(altName, resvFile, juncFile, dShiftFile, outDssFile, useObsData, bar, txtArea, ratingDssFile = None):
    """
    Function to export data that RAS wants out to an external DSS File.
    RAS doesn't want all of the data, just at selected reservoirs and junctions.
    For reservoirs, RAS wants one of 2 options:
    
        1. The forebay elevation (from observed data, not modeled)
        2. The "natural" elevation at the forebay location, assuming the dam isn't there (uses rating curve)
        
    For junctions, RAS wants the total flow and any local flows.
    The FPart needs to be consistent as well, since the idea is to just swap out
    one of these exported DSS files for another one without having to do re-linking in RAS.
    
    :param str altName: The alternative to use to get the time series mapping (e.g "Observed")
    :param str resvFile:   Pathname to the input text file with list of reservoirs (case-sensitive)
    :param str juncFile:   Pathname to the input text file with list of junctions (case-sensitive)
    :param str dShiftFile: Pathname to tab-delimited text file with datum shifts
    :param str outDssFile: Pathname to the desired output file
    :param boolean useObsData: If true, then "Observed" data will be retrieved when possible
                               and converted to the alternative timestep.
                               When it doesn't exist, ResSim output is used.
                               If false, then ResSim output is always used.
    :param JProgressBar bar: 
    :param JTextArea txtArea: Must have a function defined called "printToGUI"
    :param str ratingDssFile: (Optional) Pathname to dss file with rating curves as paired data
            Rating curves at reservoir locations to simulate "natural" conditions
            If not supplied, then rating curves will not be applied
    """
    fPart = "To RAS" #alert, hard coded
    msg = "----------------------------------------------------------------------"
    msg += "\nExporting Data to DSS for RAS"
    msg += "\nOutput DSS File:                       %s" %outDssFile
    msg += "\nAlternative Name:                      %s" %altName
    msg += "\nInput Reservoir List:                  %s" %resvFile
    msg += "\nInput Junction List:                   %s" %juncFile
    msg += "\nInput Datum Shift List:                %s" %dShiftFile
    msg += "\nUsing Observed Data when possible?     %s" %useObsData
    if ratingDssFile:
        msg += "\nRating Curve DSS File:                 %s" %ratingDssFile
    else:
        msg += "\nNot using any external Rating Curves"
    txtArea.printToGUI("Exporting Data to DSS for RAS...")
    logging.info(msg)
    #########################################
    #Open and process the reservoir, junction, and datum shift files
    #Reservoirs
    msg = "Processing file: " + resvFile + "\n"
    logging.info(msg)
    lines = cFile.fileOpenReadClose(resvFile)
    lines = cFile.stripOutCommentLines(lines)
    resvList = [l.strip() for l in lines]
    #Junctions
    msg = "Processing file: " + juncFile + "\n"
    logging.info(msg)
    lines = cFile.fileOpenReadClose(juncFile)
    lines = cFile.stripOutCommentLines(lines)
    juncList = [l.strip() for l in lines]
    #Datum shifts
    #1st field is CBT code, 2nd field is datum shift from 29 to 88, 3rd field is ResSim name
    msg = "Processing file: " + dShiftFile + "\n"
    logging.info(msg)
    lines = cFile.fileOpenReadClose(dShiftFile)
    lines = cFile.stripOutCommentLines(lines)
    dShiftDict = {} #keys are ResSim names, values are datum shifts
    for l in lines:
        fields = l.strip().split("\t")
        elemName = fields[2].strip() #3rd field
        dShiftStr = fields[1].strip() #2nd field
        try:
            dShift = float(dShiftStr)
        except ValueError:
            errMsg = "%s: Could not convert \"%s\" to a number." %(elemName, dShiftStr)
            logging.error(errMsg)
            txtArea.printToGUI(errMsg)
            return None
        dShiftDict[elemName] = dShift
    ###################################
    #Open up the alternative information
    simPeriod = ResSimController.getSimulation() #SimulationPeriod
    simDssFile = simPeriod.getOutputDSSFilePath()
    run = ResSimController.getSpecificRun(simPeriod, altName) #RssSimRun
    network = ResSimController.getNetwork(run)
    alt = run.getRssAlt() #RssAlt
    tsInt = alt.getTimeStepString() #e.g. 1HOUR, 1DAY
    startTime, endTime, lookbackTime = ResSimController.getSimulationTimes(simPeriod)
    #To get regulated output TSDataSet, need to get at the RssRun object (RssAlt doesn't work)
    rssRunName = run.getKey() #e.g. Test-----0
    #Loading this the first time can take a while...
    rssRunObj = ResSimController.getRssRun(rssRunName) 
    
    ####################################
    # Before we go too far, check the input text files to make sure all elements exist
    failElems = []
    for resvName in resvList:
        if network.findReservoir(resvName) is None: failElems.append(resvName)
    for juncName in juncList:
        if network.findJunction(juncName) is None: failElems.append(juncName)
    if failElems != []:
        msg += "\nThe following elements specified in the text files do not exist in the model:"
        for failElem in failElems: msg += "\n\t%s" %failElem
        logging.error(msg)
        txtArea.printToGUI(msg)
        return None
    # Before we go too far, check to see datum shifts defined at all locations
    for resvName in resvList:
        if not dShiftDict.has_key(resvName): failElems.append(resvName)
    if failElems != []:
        msg += "\nThe following elements specified in the text files"
        msg += "\ndo not have a datum shift properly defined:"
        for failElem in failElems: msg += "\n\t%s" %failElem
        mgs += "\nThese elements must be present in the datum shifts file (case-sensitive)!"
        logging.error(msg)
        txtArea.printToGUI(msg)
        return None
        #OK, all elements should exist in the model
    #Open output files
    msg = "Opening Dss Files:\n  %s\n  %s" %(simDssFile, outDssFile)
    logging.info(msg)
    simDss = DSS.open(simDssFile, lookbackTime, endTime) 
    outDss = DSS.open(outDssFile, lookbackTime, endTime)
    if ratingDssFile: ratingDss = DSS.open(ratingDssFile)
    barCounter = 0
    barDenom = len(resvList) + len(juncList)
    ##################################################################
    #Loop through all reservoirs
    msg = "\nProcessing Reservoirs:"
    txtArea.printToGUI(msg)
    logging.info(msg)
    modeledElevResvs = [] # list to hold reservoirs that we wanted observed data, but used modeled instead
    modeledOutflowResvs = [] # list to hold reservoirs that we wanted observed data, but used modeled instead
    noRatingCurveResvs = [] # list to hold reservoirs that we wanted to use a rating curve, but didn't have one
    for resvName in resvList:
        msg = "  %s" %resvName
        txtArea.printToGUI(msg)
        logging.info(msg)
        bar.setValue(int(float(barCounter)/barDenom*100))
        barCounter += 1
        ###################################
        #Start with reservoir outflow
        #Observed flows are actually mapped in at the outflow junction--get it
        element = network.findReservoir(resvName).getDownstreamNode().getDownstreamElement() #e.g. SKQ_OUT
        rssConstant = RssModelVariableConstants.VID_NODE_FLOW
        tsm = cResSim.getTSMFromSimulationDSS(simDss, element, rssRunObj, rssConstant, txtArea, 
         useObsData = useObsData, isStrict = False, displayMessages = False)
        if tsm is None and useObsData: 
            #Wanted to get "Observed Data", but it didn't exist
            #Get modeled data instead (but make a note of it)
            tsm = cResSim.getTSMFromSimulationDSS(simDss, element, rssRunObj, rssConstant, txtArea,
             useObsData = False, isStrict = True, displayMessages = True)
            modeledOutflowResvs.append(element._name)
        if tsm is None: #failed to retrieve the data
            errMsg = "Failed to retrieve data at: %s" %element
            errMsg = "\nSee the log file for more details"
            txtArea.printToGUI(errMsg)
            logging.error(errMsg)
            return None
        #Convert to the alternative timestep (observed data may not be consistent timestep)
        tsm = cTsUtils.transformTSM(tsm, tsInt)
        path = tsm.getPath()
        tsc = tsm.getData()
        outPath = DSSPathString(path)
        outPath.setBPart(element._name)
        outPath.setCPart("FLOW")
        outPath.setFPart(fPart)
        cDSS.writeTSC(tsc, outDss, outPath.getPathname())
        #Save a copy for later use if necessary--(rating curve interpolation)
        outflowTSM = tsm.copy()
        #######################################
        #Done with reservoir outflow--move to pool elevations
        element = network.findReservoir(resvName)
        rssConstant = RssModelVariableConstants.VID_POOL_ELEV
        ratingTbl = None
        if ratingDssFile:
            #Want to use rating curves
            #Try to get the rating curve as a table
            #If it fails, it will return None and modeled elevations will be used (with a note of it)
            ratingPath = "//%s/FLOW-ELEV//NAVD88/NATURAL/" %resvName
            ratingTbl = cDSS.readPairedDataFromDSS(ratingPath, ratingDss)
            #Don't apply the natural rating curve for natural lakes--use the modeled data
            if resvName in naturalLakes:
                ratingTbl = None
            #if no rating table is being used, save it to the "naughty" list
            if ratingTbl is None: noRatingCurveResvs.append(element._name)
        if ratingTbl: #a rating table is defined--use it
            #Apply the rating curve to the previously retrieved outflow data
            #Outflow is okay to use because typically in these runs, inflow=outflow
            #  and the rating curves are defined right at the dam location
            tsm = outflowTSM.copy()
            tsm.setUnits("ft")
            tsm.setType("INST-VAL")
            tsc = tsm.getData()
            tsc.values = [ratingTbl.interpolate(v) for v in tsc.values]
            tsm.setData(tsc)
        else:
            #Don't use rating curves, use modeled data
            #retrieve the time series
            tsm = cResSim.getTSMFromSimulationDSS(simDss, element, rssRunObj, rssConstant, txtArea,
             useObsData = useObsData, isStrict = False, displayMessages = False)
            if tsm is None and useObsData: 
                #Wanted to get "Observed Data", but it didn't exist
                #Get modeled data instead (but make a note of it)
                #Check to see if forebay headloss is defined. If it is defined, don't want
                # the "pool" elevations--we want the "forebay" after headloss deducted
                #The headloss must belong to the dam itself, not to a powerplant within the dam
                #Assumes that if observed data is defined at these locations, it is mapped to forebay, not pool
                # so no transformation is appropriate to the observed data
                #This is how to get at the forebay head loss if it is attached to the dam itself
                #Not sure how to access it if it is attached to the powerplant in the dam... (tried lots of things)
                resvDamElem = element.getElementsByClass(ReservoirDamElement, None)[0] # vector of # hec.rss.model.ReservoirDamElement
                fbHeadLoss = resvDamElem.getForebayHeadLoss() # hec.rss.model.ForebayHeadLoss
                if fbHeadLoss: #there is forebay head loss defined
                    fbTs = fbHeadLoss.getTSRecordProxy(143) #Forebay (after headloss deducted from pool)
                    hlTs = fbHeadLoss.getTSRecordProxy(144) #Headloss (ft)
                    fbTsName = fbTs.getName() #e.g. Albeni Falls-Dam at Pend Oreille River-FOREBAY
                    fbTsVarID = fbTs.getVariableId()
                    #tsRec = cResSim.getTSRecord(tsDataSetObj, fbHeadLoss, 143, txtArea, isStrict = True, displayMessages=True)
                    tsm = cResSim.getTSMFromSimulationDSS(simDss, fbHeadLoss, rssRunObj, fbTsVarID, txtArea, 
                     useObsData = False, isStrict = True, displayMessages = True)
                else: #no forebay headloss, just get pool elev
                    tsm = cResSim.getTSMFromSimulationDSS(simDss, element, rssRunObj, rssConstant, txtArea,
                     useObsData = False, isStrict = True, displayMessages = True)
                modeledElevResvs.append(element._name)
            if tsm is None: #failed to retrieve the data
                errMsg = "Failed to retrieve data at: %s" %element
                errMsg = "\nSee the log file for more details"
                txtArea.printToGUI(errMsg)
                logging.error(errMsg)
                return None
            path = tsm.getPath()
            #Add in the datum shift
            dShift = dShiftDict[resvName]
            tsm = tsm.add(dShift)
        #Convert to the alternative timestep (observed data may not be consistent timestep)
        tsm = cTsUtils.transformTSM(tsm, tsInt)
        tsc = tsm.getData()
        outPath = DSSPathString(path)
        outPath.setBPart(resvName)
        outPath.setCPart("ELEV-FOREBAY-NAVD88")
        outPath.setFPart(fPart)
        cDSS.writeTSC(tsc, outDss, outPath.getPathname())
        ####################################
        #Alert! Special Logic for Corra Linn (Queens Bay)
        #The downstream boundary condition of the RAS model is a time series
        #that is the Queens Bay elevation plus a half a foot
        #The Queens Bay elevation is equivalent to the ResSim pool
        if element._name == "Corra Linn":
            msg = "     Adding a half foot to Corra Linn pool and saving as Queens Bay+0.5"
            txtArea.printToGUI(msg)
            logging.info(msg)
            tsm = tsm.add(0.5) #half a foot
            outPath.setBPart("Queens Bay+0.5")
            outPath.setCPart("ELEV-NAVD88")
            tsc = tsm.getData()
            cDSS.writeTSC(tsc, outDss, outPath.getPathname())
    ########################################################################
    #Done with reservoirs, move to junctions
    #Need to write out any local flows at the junction, as well as total flow
    msg = "\nProcessing Junctions:"
    txtArea.printToGUI(msg)
    logging.info(msg)
    modeledFlowJuncs = [] # list to hold Junctions that we wanted observed data, but used modeled instead
    for juncName in juncList:
        msg = "  %s" %juncName
        txtArea.printToGUI(msg)
        logging.info(msg)
        bar.setValue(int(float(barCounter)/barDenom*100))
        barCounter += 1
        element = network.findJunction(juncName)
        ############################
        #Write out all local flows associated with this junction
        #locFlows = element.getLocalFlowTimeSeries() #doesn't work
        nodes = element.getNodeVector()
        for node in nodes: #One local flow per node in ResSim
            #Local flow nodes have no upstream element
            if node.getUpstreamElement(): continue #must be a connected element, skip it
            logging.debug("\tNode: %s" %node)
            rssConstant = RssModelVariableConstants.VID_NODE_FLOW
            #Local flows aren't typically given the observed data check-box
            #Don't retrieve true "Observed Data", just get the local flow time series
            #Output local flows are stored to the node as FLOW, not KNOWNFLOW
            #They will always have the same timestep as the alternative
            tsm = cResSim.getTSMFromSimulationDSS(simDss, node, rssRunObj, rssConstant, txtArea, 
             useObsData = False, isStrict = True, displayMessages = True)
            if tsm is None: #failed to retrieve the data
                errMsg = "Failed to retrieve data at: %s" %element
                errMsg = "\nSee the log file for more details"
                txtArea.printToGUI(errMsg)
                logging.error(errMsg)
                return None
            path = tsm.getPath()
            tsc = tsm.getData()
            outPath = DSSPathString(path)
            #Check to make sure the local flow is spit out in a nice form for RAS
            #In later versions of ResSim 3.2.1197 at least, when a new local flow is created,
            #the default is to name it "%s %s" %(junctionName, localFlowName)
            #But we just want to print out the localFlowName, not the junctionName too
            bPart = outPath.getBPart()
            badBpart = "%s %s" %(juncName, juncName)
            if bPart.upper().startswith(badBpart.upper()):
                #replace the b part with just the local flow name
                bPart = bPart[len(juncName)+1:] #get it to "xx FLOW-LOC"
                outPath.setBPart(bPart)
            #ResSim outputs all local flows as just "FLOW"
            #outPath.setCPart("FLOW-LOC") 
            outPath.setFPart(fPart)
            cDSS.writeTSC(tsc, outDss, outPath.getPathname())
        ############################
        #Write out the total flow at this junction
        rssConstant = RssModelVariableConstants.VID_NODE_FLOW
        #suppress messages out to the txtArea, since many locations will not have obsData
        tsm = cResSim.getTSMFromSimulationDSS(simDss, element, rssRunObj, rssConstant, txtArea,
         useObsData = useObsData, isStrict = True, displayMessages = False)
        if tsm is None and useObsData: 
            #Wanted to get "Observed Data", but it didn't exist
            #Get modeled data instead (but make a note of it)
            tsm = cResSim.getTSMFromSimulationDSS(simDss, element, rssRunObj, rssConstant, txtArea,
             useObsData = False, isStrict = True, displayMessages = True)
            modeledFlowJuncs.append(element._name)
        if tsm is None: #failed to retrieve the data
            errMsg = "Failed to retrieve data at: %s" %element
            errMsg = "\nSee the log file for more details"
            txtArea.printToGUI(errMsg)
            logging.error(errMsg)
            return None
        #Convert to the alternative timestep (observed data may not be consistent timestep)
        tsm = cTsUtils.transformTSM(tsm, tsInt)
        path = tsm.getPath()
        tsc = tsm.getData()
        outPath = DSSPathString(path)
        outPath.setAPart("")
        outPath.setBPart(element._name)
        outPath.setCPart("FLOW")
        outPath.setFPart(fPart)
        cDSS.writeTSC(tsc, outDss, outPath.getPathname())
        #############################
        #Write out the observed elevation at this junction if it exists
        #e.g. Mouth of Columbia River input elevation data may be finer than timestep
        rssConstant = RssModelVariableConstants.VID_JUNC_ELEV
        #suppress messages out to the txtArea, since many locations will not have obsData
        tsm = cResSim.getTSMFromSimulationDSS(simDss, element, rssRunObj, rssConstant, txtArea,
         useObsData = True, isStrict = False, displayMessages = False)
        if tsm: 
            #Observed data exists! Write it out
            msg = "     Echoing observed elevation data"
            txtArea.printToGUI(msg)
            logging.info(msg)
            path = tsm.getPath()
            tsc = tsm.getData()
            outPath = DSSPathString(path)
            outPath.setAPart("")
            outPath.setBPart(element._name)
            outPath.setFPart(fPart)
            cDSS.writeTSC(tsc, outDss, outPath.getPathname())
    #Close all DSS Files
    simDss.close()
    outDss.close()
    msg = "\nCompute Complete!"
    txtArea.printToGUI(msg)
    logging.info(msg)
    bar.setValue(100)
    #Print out any warning messages
    msg = ""
    if len(modeledElevResvs) > 0 and useObsData:
        msg += "\nUsed modeled elevation data (not actual observed data) for:"
        for resv in modeledElevResvs: msg += "\n\t%s" %resv
    if len(noRatingCurveResvs) > 0:
        msg += "\nUsed modeled elevation data (not 'natural' rating curve) for:"
        for resv in noRatingCurveResvs: msg += "\n\t%s" %resv
    if len(modeledOutflowResvs) > 0 and useObsData:
        msg += "\nUsed modeled outflow data (not actual observed data) for:"
        for resv in modeledOutflowResvs: msg += "\n\t%s" %resv
    if len(modeledFlowJuncs) > 0 and useObsData:
        msg += "\nUsed modeled flow data (not actual observed data) for:"
        for junc in modeledFlowJuncs: msg += "\n\t%s" %junc
    logging.warning(msg)
    txtArea.printToGUI(msg)
    
def createVerfPlots (obsAltName, unrAltName, resvFile, juncFile, bar, txtArea) :
    """
    John McCoskery
    Method to create plots in JPEG format for model review and verification.  Plots
    will contain data for "observed-observed", "modeled-observed", and unregulated
    conditions w/in the model.  Reservoirs will plot ELEV, FLOW-IN, and FLOW-OUT.
    Junctions will plot FLOW.  
    
    All reservoirs and junctions are defined in input files, resvFile and juncFile.
    If a reservoir or junction element is not defined in network, then a note is created
    in the log file and the element is skipped.
    
    :param str obsAltName: Name of "observed" alternative
    :param str unrAltName: Name of unregulated alternative
    :param str resvFile:   Pathname to input text file containing list of reservoirs
    :param str juncFile:   Pathname to input text file containing list of junctions
    :param JProgressBar bar: 
    :param JTextArea txtArea: Must have a function defined called "printToGUI"
    """
    msg =  "----------------------------------------------------------------------"
    msg += "\nCreating Verification Plots."
    msg += "\nModeled-Observed Alternative Name             %s" %obsAltName
    msg += "\nModeled-Unregulated Alternative Name          %s" %unrAltName
    msg += "\nInput Reservoir List                          %s" %resvFile
    msg += "\nInput Junction List                           %s" %juncFile
    msg += "\n----------------------------------------------------------------------\n"
    
    txtArea.printToGUI("Creating Verification Plots...")
    logging.info(msg)
    
    #Open and process the reservoir and junction lists
    #Reservoirs
    msg = "Processing file: " + resvFile + "\n"
    logging.info(msg)
    lines = cFile.fileOpenReadClose(resvFile)
    lines = cFile.stripOutCommentLines(lines)
    resvList = [l.strip() for l in lines]
    #Junctions
    msg = "Processing file: " + juncFile + "\n"
    logging.info(msg)
    lines = cFile.fileOpenReadClose(juncFile)
    lines = cFile.stripOutCommentLines(lines)
    juncList = [l.strip() for l in lines]
    
    # get simulation information
    simPeriod = ResSimController.getSimulation()
    startTime, EndTime, LookbackTime = ResSimController.getSimulationTimes(simPeriod)   # run times
    simDssFile = simPeriod.getOutputDSSFilePath()                       # DSS filename
    # 
    obsRun = ResSimController.getSpecificRun(simPeriod, obsAltName)
    obsAlt = obsRun.getRssAlt()
    obsRssRunName = obsRun.getKey()
    obsRunObj = ResSimController.getRssRun(obsRssRunName)
    # 
    unrRun = ResSimController.getSpecificRun(simPeriod, unrAltName)
    unrAlt = unrRun.getRssAlt()
    unrRssRunName = unrRun.getKey()
    unrRunObj = ResSimController.getRssRun(unrRssRunName)
    #
    network = ResSimController.getNetwork(obsRun)                                        # same network for both Alts??
    
    # open simulation DSS file
    msg = "\nOpening DSS File:\n    %s\n" %simDssFile
    logging.info(msg)
    simDSS = DSS.open(simDssFile, LookbackTime, EndTime)
    
    barCounter = 0
    barDenom = len(resvList) + len(juncList)
    
    # loop through reservoirs and build plots
    for rn in resvList :
        msg = "\nCreating Reservoir Plot\n%s" % rn.upper()
        txtArea.printToGUI(msg)
        logging.info(msg)
        
        bar.setValue(int(float(barCounter) / barDenom*100))
        barCounter += 1
        
        # verify that reservoir exists in network
        if network.findReservoir(rn) is None :
            msg = "WARNING reservoir does not exist in network."
            logging.info(msg)
            txtArea.printToGUI(msg)
            continue                                                    # if reservoir not in network, go to next item in list
            
        # use modeled-observed alternative to get real-observed data
        # flow-IN
        element = network.findReservoir(rn).getUpstreamNode().getUpstreamElement()
        rssConstant = RssModelVariableConstants.VID_NODE_FLOW
        obsFlowIN = cResSim.getTSMFromSimulationDSS(simDSS, element, obsRunObj, rssConstant, txtArea, 
            useObsData = True, isStrict = False, displayMessages = False)
        if obsFlowIN is None :
            msg = "Observed FLOW-IN timeseries not found."
            logging.info(msg)
            txtArea.printToGUI(msg)
        else :
            msg = "Observed FLOW-IN:             %s" %obsFlowIN.getPath()
            logging.info(msg)
        # flow-OUT
        element = network.findReservoir(rn).getDownstreamNode().getDownstreamElement()
        rssConstant = RssModelVariableConstants.VID_NODE_FLOW
        obsFlowOUT = cResSim.getTSMFromSimulationDSS(simDSS, element, obsRunObj, rssConstant, txtArea, 
            useObsData = True, isStrict = False, displayMessages = False)
        if obsFlowOUT is None :
            msg = "Observed FLOW-OUT timeseries not found."
            logging.info(msg)
            txtArea.printToGUI(msg)
        else :
            msg = "Observed FLOW-OUT:            %s" %obsFlowOUT.getPath()
            logging.info(msg)
        # Elev
        element = network.findReservoir(rn)
        rssConstant = RssModelVariableConstants.VID_POOL_ELEV
        obsELEV = cResSim.getTSMFromSimulationDSS(simDSS, element, obsRunObj, rssConstant, txtArea, 
            useObsData = True, isStrict = False, displayMessages = False)
        if obsELEV is None :
            msg = "Observed ELEV timeseries not found."
            logging.info(msg)
            txtArea.printToGUI(msg)
        else :
            msg = "Observed ELEV:                %s" %obsELEV.getPath()
            logging.info(msg)
        # now get "modeled"-observed data
        # flow-IN
        element = network.findReservoir(rn).getUpstreamNode().getUpstreamElement()
        rssConstant = RssModelVariableConstants.VID_NODE_FLOW
        mObsFlowIN = cResSim.getTSMFromSimulationDSS(simDSS, element, obsRunObj, rssConstant, txtArea, 
            useObsData = False, isStrict = True, displayMessages = True)
        if mObsFlowIN is None :
            msg = "Modeled-Observed FLOW-IN timeseries not found."
            logging.info(msg)
            txtArea.printToGUI(msg)
        else :
            msg = "Modeled-Observed FLOW-IN:     %s" %mObsFlowIN.getPath()
            logging.info(msg)
        # flow-OUT
        element = network.findReservoir(rn).getDownstreamNode().getDownstreamElement()
        rssConstant = RssModelVariableConstants.VID_NODE_FLOW
        mObsFlowOUT = cResSim.getTSMFromSimulationDSS(simDSS, element, obsRunObj, rssConstant, txtArea, 
            useObsData = False, isStrict = True, displayMessages = True)
        if mObsFlowOUT is None :
            msg = "Modeled-Observed FLOW-OUT timeseries not found."
            logging.info(msg)
            txtArea.printToGUI(msg)
        else :
            msg = "Modeled-Observed FLOW-OUT:    %s" %mObsFlowOUT.getPath()
            logging.info(msg)
        # Elev
        element = network.findReservoir(rn)
        rssConstant = RssModelVariableConstants.VID_POOL_ELEV
        mObsELEV = cResSim.getTSMFromSimulationDSS(simDSS, element, obsRunObj, rssConstant, txtArea, 
            useObsData = False, isStrict = True, displayMessages = True)
        if mObsELEV is None :
            msg = "Modeled-Observed ELEV timeseries not found."
            logging.info(msg)
            txtArea.printToGUI(msg)
        else :
            msg = "Modeled-Observed ELEV:        %s" %mObsELEV.getPath()
            logging.info(msg)
        # now get "modeled"-unregulated data
        # flow-IN
        element = network.findReservoir(rn).getUpstreamNode().getUpstreamElement()
        rssConstant = RssModelVariableConstants.VID_NODE_FLOW
        mUnrFlowIN = cResSim.getTSMFromSimulationDSS(simDSS, element, unrRunObj, rssConstant, txtArea, 
            useObsData = False, isStrict = True, displayMessages = True)
        if mUnrFlowIN is None :
            msg = "Modeled-Unregulated FLOW-IN timeseries not found."
            logging.info(msg)
            txtArea.printToGUI(msg)
        else :
            msg = "Modeled-Unregulated FLOW-IN:  %s" %mUnrFlowIN.getPath()
            logging.info(msg)
        # flow-OUT
        element = network.findReservoir(rn).getDownstreamNode().getDownstreamElement()
        rssConstant = RssModelVariableConstants.VID_NODE_FLOW
        mUnrFlowOUT = cResSim.getTSMFromSimulationDSS(simDSS, element, unrRunObj, rssConstant, txtArea, 
            useObsData = False, isStrict = True, displayMessages = True)
        if mUnrFlowOUT is None :
            msg = "Modeled-Unregulated FLOW-OUT timeseries not found."
            logging.info(msg)
            txtArea.printToGUI(msg)
        else :
            msg = "Modeled-Unregualted FLOW-OUT: %s" %mUnrFlowOUT.getPath()
            logging.info(msg)
        # Elev
        element = network.findReservoir(rn)
        rssConstant = RssModelVariableConstants.VID_POOL_ELEV
        mUnrELEV = cResSim.getTSMFromSimulationDSS(simDSS, element, unrRunObj, rssConstant, txtArea, 
            useObsData = False, isStrict = True, displayMessages = True)
        if mUnrELEV is None :
            msg = "Modeled-Unregulated ELEV timeseries not found."
            logging.info(msg)
            txtArea.printToGUI(msg)
        else :
            msg = "Modeled-Unregulated ELEV:     %s" %mUnrELEV.getPath()
            logging.info(msg)
        # build plot object; elevations in top view, flows in bottom view
        plot = Plot.newPlot()
        layout = Plot.newPlotLayout()
        topview = layout.addViewport(50)                        # top view for elevations
        botview = layout.addViewport(50)                        # bottom view for flows
        # add elevation data
        #if a timeseries is None it just will not show up on plot
        # pass in timeseries at TimeSeriesContainer.
        try :
            topview.addCurve("Y1", obsELEV.getData())
        except :
            topview.addCurve("Y1", None)
        try :
            topview.addCurve("Y1", mObsELEV.getData())
        except :
            topview.addCurve("Y1", None)
        try :
            topview.addCurve("Y1", mUnrELEV.getData())
        except :
            topview.addCurve("Y1", None)
        # add flow data
        try :
            botview.addCurve("Y1", obsFlowIN.getData())
        except :
            botview.addCurve("Y1", None)
        try :
            botview.addCurve("Y1", mObsFlowIN.getData())
        except :
            botview.addCurve("Y1", None)
        try :
            botview.addCurve("Y1", mUnrFlowIN.getData())
        except :
            botview.addCurve("Y1", None)
        try :
            botview.addCurve("Y1", obsFlowOUT.getData())
        except :
            botview.addCurve("Y1", None)
        try :
            botview.addCurve("Y1", mObsFlowOUT.getData())
        except :
            botview.addCurve("Y1", None)
        try :
            botview.addCurve("Y1", mUnrFlowOUT.getData())
        except :
            botview.addCurve("Y1", None)
        # build plot and show - need to "show" in order to adjust things...
        plot.configurePlotLayout(layout)
        plot.showPlot()
        # make adjustments to viewport 1 
        vp = plot.getViewport(0)
        vp.setMinorGridXVisible(True)
        vp.setDrawMinorXGridOn()
        vp.setBorderColor("gray")
        # change colors for obsELEV TSC
        try :
            plot.getCurve(obsELEV).setLineColor("black")
            plot.getCurve(obsELEV).setLineStyle("Solid")
            plot.getCurve(obsELEV).setLineStepStyle("linear")
            plot.getCurve(obsELEV).setLineWidth(1.0)
            plot.setLegendLabelText(obsELEV.getData(), "Obsv-HF")
        except :
            msg = "WARNING could not complete Obs-ELEV formatting."
            logging.info(msg)
            txtArea.printToGUI(msg)
        # change colors for mObsELEV TSC
        try :
            plot.getCurve(mObsELEV).setLineColor("darkgreen")
            plot.getCurve(mObsELEV).setLineStyle("Solid")
            plot.getCurve(mObsELEV).setLineStepStyle("linear")
            plot.getCurve(mObsELEV).setLineWidth(2.)
            plot.setLegendLabelText(mObsELEV.getData(), "Mod-HF")
        except :
            msg = "WARNING could not complete Mod-Obs-ELEV formatting."
            logging.info(msg)
            txtArea.printToGUI(msg)
        # change colors for mUnrELEV TSC
        try :
            plot.getCurve(mUnrELEV).setLineColor("darkgreen")
            plot.getCurve(mUnrELEV).setLineStyle("Dash")
            plot.getCurve(mUnrELEV).setLineStepStyle("linear")
            plot.getCurve(mUnrELEV).setLineWidth(2.)
            plot.setLegendLabelText(mUnrELEV.getData(), "Unreg-HF")
        except :
            msg = "WARNING could not complete Unreg-ELEV formatting."
            logging.info(msg)
            txtArea.printToGUI(msg)         
        # make adjustments to viewport 1 
        vp = plot.getViewport(1)
        vp.setMinorGridXVisible(True)
        vp.setDrawMinorXGridOn()
        vp.setBorderColor("gray")
        # change colors for obsFlowIN TSC
        if not obsFlowIN is None :
            plot.getCurve(obsFlowIN).setLineColor("black")
            plot.getCurve(obsFlowIN).setLineStyle("Solid")
            plot.getCurve(obsFlowIN).setLineStepStyle("step")
            plot.getCurve(obsFlowIN).setLineWidth(1.0)
            plot.setLegendLabelText(obsFlowIN.getData(), "Obsv-QI")
        else :
            msg = "WARNING could not complete Obs-FlowIN formatting."
            logging.info(msg)
            txtArea.printToGUI(msg)         
        # change colors for mObsFlowIN TSC
        if not mObsFlowIN is None :
            plot.getCurve(mObsFlowIN).setLineColor("red")
            plot.getCurve(mObsFlowIN).setLineStyle("Solid")
            plot.getCurve(mObsFlowIN).setLineStepStyle("step")
            plot.getCurve(mObsFlowIN).setLineWidth(2.)
            plot.setLegendLabelText(mObsFlowIN.getData(), "Mod-QI")
        else :
            msg = "WARNING could not complete Mod-Obs-FlowIN formatting."
            logging.info(msg)
            txtArea.printToGUI(msg)         
        # change colors for mUnrFlowIN TSC
        if not mUnrFlowIN is None :
            plot.getCurve(mUnrFlowIN).setLineColor("darkred")
            plot.getCurve(mUnrFlowIN).setLineStyle("Dash")
            plot.getCurve(mUnrFlowIN).setLineStepStyle("step")
            plot.getCurve(mUnrFlowIN).setLineWidth(2.)
            plot.setLegendLabelText(mUnrFlowIN.getData(), "Unreg-QI")
        else :
            msg = "WARNING could not complete Unreg-FlowIN formatting."
            logging.info(msg)
            txtArea.printToGUI(msg)         
        # change colors for obsFlowOUT TSC
        if not obsFlowOUT is None :
            plot.getCurve(obsFlowOUT).setLineColor("black")
            plot.getCurve(obsFlowOUT).setLineStyle("Solid")
            plot.getCurve(obsFlowOUT).setLineStepStyle("step")
            plot.getCurve(obsFlowOUT).setLineWidth(1.0)
            plot.setLegendLabelText(obsFlowOUT.getData(), "Obsv-QR")
        else :
            msg = "WARNING could not complete Obs-FlowOUT formatting."
            logging.info(msg)
            txtArea.printToGUI(msg)         
        # change colors for mObsFlowOUT TSC
        if not mObsFlowOUT is None :
            plot.getCurve(mObsFlowOUT).setLineColor("blue")
            plot.getCurve(mObsFlowOUT).setLineStyle("Solid")
            plot.getCurve(mObsFlowOUT).setLineStepStyle("step")
            plot.getCurve(mObsFlowOUT).setLineWidth(2.)
            plot.setLegendLabelText(mObsFlowOUT.getData(), "Mod-QR")
        else :
            msg = "WARNING could not complete Mod-Obs-FlowOUT formatting."
            logging.info(msg)
            txtArea.printToGUI(msg)         
        # change colors for mUnrFlowOUT TSC
        if not mUnrFlowOUT is None :
            plot.getCurve(mUnrFlowOUT).setLineColor("darkblue")
            plot.getCurve(mUnrFlowOUT).setLineStyle("Dash")
            plot.getCurve(mUnrFlowOUT).setLineStepStyle("step")
            plot.getCurve(mUnrFlowOUT).setLineWidth(2.)
            plot.setLegendLabelText(mUnrFlowOUT.getData(), "Unreg-QR")
        else :
            msg = "WARNING could not complete Unreg-FlowOUT formatting."
            logging.info(msg)
            txtArea.printToGUI(msg)         
        
        # save plot to JPEG file
        pltFile = network.makeAbsolutePathFromWatershed("shared/Plots/Reservoirs/%s.png" %rn)
        cFile.ensure_dir(pltFile)
        plot.setSize(1000, 650)
        plot.saveToPng(pltFile)
        plot.close()
    # loop through junctions and build plots
    for jn in juncList :
        msg = "\nCreating Junction Plot\n%s" % jn.upper()
        txtArea.printToGUI(msg)
        logging.info(msg)
        
        bar.setValue(int(float(barCounter) / barDenom*100))
        barCounter += 1
        
        # verify that junction exists in network
        if network.findJunction(jn) is None :
            msg = "WARNING junction does not exist in network."
            logging.info(msg)
            txtArea.printToGUI(msg)
            continue                                                    # if junction not in network, go to next item in list
            
        # use modeled-observed alternative to get real-observed data
        # flow
        element = network.findJunction(jn)
        rssConstant = RssModelVariableConstants.VID_NODE_FLOW
        obsFlow = cResSim.getTSMFromSimulationDSS(simDSS, element, obsRunObj, rssConstant, txtArea, 
            useObsData = True, isStrict = False, displayMessages = False)
        if obsFlow is None :
            msg = "Observed FLOW timeseries not found."
            logging.info(msg)
            txtArea.printToGUI(msg)
        else :
            msg = "Observed FLOW:                %s" %obsFlow.getPath()
            logging.info(msg)
        # now get "modeled"-observed data
        # flow-IN
        rssConstant = RssModelVariableConstants.VID_NODE_FLOW
        mObsFlow = cResSim.getTSMFromSimulationDSS(simDSS, element, obsRunObj, rssConstant, txtArea, 
            useObsData = False, isStrict = True, displayMessages = True)
        if mObsFlow is None :
            msg = "Modeled-Observed FLOW timeseries not found."
            logging.info(msg)
            txtArea.printToGUI(msg)
        else :
            msg = "Modeled-Observed FLOW:        %s" %mObsFlow.getPath()
            logging.info(msg)
        # now get "modeled"-unregulated data
        # flow
        rssConstant = RssModelVariableConstants.VID_NODE_FLOW
        mUnrFlow = cResSim.getTSMFromSimulationDSS(simDSS, element, unrRunObj, rssConstant, txtArea, 
            useObsData = False, isStrict = True, displayMessages = True)
        if mUnrFlow is None :
            msg = "Modeled-Unregulated FLOW timeseries not found."
            logging.info(msg)
            txtArea.printToGUI(msg)
        else :
            msg = "Modeled-Unregulated FLOW:     %s" %mUnrFlow.getPath()
            logging.info(msg)
        # build plot object; elevations in top view, flows in bottom view
        plot = Plot.newPlot()
        layout = Plot.newPlotLayout()
        topview = layout.addViewport(50)                        # top view for elevations
        # add elevation data
        #if a timeseries is None it just will not show up on plot
        # pass in timeseries at TimeSeriesContainer.
        try :
            topview.addCurve("Y1", obsFlow.getData())
        except :
            topview.addCurve("Y1", None)
        try :
            topview.addCurve("Y1", mObsFlow.getData())
        except :
            topview.addCurve("Y1", None)
        try :
            topview.addCurve("Y1", mUnrFlow.getData())
        except :
            topview.addCurve("Y1", None)
        # build plot and show - need to "show" in order to adjust things...
        plot.configurePlotLayout(layout)
        plot.showPlot()
        # make adjustments to viewport 1 
        vp = plot.getViewport(0)
        vp.setMinorGridXVisible(True)
        vp.setDrawMinorXGridOn()
        vp.setBorderColor("gray")
        # change colors for obsFlow TSC
        try :
            plot.getCurve(obsFlow).setLineColor("black")
            plot.getCurve(obsFlow).setLineStyle("Solid")
            plot.getCurve(obsFlow).setLineStepStyle("linear")
            plot.getCurve(obsFlow).setLineWidth(1.0)
            plot.setLegendLabelText(obsFlow.getData(), "Obsv-QR")
        except :
            msg = "WARNING could not complete Obs-Flow formatting."
            logging.info(msg)
            txtArea.printToGUI(msg)
        # change colors for mObsFlow TSC
        try :
            plot.getCurve(mObsFlow).setLineColor("blue")
            plot.getCurve(mObsFlow).setLineStyle("Solid")
            plot.getCurve(mObsFlow).setLineStepStyle("linear")
            plot.getCurve(mObsFlow).setLineWidth(2.)
            plot.setLegendLabelText(mObsFlow.getData(), "Mod-QR")
        except :
            msg = "WARNING could not complete Mod-Obs-Flow formatting."
            logging.info(msg)
            txtArea.printToGUI(msg)
        # change colors for mUnrFlow TSC
        try :
            plot.getCurve(mUnrFlow).setLineColor("blue")
            plot.getCurve(mUnrFlow).setLineStyle("Dash")
            plot.getCurve(mUnrFlow).setLineStepStyle("linear")
            plot.getCurve(mUnrFlow).setLineWidth(2.)
            plot.setLegendLabelText(mUnrELEV.getData(), "Unreg-QR")
        except :
            msg = "WARNING could not complete Unreg-Flow formatting."
            logging.info(msg)
            txtArea.printToGUI(msg)         
        
        # save plot to PNG file
        pltFile = network.makeAbsolutePathFromWatershed("shared/Plots/Junctions/%s.png" %jn)
        cFile.ensure_dir(pltFile)
        plot.setSize(1000, 650)
        plot.saveToPng(pltFile)
        plot.close()
    # close DSS file
    simDSS.close()
    # print in file messages
    msg = "\nCompute Complete!"
    txtArea.printToGUI(msg)
    logging.info(msg)
    bar.setValue(100)

def calcSelectedUnregs(outListFile, unregAltName, outDssFile, bar, txtArea, 
    overrideObsDssFile, outFPart, toAlias=None):
    """
    Calculates and writes unregulated flows at specified locations, since we
    don't generally want unreg flows everywhere.
    Runs :meth:`computeFlows`
    Assumes a simulation in ResSim is already open.
    
    :param str outListFile: The pathname to the text file with the desired output locations
    :param str altName: The alternative to use to get the time series mapping (e.g "MyUnreg")
    :param str outDssFile: Pathname to the desired output file
    :param JProgressBar bar: 
    :param JTextArea txtArea: Must have a function defined called "printToGUI"
    :param str overrideObsDssFile: All flow data will be read from this file. 
        See :meth:`computeFlows` for more details. 
    :param str outFPart: The output f-part for the unregulated flow time series.
    :param str toAlias: If specified, the B-part of the output will be renamed
           from the ResSim output to any valid other location code from :any:`NameAlias`
           e.g. "CBT_CODE". If not provided, the ResSim name will be used.
    :return: A list of TimeSeriesContainer objects that were written to DSS
    """
    #Read in the desired output locations from the text file
    lines = cFile.fileOpenReadClose(outListFile)
    outLocations = cFile.stripOutCommentLines(lines)
    #Calculate unregulated flows everywhere
    simPeriod = ResSimController.getSimulation()
    run = ResSimController.getSpecificRun(simPeriod, unregAltName) #RssSimRun
    if run is None:
        errMsg = "No alternative exists named: %s" %altName
        txtArea.printToGUI(errMsg)
        logging.error(errMsg)
        return None
    network = ResSimController.getNetwork(run)
    outTSCs = computeFlows("UNREG", network, unregAltName, outDssFile,
        True, bar, txtArea, overrideObsDssFile, outFPart
        )
    outDss = cDSS.openDSSFile(outDssFile)
    #We've calculated unreg flows at every junction and reservoir
    #We don't want to write all of this output--we only want selected locations
    writtenTSCs = []
    for i, outLocation in enumerate(outLocations):
        logging.info("Processing desired output %s of %s: %s" %(i+1, len(outLocations), outLocation))
        searchLocation = outLocation.upper()
        #Try to find a match with the output location and the output timeseries
        foundMatch = False
        for outTSC in outTSCs:
            dssPath = DSSPathname(outTSC.fullName)
            tscLocation = dssPath.getBPart().upper()
            if searchLocation == tscLocation:
                logging.debug("  Found matching unreg flow: %s" %tscLocation)
                tscToWrite = outTSC.clone()
                foundMatch = True
                break
        if not foundMatch:
            logging.warning("Failed to find unreg flow record for: %s" %outLocation)
            continue
        #We have the unreg timeseries, but we may want to change the naming convention
        if toAlias:
            #Change the naming convention
            #If the location has an "_IN" or "_OUT" in it, it is likely a reservoir
            #So we need to strip off those characters for a lookup
            if "_IN" in tscLocation or "_OUT" in tscLocation:
                tscLocation = tscLocation.replace("_IN","").replace("_OUT","")
            bPart = NameAlias.myLocationAlias.lookup(tscLocation, "RESSIM_NAME", toAlias)
            if bPart is None:
                logging.warning("Failed to rename the b-part: %s" %bPart)
                logging.warning("Make sure the location is defined in LocationAlias.csv")
                continue
            dssPath.setBPart(bPart.upper())
        #Write out the unreg flow
        tscToWrite = cDSS.writeTSC(tscToWrite, outDss, dssPath.getPathname())
        writtenTSCs.append(tscToWrite)
    outDss.close()
    return writtenTSCs