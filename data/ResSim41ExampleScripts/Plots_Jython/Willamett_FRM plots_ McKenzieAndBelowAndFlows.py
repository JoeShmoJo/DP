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
		###HCR Below
		OBSHCRElev = cwmsFile.read("//HILLS CREEK-POOL/ELEV/01JAN2023/3HOUR/------R0/")
		OBSHCRElev.setVersion("RFC 10-Day Forecast")
		SimHCRInflow = cwmsFile.read("//HILLS CREEK-POOL/FLOW-IN/01JAN2023/3HOUR/------R0/")
		SimHCRInflow.setVersion("RFC 10-Day Forecast")
		SimHCROutflow = cwmsFile.read("//HILLS CREEK-POOL/FLOW-OUT/01JAN2023/3HOUR/------R0/")
		SimHCROutflow.setVersion("RFC 10-Day Forecast")
		HCRRuleCurve = cwmsFile.read("//HILLS CREEK-CONSERVATION/ELEV-ZONE/01JAN2023/3HOUR/------R0/")
		HCRRuleCurve.setVersion("RFC 10-Day Forecast")
		#HCRRuleCurveN = cwmsFile.get("//HCR/ELEV-RULECURVE/01OCT2023/IR-MONTH/CENWP-CALC/")
		HCRLBElev = cwmsFile.get("//HCR/Elev-Forebay/28Feb2025 - 04Mar2025/1Hour/CBT-REV/")		


		OBSHCRElev = OBSHCRElev.getData()
		SimHCRInflow = SimHCRInflow.getData()
		SimHCROutflow = SimHCROutflow.getData()
		HCRRuleCurve = HCRRuleCurve.getData()


        #LOP Below
        
        
		OBSLOPElev = cwmsFile.read("//LOOKOUT POINT-POOL/ELEV/01JAN2023/3HOUR/------R0/")
		OBSLOPElev.setVersion("RFC 10-Day Forecast")
		SimLOPInflow = cwmsFile.read("//LOOKOUT POINT-POOL/FLOW-IN/01JAN2023/3HOUR/------R0/")
		SimLOPInflow.setVersion("RFC 10-Day Forecast")
		SimLOPOutflow = cwmsFile.read("//LOOKOUT POINT-POOL/FLOW-OUT/01JAN2023/3HOUR/------R0/")
		SimLOPOutflow.setVersion("RFC 10-Day Forecast")
		LOPRuleCurve = cwmsFile.read("//LOOKOUT POINT-CONSERVATION/ELEV-ZONE//3HOUR/------R0/")
		LOPRuleCurve.setVersion("RFC 10-Day Forecast")
		LOPLBElev = cwmsFile.get("//LOP/Elev-Forebay/28Feb2025 - 04Mar2025/1Hour/CBT-REV/")
		#LOPRuleCurveN = cwmsFile.get("//LOP/ELEV-RULECURVE/01JAN2023/IR-MONTH/CENWP-CALC/")

		

		

		OBSLOPElev = OBSLOPElev.getData()
		SimLOPInflow = SimLOPInflow.getData()
		SimLOPOutflow = SimLOPOutflow.getData()
		LOPRuleCurve = LOPRuleCurve.getData()
	




		

		CGRLBElev = cwmsFile.get("//CGR/Elev-Forebay/28Feb2025 - 04Mar2025/1Hour/CBT-REV/")

		OBSCGRElev = cwmsFile.read("//COUGAR-POOL/ELEV/01JAN2023/3HOUR/------R0/")
		OBSCGRElev.setVersion("RFC 10-Day Forecast")
		SimCGRInflow = cwmsFile.read("//COUGAR-POOL/FLOW-IN/01JAN2023/3HOUR/------R0/")
		SimCGRInflow.setVersion("RFC 10-Day Forecast")
		SimCGROutflow = cwmsFile.read("//COUGAR-POOL/FLOW-OUT/01JAN2023/3HOUR/------R0/")
		SimCGROutflow.setVersion("RFC 10-Day Forecast")
		CGRRuleCurve = cwmsFile.read("//COUGAR-CONSERVATION/ELEV-ZONE/01JAN2023/3HOUR/------R0/")
		CGRRuleCurve.setVersion("RFC 10-Day Forecast")
		#CGRRuleCurveN = cwmsFile.get("//CGR/ELEV-RULECURVE/01NOV2023/IR-MONTH/CENWP-CALC/")
		
		
		OBSCGRElev = OBSCGRElev.getData()
		SimCGRInflow = SimCGRInflow.getData()
		SimCGROutflow = SimCGROutflow.getData()
		CGRRuleCurve = CGRRuleCurve.getData()
	

				
		

		
		
		
		###FAL Below
		FALLBElev = cwmsFile.get("//FAL/Elev-Forebay/28Feb2025 - 04Mar2025/6Hour/RFC-FCST/")

		
		OBSFALElev = cwmsFile.read("//FALL CREEK-POOL/ELEV/01JAN2023/3HOUR/------R0/")
		OBSFALElev.setVersion("25% Flow Forecast")
		SimFALInflow = cwmsFile.read("//FALL CREEK-POOL/FLOW-IN/01JAN2023/3HOUR/------R0/")
		SimFALInflow.setVersion("25% Flow Forecast")
		SimFALOutflow = cwmsFile.read("//FALL CREEK-POOL/FLOW-OUT/01JAN2023/3HOUR/------R0/")
		SimFALOutflow.setVersion("25% Flow Forecast")
		FALRuleCurve = cwmsFile.read("//FALL CREEK-CONSERVATION/ELEV-ZONE/01JAN2023/3HOUR/------R0/")
		FALRuleCurve.setVersion("25% Flow Forecast")
		FALRuleCurveN = cwmsFile.get("//FAL/ELEV-RULECURVE/01APR2023/IR-MONTH/CENWP-CALC/")
		

		

		
		OBSFALElev = OBSFALElev.getData()
		SimFALInflow = SimFALInflow.getData()
		SimFALOutflow = SimFALOutflow.getData()
		FALRuleCurve = FALRuleCurve.getData()
		
		
		BLRLBElev = cwmsFile.get("//BLU/Elev-Forebay/28Feb2025 - 04Mar2025/6Hour/RFC-FCST/")

		
		OBSBLRElev = cwmsFile.read("//BLUE RIVER-POOL/ELEV/01JAN2023/3HOUR/------R0/")
		OBSBLRElev.setVersion("RFC 10-Day Forecast")
		SimBLRInflow = cwmsFile.read("//BLUE RIVER-POOL/FLOW-IN/01JAN2023/3HOUR/------R0/")
		SimBLRInflow.setVersion("RFC 10-Day Forecast")
		SimBLROutflow = cwmsFile.read("//BLUE RIVER-POOL/FLOW-OUT/01JAN2023/3HOUR/------R0/")
		SimBLROutflow.setVersion("RFC 10-Day Forecast")
		BLRRuleCurve = cwmsFile.read("//BLUE RIVER-CONSERVATION/ELEV-ZONE/01JAN2023/3HOUR/------R0/")
		BLRRuleCurve.setVersion("RFC 10-Day Forecast")
		BLRRuleCurveN = cwmsFile.get("//BLU/ELEV-RULECURVE/01APR2023/IR-MONTH/CENWP-CALC/")
		




		
		OBSBLRElev = OBSBLRElev.getData()
		SimBLRInflow = SimBLRInflow.getData()
		SimBLROutflow = SimBLROutflow.getData()
		BLRRuleCurve = BLRRuleCurve.getData()
	


								
				
		DORLBElev = cwmsFile.get("//DOR/Elev-Forebay/28Feb2025 - 04Mar2025/6Hour/RFC-FCST/")
		
		OBSDORElev = cwmsFile.read("//DORENA-POOL/ELEV/01JAN2023/3HOUR/------R0/")
		OBSDORElev.setVersion("RFC 10-Day Forecast")
		SimDORInflow = cwmsFile.read("//DORENA-POOL/FLOW-IN/01JAN2023/3HOUR/------R0/")
		SimDORInflow.setVersion("RFC 10-Day Forecast")
		SimDOROutflow = cwmsFile.read("//DORENA-POOL/FLOW-OUT/01JAN2023/3HOUR/------R0/")
		SimDOROutflow.setVersion("RFC 10-Day Forecast")
		DORRuleCurve = cwmsFile.read("//DORENA-CONSERVATION/ELEV-ZONE/01JAN2023/3HOUR/------R0/")
		DORRuleCurve.setVersion("RFC 10-Day Forecast")
		#DORRuleCurveN = cwmsFile.get("//DOR/ELEV-RULECURVE/01JUL2023/IR-MONTH/CENWP-CALC/")
		

		

		OBSDORElev = OBSDORElev.getData()
		SimDORInflow = SimDORInflow.getData()
		SimDOROutflow = SimDOROutflow.getData()
		DORRuleCurve = DORRuleCurve.getData()
				
		
		
		COTLBElev = cwmsFile.get("//COT/Elev-Forebay/28Feb2025 - 04Mar2025/6Hour/RFC-FCST/")

		#COTRuleCurveN = cwmsFile.get("//COT/ELEV-RULECURVE//IR-MONTH/CENWP-CALC/")
		
		OBSCOTElev = cwmsFile.read("//COTTAGE GROVE-POOL/ELEV/01JAN2023/3HOUR/------R0/")
		OBSCOTElev.setVersion("RFC 10-Day Forecast")
		SimCOTInflow = cwmsFile.read("//COTTAGE GROVE-POOL/FLOW-IN/01JAN2023/3HOUR/------R0/")
		SimCOTInflow.setVersion("RFC 10-Day Forecast")
		SimCOTOutflow = cwmsFile.read("//COTTAGE GROVE-POOL/FLOW-OUT/01JAN2023/3HOUR/------R0/")
		SimCOTOutflow.setVersion("RFC 10-Day Forecast")
		COTRuleCurveN = cwmsFile.get("//COT/ELEV-RULECURVE//IR-MONTH/CENWP-CALC/")
		COTRuleCurve = cwmsFile.read("//COTTAGE GROVE-CONSERVATION/ELEV-ZONE/01NOV2024/3HOUR/------R0/")
		COTRuleCurve.setVersion("RFC 10-Day Forecast")		
		
		OBSCOTElev = OBSCOTElev.getData()
		SimCOTInflow = SimCOTInflow.getData()
		SimCOTOutflow = SimCOTOutflow.getData()
		COTRuleCurve = COTRuleCurve.getData()


		
		


		
		
		
		#WILLAMETTE FLOW DATA 

		SALOFlow = cwmsFile.read("//WILLAMETTE_AT SALEM/FLOW/01JAN2023/3HOUR/------R0/")
		SALOFlow.setVersion("RFC 10-Day Forecast")
		SALOFlowUR = cwmsFile.read("//WILLAMETTE_AT SALEM/FLOW-UNREG/01JAN2023/3HOUR/------R0/")
		SALOFlowUR.setVersion("RFC 10-Day Unregulated")
		ALBOFlow = cwmsFile.read("//WILLAMETTE_AT ALBANY/FLOW/01JAN2023/3HOUR/------R0/")
		ALBOFlow.setVersion("RFC 10-Day Forecast")
		ALBOFlowUR = cwmsFile.read("//WILLAMETTE_AT ALBANY/FLOW-UNREG/01JAN2023/3HOUR/------R0/")
		ALBOFlowUR.setVersion("RFC 10-Day Unregulated")
		EUGOFlow = cwmsFile.read("//WILLAMETTE_AT EUGENE/FLOW/01JAN2023/3HOUR/------R0/")
		EUGOFlow.setVersion("RFC 10-Day Forecast")
		EUGOFlowUR = cwmsFile.read("//WILLAMETTE_AT EUGENE/FLOW-UNREG/01JAN2023/3HOUR/------R0/")
		EUGOFlowUR.setVersion("RFC 10-Day Unregulated")
		HAROFlow = cwmsFile.read("//WILLAMETTE_AT HARRISBURG/FLOW/01JAN2023/3HOUR/------R0/")
		HAROFlow.setVersion("RFC 10-Day Forecast")
		HAROFlowUR = cwmsFile.read("//WILLAMETTE_AT HARRISBURG/FLOW-UNREG/01JAN2023/3HOUR/------R0/")
		HAROFlowUR.setVersion("RFC 10-Day Unregulated")
		GOSOFlow = cwmsFile.read("//CF WILLAMETTE_NR GOSHEN/FLOW/01NOV2024/3HOUR/------R0/")
		GOSOFlow.setVersion("RFC 10-Day Forecast")
		GOSOFlowUR = cwmsFile.read("//CF WILLAMETTE_NR GOSHEN/FLOW-UNREG/01NOV2024/3HOUR/------R0/")
		GOSOFlowUR.setVersion("RFC 10-Day Unregulated")
		JASOFlow = cwmsFile.read("//MF WILLAMETTE_AT JASPER/FLOW/01NOV2024/3HOUR/------R0/")
		JASOFlow.setVersion("RFC 10-Day Forecast")
		JASOFlowUR = cwmsFile.read("//MF WILLAMETTE_AT JASPER/FLOW-UNREG/01NOV2024/3HOUR/------R0/")
		JASOFlowUR.setVersion("RFC 10-Day Unregulated")
		JFFOFlow = cwmsFile.read("//SANTIAM_AT JEFFERSON/FLOW/01NOV2024/3HOUR/------R0/")
		JFFOFlow.setVersion("RFC 10-Day Forecast")
		JFFOFlowUR = cwmsFile.read("//SANTIAM_AT JEFFERSON/FLOW-UNREG/01NOV2024/3HOUR/------R0/")
		JFFOFlowUR.setVersion("RFC 10-Day Unregulated")


		SALOFlow = SALOFlow.getData()
		ALBOFlow = ALBOFlow.getData()
		EUGOFlow = EUGOFlow.getData()
		HAROFlow = HAROFlow.getData()
		GOSOFlow = GOSOFlow.getData()
		JASOFlow = JASOFlow.getData()
		JFFOFlow = JFFOFlow.getData()
		SALOFlowUR = SALOFlowUR.getData()
		ALBOFlowUR = ALBOFlowUR.getData()
		EUGOFlowUR = EUGOFlowUR.getData()
		HAROFlowUR = HAROFlowUR.getData()
		GOSOFlowUR = GOSOFlowUR.getData()
		JASOFlowUR = JASOFlowUR.getData()
		JFFOFlowUR = JFFOFlowUR.getData()


        
### Create Plot ####
		LOP_Plot = Plot.newPlot("Look Out Point Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		#TopView.addCurve("Y1", MeridianHamptonBR)
		#TopView.addCurve("Y1", SignalPointBR)
		#TopView.addCurve("Y1", LOPSpillwayCrest)
		TopView.addCurve("Y1", OBSLOPElev)
		#TopView.addCurve("Y1", BlackCanyoneBR)
		TopView.addCurve("Y1", LOPRuleCurve)
		TopView.addCurve("Y1", LOPLBElev)
		#TopView.addCurve("Y1", LOPRuleCurveN)
        #TopView.addCurve("Y1", MeridianHamptonBR)    
		BottomView.addCurve("Y1", SimLOPInflow)
		BottomView.addCurve("Y1", SimLOPOutflow)
		#BottomView.addCurve("Y1", Sim25LOPOutflow)
		#BottomView.addCurve("Y1", Sim75LOPOutflow)
		LOP_Plot.configurePlotLayout(Layout)
		LOP_Plot.showPlot()    


		COT_Plot = Plot.newPlot("Cottage Grove Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSCOTElev)
		TopView.addCurve("Y1",COTRuleCurve)
		#TopView.addCurve("Y1", COTRuleCurveN)
		TopView.addCurve("Y1", COTLBElev)
		
		
		BottomView.addCurve("Y1", SimCOTInflow)
		BottomView.addCurve("Y1", SimCOTOutflow)
		COT_Plot.configurePlotLayout(Layout)
		COT_Plot.showPlot()
		
        
		HCR_Plot = Plot.newPlot("Hills Creek Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSHCRElev)

		TopView.addCurve("Y1", HCRRuleCurve)
		#TopView.addCurve("Y1", HCRRuleCurveN)

		TopView.addCurve("Y1", HCRLBElev)
		BottomView.addCurve("Y1", SimHCRInflow)

		BottomView.addCurve("Y1", SimHCROutflow)

		HCR_Plot.configurePlotLayout(Layout)
		HCR_Plot.showPlot()
        
       
		
		HCR_Plot = Plot.newPlot("Hills Creek Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSHCRElev)

		TopView.addCurve("Y1", HCRRuleCurve)
		#TopView.addCurve("Y1", HCRRuleCurveN)
		TopView.addCurve("Y1", HCRLBElev)
		
		BottomView.addCurve("Y1", SimHCRInflow)
		BottomView.addCurve("Y1", SimHCROutflow)
		HCR_Plot.configurePlotLayout(Layout)
		HCR_Plot.showPlot()
		
		
		BLR_Plot = Plot.newPlot("Blue River Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSBLRElev)
		TopView.addCurve("Y1",BLRRuleCurve)
		#TopView.addCurve("Y1", BLRRuleCurveN)
		TopView.addCurve("Y1",BLRLBElev)
		
		BottomView.addCurve("Y1", SimBLRInflow)
		BottomView.addCurve("Y1", SimBLROutflow)
		BLR_Plot.configurePlotLayout(Layout)
		BLR_Plot.showPlot()

		
		CGR_Plot = Plot.newPlot("Cougar Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSCGRElev)

		TopView.addCurve("Y1",CGRRuleCurve)
		#TopView.addCurve("Y1", CGRRuleCurveN)

		TopView.addCurve("Y1",CGRLBElev)

		
		BottomView.addCurve("Y1", SimCGRInflow)
		BottomView.addCurve("Y1", SimCGROutflow)
		CGR_Plot.configurePlotLayout(Layout)
		CGR_Plot.showPlot()		
		
		
		FAL_Plot = Plot.newPlot("Fall Creek Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSFALElev)
		TopView.addCurve("Y1",FALRuleCurve)
		#TopView.addCurve("Y1", FALRuleCurveN)
		TopView.addCurve("Y1",FALLBElev)
		
		BottomView.addCurve("Y1", SimFALInflow)
		BottomView.addCurve("Y1", SimFALOutflow)
		FAL_Plot.configurePlotLayout(Layout)
		FAL_Plot.showPlot()
		
		
		DOR_Plot = Plot.newPlot("Dorena Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSDORElev)
		TopView.addCurve("Y1",DORRuleCurve)
		#TopView.addCurve("Y1", DORRuleCurveN)
		TopView.addCurve("Y1", DORLBElev)
		BottomView.addCurve("Y1", SimDORInflow)
		BottomView.addCurve("Y1", SimDOROutflow)
		DOR_Plot.configurePlotLayout(Layout)
		DOR_Plot.showPlot()


		
		SALO_Plot = Plot.newPlot("Salem Flow Forecast")
		Layout = Plot.newPlotLayout()
		BottomView = Layout.addViewport(30)
		BottomView.addCurve("Y1", SALOFlow)
		BottomView.addCurve("Y1", SALOFlowUR)
		SALO_Plot.configurePlotLayout(Layout)
		SALO_Plot.showPlot()

		ALBO_Plot = Plot.newPlot("Albany Flow Forecast")
		Layout = Plot.newPlotLayout()
		BottomView = Layout.addViewport(30)
		BottomView.addCurve("Y1", ALBOFlow)
		BottomView.addCurve("Y1", ALBOFlowUR)
		ALBO_Plot.configurePlotLayout(Layout)
		ALBO_Plot.showPlot()
        
		EUGO_Plot = Plot.newPlot("Eugene Flow Forecast")
		Layout = Plot.newPlotLayout()
		BottomView = Layout.addViewport(30)
		BottomView.addCurve("Y1", EUGOFlow)
		BottomView.addCurve("Y1", EUGOFlowUR)
		EUGO_Plot.configurePlotLayout(Layout)
		EUGO_Plot.showPlot()

		HARO_Plot = Plot.newPlot("Harissburg Flow Forecast")
		Layout = Plot.newPlotLayout()
		BottomView = Layout.addViewport(30)
		BottomView.addCurve("Y1", HAROFlow)
		BottomView.addCurve("Y1", HAROFlowUR)
		HARO_Plot.configurePlotLayout(Layout)
		HARO_Plot.showPlot()



		JASO_Plot = Plot.newPlot("Jasper Flow Forecast")
		Layout = Plot.newPlotLayout()
		BottomView = Layout.addViewport(30)
		BottomView.addCurve("Y1", JASOFlow)
		BottomView.addCurve("Y1", JASOFlowUR)
		JASO_Plot.configurePlotLayout(Layout)
		JASO_Plot.showPlot()
        
		JFFO_Plot = Plot.newPlot("Jefferson Flow Forecast")
		Layout = Plot.newPlotLayout()
		BottomView = Layout.addViewport(30)
		BottomView.addCurve("Y1", JFFOFlow)
		BottomView.addCurve("Y1", JFFOFlowUR)
		JFFO_Plot.configurePlotLayout(Layout)
		JFFO_Plot.showPlot()

		GOSO_Plot = Plot.newPlot("Goshen Flow Forecast")
		Layout = Plot.newPlotLayout()
		BottomView = Layout.addViewport(30)
		BottomView.addCurve("Y1", GOSOFlow)
		BottomView.addCurve("Y1", GOSOFlowUR)
		GOSO_Plot.configurePlotLayout(Layout)
		GOSO_Plot.showPlot()













				
####### Plot Line Styles####
		

		OBSLOPElevCurve_50 = LOP_Plot.getCurve(OBSLOPElev)
		OBSLOPElevCurve_50.setLineWidth(6)
		OBSLOPElevCurve_50 = LOP_Plot.getCurve(OBSLOPElev)
		OBSLOPElevCurve_50.setLineColor("green")
		OBSLOPElevCurve_50.setLineStyle("solid")
		OBSLOPElevCurve_50.setLineWidth(3)

		'''		
		LOPRuleCurveNormal = LOP_Plot.getCurve(LOPRuleCurveN)
		LOPRuleCurveNormal.setLineWidth(3)
		LOPRuleCurveNormal = LOP_Plot.getCurve(LOPRuleCurveN)
		LOPRuleCurveNormal.setLineColor("Black")
		LOPRuleCurveNormal.setLineStyle("Solid")
		LOPRuleCurveNormal.setLineWidth(3)
		'''
		OBSLOPOUTFLOWCurve_50 = LOP_Plot.getCurve(SimLOPOutflow)
		OBSLOPOUTFLOWCurve_50.setLineWidth(3)
		OBSLOPOUTFLOWCurve_50 = LOP_Plot.getCurve(SimLOPOutflow)
		OBSLOPOUTFLOWCurve_50.setLineColor("darkgreen")
		OBSLOPOUTFLOWCurve_50.setLineStyle("dash")
		OBSLOPOUTFLOWCurve_50.setLineWidth(3)


		LOPRuleCurveEIS = LOP_Plot.getCurve(LOPRuleCurve)
		LOPRuleCurveEIS.setLineWidth(3)
		LOPRuleCurveEIS = LOP_Plot.getCurve(LOPRuleCurve)
		LOPRuleCurveEIS.setLineColor("black")
		LOPRuleCurveEIS.setLineStyle("dash")

		OBSLOPINFLOWCurve_50 = LOP_Plot.getCurve(SimLOPInflow)
		OBSLOPINFLOWCurve_50.setLineWidth(3)
		OBSLOPINFLOWCurve_50 = LOP_Plot.getCurve(SimLOPInflow)
		OBSLOPINFLOWCurve_50.setLineColor("green")
		OBSLOPINFLOWCurve_50.setLineStyle("solid")
		OBSLOPINFLOWCurve_50.setLineWidth(3)
		

		
		LOPLBElev2 = LOP_Plot.getCurve(LOPLBElev)
		LOPLBElev2.setLineWidth(5)
		LOPLBElev2 = LOP_Plot.getCurve(LOPLBElev)
		LOPLBElev2.setLineColor("darkmagenta")
		LOPLBElev2.setLineStyle("solid")
        

		############### HCR below


		OBSHCRElevCurve_50 = HCR_Plot.getCurve(OBSHCRElev)
		OBSHCRElevCurve_50.setLineWidth(6)
		OBSHCRElevCurve_50 = HCR_Plot.getCurve(OBSHCRElev)
		OBSHCRElevCurve_50.setLineColor("green")
		OBSHCRElevCurve_50.setLineStyle("solid")
		OBSHCRElevCurve_50.setLineWidth(3)

		'''		
		HCRRuleCurveNormal = HCR_Plot.getCurve(HCRRuleCurveN)
		HCRRuleCurveNormal.setLineWidth(3)
		HCRRuleCurveNormal = HCR_Plot.getCurve(HCRRuleCurveN)
		HCRRuleCurveNormal.setLineColor("Black")
		HCRRuleCurveNormal.setLineStyle("Solid")
		HCRRuleCurveNormal.setLineWidth(3)
	    '''		
		OBSHCROUTFLOWCurve_50 = HCR_Plot.getCurve(SimHCROutflow)
		OBSHCROUTFLOWCurve_50.setLineWidth(3)
		OBSHCROUTFLOWCurve_50 = HCR_Plot.getCurve(SimHCROutflow)
		OBSHCROUTFLOWCurve_50.setLineColor("darkgreen")
		OBSHCROUTFLOWCurve_50.setLineStyle("dash")
		OBSHCROUTFLOWCurve_50.setLineWidth(3)

		HCRRuleCurveEIS = HCR_Plot.getCurve(HCRRuleCurve)
		HCRRuleCurveEIS.setLineWidth(6)
		HCRRuleCurveEIS = HCR_Plot.getCurve(HCRRuleCurve)
		HCRRuleCurveEIS.setLineColor("black")
		HCRRuleCurveEIS.setLineStyle("dash")
		

		OBSHCRINFLOWCurve_50 = HCR_Plot.getCurve(SimHCRInflow)
		OBSHCRINFLOWCurve_50.setLineWidth(3)
		OBSHCRINFLOWCurve_50 = HCR_Plot.getCurve(SimHCRInflow)
		OBSHCRINFLOWCurve_50.setLineColor("green")
		OBSHCRINFLOWCurve_50.setLineStyle("solid")
		OBSHCRINFLOWCurve_50.setLineWidth(3)
		

		HCRLBElev2 = HCR_Plot.getCurve(HCRLBElev)
		HCRLBElev2.setLineWidth(5)
		HCRLBElev2 = HCR_Plot.getCurve(HCRLBElev)
		HCRLBElev2.setLineColor("darkmagenta")
		HCRLBElev2.setLineStyle("solid")
		HCRLBElev2.setLineWidth(5)

		

		
		
						############### FAL below
		


		OBSFALElevCurve_50 = FAL_Plot.getCurve(OBSFALElev)
		OBSFALElevCurve_50.setLineWidth(6)
		OBSFALElevCurve_50 = FAL_Plot.getCurve(OBSFALElev)
		OBSFALElevCurve_50.setLineColor("green")
		OBSFALElevCurve_50.setLineStyle("solid")
		OBSFALElevCurve_50.setLineWidth(3)

		'''
		FALRuleCurveNormal = FAL_Plot.getCurve(FALRuleCurveN)
		FALRuleCurveNormal.setLineWidth(3)
		FALRuleCurveNormal = FAL_Plot.getCurve(FALRuleCurveN)
		FALRuleCurveNormal.setLineColor("black")
		FALRuleCurveNormal.setLineStyle("Solid")
		FALRuleCurveNormal.setLineWidth(3)
        
        '''		

		OBSFALOUTFLOWCurve_50 = FAL_Plot.getCurve(SimFALOutflow)
		OBSFALOUTFLOWCurve_50.setLineWidth(3)
		OBSFALOUTFLOWCurve_50 = FAL_Plot.getCurve(SimFALOutflow)
		OBSFALOUTFLOWCurve_50.setLineColor("darkgreen")
		OBSFALOUTFLOWCurve_50.setLineStyle("dash")
		OBSFALOUTFLOWCurve_50.setLineWidth(3)


		FALRuleCurveEIS = FAL_Plot.getCurve(FALRuleCurve)
		FALRuleCurveEIS.setLineWidth(6)
		FALRuleCurveEIS = FAL_Plot.getCurve(FALRuleCurve)
		FALRuleCurveEIS.setLineColor("black")
		FALRuleCurveEIS.setLineStyle("dash")
		FALRuleCurveEIS.setLineWidth(3)
		

		OBSFALINFLOWCurve_50 = FAL_Plot.getCurve(SimFALInflow)
		OBSFALINFLOWCurve_50.setLineWidth(3)
		OBSFALINFLOWCurve_50 = FAL_Plot.getCurve(SimFALInflow)
		OBSFALINFLOWCurve_50.setLineColor("green")
		OBSFALINFLOWCurve_50.setLineStyle("solid")
		OBSFALINFLOWCurve_50.setLineWidth(3)
		

		
		FALLBElev2 = FAL_Plot.getCurve(FALLBElev)
		FALLBElev2.setLineWidth(5)
		FALLBElev2 = FAL_Plot.getCurve(FALLBElev)
		FALLBElev2.setLineColor("darkmagenta")
		FALLBElev2.setLineStyle("solid")
		FALLBElev2.setLineWidth(5)
		

		
		
						############### CGR below

		
		OBSCGRElevCurve_50 = CGR_Plot.getCurve(OBSCGRElev)
		OBSCGRElevCurve_50.setLineWidth(6)
		OBSCGRElevCurve_50 = CGR_Plot.getCurve(OBSCGRElev)
		OBSCGRElevCurve_50.setLineColor("green")
		OBSCGRElevCurve_50.setLineStyle("solid")
		OBSCGRElevCurve_50.setLineWidth(3)

		'''
		CGRRuleCurveNormal = CGR_Plot.getCurve(CGRRuleCurveN)
		CGRRuleCurveNormal.setLineWidth(5)
		CGRRuleCurveNormal = CGR_Plot.getCurve(CGRRuleCurveN)
		CGRRuleCurveNormal.setLineColor("Black")
		CGRRuleCurveNormal.setLineStyle("Solid")
		CGRRuleCurveNormal.setLineWidth(5)
		'''

		OBSCGROUTFLOWCurve_50 = CGR_Plot.getCurve(SimCGROutflow)
		OBSCGROUTFLOWCurve_50.setLineWidth(3)
		OBSCGROUTFLOWCurve_50 = CGR_Plot.getCurve(SimCGROutflow)
		OBSCGROUTFLOWCurve_50.setLineColor("darkgreen")
		OBSCGROUTFLOWCurve_50.setLineStyle("dash")
		OBSCGROUTFLOWCurve_50.setLineWidth(3)

		CGRRuleCurveEIS = CGR_Plot.getCurve(CGRRuleCurve)
		CGRRuleCurveEIS.setLineWidth(3)
		CGRRuleCurveEIS = CGR_Plot.getCurve(CGRRuleCurve)
		CGRRuleCurveEIS.setLineColor("black")
		CGRRuleCurveEIS.setLineStyle("dash")
		

		OBSCGRINFLOWCurve_50 = CGR_Plot.getCurve(SimCGRInflow)
		OBSCGRINFLOWCurve_50.setLineWidth(3)
		OBSCGRINFLOWCurve_50 = CGR_Plot.getCurve(SimCGRInflow)
		OBSCGRINFLOWCurve_50.setLineColor("green")
		OBSCGRINFLOWCurve_50.setLineStyle("solid")
		
		CGRLBElev2 = CGR_Plot.getCurve(CGRLBElev)
		CGRLBElev2.setLineWidth(5)
		CGRLBElev2 = CGR_Plot.getCurve(CGRLBElev)
		CGRLBElev2.setLineColor("darkmagenta")
		CGRLBElev2.setLineStyle("solid")
		
		
				############### BLR below
		

		OBSBLRElevCurve_50 = BLR_Plot.getCurve(OBSBLRElev)
		OBSBLRElevCurve_50.setLineWidth(6)
		OBSBLRElevCurve_50 = BLR_Plot.getCurve(OBSBLRElev)
		OBSBLRElevCurve_50.setLineColor("green")
		OBSBLRElevCurve_50.setLineStyle("solid")
		OBSBLRElevCurve_50.setLineWidth(3)

		'''		
		BLRRuleCurveNormal = BLR_Plot.getCurve(BLRRuleCurveN)
		BLRRuleCurveNormal.setLineWidth(3)
		BLRRuleCurveNormal = BLR_Plot.getCurve(BLRRuleCurveN)
		BLRRuleCurveNormal.setLineColor("black")
		BLRRuleCurveNormal.setLineStyle("Solid")
		BLRRuleCurveNormal.setLineWidth(3)
		'''

		OBSBLROUTFLOWCurve_50 = BLR_Plot.getCurve(SimBLROutflow)
		OBSBLROUTFLOWCurve_50.setLineWidth(3)
		OBSBLROUTFLOWCurve_50 = BLR_Plot.getCurve(SimBLROutflow)
		OBSBLROUTFLOWCurve_50.setLineColor("darkgreen")
		OBSBLROUTFLOWCurve_50.setLineStyle("dash")
		OBSBLROUTFLOWCurve_50.setLineWidth(3)

		
		BLRRuleCurveEIS = BLR_Plot.getCurve(BLRRuleCurve)
		BLRRuleCurveEIS.setLineWidth(6)
		BLRRuleCurveEIS = BLR_Plot.getCurve(BLRRuleCurve)
		BLRRuleCurveEIS.setLineColor("black")
		BLRRuleCurveEIS.setLineStyle("dash")
		BLRRuleCurveEIS.setLineWidth(3)
		
		OBSBLRINFLOWCurve_50 = BLR_Plot.getCurve(SimBLRInflow)
		OBSBLRINFLOWCurve_50.setLineWidth(3)
		OBSBLRINFLOWCurve_50 = BLR_Plot.getCurve(SimBLRInflow)
		OBSBLRINFLOWCurve_50.setLineColor("green")
		OBSBLRINFLOWCurve_50.setLineStyle("solid")
		OBSBLRINFLOWCurve_50.setLineWidth(3)
		

		BLRLBELEV2 = BLR_Plot.getCurve(BLRLBElev)
		BLRLBELEV2.setLineWidth(3)
		BLRLBELEV2.setLineColor("darkmagenta")
		BLRLBELEV2.setLineStyle("solid")
		
				############### DOR below


		OBSDORElevCurve_50 = DOR_Plot.getCurve(OBSDORElev)
		OBSDORElevCurve_50.setLineWidth(6)
		OBSDORElevCurve_50 = DOR_Plot.getCurve(OBSDORElev)
		OBSDORElevCurve_50.setLineColor("green")
		OBSDORElevCurve_50.setLineStyle("solid")
		OBSDORElevCurve_50.setLineWidth(3)

		'''		
		DORRuleCurveNormal = DOR_Plot.getCurve(DORRuleCurveN)
		DORRuleCurveNormal.setLineWidth(3)
		DORRuleCurveNormal = DOR_Plot.getCurve(DORRuleCurveN)
		DORRuleCurveNormal.setLineColor("black")
		DORRuleCurveNormal.setLineStyle("Solid")
		DORRuleCurveNormal.setLineWidth(3)
		'''		

		OBSDOROUTFLOWCurve_50 = DOR_Plot.getCurve(SimDOROutflow)
		OBSDOROUTFLOWCurve_50.setLineWidth(3)
		OBSDOROUTFLOWCurve_50 = DOR_Plot.getCurve(SimDOROutflow)
		OBSDOROUTFLOWCurve_50.setLineColor("darkgreen")
		OBSDOROUTFLOWCurve_50.setLineStyle("dash")
		OBSDOROUTFLOWCurve_50.setLineWidth(3)

		
		DORRuleCurveEIS = DOR_Plot.getCurve(DORRuleCurve)
		DORRuleCurveEIS.setLineWidth(6)
		DORRuleCurveEIS = DOR_Plot.getCurve(DORRuleCurve)
		DORRuleCurveEIS.setLineColor("black")
		DORRuleCurveEIS.setLineStyle("dash")
		DORRuleCurveEIS.setLineWidth(3)
		

		OBSDORINFLOWCurve_50 = DOR_Plot.getCurve(SimDORInflow)
		OBSDORINFLOWCurve_50.setLineWidth(3)
		OBSDORINFLOWCurve_50 = DOR_Plot.getCurve(SimDORInflow)
		OBSDORINFLOWCurve_50.setLineColor("green")
		OBSDORINFLOWCurve_50.setLineStyle("solid")
		OBSDORINFLOWCurve_50.setLineWidth(3)
		

		DORLBElev2 = DOR_Plot.getCurve(DORLBElev)
		DORLBElev2.setLineWidth(5)
		DORLBElev2.setLineColor("darkmagenta")
		DORLBElev2.setLineStyle("solid")
	
						############### COT below


		OBSCOTElevCurve_50 = COT_Plot.getCurve(OBSCOTElev)
		OBSCOTElevCurve_50.setLineWidth(6)
		OBSCOTElevCurve_50 = COT_Plot.getCurve(OBSCOTElev)
		OBSCOTElevCurve_50.setLineColor("green")
		OBSCOTElevCurve_50.setLineStyle("solid")
		OBSCOTElevCurve_50.setLineWidth(3)


		
		#COTRuleCurveNormal = COT_Plot.getCurve(COTRuleCurveN)

		

		OBSCOTOUTFLOWCurve_50 = COT_Plot.getCurve(SimCOTOutflow)
		OBSCOTOUTFLOWCurve_50.setLineWidth(3)
		OBSCOTOUTFLOWCurve_50 = COT_Plot.getCurve(SimCOTOutflow)
		OBSCOTOUTFLOWCurve_50.setLineColor("darkgreen")
		OBSCOTOUTFLOWCurve_50.setLineStyle("dash")
		OBSCOTOUTFLOWCurve_50.setLineWidth(3)

		
		COTRuleCurveEIS = COT_Plot.getCurve(COTRuleCurve)
		COTRuleCurveEIS.setLineWidth(3)
		COTRuleCurveEIS = COT_Plot.getCurve(COTRuleCurve)
		COTRuleCurveEIS.setLineColor("black")
		COTRuleCurveEIS.setLineStyle("dash")
		COTRuleCurveEIS.setLineWidth(3)
		
		OBSCOTINFLOWCurve_50 = COT_Plot.getCurve(SimCOTInflow)
		OBSCOTINFLOWCurve_50.setLineWidth(3)
		OBSCOTINFLOWCurve_50.setLineColor("green")
		OBSCOTINFLOWCurve_50.setLineStyle("solid")
	

		OCOTLBELEV2 = COT_Plot.getCurve(COTLBElev)
		OCOTLBELEV2.setLineWidth(3)
		OCOTLBELEV2.setLineColor("darkmagenta")
		OCOTLBELEV2.setLineStyle("solid")

        
		##### Albany below


		
		ALBOFlow_50 = ALBO_Plot.getCurve(ALBOFlow)
		ALBOFlow_50.setLineWidth(3)
		ALBOFlow_50 = ALBO_Plot.getCurve(ALBOFlow)
		ALBOFlow_50.setLineColor("blue")
		ALBOFlow_50.setLineStyle("solid")
		ALBOFlow_50.setLineWidth(3)


		######SALEM BELOW


		
		SALEMFlow_50 = SALO_Plot.getCurve(SALOFlow)
		SALEMFlow_50.setLineWidth(3)
		SALEMFlow_50 = SALO_Plot.getCurve(SALOFlow)
		SALEMFlow_50.setLineColor("blue")
		SALEMFlow_50.setLineStyle("solid")
		SALEMFlow_50.setLineWidth(3)


		
		EUGENEFlow_50 = EUGO_Plot.getCurve(EUGOFlow)
		EUGENEFlow_50.setLineWidth(3)
		EUGENEFlow_50 = EUGO_Plot.getCurve(EUGOFlow)
		EUGENEFlow_50.setLineColor("blue")
		EUGENEFlow_50.setLineStyle("solid")
		EUGENEFlow_50.setLineWidth(3)


        
		HARRISBURGFlow_50 = HARO_Plot.getCurve(HAROFlow)
		HARRISBURGFlow_50.setLineWidth(3)
		HARRISBURGFlow_50 = HARO_Plot.getCurve(HAROFlow)
		HARRISBURGFlow_50.setLineColor("blue")
		HARRISBURGFlow_50.setLineStyle("solid")
		HARRISBURGFlow_50.setLineWidth(3)



		GoshenFlow = GOSO_Plot.getCurve(GOSOFlow)
		GoshenFlow.setLineWidth(3)
		GoshenFlow = GOSO_Plot.getCurve(GOSOFlow)
		GoshenFlow.setLineColor("blue")
		GoshenFlow.setLineStyle("solid")
		GoshenFlow.setLineWidth(3)


		
		JASPERFlow = JASO_Plot.getCurve(JASOFlow)
		JASPERFlow.setLineWidth(3)
		JASPERFlow = JASO_Plot.getCurve(JASOFlow)
		JASPERFlow.setLineColor("blue")
		JASPERFlow.setLineStyle("solid")
		JASPERFlow.setLineWidth(3)


        
		JeffersonFlow = JFFO_Plot.getCurve(JFFOFlow)
		JeffersonFlow.setLineWidth(3)
		JeffersonFlow = JFFO_Plot.getCurve(JFFOFlow)
		JeffersonFlow.setLineColor("blue")
		JeffersonFlow.setLineStyle("solid")
		JeffersonFlow.setLineWidth(3)


     
#####Axis Formating####
		TopViewport_CGR = CGR_Plot.getViewport(0)
		BottomViewport_CGR = CGR_Plot.getViewport(1)
		Top_Y_Axis = TopViewport_CGR.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport_CGR.getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_CGR.getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("Pool Elevation")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)
		Bottom_Y_Axis = BottomViewport_CGR.getAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport_CGR.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_CGR.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(250)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)
		
		
		CGR_SW = AxisMarker()
		CGR_SW.axis = "Y"
		CGR_SW.value = "1656.75"
		CGR_SW.labelText = "CGR Spillway ~ 1656.75"
		CGR_SW.labelPosition = "above"
		CGR_SW.labelColor = "Purple"
		CGR_SW.labelFont = "Dialog,BOLD,14";
		CGR_SW.lineColor = "Purple"
		CGR_SW.lineStyle = "dot"
		CGR_SW.lineWidth = 4
		TopViewport_CGR.addAxisMarker(CGR_SW)	
	


		
		TopViewport_LOP = LOP_Plot.getViewport(0)
		BottomViewport_LOP = LOP_Plot.getViewport(1)
		Top_Y_Axis = TopViewport_LOP.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport_LOP .getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_LOP .getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("Pool Elevation")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(14, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)
		Bottom_Y_Axis = BottomViewport_LOP .getAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport_LOP .getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_LOP .getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)
        
		LOP_SW = AxisMarker()
		LOP_SW.axis = "Y"
		LOP_SW.value = "887.5"
		LOP_SW.labelText = "LOP Spillway ~ 887.5"
		LOP_SW.labelPosition = "above"
		LOP_SW.labelColor = "Purple"
		LOP_SW.labelFont = "Dialog,BOLD,14";
		LOP_SW.lineColor = "purple"
		LOP_SW.lineStyle = "dot"
		LOP_SW.lineWidth = 4
		TopViewport_LOP.addAxisMarker(LOP_SW)
         
        
		TopViewport_HCR = HCR_Plot.getViewport(0)
		BottomViewport_HCR = HCR_Plot.getViewport(1)
		Top_Y_Axis = TopViewport_HCR.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport_HCR.getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_HCR.getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("Pool Elevation")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(14, 14, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)
		Bottom_Y_Axis = BottomViewport_HCR.getAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport_HCR.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_HCR.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)
        
        
        
		HCRSW = AxisMarker()
		HCRSW.axis = "Y"
		HCRSW.value = "1495.5"
		HCRSW.labelText = "HCR Spillway ~ 1495.5"
		HCRSW.labelPosition = "above"
		HCRSW.labelColor = "purple"
		HCRSW.labelFont = "Dialog,BOLD,14";
		HCRSW.lineColor = "purple"
		HCRSW.lineStyle = "dot"
		HCRSW.lineWidth = 4
		TopViewport_HCR.addAxisMarker(HCRSW)

		
		TopViewport_FAL = FAL_Plot.getViewport(0)
		BottomViewport_FAL = FAL_Plot.getViewport(1)
		Top_Y_Axis = TopViewport_FAL.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport_FAL.getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_FAL.getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("Pool Elevation")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)
		Bottom_Y_Axis = BottomViewport_FAL.getAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport_FAL.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_FAL.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)

		FALSW = AxisMarker()
		FALSW.axis = "Y"
		FALSW.value = "791.6"
		FALSW.labelText = "FAL Spillway ~ 791.6"
		FALSW.labelPosition = "above"
		FALSW.labelColor = "purple"
		FALSW.labelFont = "Dialog,BOLD,14";
		FALSW.lineColor = "purple"
		FALSW.lineStyle = "dot"
		FALSW.lineWidth = 4
		TopViewport_FAL.addAxisMarker(FALSW)        

		TopViewport_BLR = BLR_Plot.getViewport(0)
		BottomViewport_BLR = BLR_Plot.getViewport(1)
		Top_Y_Axis = TopViewport_BLR.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport_BLR.getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_BLR.getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("Pool Elevation")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)
		Bottom_Y_Axis = BottomViewport_BLR.getAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport_BLR.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_BLR.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)

		BLRSW = AxisMarker()
		BLRSW.axis = "Y"
		BLRSW.value = "1321"
		BLRSW.labelText = "BLR Spillway ~ 1321"
		BLRSW.labelPosition = "above"
		BLRSW.labelColor = "purple"
		BLRSW.labelFont = "Dialog,BOLD,14";
		BLRSW.lineColor = "purple"
		BLRSW.lineStyle = "dot"
		BLRSW.lineWidth = 4
		TopViewport_BLR.addAxisMarker(BLRSW)        
        

		TopViewport_DOR = DOR_Plot.getViewport(0)
		BottomViewport_DOR = DOR_Plot.getViewport(1)
		Top_Y_Axis = TopViewport_DOR.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport_DOR.getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_DOR.getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("Pool Elevation")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)
		Bottom_Y_Axis = BottomViewport_DOR.getAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport_DOR.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_DOR.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)

        

		TopViewport_COT = COT_Plot.getViewport(0)
		BottomViewport_COT = COT_Plot.getViewport(1)
		Top_Y_Axis = TopViewport_COT.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport_COT.getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_COT.getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("Pool Elevation")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)
		Bottom_Y_AxisLabel = BottomViewport_COT.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_COT.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)



		BottomViewport_SALO = SALO_Plot.getViewport(0)
		Bottom_Y_AxisLabel = BottomViewport_SALO.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_SALO.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)

		SALOBF = AxisMarker()
		SALOBF.axis = "Y"
		SALOBF.value = "94000"
		SALOBF.labelText = "Bank Full ~ 94000"
		SALOBF.labelPosition = "above"
		SALOBF.labelColor = "purple"
		SALOBF.labelFont = "Dialog,BOLD,14";
		SALOBF.lineColor = "purple"
		SALOBF.lineStyle = "dot"
		SALOBF.lineWidth = 4
		BottomViewport_SALO.addAxisMarker(SALOBF)   

		BottomViewport_ALBO = ALBO_Plot.getViewport(0)
		Bottom_Y_AxisLabel = BottomViewport_ALBO.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_ALBO.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)

		ALBOBF = AxisMarker()
		ALBOBF.axis = "Y"
		ALBOBF.value = "68586"
		ALBOBF.labelText = "Bank Full ~ 68586"
		ALBOBF.labelPosition = "above"
		ALBOBF.labelColor = "purple"
		ALBOBF.labelFont = "Dialog,BOLD,14";
		ALBOBF.lineColor = "purple"
		ALBOBF.lineStyle = "dot"
		ALBOBF.lineWidth = 4
		BottomViewport_ALBO.addAxisMarker(ALBOBF) 
		
		BottomViewport_HARO = HARO_Plot.getViewport(0)
		Bottom_Y_AxisLabel = BottomViewport_HARO.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_HARO.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)

		HAROBF = AxisMarker()
		HAROBF.axis = "Y"
		HAROBF.value = "37864"
		HAROBF.labelText = "Bank Full ~ 37864"
		HAROBF.labelPosition = "above"
		HAROBF.labelColor = "purple"
		HAROBF.labelFont = "Dialog,BOLD,14";
		HAROBF.lineColor = "purple"
		HAROBF.lineStyle = "dot"
		HAROBF.lineWidth = 4
		BottomViewport_HARO.addAxisMarker(ALBOBF)   
		
		BottomViewport_JASO = JASO_Plot.getViewport(0)
		Bottom_Y_AxisLabel = BottomViewport_JASO.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_JASO.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)

		JASOBF = AxisMarker()
		JASOBF.axis = "Y"
		JASOBF.value = "19473"
		JASOBF.labelText = "Bank Full ~ 19473"
		JASOBF.labelPosition = "above"
		JASOBF.labelColor = "purple"
		JASOBF.labelFont = "Dialog,BOLD,14";
		JASOBF.lineColor = "purple"
		JASOBF.lineStyle = "dot"
		JASOBF.lineWidth = 4
		BottomViewport_JASO.addAxisMarker(JASOBF)    
		
		BottomViewport_JFFO = JFFO_Plot.getViewport(0)
		Bottom_Y_AxisLabel = BottomViewport_JFFO.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_JFFO.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)

		JFFOBF = AxisMarker()
		JFFOBF.axis = "Y"
		JFFOBF.value = "40317"
		JFFOBF.labelText = "Bank Full ~ 40317"
		JFFOBF.labelPosition = "above"
		JFFOBF.labelColor = "purple"
		JFFOBF.labelFont = "Dialog,BOLD,14";
		JFFOBF.lineColor = "purple"
		JFFOBF.lineStyle = "dot"
		JFFOBF.lineWidth = 4
		BottomViewport_JFFO.addAxisMarker(JFFOBF)   

		BottomViewport_GOSO = GOSO_Plot.getViewport(0)
		Bottom_Y_AxisLabel = BottomViewport_GOSO.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_GOSO.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)

		GOSOBF = AxisMarker()
		GOSOBF.axis = "Y"
		GOSOBF.value = "12340"
		GOSOBF.labelText = "Bank Full ~ 12340"
		GOSOBF.labelPosition = "above"
		GOSOBF.labelColor = "purple"
		GOSOBF.labelFont = "Dialog,BOLD,14";
		GOSOBF.lineColor = "purple"
		GOSOBF.lineStyle = "dot"
		GOSOBF.lineWidth = 4
		BottomViewport_GOSO.addAxisMarker(GOSOBF)   
		
		BottomViewport_EUGO = EUGO_Plot.getViewport(0)
		Bottom_Y_AxisLabel = BottomViewport_EUGO.getAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_EUGO.getAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.getProperties()
		BottomTicProps.setMajorTicFontStyle(1)

		EUGOBF = AxisMarker()
		EUGOBF.axis = "Y"
		EUGOBF.value = "39500"
		EUGOBF.labelText = "Bank Full ~ 39500"
		EUGOBF.labelPosition = "above"
		EUGOBF.labelColor = "purple"
		EUGOBF.labelFont = "Dialog,BOLD,14";
		EUGOBF.lineColor = "purple"
		EUGOBF.lineStyle = "dot"
		EUGOBF.lineWidth = 4
		BottomViewport_EUGO.addAxisMarker(EUGOBF)   

        
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
        
        
		TopViewport_ALBO = ALBO_Plot.getViewport(0)        
		TopViewport_SALO = SALO_Plot.getViewport(0)        
		TopViewport_HARO = HARO_Plot.getViewport(0)        
		TopViewport_EUGO = EUGO_Plot.getViewport(0)        
		TopViewport_JFFO = JFFO_Plot.getViewport(0)	
		TopViewport_JASO = JASO_Plot.getViewport(0)			
		
		        
		TopViewport_LOP.addAxisMarker(CurrentTime)                    
		BottomViewport_LOP.addAxisMarker(CurrentTime) 		
		TopViewport_HCR.addAxisMarker(CurrentTime)                    
		BottomViewport_HCR.addAxisMarker(CurrentTime)
		TopViewport_FAL.addAxisMarker(CurrentTime)                    
		BottomViewport_FAL.addAxisMarker(CurrentTime) 		
		TopViewport_CGR.addAxisMarker(CurrentTime)                    
		BottomViewport_CGR.addAxisMarker(CurrentTime) 
		TopViewport_BLR.addAxisMarker(CurrentTime)                    
		BottomViewport_BLR.addAxisMarker(CurrentTime) 
		TopViewport_DOR.addAxisMarker(CurrentTime)                    
		BottomViewport_DOR.addAxisMarker(CurrentTime) 
		TopViewport_COT.addAxisMarker(CurrentTime)                    
		BottomViewport_COT.addAxisMarker(CurrentTime)
		TopViewport_ALBO.addAxisMarker(CurrentTime)         
		TopViewport_SALO.addAxisMarker(CurrentTime)           
		TopViewport_HARO.addAxisMarker(CurrentTime)   
		TopViewport_EUGO.addAxisMarker(CurrentTime)
		TopViewport_JFFO.addAxisMarker(CurrentTime)
		#TopViewport_MNRO.addAxisMarker(CurrentTime)
		#TopViewport_MEHO.addAxisMarker(CurrentTime)   
		TopViewport_JASO.addAxisMarker(CurrentTime)
        
###### Save Plot as A jpeg####


		LOP_Plot.setSize(1400, 1300)
		LOP_Plot.setLocation(100, 100)
		LOP_Plot.saveToJpeg("F:\LOP_FcstPlot.jpg")
		LOP_Plot.close()
		
		
		HCR_Plot.setSize(1400, 1300)
		HCR_Plot.setLocation(100, 100)
		HCR_Plot.saveToJpeg("F:\HCR_FcstPlot.jpg")
		HCR_Plot.close()
		

		FAL_Plot.setSize(1400, 1300)
		FAL_Plot.setLocation(100, 100)
		FAL_Plot.saveToJpeg("F:\FAL_FcstPlot.jpg")
		FAL_Plot.close()
		
		DOR_Plot.setSize(1400, 1300)
		DOR_Plot.setLocation(100, 100)
		DOR_Plot.saveToJpeg("F:\DOR_FcstPlot.jpg")
		DOR_Plot.close()

		COT_Plot.setSize(1400, 1300)
		COT_Plot.setLocation(100, 100)
		COT_Plot.saveToJpeg("F:\COT_FcstPlot.jpg")
		COT_Plot.close()
				
		BLR_Plot.setSize(1400, 1300)
		BLR_Plot.setLocation(100, 100)
		BLR_Plot.saveToJpeg("F:\BLR_FcstPlot.jpg")
		BLR_Plot.close()
			
		CGR_Plot.setSize(1400, 1300)
		CGR_Plot.setLocation(100, 100)
		CGR_Plot.saveToJpeg("F:\CGR_FcstPlot.jpg")
		CGR_Plot.close()
		
		SALO_Plot.setSize(1400, 1300)
		SALO_Plot.setLocation(100, 100)
		SALO_Plot.saveToJpeg("F:\SALO_FcstPlot.jpg")
		SALO_Plot.close()	

		ALBO_Plot.setSize(1400, 1300)
		ALBO_Plot.setLocation(100, 100)
		ALBO_Plot.saveToJpeg("F:\ALBO_FcstPlot.jpg")
		ALBO_Plot.close()
        
		EUGO_Plot.setSize(1400, 1300)
		EUGO_Plot.setLocation(100, 100)
		EUGO_Plot.saveToJpeg("F:\EUGO_FcstPlot.jpg")
		EUGO_Plot.close()	     
        
		HARO_Plot.setSize(1400, 1300)
		HARO_Plot.setLocation(100, 100)
		HARO_Plot.saveToJpeg("F:\HARO_FcstPlot.jpg")
		HARO_Plot.close()

		JFFO_Plot.setSize(1400, 1300)
		JFFO_Plot.setLocation(100, 100)
		JFFO_Plot.saveToJpeg("F:\JFFO_FcstPlot.jpg")
		JFFO_Plot.close()

		JASO_Plot.setSize(1400, 1300)
		JASO_Plot.setLocation(100, 100)
		JASO_Plot.saveToJpeg("F:\JASO_FcstPlot.jpg")
		JASO_Plot.close()

		GOSO_Plot.setSize(1400, 1300)
		GOSO_Plot.setLocation(100, 100)
		GOSO_Plot.saveToJpeg("F:\GOSO_FcstPlot.jpg")
		GOSO_Plot.close()


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
