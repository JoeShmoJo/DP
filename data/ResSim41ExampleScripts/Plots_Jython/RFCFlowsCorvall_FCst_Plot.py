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
	
		
		RFCMON = cwmsFile.get("//MNRO/FLOW--INST/01MAR2019/IR-MONTH/RFC-FCST/")
		SimMONflow = cwmsFile.get("//LONG TOM_AT MONROE/FLOW/01AUG2019/3HOUR/------R0/")
		OUTMONflow = cwmsFile.get("/LONG TOM RIVER/MONROE OR/FLOW/01MAR2019/1HOUR/USGS 14170000/")
		MONflood = cwmsFile.get("/MONFLOODSTAGE//FLOW/01MAR2019/1HOUR/FLOOD_STAGE/")
		MONbank = cwmsFile.get("/MONBANKFULL//FLOW/01MAR2019/1HOUR/BANK_FULL/")
		
		RFCHAR = cwmsFile.get("//HARO/FLOW--INST/01MAR2019/IR-MONTH/RFC-FCST/")
		SimHARflow = cwmsFile.get("//WILLAMETTE_AT HARRISBURG/FLOW/01AUG2019/3HOUR/------R0/")
		RFCHARflow = cwmsFile.get("/WILLAMETTE RIVER/HARRISBURG OR/FLOW/01MAR2019/1HOUR/USGS 14166000/")
		HARflood = cwmsFile.get("/HARFLOODSTAGE//FLOW/01MAR2019/1HOUR/FLOOD_STAGE/")
		HARbank = cwmsFile.get("/HARBANKFULL//FLOW/01MAR2019/1HOUR/BANK_FULL/")
		
		RFCCOR = cwmsFile.get("//CORO/FLOW--INST/01MAR2019/IR-MONTH/RFC-FCST/")
		SIMCORflow = cwmsFile.get("//WILLAMETTE+MARYS/FLOW/01AUG2019/3HOUR/------R0/")
		RFCCORflow = cwmsFile.get("/SANTIAM RIVER/JEFFERSON OR/FLOW/01MAR2019/1HOUR/USGS 14189000/")
		CORflood = cwmsFile.get("/CORFLOODSTAGE//FLOW/01MAR2019/1HOUR/FLOOD_STAGE/")
		CORbank = cwmsFile.get("/CORBANKFULL//FLOW/01MAR2019/1HOUR/BANK_FULL/")		
		
		RFCALBO = cwmsFile.get("//ALBO/FLOW--INST/01AUG2019/IR-MONTH/RFC-FCST/")
		SimALBOflow = cwmsFile.get("//WILLAMETTE_AT ALBANY/FLOW/01AUG2019/3HOUR/------R0/")
		RFCALBOflow = cwmsFile.get("/WILLAMETTE RIVER/ALBANY OR/FLOW/01JUL2019/1HOUR/USGS 14174000/")
		ALBOflood = cwmsFile.get("/ALBOFLOODSTAGE//FLOW/01MAR2019/1HOUR/FLOOD_STAGE/")
		ALBObank = cwmsFile.get("/ALBOBANKFULL//FLOW/01MAR2019/1HOUR/BANK_FULL/")
		
		RFCSLMO = cwmsFile.get("//SLMO/FLOW--INST/01JUL2019/IR-MONTH/RFC-FCST/")
		SimSLMOflow = cwmsFile.get("//WILLAMETTE_AT SALEM/FLOW/01AUG2019/3HOUR/------R0/")
		RFCSLMOflow = cwmsFile.get("/WILLAMETTE RIVER/SALEM OR/FLOW/01JUL2019/1HOUR/USGS 14191000/")
		SLMOflood = cwmsFile.get("/SLMOFLOODSTAGE//FLOW/01MAR2019/1HOUR/FLOOD_STAGE/")
		SLMObank = cwmsFile.get("/SLMOBANKFULL//FLOW/01MAR2019/1HOUR/BANK_FULL/")
		
### Create Plot ####
		MON_Plot = Plot.newPlot("Monroe Project Forecast")
		Layout = Plot.newPlotLayout()
		#TopView = Layout.addViewport(10)
		BottomView = Layout.addViewport(20)
		#TopView.addCurve("Y1", MONbank)
		#TopView.addCurve("Y1", MONflood)
		BottomView.addCurve("Y1", RFCMON)
		BottomView.addCurve("Y1", SimMONflow)
		BottomView.addCurve("Y1", OUTMONflow)
		MON_Plot.configurePlotLayout(Layout)
		MON_Plot.showPlot()
		
		HAR_Plot = Plot.newPlot("Harrisburg Project Forecast")
		Layout = Plot.newPlotLayout()
		#TopView = Layout.addViewport(10)
		BottomView = Layout.addViewport(20)
		BottomView.addCurve("Y1", RFCHAR)
		BottomView.addCurve("Y1", SimHARflow)
		BottomView.addCurve("Y1", RFCHARflow)
		#TopView.addCurve("Y1", HARflood)
		#TopView.addCurve("Y1", HARbank)
		HAR_Plot.configurePlotLayout(Layout)
		HAR_Plot.showPlot()
		
		COR_Plot = Plot.newPlot("Corvallis Project Forecast")
		Layout = Plot.newPlotLayout()
		#TopView = Layout.addViewport(10)
		BottomView = Layout.addViewport(20)
		BottomView.addCurve("Y1", RFCCOR)
		BottomView.addCurve("Y1", SIMCORflow)
		BottomView.addCurve("Y1", RFCCORflow)
		#TopView.addCurve("Y1", CORflood)
		#TopView.addCurve("Y1", CORbank)
		COR_Plot.configurePlotLayout(Layout)
		COR_Plot.showPlot()
		
		ALBO_Plot = Plot.newPlot("Albany Project Forecast")
		Layout = Plot.newPlotLayout()
		#TopView = Layout.addViewport(10)
		BottomView = Layout.addViewport(20)
		BottomView.addCurve("Y1", RFCALBO)
		BottomView.addCurve("Y1", SimALBOflow)
		BottomView.addCurve("Y1", RFCALBOflow)
		#TopView.addCurve("Y1", ALBOflood)
		#TopView.addCurve("Y1", ALBObank)
		ALBO_Plot.configurePlotLayout(Layout)
		ALBO_Plot.showPlot()
		
		SLMO_Plot = Plot.newPlot("Salem Project Forecast")
		Layout = Plot.newPlotLayout()
		#TopView = Layout.addViewport(10)
		BottomView = Layout.addViewport(20)
		BottomView.addCurve("Y1", RFCSLMO)
		BottomView.addCurve("Y1", SimSLMOflow)
		BottomView.addCurve("Y1", RFCSLMOflow)
		#TopView.addCurve("Y1", SLMOflood)
		#TopView.addCurve("Y1", SLMObank)
		SLMO_Plot.configurePlotLayout(Layout)
		SLMO_Plot.showPlot()
		
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
		TopViewport = MON_Plot.getViewport(0)
		BottomViewport = MON_Plot.getViewport(1)
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
		BottomViewport = MON_Plot.getViewport(0)
		BottomViewport = MON_Plot.getViewport(1)
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
		
		TopViewport = HAR_Plot.getViewport(0)
		BottomViewport = HAR_Plot.getViewport(1)
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
		BottomViewport = HAR_Plot.getViewport(0)
		BottomViewport = HAR_Plot.getViewport(1)
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
		
		TopViewport = COR_Plot.getViewport(0)
		BottomViewport = COR_Plot.getViewport(1)
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
		BottomViewport = COR_Plot.getViewport(0)
		BottomViewport = COR_Plot.getViewport(1)
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
		
		TopViewport = ALBO_Plot.getViewport(0)
		BottomViewport = ALBO_Plot.getViewport(1)
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
		BottomViewport = ALBO_Plot.getViewport(0)
		BottomViewport = ALBO_Plot.getViewport(1)
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
		
		TopViewport = SLMO_Plot.getViewport(0)
		BottomViewport = SLMO_Plot.getViewport(1)
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
		BottomViewport = SLMO_Plot.getViewport(0)
		BottomViewport = SLMO_Plot.getViewport(1)
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
		MON_Plot.setSize(1400, 1300)
		MON_Plot.setLocation(100, 100)
		MON_Plot.saveToJpeg("C:\CWMS\Plots\COR\MON_FcstPlot.jpg")
		#MON_Plot.close()
		
		HAR_Plot.setSize(1400, 1300)
		HAR_Plot.setLocation(100, 100)
		HAR_Plot.saveToJpeg("C:\CWMS\Plots\COR\HAR_FcstPlot.jpg")
		#HAR_Plot.close()
		
		COR_Plot.setSize(1400, 1300)
		COR_Plot.setLocation(100, 100)
		COR_Plot.saveToJpeg("C:\CWMS\Plots\COR\COR_FcstPlot.jpg")
		#COR_Plot.close()
		ALBO_Plot.setSize(1400, 1300)
		ALBO_Plot.setLocation(100, 100)
		ALBO_Plot.saveToJpeg("C:\CWMS\Plots\COR\ALBO_FcstPlot.jpg")
		#ALBO_Plot.close()
		
		SLMO_Plot.setSize(1400, 1300)
		SLMO_Plot.setLocation(100, 100)
		SLMO_Plot.saveToJpeg("C:\CWMS\Plots\COR\SLMO_FcstPlot.jpg")
		#SLMO_Plot.close()
		
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
