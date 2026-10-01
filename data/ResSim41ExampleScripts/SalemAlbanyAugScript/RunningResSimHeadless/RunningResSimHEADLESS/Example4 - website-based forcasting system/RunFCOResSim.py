"""
# Name: RunFCOResSim.py
# Author: Max Barry, David Ford Consulting Engineers, Inc.
# Description: Runs HEC-ResSim without the interface.
# LAST MODIFIED: 1/29/2014 by MJB
#
"""
from hec.script import ResSim, Constants
from hec.client import ClientApp
from hec.heclib.util import HecTime

from hec.heclib import dss
from time import strftime,localtime
from java.lang import String
import sys
import jarray

sys.path.append("/usr/local/hec/HEC-ResSim/DSS_FCO/bin/")


#Required Path to sys folder for DSS_FCO
FCO_DSS_CONFIG = "/usr/local/hec/HEC-ResSim/DSS_FCO/bin/.FCO_DSS.cfg"

def GetConfigInfo():
    """Returns the FCO configuration file path, and forecast user id"""
    from ConfigParser import ConfigParser
    cfgread = ConfigParser()
    cfgread.read(FCO_DSS_CONFIG)
    apdir = cfgread.get('Application', 'app_dir')
    cfil = cfgread.get('Application', 'config_file')
    sysfol = cfgread.get('Application', 'system_folder')
    userid = cfgread.get('Application', 'user_forecast_id')
    del cfgread
    return ('%s/%s/%s'%(apdir,sysfol,cfil),userid)


def GetConfigSys():
    from ConfigParser import ConfigParser
    cfgread = ConfigParser()
    cfgread.read(FCO_DSS_CONFIG)
    appdir = cfgread.get('Application', 'app_dir')
    sysfol = cfgread.get('Application', 'system_folder')
    del cfgread
    return '%s/%s'%(appdir,sysfol)

# def __getExtractMinusHour(d):
#     """Subtracts an our for StartDate for the extract"""
#     return __DateSubtractMinZeroMinHEC(d,60)

def init():
    """Initialize variables"""
    from os import path
    from fcoconfig import fcodssconfig,FCO_DSS_Runtime
    
#     print "Python Version: "  + sys.version
#     print "Python Version info: "  + sys.version_info
    
    (configpath,fcuserid) = GetConfigInfo()
    objcf = fcodssconfig(configpath)
    objcf.LoadConfigFile()
    objrt = FCO_DSS_Runtime(objcf.getFile('RuntimeConfig'))
    objrt.LoadConfigFile()
    
    rtuserid=objrt.UserID
    
    arrAlts = []
    #Only Run WCM_rules if the temp output .dss file does not exist.
    
    print "\nChecking %s..."%"Ensemble"
    if path.exists(path.join(objcf.getFolder("Overrides"),objcf.getFile('DssOverrideEFile'))):
        arrAlts.append("Ensemble")
        print "\n%s added..."%"Ensemble"
    else:    
        print "\nChecking what alternatives need to run:"
        print "\nChecking %s..."%"WCM_rules"
        if not path.exists(objcf.getFile('DssOutput')):     
            arrAlts.append("WCM_rules")
            print "\n%s added..."%"WCM_rules"
        else:
            print "\n%s not added no change..."%"WCM_rules"    
        #Only run Projected and Sandbox if their overrides exist
        print "\nChecking %s..."%"Projected"
        if path.exists(path.join(objcf.getFolder("Overrides"),objcf.getFile('DssOverrideBFile'))):
            arrAlts.append("Projected")
            print "\n%s added..."%"Projected"
        else:
            print "\n%s not added no change..."%"Projected"
        print "\nChecking %s..."%"Sandbox"
        if path.exists(path.join(objcf.getFolder("Overrides"),objcf.getFile('DssOverrideCFile'))):
            arrAlts.append("Sandbox")
            print "\n%s added..."%"Sandbox"
        else:
            print "\n%s not added no change..."%"Sandbox"


         
    #Set runtime info from input file.
    print "Initializing variables"    
    simName = objcf.getFile("SimulationName")
    print "Simulation name: %s"%simName

    watershedWkspFile = objcf.getFile("WatershedFileName")
    print "Watershed Work space file name: %s"%watershedWkspFile
    
    watershedDir = objcf.getFolder("WatershedDirectory")
    print "Watershed directory name: %s"%watershedDir
  
    overridesDir = objcf.getFolder("Overrides")
    print "Overrides directory name is %s"%overridesDir
     
    wkspFileName = path.join(watershedDir, "%s.wksp" % watershedWkspFile)
    print "Workspace file name is " + wkspFileName
    (lookBackTime,forecastTime,endTime)=__GetCurrentRuntimeDates(objrt)
    print "Debug After __GetCurrentRuntimeDates"
    #fildate = open(path.join(GetConfigSys(),'rt_dates.txt'),'r') # Changed 9-28-2009
    #fildate.readline()        #read header
    #strline = fildate.readline()
    #fildate.close()
    #print "Times: ", strline
    #(lookBackTime,forecastTime,endTime)= split(strline,',')
    return (simName,arrAlts,watershedDir,wkspFileName,lookBackTime,forecastTime,endTime,overridesDir)

def __ConvertHecDateTimeStrings(strDate):
    """Convert date/time string to HEC date/time"""
    from time import strftime
    from java.text import SimpleDateFormat
    
    sdf = SimpleDateFormat
    
    pattern_in = sdf('MM/dd/yyyy HH:mm:ss')
    pattern_HHmm = sdf('HHmm')
    pattern_ddMMMyyyy = sdf('ddMMMyyyy')
    dat_in = pattern_in.parse(strDate)
    
    # tm = __ftimconv(strDate)
    print "Debug __ConvertHecDateTimeStrings: datFor: "
    #print dat_in
    
    ################# Stoping here
    #StartTime =  strftime('%H%M',tm)
    StartTime = pattern_HHmm.format(dat_in)
    print "Debug __ConvertHecDateTimeStrings: StartTime: "
    print StartTime
    
    #StartDate = strftime('%d%b%Y',tm)
    StartDate = pattern_ddMMMyyyy.format(dat_in)
    print "Debug __ConvertHecDateTimeStrings: StartDate: "
    print StartDate 
    
    return "%s %s"%(StartDate,StartTime)

def __GetCurrentRuntimeDates(objrt):
    """Returns a tuple of runtime dates"""
    #Get dates
    #Set min to to Zero min for for ResSim Run.
    datFor = objrt.ForecastDateTime
    
    print "Debug __GetCurrentRuntimeDates: datFor: " + datFor 
    
    strForecastDateTime = __ConvertHecDateTimeStrings(datFor)
    
    print "Debug __GetCurrentRuntimeDates: strForecastDateTime : " + strForecastDateTime
    
    strStartDateTime = __ConvertHecDateTimeStrings(objrt.StartDateTime)
    
    print "Debug __GetCurrentRuntimeDates: strStartDateTime : " + strStartDateTime
    
    strEndDate = __ConvertHecDateTimeStrings(objrt.EndTimeForecast)
    
    print "Debug __GetCurrentRuntimeDates: strEndDate : " + strEndDate
    
    return (strStartDateTime,strForecastDateTime,strEndDate)

def __RemoveDssFile(strfile):
    from os import path,remove
    if path.exists(strfile):
        remove(strfile)
        print "%s removed"%strfile
        (fil,ext) = path.splitext(strfile)
        #Remove catalog file if it exists.
        fildsc = '%s.dsc'%fil
        if path.exists(fildsc):
            remove(fildsc)
            print "%s removed"%fildsc
        fildsk = '%s.dsk'%fil
        if path.exists(fildsk):
            remove(fildsk)
            print "%s removed"%fildsk

#Main
def __Process():
    from os import path
    import shutil
    from string import split,replace
    (simName,arrAlts,watershedDir,watershedWkspFile,lookBackTime,forecastTime,endTime,overridesDir)=init()
    
    print "INIT FINISHED!!!!!!!"
    
    if len(arrAlts) == 0:
        print "\nNO CHANGES!! NO ALTERNATIVE TO RUN."
    else:
        print "\nOPENING WATERSHED %s"%watershedWkspFile
        openWatershed(watershedWkspFile)
        # to set the main application window visible
        #ClientApp.frame().setVisible(1)
        dss.HecDSSFileAccess.setMessageLevel(1)  #This turns down the logging level in DSS.
        # get the simulation module
    
        ResSim.selectModule("Simulation")
        # get the simulation module
        simModule = ResSim.getCurrentModule()
        
        #if the simulation exists, delete it. does not remove its directory
        #if os.path.exists(watershedDir + "/rss/" + simName):
        if simModule.simulationExists(simName):
            print "Removing existing simulation %s"%simName
            simModule.deleteSimulation(simName)
        strAlts = ''        
        for altName in arrAlts:
            altNamePadded = FormatAltLongName(altName)
            if strAlts =='':
                strAlts ="%s"%altNamePadded
            else: strAlts = "%s,%s"%(strAlts,altNamePadded) 
            
        alts = jarray.array(split(strAlts,","), String)        
        simulation = simModule.createSimulation(simName,"FCO simulation", lookBackTime, forecastTime, endTime, 1, HecTime.HOUR_INCREMENT, alts)        
        #Run all Alt
        print "\nRUNNING ALTERNATIVES"
        for i in range(len(arrAlts)):
            altNamePadded = FormatAltLongName(arrAlts[i])
            overrideName = altNamePadded + "0.dss"
            if path.exists(overridesDir + "/" + overrideName):
                print "Copying overrides HEC-DSS file from %s"%(overridesDir + "/" + overrideName)
                print " to %s"%(watershedDir + "/rss/" + replace(simName," ","_") + "/rss/" + overrideName)
                shutil.copy(overridesDir + "/" + overrideName, watershedDir + "/rss/" + replace(simName," ","_") + "/rss/" + overrideName)            
                __RemoveDssFile(overridesDir + "/" + overrideName)
            print "\nRUNNING ALTERNATIVE: %s at %s"%(arrAlts[i],strftime('%m/%d/%Y %H:%M:%S',localtime()))
            simRun = simModule.getSimulationRun(arrAlts[i])
            simModule.computeRun(simRun, -1, Constants.TRUE, Constants.TRUE)
        
        print "\nALTERNATIVES RUNS COMPLETED at %s"%strftime('%m/%d/%Y %H:%M:%S',localtime())
        #save the all workspace
        print "SAVING THE WORKSPACES"
        ClientApp.Workspace().saveWorkspace(Constants.TRUE)
        #Exit HEC-ResSim.
    print "EXIT HEC-RESSIM"
    #ClientApp.frame().exitApplication() 
    
def openWatershed(watershed, watershedDir = None) :
    '''
    Opens a specified watershed in ResSim.
    '''
    import hec
    import os
    #----------------------------------------------#
    # determine watershed info from the parameters #
    #----------------------------------------------#
    if watershedDir is not None :
        openWatershed(os.path.join(watershedDir, watershed))
    if os.path.exists(watershed) :
        if os.path.isfile(watershed) :
            #---------------------------------------#
            # watershed param is workspace filename #
            #---------------------------------------#
            watershedName = os.path.basename(os.path.dirname(watershed))
            wkspFileName = watershed
        else :
            #----------------------------------------#
            # watershed param is watershed directory #
            #----------------------------------------#
            watershedName = os.path.basename(watershed)
            wkspFileName = os.path.join(watershed, "%s.wksp" % watershedName)
    else :
        newWatershed = os.path.join(
            hec.client.ClientApp.app().getAppStartDir(), 
            "watershed", 
            "base", 
            watershed)
        if os.path.exists(newWatershed) :
            return openWatershed(newWatershed)
        else :
            raise Exception("Unable to open watershed %s" % newWatershed)
    #-------------------------------------------------#
    # open the watershed and verify we were sucessful #
    #-------------------------------------------------#        
    ResSim.openWatershed(wkspFileName.replace(os.sep, "/"))
    if ResSim.getWatershedName() != watershedName :
        raise Exception("Unable to open watershed %s" % wkspFileName)

def FormatAltLongName(altName):
    #pad the alternative name with dashes to 10 characters
    altNamePadded = altName
    altNamePadded = altNamePadded.replace(' ', '$')
    altNamePadded = altNamePadded.ljust(10)
    altNamePadded = altNamePadded.replace(' ', '-')
    altNamePadded = altNamePadded.replace('$', ' ')
    return altNamePadded

try:
    __Process()
    ClientApp.frame().exitApplication()
    sys.exit(0)
    print "HEC-ResSim run complete!"
except:
    import traceback
    ClientApp.frame().exitApplication()
    print "HEC-ResSim run failed!"
    traceback.print_exc()

 
