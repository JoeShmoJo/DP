'''
cUSGS Module
Contains code to grab USGS data from the web
Created by John McCoskery, updated by Ryan Cahill 9/2014
'''

from hec.heclib.util import Heclib, HecTime
from hec.hecmath import DSS, TimeSeriesMath
from hec.io import TimeSeriesContainer
from hec.script import Constants
from hec.lang import DSSPathString
from javax.swing import JProgressBar, JPanel, JFrame, JTextField
from java.awt import BorderLayout, GridLayout
from java.text import SimpleDateFormat
import datetime, sys, urllib, time, logging

import cFile, cTsUtils
import subprocess
import os

################################################################################
# STATIC INPUT
Cal = ["Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", \
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
Param_Def = {   "FLOW"  :   ["00060", "CFS"],
                "ELEV2"  :   ["00062", "FT"], #few USGS gages have this defined
                "ELEV3"  :   ["62614", "FT"], #few USGS gages have this defined (e.g. Lookout Point)
                "ELEV29"  :   ["72020", "FT"], #elev NGVD29 (Hungry Horse), few USGS gages have this defined
                "ELEV"  :   ["00065", "FT"], #convert stage to elev using datum
                "STAGE" :   ["00065", "FT"]
            }
Err_Codes = ["SSN", "ICE", "PR", "RAT", "EQP", "FLD", \
             "DIS", "DRY", "--", "MNT", "ZFL", "***"]
Valid_Intv = {  "1HOUR" :   60, 
                "4HOUR" :  240,
                "6HOUR" :  360,
               "12HOUR" :  720,
                 "1DAY" : 1440
             }
################################################################################
# CLASS DEFINITIONS

# END OF CLASS DEFINITIONS
################################################################################
# FUNCTION DEFINITIONS
# **********************************************************************
# method to get vertical datum information for USGS site
# **********************************************************************
def getLinesHTTPS(my_url):
    #Reads a webpage and returns a list of strings that are the lines of the webpage. 
    #This is necessary because the version
    #of python shipped with Jython cannot seem to handle urls starting with https
    #very clunky. 
    
    scriptName = "getHTTPS.py" #todo hardcoded since it lives in the same directory
    outFileName = "temp.txt"
    dirName = os.path.dirname(__file__)
    scriptName = os.path.join(dirName, scriptName)
    outFileName = os.path.join(dirName, outFileName)
    #Have to launch an outside version of python to get the https webpage
    shellCommand = "python %s %s %s" %(scriptName, my_url, outFileName)
    subprocess.call(shellCommand)
    lines = cFile.fileOpenReadClose(outFileName)
    os.remove(outFileName)
    return lines
def get_vert_datum (usgs_id) :
    my_url = "https://waterservices.usgs.gov/nwis/site/?format=rdb&sites=%s" % usgs_id
    try :
        #content = urllib.urlopen(my_url)
        #c = content.readlines()
        #content.close()
        c = getLinesHTTPS(my_url)
    except :
        logging.error ("ERROR connecting to URL\n%s." % my_url)
        logging.error ("vertical datum (ft)           %30.2f" % 0.)
        return 0.
    datum_name = None
    datum = 0.
    for x in range (0, len(c)) :
        line = c[x].strip()
        if line.startswith("USGS") :
            park = line.split("\t")
            datum_name = park[-2]
            datum = eval(park[-4])
    logging.info ("vertical datum                %30s" % datum_name)
    logging.info ("datum offset (ft)             %30.2f" % datum)
    return datum, datum_name

# **********************************************************************
# method to grab instantaneous or daily data from NWIS.  IR-MONTH
# if t1 = 25Dec1964 2400 and t2 = 27Dec1964 2400, the output data
# will start at 25Dec1964 2400 and end at 27Dec 2345
# **********************************************************************
def get_data (usgs_id, parm_code, t1, t2, offset=0., dvORuv="dv") :
    if dvORuv == "uv":
        numFlds = 7 #expected number of columns
        valIdx = 5  #column index of the values
    else: #default to daily
        numFlds = 5
        valIdx = 3
    
    # set URL ("uv" for realtime, "dv" for daily)
    my_url = "https://nwis.waterdata.usgs.gov/usa/nwis/%s?" %dvORuv
    my_url = "%scb_%s=on&" % (my_url, parm_code)
    my_url = "%sformat=rdb&site_no=%s&" % (my_url, usgs_id)
    my_url = "%speriod=&begin_date=%s&" % (my_url, t1)
    my_url = "%send_date=%s" % (my_url, t2)
    logging.info("%s" % my_url)
    # try to read content from NWIS, on error return None
    try:
        #content = urllib.urlopen(my_url)
        #c = content.readlines()
        #content.close()
        c = getLinesHTTPS(my_url)
    except :
        logging.error("ERROR opening URL")
        return False
    # NWIS will return 1 line message if data found for URL
    if len(c) <= 1 :
        logging.error("ERROR retrieving timeseries.\n%s" % c[0])
        return False
    elif "<!DOCTYPE html>" == c[0].strip(): #shouldn't get html, must be an error
        logging.error("ERROR in URL format")
        return False    
    # extract data to usgs_times and usgs_data array
    times = []
    values = []
    ht = HecTime()
    # loop through content and load time/values to arrays
    for x in range(0, len(c)) :
        line = c[x].strip()
        if line.startswith("USGS") :
            park = line.split()
            # set up date/time object
            datestr = park[2]
            p = datestr.split("-") # yyyy-mm-dd
            dy = int(p[0])
            dm = int(p[1])
            dd = int(p[2])
            if dvORuv == "uv":
              timestr = park[3]
              p = timestr.split(":") # hh:mm
              th = int(p[0])
              tm = int(p[1])
              ht.set("%02i%s%04i %02i%02i" % (dd, Cal[dm], dy, th, tm))
            else: #daily
              ht.set("%02i%s%04i 2400" % (dd, Cal[dm], dy))
            # set value
            if len(park) != numFlds :
                #Not the number of fields expected--just grab the 2nd to last field
                #This often happens when multiple statistics exist for a parameter (max, min, avg)
                if dvORuv == "dv" and parm_code == "00065":
                     #If retrieving daily stages, it will return 3 statistics-min, max, mean
                     #Mean is the last one
                     numFlds = 9
                     valIdx = 7
                     value = eval(park[-2]) + offset
                else: #set to undefined
                     value = Constants.UNDEFINED_DOUBLE
            elif park[-1] in Err_Codes :
                value = Constants.UNDEFINED_DOUBLE
            else :
                if "_" in park[valIdx]: #e.g. 5140_ICE, the 5140 cfs should still be retrieved
                  findIdx = park[valIdx].find("_")
                  park[valIdx] = park[valIdx][:findIdx]
                value = eval(park[valIdx]) + offset
            # see if time already exists in array, if it does than write
            # value to that index, other wise append time and value
            try :
                n = times.index(ht.value())
                if value != Constants.UNDEFINED_DOUBLE :
                    values[n] = value
            except :
                times.append(ht.value())
                values.append(value)
        # skip any other lines
    c = None
    if len(times) == 0: 
      logging.error("No Data found!")
      return False # no data
    # build TimeSeriesContainer object
    tsc = TimeSeriesContainer()
    tsc.numberValues = len(times)
    tsc.times = times
    tsc.values = values
    tsc.interval = -1
    return tsc

    
# **********************************************************************
# MAIN
# **********************************************************************
def importUSGSData(extractF, rawdssF, dstr1, dstr2, simintv, bar, txtArea):
  '''
  Function to read in a list of USGS locations, convert them to regular interval
  records and and store to outDssFile 
    extractF = string, filename with USGS locations
    rawdssF = string, dss filename to store extracted data
    dstr1 = string, beginning day for the extract (e.g. "01Oct2012")
    dstr2 = string, ending day for the extract
    simintv = string, the desired output timestep ("1HOUR" or "1DAY")
    bar = JProgressBar for status %
    txtArea = JTextArea for status text (with a method defined called "printToGUI"
  ''' 
  #delimiterType = ";" #old way was semi-colon, do tabs now
  delimiterType = "\t"
  
  # set simulation interval, default to 1DAY if not passed in
  try :
      simintv = simintv.upper()
  except :
      simintv = "1DAY"
  
  # write some stuff to the log file...
  txtArea.printToGUI("Extracting USGS Data...")
  logging.info("extraction list: %s" % extractF)
  logging.info("raw data dss file: %s" % rawdssF)
  
  # set start and end times
  d1 = HecTime()
  d1.set(dstr1 + " 2400")
  logging.info("extraction start date         %30s" % d1.dateAndTime(4))
  
  d2 = HecTime()
  d2.set(dstr2 + " 2400")
  logging.info("extraction end date           %30s" % d2.dateAndTime(4))
  
  # create USGS time strings
  t1 = "%04i-%02i-%02i" % (d1.year(), d1.month(), d1.day())
  t2 = "%04i-%02i-%02i" % (d2.year(), d2.month(), d2.day())
  
  # verify simulation interval
  logging.info("simulation interval           %30s" % simintv)
  if not simintv in Valid_Intv.keys() :
      logging.error("ERROR setting simulation interval in minutes.")
      logging.error("data will not be extracted.")
      return None
  tscintv = Valid_Intv[simintv]
  logging.info("interval in minutes           %30i" % tscintv)
  
  # open extract list file and store contents to memory
  try :
      c = cFile.fileOpenReadClose(extractF)
  except :
      logging.error("ERROR reading extract list file.")
      return None
  
  extract_list = cFile.stripOutCommentLines(c)
  
  num_to_extract = len(extract_list)
  if num_to_extract == 0 :
      logging.error("no timeseries defined in extract list.")
      return None
  logging.info("number of timeseries to extract         %20i" % num_to_extract)
  
  # open DSS files
  rawdss = DSS.open(rawdssF)
  
  # loop through extract_list and process commands
  bar.setValue(0)
  failList = [] #USGS ID's that failed
  incompleteDict = {} #USGS ID's that couldn't get the full time window
  i = 0
  for line in extract_list :
      i += 1
      if delimiterType == ";":
        park = line.split(delimiterType)
        usgs_id = park[0].strip()
        parameter = park[1].strip()
        desc = park[2].strip()
      else: #assume tabbed
        park = line.split(delimiterType)
        usgs_id = park[0].strip()
        parameter = park[1].strip()
        desc = park[3].strip() #sometimes the description has quotes around it
        desc = desc.replace('"','').strip()
      txtArea.printToGUI("%s : %s : %s" % (usgs_id, parameter, desc))     
      logging.info("\nusgs id             %40s" % usgs_id)
      logging.info("site description    %40s" % desc)
      logging.info("parameter           %40s" % parameter)
      # verify that parameter is defined
      if not parameter.upper() in Param_Def.keys() :
          logging.error("ERROR parameter is not definable.")
          failList.append(line)
          continue
      else :
          parm_code = Param_Def[parameter.upper()][0]
          ts_units =  Param_Def[parameter.upper()][1]
      # get vertical datum from NWIS
      if parameter.upper() == "ELEV" :
          datum, datum_name = get_vert_datum(usgs_id)
      else : 
          datum = 0. # set to 0 for flow/stage
      # extract raw data from NWIS, will return a TSC if good, False if not
      if simintv == "1DAY" :
          tsc = get_data (usgs_id, parm_code, t1, t2, datum, "dv")
      else :
          tsc = get_data (usgs_id, parm_code, t1, t2, datum, "uv")
      if not tsc:
        logging.error("data not written to DSS file.")
        txtArea.printToGUI("\tFailed to retrieve: %s" %usgs_id)
        failList.append(line)
        continue
      if parameter.upper() == "FLOW" :
          ts_type = "PER-AVER"
      else :
          ts_type = "INST-VAL"
      cPart = parameter
      if parameter.upper() == "ELEV" : # write out the datum name
        cPart = "ELEV-%s" %datum_name
      elif "ELEV" in parameter.upper() : #NGVD29 by definition
        cPart = "ELEV-NGVD29"
      #Check data to see if it spans the whole length
      dataStartDate = HecTime(tsc.times[0], HecTime.MINUTE_INCREMENT)
      dataEndDate = HecTime(tsc.times[-1], HecTime.MINUTE_INCREMENT)
      logging.info("data start date     %40s" % dataStartDate.toString(14)) #02Jun85
      logging.info("data end date       %40s" % dataEndDate.toString(14))
      #The end date of the data will be 15 minutes prior to the actual desired end date
      if dataStartDate.greaterThan(d1) or (d2.value() - dataEndDate.value()) > 1440:
        #1440 is minutes in a day, if more than a day before, then it's a problem
        #Didn't get the whole time window, save it to spit out later
        incompleteDict[usgs_id] = {}
        incompleteDict[usgs_id]["Start"] = dataStartDate.clone()
        incompleteDict[usgs_id]["End"] = dataEndDate.clone()
      # write IR-MONTH data to raw DSS file
      path = "/%s/%s/%s//%s/USGS-NWIS" % (desc, usgs_id, cPart, "IR-MONTH")
      cTsUtils.write_data (rawdss, tsc, path, ts_units, ts_type)
      # transform to simulation interval
      tsc = cTsUtils.transform_to_regular (tsc, simintv, parameter)
      # write regular interval data to raw dss file
      path = "/%s/%s/%s//%s/USGS-NWIS" % (desc, usgs_id, cPart, simintv)
      cTsUtils.write_data (rawdss, tsc, path, ts_units, ts_type)
      bar.setValue(int(float(i)/len(extract_list)*100))
      
  rawdss.close()
  msg = "\nDONE EXTRACTING USGS DATA FROM WEB!"
  if len(failList) > 0:
    msg += "\nFailed to extract the following USGS IDs:"
    for failID in failList:
      msg += "\n\t%s" %failID
  if len(incompleteDict.keys()) > 0:
    msg += "\nFailed to extract complete time window the following IDs:"
    msg += "\n\tUSGS ID       Data Begin Date          Data End Date"
    for usgs_id in incompleteDict.keys():
      dataStartDate = incompleteDict[usgs_id]["Start"].toString(14) #02Jun85
      dataEndDate = incompleteDict[usgs_id]["End"].toString(14)
      msg += "\n\t%s      %s           %s" %(usgs_id, dataStartDate, dataEndDate)
  
  logging.info(msg)
  txtArea.printToGUI(msg)
  bar.setValue(100)
  return None