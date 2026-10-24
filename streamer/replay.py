import argparse
import json
import time

import pandas as pd
import requests

DATA_PATH = "data/Occupancy_Estimation.csv"


def build_message(row):
    timestamp = pd.to_datetime(row["Date"] + " " + row["Time"]).isoformat()
    return {
        "timestamp": timestamp,
        "room_id": "classroom_1",
        "temperature": round(float(row[["S1_Temp", "S2_Temp", "S3_Temp", "S4_Temp"]].mean()), 2),
        "light": round(float(row[["S1_Light", "S2_Light", "S3_Light", "S4_Light"]].mean()), 2),
        "sound": round(float(row[["S1_Sound", "S2_Sound", "S3_Sound", "S4_Sound"]].mean()), 3),
        "co2": float(row["S5_CO2"]),
        "co2_slope": round(float(row["S5_CO2_Slope"]), 4),
        "pir_1": int(row["S6_PIR"]),
        "pir_2": int(row["S7_PIR"]),
        "true_occupancy": int(row["Room_Occupancy_Count"]),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=float, default=0.5, help="seconds between messages")
    parser.add_argument("--limit", type=int, default=20, help="number of rows to send")
    parser.add_argument("--post", type=str, default=None,
                        help="backend URL, e.g. http://127.0.0.1:8000/readings")
    args = parser.parse_args()

    df = pd.read_csv(DATA_PATH)
    for _, row in df.head(args.limit).iterrows():
        message = build_message(row)
        print(json.dumps(message))
        if args.post:
            response = requests.post(args.post, json=message, timeout=5)
            response.raise_for_status()
        time.sleep(args.delay)


if __name__ == "__main__":
    main()