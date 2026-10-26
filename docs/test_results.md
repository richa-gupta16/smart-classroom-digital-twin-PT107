# Test Results

Results recorded so far for the Digital Twin for Smart Classroom Energy and Occupancy Management project. All tests ran on a local laptop (Windows, Python virtual environment `.venv`), with the streamer and backend on the same machine.

Last updated: 24-10-2026

## 1. Dataset exploration

Script: `ml/explore_data.py`
Dataset: UCI Room Occupancy Estimation (`data/Occupancy_Estimation.csv`)

| Item | Result |
|---|---|
| Rows x columns | 10,129 x 19 |
| Missing values | 0 in all columns |
| First reading | 2017/12/22 10:49:41 |
| Last reading | 2018/01/11 09:00:09 |
| Sampling interval | about 30 seconds |

Class distribution of `Room_Occupancy_Count`:

| People in room | Rows | Share |
|---|---|---|
| 0 | 8,228 | 81.2% |
| 1 | 459 | 4.5% |
| 2 | 748 | 7.4% |
| 3 | 694 | 6.9% |

Observation: the classes are heavily imbalanced. A model that always predicts "empty" would reach about 81% accuracy, so model evaluation must use precision, recall, F1 and a confusion matrix, not accuracy alone.

Time structure (`ml/check_time.py`):
- 7 distinct dates in three recording blocks (22-24 Dec, 25-26 Dec, 10-11 Jan), separated by gaps of 1 day and 15 days.
- Within a block, readings are continuous at 30-31 s intervals (9,987 of 10,129 gaps).
- Occupied periods exist only on 22 Dec, 23 Dec and 10 Jan. Class "1 person" appears only on 22 and 23 Dec.
- Because adjacent readings are near-identical, a random split would leak information, so train and test are split by whole days.

## 2. Replay streamer

Script: `streamer/replay.py`

| Test | Result |
|---|---|
| First 10 rows printed as JSON | Passed. Every message contains exactly the fields in `docs/message_format.md`. |
| Timestamp spacing | About 30 seconds between messages, as in the dataset |

Observation (small sample, first 10 rows): the true occupancy was 1 in all 10 rows, but the PIR sensors fired in only 2 of them. This shows that PIR alone can miss people who are sitting still, which supports using a model that combines CO2, sound, light and temperature.

## 3. Backend functional test

Backend: FastAPI + SQLite (`backend/main.py`)

| Test | Result |
|---|---|
| 50 messages sent with `--post` | 50 rows stored |
| `GET /readings?limit=50` | Returned 50 items, HTTP 200 |
| `GET /readings/latest` | Returned the 50th message with its timestamp, HTTP 200 |

Evidence: `docs/backend_test_readings.png`, `docs/backend_test_latest.png`

## 4. Full-dataset stress test

Command:

```
Measure-Command { python streamer/replay.py --limit 10129 --delay 0 --post http://127.0.0.1:8000/readings | Out-Null }
```

| Metric | Result |
|---|---|
| Readings sent | 10,129 |
| Readings stored (SQL row count) | 10,129 |
| Data loss | 0% |
| Failed requests | 0 (every request returned `200 OK`) |
| Total time | 293.13 s (4 min 53 s) |
| Throughput | about 34.6 readings per second |
| Average time per reading | about 28.9 ms (HTTP request + database write) |

Conditions and limits:
- Streamer and server ran on the same machine, so there was no network latency.
- Each message was a separate HTTP request with its own database connection. Throughput could be higher with batching or a persistent connection.
- The real dataset interval is 30 s per reading, so the pipeline is much faster than a live feed would require.

## 5. Occupancy ML model

Status: **Pending.** Train/test split, model training and evaluation have not been done yet.

To be recorded: accuracy, per-class precision/recall/F1, confusion matrix, and comparison with a PIR-only baseline.

## 6. 3D twin and live synchronization

Status: **Pending.** Blender model and dashboard are in progress. Message-to-display latency has not been measured yet.

## 7. Energy simulation and comfort

Status: **Pending.** Baseline vs. occupancy-based control (kWh) and comfort compliance have not been measured yet. Results will be labeled as simulation results.