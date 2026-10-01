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
		
		
		OBSDETElev = cwmsFile.get("/ROGUE/LOS/ELEV-LAKE//1HOUR/NWP-REV/")
		SimDETElev = cwmsFile.get("//LOSTCREEKLK-POOL/ELEV//1HOUR/G0D0R0/")
		SimDETInflow = cwmsFile.get("//LOSTCREEKLK-POOL/FLOW-IN//1HOUR/G0D0R0/")
		OBSDETOutflow = cwmsFile.get("/ROGUE/LOS/FLOW-OUT//1HOUR/NWP-REV/")
		OBSDETInflow = cwmsFile.get("/ROGUE/LOS/FLOW-IN//15MIN/3 HOUR AVERAGE/")
		SimDETOutflow = cwmsFile.get("//LOSTCREEKLK-POOL/FLOW-OUT//1HOUR/G0D0R0/")
		RFCDETInflow = cwmsFile.get("/ROGUE/LOS/FLOW-IN--INST//IR-MONTH/RFC-FCST/")
		
		
		OBSGPRElev = cwmsFile.get("/ROGUE/APP/ELEV-LAKE//1HOUR/NWP-REV/")
		SimGPRElev = cwmsFile.get("//APPLEGATELK-POOL/ELEV//1HOUR/G0D0R0/")
		SimGPRInflow = cwmsFile.get("//APPLEGATELK/FLOW-IN/01SEP2018/1HOUR/G0D0R0/")
		OBSGPROutflow = cwmsFile.get("/ROGUE/APP/FLOW-OUT//1HOUR/NWP-REV/")
		OBSGPRInflow = cwmsFile.get("/ROGUE/APP/FLOW-IN//15MIN/3 HOUR AVERAGE/")
		SimGPROutflow = cwmsFile.get("//APPLEGATELK-POOL/FLOW-OUT//1HOUR/G0D0R0/")
		RFCGPRInflow = cwmsFile.get("/ROGUE/APP/FLOW-IN--INST//IR-MONTH/RFC-FCST/")
		
		OBSLOPElev = cwmsFile.get("/ROGUE/APP/ELEV-LAKE//1HOUR/NWP-REV/")
		SimLOPElev = cwmsFile.get("//APPLEGATELK-POOL/ELEV//1HOUR/G0D0R0/")
		SimLOPInflow = cwmsFile.get("//APPLEGATELK/FLOW-IN/01SEP2018/1HOUR/G0D0R0/")
		OBSLOPOutflow = cwmsFile.get("/ROGUE/APP/FLOW-OUT//1HOUR/NWP-REV/")
		OBSLOPInflow = cwmsFile.get("/ROGUE/APP/FLOW-IN//15MIN/3 HOUR AVERAGE/")
		SimLOPOutflow = cwmsFile.get("//APPLEGATELK-POOL/FLOW-OUT//1HOUR/G0D0R0/")
		RFCLOPInflow = cwmsFile.get("/ROGUE/APP/FLOW-IN--INST//IR-MONTH/RFC-FCST/")		
		
		
### Create Plot ####
		LOS_Plot = Plot.newPlot("Lost Creek Lake Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSLOSElev)
		TopView.addCurve("Y1", SimLOSElev)
		BottomView.addCurve("Y1", SimLOSInflow)
		BottomView.addCurve("Y1", OBSLOSOutflow)
		BottomView.addCurve("Y1", OBSLOSInflow)
		BottomView.addCurve("Y1", SimLOSOutflow)
		BottomView.addCurve("Y1", RFCLOSInflow)
		LOS_Plot.configurePlotLayout(Layout)
		LOS_Plot.showPlot()
		
		APP_Plot = Plot.newPlot("Applegate Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSAPPElev)
		TopView.addCurve("Y1", SimAPPElev)
		BottomView.addCurve("Y1", SimAPPInflow)
		BottomView.addCurve("Y1", OBSAPPOutflow)
		BottomView.addCurve("Y1", OBSAPPInflow)
		BottomView.addCurve("Y1", SimAPPOutflow)
		BottomView.addCurve("Y1", RFCAPPInflow)
		APP_Plot.configurePlotLayout(Layout)
		APP_Plot.showPlot()
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
		TopViewport = LOS_Plot.getViewport(0)
		BottomViewport = LOS_Plot.getViewport(1)
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
		BottomViewport = LOS_Plot.getViewport(0)
		BottomViewport = LOS_Plot.getViewport(1)
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
		
		TopViewport = APP_Plot.getViewport(0)
		BottomViewport = APP_Plot.getViewport(1)
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
		BottomViewport = APP_Plot.getViewport(0)
		BottomViewport = APP_Plot.getViewport(1)
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
		LOP_Plot.saveToJpeg("C:\CWMS\Plots\LOS_FcstPlot.jpg")
		#LOS_Plot.close()
		
		DET_Plot.setSize(1400, 1300)
		DET_Plot.setLocation(100, 100)
		DET_Plot.saveToJpeg("C:\CWMS\Plots\APP_FcstPlot.jpg")
		#APP_Plot.close()
		GPR_Plot.setSize(1400, 1300)
		GPR_Plot.setLocation(100, 100)
		GPR_Plot.saveToJpeg("C:\CWMS\Plots\APP_FcstPlot.jpg")
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
