# OrbitSchedulers - IASTAM 6.0 Project 6
Dynamic Workload Allocation Between Space and Ground.

---

## Team A — Week 1

### M2 — Radiation Model (`src/env/radiation.py`)

Stochastic radiation failure model using an exponential distribution.

- Three failure modes: **SDC** (17 rad), **HBM** (44 rad), **SEFI** (5000 rad)
- Cumulative dose tracking (dose rate = 0.01 rad/s)
- Reproducible via fixed random seed

```python
from src.env.radiation import RadiationModel, FailureMode

model = RadiationModel(seed=42)
model.time_to_failure(17.0)   # random time to SDC event
model.add_exposure(100)       # cumulative_dose → 1.0 rad
```

---

### M3 — PSPLIB Parser (`src/env/psplib_loader.py`)

Parses PSPLIB J30 benchmark instances (semicolon/whitespace-separated `.sm` format).

Extracts:
- **PRECEDENCE RELATIONS** — converts successors → predecessor lists
- **REQUESTS/DURATIONS** — extracts duration and resource demands

Returns a **list of dictionaries** with keys: `id`, `duration`, `predecessors`, `resources`.

#### Usage — single instance

```python
from src.env.psplib_loader import load_psplib

tasks = load_psplib("data/j3010_1.sm")
# [
#     {"id": 1, "duration": 0, "predecessors": [], "resources": [0, 0, 0, 0]},
#     {"id": 2, "duration": 2, "predecessors": [1], "resources": [1, 2, 4, 0]},
#     ...
# ]
```

#### Usage — all 480 instances

```python
from src.env.psplib_loader import load_all_psplib

all_data = load_all_psplib("data")
# {"j3010_1.sm": [...], "j3010_2.sm": [...], ...}
```

#### Parsed output file

All 480 instances pre-parsed as JSON:

```
data/j30_all_parsed.json
```

---

## Project Structure

```
├── data/                      # 480 extracted PSPLIB J30 instances (.sm)
│   ├── j3010_1.sm             # Instance 1
│   ├── j3010_2.sm             # Instance 2
│   ├── ...                    # (480 total)
│   └── j30_all_parsed.json    # All instances parsed as JSON
│
├── src/
│   └── env/
│       ├── radiation.py       # M2 — Radiation failure model
│       └── psplib_loader.py   # M3 — PSPLIB parser
│
├── tests/
│   └── test_psplib_loader.py  # M3 tests (6 tests)
│
├── src/tests/
│   └── test_radiation.py      # M2 tests (4 tests)
│
├── requirements.txt
└── README.md
```

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run Tests

```bash
pytest tests/ -v              # M3 PSPLIB tests
pytest src/tests/ -v          # M2 Radiation tests
```