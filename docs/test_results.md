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

### Feature experiments (`ml/train_v2.py`)

Same train/test split. Variant A: 7 base features. Variant B: A plus rolling means over the previous 10 readings (about 5 min, past data only) of PIR, sound, CO2 and light. Variant C: B without temperature.

| Variant | Count acc. | Count macro F1 | Occupied precision | Occupied recall | Occupied F1 |
|---|---|---|---|---|---|
| A | 0.893 | 0.679 | 0.997 | 0.713 | 0.831 |
| B | 0.885 | 0.675 | 0.992 | 0.775 | 0.870 |
| C | 0.892 | 0.703 | 0.991 | 0.778 | 0.871 |

Per-day occupied recall:

| Test day | Occupied rows | A | B | C |
|---|---|---|---|---|
| 23 Dec 2017 | 782 | 0.811 | 0.926 | 0.930 |
| 10 Jan 2018 | 294 | 0.452 | 0.374 | 0.374 |

Findings:
- Rolling features improve overall occupied recall (0.713 to 0.775), and removing temperature has no meaningful effect, so variant C is used.
- The overall improvement comes from 23 Dec. On 10 Jan, recall falls, so the model generalizes poorly to a day recorded 3 weeks after the training days.
- 23 Dec supplies 782 of the 1,076 occupied test rows, so overall figures are dominated by one day.

### Leave-one-occupied-day-out evaluation (`ml/train_cv.py`)

Each of the three days with people was held out in turn and the model (variant C features) was trained on all other days.

| Held-out day | Occupied rows | Occupied precision | Occupied recall | Occupied F1 | Count acc. | Count macro F1 |
|---|---|---|---|---|---|---|
| 22 Dec 2017 | 825 | 0.977 | 0.979 | 0.978 | 0.863 | 0.841 |
| 23 Dec 2017 | 782 | 0.971 | 0.978 | 0.975 | 0.925 | 0.808 |
| 10 Jan 2018 | 294 | 1.000 | 0.374 | 0.545 | 0.757 | 0.518 |
| Mean of folds | | 0.983 | 0.777 | 0.833 | 0.848 | 0.722 |

Findings:
- Occupied recall is about 0.98 on 22 and 23 Dec but 0.374 on 10 Jan, so performance on a day recorded 3 weeks later is much worse. The mean hides this spread.
- On 10 Jan, precision is 1.000: the model never predicts people in an empty room, but misses most occupied readings.
- Mean sensor values on occupied rows: light 120.8 (22 Dec), 96.3 (23 Dec), 58.7 (10 Jan); sound 0.50, 0.42, 0.30; CO2 775.8, 655.0, 639.6 ppm. Light was the most important feature in the model, and it is about half as bright on 10 Jan. This is a likely explanation, not a proven cause.
- Only three days contain people, so these estimates are uncertain. The dataset is from a small room, not a classroom.

Consequence for control: the model errs towards "empty". The control logic therefore uses a hold-off delay before switching off and a PIR override (any PIR trigger counts as occupied).

The final model (`ml/save_model.py`) is trained on all 7 days, so it has no held-out test set; the table above is the performance estimate.

## 6. 3D twin and live synchronization

Status: working prototype. The room is built from Three.js primitives (a Blender model is not yet integrated).

Pipeline tested end-to-end: replay streamer -> FastAPI backend (random forest predicts occupancy per reading) -> SQLite -> browser dashboard polling `/readings/latest` every 300 ms.

Dashboard behaviour observed:
- Empty room: predicted 0, lights and AC shown OFF.
- Occupied room: capsules appear for the predicted count (1, 2, 3 people), lights and AC shown ON.
- Panel shows time, temperature, light, CO2, PIR values, predicted vs. actual count, and update delay.

Update delay (server stores reading -> dashboard shows it), replay of 22 Dec 2017 at 0.5 s per message:

| Metric | Result |
|---|---|
| Readings measured | 429 (at time of screenshot) |
| Average delay | 221 ms |
| Maximum delay | 752 ms |

The delay includes the dashboard's own 300 ms polling interval, so true processing delay is lower.

Limits:
- The demo replays 22 Dec, which is in the model's training data, so predicted-vs-actual agreement on the dashboard is not a performance measure. Model performance is reported in section 5.
- Lights and AC currently follow a placeholder rule (on whenever the prediction is occupied). The hold-off delay and PIR override are not yet implemented.
- Delay was measured on one machine with the server and browser running locally.

Evidence: `docs/dashboard_empty.png`, `docs/dashboard_one_person.png`, `docs/dashboard_two_people.png`, demo video (Drive link in the form).

## 7. Energy simulation

Script: `simulation/energy_sim.py`. This is a simulation on 87.4 hours of recorded data (7 dates) from the UCI Room Occupancy Estimation dataset, not a measured classroom.

Assumptions (sources in `docs/energy_assumptions.md`): 4 light fixtures x 36 W; AC at 0.53 kW average input while running; combined 0.674 kW. Lights and AC switch together on one on/off signal; no thermal model.

Occupancy predictions for each day come from a model trained on the other six days. A PIR trigger always counts as occupied. Hold-off = minutes without detection before switching off.

| Strategy | Hours on | kWh | Saving vs. fixed schedule | Occupied time with lights off |
|---|---|---|---|---|
| Always on | 87.4 | 58.88 | -177.7% | 0.0% |
| Fixed 08:00-18:00 | 31.5 | 21.20 | 0.0% | 21.0% |
| Lecture timetable | 8.7 | 5.86 | 72.4% | 84.4% |
| PIR only, hold 10 min | 18.6 | 12.57 | 40.7% | 0.3% |
| Model only, hold 10 min | 17.2 | 11.60 | 45.3% | 9.8% |
| Model + PIR override, hold 10 min | 19.8 | 13.32 | 37.2% | 0.0% |
| Perfect knowledge (upper bound), hold 10 min | 17.2 | 11.59 | 45.3% | 0.0% |

Hold-off sweep, model + PIR override:

| Hold-off | Hours on | kWh | Occupied time with lights off | Saving vs. fixed |
|---|---|---|---|---|
| 5 min | 18.4 | 12.42 | 0.0% | 41.4% |
| 10 min | 19.8 | 13.32 | 0.0% | 37.2% |
| 15 min | 20.9 | 14.10 | 0.0% | 33.5% |
| 30 min | 24.0 | 16.20 | 0.0% | 23.6% |

Short hold-off sweep, PIR only vs. model + PIR override:

| Hold-off | PIR only: hours on | kWh | Occupied time dark | Saving vs. fixed | Model + PIR: hours on | kWh | Occupied time dark | Saving vs. fixed |
|---|---|---|---|---|---|---|---|---|
| 1 min | 12.7 | 8.57 | 24.5% | 59.6% | 17.0 | 11.44 | 2.0% | 46.0% |
| 2 min | 15.0 | 10.09 | 12.0% | 52.4% | 17.5 | 11.77 | 0.8% | 44.5% |
| 3 min | 16.1 | 10.86 | 6.3% | 48.8% | 17.8 | 12.01 | 0.3% | 43.3% |
| 5 min | 17.3 | 11.69 | 1.5% | 44.9% | 18.4 | 12.42 | 0.0% | 41.4% |
| 10 min | 18.6 | 12.57 | 0.3% | 40.7% | 19.8 | 13.32 | 0.0% | 37.2% |

Findings:
- Occupancy-based control used 37-45% less energy than the fixed 08:00-18:00 schedule in this simulation, while the fixed schedule left 21% of occupied time without lights and the lecture timetable left 84%, because the room was used outside those hours.
- The occupancy model alone saved 45.3% but left people without lights 9.8% of the time (the model misses most occupied readings on 10 Jan). Adding the PIR override reduced this to 0.0% at a cost of 8 percentage points of savings.
- - At a 10-minute hold-off, PIR alone (40.7% saving, 0.3% of occupied time dark) was close to model + PIR (37.2%, 0.0%). The model's advantage appears at shorter hold-offs: model + PIR with a 3-minute hold-off left 0.3% of occupied time dark and saved 43.3% (12.01 kWh), against 40.7% (12.57 kWh) for PIR alone at 10 minutes, about 4.5% less energy at the same comfort level. PIR alone with 1-2 minute hold-offs saved 52-60% but left 12-25% of occupied time dark.
- The gain is modest (about 1-3 percentage points at matched comfort). Hold-off values were examined on the same data used to evaluate them, and only three days contain people, so this is indicative, not conclusive.
- Longer hold-offs cost energy without improving comfort here: 5 min saved 41.4%, 30 min saved 23.6%.
- Percentage savings do not depend on the power values, because lights and AC switch together; only absolute kWh do.

Limits:
- Only 87.4 hours of data from a small room (3 dates with people), recorded in December and January. The room is empty about 81% of the time.
- Savings depend on the chosen baseline. Savings against "always on" (77-80%) are inflated by night-time hours and are not used as the headline.
- AC is modelled as constant average power; temperature comfort is not simulated.
- In a real room, switching lights off would change the light sensor value that the model depends on. This feedback is not simulated.
- The "off events while occupied" count only registers switch-offs that happen while someone is present, so it understates time spent in the dark; occupied-time-with-lights-off is the comfort measure.