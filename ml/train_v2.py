import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, recall_score, precision_score

df = pd.read_csv("data/Occupancy_Estimation.csv")
df["timestamp"] = pd.to_datetime(df["Date"] + " " + df["Time"])
df["day"] = df["timestamp"].dt.strftime("%Y-%m-%d")
df = df.sort_values("timestamp").reset_index(drop=True)

# Recording blocks: a new block starts after any gap longer than 5 minutes
df["block"] = (df["timestamp"].diff() > pd.Timedelta(minutes=5)).cumsum()

df["temperature"] = df[["S1_Temp", "S2_Temp", "S3_Temp", "S4_Temp"]].mean(axis=1)
df["light"] = df[["S1_Light", "S2_Light", "S3_Light", "S4_Light"]].mean(axis=1)
df["sound"] = df[["S1_Sound", "S2_Sound", "S3_Sound", "S4_Sound"]].mean(axis=1)
df["co2"] = df["S5_CO2"]
df["co2_slope"] = df["S5_CO2_Slope"]
df["pir_1"] = df["S6_PIR"]
df["pir_2"] = df["S7_PIR"]
df["pir_any"] = ((df["pir_1"] + df["pir_2"]) > 0).astype(int)

# Rolling features over the previous 10 readings (about 5 minutes), inside each block only
WINDOW = 10
for col in ["pir_any", "sound", "co2", "light"]:
    df[col + "_roll"] = (df.groupby("block")[col]
                           .rolling(WINDOW, min_periods=1).mean()
                           .reset_index(level=0, drop=True))

BASE = ["temperature", "light", "sound", "co2", "co2_slope", "pir_1", "pir_2"]
ROLL = ["pir_any_roll", "sound_roll", "co2_roll", "light_roll"]
VARIANTS = {
    "A: base features": BASE,
    "B: base + rolling": BASE + ROLL,
    "C: B without temperature": [f for f in BASE + ROLL if f != "temperature"],
}

TARGET = "Room_Occupancy_Count"
TRAIN_DAYS = ["2017-12-22", "2017-12-24", "2017-12-25", "2017-12-26"]
TEST_DAYS = ["2017-12-23", "2018-01-10", "2018-01-11"]
train = df[df["day"].isin(TRAIN_DAYS)]
test = df[df["day"].isin(TEST_DAYS)]
y_test = test[TARGET]
y_test_bin = (y_test > 0).astype(int)

rows = []
preds = {}
for name, feats in VARIANTS.items():
    model = RandomForestClassifier(n_estimators=200, class_weight="balanced",
                                   random_state=42, n_jobs=-1)
    model.fit(train[feats], train[TARGET])
    p = model.predict(test[feats])
    preds[name] = p
    pb = (p > 0).astype(int)
    rows.append({
        "variant": name,
        "count_acc": round(accuracy_score(y_test, p), 3),
        "count_macroF1": round(f1_score(y_test, p, average="macro", zero_division=0), 3),
        "occ_precision": round(precision_score(y_test_bin, pb, zero_division=0), 3),
        "occ_recall": round(recall_score(y_test_bin, pb, zero_division=0), 3),
        "occ_F1": round(f1_score(y_test_bin, pb, zero_division=0), 3),
    })

print(pd.DataFrame(rows).to_string(index=False))

print("\nPer-day results for each variant (count accuracy, occupied recall):")
for name, p in preds.items():
    t = test.copy()
    t["pred"] = p
    print("\n" + name)
    for day, g in t.groupby("day"):
        occ = g[TARGET] > 0
        rec = ((g["pred"] > 0) & occ).sum() / occ.sum() if occ.sum() else float("nan")
        acc = (g["pred"] == g[TARGET]).mean()
        print(f"  {day}: rows={len(g)}, occupied rows={occ.sum()}, "
              f"acc={acc:.3f}, occupied recall={rec:.3f}")