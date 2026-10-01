# -*- coding: utf-8 -*-
"""
See GIT repository here with ReadMe for more information:
https://nwd-wmshare.nwd.usace.army.mil/git/ResOps/ResSimAltCompare

"""

import xml.etree.ElementTree as ET    
import pandas as pd
import datetime
from datetime import timedelta
import os

###############################################################################
#USER-DEFINED INPUTS

#XML file locations (pathnames are relative to this script location)
ALT1_FILE = "example_data/Temp1Day_InputReport.xml"
#ALT1_FILE = "example_data/FRM_Base1d_InputReport.xml"
#ALT1_FILE = "example_data/F1NA.xml"
ALT2_FILE = "example_data/FRM_Base1d_InputReport.xml"

#ALT1_FILE = "example_data/ALL_OPS_2024-12-10.xml"
#ALT2_FILE = "example_data/ALL_OPS_2025-02-21_.xml"

OUTPUT_FILE = "outputAltCompare.txt"

###############################################################################
#FIXED CONSTANTS
#ResSim stores things that are a "function of" something (e.g. zone type) as a coded number. Here is the lookup
FUNCTION_OF_LOOKUP = {0:"Date", 1:"DateTime",2:"ModelVariable",3:"TimeSeries",4:"StateVariable",5:"2-variable"}
RULE_LIMIT_TYPE_LOOKUP = {-1:"Minimum",0:"Specified",1:"Maximum"}
INTERP_TYPE_LOOKUP = {0:"Linear",2:"Step"}
    

################################################################################

class Alt_Data:
    '''
    Class that represents all relevant data from an alternative
    Typical usage is to supply the alternative .xml file when creating this object,
    which will parse the file and populate it.
    
    After creating two instances of this class (different alternatives),
    they can be fed into the Alt_Compare class
    '''
    def __init__(self, xmlFile):
        self.xmlFile = xmlFile
        self.tree = ET.parse(xmlFile, parser=ET.XMLParser(encoding='latin')) #UTF-8 doesn't work sometimes, there is a weird dash character x96)
        #This weird character pops up in the Brownlee conservation zone description in the CRT model from 2018
        self.root = self.tree.getroot()
        self.altDict = self.parseXMLFile() #Nested dictionary that holds all data
        
        '''
        Examples of how to get data from the xml file
        #Walk the root
        for child in self.root:
            print(child.tag, child.attrib)
        
        # Access specific elements that are only direct children of the root
        for elem in self.root.findall('Alternative_Data'):
            print("tag", elem.tag)
            print("attrib", elem.attrib)
            print("text", elem.text)
            
        # Access specific elements that occur anywhere in the file
        for elem in self.root.iter('Lookback'):
            print("tag", elem.tag)
            print("attrib", elem.attrib)
            print("text", elem.text)
            
        # Get a list of all reservoir names
        x = [e.get("Reservoir_Name") for e in self.root.iter('Reservoir_System')]
        '''

    def parseXMLFile(self):
        '''
        Parses the ResSim alternative xml file and creates a nested python dictionary
        '''
        altDict = {"OpSet":{}, #keys: reservoir name, values=name of Operation Set used
                   "Lookback":{},  #keys: lookback parameter name (e.g. "Big Cliff-Pool Elevation"), values=option chosen (e.g. "Set to Guide Curve")
                   "TimeSeries":{}, #keys: Time Series parameter name (e.g. "Green Peter_Inflow"), values=dss file/pathname (e.g. 'DSSFile="shared/inflows.dss" Pathname="//Test/Flow//1DAY/Test/')
                   "Reach":{}, #keys: reach name, value = nested dictionary (reachDict)
                   "Reservoir":{} #keys: reservoir name, value = nested dictionary (resvDict)
                   }
                
        opSetDict = self.parseOpSets()
        lookbackDict = self.parseLookback()
        timeseriesDict = self.parseTimeSeries()
        reachDict = self.parseReaches()
        resvDict = self.parseReservoirs()
        #Populate the dictionary
        altDict["OpSet"] = opSetDict
        altDict["Lookback"] = lookbackDict
        altDict["TimeSeries"] = timeseriesDict
        altDict["Reach"] = reachDict
        altDict["Reservoir"] = resvDict
        return altDict
            
    def parseOpSets(self):
        '''Returns a dictionary with key as reservor name and value as operation set name'''
        opSetDict = {}
        for e in self.root.iter('Reservoir_System'):
            opSetDict[e.get("Reservoir_Name")] = e.get("Operation_Set")
        return opSetDict
        
    def parseLookback(self):
        '''Returns a nested dictionary
        first level keys: lookback parameter name (e.g. "Big Cliff-Pool Elevation"), 
        values= type/default value: e.g. "Type=Set to Guide Curve, DefaultValue="""
        '''
        lookbackDict = {}
        for e in self.root.iter('Lookback'):
            var = e.get("Variable") #e.g. "Lookback Release"
            var = var.replace("Lookback ","") #No need to keep saying lookback, we already know
            lookbackName = "%s-%s" %(e.get("Location"), var)
            lookbackType = e.get("Type")
            lookbackDefault = e.get("Default_Values")
            lookbackDict[lookbackName] = "Type=%s, DefaultValue=%s" %(lookbackType, lookbackDefault)
        return lookbackDict
    
    def parseTimeSeries(self):
        '''Returns a dictionary
        keys: Time Series parameter name (e.g. "Green Peter_Inflow"), 
        values= dss file/pathname (e.g. 'DSSFile="shared/inflows.dss" Pathname="//Test/Flow//1DAY/Test/')
        '''
        timeseriesDict = {}
        for e in self.root.iter('TimeSeries'):
            tsName = e.get("Name") #e.g. Willamette+Ash Cr_Local_WR_AshCr_S01
            dssFile = e.get("File_Name")
            pathname = e.get("Pathname")
            timeseriesDict[tsName] = "DSSFile=%s, Pathname=%s" %(dssFile, pathname)
        return timeseriesDict
    
    def parseReaches(self):
        '''
        Returns a nested dictionary, with 1st level keys reach names, and values a dictionary like below:
            reachDict = {"Method":"", 
                 "Data":{} #Data is dictionary that varies depending on what routing method is used
                 }
        '''
        reachDict = {}
        for e in self.root.iter('Reach'):
            reachName = e.get("Name")
            eRouting = e.findall('Routing')[0]
            typeName = eRouting.get("Type")
            reachDict[reachName] = {"Method":typeName, "Data":{}}
            if typeName == "NullRouting":
                continue
            subreaches = eRouting.get("NumberOfSubReaches")
            reachDict[reachName]["Data"]["Subreaches"] = subreaches
            if typeName == "ModifiedPulse":
                #Create a dataframe of storage vs outflow
                outflows = [float(record.get('Outflow')) for record in eRouting]
                storages = [float(record.get('Storage')) for record in eRouting]
                dfStorOutflow = pd.DataFrame()
                dfStorOutflow["Outflow"] = outflows
                dfStorOutflow["Storage"] = storages
                reachDict[reachName]["Data"]["Table"] = dfStorOutflow
            elif typeName == "MuskingumRouting":
                reachDict[reachName]["Data"]["K"] = float(eRouting.get('MuskingumK'))
                reachDict[reachName]["Data"]["X"] = float(eRouting.get('MuskingumX'))
            elif typeName == "SsarrRouting":
                if "KTS" in eRouting.attrib:
                    reachDict[reachName]["Data"]["KTS"] = float(eRouting.get('KTS'))
                    reachDict[reachName]["Data"]["n"] = float(eRouting.get('NumberOfCoefficients'))
                else:
                    #Defined as table of outflow and time of storage
                    elemRelease = eRouting.findall('Outflow')[0]
                    outflows = self.readArray(elemRelease)
                    elemTS = eRouting.findall('TimeOfStorage')[0]
                    timeOfStorages = self.readArray(elemTS)
                    dfStorOutflow = pd.DataFrame()
                    dfStorOutflow["Outflow"] = outflows
                    dfStorOutflow["TimeOfStorage"] = timeOfStorages
                    reachDict[reachName]["Data"]["Table"] = dfStorOutflow
            else:
                #other methods
                pass
        return reachDict
    
    def parseReservoirs(self):
        '''
        Returns a nested dictionary, with 1st level keys reservoir names, and values a dictionary
        '''
    
        resvDict = {}
        for e in self.root.iter('Reservoir'):
            resvName = e.get("Name")
            resvDict[resvName] = {
                    "ElevStor":None, #pandas dataframe with elev/stor
                    "Outlet":{}, 
                    "Zone":{}, 
                    "Rule":{}, 
                    "If_Blocks":{}
                    }
            elevStor = self.parseElevStor(e)
            outletDict = self.parseOutlets(e)
            zoneDict = self.parseZones(e)
            ruleDict = self.parseRules(e)
            
            resvDict[resvName]["ElevStor"] = elevStor
            resvDict[resvName]["Outlet"] = outletDict
            resvDict[resvName]["Zone"] = zoneDict
            resvDict[resvName]["Rule"] = ruleDict
        return resvDict
            
    def readArray(self, elemArray, attribName="D"):
        '''
        The alternative xml file has a weird format for many arrays where
        it only spits out 10 elements at a time. We want single array of all elements,
        not split by 10.
        
        This function will properly read something that looks like:
              <doubleArray Length="103" Step="10">
                <D Range="0-9" Data="1106.0,1108.0,1110.0,1111.0,1112.0,1113.0,1114.0,1115.0,1116.0,1117.0" />
                <D Range="10-19" Data="1118.0,1119.0,1120.0,1121.0,1122.0,1123.0,1124.0,1125.0,1126.0,1127.0" />
                <D Range="20-29" Data="1128.0,1129.0,1130.0,1131.0,1132.0,1133.0,1134.0,1135.0,1136.0,1137.0" />
                <D Range="30-39" Data="1138.0,1139.0,1140.0,1141.0,1142.0,1143.0,1144.0,1145.0,1146.0,1147.0" />
                <D Range="40-49" Data="1148.0,1149.0,1150.0,1151.0,1152.0,1153.0,1154.0,1155.0,1156.0,1157.0" />
                <D Range="50-59" Data="1158.0,1159.0,1160.0,1161.0,1162.0,1163.0,1164.0,1165.0,1166.0,1167.0" />
                <D Range="60-69" Data="1168.0,1169.0,1170.0,1171.0,1172.0,1173.0,1174.0,1175.0,1176.0,1177.0" />
                <D Range="70-79" Data="1178.0,1179.0,1180.0,1181.0,1182.0,1183.0,1184.0,1185.0,1186.0,1187.0" />
                <D Range="80-89" Data="1188.0,1189.0,1190.0,1191.0,1192.0,1193.0,1194.0,1195.0,1196.0,1197.0" />
                <D Range="90-99" Data="1198.0,1199.0,1200.0,1201.0,1202.0,1203.0,1204.0,1205.0,1206.0,1207.0" />
                <D Range="100-103" Data="1208.0,1209.0,1210.0" />
              </doubleArray>
        '''
        outList = []
        for e in elemArray.iter(attribName):
            outList.extend(e.get("Data").split(","))
        #convert to float
        outList = [float(item) for item in outList]
        if attribName == "I":
            #Not a double, an integer
            #This is minutes past 31Dec 0000
            #So "01JAN" in the input table is actually "01JAN 0000"
            #"01JAN" is 1440, which is 1440 minutes past 31Dec 0000
            #Convert to date in format DDMMM
            #The table is defined for a non-leap year
            baseDate = datetime.datetime(2001,12,31)
            outList = [(baseDate + timedelta(minutes=item)).strftime("%d%b") for item in outList]
        return outList
    
    def parseElevStor(self, elemResv):
        '''
        Returns elev-stor table as a pandas dataframe
        '''
        elemElev = elemResv.findall('Res_Physical_Data/Res_Pool/Pool_Elevation')[0]
        elevs = self.readArray(elemElev)
        #TODO As of 3/20/2025 (ResSim 3.5), there is a bug in the alternative xml exporter
        #So that the storage values are stored as Area
        #elemStor = elemResv.findall('Res_Physical_Data/Res_Pool/Storage')[0]
        elemStor = elemResv.findall('Res_Physical_Data/Res_Pool/Area')[0]
        stors = self.readArray(elemStor)
        df = pd.DataFrame({"Elev":elevs,"Stor":stors})
        return df

    def parseOutlets(self, elemResv):
        '''
        Returns a dictionary with outlet information for the given reservoir 
        1st level key is outlet name
        value is a dictionary with the following keys: "Type", "NumGates", "ElevReleaseTable"
        '''
        outletDict = {}
        resvName = elemResv.get("Name")
        outletElemTypes = ['Controlled_Outlet', 'Spillway', 'Power_Plant']
        for outletElemType in outletElemTypes:
            for elemOutlet in elemResv.iter(outletElemType):
                outletName = elemOutlet.get("Name").replace(resvName+"-","") #e.g. 'Detroit-Upper Controlled Outlet'
                outletDict[outletName] = {
                        "Type":outletElemType,
                        "NumGates":0,
                        "ElevReleaseTable": pd.DataFrame()
                         }
                #Get the necessary attributes
                if outletElemType == "Spillway":
                    elemElev = elemOutlet.findall('Elevation')[0]
                    elevs = self.readArray(elemElev)
                    elemFlow = elemOutlet.findall('Outflow')[0]
                    flows = self.readArray(elemFlow)
                    df = pd.DataFrame({"Elev":elevs,"Flow":flows})
                elif outletElemType == "Power_Plant":
                    numGates = elemOutlet.get("Number_of_Gates")
                    outletDict[outletName]["NumGates"] = numGates
                    elemElev = elemOutlet.findall('Gate_Elevation')[0]
                    elevs = self.readArray(elemElev)
                    elemFlow = elemOutlet.findall('Gate_MaxCapacity')[0]
                    flows = self.readArray(elemFlow)
                    df = pd.DataFrame({"Elev":elevs,"Flow":flows})
                elif outletElemType == "Controlled_Outlet":
                    numGates = elemOutlet.get("Number_of_Gates")
                    outletDict[outletName]["NumGates"] = numGates
                    #TODO As of 3/20/2025 (ResSim 3.5), there is a bug in the alternative xml exporter
                    #So that each gate setting capacity just repeats the elevations over and over
                    df = pd.DataFrame()
                else:
                    df = pd.DataFrame()
                outletDict[outletName]["ElevReleaseTable"] = df
        return outletDict

    def parseZones(self, elemResv):
        '''
        Returns a dictionary that represents all zone definitions at a given reservoir
        keys are zone names
        values is a dictionary with the following keys: "FunctionOf", "Table", "RuleList"
        '''
        zoneDict = {}
        for elemZone in elemResv.iter("Zone"):
            zoneName = elemZone.get("Name")
            zoneDict[zoneName] = {}
            zoneFunctionOfCode = int(elemZone.get("Function_Of"))
            zoneFunctionOfName = FUNCTION_OF_LOOKUP[zoneFunctionOfCode]
            #Get the data table
            df = pd.DataFrame()
            if zoneFunctionOfName in ["Date", "DateTime"]:
                elemDate = elemZone.findall('Date')[0]
                dates = self.readArray(elemDate, "I")                
                elemElev = elemZone.findall('Elevations')[0]
                elevs = self.readArray(elemElev)
                #The last value is a repeat that doesn't show up in the GUI, drop it
                dates = dates[:-1]
                elevs = elevs[:-1]
                df = pd.DataFrame({"Date":dates, "Elev":elevs})
            elif zoneFunctionOfName in ["TimeSeries", "StateVariable"]:
                #No data table in the file, leave it empty
                pass
            elif zoneFunctionOfName in ["ModelVariable", "2-variable"]:
                #TODO bug as of 3/21/2025: The xml file doesn't actually have the data table
                pass
            else:
                #Other options are not supported
                pass
            #Get the rule list
            elemRuleRef = elemZone.findall('RuleRefsUsed')[0]
            ruleList = [record.get('Name') for record in elemRuleRef]
            #Populate the dictionary
            zoneDict[zoneName]["FunctionOf"] = zoneFunctionOfName
            zoneDict[zoneName]["Table"] = df
            zoneDict[zoneName]["RuleList"] = ruleList
        return zoneDict
    
    def parseRules(self, elemResv):
        '''
        Returns a dictionary that represents all rules at a given reservoir
        keys are rule names
        values is a dictionary with the following keys: "LimitType", "InterpType", "FunctionOf", "Table"
        '''
        ruleDict = {}
        for elemRule in elemResv.iter("Rule"):
            ruleName = elemRule.get("Name")
            #TODO as of 3/21/2025, bug in the xml export doesn't export rule Name for rules of type InducedSurcharge or Scripted
            if ruleName is None: continue
            ruleDict[ruleName] = {}
            #Get what the rule is a function of
            ruleFunctionOfName = ""
            if "Function_Of" in elemRule.attrib:
                ruleFunctionOfCode = int(elemRule.get("Function_Of"))
                ruleFunctionOfName = FUNCTION_OF_LOOKUP[ruleFunctionOfCode]
            #Get the limit type
            limitType = "Minimum" #default, applies for induced surcharge too
            if "Limit_Type" in elemRule.attrib: 
                limitTypeCode = int(elemRule.get("Limit_Type"))
                limitType = RULE_LIMIT_TYPE_LOOKUP[limitTypeCode]
            #Get the interpolation type
            interpTypeCode = int(elemRule.get("InterpType"))
            interpType = INTERP_TYPE_LOOKUP[interpTypeCode]
            #Get the data table
            df = self.getRuleDF(elemRule, ruleFunctionOfName)
            #Set the values of the dictionary
            ruleDict[ruleName]["LimitType"] = limitType
            ruleDict[ruleName]["FunctionOf"] = ruleFunctionOfName
            ruleDict[ruleName]["InterpType"] = interpType
            ruleDict[ruleName]["Table"] = df
        
        return ruleDict

    def getRuleDF(self, elemRule, ruleFunctionOfName):
        '''
        Returns a dataframe representing the rule table that you see in the GUI
        '''
        df = pd.DataFrame()
        if "TimeOfRecession" in elemRule.attrib:
            #Induced surcharge rule. Doesn't have all normal attributes
            #e.g. <Rule Rule="InducedSurcharge" TimeOfRecession="24.0" InterpType="0">
            elemElev = elemRule.findall('ISEnvelopeCurve_Elevation')[0]
            elevs = self.readArray(elemElev)
            elemRelease = elemRule.findall('ISEnvelopeCurve_Release')[0]
            flows = self.readArray(elemRelease)
            df = pd.DataFrame({"Elev":elevs, "Release":flows})
        if ruleFunctionOfName in ["Date", "DateTime"]:
            elemDate = elemRule.findall('Date')[0]
            dates = self.readArray(elemDate, "I")               
            #TODO bug 3/21/2025: For rules defined as a function of date, the release table is given the xml tag of "Elevation" rather than "Flow"
            elemRelease = elemRule.findall('Elevations')[0]
            flows = self.readArray(elemRelease)
            #The last value is a repeat that doesn't show up in the GUI, drop it
            dates = dates[:-1]
            flows = flows[:-1]
            df = pd.DataFrame({"Date":dates, "Release":flows})
        elif ruleFunctionOfName in ["ModelVariable", "TimeSeries", "StateVariable"]:
            #very similar processing for these
            tagNameLookup = {"ModelVariable": "ModelVariable", 
                             "TimeSeries":"TimeSeriesVariable",
                             "StateVariable":"StateVariable"} #tag in xml file
            tagName = tagNameLookup[ruleFunctionOfName]
            elemVar = elemRule.findall(tagName)[0]
            varsList = self.readArray(elemVar)
            if elemRule.get("HasSeasonalVariation") == "true":
                df = pd.DataFrame({ruleFunctionOfName:varsList})
                for i, eChild in enumerate(elemRule):
                    if eChild.tag == tagName: continue
                    #paramName = eChild.tag #The xml exporter puts all the table columns as "Parameter1"
                    flows = self.readArray(eChild)
                    colName = "Column %s" %i
                    df[colName] = flows
            else:
                #Just a simple table
                elemRelease = elemRule.findall('Parameter')[0]
                flows = self.readArray(elemRelease)
                df = pd.DataFrame({ruleFunctionOfName:varsList, "Release":flows})
        return df
        
class Alt_Compare:
    '''
    Class to compare two alternatives and write out differences to a text file
    
    Typical usage
    
    Alt_Compare(altData1, altData2, outputFile, logLevel)
    '''
    def __init__(self, altData1, altData2, outputFile, logLevel="Detailed"):
        self.altData1 = altData1
        self.altData2 = altData2
        self.altDict1 = altData1.altDict
        self.altDict2 = altData2.altDict
        self.outFile = outputFile
        
        self.log = ""
        self.printToConsole = True
        self.compareAlts()
    
    def addToLog(self, strToAdd):
        self.log = "%s\n%s" %(self.log, strToAdd)
        if self.printToConsole: print(strToAdd)
        
    def addToLogIfNoMatch(self, thing1, thing2, logIntroMsg="Mismatch:"):
        '''
        Checks that 2 things match, and if not, logs a message
        Also returns True if they are a match, False if not a match
        '''
        isMatch = self.areEqual(thing1, thing2)
        if isMatch:
            return True
        self.logBothAltValues(thing1, thing2, logIntroMsg)
        return False
        
    def compareAlts(self):
        '''
        The main function to compare two alternatives
        '''
        altDict1 = self.altDict1
        altDict2 = self.altDict2
        
        self.addToLog("Comparing two alternatives")
        self.addToLog("Alt1: %s" %self.altData1.xmlFile)
        self.addToLog("Alt2: %s" %self.altData2.xmlFile)
        
        #Thought about walking the whole dictionary in a standard way, but it was too hard with the recursion of a nested dictionary
        #Go parameter by parameter instead. A bit of duplication, but not horrible
        
        #OpSets
        self.addToLog("\nChecking OpSets")
        dict1 = altDict1["OpSet"]
        dict2 = altDict2["OpSet"]
        self.checkSimpleDict(dict1, dict2, "Reservoir Names", "Operation Set")

        #Time Series mapping
        self.addToLog("\nChecking Time Series Mapping")
        dict1 = altDict1["TimeSeries"]
        dict2 = altDict2["TimeSeries"]
        self.checkSimpleDict(dict1, dict2, "Time Series Locations", "Time Series Mapping")     
        
        #Lookback
        self.addToLog("\nChecking Lookback Mapping")
        dict1 = altDict1["Lookback"]
        dict2 = altDict2["Lookback"]
        self.checkSimpleDict(dict1, dict2, "Lookback Locations", "Lookback Input")          
        
        #Reaches
        self.addToLog("\nChecking Reaches")
        dict1 = altDict1["Reach"]
        dict2 = altDict2["Reach"]
        self.addToLogIfNoMatch(sorted(dict1.keys()), sorted(dict2.keys()), "Mismatch: Reach Names")
        for reachName, reachDict1 in dict1.items():
            if not reachName in dict2: continue
            reachDict2 = dict2[reachName]
            isMatch = self.addToLogIfNoMatch(reachDict1["Method"], reachDict2["Method"], "Mismatch: Method at %s" %reachName)
            if isMatch and reachDict1["Method"] != "NullRouting": #Check the table too
                dataDict1 = reachDict1["Data"]
                dataDict2 = reachDict2["Data"]
                self.checkSimpleDict(dataDict1, dataDict2, "Parameter Name at %s" %reachName, "Value at %s" %reachName)    
                #self.addToLogIfNoMatch(dataDict1["Subreaches"], dataDict2["Subreaches"], "Mismatch: Subreaches at %s" %reachName)
                #self.addToLogIfNoMatch(dataDict1["Table"], dataDict2["Table"], "Mismatch: Routing Table at %s" %reachName)
        
        #Reservoirs
        self.addToLog("\nChecking Reservoirs")
        dict1 = altDict1["Reservoir"]
        dict2 = altDict2["Reservoir"]
        for resvName, resvDict1 in dict1.items():
            if not resvName in dict2: continue
            resvDict2 = dict2[resvName]
            #ElevStor
            self.addToLogIfNoMatch(resvDict1["ElevStor"], resvDict2["ElevStor"], "Mismatch: Elevation-Storage Table at %s" %resvName)
            #Outlets
            self.addToLogIfNoMatch(sorted(resvDict1["Outlet"].keys()), sorted(resvDict2["Outlet"].keys()), "Mismatch: Outlet Names at %s" %resvName)
            for outletName, outletDict1 in resvDict1["Outlet"].items():
                if not outletName in resvDict2["Outlet"]: continue
                outletDict2 = resvDict2["Outlet"][outletName]
                #Check outlet types
                isMatch = self.addToLogIfNoMatch(outletDict1["Type"], outletDict2["Type"], "Mismatch: Outlet Type at %s: %s" %(resvName, outletName))
                if not isMatch: continue
                for outletParamName, val in outletDict1.items():
                    self.addToLogIfNoMatch(outletDict1[outletParamName], outletDict2[outletParamName], "Mismatch: Outlet Data at %s: %s: %s" %(resvName, outletName, outletParamName))
            #Zones
            for zoneName, zoneDict1 in resvDict1["Zone"].items():
                if not zoneName in resvDict2["Zone"]: continue
                zoneDict2 = resvDict2["Zone"][zoneName]
                #Do the rule stack
                self.addToLogIfNoMatch(zoneDict1["RuleList"], zoneDict2["RuleList"], "Mismatch: Rule stack at %s: %s" %(resvName, zoneName))
                #Zone definition
                isMatch = self.addToLogIfNoMatch(zoneDict1["FunctionOf"], zoneDict2["FunctionOf"], "Mismatch: Zone definition as a function of at %s: %s" %(resvName, zoneName))
                if isMatch:
                    self.addToLogIfNoMatch(zoneDict1["Table"], zoneDict2["Table"], "Mismatch: Zone table at %s: %s" %(resvName, zoneName))
            #Rules
            for ruleName, ruleDict1 in resvDict1["Rule"].items():
                if not ruleName in resvDict2["Rule"]: continue
                ruleDict2 = resvDict2["Rule"][ruleName]
                #Limit Type
                self.addToLogIfNoMatch(ruleDict1["LimitType"], ruleDict2["LimitType"], "Mismatch: Rule type at %s: %s" %(resvName, ruleName))
                #Function of
                isMatch = self.addToLogIfNoMatch(ruleDict1["FunctionOf"], ruleDict2["FunctionOf"], "Mismatch: Rule function of at %s: %s" %(resvName, ruleName))
                if isMatch:
                    self.addToLogIfNoMatch(ruleDict1["InterpType"], ruleDict2["InterpType"], "Mismatch: Rule interpolation type at %s: %s" %(resvName, ruleName))
                    self.addToLogIfNoMatch(ruleDict1["Table"], ruleDict2["Table"], "Mismatch: Rule table at %s: %s" %(resvName, ruleName))
                
        #Write it to output
        writeTextToFile(self.log, self.outFile)
        
        
    def checkSimpleDict(self, dict1, dict2, keyName, valName):
        '''
        If you have a simple dictionary (not nested), this will check both the keys and the values
        keyName = string, a description of what the keys are (e.g. "Reservoir Names")
        valName = string, a description of what the values are (e.g. "Lookback Mapping")
        '''
        #Check the keys
        self.addToLogIfNoMatch(sorted(dict1.keys()), sorted(dict2.keys()), "Mismatch: %s" %keyName)
        #Check the linking
        for key, val1 in dict1.items():
            if key not in dict2: continue
            val2 = dict2[key]
            self.addToLogIfNoMatch(val1, val2, "Mismatch: %s is different for: %s" %(valName, key))
        
    def logBothAltValues(self, thing1, thing2, logIntroMsg="Mismatch:"):
        '''
        Usually, if there is a mismatch, we want to add it to the log
        This will do that
        '''
        self.addToLog(logIntroMsg)
        
        self.addToLog("Alt1:%s" %self.toString(thing1))
        self.addToLog("Alt2:%s" %self.toString(thing2))
        
    def toString(self, thing):
        '''
        Creates a nice string representation of an object that will print nicely
        For instance, if you input a list, it will have a new line for each list entry
        rather than showing it as comma delimited
        '''
        if isinstance(thing, list):
            outStr = ""
            for l in thing:
                outStr += "\n%s" %l
        elif isinstance(thing, pd.DataFrame):
            outStr = "\n" + thing.to_string(index=False)
        else:
            outStr = str(thing)
        return outStr
    
    def areEqual(self, thing1, thing2):
        '''
        Compares 2 objects.
        Currently supports:
            string
            float
            list
            DataFrame
        
        Does not support dictionaries
        
        returns True if the same
        returns False if not the same
        '''
        isMatch = True
        
        if thing1.__class__ != thing2.__class__:
            isMatch = False
        if thing1 is None or isinstance(thing1, str) or isinstance(thing1, list) or isinstance(thing1, int) or isinstance(thing1, float):
            if thing1 != thing2:
                isMatch = False
        elif isinstance(thing1, pd.DataFrame):
            if not thing1.equals(thing2):
                isMatch = False
        else:
            print("Class not supported: %s" %thing1.__class__)
        
        return isMatch

def ensure_dir(f):
    """
    Create any necessary directories found in "f", if they don't exist
    # e.g. f = "C:/RAFT/GIS/foo/bar", foo and bar folders will be created
    """
    d = os.path.dirname(f)
    if d != "" and not os.path.exists(d):
        os.makedirs(d)
    return None

def checkIfFileOpen(filePath):
    """Returns True if the file is open by another application (e.g. Excel)"""
    if not os.path.exists(filePath):
        #Can't be open by another application if it doesn't even exist
        return False
    try:
        myfile = open(filePath, "r+") # or "a+", whatever you need
        myfile.close()
        return False
    except IOError:
        return True
        
def writeTextToFile(msg, txtFileName):
    """
    Save some text to a file
    
    :param msg: String or list of strings, the message to be written
    :param str txtFileName: The full pathname of the text file (e.g. C:\test.txt)
    """
    if checkIfFileOpen(txtFileName):
        msg = "Could not open file! Please close the file and try again:\n%s" %txtFileName
        raise AssertionError(msg)
    ensure_dir(txtFileName)
    outFile = open(txtFileName, 'w')
    if isinstance(msg, list):
        #more efficient to use writelines when a really large text file with lines
        outFile.writelines(msg)
    else:
        #Assumes line breaks are already defined in the string to be output ("\n")
        outFile.write(msg)
    outFile.close()
    return None

###############################################################################
#MAIN CODE

altData1 = Alt_Data(ALT1_FILE)
altData2 = Alt_Data(ALT2_FILE)
Alt_Compare(altData1, altData2, OUTPUT_FILE)

