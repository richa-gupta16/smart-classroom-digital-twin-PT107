import sqlite3
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

DB_PATH = "backend/twin.db"
MODEL_PATH = "ml/occupancy_model.joblib"
WINDOW = 10          # previous 10 readings (about 5 minutes), same as ml/features.py
GAP_SECONDS = 300    # a gap over 5 minutes starts a new block, same as training

app = FastAPI(title="Classroom Digital Twin API")

bundle = joblib.load(MODEL_PATH) if Path(MODEL_PATH).exists() else None
if bundle is None:
    print("WARNING: model file not found. Run: python ml/save_model.py")

history = {}   # room_id -> last readings
last_ts = {}   # room_id -> last timestamp


class Reading(BaseModel):
    timestamp: str
    room_id: str
    temperature: float
    light: float
    sound: float
    co2: float
    co2_slope: float
    pir_1: int
    pir_2: int
    true_occupancy: int


def predict_occupancy(r: Reading):
    if bundle is None:
        return None
    ts = datetime.fromisoformat(r.timestamp)
    prev = last_ts.get(r.room_id)
    if prev is None or abs((ts - prev).total_seconds()) > GAP_SECONDS:
        history[r.room_id] = deque(maxlen=WINDOW)
    last_ts[r.room_id] = ts

    h = history[r.room_id]
    h.append({
        "pir_any": 1 if (r.pir_1 + r.pir_2) > 0 else 0,
        "sound": r.sound, "co2": r.co2, "light": r.light,
    })
    n = len(h)
    features = {
        "light": r.light, "sound": r.sound, "co2": r.co2, "co2_slope": r.co2_slope,
        "pir_1": r.pir_1, "pir_2": r.pir_2,
        "pir_any_roll": sum(x["pir_any"] for x in h) / n,
        "sound_roll": sum(x["sound"] for x in h) / n,
        "co2_roll": sum(x["co2"] for x in h) / n,
        "light_roll": sum(x["light"] for x in h) / n,
    }
    X = pd.DataFrame([features])[bundle["features"]]
    return int(bundle["model"].predict(X)[0])


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            room_id TEXT,
            temperature REAL,
            light REAL,
            sound REAL,
            co2 REAL,
            co2_slope REAL,
            pir_1 INTEGER,
            pir_2 INTEGER,
            true_occupancy INTEGER,
            predicted_occupancy INTEGER,
            received_ms INTEGER
        )
        """
    )
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(readings)")}
    for col in ("predicted_occupancy", "received_ms"):
        if col not in existing:
            conn.execute(f"ALTER TABLE readings ADD COLUMN {col} INTEGER")
    return conn


@app.post("/readings")
def add_reading(reading: Reading):
    predicted = predict_occupancy(reading)
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO readings
        (timestamp, room_id, temperature, light, sound, co2, co2_slope,
         pir_1, pir_2, true_occupancy, predicted_occupancy, received_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            reading.timestamp, reading.room_id, reading.temperature, reading.light,
            reading.sound, reading.co2, reading.co2_slope, reading.pir_1,
            reading.pir_2, reading.true_occupancy, predicted, int(time.time() * 1000),
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "stored", "predicted_occupancy": predicted}


@app.get("/readings/latest")
def latest_reading():
    conn = get_conn()
    row = conn.execute("SELECT * FROM readings ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else {"message": "no data yet"}


@app.get("/readings")
def list_readings(limit: int = 20):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM readings ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Serves the 3D dashboard at http://127.0.0.1:8000/dashboard/
app.mount("/dashboard", StaticFiles(directory="twin/dashboard", html=True), name="dashboard")