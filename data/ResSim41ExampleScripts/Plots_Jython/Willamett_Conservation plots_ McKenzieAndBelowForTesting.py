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
		HCRLBElev = cwmsFile.get("/WILLAMETTE/HILLS CREEK/ELEV(29)/01DEC2022/1HOUR/OBSERVED/")
		OBS25HCRElev = cwmsFile.read("//HILLS CREEK-POOL/ELEV/01JAN2023/1DAY/------20/")
		OBS25HCRElev.setVersion("25% Flow Forecast")
		Sim25HCRInflow = cwmsFile.read("//HILLS CREEK-POOL/FLOW-IN/01JAN2023/1DAY/------20/")
		Sim25HCRInflow.setVersion("25% Flow Forecast")
		Sim25HCROutflow = cwmsFile.read("//HILLS CREEK-POOL/FLOW-OUT/01JAN2023/1DAY/------20/")
		Sim25HCROutflow.setVersion("25% Flow Forecast")
		HCR25RuleCurve = cwmsFile.read("//HILLS CREEK-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/------20/")
		HCR25RuleCurve.setVersion("25% Flow Forecast")
		HCRRuleCurveN = cwmsFile.get("//HCR/ELEV-RULECURVE/01OCT2023/IR-MONTH/CENWP-CALC/")
		
		OBSHCRElev = cwmsFile.read("//HILLS CREEK-POOL/ELEV/01JAN2023/1DAY/------2050/")
		OBSHCRElev.setVersion("50% Flow Forecast")
		SimHCRInflow = cwmsFile.read("//HILLS CREEK-POOL/FLOW-IN/01JAN2023/1DAY/------2050/")
		SimHCRInflow.setVersion("50% Flow Forecast")
		SimHCROutflow = cwmsFile.read("//HILLS CREEK-POOL/FLOW-OUT/01JAN2023/1DAY/------2050/")
		SimHCROutflow.setVersion("50% Flow Forecast")
		HCRRuleCurve = cwmsFile.read("//HILLS CREEK-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/------2050/")
		HCRRuleCurve.setVersion("50% Flow Forecast")
		HCRRuleCurveN = cwmsFile.get("//HCR/ELEV-RULECURVE/01OCT2023/IR-MONTH/CENWP-CALC/")
		
		OBS75HCRElev = cwmsFile.read("//HILLS CREEK-POOL/ELEV/01JAN2023/1DAY/------205070/")
		OBS75HCRElev.setVersion("75% Flow Forecast")
		Sim75HCRInflow = cwmsFile.read("//HILLS CREEK-POOL/FLOW-IN/01JAN2023/1DAY/------205070/")
		Sim75HCRInflow.setVersion("75% Flow Forecast")
		Sim75HCROutflow = cwmsFile.read("//HILLS CREEK-POOL/FLOW-OUT/01JAN2023/1DAY/------205070/")
		Sim75HCROutflow.setVersion("75% Flow Forecast")
		HCRRuleCurve = cwmsFile.read("//HILLS CREEK-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/------205070/")
		HCRRuleCurve.setVersion("75% Flow Forecast")
		HCRRuleCurveN = cwmsFile.get("//HCR/ELEV-RULECURVE/01OCT2023/IR-MONTH/CENWP-CALC/")

		OBS25HCRElev = OBS25HCRElev.getData()
		Sim25HCRInflow = Sim25HCRInflow.getData()
		Sim25HCROutflow = Sim25HCROutflow.getData()
		HCR25RuleCurve = HCR25RuleCurve.getData()
		
		OBSHCRElev = OBSHCRElev.getData()
		SimHCRInflow = SimHCRInflow.getData()
		SimHCROutflow = SimHCROutflow.getData()
		HCRRuleCurve = HCRRuleCurve.getData()
	
		OBS75HCRElev = OBS75HCRElev.getData()
		Sim75HCRInflow = Sim75HCRInflow.getData()
		Sim75HCROutflow = Sim75HCROutflow.getData()


        #LOP Below
        
        
		OBSLOPElev = cwmsFile.read("//LOOKOUT POINT-POOL/ELEV/01JAN2023/1DAY/------2050/")
		OBSLOPElev.setVersion("50% Flow Forecast")
		SimLOPInflow = cwmsFile.read("//LOOKOUT POINT-POOL/FLOW-IN/01JAN2023/1DAY/------2050/")
		SimLOPInflow.setVersion("50% Flow Forecast")
		SimLOPOutflow = cwmsFile.read("//LOOKOUT POINT-POOL/FLOW-OUT/01JAN2023/1DAY/------2050/")
		SimLOPOutflow.setVersion("25% Flow Forecast")
		LOPRuleCurve = cwmsFile.read("//LOOKOUT POINT-CONSERVATION/ELEV-ZONE//1DAY/------20/")
		LOPRuleCurve.setVersion("25% Flow Forecast")
		LOPLBElev = cwmsFile.get("/WILLAMETTE/LOOKOUT POINT/ELEV(29)/01DEC2022/1HOUR/OBSERVED/")



		OBS25LOPElev = cwmsFile.read("//LOOKOUT POINT-POOL/ELEV/01JAN2023/1DAY/------20/")
		OBS25LOPElev.setVersion("25% Flow Forecast")
		Sim25LOPInflow = cwmsFile.read("//LOOKOUT POINT-POOL/FLOW-IN/01JAN2023/1DAY/------20/")
		Sim25LOPInflow.setVersion("25% Flow Forecast")
		Sim25LOPOutflow = cwmsFile.read("//LOOKOUT POINT-POOL/FLOW-OUT/01JAN2023/1DAY/------20/")
		Sim25LOPOutflow.setVersion("25% Flow Forecast")

		
		LOPRuleCurveN = cwmsFile.get("//LOP/ELEV-RULECURVE/01JAN2023/IR-MONTH/CENWP-CALC/")
		OBS75LOPElev = cwmsFile.read("//LOOKOUT POINT-POOL/ELEV/01JAN2023/1DAY/------205070/")
		OBS75LOPElev.setVersion("75% Flow Forecast")
		Sim75LOPInflow = cwmsFile.read("//LOOKOUT POINT-POOL/FLOW-IN/01JAN2023/1DAY/------205070/")
		Sim75LOPInflow.setVersion("75% Flow Forecast")
		Sim75LOPOutflow = cwmsFile.read("//LOOKOUT POINT-POOL/FLOW-OUT/01JAN2023/1DAY/------205070/")
		Sim75LOPOutflow.setVersion("75% Flow Forecast")
		
		

		OBS25LOPElev = OBS25LOPElev.getData()
		Sim25LOPInflow = Sim25LOPInflow.getData()
		Sim25LOPOutflow = Sim25LOPOutflow.getData()
		
		
		OBSLOPElev = OBSLOPElev.getData()
		SimLOPInflow = SimLOPInflow.getData()
		SimLOPOutflow = SimLOPOutflow.getData()
		LOPRuleCurve = LOPRuleCurve.getData()
	
		OBS75LOPElev = OBS75LOPElev.getData()
		Sim75LOPInflow = Sim75LOPInflow.getData()
		Sim75LOPOutflow = Sim75LOPOutflow.getData()

		
		
		
		




		

		CGRLBElev = cwmsFile.get("/WILLAMETTE/COUGAR/ELEV(29)/01FEB2023/1HOUR/OBSERVED/")
		OBS25CGRElev = cwmsFile.read("//COUGAR-POOL/ELEV/01JAN2023/1DAY/------20/")
		OBS25CGRElev.setVersion("25% Flow Forecast")
		Sim25CGRInflow = cwmsFile.read("//COUGAR-POOL/FLOW-IN/01JAN2023/1DAY/------20/")
		Sim25CGRInflow.setVersion("25% Flow Forecast")
		Sim25CGROutflow = cwmsFile.read("//COUGAR-POOL/FLOW-OUT/01JAN2023/1DAY/------20/")
		Sim25CGROutflow.setVersion("25% Flow Forecast")
		CGRRuleCurve = cwmsFile.read("//COUGAR-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/------20/")
		CGRRuleCurve.setVersion("25% Flow Forecast")


		OBSCGRElev = cwmsFile.read("//COUGAR-POOL/ELEV/01JAN2023/1DAY/------2050/")
		OBSCGRElev.setVersion("50% Flow Forecast")
		SimCGRInflow = cwmsFile.read("//COUGAR-POOL/FLOW-IN/01JAN2023/1DAY/------2050/")
		SimCGRInflow.setVersion("50% Flow Forecast")
		SimCGROutflow = cwmsFile.read("//COUGAR-POOL/FLOW-OUT/01JAN2023/1DAY/------2050/")
		SimCGROutflow.setVersion("50% Flow Forecast")
		CGRRuleCurve = cwmsFile.read("//COUGAR-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/------2050/")
		CGRRuleCurve.setVersion("50% Flow Forecast")

		
		OBS75CGRElev = cwmsFile.read("//COUGAR-POOL/ELEV/01JAN2023/1DAY/------205070/")
		OBS75CGRElev.setVersion("75% Flow Forecast")
		Sim75CGRInflow = cwmsFile.read("//COUGAR-POOL/FLOW-IN/01JAN2023/1DAY/------205070/")
		Sim75CGRInflow.setVersion("75% Flow Forecast")
		Sim75CGROutflow = cwmsFile.read("//COUGAR-POOL/FLOW-OUT/01JAN2023/1DAY/------205070/")
		Sim75CGROutflow.setVersion("75% Flow Forecast")
		CGR75RuleCurve = cwmsFile.read("//COUGAR-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/------205070/")
		CGR75RuleCurve.setVersion("75% Flow Forecast")
		CGRRuleCurveN = cwmsFile.get("//CGR/ELEV-RULECURVE/01NOV2023/IR-MONTH/CENWP-CALC/")


		OBS25CGRElev = OBS25CGRElev.getData()
		Sim25CGRInflow = Sim25CGRInflow.getData()
		Sim25CGROutflow = Sim25CGROutflow.getData()
		
		
		OBSCGRElev = OBSCGRElev.getData()
		SimCGRInflow = SimCGRInflow.getData()
		SimCGROutflow = SimCGROutflow.getData()
		CGRRuleCurve = CGRRuleCurve.getData()
	
		OBS75CGRElev = OBS75CGRElev.getData()
		Sim75CGRInflow = Sim75CGRInflow.getData()
		Sim75CGROutflow = Sim75CGROutflow.getData()

				
		

		
		
		
		###FAL Below
		FALLBElev = cwmsFile.get("/WILLAMETTE/FALL CREEK/ELEV(29)/01APR2023/1HOUR/OBSERVED/")
		OBSFALElev = cwmsFile.read("//FALL CREEK-POOL/ELEV/01JAN2023/1DAY/------2050/")
		OBSFALElev.setVersion("50% Flow Forecast")
		SimFALInflow = cwmsFile.read("//FALL CREEK-POOL/FLOW-IN/01JAN2023/1DAY/------2050/")
		SimFALInflow.setVersion("50% Flow Forecast")
		SimFALOutflow = cwmsFile.read("//FALL CREEK-POOL/FLOW-OUT/01JAN2023/1DAY/------2050/")
		SimFALOutflow.setVersion("50% Flow Forecast")
		FALRuleCurve = cwmsFile.read("//FALL CREEK-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/------2050/")
		FALRuleCurve.setVersion("50% Flow Forecast")
		FALRuleCurveN = cwmsFile.read("//FAL/ELEV-RULECURVE/01APR2023/IR-MONTH/CENWP-CALC/")
		
		OBS25FALElev = cwmsFile.read("//FALL CREEK-POOL/ELEV/01JAN2023/1DAY/------20/")
		OBS25FALElev.setVersion("25% Flow Forecast")
		Sim25FALInflow = cwmsFile.read("//FALL CREEK-POOL/FLOW-IN/01JAN2023/1DAY/------20/")
		Sim25FALInflow.setVersion("25% Flow Forecast")
		Sim25FALOutflow = cwmsFile.read("//FALL CREEK-POOL/FLOW-OUT/01JAN2023/1DAY/------20/")
		Sim25FALOutflow.setVersion("25% Flow Forecast")
		FALRuleCurve = cwmsFile.read("//FALL CREEK-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/------20/")
		FALRuleCurve.setVersion("25% Flow Forecast")
		FALRuleCurveN = cwmsFile.get("//FAL/ELEV-RULECURVE/01APR2023/IR-MONTH/CENWP-CALC/")
		
		OBS50FALElev = cwmsFile.read("//FALL CREEK-POOL/ELEV/01JAN2023/1DAY/------2050/")
		OBS50FALElev.setVersion("50% Flow Forecast")
		OBS75FALElev = cwmsFile.read("//FALL CREEK-POOL/ELEV/01JAN2023/1DAY/------205070/")
		OBS75FALElev.setVersion("75% Flow Forecast")
		Sim50FALInflow = cwmsFile.read("//FALL CREEK-POOL/FLOW-IN/01JAN2023/1DAY/------2050/")
		Sim50FALInflow.setVersion("50% Flow Forecast")
		Sim50FALOutflow = cwmsFile.read("//FALL CREEK-POOL/FLOW-OUT/01JAN2023/1DAY/------2050/")
		Sim50FALOutflow.setVersion("50% Flow Forecast")
		Sim75FALInflow = cwmsFile.read("//FALL CREEK-POOL/FLOW-IN/01JAN2023/1DAY/------205070/")
		Sim75FALInflow.setVersion("75% Flow Forecast")
		Sim75FALOutflow = cwmsFile.read("//FALL CREEK-POOL/FLOW-OUT/01JAN2023/1DAY/------205070/")
		Sim75FALOutflow.setVersion("75% Flow Forecast")

		

		OBS25FALElev = OBS25FALElev.getData()
		Sim25FALInflow = Sim25FALInflow.getData()
		Sim25FALOutflow = Sim25FALOutflow.getData()

		
		OBSFALElev = OBSFALElev.getData()
		SimFALInflow = SimFALInflow.getData()
		SimFALOutflow = SimFALOutflow.getData()
		FALRuleCurve = FALRuleCurve.getData()
	
		OBS75FALElev = OBS75FALElev.getData()
		Sim75FALInflow = Sim75FALInflow.getData()
		Sim75FALOutflow = Sim75FALOutflow.getData()

				
		
		
		
		

		
		
		
		BLRLBElev = cwmsFile.get("/WILLAMETTE/BLUE RIVER/ELEV(29)/01FEB2023/1HOUR/OBSERVED/")
		OBS25BLRElev = cwmsFile.read("//BLUE RIVER-POOL/ELEV/01JAN2023/1DAY/------20/")
		OBS25BLRElev.setVersion("25% Flow Forecast")
		Sim25BLRInflow = cwmsFile.read("//BLUE RIVER-POOL/FLOW-IN/01JAN2023/1DAY/------20/")
		Sim25BLRInflow.setVersion("25% Flow Forecast")
		Sim25BLROutflow = cwmsFile.read("//BLUE RIVER-POOL/FLOW-OUT/01JAN2023/1DAY/------20/")
		Sim25BLROutflow.setVersion("25% Flow Forecast")
		BLRRuleCurve = cwmsFile.read("//BLUE RIVER-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/------20/")
		BLRRuleCurve.setVersion("25% Flow Forecast")
		BLRRuleCurveN = cwmsFile.get("//BLU/ELEV-RULECURVE/01APR2023/IR-MONTH/CENWP-CALC/")
		
		OBSBLRElev = cwmsFile.read("//BLUE RIVER-POOL/ELEV/01JAN2023/1DAY/------2050/")
		OBSBLRElev.setVersion("50% Flow Forecast")
		SimBLRInflow = cwmsFile.read("//BLUE RIVER-POOL/FLOW-IN/01JAN2023/1DAY/------2050/")
		SimBLRInflow.setVersion("50% Flow Forecast")
		SimBLROutflow = cwmsFile.read("//BLUE RIVER-POOL/FLOW-OUT/01JAN2023/1DAY/------2050/")
		SimBLROutflow.setVersion("50% Flow Forecast")
		BLRRuleCurve = cwmsFile.read("//BLUE RIVER-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/------2050/")
		BLRRuleCurve.setVersion("50% Flow Forecast")

		
		OBS75BLRElev = cwmsFile.read("//BLUE RIVER-POOL/ELEV/01JAN2023/1DAY/------205070/")
		OBS75BLRElev.setVersion("75% Flow Forecast")
		Sim75BLRInflow = cwmsFile.read("//BLUE RIVER-POOL/FLOW-IN/01JAN2023/1DAY/------205070/")
		Sim75BLRInflow.setVersion("75% Flow Forecast")
		Sim75BLROutflow = cwmsFile.read("//BLUE RIVER-POOL/FLOW-OUT/01JAN2023/1DAY/------205070/")
		Sim75BLROutflow.setVersion("75% Flow Forecast")
		BLRRuleCurve = cwmsFile.read("//BLUE RIVER-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/------205070/")
		BLRRuleCurve.setVersion("75% Flow Forecast")


		OBS25BLRElev = OBS25BLRElev.getData()
		Sim25BLRInflow = Sim25BLRInflow.getData()
		Sim25BLROutflow.getData()

		
		OBSBLRElev = OBSBLRElev.getData()
		SimBLRInflow = SimBLRInflow.getData()
		SimBLROutflow = SimBLROutflow.getData()
		BLRRuleCurve = BLRRuleCurve.getData()
	
		OBS75BLRElev = OBS75BLRElev.getData()
		Sim75BLRInflow = Sim75BLRInflow.getData()
		Sim75BLROutflow = Sim75BLROutflow.getData()

								
				
		DORLBElev = cwmsFile.get("/WILLAMETTE/DORENA/ELEV(29)/01DEC2022/1HOUR/OBSERVED/")
		OBS25DORElev = cwmsFile.read("//DORENA-POOL/ELEV/01JAN2023/1DAY/------20/")
		OBS25DORElev.setVersion("25% Flow Forecast")
		Sim25DORInflow = cwmsFile.read("//DORENA-POOL/FLOW-IN/01JAN2023/1DAY/------20/")
		Sim25DORInflow.setVersion("25% Flow Forecast")
		Sim25DOROutflow = cwmsFile.read("//DORENA-POOL/FLOW-OUT/01JAN2023/1DAY/------20/")
		Sim25DOROutflow.setVersion("25% Flow Forecast")
		DORRuleCurve = cwmsFile.read("//DORENA-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/------20/")
		DORRuleCurve.setVersion("25% Flow Forecast")
		DORRuleCurveN = cwmsFile.get("//DOR/ELEV-RULECURVE/01JUL2023/IR-MONTH/CENWP-CALC/")
		
		OBSDORElev = cwmsFile.read("//DORENA-POOL/ELEV/01JAN2023/1DAY/------2050/")
		OBSDORElev.setVersion("50% Flow Forecast")
		SimDORInflow = cwmsFile.read("//DORENA-POOL/FLOW-IN/01JAN2023/1DAY/------2050/")
		SimDORInflow.setVersion("50% Flow Forecast")
		SimDOROutflow = cwmsFile.read("//DORENA-POOL/FLOW-OUT/01JAN2023/1DAY/------2050/")
		SimDOROutflow.setVersion("50% Flow Forecast")
		DORRuleCurve = cwmsFile.read("//DORENA-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/------2050/")
		DORRuleCurve.setVersion("50% Flow Forecast")

		
		OBS75DORElev = cwmsFile.read("//DORENA-POOL/ELEV/01JAN2023/1DAY/------205070/")
		OBS75DORElev.setVersion("75% Flow Forecast")
		Sim75DORInflow = cwmsFile.read("//DORENA-POOL/FLOW-IN/01JAN2023/1DAY/------205070/")
		Sim75DORInflow.setVersion("75% Flow Forecast")
		Sim75DOROutflow = cwmsFile.read("//DORENA-POOL/FLOW-OUT/01JAN2023/1DAY/------205070/")
		Sim75DOROutflow.setVersion("75% Flow Forecast")
		DORRuleCurve = cwmsFile.read("//DORENA-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/------205070/")
		DORRuleCurve.setVersion("75% Flow Forecast")

		
		OBS25DORElev = OBS25DORElev.getData()
		Sim25DORInflow = Sim25DORInflow.getData()
		Sim25DOROutflow = Sim25DOROutflow.getData()

		
		OBSDORElev = OBSDORElev.getData()
		SimDORInflow = SimDORInflow.getData()
		SimDOROutflow = SimDOROutflow.getData()
		DORRuleCurve = DORRuleCurve.getData()
	
		OBS75DORElev = OBS75DORElev.getData()
		Sim75DORInflow = Sim75DORInflow.getData()
		Sim75DOROutflow = Sim75DOROutflow.getData()
	
				
		
		
		COTLBElev = cwmsFile.get("/WILLAMETTE/COTTAGE GROVE/ELEV(29)/01APR2023/1HOUR/OBSERVED/")
		OBS25COTElev = cwmsFile.read("//COTTAGE GROVE-POOL/ELEV/01JAN2023/1DAY/------20/")
		OBS25COTElev.setVersion("25% Flow Forecast")
		Sim25COTInflow = cwmsFile.read("//COTTAGE GROVE-POOL/FLOW-IN/01JAN2023/1DAY/------20/")
		Sim25COTInflow.setVersion("25% Flow Forecast")
		Sim25COTOutflow = cwmsFile.read("//COTTAGE GROVE-POOL/FLOW-OUT/01JAN2023/1DAY/------20/")
		Sim25COTOutflow.setVersion("25% Flow Forecast")
		COTRuleCurve = cwmsFile.read("//COTTAGE GROVE-CONSERVATION/ELEV-ZONE/01JAN2023/1DAY/------20/")
		COTRuleCurve.setVersion("25% Flow Forecast")
		COTRuleCurveN = cwmsFile.get("//COT/ELEV-RULECURVE//IR-MONTH/CENWP-CALC/")
		
		OBSCOTElev = cwmsFile.read("//COTTAGE GROVE-POOL/ELEV/01JAN2023/1DAY/------2050/")
		OBSCOTElev.setVersion("50% Flow Forecast")
		SimCOTInflow = cwmsFile.read("//COTTAGE GROVE-POOL/FLOW-IN/01JAN2023/1DAY/------2050/")
		SimCOTInflow.setVersion("50% Flow Forecast")
		SimCOTOutflow = cwmsFile.read("//COTTAGE GROVE-POOL/FLOW-OUT/01JAN2023/1DAY/------2050/")
		SimCOTOutflow.setVersion("50% Flow Forecast")

		
		
		OBS75COTElev = cwmsFile.read("//COTTAGE GROVE-POOL/ELEV/01JAN2023/1DAY/------205070/")
		OBS75COTElev.setVersion("75% Flow Forecast")
		Sim75COTInflow = cwmsFile.read("//COTTAGE GROVE-POOL/FLOW-IN/01JAN2023/1DAY/------205070/")
		Sim75COTInflow.setVersion("75% Flow Forecast")
		Sim75COTOutflow = cwmsFile.read("//COTTAGE GROVE-POOL/FLOW-OUT/01JAN2023/1DAY/------205070/")
		Sim75COTOutflow.setVersion("75% Flow Forecast")

		
		
		OBS25COTElev = OBS25COTElev.getData()
		Sim25COTInflow = Sim25COTInflow.getData()
		Sim25COTOutflow = Sim25COTOutflow.getData()

		
		OBSCOTElev = OBSCOTElev.getData()
		SimCOTInflow = SimCOTInflow.getData()
		SimCOTOutflow = SimCOTOutflow.getData()
		COTRuleCurve = COTRuleCurve.getData()
	
		OBS75COTElev = OBS75COTElev.getData()
		Sim75COTInflow = Sim75COTInflow.getData()
		Sim75COTOutflow = Sim75COTOutflow.getData()

				


		

		
		
		
		#WILLAMETTE FLOW DATA 

		SALO25Flow = cwmsFile.read("//WILLAMETTE_AT SALEM/FLOW/01JAN2023/1DAY/------20/")
		SALO25Flow.setVersion("25% Flow Forecast")
		SALOFlow = cwmsFile.read("//WILLAMETTE_AT SALEM/FLOW/01JAN2023/1DAY/------2050/")
		SALOFlow.setVersion("50% Flow Forecast")
		SALO75Flow = cwmsFile.read("//WILLAMETTE_AT SALEM/FLOW/01JAN2023/1DAY/------205070/")
		SALO75Flow.setVersion("75% Flow Forecast")
		BIOPMIN = cwmsFile.get("//SALEM BIOP MIN BY WY/FLOW-MIN/01JAN2023/1DAY/------2050/")
        #SALOOBS = cwmsFile.read("")

		ALBO25Flow = cwmsFile.read("//WILLAMETTE_AT ALBANY/FLOW/01JAN2023/1DAY/------20/")
		ALBO25Flow.setVersion("25% Flow Forecast")
		ALBOFlow = cwmsFile.read("//WILLAMETTE_AT ALBANY/FLOW/01JAN2023/1DAY/------2050/")
		ALBOFlow.setVersion("50% Flow Forecast")
		ALBO75Flow = cwmsFile.read("//WILLAMETTE_AT ALBANY/FLOW/01JAN2023/1DAY/------205070/")
		ALBO75Flow.setVersion("75% Flow Forecast")
		ALBOBIOPMIN = cwmsFile.get("//ALBANY BIOP MIN BY WY/FLOW-MIN/01JAN2023/1DAY/------2050/")
        #ALBOOBS = cwmsFile.read("")

		EUGO25Flow = cwmsFile.read("//WILLAMETTE_AT EUGENE/FLOW/01JAN2023/1DAY/------20/")
		EUGO25Flow.setVersion("25% Flow Forecast")
		EUGOFlow = cwmsFile.read("//WILLAMETTE_AT EUGENE/FLOW/01JAN2023/1DAY/------2050/")
		EUGOFlow.setVersion("50% Flow Forecast")
		EUGO75Flow = cwmsFile.read("//WILLAMETTE_AT EUGENE/FLOW/01JAN2023/1DAY/------205070/")
		EUGO75Flow.setVersion("75% Flow Forecast")

		HARO25Flow = cwmsFile.read("//WILLAMETTE_AT HARRISBURG/FLOW/01JAN2023/1DAY/------20/")
		HARO25Flow.setVersion("25% Flow Forecast")
		HAROFlow = cwmsFile.read("//WILLAMETTE_AT HARRISBURG/FLOW/01JAN2023/1DAY/------2050/")
		HAROFlow.setVersion("50% Flow Forecast")
		HARO75Flow = cwmsFile.read("//WILLAMETTE_AT HARRISBURG/FLOW/01JAN2023/1DAY/------205070/")
		HARO75Flow.setVersion("75% Flow Forecast")



		SALO25Flow = SALO25Flow.getData()
		SALOFlow = SALOFlow.getData()
		SALO75Flow = SALO75Flow.getData()
		ALBO25Flow = ALBO25Flow.getData()
		ALBOFlow = ALBOFlow.getData()
		ALBO75Flow = ALBO75Flow.getData()
		EUGO25Flow = EUGO25Flow.getData()
		EUGOFlow = EUGOFlow.getData()
		EUGO75Flow = EUGO75Flow.getData()
		HARO25Flow = HARO25Flow.getData()
		HAROFlow = HAROFlow.getData()
		HARO75Flow = HARO75Flow.getData()
		







        
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

		
		SALO_Plot = Plot.newPlot("Salem Flow Forecast")
		Layout = Plot.newPlotLayout()
		BottomView = Layout.addViewport(30)
		BottomView.addCurve("Y1", SALO25Flow)
		BottomView.addCurve("Y1", SALOFlow)
		BottomView.addCurve("Y1", SALO75Flow)
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


		
		SALEMFlow_50 = SALO_Plot.getCurve(SALOFlow)
		SALEMFlow_50.setLineWidth(3)
		SALEMFlow_50 = SALO_Plot.getCurve(SALOFlow)
		SALEMFlow_50.setLineColor("green")
		SALEMFlow_50.setLineStyle("solid")
		SALEMFlow_50.setLineWidth(3)

		SALEMFlow_75 = SALO_Plot.getCurve(SALO75Flow)
		SALEMFlow_75.setLineWidth(3)
		SALEMFlow_75 = SALO_Plot.getCurve(SALO75Flow)
		SALEMFlow_75.setLineColor("cyan")
		SALEMFlow_75.setLineStyle("solid")
		SALEMFlow_75.setLineWidth(3)
		
		SALEMFlow_25 = SALO_Plot.getCurve(SALO25Flow)
		SALEMFlow_25.setLineWidth(3)
		SALEMFlow_25 = SALO_Plot.getCurve(SALO25Flow)
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
        
		TopViewport_LOP.addAxisMarker(CurrentTime)                    
		BottomViewport_LOP.addAxisMarker(CurrentTime) 		
		TopViewport_HCR.addAxisMarker(CurrentTime)                    
		BottomViewport_HCR.addAxisMarker(CurrentTime) 		
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
		TopViewport_SALO.addAxisMarker(CurrentTime)   
		TopViewport_SALO.addAxisMarker(CurrentTime)   

        
###### Save Plot as A jpeg####


		LOP_Plot.setSize(1400, 1300)
		LOP_Plot.setLocation(100, 100)
		LOP_Plot.saveToJpeg("W:\LOP_FcstPlot.jpg")
		#LOP_Plot.close()
		
		
		HCR_Plot.setSize(1400, 1300)
		HCR_Plot.setLocation(100, 100)
		HCR_Plot.saveToJpeg("W:\HCR_FcstPlot.jpg")
		HCR_Plot.close()
		

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
		
############ Set Data up for exporting to Excel####
		datasets = java.util.Vector()
		
		#datasets.add(OBS25LOPElev)
		#datasets.add(Sim25LOPOutflow)
		datasets.add(OBSLOPElev)
		datasets.add(SimLOPOutflow)
		#datasets.add(OBS75LOPElev)
		#datasets.add(Sim75LOPOutflow)
		
		#datasets.add(OBS25HCRElev)
		#datasets.add(Sim25HCROutflow)
		datasets.add(OBSHCRElev)
		datasets.add(SimHCROutflow)
		#datasets.add(OBS75HCRElev)
		#datasets.add(Sim75HCROutflow)
		
		#datasets.add(OBS25FALElev)
		#datasets.add(Sim25FALOutflow)
		datasets.add(OBSFALElev)
		datasets.add(SimFALOutflow)
		#datasets.add(OBS75FALElev)
		#datasets.add(Sim75FALOutflow)
		
		#datasets.add(OBS25DORElev)
		#datasets.add(Sim25DOROutflow)
		datasets.add(OBSDORElev)
		datasets.add(SimDOROutflow)
		#datasets.add(OBS75DORElev)
		#datasets.add(Sim75DOROutflow)
		
		#datasets.add(OBS25COTElev)
		#datasets.add(Sim25COTOutflow)
		datasets.add(OBSCOTElev)
		datasets.add(SimCOTOutflow)
		#datasets.add(OBS75COTElev)
		#datasets.add(Sim75COTOutflow)

		#datasets.add(Sim25BLRElev)
		#datasets.add(Sim25BLROutflow)
		datasets.add(OBSBLRElev)
		datasets.add(SimBLROutflow)
		#datasets.add(OBS75BLRElev)
		#datasets.add(Sim75BLROutflow)
				
		#datasets.add(OBS25CGRElev)
		#datasets.add(Sim25CGROutflow)
		datasets.add(OBSCGRElev)
		datasets.add(SimCGROutflow)
		#datasets.add(OBS75CGRElev)
		#datasets.add(Sim75CGROutflow)

		datasets.add(SALOFlow)
		datasets.add(EUGOFlow)
						
		ExcelTable = HecDataTableToExcel.newTable()
		ExcelTable.createExcelFile(datasets,"W:\Fcst.xls")

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
