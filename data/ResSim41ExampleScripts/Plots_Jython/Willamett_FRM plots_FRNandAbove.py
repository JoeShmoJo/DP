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
	
		

		
	########################PROJECTS 	
		
		###GPR BELOW
		GPRLBElev = cwmsFile.get("//GPR/Elev-Forebay/28Feb2025 - 04Mar2025/1Hour/CBT-REV/")
		OBSGPRElev = cwmsFile.read("//GREEN PETER-POOL/ELEV/01NOV2024/3HOUR/------R0/")
		OBSGPRElev.setVersion("RFC 10-Day Flow Forecast")
		SimGPRInflow = cwmsFile.read("//GREEN PETER-POOL/FLOW-IN/01JAN2023/3HOUR/------R0/")
		SimGPRInflow.setVersion("RFC 10-Day Flow Forecast")
		SimGPROutflow = cwmsFile.read("//GREEN PETER-POOL/FLOW-OUT/01JAN2023/3HOUR/------R0/")
		SimGPROutflow.setVersion("RFC 10-Day Flow Forecast")
		GPRRuleCurve = cwmsFile.read("//GREEN PETER-CONSERVATION/ELEV-ZONE/01JAN2023/3HOUR/------R0/")
				
		#GPRRuleCurveN = cwmsFile.get("//GPR/ELEV-RULECURVE/01MAR2023/IR-MONTH/CENWP-CALC/")

		OBSGPRElev = OBSGPRElev.getData()
		SimGPRInflow = SimGPRInflow.getData()
		SimGPROutflow = SimGPROutflow.getData()
		GPRRuleCurve = GPRRuleCurve.getData()
			
				
		#### FOS BELOW
		FOSLBElev = cwmsFile.get("//FOS/Elev-Forebay/28Feb2025 - 04Mar2025/1Hour/CBT-REV/")
		OBSFOSElev = cwmsFile.read("//FOSTER-POOL/ELEV/01JAN2023/3HOUR/------R0/")
		OBSFOSElev.setVersion("RFC 10-Day Flow Forecast")
		SimFOSInflow = cwmsFile.read("//FOSTER-POOL/FLOW-IN/01JAN2023/3HOUR/------R0/")
		SimFOSInflow.setVersion("RFC 10-Day Flow Forecast")
		SimFOSOutflow = cwmsFile.read("//FOSTER-POOL/FLOW-OUT/01JAN2023/3HOUR/------R0/")
		SimFOSOutflow.setVersion("RFC 10-Day Flow Forecast")
		FOSRuleCurve = cwmsFile.read("//FOSTER-CONSERVATION/ELEV-ZONE/01JAN2023/3HOUR/------R0/")
		FOSRuleCurveN = cwmsFile.get("//FOS/ELEV-RULECURVE/01MAY2023/IR-MONTH/CENWP-CALC/")
		
		OBSFOSElev = OBSFOSElev.getData()
		SimFOSInflow = SimFOSInflow.getData()
		SimFOSOutflow = SimFOSOutflow.getData()
		FOSRuleCurve = FOSRuleCurve.getData()
	

		#//BIG CLIFF-POOL/FLOW-OUT/01JAN2023/1DAY/20C0/
		
		####DET Below
		DETLBElev = cwmsFile.get("//DET/Elev-Forebay/28Feb2025 - 04Mar2025/1Hour/CBT-REV/")
		OBSDETElev = cwmsFile.read("//DETROIT-POOL/ELEV/01JAN2023/3HOUR/------R0/")
		OBSDETElev.setVersion("RFC 10-Day Flow Forecast")
		SimDETInflow = cwmsFile.read("//DETROIT-POOL/FLOW-IN/01JAN2023/3HOUR/------R0/")
		SimDETInflow.setVersion("RFC 10-Day Flow Forecast")
		SimDETOutflow = cwmsFile.read("//DETROIT-POOL/FLOW-OUT/01JAN2023/3HOUR/------R0/")
		SimDETOutflow.setVersion("RFC 10-Day Flow Forecast")
		DETRuleCurve = cwmsFile.read("//DETROIT-CONSERVATION/ELEV-ZONE/01JAN2023/3HOUR/------R0/")
		DETRuleCurve.setVersion("RFC 10-Day Flow Forecast")
		DETRuleCurveN = cwmsFile.get("//DET/ELEV-RULECURVE/01MAY2023/IR-MONTH/CENWP-CALC/")
		



		OBSDETElev = OBSDETElev.getData()
		SimDETInflow = SimDETInflow.getData()
		SimDETOutflow = SimDETOutflow.getData()
		DETRuleCurve = DETRuleCurve.getData()
	

		##########CGR Below 
				
		CGRLBElev = cwmsFile.get("//CGR/Elev-Forebay/28Feb2025 - 04Mar2025/1Hour/CBT-REV/")
		OBSCGRElev = cwmsFile.read("//COUGAR-POOL/ELEV/01JAN2023/3HOUR/------R0/")
		OBSCGRElev.setVersion("RFC 10-Day Flow Forecast")
		SimCGRInflow = cwmsFile.read("//COUGAR-POOL/FLOW-IN/01JAN2023/3HOUR/------R0/")
		SimCGRInflow.setVersion("RFC 10-Day Flow Forecast")
		SimCGROutflow = cwmsFile.read("//COUGAR-POOL/FLOW-OUT/01JAN2023/3HOUR/------R0/")
		SimCGROutflow.setVersion("RFC 10-Day Flow Forecast")
		CGRRuleCurve = cwmsFile.read("//COUGAR-CONSERVATION/ELEV-ZONE/01JAN2023/3HOUR/------R0/")

		OBSCGRElev = OBSCGRElev.getData()
		SimCGRInflow = SimCGRInflow.getData()
		SimCGROutflow = SimCGROutflow.getData()
		CGRRuleCurve = CGRRuleCurve.getData()
	

		##### FRN Below
		
		FRNLBElev = cwmsFile.get("//FRN/Elev-Forebay/28Feb2025 - 04Mar2025/6Hour/RFC-FCST/")
		OBSFRNElev = cwmsFile.read("//FERN RIDGE-POOL/ELEV/01JAN2023/3HOUR/------R0/")
		OBSFRNElev.setVersion("RFC 10-Day Flow Forecast")
		SimFRNInflow = cwmsFile.read("//FERN RIDGE-POOL/FLOW-IN/01JAN2023/3HOUR/------R0/")
		SimFRNInflow.setVersion("RFC 10-Day Flow Forecast")
		SimFRNOutflow = cwmsFile.read("//FERN RIDGE-POOL/FLOW-OUT/01JAN2023/3HOUR/------R0/")
		SimFRNOutflow.setVersion("RFC 10-Day Flow Forecast")
		FRNRuleCurve = cwmsFile.read("//FERN RIDGE-CONSERVATION/ELEV-ZONE/01JAN2023/3HOUR/------R0/")
		FRNRuleCurve.setVersion("RFC 10-Day Flow Forecast")
		#FRNRuleCurveN = cwmsFile.get("//FRN/ELEV-RULECURVE/01JUN2023/IR-MONTH/CENWP-CALC/")
		
						
		OBSFRNElev = OBSFRNElev.getData()
		SimFRNInflow = SimFRNInflow.getData()
		SimFRNOutflow = SimFRNOutflow.getData()
		FRNRuleCurve = FRNRuleCurve.getData()
	

############################################ Control Points

		MNRO = cwmsFile.read("//LONG TOM_AT MONROE/FLOW/01NOV2024/3HOUR/------R0/")
		MNRO.setVersion("RFC 10-Day Flow Forecast")
		MNROUR = cwmsFile.read("//LONG TOM_AT MONROE/FLOW-UNREG/01NOV2024/3HOUR/------R0/")
		MNROUR.setVersion("RFC 10-Day Flow Forecast Unregulated")					
		VIDO = cwmsFile.read("//MCKENZIE_AT VIDA/FLOW/01NOV2024/3HOUR/------R0/")
		VIDO.setVersion("RFC 10-Day Flow Forecast")
		VIDOUR = cwmsFile.read("//MCKENZIE_AT VIDA/FLOW-UNREG/15Nov2024 - 25Nov2024/3Hour/------R0/")
		VIDOUR.setVersion("RFC 10-Day Flow Forecast Unregulated")				
		MEHO = cwmsFile.read("//NO SANTIAM_AT MEHAMA/FLOW/01NOV2024/3HOUR/------R0/")
		MEHO.setVersion("RFC 10-Day Flow Forecast")
		MEHOUR = cwmsFile.read("//NO SANTIAM_AT MEHAMA/FLOW-UNREG/15Nov2024 - 25Nov2024/3Hour/------R0/")
		MEHOUR.setVersion("RFC 10-Day Flow Forecast Unregulated")		
		WTLO = cwmsFile.read("//SO SANTIAM_AT WATERLOO/FLOW/01NOV2024/3HOUR/------R0/")
		WTLO.setVersion("RFC 10-Day Flow Forecast")				
		WTLOUR = cwmsFile.read("//SO SANTIAM_AT WATERLOO/FLOW-UNREG/01NOV2024/3HOUR/------R0/")
		WTLOUR.setVersion("RFC 10-Day Flow Forecast Unregulated")	
						
		VIDO = VIDO.getData()
		VIDOUR = VIDOUR.getData()
		MEHO = MEHO.getData()
		MEHOUR = MEHOUR.getData()
		MNRO = MNRO.getData()
		MNROUR = MNROUR.getData()		
		WTLO = WTLO.getData()
		WTLOUR = WTLOUR.getData()
        
### Create Plot ####

        


		DET_Plot = Plot.newPlot("Detroit Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSDETElev)
		TopView.addCurve("Y1", OBSDETElev)
		TopView.addCurve("Y1", DETRuleCurve)
		#TopView.addCurve("Y1", DETRuleCurveN)
		TopView.addCurve("Y1", DETLBElev)		
		BottomView.addCurve("Y1", SimDETInflow)
		BottomView.addCurve("Y1", SimDETOutflow)
		DET_Plot.configurePlotLayout(Layout)
		DET_Plot.showPlot()
		
		
		
		GPR_Plot = Plot.newPlot("Green Peter Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSGPRElev)
		TopView.addCurve("Y1", GPRRuleCurve)
		#TopView.addCurve("Y1", GPRRuleCurveN)
		TopView.addCurve("Y1", GPRLBElev)		
		BottomView.addCurve("Y1", SimGPRInflow)
		BottomView.addCurve("Y1", SimGPROutflow)
		GPR_Plot.configurePlotLayout(Layout)
		GPR_Plot.showPlot()
		
		
		
		FOS_Plot = Plot.newPlot("Foster Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSFOSElev)
		TopView.addCurve("Y1", FOSRuleCurve)
		#TopView.addCurve("Y1", FOSRuleCurveN)
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
		TopView.addCurve("Y1", FRNRuleCurve)
		#TopView.addCurve("Y1", FRNRuleCurveN)
		TopView.addCurve("Y1", FRNLBElev)		
		BottomView.addCurve("Y1", SimFRNInflow)
		BottomView.addCurve("Y1", SimFRNOutflow)
		FRN_Plot.configurePlotLayout(Layout)
		FRN_Plot.showPlot()

		MNRO_Plot = Plot.newPlot("Long Tom River @ Monroe Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		TopView.addCurve("Y1", MNRO)
		TopView.addCurve("Y1", MNROUR)	
		MNRO_Plot.configurePlotLayout(Layout)
		MNRO_Plot.showPlot()

		VIDO_Plot = Plot.newPlot("McKenzie River near Vida")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		TopView.addCurve("Y1", VIDO)
		TopView.addCurve("Y1", VIDOUR)	
		VIDO_Plot.configurePlotLayout(Layout)
		VIDO_Plot.showPlot()

		MEHO_Plot = Plot.newPlot("McKenzie River near Vida")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		TopView.addCurve("Y1", MEHO)
		TopView.addCurve("Y1", MEHOUR)	
		MEHO_Plot.configurePlotLayout(Layout)
		MEHO_Plot.showPlot()

		WTLO_Plot = Plot.newPlot("South Santiam River @ Waterloo")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		TopView.addCurve("Y1", WTLO)
		TopView.addCurve("Y1", WTLOUR)	
		WTLO_Plot.configurePlotLayout(Layout)
		WTLO_Plot.showPlot()


				
####### Plot Line Styles####

		####GPR Below
		
		OBSGPRElevCurve = GPR_Plot.getCurve(OBSGPRElev)
		OBSGPRElevCurve.setLineWidth(6)
		OBSGPRElevCurve = GPR_Plot.getCurve(OBSGPRElev)
		OBSGPRElevCurve.setLineColor("green")
		OBSGPRElevCurve.setLineStyle("solid")
		OBSGPRElevCurve.setLineWidth(3)
		
		'''
		GPRRuleCurveNormal = GPR_Plot.getCurve(GPRRuleCurveN)
		GPRRuleCurveNormal.setLineWidth(3)
		GPRRuleCurveNormal = GPR_Plot.getCurve(GPRRuleCurveN)
		GPRRuleCurveNormal.setLineColor("black")
		GPRRuleCurveNormal.setLineStyle("Solid")
		GPRRuleCurveNormal.setLineWidth(3)
		'''

		OBSGPROUTFLOWCurve = GPR_Plot.getCurve(SimGPROutflow)
		OBSGPROUTFLOWCurve.setLineWidth(3)
		OBSGPROUTFLOWCurve = GPR_Plot.getCurve(SimGPROutflow)
		OBSGPROUTFLOWCurve.setLineColor("darkgreen")
		OBSGPROUTFLOWCurve.setLineStyle("dash")
		OBSGPROUTFLOWCurve.setLineWidth(3)
		
		

		GPRRuleCurveEIS = GPR_Plot.getCurve(GPRRuleCurve)
		GPRRuleCurveEIS.setLineWidth(6)
		GPRRuleCurveEIS = GPR_Plot.getCurve(GPRRuleCurve)
		GPRRuleCurveEIS.setLineColor("black")
		GPRRuleCurveEIS.setLineStyle("dash")
		GPRRuleCurveEIS.setLineWidth(3)
		
		
		OBSGPRINFLOWCurve = GPR_Plot.getCurve(SimGPRInflow)
		OBSGPRINFLOWCurve.setLineWidth(3)
		OBSGPRINFLOWCurve = GPR_Plot.getCurve(SimGPRInflow)
		OBSGPRINFLOWCurve.setLineColor("green")
		OBSGPRINFLOWCurve.setLineStyle("solid")
		OBSGPRINFLOWCurve.setLineWidth(3)     
		
	
		GPRLBElev2 = GPR_Plot.getCurve(GPRLBElev)
		GPRLBElev2.setLineWidth(5)
		GPRLBElev2 = GPR_Plot.getCurve(GPRLBElev)
		GPRLBElev2.setLineColor("darkmagenta")
		GPRLBElev2.setLineStyle("Solid")
		
		
		###FOS Below
		
		OBSFOSElevCurve = FOS_Plot.getCurve(OBSFOSElev)
		OBSFOSElevCurve.setLineWidth(3)
		OBSFOSElevCurve = FOS_Plot.getCurve(OBSFOSElev)
		OBSFOSElevCurve.setLineColor("green")
		OBSFOSElevCurve.setLineStyle("solid")
		OBSFOSElevCurve.setLineWidth(3)
		'''
		FOSRuleCurveNormal = FOS_Plot.getCurve(FOSRuleCurveN)
		FOSRuleCurveNormal.setLineWidth(3)
		FOSRuleCurveNormal = FOS_Plot.getCurve(FOSRuleCurveN)
		FOSRuleCurveNormal.setLineColor("black")
		FOSRuleCurveNormal.setLineStyle("Solid")
		FOSRuleCurveNormal.setLineWidth(3)
		'''

		OBSFOSOUTFLOWCurve = FOS_Plot.getCurve(SimFOSOutflow)
		OBSFOSOUTFLOWCurve.setLineWidth(5)
		OBSFOSOUTFLOWCurve = FOS_Plot.getCurve(SimFOSOutflow)
		OBSFOSOUTFLOWCurve.setLineColor("darkgreen")
		OBSFOSOUTFLOWCurve.setLineStyle("dash")
		OBSFOSOUTFLOWCurve.setLineWidth(5)

		
		FOSRuleCurveEIS = FOS_Plot.getCurve(FOSRuleCurve)
		FOSRuleCurveEIS.setLineWidth(6)
		FOSRuleCurveEIS = FOS_Plot.getCurve(FOSRuleCurve)
		FOSRuleCurveEIS.setLineColor("black")
		FOSRuleCurveEIS.setLineStyle("dash")
		FOSRuleCurveEIS.setLineWidth(3)
		

		OBSFOSINFLOWCurve = FOS_Plot.getCurve(SimFOSInflow)
		OBSFOSINFLOWCurve.setLineWidth(3)
		OBSFOSINFLOWCurve = FOS_Plot.getCurve(SimFOSInflow)
		OBSFOSINFLOWCurve.setLineColor("green")
		OBSFOSINFLOWCurve.setLineStyle("solid")
		OBSFOSINFLOWCurve.setLineWidth(3)
		
		
		FOSLBElev2 = FOS_Plot.getCurve(FOSLBElev)
		FOSLBElev2.setLineWidth(5)
		FOSLBElev2 = FOS_Plot.getCurve(FOSLBElev)
		FOSLBElev2.setLineColor("darkmagenta")
		FOSLBElev2.setLineStyle("solid")
		FOSLBElev2.setLineWidth(5)
		
		
				############### DET below
		
		OBSDETElevCurve = DET_Plot.getCurve(OBSDETElev)
		OBSDETElevCurve.setLineWidth(6)
		OBSDETElevCurve = DET_Plot.getCurve(OBSDETElev)
		OBSDETElevCurve.setLineColor("green")
		OBSDETElevCurve.setLineStyle("solid")
		OBSDETElevCurve.setLineWidth(3)

		'''
		DETRuleCurveNormal = DET_Plot.getCurve(DETRuleCurveN)
		DETRuleCurveNormal.setLineWidth(3)
		DETRuleCurveNormal = DET_Plot.getCurve(DETRuleCurveN)
		DETRuleCurveNormal.setLineColor("black")
		DETRuleCurveNormal.setLineStyle("Solid")
		DETRuleCurveNormal.setLineWidth(3)
		'''
		OBSDETOUTFLOWCurve = DET_Plot.getCurve(SimDETOutflow)
		OBSDETOUTFLOWCurve.setLineWidth(3)
		OBSDETOUTFLOWCurve = DET_Plot.getCurve(SimDETOutflow)
		OBSDETOUTFLOWCurve.setLineColor("darkgreen")
		OBSDETOUTFLOWCurve.setLineStyle("dash")
		OBSDETOUTFLOWCurve.setLineWidth(3)

		
		DETRuleCurveEIS = DET_Plot.getCurve(DETRuleCurve)
		DETRuleCurveEIS.setLineWidth(3)
		DETRuleCurveEIS = DET_Plot.getCurve(DETRuleCurve)
		DETRuleCurveEIS.setLineColor("black")
		DETRuleCurveEIS.setLineStyle("dash")
		
		OBSDETINFLOWCurve = DET_Plot.getCurve(SimDETInflow)
		OBSDETINFLOWCurve.setLineWidth(3)
		OBSDETINFLOWCurve = DET_Plot.getCurve(SimDETInflow)
		OBSDETINFLOWCurve.setLineColor("green")
		OBSDETINFLOWCurve.setLineStyle("solid")
		

		DETLBElev2 = DET_Plot.getCurve(DETLBElev)
		DETLBElev2.setLineWidth(5)
		DETLBElev2.setLineColor("darkmagenta")
		DETLBElev2.setLineStyle("solid")

		


		############### FRN below
		
		OBSFRNElevCurve = FRN_Plot.getCurve(OBSFRNElev)
		OBSFRNElevCurve.setLineWidth(6)
		OBSFRNElevCurve = FRN_Plot.getCurve(OBSFRNElev)
		OBSFRNElevCurve.setLineColor("green")
		OBSFRNElevCurve.setLineStyle("solid")
		OBSFRNElevCurve.setLineWidth(3)

		'''
		FRNRuleCurveNormal = FRN_Plot.getCurve(FRNRuleCurveN)
		FRNRuleCurveNormal.setLineWidth(3)
		FRNRuleCurveNormal = FRN_Plot.getCurve(FRNRuleCurveN)
		FRNRuleCurveNormal.setLineColor("black")
		FRNRuleCurveNormal.setLineStyle("Solid")
		FRNRuleCurveNormal.setLineWidth(3)
		'''

		OBSFRNOUTFLOWCurve = FRN_Plot.getCurve(SimFRNOutflow)
		OBSFRNOUTFLOWCurve.setLineWidth(3)
		OBSFRNOUTFLOWCurve = FRN_Plot.getCurve(SimFRNOutflow)
		OBSFRNOUTFLOWCurve.setLineColor("darkgreen")
		OBSFRNOUTFLOWCurve.setLineStyle("dash")
		OBSFRNOUTFLOWCurve.setLineWidth(3)


		FRNRuleCurveEIS = FRN_Plot.getCurve(FRNRuleCurve)
		FRNRuleCurveEIS.setLineWidth(6)
		FRNRuleCurveEIS = FRN_Plot.getCurve(FRNRuleCurve)
		FRNRuleCurveEIS.setLineColor("black")
		FRNRuleCurveEIS.setLineStyle("dash")
		FRNRuleCurveEIS.setLineWidth(3)
		
		OBSFRNINFLOWCurve = FRN_Plot.getCurve(SimFRNInflow)
		OBSFRNINFLOWCurve.setLineWidth(3)
		OBSFRNINFLOWCurve = FRN_Plot.getCurve(SimFRNInflow)
		OBSFRNINFLOWCurve.setLineColor("green")
		OBSFRNINFLOWCurve.setLineStyle("dash")
		OBSFRNINFLOWCurve.setLineWidth(3)
		
		
		FRNLBElev2 = FRN_Plot.getCurve(FRNLBElev)
		FRNLBElev2.setLineWidth(5)
		FRNLBElev2 = FRN_Plot.getCurve(FRNLBElev)
		FRNLBElev2.setLineColor("darkmagenta")
		FRNLBElev2.setLineStyle("solid")
		FRNLBElev2.setLineWidth(5)
		
#################### Control Point Curves


		MEHOFLOW = MEHO_Plot.getCurve(MEHO)
		MEHOFLOW.setLineWidth(5)
		MEHOFLOW = MEHO_Plot.getCurve(MEHO)
		MEHOFLOW.setLineColor("darkblue")
		MEHOFLOW.setLineStyle("solid")
		
		MNROFLOW = MNRO_Plot.getCurve(MNRO)
		MNROFLOW.setLineWidth(5)
		MNROFLOW = MNRO_Plot.getCurve(MNRO)
		MNROFLOW.setLineColor("darkblue")
		MNROFLOW.setLineStyle("solid")



		VIDOFLOW = VIDO_Plot.getCurve(VIDO)
		VIDOFLOW.setLineWidth(5)
		VIDOFLOW = VIDO_Plot.getCurve(VIDO)
		VIDOFLOW.setLineColor("darkblue")
		VIDOFLOW.setLineStyle("solid")
		
		WTLOFLOW = WTLO_Plot.getCurve(WTLO)
		WTLOFLOW.setLineWidth(5)
		WTLOFLOW = WTLO_Plot.getCurve(WTLO)
		WTLOFLOW.setLineColor("darkblue")
		WTLOFLOW.setLineStyle("solid")



        
#####Axis Formating Project plots##########

        
        
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
        
        
        

		

#####Axis Formating Control Popint plots##########


		TopViewport_MEHO = MEHO_Plot.getViewport(0)
		Top_Y_Axis = TopViewport_MEHO.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport_MEHO.getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_MEHO.getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("Flow (CFS)")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)


		MEHOBF = AxisMarker()
		MEHOBF.axis = "Y"
		MEHOBF.value = "16450.4"
		MEHOBF.labelText = "MEHO Bank Full ~ 16450.4"
		MEHOBF.labelPosition = "above"
		MEHOBF.labelColor = "purple"
		MEHOBF.labelFont = "Dialog,BOLD,14";
		MEHOBF.lineColor = "purple"
		MEHOBF.lineStyle = "dot"
		MEHOBF.lineWidth = 4
		TopViewport_MEHO.addAxisMarker(MEHOBF)        
        

		TopViewport_MNRO = MNRO_Plot.getViewport(0)
		Top_Y_Axis = TopViewport_MNRO.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport_MNRO.getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_MNRO.getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("Flow (CFS)")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)


		MNROBF = AxisMarker()
		MNROBF.axis = "Y"
		MNROBF.value = "5660.96"
		MNROBF.labelText = "MNRO Bank Full ~ 5660.96"
		MNROBF.labelPosition = "above"
		MNROBF.labelColor = "purple"
		MNROBF.labelFont = "Dialog,BOLD,14";
		MNROBF.lineColor = "purple"
		MNROBF.lineStyle = "dot"
		MNROBF.lineWidth = 4
		TopViewport_MNRO.addAxisMarker(MNROBF)


		TopViewport_VIDO = VIDO_Plot.getViewport(0)
		Top_Y_Axis = TopViewport_VIDO.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport_VIDO.getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_VIDO.getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("Flow (CFS)")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)


		VIDOBF = AxisMarker()
		VIDOBF.axis = "Y"
		VIDOBF.value = "22180"
		VIDOBF.labelText = "VIDO Bank Full ~ 22180"
		VIDOBF.labelPosition = "above"
		VIDOBF.labelColor = "purple"
		VIDOBF.labelFont = "Dialog,BOLD,14";
		VIDOBF.lineColor = "purple"
		VIDOBF.lineStyle = "dot"
		VIDOBF.lineWidth = 4
		TopViewport_VIDO.addAxisMarker(VIDOBF)


		TopViewport_WTLO = WTLO_Plot.getViewport(0)
		Top_Y_Axis = TopViewport_WTLO.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport_WTLO.getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_WTLO.getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("Flow (CFS)")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)


		WTLOBF = AxisMarker()
		WTLOBF.axis = "Y"
		WTLOBF.value = "19025.83"
		WTLOBF.labelText = "WTLO Bank Full ~ 19025.83"
		WTLOBF.labelPosition = "above"
		WTLOBF.labelColor = "purple"
		WTLOBF.labelFont = "Dialog,BOLD,14";
		WTLOBF.lineColor = "purple"
		WTLOBF.lineStyle = "dot"
		WTLOBF.lineWidth = 4
		TopViewport_WTLO.addAxisMarker(WTLOBF)


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

		TopViewport_MEHO.addAxisMarker(CurrentTime)  
		TopViewport_MNRO.addAxisMarker(CurrentTime)
		TopViewport_VIDO.addAxisMarker(CurrentTime)
		TopViewport_WTLO.addAxisMarker(CurrentTime)		






###### Save Plot as A jpeg####

		DET_Plot.setSize(1400, 1300)
		DET_Plot.setLocation(100, 100)
		DET_Plot.saveToJpeg("F:\DET_FcstPlot.jpg")
		DET_Plot.close()
		
		GPR_Plot.setSize(1400, 1300)
		GPR_Plot.setLocation(100, 100)
		GPR_Plot.saveToJpeg("F:\GPR_FcstPlot.jpg")
		GPR_Plot.close()

		FOS_Plot.setSize(1400, 1300)
		FOS_Plot.setLocation(100, 100)
		FOS_Plot.saveToJpeg("F:\FOS_FcstPlot.jpg")
		FOS_Plot.close()
		

		FRN_Plot.setSize(1400, 1300)
		FRN_Plot.setLocation(100, 100)
		FRN_Plot.saveToJpeg("F:\FRN_FcstPlot.jpg")
		FRN_Plot.close()

		MEHO_Plot.setSize(1400, 1300)
		MEHO_Plot.setLocation(100, 100)
		MEHO_Plot.saveToJpeg("F:\MEHO_FcstPlot.jpg")
		MEHO_Plot.close()
		
		MNRO_Plot.setSize(1400, 1300)
		MNRO_Plot.setLocation(100, 100)
		MNRO_Plot.saveToJpeg("F:\MNRO_FcstPlot.jpg")
		MNRO_Plot.close()

		VIDO_Plot.setSize(1400, 1300)
		VIDO_Plot.setLocation(100, 100)
		VIDO_Plot.saveToJpeg("F:\VIDO_FcstPlot.jpg")
		VIDO_Plot.close()

		WTLO_Plot.setSize(1400, 1300)
		WTLO_Plot.setLocation(100, 100)
		WTLO_Plot.saveToJpeg("F:\WTLO_FcstPlot.jpg")
		WTLO_Plot.close()




################ Set Data up for exporting to Excel####
		datasets = java.util.Vector()
		
		#datasets.add(OBS25DETElev)
		#datasets.add(Sim25DETOutflow)
		datasets.add(OBSDETElev)
		datasets.add(SimDETOutflow)
		#datasets.add(OBS75DETElev)
		#datasets.add(Sim75DETOutflow)
		
		#datasets.add(OBS25GPRElev)
		#datasets.add(Sim25GPROutflow)
		datasets.add(OBSGPRElev)
		datasets.add(SimGPROutflow)
		#datasets.add(OBS75GPRElev)
		#datasets.add(Sim75GPROutflow)
		
		#datasets.add(OBS25FOSElev)
		#datasets.add(Sim25FOSOutflow)
		datasets.add(OBSFOSElev)
		datasets.add(SimFOSOutflow)
		#datasets.add(OBS75FOSElev)
		#datasets.add(Sim75FOSOutflow)
		
		#datasets.add(OBS25FRNElev)
		#datasets.add(Sim25FRNOutflow)
		datasets.add(OBSFRNElev)
		datasets.add(SimFRNOutflow)
		#datasets.add(OBS75FRNElev)
		#datasets.add(Sim75FRNOutflow)
						
		ExcelTable = HecDataTableToExcel.newTable()
		ExcelTable.createExcelFile(datasets,"Z:\FRNandAboveFcst.xls")
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
