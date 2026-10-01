"""
This module has code that deals with time. Examples include getting the current
time and determining water year. For details on 14-period time modeling, see the 
:any:`c14Period` module.
"""

from hec.heclib.util import HecTime
from hec.model import RunTimeStep
from hec.model import RunTimeWindow

from java.util import TimeZone
from java.util import GregorianCalendar

import datetime
import bisect

#Custom Imports--THIS MODULE SHOULD NEVER NEED ANY CUSTOM IMPORTS!

################################################################################
# STATIC INPUT
DAYS_IN_MONTH = [31, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31] #Feb will get changed as necessary
DATE_STR_14PER = ["31Jan","28Feb","31Mar","15Apr","30Apr","31May","30Jun","31Jul","15Aug","31Aug","30Sep","31Oct","30Nov","31Dec"]
DATE_3DIGIT_14PER = ["JAN", "FEB", "MAR", "AP1", "APR", "MAY", "JUN", "JUL", "AG1", "AUG", "SEP", "OCT", "NOV", "DEC"]
################################################################################
# CLASS DEFINITIONS
class DynamicTimeBank(object):
    """General class to store all manner of important times. Intended to be used
    as the master bank for time information so scripts don't have to keep reinventing
    the wheel.
    Typical Usage:
    Initialize it, then stuff it with data using :meth:`storeTimeStep` and 
    :meth:`storeTimeSpan`
    Then, as you increment time steps, call the :meth:`setCurrentTime` method, which
    will update all of the information in the bank to be modified if necessary.
    After you've done that, feel free to mine the time information at will using
    :meth:`getInfo`.
    """
    def __init__(self, name, RunTimeObject):
        """Initializes an empty bank with the name of whatever you so choose.
        Must give it a RunTimeStep or a RunTimeWindow to initialize. """
        self.currentTime = HecTime("01Jan1900 2400")
        self.timeStepDict = {} #TimeStep or DynamicTimeStep
        self.timeSpanDict = {} #TimeSpan or DynamicTimeSpan
        if isinstance(RunTimeObject, RunTimeWindow):
            self.rtw = RunTimeObject
        elif isinstance(RunTimeObject, RunTimeStep): 
            #must be a RunTimeStep
            self.rtw = RunTimeObject.getRunTimeWindow()
    def getCurrentTime(self):
        return self.currentTime
    def getCurrentRTS(self):
        """Returns the current time as a RunTimeStep"""
        rts = RunTimeStep(self.rtw)
        rts.setStep(0)
        step = self.rtw.getLookbackTime().computeNumberIntervals(self.currentTime, 1440)
        rts.setStep(step)
        return rts
    def setCurrentTime(self, currentTimeObj):
        """Populate all info in all underlying DynamicTimeSpans and DynamicTimeSteps
        when you advance to a new time. If currentTime is the same as before, no
        impact--it returns False. If it reset, it returns True.
        currentTimeObj is a HecTime or RunTimeStep"""
        if isinstance(currentTimeObj, HecTime): currentTime = currentTimeObj
        else: currentTime = getHecTimeFromRuntimestep(currentTimeObj)
        if currentTime.equalTo(self.currentTime):
            return False
        self.currentTime = currentTime.clone()
        for timeSpanObj in self.timeSpanDict.values():
            if isinstance(timeSpanObj, DynamicTimeSpan):
                timeSpanObj.setCurrentTime(currentTime)
        for timeStepObj in self.timeStepDict.values():
            if isinstance(timeStepObj, DynamicTimeStep):
                timeStepObj.setCurrentTime(currentTime)
        return True
    def storeNotableTime(self, name, hTime):
        """Adds an arbitrary notable time (e.g. ICF date) to the bank.
        name is a string identifier (e.g. "ICF"), and hTime is an HecTime. 
        This should be used for weird, irregular dates. For more regular dates (like June 30), 
        should use :meth:`storeDynamicTimeStep` instead"""
        self.timeStepDict[name] = TimeStep(name, self.rtw, hTime)
    def _storeDynamicTimeStep(self, timeStepObj):
        """Adds a fully defined DynamicTimeStep object to the bank
        Could be 30JUN, etc."""
        self.timeStepDict[timeStepObj.name] = timeStepObj
    def createDynamicTimeSpan(self, name, decideDays=None):
        """Creates a new DynamicTimeSpan and add it to the bank. """
        timeSpanObj = DynamicTimeSpan(name, self.rtw, decideDays)
        timeSpanObj.setCurrentTime(self.currentTime)
        self._storeDynamicTimeSpan(timeSpanObj)
    def _storeDynamicTimeSpan(self, timeSpanObj):
        """Adds a fully defined DynamicTimeSpan object to the bank"""
        self.timeSpanDict[timeSpanObj.name] = timeSpanObj
    def getTimeObject(self, name):
        """Returns either the TimeSpan or TimeStep object with a name that matches the input"""
        if name in self.timeStepDict:
            return self.timeStepDict[name]
        if name in self.timeSpanDict:
            return self.timeSpanDict[name]
        return None
    def getInfo(self, name, infoNeeded, spanBound=None):
        """
        General purpose function to get any type of information about the a TimeStep or TimeSpan in the bank.
        Different behavior if the item in the bank is a TimeSpan or a TimeStep, but works for both.
        typical usage::
        
            bank.getInfo("ICF", "RunTimeStep")
            bank.getInfo("14Per", "daysLeft")
            bank.getInfo("14Per", "HecTime", "end")
            
        :param string name: the name of the item in the bank to get info from (e.g. "ICF", "14Per")
        :param string infoNeeded: the information to retrieve.  
            If retrieving a TimeStep object, any method in HecTime or RunTimeStep can be passed in as a string.
            e.g. "day" will call HecTime.day() 
            Some custom calls are also supported, including: WY, stepNum, HecTime, RunTimeStep
            If retrieving a TimeSpan object, can use the commands used in .getInfo() for the TimeSpan class
            You can also retrieve info about the beginning or end time of the TimeSpan object
            if you use the spanBound argument
            spanBound="start", "beginning", or "end"
        :param string spanBound: (optional). If supplied, and the object specified
            by 'name' is a TimeSpan, this argument will allow you to get either the 
            beginning or end time of the TimeSpan. argument must be "start", "beginning", or "end".
            When this is the case, the 'infoNeeded' supplied should be appropriate for a TimeStep object. 
        """
        if name in self.timeStepDict:
            return self.timeStepDict[name].getInfo(infoNeeded)
        if name in self.timeSpanDict:
            timeSpan = self.timeSpanDict[name]
            #We have a timespan, the infoNeeded might be about the span itself,
            #or it might be about the beginning or end of the span
            #Assume if "DAYS" in the infoNeeded, it's about the span itself (e.g. daysPassed, daysLeft, totalDays)
            if "DAYS" in infoNeeded.upper():
                return timeSpan.getInfo(infoNeeded)
            if spanBound:
                # specified to use either the beginning or end of the time span
                if "BEGIN" in spanBound.upper() or "START" in spanBound.upper():
                    timeStepObj = timeSpan.startTimeStep
                elif "END" in spanBound.upper():
                    timeStepObj = timeSpan.endTimeStep
                else: #not a recognized spanBound string
                    return None
                return timeStepObj.getInfo(infoNeeded)
            return None #unrecognized infoNeeded/spanBound combo
        return None #no matching TimeSpan or TimeStep with the supplied name
    def printAll(self):
        m = ""
        m += self.printAllStoredTimeSteps()
        m += self.printAllStoredTimeSpans()
        return m
    def printAllStoredTimeSteps(self):
        m = "Stored TimeSteps:"
        for timeStepObj in self.timeStepDict.values():
            m = "%s\n  %s" %(m, timeStepObj.toString())
        print m
        return m
    def printAllStoredTimeSpans(self):
        m = "Stored TimeSpans:"
        for timeSpanObj in self.timeSpanDict.values():
            m = "%s\n  %s" %(m, timeSpanObj.toString())
        print m
        return m

class TimeSpan(object):
    """Represents a duration of time with a beginning and an end.
    Includes 14-period, decideDate, monthly, weekly, etc.
    The start and end times are a bit funky--assumes a daily timestep defined at 2400.
    For instance, if we were doing monthly, the startTime would be 01Mar1955 2400, 
    and the endTime would be 31Mar1955 2400."""
    
    def __init__(self, name, RunTimeObject):
        """Must give it a RunTimeStep or a RunTimeWindow to initialize"""
        self.name = name
        self.rtw = None #RunTimeWindow object
        if isinstance(RunTimeObject, RunTimeWindow):
            self.rtw = RunTimeObject
        elif isinstance(RunTimeObject, RunTimeStep): 
            self.rtw = RunTimeObject.getRunTimeWindow()
        self.startTimeStep = TimeStep(self.name+"-start", self.rtw) #blank date
        self.endTimeStep = TimeStep(self.name+"-end", self.rtw) #blank date
        self.curTimeStep = TimeStep(self.name+"-current", self.rtw) #blank date
    def __str__(self):
        return self.toString()
    def getTotalDays(self):
        """If the current date is March 31 and we're doing monthly, returns 31"""
        return self.endTimeStep.getInfo("step") - self.startTimeStep.getInfo("step") + 1
    def getDaysLeft(self):
        """If the current date is March 31 and we're doing monthly, returns 1"""
        return self.endTimeStep.getInfo("step") - self.curTimeStep.getInfo("step") + 1
    def getDaysPassed(self):
        """If the current date is March 31 and we're doing monthly, returns 30"""
        return self.curTimeStep.getInfo("step") - self.startTimeStep.getInfo("step")
    def getInfo(self, infoNeeded):
        """Get any type of information about the time span you want.
        Only custom calls are also supported: totalDays, daysLeft, daysPassed
        If the current date is March 31 and we're doing monthly, 
        daysLeft will be 1, daysPassed will be 30, and totalDays will be 31"""
        if "TOTALDAYS" in infoNeeded.upper():
            return self.getTotalDays()
        elif "LEFT" in infoNeeded.upper() or "REMAINING" in infoNeeded.upper():
            return self.getDaysLeft()
        elif "PASSED" in infoNeeded.upper():
            return self.getDaysPassed()
        return None
    def toString(self):
        return "%s: start-%s end-%s current-%s" %(self.name, 
            self.startTimeStep.hecTime.dateAndTime(4), 
            self.endTimeStep.hecTime.dateAndTime(4),
            self.curTimeStep.hecTime.dateAndTime(4))
        
class DynamicTimeSpan(TimeSpan):
    """Subclass of a :any:`TimeSpan` object that adjusts itself as the current date changes. 
    This is useful for things like 14-period, which doesn't change every day, but
    the start and ends of the current TimeSpan does shift if the day.
    Typical usage is to initialize this object, call :meth:`setCurrentTime`, and
    then use functionality from TimeSpan (e.g. getDaysLeft). Then you can keep incrementing
    by calling :meth:`setCurrentTime`
    """
    def __init__(self, name, RunTimeObject, decideDays=None):
        """name is a string, must be "14Period", "Monthly", anything if decideDays is provided, "Weekly" (weekly not implemented todo). 
        Must give it a RunTimeStep or a RunTimeWindow to initialize.
        If decideDays is provided, it should be a list of day numbers that defines the irregular time span.
        For instance: [1,8,16,23]. The first timespan would go from the 1st at 2400
        to the 7th at 2400. The last would go from 23rd at 2400 to the last day of the month
        at 2400"""
        TimeSpan.__init__(self, name, RunTimeObject)
        self.decideDays = decideDays 
    def setCurrentTime(self, currentTimeObj):
        """Resets the TimeSpan object to conform to the new currentTime provided (HecTime or RunTimeStep)
        All info gets updated when you advance to a new time"""
        if isinstance(currentTimeObj, HecTime): currentTime = currentTimeObj
        else: currentTime = getHecTimeFromRuntimestep(currentTimeObj)
        lastCurTime = self.curTimeStep.hecTime.clone()
        if currentTime.equalTo(lastCurTime):
            # The current time hasn't changed, no need to do anything
            return None
        self.curTimeStep.setTime(currentTime)
        #adjust the TimeSpan start and end dates if necessary
        lastStartTime = self.endTimeStep.hecTime.clone()
        lastEndTime = self.endTimeStep.hecTime.clone()
        startTime = currentTime.clone()
        endTime = currentTime.clone()
        if self.decideDays:
            if currentTime.day() in self.decideDays:
                startIdx = self.decideDays.index(currentTime.day())
            else:
                startIdx = bisect.bisect_left(self.decideDays, currentTime.day()) - 1
            startDay = self.decideDays[startIdx]
            startTime.setYearMonthDay(currentTime.year(), currentTime.month(), startDay, 1440)
            if startIdx == len(self.decideDays)-1:
                #We are in the last period, the end is the end of the month
                endTime.setYearMonthDay(currentTime.year(), currentTime.month() + 1, 1, 0)
            else:
                endDay = self.decideDays[startIdx+1] - 1
                endTime.setYearMonthDay(currentTime.year(), currentTime.month(), endDay, 1440)
        elif "14PER" in self.name.upper():
            endTime.addDays(getDaysLeftIn14Period(currentTime)-1)
            if endTime.equalTo(lastEndTime):
                #still in same period, no need to update anything
                return None
            startTime = endTime.clone()
            startTime.subtractDays(getDaysIn14Period(currentTime)-1)
        elif "MONTH" in self.name.upper():
            startTime.setYearMonthDay(currentTime.year(), currentTime.month(), 1, 1440)
            if startTime.equalTo(lastStartTime):
                #still in same month, no need to update anything
                return None
            endTime.setYearMonthDay(currentTime.year(), currentTime.month() + 1, 1, 0) #1st at 0000 hours is the end at 2400 hours
        self.startTimeStep.setTime(startTime)
        self.endTimeStep.setTime(endTime)
        
class TimeStep(object):
    """Represents a single timestep representing a given date. 
    Can return much valuable information about a time.
    Kind of like a combination of a RunTimeStep and an HecTime object."""
    def __init__(self, name, RunTimeObject, hTime=None):
        """Initialize the object with a given name (e.g. "ICF")
        Must give it a RunTimeStep or a RunTimeWindow to initialize.
        If a RunTimeStep is given, the object will be set to that time as well.
        If the optional hTime argument (HecTime) is supplied along with a RunTimeWindow, 
        the will be set to this time."""
        self.name = name
        self.hecTime = HecTime("01Jan1900 2400") #will be a HecTime
        self.rts = None #will be a RunTimeStep
        if isinstance(RunTimeObject, RunTimeWindow):
            self.rtw = RunTimeObject
            if hTime: self.setTime(hTime)
        elif isinstance(RunTimeObject, RunTimeStep): 
            #must be a RunTimeStep
            self.rtw = RunTimeObject.getRunTimeWindow()
            self.setTime(RunTimeObject)
        else:
            self.rtw = None
    def __str__(self):
        return self.toString()
    def setTime(self, timeObj):
        """Sets the time of the object. Must give it a RunTimeStep or a HecTime"""
        if isinstance(timeObj, HecTime):
            self.hecTime = timeObj
            self.rts = self.rtw.getRunTimeStepAtTime(self.hecTime) #this works
        else:
            self.rts = timeObj
            self.hecTime = getHecTimeFromRuntimestep(timeObj)
        return None
    def getHecTime(self):
        """Get the time as a HecTime object"""
        return self.hecTime
    def getRunTimeStep(self):
        """Get the time as a RunTimeStep object"""
        return self.rts
    def getInfo(self, infoNeeded):
        """Get any type of information about the time you want.
        Any method in HecTime or RunTimeStep can be passed in as a string.
        e.g. "day" will call HecTime.day() 
        Some custom calls are also supported, including: WY, stepNum, HecTime, RunTimeStep
        """
        #Try getting info out of the HecTime version
        method_to_call = getattr(self.hecTime, infoNeeded, None)
        if callable(method_to_call):
            return method_to_call() 
        #Try getting info out of the RunTimeStep version
        method_to_call = getattr(self.rts, infoNeeded, None)
        if callable(method_to_call):
            return method_to_call()
        #Not a built-in method to either class, must be custom
        if "WY" in infoNeeded.upper():
            return getWYear(self.hecTime)
        if "STEP" in infoNeeded.upper():
            return self.rts.getStep()
        if "HECTIME" in infoNeeded.upper():
            return self.hecTime
        if "RUNTIMESTEP" in infoNeeded.upper():
            return self.rts
        return None
    def toString(self):
        return "%s: %s" %(self.name, self.hecTime.dateAndTime(4))

class DynamicTimeStep(TimeStep):
    """Intended to be for dates, like "30Jun", that would get updated as the year changed
    todo not currently implemented
    #linkedToCurrent="sameWY", "EOP", "EOM", "BOP","BOM", "DECIDEDATE",etc
    #if linkedToCurrent, when Current time changes, this will change as well
    """
    def __init__(self, name, RunTimeObject):
        TimeStep.__init__(self, name, RunTimeObject)
        
# END OF CLASS DEFINITIONS
################################################################################
# MIGRATED FUNCTIONS (IF MOVED TO ANOTHER MODULE, FOR BACKWARD COMPATIBILITY)
# theOldFunctionThatWasHere = newModule.theReplacementFunction

################################################################################
# FUNCTION DEFINITIONS
def getCurDayAsHecTime():
    """Return an HecTime object corresponding to 0000 hours on the current date"""
    curTime = HecTime() 
    curDate = datetime.date.today()
    curTime.setYearMonthDay(curDate.year, curDate.month, curDate.day, 0000)
    return curTime
    
def getNowAsHecTime():
    """Return an HecTime object corresponding to the current time (with hour and minute)"""
    now = datetime.datetime.now()
    curTime = HecTime()
    curTime.set(now.strftime("%d%b%Y %H%M")) #e.g. 03Jan1980 0203
    return curTime
    
def getHecTimeFromRuntimestep(rtsObj):
    """
    Returns an HecTime object that reflects the true time of the step (2400 hours).
    When Running ResSim daily modeling, the .getHecTime() method does not work
    as it should--it returns an HecTime object with daily granularity, which isn't
    good when trying to retrieve data from other timeseries. This function returns
    the current day with a granularity of minutes.
    
    This function should be used exclusively in the place of .getHecTime()
    
    :param RunTimeStep rtsObj: 
    """
    currentDate = rtsObj.getHecTime().clone()
    # If the hecTime object returned is daily granularity, subtract a day due to midnight shift
    #if currentDate.getTimeGranularity() == HecTime.DAY_INCREMENT: # days
     #   currentDate.subtractDays(1) # Midnight shift
    currentMonth = currentDate.month()  
    currentDay = currentDate.day()
    currentYear = currentDate.year()
    # If the daily hecTime object does not have a granularity of minutes, 
    # Set the current date to a granularity of minutes (2400 hours at the end of the day)
    if currentDate.getTimeGranularity() == HecTime.DAY_INCREMENT: 
        currentDate.setTimeGranularity(HecTime.MINUTE_INCREMENT) #granularity of minutes
        currentDate.setYearMonthDay(currentYear, currentMonth, currentDay, 1440)
    return currentDate
    
    
def adjustTimeGranularity(hTime):
    """
    Returns an HecTime object that reflects the true time of the step (2400 hours).
    When Running ResSim daily modeling, the .getHecTime() method does not work
    as it should--it returns an HecTime object with daily granularity, which isn't
    good when trying to retrieve data from other timeseries. This function returns
    the current day with a granularity of minutes.
    
    This function should be used exclusively in the place of .getHecTime()
    
    :param hTime HecTime object
    """
    currentDate = hTime.clone()
    # If the hecTime object returned is daily granularity, subtract a day due to midnight shift
    #if currentDate.getTimeGranularity() == HecTime.DAY_INCREMENT: # days
    #    currentDate.subtractDays(1) # Midnight shift
    currentMonth = currentDate.month()  
    currentDay = currentDate.day()
    currentYear = currentDate.year()
    # If the daily hecTime object does not have a granularity of minutes, 
    # Set the current date to a granularity of minutes (2400 hours at the end of the day)
    if currentDate.getTimeGranularity() == HecTime.DAY_INCREMENT: 
        currentDate.setTimeGranularity(HecTime.MINUTE_INCREMENT) #granularity of minutes
        currentDate.setYearMonthDay(currentYear, currentMonth, currentDay, 1440)
    return currentDate
    
def getStandardTimeStr(myTime, endOfDay=False):
    """
    Many times, we need a string in the format "01Aug2005 2400".
    This is used when opening up DSS files, creating RunTimeWindows, etc.
    This method returns a time in this format. 
    If no time is provided with the HecTime input object, then it will be set
    at the beginning of the day or the end of the day based on "endOfDay".
    
    :param myTime: (HecTime or string) The time to convert
    :param boolean endOfDay: (optional) Default is False. 
        If the input HecTime already has a time defined, this variable does nothing.
        If false and time not specified, will be set to 0000.
        If true and time not specified, will be set to 2400.
    :return: string in the format "05Aug2005 2400"
    """
    hTime = HecTime(myTime)
    #We want to specify both date and time
    if hTime.time() == "": 
        #No time was specified
        if endOfDay:
            hTime.setTime("2400")
        else:
            hTime.setTime("0000")
    timeStr = "%s %s" %(hTime.date(4), hTime.getTime(False)) #e.g. "01Aug1996 2400"
    return timeStr
    
def getDaysInMonth(month, year):
    """
    Returns the proper number of days in a specified month/year (integers)
    You have to specify the year to get the proper February days for leap years
    """
    monthDate = HecTime()
    monthDate.setYearMonthDay(year, month, 1, 1440)         
    #    Get correct days in month depending on leap year or not.
    daysInMonth = DAYS_IN_MONTH[month]
    if monthDate.isLeap(year) and month == 2:
        daysInMonth = 29    
    return daysInMonth
    
def getDaysTo31Jul(hTime):
    """ return the number of days until 31 July for the specified hTime"""
    jul31Date = HecTime()
    jul31Date.setYearMonthDay(hTime.year(), 7, 31, 1440)
    daysTo31Jul = hTime.computeNumberIntervals(jul31Date, 1440)
    return daysTo31Jul
    
def getWYear(hTime):
    """Return the integer water year that hTime (HecTime object) is in"""
    wYear = hTime.year()
    if hTime.month() >= 10:
        wYear += 1
    return wYear
    
def getNextDate(cTime,m,d):
    '''
    Get the next instance of a date relative to the current time
    Don't use this function on Feb 29
    '''
    cY = cTime.year()
    cM = cTime.month()
    cD = cTime.day()
    oTime = HecTime()
    # If already past the month to set, will be next year
    if m < cM:
        yrToSet = cY+1
    elif m == cM:
        # Check against the day
        if d <= cD: # desired date is prior or equal to current, use next year
           yrToSet = cY+1 
        else: # desired date after current, use this year
            yrToSet = cY
    else:
        yrToSet = cY
    # Setting minutes to 24:00
    oTime.setYearMonthDay(yrToSet, m, d, 1440)
    return oTime
    
def getPrevDate(cTime,m,d):
    '''
    Get the previous instance of a date relative to the current time
    Don't use this function on Feb 29
    '''
    h = getNextDate(cTime,m,d)
    h.setYearMonthDay(h.year()-1,h.month(),h.day(),1440)
    return h
    
def getNumberDaysToNext(cTime,m,d):
    '''
    Returns the number of days until the next occurrence of the
      specified month ('m') and day ('d') relative to the
      current time ('cTime')
    '''
    nextDate = getNextDate(cTime,m,d)
    # Add 1 to include the current day as well
    return cTime.computeNumberIntervals(nextDate, 1440) + 1
    
def getPeriodsAsDates(periods, year, endOfDay=True):
    """
    Takes a list of period defined as ["31Jul", "15Aug", etc.] and converts them to HecTimes for a year.
    Flexible to handle other period definitions aside from 14-period if desired.
    """
    periodDates = []
    for period in periods:
        periodDate = HecTime()
        if endOfDay:
            periodDateString = period + str(year) + " 2400"
        else:
            periodDateString = period + str(year) + " 0000"
        periodDate.set(periodDateString)
        periodDates.append(periodDate)
    return periodDates
    
def _get14PeriodsIncludingLeap(year):
    """Returns 14-period dates (list of HecTimes) including leap year adjustment"""
    periods = list(DATE_STR_14PER)
    if HecTime.isLeap(year):
        periods[1] = "29Feb"
    else:
        periods[1] = "28Feb"
    periodDates = getPeriodsAsDates(periods, year)
    return periodDates
    
def get14PeriodDates(startTime, endTime, extendToEOP=False):
    """
    Returns a list of end of period dates (14-period), as HecTime
    that fall between startTime and endTime, inclusive
    startTime and endTime are HecTime
    e.g. if startTime = 14August 2024, and endTime=02Oct2024, would return:
        [15Aug2024, 31Aug2024, 30Sep2024]
        
    If extendToEOP is True, then the last time returned will be extended to the next end of period
    In the previous example, if extendToEOP=True, we would return:
        [15Aug2024, 31Aug2024, 31Oct2024]
    """
    perStr14 = list(DATE_STR_14PER)
    perTimes = []
    currentDate = startTime.clone()
    numSteps = startTime.computeNumberIntervals(endTime, 1440)+1
    for j in range(numSteps): #Cycle through each day
        if j > 0: currentDate.addDays(1)
        currentDateStr = currentDate.toString(4)[:5] # will return a format "03Jun"
        if currentDate.isLeap(currentDate.year()):
            perStr14[1] = "29Feb"
        else:
            perStr14[1] = "28Feb"
        if currentDateStr in perStr14:
            perTimes.append(currentDate.clone())
    if extendToEOP:
        #Check the last time, add another date if the endTime doesn't fall exactly on an EOP date
        if not currentDateStr in perStr14:
            currentDate.addDays(getDaysLeftIn14Period(currentDate)-1)
            perTimes.append(currentDate.clone())
    return perTimes
    
def getDaysIn14Period(hTime):
    """
    Function to return the number of days in a period that hTime is in (hTime).
    Assumes hTime is defined at the end of a period (e.g. 31March 2400 is "MAR").
    Looks backward from the hTime until the last encountered EOP date.
    """
    daysIn14PeriodDict = {"JAN":31, "FEB":28, "MAR":31, "AP1":15, "APR":15, "MAY":31,
        "JUN":30, "JUL":31, "AG1":15, "AUG":16, "SEP":30, "OCT":31, "NOV":30, "DEC":31}
    periodName = get3Digit14Period(hTime)
    daysIn14Period = daysIn14PeriodDict[periodName]
    if hTime.month()==2 and HecTime.isLeap(hTime.year()):
        daysIn14Period = 29
    return daysIn14Period
    
def getDaysLeftIn14Period(hTime):
    """
    Function to return the number of days left in the period that hTime is in, 
    including today.
    e.g. if hTime was 31March, it would return 1
    e.g. if hTime was 01March, it would return 31
    e.g. if hTime was 01April, it would return 15
    Assumes hTime is defined at the end of a period (e.g. 31March 2400 is "MAR").
    Looks backward from the hTime until the last encountered EOP date.
    """
    periodDates = _get14PeriodsIncludingLeap(hTime.year())
    daysLeftInPeriod = 0
    for periodDate in periodDates:
        if periodDate.greaterThanEqualTo(hTime):
            #Add 1 to include the current day as well
            daysLeftInPeriod = hTime.computeNumberIntervals(periodDate, 1440) + 1
            break
    return int(daysLeftInPeriod)

def get3Digit14Period(hTime):
    """
    Get 3 digit abbreviation for the 14-period of the current date (HecTime).
    Returns a string, e.g. "JUN", (April/Aug are split into "AP1" and "APR").
    """
    cm = hTime.month()
    cd = hTime.day()
    if cm == 4 and cd < 16 :
        period = "AP1"
    elif cm == 8 and cd < 16 :
        period = "AG1"
    else :
        period = hTime.toString(119)[0:3] #119 format is "JUN 85", want "JUN"
    return period
    
def get14PeriodIndex(hTime):
    """Get an index number for supplied time. 1=JAN, 14=DEC. 
    For instance, if 31Mar1930 2400 was supplied, this would return 3"""
    period3Digit = get3Digit14Period(hTime)
    idxNum = DATE_3DIGIT_14PER.index(period3Digit)
    return idxNum + 1
    
def isDaylightSaving(hTime):
    """Return True if the HecTime is in Daylight Savings, False if in Standard Time.
    Daylight saving time goes from the 2nd sunday in march to the 1st sunday in november.
    This is only true since 2007--it was different before, but this method works.
    """
    tz = TimeZone.getTimeZone("US/Pacific") #or PST or PDT or US/Mountain
    #tz.observesDaylightTime() #True for US/Pacific
    #Not sure why I have to subtract 1 from the month, but it works well that way
    cal = GregorianCalendar(hTime.year(), hTime.month()-1, hTime.day())
    jDate = cal.getTime()
    #jDate = hTime.getJavaDate(0) #Doesn't work right
    return tz.inDaylightTime(jDate)
    
def getHoursOffsetFromUTC(tzName):
    """
    Return the number of hours a timezone is offset from UTC.
    For instance, PST has an offset of -8 from UTC (subtract 8 hours from UTC to get PST).
    If a timezone name is given that has daylight savings embedded in it
    (e.g. US/Pacific), will return the offset to get to standard time.
    
    :param str tzName: The timezone of interest, e.g. "PDT", "PST", "US/Pacific"
    """
    tz = TimeZone.getTimeZone(tzName)
    offsetMilis = tz.getRawOffset()
    offsetHours = offsetMilis/60/60/1000
    '''
    Another possible way to do it using python rather than java, haven't actually tried it
    os.environ['TZ'] = 'US/Pacific'
    time.tzset()
    if time.localtime().tm_isdst == 1:
      tz_offset = time.altzone/3600 #Daylight Savings offset in hours
    else:
      tz_offset = time.timezone/3600 #Standard offset in hours
    '''
    return offsetHours
    
def convertHecTimeToExcelDate(hTime):
    """
    Converts an HecTime object to a date in Excel format
    HecTime stores times as the number of minutes past 01Jan1900 0000 (time zero)
    Excel stores times as the number of days past 31Dec1899 0000 (time zero)
    However, the default is for Excel to store day values at 0000, while we tend
    to think of HecTime daily objects being defined at 2400. Ignore the 1day shift.
    
    :param HecTime hTime: The HecTime to convert
    :return double: The excel date (number)
    """
    hTimeIdx = hTime.value()
    excelDateIdx = hTimeIdx/1440. #+ 1
    return excelDateIdx
    
def convertExcelDateToHecTime(excelDateVal):
    """Reverse of convertHecTimeToExcelDate"""
    hTime = HecTime()
    hTimeIdx = int(excelDateVal*1440)
    hTime.set(hTimeIdx)
    return hTime 
    
def getBeginningOfMonthDate(hTime):
    '''
    Converts a HecTime to the end-of-month date
    '''
    outTime = hTime.clone()
    outTime.setYearMonthDay(hTime.year(), hTime.month(), 1)
    return convertToHecTime(outTime)
    
def getEndOfMonthDate(hTime):
    '''
    Converts a HecTime to the end-of-month date
    '''
    outTime = hTime.clone()
    # Get next month's numeric value
    yr = hTime.year()
    m = hTime.month() + 1
    if m == 13:
        m = 1
        yr += 1
    outTime.setYearMonthDay(yr, m, 1)
    outTime.subtractDays(1)
    return outTime
    
def convertToHecTime(dtObj):
    '''
    Modified from 'getHecTimeFromRuntimestep' function NWDJyLib.cTimes module
    Converts date object to HecTime if not already and modifies the
      time granularity to be minutes for proper calls to <TimeSeriesContainer>.get
      function.
      
    rsw 2020-06-22
      
    @param dtObj       HecTime or RunTimeStep object to be converted 
                        to HecTime with minute granularity
    '''
    try:
        if isinstance(dtObj, HecTime):
            # Check time granularity and set to minutes for more robust 
            #   *.getValue(<HecTime>) calls to time series objects
            currentDate = dtObj.clone()
        elif isinstance(dtObj, RunTimeStep):
            currentDate = dtObj.getHecTime().clone()
        else:
            print("Need to pass either RunTimeStep or HecTime object to function 'convertToHecTime'")
            return None
            
            
        # If the hecTime object returned is daily granularity, subtract a day due to midnight shift
        #if currentDate.getTimeGranularity() == HecTime.DAY_INCREMENT: # days
        #    currentDate.subtractDays(1) # Midnight shift
        currentMonth = currentDate.month()  
        currentDay = currentDate.day()
        currentYear = currentDate.year()
        # If the daily hecTime object does not have a granularity of minutes, 
        # Set the current date to a granularity of minutes (2400 hours at the end of the day)
        #if currentDate.getTimeGranularity() == HecTime.DAY_INCREMENT: 
        # 2020-04-29, Ross W: Previously used to modify only if at day granularity,
        #   but this did not produce desired behavior. Always resetting time granularity.
        #   HecTime.MINUTE_INCREMENT is 1, and time granularity of HecTime object 
        #   initialized as, e.g.,  HecTime("01Jan1943") is also 1.
        currentDate.setTimeGranularity(HecTime.MINUTE_INCREMENT) #granularity of minutes
        currentDate.setYearMonthDay(currentYear, currentMonth, currentDay, 1440)

        return currentDate
            
    except Exception, exception:
        print(exception.message)
    
    
def extractTSMByTimeWindow(tsm, sTime, eTime, printErrorMessage=None):
    '''
    Reduces time window of the input TimeSeriesMath object
      to dates specified by start and end times
    '''
    # Pull TSC, develop index references to times inside of time window
    tsc = tsm.getData().clone()
    times = tsc.times
    values = tsc.values
    twIndex = [e for e in range(len(times)) if \
        times[e] >= sTime.value() and times[e] <= eTime.value()]        
    # Reassigning reduced time and value lists
    if len(twIndex) == 0: # no data
        if printErrorMessage:
            printErrorMessage("No data in TSC, returning None\t%s to %s\t%s"% \
                (str(sTime), str(eTime), tsc.fullName))
            oTime = HecTime()
            for i in range(len(times)):
                oTime.set(times[i])
                printErrorMessage("\t%s\t%s" % (str(oTime), str(values[i])))
        return None
    elif len(twIndex) == 1: # writing 14Per in Sep, one remaining value in wy
        tsc.times = [times[twIndex[0]]]
        tsc.values = [values[twIndex[0]]]
    else:
        tsc.times = times[twIndex[0]:twIndex[-1] + 1]
        tsc.values = values[twIndex[0]:twIndex[-1] + 1]
    tsc.numberValues = len(tsc.values)
    tsm.setData(tsc)
    return tsm
