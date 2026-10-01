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
		
		
		OBSCGRElev = cwmsFile.get("/WILLAMETTE/COUGAR/ELEVATION//1HOUR/OBSERVED/")
		SimCGRElev = cwmsFile.get("//COUGAR-POOL/ELEV/01DEC2018/3HOUR/------R0/")
		SimCGRInflow = cwmsFile.get("//COUGAR-POOL/FLOW-IN/01DEC2018/3HOUR/------R0/")
		OBSCGROutflow = cwmsFile.get("//COUGAR-POOL/FLOW-OUT/01DEC2018/3HOUR/------R0/")
		#OBSCGRInflow = cwmsFile.get("/WILLAMETTE/COUGAR/FLOW-IN/01DEC2018/IR-MON/OBSERVED/")
		SimCGROutflow = cwmsFile.get("//COUGAR-POOL/FLOW-OUT/01DEC2018/3HOUR/------R0/")
		RFCCGRInflow = cwmsFile.get("//CGR/FLOW-IN--INST/01DEC2018/IR-MONTH/RFC-FCST/")
		CGRRuleCurve = cwmsFile.get("//CGR/ELEV-RULECURVE/01DEC2018/IR-MONTH/CENWP-CALC/")
		
		OBSDEXElev = cwmsFile.get("/WILLAMETTE/DEXTER/ELEVATION/01DEC2018/1HOUR/OBSERVED/")
		OBSDEXOutflow = cwmsFile.get("//DEXTER-POOL/FLOW-OUT/01DEC2018/3HOUR/------R0/")
		OBSDEXInflow = cwmsFile.get("//DEXTER-POOL/FLOW-OUT/01DEC2018/3HOUR/------R0/")
		SimDEXElev = cwmsFile.get("//DEXTER-POOL/ELEV/01DEC2018/3HOUR/------R0/")
		SimDEXInflow = cwmsFile.get("//DEXTER-POOL/FLOW-IN/01DEC2018/3HOUR/------R0/")
		SimDEXOutflow = cwmsFile.get("//DEXTER-POOL/FLOW-OUT/01DEC2018/3HOUR/------R0/")
		DEXRuleCurve = cwmsFile.get("//DEX/ELEV-RULECURVE/01DEC2018/IR-MONTH/CENWP-CALC/")
		
		OBSHCRElev = cwmsFile.get("/WILLAMETTE/HILLS CREEK/ELEVATION/01DEC2018/1HOUR/OBSERVED/")
		SimHCRElev = cwmsFile.get("//HILLS CREEK-POOL/ELEV/01DEC2018/3HOUR/------R0/")
		SimHCRInflow = cwmsFile.get("//HILLS CREEK-POOL/FLOW-IN/01DEC2018/3HOUR/------R0/")
		OBSHCROutflow = cwmsFile.get("/WILLAMETTE/HILLS CREEK/FLOW-OUT/01DEC2018/1HOUR/OBSERVED/")
		OBSHCRInflow = cwmsFile.get("//HILLS CREEK/FLOW-IN/01DEC2018/3HOUR/------R0/")
		SimHCROutflow = cwmsFile.get("//HILLS CREEK-POOL/FLOW-OUT/01DEC2018/3HOUR/------R0/")
		RFCHCRInflow = cwmsFile.get("//HCR/FLOW-IN--INST/01DEC2018/IR-MONTH/RFC-FCST/")		
		HCRRuleCurve = cwmsFile.get("//HCR/ELEV-RULECURVE/01DEC2018/IR-MONTH/CENWP-CALC/")
		
		OBSBCLElev = cwmsFile.get("/WILLAMETTE/BIG CLIFF/ELEVATION/01DEC2018/1HOUR/OBSERVED/")
		SimBCLElev = cwmsFile.get("//BIG CLIFF-POOL/ELEV/01DEC2018/3HOUR/------R0/")
		SimBCLInflow = cwmsFile.get("//BIG CLIFF/FLOW-IN/01DEC2018/3HOUR/------R0/")
		OBSBCLOutflow = cwmsFile.get("/WILLAMETTE/BIG CLIFF/FLOW-OUT/01DEC2018/1HOUR/OBSERVED/")
		OBSBCLInflow = cwmsFile.get("//BIG CLIFF/FLOW-IN/01DEC2018/3HOUR/------R0/")
		SimBCLOutflow = cwmsFile.get("//BIG CLIFF-POOL/FLOW-OUT/01DEC2018/3HOUR/------R0/")
		BCLRuleCurve = cwmsFile.get("//BCL/ELEV-RULECURVE/01DEC2018/IR-MONTH/CENWP-CALC/")			
		
		OBSFOSElev = cwmsFile.get("/WILLAMETTE/FOSTER/ELEVATION/01DEC2018/1HOUR/OBSERVED/")
		SimFOSElev = cwmsFile.get("//FOSTER-POOL/ELEV/01DEC2018/3HOUR/------R0/")
		SimFOSInflow = cwmsFile.get("//FOSTER-POOL/FLOW-IN/01DEC2018/3HOUR/------R0/")
		OBSFOSOutflow = cwmsFile.get("//SSFO/FLOW/01DEC2018/IR-MONTH/MIXED-COMPUTED-REV/")
		OBSFOSInflow = cwmsFile.get("//FOSTER/FLOW-IN/01DEC2018/3HOUR/------R0/")
		SimFOSOutflow = cwmsFile.get("//FOSTER-POOL/FLOW-OUT/01DEC2018/3HOUR/------R0/")
		RFCFOSInflow = cwmsFile.get("//FOS/FLOW-IN--INST/01DEC2018/IR-MONTH/RFC-FCST/")
		FOSRuleCurve = cwmsFile.get("//FOS/ELEV-RULECURVE/01DEC2018/IR-MONTH/CENWP-CALC/")		
		
### Create Plot ####
		CGR_Plot = Plot.newPlot("Cougar Lake Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSCGRElev)
		TopView.addCurve("Y1", SimCGRElev)
		TopView.addCurve("Y1", CGRRuleCurve)
		BottomView.addCurve("Y1", SimCGRInflow)
		BottomView.addCurve("Y1", OBSCGROutflow)
		#BottomView.addCurve("Y1", OBSCGRInflow)
		BottomView.addCurve("Y1", SimCGROutflow)
		BottomView.addCurve("Y1", RFCCGRInflow)
		CGR_Plot.configurePlotLayout(Layout)
		CGR_Plot.showPlot()
		
		DEX_Plot = Plot.newPlot("Dexter Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSDEXElev)
		TopView.addCurve("Y1", SimDEXElev)
		TopView.addCurve("Y1", DEXRuleCurve)
		BottomView.addCurve("Y1", SimDEXInflow)
		BottomView.addCurve("Y1", OBSDEXOutflow)
		BottomView.addCurve("Y1", OBSDEXInflow)
		BottomView.addCurve("Y1", SimDEXOutflow)
		DEX_Plot.configurePlotLayout(Layout)
		DEX_Plot.showPlot()
		
		HCR_Plot = Plot.newPlot("Hills Creek Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSHCRElev)
		TopView.addCurve("Y1", SimHCRElev)
		TopView.addCurve("Y1", HCRRuleCurve)
		BottomView.addCurve("Y1", SimHCRInflow)
		BottomView.addCurve("Y1", OBSHCROutflow)
		BottomView.addCurve("Y1", OBSHCRInflow)
		BottomView.addCurve("Y1", SimHCROutflow)
		BottomView.addCurve("Y1", RFCHCRInflow)
		HCR_Plot.configurePlotLayout(Layout)
		HCR_Plot.showPlot()
		
		BCL_Plot = Plot.newPlot("Big Cliff Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSBCLElev)
		TopView.addCurve("Y1", SimBCLElev)
		TopView.addCurve("Y1", BCLRuleCurve)
		BottomView.addCurve("Y1", SimBCLInflow)
		BottomView.addCurve("Y1", OBSBCLOutflow)
		BottomView.addCurve("Y1", OBSBCLInflow)
		BCL_Plot.configurePlotLayout(Layout)
		BCL_Plot.showPlot()
		
		FOS_Plot = Plot.newPlot("Foster Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSFOSElev)
		TopView.addCurve("Y1", SimFOSElev)
		TopView.addCurve("Y1", FOSRuleCurve)
		BottomView.addCurve("Y1", SimFOSInflow)
		BottomView.addCurve("Y1", OBSFOSOutflow)
		BottomView.addCurve("Y1", OBSFOSInflow)
		BottomView.addCurve("Y1", SimFOSOutflow)
		BottomView.addCurve("Y1", RFCFOSInflow)
		FOS_Plot.configurePlotLayout(Layout)
		FOS_Plot.showPlot()
		
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
		TopViewport = CGR_Plot.getViewport(0)
		BottomViewport = CGR_Plot.getViewport(1)
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
		BottomViewport = CGR_Plot.getViewport(0)
		BottomViewport = CGR_Plot.getViewport(1)
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
		
		TopViewport = DEX_Plot.getViewport(0)
		BottomViewport = DEX_Plot.getViewport(1)
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
		BottomViewport = DEX_Plot.getViewport(0)
		BottomViewport = DEX_Plot.getViewport(1)
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
		
		TopViewport = HCR_Plot.getViewport(0)
		BottomViewport = HCR_Plot.getViewport(1)
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
		BottomViewport = HCR_Plot.getViewport(0)
		BottomViewport = HCR_Plot.getViewport(1)
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
		
		TopViewport = BCL_Plot.getViewport(0)
		BottomViewport = BCL_Plot.getViewport(1)
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
		BottomViewport = BCL_Plot.getViewport(0)
		BottomViewport = BCL_Plot.getViewport(1)
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
		
		TopViewport = FOS_Plot.getViewport(0)
		BottomViewport = FOS_Plot.getViewport(1)
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
		BottomViewport = FOS_Plot.getViewport(0)
		BottomViewport = FOS_Plot.getViewport(1)
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
		HCR_Plot.setSize(1400, 1300)
		HCR_Plot.setLocation(100, 100)
		HCR_Plot.saveToJpeg("C:\CWMS\Plots\HCR_FcstPlot.jpg")
		#LOS_Plot.close()
		
		BCL_Plot.setSize(1400, 1300)
		BCL_Plot.setLocation(100, 100)
		BCL_Plot.saveToJpeg("C:\CWMS\Plots\BCL_FcstPlot.jpg")
		#APP_Plot.close()
		FOS_Plot.setSize(1400, 1300)
		FOS_Plot.setLocation(100, 100)
		FOS_Plot.saveToJpeg("C:\CWMS\Plots\FOS_FcstPlot.jpg")
		#APP_Plot.close()
		CGR_Plot.setSize(1400, 1300)
		CGR_Plot.setLocation(100, 100)
		CGR_Plot.saveToJpeg("C:\CWMS\Plots\CGR_FcstPlot.jpg")		
		
		DEX_Plot.setSize(1400, 1300)
		DEX_Plot.setLocation(100, 100)
		DEX_Plot.saveToJpeg("C:\CWMS\Plots\DEX_FcstPlot.jpg")		
		
		
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
