from __future__     import with_statement
from hec.script import *
from hec2.rts.script import *
from javax.swing import *
from java.awt import Toolkit
from javax.swing.event import ListSelectionListener, ChangeListener
from java.awt.event import ActionListener, WindowListener
from hec.io import TimeSeriesContainer
from hec.heclib.util import *
from hec.script.Constants import *
from hec.hecmath import *
from hec.dssgui import ListSelection
from hec.heclib.dss import *
from hec.dataTable import *
from com.rma.client import Browser
import time, thread, wcds, java, javax, os, operator,  hec, traceback, string
def output(msg="") :
	'''
	Output to console log
	'''
	print ("%s : %s" % (progname, msg))
def error(msg) :
	'''
	Outputs an error message and rasies an exception
	'''
	output(msg)
	raise Exception(msg)
	
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
try :
	try :
################## Stection-Start ####################################################################
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
		
		dssfile = fcst.getOutDssPath()
		cwmsFile = HecDss.open(dssfile)
		
		#print 'fcstTimeWindowString : %s' %(fcstTimeWindowString)
		important_times = [ i.strip(' ') for i in fcstTimeWindowString.split(';') ]
		start_time, forecast_time, end_time = important_times[0], important_times[1], important_times[2]
		
		cwmsFile.setTimeWindow(start_time, end_time)
		
################## Stection-End ######################################################################
################## Stection-Start ####################################################################
		## Enter your script in this section	##
#### This section gets data from the Forecast DSS file.
	
		
		RFCVID = cwmsFile.get("//MCKENZIE_AT VIDA/FLOW/01APR2019/3HOUR/------R0/")
		SimVIDflow = cwmsFile.get("//MCKENZIE_AT VIDA/FLOW-IN//3HOUR/------R0/")
		RFCVIDflow = cwmsFile.get("/MCKENZIE RIVER/VIDA OR/FLOW//1HOUR/USGS 14162500/")
		VIDflood = cwmsFile.get("/VIDFLOODSTAGE//FLOW/01MAR2019/1HOUR/FLOOD_STAGE/")
		VIDbank = cwmsFile.get("/VIDBANKFULL//FLOW/01MAR2019/1HOUR/BANK_FULL/")
		
		RFCGOS = cwmsFile.get("//GOSO/FLOW--INST/01MAR2019/IR-MONTH/RFC-FCST/")
		SimGOSflow = cwmsFile.get("//CF WILLAMETTE_NR GOSHEN/FLOW-IN/01JUL2019/3HOUR/------R0/")
		RFCGOSflow = cwmsFile.get("/COAST FORK WILLAMETTE RIVER/GOSHEN OR/FLOW/01MAR2019/1HOUR/USGS 14157500/")
		GOSflood = cwmsFile.get("/GOSFLOODSTAGE//FLOW/01MAR2019/1HOUR/FLOOD_STAGE/")
		GOSbank = cwmsFile.get("/GOSBANKFULL//FLOW/01MAR2019/1HOUR/BANK_FULL/")
		
		RFCJAS = cwmsFile.get("//JASO/FLOW--INST/01MAR2019/IR-MONTH/RFC-FCST/")
		SIMJASflow = cwmsFile.get("//MF WILLAMETTE+FALL TO MF WILLAMETTE_AT JASPER/FLOW/01AUG2019/3HOUR/------R0/")
		RFCJASflow = cwmsFile.get("/MIDDLE FORK WILLAMETTE RIVER/JASPER OR/FLOW/01MAR2019/1HOUR/USGS 14152000/")
		JASflood = cwmsFile.get("/JASFLOODSTAGE//FLOW/01MAR2019/1HOUR/FLOOD_STAGE/")
		JASbank = cwmsFile.get("/JASBANKFULL//FLOW/01MAR2019/1HOUR/BANK_FULL/")		
		
		RFCEUG = cwmsFile.get("//EUGO/FLOW--INST/01MAR2019/IR-MONTH/RFC-FCST/")
		SIMEUGflow = cwmsFile.get("//WILLAMETTE_AT EUGENE/FLOW/01AUG2019/3HOUR/------R0/")
		RFCEUGflow = cwmsFile.get("/WILLAMETTE/EUGENE/FLOW/01MAR2019/1HOUR/OBSERVED/")
		EUGflood = cwmsFile.get("/EUGFLOODSTAGE//FLOW/01MAR2019/1HOUR/FLOOD_STAGE/")
		EUGbank = cwmsFile.get("/EUGBANKFULL//FLOW/01MAR2019/1HOUR/BANK_FULL/")
		
### Create Plot ####
		VID_Plot = Plot.newPlot("VIDA Project Forecast")
		Layout = Plot.newPlotLayout()
		#TopView = Layout.addViewport(10)
		BottomView = Layout.addViewport(10)
		BottomView.addCurve("Y1", RFCVID)
		BottomView.addCurve("Y1", SimVIDflow)
		BottomView.addCurve("Y1", RFCVIDflow)
		#TopView.addCurve("Y1", VIDflood)
		#TopView.addCurve("Y1", VIDbank)
		VID_Plot.configurePlotLayout(Layout)
		VID_Plot.showPlot()
		
		GOS_Plot = Plot.newPlot("Goshen Project Forecast")
		Layout = Plot.newPlotLayout()
		#TopView = Layout.addViewport(10)
		BottomView = Layout.addViewport(10)
		BottomView.addCurve("Y1", RFCGOS)
		BottomView.addCurve("Y1", SimGOSflow)
		BottomView.addCurve("Y1", RFCGOSflow)
		#TopView.addCurve("Y1", GOSflood)
		#TopView.addCurve("Y1", GOSbank)
		GOS_Plot.configurePlotLayout(Layout)
		GOS_Plot.showPlot()
		
		JAS_Plot = Plot.newPlot("Jasper Project Forecast")
		Layout = Plot.newPlotLayout()
		#TopView = Layout.addViewport(10)
		BottomView = Layout.addViewport(10)
		BottomView.addCurve("Y1", RFCJAS)
		BottomView.addCurve("Y1", SIMJASflow)
		BottomView.addCurve("Y1", RFCJASflow)
		#TopView.addCurve("Y1", JASflood)
		#TopView.addCurve("Y1", JASbank)
		JAS_Plot.configurePlotLayout(Layout)
		JAS_Plot.showPlot()
		
		EUG_Plot = Plot.newPlot("Eugene Project Forecast")
		Layout = Plot.newPlotLayout()
		#TopView = Layout.addViewport(10)
		BottomView = Layout.addViewport(10)
		BottomView.addCurve("Y1", RFCEUG)
		BottomView.addCurve("Y1", SIMEUGflow)
		BottomView.addCurve("Y1", RFCEUGflow)
		#TopView.addCurve("Y1", EUGflood)
		#TopView.addCurve("Y1", EUGbank)
		EUG_Plot.configurePlotLayout(Layout)
		EUG_Plot.showPlot()
		
####### Plot Line Styles####
		#OBSMarkTwainElevCurve = MTL_Plot.getCurve(OBSMarkTwainElev)
		#OBSMarkTwainElevCurve.setLineWidth(6)
		#SimMarkTwainElev_7Curve = MTL_Plot.getCurve(SimMarkTwainElev_7QPF)
		#SimMarkTwainElev_7Curve.setLineColor("darkgreen")
		#SimMarkTwainElev_7Curve.setLineStyle("dash")
		#SimMarkTwainElev_7Curve.setLineWidth(7)
		#SimMarkTwainElev_0Curve = MTL_Plot.getCurve(SimMarkTwainElev_0QPF)
		#SimMarkTwainElev_0Curve.setLineColor("blue")
		#SimMarkTwainElev_0Curve.setLineStyle("dash")
		#SimMarkTwainElev_0Curve.setLineWidth(5)
		#OBSMarkTwainOutflowCurve = MTL_Plot.getCurve(OBSMarkTwainOutflow)
		#OBSMarkTwainOutflowCurve.setLineColor("black")
		#OBSMarkTwainOutflowCurve.setLineWidth(6)
		#SimMarkTwainOutflow_7Curve.setLineColor("darkgreen")
		#SimMarkTwainOutflow_7Curve.setLineStyle("dash")
		#SimMarkTwainOutflow_7Curve.setLineWidth(7)
		#SimMarkTwainOutflow_0Curve = MTL_Plot.getCurve(SimMarkTwainOutflow_0QPF)
		#SimMarkTwainOutflow_0Curve.setLineColor("blue")
		#SimMarkTwainOutflow_0Curve.setLineStyle("dash")
		#SimMarkTwainOutflow_0Curve.setLineWidth(5)
#####Axis Formating####
		TopViewport = VID_Plot.getViewport(0)
		BottomViewport = VID_Plot.getViewport(1)
		Top_Y_Axis = TopViewport.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport.getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport.getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(4)
		Top_Y_Axis.setLabel("FLOW CFS")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)
		BottomViewport = VID_Plot.getViewport(0)
		BottomViewport = VID_Plot.getViewport(1)
		Bottom_Y_Axis = BottomViewport.getAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(4)
		Bottom_Y_Axis.setLabel("FLOW CFS")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)
		
		TopViewport = GOS_Plot.getViewport(0)
		BottomViewport = GOS_Plot.getViewport(1)
		Top_Y_Axis = TopViewport.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport.getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport.getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(4)
		Top_Y_Axis.setLabel("FLOW CFS")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)
		BottomViewport = GOS_Plot.getViewport(0)
		BottomViewport = GOS_Plot.getViewport(1)
		Bottom_Y_Axis = BottomViewport.getAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(4)
		Bottom_Y_Axis.setLabel("FLOW CFS")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)
		
		TopViewport = JAS_Plot.getViewport(0)
		BottomViewport = JAS_Plot.getViewport(1)
		Top_Y_Axis = TopViewport.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport.getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport.getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(4)
		Top_Y_Axis.setLabel("FLOW CFS")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)
		BottomViewport = JAS_Plot.getViewport(0)
		BottomViewport = JAS_Plot.getViewport(1)
		Bottom_Y_Axis = BottomViewport.getAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(4)
		Bottom_Y_Axis.setLabel("FLOW CFS")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)
		
		TopViewport = EUG_Plot.getViewport(0)
		BottomViewport = EUG_Plot.getViewport(1)
		Top_Y_Axis = TopViewport.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport.getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport.getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(1000)
		Top_Y_Axis.setLabel("FLOW CFS")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)
		BottomViewport = EUG_Plot.getViewport(0)
		BottomViewport = EUG_Plot.getViewport(1)
		Bottom_Y_Axis = BottomViewport.getAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(4)
		Bottom_Y_Axis.setLabel("FLOW CFS")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)
		
###### Save Plot as A jpeg####
		VID_Plot.setSize(1400, 1300)
		VID_Plot.setLocation(100, 100)
		VID_Plot.saveToJpeg("C:\CWMS\Plots\VID_FcstPlot.jpg")
		#VID_Plot.close()
		
		GOS_Plot.setSize(1400, 1300)
		GOS_Plot.setLocation(100, 100)
		GOS_Plot.saveToJpeg("C:\CWMS\Plots\GOS_FcstPlot.jpg")
		#GOS_Plot.close()
		
		JAS_Plot.setSize(1400, 1300)
		JAS_Plot.setLocation(100, 100)
		JAS_Plot.saveToJpeg("C:\CWMS\Plots\JAS_FcstPlot.jpg")
		#JAS_Plot.close()
		
		EUG_Plot.setSize(1400, 1300)
		EUG_Plot.setLocation(100, 100)
		EUG_Plot.saveToJpeg("C:\CWMS\Plots\EUG_FcstPlot.jpg")
		#EUG_Plot.close()
		
################ Set Data up for exporting to Excel####
		#datasets = java.util.Vector()
		#datasets.add(OBSLOSElev)
		#datasets.add(SimLOSElev)
		#datasets.add(SimLOSInflow)
		#datasets.add(OBSLOSOutflow)
		#datasets.add(SimLOSOutflow)
		#datasets.add(RFCLOSInflow)
		#list = []
		#list.append(datasets)
		#ExcelTable = HecDataTableToExcel.newTable()
		#ExcelTable.createExcelFile(list,"C:\CWMS\Data\LOSLakeFCstData.xls")
		#os.popen("C:\CWMS\Data\LOSLakeFCstData.xls")
################## Stection-End ######################################################################
		
	except Exception, e :
		MessageBox.showError(' '.join(e.args), "Python Error")
	except java.lang.Exception, e :
		MessageBox.showError(e.getMessage(), "Error")
finally:
	cwmsFile.done()
