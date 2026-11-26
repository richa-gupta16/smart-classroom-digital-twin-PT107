import os
import sys

import pandas as pd
from sklearn.ensemble import RandomForestClassifier

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "ml"))
from features import FEATURES, add_features

raw = pd.read_csv("data/Occupancy_Estimation.csv")
df = pd.DataFrame({
    "timestamp": pd.to_datetime(raw["Date"] + " " + raw["Time"]),
    "light": raw[["S1_Light", "S2_Light", "S3_Light", "S4_Light"]].mean(axis=1),
    "sound": raw[["S1_Sound", "S2_Sound", "S3_Sound", "S4_Sound"]].mean(axis=1),
    "co2": raw["S5_CO2"], "co2_slope": raw["S5_CO2_Slope"],
    "pir_1": raw["S6_PIR"], "pir_2": raw["S7_PIR"],
    "true_occupancy": raw["Room_Occupancy_Count"],
})
df = add_features(df)
df["day"] = df["timestamp"].dt.strftime("%Y-%m-%d")
occ = df["true_occupancy"] > 0

# Day-held-out predictions, as in the energy simulation
df["pred"] = 0
for d in df["day"].unique():
    held = df["day"] == d
    m = RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=42, n_jobs=-1)
    m.fit(df.loc[~held, FEATURES], df.loc[~held, "true_occupancy"])
    df.loc[held, "pred"] = m.predict(df.loc[held, FEATURES])

nxt = df["timestamp"].shift(-1)
df["dt"] = (nxt - df["timestamp"]).dt.total_seconds().clip(upper=60).fillna(30)


def control(signal, hold_min):
    hold_s, on, last, prev, out = hold_min * 60, False, None, None, []
    for s, t, b in zip(signal, df["timestamp"], df["block"]):
        if b != prev:
            on, last, prev = False, None, b
        if s:
            on, last = True, t
        elif on and (t - last).total_seconds() >= hold_s:
            on = False
        out.append(on)
    return pd.Series(out, index=df.index)


pir = (df["pir_any"] > 0).to_numpy()
mod = (df["pred"] > 0).to_numpy()
strategies = {
    "PIR only, 10 min": control(pir, 10),
    "Model only, 10 min": control(mod, 10),
    "Model + PIR, 3 min": control(mod | pir, 3),
}

print("PIR-only recall per occupied day:")
for d in ["2017-12-22", "2017-12-23", "2018-01-10"]:
    g = df["day"] == d
    print(f"  {d}: {((df['pir_any'] > 0) & occ & g).sum() / (occ & g).sum():.3f}")
overall = ((df["pir_any"] > 0) & occ & df["day"].isin(["2017-12-22", "2017-12-23", "2018-01-10"])).sum() \
    / (occ & df["day"].isin(["2017-12-22", "2017-12-23", "2018-01-10"])).sum()
print(f"  all three days pooled: {overall:.3f}")

print("\nShare of occupied time without lights, per day:")
for name, on in strategies.items():
    row = []
    for d in ["2017-12-22", "2017-12-23", "2018-01-10"]:
        g = (df["day"] == d)
        dark = (df["dt"] * (occ & ~on & g)).sum()
        row.append(f"{d}: {100 * dark / (df['dt'] * (occ & g)).sum():.1f}%")
    print(f"  {name:20s} " + "   ".join(row))