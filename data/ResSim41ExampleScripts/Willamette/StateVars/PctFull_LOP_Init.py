import sys

def initStateVariable(currentVariable, network):
    #Load up the external script file and make it accessible.
    #This allows the code to just live in one place and not be duplicated to every single state variable. 
    modulePath = network.makeAbsolutePathFromWatershed("scripts")
    if not modulePath in sys.path:
        sys.path.append(modulePath)
    import PctFull
    reload(PctFull)
    #Initialize the state variable
    returnVal = PctFull.initStateVariable(currentVariable, network)
    return returnVal