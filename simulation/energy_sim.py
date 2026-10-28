import os
import sys

import pandas as pd
from sklearn.ensemble import RandomForestClassifier

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "ml"))
sys.path.append(os.path.dirname(__file__))
from features import FEATURES, add_features
from timetable import is_scheduled

# ---- Fill these from docs/energy_assumptions.md (with sources) ----
LIGHT_FIXTURES = 4
LIGHT_WATTS_EACH = None   # watts per fixture
AC_KW = None              # electrical input in kW while running
# ---------------------------------------------------------------------

HOLD_MIN = 10             # minutes of "empty" before switching off
HOLDS = [5, 10, 15, 30]   # sweep for the model + PIR strategy

if LIGHT_WATTS_EACH is None or AC_KW is None:
    sys.exit("Fill LIGHT_WATTS_EACH and AC_KW from docs/energy_assumptions.md first.")

KW = LIGHT_FIXTURES * LIGHT_WATTS_EACH / 1000 + AC_KW

# ---- Load data (same columns as the message format) ----
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
df["day"] = df["timestamp"].dt.strftime("%Y-%m-%d")

# ---- Honest model predictions: each day predicted by a model that never saw that day ----
df["pred"] = 0
for d in df["day"].unique():
    held = df["day"] == d
    model = RandomForestClassifier(n_estimators=200, class_weight="balanced",
                                   random_state=42, n_jobs=-1)
    model.fit(df.loc[~held, FEATURES], df.loc[~held, "true_occupancy"])
    df.loc[held, "pred"] = model.predict(df.loc[held, FEATURES])

# Duration each reading represents (seconds); long gaps are capped at 60 s
nxt = df["timestamp"].shift(-1)
df["dt"] = (nxt - df["timestamp"]).dt.total_seconds().clip(upper=60).fillna(30)
print(f"Data covered: {df['dt'].sum() / 3600:.1f} hours over {df['day'].nunique()} dates\n")


def control(signal, hold_min):
    """Lights/AC on when signal is true; off after `hold_min` minutes without it."""
    hold_s = hold_min * 60
    on, last, prev_block, out = False, None, None, []
    for s, t, b in zip(signal, df["timestamp"], df["block"]):
        if b != prev_block:          # new recording block: start with everything off
            on, last, prev_block = False, None, b
        if s:
            on, last = True, t
        elif on and (t - last).total_seconds() >= hold_s:
            on = False
        out.append(on)
    return pd.Series(out, index=df.index)


def summarise(name, on):
    on = on.astype(bool)
    occ = df["true_occupancy"] > 0
    dt = df["dt"]
    hours_on = (dt * on).sum() / 3600
    off_events = (~on) & on.shift(1, fill_value=False)
    return {
        "strategy": name,
        "hours_on": round(hours_on, 1),
        "kWh": round(hours_on * KW, 2),
        "occupied_time_lights_off_%": round(100 * (dt * (occ & ~on)).sum() / (dt * occ).sum(), 1),
        "off_events_while_occupied": int((off_events & occ).sum()),
        "total_off_events": int(off_events.sum()),
    }


hour = df["timestamp"].dt.hour + df["timestamp"].dt.minute / 60
sig_model = (df["pred"] > 0).to_numpy()
sig_pir = (df["pir_any"] > 0).to_numpy()
sig_oracle = (df["true_occupancy"] > 0).to_numpy()

rows = [
    summarise("Baseline: always on", pd.Series(True, index=df.index)),
    summarise("Baseline: fixed 08:00-18:00", (hour >= 8) & (hour < 18)),
    summarise("Baseline: lecture timetable", df["timestamp"].apply(is_scheduled)),
    summarise(f"PIR only, hold {HOLD_MIN} min", control(sig_pir, HOLD_MIN)),
    summarise(f"Model only, hold {HOLD_MIN} min", control(sig_model, HOLD_MIN)),
    summarise(f"Model + PIR override, hold {HOLD_MIN} min", control(sig_model | sig_pir, HOLD_MIN)),
    summarise(f"Perfect knowledge (upper bound), hold {HOLD_MIN} min", control(sig_oracle, HOLD_MIN)),
]
res = pd.DataFrame(rows)
fixed = res.loc[res["strategy"] == "Baseline: fixed 08:00-18:00", "kWh"].iloc[0]
always = res.loc[res["strategy"] == "Baseline: always on", "kWh"].iloc[0]
res["saving_vs_fixed_%"] = (100 * (1 - res["kWh"] / fixed)).round(1)
res["saving_vs_always_%"] = (100 * (1 - res["kWh"] / always)).round(1)

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 20)
print(f"Combined power while on: {KW:.3f} kW "
      f"({LIGHT_FIXTURES} x {LIGHT_WATTS_EACH} W lights + {AC_KW} kW AC)\n")
print(res.to_string(index=False))

sweep = [summarise(f"Model + PIR, hold {h} min", control(sig_model | sig_pir, h)) for h in HOLDS]
sweep = pd.DataFrame(sweep)
sweep["saving_vs_fixed_%"] = (100 * (1 - sweep["kWh"] / fixed)).round(1)
print("\nHold-off sweep (model + PIR override):")
print(sweep.to_string(index=False))

res.to_csv("simulation/energy_results.csv", index=False)
sweep.to_csv("simulation/holdoff_sweep.csv", index=False)
print("\nSaved simulation/energy_results.csv and simulation/holdoff_sweep.csv")