import pandas as pd

df = pd.read_pickle('../../../Desktop/Test/DAQ_20250807_180349.pkl')
offset = -0.35
df["Signal"] = df["Signal"] - offset

df["LINMOT_ENABLE"][df["LINMOT_ENABLE"] < 2] = 0
df["LINMOT_ENABLE"][df["LINMOT_ENABLE"] > 2] = 1

df["LINMOT_UP_DOWN"][df["LINMOT_UP_DOWN"] < 2] = 0
df["LINMOT_UP_DOWN"][df["LINMOT_UP_DOWN"] > 2] = 1 


print(df.head())

# Do a plot
df.plot(x="Time (s)", y=["Signal", "LINMOT_ENABLE", "LINMOT_UP_DOWN"])
