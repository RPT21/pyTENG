import pandas as pd
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog
import os

# Hide tkinter root window
root = Tk()
root.withdraw()

# Select files
file1 = filedialog.askopenfilename(
    title="Select first Excel file",
    filetypes=[("Excel files", "*.xlsx *.xls")]
)

file2 = filedialog.askopenfilename(
    title="Select second Excel file",
    filetypes=[("Excel files", "*.xlsx *.xls")]
)

# Read data
df1 = pd.read_excel(file1)
df2 = pd.read_excel(file2)

# What we are measuring
measure = "Voltage"

# Clip first 10% and last 10%
def clip_middle_80_percent(df):
    n = len(df)
    start_idx = int(0.10 * n)
    end_idx = int(0.90 * n)
    return df.iloc[start_idx:end_idx].reset_index(drop=True)

df1 = clip_middle_80_percent(df1)
df2 = clip_middle_80_percent(df2)

# Common Y limits
ymin = min(df1[measure].min(), df2[measure].min())
ymax = max(df1[measure].max(), df2[measure].max())

# Common X limits
xmin = min(df1["Time (s)"].min(), df2["Time (s)"].min())
xmax = max(df1["Time (s)"].max(), df2["Time (s)"].max())

# Create figure
fig, (ax1, ax2) = plt.subplots(
    2, 1,
    figsize=(10, 8),
    sharex=True
)

ax1.plot(df1["Time (s)"], df1[measure], color="blue")
ax1.set_title(os.path.basename(file1))
ax1.set_ylabel(measure)
ax1.set_ylim(ymin, ymax)
ax1.set_xlim(xmin, xmax)
ax1.grid(True)

ax2.plot(df2["Time (s)"], df2[measure], color="red")
ax2.set_title(os.path.basename(file2))
ax2.set_ylabel(measure)
ax2.set_xlabel("Time (s)")
ax2.set_ylim(ymin, ymax)
ax2.set_xlim(xmin, xmax)
ax2.grid(True)

plt.tight_layout()
plt.show()