# name=Rules_to_CSV
# description=Imported File
# displayinmenu=true
# displaytouser=true
# displayinselector=true
# Rules_to_CSV utility script
# Saves all of the rules in a given alternative to CSV 
# in the watershed to the "scripts" directory
# User specifies which alternative the rules should be saved for

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
from hec.script import MessageBox
from hec.rss.model import RssSystem, ScriptOpRule
import os, sys, csv

zoneAbbr ={"Top of Dam": "TOD", "Flood Control": "FC", "Conservation": "CON", 
	"Inactive": "IN", "Buffer": "BUF", "Max Pool": "MAX", "Bottom of Rules":"BOT",
	"Primary Flood Control":"PRIM", "Secondary Flood Control":"SEC"}
resvAbbr = {}

# Functions
def ensure_dir(f):
	d = os.path.dirname(f)
	if not os.path.exists(d):
		os.makedirs(d)

def askForAlternative(allowMultiple=True):
	mod = ClientAppWrapper.getCurrentModule() #hec.rss.client.RSimNetworkMode
	# Set up the dialog box to choose which networks to do
	chooser = ManagerChooser(mod.frame, 1, ManagerChooser.OPEN, ManagerChooser.USES_TABLE)
	chooser.setNameFilter(ManagerChooser.NO_CAVI_NAMES_FILTER)
	chooserStrings = ("", "")
	if allowMultiple:
		chooserStrings = ("s", "(use ctrl key)")
		chooser.setMultipleSelectionsAllowed(1)
	chooser.setTitle("Select alternative%s to save rules %s" %  chooserStrings)
	chooser.setManagerType("rss", "hec.rss.model.RssAlt","Alternative", "ralt")
	chooser.setVisible(True)
	#alert! need to handle cases where user hits cancel
	altIDs = chooser.getIdentifierList() #gets all selected items after user clicks OK
	print altIDs
	return altIDs
	
def main():
	mod = ClientAppWrapper.getCurrentModule() #hec.rss.client.RSimNetworkMode
	altIDs = askForAlternative() #list of hec.identifier
	filenames = []
	for altID in altIDs:
		altName = altID.name
		print("Processing Alternative: " + altName)
		wksp = ClientAppWrapper.getWatershed() #hec.client.ClientWorkspace
		rssAlt = wksp.openManager("rss", altID) #hec.rss.model.RssAlt
		network = rssAlt.getSystem()
		csvFilename = network.makeAbsolutePathFromWatershed("scripts/RuleList/Rules_%s.csv" %altName)
		ensure_dir(csvFilename)
		filenames.append(csvFilename)
		csvHeaders = ["Reservoir", "Rule", "Zones", "Description"]
		csvRowDict = {} #will hold one line
		csvFile = open(csvFilename, 'wb')
		writer = csv.DictWriter(csvFile, fieldnames=csvHeaders)
		writer.writeheader()
		for resvName in network.getReservoirNames():
			resv = network.findReservoir(resvName)
			resID = resv.getIndex()
			resOp = resv.getReservoirOp()
			opSetIdx = rssAlt.getResOpSetSelection(resID)
			opSet = resOp.getOperationSet(opSetIdx)
			rules = opSet.getRules([])
			zones = opSet.getSortedZoneVector()
			for rule in rules:
				csvRowDict["Reservoir"] = resvName
				csvRowDict["Rule"] = rule.getName()
				csvRowDict["Description"] = rule.getDescription()
				csvRowDict["Zones"] = ""
				for zone in zones:
					csvRowDict["Rule"] = rule.getName()
					if zone.usesOpRule(rule, True):
						zoneShort = zone.getName()
						if zoneShort in zoneAbbr:
							zoneShort = zoneAbbr[zoneShort]
						if csvRowDict["Zones"] == "": #First one
							csvRowDict["Zones"] = zoneShort
						else:
							csvRowDict["Zones"] = csvRowDict["Zones"] + ", " + zoneShort
				writer.writerow(csvRowDict)
		csvFile.close()
	msg = "Exported rules to CSV: "
	for f in filenames:
		msg += "\n %s" %f
	MessageBox.showInformation(msg, "Success")
# End Functions

main()

print "done!"
