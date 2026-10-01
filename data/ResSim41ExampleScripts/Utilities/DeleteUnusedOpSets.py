# name=DeleteUnusedOpSets
# description=Imported File
# displayinmenu=true
# displaytouser=true
# displayinselector=true
# DeleteUnusedOpSets utility script
# Deletes all Operation Sets that are not used in any alternative in a given network. 
# User specifies which network the Op Sets should be deleted from

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
	chooser.setTitle("Select network%s to delete unused op sets %s" %  chooserStrings)
	chooser.setManagerType("rss", "hec.rss.model.RssSystem","Reservoir Network", "rsys")
	chooser.setVisible(True)
	#alert! need to handle cases where user hits cancel
	netIDs = chooser.getIdentifierList() #gets all selected items after user clicks OK
	print netIDs
	return netIDs
	
def main():
	mod = ClientAppWrapper.getCurrentModule() #hec.rss.client.RSimNetworkMode
	wksp = ClientAppWrapper.getWatershed() #hec.client.ClientWorkspace
	altIDs = wksp.getManagerIDList("rss", "hec.rss.model.RssAlt") #vector of hec.identifier
	netIDs = askForNetwork(allowMultiple=False)
	netID = netIDs[0]
	mod.openNetwork(netID) # opens the network (takes some time)
	network = mod.getNetwork() # RssSytem Obj
	unusedOpSets = {} #Keys are reservoir name, values are a list of OpSets
	for resvName in network.getReservoirNames():
		resv = network.findReservoir(resvName)
		resOp = resv.getReservoirOp()
		opSets = resOp.getOperationSets()
		unusedOpSets[resvName] = list(opSets)
	for altID in altIDs:
		rssAlt = wksp.openManager("rss", altID) #hec.rss.model.RssAlt
		networkForAlt = rssAlt.getSystem()
		if networkForAlt.toString() == network.toString():
			print "Processing Alternative: " + rssAlt.toString()
			for resvName in network.getReservoirNames():
				resv = network.findReservoir(resvName)
				resID = resv.getIndex()
				resOp = resv.getReservoirOp()
				opSetIdx = rssAlt.getResOpSetSelection(resID)
				opSet = resOp.getOperationSet(opSetIdx)
				if opSet in unusedOpSets[resvName]:
					print(" %s Keeping: %s" %(resvName, opSet.toString()))
					unusedOpSets[resvName].remove(opSet)
	for resvName in network.getReservoirNames():
		resv = network.findReservoir(resvName)
		resOp = resv.getReservoirOp()
		for opSet in unusedOpSets[resvName]:
			print("%s Deleting: %s" %(resvName, opSet.toString()))
			resOp.removeOpSet(opSet)
					
	MessageBox.showInformation("Done. Please save the network now", "Success!")
# End Functions

main()

print "done!"

