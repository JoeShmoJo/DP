"""
Stand-ins for the HEC Java classes, so the Damages Prevented modules (and the
NWDJyLib code they call) can run outside ResSim under plain Jython 2.7.

Not a ResSim emulator. It provides only what these scripts touch:
  - in-memory DSS files (hec.hecmath.DSS.open) keyed by file and pathname,
  - a TimeSeriesMath/TimeSeriesContainer pair on hourly integer times,
  - network elements with nodes, time-series record proxies and mappings.
Running against these proves the Python logic (traversal, routing calls,
arithmetic, file handling). It proves nothing about whether a Java method
exists in ResSim 4.1 - only running in ResSim does that.

Call install(watershedDir) before importing any module under test.
"""
import sys, types, os, copy, fnmatch

################################################################################
# DSS / time series

STORE = {}   #(FILE, PATHNAME-WITHOUT-D) -> TimeSeriesContainer

def _key(fileName, path):
    return (os.path.abspath(str(fileName)).upper(), _noD(path).upper())

def _parts(path):
    p = str(path).split("/")
    while len(p) < 8:
        p.append("")
    return p[1:7]

def _noD(path):
    a, b, c, d, e, f = _parts(path)
    return "/%s/%s/%s//%s/%s/" %(a, b, c, e, f)

class HecMathException(Exception): pass
class DSSFileException(Exception): pass

class HecTime(object):
    MINUTE_INCREMENT = 1
    def __init__(self, t=0, inc=None):
        if isinstance(t, HecTime): t = t.value()
        self._t = int(t)
    def value(self): return self._t
    def notEqualTo(self, other): return self._t != HecTime(other).value()
    def dateAndTime(self, style=None): return "t=%d" %self._t
    def toString(self, style=None): return "t=%d" %self._t
    def __str__(self): return self.toString()

class TimeSeriesContainer(object):
    def __init__(self, times=None, values=None, fullName=""):
        self.times = list(times or [])
        self.values = [float(v) for v in (values or [])]
        self.interval = 60
        self.numberValues = len(self.values)
        self.fullName = fullName
        self.type = "PER-AVER"
        self.units = "cfs"
        self.location = _parts(fullName)[1]
    def clone(self):
        return copy.deepcopy(self)

class TimeSeriesMath(object):
    def __init__(self, tsc=None):
        if tsc is None: tsc = TimeSeriesContainer()
        self._tsc = tsc
    def getData(self): return self._tsc.clone()
    def getContainer(self): return self._tsc
    def setData(self, tsc): self._tsc = tsc
    def copy(self): return TimeSeriesMath(self._tsc.clone())
    def _combine(self, other, op):
        new = self._tsc.clone()
        if isinstance(other, TimeSeriesMath):
            assert other._tsc.times == new.times, "time windows differ"
            new.values = [op(a, b) for a, b in zip(new.values, other._tsc.values)]
        else:
            new.values = [op(a, float(other)) for a in new.values]
        return TimeSeriesMath(new)
    def add(self, other): return self._combine(other, lambda a, b: a + b)
    def subtract(self, other): return self._combine(other, lambda a, b: a - b)
    def multiply(self, other): return self._combine(other, lambda a, b: a * b)
    def max(self): return max(self._tsc.values)
    def maxDate(self):
        v = self._tsc.values
        return self._tsc.times[v.index(max(v))]
    def firstValidDate(self): return self._tsc.times[0]
    def lastValidDate(self): return self._tsc.times[-1]
    def getPath(self): return self._tsc.fullName
    def setPathname(self, p): self._tsc.fullName = p
    def _setPart(self, i, value):
        p = _parts(self._tsc.fullName)
        p[i] = value
        self._tsc.fullName = "/" + "/".join(p) + "/"
    def setWatershed(self, v): self._setPart(0, v)
    def setLocation(self, v): self._setPart(1, v); self._tsc.location = v
    def setParameterPart(self, v): self._setPart(2, v)
    def setEPart(self, v): self._setPart(4, v)
    def setVersion(self, v): self._setPart(5, v)
    def getType(self): return self._tsc.type
    def setType(self, v): self._tsc.type = v
    def setUnits(self, v): self._tsc.units = v
    def transformTimeSeries(self, *args):
        raise AssertionError("fake_hec: everything here is 1HOUR, no interval conversion expected")

class DSSFile(object):
    def __init__(self, fileName):
        self._file = os.path.abspath(str(fileName))
    def getFilename(self): return self._file
    def read(self, path):
        k = _key(self._file, path)
        if k not in STORE:
            raise HecMathException("no record %s in %s" %(path, self._file))
        tsc = STORE[k].clone()
        tsc.fullName = _noD(path)
        return TimeSeriesMath(tsc)
    def write(self, tsm):
        tsc = tsm.getData()
        STORE[_key(self._file, tsc.fullName)] = tsc
    def getCatalogedPathnames(self, scan):
        want = {}
        for item in scan.split():
            k, v = item.split("=")
            want[k] = v.upper()
        out = []
        for (f, path) in STORE.keys():
            if f != self._file.upper(): continue
            a, b, c, d, e, fp = _parts(path)
            ok = True
            for k, v in want.items():
                actual = {"B": b, "C": c, "E": e, "F": fp}[k]
                if not fnmatch.fnmatch(actual, v): ok = False
            if ok: out.append("/%s/%s/%s/01JAN2026/%s/%s/" %(a, b, c, e, fp))
        return out
    def close(self): pass

class DSS(object):
    @staticmethod
    def open(fileName, start=None, end=None):
        return DSSFile(fileName)

class DSSPathString(object):
    def __init__(self, path): self._p = _parts(path)
    def getAPart(self): return self._p[0]
    def getBPart(self): return self._p[1]
    def getCPart(self): return self._p[2]
    def getEPart(self): return self._p[4]
    def getFPart(self): return self._p[5]
    def setDPart(self, d): self._p[3] = d
    def getPathname(self): return "/" + "/".join(self._p) + "/"

def putRecord(fileName, path, values, times):
    STORE[_key(fileName, path)] = TimeSeriesContainer(times, values, _noD(path))

def getRecord(fileName, path):
    return STORE.get(_key(fileName, path))

################################################################################
# Network

class RssModelVariableConstants(object):
    VID_NODE_FLOW = 1
    VID_NODE_KNOWNFLOW = 2
    VID_POOL_INFLOW = 3
    VID_POOL_OUTFLOW = 4

class JVector(list):
    """java.util.Vector: add(x) appends, add(i, x) inserts"""
    def add(self, a, b=None):
        if b is None: self.append(a)
        else: self.insert(a, b)

class TSRecordProxy(object):
    def __init__(self, name, factor=1.0):
        self._name = name
        self._factor = factor
    def getName(self): return self._name
    def getFactor(self): return self._factor

class Node(object):
    def __init__(self, name, up=None, down=None):
        self._name = name
        self.up = up
        self.down = down
        self.proxies = {}
    def getUpstreamElement(self): return self.up
    def getDownstreamElement(self): return self.down
    def getTSRecordProxy(self, vid): return self.proxies.get(vid)
    def toString(self): return self._name
    def __str__(self): return self._name

class Element(object):
    def __init__(self, name):
        self._name = name
        self.dsNode = None
        self.nodes = []
        self.connected = []
        self.proxies = {}
        self.parent = None
        self.kids = []
        self.function = None
        self.system = None
    def toString(self): return self._name
    def __str__(self): return self._name
    def __repr__(self): return "<%s %s>" %(self.__class__.__name__, self._name)
    def getDownstreamNode(self): return self.dsNode
    def getNodeVector(self): return list(self.nodes)
    def getConnectedElements(self): return list(self.connected)
    def getTSRecordProxy(self, vid): return self.proxies.get(vid)
    def getParent(self): return self.parent
    def children(self): return list(self.kids)
    def getFunction(self): return self.function
    def getSystem(self): return self.system

class JunctionElement(Element): pass
class ReachElement(Element): pass
class ReservoirElement(Element): pass
class DiversionElement(Element): pass

class NullRouting(object): pass
class SsarrRouting(object): pass
class PulsChannelRoutingWithLosses(object): pass
class MuskingumRouting(object): pass

class TSRecord(object):
    def __init__(self, name, vid, dssFile, path, param="Flow"):
        self._name = name
        self._vid = vid
        self._file = dssFile
        self._path = path
        self._param = param
    def getName(self): return self._name
    def getParamName(self): return self._param
    def getVariableId(self): return self._vid
    def getDSSFilename(self): return self._file
    def getDSSPathname(self): return self._path
    def setDSSFilename(self, f): self._file = f

class TSDataSet(object):
    def __init__(self): self.recs = {}
    def put(self, rec): self.recs[(rec.getName(), rec.getVariableId())] = rec
    def getTSRecord(self, name, vid): return self.recs.get((name, vid))
    def getTSRecords(self): return list(self.recs.values())

class Network(object):
    """A toy RssSystem. Elements are added in downstream order per branch."""
    def __init__(self, watershedDir):
        self.wsDir = watershedDir
        self.junctions = {}
        self.reaches = {}
        self.reservoirs = {}
        self.headwaters = []
        self.flowOrder = []   #every element, upstream to downstream along each path
    def makeAbsolutePathFromWatershed(self, rel):
        if rel == "": return ""
        return os.path.abspath(os.path.join(self.wsDir, rel))
    def getJunctionNames(self): return list(self.junctions.keys())
    def findJunction(self, n): return self.junctions.get(str(n))
    def getReachNames(self): return list(self.reaches.keys())
    def findReach(self, n): return self.reaches.get(str(n))
    def findReservoir(self, n): return self.reservoirs.get(str(n))
    def getReservoirNames(self): return list(self.reservoirs.keys())
    def getHeadwaterJunctions(self): return list(self.headwaters)
    def getDownstreamElements(self, start):
        """Elements below start, following the network to the mouth"""
        out = JVector()
        elem = start
        while True:
            node = elem.getDownstreamNode()
            if node is None or node.getDownstreamElement() is None: break
            nxt = node.getDownstreamElement()
            if nxt._name == "Pool": nxt = nxt.getParent()
            out.append(nxt)
            elem = nxt
        return out

################################################################################
# ResSim application objects

class Workspace(object):
    def __init__(self, wsDir): self.wsDir = wsDir
    def makeAbsolutePath(self, rel): return os.path.abspath(os.path.join(self.wsDir, rel))

class _ClientApp(object):
    ws = None
    @staticmethod
    def Workspace(): return _ClientApp.ws

class RunTimeWindow(object):
    def __init__(self, lookback, start, end):
        self.l, self.s, self.e = lookback, start, end
    def getStartTimeString(self): return str(self.s)
    def getEndTimeString(self): return str(self.e)
    def getLookbackTimeString(self): return str(self.l)

class RssAlt(object):
    def __init__(self, timestep, obsSet, inputSet):
        self._ts = timestep
        self._obs = obsSet
        self._input = inputSet
    def getTimeStepString(self): return self._ts
    def getTimestep(self): return self._ts
    def getObservedTSDataSet(self): return self._obs
    def getInputTSDataSet(self): return self._input

class RssRun(object):
    def __init__(self, network, alt, regOutput):
        self._net = network
        self._alt = alt
        self._out = regOutput
    def getNetwork(self): return self._net
    def getAlternative(self): return self._alt
    def getObservedTSData(self): return self._alt.getObservedTSDataSet()
    def getRegOutputTSData(self): return self._out

class SimRun(object):
    def __init__(self, userName, key, network, alt):
        self._user = userName
        self._key = key
        self._net = network
        self._alt = alt
    def getUserName(self): return self._user
    def getKey(self): return self._key
    def getRssSystem(self): return self._net
    def getRssAlt(self): return self._alt

class Simulation(object):
    def __init__(self, rtw, simDss):
        self._rtw = rtw
        self._simDss = simDss
        self.runs = {}
    def getRunTimeWindow(self): return self._rtw
    def getOutputDSSFilePath(self): return self._simDss
    def getSimulationRuns(self): return list(self.runs.values())
    def getSimulationRun(self, name): return self.runs.get(name)

class Module(object):
    sim = None
    rssRuns = {}
    def getName(self): return "Simulation"
    def getSimulation(self): return Module.sim
    def getRssRun(self, key): return Module.rssRuns.get(key)

class _ResSim(object):
    @staticmethod
    def getCurrentModule(): return Module()

################################################################################

def _mod(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m

def _dummy(name):
    return type(name, (object,), {})

def install(watershedDir):
    _ClientApp.ws = Workspace(watershedDir)
    for pkg in ("hec", "hec.rss", "hec.heclib", "hec.clientapp", "hec.client", "hec.dssgui"):
        _mod(pkg)
    constants = type("Constants", (object,), {"TRUE": True, "FALSE": False})
    _mod("hec.script", Constants=constants, MessageBox=_dummy("MessageBox"), Plot=_dummy("Plot"),
         ResSim=_ResSim, ClientAppWrapper=_dummy("ClientAppWrapper"))
    _mod("hec.rss.script", ResSim=_ResSim, ClientAppWrapper=_dummy("ClientAppWrapper"))
    _mod("hec.clientapp.client", ClientApp=_ClientApp)
    _mod("hec.client", ClientApp=_ClientApp)
    _mod("hec.heclib.util", HecTime=HecTime, Heclib=_dummy("Heclib"))
    _mod("hec.heclib.dss", HecDss=_dummy("HecDss"), HecDataManager=_dummy("HecDataManager"))
    _mod("hec.hecmath", DSS=DSS, DSSFile=DSSFile, TimeSeriesMath=TimeSeriesMath, TextMath=_dummy("TextMath"),
         HecMathException=HecMathException, DSSFileException=DSSFileException)
    _mod("hec.lang", DSSPathString=DSSPathString)
    _mod("hec.io", TimeSeriesContainer=TimeSeriesContainer, PairedDataContainer=_dummy("PairedDataContainer"),
         TextContainer=_dummy("TextContainer"))
    _mod("hec.model", PairedValuesExt=_dummy("PairedValuesExt"), RunTimeStep=_dummy("RunTimeStep"),
         RunTimeWindow=RunTimeWindow, SeasonalValue=_dummy("SeasonalValue"))
    _mod("hec.dssgui", HecDssVue=_dummy("HecDssVue"))
    model = dict(JunctionElement=JunctionElement, ReachElement=ReachElement, ReservoirElement=ReservoirElement,
                 DiversionElement=DiversionElement, NullRouting=NullRouting, SsarrRouting=SsarrRouting,
                 PulsChannelRoutingWithLosses=PulsChannelRoutingWithLosses, MuskingumRouting=MuskingumRouting,
                 RssModelVariableConstants=RssModelVariableConstants)
    for n in ("SpecifiedRelease", "DiversionRule", "TimeSeries", "ConstantRelease", "MonthlyRelease",
              "ReservoirDamElement", "DivertedOutletElement", "ReservoirOutletElement", "Dam", "ControlStructure"):
        model[n] = _dummy(n)
    _mod("hec.rss.model", **model)
