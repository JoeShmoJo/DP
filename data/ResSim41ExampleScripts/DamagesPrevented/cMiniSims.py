"""
Step 3 of Damages Prevented: mini-simulations, the flow reduction credited to
each reservoir at each control point.

Ported from AFDR/cDamPrev.runMiniSimulations for ResSim 4.1. The algorithm is
unchanged; the Columbia natural-lake logic is gone and the results go to CSV
files instead of an .xls (the jxl library is not part of ResSim 4.1).

Needs an Observed and an Unregulated alternative in the open simulation, both
computed, on the same network. They are not recomputed. For each reservoir R
(a re-regulating reservoir is run together with the reservoir above it):

  WITHOUT R    Start from R's inflow in the Observed run and route it down the
               network with each reach's own routing. Add locals and tributary
               flows from the Observed run; at every other reservoir add its
               observed outflow minus inflow. R (and its re-reg) pass inflow.
  WITH ONLY R  The same from the Unregulated run: every reservoir passes inflow
               except R (and its re-reg), which applies its observed storage change.

At each control point the reduction credited to R is the average of
    (unregulated peak - WITH ONLY R peak) and (WITHOUT R peak - observed peak).
Peaks are rounded to the nearest 100 cfs first, as in the original.

Added-flow control points (config/AddedFlowPoints.csv) are points beyond the
network, e.g. Willamette+Clackamas: every series at their base junction
(unregulated, modeled observed, each WITHOUT / WITH ONLY run) plus a gage
record from obsData.dss times a factor, hour by hour, not routed. List them in
ControlPoints.txt like any other control point.

Outputs:
    MiniSimulations.dss   //<junction>/FLOW//<step>/<UNREGULATED | MODELED OBSERVED |
                          OBSERVED | WITHOUT <resv> | WITH ONLY <resv>>/
    Results/Preliminary_per_project.csv  reduction matrix, control point x reservoir
    Results/Mini-Simulations.csv         peaks behind each reduction
    Results/CP_Peaks.csv                 unregulated vs regulated peak at each control point
    Results/Resv_Peaks.csv               peak inflow and outflow at that time, each reservoir
"""
from hec.hecmath import DSS, TimeSeriesMath
from hec.lang import DSSPathString
from hec.heclib.util import HecTime
from hec.rss.model import ReservoirElement, JunctionElement, ReachElement
from hec.rss.model import RssModelVariableConstants
import os, csv, logging

from NWDJyLib import cRouting, cFile
from NWDJyLib.ResSim import cResSim, ResSimController
from NWDJyLib.DSS import cDSS, cTsUtils
from DamagesPrevented import DPSettings

################################################################################
# CLASS DEFINITIONS

class JuncPeaks:
    """All the peak flows for one junction (observed, unregulated, each with/without run)"""
    def __init__(self, name):
        self._name = name
        self.obsPeak = None          #"Observed Data" mapped at the junction
        self.obsPeakTime = None
        self.modeledObsPeak = None   #Observed alternative's computed flow
        self.modeledObsPeakTime = None
        self.isGaged = False         #True if "Observed Data" exists here
        self.note = None             #source note for an added-flow point
        self.unregPeak = None
        self.unregPeakTime = None
        self.rPeakDict = {}          #rPeakDict[resvName]["WITH"/"WITHOUT"/"reduction"]
        self.rPeakTimeDict = {}
    def getPeakWith(self, rName):
        if rName in self.rPeakDict.keys(): return self.rPeakDict[rName]["WITH"]
    def getPeakWithout(self, rName):
        if rName in self.rPeakDict.keys(): return self.rPeakDict[rName]["WITHOUT"]
    def getContributingResvs(self):
        return self.rPeakDict.keys()
    def setPeakInfo(self, rName, peak, TOP, isWith):
        """isWith = True for a WITH ONLY run, False for a WITHOUT run"""
        if not rName in self.rPeakDict.keys():
            self.rPeakDict[rName] = {}
            self.rPeakTimeDict[rName] = {}
        if isWith: withType = "WITH"
        else:      withType = "WITHOUT"
        self.rPeakDict[rName][withType] = peak
        self.rPeakTimeDict[rName][withType] = TOP
    def setFlowReduction(self, rName, reduction):
        self.rPeakDict[rName]["reduction"] = reduction
    def getFlowReduction(self, rName):
        return self.rPeakDict[rName]["reduction"]
    def setModeledObsPeakInfo(self, peak, TOP):
        self.modeledObsPeak = peak
        self.modeledObsPeakTime = TOP
    def setObsPeakInfo(self, peak, TOP):
        self.obsPeak = peak
        self.obsPeakTime = TOP
    def setUnregPeakInfo(self, peak, TOP):
        self.unregPeak = peak
        self.unregPeakTime = TOP
    def setGaged(self, isGaged):
        self.isGaged = isGaged

class ResvPeaks:
    """Peak inflow, its time, and the outflow at that time for one reservoir"""
    def __init__(self, name):
        self._name = name
        self.inflowPeak = None
        self.inflowPeakTime = None
        self.outflowPeak = None   #outflow at the time of peak inflow
    def setInflowPeakInfo(self, peak, TOP):
        self.inflowPeak = peak
        self.inflowPeakTime = TOP
    def setOutflowAtInflowPeakTime(self, peak):
        self.outflowPeak = peak

################################################################################
# PEAK FLOWS FROM THE OBSERVED AND UNREGULATED RUNS

def _addedSeries(baseTSM, point, fPart):
    """The base junction series plus an added-flow point's gage, named for the point"""
    tsm = baseTSM.add(point["addTSM"])
    tsInt = DSSPathString(baseTSM.getPath()).getEPart()
    tsm.setPathname("//%s/FLOW//%s/%s/" %(point["name"], tsInt, fPart))
    return tsm

def getJuncPeakFlows(rssRunObs, rssRunUnreg, simDss, outDss, outputJuncs, bar, txtArea, addedByJunc = None):
    """
    Unregulated, modeled observed and (where mapped) observed flows at each
    control point. Writes each to outDss and returns {junction name: JuncPeaks}.
    addedByJunc: {base junction name: [added-flow point dicts]}; each point gets
    its own JuncPeaks (not gaged) from the base junction's series plus its gage.
    """
    if addedByJunc is None: addedByJunc = {}
    juncPeakDict = {}
    initialBar = bar.getValue()
    rssConstant = RssModelVariableConstants.VID_NODE_FLOW
    for i in range(len(outputJuncs)):
        junc = outputJuncs[i]
        bar.setValue(initialBar + int(float(i)/len(outputJuncs)*10))
        juncName = junc.toString()
        msg = "\tJunction: %s" %juncName
        logging.info(msg)
        txtArea.printToGUI(msg)
        jp = JuncPeaks(juncName)
        unregTSM = cResSim.getTSMFromSimulationDSS(simDss, junc, rssRunUnreg, rssConstant, txtArea,
         useObsData=False, isStrict = True, displayMessages = True)
        modeledObsTSM = cResSim.getTSMFromSimulationDSS(simDss, junc, rssRunObs, rssConstant, txtArea,
         useObsData = False, isStrict = True, displayMessages = True)
        addedHere = []
        if addedByJunc.has_key(juncName): addedHere = addedByJunc[juncName]
        for point in addedHere:
            ap = JuncPeaks(point["name"])
            ap.setGaged(False)
            ap.note = point["note"]
            addUnreg = _addedSeries(unregTSM, point, "UNREGULATED")
            ap.setUnregPeakInfo(addUnreg.max(), HecTime(addUnreg.maxDate(), HecTime.MINUTE_INCREMENT))
            outDss.write(addUnreg)
            addObs = _addedSeries(modeledObsTSM, point, "MODELED OBSERVED")
            ap.setModeledObsPeakInfo(addObs.max(), HecTime(addObs.maxDate(), HecTime.MINUTE_INCREMENT))
            outDss.write(addObs)
            juncPeakDict[point["name"]] = ap
            msg = "\tAdded-flow point: %s = %s + %s" %(point["name"], juncName, point["note"])
            logging.info(msg)
            txtArea.printToGUI(msg)
        jp.setUnregPeakInfo(unregTSM.max(), HecTime(unregTSM.maxDate(), HecTime.MINUTE_INCREMENT))
        unregTSM.setLocation(juncName)
        unregTSM.setParameterPart("FLOW")
        unregTSM.setVersion("UNREGULATED")
        outDss.write(unregTSM)
        jp.setModeledObsPeakInfo(modeledObsTSM.max(), HecTime(modeledObsTSM.maxDate(), HecTime.MINUTE_INCREMENT))
        modeledObsTSM.setLocation(juncName)
        modeledObsTSM.setParameterPart("FLOW")
        modeledObsTSM.setVersion("MODELED OBSERVED")
        outDss.write(modeledObsTSM)
        obsTSM = cResSim.getTSMFromSimulationDSS(simDss, junc, rssRunObs, rssConstant, txtArea,
         useObsData=True, isStrict = False, displayMessages = False)
        if obsTSM:
            jp.setObsPeakInfo(obsTSM.max(), HecTime(obsTSM.maxDate(), HecTime.MINUTE_INCREMENT))
            obsTSM.setWatershed("")
            obsTSM.setLocation(juncName)
            obsTSM.setParameterPart("FLOW")
            obsTSM.setVersion("OBSERVED")
            outDss.write(obsTSM)
            jp.setGaged(True)
        else:
            jp.setGaged(False)
        juncPeakDict[juncName] = jp
    return juncPeakDict

def getResvPeakFlows(rssRunObs, simDss, resvElems, reregDict, bar, txtArea):
    """
    Peak modeled inflow, its time, and the outflow at that time for each
    reservoir (the re-reg's outflow for a reservoir with a re-reg).
    Returns {reservoir name: ResvPeaks}, or None on failure.
    """
    resvPeakDict = {}
    network = rssRunObs.getNetwork()
    initialBar = bar.getValue()
    for i in range(len(resvElems)):
        resvElem = resvElems[i]
        resvName = resvElem.toString()
        bar.setValue(initialBar + int(float(i)/len(resvElems)*10))
        txtArea.printToGUI("\tReservoir: %s" %resvName)
        logging.info("\tReservoir: %s" %resvName)
        rp = ResvPeaks(resvName)
        rssConstant = RssModelVariableConstants.VID_POOL_INFLOW
        inTSM = cResSim.getTSMFromSimulationDSS(simDss, resvElem, rssRunObs, rssConstant, txtArea,
         useObsData=False, isStrict = True, displayMessages = True)
        if not inTSM:
            errMsg = "Failed to retrieve inflow data at: %s" %resvName
            errMsg += "\nSee the log file for more details"
            txtArea.printToGUI(errMsg)
            logging.error(errMsg)
            return None
        #For a reservoir with a re-reg, use the re-reg's outflow
        dsResvElem = resvElem
        if resvName in reregDict.keys():
            dsResvElem = network.findReservoir(reregDict[resvName])
        #Observed flows are mapped at the outflow junction (e.g. Cougar_OUT)
        outJunc = dsResvElem.getDownstreamNode().getDownstreamElement()
        rssConstant = RssModelVariableConstants.VID_NODE_FLOW
        outTSM = cResSim.getTSMFromSimulationDSS(simDss, outJunc, rssRunObs, rssConstant, txtArea,
         useObsData = True, isStrict = False, displayMessages = False)
        if outTSM is None:
            #No observed data there - use the modeled flow
            outTSM = cResSim.getTSMFromSimulationDSS(simDss, outJunc, rssRunObs, rssConstant, txtArea,
             useObsData = False, isStrict = True, displayMessages = True)
        if outTSM is None:
            errMsg = "Failed to retrieve outflow data at: %s" %outJunc
            errMsg += "\nSee the log file for more details"
            txtArea.printToGUI(errMsg)
            logging.error(errMsg)
            return None
        timeOfPeakInflow = HecTime(inTSM.maxDate(), HecTime.MINUTE_INCREMENT)
        outTSC = outTSM.getData()
        outflowAtPeakInflowTime = outTSC.values[outTSC.times.index(timeOfPeakInflow.value())]
        rp.setInflowPeakInfo(inTSM.max(), timeOfPeakInflow)
        rp.setOutflowAtInflowPeakTime(outflowAtPeakInflowTime)
        resvPeakDict[resvName] = rp
    return resvPeakDict

################################################################################
# THE MINI-SIMULATIONS

def forceMinRelease(outflowTSM, minRel, conserveVolume=True):
    """
    Caps a time series to a minimum flow. With conserveVolume, the volume added
    to lift a value is taken back from later values as soon as possible, so the
    sum of the series is unchanged (as ResSim would at a reservoir).
    """
    correctedTSM = outflowTSM.copy()
    correctedTSC = correctedTSM.getData()
    values = correctedTSC.values
    runningVolDiff = 0
    for i in range(len(values)):
        if conserveVolume:
            newVal = max(values[i] - runningVolDiff, minRel)
            volDiff = newVal - values[i]
            runningVolDiff += volDiff
        else:
            newVal = max(values[i], minRel)
        values[i] = newVal
    correctedTSC.values = values
    correctedTSM.setData(correctedTSC)
    return correctedTSM

def runResvSimulations(rssRunObs, rssRunUnreg, simDss, outDss, resvsToRun, outputJuncs, juncPeakDict, reregDict, isWith, bar, txtArea, addedByJunc = None):
    """
    Runs every WITH ONLY (isWith=True) or WITHOUT (isWith=False) mini-simulation,
    writes the flow at each control point to outDss, and adds the peaks to juncPeakDict.
    rssRunObs and rssRunUnreg must be on the same network.
    """
    if addedByJunc is None: addedByJunc = {}
    simDssFile = simDss.getFilename()
    if isWith: rssRunObj = rssRunUnreg #no reservoirs except one
    else: rssRunObj = rssRunObs
    network = rssRunObj.getNetwork()
    #Reservoirs with more than one inflow junction (pool Elements, not ReservoirElements)
    confResvDict = cResSim.getConfluenceResvPoolDict(resvsToRun[0].getSystem())
    confResvs = confResvDict.keys()
    #Junction names as strings, since "network" may not be the network resvsToRun came from
    confJuncNames = [j.toString() for j in cResSim.getConfluenceJunctions(network)]
    outputJuncNames = [j.toString() for j in outputJuncs]
    #Time series read once and reused across all the runs
    tsBank = cResSim.tsmBank()
    initialBar = bar.getValue()
    for i in range(len(resvsToRun)):
        resvElem = resvsToRun[i]
        resvName = resvElem.toString()
        msg = "\tReservoir: %s" %resvName
        logging.info(msg)
        txtArea.printToGUI(msg)
        bar.setValue(initialBar + int(float(i)/len(resvsToRun)*40))
        if isWith: fPartOut = "WITH ONLY %s" %resvName
        else: fPartOut = "WITHOUT %s" %resvName
        reregName = ""
        if resvName in reregDict.keys(): reregName = reregDict[resvName]
        #Start from the reservoir inflow (the reservoir passes inflow)
        rssConstant = RssModelVariableConstants.VID_POOL_INFLOW
        flowTSM = cResSim.getTSMFromSimulationDSS(simDss, resvElem, rssRunObj, rssConstant, txtArea,
         useObsData=False, isStrict = True, displayMessages = True)
        #Then work downstream
        dsElems = network.getDownstreamElements(resvElem)
        dsElems.add(0, resvElem)
        for elem in dsElems:
            elemName = elem.toString()
            ##########################################################################
            if isinstance(elem, JunctionElement):
                logging.debug("  Junction: %s" %elemName)
                #Confluence: add the flow from the other upstream reaches
                if elemName in confJuncNames:
                    for rch in cResSim.getConnectedReaches(elem):
                        if rch in dsElems: continue #in the flow path; only tributaries
                        rchNode = rch.getDownstreamNode()
                        tsName = "%s Flow" %rchNode.toString()
                        reachTSM = tsBank.withdrawTS(simDssFile, tsName)
                        if not reachTSM:
                            rssConstant = RssModelVariableConstants.VID_NODE_FLOW
                            reachTSM = cResSim.getTSMFromSimulationDSS(simDss, rchNode, rssRunObj, rssConstant, txtArea,
                             useObsData=False, isStrict = True, displayMessages = True)
                            tsBank.depositTS(simDssFile, tsName, reachTSM)
                        flowTSM = flowTSM.add(reachTSM)
                #Local flows (one node per local; local nodes have no upstream element)
                for node in elem.getNodeVector():
                    if node.getUpstreamElement(): continue
                    tsName = "%s Local Flow" %node.toString()
                    locFlowTSM = tsBank.withdrawTS(simDssFile, tsName)
                    if not locFlowTSM:
                        #Output locals are stored to the node as FLOW (inflow multipliers applied)
                        rssConstant = RssModelVariableConstants.VID_NODE_FLOW
                        locFlowTSM = cResSim.getTSMFromSimulationDSS(simDss, node, rssRunObj, rssConstant, txtArea,
                         useObsData = False, isStrict = True, displayMessages = True)
                        tsBank.depositTS(simDssFile, tsName, locFlowTSM)
                    flowTSM = flowTSM.add(locFlowTSM)
                #Diversions come out (should be 0 in unregulated if that's expected).
                #Ignored unless DPSettings.INCLUDE_DIVERSIONS.
                divElems = None
                if DPSettings.INCLUDE_DIVERSIONS:
                    divElems = cResSim.getConnectedDiversions(elem)
                if divElems:
                    for divElem in divElems:
                        divNode = divElem.getUpstreamNode() #diverted flow is in the upstream node
                        tsName = "%s Diversion Flow" %divNode.toString()
                        divTSM = tsBank.withdrawTS(simDssFile, tsName)
                        if not divTSM:
                            rssConstant = RssModelVariableConstants.VID_NODE_FLOW
                            divTSM = cResSim.getTSMFromSimulationDSS(simDss, divNode, rssRunObj, rssConstant, txtArea,
                             useObsData=False, isStrict = True, displayMessages = True)
                            tsBank.depositTS(simDssFile, tsName, divTSM)
                        flowTSM = flowTSM.subtract(divTSM)
                        flowTSM = forceMinRelease(flowTSM, 0, conserveVolume=False)
            ##########################################################################
            elif isinstance(elem, ReachElement):
                #Reaches can't carry negative flow
                flowTSM = forceMinRelease(flowTSM, 0, conserveVolume=False)
                routeReach = cRouting.buildReach(elem.getFunction())
                if routeReach is None:
                    errMsg = "%s uses routing %s; supported are SSARR, Muskingum, Modified Puls and Null" %(elemName, elem.getFunction().__class__)
                    logging.error(errMsg)
                    txtArea.printToGUI(errMsg)
                    tsBank.close()
                    return None
                flowTSM = TimeSeriesMath(routeReach.routeTSC(flowTSM.getData()))
            ##########################################################################
            elif isinstance(elem, ReservoirElement):
                logging.debug("  Reservoir: %s" %elemName)
                poolElem = cResSim.getPoolElemFromResvElem(elem)
                #Confluence reservoir: add the other upstream junctions
                if poolElem in confResvs and elem != resvElem:
                    for juncElem in confResvDict[poolElem]:
                        if juncElem in dsElems: continue
                        tsName = "%s Junction Flow" %juncElem.toString()
                        juncTSM = tsBank.withdrawTS(simDssFile, tsName)
                        if not juncTSM:
                            rssConstant = RssModelVariableConstants.VID_NODE_FLOW
                            juncTSM = cResSim.getTSMFromSimulationDSS(simDss, juncElem, rssRunObj, rssConstant, txtArea,
                             useObsData=False, isStrict = True, displayMessages = True)
                            tsBank.depositTS(simDssFile, tsName, juncTSM)
                        flowTSM = flowTSM.add(juncTSM)
                isThisProject = (elem == resvElem or elem._name == reregName)
                if isWith and not isThisProject:
                    logging.debug("  Assume passes inflow: %s" %elemName)
                elif not isWith and isThisProject:
                    logging.debug("  Without run - passes inflow: %s" %elemName)
                else:
                    #Apply this reservoir's observed storage change: + outflow - inflow
                    #(inflow minus outflow rather than pool storage, which ResSim
                    #does not balance during the lookback)
                    tsName = "%s Inflow" %elemName
                    inflowTSM = tsBank.withdrawTS(simDssFile, tsName)
                    if not inflowTSM:
                        rssConstant = RssModelVariableConstants.VID_POOL_INFLOW
                        inflowTSM = cResSim.getTSMFromSimulationDSS(simDss, elem, rssRunObs, rssConstant, txtArea,
                         useObsData=False, isStrict = True, displayMessages = True)
                        tsBank.depositTS(simDssFile, tsName, inflowTSM)
                    tsName = "%s Outflow" %elemName
                    outflowTSM = tsBank.withdrawTS(simDssFile, tsName)
                    if not outflowTSM:
                        rssConstant = RssModelVariableConstants.VID_POOL_OUTFLOW
                        outflowTSM = cResSim.getTSMFromSimulationDSS(simDss, elem, rssRunObs, rssConstant, txtArea,
                         useObsData=False, isStrict = True, displayMessages = True)
                        tsBank.depositTS(simDssFile, tsName, outflowTSM)
                    flowTSM = flowTSM.add(outflowTSM)
                    flowTSM = flowTSM.subtract(inflowTSM)
                    flowTSM = forceMinRelease(flowTSM, 0, conserveVolume=True)
            if elemName in outputJuncNames:
                tsInt = DSSPathString(flowTSM.getPath()).getEPart()
                flowTSM.setPathname("//%s/FLOW//%s/%s/" %(elemName, tsInt, fPartOut))
                outDss.write(flowTSM)
                juncPeakDict[elemName].setPeakInfo(resvName, flowTSM.max(), HecTime(flowTSM.maxDate(), HecTime.MINUTE_INCREMENT), isWith)
                addedHere = []
                if addedByJunc.has_key(elemName): addedHere = addedByJunc[elemName]
                for point in addedHere:
                    addTSM = _addedSeries(flowTSM, point, fPartOut)
                    outDss.write(addTSM)
                    juncPeakDict[point["name"]].setPeakInfo(resvName, addTSM.max(), HecTime(addTSM.maxDate(), HecTime.MINUTE_INCREMENT), isWith)
    tsBank.close()
    return juncPeakDict

################################################################################
# RESULTS

def computeReductions(juncNames, resvNames, juncPeakDict):
    """
    Flow reduction credited to each reservoir at each control point it is
    upstream of: average of (unreg - WITH ONLY) and (WITHOUT - modeled observed),
    peaks rounded to the nearest 100 cfs. Stored on the JuncPeaks objects.
    The modeled observed peak is used (not the gage) so a gage reported at a
    different time step than the simulation can't skew it.
    """
    for resvName in resvNames:
        for juncName in juncNames:
            jp = juncPeakDict[juncName]
            if not resvName in jp.getContributingResvs():
                continue
            unregPeak = round(jp.unregPeak, -2)
            obsPeak = round(jp.modeledObsPeak, -2)
            withDiff = unregPeak - round(jp.getPeakWith(resvName), -2)
            withoutDiff = round(jp.getPeakWithout(resvName), -2) - obsPeak
            jp.setFlowReduction(resvName, (withDiff + withoutDiff)/2.)
    return juncPeakDict

def _num(value):
    return "%.0f" %value

def _writeCSV(fileName, rows):
    handle = open(fileName, "wb")
    writer = csv.writer(handle, lineterminator="\n")
    for row in rows:
        writer.writerow(row)
    handle.close()

def exportToCSV(outDir, juncNames, resvNames, juncPeakDict, resvPeakDict, reregDict):
    """Writes the four result tables. Returns the list of files written."""
    if not os.path.exists(outDir):
        os.makedirs(outDir)
    files = []
    #Reduction matrix: control point x reservoir
    rows = [["Preliminary estimated flow reduction at each control point per project (cfs)"],
            ["Average of 2 mini-simulations: WITH ONLY the project and WITHOUT the project"],
            ["The per-project numbers do not always add up to the total reduction and may need adjusting"],
            ["Control Point", "Total Flow Reduction"] + resvNames]
    for juncName in juncNames:
        jp = juncPeakDict[juncName]
        row = [juncName, _num(round(jp.unregPeak, -2) - round(jp.modeledObsPeak, -2))]
        for resvName in resvNames:
            if resvName in jp.getContributingResvs():
                row.append(_num(jp.getFlowReduction(resvName)))
            else:
                row.append("x")
        rows.append(row)
    files.append(os.path.join(outDir, "Preliminary_per_project.csv"))
    _writeCSV(files[-1], rows)
    #Peaks behind each reduction
    rows = [["Reservoir", "Control Point", "Unreg Peak Flow (cfs)", "Modeled Obs Peak Flow (cfs)", "Flow Reduction (cfs)",
             "Without Peak Flow (cfs)", "Peak Discharge Increase (cfs)", "With Only Peak Flow (cfs)",
             "Peak Discharge Reduction (cfs)", "Average Reduction Credited (cfs)"]]
    for resvName in resvNames:
        for juncName in juncNames:
            jp = juncPeakDict[juncName]
            if not resvName in jp.getContributingResvs():
                continue
            unregPeak = round(jp.unregPeak, -2)
            obsPeak = round(jp.modeledObsPeak, -2)
            withPeak = round(jp.getPeakWith(resvName), -2)
            withoutPeak = round(jp.getPeakWithout(resvName), -2)
            rows.append([resvName, juncName, _num(unregPeak), _num(obsPeak), _num(unregPeak - obsPeak),
                         _num(withoutPeak), _num(withoutPeak - obsPeak), _num(withPeak), _num(unregPeak - withPeak),
                         _num(jp.getFlowReduction(resvName))])
    files.append(os.path.join(outDir, "Mini-Simulations.csv"))
    _writeCSV(files[-1], rows)
    #Unregulated vs regulated peak at each control point
    rows = [["Control Point", "Unreg Peak Flow (cfs)", "Date/Time of Unreg Peak", "Regulated Peak Flow (cfs)",
             "Date/Time of Regulated Peak", "Flow Reduction (cfs)", "Regulated Peak Source"]]
    for juncName in juncNames:
        jp = juncPeakDict[juncName]
        unregPeak = round(jp.unregPeak, -2)
        if jp.isGaged:
            regPeak = round(jp.obsPeak, -2)
            regTime = jp.obsPeakTime
            source = "gaged"
        else:
            regPeak = round(jp.modeledObsPeak, -2)
            regTime = jp.modeledObsPeakTime
            source = "ResSim simulated, not gaged"
            if jp.note:
                source = jp.note
        rows.append([juncName, _num(unregPeak), jp.unregPeakTime.toString(4), _num(regPeak),
                     regTime.toString(4), _num(unregPeak - regPeak), source])
    files.append(os.path.join(outDir, "CP_Peaks.csv"))
    _writeCSV(files[-1], rows)
    #Reservoir peak inflow and outflow at that time
    rows = [["Reservoir", "Peak Inflow (cfs)", "Time of Peak", "Outflow at Time of Peak (cfs)", "Flow Difference (cfs)", "Note"]]
    for resvName in resvNames:
        rp = resvPeakDict[resvName]
        inflowPeak = round(rp.inflowPeak, -2)
        outflowAtTOP = round(rp.outflowPeak, -2)
        note = ""
        if resvName in reregDict.keys():
            note = "Outflow is from re-reg: %s" %reregDict[resvName]
        rows.append([resvName, _num(inflowPeak), rp.inflowPeakTime.toString(4), _num(outflowAtTOP),
                     _num(inflowPeak - outflowAtTOP), note])
    files.append(os.path.join(outDir, "Resv_Peaks.csv"))
    _writeCSV(files[-1], rows)
    return files

################################################################################
# ENTRY POINT

def readNameList(txtFile):
    """Names from a config list, one per line, # comments stripped"""
    return cFile.stripOutCommentLines(cFile.fileOpenReadClose(txtFile))

def readAddedFlowPoints(csvFile):
    """
    AddedFlowPoints.csv: Name,BaseJunction,Station,Factor[,Comments], # lines are comments.
    Returns {name: {"name", "base", "station", "factor"}}. A missing file means none.
    """
    points = {}
    if not csvFile or not os.path.exists(csvFile):
        return points
    for line in readNameList(csvFile):
        fields = [f.strip() for f in line.split(",")]
        if len(fields) < 3 or fields[0] == "" or fields[0].upper() == "NAME":
            continue
        factor = 1.0
        if len(fields) > 3 and fields[3] != "":
            factor = float(fields[3])
        points[fields[0]] = {"name": fields[0], "base": fields[1], "station": fields[2], "factor": factor}
    return points

def _loadAddedFlows(points, obsDssFile, tsInt, lookbackTime, endTime, txtArea):
    """
    Reads each added-flow point's gage from obsData.dss (station = B part, C part
    containing FLOW, alternative time step) and multiplies it by its factor.
    Missing hours count as 0, with a warning. Returns an error message, or "".
    """
    errMsg = ""
    obsDss = DSS.open(obsDssFile, lookbackTime, endTime)
    for point in points:
        tsm = cDSS.readTSMfromPathnameParts(obsDss, bPart=point["station"], cPart="*FLOW*", ePart=tsInt)
        if tsm is None:
            errMsg += "\n\t%s: no FLOW record with B part %s at %s in %s" %(point["name"], point["station"], tsInt, obsDssFile)
            continue
        tsm = cTsUtils.transformTSM(tsm, tsInt)
        tsc = tsm.getData()
        values = list(tsc.values)
        nMissing = 0
        for i in range(len(values)):
            if not (values[i] > -900. and values[i] < 1.e30): #missing (-901/-902, UNDEFINED) or NaN
                values[i] = 0.
                nMissing += 1
        if nMissing:
            msg = "WARNING: %s - %d missing hour(s) in gage %s counted as 0; fill them in obsData.dss." %(point["name"], nMissing, point["station"])
            logging.warning(msg)
            txtArea.printToGUI(msg)
        tsc.values = values
        point["addTSM"] = TimeSeriesMath(tsc).multiply(point["factor"])
        point["note"] = "%s (ResSim) + gage %s" %(point["base"], point["station"])
        if point["factor"] != 1.0:
            point["note"] += " x %s" %point["factor"]
        point["note"] += ", not routed"
    obsDss.close()
    return errMsg

def runMiniSimulations(altNameObs, altNameUnreg, outDssFile, outDir, juncFile, resvFile, reregDict, bar, txtArea,
                       addedFile = None, obsDssFile = None):
    """
    Runs all mini-simulations and writes MiniSimulations.dss and the CSV tables.

    :param str altNameObs:   the Observed alternative (computed)
    :param str altNameUnreg: the Unregulated alternative (computed, same network)
    :param str outDssFile:   MiniSimulations.dss
    :param str outDir:       folder for the CSV tables
    :param str juncFile:     ControlPoints.txt
    :param str resvFile:     Reservoirs.txt
    :param dict reregDict:   {reservoir: its re-regulating reservoir}
    :param str addedFile:    AddedFlowPoints.csv (optional)
    :param str obsDssFile:   obsData.dss, read for the added-flow points' gages
    :return: list of CSV files written, or None if the compute stopped
    """
    msg = "----------------------------------------------------------------------"
    msg += "\nComputing Mini-Simulations"
    msg += "\nObserved Alternative:     %s" %altNameObs
    msg += "\nUnregulated Alternative:  %s" %altNameUnreg
    msg += "\nControl points:           %s" %juncFile
    msg += "\nReservoirs:               %s" %resvFile
    msg += "\nRe-regs:                  %s" %reregDict
    msg += "\nAdded-flow points:        %s" %addedFile
    msg += "\nOutput DSS File:          %s" %outDssFile
    msg += "\nOutput CSV Folder:        %s" %outDir
    logging.info(msg)
    txtArea.printToGUI("Computing Mini-Simulations...")
    simPeriod = ResSimController.getSimulation()
    simDssFile = simPeriod.getOutputDSSFilePath()
    startTime, endTime, lookbackTime = ResSimController.getSimulationTimes(simPeriod)
    txtArea.printToGUI("Loading alternatives...")
    runObs = ResSimController.getSpecificRun(simPeriod, altNameObs)
    runUnreg = ResSimController.getSpecificRun(simPeriod, altNameUnreg)
    if runObs is None or runUnreg is None:
        errMsg = "Both alternatives must be in the open simulation: %s, %s" %(altNameObs, altNameUnreg)
        logging.error(errMsg)
        txtArea.printToGUI(errMsg)
        return None
    network = ResSimController.getNetwork(runObs)
    #The RssRun gives access to the regulated output mapping (RssAlt does not)
    rssRunObs = ResSimController.getRssRun(runObs.getKey())
    rssRunUnreg = ResSimController.getRssRun(runUnreg.getKey())
    if rssRunUnreg.getAlternative().getTimestep() != rssRunObs.getAlternative().getTimestep():
        errMsg = "The Observed and Unregulated alternatives have different time steps; they must match."
        logging.error(errMsg)
        txtArea.printToGUI(errMsg)
        return None
    #Check every configured name before computing anything
    juncList = readNameList(juncFile)
    resvList = readNameList(resvFile)
    addedPoints = readAddedFlowPoints(addedFile)
    failElems = []
    outputJuncs = []
    addedByJunc = {}      #base junction name -> [added-flow points]
    addedToLoad = []
    resvsToRun = []
    for resvName in resvList:
        resvElem = network.findReservoir(resvName)
        if not resvElem: failElems.append("reservoir: %s" %resvName)
        elif resvName in reregDict.values(): continue #run with the reservoir above it
        else: resvsToRun.append(resvElem)
    for rereg in reregDict.keys() + reregDict.values():
        if not network.findReservoir(rereg): failElems.append("reservoir in REREG (DPSettings.py): %s" %rereg)
    for juncName in juncList:
        if juncName in addedPoints.keys():
            point = addedPoints[juncName]
            baseElem = network.findJunction(point["base"])
            if baseElem is None:
                failElems.append("base junction of added-flow point %s (AddedFlowPoints.csv): %s" %(juncName, point["base"]))
                continue
            if not point["base"] in [j.toString() for j in outputJuncs]:
                outputJuncs.append(baseElem)
            if not addedByJunc.has_key(point["base"]): addedByJunc[point["base"]] = []
            addedByJunc[point["base"]].append(point)
            addedToLoad.append(point)
            continue
        juncElem = network.findJunction(juncName)
        if juncElem is None: failElems.append("junction: %s" %juncName)
        elif not juncName in [j.toString() for j in outputJuncs]: outputJuncs.append(juncElem)
    if failElems:
        errMsg = "These names are not in the network. Fix the spelling in the config file (or remove them):"
        for failElem in failElems: errMsg += "\n\t%s" %failElem
        errMsg += "\nConfig files:\n\t%s\n\t%s" %(juncFile, resvFile)
        logging.error(errMsg)
        txtArea.printToGUI(errMsg)
        return None
    if not resvsToRun:
        errMsg = "No reservoirs to run - check %s" %resvFile
        logging.error(errMsg)
        txtArea.printToGUI(errMsg)
        return None
    if addedToLoad:
        tsInt = runObs.getRssAlt().getTimeStepString()
        errMsg = _loadAddedFlows(addedToLoad, obsDssFile, tsInt, lookbackTime, endTime, txtArea)
        if errMsg:
            errMsg = "Added-flow point gage not found:" + errMsg + "\nCheck the Station column of %s." %addedFile
            logging.error(errMsg)
            txtArea.printToGUI(errMsg)
            return None
    simDss = DSS.open(simDssFile, lookbackTime, endTime)
    outDss = DSS.open(outDssFile, lookbackTime, endTime)
    txtArea.printToGUI("Retrieving observed and unregulated peak flows for reservoirs...")
    resvPeakDict = getResvPeakFlows(rssRunObs, simDss, resvsToRun, reregDict, bar, txtArea)
    if not resvPeakDict:
        return _stop(simDss, outDss, txtArea)
    txtArea.printToGUI("Retrieving observed and unregulated peak flows for control points...")
    juncPeakDict = getJuncPeakFlows(rssRunObs, rssRunUnreg, simDss, outDss, outputJuncs, bar, txtArea, addedByJunc)
    if not juncPeakDict:
        return _stop(simDss, outDss, txtArea)
    txtArea.printToGUI("Running 'without' simulations...")
    juncPeakDict = runResvSimulations(rssRunObs, rssRunUnreg, simDss, outDss, resvsToRun, outputJuncs, juncPeakDict, reregDict, False, bar, txtArea, addedByJunc)
    if not juncPeakDict:
        return _stop(simDss, outDss, txtArea)
    txtArea.printToGUI("Running 'with only' simulations...")
    juncPeakDict = runResvSimulations(rssRunObs, rssRunUnreg, simDss, outDss, resvsToRun, outputJuncs, juncPeakDict, reregDict, True, bar, txtArea, addedByJunc)
    if not juncPeakDict:
        return _stop(simDss, outDss, txtArea)
    #Results in ControlPoints.txt order (a base junction not listed there is computed but not reported)
    juncNames = juncList
    resvNames = [r.toString() for r in resvsToRun]
    computeReductions(juncNames, resvNames, juncPeakDict)
    files = exportToCSV(outDir, juncNames, resvNames, juncPeakDict, resvPeakDict, reregDict)
    simDss.close()
    outDss.close()
    bar.setValue(100)
    msg = "Output DSS File: %s" %outDssFile
    for f in files: msg += "\nOutput CSV: %s" %f
    msg += "\nCompute Complete!"
    logging.info(msg)
    txtArea.printToGUI(msg)
    return files

def _stop(simDss, outDss, txtArea):
    logging.error("COMPUTE FAILED")
    txtArea.printToGUI("COMPUTE FAILED")
    simDss.close()
    outDss.close()
    return None
