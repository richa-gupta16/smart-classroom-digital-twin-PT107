import pandas as pd

df = pd.read_csv("data/Occupancy_Estimation.csv")
df["timestamp"] = pd.to_datetime(df["Date"] + " " + df["Time"])
print("Rows per date:")
print(df["timestamp"].dt.date.value_counts().sort_index())

gaps = df["timestamp"].diff()
print("\nMost common gaps between rows:")
print(gaps.value_counts().head())
print("\nGaps longer than 5 minutes:")
print(gaps[gaps > pd.Timedelta(minutes=5)])

print("\nOccupancy by date:")
print(df.groupby(df["timestamp"].dt.date)["Room_Occupancy_Count"].value_counts().unstack(fill_value=0))