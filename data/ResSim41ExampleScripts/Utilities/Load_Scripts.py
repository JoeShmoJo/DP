# name=Read Scripts Into Model
# description=Imported File
# displayinmenu=true
# displaytouser=true
# displayinselector=true
# Load_Scripts utility script
# Loads all of the scripted rules and state variable scripts currently existing
# in the watershed from the "scripts" directory
# Based on the Save_Scripts.py utility.
# User specifies which networks the scripts should be loaded for.

#ClientAppWrapper moved to hec.rss.script in ResSim 4.1. 4.1 still accepts the old
#path but warns that support will be removed. Import both ways so this
#file runs under 4.1 and 3.5 alike.
try:
    from hec.rss.script import ClientAppWrapper        #ResSim 4.1
except ImportError:
    from hec.script import ClientAppWrapper            #ResSim 3.5
#ManagerChooser moved from hec.client to hec.clientapp.client in ResSim 4.1.
#Import it both ways so this file runs under 4.1 and 3.5 alike.
try:
    from hec.clientapp.client import ManagerChooser   #ResSim 4.1
except ImportError:
    from hec.client import ManagerChooser             #ResSim 3.5
from hec.rss.model import RssSystem, ScriptOpRule
import os, sys

# Functions
def ensure_dir(f):
	d = os.path.dirname(f)
	if not os.path.exists(d):
		os.makedirs(d)

def printToFile(fName, txt):
	ensure_dir(fName)
	outFile = open(fName, 'w')
	outFile.writelines(txt)
	outFile.close()

def fileToString(fName):
	if os.path.exists(fName):
		f = open(fName,'r')
		string = f.read()
		f.close()
		return string
	else:
		return ""


def main():
	mod = ClientAppWrapper.getCurrentModule() #hec.rss.client.RSimNetworkMode
	# Set up the dialog box to choose which networks to do
	chooser = ManagerChooser(mod.frame, 1, ManagerChooser.OPEN, ManagerChooser.USES_TABLE)
	chooser.setNameFilter(ManagerChooser.NO_CAVI_NAMES_FILTER)
	chooser.setMultipleSelectionsAllowed(1)
	chooser.setTitle("Select networks to read scripts into (use ctrl key)")
	chooser.setManagerType("rss", "hec.rss.model.RssSystem","Reservoir Network", "rsys")
	#chooser.setManagerType("rss", "hec.rss.model.RssAlt","Reservoir Network", "rsys")
	chooser.setVisible(True)
	#alert! need to handle cases where user hits cancel
	netIDs = chooser.getIdentifierList() #gets all selected items after user clicks OK
	print netIDs
	try: origNetworkName = mod.getNetwork().toString()
	except: origNetworkName = "" # no network opened
	for netID in netIDs:
		mod.openNetwork(netID) # opens the network (takes some time)
		network = mod.getNetwork() # RssSytem Obj
		print "Processing Network: " + network.toString()
		if network.toString() == origNetworkName:
			origNetworkID = netID
		##############################################################################
		# Process State Variables
		loadPath = network.makeAbsolutePathFromWatershed("scripts")
		loadPath += "/"+network.toString() + "/StateVars"
		for sv in network.getStateVariableList():
			if sv.isSlave(): continue
			print "Processing SV: " + sv.toString()
			initFileName = loadPath+"/"+sv.toString()+"_Init.py"
			mainFileName = loadPath+"/"+sv.toString()+"_Main.py"
			cleanupFileName = loadPath+"/"+sv.toString()+"_Cleanup.py"
			if os.path.exists(initFileName):
				initScriptText = fileToString(initFileName)
				#print "#"*80
				#print scriptText
				sv.setInitScript(initScriptText)
			if os.path.exists(mainFileName):
				mainScriptText = fileToString(mainFileName)
				#print "#"*80
				#print scriptText
				sv.setScript(mainScriptText)
			if os.path.exists(cleanupFileName):
				cleanupScriptText = fileToString(cleanupFileName)
				#print "#"*80
				#print scriptText
				sv.setCleanupScript(cleanupScriptText)
		##############################################################################
		# Process Scripted Rules
		loadPath = network.makeAbsolutePathFromWatershed("scripts")
		loadPath += "/"+network.toString() + "/ScriptedRules"
		for resvName in network.getReservoirNames():
			resv = network.findReservoir(resvName)
			rules = resv.getReservoirOp().getRules()
			for rule in rules:
				if isinstance(rule, ScriptOpRule):
					print "processing: " + resv.toString() + "," + rule.toString()
					scriptFileName = loadPath+"/"+resvName+"/"+rule.toString()+".py"
					if os.path.exists(scriptFileName):
						ruleScriptText = fileToString(scriptFileName)
						rule.setScriptText(ruleScriptText)
		# reset to original network
		try: mod.openNetwork(origNetworkID)
		except: pass	 
# End Functions

main()

print "done!"

  
