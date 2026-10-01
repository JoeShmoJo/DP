'''

These set of functions assist in loading or reloading modules
  into the current environment so that WAT/ResSim/CWMS program doesn't
  need to be closed and re-opened with each change.

Using the 'loadWatershedModules' function, pass the network object
  and directories within the watershed's 'scripts' directory
  to load
  
e.g.,
    from NWDJyLib import cLoadModules
    cLoadModules.loadWatershedModules(loadModules=["utils"])
  
'''

import os
import fnmatch
import glob
import imp
import org.python.core.PyTuple as PyTuple




def getAllFilesInDir(moduleDir, fileFilters= ["*.py","[!__init__.py]*"]):
    matches = []
    for root, dirnames, filenames in os.walk(moduleDir):
        # Avoid recursion by skipping 'cLoadModules'; ignore archived files
        if "cLoadModules" in root or "archive" in root:
            continue
        # Applying file filters
        for fileFilter in fileFilters:
            filenames = fnmatch.filter(filenames, fileFilter)
        
        for filename in filenames:
            matches.append(os.path.join(root, filename))
    return matches
    
def findModuleDirs(baseDir):
    '''
    Search recursively within all subdirectories for 
        module base directires (i.e. dirs with 
        __init__.py files)
    '''
    matches = []
    for root, dirnames, filenames in os.walk(baseDir):
        # If no init files, or in the state variable scripts
        if "__init__.py" not in filenames or \
            "StateVars" in root:
            continue
        matches.append(root)
    matches = list(set(matches))
    return matches

def convertFilePathToModuleName(filePath, scriptsDir):
    '''
    Converts from directory path to 
    '''
    filePath=filePath.replace(scriptsDir+"\\","")
    filePath=filePath.replace("\\",".")
    filePath=filePath.replace(".py","")
    return filePath
    

def loadModule(moduleName, getAbsPath):
    '''
    (Re)loads a module given the relative path from
      the watershed.
    @param moduleName String, of module name
                      e.g., 'NWDJyLib.Utils.SimplePy'
    '''

    # Preparing arguments for 'load_module' function; 
    #   check existence of external script
    pathname = getAbsPath("scripts/"+\
        moduleName.replace(".","/")+".py")
    if not os.path.exists(pathname):
        return False
    fp = open(pathname,"r")
    description=PyTuple(imp.get_suffixes()[0])

    # Loading module (will also reload if already loaded)
    try:
        thisSVModule = imp.load_module(moduleName, fp, pathname, description)
    finally:
        # Since we may exit via an exception, close fp explicitly.
        if fp:
            fp.close()
    return True
    
def loadWatershedModules(network=None,currentAlt=None, modulesToLoad=["NWDJyLib"]):
    '''
    (Re)load all modules in the watershed directory(ies) specified in modulesToLoad
       argument
    '''
    if network: # State Variable Script or Scripted Rule
        p = network.printMessage
        getAbsPath = network.makeAbsolutePathFromWatershed
    elif currentAlt: # ScriptingPlugin Script
        p = currentAlt.addComputeMessage
        getAbsPath = currentAlt.getAbsolutePath
    p("cLoadModules:\tStart modules load")
    # Grab all module directories
    scriptsDir = getAbsPath("scripts")
    moduleDirs = []
    for mod in modulesToLoad:
        modulePath = os.path.join(scriptsDir,mod)
        p("cLoadModules:\t\tLooking in this dir:\t%s" % modulePath)
        moduleDirs = moduleDirs + findModuleDirs(modulePath)
    p("cLoadModules:\tFound %g modules to load" % len(moduleDirs))
    
    # Grab the .py files within each module directory
    scriptFiles = []
    for moduleDir in moduleDirs:
        moduleFiles = getAllFilesInDir(moduleDir)
        scriptFiles = scriptFiles + moduleFiles
    p("cLoadModules:\tFound %g scripts within modules:\n\t%s" % \
        (len(scriptFiles), "\n\t".join(scriptFiles)))
    
    # Convert the module file paths to "." convention for loading
    for filePath in scriptFiles:
        moduleName = convertFilePathToModuleName(filePath, scriptsDir)
        loadModule(moduleName, getAbsPath)
        #rjc 27-Aug-2025
        #Below code can just print a message and still run, which is not good.
        #In ResSim, you can run a simulation successfully, and then make a change to a script that had a syntax error,
        #And then ResSim would still run the simulation again because it wasn't forcing a reload (bad)
        #Force the reload instead by not nesting it in a try/except statement
        '''
        try:
            success = loadModule(moduleName, getAbsPath)
        except Exception, exception:
            p("cLoadModules:\tError loading %s:\t%s" % \
                (moduleName, exception.message))
        '''
    return True
    
    
def getNewExternalSVObj(network, svName, currentVariable):
    moduleName = "externalSVs.%s" % svName

    # Preparing arguments for 'load_module' function; 
    #   check existence of external script
    pathname = network.makeAbsolutePathFromWatershed("scripts/"+\
        moduleName.replace(".","/")+".py")
    if not os.path.exists(pathname):
        network.printErrorMessage("Could not find state variable's \
            external script.  Expected here:\n\t%s" % pathname)
        return False
    fp = open(pathname,"r")
    description=PyTuple(imp.get_suffixes()[0])

    # Loading module (will also reload if already loaded)
    try:
        thisSVModule = imp.load_module(moduleName, fp, pathname, description)
    finally:
        # Since we may exit via an exception, close fp explicitly.
        if fp:
            fp.close()
            
    # create new class object and calling __init__ function
    return getattr(thisSVModule,svName)(network, currentVariable)
    