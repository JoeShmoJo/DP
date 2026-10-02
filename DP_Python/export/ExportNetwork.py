###############################################################################
# Export Network for DP_Python
#
# Paste ALL of this file into a ResSim Scripts-pane script (Simulation module,
# Script > New/Edit), save, and run it with the simulation that holds the
# Observed and Unregulated alternatives open.
#
# Writes <watershed>/DP_Python_export/network.json: everything the Damages
# Prevented scripts read from ResSim, so DP_Python can run without it:
#   - junctions, reaches, reservoirs and how they connect
#   - the local inflows at each junction and their inflow multipliers
#   - each reach's routing (SSARR, Muskingum, Modified Puls, Null) and parameters
#   - the compute order, headwaters, confluences and each reservoir's
#     downstream path, from the same NWDJyLib helpers the ResSim menu uses
#   - for every alternative in the simulation, the Observed Data and
#     Time-Series mappings (which DSS record feeds which location)
# Copy the file to DP_Python/network/network.json in the repo.
#
# Rerun it whenever the network, the routing or the alternative mappings change.
# Only reads the model; changes nothing.
#
# Oct 2026, for the Willamette watershed in ResSim 4.1.
###############################################################################
try:
    from hec.rss.script import ResSim                  #ResSim 4.1
except ImportError:
    from hec.script import ResSim                      #ResSim 3.5
from hec.rss.model import JunctionElement, ReachElement, ReservoirElement, DiversionElement
from hec.rss.model import SsarrRouting, NullRouting
from hec.rss.model import MuskingumRouting, PulsChannelRoutingWithLosses
from hec.rss.model import RssModelVariableConstants
import os, sys, json, time

################################################################################
# USER INPUT
OUTPUT_REL = "DP_Python_export/network.json"   #relative to the watershed folder
EXPORT_VERSION = 1

################################################################################
# FIND THE WATERSHED AND NWDJyLib

def _openSimulation():
    module = ResSim.getCurrentModule()
    if module.getName() != "Simulation":
        raise AssertionError("Run this from the Simulation module. ResSim is in the %s module." %module.getName())
    simulation = module.getSimulation()
    if not simulation:
        raise AssertionError("Open the simulation holding the Observed and Unregulated alternatives, then run this again.")
    return simulation

################################################################################
# ELEMENT IDS

def elemId(elem):
    """'junction:<name>', 'reach:<name>', 'reservoir:<name>', 'pool:<reservoir>', 'diversion:<name>', or None"""
    if elem is None:
        return None
    if isinstance(elem, JunctionElement):
        return "junction:%s" %elem.toString()
    if isinstance(elem, ReachElement):
        return "reach:%s" %elem.toString()
    if isinstance(elem, ReservoirElement):
        return "reservoir:%s" %elem.toString()
    if isinstance(elem, DiversionElement):
        return "diversion:%s" %elem.toString()
    if elem.toString() == "Pool":
        try:
            return "pool:%s" %elem.getParent().toString()
        except:
            pass
    return "other:%s" %elem.toString()

def _downstreamId(elem):
    try:
        return elemId(elem.getDownstreamNode().getDownstreamElement())
    except:
        return None

def _proxyName(obj, vid):
    try:
        tsrp = obj.getTSRecordProxy(vid)
    except:
        return None
    if tsrp is None:
        return None
    return str(tsrp.getName())

def _floats(values):
    out = []
    for v in values:
        out.append(float(v))
    return out

################################################################################
# ROUTING

def routingInfo(routingObj):
    """Everything NWDJyLib/cRouting.buildReach reads, as plain values"""
    if isinstance(routingObj, SsarrRouting):
        info = {"method": "SSARR", "supported": True, "subreaches": int(routingObj.getNumberReaches())}
        if routingObj.getKTS():
            info["kts"] = float(routingObj.getKTS())
            info["n"] = float(routingObj.getNCoefficient())
        else:
            table = routingObj.getOutflowTimeOfStorageTable()
            info["table"] = {"outflow": _floats(table.getXArray()), "timeOfStorage": _floats(table.getYArray())}
        return info
    if isinstance(routingObj, PulsChannelRoutingWithLosses):
        stors = []
        flows = []
        for pulsRecord in routingObj.getPulsVector():
            stors.append(float(pulsRecord.stor))
            flows.append(float(pulsRecord.outflow))
        info = {"method": "Modified Puls", "supported": True, "subreaches": int(routingObj.getnumberReaches()),
                "storage": stors, "outflow": flows}
        try:
            info["hasChannelLosses"] = bool(routingObj.getHasChannelLosses())
        except:
            pass
        return info
    if isinstance(routingObj, MuskingumRouting):
        return {"method": "Muskingum", "supported": True, "subreaches": int(routingObj.getnumberReaches()),
                "k": _floats(routingObj.getmuskingumK()), "x": _floats(routingObj.getmuskingumX())}
    if isinstance(routingObj, NullRouting):
        return {"method": "Null", "supported": True}
    return {"method": routingObj.__class__.__name__, "supported": False}

################################################################################
# NETWORK

def junctionLocals(junc):
    """Local inflow nodes at a junction, as cWaterBalance finds them"""
    name = junc.toString()
    locs = []
    for node in junc.getNodeVector():
        if str(node.getDownstreamElement()) != name: continue
        if node.getUpstreamElement(): continue #a connected element, not a local
        tsrp = node.getTSRecordProxy(RssModelVariableConstants.VID_NODE_KNOWNFLOW)
        if not tsrp: continue
        locs.append({"node": node.toString(),
                     "knownFlowProxy": str(tsrp.getName()),
                     "factor": float(tsrp.getFactor()),
                     "flowProxy": _proxyName(node, RssModelVariableConstants.VID_NODE_FLOW)})
    return locs

def exportNetwork(network, cResSim):
    elements = {}
    diversions = {}
    for name in network.getJunctionNames():
        junc = network.findJunction(name)
        connected = []
        for e in junc.getConnectedElements():
            connected.append(elemId(e))
            if isinstance(e, DiversionElement):
                diversions[elemId(e)] = {"type": "diversion", "name": e.toString(), "junction": name}
        elements[elemId(junc)] = {
            "type": "junction", "name": str(name),
            "downstream": _downstreamId(junc),
            "flowProxy": _proxyName(junc.getDownstreamNode(), RssModelVariableConstants.VID_NODE_FLOW),
            "connected": connected,
            "locals": junctionLocals(junc)}
    for name in network.getReachNames():
        reach = network.findReach(name)
        elements[elemId(reach)] = {
            "type": "reach", "name": str(name),
            "downstream": _downstreamId(reach),
            "flowProxy": _proxyName(reach.getDownstreamNode(), RssModelVariableConstants.VID_NODE_FLOW),
            "routing": routingInfo(reach.getFunction())}
    confResvDict = cResSim.getConfluenceResvPoolDict(network)
    for name in network.getReservoirNames():
        resv = network.findReservoir(name)
        pool = cResSim.getPoolElemFromResvElem(resv)
        upstream = []
        if pool in confResvDict.keys():
            for j in confResvDict[pool]:
                upstream.append(elemId(j))
        dsElems = []
        for e in network.getDownstreamElements(resv):
            dsElems.append(elemId(e))
        elements[elemId(resv)] = {
            "type": "reservoir", "name": str(name),
            "pool": elemId(pool),
            "downstream": _downstreamId(pool),
            "confluenceInflowJunctions": upstream,
            "inflowProxy": _proxyName(resv, RssModelVariableConstants.VID_POOL_INFLOW),
            "outflowProxy": _proxyName(resv, RssModelVariableConstants.VID_POOL_OUTFLOW),
            "downstreamElements": dsElems}
    for key in diversions.keys():
        elements[key] = diversions[key]
    order = []
    for e in cResSim.orderElementsFromUpstream(network):
        order.append(elemId(e))
    return {
        "elements": elements,
        "orderFromUpstream": order,
        "headwaterJunctions": [elemId(j) for j in cResSim.getRealHeadwaterJunctions(network)],
        "confluenceJunctions": [elemId(j) for j in cResSim.getConfluenceJunctions(network)],
        "confluenceReservoirs": dict([(elemId(p), [elemId(j) for j in confResvDict[p]]) for p in confResvDict.keys()])}

################################################################################
# ALTERNATIVE MAPPINGS

def tsRecords(tsDataSet):
    recs = []
    for tsRec in tsDataSet.getTSRecords():
        recs.append({"name": str(tsRec.getName()),
                     "variableId": int(tsRec.getVariableId()),
                     "param": str(tsRec.getParamName()),
                     "dssFile": str(tsRec.getDSSFilename()),
                     "pathname": str(tsRec.getDSSPathname())})
    return recs

def exportAlternatives(simulation):
    alts = {}
    for run in simulation.getSimulationRuns():
        alt = run.getRssAlt()
        alts[str(run.getUserName())] = {
            "timeStep": str(alt.getTimeStepString()),
            "observed": tsRecords(alt.getObservedTSDataSet()),
            "input": tsRecords(alt.getInputTSDataSet())}
    return alts

################################################################################
# MAIN

def main():
    simulation = _openSimulation()
    network = None
    for run in simulation.getSimulationRuns():
        network = run.getRssSystem()
        break
    if network is None:
        raise AssertionError("The open simulation has no alternatives.")
    scriptsDir = str(network.makeAbsolutePathFromWatershed("scripts"))
    if not scriptsDir in sys.path:
        sys.path.append(scriptsDir)
    from NWDJyLib.ResSim import cResSim, ResSimController

    startTime, endTime, lookbackTime = ResSimController.getSimulationTimes(simulation)
    out = {
        "exportVersion": EXPORT_VERSION,
        "exported": time.strftime("%Y-%m-%d %H:%M"),
        "watershedDir": str(network.makeAbsolutePathFromWatershed("")),
        "simulationWindow": {"lookback": str(lookbackTime), "start": str(startTime), "end": str(endTime)},
        "variableIds": {
            "NODE_FLOW": int(RssModelVariableConstants.VID_NODE_FLOW),
            "NODE_KNOWNFLOW": int(RssModelVariableConstants.VID_NODE_KNOWNFLOW),
            "POOL_INFLOW": int(RssModelVariableConstants.VID_POOL_INFLOW),
            "POOL_OUTFLOW": int(RssModelVariableConstants.VID_POOL_OUTFLOW),
            "OPRULETS_TSINPUT": int(RssModelVariableConstants.VID_OPRULETS_TSINPUT)},
        "network": exportNetwork(network, cResSim),
        "alternatives": exportAlternatives(simulation)}

    outFile = str(network.makeAbsolutePathFromWatershed(OUTPUT_REL))
    outDir = os.path.dirname(outFile)
    if not os.path.exists(outDir):
        os.makedirs(outDir)
    handle = open(outFile, "w")
    try:
        json.dump(out, handle, indent=1, sort_keys=True)
    finally:
        handle.close()

    nets = out["network"]
    counts = {}
    for e in nets["elements"].values():
        counts[e["type"]] = counts.get(e["type"], 0) + 1
    unsupported = []
    for e in nets["elements"].values():
        if e["type"] == "reach" and not e["routing"]["supported"]:
            unsupported.append("%s (%s)" %(e["name"], e["routing"]["method"]))
    msg = "Exported %s" %outFile
    msg += "\n   %s" %", ".join(["%s: %d" %(k, counts[k]) for k in sorted(counts.keys())])
    msg += "\n   alternatives: %s" %", ".join(sorted(out["alternatives"].keys()))
    if unsupported:
        msg += "\n   WARNING - reaches with routing DP_Python can't reproduce: %s" %", ".join(unsupported)
    print msg
    return outFile

main()
