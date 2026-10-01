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


import DBAPI, datetime, time, calendar, inspect, java, os, sys, traceback, math, shutil, logging, getpass
import javax.swing.JFrame;
import java.lang
from com.rma.client import Browser
from hec.script     import *
import os, string, time
progname = None
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
		
def getOffsets(filename) :
	'''
	Reads the offsets from the "verticalDatumOffsets.txt" file in the base shared directory
	'''
	def parseLine(line) : 
		return map(string.strip, line.split("#")[2].strip().split(","))
		
	if not os.path.isfile(filename) : 
		error("No such file: %s" % filename)
		
	with open(filename, "r") as f : lines = f.read().strip().split("\n")
	offsets = {}
	transtable = string.maketrans("#,", "  ")
	for line in lines :
		line = line.strip().upper()
		if line.startswith("#29-88#") :
			bPart, offset = parseLine(line)
			offset = float(offset)
			offsets.setdefault(bPart, {})["29"] = offset
		elif line.startswith("LOCAL-88") :
			bPart, offset = parseLine(line)
			offset = float(offset)
			offsets.setdefault(bPart, {})["LOCAL"] = offset
	output()
	output("Offsets from %s:" % filename)
	for bPart in sorted(offsets.keys()) :
		for datum in sorted(offsets[bPart].keys()) :
			output("\t%s:\t%s to 88 = %s ft" % (bPart, datum, offsets[bPart][datum]))
	return offsets
def applyOffsets(dssfile, offsets) :
	'''
	applies the offsets to the forecast DSS file
	'''
	valueCount = recordCount = skipped = 0
	dss = HecDss.open(dssfile)
	try :
		records = {}
		for pn in sorted([p for p in dss.getPathnameList() if p.split("/")[3].startswith("ELEV")]) :
			bPart, cPart = pn.split("/")[2:4]
			if cPart.startswith("ELEV(29)") :
				records.setdefault(bPart, {}).setdefault("29", []).append(pn)
			elif cPart.startswith("ELEV(LOCAL)") :
				records.setdefault(bPart, {}).setdefault("LOCAL", []).append(pn)
			else :
				records.setdefault(bPart, {}).setdefault("NORMAL", []).append(pn)
		if progname == "29_to_88" :
			for bPart in sorted(records.keys()) :
				for datum in ("29", "LOCAL") :
					if records[bPart].has_key(datum) :
						if not offsets.has_key(bPart) or not offsets[bPart].has_key(datum) :
							output("No offset specified for %s for %s to 88, but records exist in forecast DSS file" % (bPart, datum))
							skipped += 1
							continue
						offset = offsets[bPart][datum]
						for pathname in records[bPart][datum] :
							tsc = dss.get(pathname)
							recordCount += 1
							for i in range(len(tsc.values)) :
								if tsc.values[i] != Constants.UNDEFINED :
									tsc.values[i] += offset
									valueCount += 1
							tsc.parameter = tsc.parameter.replace("ELEV(%s)" % datum, "ELEVATION")
							tsc.fullName = tsc.fullName.replace("ELEV(%s)" % datum, "ELEVATION")
							output("%s --> %s" % (pathname, tsc.fullName))
							dss.put(tsc)
		elif progname == "88_to_29" :
			for bPart in sorted(records.keys()) :
				if records[bPart].has_key("NORMAL") :
					if not offsets.has_key(bPart) :
						output("No offset specified for %s for 88 to 29 or local, but records exist in forecast DSS file" % bPart)
						skipped += 1
						continue
					for pathname in records[bPart]["NORMAL"] :
						for datum in ("29", "LOCAL") :
							if offsets[bPart].has_key(datum) :
								offset = offsets[bPart][datum]
								tsc = dss.get(pathname)
								recordCount += 1
								for i in range(len(tsc.values)) :
									if tsc.values[i] != Constants.UNDEFINED :
										tsc.values[i] -= offset
										valueCount += 1
								tsc.parameter = tsc.parameter.replace("ELEVATION", "ELEV(%s)" % datum)
								tsc.fullName = tsc.fullName.replace("ELEVATION", "ELEV(%s)" % datum)
								output("%s --> %s" % (pathname, tsc.fullName))
								dss.put(tsc)
		else :
			error("Unexpected script name: %s" % progname)
			
		return valueCount, recordCount, skipped
		
	finally :
		dss.done()		
	
user     = arg1
progname = arg2
output("===================================")
output("Running at %s" % time.ctime())
output("===================================")
frame    = Browser.getBrowser().getBrowserFrame()
proj     = frame.getCurrentProject()
pane     = frame.getTabbedPane()
tab      = pane.getSelectedComponent()
chktab(tab)
fcst     = tab.getForecast()
chkfcst(fcst)
dssfile  = fcst.getOutDssPath()
shdir    = os.path.join(proj.getProjectDirectory(), "shared")
filename = os.path.join(shdir, "verticalDatumOffsets.txt")
offsets  = getOffsets(filename)
valueCount, recordCount, skipped = applyOffsets(dssfile, offsets)
msg = "Shifted %d values in %d records - %d location(s) skipped" % (valueCount, recordCount, skipped)
output()
output(msg)
MessageBox.showInformation(msg, progname)
