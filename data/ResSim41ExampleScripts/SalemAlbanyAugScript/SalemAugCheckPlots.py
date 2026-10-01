import pandas as pd
import importlib
from pydsstools.heclib.dss import HecDss
import numpy as np
import os
from pydsstools.core import TimeSeriesContainer
import matplotlib.pyplot as plt
import SalemAugConfig as cfg
import webbrowser
import plotly.graph_objects as go
import plotly.express as px
cfg = importlib.reload(cfg)


SIM_NAME = cfg.SIM_NAME
ALTERNATIVE_NAME_STEP1 = cfg.ALTERNATIVE_NAME_STEP1 + (
    "--0" if len(cfg.ALTERNATIVE_NAME_STEP1) == 8 else
    "-0" if len(cfg.ALTERNATIVE_NAME_STEP1) == 9 else
    "0" if len(cfg.ALTERNATIVE_NAME_STEP1) == 10 else
    ""  # no change if the length is 11
)
ALTERNATIVE_NAME_STEP2 = cfg.ALTERNATIVE_NAME_STEP2 + (
    "--0" if len(cfg.ALTERNATIVE_NAME_STEP2) == 8 else
    "-0" if len(cfg.ALTERNATIVE_NAME_STEP2) == 9 else
    "0" if len(cfg.ALTERNATIVE_NAME_STEP2) == 10 else
    ""  # no change if the length is 11
)

AUG_RESERVOIRS_DICT = cfg.AUG_RESERVOIRS_DICT
WATERSHED_FILEPATH = cfg.WATERSHED_FILEPATH
# DSS_FILE_IN should be up a directory from the ResSim wksp file in the rss folder then up inot the SIM_NAME folder
DSS_FILE_IN = os.path.join(os.path.dirname(WATERSHED_FILEPATH), "rss", SIM_NAME, "simulation.dss")

DSS_FILE_OUT = os.path.join(os.path.dirname(WATERSHED_FILEPATH), "rss", SIM_NAME, "Step2outflows.dss")

START_DT = cfg.START_DT
END_DT = cfg.END_DT
FORECAST_DAYS = cfg.FORECAST_DAYS
PERIOD_START = cfg.PERIOD_START
PERIOD_END = cfg.PERIOD_END
WY_DES_DT = cfg.WY_DES_DT
AF_PER_CFS_DAY = cfg.AF_PER_CFS_DAY

TRAVEL_TIME_DAYS_DICT = cfg.TRAVEL_TIME_DAYS_DICT
MIN_CON_STOR_DICT = cfg.MIN_CON_STOR_DICT
ALIAS_DICT = cfg.ALIAS_DICT
WY_TYPE_FLOW_DICT = cfg.WY_TYPE_FLOW_DICT
TRIB_MINFLOW_DICT = cfg.TRIB_MINFLOW_DICT


YEARS = [
    2005,
    2006,
    2007,
]

def create_path_dict(F_PART):
    path_dict = {
        "LOP_stor": f"//LOOKOUT POINT-POOL/STOR//1DAY/{F_PART}/",
        "LOP_inflow": f"//LOOKOUT POINT-POOL/FLOW-IN//1DAY/{F_PART}/",
        "LOP_inflow": f"//LOOKOUT POINT_OUT/FLOW-UNREG//1DAY/{F_PART}/",
        "LOP_outflow": f"//LOOKOUT POINT-POOL/FLOW-OUT//1DAY/{F_PART}/",
        "LOP_rcStor": f"//LOOKOUT POINT-RULE CURVE/STOR-ZONE//1DAY/{F_PART}/",
        "DET_stor": f"//DETROIT-POOL/STOR//1DAY/{F_PART}/",
        "DET_inflow": f"//DETROIT-POOL/FLOW-IN//1DAY/{F_PART}/",
        "DET_outflow": f"//DETROIT-POOL/FLOW-OUT//1DAY/{F_PART}/",
        "DET_rcStor": f"//DETROIT-RULE CURVE/STOR-ZONE//1DAY/{F_PART}/",
        "GPR_stor": f"//GREEN PETER-POOL/STOR//1DAY/{F_PART}/",
        "GPR_inflow": f"//GREEN PETER-POOL/FLOW-IN//1DAY/{F_PART}/",
        "GPR_inflow": f"//FOSTER_OUT/FLOW-UNREG//1DAY/{F_PART}/",
        "GPR_outflow": f"//GREEN PETER-POOL/FLOW-OUT//1DAY/{F_PART}/",
        "GPR_rcStor": f"//GREEN PETER-RULE CURVE/STOR-ZONE//1DAY/{F_PART}/",
        "CGR_stor": f"//COUGAR-POOL/STOR//1DAY/{F_PART}/",
        "CGR_inflow": f"//COUGAR-POOL/FLOW-IN//1DAY/{F_PART}/",
        "CGR_outflow": f"//COUGAR-POOL/FLOW-OUT//1DAY/{F_PART}/",
        "CGR_rcStor": f"//COUGAR-RULE CURVE/STOR-ZONE//1DAY/{F_PART}/",
        "BLU_stor": f"//BLUE RIVER-POOL/STOR//1DAY/{F_PART}/",
        "BLU_inflow": f"//BLUE RIVER-POOL/FLOW-IN//1DAY/{F_PART}/",
        "BLU_outflow": f"//BLUE RIVER-POOL/FLOW-OUT//1DAY/{F_PART}/",
        "BLU_rcStor": f"//BLUE RIVER-RULE CURVE/STOR-ZONE//1DAY/{F_PART}/",
        "FAL_stor": f"//FALL CREEK-POOL/STOR//1DAY/{F_PART}/",
        "FAL_inflow": f"//FALL CREEK-POOL/FLOW-IN//1DAY/{F_PART}/",
        "FAL_outflow": f"//FALL CREEK-POOL/FLOW-OUT//1DAY/{F_PART}/",
        "FAL_rcStor": f"//FALL CREEK-RULE CURVE/STOR-ZONE//1DAY/{F_PART}/",
        "HCR_stor": f"//HILLS CREEK-POOL/STOR//1DAY/{F_PART}/",
        "HCR_inflow": f"//HILLS CREEK-POOL/FLOW-IN//1DAY/{F_PART}/",
        "HCR_outflow": f"//HILLS CREEK-POOL/FLOW-OUT//1DAY/{F_PART}/",
        "HCR_rcStor": f"//HILLS CREEK-RULE CURVE/STOR-ZONE//1DAY/{F_PART}/",
        "DOR_stor": f"//DORENA-POOL/STOR//1DAY/{F_PART}/",
        "DOR_inflow": f"//DORENA-POOL/FLOW-IN//1DAY/{F_PART}/",
        "DOR_outflow": f"//DORENA-POOL/FLOW-OUT//1DAY/{F_PART}/",
        "DOR_rcStor": f"//DORENA-RULE CURVE/STOR-ZONE//1DAY/{F_PART}/",
        "COT_stor": f"//COTTAGE GROVE-POOL/STOR//1DAY/{F_PART}/",
        "COT_inflow": f"//COTTAGE GROVE-POOL/FLOW-IN//1DAY/{F_PART}/",
        "COT_outflow": f"//COTTAGE GROVE-POOL/FLOW-OUT//1DAY/{F_PART}/",
        "COT_rcStor": f"//COTTAGE GROVE-RULE CURVE/STOR-ZONE//1DAY/{F_PART}/",
        "FRN_stor": f"//FERN RIDGE-POOL/STOR//1DAY/{F_PART}/",
        "FRN_inflow": f"//FERN RIDGE-POOL/FLOW-IN//1DAY/{F_PART}/",
        "FRN_outflow": f"//FERN RIDGE-POOL/FLOW-OUT//1DAY/{F_PART}/",
        "FRN_rcStor": f"//FERN RIDGE-RULE CURVE/STOR-ZONE//1DAY/{F_PART}/",
        "FOS_stor": f"//FOSTER-POOL/STOR//1DAY/{F_PART}/",
        "FOS_inflow": f"//FOSTER-POOL/FLOW-IN//1DAY/{F_PART}/",
        "FOS_outflow": f"//FOSTER-POOL/FLOW-OUT//1DAY/{F_PART}/",
        "FOS_rcStor": f"//FOSTER-RULE CURVE/STOR-ZONE//1DAY/{F_PART}/",
        "SLM_flow": f"//WILLAMETTE_AT SALEM/FLOW/01JAN1935/1DAY/{F_PART}/"
    }
    return path_dict



# Reads all paths from a DSS file into a single DataFrame.
def readallpaths(dss_file, path_dict, start_dt, end_dt):
    fid = HecDss.Open(dss_file)
    dflist = []
    for alias, path in path_dict.items():
        try:
            ts = fid.read_ts(path, window=(start_dt, end_dt), trim_missing=True)
            df = pd.DataFrame(ts.values, columns=[alias], index=np.array(ts.pytimes))
            dflist.append(df.copy())
        except Exception as e:
            msg = f"[DSS] Failed '{alias}' -> {path} in {os.path.basename(dss_file)}: {e}"
    fid.close()
    if not dflist:
        return pd.DataFrame()
    data = pd.concat(dflist, axis=1)
    data.index = pd.to_datetime(data.index)
    # (rare) guard
    data = data[~data.index.duplicated(keep="last")]
    return data

def get_min_max_conservation_storage(data, YEARS):
    """
    Extract min and max conservation storage values using the year from START_DT.

    Uses:
      minConStor = rcStor on Jan 1 of START_DT.year
      maxConStor = rcStor on Jun 15 of START_DT.year

    Returns:
      minConStor_dict, maxConStor_dict
    """

    year = YEARS[0]
    jan1_dt = pd.Timestamp(year, 1, 1)
    jun15_dt = pd.Timestamp(year, 6, 15)

    # Safety check: ensure these dates exist
    if jan1_dt not in data.index:
        raise ValueError(f"Missing Jan 1 {year} in data index.")
    if jun15_dt not in data.index:
        raise ValueError(f"Missing Jun 15 {year} in data index.")

    minConStor_dict = {}
    maxConStor_dict = {}

    for res in AUG_RESERVOIRS_DICT.keys():
        alias = ALIAS_DICT[res]
        rc_col = f"{alias}_rcStor"

        minConStor_dict[res] = data.loc[jan1_dt, rc_col]
        maxConStor_dict[res] = data.loc[jun15_dt, rc_col]

    return minConStor_dict, maxConStor_dict

def compute_percent_con_storage_by_year(years, data, minConStor_dict, maxConStor_dict):
    """
    Computes the % full conservation storage time series for each reservoir,
    for each year provided.

    Args:
        years (iterable): List of years to process.
        data (pd.DataFrame): Daily/hourly storage dataframe, datetime index.
        minConStor_dict (dict): {res: min conservation storage value}
        maxConStor_dict (dict): {res: max conservation storage value}

    Returns:
        dict: {year: DataFrame of %full storage time series}
    """

    percent_con_stor_by_year = {}

    for year in years:
        # Slice data to that calendar year
        start_dt = pd.Timestamp(year=year, month=1, day=1)
        end_dt   = pd.Timestamp(year=year, month=12, day=31)
        year_data = data.loc[start_dt:end_dt].copy()

        # DataFrame to store percent-full results
        year_pct_df = pd.DataFrame(index=year_data.index)

        for res in AUG_RESERVOIRS_DICT.keys():
            alias = ALIAS_DICT[res]
            stor_col = f"{alias}_stor"

            minConStor = minConStor_dict[res]
            maxConStor = maxConStor_dict[res]
            usable_range = maxConStor - minConStor

            # Compute fraction full
            frac_full = (year_data[stor_col] - minConStor) / usable_range

            # Convert to percent
            pct_full = frac_full * 100.0

            # Add to year's DataFrame
            year_pct_df[alias] = pct_full

        percent_con_stor_by_year[year] = year_pct_df

    return percent_con_stor_by_year


# Main

step1_path_dict = create_path_dict(ALTERNATIVE_NAME_STEP1)
step2_path_dict = create_path_dict(ALTERNATIVE_NAME_STEP2)

# make a path dict that has all the stor and rcstor paths for reservoirs
step1_store_path_dict = {}
for path in step1_path_dict:
    if "_stor" in path or "_rcStor" in path:
        step1_store_path_dict[path] = step1_path_dict[path]

step2_store_path_dict = {}
for path in step2_path_dict:
    if "_stor" in path or "_rcStor" in path:
        step2_store_path_dict[path] = step2_path_dict[path]

step1_data = readallpaths(DSS_FILE_IN, step1_store_path_dict, START_DT, END_DT)

step2_data = readallpaths(DSS_FILE_IN, step2_store_path_dict, START_DT, END_DT)

# Create paths for dss files, read dss data, add minflows, create net flows (inflow - minflow), and combine.
# data = readallpaths(DSS_FILE, path_dict, START_DT, END_DT)

# Extract the min con stor and max con stor
minConStor_dict, maxConStor_dict = get_min_max_conservation_storage(step1_data, YEARS)

step1_pct_con = compute_percent_con_storage_by_year(
    YEARS,
    step1_data,
    minConStor_dict,
    maxConStor_dict
)

step2_pct_con = compute_percent_con_storage_by_year(
    YEARS,
    step2_data,
    minConStor_dict,
    maxConStor_dict
)

# Plot comparison of step 1 and step 2 percent conservation storage for each reservoir for year in YEARS
# make this a ploty interactive figure. step 2 should be dashed lines.

# import os
# import plotly.graph_objects as go
# import plotly.express as px
# import matplotlib.pyplot as plt

# -------------------------------------------------------
# 0. Output folder for ALL plots
# -------------------------------------------------------
PLOT_DIR = "SalemAugPlots"
os.makedirs(PLOT_DIR, exist_ok=True)

# -------------------------------------------------------
# 1. Assign mapping colors for multi-reservoir figures only
# -------------------------------------------------------
RES_COLORS = {
    res: color
    for res, color in zip(
        AUG_RESERVOIRS_DICT.keys(),
        px.colors.qualitative.D3   # consistent colors for multi-reservoir plots
    )
}

# Colors for individual reservoir PNGs
INDIV_STEP1_COLOR = "red"
INDIV_STEP2_COLOR = "red"

# -------------------------------------------------------
# 2. Loop through years and generate plots
# -------------------------------------------------------
for year in YEARS:

    step1_df = step1_pct_con[year]
    step2_df = step2_pct_con[year]

    # -------------------------------
    # (A) Plotly multi-reservoir HTML
    # -------------------------------
    fig = go.Figure()

    for res in AUG_RESERVOIRS_DICT.keys():
        alias = ALIAS_DICT[res]
        color = RES_COLORS[res]     # multi-reservoir uses mapped color

        # Step 1
        fig.add_trace(go.Scatter(
            x=step1_df.index,
            y=step1_df[alias],
            mode="lines",
            name="Step 1",
            legendgroup=res,
            legendgrouptitle_text=res,
            line=dict(color=color, dash="solid")
        ))

        # Step 2
        fig.add_trace(go.Scatter(
            x=step2_df.index,
            y=step2_df[alias],
            mode="lines",
            name="Step 2",
            legendgroup=res,
            showlegend=True,
            line=dict(color=color, dash="dash")
        ))

    fig.update_layout(
        title=f"Percent Conservation Storage Comparison for Year {year}",
        xaxis_title="Date",
        yaxis_title="Percent Conservation Storage (%)",
        hovermode="x unified",
        legend=dict(groupclick="toggleitem", borderwidth=1)
    )

    # Save Plotly HTML inside the folder
    output_html = os.path.join(
        PLOT_DIR, f"Salem_Augmentation_Comparison_{year}.html"
    )
    fig.write_html(output_html)
    print(f"Saved Plotly HTML: {output_html}")


    # -------------------------------------------------------
    # (B) Matplotlib: Per-reservoir PNGs (Step 1 vs Step 2)
    # -------------------------------------------------------
    for res in AUG_RESERVOIRS_DICT.keys():
        alias = ALIAS_DICT[res]

        plt.figure(figsize=(10,5))

        # Step 1 (solid red)
        plt.plot(
            step1_df.index,
            step1_df[alias],
            label="Step 1",
            linestyle='-',
            color=INDIV_STEP1_COLOR
        )

        # Step 2 (dashed red)
        plt.plot(
            step2_df.index,
            step2_df[alias],
            label="Step 2",
            linestyle='--',
            color=INDIV_STEP2_COLOR
        )

        plt.title(f"{res} – Percent Conservation Storage (Step 1 vs Step 2) – {year}")
        plt.xlabel("Date")
        plt.ylabel("Percent Conservation Storage (%)")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        res_png = os.path.join(
            PLOT_DIR, f"{alias}_{year}_Step1_vs_Step2.png"
        )
        plt.savefig(res_png, dpi=150)
        plt.close()
        print(f"Saved per-reservoir PNG: {res_png}")


    # -------------------------------------------------------
    # (C) Matplotlib: Step-2-only PNG (multi-reservoir)
    # -------------------------------------------------------
    plt.figure(figsize=(10,5))

    for res in AUG_RESERVOIRS_DICT.keys():
        alias = ALIAS_DICT[res]
        color = RES_COLORS[res]   # multi-reservoir uses mapping

        plt.plot(
            step2_df.index,
            step2_df[alias],
            label=res,
            linestyle='-',
            color=color
        )

    plt.title(f"Percent Conservation Storage – Step 2 Only – {year}")
    plt.xlabel("Date")
    plt.ylabel("Percent Conservation Storage (%)")
    plt.legend(title="Reservoir", ncol=2)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    step2_png = os.path.join(
        PLOT_DIR, f"Salem_Augmentation_Step2_Only_{year}.png"
    )
    plt.savefig(step2_png, dpi=150)
    plt.close()
    print(f"Saved Step 2 only PNG: {step2_png}")
