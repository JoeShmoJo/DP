'''
Simple state variable that duplicates the cumulative local flow.
Cumulative local is all inflow downstream of dams, routed to the point of interest.
This also includes the flow from Green Peter to Foster (Foster not counted as a "dam" since it is small)

This state variable is referenced by pseudo-downstream control rules at upstream reservoirs.
Ideally, the cumloc would have just been selectable as a "Model Variable",
but it is not available as a Model Variable in ResSim 3.3 or 3.5
'''

from hec.script import Constants
from hec.hecmath import TimeSeriesMath
from hec.model import RunTimeStep

lagHoursFromFoster = 12. #From Willamette SOP stick routing diagram, rounded to nearest 3-hour

def initStateVariable(currentVariable, network):
	thisRun=network.getRssRun()
	runTimeWindow = thisRun.getRunTimeWindow()
	currentRuntimestep = RunTimeStep(runTimeWindow) # dummy runtimestep object
	totalNumSteps = runTimeWindow.getNumSteps()
	cumLocTSInst = thisRun.getTSRecordByPathParts("Santiam_at Jefferson","FLOW-CUMLOC") 
	cumlocFlowTS = TimeSeriesMath.createInstance(cumLocTSInst.getTimeSeriesContainer())
	#Add in locals from Green Peter to Foster
	cumLocTSInstFOS = thisRun.getTSRecordByPathParts("Foster_IN","FLOW-CUMLOC") 
	cumlocFlowTSFOS = TimeSeriesMath.createInstance(cumLocTSInstFOS.getTimeSeriesContainer())
	#Apply routing (no attenuation assumed for simplicity)
	#The shift has to be a multiple of the simulation timestep
	timeStepMinutes = cumLocTSInst.getTimeStepMinutes()
	shiftMinutes = int(timeStepMinutes*round((60*lagHoursFromFoster)/timeStepMinutes, 0))
	cumlocFlowTSFOS = cumlocFlowTSFOS.shiftInTime(shiftMinutes) #takes shift in minutes
	cumlocFlowTS = cumlocFlowTS.add(cumlocFlowTSFOS)
	cumlocFlowLocalTS = currentVariable.localTimeSeriesNew("cumlocFlowTS", cumlocFlowTS.getData())
	variableTS = currentVariable.getTimeSeries()
	for i in range(totalNumSteps+1):
		currentRuntimestep.setStep(i)
		variableTS.setCurrentValue(currentRuntimestep, cumlocFlowLocalTS.getCurrentValue(currentRuntimestep))
	return Constants.TRUE