# name=Write Scripts From Model
# description=Imported File
# displayinmenu=true
# displaytouser=true
# displayinselector=true
# Save_Scripts utility script
# Saves all of the scripted rules and state variable scripts currently existing
# in the watershed to the "scripts" directory
# User specifies which networks the scripts should be saved for

from __future__ import with_statement
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

def leaderReplace(txtLine, old, new):
	if len(txtLine) == 0:
		return txtLine
	newLine = txtLine
	prefix = ""
	while newLine[0] == old:
		newLine = newLine[1:]
		prefix += new
	return "%s%s" % (prefix, newLine)

def spacify(txtLine, nSpaces=4):
	#return txtLine.replace("\t", " "*nSpaces)
	return leaderReplace(txtLine, "\t", " "*nSpaces)

def tabify(txtLine, nSpaces=4):
	return leaderReplace(txtLine, " "*nSpaces, "\t")

def printToFile(fName, txt, checkFile=False, leaderFunc=tabify):
	ensure_dir(fName)
	if checkFile:
		with open(fName, 'r') as checkFile:
			check = checkFile.read().strip()
			if check != txt:
				print("File does not match, writing to timestamped file")
				fname = "%s_%s.py" % (fName[:3], time.strftime("%Y%m%d_%H%M"))
	with open(fName, 'w') as outFile:
		if not leaderFunc is None:
			txt =  "\n".join([leaderFunc(t) for t in txt.split("\n")])
		outFile.writelines(txt)

def askForNetwork(allowMultiple=True):
	mod = ClientAppWrapper.getCurrentModule() #hec.rss.client.RSimNetworkMode
	# Set up the dialog box to choose which networks to do
	chooser = ManagerChooser(mod.frame, 1, ManagerChooser.OPEN, ManagerChooser.USES_TABLE)
	chooser.setNameFilter(ManagerChooser.NO_CAVI_NAMES_FILTER)
	chooserStrings = ("", "")
	if allowMultiple:
		chooserStrings = ("s", "(use ctrl key)")
		chooser.setMultipleSelectionsAllowed(1)
	chooser.setTitle("Select network%s to save scripts %s" %  chooserStrings)
	chooser.setManagerType("rss", "hec.rss.model.RssSystem","Reservoir Network", "rsys")
	chooser.setVisible(True)
	#alert! need to handle cases where user hits cancel
	netIDs = chooser.getIdentifierList() #gets all selected items after user clicks OK
	print netIDs
	return netIDs
	
def main():
	mod = ClientAppWrapper.getCurrentModule() #hec.rss.client.RSimNetworkMode
	try: 
		origNetworkName = mod.getNetwork().toString()
	except: 
		origNetworkName = "" # no network opened
	netIDs = askForNetwork()
	
	for netID in netIDs:
		mod.openNetwork(netID) # opens the network (takes some time)
		network = mod.getNetwork() # RssSytem Obj
		print "Processing Network: " + network.toString()
		if network.toString() == origNetworkName:
			origNetworkID = netID
		##############################################################################
		# Process State Variables
		savePath = network.makeAbsolutePathFromWatershed("scripts")
		savePath += "/"+network.toString() + "/StateVars"
		for sv in network.getStateVariableList():
			if sv.isSlave(): continue
			print "Processing SV: " + sv.toString()
			iS = sv.getInitScript()
			mS = sv.getScript()
			cS = sv.getCleanupScript()
			# only save the script if it isn't empty
			if iS != "":
				printToFile(savePath+"/"+sv.toString()+"_Init.py",iS)
			if mS != "":
				printToFile(savePath+"/"+sv.toString()+"_Main.py",mS)
			if cS != "":
				printToFile(savePath+"/"+sv.toString()+"_Cleanup.py",cS)
		##############################################################################
		# Process Scripted Rules
		savePath = network.makeAbsolutePathFromWatershed("scripts")
		savePath += "/"+network.toString() + "/ScriptedRules"
		for resvName in network.getReservoirNames():
			resv = network.findReservoir(resvName)
			rules = resv.getReservoirOp().getRules()
			for rule in rules:
				if isinstance(rule, ScriptOpRule):
					print "processing: " + resv.toString() + "," + rule.toString()
					printToFile(savePath+"/"+resvName+"/"+rule.toString()+".py",rule.getScriptText())
		# reset to original network
		try: mod.openNetwork(origNetworkID)
		except: pass     
# End Functions

main()

print "done!"
