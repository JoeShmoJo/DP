'''
Downloads the 10-day ESP data from web service via R script
'''
# must be run first
from __future__ import with_statement
from com.rma.client import Browser
import os, shutil, time, subprocess
### Config ##############################
#rExecutablePath = "D:/crt_crso/FRA_Plotter_v4.6.1/resources/R-3.4.2/bin/x64/Rscript.exe"
#rExecutablePath = "\\\\nww-netapp1\\prjmgnt\\CWMS\\software\\R-3.4.2\\bin\\x64\\Rscript.exe"
#scriptName = "ESP Download.R"
scriptName = "Download_ESP.bat"
#scriptName = "Example - Passing Input Args to Script.R"
#scriptName = "Passing Input Args to Script.bat"
#dssFileName = "columbia5_6hr.dss" #5 day, 6 hr
dssFileName = "columbia10_6hr.dss" #10 day, 6 hr
### Functions #########################
def output(msg="") :
	'''
	Output to console log
	'''
	Browser.getBrowserFrame().addMessage("%s" %  msg)
	
### Loading Config File ---------------------------------------------------------------
output("\n\n--- Begin ESP DSS Download -------------------")
output(str(time.ctime()))
#
#Getting shared directory
frame = Browser.getBrowser().getBrowserFrame()
proj = frame.getCurrentProject()
#shdir    = proj.getProjectDirectory() + "/shared"
scriptsdir = proj.getProjectDirectory() + "/scripts/esp_download/"
os.chdir(scriptsdir)
scriptPath = proj.getProjectDirectory() + "/scripts/esp_download/Download_ESP.bat"
#scriptPath = scriptPath.replace("\\","/")
#args = shdir+"/"+dssFileName #Passing the location to save the DSS file
#output("R Executable:\t%s\nESP Download Script:\t%s\nDSS Output Location:\t%s" % (rExecutablePath,scriptPath,args) )
#evalString = '"' + rExecutablePath + '" --vanilla "' + scriptPath + '" "' + args + '"'
#output("String to evaluate:\n%s" % evalString)
#os.system(evalString)
#subprocess.call(evalString)
evalString = '"'+scriptPath+'"'
evalString=evalString.replace("\\","/")
output("Calling Download Script:\t%s" % evalString)
subprocess.call(evalString)
output(str(time.ctime()))
output("--- End ESP DSS Download ---------------------\n\n")
