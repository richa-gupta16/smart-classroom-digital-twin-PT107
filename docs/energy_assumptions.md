# Energy Assumptions

These values are used by `simulation/energy_sim.py`. The results are a simulation on dataset replay, not measurements from a real classroom.

## 1. Equipment power

| Item | Value | Source (product name, page or datasheet link, date accessed) |
|---|---|---|
| Number of light fixtures | 4 | Matches the fixtures in the 3D twin model (`twin/dashboard/index.html`) |

| Power per light fixture | 36 W | Philips Essential Full Glow 2x2 Recessed LED Panel (Model: RC360B LED36S), [Jainsons Lights](https://jainsonslightsonline.com/products/philips-essential-full-glow-2x2-panel-36w-rc360b-led36s), accessed 28-10-2026 |


| Split AC average electrical input while running | 0.53 kW | Carrier CAI18CE3R36W0 1.5 Ton 3 Star Inverter Split AC. BEE label annual consumption 854.39 kWh / 1,600 h assumed by the label = 0.534 kW. <link to the page where you saw 854.39>, accessed 28-10-2026 |

How the combined power is calculated in the script:

combined power (kW) = (4 x power per fixture in W) / 1000 + AC input power in kW

Example of the formula only (not our values): 4 fixtures of 20 W and an AC drawing 1.2 kW would give 0.08 + 1.2 = 1.28 kW.

## 2. Control strategies compared

| Strategy | Definition |
|---|---|
| Always on | Lights and AC on for the whole recorded time (upper reference) |
| Fixed schedule | On from 08:00 to 18:00 every day, whether or not anyone is present (assumed typical practice) |
| Lecture timetable | On only in scheduled lecture slots on weekdays (`simulation/timetable.py`: 09-12 and 14-16) |
| PIR only | On when either PIR sensor fires, off after the hold-off time |
| Model only | On when the occupancy model predicts at least 1 person, off after the hold-off time |
| Model + PIR override | On when the model predicts occupied or any PIR fires, off after the hold-off time |
| Perfect knowledge | Uses the true head count. Shows the best any detector could do (upper bound) |

Hold-off time: 10 minutes in the main comparison. 5, 10, 15 and 30 minutes in the sweep.

## 3. Modelling simplifications

- Lights and AC are switched together by one on/off signal.
- The AC is modelled at constant average input power while on. There is no thermal model, no compressor cycling and no pre-cooling. Energy for the AC is therefore only an approximation.
- Only electrical energy (kWh) is counted. Cost and carbon emissions are not calculated.
- Comfort is measured as the share of occupied time with lights off. Temperature comfort is not simulated.
- Readings are weighted by the time between them (capped at 60 s), so gaps in the data do not count as time.

## 4. Data used

- UCI Room Occupancy Estimation dataset: 10,129 readings over 7 dates (22 Dec 2017 to 11 Jan 2018), about 30 s apart.
- A small room, not a classroom. People are present on only 3 of the 7 dates, and about 81% of readings have no one in the room.
- Occupancy predictions for each day come from a model trained on the other six days.

## 5. Known limits

- Savings depend on the chosen baseline, and on this dataset being empty most of the time. They should not be generalised to other classrooms.
- In a real room, switching the lights off would change the light sensor reading, which is the model's most important input. This feedback is not simulated.
- Power values come from specific products and vary by model, age and settings.