# name=DeleteUnusedRules
# description=Imported File
# displayinmenu=true
# displaytouser=true
# displayinselector=true
# DeleteUnusedRules utility script
# Deletes all rules that are not used in any operation set in a given network. 
# User specifies which networks the rules should be deleted from
# BE CAREFUL WITH THIS, I'VE SEEN IT OCCASSIONALLY DELETE A RULE THAT EXISTS IN AN OPERATION SET
# TYPICALLY IT'S A DOWNSTREAM CONTROL RULE. SO DO A SCREEN COMPARE OR RUN "Rules_to_CSV.py" to make sure it worked. 

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
from hec.script import MessageBox
from hec.rss.model import RssSystem, ScriptOpRule
import os, sys, csv

# Functions
def askForNetwork(allowMultiple=True):
	mod = ClientAppWrapper.getCurrentModule() #hec.rss.client.RSimNetworkMode
	# Set up the dialog box to choose which networks to do
	chooser = ManagerChooser(mod.frame, 1, ManagerChooser.OPEN, ManagerChooser.USES_TABLE)
	chooser.setNameFilter(ManagerChooser.NO_CAVI_NAMES_FILTER)
	chooserStrings = ("", "")
	if allowMultiple:
		chooserStrings = ("s", "(use ctrl key)")
		chooser.setMultipleSelectionsAllowed(1)
	chooser.setTitle("Select network%s to delete unused rules %s" %  chooserStrings)
	chooser.setManagerType("rss", "hec.rss.model.RssSystem","Reservoir Network", "rsys")
	chooser.setVisible(True)
	#alert! need to handle cases where user hits cancel
	netIDs = chooser.getIdentifierList() #gets all selected items after user clicks OK
	print netIDs
	return netIDs
	
def main():
	mod = ClientAppWrapper.getCurrentModule() #hec.rss.client.RSimNetworkMode
	netIDs = askForNetwork()
	for netID in netIDs:
		mod.openNetwork(netID) # opens the network (takes some time)
		network = mod.getNetwork() # RssSytem Obj
		print "Processing Network: " + network.toString()
		for resvName in network.getReservoirNames():
			resv = network.findReservoir(resvName)
			resID = resv.getIndex()
			resOp = resv.getReservoirOp()
			unusedRules = list(resOp.getRules())
			opSets = resOp.getOperationSets()
			for opSet in opSets:
				rules = opSet.getRules([])
				for rule in rules:
					if rule in unusedRules:
						print("%s: Deleting %s" %(resv.toString(), rule.toString()))
						unusedRules.remove(rule)
			for rule in unusedRules:
				resOp.deleteOpRule(rule)
	MessageBox.showInformation("Done. Please save the network now", "Success!")
# End Functions

main()

print "done!"

