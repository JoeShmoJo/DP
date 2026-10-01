from __future__     import with_statement
from hec.heclib.dss import *
from com.rma.client import Browser
#
## Config ##
#located in shared directory, all paths will be copied to the forecast.dss
copyFromDSSFileName = "columbia10_6hr.dss"
#
### Functions ##
def output(msg="") :
	'''
	Output to console log
	'''
	Browser.getBrowserFrame().addMessage("%s" %  msg)
	
def chktab(tab) :
	'''
	Checks that the "Modeling" tab is selected
	'''
	if tab.getTabTitle() != "Modeling" : 
		msg = "The Modeling tab must be selected"
		output("ERROR : %s" % msg)
		raise Exception(msg)
	 
def chkfcst(fcst) :
	'''
	Checks that a forecast is open
	'''
	if fcst is None : 
		msg = "A forecast must be open"
		output("ERROR : %s" % msg)
		raise Exception(msg)
## This section finds the current forecast.dss file (i.e. active forecast) ##
## Get the current forecast ##
frame = Browser.getBrowser().getBrowserFrame()
proj = frame.getCurrentProject()
pane = frame.getTabbedPane()
tab = pane.getSelectedComponent()
chktab(tab)
fcst = tab.getForecast()
chkfcst(fcst)
fcstTimeWindowString = str(fcst.getRunTimeWindow())
fcstNames = fcst.getForecastRunNames()
fcstRun = fcst.getForecastRun(fcstNames[0])
fcstRunKey = fcstRun.getKey()
fcstDssFileName = fcst.getOutDssPath()
#
#
## Copy ESP Data ##
output("\n\nCopying ESP data to forecast DSS\n\n")
shdir    = proj.getProjectDirectory() + "/shared"
copyFromDSSFilePath = shdir+"/"+copyFromDSSFileName
dssFile = HecDss.open(copyFromDSSFilePath)
allPaths = dssFile.getCatalogedPathnames()
#
#copy all paths to forecast DSS
splitTimeWindow = fcstTimeWindowString.split("; ")
startTimeSplit = [e.replace(",","") for e in splitTimeWindow[0].split(" ")]
endTimeSplit = [e.replace(",","") for e in splitTimeWindow[2].split(" ")]
timeWindowString = "%02g%s%4g 2400 %02g%s%4g 2400" % \
  (int(startTimeSplit[0]), startTimeSplit[1][:3].upper(), int(startTimeSplit[2]),
  int(endTimeSplit[0]), endTimeSplit[1][:3].upper(), int(endTimeSplit[2]))
#output(timeWindowString)
dssFile.setTimeWindow(timeWindowString)
#
#output("\nSet start time:\t%s\nSet end time:\t%s" % (dssFile.getStartTime(), dssFile.getEndTime()))
dssFile.copyRecordsFrom(fcstDssFileName, allPaths)
dssFile.done()
