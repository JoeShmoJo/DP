"""
This code contains rudimentary functions that use basic python classes.
Examples include string manipulation, and messing with lists/dictionaries.
This code is usually not necessary, since it can be replaced largely by 1-line
python statements, but the CRT ResSim model uses some of it. 
For details on manipulating files/folders, see the :any:`cFile` module.
Details on manipulating dates and times can be found in :any:`cTimes` module.
Details on logging can be found in :any:`cLogging` module.
"""

import logging
import datetime
import os
from bisect import bisect_left

#This module should never need to import any java classes or NWDJyLib classes!

################################################################################
# STATIC INPUT

################################################################################
# CLASS DEFINITIONS
class Interpolate(object):
    """ 
    Piecewise Linear Interpolation
    Assumes x values in continuous ascending order, will not extrapolate
    Typical usage:
    obj = Interpolate([5,6,7],[8,9,10])
    y = obj.interp(5.5)
    """
    def __init__(self, x_list, y_list):
        if any(y - x <= 0 for x, y in zip(x_list, x_list[1:])):
            raise ValueError("x_list must be in strictly ascending order!")
        x_list = self.x_list = [float(x) for x in x_list]
        y_list = self.y_list = [float(y) for y in y_list]
        intervals = zip(x_list, x_list[1:], y_list, y_list[1:])
        self.slopes = [(y2 - y1)/(x2 - x1) for x1, x2, y1, y2 in intervals]

    def __getitem__(self, x):
        i = bisect_left(self.x_list, x) - 1
        if x <=self.x_list[0]:
            y = self.y_list[0]
        elif x >=self.x_list[-1]:
            y = self.y_list[-1]
        else:
            y = self.y_list[i] + self.slopes[i] * (x - self.x_list[i])
        return y
    def __call__(self, x):
        return self.__getitem__(x)
    def interp(self, x):
        return self.__getitem__(x)
# END OF CLASS DEFINITIONS
################################################################################
# MIGRATED FUNCTIONS (IF MOVED TO ANOTHER MODULE, FOR BACKWARD COMPATIBILITY)
# theOldFunctionThatWasHere = newModule.theReplacementFunction
################################################################################
# FUNCTION DEFINITIONS

def upperList(L): 
    """Upcases a list of strings"""
    return [i.upper() for i in L]

def combine2Lists(list1, list2):
    """Appends the items of list2 onto list1"""
    return list1 + list2

def createDictionaryFrom2Lists(list1, list2):
    """
    Returns a dictionary object that has list1 as the keys, and list2 as the values.
    list1, list2 = lists of the same length
    """
    dictObj = {}
    for key, value in zip(list1, list2):
        dictObj[key] = value
    return dictObj
        
def createDictFrom2Dicts(dict1, dict2):
    """
    Returns a dictionary object that has all of the items in dict1 and dict2.
    dict1, dict2 = dictionaries with non-identical keys
    """
    dict1.update(dict2)
    return dict1

def createDictFrom4Lists(keys1, list1, keys2, list2):
    """
    Returns a dictionary with the keys1 corresponding to list1
    and keys2 corresponding to list2.
    all variables = lists
    """
    dictObj = {}
    for key, value in zip(keys1+keys2, list1+list2):
        dictObj[key] = value
    return dictObj
    
def rndStrLen(value,fldLen,rnd) :
    """
    Rounds a number to a number of digits, making sure there are
    fldLen number of characters, and converts to string
    """
    return strLen(rndStr(value, rnd), fldLen)
    # old code # EAH
    #str = String(String().valueOf(round(value,rnd)))
    #if rnd > 0 :
    #       numOfTrailingZeros = rnd-str.length()+str.indexOf(".")+1
    #       for i in range(numOfTrailingZeros) :
    #               str = String(str.concat("0"))
    #elif rnd == 0 :
    #       str = String(str.substring(0,str.indexOf(".")))
    #extraZero = str.length()-str.indexOf(".") - 1 - rnd
    #if extraZero > 0 and rnd > 0 :
    #       str = String(str.substring(0,str.length()-extraZero))
    #numOfLeadingSpaces = fldLen-rnd-2-str.indexOf(".")
    #for i in range(numOfLeadingSpaces) :
    #       str = String(String(" ").concat(str))
    #return str.toString()
    
def rndStr(value,rnd) :
    """Rounds a number to a number of digits and converts to string"""
    return str(round(value, rnd))
    # old code #EAH
    # valueRounded = round(value,rnd)
    # if rnd > 0 or abs(valueRounded) > 2147483647. :
    #       str = String(String().valueOf(valueRounded))
    # else :
    #       str = String(String().valueOf(int(valueRounded)))
    # return str.toString()

def strLen(value,fldLen) :
    """
    Returns a string of text with trailing spaces so that the total number 
    of characters = fldLen.
    value = string or anything that can be converted to a string
    """
    # uses python native method #EAH
    return str(value).ljust(fldLen)
    # old code starts here #EAH
    # strObj = str(value)
    # numOfExtraSpaces = fldLen-len(strObj)
    # for i in range(numOfExtraSpaces) :
    #       strObj += " "
    # return strObj
        
def drange(limit1, limit2 = None, increment = 1.):
    """
    Range function that accepts floats (and integers).
    
    Usage:
    drange(-2, 2, 0.1)
    drange(10)
    drange(10, increment = 0.5)
    
    The returned value is an iterator.  Use list(drange) for a list.
    """
    
    if limit2 is None:
        limit2, limit1 = limit1, 0.
    else:
        limit1 = float(limit1)
    
    count = int(round((limit2 - limit1)/increment,0))
    return (limit1 + n*increment for n in range(count))
    
def expandGrid(asTuple=True, **kwargs):
    '''
    Input is a series of lists as named arguments
    Output is a dictionary preserving names that defines each combination, 
      or a tuple of each pairing if asTuple=True
    '''
    # lengths of each input list
    listLens = [len(e) for e in kwargs.itervalues()] 
    # multiply all list lengths together to get total number of combinations
    nCombos = reduce((lambda x, y: x * y), listLens) 
    outDict = {}
    nTimesRepEachValue=1 #initialize as repeating only once
    for key in kwargs.keys():
        nTimesRepList=nCombos/(len(kwargs[key])*nTimesRepEachValue)
        tempVals=[] #temporary list to store repeated values
        for v in range(nTimesRepList):
            valsToAppend =[item for item in kwargs[key] for i in range(nTimesRepEachValue)]
            tempVals=tempVals+valsToAppend
        outDict[key] = tempVals
        # Accumulating the number of times needed to repeat each value
        nTimesRepEachValue=len(kwargs[key])*nTimesRepEachValue
    if asTuple: 
        return reduce(zip, outDict.itervalues())
    return outDict
