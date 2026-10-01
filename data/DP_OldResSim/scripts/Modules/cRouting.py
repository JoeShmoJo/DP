'''
cRouting Module
Contains code to simulate routing reaches
All routing reaches have a method called "routeTSC" which will route a timeseries container
If you have an object of class "hec.rss.model.Routing", use the function called
"buildReach" to build the appropriate reach object
'''

from hec.script import Constants
from hec.model import PairedValuesExt
from hec.io import TimeSeriesContainer
from hec.rss.model import SsarrRouting, NullRouting 
from hec.rss.model import MuskingumRouting, PulsChannelRoutingWithLosses
import math, logging

class NullReach:
	''' 
	NullReach: simulate Null Routing
	'''
	def __init__(self):
		return None
	
	def routeTSC(self, tsc):
		return tsc
	
class ModPulsReach:
	''' 
	ModPulsReach : class to simulate a SSARR routing reach 
	Cannot handle reach losses--just does the routing
	Typically just init the reach, and then route a timeseries with "routeTSC"
	author: Ryan Cahill
	date modified: September 5, 2014
	'''
	def __init__(self, storFlowTbl, numSubreaches) :
		'''
		Initialization
		storFlowTbl: PairedValuesExt of storage-outflow table
		numSubreaches: the number of subreaches (must be 1 or greater)
		'''
		self.numSubreaches = numSubreaches
		self.storFlowTbl = storFlowTbl
		self.timeStepSeconds = 0 # compute interval in seconds (set depending on tsc)
		self.workingDischarge = [0 for i in range(numSubreaches)] # array to keep track of discharge for each subreach
		self.finalSubreachOutflow = [0 for i in range(numSubreaches)] # array to keep track of final outflow for each subreach
		self.storIndTbl = None # PairedValuesExt (x is flow, y is storage indication)
		self.storIndTblReverse = None # PairedValuesExt (x is storage indication, y is flow)
	
	def initStorIndicationTbl(self):
		''' 
		Initialize storage indication table
		Storage indication table converts the storage values to cfs, based
		on the time step so that the storage and flow data can be easily added
		timeStepSeconds and numSubreaches must already be defined    	
		Assumes the units of storage are ac-ft and outflow are cfs
		'''			
		if self.timeStepSeconds == 0: 
			logging.error("Need to set the timestep of the Modified Puls Routing")
			return False
		storages = self.storFlowTbl.getXArray()
		outflows = self.storFlowTbl.getYArray()
		# manipulate the storage indication values
		storIndications = []
		for i in range(len(storages)):
			storIndications.append(0.5*outflows[i] + storages[i]*43560./self.timeStepSeconds/self.numSubreaches)	 
		storIndTbl = PairedValuesExt() 		
		storIndTbl.setArrays(outflows,storIndications)
		self.storIndTbl = storIndTbl
		# generate the table in reverse as well
		storIndTblRev = PairedValuesExt()
		storIndTblRev.setArrays(storIndications, outflows)
		self.storIndTblReverse = storIndTblRev
	
	def routeTSC(self, tsc) :
		'''
		Method to route a whole TimeSeriesContainer using Modified Puls
		The TimeSeriesContainer must have the "interval" property defined (minutes in each timestep)
		'''
		tscRouted = tsc.clone() # tsc with routed flows
		# Define the storage indication table (if not already defined)
		if tsc.interval <= 0:
			logging.error("Need to feed in a TimeSeriesContainer with regular interval data defined")
			return None
		elif self.timeStepSeconds <> tsc.interval*60:
			# The input tsc has a different timestep than what has been used until now-refresh
			self.timeStepSeconds = tsc.interval*60
			self.initStorIndicationTbl()
		# set the initial flows
		qInit = tsc.values[0]
		self.finalSubreachOutflow = [qInit for i in range(self.numSubreaches)]
		self.workingDischarge = [qInit for i in range(self.numSubreaches)]
		
		for j in range(tsc.numberValues) :
			q1 = tsc.values[j]
			if j == 0 :
				# if the first timestep, just use first flow value
				q0 = tsc.values[j]  
			else :
				q0 = tsc.values[j-1]
			# Route the flows
			tscRouted.values[j] = self.routeOneStep(q0, q1)
		return tscRouted                                 
	    
	def routeOneStep (self, qin0, qin1) :
		'''
		# Route one timestep
		#		qin0, qin1  are reach inflow for previous, current step
		# The following variables must already be defined:
		#		workingDischarge
		#		finalSubreachOutflow
		#		storIndTbl (the time step is wrapped up in this table, don't need to know timestep)
		'''	
		# Loop through each subreach
		for i in range(self.numSubreaches):
			# average the beginning and end of period outflows
			qin_avg = .5 * (qin0 + qin1)
			# get beginning of period working discharge (outflow from the subreach from previous timestep)
			d0 = self.workingDischarge[i]
			# calculate storage indication
			storageIndication0 = self.storIndTbl.interpolate(d0)
			# compute storage for current step
			storageIndication1 = max(0, storageIndication0 - d0 + qin_avg)
			# Interpolate outflow (working discharge) from storage indication
			d1 = max(0, self.storIndTblReverse.interpolate(storageIndication1))
			# save current subreach values for next time step
			self.workingDischarge[i] = d1
			# transfer values to do next subreach
			qin0 = self.finalSubreachOutflow[i]
			qin1 = d1				
			self.finalSubreachOutflow[i] = d1
		return d1

class MuskingumReach:
	''' 
	MuskingumReach : class to simulate a Muskingum routing reach 
	Cannot handle reach losses--just does the routing
	Typically just init the reach, and then route a timeseries with "routeTSC"
	author: Ryan Cahill
	date modified: September 12, 2014
	'''
	def __init__(self, muskingumK, muskingumX, numSubreaches):
		'''
		Initialization
		muskingumK: Slope of the storage outflow relationship (hours)
		muskingumX: Weighting factor on inflow. If X=0, inflow doesn't affect storage and there is maximum attenuation. 
		numSubreaches: the number of subreaches (must be 1 or greater)
		'''
		assert 0 <= muskingumX <= 0.5 #x cannot be above 0.5
		self.numSubreaches = numSubreaches
		self.muskingumK = muskingumK
		self.muskingumX = muskingumX
		self.initialSubreachOutflow = [0 for i in range(numSubreaches)] # array to keep track of initial outflow for each subreach
		self.finalSubreachOutflow = [0 for i in range(numSubreaches)] # array to keep track of final outflow for each subreach
	
	def routeTSC(self, tsc):
		'''
		Method to route a whole TimeSeriesContainer
		The TimeSeriesContainer must have the "interval" property defined (minutes in each timestep)
		'''
		tscRouted = tsc.clone() # tsc with routed flows
		# Define the storage indication table (if not already defined)
		if tsc.interval <= 0:
			logging.error("Need to feed in a TimeSeriesContainer with regular interval data defined")
			return None
		dtHours = tsc.interval/60. #timestep in hours (routing equations work in hours)
		# set the initial flows
		qInit = tsc.values[0]
		self.finalSubreachOutflow = [qInit for i in range(self.numSubreaches)]
		self.initialSubreachOutflow = [qInit for i in range(self.numSubreaches)]
		
		for j in range(tsc.numberValues):
			q1 = tsc.values[j]
			if j == 0 :
				# if the first timestep, just use first flow value
				q0 = tsc.values[j]  
			else :
				q0 = tsc.values[j-1]
			# Route the flows
			tscRouted.values[j] = self.routeOneStep(dtHours, q0, q1)
		return tscRouted                                 
	    
	def routeOneStep (self, deltaT, q0, q1):
		'''
		# Route one timestep
		#		deltaT = timestep (hours)
		#		qin0, qin1  are reach inflow for previous, current step
		# The following variables must already be defined:
		#		initialSubreachOutflow
		#		finalSubreachOutflow
		'''	
		muskingumX = self.muskingumX
		muskingumK = self.muskingumK
		numberSubreaches = self.numSubreaches
		subK = muskingumK/float(numberSubreaches)
		# calculate muskingum coeffients
		c0 = (-subK*muskingumX + .5*deltaT)/(subK-subK*muskingumX + .5*deltaT)
		c1 = (+subK*muskingumX + .5*deltaT)/(subK-subK*muskingumX + .5*deltaT)
		c2 = (subK-subK*muskingumX - .5*deltaT)/(subK-subK*muskingumX + .5*deltaT)
		# define initial estimates
		qin0 = q0
		qin1 = q1
		# Loop through each subreach
		for i in range(numberSubreaches):
			qout0 = self.initialSubreachOutflow[i]
			qout1 = c0*qin1 + c1*qin0 + c2*qout0  #apply the Muskingum coefficients
			qin1 = qout1
			self.finalSubreachOutflow[i] = qout1
			# outflow0 is inflow0 for next subreach
			qin0 = qout0
		# save values for next time step
		for i in range(numberSubreaches):
			self.initialSubreachOutflow[i] = self.finalSubreachOutflow[i]
		# return reach outflow for this step
		return qout1

		
''' SsarrReach : class to simulate a SSARR routing reach (John McCoskery)'''
class SsarrReach:
    # constructor --------------------------------------
    def __init__ (self) :
        self.nps = 0                                    # number of routing phases
        self.ncoeff = 0                                 # SSARR n-coefficient
        self.kts = 0                                    # SSARR Time of Storage coefficient
        self.xhr = 24                                   # compute interval in hours
        self.qrts = None                                # flow-Ts table (PairedValuesExt)
        self._qrts = Constants.FALSE                    # flag if table is used or not
        self.qph = []                                   # array to keep track of phase flows
    
    # method to initialize w/ qr-ts table --------------
    def build1 (self, qts, nump) :
        self.qrts = qts                                 # set table
        self._qrts = Constants.TRUE                     # set flag
        self.nps = nump                                 # set number of phases
    
    # method initialize w/ kts method ------------------
    def build2 (self, nump, n, k) :
        self.nps = nump                                 # set number of phases
        self.ncoeff = n                                 # set SSARR n-coeff
        self.kts = k                                    # set SSARR kts value
    
    # initialize phases for first step -----------------
    def init_phases (self, qi) :
        self.qph = []                                   # set or clear qph as array
        x = 0
        while x < self.nps :                            # for each phase
            self.qph.append(qi)                         # set qph = qi
            x += 1
    
    # method to route flows for one step (sets qph)-----
    def nroute (self, q1, q2) :
        ph = self.qph                                   # set ph = object qph array
        phave = 0.; n = 1                               # average phase value
        
        x = 0
        while x < self.nps :                            # sum values in current qp array
            phave += ph[x]
            x += 1
        phave = phave / self.nps                        # average for phases
        
        if phave <= 0.001 : phave = 1.0                 # will for Ts = KTS or close to bottom of QR-Ts table 
                                                        # this is what ResSim does to get around (-) qph values
        # compute time of storage value, Ts
        if self._qrts == Constants.TRUE :
            ts = self.qrts.interpolate(phave)           # w/ qr-ts table
        else :
            ts = self.kts / math.pow(phave, self.ncoeff)# w/ kts method
        
        q_ph = []
        if ts < 0.05 :                                  # if ts is very small...
            x = 0
            while x < self.nps :                        # don't route, set phase flows = q2
                q_ph.append(q2)
                x += 1
        else :                                          # ts is big enough to route
            x = 0
            while x < self.nps :                        # copy qph array to q_ph
                q_ph.append(ph[x])
                x += 1
            if ts < self.xhr / 2 :                      # if ts is smaller than xhr/2 compute sub-interval
                n = int(self.xhr / 2 / ts) + 1
                xh2r = self.xhr / 2. / n                # NOTE: the '2.' makes xhr2 a float, w/out it n forces it to an int
            else :
                n = 1
                xh2r = self.xhr / 2.
            
            tsr = xh2r / (ts + xh2r)                    # compute tsr
            xint = (q2 - q1) / n                        # compute average flow over sub-interval
            pqi = q1 - xint / 2                         # compute average qin to reach
            
            j = 0
            while j < n :                               # compute phase flows for each substep
                pqi = pqi + xint
                qi = pqi                                # initialze inflow for first sub-reach
                x = 0
                while x < self.nps :                    # loop through each sub-reach
                    dq = qi - q_ph[x]                   # compute difference between current qi and previous qi for sub-reach
                    dq = dq * tsr                       # multiply by ts for sub interval
                    qi = q_ph[x] + dq                   # adjust initial qi to sub-reach
                    q_ph[x] = qi + dq                   # compute final flow for sub-reach
                    x += 1
                j += 1
        
        self.qph = q_ph                                 # set object.qph to q_ph
        return q_ph[-1]                                 # return the reach outflow (from the last subreach)
    
    # method to route a timeseries wholly --------------
    def routeTSC (self, ts) :
        num = ts.numberValues                               # set number of values from input tsc
        self.xhr = ts.interval/60.                          # convert to hours
        qrr = []                                            # routed flow array
        
        for x in range(0, num) :
            if x == 0 :
                self.init_phases (ts.values[x])             # if x == 0 then initialize qph array
            else :
                self.nroute(ts.values[x-1], ts.values[x])   # otherwise route flows
            qrr.append(self.qph[-1])                        # store final phase flow to qrr array
        
        tsc = ts.clone()                                    # build return tsc
        #tsc.numberValues = num                              # set number of values
        tsc.times = ts.times                                # use input times
        tsc.values = qrr                                    # set values
        return tsc                                          # return tsc
        
def buildReach(routingObj):
	'''
	Function to create a custom routing reach class (defined in this module)
	from the input routingObj. This allows you to run the "routeTSC" method on the
	return object. Can only handle SSARR, Null, ModPuls, and Muskingum
	@param	Routing				routingObj	The input routing object (typ. from ResSim)
																		ReachElement.getFunction()
	@return	custom class	reachObj		A resulting reach of any type
																		Returns None if not a supported routing type
	'''
	if isinstance(routingObj, SsarrRouting):				
		# Check to see if its defined as a table or not
		subreaches = routingObj.getNumberReaches()
		if routingObj.getKTS():
			kts = routingObj.getKTS()
			n = routingObj.getNCoefficient() 
			reachObj = SsarrReach()
			reachObj.build2(subreaches, n, kts)
			#txtArea.append("\n\tSSARR Coefficients: KTS=%.1f n=%.1f subreaches=%.0f" %(kts, n, subreaches))
		else:
			# Defined as an interpolation table
			table = routingObj.getOutflowTimeOfStorageTable()
			reachObj = SsarrReach()
			reachObj.build1(table, subreaches)			
			#txtArea.append("\n\tSSARR Table routing: subreaches=%.0f" %subreaches)	
		return reachObj
	elif isinstance(routingObj, PulsChannelRoutingWithLosses):
		subreaches = routingObj.getnumberReaches()
		stors = []
		flows = []
		for pulsRecord in routingObj.getPulsVector():
			stors.append(pulsRecord.stor)
			flows.append(pulsRecord.outflow)	
		storFlowTbl = PairedValuesExt()
		storFlowTbl.setArrays(stors, flows)
		reachObj = ModPulsReach(storFlowTbl, subreaches)
		return reachObj
	elif isinstance(routingObj, MuskingumRouting):
		subreaches = routingObj.getnumberReaches()
		muskK = routingObj.getmuskingumK()[0]
		muskX = routingObj.getmuskingumX()[0]
		reachObj = MuskingumReach(muskK, muskX, subreaches)
		return reachObj
	elif isinstance(routingObj, NullRouting):
		return NullReach()
	else:
		return None
		