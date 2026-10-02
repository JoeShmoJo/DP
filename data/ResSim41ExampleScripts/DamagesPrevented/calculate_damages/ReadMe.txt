Josh Roach
CENWP-HY
03Jan2024

The script Calculate_DP.py calculates damages from regulated and unregulated flows in the Willamette basin.

The Read_Damage_Curves.py reads in the damage curves from the WV_Projects_Average_Annual_Benefits spreadsheet . This takes a few minutes because of the method used to read the spreadsheet is slow to get around the spreadsheet formatting and formulas, but the data is written out to the regulated_damage_curves.pkl for quick read in later. So long as the curves don't change, the spreadsheet doesn't need to be read again. 

The Cacluclate_DP.py reads in the Willamette control point regulated and unregulated flows from the FlowReductions_2023.xlsx. This spreadsheet is produced by Ryan Cahill's Damages Prevented scripts with the name FlowReductions.xls, but I couldn't get the python module to read the old excel format to work so I saved the spreadsheet as an xlsx. The Calculate_DP.py script then reads the regulated_damage_curves.pkl and interpolates the damages for each regulated and unregulated flow. 

The damages_prevented_df is written out to the damages_prevented.csv

