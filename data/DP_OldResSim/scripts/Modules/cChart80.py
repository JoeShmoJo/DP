naturalLakes = 0
arrowName = 0
naturalOutletName = 0

def runChart80Simulation(rssRunObs, rssRunUnreg, simDss, outDss, resvList, diversionList, outputJuncs, fPartOut, bar, txtArea):
	'''
	This function is quite similar to the "runResvSimulations"
	If I had time, I would have made one function that would do both--rjc, Oct 2015
	Chart 80 is produced by NWD, and shows the flow reduction at TDA as a time series from separate groups of projects
	The approach to generate Chart 80 is to incrementally add in projects to the unregulated run
	This is very similar to the "isWith=True" simulations of the "runResvSimulations", except there is more than one project at a time
	Natural lake operations will be modeled if the project isn't in the selected list

	rssRunObs and rssRunUnreg must be based off the same network for this to work!
	@rssRunObs		rssRun   the modeled Observed RssRun (with observed data defined)
	@rssRunUnreg  rssRun   the modeled Unregulated Rssrun (with natural lake effects)
	@simDss 			DssFile  already opened simulation.dss file
	@outDss 			DssFile  already opened output dss file
	@resvList	list     list of strings of the projects (reservoirs or diversions) to include in the simulation
	@outputJuncs	list     list of JunctionElements where to save detailed output
	return todo
	'''

	confJuncs = cResSim.getConfluenceJunctions(network)
	confResvDict = cResSim.getConfluenceResvPoolDict(network)
	confResvs = confResvDict.keys() #pool Element, not ReservoirElement
	hwJuncs = cResSim.getRealHeadwaterJunctions(network)
	orderedElements = cResSim.orderElementsFromUpstream(network)
	
	
	
	
	simDssFile = simDss.getFilename()
	rssRunObj = rssRunUnreg # base rssRun can be the unregulated run (doesn't really matter)
	rssAltUnreg = rssRunUnreg.getAlternative() #need this for lookback natural lake elevs
	numLookbackSteps = rssRunObj.getRunTimeWindow().getNumLookbackSteps()
	network = rssRunObj.getNetwork()
	# Get reservoirs with more than one inflow
	# Need to get the elements in the same network as the "resvsToRun" for identity testing
	confResvDict = cResSim.getConfluenceResvPoolDict(resvsToRun[0].getSystem())
	confResvs = confResvDict.keys() #pool Element, not ReservoirElement
	#Need to deal with junction names as strings, since "network" may be different
	#  than the network that "resvsToRun" were based off of
	confJuncNames = [j.toString() for j in cResSim.getConfluenceJunctions(network)]
	#Set up the time series bank that will hold read time series so we don't have to read/write continually
	tsBank = cResSim.tsmBank()
	initialBar = bar.getValue()
	
	
	
	
	
	
	
	
	
	# dictionary of timeseries containers for tributary regulated flows
	tribFlows = {} #keys are Elements of some sort (e.g. Reach), values are TSCs 
	
	#Proceed through all elements, saving "flowTSM" as the current state of the routed flow
	for i in range(len(orderedElements)):
		bar.setValue(int(float(i)/len(orderedElements)*100))
		elem = orderedElements[i]
		if elem == None: continue
		elemName = elem.toString()
		if isinstance(elem, JunctionElement):
			# If the junction is a confluence junction, add in the flow from upstrm reaches
			logging.debug("  Junction: %s" %elemName)
			if elemName in confJuncNames:
				logging.debug("    Confluence Junction!")
				upstreamReaches = cResSim.getConnectedReaches(elem)
				for rch in upstreamReaches:
					if tribFlows.has_key(rch):
						flowTSM = flowTSM.add(tribFlows[rch])  #timewindow previously checked
						logging.debug("added %s" %rch)
					else:
						# probably the downstream reach, skip it
						logging.debug("%s: Downstream reach" %rch)
						continue
			# Add in any local flows
			nodes = elem.getNodeVector()
			for node in nodes: #One local flow per node in ResSim
				#Local flow nodes have no upstream element
				if node.getUpstreamElement(): continue #must be a connected element, skip it
				logging.debug("    Local Flow Node: %s" %node)
				tsName = "%s Local Flow" %node.toString()
				locFlowTSM = tsBank.withdrawTS(simDssFile, tsName) #will return None if doesn't exist yet
				if not locFlowTSM: #need to read it for the first time
					rssConstant = RssModelVariableConstants.VID_NODE_FLOW
					#Output local flows are stored to the node as FLOW, not KNOWNFLOW
					#Any inflow multipliers are already accounted for
					locFlowTSM = cResSim.getTSMFromSimulationDSS(simDss, node, rssRunObj, rssConstant, txtArea, 
					 useObsData = False, isStrict = True, displayMessages = True)
					tsBank.depositTS(simDssFile, tsName, locFlowTSM)
				locFlowTSC = locFlowTSM.getData()
				if elem in hwJuncs: #use the data directly
					logging.info("\t\tUsing input local flow: %s" %locFlowTSM.getPath())
					flowTSM = locFlowTSM.copy()
				else: #add to the existing flows
					logging.info("\t\tAdding input local flow to the total flow: %s" %locFlowTSM.getPath())
					flowTSM = flowTSM.add(locFlowTSM) #timewindow previously checked
			# Account for diversions
			divElems = cResSim.getConnectedDiversions(elem)
			if divElems:
				for divElem in divElems:
					#There is a diversion--take it out if it is identified as a diversion to include (should be set to 0 in unreg model)
					logging.debug("    Diversion found: %s" %divElem)
					if divElem in diversionList:
						#The diversion should be included--deduct it from the flow
						divNode = divElem.getUpstreamNode() #flow being taken out to a diversion is in upstream node
						tsName = "%s Diversion Flow" %divNode.toString()
						divTSM = tsBank.withdrawTS(simDssFile, tsName) #will return None if doesn't exist yet
						if not divTSM: #need to read it for the first time
							#read the diversion from the observed run
							rssConstant = RssModelVariableConstants.VID_NODE_FLOW
							divTSM = cResSim.getTSMFromSimulationDSS(simDss, divNode, rssRunObs, rssConstant, txtArea, 
								useObsData=False, isStrict = True, displayMessages = True)
							tsBank.depositTS(simDssFile, tsName, divTSM)
						flowTSM = flowTSM.subtract(divTSM) #divTSM are positive numbers
		elif isinstance(elem, ReachElement):
			# If the element is a reach, route the flow to the next junction
			routingObj = elem.getFunction()
			logging.info("Reach : %s" %elemName)
			routeReach = cRouting.buildReach(routingObj)
			if routeReach is None:
				errMsg = "The Script cannot handle any routing methods besides SSARR, Muskingum, ModPuls, or Null:"
				errMsg += "\n%s has routing of: %s" %(elemName, routingObj.__class__)
				logging.error(errMsg)
				txtArea.printToGUI(errMsg)
				return None
			logging.debug("\tRouting Type: %s" %routingObj.__class__)
			flowTSC = routeReach.routeTSC(flowTSM.getData())
			flowTSM = TimeSeriesMath(flowTSC)
		elif isinstance(elem, ReservoirElement):
			pass #a ReservoirElement will never be hit--they are stored as "Pool" Elements in orderedElements
		elif elemName == "Pool": #reservoir pool element
			resvElem = elem.getParent() #To get the ReservoirElement, need to do a .getParent() call
			resvName = resvElem.toString()
			if elem in confResvs:
				# If the junction is a confluence reservoir, add in the flow from upstrm junctions
				logging.debug("\tIt's a confluence reservoir")
				upstreamJunctions = confResvDict[elem]
				for juncElem in upstreamJunctions:
					if tribFlows.has_key(juncElem):
						flowTSM = flowTSM.add(tribFlows[juncElem])  #timewindow previously checked
						logging.debug("added %s" %juncElem)
					else:
						# The upstream junction flow should already exist
						errMsg = "ERROR: At confluence reservoir: %s" %resvName
						errMsg +="\nCouldn't locate input flow time series for Junction: %s" %juncElem
						logging.error(errMsg)
						txtArea.printToGUI(errMsg)
						return None
			# If the element is a reservoir, account for any storage or draft this time step if selected
			# Otherwise, pass inflow or do natural lake operation
			logging.debug("  Reservoir: %s" %resvName)
			# Now, deal with the reservoir itself
			if resvName in naturalLakes and (not resvName in resvList):
				#Account for the attenuation effects here
				logging.debug(" Natural Lake modeled at: %s" %resvName)
				if resvName == arrowName:
					#Arrow Lake natural lake operations need to be done specially
					logging.debug("Arrow Lakes logic is computing")
					flowTSM = computeArrowLakeOps(rssRunObj, simDss, outDss, flowTSM, fPartOut, txtArea)
				else: #not Arrow
					elevStorTbl = cResSim.getElevationStorageTable(resvName, network)
					elevRelTbl = cResSim.getElevationReleaseTable(resvName, naturalOutletName, network)
					startElev = cResSim.getLookback(resvName, rssAltUnreg, "ELEV") #unreg alt has lookback info
					if not elevRelTbl:
						errMsg = "Failed to find an outlet at: %s  named: %s" %(resvName, naturalOutletName)
						logging.error(errMsg)
						txtArea.printToGUI(errMsg)
						return None
					if not startElev:
						errMsg = "Failed to retrieve lookback elevation at: %s for alternative: %s" %(resvName, rssAltUnreg)
						errMsg += "\nIt must be specified as a constant"
						logging.error(errMsg)
						txtArea.printToGUI(errMsg)
						return None
					flowTSM, elevTSM = computeNatLakeOps(startElev, numLookbackSteps, elevStorTbl, elevRelTbl, flowTSM)
			elif not resvName in resvList: 
				logging.debug("  Assume passes inflow: %s" %resvName)
				#not the resv or its rereg--just assume it passes inflow
			else:
				# get outflow minus inflow from observed run and add it to the incoming flow
				logging.debug("  Accounting for change in storage at: %s" %resvName)
				# Note: I originally used the pool storage difference, but this does not work
				# for the lookback, when ResSim violates conservation of mass. 
				# Use inflow minus outflow instead
				tsName = "%s Inflow" %resvName
				inflowTSM = tsBank.withdrawTS(simDssFile, tsName) #will return None if doesn't exist yet
				if not inflowTSM: #need to read it for the first time
					rssConstant = RssModelVariableConstants.VID_POOL_INFLOW
					inflowTSM = cResSim.getTSMFromSimulationDSS(simDss, resvElem, rssRunObs, rssConstant, txtArea, 
						useObsData=False, isStrict = True, displayMessages = True)
					tsBank.depositTS(simDssFile, tsName, inflowTSM)
				tsName = "%s Outflow" %resvName
				outflowTSM = tsBank.withdrawTS(simDssFile, tsName) #will return None if doesn't exist yet
				if not outflowTSM: #need to read it for the first time
					rssConstant = RssModelVariableConstants.VID_POOL_OUTFLOW
					outflowTSM = cResSim.getTSMFromSimulationDSS(simDss, resvElem, rssRunObs, rssConstant, txtArea, 
						useObsData=False, isStrict = True, displayMessages = True)
					tsBank.depositTS(simDssFile, tsName, outflowTSM)
				flowTSM = flowTSM.add(outflowTSM)
				flowTSM = flowTSM.subtract(inflowTSM)
				#Sometimes the storage difference approach will cause the reservoir to release less than 0
				#Correct for any negative outflows
				flowTSM = forceMinRelease(flowTSM, 0)
		if elem in outputJuncs:
			#We are at a detailed output location--write out to DSS
			#Tell whether hourly or daily
			flowPath = DSSPathString(flowTSM.getPath())
			tsInt = flowPath.getEPart()
			outputPath = "//%s/FLOW//%s/%s/" %(elem.toString(), tsInt, fPartOut)
			flowTSM.setPathname(outputPath)
			outDss.write(flowTSM)
		# Need to check if the next point is a confluence
		# If so, need to save off the time series so the confluence can retrieve it
		dsNode = elem.getDownstreamNode()
		dsElem = dsNode.getDownstreamElement()
		if dsElem in confJuncs or dsElem in confResvs:
			logging.debug("Saving to Tributary Flow dictionary: %s" %elem)
			# Save the flows to the tribFlows dictionary
			tribFlows[elem] = flowTSM.copy()
			# Reset the flowTSM variable to 0
			flowTSM = flowTSM.multiply(0)
	tsBank.close()
	return True
	
