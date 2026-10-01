"""
This module contains various code for dealing with DSS-VUE "collections".
Collections do not exist in the publicly available DSS-VUE
(version 2.0.1.16, February 2010).
Some of this functionality is used by the :any:`cEnsemble` module.
"""

from hec.heclib.util import HecTime
from hec.heclib.dss import HecDss
from hec.heclib.dss import DSSPathname
from hec.io import TimeSeriesContainer
from hec.io import TimeSeriesCollectionContainer
import logging
import math
from NWDJyLib import cFile

################################################################################
# STATIC INPUT

################################################################################
# CLASS DEFINITIONS

class CyclicCollection:
    """Class that takes a collection dataset and does cyclic analysis on it.
    For example, this can be used to calculate the 50% trace of ESP data.
    After creating the object, data should be added via :meth:`addData` or :meth:`addAllData`.
    Then, :meth:`runCyclicAnalysis` can be executed and results retrieved with
    :meth:`getCyclicTSC`
    
    :param list percentiles: desired percentiles in decimal form e.g. [.05,.95]
                     can have "MEAN", "MAX", "MIN" as well. 
                     If not provided here, can set later via :meth:`setPercentiles`
    """
    def __init__(self, percentiles=[]):
        self.hasOverride = False # if the values of all percentiles are to be overriden for a period of time (e.g. lookback)
        self.Override = None
        self.percentiles = percentiles # intended to be a list like [.05,.95], can have "MEAN", "MAX", "MIN" as well
        self.rawTSCs = [] # list of timeseries containers
        self.cyclicTimes = [] # list of cyclic analysis times
        #Define a big data dictionary that has a key for each time, 
        #with each "value" being a list of all values for that timestep 
        self.cyclicData = {}
        self.cyclicTSCs = [] # list of time series containers that have done cyclic analysis
        self.numYears = 0
        self.origPath = ""
    def setPercentiles(self, pcs):
        """Define the output percentile traces, if not provided on initialization.
        
        :param list pcs: desired percentiles in decimal form e.g. [.05,.95]
                         can have "MEAN", "MAX", "MIN" as well
        """
        self.percentiles = pcs
    def addData(self, tsc):
        """Add one additional TimeSeriesContainer to the collection"""
        self.rawTSCs.append(tsc)
        self.numYears += 1
    def addAllData(self, tscList):
        """Input a list of TimeSeriesContainer objects to populate the object"""
        for tsc in tscList:
            self.addData(tsc)
    def addOverride(self, tsc):
        """If specified, this timeseries will override all other percentile output. 
        Can be a subset of the times of the larger group of timeseries. 
        (e.g. for lookback plotting)
        """
        self.Override = tsc
        self.hasOverride = True
    def applyOverride(self):
        """At concurrent timestamps, override all the values of the computed 
        cyclic analyses with this time series
        """
        if self.hasOverride:
            for cyclicTSC in self.cyclicTSCs:
                for i in range(len(cyclicTSC.times)):
                    if cyclicTSC.times[i] in self.Override.times:
                        idx = self.Override.times.index(cyclicTSC.times[i])
                        cyclicTSC.values[i] = self.Override.values[idx] 
    def _prepTSC(self, tscTemplate):
        """Creates a TimeSeriesContainer that will hold an output cyclic analysis.
        The output pathname is not fully well defined after this step yet-
        it is just a copy of the input.
        Called by :meth:`runCyclicAnalysis`
        
        :param TimeSeriesContainer tscTemplate: has desired output units, type, and pathname
        """
        tsc = TimeSeriesContainer()
        tsc.times = self.cyclicTimes
        tsc.numberValues = len(tsc.times)
        tsc.units = tscTemplate.units
        tsc.type = tscTemplate.type
        self.origPath = tscTemplate.fullName
        tsc.fullName = tscTemplate.fullName
        #dssPath = DSSPathname(tscTemplate.fullName)
        #dssPath.setFPart("Cyclic Analysis")
        #tsc.fullName = dssPath.getPathname()
        return tsc
    def _organizeData(self):
        """Populate the cyclicData dictionary in preparation for cyclic analysis
        For each timestep, add the data value from every input timeseries
        Invoked by :meth:`runCyclicAnalysis`
        """
        self.cyclicTimes = list(self.rawTSCs[0].times)
        for i in range(len(self.cyclicTimes)):
            self.cyclicData[self.cyclicTimes[i]] = []
            for j in range(len(self.rawTSCs)):
                self.cyclicData[self.cyclicTimes[i]].append(self.rawTSCs[j].values[i])
            self.cyclicData[self.cyclicTimes[i]].sort() #sort ascending
    def _getRenamedPathname(self, pc):
        """
        Return a pathname that is suitable for writing the cyclic analysis output.
        Must be run after :meth:`_prepTSC`, so that the .origPath field is populated.
        The C-part of the output will reflect the input.
        The F-part of the output will do the following:
        
            1. If the input F-part signals a collection (e.g. C:001949|), 
               strip the collection identifier out, but leave the rest of the f-part
            2. Append a modifier to the F-part (e.g. "-P50", "MAX")
        
        Invoked by :meth:`runCyclicAnalysis`
        The old way of doing this modified the C-part and renamed the f-part "CYCLIC ANALYSIS"
        
        :param pc: a decimal percentile or the following strings: "MAX", "MIN", "MEAN", "AVERAGE"
        :return outPath: The renamed pathname (string)
        """
        dssPath = DSSPathname(self.origPath.upper())
        if DSSPathname.isaCollectionPath(dssPath.getPathname()):
            #If it's a collection, strip the collection identifier out the f-part
            dssPath = DSSPathname(dssPath.getPathname(True)) #removes the collection
        #Now tack on the modifier to the F-part
        if isinstance(pc, str):
            if dssPath.getFPart() == "": #Don't include the leading dash if blank
                newFPart = pc
            else:
                newFPart = "%s-%s" %(dssPath.getFPart(), pc) #eg TESTING-MAX
            #dssPath.setCPart("%s-%s" %(dssPath.getCPart(), pc)) #eg FLOW-MAX
        else:
            if dssPath.getFPart() == "": #Don't include the leading dash if blank
                newFPart = "p%02.0f" %pc*100
            else:
                newFPart = "%s-p%02.0f" %(dssPath.getFPart(), pc*100) #eg TESTING-P50
            #dssPath.setCPart("%s-p%.0f" %(dssPath.getCPart(), pc*100)) #eg FLOW-P50
        #dssPath.setFPart("CYCLIC ANALYSIS")
        dssPath.setFPart(newFPart)
        outPath = dssPath.getPathname()
        return outPath
        
    def runCyclicAnalysis(self):
        """The meat of the class. This method takes the TimeSerieses loaded
        and performs the cyclic analysis calculations. After this is done, 
        the .cyclicTSCs attribute is filled in and :meth:`getCyclicTSC` can be used
        """
        self._organizeData()
        cyclicTSC = self._prepTSC(self.rawTSCs[0])
        self.cyclicTSCs = []
        for k in range(len(self.percentiles)):
            pc = self.percentiles[k]
            #idx = int(round(pc*(self.numYears-1),0)) #old way of doing it
            pcVals = []
            for i in range(len(self.cyclicTimes)):
                #pcVals.append(self.cyclicData[self.cyclicTimes[i]][idx])
                listForCurrentTime = self.cyclicData[self.cyclicTimes[i]]
                if pc == "MAX":
                    pcVals.append(max(listForCurrentTime))
                elif pc == "MIN":
                    pcVals.append(min(listForCurrentTime))
                elif pc == "MEAN" or pc == "AVERAGE":
                    pcVals.append(sum(listForCurrentTime)/len(listForCurrentTime))
                else: #must be a number
                    pcVals.append(percentile(listForCurrentTime, pc))
            cyclicTSC.values = pcVals
            #Reset the pathname of the output
            cyclicTSC.fullName = self._getRenamedPathname(pc)
            self.cyclicTSCs.append(cyclicTSC.clone())
        return True
    def getCyclicTSC(self, pct):
        """Retrieve one of the previously calculated percentile traces
        
        :param pct: One of the input percentiles previously defined in this object (float or string)
        :return TimeSeriesContainer: the percentile trace
        """
        if pct not in self.percentiles: 
            print "ERROR! The percentile specified is not in the list"
            return None
        idx = self.percentiles.index(pct)
        cyclicTSC = self.cyclicTSCs[idx]
        return cyclicTSC
    def writeAll(self, dssFile):
        """writes all cyclic records to an already open dssFile (DssFile or HecDss)"""
        for cyclicTSC in self.cyclicTSCs:
            dssFile.put(cyclicTSC)  
            
class CyclicCollectionPlot:
    """Class for generating plots of cyclic collections. Currently only used
    For NWP's Willamette ESP modeling. Poorly documented"""
    def __init__(self, cc):
        self.cc = cc # Should be a CyclicCollection object
        self.plot = Plot.newPlot("") # hec.gfx2d.G2dDialog
        self.layout = Plot.newPlotLayout() # hec.gfx2d.PlotLayout
        self.view = self.layout.addViewport(100.) #hec.gfx2d.ViewportLayout
        self.lcDict = lcDict # line color dictionary (expected to be defined earlier)
        self.lwStd = 2. # standard line weight
    def setSize(self, x, y):
        self.plot.setSize(x,y)
    def setTitle(self, titleStr):
        self.plot.setPlotTitleText(titleStr)
        title = self.plot.getPlotTitle()
        title.setFont("Arial Black")
        title.setFontSize(18)
        self.plot.setPlotTitleVisible(True)
    def setTimeOfForecast(self, timeStr):
        # sets a vertical line marker for the time of forecast
        # e.g. timeStr = "30Jan3001 2400"
        marker = G2dMarkerProperties()
        marker.setHasLabel(True)
        marker.setLabel("Time of Forecast")
        marker.setLabelPosition(1) # to the right of the vertical line
        marker.setLabelAlignment(1) # right alignment (top of screen)
        marker.setDrawOnAxis(0) # 0 = x axis, 1 = y axis
        marker.setDrawLine(True)
        marker.setDrawLabel(True)
        marker.setLinePattern([10.0,4.0]) # 10 pixels colored followed by 4 uncolored
        hTime = HecTime(timeStr, HecTime.MINUTE_INCREMENT)
        marker.setMarkerValue(hTime.value())
        self.vp.addAxisMarker(marker)           
    def setGrid(self, dotPat):
        # dotPat = list of floats, 1st entry is solid pixes, 2nd entry is empty pixels
        panel = self.plot.getPlotpanel()
        panel.setHorizontalViewportSpacing(0)
        prop = self.vp.getProperties()      
        prop.setMajorXGridStyle(dotPat)
        prop.setMajorYGridStyle(dotPat)     
    def setYAxisTitle(self, yTitle):
        yaxis = self.vp.getAxis("Y1")
        yaxis.setLabel(yTitle)
    def addCurves(self):
        for i in range(len(self.cc.cyclicTSCs)-1,-1,-1): # loop backwards
            #shift data back to the current year
            shiftStr = "-%sY" %(3001-int(curYear))
            TSMY = TimeSeriesMath(self.cc.cyclicTSCs[i])
            TSMY = TSMY.shiftInTime(shiftStr)
            self.view.addCurve("Y1", TSMY.getData())
            #self.view.addCurve("Y1", self.cc.cyclicTSCs[i])    
    def setupPlotAfterAllCurvesAdded(self):
        self.plot.configurePlotLayout(self.layout)
        self.plot.setSize(1000, 800)
        self.vp = self.plot.getViewport(0) # hec.gfx2d.Viewport
    def save(self, fName):
        # must have done "showPlot()" before you can save to file!
        if not os.path.exists(os.path.dirname(fName)):
            os.makedirs(os.path.dirname(fName))
        self.plot.saveToPng(fName)
    def show(self):
        self.plot.showPlot()
    def close(self):
        self.plot.close()
    def generateCyclicPlot(self, titleString, legendParam, startTimeStr):
        # function to generate a nicely fomatted plot with the non-exceddances
        # startTimeStr = the start time of the simulation
        if self.cc.hasRC: #do this first so it pops up first in the legend
            #shift data back to the current year
            shiftStr = "-%sY" %(3001-int(curYear)) #e.g. "-950Y"
            tsmRC = TimeSeriesMath(self.cc.RC)
            tsmRC = tsmRC.shiftInTime(shiftStr)
            self.view.addCurve("Y1", tsmRC.getData())
            #self.view.addCurve("Y1", self.cc.RC)
        self.addCurves() #add in the meat of the data
        self.setupPlotAfterAllCurvesAdded()
        if self.cc.hasRC:
            rcCurve = self.plot.getCurve(self.cc.RC) # hec.gfx2d.G2dLine
            rcCurve.setLineColor("black")
            rcCurve.setLineWidth(3.)
            #rcCurve.setLineStyle("Dash") # since the parameter is elev-zone, it auto-makes it dashed
            rcLabel = self.plot.getLegendLabel(self.cc.RC)
            rcLabel.setText("Rule Curve")
        # The easy way of changing legend labels didn't work, so we have to do it the hard way
        legendProps = self.plot.getLegend().getProperties().getLegendItemProperties()#list of hec.gfx2d.G2dLabelDrawProp
        legendIdx = 0
        if self.cc.hasRC: legendIdx +=1
        for i  in range(len(self.cc.percentiles)-1,-1,-1): #loop backwards 
            pc = self.cc.percentiles[i]
            curve = self.plot.getCurve(self.cc.cyclicTSCs[i])
            if not self.lcDict.has_key(pc):
                #MessageBox.showError("No line color defined for percentile: %s\nFix the 'lcDict' parameter in the script" %pc, "Error")
                msg = "No line color defined for percentile: %s\nFix the 'lcDict' parameter in the script" %pc, "Error"
                raise AssertionError, msg
            curve.setLineColor(self.lcDict[pc])
            curve.setLineWidth(self.lwStd)
            #put fill underneath the line (actually, it looks pretty bad--don't do it
            #curve.setFillColor(self.lcDict[pc])
            #curve.setFillPattern("below") #this doesn't work. default is solid, not sure how to change it
            #curve.setFillType("below") #this works, whether to fill above or below the curve
            # This approach doesn't work! need to do showPlot() first but I want to wait until the end
            #legendLabel = self.plot.getLegendLabel(self.cc.cyclicTSCs[i]) 
            #legendLabel.setText("%.0f%s %s Non-Exceedance" %(pc*100, '%', legendParam))
            legendProps[legendIdx].text = "%.0f%s %s Non-Exceedance" %(pc*100, '%', legendParam)
            legendIdx += 1
        if "ELEV" in legendParam.upper():
            #for elevation entries, put a disclaimer on the plot
            self.plot.getLegend().setTitle(disclaimerText) #set the legend title to the disclaimer
        self.plot.getLegend().refreshLegendItems()
        self.setTitle(titleString)      
        self.setYAxisTitle("%s (%s)" %(legendParam, self.cc.cyclicTSCs[0].units)) 
        self.setGrid([2.,8.])  #  grid pattern - 2 solid pixels followed by 8 blank ones
        #set time of forecast on current year
        curYearFcstStr = startTimeStr.replace("3001", curYear)
        self.setTimeOfForecast(curYearFcstStr)
        #self.setTimeOfForecast(startTimeStr) #3001 data
        return self.plot
# END OF CLASS DEFINITIONS
################################################################################
# FUNCTION DEFINITIONS
def getCollectionSequences(dssFile, examplePath):
    """
    This function shows how many separate items comprise a DSS-VUE Collection.
    Each item in a collection is a "sequence"
    
    :param dssFile: The already opened dss file (DSSFile or HecDss) with data
    :param str examplePath: An example pathname to test how many collections there are. 
            e.g. "//ALFW1/FLOW-LOC//6HOUR//", The D and F-parts are ignored
    :return list: a list of all the sequences existing in the collection in the dss file.
                  Strings. (e.g. [001956, 001957])
    """
    exampleDssPath = DSSPathname(examplePath)
    aPart, bPart, cPart, dPart, ePart, fPart = exampleDssPath.getParts()
    paths = dssFile.getCatalogedPathnames("A=%s B=%s C=%s E=%s" %(aPart, bPart, cPart, ePart))
    collectionList = []
    for path in paths:
        #should return something like: "//ALFW1/FLOW-LOC/01NOV2015/6HOUR/C:001949|/"
        dssPath = DSSPathname(path)
        if DSSPathname.isaCollectionPath(path):
            #collectionNum = dssPath.getFPart().split("|")[0].split(":")[-1]
            collectionNum = dssPath.getCollectionSequence()
            if not collectionNum in collectionList: collectionList.append(collectionNum)
    return collectionList

def percentile(numList, percent):
    """
    Find the percentile of a list of values.

    :param list numList: a list of values. MUST BE already sorted from low to high.
    :param float percent: a float value from 0.0 to 1.0.

    :return float: the percentile of the values
    """
    key=lambda x:x #key function to compute value from each element of numList.
    if not numList:
        return None
    k = (len(numList)-1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return key(numList[int(k)])
    d0 = key(numList[int(f)]) * (c-k)
    d1 = key(numList[int(c)]) * (k-f)
    return d0+d1
    
def summarizeCollectionPathnames(inputDssFile, pathListFile, percentiles, beginTimeStr=None, endTimeStr=None):
    """
    Generates summary hydrographs for DSS-VUE collections.
    The collections on which to do the operation are specified as input.
    It will spit out the output to the input file, with a different f-part.
    
    :param str inputDssFile: The full path of the dss file with the data
    :param str pathListFile: The full path of the input text file with a list of pathnames to process
    :param list percentiles: desired percentiles in decimal form e.g. [.05,.95]
    :param str beginTimeStr: If supplied, the timewindow to extract the data. 
                             e.g. "02Jun1985 2400"
                             If not supplied, the entire timewindow will be done
    """
    logging.info("extraction start date         %20s" % beginTimeStr)
    logging.info("extraction end date           %20s" % endTimeStr)
    logging.info("Input Dss File: %s" %inputDssFile)
    logging.info("Input pathname file: %s" %pathListFile)
    
    dssFile = HecDss.open(inputDssFile)
    lines = cFile.fileOpenReadClose(pathListFile)
    lines = cFile.stripOutCommentLines(lines)
    #First pathname should be something like "//ALFW1/FLOW-LOC//6HOUR/C:001949|/"
    #Find the sequences comprising the collection from the 1st pathname as template
    sequenceList = getCollectionSequences(dssFile, lines[0].strip()) #e.g. [001948,001949...]
    logging.debug("List of sequences: %s" %sequenceList)
    failPaths = [] #List of pathnames that failed to process
    for i, line in enumerate(lines): 
        path = line.strip()     
        logging.info("Processing %s of %s: %s" %(i+1, len(lines), path))
        dssPath = DSSPathname(path.upper()) #.get() needs an uppercase string
        #Initialize the CyclicCollection object
        cycColl = CyclicCollection(percentiles)
        #Stuff the CyclicCollection object with data for each sequence in the collection
        for sequenceStr in sequenceList:
            dssPath.setCollectionSequence(sequenceStr)
            if beginTimeStr is None:
                #Grab the entire window
                tsc = dssFile.get(dssPath.getPathname(), True)
            else:
                #User-specified input, just grab a subset of the time window
                tsc = dssFile.get(dssPath.getPathname(), beginTimeStr, endTimeStr)
            if not tsc:
                logging.warning("\tFailed to read: %s" %path)
                failPaths.append(path)
                continue
            cycColl.addData(tsc)
        #Compute the statistics and write out the summary hydrographs
        cycColl.runCyclicAnalysis()
        cycColl.writeAll(dssFile)
    if len(failPaths) > 0:
        logging.warning("Failed to extract the following paths:")
        for failPath in failPaths: logging.warning("\t%s" %failPath)
    dssFile.close()
    return True
    
def resetTSMappingCollectionFparts(tsDataSet, collectionStr):
    """
    Resets the F-part of dss pathnames for an entire time series data set.
    Any time series inputs that are not collections will be skipped.
    Typically used in ensemble data processing using ResSim time series mapping.
    This actually modifies the input tsDataSet, so it will be changed.
    For instance, if the timeseries mapping for a location was:
    
    "//ALFW1/FLOW-LOC/01NOV2015/6HOUR/C:001949|ResSim-myTest/"
    
    And the input collectionStr was "001950", the pathname would be changed to:
    
    "//ALFW1/FLOW-LOC/01NOV2015/6HOUR/C:001950|ResSim-myTest/"
    
    :param TSDataSet tsDataSet: The input time series mapping that will be changed
    :param collectionStr: String or integer. The collection index to set the 
        f-part of the timeseries mapping to e.g. "001960" or 1960
    :return: True if successful. The input TSDataSet object now has all of the
             f-parts reset to the desired collectionStr
    """
    for tsRecord in tsDataSet.getTSRecords():
        path = tsRecord.getDSSPathname()
        if DSSPathname.isaCollectionPath(path):
            dssPath = DSSPathname(path)
            dssPath.setCollectionSequence(collectionStr)
            tsRecord.setDSSPathname(dssPath.getPathname())
    return True
