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
		###25% STORAGE
		#BCLSTOR25 = cwmsFile.read("//BIG CLIFF-POOL/STOR/01JAN2023/1DAY/------20/")
		
		BLUSTOR25 = cwmsFile.read("//BLUE RIVER-POOL/STOR/01JAN2023/1DAY/------20/")
		BLUSTOR25 = BLUSTOR25.add(-4000.00)
		#cwmsFile.write(BLUSTOR25)		
		COTSTOR25 = cwmsFile.read("//COTTAGE GROVE-POOL/STOR/01JAN2023/1DAY/------20/")
		COTSTOR25 = COTSTOR25.add(-3100.00)
		#cwmsFile.write(COTSTOR25)		
		CGRSTOR25 = cwmsFile.read("//COUGAR-POOL/STOR/01JAN2023/1DAY/------20/")
		CGRSTOR25 = CGRSTOR25.add(-52200.00)
		#cwmsFile.write(CGRSTOR25)		
		DETSTOR25 = cwmsFile.read("//DETROIT-POOL/STOR/01JAN2023/1DAY/------20/")
		DETSTOR25 = DETSTOR25.add(-148300.00)
		#cwmsFile.write(DETSTOR25)			
		DEXSTOR25 = cwmsFile.read("//DEXTER-POOL/STOR/01JAN2023/1DAY/------20/")
		DEXSTOR25 = DEXSTOR25.add(-22500.00)
		#cwmsFile.write(DEXSTOR25)		
		DORSTOR25 = cwmsFile.read("//DORENA-POOL/STOR/01JAN2023/1DAY/------20/")
		DORSTOR25 = DORSTOR25.add(-7100.00)
		#cwmsFile.write(DORSTOR25)		
		FALSTOR25 = cwmsFile.read("//FALL CREEK-POOL/STOR/01JAN2023/1DAY/------20/")
		FALSTOR25 = FALSTOR25.add(-9500.00)
		#cwmsFile.write(FALSTOR25)			
		FRNSTOR25 = cwmsFile.read("//FERN RIDGE-POOL/STOR/01JAN2023/1DAY/------20/")
		FRNSTOR25 = FRNSTOR25.add(-2800.00)
		#cwmsFile.write(FRNSTOR25)			
		FOSSTOR25 = cwmsFile.read("//FOSTER-POOL/STOR/01JAN2023/1DAY/------20/")
		FOSSTOR25 = FOSSTOR25.add(-31100.00)
		#cwmsFile.write(FOSSTOR25)		
		GPRSTOR25 = cwmsFile.read("//GREEN PETER-POOL/STOR/01JAN2023/1DAY/------20/")   
		GPRSTOR25 = GPRSTOR25.add(-159900.00)
		#cwmsFile.write(GPRSTOR25)		     
		HCRSTOR25 = cwmsFile.read("//HILLS CREEK-POOL/STOR/01JAN2023/1DAY/------20/")  
		HCRSTOR25 = HCRSTOR25.add(-155400.00)
		#cwmsFile.write(HCRSTOR25)	
		LOPSTOR25 = cwmsFile.read("//LOOKOUT POINT-POOL/STOR/01JAN2023/1DAY/------20/")        
		LOPSTOR25 = LOPSTOR25.add(-113600.00)
		#cwmsFile.write(LOPSTOR25)	        
		#BLUSTOR25.setVersion("25")




		
		SystemStorage_25 = COTSTOR25.add(CGRSTOR25).add(DETSTOR25).add(BLUSTOR25).add(CGRSTOR25).add(DORSTOR25).add(FALSTOR25).add(FOSSTOR25).add(GPRSTOR25).add(HCRSTOR25).add(LOPSTOR25).divide(1000000)        
		SystemStorage_25.setVersion("25% Forecast System Storage")
		SystemStorage_25.setLocation("")

		BLUSTOR50 = cwmsFile.read("//BLUE RIVER-POOL/STOR/01JAN2023/1DAY/------2050/")
		BLUSTOR50 = BLUSTOR50.add(-4000.00)
		#cwmsFile.write(BLUSTOR25)	//ABV HAYDEN BRIDGE_AT SPRINGFIELD/FLOW-LOCAL/01JAN2023/1DAY/------2050/
	
		COTSTOR50 = cwmsFile.read("//COTTAGE GROVE-POOL/STOR/01JAN2023/1DAY/------2050/50/")
		COTSTOR50 = COTSTOR50.add(-3100.00)
		#cwmsFile.write(COTSTOR25)		
		CGRSTOR50 = cwmsFile.read("//COUGAR-POOL/STOR/01JAN2023/1DAY/------2050/")
		CGRSTOR50 = CGRSTOR50.add(-52200.00)
		#cwmsFile.write(CGRSTOR25)		
		DETSTOR50 = cwmsFile.read("//DETROIT-POOL/STOR/01JAN2023/1DAY/------2050//")
		DETSTOR50 = DETSTOR50.add(-148300.00)
		#cwmsFile.write(DETSTOR25)			
		DEXSTOR50 = cwmsFile.read("//DEXTER-POOL/STOR/01JAN2023/1DAY/------2050/")
		DEXSTOR50 = DEXSTOR50.add(-22500.00)
		#cwmsFile.write(DEXSTOR25)		
		DORSTOR50 = cwmsFile.read("//DORENA-POOL/STOR/01JAN2023/1DAY/------2050/")
		DORSTOR50 = DORSTOR50.add(-7100.00)
		#cwmsFile.write(DORSTOR25)		
		FALSTOR50 = cwmsFile.read("//FALL CREEK-POOL/STOR/01JAN2023/1DAY/------2050/")
		FALSTOR50 = FALSTOR50.add(-9500.00)
		#cwmsFile.write(FALSTOR25)			
		FRNSTOR50 = cwmsFile.read("//FERN RIDGE-POOL/STOR/01JAN2023/1DAY/------2050/")
		FRNSTOR50 = FRNSTOR50.add(-2800.00)
		#cwmsFile.write(FRNSTOR25)			
		FOSSTOR50 = cwmsFile.read("//FOSTER-POOL/STOR/01JAN2023/1DAY/------2050/")
		FOSSTOR50 = FOSSTOR50.add(-31100.00)
		#cwmsFile.write(FOSSTOR25)		
		GPRSTOR50 = cwmsFile.read("//GREEN PETER-POOL/STOR/01JAN2023/1DAY/------2050/")   
		GPRSTOR50 = GPRSTOR50.add(-159900.00)
		#cwmsFile.write(GPRSTOR25)		     
		HCRSTOR50 = cwmsFile.read("//HILLS CREEK-POOL/STOR/01JAN2023/1DAY/------2050/")  
		HCRSTOR50 = HCRSTOR50.add(-155400.00)
		#cwmsFile.write(HCRSTOR25)	
		LOPSTOR50 = cwmsFile.read("//LOOKOUT POINT-POOL/STOR/01JAN2023/1DAY/------2050/")        
		LOPSTOR50 = LOPSTOR50.add(-113600.00)
		#cwmsFile.write(LOPSTOR25)	        
		#BLUSTOR25.setVersion("25")

		


		
		SystemStorage_50 = COTSTOR50.add(CGRSTOR50).add(DETSTOR50).add(BLUSTOR50).add(CGRSTOR50).add(DORSTOR50).add(FALSTOR50).add(FOSSTOR50).add(GPRSTOR50).add(HCRSTOR50).add(LOPSTOR50).divide(1000000)        
		SystemStorage_50.setVersion("50% Forecast System Storage")
		SystemStorage_50.setLocation("")

		BLUSTOR75 = cwmsFile.read("//BLUE RIVER-POOL/STOR/01JAN2023/1DAY/------205070/")
		BLUSTOR75 = BLUSTOR75.add(-4000.00)
		#cwmsFile.write(BLUSTOR75)		
		COTSTOR75 = cwmsFile.read("//COTTAGE GROVE-POOL/STOR/01JAN2023/1DAY/------205070/")
		COTSTOR75 = COTSTOR75.add(-3100.00)
		#cwmsFile.write(COTSTOR75)		
		CGRSTOR75 = cwmsFile.read("//COUGAR-POOL/STOR/01JAN2023/1DAY/------205070/")
		CGRSTOR75 = CGRSTOR75.add(-52200.00)
		#cwmsFile.write(CGRSTOR75)		
		DETSTOR75 = cwmsFile.read("//DETROIT-POOL/STOR/01JAN2023/1DAY/------205070/")
		DETSTOR75 = DETSTOR75.add(-148300.00)
		#cwmsFile.write(DETSTOR75)			
		DEXSTOR75 = cwmsFile.read("//DEXTER-POOL/STOR/01JAN2023/1DAY/------205070/")
		DEXSTOR75 = DEXSTOR75.add(-27500.00)
		#cwmsFile.write(DEXSTOR75)		
		DORSTOR75 = cwmsFile.read("//DORENA-POOL/STOR/01JAN2023/1DAY/------205070/")
		DORSTOR75 = DORSTOR75.add(-7100.00)
		#cwmsFile.write(DORSTOR75)		
		FALSTOR75 = cwmsFile.read("//FALL CREEK-POOL/STOR/01JAN2023/1DAY/------205070/")
		FALSTOR75 = FALSTOR75.add(-9500.00)
		#cwmsFile.write(FALSTOR75)			
		FRNSTOR75 = cwmsFile.read("//FERN RIDGE-POOL/STOR/01JAN2023/1DAY/------205070/")
		FRNSTOR75 = FRNSTOR75.add(-2800.00)
		#cwmsFile.write(FRNSTOR75)			
		FOSSTOR75 = cwmsFile.read("//FOSTER-POOL/STOR/01JAN2023/1DAY/------205070/")
		FOSSTOR75 = FOSSTOR75.add(-31100.00)
		#cwmsFile.write(FOSSTOR75)		
		GPRSTOR75 = cwmsFile.read("//GREEN PETER-POOL/STOR/01JAN2023/1DAY/------205070/")   
		GPRSTOR75 = GPRSTOR75.add(-159900.00)
		#cwmsFile.write(GPRSTOR75)		     
		HCRSTOR75 = cwmsFile.read("//HILLS CREEK-POOL/STOR/01JAN2023/1DAY/------205070/")  
		HCRSTOR75 = HCRSTOR75.add(-155400.00)
		#cwmsFile.write(HCRSTOR75)	
		LOPSTOR75 = cwmsFile.read("//LOOKOUT POINT-POOL/STOR/01JAN2023/1DAY/------205070/")        
		LOPSTOR75 = LOPSTOR75.add(-113600.00)
		#cwmsFile.write(LOPSTOR75)	        
		#BLUSTOR75.setVersion("75")

	
		SystemStorage_75 = COTSTOR75.add(CGRSTOR75).add(DETSTOR75).add(BLUSTOR75).add(CGRSTOR75).add(DORSTOR75).add(FALSTOR75).add(FOSSTOR75).add(GPRSTOR75).add(HCRSTOR75).add(LOPSTOR75).divide(1000000)        
		SystemStorage_75.setVersion("75% Forecast System Storage")
		SystemStorage_75.setLocation("")		

		WILSTORRuleCurveN = cwmsFile.get("/WILLAMETTE//STOR/01JAN2024/1DAY/CENWP-CALC/")
    
### Create Plot ####
		SystemStorage_25 = SystemStorage_25.getData()
		SystemStorage_50 = SystemStorage_50.getData()
		SystemStorage_75 = SystemStorage_75.getData()

	
		SystemStorage_Plot = Plot.newPlot("System Storage Forecast")
		Layout = Plot.newPlotLayout()
		TopView = Layout.addViewport(100)
		TopView.addCurve("Y1", SystemStorage_25)
		TopView.addCurve("Y1", SystemStorage_50)
		TopView.addCurve("Y1", SystemStorage_75)
		TopView.addCurve("Y1", WILSTORRuleCurveN)
		
		#TopView.addCurve("Y1", FOS25ADJ)
		#TopView.addCurve("Y1", GPR25ADJ)
		#TopView.addCurve("Y1", DET25ADJ)
		#TopView.addCurve("Y1", HCR25ADJ)
		#TopView.addCurve("Y1", DOR25ADJ)
		#TopView.addCurve("Y1", LOP25ADJ)
		#TopView.addCurve("Y1", FAL25ADJ)
		#TopView.addCurve("Y1", DEX25ADJ)
       # TopView.addCurve("Y1", CGR25ADJ)    
		SystemStorage_Plot.configurePlotLayout(Layout)
		SystemStorage_Plot.showPlot()    




				
####### Plot Line Styles####
	
		Storage_25 = SystemStorage_Plot.getCurve(SystemStorage_25)
		Storage_25.setLineWidth(6)
		Storage_25 = SystemStorage_Plot.getCurve(SystemStorage_25)
		Storage_25.setLineColor("yellow")
		Storage_25.setLineStyle("solid")
		Storage_25.setLineWidth(3)

		Storage_50 = SystemStorage_Plot.getCurve(SystemStorage_50)
		Storage_50.setLineWidth(6)
		Storage_50 = SystemStorage_Plot.getCurve(SystemStorage_50)
		Storage_50.setLineColor("green")
		Storage_50.setLineStyle("solid")
		Storage_50.setLineWidth(3)

		Storage_75 = SystemStorage_Plot.getCurve(SystemStorage_75)
		Storage_75.setLineWidth(3)
		Storage_75 = SystemStorage_Plot.getCurve(SystemStorage_75)
		Storage_75.setLineColor("cyan")
		Storage_75.setLineStyle("Solid")
		Storage_75.setLineWidth(3)

		WILstorRuleCurve = SystemStorage_Plot.getCurve(WILSTORRuleCurveN)
		WILstorRuleCurve.setLineWidth(3)
		WILstorRuleCurve = SystemStorage_Plot.getCurve(WILSTORRuleCurveN)
		WILstorRuleCurve.setLineColor("black")
		WILstorRuleCurve.setLineStyle("Solid")
		WILstorRuleCurve.setLineWidth(3)
       
#####Axis Formating####
		TopViewport_SysST = SystemStorage_Plot.getViewport(0)
		Top_Y_Axis = TopViewport_SysST.getAxis("Y1")
		Top_Y_AxisLabel = TopViewport_SysST .getAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_SysST .getAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(.1)
		Top_Y_Axis.setLabel("System Storage (MAF)")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(14, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.getProperties()
		TopTicProps.setMajorTicFontStyle(1)

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

		TopViewport_SysST = SystemStorage_Plot.getViewport(0) 		
		TopViewport_SysST.addAxisMarker(CurrentTime)         
###### Save Plot as A jpeg####


		SystemStorage_Plot.setSize(1400, 1300)
		SystemStorage_Plot.setLocation(100, 100)
		SystemStorage_Plot.saveToJpeg("Z:\SystemStorage.jpg")
		SystemStorage_Plot.close()

		


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
