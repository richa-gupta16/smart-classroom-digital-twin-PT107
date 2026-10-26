import os
import sys

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

sys.path.append(os.path.dirname(__file__))
from features import FEATURES, add_features

raw = pd.read_csv("data/Occupancy_Estimation.csv")
df = pd.DataFrame({
    "timestamp": pd.to_datetime(raw["Date"] + " " + raw["Time"]),
    "light": raw[["S1_Light", "S2_Light", "S3_Light", "S4_Light"]].mean(axis=1),
    "sound": raw[["S1_Sound", "S2_Sound", "S3_Sound", "S4_Sound"]].mean(axis=1),
    "co2": raw["S5_CO2"],
    "co2_slope": raw["S5_CO2_Slope"],
    "pir_1": raw["S6_PIR"],
    "pir_2": raw["S7_PIR"],
    "true_occupancy": raw["Room_Occupancy_Count"],
})
df = add_features(df)

model = RandomForestClassifier(n_estimators=200, class_weight="balanced",
                               random_state=42, n_jobs=-1)
model.fit(df[FEATURES], df["true_occupancy"])

joblib.dump({"model": model, "features": FEATURES}, "ml/occupancy_model.joblib")
size_mb = os.path.getsize("ml/occupancy_model.joblib") / 1e6
print(f"Saved ml/occupancy_model.joblib ({size_mb:.1f} MB), trained on {len(df)} rows")