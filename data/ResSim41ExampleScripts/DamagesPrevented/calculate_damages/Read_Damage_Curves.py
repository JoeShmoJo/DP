# -*- coding: utf-8 -*-
"""
Created on Fri Dec 22 10:34:07 2023

@author: g2encjer
"""
import pandas as pd

# Define the path to your Excel file
excel_file_path = 'WV_Projects_Average_Annual_Benefits.xlsx'

# Define the tabs in the Excel file
tabs = ['Albany', 'Big Cliff', 'Coburg', 'Corvallis', 'Cottage Grove', 'Oakridge', 'Dorena', 'Eugene', 'Fall Creek', 'Foster', 'Goshen', 'Harrisburg', 'Jasper', 'Jefferson', 'Mehama', 'Monroe', 'Newberg', 'Salem', 'Vida', 'Walterville', 'Waterloo', 'Willamette+Clackamas', 'Willamette Falls']

# Initialize dictionaries to hold the dataframes
regulated_data = {}
unregulated_data = {}

# Function to read specific ranges for a sheet
def read_table(sheet, header_row, data_start_row, data_end_row):
    header = pd.read_excel(excel_file_path, sheet_name=sheet, usecols='F:I', skiprows=header_row, nrows=1, header=None).values[0]
    data = pd.read_excel(excel_file_path, sheet_name=sheet, usecols='F:I', skiprows=data_start_row, nrows=data_end_row - data_start_row + 1, header=None)
    df = pd.DataFrame(data, columns=header)
    return df

# Iterate over each tab and read the data
for tab in tabs:
    # Read the regulated data
    regulated_df = read_table(tab, 3, 4, 17)  # Header at row 4, data from row 5 to 18
    regulated_data[tab] = regulated_df

    # Read the unregulated data
    unregulated_df = read_table(tab, 22, 24, 37)  # Header at row 23, data from row 25 to 38
    unregulated_data[tab] = unregulated_df

# At this point, 'regulated_data' and 'unregulated_data' dictionaries are filled with dataframes for each tab






import openpyxl



# Function to read data from a specific range in a worksheet
def read_data(sheet, header_row, data_start_row, data_end_row):
    header = [cell.value for cell in sheet[header_row]][5:9]  # Read header from F to I
    data = []
    for row in sheet.iter_rows(min_row=data_start_row+1, max_row=data_end_row+1, min_col=6, max_col=9):
        data.append([cell.value for cell in row])
    return pd.DataFrame(data, columns=header)

# Initialize dictionaries to hold the dataframes
regulated_data = {}
unregulated_data = {}

# Load the workbook
wb = openpyxl.load_workbook(excel_file_path, data_only=True)

# Iterate over each tab and read the data
for tab in tabs:
    ws = wb[tab]

    # Read the regulated data
    regulated_data[tab] = read_data(ws, 4, 4, 17)  # Header at row 4, data from row 5 to 18

    # Read the unregulated data
    unregulated_data[tab] = read_data(ws, 23, 24, 37)  # Header at row 23, data from row 25 to 38

wb.close()

# At this point, 'regulated_data' and 'unregulated_data' dictionaries are filled with dataframes for each tab


pd.to_pickle(regulated_data, 'regulated_damage_curves.pkl')
pd.to_pickle(unregulated_data, 'unregulated_damage_curves.pkl')

a= pd.read_pickle('unregulated_damage_curves.pkl')
