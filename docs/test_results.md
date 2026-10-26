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

Script: `ml/train_baseline.py`.
 Model: random forest (200 trees, balanced class weights), 7 features from the message format (temperature, light, sound, CO2, CO2 slope, PIR 1, PIR 2). Timestamp and hour are not used as features.

Split by whole days, because adjacent 30 s readings are near-identical and a random split would leak information:
- Train: 22, 24, 25, 26 Dec 2017 (5,305 rows)
- Test: 23 Dec 2017, 10 Jan and 11 Jan 2018 (4,824 rows; classes 0/1/2/3 = 3,748 / 254 / 491 / 331)

Occupied vs. empty (test set):

| Method | Precision | Recall | F1 | Accuracy |
|---|---|---|---|---|
| PIR rule (either sensor = 1) | 0.98 | 0.56 | 0.72 | 0.90 |
| Random forest | 1.00 | 0.71 | 0.83 | 0.94 |

Occupancy count, 0 to 3 people (random forest): accuracy 0.893, macro F1 0.68. Always predicting "empty" gives 0.777.

| People | Precision | Recall | F1 |
|---|---|---|---|
| 0 | 0.92 | 1.00 | 0.96 |
| 1 | 0.82 | 0.44 | 0.57 |
| 2 | 0.82 | 0.66 | 0.73 |
| 3 | 0.54 | 0.39 | 0.45 |

Feature importance: light 0.392, CO2 0.232, temperature 0.188, CO2 slope 0.104, sound 0.055, PIR 2 0.025, PIR 1 0.004.

Evidence: `docs/confusion_matrix.png`

Limitations:
- About 29% of occupied readings are missed, so control logic needs a delay before switching off.
- Class "1 person" appears only on 2 dates and class "3" mostly on 3, so per-class scores are indicative.
- Only 22 Dec has occupied rows in training. The dataset is from a small room, not a classroom.
- Temperature has high importance and may reflect weather or season rather than occupancy. Checked in`ml/train_baseline.py`.

## 6. 3D twin and live synchronization

Status: **Pending.** Blender model and dashboard are in progress. Message-to-display latency has not been measured yet.

## 7. Energy simulation and comfort

Status: **Pending.** Baseline vs. occupancy-based control (kWh) and comfort compliance have not been measured yet. Results will be labeled as simulation results.