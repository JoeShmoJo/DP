# name=RuleProbe
# description=Imported File
# displayinmenu=true
# displaytouser=true
# displayinselector=true
# RuleProbe utility script
# A throwaway probe. For every built-in (not scripted) rule in the active
# operation sets of the chosen alternative, writes what the rule object can
# report: its type, and the value of every get/is method that takes no
# arguments. Used to find the calls that read a downstream control rule's
# location and flow limit, which the API reference does not cover.
# Changes nothing in the model. Writes scripts/RuleList/RuleProbe_<alternative>.txt

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
import os, sys

# Getters whose results are worth opening up one level further
DIG_WORDS = ["Loc", "Limit", "Flow", "Func", "Table", "Element", "Max", "Min", "Value", "Season", "Curve"]
MAX_TEXT = 300

# Functions
def ensure_dir(f):
	d = os.path.dirname(f)
	if not os.path.exists(d):
		os.makedirs(d)

def askForAlternative(allowMultiple=True):
	mod = ClientAppWrapper.getCurrentModule() #hec.rss.client.RSimNetworkMode
	chooser = ManagerChooser(mod.frame, 1, ManagerChooser.OPEN, ManagerChooser.USES_TABLE)
	chooser.setNameFilter(ManagerChooser.NO_CAVI_NAMES_FILTER)
	chooserStrings = ("", "")
	if allowMultiple:
		chooserStrings = ("s", "(use ctrl key)")
		chooser.setMultipleSelectionsAllowed(1)
	chooser.setTitle("Select alternative%s to probe rules %s" %  chooserStrings)
	chooser.setManagerType("rss", "hec.rss.model.RssAlt","Alternative", "ralt")
	chooser.setVisible(True)
	altIDs = chooser.getIdentifierList() #gets all selected items after user clicks OK
	return altIDs

def short(value):
	try:
		text = str(value)
	except:
		text = "<unprintable>"
	text = text.replace("\n", " ").replace("\r", " ")
	if len(text) > MAX_TEXT:
		text = text[:MAX_TEXT] + "..."
	return text

def getters(obj):
	"""[(name, value)] for every get/is method of obj that runs with no arguments."""
	found = []
	try:
		names = dir(obj)
	except:
		return found
	for name in names:
		if not (name.startswith("get") or name.startswith("is")):
			continue
		method = getattr(obj, name, None)
		if not callable(method):
			continue
		try:
			found.append((name, method()))
		except:
			pass #needs arguments, or cannot be called here
	return found

def typeName(obj):
	try:
		return str(type(obj))
	except:
		return "?"

def probeRule(out, resvName, zoneNames, rule):
	out.write("=" * 70 + "\n")
	out.write("%s | %s | zones: %s\n" % (resvName, short(rule), ", ".join(zoneNames)))
	out.write("type: %s\n" % typeName(rule))
	for name, value in getters(rule):
		out.write("  %s() = %s   [%s]\n" % (name, short(value), typeName(value)))
		dig = False
		for word in DIG_WORDS:
			if word in name:
				dig = True
		if dig and value is not None and not isinstance(value, (str, int, float, bool)):
			for subName, subValue in getters(value):
				out.write("      .%s() = %s   [%s]\n" % (subName, short(subValue), typeName(subValue)))

def main():
	altIDs = askForAlternative()
	filenames = []
	for altID in altIDs:
		altName = altID.name
		print("Probing Alternative: " + altName)
		wksp = ClientAppWrapper.getWatershed() #hec.client.ClientWorkspace
		rssAlt = wksp.openManager("rss", altID) #hec.rss.model.RssAlt
		network = rssAlt.getSystem()
		fileName = network.makeAbsolutePathFromWatershed("scripts/RuleList/RuleProbe_%s.txt" % altName)
		ensure_dir(fileName)
		filenames.append(fileName)
		out = open(fileName, "w")
		for resvName in network.getReservoirNames():
			resv = network.findReservoir(resvName)
			opSetIdx = rssAlt.getResOpSetSelection(resv.getIndex())
			opSet = resv.getReservoirOp().getOperationSet(opSetIdx)
			zones = opSet.getSortedZoneVector()
			for rule in opSet.getRules([]):
				if isinstance(rule, ScriptOpRule):
					continue #scripted rules keep their settings in our own configs
				zoneNames = [zone.getName() for zone in zones if zone.usesOpRule(rule, True)]
				try:
					probeRule(out, resvName, zoneNames, rule)
				except:
					out.write("  could not probe: %s\n" % str(sys.exc_info()[1]))
		out.close()
	msg = "Rule probe written to: "
	for f in filenames:
		msg += "\n %s" % f
	MessageBox.showInformation(msg, "Done")
# End Functions

main()

print "done!"
