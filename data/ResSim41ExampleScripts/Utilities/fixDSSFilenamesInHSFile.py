 # launch as Python script from $WATERSHED\scripts\utility\ directory after updating pathnames in FRA sampler.
 # Script will automatically fix the filenames referenced.  Makes it a lot faster to change datasets.

from xml.dom.minidom import parse

#hsFilename = os.path.join(os.getcwd(),r'\..\..\hs\CRT_HS_2020L.hs')

hsFilename = "C:\\Users\\g2enctdc\\Documents\\00_CRT_WAT_WATERSHEDS\\CRT_Master_2022-06-15_NewFRAPDPs_PA_TCv2\\hs\\CRT_HS_2020L.hs"

dom = parse(hsFilename)

synthYears = dom.getElementsByTagName("HydrologicSampling")[0].getElementsByTagName("SeasonHydroEvents")[0].getElementsByTagName("SeasonHydroEvent")[0].getElementsByTagName("HydroEvents")[0].getElementsByTagName("SyntheticYears")[0].getElementsByTagName("SyntheticYear")
for sy in synthYears:
    name = sy.getAttribute("Name")
    print(name)
    entries = sy.getElementsByTagName("HydrographTable")[0].getElementsByTagName("location")
    for entry in entries:
        entry.setAttribute("filename", "shared/FRA_2020L/CRT_Inflows_%NAME%.dss".replace("%NAME%", name))
        print("\t%s" % entry.getAttribute("CompPt"))

with open("%s" % hsFilename, 'w') as outFile:
	outFile.write(dom.toprettyxml(indent="", newl=""))