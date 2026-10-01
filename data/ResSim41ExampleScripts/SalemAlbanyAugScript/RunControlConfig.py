#Run config for the Salem/Albany flow aug script

#ResSim Simulation Name
SIM_NAME="2026.02.24-2400"

# Step 1 alternative name (without flow-aug)
#If you want to process multiple alternatives, supply a list of their names
ALTERNATIVE_NAME_STEP1 = "ConSeson"
# ALTERNATIVE_NAME_STEP1 = ["ConNoAug"]

# How many days to look ahead for the actual year when calculating water balances.
# The median remaining seasonal net volume is used after the forecast period.
FORECAST_DAYS = 10

# Periods used for storage balance calculation for augmentation propotions.
PERIOD_START = (4, 1)  # Month, Day
PERIOD_END = (10, 31)  # Month, Day
