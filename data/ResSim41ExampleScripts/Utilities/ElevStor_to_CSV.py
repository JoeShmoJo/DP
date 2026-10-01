# name=ElevStor_to_CSV
# description=Imported File
# displayinmenu=true
# displaytouser=true
# displayinselector=true

# ElevStor_to_CSV utility script
# Saves all of the elevation/storage curves for a network
# to the "scripts" directory
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
from hec.script import MessageBox
from hec.rss.model import RssSystem, ScriptOpRule
import os, sys, csv

# Functions
def ensure_dir(f):
	d = os.path.dirname(f)
	if not os.path.exists(d):
		os.makedirs(d)

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
	netIDs = askForNetwork()
	filenames = []
	for netID in netIDs:
		mod.openNetwork(netID) # opens the network (takes some time)
		network = mod.getNetwork() # RssSytem Obj
		print "Processing Network: " + network.toString()
		##############################################################################
		# Process tables
		csvFilename = network.makeAbsolutePathFromWatershed("scripts/%s/ElevStor.csv" %network.toString())
		ensure_dir(csvFilename)
		filenames.append(csvFilename)
		csvHeaders = ["Reservoir", "Elev", "Stor"]
		csvRowDict = {} #will hold one line
		csvFile = open(csvFilename, 'wb')
		writer = csv.DictWriter(csvFile, fieldnames=csvHeaders)
		writer.writeheader()
		for resvName in network.getReservoirNames():
			resv = network.findReservoir(resvName)
			elevStor = resv.getStorageFunction().getElevationStorageValues()
			elevs = elevStor.getXArray()
			stors = elevStor.getYArray()
			for i in range(len(elevs)):
				csvRowDict["Reservoir"] = resvName
				csvRowDict["Elev"] = elevs[i]
				csvRowDict["Stor"] = stors[i]
				writer.writerow(csvRowDict)
		csvFile.close()
	msg = "Exported rules to CSV: "
	for f in filenames:
		msg += "\n %s" %f
	MessageBox.showInformation(msg, "Success")
# End Functions

main()

print "done!"
