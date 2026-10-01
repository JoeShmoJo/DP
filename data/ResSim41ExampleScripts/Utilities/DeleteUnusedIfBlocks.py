# name=DeleteUnusedIfBlocks
# description=Imported File
# displayinmenu=true
# displaytouser=true
# displayinselector=true
# DeleteUnusedIfBlocks utility script
# Deletes all if blocks in a given network. 
# User specifies which networks the if blocks should be deleted from
#This script doesn't work very consistently, not sure what the issue is. 

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
	chooser.setTitle("Select network%s to delete unused if blocks %s" %  chooserStrings)
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
			unusedList = list(resOp.getConditionalBlocks())
			print(resvName, unusedList)
			for i in range(1,10):
				ifBlock = resOp.getConditionalBlock(i)
				print(i, ifBlock)
			'''
			opSets = resOp.getOperationSets()
			for opSet in opSets:
				zones = opSet.getZoneVector()
                for zone in zones:
                    ifBlocks = zone.getConditionalBlockRefs([])
                    for ifBlockRef in ifBlocks:
                        ifBlock = ifBlockRef.getConditionalBlock()
                        if ifBlock in unusedList:
                            #print("%s: Deleting %s" %(resv.toString(), ifBlock.toString()))
                            unusedList.remove(ifBlock)
			'''
			for ifBlock in unusedList:
				print("%s: Deleting %s" %(resv.toString(), ifBlock.toString()))
				resOp.deleteConditionalBlock(ifBlock)
	MessageBox.showInformation("Done. Please save the network now", "Success!")
# End Functions

main()

print "done!"

