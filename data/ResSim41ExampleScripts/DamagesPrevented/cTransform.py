"""
Step 1 of Damages Prevented: tributary locals computed from gage data alone.

Ported from AFDR/cLocFlows.transformGageData for ResSim 4.1. For the
Willamette this is a single record, Willamette Falls = 1.5 x Pudding River at
Aurora, but any area-ratio / MOVE.1 transformation in the config CSV works.

Config (scripts/DamagesPrevented/config/TransformedLocals.csv), one row per
record, # lines are comments:

    Bpart,Cpart,Station,AreaRatio,aMOVE1,bMOVE1,BCF,Comments
    WILLAMETTE FALLS,FLOW-LOC,14202000,1.5,,,,Pudding R at Aurora x 1.5

Station is the B part of the gage record in obsData.dss (C part containing
FLOW). A row with Bpart ADD is computed and added to the next row instead of
being written. Output: //<Bpart>/<Cpart>//<time step>/COMPUTED/ in DPcalc.dss.
"""
from hec.hecmath import DSS, TimeSeriesMath
import logging

from NWDJyLib import cFile
from NWDJyLib.DSS import cDSS, cTsUtils

################################################################################

def _toFloat(text):
    """float of a CSV field, or None if it is blank or not a number"""
    try:
        return float(text.strip())
    except:
        return None

def parseTransformCSV(csvFile):
    """
    Reads the transformation config.
    Returns a list of dicts with keys bPart, cPart, station, areaRatio, aMove1, bMove1, bcf.
    """
    lines = cFile.fileOpenReadClose(csvFile)
    lines = cFile.stripOutCommentLines(lines)
    rows = []
    for line in lines:
        fields = line.split(",")
        while len(fields) < 7:
            fields.append("")
        rows.append({
            "bPart": fields[0].strip(),
            "cPart": fields[1].strip(),
            "station": fields[2].strip(),
            "areaRatio": _toFloat(fields[3]),
            "aMove1": _toFloat(fields[4]),
            "bMove1": _toFloat(fields[5]),
            "bcf": _toFloat(fields[6]),
        })
    return rows

def transformGageData(obsDssFile, outDssFile, csvFile, tsInt, startTime, endTime, fPart, bar, txtArea):
    """
    Computes every record in csvFile from the gage data in obsDssFile and
    writes them to outDssFile.

    :param str obsDssFile: obsData.dss (downloaded USGS/CWMS data)
    :param str outDssFile: DPcalc.dss
    :param str csvFile:    TransformedLocals.csv
    :param str tsInt:      time step of the output records, e.g. "1HOUR"
    :param str startTime:  start of the time window (simulation lookback time)
    :param str endTime:    end of the time window
    :param str fPart:      F part of the output records
    :param bar:            JProgressBar
    :param txtArea:        JTextArea with a printToGUI method
    :return: list of the pathnames written
    """
    msg = "----------------------------------------------------------------------"
    msg += "\nTRANSFORMING TRIBUTARY FLOWS"
    msg += "\nInput File  : %s" %csvFile
    msg += "\nObserved DSS: %s" %obsDssFile
    msg += "\nOutput DSS  : %s" %outDssFile
    msg += "\nTime Window : %s to %s" %(startTime, endTime)
    msg += "\nTime Step   : %s" %tsInt
    logging.info(msg)
    txtArea.printToGUI("Transforming tributary flows...")
    rows = parseTransformCSV(csvFile)
    obsDss = DSS.open(obsDssFile, startTime, endTime)
    outDss = DSS.open(outDssFile, startTime, endTime)
    failStations = []
    written = []
    prevTSM = None
    for i in range(len(rows)):
        row = rows[i]
        bar.setValue(int(float(i)/len(rows)*100))
        txtArea.printToGUI("Processing: %s" %row["bPart"])
        logging.info("Processing: %s from station %s" %(row["bPart"], row["station"]))
        obsTSM = cDSS.readTSMfromPathnameParts(obsDss, bPart=row["station"], cPart="*FLOW*", ePart=tsInt)
        if obsTSM is None:
            failStations.append("%s (for %s)" %(row["station"], row["bPart"]))
            prevTSM = None
            continue
        newTSM = None
        #If both MOVE.1 and area ratio are defined, MOVE.1 goes first
        if row["aMove1"] is not None and row["bMove1"] is not None:
            tscNew = cTsUtils.move1TransformEqn2(obsTSM.getData(), row["aMove1"], row["bMove1"], row["bcf"])
            if tscNew is None:
                errMsg = "MOVE.1 transformation failed for %s. See the log for details." %row["bPart"]
                logging.error(errMsg)
                txtArea.printToGUI(errMsg)
                obsDss.close()
                outDss.close()
                return None
            newTSM = TimeSeriesMath(tscNew)
        if row["areaRatio"] is not None:
            logging.info("\tArea Ratio: %s" %row["areaRatio"])
            if newTSM:
                newTSM = newTSM.multiply(row["areaRatio"])
            else:
                newTSM = obsTSM.multiply(row["areaRatio"])
        if newTSM is None:
            logging.warning("\tNo transformation defined for %s - copying the gage record" %row["bPart"])
            newTSM = obsTSM
        if prevTSM:
            #the previous row was an ADD - include it
            newTSM = newTSM.add(prevTSM)
        if row["bPart"].upper() == "ADD":
            prevTSM = newTSM
            continue
        prevTSM = None
        outputPath = "//%s/%s//%s/%s/" %(row["bPart"], row["cPart"], tsInt, fPart)
        newTSM.setPathname(outputPath)
        outDss.write(newTSM)
        written.append(outputPath)
        msg = "\tWrote: %s" %outputPath
        logging.info(msg)
        txtArea.printToGUI(msg)
    obsDss.close()
    outDss.close()
    bar.setValue(100)
    if failStations:
        msg = "\nNo gage record found in %s for:" %obsDssFile
        for station in failStations:
            msg += "\n\t%s" %station
        msg += "\nCheck the Station column of %s against obsData.dss." %csvFile
        logging.warning(msg)
        txtArea.printToGUI(msg)
    msg = "\nDone transforming tributary locals. %d record(s) written to %s" %(len(written), outDssFile)
    logging.info(msg)
    txtArea.printToGUI(msg)
    return written
