# OrbitSchedulers - IASTAM 6.0 Project 6
Dynamic Workload Allocation Between Space and Ground.

---

## Team A — Week 1

### M2 — Radiation Model (`src/env/radiation.py`)

Stochastic radiation failure model using an exponential distribution.

- Three failure modes: **SDC** (17 rad), **HBM** (44 rad), **SEFI** (5000 rad)
- Conditional model: `time_to_failure` accounts for accumulated dose
- Cumulative dose tracking (dose rate = 0.01 rad/s)
- `next_failure()` returns the earliest failure among all modes
- Reproducible via fixed random seed

```python
from src.env.radiation import RadiationModel, FailureMode

model = RadiationModel(seed=42)

# Time to failure (conditional on accumulated dose)
model.add_exposure(1000)       # 10 rad accumulated
model.time_to_failure(17.0)    # remaining 7 rad → mean ≈ 700 s

# Next failure among all modes
mode, time = model.next_failure()
```

---

### M3 — PSPLIB Parser (`src/env/psplib_loader.py`)

Parses PSPLIB J30 benchmark instances (semicolon/whitespace-separated `.sm` format).

Extracts:
- **PRECEDENCE RELATIONS** — converts successors → predecessor lists
- **REQUESTS/DURATIONS** — extracts duration and resource demands

Returns a **list of 30 dictionaries** (supersource/supersink excluded) with keys: `id`, `duration`, `predecessors`, `resources`.

#### Usage — single instance

```python
from src.env.psplib_loader import load_psplib

tasks = load_psplib("data/j3010_1.sm")
# [
#     {"id": 2, "duration": 2, "predecessors": [1], "resources": [1, 2, 4, 0]},
#     {"id": 3, "duration": 5, "predecessors": [1], "resources": [0, 5, 9, 10]},
#     ...
# ]
```

#### Usage — all 480 instances

```python
from src.env.psplib_loader import load_all_psplib

all_data = load_all_psplib("data")
# {"j3010_1.sm": [...], "j3010_2.sm": [...], ...}
```

#### Generate parsed JSON (not committed to Git)

```bash
python scripts/build_j30_json.py
# → data/j30_all_parsed.json
```

---

## Project Structure

```
├── data/                      # 480 PSPLIB J30 instances (.sm)
│   ├── j3010_1.sm
│   ├── j3010_2.sm
│   └── ...                    # (480 total)
│
├── src/
│   └── env/
│       ├── radiation.py       # M2 — Radiation failure model
│       └── psplib_loader.py   # M3 — PSPLIB parser
│
├── tests/
│   ├── test_radiation.py      # M2 tests (9 tests)
│   └── test_psplib_loader.py  # M3 tests (10 tests)
│
├── scripts/
│   └── build_j30_json.py     # Generate j30_all_parsed.json
│
├── docs/
│   └── explanation.md         # Technical explanation
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
pytest tests/ -v
```
Dynamic Workload Allocation Between Space and Ground.x