These scripts run the 2 step process for adjusting the Salem and Albany reservoir augmentation flow. 

Current workflow:
	Create your ResSim simulation with the alternatives
	Set the RunControlConfig.py config parameters. Most importantly, the simulation name.
	Run the alternative in ResSim (Step 1, no flow aug)
	run the TwoStepSalemAlbanyAug.py file. This writes the min flows to the simulation file that is read by Step 2.
	run the alternative in Ressim again to do the Step 2. (or you can make a trial and run that to do step 2 so you can see with/without flow aug)

The SalemAugCheckPlots.py file generates plots that show the contribution of each project toward the Salem flow targets. Useful for diagnostics.

The bat files aren't working yet. I was trying to make an exe but that isn't going to happen. I will get a bat file that will do the whole process though, except setting up the initial alternative.  I will have the .yml for the environment too. For now, just remember that numpy has to be 1.22.4 or something old to work with pydsstools.

The median_remaining_by_day.pkl file contains remaining runoff from a given date through the end of October. It was computed using 1935-2019 data by Josh Roach on 10Dec2025.


