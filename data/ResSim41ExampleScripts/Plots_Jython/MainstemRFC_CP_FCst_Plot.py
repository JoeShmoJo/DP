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
	
		
		RFCMEHO = cwmsFile.get("//MEHO/FLOW--INST/01AUG2019/IR-MONTH/RFC-FCST/")
		SimMEHOflow = cwmsFile.get("//NO SANTIAM_AT MEHAMA/FLOW/01AUG2019/3HOUR/------R0/")
		OUTMEHOflow = cwmsFile.get("/LITTLE NORTH SANTIAM RIVER/MEHAMA OR/FLOW/01MAR2019/1HOUR/USGS 14182500/")
		MEHOflood = cwmsFile.get("/MEHOFLOODSTAGE//FLOW/01MAR2019/1HOUR/FLOOD_STAGE/")
		MEHObank = cwmsFile.get("/MEHOBANKFULL//FLOW/01MAR2019/1HOUR/BANK_FULL/")
		
		RFCWTL = cwmsFile.get("//WTLO/FLOW--INST/01AUG2019/IR-MONTH/RFC-FCST/")
		SimWTLflow = cwmsFile.get("//SO SANTIAM_AT WATERLOO/FLOW/01AUG2019/3HOUR/------R0/")
		OUTWTLflow = cwmsFile.get("/LITTLE NORTH SANTIAM RIVER/MEHAMA OR/FLOW/01MAR2019/1HOUR/USGS 14182500/")
		WTLflood = cwmsFile.get("/WTLFLOODSTAGE//FLOW/01MAR2019/1HOUR/FLOOD_STAGE/")
		WTLbank = cwmsFile.get("/WTLBANKFULL//FLOW/01MAR2019/1HOUR/BANK_FULL/")
		
		RFCJeff = cwmsFile.get("//JFFO/FLOW--INST/01AUG2019/IR-MONTH/RFC-FCST/")
		SIMJeffflow = cwmsFile.get("//SANTIAM_AT JEFFERSON/FLOW/01JUL2019/3HOUR/------R0/")
		OUTJEFflow = cwmsFile.get("/SANTIAM RIVER/JEFFERSON OR/FLOW/01MAR2019/1HOUR/USGS 14189000/")
		JEFflood = cwmsFile.get("/JEFFLOODSTAGE//FLOW/01MAR2019/1HOUR/FLOOD_STAGE/")
		JEFbank = cwmsFile.get("/JEFBANKFULL//FLOW/01MAR2019/1HOUR/BANK_FULL/")		
		
### Create Plot ####
		MEHO_Plot = Plot.newPlot("Mehama Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(10)
		BottomView = Layout.addViewport(20)
		BottomView.addCurve("Y1", RFCMEHO)
		BottomView.addCurve("Y1", SimMEHOflow)
		BottomView.addCurve("Y1", OUTMEHOflow)
		TopView.addCurve("Y1", MEHObank)
		TopView.addCurve("Y1", MEHOflood)
		MEHO_Plot.configurePlotLayout(Layout)
		MEHO_Plot.showPlot()
		
		WTL_Plot = Plot.newPlot("Waterloo Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(10)
		BottomView = Layout.addViewport(20)
		BottomView.addCurve("Y1", RFCWTL)
		BottomView.addCurve("Y1", SimWTLflow)
		BottomView.addCurve("Y1", OUTWTLflow)
		TopView.addCurve("Y1", WTLflood)
		TopView.addCurve("Y1", WTLbank)
		WTL_Plot.configurePlotLayout(Layout)
		WTL_Plot.showPlot()
		
		JEF_Plot = Plot.newPlot("Jefferson Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(5)
		BottomView = Layout.addViewport(5)
		BottomView.addCurve("Y1", RFCJeff)
		BottomView.addCurve("Y1", SIMJeffflow)
		BottomView.addCurve("Y1", OUTJEFflow)
		TopView.addCurve("Y1", JEFflood)
		TopView.addCurve("Y1", JEFbank)
		JEF_Plot.configurePlotLayout(Layout)
		JEF_Plot.showPlot()
		
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
		TopViewport = MEHO_Plot.getViewport(0)
		BottomViewport = MEHO_Plot.getViewport(1)
		Top_Y_Axis = TopViewport.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport.getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport.getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("FLOW CFS")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)
		BottomViewport = MEHO_Plot.getViewport(0)
		BottomViewport = MEHO_Plot.getViewport(1)
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
		
		TopViewport = WTL_Plot.getViewport(0)
		BottomViewport = WTL_Plot.getViewport(1)
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
		BottomViewport = WTL_Plot.getViewport(0)
		BottomViewport = WTL_Plot.getViewport(1)
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
		
		TopViewport = JEF_Plot.getViewport(0)
		BottomViewport = JEF_Plot.getViewport(1)
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
		BottomViewport = JEF_Plot.getViewport(0)
		BottomViewport = JEF_Plot.getViewport(1)
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
		MEHO_Plot.setSize(1400, 1300)
		MEHO_Plot.setLocation(100, 100)
		MEHO_Plot.saveToJpeg("C:\CWMS\Plots\MEHO_FcstPlot.jpg")
		#MEHO_Plot.close()
		
		WTL_Plot.setSize(1400, 1300)
		WTL_Plot.setLocation(100, 100)
		WTL_Plot.saveToJpeg("C:\CWMS\Plots\WTL_FcstPlot.jpg")
		#WTL_Plot.close()
		
		JEF_Plot.setSize(1400, 1300)
		JEF_Plot.setLocation(100, 100)
		JEF_Plot.saveToJpeg("C:\CWMS\Plots\JEF_FcstPlot.jpg")
		#JEF_Plot.close()
		
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
