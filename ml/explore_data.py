import pandas as pd

df = pd.read_csv("data/Occupancy_Estimation.csv")
print(df.shape)
print(df.head())
print(df.describe())
print(df.isna().sum())
print("First:", df["Date"].iloc[0], df["Time"].iloc[0])
print("Last:", df["Date"].iloc[-1], df["Time"].iloc[-1])
print(df["Room_Occupancy_Count"].value_counts())