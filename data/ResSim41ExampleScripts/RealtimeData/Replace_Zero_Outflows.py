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
from hec.heclib.util                  import HecDouble

import DBAPI, datetime, time, calendar, inspect, java, os, sys, traceback, math, shutil, logging, getpass
import javax.swing.JFrame;
import java.lang
from com.rma.client import Browser
from hec.script     import *
import os, string, time
#**************************************************************************************************
# Open the DSS File
#
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
#**************************************************************************************************
# Read pathnames, apply replaceSpecificValues function, and write back out to DSS
#
pathnamesList = [	"/WILLAMETTE/BIG CLIFF/FLOW-GEN//1HOUR/OBSERVED/",
					"/WILLAMETTE/COUGAR/FLOW-GEN//1HOUR/OBSERVED/",
					"/WILLAMETTE/DETROIT/FLOW-GEN//1HOUR/OBSERVED/",
					"/WILLAMETTE/DEXTER/FLOW-GEN//1HOUR/OBSERVED/",
					"/WILLAMETTE/FOSTER/FLOW-GEN//1HOUR/OBSERVED/",
					"/WILLAMETTE/GREEN PETER/FLOW-GEN//1HOUR/OBSERVED/",
					"/WILLAMETTE/HILLS CREEK/FLOW-GEN//1HOUR/OBSERVED/",
					"/WILLAMETTE/LOOKOUT POINT/FLOW-GEN//1HOUR/OBSERVED/"
				]
duplicateRecords(PathnameList)
for pathname in range(len(pathnamesList)) :
	print "reading record pathname ...",pathnamesList[pathname]
	dataset = cwmsFile.read(pathnamesList[pathname])
	print "replacingSpecificValues ...", fromValue, "to", toValue
	modifiedDataset = dataset.replaceSpecificValues(fromValue,toValue)
	#print "writing record pathname ...",DSSPathname(modifiedDataset.getPath())
	cwmsFile.write(modifiedDataset)
	
cwmsFile.close()
print "\nProcess is Done!\n"
