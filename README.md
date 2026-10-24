# Digital Twin for Smart Classroom Energy and Occupancy Management

Major Project (Phase I onward), B.Tech Computer Science and Engineering
School of Computer Science and Engineering, IILM University, Greater Noida
Session 2026-27

**Guide:** Ms. Bhavana Shrivastava

## Team

| Name | Roll No. | Role |
|---|---|---|
| Richa Gupta | 2410031049 | Team lead, backend and integration |
| Priyanshu Kumar Tiwari | 2410031026 | ML (occupancy model) |
| Ritika Kumari | 2410031028 | 3D twin and frontend |
| Ankita Mandal | 2410031070 | Simulation and control |

## Overview

This project builds a Digital Twin of a university classroom that mirrors occupancy and environmental conditions in a virtual 3D model and uses occupancy-based control to reduce lighting and HVAC energy use.

Physical sensors are replaced by a dataset-driven virtual sensor layer. A streamer replays public dataset rows as if they were live sensor readings, and the rest of the pipeline treats them as real. All energy results come from simulation, not a live classroom.

## System Pipeline

Dataset replay streamer -> Backend (FastAPI + database) -> Occupancy ML model -> Control logic (simulation) -> 3D twin dashboard

## Repository Structure

```
smart-classroom-digital-twin-PT107/
├── data/          # raw datasets
├── streamer/      # replays dataset rows as virtual sensors
├── backend/       # FastAPI app and database
├── ml/            # occupancy model scripts and notebooks
├── twin/          # Blender model and Three.js dashboard
├── simulation/    # classroom timetable, control logic, energy model
├── docs/          # message format, architecture, screenshots
├── requirements.txt
└── README.md
```

## Setup

1. Clone the repository:
```
git clone https://github.com/richa-gupta16/smart-classroom-digital-twin-PT107.git
cd smart-classroom-digital-twin-PT107
```

2. Create and activate a virtual environment (Windows PowerShell):
```
python -m venv .venv
.venv\Scripts\Activate.ps1
```
On Mac/Linux use `source .venv/bin/activate`.

3. Install dependencies:
```
pip install -r requirements.txt
```

4. Place the dataset files in `data/` (see below), then run the exploration script:
```
python ml/explore_data.py
```

## Datasets and Citations

All datasets come from the UCI Machine Learning Repository. Check the license on each dataset page before reuse.

### 1. Room Occupancy Estimation (main dataset)
Temperature, light, sound, CO2 and PIR readings with a ground-truth head count (0-3).

```bibtex
@misc{room_occupancy_estimation_864,
  author       = {Singh, Adarsh Pal and Chaudhari, Sachin},
  title        = {{Room Occupancy Estimation}},
  year         = {2018},
  howpublished = {UCI Machine Learning Repository},
  note         = {{DOI}: https://doi.org/10.24432/C5P605}
}
```
License: [CC BY 4.0](https://creativecommons.org) (Verified from the UCI Machine Learning Repository)

### 2. Occupancy Detection
Temperature, humidity, light and CO2 readings with an occupied / not-occupied label.

Candanedo, L. (2016). *Occupancy Detection* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5X01N

```bibtex
@misc{occupancy_detection__357,
  author       = {Candanedo, Luis},
  title        = {{Occupancy Detection}},
  year         = {2016},
  howpublished = {UCI Machine Learning Repository},
  note         = {{DOI}: https://doi.org/10.24432/C5X01N}
}
```

License: [Public Domain (CC0)](https://creativecommons.org)

## Message Format

All modules exchange data in one JSON format. See [docs/message_format.md](docs/message_format.md).

## Project Status

- [x] Repository and folder structure
- [x] Dataset downloaded and explored
- [x] Message format defined
- [ ] Replay streamer
- [ ] Backend and database
- [ ] Occupancy ML model
- [ ] 3D twin dashboard
- [ ] Control logic and energy simulation
- [ ] Evaluation and documentation

## Git Workflow

- Do not work directly on `main`. Create your own branch, for example `git checkout -b ml-work`.
- Commit small and often with clear messages.
- Run `git pull` before `git push`.