'''
Simple state variable that duplicates the cumulative local flow.
Cumulative local is all inflow downstream of dams, routed to the point of interest.

This state variable is referenced by pseudo-downstream control rules at upstream reservoirs.
Ideally, the cumloc would have just been selectable as a "Model Variable",
but it is not available as a Model Variable in ResSim 3.3 or 3.5
'''

from hec.script import Constants
from hec.hecmath import TimeSeriesMath
from hec.model import RunTimeStep

def initStateVariable(currentVariable, network):
	thisRun=network.getRssRun()
	runTimeWindow = thisRun.getRunTimeWindow()
	currentRuntimestep = RunTimeStep(runTimeWindow) # dummy runtimestep object
	totalNumSteps = runTimeWindow.getNumSteps()
	cumLocTSInst = thisRun.getTSRecordByPathParts("Willamette_at Harrisburg","FLOW-CUMLOC") 
	cumlocFlowTS = TimeSeriesMath.createInstance(cumLocTSInst.getTimeSeriesContainer())
	cumlocFlowLocalTS = currentVariable.localTimeSeriesNew("cumlocFlowTS", cumlocFlowTS.getData())
	variableTS = currentVariable.getTimeSeries()
	for i in range(totalNumSteps+1):
		currentRuntimestep.setStep(i)
		variableTS.setCurrentValue(currentRuntimestep, cumlocFlowLocalTS.getCurrentValue(currentRuntimestep))
	return Constants.TRUE