"""
Step 2 of Damages Prevented: water-balance local flows.

Ported from AFDR/cDamPrev.computeLocalFlows for ResSim 4.1. No compute is
needed first: everything comes from the Observed alternative's time series
mapping and the network's own reach routing.

Walking the network from the headwaters down, the script routes the flow it
has so far through each reach. At every junction with observed flow mapped
(Observed tab), the local mapped at that junction (Timeseries tab) is

    local = observed flow - routed flow arriving from upstream

and the routed flow is then reset to the observed flow. At junctions without
observed flow, the mapped local is read and added. Each computed local is
written to the pathname it is mapped to, in DPcalc.dss.

Change from the original: the computed locals and the transformed locals
(Willamette Falls) now share DPcalc.dss. The original skipped its output file
entirely when loading inputs, which would also skip Willamette Falls. Here
DPcalc.dss is loaded separately: any input record already in it is used, and
the records about to be computed are simply not there yet on a first run.
"""
from hec.hecmath import DSS, TimeSeriesMath
from hec.heclib.util import HecTime
from hec.lang import DSSPathString
from hec.rss.model import JunctionElement, ReachElement
from hec.rss.model import RssModelVariableConstants
import logging

from NWDJyLib import cRouting
from NWDJyLib.ResSim import cResSim, ResSimController
from NWDJyLib.DSS import cDSS, cTsUtils

################################################################################

def _sameFile(a, b):
    return str(a).replace("\\", "/").upper() == str(b).replace("\\", "/").upper()

def _checkIn(tsBank, network, dssDict, tsDataSet, rssConstant, tsInt, beginTime, endTime,
             onlyFile=None, skipFile=None, reportMissing=True):
    """
    Loads the records of tsDataSet with variable rssConstant into tsBank,
    converted to tsInt, keyed by the absolute DSS file name.

    Does what cResSim.tsmBank.checkInTimeSeries does, except that relative DSS
    file names are resolved against the watershed (network) rather than
    ClientApp.Workspace(), which in ResSim 4.1 is the AppData workspace.

    onlyFile:      load only the records mapped to this file
    skipFile:      skip the records mapped to this file
    reportMissing: list records that don't exist (off for DPcalc.dss, whose
                   locals don't exist until this step writes them)
    Returns a message listing missing records and records that don't cover the
    whole time window (blank if none).
    """
    beginHecTime = HecTime(beginTime)
    endHecTime = HecTime(endTime)
    missing = ""
    truncated = ""
    for tsRec in tsDataSet.getTSRecords():
        if tsRec.getVariableId() != rssConstant:
            continue
        if tsRec.getDSSFilename() == "":
            continue
        dssName = network.makeAbsolutePathFromWatershed(tsRec.getDSSFilename())
        if onlyFile is not None and not _sameFile(dssName, onlyFile):
            continue
        if skipFile is not None and _sameFile(dssName, skipFile):
            continue
        if "COMPUTE_ME" in str(dssName).upper():
            continue
        pathname = tsRec.getDSSPathname()
        if len(pathname) == pathname.count("/"):
            continue
        if tsBank.containsTS(dssName, pathname):
            continue
        try:
            tsm = dssDict[dssName].read(pathname)
        except:
            if reportMissing:
                missing += "\n  Name:       %s" %tsRec.getName()
                missing += "\n  Dss File:   %s" %dssName
                missing += "\n  Pathname:   %s\n" %pathname
            continue
        first = HecTime(tsm.firstValidDate(), HecTime.MINUTE_INCREMENT)
        last = HecTime(tsm.lastValidDate(), HecTime.MINUTE_INCREMENT)
        if first.notEqualTo(beginHecTime) or last.notEqualTo(endHecTime):
            truncated += "\n  Name:       %s" %tsRec.getName()
            truncated += "\n  Dss File:   %s" %dssName
            truncated += "\n  Pathname:   %s" %pathname
            truncated += "\n  Covers:     %s to %s (need %s to %s)\n" %(first.dateAndTime(), last.dateAndTime(),
                                                                    beginHecTime.dateAndTime(), endHecTime.dateAndTime())
            continue
        tsBank.depositTS(dssName, pathname, cTsUtils.transformTSM(tsm, tsInt))
    msg = ""
    if missing:
        msg += "\n\nTime Series that do not exist:" + missing
    if truncated:
        msg += "\n\nTime Series not defined over the full time window:" + truncated
    return msg

def computeWaterBalanceLocals(altName, outDssFile, negs, bar, txtArea):
    """
    Computes the water-balance locals for altName and writes them to outDssFile.

    :param str altName:    the Observed alternative (as named in the simulation)
    :param str outDssFile: DPcalc.dss (absolute path)
    :param bool negs:      True if negative locals are allowed
    :param bar:            JProgressBar
    :param txtArea:        JTextArea with a printToGUI method
    :return: number of locals computed, or None if the compute stopped
    """
    msg = "----------------------------------------------------------------------"
    msg += "\nComputing Water-Balance Local Flows"
    msg += "\nAlternative:                           %s" %altName
    msg += "\nOutput DSS File:                       %s" %outDssFile
    msg += "\nNegative locals allowed:               %s" %negs
    logging.info(msg)
    txtArea.printToGUI("Computing water-balance local flows...")

    simPeriod = ResSimController.getSimulation()
    run = ResSimController.getSpecificRun(simPeriod, altName)
    if run is None:
        errMsg = "Alternative %s is not in the open simulation." %altName
        logging.error(errMsg)
        txtArea.printToGUI(errMsg)
        return None
    network = run.getRssSystem()
    simDssFile = simPeriod.getOutputDSSFilePath()
    alt = run.getRssAlt()
    tsInt = alt.getTimeStepString() #e.g. 1HOUR
    rtw = simPeriod.getRunTimeWindow()
    startTime, endTime, lookbackTime = ResSimController.getSimulationTimes(simPeriod)

    if not _checkRouting(network, txtArea):
        return None
    confJuncs = cResSim.getConfluenceJunctions(network)
    confResvDict = cResSim.getConfluenceResvPoolDict(network)
    confResvs = confResvDict.keys() #pool Element, not ReservoirElement
    hwJuncs = cResSim.getRealHeadwaterJunctions(network)
    orderedElements = cResSim.orderElementsFromUpstream(network)
    obsTSDataSet = alt.getObservedTSDataSet()
    inputTSDataSet = alt.getInputTSDataSet()

    #Open every DSS file the alternative maps in
    dssDict = {}
    for tsRec in list(obsTSDataSet.getTSRecords()) + list(inputTSDataSet.getTSRecords()):
        dssFile = tsRec.getDSSFilename()
        if dssFile == "":
            continue
        dssFile = network.makeAbsolutePathFromWatershed(dssFile)
        if dssFile not in dssDict.keys():
            logging.info("Opening Dss File: %s" %dssFile)
            dssDict[dssFile] = DSS.open(dssFile, lookbackTime, endTime)
    outDss = None
    for dssFile in dssDict.keys():
        if _sameFile(dssFile, outDssFile):
            outDss = dssDict[dssFile]
    if outDss is None:
        errMsg = "None of the locals in alternative %s are mapped to:\n%s" %(altName, outDssFile)
        errMsg += "\nPoint the water-balance locals in the Timeseries tab at that file, or change DPCALC_DSS in DPSettings.py."
        logging.error(errMsg)
        txtArea.printToGUI(errMsg)
        for f in dssDict.values(): f.close()
        return None

    #Load every input time series up front, converted to the alternative time step
    txtArea.printToGUI("Loading input time series...")
    tsBank = cResSim.tsmBank()
    obsMsg = _checkIn(tsBank, network, dssDict, obsTSDataSet, RssModelVariableConstants.VID_NODE_FLOW,
                      tsInt, lookbackTime, endTime, skipFile = outDssFile)
    stdMsg = _checkIn(tsBank, network, dssDict, inputTSDataSet, RssModelVariableConstants.VID_NODE_KNOWNFLOW,
                      tsInt, lookbackTime, endTime, skipFile = outDssFile)
    calcMsg = _checkIn(tsBank, network, dssDict, inputTSDataSet, RssModelVariableConstants.VID_NODE_KNOWNFLOW,
                       tsInt, lookbackTime, endTime, onlyFile = outDssFile, reportMissing = False)
    if obsMsg or stdMsg or calcMsg:
        #Reported, not fatal (as in the original): a series that is truly needed
        #stops the compute where it is used, with its name.
        errMsg = "WARNING: not every mapped time series covers the full time window."
        if obsMsg: errMsg += "\nObserved Data tab:" + obsMsg
        if stdMsg: errMsg += "\nTimeseries tab:" + stdMsg
        if calcMsg: errMsg += "\nTimeseries tab (%s):%s" %(outDssFile, calcMsg)
        logging.warning(errMsg)
        txtArea.printToGUI(errMsg)
    else:
        txtArea.printToGUI("All input time series look good!")

    simDss = DSS.open(simDssFile, lookbackTime, endTime)
    rssRunObj = ResSimController.getRssRun(run.getKey()) #for diversion flows from the last compute
    divsNotDeducted = [] #diversions with no flow from their rule or a previous compute
    tribFlows = {} #keys are Elements (e.g. reaches), values are TimeSeriesMath
    numLocals = 0
    regTSM = None
    #Proceed through all elements, keeping regTSM as the current routed flow
    for i in range(len(orderedElements)):
        bar.setValue(int(float(i)/len(orderedElements)*100))
        element = orderedElements[i]
        if element == None: continue
        elemName = str(element)
        nodes = element.getNodeVector()
        if elemName == "Pool": #reservoir pool element
            if element in confResvs:
                #confluence reservoir: add the flow from the other upstream junctions
                for juncElem in confResvDict[element]:
                    if tribFlows.has_key(juncElem):
                        regTSM = regTSM.add(tribFlows[juncElem])
                    else:
                        errMsg = "At confluence reservoir %s, no flow was computed for upstream junction %s" %(element.getParent(), juncElem)
                        _stop(errMsg, txtArea, tsBank, simDss, dssDict)
                        return None
        if isinstance(element, JunctionElement):
            logging.info("Junction: %s" %elemName)
            divElems = cResSim.getConnectedDiversions(element)
            if divElems: #deduct any diversion
                for divElem in divElems:
                    logging.info("\tDiversion found: %s" %divElem)
                    divTSM = _diversionTSM(divElem, rtw, inputTSDataSet, tsInt, simDss, rssRunObj, txtArea)
                    if divTSM is None:
                        divsNotDeducted.append(str(divElem))
                    elif regTSM is not None:
                        regTSM = regTSM.subtract(divTSM)
            if element in confJuncs:
                #confluence junction: add the flow from the other upstream reaches
                for rch in list(cResSim.getConnectedReaches(element)):
                    if tribFlows.has_key(rch):
                        regTSM = regTSM.add(tribFlows[rch])
            #Observed flow at this junction, if mapped (one total-flow record per location)
            obsTSM = None
            rssConstant = RssModelVariableConstants.VID_NODE_FLOW
            tsRecObs = cResSim.getTSRecord(obsTSDataSet, element, rssConstant, txtArea, isStrict=True, displayMessages=False)
            if tsRecObs:
                obsPath = tsRecObs.getDSSPathname()
                obsDssFilename = tsRecObs.getDSSFilename()
                if len(obsPath) == obsPath.count("/") or obsDssFilename == "":
                    msg = "\tBlank pathname - no observed flow used at: %s" %elemName
                    logging.warning(msg)
                    txtArea.printToGUI(msg)
                else:
                    obsDssFilename = network.makeAbsolutePathFromWatershed(obsDssFilename)
                    obsTSM = tsBank.withdrawTS(obsDssFilename, obsPath)
                    if obsTSM is None:
                        errMsg = "Observed flow at %s could not be loaded:\n%s\n%s" %(elemName, obsDssFilename, obsPath)
                        errMsg += "\nSee the warnings above about missing or short time series."
                        _stop(errMsg, txtArea, tsBank, simDss, dssDict)
                        return None
            #Local flows at this junction (one node per local)
            rssConstant = RssModelVariableConstants.VID_NODE_KNOWNFLOW
            for node in nodes:
                if str(node.getDownstreamElement()) != elemName: continue
                if node.getUpstreamElement(): continue #a connected element, not a local
                tsrp = node.getTSRecordProxy(RssModelVariableConstants.VID_NODE_KNOWNFLOW)
                if not tsrp: continue
                tsRec = cResSim.getTSRecord(inputTSDataSet, node, rssConstant, txtArea, isStrict=False, displayMessages=False)
                if not tsRec:
                    errMsg = "Failed to locate local inflow information for: %s" %tsrp.getName()
                    errMsg += "\nMap a fake time series in here, save the time series mapping,"
                    errMsg += "\nand then clear out the fake time series. The network just needs"
                    errMsg += "\nto be reconfigured at this location."
                    _stop(errMsg, txtArea, tsBank, simDss, dssDict)
                    return None
                locFlowPath = tsRec.getDSSPathname()
                locFlowTsInt = DSSPathString(locFlowPath).getEPart()
                locFlowDssFilename = network.makeAbsolutePathFromWatershed(tsRec.getDSSFilename())
                factor = tsrp.getFactor() #local inflow multiplier
                if obsTSM: #observed flow here - compute the local
                    obsTSM.setType("PER-AVER")
                    if len(locFlowPath) == locFlowPath.count("/"):
                        msg = "\t\tBlank local flow pathname at %s - not computing a local" %elemName
                        logging.warning(msg)
                        txtArea.printToGUI(msg)
                    elif element in hwJuncs:
                        #headwater junction: the local is the observed flow
                        obsTSMToWrite = cTsUtils.transformTSM(obsTSM, locFlowTsInt)
                        _writeLocal(obsTSMToWrite.getData(), locFlowPath, locFlowDssFilename, outDssFile, simDss, outDss, elemName, txtArea)
                        numLocals += 1
                    else:
                        msg = "Local Flow at: %s" %elemName
                        txtArea.printToGUI(msg)
                        logging.info(msg)
                        locTSC = obsTSM.subtract(regTSM).getData()
                        if not negs:
                            locTSC = cTsUtils.removeNegativeLocals(locTSC)
                        locTSM = cTsUtils.transformTSM(TimeSeriesMath(locTSC), locFlowTsInt)
                        _writeLocal(locTSM.getData(), locFlowPath, locFlowDssFilename, outDssFile, simDss, outDss, elemName, txtArea)
                        numLocals += 1
                elif tsRecObs:
                    #observed flow expected here but blank - all local goes downstream
                    logging.info("\t\tObserved flow at %s is blank; not adding local flow" %elemName)
                else:
                    #no observed flow here - add the mapped local
                    if len(locFlowPath) == locFlowPath.count("/"):
                        msg = "\t\tBlank local flow pathname at %s - not adding local flow" %elemName
                        logging.warning(msg)
                        txtArea.printToGUI(msg)
                    else:
                        locFlowTSM = tsBank.withdrawTS(locFlowDssFilename, locFlowPath)
                        if locFlowTSM is None:
                            errMsg = "Local flow at %s could not be read:\n%s\n%s" %(elemName, locFlowDssFilename, locFlowPath)
                            errMsg += "\nThere is no observed flow here, so this local must already exist"
                            errMsg += "\nand cover the whole simulation window (lookback to end)."
                            errMsg += "\nIf it is listed in the warnings above as not covering the full window,"
                            errMsg += "\nextend the record or change the simulation window so they line up."
                            if _sameFile(locFlowDssFilename, outDssFile):
                                errMsg += "\nIt is mapped to %s - run step 1 (transform gage data) first if it is a transformed local." %outDssFile
                            _stop(errMsg, txtArea, tsBank, simDss, dssDict)
                            return None
                        locFlowTSM = locFlowTSM.multiply(factor)
                        if element in hwJuncs or regTSM is None:
                            regTSM = locFlowTSM.copy()
                        else:
                            regTSM = regTSM.add(locFlowTSM)
                        logging.info("\t\tAdded input local flow: %s" %locFlowPath)
            #Observed flow resets the routed flow (also at points with no local, e.g. dam outlets)
            if obsTSM:
                logging.info("\tObserved flow exists at %s: resetting flow" %elemName)
                regTSM = obsTSM.copy()
        elif isinstance(element, ReachElement):
            routeReach = cRouting.buildReach(element.getFunction())
            logging.info("Reach : %s" %elemName)
            regTSM = TimeSeriesMath(routeReach.routeTSC(regTSM.getData()))
        #Save the flow for a downstream confluence and start the next branch from zero
        dsElem = element.getDownstreamNode().getDownstreamElement()
        if dsElem in confJuncs or dsElem in confResvs:
            tribFlows[element] = regTSM.copy()
            regTSM = regTSM.multiply(0)

    tsBank.close()
    simDss.close()
    for dssFile in dssDict.values(): dssFile.close()
    bar.setValue(100)
    if divsNotDeducted:
        msg = "\nWARNING: %d diversion(s) were not deducted (taken as 0):" %len(divsNotDeducted)
        for d in divsNotDeducted:
            msg += "\n   %s" %d
        msg += "\nTheir rules (e.g. scripted rules) can't be evaluated outside a compute, and"
        msg += "\nalternative %s has no computed diversion flow for them yet." %altName
        msg += "\nThe locals above therefore include those withdrawals. To account for them:"
        msg += "\ncompute %s, run this step again (it then uses the computed diversion" %altName
        msg += "\nflows), and compute %s once more." %altName
        logging.warning(msg)
        txtArea.printToGUI(msg)
    msg = "\nDone. %d water-balance local(s) written to %s" %(numLocals, outDssFile)
    logging.info(msg)
    txtArea.printToGUI(msg)
    return numLocals

def _diversionTSM(divElem, rtw, inputTSDataSet, tsInt, simDss, rssRunObj, txtArea):
    """
    Flow taken by a diversion over the simulation window, or None.

    First from the diversion's own rule (constant, seasonal, monthly or time
    series, via cResSim.getDiversionTSC). Diversions with no rule on their
    controller, or a rule that can't be evaluated outside a compute (scripted,
    flexible), fall back to the diversion flow from the alternative's last
    compute in simulation.dss, as the mini-simulations read it. None if neither
    has it.
    """
    try:
        divTSC = cResSim.getDiversionTSC(divElem, rtw, inputTSDataSet)
    except:
        divTSC = None #e.g. no rule on the controller (IndexError)
    if divTSC is not None:
        return cTsUtils.transformTSM(TimeSeriesMath(divTSC), tsInt)
    try:
        divNode = divElem.getUpstreamNode() #diverted flow is in the upstream node
        divTSM = cResSim.getTSMFromSimulationDSS(simDss, divNode, rssRunObj, RssModelVariableConstants.VID_NODE_FLOW,
                                                  txtArea, useObsData = False, isStrict = False, displayMessages = False)
    except:
        divTSM = None
    if divTSM is None:
        logging.warning("\tNo diversion flow from the rule or a previous compute: %s (taken as 0)" %divElem)
        return None
    logging.info("\tDiversion flow taken from the last compute: %s" %divElem)
    return cTsUtils.transformTSM(divTSM, tsInt)

def _writeLocal(tsc, locFlowPath, locFlowDssFilename, outDssFile, simDss, outDss, elemName, txtArea):
    """Writes a computed local to simulation.dss and to the file it is mapped to."""
    cDSS.writeTSC(tsc, simDss, locFlowPath)
    cDSS.writeTSC(tsc, outDss, locFlowPath)
    if not _sameFile(locFlowDssFilename, outDssFile):
        msg = "\t\tNOTE: the local at %s is mapped to %s, not %s. It was written to %s; repoint it in the Timeseries tab." %(elemName, locFlowDssFilename, outDssFile, outDssFile)
        logging.warning(msg)
        txtArea.printToGUI(msg)

def _checkRouting(network, txtArea):
    """Every reach must use a routing method cRouting can reproduce. Lists any that don't."""
    bad = []
    for reachName in network.getReachNames():
        reach = network.findReach(str(reachName))
        if reach is None: continue
        if cRouting.buildReach(reach.getFunction()) is None:
            bad.append("%s (%s)" %(reachName, reach.getFunction().__class__))
    if bad:
        errMsg = "These reaches use a routing method the script cannot reproduce"
        errMsg += " (supported: SSARR, Muskingum, Modified Puls, Null):"
        for b in bad: errMsg += "\n\t%s" %b
        logging.error(errMsg)
        txtArea.printToGUI(errMsg)
        return False
    return True

def _stop(errMsg, txtArea, tsBank, simDss, dssDict):
    logging.error(errMsg)
    txtArea.printToGUI(errMsg)
    txtArea.printToGUI("COMPUTE STOPPED")
    tsBank.close()
    simDss.close()
    for dssFile in dssDict.values(): dssFile.close()
