"""
Module that allows naming conventions to be converted.
It expects there to be a "naming conversion" .csv file in this directory called
"LocationAlias.csv", as well as "ParamAlias.csv".
When this module is imported, it will load in the .csv file automatically.
The object created is called "myLocationAlias" for locations, "myParamAlias" for parameters.
After importing this module, just use the myNameAlias object. Typical usage::

    from NWDJyLib.FixedData import NameAlias
    foo = NameAlias.myLocationAlias.lookup("SPDI", "CBT_CODE", "USGS_CODE")
    foo = NameAlias.myParamAlias.lookup("QR", "SHEF_CODE", "RESSIM_PARAM")

As of January 2016, the following keywords for "typeStr" are supported for locations

        -MODIFIED_FLOW_CODE    Modified Flow Report naming convention (e.g. ARD)
        -CBT_CODE              e.g. ARDB or LIB
        -CBT_NAME              e.g. Arrow Dam
        -CBT_CODE_LAKE         Only applicable if a natural lake, e.g. FQRB or HOPI
        -RESSIM_NAME           Name used in CRT ResSim convention (e.g. Arrow Lakes)
        -NWRFC_CODE            e.g. ARDQ2
        -USGS_CODE             e.g. 12304500
        -USGS_NAME             e.g. Yaak River near Troy MT

For parameters, the following keywords are supported:

        -SHEF_CODE     e.g. QR, similar to what you see in Dataquery
        -CWMS_PARAM    e.g. Flow-Pump, what you would see in DBQuery or CWMS
        -RESSIM_PARAM  e.g. Elev-Pool, what ResSim likes to output
        -NWRFC_CODE    e.g. SSTG, what the NWRFC uses
        
"""

import os
#Custom imports
from NWDJyLib import cFile
################################################################################
# STATIC INPUT
CSV_LOCATIONS = "LocationAlias.csv"
CSV_PARAMETERS = "ParamAlias.csv"
################################################################################
# CLASS DEFINITIONS
myLocationAlias = None
myParamAlias = None

class Alias:
    """ 
    This class allows an alias dictionary to be populated and looked up later to
    convert naming conventions at will. 
    The most typical way to use this is to have the name aliases defined in a csv file.
    Load it in using :meth:`initializeFromCSV`, and then use 
    :meth:`lookup` to convert between names.
    This is definitely not as efficient as a database, but it's pretty useful to
    have your name conversions defined in a csv file rather than hardcoded.
    """
    
    def __init__(self):
        self.masterDict = {} #keys are header names, values are the list of values
    
    def setMasterDict(self, masterDict):
        """
        If a dictionary has already been set up that is of the proper format,
        it can be used to initialize this object and used for a lookup.
        """
        self.masterDict = masterDict
    def _initializeDict(self, typeStrList):
        """
        Initialize the master dictionary. 
        :param list typeStrList: A list of strings. The types of names
                  (e.g. ["CBT_Code", "BPA_Name", "common_name"])
        """
        self.masterDict = {}
        #Create an empty list for each name type
        for typeStr in typeStrList:
            self.masterDict[typeStr] = []
    
    def _addDict(self, dictObj):
        """
        Add one item to the master lookup dictionary.
        
        :param dict dictObj: A dictionary object with keys as name type, 
                             values are strings for the corresponding name
        """
        for typeName in dictObj:
            nameStr = dictObj[typeName]
            self.masterDict[typeName].append(nameStr)
    
    def initializeFromCSV(self, csvFile):
        """
        Initializes the object from a .csv file.
        The .csv file should have name types as columns
        """
        if not cFile.doesFileExist(csvFile):
            print("Failed to initialize Name Alias Dictionary--file doesn't exist: ")
            print(csvFile)
            return None
        lines = cFile.fileOpenReadClose(csvFile)
        lines = cFile.stripOutCommentLines(lines)
        csvDictReader = cFile.getCSVDictReader(lines)
        for i, csvDict in enumerate(csvDictReader):
            #.fieldnames isn't populated until we begin iterating
            if i == 0: self._initializeDict(csvDictReader.fieldnames)
            self._addDict(csvDict)
        return True
        
    def typeExists(self, typeStr):
        """Return True if the specified name type exists in the master dictionary"""
        if typeStr in self.masterDict.keys(): 
            return True
        else: 
            return False
    
    def _getNameIndex(self, nameStr, typeStr):
        """Private function to get the index of occurrence of the name.
        Returns None if the name isn't found in the typeStr name type.
        Case-insensitive"""
        nameList = self.masterDict[typeStr]
        #Convert the lookup name and the list to upper case to ensure a match
        lookupList = [name.upper() for name in nameList]
        nameStrUpper = nameStr.upper()
        if nameStrUpper in lookupList:
            nameIndex = lookupList.index(nameStrUpper)
            return nameIndex
        else:
            return None
            
    def nameExists(self, nameStr, typeStr):
        """Detect whether the input name exists in the master dictionary.
        This is just as computationally intensive as actually using :meth:`lookup`
        , so it is more advantageous usually just to skip this functionality.
        
        :param str nameStr: The name that will be tested
        :param str typeStr: The name type to do the lookup on.
                            If None, the function will check all name types
        :return boolean result: Return True if the name exists, False otherwise
        """
        found = False
        if typeStr is None:
            #Check all name types
            for nameType in self.masterDict.keys():
                nameIndex = self._getNameIndex(nameStr, nameType)
                if nameIndex is not None:
                    found = True
                    break
        else: 
            #Check a specific name type
            if not self.typeExists(typeStr):
                return False
            nameIndex = self._getNameIndex(nameStr, typeStr)
            if nameIndex is not None:
                found = True
        if found:
            return True
        else: 
            return False
        
    def lookup(self, nameStr, fromType, toType):
        """The main functionality of the object is here. Looks up an alias
        for a desired name. Case-insensitive
        
        :param str nameStr: The name to lookup (e.g. "SPDI")
        :param str fromType: The name type of the input name (e.g. "CBT_Code")
        :param str toType: The name type of the output name (e.g. "USGS_Code")
        :return outName: The name that was looked up (or None if no match)
        """
        if not self.typeExists(fromType) or not self.typeExists(toType):
            print("name type not found in lookup dictionary: %s,%s" %(fromType, toType))
            return None
        nameIdx = self._getNameIndex(nameStr, fromType)
        if nameIdx is None: 
            #print "name not found in lookup dictionary: %s,%s" %(nameStr, fromType)
            return None
        outputName = self.masterDict[toType][nameIdx]
        if outputName == "": #not defined for the output type
            return None
        return outputName
        
# END OF CLASS DEFINITIONS
################################################################################
# FUNCTION DEFINITIONS
def _initializeObject():
    """Create a Alias object from the csv file in the current directory"""
    scriptDir = os.path.dirname(__file__)
    csvFileName = os.path.join(scriptDir, CSV_LOCATIONS)
    myLocationAlias = Alias()
    myLocationAlias.initializeFromCSV(csvFileName)
    #print myNameAlias.lookup("SPDI", "CBT_CODE", "USGS_CODE")
    #repeat for parameters
    csvFileName = os.path.join(scriptDir, CSV_PARAMETERS)
    myParamAlias = Alias()
    myParamAlias.initializeFromCSV(csvFileName)
    return myLocationAlias, myParamAlias
    
myLocationAlias, myParamAlias = _initializeObject()