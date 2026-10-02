# -*- coding: utf-8 -*-
'''
Find the dollar reduction associated with each project:
    1 - Calculate the damages prevented for each event by interpolating from the 2024 Disposition damage curves from the Damages Prevented Flow Reductions CP_Peaks calculated by the ResSim Scripts
    2 - Correct the Preliminary_per_project flow rductions calcuated by the ResSim Scripts:

        2a - Sum the individual project reductions and find the difference between the sum and the total difference
        2b - Sum the reductions (positive or negative) for reservoir groups ([Hills Creek, Lookout Point, Fall Creek],[Green Peter, Foster],[Cottage Grove,Dorena]) and distributing the sum for
            group by the percent flood storage the group has. This script has the functionality to easilly add or modify groups
        2v - Distribute the difference beween the sum of the reductions and the total by the percent flood storage of a contributing reservoir to the total flood storage of each contributing
            reservoir.

    4 - Find the proportional reduction for the event provided by each reservoir.
    5 - Multiply the proportional flow reduction for each location by the $$$ Damages Prevented

Oct 2026: reads the CSV results written by the ResSim 4.1 Damages Prevented menu
(DPdata/Results/CP_Peaks.csv and Preliminary_per_project.csv) instead of the old
FlowReductions.xls. Control points are matched to damage curves by their name in
the Willamette ResSim 4.1 network. The method itself is unchanged.

Usage:  python Calculate_DP.py
        python Calculate_DP.py <Results folder> [output tag]
Writes damages_prevented<_tag>.csv and damages_prevented_ByProject<_tag>.csv
next to this script.
'''
import os
import sys
import pandas as pd
import numpy as np

################################################################################
# USER INPUT
try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:   # pasted into a Jupyter/IPython cell
    SCRIPT_DIR = os.getcwd()

# The folder the ResSim Damages Prevented menu writes its CSV results to: the
# folder this script is in if it holds CP_Peaks.csv, else ../DPdata/Results
if os.path.exists(os.path.join(SCRIPT_DIR, 'CP_Peaks.csv')):
    RESULTS_DIR = SCRIPT_DIR
else:
    RESULTS_DIR = os.path.join(SCRIPT_DIR, '..', 'DPdata', 'Results')
# Added to the output file names, e.g. '2026' -> damages_prevented_2026.csv
OUTPUT_TAG = ''

# Damage curves (Read_Damage_Curves.py): next to this script, or in
# DamagesPrevented/calculate_damages when the script is run from DPdata/Results
DAMAGE_CURVES_PKL = os.path.join(SCRIPT_DIR, 'regulated_damage_curves.pkl')
if not os.path.exists(DAMAGE_CURVES_PKL):
    DAMAGE_CURVES_PKL = os.path.join(SCRIPT_DIR, '..', '..', 'calculate_damages', 'regulated_damage_curves.pkl')

# Damage curve (tab in WV_Projects_Average_Annual_Benefits.xlsx) -> control point
# name in the Willamette ResSim 4.1 network (old network name in the comment)
aliases_dict = {
    "Jasper": "MF Willamette_at Jasper",
    "Goshen": "CF WIllamette_nr Goshen",
    "Eugene": "Willamette_at Eugene",
    "Vida": "McKenzie_at Vida",
    "Harrisburg": "Willamette_at Harrisburg",
    "Monroe": "Long Tom_at Monroe",
    "Albany": "Willamette_at Albany",
    "Mehama": "No Santiam_at Mehama",
    "Waterloo": "So Santiam_at Waterloo",
    "Jefferson": "Santiam_at Jefferson",
    "Salem": "Willamette_at Salem",
    "Newberg": "Willamette_at Newberg",
    "Willamette Falls": "Willamette_abv Falls at Oregon City",
    "Willamette+Clackamas": "Willamette+Clackamas",
    "Corvallis": "Willamette+Marys",
    "Walterville": "Mkenzie_nr Walterville",               # McKenzie R. NR Walterville
    "Oakridge": "MF Willamette NR Oakridge",                # MF Willamette_blw NFork nr Oakridge
    "Coburg": "McKenzie_nr Coburg",
    "Cottage Grove": "Cottage Grove_OUT",                   # CF Willamette_blw Cottage Grove Dam
    "Dorena": "Dorena_OUT",                                 # Row_nr Cottage Grove
    "Big Cliff": "Big Cliff_OUT",                           # No Santiam_at Niagara
    "Fall Creek": "Fall Creek_OUT",                         # Fall_btw Winberry Cr nr Fall Creek
    "Foster": "Foster_OUT"                                  # So Santiam_nr Foster
}

Reservoir_Flood_Storage_Dict = {
    'Hills Creek': 200.1,
    'Lookout Point': 337.4,
    'Dexter': 4.8,
    'Fall Creek': 113.7,
    'Cottage Grove': 29.8,
    'Dorena': 70.5,
    'Fern Ridge': 108.6,
    'Cougar': 147.8,
    'Blue River': 85.5,
    'Green Peter': 268.2,
    'Foster': 29.7,
    'Detroit': 300.2,
    'Big Cliff': 2.9
}

# Define the groups of reservoirs
reservoir_groups = [
    ['Hills Creek', 'Lookout Point', 'Fall Creek'],
    ['Cottage Grove', 'Dorena'],
    ['Green Peter', 'Foster']
]
################################################################################


def read_cp_peaks(results_dir):
    """
    CP_Peaks.csv with the columns the rest of the script uses:
    Control Point, Unreg Peak Flow, Regulated Peak Flow, Flow Reduction (+ dates).
    """
    df = pd.read_csv(os.path.join(results_dir, 'CP_Peaks.csv'))
    return df.rename(columns={
        'Unreg Peak Flow (cfs)': 'Unreg Peak Flow',
        'Regulated Peak Flow (cfs)': 'Regulated Peak Flow',
        'Flow Reduction (cfs)': 'Flow Reduction'})


def read_per_project(results_dir):
    """Preliminary_per_project.csv: control points down, reservoirs across, 'x' = not downstream."""
    # Three description lines, then the header
    df = pd.read_csv(os.path.join(results_dir, 'Preliminary_per_project.csv'), header=3, index_col=0)
    df = df.replace('x', np.nan)
    return df.apply(pd.to_numeric)


# Function to interpolate property damage
def interpolate_damage(flow, damage_curve_df):
    # Ensure we're working on a copy to avoid SettingWithCopyWarning
    damage_curve_df = damage_curve_df.copy()

    # Check and standardize column names
    if 'Flow (cfs)' not in damage_curve_df.columns and 'Flow' in damage_curve_df.columns:
        damage_curve_df.rename(columns={'Flow': 'Flow (cfs)'}, inplace=True)
    if 'Property Damage' not in damage_curve_df.columns:
        raise KeyError(f"'Property Damage' column not found in the DataFrame columns: {damage_curve_df.columns}")

    # Remove any rows with NaN in the relevant columns
    damage_curve_df.dropna(subset=['Flow (cfs)', 'Property Damage'], inplace=True)

    # Ensure the flow values are sorted
    damage_curve_df.sort_values('Flow (cfs)', inplace=True)

    # Interpolate to find the property damage for the given flow
    return np.interp(flow, damage_curve_df['Flow (cfs)'].values, damage_curve_df['Property Damage'].values)


# Function to map long names to short names
def map_long_to_short(long_name, aliases_dict):
    for short, long in aliases_dict.items():
        if long == long_name:
            return short
    return None  # If no match is found


def main(results_dir, tag):
    out_suffix = '_' + tag if tag else ''
    print(f"Results: {os.path.abspath(results_dir)}")

    """
    Part 1 - Interpolate $ Damges from Damages Prevented flows and 2024 Disposition damage curves
    Created on Wed Dec 27 10:28:06 2023
    @author: g2encjer
    """
    damage_curves_dict = pd.read_pickle(DAMAGE_CURVES_PKL)
    damages_prevented_df = read_cp_peaks(results_dir)

    # Map long names to short names in the Damages_Prevented table
    damages_prevented_df['Short Name'] = damages_prevented_df['Control Point'].apply(lambda x: map_long_to_short(x, aliases_dict))

    # Interpolate property damage for each control point
    for index, row in damages_prevented_df.iterrows():
        short_name = row['Short Name']
        unreg_flow = row['Unreg Peak Flow']
        reg_flow = row['Regulated Peak Flow']

        # Retrieve the corresponding damage curve DataFrame
        damage_curve_df = damage_curves_dict.get(short_name)

        if damage_curve_df is not None:
            # Interpolate damage for unregulated flow
            unreg_damage = interpolate_damage(unreg_flow, damage_curve_df)

            # Interpolate damage for regulated flow
            reg_damage = interpolate_damage(reg_flow, damage_curve_df)

            # Calculate the difference in damage
            damage_difference = unreg_damage - reg_damage

            # Assign the calculated damages to new columns in the DataFrame
            damages_prevented_df.at[index, 'Unreg Property Damage'] = unreg_damage
            damages_prevented_df.at[index, 'Reg Property Damage'] = reg_damage
            damages_prevented_df.at[index, 'Damage Difference'] = damage_difference
        else:
            print(f"WARNING: no damage curve for control point '{row['Control Point']}' - add it to aliases_dict. Counted as $0.")

    used = set(damages_prevented_df['Short Name'].dropna())
    for short in damage_curves_dict:
        if short not in used:
            print(f"Note: damage curve '{short}' has no control point in these results.")

    Total_Damages_Prevented = damages_prevented_df['Damage Difference'].sum()

    columns_to_round = [
        "Unreg Peak Flow", "Regulated Peak Flow", "Flow Reduction",
        "Unreg Property Damage", "Reg Property Damage", "Damage Difference"
    ]
    damages_prevented_df[columns_to_round] = damages_prevented_df[columns_to_round].round(0)
    damages_prevented_df.index = damages_prevented_df['Control Point']
    out1 = os.path.join(SCRIPT_DIR, f'damages_prevented{out_suffix}.csv')
    damages_prevented_df.to_csv(out1, index=False)

    """
    Part 2
    Correct per project reductions and allocate per project $$$ damages reduced
    Created on Thu Dec 12 12:10:02 2024
    @author: g2encjer
    """
    # Calculate the proportion of each reservoir's storage compared to its group's total storage
    reservoir_proportions = {}

    # Calculate proportions for reservoirs in groups
    for group in reservoir_groups:
        group_total_storage = sum(Reservoir_Flood_Storage_Dict[res] for res in group)
        for res in group:
            reservoir_proportions[res] = Reservoir_Flood_Storage_Dict[res] / group_total_storage

    # Assign proportion 1 for reservoirs not in any group
    all_grouped_reservoirs = set(res for group in reservoir_groups for res in group)
    for res in Reservoir_Flood_Storage_Dict:
        if res not in all_grouped_reservoirs:
            reservoir_proportions[res] = 1

    # Per-project reductions ('x' already NaN). Re-regulating dams (Big Cliff,
    # Dexter) have no column: the ResSim scripts credit them to Detroit and
    # Lookout Point.
    df = read_per_project(results_dir)
    unknown = [c for c in df.columns if c != 'Total Flow Reduction' and c not in Reservoir_Flood_Storage_Dict]
    if unknown:
        raise KeyError(f"Reservoirs in Preliminary_per_project missing from Reservoir_Flood_Storage_Dict: {unknown}")

    df2 = df.copy()

    for group in reservoir_groups:
        group = [res for res in group if res in df2.columns]
        group_sum = df2[group].sum(axis=1)  # Calculate row-wise sum for the group
        # Assign the group sum back to all columns in the group
        for col in group:
            df2[col] = group_sum

    df3 = df2.copy()
    # Multiply each value in df2 columns by their respective reservoir_proportions
    for col in df2.columns:
        if col in reservoir_proportions:
            df3[col] = df3[col] * reservoir_proportions[col]

    # Replace values less than 1 with NaN
    df3[df3 < 1] = np.nan

    # Calculate the Difference column
    df3['Difference'] = df3['Total Flow Reduction'] - df3.drop(columns=['Total Flow Reduction']).sum(axis=1)

    df4 = df3.copy()

    # Redistribute the "Difference" to reservoirs based on their flood storage
    for index, row in df4.iterrows():
        # Identify reservoirs with reductions in the current row
        reservoirs_with_reduction = row.drop(labels=['Total Flow Reduction', 'Difference']).dropna().index
        if len(reservoirs_with_reduction) > 0:
            # Calculate the total storage for these reservoirs
            total_storage = sum(Reservoir_Flood_Storage_Dict[res] for res in reservoirs_with_reduction)
            # Redistribute the difference proportionally
            for res in reservoirs_with_reduction:
                storage_proportion = Reservoir_Flood_Storage_Dict[res] / total_storage
                df4.at[index, res] += row['Difference'] * storage_proportion

    # Verify the result
    Final_Difference = df4['Total Flow Reduction'] - df4.drop(columns=['Total Flow Reduction', "Difference"]).sum(axis=1)
    Total_Flow_Reduction = df4['Total Flow Reduction']

    print(df4['Difference'])

    df5 = df4.drop(columns=["Difference", 'Total Flow Reduction'])

    df5 = df5.div(Total_Flow_Reduction, axis=0)

    # No total reduction (NaN or 0) -> nothing to share out
    df5 = df5.replace([np.inf, -np.inf], np.nan).fillna(0)

    df6 = df5.copy()

    Damages_Prevented_by_Project = df6.mul(damages_prevented_df['Damage Difference'].fillna(0), axis=0)

    Damages_Prevented_by_Project = Damages_Prevented_by_Project.fillna(0).astype(int)

    out2 = os.path.join(SCRIPT_DIR, f'damages_prevented_ByProject{out_suffix}.csv')
    Damages_Prevented_by_Project.to_csv(out2, index=True)

    print(f"\nTotal damages prevented: ${Total_Damages_Prevented:,.0f}")
    print(f"Wrote {out1}")
    print(f"Wrote {out2}")
    return damages_prevented_df, Damages_Prevented_by_Project


if __name__ == '__main__':
    # Jupyter/Spyder kernels add their own '--f=...' argument; ignore anything starting with '-'
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    results_dir = args[0] if len(args) > 0 else RESULTS_DIR
    tag = args[1] if len(args) > 1 else OUTPUT_TAG
    main(results_dir, tag)
