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
		OBSDETElev = cwmsFile.get("/WILLAMETTE/DETROIT/ELEVATION//1HOUR/OBSERVED/")
		SimDETElev = cwmsFile.get("//DETROIT-POOL/ELEV/01FEB2020/3HOUR/S0--D0M0/")
		SimDETInflow = cwmsFile.get("//DETROIT-POOL/FLOW-IN/01FEB2020/3HOUR/S0--D0M0/")
		OBSDETOutflow = cwmsFile.get("/WILLAMETTE/DETROIT/FLOW-OUT//1HOUR/OBSERVED/")
		OBSDETInflow = cwmsFile.get("/WILLAMETTE/DETROIT/FLOW-IN//IR-MON/OBSERVED/")
		RFCDETInflow = cwmsFile.get("//DET/FLOW-IN--INST/01FEB2020/IR-MONTH/RFC-FCST/")
		SimDETOutflow = cwmsFile.get("//DETROIT-POOL/FLOW-OUT/01FEB2020/3HOUR/S0--D0M0/")
	
		
		OBSGPRElev = cwmsFile.get("/WILLAMETTE/GREEN PETER/ELEVATION/01DEC2018/1HOUR/OBSERVED/")
		SimGPRElev = cwmsFile.get("//GREEN PETER-POOL/ELEV/01DEC2018/3HOUR/S0--D0M0/")
		SimGPRInflow = cwmsFile.get("//GREEN PETER-POOL/FLOW-IN/01DEC2018/3HOUR/S0--D0M0/")
		SimGPROutflow = cwmsFile.get("//GREEN PETER-POOL/FLOW-OUT/01DEC2018/3HOUR/S0--D0M0/")
		OBSGPRInflow = cwmsFile.get("/WILLAMETTE/GREEN PETER/FLOW-IN/01DEC2018/IR-MON/OBSERVED/")
		OBSGPROutflow = cwmsFile.get("/WILLAMETTE/GREEN PETER/FLOW-OUT/01DEC2018/1HOUR/OBSERVED/")
		RFCGPRInflow = cwmsFile.get("//GPR/FLOW-IN--INST/01FEB2020/IR-MONTH/RFC-FCST/")
		
		OBSLOPElev = cwmsFile.get("/WILLAMETTE/LOOKOUT POINT/ELEVATION//1HOUR/OBSERVED/")
		SimLOPElev = cwmsFile.get("//LOOKOUT POINT-POOL/ELEV//3HOUR/S0--D0M0/")
		SimLOPInflow = cwmsFile.get("//LOOKOUT POINT-POOL/FLOW-IN//3HOUR/S0--D0M0/")
		OBSLOPOutflow = cwmsFile.get("/WILLAMETTE/LOOKOUT POINT/FLOW-OUT//1HOUR/OBSERVED/")
		OBSLOPInflow = cwmsFile.get("/WILLAMETTE/LOOKOUT POINT/FLOW-IN//IR-MON/OBSERVED/")
		SimLOPOutflow = cwmsFile.get("//LOOKOUT POINT-POOL/FLOW-OUT//3HOUR/S0--D0M0/")
		RFCLOPInflow = cwmsFile.get("//LOP/FLOW-IN--INST/01FEB2020/IR-MONTH/RFC-FCST/")
		
### Create Plot ####
		DET_Plot = Plot.newPlot("Detroit Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSDETElev)
		TopView.addCurve("Y1", SimDETElev)
		BottomView.addCurve("Y1", SimDETInflow)
		BottomView.addCurve("Y1", OBSDETOutflow)
		BottomView.addCurve("Y1", RFCDETInflow)
		BottomView.addCurve("Y1", SimDETOutflow)
		DET_Plot.configurePlotLayout(Layout)
		DET_Plot.showPlot()
		
		GPR_Plot = Plot.newPlot("Green Peter Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSGPRElev)
		TopView.addCurve("Y1", SimGPRElev)
		BottomView.addCurve("Y1", SimGPRInflow)
		BottomView.addCurve("Y1", OBSGPROutflow)
		BottomView.addCurve("Y1", RFCGPRInflow)
		BottomView.addCurve("Y1", SimGPROutflow)
		GPR_Plot.configurePlotLayout(Layout)
		GPR_Plot.showPlot()
		
		LOP_Plot = Plot.newPlot("Lookout Point Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSLOPElev)
		TopView.addCurve("Y1", SimLOPElev)
		BottomView.addCurve("Y1", SimLOPInflow)
		BottomView.addCurve("Y1", OBSLOPOutflow)
		BottomView.addCurve("Y1", RFCLOPInflow)
		BottomView.addCurve("Y1", SimLOPOutflow)
		LOP_Plot.configurePlotLayout(Layout)
		LOP_Plot.showPlot()
		
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
