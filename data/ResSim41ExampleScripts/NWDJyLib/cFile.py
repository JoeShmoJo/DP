"""
Contains code to manipulate text files and process CSV files.
Also contains code for general operating system file management.
"""

import io
import os
import sys
import csv
import shutil

################################################################################
# STATIC INPUT

################################################################################
# CLASS DEFINITIONS

# END OF CLASS DEFINITIONS
################################################################################
# FUNCTION DEFINITIONS

def ensure_dir(f):
    """
    Create any necessary directories found in "f", if they don't exist
    # e.g. f = "C:/RAFT/GIS/foo/bar", foo and bar folders will be created
    """
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)
    return None

def doesFileExist(fName):
    """Return True if the file specified by fName (string) exists"""
    return os.path.exists(fName)
    
def delete(fName):
    """Deletes the specified file or folder. If it doesn't exist, does nothing.
    Returns True if successful, False if not."""
    if not os.path.exists(fName): 
        #It's already gone--no need to raise alarm
        return True
    if os.path.isfile(fName):
        try: 
            os.remove(fName)
        except: 
            return False
    if os.path.isdir(fName):
        try: 
            #os.rmdir only works if the directory is empty
            #Delete the folder and all subfolders/files
            shutil.rmtree(fName)
        except: 
            return False
    return True
    
def copyFile(src, dst):
    """Copies the src file to the dst. Uses shutil.copy2"""
    try:
        shutil.copy2(src, dst)
    except:
        return False
    return True
    
def fileOpenReadClose(txtFileName):
    """Open a text file and reads the lines, storing as a list"""
    if not os.path.exists(txtFileName): 
        errMsg = "File does not exist: \n%s" %txtFileName
        raise AssertionError(errMsg)
    txtFile = open(txtFileName, 'r')
    txtLines = txtFile.readlines()
    txtFile.close()
    return txtLines

def fileOpenReadCloseWithEncoding(txtFileName, encoding):
    """Open a text file and reads the lines, storing as a list"""
    if not os.path.exists(txtFileName): 
        errMsg = "File does not exist: \n%s" %txtFileName
        raise AssertionError(errMsg)
    txtFile = io.open(txtFileName, 'r', encoding=encoding)
    txtLines = txtFile.readlines()
    txtFile.close()
    return txtLines

def stripOutCommentLines(txtLines):
    """
    Strip out comment lines from list of strings (assumes comment character is #).
    Returns a list of strings."""
    newLines = []
    for txtLine in txtLines:
        line = txtLine.strip()
        if len(line) == 0 : pass               # skip blank lines
        elif line.count(",") == len(line) : pass # CSV file with only commas
        elif line.startswith("#") : pass       # commented line
        elif line.startswith('"#') : pass      # commented line
        elif line.startswith('",') : pass      # commented line
        elif line.startswith('\xef\xbb\xbf') : pass #junk UTC encoding characters
        else : 
            #strip out any inline comments
            if "#" in line:
                cmtIdx = line.find("#") #returns -1 if not found
                line = line[:cmtIdx].strip()
            newLines.append(line)
    return newLines
    
def checkIfFileOpen(filePath):
    """Returns True if the file is open by another application (e.g. Excel)"""
    if not os.path.exists(filePath):
        #Can't be open by another application if it doesn't even exist
        return False
    try:
        myfile = open(filePath, "r+") # or "a+", whatever you need
        myfile.close()
        return False
    except IOError(FileNotFoundException):
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
    outFile = open(txtFileName, 'w')
    if isinstance(msg, list):
        #more efficient to use writelines when a really large text file with lines
        outFile.writelines(msg)
    else:
        #Assumes line breaks are already defined in the string to be output ("\n")
        outFile.write(msg)
    outFile.close()
    return None

def getCSVReader(txtLines):
    """
    Gets a CSV Reader object (see https://docs.python.org/2/library/csv.html)
    You can iterate on this object, but not get a specific line.
    
    :param list txtLines: list of strings (comment lines should already be 
                          erased, and first line should be headers)
    :return csv.reader: A list of list objects (one list of strings for each line)
    """
    return csv.reader(txtLines)
    
def getCSVDictReader(txtLines):
    """
    Gets a CSV DictReader object.
    You can iterate on this object, but not get a specific line.
    Note that the .fieldnames parameter is not available until you've iterated once
    by using .next() or going inside a for-loop.
    If you want a list, use :func:`convertCSVDictReaderToListDict`
    
    :param list txtLines: list of strings (comment lines should already be 
                          erased, and first line should be headers)
    :return list: A list of dictionary objects (one dictionary for each line)
                  keys of the dictionary are the column header names
    """
    return csv.DictReader(txtLines)
    
def convertCSVDictReaderToListDict(csvDictObj):
    """
    Takes a csv.DictReader object and "listifies" it so you don't have to iterate on it
    """
    outList = []
    for d in csvDictObj: outList.append(d)
    return outList

def mergeListOfDicts(list_of_dicts):
    merged_dict = {}
    for d in list_of_dicts:
        for key, value in d.items():
            if key not in merged_dict:
                merged_dict[key] = []
            merged_dict[key].append(value)
    return merged_dict

def getListOfDictsFromCSV(txtFile):
    """
    Included for backward compatibility, and because it is difficult to discern
    the field names of a .csv file using csv.DictReader without starting to iterate.
    If lines are just read with a DictReader, the .fieldnames attribute won't be 
    populated until you've iterated once on the object.
    Returns a list of dictionaries (one dictionary for each row in the file).
    The keys of the dictionaries are the column header names. 
    
    Assumes csv file is encoded in utf-8-sig
    
    :param str txtFile: .csv file with the column headings
    """
    lines = fileOpenReadCloseWithEncoding(txtFile, 'utf-8-sig')
    lines = stripOutCommentLines(lines)
    csvDict = getCSVDictReader(lines)
    listDict = convertCSVDictReaderToListDict(csvDict)
    headers = csvDict.fieldnames
    return listDict, headers

# def convertRowDictsToNestedDict(listDict):
    # """
    # Converts a list of row-oriented dictionaries (from getListOfDictsFromCSV)
    # into a nested dictionary where the first level keys are column names 
    # (e.g., reservoir names) and second level keys are parameter names 
    # (e.g., 'drawdownTargetElevs').

    # :param list listDict: List of dictionaries, each representing a row
    # :return dict: Nested dictionary [column_name][parameter] = value
    # """
    # nested = {}
    # for row in listDict:
        # param = row["ResSimName"]
        # for resName in row:
            # if resName == "ResSimName":
                # continue
            # if resName not in nested:
                # nested[resName] = {}
            # nested[resName][param] = row[resName]
    # return nested

def getCSVDictWithHeaders(txtFile):
    listDict, headers = getListOfDictsFromCSV(txtFile)
    csvHeaderDict = mergeListOfDicts(listDict)
    return csvHeaderDict
    
################################################################################
# MIGRATED FUNCTIONS (IF MOVED TO ANOTHER MODULE, FOR BACKWARD COMPATIBILITY)
# theOldFunctionThatWasHere = newModule.theReplacementFunction
#printMsgToFile = writeTextToFile #old name for the same function

################################################################################