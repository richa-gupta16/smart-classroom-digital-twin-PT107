import sqlite3

from fastapi import FastAPI
from pydantic import BaseModel

DB_PATH = "backend/twin.db"

app = FastAPI(title="Classroom Digital Twin API")


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
            true_occupancy INTEGER
        )
        """
    )
    return conn


@app.post("/readings")
def add_reading(reading: Reading):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO readings
        (timestamp, room_id, temperature, light, sound, co2, co2_slope, pir_1, pir_2, true_occupancy)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            reading.timestamp, reading.room_id, reading.temperature, reading.light,
            reading.sound, reading.co2, reading.co2_slope, reading.pir_1,
            reading.pir_2, reading.true_occupancy,
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "stored"}


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