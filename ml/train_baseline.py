import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, classification_report,
                             ConfusionMatrixDisplay)

df = pd.read_csv("data/Occupancy_Estimation.csv")
df["timestamp"] = pd.to_datetime(df["Date"] + " " + df["Time"])
df["day"] = df["timestamp"].dt.strftime("%Y-%m-%d")

# Same features as the streamed message (docs/message_format.md)
df["temperature"] = df[["S1_Temp", "S2_Temp", "S3_Temp", "S4_Temp"]].mean(axis=1)
df["light"] = df[["S1_Light", "S2_Light", "S3_Light", "S4_Light"]].mean(axis=1)
df["sound"] = df[["S1_Sound", "S2_Sound", "S3_Sound", "S4_Sound"]].mean(axis=1)
df["co2"] = df["S5_CO2"]
df["co2_slope"] = df["S5_CO2_Slope"]
df["pir_1"] = df["S6_PIR"]
df["pir_2"] = df["S7_PIR"]

FEATURES = ["temperature", "light", "sound", "co2", "co2_slope", "pir_1", "pir_2"]
TARGET = "Room_Occupancy_Count"

TRAIN_DAYS = ["2017-12-22", "2017-12-24", "2017-12-25", "2017-12-26"]
TEST_DAYS = ["2017-12-23", "2018-01-10", "2018-01-11"]

train = df[df["day"].isin(TRAIN_DAYS)]
test = df[df["day"].isin(TEST_DAYS)]
print("Train rows:", len(train), " Test rows:", len(test))
print("Train classes:\n", train[TARGET].value_counts().sort_index())
print("Test classes:\n", test[TARGET].value_counts().sort_index())

X_train, y_train = train[FEATURES], train[TARGET]
X_test, y_test = test[FEATURES], test[TARGET]

# ---- Baselines ----
print("\n=== Baseline 1: always predict empty (count task) ===")
print("Accuracy:", round(accuracy_score(y_test, [0] * len(y_test)), 4))

print("\n=== Baseline 2: PIR rule (occupied vs empty) ===")
y_test_bin = (y_test > 0).astype(int)
pir_pred = ((test["pir_1"] + test["pir_2"]) > 0).astype(int)
print(classification_report(y_test_bin, pir_pred,
                            target_names=["empty", "occupied"], zero_division=0))

# ---- Random forest ----
model = RandomForestClassifier(n_estimators=200, class_weight="balanced",
                               random_state=42, n_jobs=-1)
model.fit(X_train, y_train)
pred = model.predict(X_test)

print("\n=== Random forest: occupancy count 0-3 ===")
print("Accuracy:", round(accuracy_score(y_test, pred), 4))
print(classification_report(y_test, pred, zero_division=0))

print("=== Random forest as occupied vs empty ===")
print(classification_report(y_test_bin, (pred > 0).astype(int),
                            target_names=["empty", "occupied"], zero_division=0))

print("Feature importance:")
for name, imp in sorted(zip(FEATURES, model.feature_importances_),
                        key=lambda t: -t[1]):
    print(f"  {name}: {imp:.3f}")

ConfusionMatrixDisplay.from_predictions(y_test, pred)
plt.title("Occupancy count: confusion matrix (test days)")
plt.savefig("docs/confusion_matrix.png", dpi=150, bbox_inches="tight")
print("\nSaved docs/confusion_matrix.png")