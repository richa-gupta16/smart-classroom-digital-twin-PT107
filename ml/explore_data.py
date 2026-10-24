import pandas as pd

df = pd.read_csv("data/Occupancy_Estimation.csv")
print(df.shape)
print(df.head())
print(df.describe())
print(df.isna().sum())