from hec.heclib.util   import HecTime
from hec2.rts.client   import RTS
from hec2.rts.script   import Forecast
from java.awt          import Frame
from java.awt          import Container
import threading, time
from hec.script.Constants import TRUE, FALSE
from javax.swing import JOptionPane
from hec.dataTable import *
from hec.script import *
from hec.heclib.dss import *
from hec.hecmath import *
from hec.heclib import grid
from hec.heclib.grid import *
from hec.heclib.util import HecTime
import sys, time
#**************************************************************************************************
# Open the DSS File
forecast = RTS.getBrowserFrame().getForecastTab().getForecast()
forecastDSSFilePath = forecast.getForecastDSSFilename()
rtw = forecast.getRunTimeWindow()
rtwString = str(rtw)
startTime = rtw.getLookbackTimeString()
endTime = rtw.getEndTimeString()
print rtwString
important_times = [ i.strip(' ') for i in rtwString.split(';') ]
startTime, forecastTime, endTime = important_times[0], important_times[1], important_times[2]
print forecastTime
hecTimeforecast=HecTime()
hecTimeforecast.set(forecastTime)
dssFile = HecDss.open(forecastDSSFilePath)
print "\n________________________________________________________________________"
print forecastDSSFilePath, "(", startTime, " to ", endTime, ")\A"
#############################################################################################################
#   Fill in the following two lines to match the gridded temperature data from your extract.
originalFpart = "QTB"
cPart = "AIRTEMP"
#manualFPart = "QO" Use this to manually specify new F part
#############################################################################################################
#### Get the F Parts of the model alternatives
SelectedFcst = Forecast.getSelectedForecast()
SelectedFcstName = SelectedFcst.getName()
FcstRunNames = SelectedFcst.getForecastRunNames()
FPartList = []
for FcstName in FcstRunNames :
	FcstRun = SelectedFcst.getForecastRun(FcstName)
	ModelAlt = FcstRun.getModelAlternatives()
	FPartList.append(FcstRun.getFPart(ModelAlt[0]))
print "F Part will change to:  ", FPartList[0], "\S\"
#### Get a list of the extracted forecast temperature records that are beyond the forecast time 
pathnames =  dssFile.getPathnameList()
forecastTimePathnames = []
for each in pathnames:
	if cPart in each:
			if originalFpart in each:
				testPath = DSSPathname(each)
				dpart = testPath.getDPart()
				hecTimeRecord = HecTime()
				hecTimeRecord.set(dpart)
				if hecTimeRecord > hecTimeforecast:
					forecastTimePathnames.append(each)
if len(forecastTimePathnames) == 0:
	print "----NO FORECAST TEMPERATURE PATHNAMES FOUND. EXITING.----"
	exit()
### First gets a grid container with the extracted temperature grid
### Second, clones the grid container and sets the F part (from above) to mimic MFP output 
### Third, modifys the time window of the grid in the metadata. Not sure why, but during the...
### forecast time MFP outputs instantaneous temp grids with a 6 hour time span in the metadata. 
### This script mimics that 6 hour time span in the metadata
### Fourth, the grid is converted from deg F to deg C and matches 
###
def RenameAndConvert(NewFPart):
	for each in forecastTimePathnames:
				print ("Original Record:  ", each)
				dssPathname = DSSPathname(each)
				gridContainer = dssFile.get(each)
				dssPathname.setFPart(NewFPart)
				newgridContainer = gridContainer.clone()
				newgridContainer.fullName = str(dssPathname)
				recEndTime = HecTime(dssPathname.dPart())
				recStartTime = recEndTime.clone()
				recStartTime.addHours(-6)
				newgridContainer.getGridInfo().setGridTimes(recStartTime, recEndTime)
				theGrid = newgridContainer.getGridData()
				subGrid = GridUtilities.scalarSubtract(theGrid, 32)
				multGrid = GridUtilities.scalarMultiply(subGrid, 0.556)
				newgridContainer.gridData = multGrid
				newgridContainer.getGridInfo().setDataUnits("deg C")
				dssFile.put(newgridContainer)
				print ("Grids Renamed to: \n", dssPathname , "\n\n")
		
				
def computeAlternative(currentAlternative, computeOptions):
	global _currentAlt
	_currentAlt = currentAlternative
	global rtw
	rtw = computeOptions.getRunTimeWindow()
	RenameAndConvert(FPartList[0])
	return 
	print ("Done, closing Forecast.dss \n\n")
	dssFile.close()
