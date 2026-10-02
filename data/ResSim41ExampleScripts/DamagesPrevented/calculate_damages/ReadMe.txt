Josh Roach
CENWP-HY
03Jan2024

The script Calculate_DP.py calculates damages from regulated and unregulated flows in the Willamette basin.

The Read_Damage_Curves.py reads in the damage curves from the WV_Projects_Average_Annual_Benefits spreadsheet . This takes a few minutes because of the method used to read the spreadsheet is slow to get around the spreadsheet formatting and formulas, but the data is written out to the regulated_damage_curves.pkl for quick read in later. So long as the curves don't change, the spreadsheet doesn't need to be read again. 

The Cacluclate_DP.py reads in the Willamette control point regulated and unregulated flows from the FlowReductions_2023.xlsx. This spreadsheet is produced by Ryan Cahill's Damages Prevented scripts with the name FlowReductions.xls, but I couldn't get the python module to read the old excel format to work so I saved the spreadsheet as an xlsx. The Calculate_DP.py script then reads the regulated_damage_curves.pkl and interpolates the damages for each regulated and unregulated flow. 

The damages_prevented_df is written out to the damages_prevented.csv



Oct 2026 update (ResSim 4.1 Willamette watershed)
Calculate_DP.py now reads the CSV results the ResSim 4.1 Damages Prevented menu writes
(scripts/DamagesPrevented/DPdata/Results/CP_Peaks.csv and Preliminary_per_project.csv),
so no spreadsheet conversion is needed. Run it from anywhere:

    python Calculate_DP.py                                   (reads ../DPdata/Results)
    python Calculate_DP.py <Results folder or FlowReductions.xls/.xlsx> [tag]

The tag is added to the output names (damages_prevented_<tag>.csv and
damages_prevented_ByProject_<tag>.csv). Old FlowReductions spreadsheets still work for past years:
it reproduces damages_prevented_2024.csv and damages_prevented_ByProject_2024.csv exactly from
FlowReductions_2024.xls. Reading an .xls needs the xlrd package; .xlsx needs openpyxl.

Control points are matched to damage curves by name in either network (aliases_dict), any case.
The dam-outlet control points in the new network are the _OUT junctions (Cottage Grove_OUT,
Dorena_OUT, Big Cliff_OUT, Fall Creek_OUT, Foster_OUT) and use the same curves as the old gage
names. Willamette+Clackamas is not in the new network, so its curve is unused. Big Cliff and Dexter
have no per-project column: their reductions are credited to Detroit and Lookout Point.
