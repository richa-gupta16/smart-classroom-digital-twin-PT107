import os

os.environ["DATABASE_URL"] = "sqlite:///test_twin.db"   # set before importing the app

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

SAMPLE = {
    "timestamp": "2017-12-22T10:49:41",
    "room_id": "classroom_1",
    "temperature": 24.91,
    "light": 62.0,
    "sound": 0.098,
    "co2": 390.0,
    "co2_slope": 0.7692,
    "pir_1": 0,
    "pir_2": 0,
    "true_occupancy": 1,
}


def test_health_reports_database_and_model():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["database"] is True
    assert body["model_loaded"] is True


def test_post_reading_returns_prediction():
    r = client.post("/readings", json=SAMPLE)
    assert r.status_code == 200
    assert r.json()["status"] == "stored"
    assert r.json()["predicted_occupancy"] in (0, 1, 2, 3)


def test_latest_returns_stored_reading():
    client.post("/readings", json=SAMPLE)
    r = client.get("/readings/latest")
    assert r.status_code == 200
    assert r.json()["room_id"] == "classroom_1"


def test_list_respects_limit():
    for _ in range(3):
        client.post("/readings", json=SAMPLE)
    r = client.get("/readings?limit=2")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_missing_field_is_rejected():
    bad = dict(SAMPLE)
    del bad["co2"]
    assert client.post("/readings", json=bad).status_code == 422