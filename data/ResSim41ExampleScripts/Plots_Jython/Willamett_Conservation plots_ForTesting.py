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
from hec.script             import renameRecords

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
		HCRLBElev = cwmsFile.get("/WILLAMETTE/HILLS CREEK/ELEV(29)/01DEC2022/1HOUR/OBSERVED/")
		OBS25HCRElev = cwmsFile.get("//HILLS CREEK-POOL/ELEV/01JAN2023/1DAY/25% Flow Forecast/")
		Sim25HCRInflow = cwmsFile.get("//HILLS CREEK-POOL/FLOW-IN/01JAN2023/1DAY/25% Flow Forecast/")
		Sim25HCROutflow = cwmsFile.get("//HILLS CREEK-POOL/FLOW-OUT/01JAN2023/1DAY/25% Flow Forecast/")
		HCR25RuleCurve = cwmsFile.get("//HILLS CREEK-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/25% Flow Forecast/")
		HCRRuleCurveN = cwmsFile.get("//HCR/ELEV-RULECURVE/01OCT2023/IR-MONTH/CENWP-CALC/")
		
		OBSHCRElev = cwmsFile.get("//HILLS CREEK-POOL/ELEV/01JAN2023/1DAY/50% Flow Forecast/")
		SimHCRInflow = cwmsFile.get("//HILLS CREEK-POOL/FLOW-IN/01JAN2023/1DAY/50% Flow Forecast/")
		SimHCROutflow = cwmsFile.get("//HILLS CREEK-POOL/FLOW-OUT/01JAN2023/1DAY/50% Flow Forecast/")
		HCRRuleCurve = cwmsFile.get("//HILLS CREEK-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/50% Flow Forecast/")
		HCRRuleCurveN = cwmsFile.get("//HCR/ELEV-RULECURVE/01OCT2023/IR-MONTH/CENWP-CALC/")
		
		OBS75HCRElev = cwmsFile.get("//HILLS CREEK-POOL/ELEV/01JAN2023/1DAY/75% Flow Forecast/")
		Sim75HCRInflow = cwmsFile.get("//HILLS CREEK-POOL/FLOW-IN/01JAN2023/1DAY/75% Flow Forecast/")
		Sim75HCROutflow = cwmsFile.get("//HILLS CREEK-POOL/FLOW-OUT/01JAN2023/1DAY/75% Flow Forecast/")
		HCRRuleCurve = cwmsFile.get("//HILLS CREEK-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/75% Flow Forecast/")
		HCRRuleCurveN = cwmsFile.get("//HCR/ELEV-RULECURVE/01OCT2023/IR-MONTH/CENWP-CALC/")
		
		HCRSW = cwmsFile.get("//HILLS CREEK-SPILLWAY CREST/ELEV-ZONE/01JAN2023/1DAY/20/")
		PackardBR = cwmsFile.get("//HILLS CREEK-PACKARD/ELEV-ZONE/01JAN2023/1DAY/20/")
		BinghamBR = cwmsFile.get("//HILLS CREEK-BINGHAM/ELEV-ZONE/01JAN2023/1DAY/20/")
		CTBeach = cwmsFile.get("//HILLS CREEK-CT BEACH/ELEV-ZONE/01JAN2023/1DAY/20/")		
		
        #LOP Below
        
        
		OBSLOPElev = cwmsFile.get("//LOOKOUT POINT-POOL/ELEV/01JAN2023/1DAY/50% Flow Forecast/")
		SimLOPInflow = cwmsFile.get("//LOOKOUT POINT-POOL/FLOW-IN/01JAN2023/1DAY/50% Flow Forecast/")
		SimLOPOutflow = cwmsFile.get("//LOOKOUT POINT-POOL/FLOW-OUT/01JAN2023/1DAY/50% Flow Forecast/")
		LOPRuleCurve = cwmsFile.get("//LOOKOUT POINT-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/20/")
		LOPLBElev = cwmsFile.get("/WILLAMETTE/LOOKOUT POINT/ELEV(29)/01DEC2022/1HOUR/OBSERVED/")
		
		OBS25LOPElev = cwmsFile.get("//LOOKOUT POINT-POOL/ELEV/01JAN2023/1DAY/25% Flow Forecast/")
		Sim25LOPInflow = cwmsFile.get("//LOOKOUT POINT-POOL/FLOW-IN/01JAN2023/1DAY/25% Flow Forecast/")
		Sim25LOPOutflow = cwmsFile.get("//LOOKOUT POINT-POOL/FLOW-OUT/01JAN2023/1DAY/25% Flow Forecast/")
		LOPRuleCurveN = cwmsFile.get("//LOP/ELEV-RULECURVE/01JAN2023/IR-MONTH/CENWP-CALC/")
		OBS75LOPElev = cwmsFile.get("//LOOKOUT POINT-POOL/ELEV/01JAN2023/1DAY/75% Flow Forecast/")
		Sim75LOPInflow = cwmsFile.get("//LOOKOUT POINT-POOL/FLOW-IN/01JAN2023/1DAY/75% Flow Forecast/")
		Sim75LOPOutflow = cwmsFile.get("//LOOKOUT POINT-POOL/FLOW-OUT/01JAN2023/1DAY/75% Flow Forecast/")
		
		
		
		LOPSpillwayCrest = cwmsFile.get("//LOOKOUT POINT-SPILLWAY CREST/ELEV-ZONE/01JAN2023/1DAY/20/")
		BlackCanyoneBR = cwmsFile.get("//LOOKOUT POINT-BLACK CANYON/ELEV-ZONE/01JAN2023/1DAY/20/")
		MeridianHamptonBR = cwmsFile.get("//LOOKOUT POINT-MERIDIAN & HAMPTON LANDING/ELEV-ZONE/01JAN2023/1DAY/20/")
		SignalPointBR = cwmsFile.get("//LOOKOUT POINT-SIGNAL POINT/ELEV-ZONE/01JAN2023/1DAY/20/")
		
		
		
		
		###GPR BELOW
		GPRLBElev = cwmsFile.get("/WILLAMETTE/GREEN PETER/ELEV(29)/01JAN2023/1HOUR/OBSERVED/")
		OBSGPRElev = cwmsFile.get("//GREEN PETER-POOL/ELEV/01JAN2023/1DAY/50% Flow Forecast/")
		SimGPRInflow = cwmsFile.get("//GREEN PETER-POOL/FLOW-IN/01JAN2023/1DAY/50% Flow Forecast/")
		SimGPROutflow = cwmsFile.get("//GREEN PETER-POOL/FLOW-OUT/01JAN2023/1DAY/50% Flow Forecast/")
		GPRRuleCurve = cwmsFile.get("//GREEN PETER-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/50% Flow Forecast/")
		
		OBS25GPRElev = cwmsFile.get("//GREEN PETER-POOL/ELEV/01JAN2023/1DAY/25% Flow Forecast/")
		Sim25GPRInflow = cwmsFile.get("//GREEN PETER-POOL/FLOW-IN/01JAN2023/1DAY/25% Flow Forecast/")
		Sim25GPROutflow = cwmsFile.get("//GREEN PETER-POOL/FLOW-OUT/01JAN2023/1DAY/25% Flow Forecast/")
		GPRRuleCurve = cwmsFile.get("//GREEN PETER-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/25% Flow Forecast/")
		
		OBS75GPRElev = cwmsFile.get("//GREEN PETER-POOL/ELEV/01JAN2023/1DAY/75% Flow Forecast/")
		Sim75GPRInflow = cwmsFile.get("//GREEN PETER-POOL/FLOW-IN/01JAN2023/1DAY/75% Flow Forecast/")
		Sim75GPROutflow = cwmsFile.get("//GREEN PETER-POOL/FLOW-OUT/01JAN2023/1DAY/75% Flow Forecast/")
		GPRRuleCurve = cwmsFile.get("//GREEN PETER-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/75% Flow Forecast/")
		
		GPRRuleCurveN = cwmsFile.get("//GPR/ELEV-RULECURVE/01MAR2023/IR-MONTH/CENWP-CALC/")
		GPRSW = cwmsFile.get("//GREEN PETER-SPILLWAY CREST/ELEV-ZONE/01JAN2023/1DAY/50% Flow Forecast/")
		ThistleCreekBR = cwmsFile.get("//GREEN PETER-THISTLE/ELEV-ZONE/01JAN2023/1DAY/20/")
		WHITCOMB = cwmsFile.get("//GREEN PETER-WHITCOMB/ELEV-ZONE/01JAN2023/1DAY/20/")
		
		
		#### FOS BELOW
		FOSLBElev = cwmsFile.get("/WILLAMETTE/FOSTER/ELEV(29)/01MAR2023/1HOUR/OBSERVED/")
		OBSFOSElev = cwmsFile.get("//FOSTER-POOL/ELEV/01JAN2023/1DAY/50% Flow Forecast/")
		SimFOSInflow = cwmsFile.get("//FOSTER-POOL/FLOW-IN/01JAN2023/1DAY/50% Flow Forecast/")
		SimFOSOutflow = cwmsFile.get("//FOSTER-POOL/FLOW-OUT/01JAN2023/1DAY/50% Flow Forecast/")
		FOSRuleCurve = cwmsFile.get("//FOSTER-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/50% Flow Forecast/")
		FOSRuleCurveN = cwmsFile.get("//FOS/ELEV-RULECURVE/01MAY2023/IR-MONTH/CENWP-CALC/")
		
		OBS25FOSElev = cwmsFile.get("//FOSTER-POOL/ELEV/01JAN2023/1DAY/25% Flow Forecast/")
		Sim25FOSInflow = cwmsFile.get("//FOSTER-POOL/FLOW-IN/01JAN2023/1DAY/25% Flow Forecast/")
		Sim25FOSOutflow = cwmsFile.get("//FOSTER-POOL/FLOW-OUT/01JAN2023/1DAY/25% Flow Forecast/")
		FOS25RuleCurve = cwmsFile.get("//FOSTER-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/25% Flow Forecast/")
		FOSRuleCurveN = cwmsFile.get("//FOS/ELEV-RULECURVE/01MAY2023/IR-MONTH/CENWP-CALC/")
		
		OBS75FOSElev = cwmsFile.get("//FOSTER-POOL/ELEV/01JAN2023/1DAY/75% Flow Forecast/")
		Sim75FOSInflow = cwmsFile.get("//FOSTER-POOL/FLOW-IN/01JAN2023/1DAY/75% Flow Forecast/")
		Sim75FOSOutflow = cwmsFile.get("//FOSTER-POOL/FLOW-OUT/01JAN2023/1DAY/75% Flow Forecast/")
		FOSRuleCurve = cwmsFile.get("//FOSTER-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/75% Flow Forecast/")
		FOSRuleCurveN = cwmsFile.get("//FOS/ELEV-RULECURVE/01MAY2023/IR-MONTH/CENWP-CALC/")


		
		#//BIG CLIFF-POOL/FLOW-OUT/01JAN2023/1DAY/20C0/
		
		####DET Below
		DETLBElev = cwmsFile.get("/WILLAMETTE/DETROIT/ELEV(29)/01APR2023/1HOUR/OBSERVED/")
		OBS25DETElev = cwmsFile.get("//DETROIT-POOL/ELEV/01JAN2023/1DAY/25% Flow Forecast/")
		Sim25DETInflow = cwmsFile.get("//DETROIT-POOL/FLOW-IN/01JAN2023/1DAY/25% Flow Forecast/")
		Sim25DETOutflow = cwmsFile.get("//DETROIT-POOL/FLOW-OUT/01JAN2023/1DAY/25% Flow Forecast/")
		DETRuleCurve = cwmsFile.get("//DETROIT-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/25% Flow Forecast/")
		DETRuleCurveN = cwmsFile.get("//DET/ELEV-RULECURVE/01MAY2023/IR-MONTH/CENWP-CALC/")
		
		OBSDETElev = cwmsFile.get("//DETROIT-POOL/ELEV/01JAN2023/1DAY/50% Flow Forecast/")
		SimDETInflow = cwmsFile.get("//DETROIT-POOL/FLOW-IN/01JAN2023/1DAY/50% Flow Forecast/")
		SimDETOutflow = cwmsFile.get("//BIG CLIFF-POOL/FLOW-OUT/01JAN2023/1DAY/50% Flow Forecast/")
		DETRuleCurve = cwmsFile.get("//DETROIT-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/50% Flow Forecast/")
		DETRuleCurveN = cwmsFile.get("//DET/ELEV-RULECURVE/01MAY2023/IR-MONTH/CENWP-CALC/")
		
		OBS75DETElev = cwmsFile.get("//DETROIT-POOL/ELEV/01JAN2023/1DAY/75% Flow Forecast/")
		Sim75DETInflow = cwmsFile.get("//DETROIT-POOL/FLOW-IN/01JAN2023/1DAY/75% Flow Forecast/")
		Sim75DETOutflow = cwmsFile.get("//DETROIT-POOL/FLOW-OUT/01JAN2023/1DAY/75% Flow Forecast/")
		DETRuleCurve = cwmsFile.get("//DETROIT-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/75% Flow Forecast/")
		DETRuleCurveN = cwmsFile.get("//DET/ELEV-RULECURVE/01MAY2023/IR-MONTH/CENWP-CALC/")
				
		DETSW = cwmsFile.get("//DETROIT-SPILL WAY CREST/ELEV-ZONE/01JAN2023/1DAY/20/")
		SouthShoreBR = cwmsFile.get("//DETROIT-SOUTH SHORE/ELEV-ZONE/01JAN2023/1DAY/20/")
		StateParkDBR = cwmsFile.get("//DETROIT-STATE PARK D/ELEV-ZONE/01JAN2023/1DAY/20/")
		StateParkGBR = cwmsFile.get("//DETROIT-STATE PARK G/ELEV-ZONE/01JAN2023/1DAY/20/")
		MongoldBR = cwmsFile.get("//DETROIT-MONGOLD/ELEV-ZONE/01JAN2023/1DAY/20/")
		KanesMarinaBR = cwmsFile.get("//DETROIT-KANES MARINA/ELEV-ZONE/01JAN2023/1DAY/20/")
				
		CGRLBElev = cwmsFile.get("/WILLAMETTE/COUGAR/ELEV(29)/01FEB2023/1HOUR/OBSERVED/")
		OBS25CGRElev = cwmsFile.get("//COUGAR-POOL/ELEV/01JAN2023/1DAY/25% Flow Forecast/")
		Sim25CGRInflow = cwmsFile.get("//COUGAR-POOL/FLOW-IN/01JAN2023/1DAY/25% Flow Forecast/")
		Sim25CGROutflow = cwmsFile.get("//COUGAR-POOL/FLOW-OUT/01JAN2023/1DAY/25% Flow Forecast/")
		CGRRuleCurve = cwmsFile.get("//COUGAR-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/25% Flow Forecast/")
		CGRRuleCurveN = cwmsFile.get("//CGR/ELEV-RULECURVE/01NOV2023/IR-MONTH/CENWP-CALC/")

		OBSCGRElev = cwmsFile.get("//COUGAR-POOL/ELEV/01JAN2023/1DAY/50% Flow Forecast/")
		SimCGRInflow = cwmsFile.get("//COUGAR-POOL/FLOW-IN/01JAN2023/1DAY/50% Flow Forecast/")
		SimCGROutflow = cwmsFile.get("//COUGAR-POOL/FLOW-OUT/01JAN2023/1DAY/50% Flow Forecast/")
		CGRRuleCurve = cwmsFile.get("//COUGAR-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/50% Flow Forecast/")
		CGRRuleCurveN = cwmsFile.get("//CGR/ELEV-RULECURVE/01NOV2023/IR-MONTH/CENWP-CALC/")
		
		OBS75CGRElev = cwmsFile.get("//COUGAR-POOL/ELEV/01JAN2023/1DAY/75% Flow Forecast/")
		Sim75CGRInflow = cwmsFile.get("//COUGAR-POOL/FLOW-IN/01JAN2023/1DAY/75% Flow Forecast/")
		Sim75CGROutflow = cwmsFile.get("//COUGAR-POOL/FLOW-OUT/01JAN2023/1DAY/75% Flow Forecast/")
		CGR75RuleCurve = cwmsFile.get("//COUGAR-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/75% Flow Forecast/")
		CGRRuleCurveN = cwmsFile.get("//CGR/ELEV-RULECURVE/01NOV2023/IR-MONTH/CENWP-CALC/")
		
		CGRSpillwayCrest = cwmsFile.get("//COUGAR-SPILLWAY CREST/ELEV-ZONE/01JAN2023/1DAY/20/")
		
		

		
		
		
		###FAL Below
		FALLBElev = cwmsFile.get("/WILLAMETTE/FALL CREEK/ELEV(29)/01APR2023/1HOUR/OBSERVED/")
		OBSFALElev = cwmsFile.get("//FALL CREEK-POOL/ELEV/01JAN2023/1DAY/50% Flow Forecast/")
		SimFALInflow = cwmsFile.get("//FALL CREEK-POOL/FLOW-IN/01JAN2023/1DAY/50% Flow Forecast/")
		SimFALOutflow = cwmsFile.get("//FALL CREEK-POOL/FLOW-OUT/01JAN2023/1DAY/50% Flow Forecast/")
		FALRuleCurve = cwmsFile.get("//FALL CREEK-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/50% Flow Forecast/")
		FALRuleCurveN = cwmsFile.get("//FAL/ELEV-RULECURVE/01APR2023/IR-MONTH/CENWP-CALC/")
		
		OBS25FALElev = cwmsFile.get("//FALL CREEK-POOL/ELEV/01JAN2023/1DAY/25% Flow Forecast/")
		Sim25FALInflow = cwmsFile.get("//FALL CREEK-POOL/FLOW-IN/01JAN2023/1DAY/25% Flow Forecast/")
		Sim25FALOutflow = cwmsFile.get("//FALL CREEK-POOL/FLOW-OUT/01JAN2023/1DAY/25% Flow Forecast/")
		FALRuleCurve = cwmsFile.get("//FALL CREEK-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/25% Flow Forecast/")
		FALRuleCurveN = cwmsFile.get("//FAL/ELEV-RULECURVE/01APR2023/IR-MONTH/CENWP-CALC/")
		
		OBS50FALElev = cwmsFile.get("//FALL CREEK-POOL/ELEV/01JAN2023/1DAY/50% Flow Forecast/")
		OBS75FALElev = cwmsFile.get("//FALL CREEK-POOL/ELEV/01JAN2023/1DAY/75% Flow Forecast/")
		Sim50FALInflow = cwmsFile.get("//FALL CREEK-POOL/FLOW-IN/01JAN2023/1DAY/50% Flow Forecast/")
		Sim50FALOutflow = cwmsFile.get("//FALL CREEK-POOL/FLOW-OUT/01JAN2023/1DAY/50% Flow Forecast/")
		Sim75FALInflow = cwmsFile.get("//FALL CREEK-POOL/FLOW-IN/01JAN2023/1DAY/75% Flow Forecast/")
		Sim75FALOutflow = cwmsFile.get("//FALL CREEK-POOL/FLOW-OUT/01JAN2023/1DAY/75% Flow Forecast/")
		
		FALSpillwayCrest = cwmsFile.get("//FALL CREEK-SPILLWAY CREST/ELEV-ZONE/01JAN2023/1DAY/20/")
		WINBERRYBR = cwmsFile.get("//FALL CREEK-WINBERRY/ELEV-ZONE/01JAN2023/1DAY/20/")
		NorthShoreBR = cwmsFile.get("//FALL CREEK-NORTH SHORE/ELEV-ZONE/01JAN2023/1DAY/20/")
		CascaraBR = cwmsFile.get("//FALL CREEK-CASCARA/ELEV-ZONE/01JAN2023/1DAY/20/")
		
		
		
		
		
		
		FRNLBElev = cwmsFile.get("/WILLAMETTE/FERN RIDGE/ELEV(29)/01APR2023/1HOUR/OBSERVED/")
		OBS25FRNElev = cwmsFile.get("//FERN RIDGE-POOL/ELEV/01JAN2023/1DAY/25% Flow Forecast/")
		Sim25FRNInflow = cwmsFile.get("//FERN RIDGE-POOL/FLOW-IN/01JAN2023/1DAY/25% Flow Forecast/")
		Sim25FRNOutflow = cwmsFile.get("//FERN RIDGE-POOL/FLOW-OUT/01JAN2023/1DAY/25% Flow Forecast/")
		FRNRuleCurve = cwmsFile.get("//FERN RIDGE-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/25% Flow Forecast/")
		FRNRuleCurveN = cwmsFile.get("//FRN/ELEV-RULECURVE/01JUN2023/IR-MONTH/CENWP-CALC/")
		
		OBSFRNElev = cwmsFile.get("//FERN RIDGE-POOL/ELEV/01JAN2023/1DAY/50% Flow Forecast/")
		SimFRNInflow = cwmsFile.get("//FERN RIDGE-POOL/FLOW-IN/01JAN2023/1DAY/50% Flow Forecast/")
		SimFRNOutflow = cwmsFile.get("//FERN RIDGE-POOL/FLOW-OUT/01JAN2023/1DAY/50% Flow Forecast/")
		FRNRuleCurve = cwmsFile.get("//FERN RIDGE-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/50% Flow Forecast/")
		FRNRuleCurveN = cwmsFile.get("//FRN/ELEV-RULECURVE/01JUN2023/IR-MONTH/CENWP-CALC/")
		
		OBS75FRNElev = cwmsFile.get("//FERN RIDGE-POOL/ELEV/01JAN2023/1DAY/75% Flow Forecast/")
		Sim75FRNInflow = cwmsFile.get("//FERN RIDGE-POOL/FLOW-IN/01JAN2023/1DAY/75% Flow Forecast/")
		Sim75FRNOutflow = cwmsFile.get("//FERN RIDGE-POOL/FLOW-OUT/01JAN2023/1DAY/50% Flow Forecast/")
		FRNRuleCurve = cwmsFile.get("//FERN RIDGE-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/75% Flow Forecast/")
		FRNRuleCurveN = cwmsFile.get("//FRN/ELEV-RULECURVE/01JUN2023/IR-MONTH/CENWP-CALC/")
		
		
		
		FRNSpillwayCrest = cwmsFile.get("//FERN RIDGE-SPILLWAY CREST/ELEV-ZONE/01JAN2023/1DAY/20/")
		ORCHARDBR = cwmsFile.get("//FERN RIDGE-ORCHARD/ELEV-ZONE/01JAN2023/1DAY/20/")
		PERKINSBR = cwmsFile.get("//FERN RIDGE-PERKINS/ELEV-ZONE/01JAN2023/1DAY/20/")
		RICHARDSONBR = cwmsFile.get("//FERN RIDGE-RICHARDSON/ELEV-ZONE/01JAN2023/1DAY/20/")
		FERNRIDGESHORESBR = cwmsFile.get("//FERN RIDGE-FERN RIDGE SHORES/ELEV-ZONE/01JAN2023/1DAY/20/")
		
		
		
		BLRLBElev = cwmsFile.get("/WILLAMETTE/BLUE RIVER/ELEV(29)/01FEB2023/1HOUR/OBSERVED/")
		OBS25BLRElev = cwmsFile.get("//BLUE RIVER-POOL/ELEV/01JAN2023/1DAY/25% Flow Forecast/")
		Sim25BLRInflow = cwmsFile.get("//BLUE RIVER-POOL/FLOW-IN/01JAN2023/1DAY/25% Flow Forecast/")
		Sim25BLROutflow = cwmsFile.get("//BLUE RIVER-POOL/FLOW-OUT/01JAN2023/1DAY/25% Flow Forecast/")
		BLRRuleCurve = cwmsFile.get("//BLUE RIVER-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/25% Flow Forecast/")
		BLRRuleCurveN = cwmsFile.get("//BLU/ELEV-RULECURVE/01APR2023/IR-MONTH/CENWP-CALC/")
		
		OBSBLRElev = cwmsFile.get("//BLUE RIVER-POOL/ELEV/01JAN2023/1DAY/50% Flow Forecast/")
		SimBLRInflow = cwmsFile.get("//BLUE RIVER-POOL/FLOW-IN/01JAN2023/1DAY/50% Flow Forecast/")
		SimBLROutflow = cwmsFile.get("//BLUE RIVER-POOL/FLOW-OUT/01JAN2023/1DAY/50% Flow Forecast/")
		BLRRuleCurve = cwmsFile.get("//BLUE RIVER-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/50% Flow Forecast/")
		BLRRuleCurveN = cwmsFile.get("//BLU/ELEV-RULECURVE/01APR2023/IR-MONTH/CENWP-CALC/")
		
		OBS75BLRElev = cwmsFile.get("//BLUE RIVER-POOL/ELEV/01JAN2023/1DAY/75% Flow Forecast/")
		Sim75BLRInflow = cwmsFile.get("//BLUE RIVER-POOL/FLOW-IN/01JAN2023/1DAY/75% Flow Forecast/")
		Sim75BLROutflow = cwmsFile.get("//BLUE RIVER-POOL/FLOW-OUT/01JAN2023/1DAY/75% Flow Forecast/")
		BLRRuleCurve = cwmsFile.get("//BLUE RIVER-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/75% Flow Forecast/")
		BLRRuleCurveN = cwmsFile.get("//BLU/ELEV-RULECURVE/01APR2023/IR-MONTH/CENWP-CALC/")
		
		BLRSW = cwmsFile.get("//BLUE RIVER-SPILLWAY CREST/ELEV-ZONE/01JAN2023/1DAY/20/")
		LookoutBR = cwmsFile.get("//BLUE RIVER-LOOKOUT/ELEV-ZONE/01JAN2023/1DAY/20/")
		SaddleDamBR = cwmsFile.get("//BLUE RIVER-SADDLE DAM/ELEV-ZONE/01JAN2023/1DAY/20/")
		
				
				
		DORLBElev = cwmsFile.get("/WILLAMETTE/DORENA/ELEV(29)/01DEC2022/1HOUR/OBSERVED/")
		OBS25DORElev = cwmsFile.get("//DORENA-POOL/ELEV/01JAN2023/1DAY/25% Flow Forecast/")
		Sim25DORInflow = cwmsFile.get("//DORENA-POOL/FLOW-IN/01JAN2023/1DAY/25% Flow Forecast/")
		Sim25DOROutflow = cwmsFile.get("//DORENA-POOL/FLOW-OUT/01JAN2023/1DAY/25% Flow Forecast/")
		DORRuleCurve = cwmsFile.get("//DORENA-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/25% Flow Forecast/")
		DORRuleCurveN = cwmsFile.get("//DOR/ELEV-RULECURVE/01JUL2023/IR-MONTH/CENWP-CALC/")
		
		OBSDORElev = cwmsFile.get("//DORENA-POOL/ELEV/01JAN2023/1DAY/50% Flow Forecast/")
		SimDORInflow = cwmsFile.get("//DORENA-POOL/FLOW-IN/01JAN2023/1DAY/50% Flow Forecast/")
		SimDOROutflow = cwmsFile.get("//DORENA-POOL/FLOW-OUT/01JAN2023/1DAY/50% Flow Forecast/")
		DORRuleCurve = cwmsFile.get("//DORENA-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/50% Flow Forecast/")
		DORRuleCurveN = cwmsFile.get("//DOR/ELEV-RULECURVE/01JUL2023/IR-MONTH/CENWP-CALC/")
		
		OBS75DORElev = cwmsFile.get("//DORENA-POOL/ELEV/01JAN2023/1DAY/75% Flow Forecast/")
		Sim75DORInflow = cwmsFile.get("//DORENA-POOL/FLOW-IN/01JAN2023/1DAY/75% Flow Forecast/")
		Sim75DOROutflow = cwmsFile.get("//DORENA-POOL/FLOW-OUT/01JAN2023/1DAY/75% Flow Forecast/")
		DORRuleCurve = cwmsFile.get("//DORENA-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/75% Flow Forecast/")
		DORRuleCurveN = cwmsFile.get("//DOR/ELEV-RULECURVE/01JUL2023/IR-MONTH/CENWP-CALC/")
		
		HarmsParkBR = cwmsFile.get("//DORENA-HARMS PARK/ELEV-ZONE/01JAN2023/1DAY/20/")
		
		
		COTLBElev = cwmsFile.get("/WILLAMETTE/COTTAGE GROVE/ELEV(29)/01APR2023/1HOUR/OBSERVED/")
		OBS25COTElev = cwmsFile.get("//COTTAGE GROVE-POOL/ELEV/01JAN2023/1DAY/25% Flow Forecast/")
		Sim25COTInflow = cwmsFile.get("//COTTAGE GROVE-POOL/FLOW-IN/01JAN2023/1DAY/25% Flow Forecast/")
		Sim25COTOutflow = cwmsFile.get("//COTTAGE GROVE-POOL/FLOW-OUT/01JAN2023/1DAY/25% Flow Forecast/")
		COTRuleCurve = cwmsFile.get("//COTTAGE GROVE-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/25% Flow Forecast/")
		COTRuleCurveN = cwmsFile.get("//COT/ELEV-RULECURVE//IR-MONTH/CENWP-CALC/")
		
		OBSCOTElev = cwmsFile.get("//COTTAGE GROVE-POOL/ELEV/01JAN2023/1DAY/50% Flow Forecast/")
		SimCOTInflow = cwmsFile.get("//COTTAGE GROVE-POOL/FLOW-IN/01JAN2023/1DAY/50% Flow Forecast/")
		SimCOTOutflow = cwmsFile.get("//COTTAGE GROVE-POOL/FLOW-OUT/01JAN2023/1DAY/50% Flow Forecast/")
		COTRuleCurve = cwmsFile.get("//COTTAGE GROVE-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/25% Flow Forecast/")
		COTRuleCurveN = cwmsFile.get("//COT/ELEV-RULECURVE/01JUL2023/IR-MONTH/CENWP-CALC/")
		
		
		OBS75COTElev = cwmsFile.get("//COTTAGE GROVE-POOL/ELEV/01JAN2023/1DAY/75% Flow Forecast/")
		Sim75COTInflow = cwmsFile.get("//COTTAGE GROVE-POOL/FLOW-IN/01JAN2023/1DAY/75% Flow Forecast/")
		Sim75COTOutflow = cwmsFile.get("//COTTAGE GROVE-POOL/FLOW-OUT/01JAN2023/1DAY/75% Flow Forecast/")
		COTRuleCurve = cwmsFile.get("//COTTAGE GROVE-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/25% Flow Forecast/")
		COTRuleCurveN = cwmsFile.get("//COT/ELEV-RULECURVE/01JUL2023/IR-MONTH/CENWP-CALC/")
		
		
		
		COT_Plot = Plot.newPlot("Cottage Grove Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSCOTElev)
		TopView.addCurve("Y1", OBS25COTElev)
		TopView.addCurve("Y1", OBS75COTElev)
		TopView.addCurve("Y1",COTRuleCurve)
		TopView.addCurve("Y1", COTRuleCurveN)
		TopView.addCurve("Y1", COTLBElev)
		
		
		BottomView.addCurve("Y1", SimCOTInflow)
		BottomView.addCurve("Y1", SimCOTOutflow)
		COT_Plot.configurePlotLayout(Layout)
		COT_Plot.showPlot()

		
		
		
		#WILLAMETTE FLOW DATA 

		SALEM25Flow = cwmsFile.get("//WILLAMETTE_AT SALEM/FLOW/01JAN2023/1DAY/25% Flow Forecast/")
		SALEMFlow = cwmsFile.get("//WILLAMETTE_AT SALEM/FLOW/01JAN2023/1DAY/50% Flow Forecast/")
		SALEM75Flow = cwmsFile.get("//WILLAMETTE_AT SALEM/FLOW/01JAN2023/1DAY/75% Flow Forecast/")
		BIOPMIN = cwmsFile.get("//SALEM BIOP MIN BY WY/FLOW-MIN/01JAN2023/1DAY/50% Flow Forecast/")
        #SALOOBS = cwmsFile.get("")

		ALBO25Flow = cwmsFile.get("//WILLAMETTE_AT ALBANY/FLOW/01JAN2023/1DAY/25% Flow Forecast/")
		ALBOFlow = cwmsFile.get("//WILLAMETTE_AT ALBANY/FLOW/01JAN2023/1DAY/50% Flow Forecast/")
		ALBO75Flow = cwmsFile.get("//WILLAMETTE_AT ALBANY/FLOW/01JAN2023/1DAY/75% Flow Forecast/")
		ALBOBIOPMIN = cwmsFile.get("//ALBANY BIOP MIN BY WY/FLOW-MIN/01JAN2023/1DAY/50% Flow Forecast/")
        #ALBOOBS = cwmsFile.get("")

		EUGO25Flow = cwmsFile.get("//WILLAMETTE_AT EUGENE/FLOW/01JAN2023/1DAY/25% Flow Forecast/")
		EUGOFlow = cwmsFile.get("//WILLAMETTE_AT EUGENE/FLOW/01JAN2023/1DAY/50% Flow Forecast/")
		EUGO75Flow = cwmsFile.get("//WILLAMETTE_AT EUGENE/FLOW/01JAN2023/1DAY/75% Flow Forecast/")

		HARO25Flow = cwmsFile.get("//WILLAMETTE_AT HARRISBURG/FLOW/01JAN2023/1DAY/25% Flow Forecast/")
		HAROFlow = cwmsFile.get("//WILLAMETTE_AT HARRISBURG/FLOW/01JAN2023/1DAY/50% Flow Forecast/")
		HARO75Flow = cwmsFile.get("//WILLAMETTE_AT HARRISBURG/FLOW/01JAN2023/1DAY/75% Flow Forecast/")


        
### Create Plot ####
		LOP_Plot = Plot.newPlot("Look Out Point Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		#TopView.addCurve("Y1", MeridianHamptonBR)
		#TopView.addCurve("Y1", SignalPointBR)
		#TopView.addCurve("Y1", LOPSpillwayCrest)
		TopView.addCurve("Y1", OBSLOPElev)
		TopView.addCurve("Y1", OBS25LOPElev)
		TopView.addCurve("Y1", OBS75LOPElev)
		#TopView.addCurve("Y1", BlackCanyoneBR)
		TopView.addCurve("Y1", LOPRuleCurve)
		TopView.addCurve("Y1", LOPLBElev)
		TopView.addCurve("Y1", LOPRuleCurveN)
        #TopView.addCurve("Y1", MeridianHamptonBR)    
		BottomView.addCurve("Y1", SimLOPInflow)
		BottomView.addCurve("Y1", SimLOPOutflow)
		#BottomView.addCurve("Y1", Sim25LOPOutflow)
		#BottomView.addCurve("Y1", Sim75LOPOutflow)
		LOP_Plot.configurePlotLayout(Layout)
		LOP_Plot.showPlot()    



        
		HCR_Plot = Plot.newPlot("Hills Creek Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSHCRElev)
		TopView.addCurve("Y1", OBS25HCRElev)
		TopView.addCurve("Y1", OBS75HCRElev)
		TopView.addCurve("Y1", HCRRuleCurve)
		TopView.addCurve("Y1", HCRRuleCurveN)
		#TopView.addCurve("Y1", HCRSW)
		#TopView.addCurve("Y1", PackardBR)
		#TopView.addCurve("Y1", BinghamBR)
		#TopView.addCurve("Y1", CTBeach)
		TopView.addCurve("Y1", HCRLBElev)
		BottomView.addCurve("Y1", SimHCRInflow)
		#BottomView.addCurve("Y1", Sim25HCRInflow)
		#BottomView.addCurve("Y1", Sim75HCRInflow)
		BottomView.addCurve("Y1", SimHCROutflow)
		#BottomView.addCurve("Y1", Sim25HCROutflow)
		#BottomView.addCurve("Y1", Sim75HCROutflow)
		HCR_Plot.configurePlotLayout(Layout)
		HCR_Plot.showPlot()
        
        


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
		
		
		
		HCR_Plot = Plot.newPlot("Hills Creek Project Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(70)
		BottomView = Layout.addViewport(30)
		TopView.addCurve("Y1", OBSHCRElev)
		TopView.addCurve("Y1", OBS25HCRElev)
		TopView.addCurve("Y1", OBS75HCRElev)
		TopView.addCurve("Y1", HCRRuleCurve)
		TopView.addCurve("Y1", HCRRuleCurveN)
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
		TopView.addCurve("Y1", OBS25BLRElev)
		TopView.addCurve("Y1", OBS75BLRElev)
		TopView.addCurve("Y1",BLRRuleCurve)
		TopView.addCurve("Y1", BLRRuleCurveN)
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
		TopView.addCurve("Y1", OBS25CGRElev)
		TopView.addCurve("Y1", OBS75CGRElev)
		TopView.addCurve("Y1",CGRRuleCurve)
		TopView.addCurve("Y1", CGRRuleCurveN)

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
		TopView.addCurve("Y1", OBS25FALElev)
		TopView.addCurve("Y1", OBS75FALElev)
		TopView.addCurve("Y1",FALRuleCurve)
		TopView.addCurve("Y1", FALRuleCurveN)
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
		TopView.addCurve("Y1", OBS25DORElev)
		TopView.addCurve("Y1", OBS75DORElev)
		TopView.addCurve("Y1",DORRuleCurve)
		TopView.addCurve("Y1", DORRuleCurveN)
		TopView.addCurve("Y1", DORLBElev)
		BottomView.addCurve("Y1", SimDORInflow)
		BottomView.addCurve("Y1", SimDOROutflow)
		DOR_Plot.configurePlotLayout(Layout)
		DOR_Plot.showPlot()


		
		SALO_Plot = Plot.newPlot("Salem Flow Forecast")
		Layout = Plot.newPlotLayout()
		BottomView = Layout.addViewport(30)
		BottomView.addCurve("Y1", SALEM25Flow)
		BottomView.addCurve("Y1", SALEMFlow)
		BottomView.addCurve("Y1", SALEM75Flow)
		BottomView.addCurve("Y1", BIOPMIN)
		SALO_Plot.configurePlotLayout(Layout)
		SALO_Plot.showPlot()

		ALBO_Plot = Plot.newPlot("Albany Flow Forecast")
		Layout = Plot.newPlotLayout()
		BottomView = Layout.addViewport(30)
		BottomView.addCurve("Y1", ALBO25Flow)
		BottomView.addCurve("Y1", ALBOFlow)
		BottomView.addCurve("Y1", ALBO75Flow)
		BottomView.addCurve("Y1", ALBOBIOPMIN)
		ALBO_Plot.configurePlotLayout(Layout)
		ALBO_Plot.showPlot()
        
		EUGO_Plot = Plot.newPlot("Eugene Flow Forecast")
		Layout = Plot.newPlotLayout()
		BottomView = Layout.addViewport(30)
		BottomView.addCurve("Y1", EUGO25Flow)
		BottomView.addCurve("Y1", EUGOFlow)
		BottomView.addCurve("Y1", EUGO75Flow)
		EUGO_Plot.configurePlotLayout(Layout)
		EUGO_Plot.showPlot()

		HARO_Plot = Plot.newPlot("Harissburg Flow Forecast")
		Layout = Plot.newPlotLayout()
		BottomView = Layout.addViewport(30)
		BottomView.addCurve("Y1", HARO25Flow)
		BottomView.addCurve("Y1", HAROFlow)
		BottomView.addCurve("Y1", HARO75Flow)
		HARO_Plot.configurePlotLayout(Layout)
		HARO_Plot.showPlot()
				
####### Plot Line Styles####
		
		OBSLOPElevCurve_25 = LOP_Plot.getCurve(OBS25LOPElev)
		OBSLOPElevCurve_25.setLineWidth(6)
		OBSLOPElevCurve_25 = LOP_Plot.getCurve(OBS25LOPElev)
		OBSLOPElevCurve_25.setLineColor("yellow")
		OBSLOPElevCurve_25.setLineStyle("solid")
		OBSLOPElevCurve_25.setLineWidth(3)

		OBSLOPElevCurve_50 = LOP_Plot.getCurve(OBSLOPElev)
		OBSLOPElevCurve_50.setLineWidth(6)
		OBSLOPElevCurve_50 = LOP_Plot.getCurve(OBSLOPElev)
		OBSLOPElevCurve_50.setLineColor("green")
		OBSLOPElevCurve_50.setLineStyle("solid")
		OBSLOPElevCurve_50.setLineWidth(3)

		OBSLOPElevCurve_75 = LOP_Plot.getCurve(OBS75LOPElev)
		OBSLOPElevCurve_75.setLineWidth(3)
		OBSLOPElevCurve_75 = LOP_Plot.getCurve(OBS75LOPElev)
		OBSLOPElevCurve_75.setLineColor("cyan")
		OBSLOPElevCurve_75.setLineStyle("Solid")
		OBSLOPElevCurve_75.setLineWidth(3)
		
		LOPRuleCurveNormal = LOP_Plot.getCurve(LOPRuleCurveN)
		LOPRuleCurveNormal.setLineWidth(3)
		LOPRuleCurveNormal = LOP_Plot.getCurve(LOPRuleCurveN)
		LOPRuleCurveNormal.setLineColor("Black")
		LOPRuleCurveNormal.setLineStyle("Solid")
		LOPRuleCurveNormal.setLineWidth(3)

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

		OBSHCRElevCurve_25 = HCR_Plot.getCurve(OBS25HCRElev)
		OBSHCRElevCurve_25.setLineWidth(6)
		OBSHCRElevCurve_25 = HCR_Plot.getCurve(OBS25HCRElev)
		OBSHCRElevCurve_25.setLineColor("yellow")
		OBSHCRElevCurve_25.setLineStyle("solid")
		OBSHCRElevCurve_25.setLineWidth(3)

		OBSHCRElevCurve_50 = HCR_Plot.getCurve(OBSHCRElev)
		OBSHCRElevCurve_50.setLineWidth(6)
		OBSHCRElevCurve_50 = HCR_Plot.getCurve(OBSHCRElev)
		OBSHCRElevCurve_50.setLineColor("green")
		OBSHCRElevCurve_50.setLineStyle("solid")
		OBSHCRElevCurve_50.setLineWidth(3)

		OBSHCRElevCurve_75 = HCR_Plot.getCurve(OBS75HCRElev)
		OBSHCRElevCurve_75.setLineWidth(3)
		OBSHCRElevCurve_75 = HCR_Plot.getCurve(OBS75HCRElev)
		OBSHCRElevCurve_75.setLineColor("cyan")
		OBSHCRElevCurve_75.setLineStyle("Solid")
		OBSHCRElevCurve_75.setLineWidth(3)
		
		HCRRuleCurveNormal = HCR_Plot.getCurve(HCRRuleCurveN)
		HCRRuleCurveNormal.setLineWidth(3)
		HCRRuleCurveNormal = HCR_Plot.getCurve(HCRRuleCurveN)
		HCRRuleCurveNormal.setLineColor("Black")
		HCRRuleCurveNormal.setLineStyle("Solid")
		HCRRuleCurveNormal.setLineWidth(3)
		
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

		
		
						############### FAL below
		
		OBSFALElevCurve_25 = FAL_Plot.getCurve(OBS25FALElev)
		OBSFALElevCurve_25.setLineWidth(6)
		OBSFALElevCurve_25 = FAL_Plot.getCurve(OBS25FALElev)
		OBSFALElevCurve_25.setLineColor("yellow")
		OBSFALElevCurve_25.setLineStyle("solid")
		OBSFALElevCurve_25.setLineWidth(3)

		OBSFALElevCurve_50 = FAL_Plot.getCurve(OBSFALElev)
		OBSFALElevCurve_50.setLineWidth(6)
		OBSFALElevCurve_50 = FAL_Plot.getCurve(OBSFALElev)
		OBSFALElevCurve_50.setLineColor("green")
		OBSFALElevCurve_50.setLineStyle("solid")
		OBSFALElevCurve_50.setLineWidth(3)

		OBSFALElevCurve_75 = FAL_Plot.getCurve(OBS75FALElev)
		OBSFALElevCurve_75.setLineWidth(3)
		OBSFALElevCurve_75 = FAL_Plot.getCurve(OBS75FALElev)
		OBSFALElevCurve_75.setLineColor("cyan")
		OBSFALElevCurve_75.setLineStyle("Solid")
		OBSFALElevCurve_75.setLineWidth(3)
		
		FALRuleCurveNormal = FAL_Plot.getCurve(FALRuleCurveN)
		FALRuleCurveNormal.setLineWidth(3)
		FALRuleCurveNormal = FAL_Plot.getCurve(FALRuleCurveN)
		FALRuleCurveNormal.setLineColor("black")
		FALRuleCurveNormal.setLineStyle("Solid")
		FALRuleCurveNormal.setLineWidth(3)
		

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
		
						############### CGR below
		OBSCGRElevCurve_25 = CGR_Plot.getCurve(OBS25CGRElev)
		OBSCGRElevCurve_25.setLineWidth(6)
		OBSCGRElevCurve_25 = CGR_Plot.getCurve(OBS25CGRElev)
		OBSCGRElevCurve_25.setLineColor("yellow")
		OBSCGRElevCurve_25.setLineStyle("solid")
		OBSCGRElevCurve_25.setLineWidth(3)
		
		OBSCGRElevCurve_50 = CGR_Plot.getCurve(OBSCGRElev)
		OBSCGRElevCurve_50.setLineWidth(6)
		OBSCGRElevCurve_50 = CGR_Plot.getCurve(OBSCGRElev)
		OBSCGRElevCurve_50.setLineColor("green")
		OBSCGRElevCurve_50.setLineStyle("solid")
		OBSCGRElevCurve_50.setLineWidth(3)

		OBSCGRElevCurve_75 = CGR_Plot.getCurve(OBS75CGRElev)
		OBSCGRElevCurve_75.setLineWidth(3)
		OBSCGRElevCurve_75 = CGR_Plot.getCurve(OBS75CGRElev)
		OBSCGRElevCurve_75.setLineColor("cyan")
		OBSCGRElevCurve_75.setLineStyle("Solid")
		OBSCGRElevCurve_75.setLineWidth(3)
		
		CGRRuleCurveNormal = CGR_Plot.getCurve(CGRRuleCurveN)
		CGRRuleCurveNormal.setLineWidth(5)
		CGRRuleCurveNormal = CGR_Plot.getCurve(CGRRuleCurveN)
		CGRRuleCurveNormal.setLineColor("Black")
		CGRRuleCurveNormal.setLineStyle("Solid")
		CGRRuleCurveNormal.setLineWidth(5)


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
		
		OBSBLRElevCurve_25 = BLR_Plot.getCurve(OBS25BLRElev)
		OBSBLRElevCurve_25.setLineWidth(6)
		OBSBLRElevCurve_25 = BLR_Plot.getCurve(OBS25BLRElev)
		OBSBLRElevCurve_25.setLineColor("yellow")
		OBSBLRElevCurve_25.setLineStyle("solid")
		OBSBLRElevCurve_25.setLineWidth(3)

		OBSBLRElevCurve_50 = BLR_Plot.getCurve(OBSBLRElev)
		OBSBLRElevCurve_50.setLineWidth(6)
		OBSBLRElevCurve_50 = BLR_Plot.getCurve(OBSBLRElev)
		OBSBLRElevCurve_50.setLineColor("green")
		OBSBLRElevCurve_50.setLineStyle("solid")
		OBSBLRElevCurve_50.setLineWidth(3)

		OBSBLRElevCurve_75 = BLR_Plot.getCurve(OBS75BLRElev)
		OBSBLRElevCurve_75.setLineWidth(3)
		OBSBLRElevCurve_75 = BLR_Plot.getCurve(OBS75BLRElev)
		OBSBLRElevCurve_75.setLineColor("cyan")
		OBSBLRElevCurve_75.setLineStyle("Solid")
		OBSBLRElevCurve_75.setLineWidth(3)
		
		BLRRuleCurveNormal = BLR_Plot.getCurve(BLRRuleCurveN)
		BLRRuleCurveNormal.setLineWidth(3)
		BLRRuleCurveNormal = BLR_Plot.getCurve(BLRRuleCurveN)
		BLRRuleCurveNormal.setLineColor("black")
		BLRRuleCurveNormal.setLineStyle("Solid")
		BLRRuleCurveNormal.setLineWidth(3)


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
		OBSDORElevCurve_25 = DOR_Plot.getCurve(OBS25DORElev)
		OBSDORElevCurve_25.setLineWidth(6)
		OBSDORElevCurve_25 = DOR_Plot.getCurve(OBS25DORElev)
		OBSDORElevCurve_25.setLineColor("yellow")
		OBSDORElevCurve_25.setLineStyle("solid")
		OBSDORElevCurve_25.setLineWidth(3)

		OBSDORElevCurve_50 = DOR_Plot.getCurve(OBSDORElev)
		OBSDORElevCurve_50.setLineWidth(6)
		OBSDORElevCurve_50 = DOR_Plot.getCurve(OBSDORElev)
		OBSDORElevCurve_50.setLineColor("green")
		OBSDORElevCurve_50.setLineStyle("solid")
		OBSDORElevCurve_50.setLineWidth(3)

		OBSDORElevCurve_75 = DOR_Plot.getCurve(OBS75DORElev)
		OBSDORElevCurve_75.setLineWidth(3)
		OBSDORElevCurve_75 = DOR_Plot.getCurve(OBS75DORElev)
		OBSDORElevCurve_75.setLineColor("cyan")
		OBSDORElevCurve_75.setLineStyle("Solid")
		OBSDORElevCurve_75.setLineWidth(3)
		
		DORRuleCurveNormal = DOR_Plot.getCurve(DORRuleCurveN)
		DORRuleCurveNormal.setLineWidth(3)
		DORRuleCurveNormal = DOR_Plot.getCurve(DORRuleCurveN)
		DORRuleCurveNormal.setLineColor("black")
		DORRuleCurveNormal.setLineStyle("Solid")
		DORRuleCurveNormal.setLineWidth(3)
		

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
		OBSCOTElevCurve_25 = COT_Plot.getCurve(OBS25COTElev)
		OBSCOTElevCurve_25.setLineWidth(6)
		OBSCOTElevCurve_25 = COT_Plot.getCurve(OBS25COTElev)
		OBSCOTElevCurve_25.setLineColor("yellow")
		OBSCOTElevCurve_25.setLineStyle("solid")
		OBSCOTElevCurve_25.setLineWidth(3)

		OBSCOTElevCurve_50 = COT_Plot.getCurve(OBSCOTElev)
		OBSCOTElevCurve_50.setLineWidth(6)
		OBSCOTElevCurve_50 = COT_Plot.getCurve(OBSCOTElev)
		OBSCOTElevCurve_50.setLineColor("green")
		OBSCOTElevCurve_50.setLineStyle("solid")
		OBSCOTElevCurve_50.setLineWidth(3)

		OBSCOTElevCurve_75 = COT_Plot.getCurve(OBS75COTElev)
		OBSCOTElevCurve_75.setLineWidth(3)
		OBSCOTElevCurve_75 = COT_Plot.getCurve(OBS75COTElev)
		OBSCOTElevCurve_75.setLineColor("cyan")
		OBSCOTElevCurve_75.setLineWidth(3)
		
		COTRuleCurveNormal = COT_Plot.getCurve(COTRuleCurveN)
		OBSCOTElevCurve_75.setLineWidth(3)
		OBSCOTElevCurve_75 = COT_Plot.getCurve(COTRuleCurveN)
		OBSCOTElevCurve_75.setLineColor("Black")
		OBSCOTElevCurve_75.setLineStyle("Solid")
		OBSCOTElevCurve_75.setLineWidth(3)
		

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
		ALBOFlow_50.setLineColor("green")
		ALBOFlow_50.setLineStyle("solid")
		ALBOFlow_50.setLineWidth(3)

		ALBOFlow_75 = ALBO_Plot.getCurve(ALBO75Flow)
		ALBOFlow_75.setLineWidth(3)
		ALBOFlow_75 = ALBO_Plot.getCurve(ALBO75Flow)
		ALBOFlow_75.setLineColor("cyan")
		ALBOFlow_75.setLineStyle("solid")
		ALBOFlow_75.setLineWidth(3)
		
		ALBOFlow_25 = ALBO_Plot.getCurve(ALBO25Flow)
		ALBOFlow_25.setLineWidth(3)
		ALBOFlow_25 = ALBO_Plot.getCurve(ALBO25Flow)
		ALBOFlow_25.setLineColor("yellow")
		ALBOFlow_25.setLineStyle("solid")
		ALBOFlow_25.setLineWidth(3)
		######SALEM BELOW


		
		SALEMFlow_50 = SALO_Plot.getCurve(SALEMFlow)
		SALEMFlow_50.setLineWidth(3)
		SALEMFlow_50 = SALO_Plot.getCurve(SALEMFlow)
		SALEMFlow_50.setLineColor("green")
		SALEMFlow_50.setLineStyle("solid")
		SALEMFlow_50.setLineWidth(3)

		SALEMFlow_75 = SALO_Plot.getCurve(SALEM75Flow)
		SALEMFlow_75.setLineWidth(3)
		SALEMFlow_75 = SALO_Plot.getCurve(SALEM75Flow)
		SALEMFlow_75.setLineColor("cyan")
		SALEMFlow_75.setLineStyle("solid")
		SALEMFlow_75.setLineWidth(3)
		
		SALEMFlow_25 = SALO_Plot.getCurve(SALEM25Flow)
		SALEMFlow_25.setLineWidth(3)
		SALEMFlow_25 = SALO_Plot.getCurve(SALEM25Flow)
		SALEMFlow_25.setLineColor("yellow")
		SALEMFlow_25.setLineStyle("solid")
		SALEMFlow_25.setLineWidth(3)
		
		EUGENEFlow_50 = EUGO_Plot.getCurve(EUGOFlow)
		EUGENEFlow_50.setLineWidth(3)
		EUGENEFlow_50 = EUGO_Plot.getCurve(EUGOFlow)
		EUGENEFlow_50.setLineColor("green")
		EUGENEFlow_50.setLineStyle("solid")
		EUGENEFlow_50.setLineWidth(3)

		EUGENEFlow_75 = EUGO_Plot.getCurve(EUGO75Flow)
		EUGENEFlow_75.setLineWidth(3)
		EUGENEFlow_75 = EUGO_Plot.getCurve(EUGO75Flow)
		EUGENEFlow_75.setLineColor("cyan")
		EUGENEFlow_75.setLineStyle("solid")
		EUGENEFlow_75.setLineWidth(3)
		
		EUGENEFlow_25 = EUGO_Plot.getCurve(EUGO25Flow)
		EUGENEFlow_25.setLineWidth(3)
		EUGENEFlow_25 = EUGO_Plot.getCurve(EUGO25Flow)
		EUGENEFlow_25.setLineColor("yellow")
		EUGENEFlow_25.setLineStyle("solid")
		EUGENEFlow_25.setLineWidth(3)
        
		HARRISBURGFlow_50 = HARO_Plot.getCurve(HAROFlow)
		HARRISBURGFlow_50.setLineWidth(3)
		HARRISBURGFlow_50 = HARO_Plot.getCurve(HAROFlow)
		HARRISBURGFlow_50.setLineColor("green")
		HARRISBURGFlow_50.setLineStyle("solid")
		HARRISBURGFlow_50.setLineWidth(3)

		HARRISBURGFlow_75 = HARO_Plot.getCurve(HARO75Flow)
		HARRISBURGFlow_75.setLineWidth(3)
		HARRISBURGFlow_75 = HARO_Plot.getCurve(HARO75Flow)
		HARRISBURGFlow_75.setLineColor("cyan")
		HARRISBURGFlow_75.setLineStyle("solid")
		HARRISBURGFlow_75.setLineWidth(3)
		
		HARRISBURGFlow_25 = HARO_Plot.getCurve(HARO25Flow)
		HARRISBURGFlow_25.setLineWidth(3)
		HARRISBURGFlow_25 = HARO_Plot.getCurve(HARO25Flow)
		HARRISBURGFlow_25.setLineColor("yellow")
		HARRISBURGFlow_25.setLineStyle("solid")
		HARRISBURGFlow_25.setLineWidth(3)        
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

		CGR_BR = AxisMarker()
		CGR_BR.axis = "Y"
		CGR_BR.value = "1635.0"
		CGR_BR.labelText = "CGR BoatRamps ~ 1635.0"
		CGR_BR.labelPosition = "above"
		CGR_BR.labelColor = "black"
		CGR_BR.labelFont = "Dialog,BOLD,14";
		CGR_BR.lineColor = "black"
		CGR_BR.lineStyle = "dot"
		CGR_BR.lineWidth = 4
		TopViewport_CGR.addAxisMarker(CGR_BR)		


		
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
        
		Meridian = AxisMarker()
		Meridian.axis = "Y"
		Meridian.value = "911"
		Meridian.labelText = "Meridian Hampton ~ 911"
		Meridian.labelPosition = "above"
		Meridian.labelColor = "black"
		Meridian.labelFont = "Dialog,BOLD,14";
		Meridian.lineColor = "black"
		Meridian.lineStyle = "dot"
		Meridian.lineWidth = 4
		TopViewport_LOP.addAxisMarker(Meridian)

		Black_Canyon = AxisMarker()
		Black_Canyon.axis = "Y"
		Black_Canyon.value = "900.0"
		Black_Canyon.labelText = "Black_Canyon BR ~ 900"
		Black_Canyon.labelPosition = "above"
		Black_Canyon.labelColor = "black"
		Black_Canyon.labelFont = "Dialog,BOLD,14";
		Black_Canyon.lineColor = "black"
		Black_Canyon.lineStyle = "dot"
		Black_Canyon.lineWidth = 4
		TopViewport_LOP.addAxisMarker(Black_Canyon)        

		Signal_point = AxisMarker()
		Signal_point.axis = "Y"
		Signal_point.value = "821.0"
		Signal_point.labelText = "Signal_point BR ~ 821"
		Signal_point.labelPosition = "below"
		Signal_point.labelColor = "black"
		Signal_point.labelFont = "Dialog,BOLD,14";
		Signal_point.lineColor = "black"
		Signal_point.lineStyle = "dot"
		Signal_point.lineWidth = 4
		TopViewport_LOP.addAxisMarker(Signal_point)       
        
        
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

		Bingham_BR = AxisMarker()
		Bingham_BR.axis = "Y"
		Bingham_BR.value = "1520"
		Bingham_BR.labelText = "Bing BR ~ 1520"
		Bingham_BR.labelPosition = "above"
		Bingham_BR.labelColor = "black"
		Bingham_BR.labelFont = "Dialog,BOLD,14";
		Bingham_BR.lineColor = "black"
		Bingham_BR.lineStyle = "dot"
		Bingham_BR.lineWidth = 4
		TopViewport_HCR.addAxisMarker(Bingham_BR)
		
		CTBeach_BR = AxisMarker()
		CTBeach_BR.axis = "Y"
		CTBeach_BR.value = "1507"
		CTBeach_BR.labelText = "CTBeach BR ~ 1507"
		CTBeach_BR.labelPosition = "above"
		CTBeach_BR.labelColor = "black"
		CTBeach_BR.labelFont = "Dialog,BOLD,14";
		CTBeach_BR.lineColor = "black"
		CTBeach_BR.lineStyle = "dot"
		CTBeach_BR.lineWidth = 4
		TopViewport_HCR.addAxisMarker(CTBeach_BR) 

		Packard_BR = AxisMarker()
		Packard_BR.axis = "Y"
		Packard_BR.value = "1441"
		Packard_BR.labelText = "Packard BR ~ 1441"
		Packard_BR.labelPosition = "above"
		Packard_BR.labelColor = "black"
		Packard_BR.labelFont = "Dialog,BOLD,14";
		Packard_BR.lineColor = "black"
		Packard_BR.lineStyle = "dot"
		Packard_BR.lineWidth = 4
		TopViewport_HCR.addAxisMarker(Packard_BR)        
        
        
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
        
        
        
		Cascara_BR = AxisMarker()
		Cascara_BR.axis = "Y"
		Cascara_BR.value = "815"
		Cascara_BR.labelText = "Cascara BR ~ 815"
		Cascara_BR.labelPosition = "above"
		Cascara_BR.labelColor = "black"
		Cascara_BR.labelFont = "Dialog,BOLD,14";
		Cascara_BR.lineColor = "black"
		Cascara_BR.lineStyle = "dot"
		Cascara_BR.lineWidth = 4
		TopViewport_FAL.addAxisMarker(Cascara_BR)    

		Winberry_BR = AxisMarker()
		Winberry_BR.axis = "Y"
		Winberry_BR.value = "803"
		Winberry_BR.labelText = "Winberry BR ~ 803"
		Winberry_BR.labelPosition = "above"
		Winberry_BR.labelColor = "black"
		Winberry_BR.labelFont = "Dialog,BOLD,14";
		Winberry_BR.lineColor = "black"
		Winberry_BR.lineStyle = "dot"
		Winberry_BR.lineWidth = 4
		TopViewport_FAL.addAxisMarker(Winberry_BR)  

		NorthShore_BR = AxisMarker()
		NorthShore_BR.axis = "Y"
		NorthShore_BR.value = "729"
		NorthShore_BR.labelText = "NorthShore BR ~ 729"
		NorthShore_BR.labelPosition = "above"
		NorthShore_BR.labelColor = "black"
		NorthShore_BR.labelFont = "Dialog,BOLD,14";
		NorthShore_BR.lineColor = "black"
		NorthShore_BR.lineStyle = "dot"
		NorthShore_BR.lineWidth = 4
		TopViewport_FAL.addAxisMarker(NorthShore_BR) 

		
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
        
        
		LookOut_BR= AxisMarker()
		LookOut_BR.axis = "Y"
		LookOut_BR.value = "1330"
		LookOut_BR.labelText = "LookOut BR ~ 1330"
		LookOut_BR.labelPosition = "above"
		LookOut_BR.labelColor = "black"
		LookOut_BR.labelFont = "Dialog,BOLD,14";
		LookOut_BR.lineColor = "black"
		LookOut_BR.lineStyle = "dot"
		LookOut_BR.lineWidth = 4
		TopViewport_BLR.addAxisMarker(LookOut_BR)  

		SaddleDam_BR = AxisMarker()
		SaddleDam_BR.axis = "Y"
		SaddleDam_BR.value = "1295"
		SaddleDam_BR.labelText = "SaddleDam BR ~ 1295"
		SaddleDam_BR.labelPosition = "above"
		SaddleDam_BR.labelColor = "black"
		SaddleDam_BR.labelFont = "Dialog,BOLD,14";
		SaddleDam_BR.lineColor = "black"
		SaddleDam_BR.lineStyle = "dot"
		SaddleDam_BR.lineWidth = 4
		TopViewport_BLR.addAxisMarker(SaddleDam_BR)  
		
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

        

        
		HarmsPark_BR = AxisMarker()
		HarmsPark_BR.axis = "Y"
		HarmsPark_BR.value = "820"
		HarmsPark_BR.labelText = "HarmsPark BR ~ 820"
		HarmsPark_BR.labelPosition = "above"
		HarmsPark_BR.labelColor = "black"
		HarmsPark_BR.labelFont = "Dialog,BOLD,14";
		HarmsPark_BR.lineColor = "black"
		HarmsPark_BR.lineStyle = "dot"
		HarmsPark_BR.lineWidth = 4
		TopViewport_DOR.addAxisMarker(HarmsPark_BR)  


		BB_BR = AxisMarker()
		BB_BR.axis = "Y"
		BB_BR.value = "765"
		BB_BR.labelText = "Baker Bay BR ~ 765"
		BB_BR.labelPosition = "above"
		BB_BR.labelColor = "black"
		BB_BR.labelFont = "Dialog,BOLD,14";
		BB_BR.lineColor = "black"
		BB_BR.lineStyle = "dot"
		BB_BR.lineWidth = 4
		TopViewport_DOR.addAxisMarker(BB_BR)  
		
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

		WilsonCreek_BR = AxisMarker()
		WilsonCreek_BR.axis = "Y"
		WilsonCreek_BR.value = "779"
		WilsonCreek_BR.labelText = "Wilson Creek BR ~ 779"
		WilsonCreek_BR.labelPosition = "above"
		WilsonCreek_BR.labelColor = "black"
		WilsonCreek_BR.labelFont = "Dialog,BOLD,14";
		WilsonCreek_BR.lineColor = "black"
		WilsonCreek_BR.lineStyle = "dot"
		WilsonCreek_BR.lineWidth = 4
		TopViewport_COT.addAxisMarker(WilsonCreek_BR)

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
        
		TopViewport_LOP.addAxisMarker(CurrentTime)                    
		BottomViewport_LOP.addAxisMarker(CurrentTime) 		
		TopViewport_GPR.addAxisMarker(CurrentTime)                    
		BottomViewport_GPR.addAxisMarker(CurrentTime) 		
		TopViewport_CGR.addAxisMarker(CurrentTime)                    
		BottomViewport_CGR.addAxisMarker(CurrentTime) 
		TopViewport_DET.addAxisMarker(CurrentTime)                    
		BottomViewport_DET.addAxisMarker(CurrentTime) 

###### Save Plot as A jpeg####


		LOP_Plot.setSize(1400, 1300)
		LOP_Plot.setLocation(100, 100)
		LOP_Plot.saveToJpeg("W:\LOP_FcstPlot.jpg")
		LOP_Plot.close()
		
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
		
		HCR_Plot.setSize(1400, 1300)
		HCR_Plot.setLocation(100, 100)
		HCR_Plot.saveToJpeg("W:\HCR_FcstPlot.jpg")
		HCR_Plot.close()
		
		FRN_Plot.setSize(1400, 1300)
		FRN_Plot.setLocation(100, 100)
		FRN_Plot.saveToJpeg("W:\FRN_FcstPlot.jpg")
		FRN_Plot.close()
		
		FAL_Plot.setSize(1400, 1300)
		FAL_Plot.setLocation(100, 100)
		FAL_Plot.saveToJpeg("W:\FAL_FcstPlot.jpg")
		FAL_Plot.close()
		
		DOR_Plot.setSize(1400, 1300)
		DOR_Plot.setLocation(100, 100)
		DOR_Plot.saveToJpeg("W:\DOR_FcstPlot.jpg")
		DOR_Plot.close()

		COT_Plot.setSize(1400, 1300)
		COT_Plot.setLocation(100, 100)
		COT_Plot.saveToJpeg("W:\COT_FcstPlot.jpg")
		COT_Plot.close()
				
		BLR_Plot.setSize(1400, 1300)
		BLR_Plot.setLocation(100, 100)
		BLR_Plot.saveToJpeg("W:\BLR_FcstPlot.jpg")
		BLR_Plot.close()
			
		CGR_Plot.setSize(1400, 1300)
		CGR_Plot.setLocation(100, 100)
		CGR_Plot.saveToJpeg("W:\CGR_FcstPlot.jpg")
		CGR_Plot.close()
		
		SALO_Plot.setSize(1400, 1300)
		SALO_Plot.setLocation(100, 100)
		SALO_Plot.saveToJpeg("W:\SALO_FcstPlot.jpg")
		SALO_Plot.close()	

		ALBO_Plot.setSize(1400, 1300)
		ALBO_Plot.setLocation(100, 100)
		ALBO_Plot.saveToJpeg("W:\ALBO_FcstPlot.jpg")
		ALBO_Plot.close()
        
		EUGO_Plot.setSize(1400, 1300)
		EUGO_Plot.setLocation(100, 100)
		EUGO_Plot.saveToJpeg("W:\EUGO_FcstPlot.jpg")
		EUGO_Plot.close()	     
        
		HARO_Plot.setSize(1400, 1300)
		HARO_Plot.setLocation(100, 100)
		HARO_Plot.saveToJpeg("W:\HARO_FcstPlot.jpg")
		HARO_Plot.close()

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
