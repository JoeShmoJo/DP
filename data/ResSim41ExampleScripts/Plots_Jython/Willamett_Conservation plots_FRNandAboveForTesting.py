from __future__     import with_statement
from decimal                            import Decimal
from hec.data.cwmsRating       import RatingSet
from hec.hecmath                    import TimeSeriesMath
from hec.io                               import TimeSeriesContainer
from hec.heclib.dss                  import HecDss
from hec.heclib.util                  import HecTime
from hec.dataui.tx                    import TsContainerDataSourceList
from hec.dataui.tx.awt             import VerifyDataDlg
from hec.dataTable                  import HecDataTableToExcel
from hec.data.cwmsRating.io  import TableRatingContainer
from hec.dssgui                       import ListSelection
from hec.script                        import MessageBox, Constants, Plot, Tabulate
from java.awt                          import BorderLayout, GridLayout, FlowLayout, Toolkit, GraphicsEnvironment, Rectangle, Color, Font
from java.awt.event                import ActionListener, FocusListener
from java.io                            import FileOutputStream, IOException
from java.lang                        import System
from java.text                        import SimpleDateFormat
from java.util                         import TimeZone
from javax.swing                   import JDialog, JCheckBox, JComboBox, JPanel, JButton, JOptionPane, JScrollPane, BoxLayout, JLabel, JTextField, SwingConstants, ScrollPaneConstants
from javax.swing.border       import EmptyBorder
from rma.services                 import ServiceLookup
from rma.swing                    import DateChooser
from time                             import mktime, localtime
from timeit                           import default_timer
from hec.script             import AxisMarker
#from hec.script             import renameRecords

import DBAPI, datetime, time, calendar, inspect, java, os, sys, traceback, math, shutil, logging, getpass
import javax.swing.JFrame;
import java.lang
from com.rma.client import Browser
from hec.script     import *
import os, string, time
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
	
		

		
		
		
		###GPR BELOW
		GPRLBElev = cwmsFile.get("/WILLAMETTE/GREEN PETER/ELEV(29)/01JAN2023/1HOUR/OBSERVED/")
		OBSGPRElev = cwmsFile.read("//GREEN PETER-POOL/ELEV/01JAN2023/1DAY/------2050/")
		OBSGPRElev.setVersion("50% Flow Forecast")
		SimGPRInflow = cwmsFile.read("//GREEN PETER-POOL/FLOW-IN/01JAN2023/1DAY/------2050/")
		SimGPRInflow.setVersion("50% Flow Forecast")
		SimGPROutflow = cwmsFile.read("//GREEN PETER-POOL/FLOW-OUT/01JAN2023/1DAY/------2050/")
		SimGPROutflow.setVersion("50% Flow Forecast")
		GPRRuleCurve = cwmsFile.read("//GREEN PETER-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/------2050/")
		
		OBS25GPRElev = cwmsFile.read("//GREEN PETER-POOL/ELEV/01JAN2023/1DAY/------20/")
		OBS25GPRElev.setVersion("25% Flow Forecast")
		Sim25GPRInflow = cwmsFile.read("//GREEN PETER-POOL/FLOW-IN/01JAN2023/1DAY/------20/")
		Sim25GPRInflow.setVersion("25% Flow Forecast")
		Sim25GPROutflow = cwmsFile.read("//GREEN PETER-POOL/FLOW-OUT/01JAN2023/1DAY/------20/")
		Sim25GPROutflow.setVersion("25% Flow Forecast")

		
		OBS75GPRElev = cwmsFile.read("//GREEN PETER-POOL/ELEV/01JAN2023/1DAY/------205070/")
		OBS75GPRElev.setVersion("75% Flow Forecast")
		Sim75GPRInflow = cwmsFile.read("//GREEN PETER-POOL/FLOW-IN/01JAN2023/1DAY/------205070/")
		Sim75GPRInflow.setVersion("75% Flow Forecast")
		Sim75GPROutflow = cwmsFile.read("//GREEN PETER-POOL/FLOW-OUT/01JAN2023/1DAY/------205070/")
		Sim75GPROutflow.setVersion("75% Flow Forecast")

		
		GPRRuleCurveN = cwmsFile.get("//GPR/ELEV-RULECURVE/01MAR2023/IR-MONTH/CENWP-CALC/")
		
		OBS25GPRElev = OBS25GPRElev.getData()
		Sim25GPRInflow = Sim25GPRInflow.getData()
		Sim25GPROutflow = Sim25GPROutflow.getData()

		
		OBSGPRElev = OBSGPRElev.getData()
		SimGPRInflow = SimGPRInflow.getData()
		SimGPROutflow = SimGPROutflow.getData()
		GPRRuleCurve = GPRRuleCurve.getData()
	
		OBS75GPRElev = OBS75GPRElev.getData()
		Sim75GPRInflow = Sim75GPRInflow.getData()
		Sim75GPROutflow = Sim75GPROutflow.getData()
		
		#### FOS BELOW
		FOSLBElev = cwmsFile.get("/WILLAMETTE/FOSTER/ELEV(29)/01MAR2023/1HOUR/OBSERVED/")
		OBSFOSElev = cwmsFile.read("//FOSTER-POOL/ELEV/01JAN2023/1DAY/------2050/")
		OBSFOSElev.setVersion("50% Flow Forecast")
		SimFOSInflow = cwmsFile.read("//FOSTER-POOL/FLOW-IN/01JAN2023/1DAY/------2050/")
		SimFOSInflow.setVersion("50% Flow Forecast")
		SimFOSOutflow = cwmsFile.read("//FOSTER-POOL/FLOW-OUT/01JAN2023/1DAY/------2050/")
		SimFOSOutflow.setVersion("50% Flow Forecast")
		FOSRuleCurve = cwmsFile.read("//FOSTER-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/------2050/")

		
		OBS25FOSElev = cwmsFile.read("//FOSTER-POOL/ELEV/01JAN2023/1DAY/------20/")
		OBS25FOSElev.setVersion("25% Flow Forecast")
		Sim25FOSInflow = cwmsFile.read("//FOSTER-POOL/FLOW-IN/01JAN2023/1DAY/------20/")
		Sim25FOSInflow.setVersion("25% Flow Forecast")
		Sim25FOSOutflow = cwmsFile.read("//FOSTER-POOL/FLOW-OUT/01JAN2023/1DAY/------20/")
		Sim25FOSOutflow.setVersion("25% Flow Forecast")
		
		FOSRuleCurveN = cwmsFile.get("//FOS/ELEV-RULECURVE/01MAY2023/IR-MONTH/CENWP-CALC/")
		
		OBS75FOSElev = cwmsFile.read("//FOSTER-POOL/ELEV/01JAN2023/1DAY/------205070/")
		OBS75FOSElev.setVersion("75% Flow Forecast")
		Sim75FOSInflow = cwmsFile.read("//FOSTER-POOL/FLOW-IN/01JAN2023/1DAY/------205070/")
		Sim75FOSInflow.setVersion("75% Flow Forecast")
		Sim75FOSOutflow = cwmsFile.read("//FOSTER-POOL/FLOW-OUT/01JAN2023/1DAY/------205070/")
		Sim75FOSOutflow.setVersion("75% Flow Forecast")
	
		
		FOSRuleCurveN = cwmsFile.get("//FOS/ELEV-RULECURVE/01MAY2023/IR-MONTH/CENWP-CALC/")

		OBS25FOSElev = OBS25FOSElev.getData()
		Sim25FOSInflow = Sim25FOSInflow.getData()
		Sim25FOSOutflow = Sim25FOSOutflow.getData()

		
		OBSFOSElev = OBSFOSElev.getData()
		SimFOSInflow = SimFOSInflow.getData()
		SimFOSOutflow = SimFOSOutflow.getData()
		FOSRuleCurve = FOSRuleCurve.getData()
	
		OBS75FOSElev = OBS75FOSElev.getData()
		Sim75FOSInflow = Sim75FOSInflow.getData()
		Sim75FOSOutflow = Sim75FOSOutflow.getData()
		
		#//BIG CLIFF-POOL/FLOW-OUT/01JAN2023/1DAY/20C0/
		
		####DET Below
		DETLBElev = cwmsFile.get("/WILLAMETTE/DETROIT/ELEV(29)/01APR2023/1HOUR/OBSERVED/")
		OBS25DETElev = cwmsFile.read("//DETROIT-POOL/ELEV/01JAN2023/1DAY/------20/")
		OBS25DETElev.setVersion("25% Flow Forecast")
		Sim25DETInflow = cwmsFile.read("//DETROIT-POOL/FLOW-IN/01JAN2023/1DAY/------20/")
		Sim25DETInflow.setVersion("25% Flow Forecast")
		Sim25DETOutflow = cwmsFile.read("//DETROIT-POOL/FLOW-OUT/01JAN2023/1DAY/------20/")
		Sim25DETOutflow.setVersion("25% Flow Forecast")
		DETRuleCurve = cwmsFile.read("//DETROIT-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/------20/")
		DETRuleCurve.setVersion("25% Flow Forecast")
		DETRuleCurveN = cwmsFile.get("//DET/ELEV-RULECURVE/01MAY2023/IR-MONTH/CENWP-CALC/")
		
		OBSDETElev = cwmsFile.read("//DETROIT-POOL/ELEV/01JAN2023/1DAY/------2050/")
		OBSDETElev = cwmsFile.read("//DETROIT-POOL/ELEV/01JAN2023/1DAY/------20/")
		OBSDETElev.setVersion("50% Flow Forecast")
		SimDETInflow = cwmsFile.read("//DETROIT-POOL/FLOW-IN/01JAN2023/1DAY/------2050/")
		SimDETInflow.setVersion("50% Flow Forecast")
		SimDETOutflow = cwmsFile.read("//BIG CLIFF-POOL/FLOW-OUT/01JAN2023/1DAY/------2050/")
		SimDETOutflow.setVersion("50% Flow Forecast")

		
		OBS75DETElev = cwmsFile.read("//DETROIT-POOL/ELEV/01JAN2023/1DAY/------205070/")
		OBS75DETElev.setVersion("75% Flow Forecast")
		Sim75DETInflow = cwmsFile.read("//DETROIT-POOL/FLOW-IN/01JAN2023/1DAY/------205070/")
		Sim75DETInflow.setVersion("75% Flow Forecast")
		Sim75DETOutflow = cwmsFile.read("//DETROIT-POOL/FLOW-OUT/01JAN2023/1DAY/------205070/")
		Sim75DETOutflow.setVersion("75% Flow Forecast")

		OBS25DETElev = OBS25DETElev.getData()
		Sim25DETInflow = Sim25DETInflow.getData()
		Sim25DETOutflow = Sim25DETOutflow.getData()

		
		OBSDETElev = OBSDETElev.getData()
		SimDETInflow = SimDETInflow.getData()
		SimDETOutflow = SimDETOutflow.getData()
		DETRuleCurve = DETRuleCurve.getData()
	
		OBS75DETElev = OBS75DETElev.getData()
		Sim75DETInflow = Sim75DETInflow.getData()
		Sim75DETOutflow = Sim75DETOutflow.getData()				

		##########CGR Below 
				
		CGRLBElev = cwmsFile.get("/WILLAMETTE/COUGAR/ELEV(29)/01FEB2023/1HOUR/OBSERVED/")
		OBS25CGRElev = cwmsFile.read("//COUGAR-POOL/ELEV/01JAN2023/1DAY/------20/")
		Sim25CGRInflow = cwmsFile.read("//COUGAR-POOL/FLOW-IN/01JAN2023/1DAY/------20/")
		Sim25CGROutflow = cwmsFile.read("//COUGAR-POOL/FLOW-OUT/01JAN2023/1DAY/------20/")
		CGRRuleCurve = cwmsFile.read("//COUGAR-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/------20/")


		OBSCGRElev = cwmsFile.read("//COUGAR-POOL/ELEV/01JAN2023/1DAY/------2050/")
		SimCGRInflow = cwmsFile.read("//COUGAR-POOL/FLOW-IN/01JAN2023/1DAY/------2050/")
		SimCGROutflow = cwmsFile.read("//COUGAR-POOL/FLOW-OUT/01JAN2023/1DAY/------2050/")
		CGRRuleCurve = cwmsFile.read("//COUGAR-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/------2050/")
		CGRRuleCurveN = cwmsFile.read("//CGR/ELEV-RULECURVE/01NOV2023/IR-MONTH/CENWP-CALC/")
		
		OBS75CGRElev = cwmsFile.read("//COUGAR-POOL/ELEV/01JAN2023/1DAY/------205070/")
		OBS75CGRElev.setVersion("75% Flow Forecast")
		Sim75CGRInflow = cwmsFile.read("//COUGAR-POOL/FLOW-IN/01JAN2023/1DAY/------205070/")
		Sim75CGRInflow.setVersion("75% Flow Forecast")
		Sim75CGROutflow = cwmsFile.read("//COUGAR-POOL/FLOW-OUT/01JAN2023/1DAY/------205070/")
		Sim75CGROutflow.setVersion("75% Flow Forecast")
		CGR75RuleCurve = cwmsFile.read("//COUGAR-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/------205070/")
		CGR75RuleCurve.setVersion("75% Flow Forecast")

		OBS25CGRElev = OBS25CGRElev.getData()
		Sim25CGRInflow = Sim25CGRInflow.getData()

		
		OBSCGRElev = OBSCGRElev.getData()
		SimCGRInflow = SimCGRInflow.getData()
		SimCGROutflow = SimCGROutflow.getData()
		CGRRuleCurve = CGRRuleCurve.getData()
	
		OBS75CGRElev = OBS75CGRElev.getData()
		Sim75CGRInflow = Sim75CGRInflow.getData()
		Sim75CGROutflow = Sim75CGROutflow.getData()
		
		##### FRN Below
		
		FRNLBElev = cwmsFile.get("/WILLAMETTE/FERN RIDGE/ELEV(29)/01APR2023/1HOUR/OBSERVED/")
		OBS25FRNElev = cwmsFile.read("//FERN RIDGE-POOL/ELEV/01JAN2023/1DAY/------20/")
		OBS25FRNElev.setVersion("25% Flow Forecast")
		Sim25FRNInflow = cwmsFile.read("//FERN RIDGE-POOL/FLOW-IN/01JAN2023/1DAY/------20/")
		Sim25FRNInflow.setVersion("25% Flow Forecast")
		Sim25FRNOutflow = cwmsFile.read("//FERN RIDGE-POOL/FLOW-OUT/01JAN2023/1DAY/------20/")
		Sim25FRNOutflow.setVersion("25% Flow Forecast")

		

		
		OBSFRNElev = cwmsFile.read("//FERN RIDGE-POOL/ELEV/01JAN2023/1DAY/------2050/")
		OBSFRNElev.setVersion("50% Flow Forecast")
		SimFRNInflow = cwmsFile.read("//FERN RIDGE-POOL/FLOW-IN/01JAN2023/1DAY/------2050/")
		SimFRNInflow.setVersion("50% Flow Forecast")
		SimFRNOutflow = cwmsFile.read("//FERN RIDGE-POOL/FLOW-OUT/01JAN2023/1DAY/------2050/")
		SimFRNOutflow.setVersion("50% Flow Forecast")
		FRNRuleCurve = cwmsFile.read("//FERN RIDGE-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/------2050/")
		FRNRuleCurve.setVersion("50% Flow Forecast")
		FRNRuleCurveN = cwmsFile.get("//FRN/ELEV-RULECURVE/01JUN2023/IR-MONTH/CENWP-CALC/")
		
		OBS75FRNElev = cwmsFile.read("//FERN RIDGE-POOL/ELEV/01JAN2023/1DAY/------205070/")
		OBS75FRNElev.setVersion("75% Flow Forecast")
		Sim75FRNInflow = cwmsFile.read("//FERN RIDGE-POOL/FLOW-IN/01JAN2023/1DAY/------205070/")
		Sim75FRNInflow.setVersion("75% Flow Forecast")
		Sim75FRNOutflow = cwmsFile.read("//FERN RIDGE-POOL/FLOW-OUT/01JAN2023/1DAY/------2050/")
		Sim75FRNOutflow.setVersion("75% Flow Forecast")

		OBS25FRNElev = OBS25FRNElev.getData()
		Sim25FRNInflow = Sim25FRNInflow.getData()
		Sim25FRNOutflow = Sim25FRNOutflow.getData()

		
		OBSFRNElev = OBSFRNElev.getData()
		SimFRNInflow = SimFRNInflow.getData()
		SimFRNOutflow = SimFRNOutflow.getData()
		FRNRuleCurve = FRNRuleCurve.getData()
	
		OBS75FRNElev = OBS75FRNElev.getData()
		Sim75FRNInflow = Sim75FRNInflow.getData()
		Sim75FRNOutflow = Sim75FRNOutflow.getData()
		
		

		
		

				
				


		

        
### Create Plot ####

        


		DET_Plot = Plot.newPlot("Detroit Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSDETElev)
		TopView.addCurve("Y1", OBS25DETElev)
		TopView.addCurve("Y1", OBS75DETElev)
		TopView.addCurve("Y1", DETRuleCurve)
		TopView.addCurve("Y1", DETRuleCurveN)
		#TopView.addCurve("Y1", DETSW)
		#TopView.addCurve("Y1", SouthShoreBR)
		#TopView.addCurve("Y1", StateParkDBR)
		#TopView.addCurve("Y1", MongoldBR)
		#TopView.addCurve("Y1", KanesMarinaBR)
		TopView.addCurve("Y1", DETLBElev)
		
		BottomView.addCurve("Y1", SimDETInflow)
		#BottomView.addCurve("Y1", Sim25DETInflow)
		#BottomView.addCurve("Y1", Sim75DETInflow)
		BottomView.addCurve("Y1", SimDETOutflow)
		#BottomView.addCurve("Y1", Sim25DETOutflow)
		#BottomView.addCurve("Y1", Sim75DETOutflow)
		DET_Plot.configurePlotLayout(Layout)
		DET_Plot.showPlot()
		
		
		
		GPR_Plot = Plot.newPlot("Green Peter Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSGPRElev)
		TopView.addCurve("Y1", OBS25GPRElev)
		TopView.addCurve("Y1", OBS75GPRElev)
		TopView.addCurve("Y1", GPRRuleCurve)
		TopView.addCurve("Y1", GPRRuleCurveN)
		#TopView.addCurve("Y1", GPRSW)
		#TopView.addCurve("Y1", ThistleCreekBR)
		#TopView.addCurve("Y1", WHITCOMB)
		TopView.addCurve("Y1", GPRLBElev)
		
		BottomView.addCurve("Y1", SimGPRInflow)
		#BottomView.addCurve("Y1", Sim25GPRInflow)
		#BottomView.addCurve("Y1", Sim75GPRInflow)
		BottomView.addCurve("Y1", SimGPROutflow)
		#BottomView.addCurve("Y1", Sim25GPROutflow)
		#BottomView.addCurve("Y1", Sim75GPROutflow)
		GPR_Plot.configurePlotLayout(Layout)
		GPR_Plot.showPlot()
		
		
		
		FOS_Plot = Plot.newPlot("Foster Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSFOSElev)
		TopView.addCurve("Y1", OBS25FOSElev)
		TopView.addCurve("Y1", OBS75FOSElev)
		TopView.addCurve("Y1", FOSRuleCurve)
		TopView.addCurve("Y1", FOSRuleCurveN)
		TopView.addCurve("Y1", FOSLBElev)
		
		BottomView.addCurve("Y1", SimFOSInflow)
		BottomView.addCurve("Y1", SimFOSOutflow)
		FOS_Plot.configurePlotLayout(Layout)
		FOS_Plot.showPlot()
		
		
		
		FRN_Plot = Plot.newPlot("Fern Ridge Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSFRNElev)
		TopView.addCurve("Y1", OBS25FRNElev)
		TopView.addCurve("Y1", OBS75FRNElev)
		TopView.addCurve("Y1", FRNRuleCurve)
		TopView.addCurve("Y1", FRNRuleCurveN)

		TopView.addCurve("Y1", FRNLBElev)
		
		BottomView.addCurve("Y1", SimFRNInflow)

		BottomView.addCurve("Y1", SimFRNOutflow)

		FRN_Plot.configurePlotLayout(Layout)
		FRN_Plot.showPlot()
		
		
		

		

		

		
		




				
####### Plot Line Styles####

		####GPR Below
		
		OBSGPRElevCurve_25 = GPR_Plot.getCurve(OBS25GPRElev)
		OBSGPRElevCurve_25.setLineWidth(6)
		OBSGPRElevCurve_25 = GPR_Plot.getCurve(OBS25GPRElev)
		OBSGPRElevCurve_25.setLineColor("yellow")
		OBSGPRElevCurve_25.setLineStyle("solid")
		OBSGPRElevCurve_25.setLineWidth(3)
		
		OBSGPRElevCurve_50 = GPR_Plot.getCurve(OBSGPRElev)
		OBSGPRElevCurve_50.setLineWidth(6)
		OBSGPRElevCurve_50 = GPR_Plot.getCurve(OBSGPRElev)
		OBSGPRElevCurve_50.setLineColor("green")
		OBSGPRElevCurve_50.setLineStyle("solid")
		OBSGPRElevCurve_50.setLineWidth(3)

		OBSGPRElevCurve_75 = GPR_Plot.getCurve(OBS75GPRElev)
		OBSGPRElevCurve_75.setLineWidth(3)
		OBSGPRElevCurve_75 = GPR_Plot.getCurve(OBS75GPRElev)
		OBSGPRElevCurve_75.setLineColor("cyan")
		OBSGPRElevCurve_75.setLineStyle("Solid")
		OBSGPRElevCurve_75.setLineWidth(3)
		
		GPRRuleCurveNormal = GPR_Plot.getCurve(GPRRuleCurveN)
		GPRRuleCurveNormal.setLineWidth(3)
		GPRRuleCurveNormal = GPR_Plot.getCurve(GPRRuleCurveN)
		GPRRuleCurveNormal.setLineColor("black")
		GPRRuleCurveNormal.setLineStyle("Solid")
		GPRRuleCurveNormal.setLineWidth(3)
		

		OBSGPROUTFLOWCurve_50 = GPR_Plot.getCurve(SimGPROutflow)
		OBSGPROUTFLOWCurve_50.setLineWidth(3)
		OBSGPROUTFLOWCurve_50 = GPR_Plot.getCurve(SimGPROutflow)
		OBSGPROUTFLOWCurve_50.setLineColor("darkgreen")
		OBSGPROUTFLOWCurve_50.setLineStyle("dash")
		OBSGPROUTFLOWCurve_50.setLineWidth(3)
		
		

		GPRRuleCurveEIS = GPR_Plot.getCurve(GPRRuleCurve)
		GPRRuleCurveEIS.setLineWidth(6)
		GPRRuleCurveEIS = GPR_Plot.getCurve(GPRRuleCurve)
		GPRRuleCurveEIS.setLineColor("black")
		GPRRuleCurveEIS.setLineStyle("dash")
		GPRRuleCurveEIS.setLineWidth(3)
		
		
		OBSGPRINFLOWCurve_50 = GPR_Plot.getCurve(SimGPRInflow)
		OBSGPRINFLOWCurve_50.setLineWidth(3)
		OBSGPRINFLOWCurve_50 = GPR_Plot.getCurve(SimGPRInflow)
		OBSGPRINFLOWCurve_50.setLineColor("green")
		OBSGPRINFLOWCurve_50.setLineStyle("solid")
		OBSGPRINFLOWCurve_50.setLineWidth(3)     
		
	
		GPRLBElev2 = GPR_Plot.getCurve(GPRLBElev)
		GPRLBElev2.setLineWidth(5)
		GPRLBElev2 = GPR_Plot.getCurve(GPRLBElev)
		GPRLBElev2.setLineColor("darkmagenta")
		GPRLBElev2.setLineStyle("Solid")
		
		
		###FOS Below
		
		OBSFOSElevCurve_25 = FOS_Plot.getCurve(OBS25FOSElev)
		OBSFOSElevCurve_25.setLineWidth(3)
		OBSFOSElevCurve_25 = FOS_Plot.getCurve(OBS25FOSElev)
		OBSFOSElevCurve_25.setLineColor("yellow")
		OBSFOSElevCurve_25.setLineStyle("solid")
		OBSFOSElevCurve_25.setLineWidth(3)

		OBSFOSElevCurve_50 = FOS_Plot.getCurve(OBSFOSElev)
		OBSFOSElevCurve_50.setLineWidth(6)
		OBSFOSElevCurve_50 = FOS_Plot.getCurve(OBSFOSElev)
		OBSFOSElevCurve_50.setLineColor("green")
		OBSFOSElevCurve_50.setLineStyle("solid")
		OBSFOSElevCurve_50.setLineWidth(5)

		OBSFOSElevCurve_75 = FOS_Plot.getCurve(OBS75FOSElev)
		OBSFOSElevCurve_75.setLineWidth(3)
		OBSFOSElevCurve_75 = FOS_Plot.getCurve(OBS75FOSElev)
		OBSFOSElevCurve_75.setLineColor("cyan")
		OBSFOSElevCurve_75.setLineStyle("Solid")
		OBSFOSElevCurve_75.setLineWidth(3)
		
		FOSRuleCurveNormal = FOS_Plot.getCurve(FOSRuleCurveN)
		FOSRuleCurveNormal.setLineWidth(3)
		FOSRuleCurveNormal = FOS_Plot.getCurve(FOSRuleCurveN)
		FOSRuleCurveNormal.setLineColor("black")
		FOSRuleCurveNormal.setLineStyle("Solid")
		FOSRuleCurveNormal.setLineWidth(3)
		

		OBSFOSOUTFLOWCurve_50 = FOS_Plot.getCurve(SimFOSOutflow)
		OBSFOSOUTFLOWCurve_50.setLineWidth(5)
		OBSFOSOUTFLOWCurve_50 = FOS_Plot.getCurve(SimFOSOutflow)
		OBSFOSOUTFLOWCurve_50.setLineColor("darkgreen")
		OBSFOSOUTFLOWCurve_50.setLineStyle("dash")
		OBSFOSOUTFLOWCurve_50.setLineWidth(5)

		
		FOSRuleCurveEIS = FOS_Plot.getCurve(FOSRuleCurve)
		FOSRuleCurveEIS.setLineWidth(6)
		FOSRuleCurveEIS = FOS_Plot.getCurve(FOSRuleCurve)
		FOSRuleCurveEIS.setLineColor("black")
		FOSRuleCurveEIS.setLineStyle("dash")
		FOSRuleCurveEIS.setLineWidth(3)
		

		OBSFOSINFLOWCurve_50 = FOS_Plot.getCurve(SimFOSInflow)
		OBSFOSINFLOWCurve_50.setLineWidth(3)
		OBSFOSINFLOWCurve_50 = FOS_Plot.getCurve(SimFOSInflow)
		OBSFOSINFLOWCurve_50.setLineColor("green")
		OBSFOSINFLOWCurve_50.setLineStyle("solid")
		OBSFOSINFLOWCurve_50.setLineWidth(3)
		
		
		FOSLBElev2 = FOS_Plot.getCurve(FOSLBElev)
		FOSLBElev2.setLineWidth(5)
		FOSLBElev2 = FOS_Plot.getCurve(FOSLBElev)
		FOSLBElev2.setLineColor("darkmagenta")
		FOSLBElev2.setLineStyle("solid")
		FOSLBElev2.setLineWidth(5)
		
		
				############### DET below
		
		OBSDETElevCurve_25 = DET_Plot.getCurve(OBS25DETElev)
		OBSDETElevCurve_25.setLineWidth(6)
		OBSDETElevCurve_25 = DET_Plot.getCurve(OBS25DETElev)
		OBSDETElevCurve_25.setLineColor("yellow")
		OBSDETElevCurve_25.setLineStyle("solid")
		OBSDETElevCurve_25.setLineWidth(3)

		OBSDETElevCurve_50 = DET_Plot.getCurve(OBSDETElev)
		OBSDETElevCurve_50.setLineWidth(6)
		OBSDETElevCurve_50 = DET_Plot.getCurve(OBSDETElev)
		OBSDETElevCurve_50.setLineColor("green")
		OBSDETElevCurve_50.setLineStyle("solid")
		OBSDETElevCurve_50.setLineWidth(3)

		OBSDETElevCurve_75 = DET_Plot.getCurve(OBS75DETElev)
		OBSDETElevCurve_75.setLineWidth(3)
		OBSDETElevCurve_75 = DET_Plot.getCurve(OBS75DETElev)
		OBSDETElevCurve_75.setLineColor("cyan")
		OBSDETElevCurve_75.setLineStyle("Solid")
		OBSDETElevCurve_75.setLineWidth(3)
		
		DETRuleCurveNormal = DET_Plot.getCurve(DETRuleCurveN)
		DETRuleCurveNormal.setLineWidth(3)
		DETRuleCurveNormal = DET_Plot.getCurve(DETRuleCurveN)
		DETRuleCurveNormal.setLineColor("black")
		DETRuleCurveNormal.setLineStyle("Solid")
		DETRuleCurveNormal.setLineWidth(3)
		
		OBSDETOUTFLOWCurve_50 = DET_Plot.getCurve(SimDETOutflow)
		OBSDETOUTFLOWCurve_50.setLineWidth(3)
		OBSDETOUTFLOWCurve_50 = DET_Plot.getCurve(SimDETOutflow)
		OBSDETOUTFLOWCurve_50.setLineColor("darkgreen")
		OBSDETOUTFLOWCurve_50.setLineStyle("dash")
		OBSDETOUTFLOWCurve_50.setLineWidth(3)

		
		DETRuleCurveEIS = DET_Plot.getCurve(DETRuleCurve)
		DETRuleCurveEIS.setLineWidth(3)
		DETRuleCurveEIS = DET_Plot.getCurve(DETRuleCurve)
		DETRuleCurveEIS.setLineColor("black")
		DETRuleCurveEIS.setLineStyle("dash")
		
		OBSDETINFLOWCurve_50 = DET_Plot.getCurve(SimDETInflow)
		OBSDETINFLOWCurve_50.setLineWidth(3)
		OBSDETINFLOWCurve_50 = DET_Plot.getCurve(SimDETInflow)
		OBSDETINFLOWCurve_50.setLineColor("green")
		OBSDETINFLOWCurve_50.setLineStyle("solid")
		

		DETLBElev2 = DET_Plot.getCurve(DETLBElev)
		DETLBElev2.setLineWidth(5)
		DETLBElev2.setLineColor("darkmagenta")
		DETLBElev2.setLineStyle("solid")

		


		############### FRN below
		
		OBSFRNElevCurve_25 = FRN_Plot.getCurve(OBS25FRNElev)
		OBSFRNElevCurve_25.setLineWidth(6)
		OBSFRNElevCurve_25 = FRN_Plot.getCurve(OBS25FRNElev)
		OBSFRNElevCurve_25.setLineColor("yellow")
		OBSFRNElevCurve_25.setLineStyle("solid")
		OBSFRNElevCurve_25.setLineWidth(3)

		OBSFRNElevCurve_50 = FRN_Plot.getCurve(OBSFRNElev)
		OBSFRNElevCurve_50.setLineWidth(6)
		OBSFRNElevCurve_50 = FRN_Plot.getCurve(OBSFRNElev)
		OBSFRNElevCurve_50.setLineColor("green")
		OBSFRNElevCurve_50.setLineStyle("solid")
		OBSFRNElevCurve_50.setLineWidth(3)

		OBSFRNElevCurve_75 = FRN_Plot.getCurve(OBS75FRNElev)
		OBSFRNElevCurve_75.setLineWidth(3)
		OBSFRNElevCurve_75 = FRN_Plot.getCurve(OBS75FRNElev)
		OBSFRNElevCurve_75.setLineColor("cyan")
		OBSFRNElevCurve_75.setLineStyle("Solid")
		OBSFRNElevCurve_75.setLineWidth(3)
		
		FRNRuleCurveNormal = FRN_Plot.getCurve(FRNRuleCurveN)
		FRNRuleCurveNormal.setLineWidth(3)
		FRNRuleCurveNormal = FRN_Plot.getCurve(FRNRuleCurveN)
		FRNRuleCurveNormal.setLineColor("black")
		FRNRuleCurveNormal.setLineStyle("Solid")
		FRNRuleCurveNormal.setLineWidth(3)


		OBSFRNOUTFLOWCurve_50 = FRN_Plot.getCurve(SimFRNOutflow)
		OBSFRNOUTFLOWCurve_50.setLineWidth(3)
		OBSFRNOUTFLOWCurve_50 = FRN_Plot.getCurve(SimFRNOutflow)
		OBSFRNOUTFLOWCurve_50.setLineColor("darkgreen")
		OBSFRNOUTFLOWCurve_50.setLineStyle("dash")
		OBSFRNOUTFLOWCurve_50.setLineWidth(3)


		FRNRuleCurveEIS = FRN_Plot.getCurve(FRNRuleCurve)
		FRNRuleCurveEIS.setLineWidth(6)
		FRNRuleCurveEIS = FRN_Plot.getCurve(FRNRuleCurve)
		FRNRuleCurveEIS.setLineColor("black")
		FRNRuleCurveEIS.setLineStyle("dash")
		FRNRuleCurveEIS.setLineWidth(3)
		
		OBSFRNINFLOWCurve_50 = FRN_Plot.getCurve(SimFRNInflow)
		OBSFRNINFLOWCurve_50.setLineWidth(3)
		OBSFRNINFLOWCurve_50 = FRN_Plot.getCurve(SimFRNInflow)
		OBSFRNINFLOWCurve_50.setLineColor("green")
		OBSFRNINFLOWCurve_50.setLineStyle("dash")
		OBSFRNINFLOWCurve_50.setLineWidth(3)
		
		
		FRNLBElev2 = FRN_Plot.getCurve(FRNLBElev)
		FRNLBElev2.setLineWidth(5)
		FRNLBElev2 = FRN_Plot.getCurve(FRNLBElev)
		FRNLBElev2.setLineColor("darkmagenta")
		FRNLBElev2.setLineStyle("solid")
		FRNLBElev2.setLineWidth(5)
		
        
#####Axis Formating####

        
        
		TopViewport_DET = DET_Plot.getViewport(0)
		BottomViewport_DET = DET_Plot.getViewport(1)
		Top_Y_Axis = TopViewport_DET.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport_DET.getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_DET.getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("Pool Elevation")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)
		Bottom_Y_Axis = BottomViewport_DET.getAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport_DET.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_DET.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)
		
		DETSW = AxisMarker()
		DETSW.axis = "Y"
		DETSW.value = "1541"
		DETSW.labelText = "DET Spillway ~ 1541"
		DETSW.labelPosition = "below"
		DETSW.labelColor = "purple"
		DETSW.labelFont = "Dialog,BOLD,14";
		DETSW.lineColor = "purple"
		DETSW.lineStyle = "dot"
		DETSW.lineWidth = 4
		TopViewport_DET.addAxisMarker(DETSW)        
        
        
        
		StateParkD_BR = AxisMarker()
		StateParkD_BR.axis = "Y"
		StateParkD_BR.value = "1556"
		StateParkD_BR.labelText = "State Park D BR ~ 1556"
		StateParkD_BR.labelPosition = "above"
		StateParkD_BR.labelColor = "black"
		StateParkD_BR.labelFont = "Dialog,BOLD,14";
		StateParkD_BR.lineColor = "black"
		StateParkD_BR.lineStyle = "dot"
		StateParkD_BR.lineWidth = 4
		TopViewport_DET.addAxisMarker(StateParkD_BR)        
        
        
		KanesMarina_BR = AxisMarker()
		KanesMarina_BR.axis = "Y"
		KanesMarina_BR.value = "1546"
		KanesMarina_BR.labelText = "Kanes Marina BR ~ 1546"
		KanesMarina_BR.labelPosition = "above"
		KanesMarina_BR.labelColor = "black"
		KanesMarina_BR.labelFont = "Dialog,BOLD,14";
		KanesMarina_BR.lineColor = "black"
		KanesMarina_BR.lineStyle = "dot"
		KanesMarina_BR.lineWidth = 4
		TopViewport_DET.addAxisMarker(KanesMarina_BR)        
        
		Hoover_BR = AxisMarker()
		Hoover_BR.axis = "Y"
		Hoover_BR.value = "1543"
		Hoover_BR.labelText = "."
		Hoover_BR.labelPosition = "center"
		Hoover_BR.labelColor = "black"
		Hoover_BR.labelFont = "Dialog,BOLD,14";
		Hoover_BR.lineColor = "black"
		Hoover_BR.lineStyle = "dot"
		Hoover_BR.lineWidth = 4
		TopViewport_DET.addAxisMarker(Hoover_BR)                  
        
		SouthShore_BR = AxisMarker()
		SouthShore_BR.axis = "Y"
		SouthShore_BR.value = "1542"
		SouthShore_BR.labelText = "Hoover BR ~ 1543, SouthShore BR ~ 1542, CoveCreek_ BR ~ 1541 "
		SouthShore_BR.labelPosition = "above"
		SouthShore_BR.labelColor = "black"
		SouthShore_BR.labelFont = "Dialog,BOLD,14";
		SouthShore_BR.lineColor = "black"
		SouthShore_BR.lineStyle = "dot"
		SouthShore_BR.lineWidth = 4
		TopViewport_DET.addAxisMarker(SouthShore_BR)         
        
		CoveCreek_BR = AxisMarker()
		CoveCreek_BR.axis = "Y"
		CoveCreek_BR.value = "1541"
		CoveCreek_BR.labelText = "."
		CoveCreek_BR.labelPosition = "below"
		CoveCreek_BR.labelColor = "black"
		CoveCreek_BR.labelFont = "Dialog,BOLD,14";
		CoveCreek_BR.lineColor = "black"
		CoveCreek_BR.lineStyle = "dot"
		CoveCreek_BR.lineWidth = 4
		TopViewport_DET.addAxisMarker(CoveCreek_BR)         
        
		StateParkG_BR = AxisMarker()
		StateParkG_BR.axis = "Y"
		StateParkG_BR.value = "1530"
		StateParkG_BR.labelText = "StateParkG BR ~ 1530"
		StateParkG_BR.labelPosition = "above"
		StateParkG_BR.labelColor = "black"
		StateParkG_BR.labelFont = "Dialog,BOLD,14";
		StateParkG_BR.lineColor = "black"
		StateParkG_BR.lineStyle = "dot"
		StateParkG_BR.lineWidth = 4
		TopViewport_DET.addAxisMarker(StateParkG_BR)  



		MONGOLD_BR = AxisMarker()
		MONGOLD_BR.axis = "Y"
		MONGOLD_BR.value = "1450"
		MONGOLD_BR.labelText = "Mongold BR ~ 1450"
		MONGOLD_BR.labelPosition = "above"
		MONGOLD_BR.labelColor = "black"
		MONGOLD_BR.labelFont = "Dialog,BOLD,14";
		MONGOLD_BR.lineColor = "black"
		MONGOLD_BR.lineStyle = "dot"
		MONGOLD_BR.lineWidth = 4
		TopViewport_DET.addAxisMarker(MONGOLD_BR)  

        
		TopViewport_FOS= FOS_Plot.getViewport(0)
		BottomViewport_FOS = FOS_Plot.getViewport(1)
		Top_Y_Axis = TopViewport_FOS.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport_FOS.getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_FOS.getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("Pool Elevation")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)
		Bottom_Y_Axis = BottomViewport_FOS.getAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport_FOS.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_FOS.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)



    
        		
		
		TopViewport_GPR = GPR_Plot.getViewport(0)
		BottomViewport_GPR = GPR_Plot.getViewport(1)
		Top_Y_Axis = TopViewport_GPR.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport_GPR.getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_GPR.getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("Pool Elevation")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)
		Bottom_Y_Axis = BottomViewport_GPR.getAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport_GPR.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_GPR.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)

		GPRSW = AxisMarker()
		GPRSW.axis = "Y"
		GPRSW.value = "968.7"
		GPRSW.labelText = "GPR Spillway ~ 968.7"
		GPRSW.labelPosition = "below"
		GPRSW.labelColor = "purple"
		GPRSW.labelFont = "Dialog,BOLD,14";
		GPRSW.lineColor = "purple"
		GPRSW.lineStyle = "dot"
		GPRSW.lineWidth = 4
		TopViewport_GPR.addAxisMarker(GPRSW)        
        
        
        
		Whitcomb_BR = AxisMarker()
		Whitcomb_BR.axis = "Y"
		Whitcomb_BR.value = "970"
		Whitcomb_BR.labelText = "Whitcomb BR ~ 970"
		Whitcomb_BR.labelPosition = "above"
		Whitcomb_BR.labelColor = "black"
		Whitcomb_BR.labelFont = "Dialog,BOLD,14";
		Whitcomb_BR.lineColor = "black"
		Whitcomb_BR.lineStyle = "dot"
		Whitcomb_BR.lineWidth = 4
		TopViewport_GPR.addAxisMarker(Whitcomb_BR)    

		Thistle_BR = AxisMarker()
		Thistle_BR.axis = "Y"
		Thistle_BR.value = "919"
		Thistle_BR.labelText = "Thistle BR ~ 919"
		Thistle_BR.labelPosition = "below"
		Thistle_BR.labelColor = "black"
		Thistle_BR.labelFont = "Dialog,BOLD,14";
		Thistle_BR.lineColor = "black"
		Thistle_BR.lineStyle = "dot"
		Thistle_BR.lineWidth = 4
		TopViewport_GPR.addAxisMarker(Thistle_BR) 


		

		
		TopViewport_FRN = FRN_Plot.getViewport(0)
		BottomViewport_FRN = FRN_Plot.getViewport(1)
		Top_Y_Axis = TopViewport_FRN.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport_FRN.getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_FRN.getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("Pool Elevation")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)
		Bottom_Y_Axis = BottomViewport_FRN.getAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport_FRN.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_FRN.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)

		FRNSW = AxisMarker()
		FRNSW.axis = "Y"
		FRNSW.value = "358.5"
		FRNSW.labelText = "FRN Spillway ~ 358.5"
		FRNSW.labelPosition = "above"
		FRNSW.labelColor = "purple"
		FRNSW.labelFont = "Dialog,BOLD,14";
		FRNSW.lineColor = "purple"
		FRNSW.lineStyle = "dot"
		FRNSW.lineWidth = 4
		TopViewport_FRN.addAxisMarker(FRNSW)        
        
        
        
		Perkins_BR = AxisMarker()
		Perkins_BR.axis = "Y"
		Perkins_BR.value = "368"
		Perkins_BR.labelText = "Perkins BR ~ 368"
		Perkins_BR.labelPosition = "above"
		Perkins_BR.labelColor = "black"
		Perkins_BR.labelFont = "Dialog,BOLD,14";
		Perkins_BR.lineColor = "black"
		Perkins_BR.lineStyle = "dot"
		Perkins_BR.lineWidth = 4
		TopViewport_FRN.addAxisMarker(Perkins_BR)  

		FernRidgeShores_BR = AxisMarker()
		FernRidgeShores_BR.axis = "Y"
		FernRidgeShores_BR.value = "367"
		FernRidgeShores_BR.labelText = "FernRidgeShores BR ~ 367"
		FernRidgeShores_BR.labelPosition = "above"
		FernRidgeShores_BR.labelColor = "black"
		FernRidgeShores_BR.labelFont = "Dialog,BOLD,14";
		FernRidgeShores_BR.lineColor = "black"
		FernRidgeShores_BR.lineStyle = "dot"
		FernRidgeShores_BR.lineWidth = 4
		TopViewport_FRN.addAxisMarker(FernRidgeShores_BR)  

		Richardson_BR = AxisMarker()
		Richardson_BR.axis = "Y"
		Richardson_BR.value = "365"
		Richardson_BR.labelText = "Richardson BR ~ 365"
		Richardson_BR.labelPosition = "above"
		Richardson_BR.labelColor = "black"
		Richardson_BR.labelFont = "Dialog,BOLD,14";
		Richardson_BR.lineColor = "black"
		Richardson_BR.lineStyle = "dot"
		Richardson_BR.lineWidth = 4
		TopViewport_FRN.addAxisMarker(Richardson_BR)  

		Orchard_BR = AxisMarker()
		Orchard_BR.axis = "Y"
		Orchard_BR.value = "364"
		Orchard_BR.labelText = "Orchard BR ~ 364"
		Orchard_BR.labelPosition = "above"
		Orchard_BR.labelColor = "black"
		Orchard_BR.labelFont = "Dialog,BOLD,14";
		Orchard_BR.lineColor = "black"
		Orchard_BR.lineStyle = "dot"
		Orchard_BR.lineWidth = 4
		TopViewport_FRN.addAxisMarker(Orchard_BR)  

		
		start = HecTime()
		start.set(forecast_time)	
		CurrentTime = AxisMarker()
		CurrentTime.axis = "X"
		CurrentTime.value = str(start)
		CurrentTime.labelText = "Forecast Time"
		CurrentTime.labelPosition = "center"
		CurrentTime.labelAlignment = "center"
		CurrentTime.labelColor = "darkgray"
		CurrentTime.labelFont = "Dialog,BOLD,14"
		CurrentTime.lineColor = "gray"
		CurrentTime.lineStyle = "dash dot"
		CurrentTime.lineWidth = 2
        
		TopViewport_DET.addAxisMarker(CurrentTime)                    
		BottomViewport_DET.addAxisMarker(CurrentTime) 		
		TopViewport_GPR.addAxisMarker(CurrentTime)                    
		BottomViewport_GPR.addAxisMarker(CurrentTime) 		
		TopViewport_FOS.addAxisMarker(CurrentTime)                    
		BottomViewport_FOS.addAxisMarker(CurrentTime) 
		TopViewport_FRN.addAxisMarker(CurrentTime)                    
		BottomViewport_FRN.addAxisMarker(CurrentTime) 



###### Save Plot as A jpeg####



		DET_Plot.setSize(1400, 1300)
		DET_Plot.setLocation(100, 100)
		DET_Plot.saveToJpeg("W:\DET_FcstPlot.jpg")
		DET_Plot.close()
		
		GPR_Plot.setSize(1400, 1300)
		GPR_Plot.setLocation(100, 100)
		GPR_Plot.saveToJpeg("W:\GPR_FcstPlot.jpg")
		GPR_Plot.close()

		FOS_Plot.setSize(1400, 1300)
		FOS_Plot.setLocation(100, 100)
		FOS_Plot.saveToJpeg("W:\FOS_FcstPlot.jpg")
		FOS_Plot.close()
		

		FRN_Plot.setSize(1400, 1300)
		FRN_Plot.setLocation(100, 100)
		FRN_Plot.saveToJpeg("W:\FRN_FcstPlot.jpg")
		FRN_Plot.close()
		
################ Set Data up for exporting to Excel####
		datasets = java.util.Vector()
		
		datasets.add(OBS25DETElev)
		datasets.add(Sim25DETOutflow)
		datasets.add(OBSDETElev)
		datasets.add(SimDETOutflow)
		datasets.add(OBS75DETElev)
		datasets.add(Sim75DETOutflow)
		
		datasets.add(OBS25GPRElev)
		datasets.add(Sim25GPROutflow)
		datasets.add(OBSGPRElev)
		datasets.add(SimGPROutflow)
		datasets.add(OBS75GPRElev)
		datasets.add(Sim75GPROutflow)
		
		datasets.add(OBS25FOSElev)
		datasets.add(Sim25FOSOutflow)
		datasets.add(OBSFOSElev)
		datasets.add(SimFOSOutflow)
		datasets.add(OBS75FOSElev)
		datasets.add(Sim75FOSOutflow)
		
		datasets.add(OBS25FRNElev)
		datasets.add(Sim25FRNOutflow)
		datasets.add(OBSFRNElev)
		datasets.add(SimFRNOutflow)
		datasets.add(OBS75FRNElev)
		datasets.add(Sim75FRNOutflow)
						
		ExcelTable = HecDataTableToExcel.newTable()
		ExcelTable.createExcelFile(datasets,"W:\FRNandAboveFcst.xls")
################## Stection-End ######################################################################
		
	except Exception, e : 
		exc_type, exc_value, exc_traceback = sys.exc_info()
		traceback.print_exception(exc_type, exc_value, exc_traceback, limit=None, file=sys.stdout)
		formatted_lines = traceback.format_exc().splitlines()
		TracebackStr = '\n'.join(formatted_lines)
		MessageBox.showError(TracebackStr, 'Python Error')
	except java.lang.Exception, e : 
		exc_type, exc_value, exc_traceback = sys.exc_info()
		traceback.print_exception(exc_type, exc_value, exc_traceback, limit=None, file=sys.stdout)
		formatted_lines = traceback.format_exc().splitlines()
		TracebackStr = '\n'.join(formatted_lines)
		MessageBox.showError(TracebackStr, 'Java Error')

finally:
	cwmsFile.done()
