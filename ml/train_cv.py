import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, f1_score,
                             precision_score, recall_score)

df = pd.read_csv("data/Occupancy_Estimation.csv")
df["timestamp"] = pd.to_datetime(df["Date"] + " " + df["Time"])
df["day"] = df["timestamp"].dt.strftime("%Y-%m-%d")
df = df.sort_values("timestamp").reset_index(drop=True)
df["block"] = (df["timestamp"].diff() > pd.Timedelta(minutes=5)).cumsum()

df["light"] = df[["S1_Light", "S2_Light", "S3_Light", "S4_Light"]].mean(axis=1)
df["sound"] = df[["S1_Sound", "S2_Sound", "S3_Sound", "S4_Sound"]].mean(axis=1)
df["co2"] = df["S5_CO2"]
df["co2_slope"] = df["S5_CO2_Slope"]
df["temperature"] = df[["S1_Temp", "S2_Temp", "S3_Temp", "S4_Temp"]].mean(axis=1)
df["pir_1"] = df["S6_PIR"]
df["pir_2"] = df["S7_PIR"]
df["pir_any"] = ((df["pir_1"] + df["pir_2"]) > 0).astype(int)

WINDOW = 10
for col in ["pir_any", "sound", "co2", "light"]:
    df[col + "_roll"] = (df.groupby("block")[col]
                           .rolling(WINDOW, min_periods=1).mean()
                           .reset_index(level=0, drop=True))

FEATURES = ["light", "sound", "co2", "co2_slope", "pir_1", "pir_2",
            "pir_any_roll", "sound_roll", "co2_roll", "light_roll"]  # variant C
TARGET = "Room_Occupancy_Count"
OCCUPIED_DAYS = ["2017-12-22", "2017-12-23", "2018-01-10"]

print("=== Leave-one-occupied-day-out (variant C features) ===")
results = []
for held_out in OCCUPIED_DAYS:
    train = df[df["day"] != held_out]
    test = df[df["day"] == held_out]
    model = RandomForestClassifier(n_estimators=200, class_weight="balanced",
                                   random_state=42, n_jobs=-1)
    model.fit(train[FEATURES], train[TARGET])
    p = model.predict(test[FEATURES])
    y = test[TARGET]
    yb, pb = (y > 0).astype(int), (p > 0).astype(int)
    labels = sorted(y.unique())
    results.append({
        "held_out_day": held_out,
        "rows": len(test),
        "occupied_rows": int(yb.sum()),
        "count_acc": round(accuracy_score(y, p), 3),
        "count_macroF1": round(f1_score(y, p, labels=labels, average="macro", zero_division=0), 3),
        "occ_precision": round(precision_score(yb, pb, zero_division=0), 3),
        "occ_recall": round(recall_score(yb, pb, zero_division=0), 3),
        "occ_F1": round(f1_score(yb, pb, zero_division=0), 3),
    })
res = pd.DataFrame(results)
print(res.to_string(index=False))
print("\nMean over the 3 folds:")
print(res[["count_acc", "count_macroF1", "occ_precision", "occ_recall", "occ_F1"]].mean().round(3))

print("\n=== Mean sensor values per day, split by empty vs occupied ===")
df["occupied"] = df[TARGET] > 0
cols = ["light", "sound", "co2", "temperature"]
print(df.groupby(["day", "occupied"])[cols].mean().round(2).to_string())