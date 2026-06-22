import pandas as pd
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog
import os

# =====================================================
# Time clipping function (keep 10% - 90% of duration)
# =====================================================

def clip_middle_80_percent(df):

    tmin = df["Time (s)"].min()
    tmax = df["Time (s)"].max()

    t_start = tmin + 0.10 * (tmax - tmin)
    t_end   = tmin + 0.90 * (tmax - tmin)

    return df[
        (df["Time (s)"] >= t_start) &
        (df["Time (s)"] <= t_end)
    ].reset_index(drop=True)


# =====================================================
# File selection
# =====================================================

root = Tk()
root.withdraw()

rload_files = []
rswitch_files = []

print("Select the 3 RLOAD files")

for i in range(3):
    file = filedialog.askopenfilename(
        title=f"Select RLOAD {i+1}",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )
    rload_files.append(file)

print("Select the 3 RSwitch files")

for i in range(3):
    file = filedialog.askopenfilename(
        title=f"Select RSwitch {i+1}",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )
    rswitch_files.append(file)


# =====================================================
# Read and clip data
# =====================================================

rload_data = []
rswitch_data = []

for file in rload_files:

    df = pd.read_excel(file)

    df = clip_middle_80_percent(df)

    rload_data.append(df)

for file in rswitch_files:

    df = pd.read_excel(file)

    df = clip_middle_80_percent(df)

    rswitch_data.append(df)


# =====================================================
# Compute global axis limits
# =====================================================

all_data = rload_data + rswitch_data

xmin = min(df["Time (s)"].min() for df in all_data)
xmax = max(df["Time (s)"].max() for df in all_data)

ymin = min(df["Voltage"].min() for df in all_data)
ymax = max(df["Voltage"].max() for df in all_data)

# Add a small margin to the Y-axis
ymargin = 0.05 * (ymax - ymin)

ymin -= ymargin
ymax += ymargin


# =====================================================
# Create 3x2 subplot layout
# =====================================================

fig, axes = plt.subplots(
    nrows=3,
    ncols=2,
    figsize=(14, 10),
    sharex=True,
    sharey=True
)


# =====================================================
# Generate plots
# =====================================================

for row in range(3):

    # ---------------------------------
    # Left column: RLOAD
    # ---------------------------------

    ax_left = axes[row, 0]

    ax_left.plot(
        rload_data[row]["Time (s)"],
        rload_data[row]["Voltage"],
        color="tab:blue",
        linewidth=1.5
    )

    ax_left.set_title(
        os.path.basename(rload_files[row]),
        fontsize=10
    )

    ax_left.grid(True, alpha=0.3)

    # ---------------------------------
    # Right column: RSwitch
    # ---------------------------------

    ax_right = axes[row, 1]

    ax_right.plot(
        rswitch_data[row]["Time (s)"],
        rswitch_data[row]["Voltage"],
        color="tab:red",
        linewidth=1.5
    )

    ax_right.set_title(
        os.path.basename(rswitch_files[row]),
        fontsize=10
    )

    ax_right.grid(True, alpha=0.3)


# =====================================================
# Apply common axis limits
# =====================================================

for ax in axes.flatten():

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)


# =====================================================
# Axis labels
# =====================================================

for ax in axes[:, 0]:
    ax.set_ylabel("Voltage (V)")

for ax in axes[-1, :]:
    ax.set_xlabel("Time (s)")


# =====================================================
# Column headers
# =====================================================

axes[0, 0].text(
    0.5,
    1.20,
    "RLOAD",
    transform=axes[0, 0].transAxes,
    ha="center",
    fontsize=14,
    fontweight="bold"
)

axes[0, 1].text(
    0.5,
    1.20,
    "RSwitch",
    transform=axes[0, 1].transAxes,
    ha="center",
    fontsize=14,
    fontweight="bold"
)


# =====================================================
# Display figure
# =====================================================

plt.tight_layout()
plt.show()