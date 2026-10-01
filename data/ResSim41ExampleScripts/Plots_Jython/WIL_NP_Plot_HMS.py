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
		OBSFRNElev = cwmsFile.get("/WILLAMETTE/FERN RIDGE/ELEVATION/01FEB2020/1HOUR/OBSERVED/")
		SimFRNElev = cwmsFile.get("//FERN RIDGE/ELEV/01FEB2020/3HOUR/S0--D0M0/")
		SimFRNInflow = cwmsFile.get("//FERN RIDGE-POOL/FLOW-IN/01FEB2020/3HOUR/S0--D0M0/")
		OBSFRNOutflow = cwmsFile.get("/WILLAMETTE/FERN RIDGE/FLOW-OUT/01FEB2020/1HOUR/OBSERVED/")
		OBSFRNInflow = cwmsFile.get("//FRN/Flow-In//15MIN/MIXED-COMPUTED-REV/")
		RFCFRNInflow = cwmsFile.get("//FRN/FLOW-IN--INST/01FEB2020/IR-MONTH/RFC-FCST/")
		SimFRNOutflow = cwmsFile.get("//FERN RIDGE-POOL/FLOW-OUT/01FEB2020/3HOUR/S0--D0M0/")
	
		
		OBSDORElev = cwmsFile.get("/WILLAMETTE/DORENA/ELEVATION/01FEB2020/1HOUR/OBSERVED/")
		SimDORElev = cwmsFile.get("//DORENA-POOL/ELEV/01DEC2018/3HOUR/S0--D0M0/")
		SimDORInflow = cwmsFile.get("//DORENA/FLOW-IN/01FEB2020/3HOUR/S0--D0M0/")
		SimDOROutflow = cwmsFile.get("//DORENA-POOL/FLOW-OUT/01DEC2018/3HOUR/S0--D0M0/")
		OBSDORInflow = cwmsFile.get("/WILLAMETTE/DORENA/FLOW-IN/01FEB2020/IR-MON/OBSERVED/")
		OBSDOROutflow = cwmsFile.get("/WILLAMETTE/DORENA/FLOW-OUT/01FEB2020/1HOUR/OBSERVED/")
		RFCDORInflow = cwmsFile.get("//DOR/FLOW-IN--INST/01FEB2020/IR-MONTH/RFC-FCST/")
		
		OBSCOTElev = cwmsFile.get("/WILLAMETTE/COTTAGE GROVE/ELEVATION//1HOUR/OBSERVED/")
		SimCOTElev = cwmsFile.get("//COTTAGE GROVE-POOL/ELEV//3HOUR/S0--D0M0/")
		SimCOTInflow = cwmsFile.get("//COTTAGE GROVE-POOL/FLOW-IN//3HOUR/S0--D0M0/")
		OBSCOTOutflow = cwmsFile.get("/WILLAMETTE/COTTAGE GROVE/FLOW-OUT//1HOUR/OBSERVED/")
		OBSCOTInflow = cwmsFile.get("//COT/Flow-In//15MIN/MIXED-COMPUTED-REV/")
		SimCOTOutflow = cwmsFile.get("//COTTAGE GROVE-POOL/FLOW-OUT//3HOUR/S0--D0M0/")
		RFCCOTInflow = cwmsFile.get("//COT/FLOW-IN--INST/01FEB2020/IR-MONTH/RFC-FCST/")
		
		OBSCGRElev = cwmsFile.get("/WILLAMETTE/COUGAR/ELEVATION//1HOUR/OBSERVED/")
		SimCGRElev = cwmsFile.get("//COUGAR-POOL/ELEV//3HOUR/S0--D0M0/")
		SimCGRInflow = cwmsFile.get("//COUGAR-POOL/FLOW-IN//3HOUR/S0--D0M0/")
		OBSCGROutflow = cwmsFile.get("/WILLAMETTE/COUGAR/FLOW-OUT//1HOUR/OBSERVED/")
		OBSCGRInflow = cwmsFile.get("//CGR/Flow-In//15MIN/MIXED-COMPUTED-REV/")
		SimCGROutflow = cwmsFile.get("//COUGAR-POOL/FLOW-OUT//3HOUR/S0--D0M0/")
		RFCCGRInflow = cwmsFile.get("//CGR/FLOW-IN--INST/01FEB2020/IR-MONTH/RFC-FCST/")		
		
		OBSBLUElev = cwmsFile.get("/WILLAMETTE/BLUE RIVER/ELEVATION//1HOUR/OBSERVED/")
		SimBLUElev = cwmsFile.get("//BLUE RIVER-POOL/ELEV//3HOUR/S0--D0M0/")
		SimBLUInflow = cwmsFile.get("//BLUE RIVER-POOL/FLOW-IN//3HOUR/S0--D0M0/")
		OBSBLUOutflow = cwmsFile.get("/WILLAMETTE/BLUE RIVER/FLOW-OUT//1HOUR/OBSERVED/")
		OBSBLUInflow = cwmsFile.get("//BLU/Flow-In//15MIN/MIXED-COMPUTED-REV/")
		SimBLUOutflow = cwmsFile.get("//BLUE RIVER-POOL/FLOW-OUT//3HOUR/S0--D0M0/")
		RFCBLUInflow = cwmsFile.get("//BLU/FLOW-IN--INST/01FEB2020/IR-MONTH/RFC-FCST/")		
		
		
		OBSFALElev = cwmsFile.get("/WILLAMETTE/FALL CREEK/ELEVATION//1HOUR/OBSERVED/")
		SimFALElev = cwmsFile.get("//FALL CREEK-POOL/ELEV//3HOUR/S0--D0M0/")
		SimFALInflow = cwmsFile.get("//FALL CREEK-POOL/FLOW-IN//3HOUR/S0--D0M0/")
		OBSFALOutflow = cwmsFile.get("/WILLAMETTE/FALL CREEK/FLOW-OUT//1HOUR/OBSERVED/")
		OBSFALInflow = cwmsFile.get("//FAL/Flow-In//15MIN/MIXED-COMPUTED-REV/")
		SimFALOutflow = cwmsFile.get("//FALL CREEK-POOL/FLOW-OUT//3HOUR/S0--D0M0/")
		#RFCFALInflow = cwmsFile.get("//FAL/FLOW-IN--INST/01FEB2020/IR-MONTH/RFC-FCST/")	.
		
		
### Create Plot ####
		FRN_Plot = Plot.newPlot("FERN RIDGE Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSFRNElev)
		TopView.addCurve("Y1", SimDETElev)
		BottomView.addCurve("Y1", SimFRNInflow)
		BottomView.addCurve("Y1", OBSFRNOutflow)
		BottomView.addCurve("Y1", RFCFRNInflow)
		BottomView.addCurve("Y1", SimFRNOutflow)
		FRN_Plot.configurePlotLayout(Layout)
		FRN_Plot.showPlot()
		
		DOR_Plot = Plot.newPlot("DORENA Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSDORElev)
		TopView.addCurve("Y1", SimDORElev)
		BottomView.addCurve("Y1", SimDORInflow)
		BottomView.addCurve("Y1", OBSDOROutflow)
		BottomView.addCurve("Y1", RFCDORInflow)
		BottomView.addCurve("Y1", SimDOROutflow)
		DOR_Plot.configurePlotLayout(Layout)
		DOR_Plot.showPlot()
		
		COT_Plot = Plot.newPlot("COTTAGE GROVE Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSCOTElev)
		TopView.addCurve("Y1", SimCOTElev)
		BottomView.addCurve("Y1", SimCOTInflow)
		BottomView.addCurve("Y1", OBSCOTOutflow)
		BottomView.addCurve("Y1", RFCCOTInflow)
		BottomView.addCurve("Y1", SimCOTOutflow)
		COT_Plot.configurePlotLayout(Layout)
		COT_Plot.showPlot()
		
		CGR_Plot = Plot.newPlot("COUGAR Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSCGRElev)
		TopView.addCurve("Y1", SimCGRElev)
		BottomView.addCurve("Y1", SimCGRInflow)
		BottomView.addCurve("Y1", OBSCGROutflow)
		BottomView.addCurve("Y1", RFCCGRInflow)
		BottomView.addCurve("Y1", SimCGROutflow)
		CGR_Plot.configurePlotLayout(Layout)
		CGR_Plot.showPlot()
		BLU_Plot = Plot.newPlot("BLUE RIVER Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSBLUElev)
		TopView.addCurve("Y1", SimBLUElev)
		BottomView.addCurve("Y1", SimBLUInflow)
		BottomView.addCurve("Y1", OBSBLUOutflow)
		BottomView.addCurve("Y1", RFCBLUInflow)
		BottomView.addCurve("Y1", SimBLUOutflow)
		BLU_Plot.configurePlotLayout(Layout)
		BLU_Plot.showPlot()
		
		FAL_Plot = Plot.newPlot("FALL CREEK Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSFALElev)
		TopView.addCurve("Y1", SimFALElev)
		BottomView.addCurve("Y1", SimFALInflow)
		BottomView.addCurve("Y1", OBSFALOutflow)
		#BottomView.addCurve("Y1", RFCFALInflow)
		BottomView.addCurve("Y1", SimFALOutflow)
		FAL_Plot.configurePlotLayout(Layout)
		FAL_Plot.showPlot()
		
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
		TopViewport = DET_Plot.getViewport(0)
		BottomViewport = DET_Plot.getViewport(1)
		Top_Y_Axis = TopViewport.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport.getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport.getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(4)
		Top_Y_Axis.setLabel("Pool Elevation")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)
		BottomViewport = DET_Plot.getViewport(0)
		BottomViewport = DET_Plot.getViewport(1)
		Bottom_Y_Axis = BottomViewport.getAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(4)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)
		
		TopViewport = GPR_Plot.getViewport(0)
		BottomViewport = GPR_Plot.getViewport(1)
		Top_Y_Axis = TopViewport.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport.getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport.getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(4)
		Top_Y_Axis.setLabel("Pool Elevation")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)
		BottomViewport = GPR_Plot.getViewport(0)
		BottomViewport = GPR_Plot.getViewport(1)
		Bottom_Y_Axis = BottomViewport.getAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(4)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)
		
		TopViewport = LOP_Plot.getViewport(0)
		BottomViewport = LOP_Plot.getViewport(1)
		Top_Y_Axis = TopViewport.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport.getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport.getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(4)
		Top_Y_Axis.setLabel("Pool Elevation")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)
		BottomViewport = LOP_Plot.getViewport(0)
		BottomViewport = LOP_Plot.getViewport(1)
		Bottom_Y_Axis = BottomViewport.getAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(4)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)
###### Save Plot as A jpeg####
		LOP_Plot.setSize(1400, 1300)
		LOP_Plot.setLocation(100, 100)
		LOP_Plot.saveToJpeg("C:\CWMS\Plots\LOP_FcstPlot.jpg")
		#LOS_Plot.close()
		
		DET_Plot.setSize(1400, 1300)
		DET_Plot.setLocation(100, 100)
		DET_Plot.saveToJpeg("C:\CWMS\Plots\DET_FcstPlot.jpg")
		#APP_Plot.close()
		
		GPR_Plot.setSize(1400, 1300)
		GPR_Plot.setLocation(100, 100)
		GPR_Plot.saveToJpeg("C:\CWMS\Plots\GPR_FcstPlot.jpg")
		#APP_Plot.close()
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
