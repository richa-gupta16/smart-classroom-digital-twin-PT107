import os
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine, text

MODEL_PATH = os.getenv("MODEL_PATH", "ml/occupancy_model.joblib")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///backend/twin.db")
for prefix in ("postgres://", "postgresql://"):
    if DATABASE_URL.startswith(prefix):
        DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len(prefix):]
        break

WINDOW = 10          # previous 10 readings (about 5 minutes), same as ml/features.py
GAP_SECONDS = 300    # a gap over 5 minutes starts a new block, same as training

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
IS_SQLITE = engine.url.get_backend_name() == "sqlite"

app = FastAPI(title="Classroom Digital Twin API")

bundle = joblib.load(MODEL_PATH) if Path(MODEL_PATH).exists() else None
if bundle is None:
    print("WARNING: model file not found. Run: python ml/save_model.py")

history = {}   # room_id -> last readings
last_ts = {}   # room_id -> last timestamp
_db_ready = False


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


def ensure_db():
    global _db_ready
    if _db_ready:
        return
    if IS_SQLITE and engine.url.database:
        os.makedirs(os.path.dirname(engine.url.database) or ".", exist_ok=True)
    id_col = "INTEGER PRIMARY KEY AUTOINCREMENT" if IS_SQLITE else "SERIAL PRIMARY KEY"
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS readings (
                id {id_col},
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
                received_ms BIGINT
            )
        """))
    _db_ready = True


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


@app.post("/readings")
def add_reading(reading: Reading):
    ensure_db()
    predicted = predict_occupancy(reading)
    params = reading.model_dump()
    params["predicted_occupancy"] = predicted
    params["received_ms"] = int(time.time() * 1000)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO readings
            (timestamp, room_id, temperature, light, sound, co2, co2_slope,
             pir_1, pir_2, true_occupancy, predicted_occupancy, received_ms)
            VALUES
            (:timestamp, :room_id, :temperature, :light, :sound, :co2, :co2_slope,
             :pir_1, :pir_2, :true_occupancy, :predicted_occupancy, :received_ms)
        """), params)
    return {"status": "stored", "predicted_occupancy": predicted}


@app.get("/readings/latest")
def latest_reading():
    ensure_db()
    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM readings ORDER BY id DESC LIMIT 1")).mappings().first()
    return dict(row) if row else {"message": "no data yet"}


@app.get("/readings")
def list_readings(limit: int = 20):
    ensure_db()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM readings ORDER BY id DESC LIMIT :limit"),
                            {"limit": limit}).mappings().all()
    return [dict(r) for r in rows]


@app.get("/health")
def health():
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded",
            "model_loaded": bundle is not None, "database": db_ok}


# Serves the 3D dashboard at /dashboard/
app.mount("/dashboard", StaticFiles(directory="twin/dashboard", html=True), name="dashboard")