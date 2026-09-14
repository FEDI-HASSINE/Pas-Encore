# Team A — Week 1 Technical Guide
## Dynamic Workload Allocation Between Space and Ground
### M2 — Radiation Model & M3 — PSPLIB Parser

> **Purpose:** One complete Week 1 study and implementation guide for Team A. It explains the technical concepts, objectives, architecture, code, tests, Git workflow, acceptance criteria, and the connection between M2 and M3.

---

# 1. Project context

The project studies **dynamic allocation of computational tasks between space and ground**.

The simulated infrastructure contains heterogeneous computing locations such as:

- `LEO-1` — orbital satellite
- `LEO-2` — orbital satellite
- `GS-Tunisia` — ground station
- `Cloud-AWS` — terrestrial cloud

A task arrives, and the future scheduler must decide where it should execute.

The problem is dynamic because the system state changes over time:

- CPU usage changes.
- Energy availability changes.
- Communication links can disappear.
- Radiation can cause failures.
- Tasks arrive with different workload characteristics.
- Some tasks can have precedence/dependency constraints.

For **Week 1**, Team A is responsible for two reusable environment/data components:

| Member | Responsibility | Main file |
|---|---|---|
| **M2** | Radiation Model | `src/env/radiation.py` |
| **M3** | PSPLIB Parser | `src/env/psplib_loader.py` |

The roadmap defines these tasks and their acceptance criteria.

---

# 2. Week 1 objective

By the end of Week 1, Team A should have two clean, tested components.

## M2 output

A radiation model that:

1. Uses an exponential failure-time model.
2. Supports three radiation effects:
   - SDC — 17 rad
   - HBM — 44 rad
   - SEFI — 5000 rad
3. Tracks cumulative radiation dose.
4. Supports a fixed random seed for reproducibility.
5. Passes a statistical sanity test.

## M3 output

A PSPLIB loader that:

1. Reads the selected `.sm` benchmark file.
2. Parses task precedence information.
3. Converts successors into predecessor lists.
4. Parses durations.
5. Parses resource requirements.
6. Returns task dictionaries with:
   - `id`
   - `duration`
   - `predecessors`
   - `resources`
7. Passes the project acceptance checks.

---

# 3. Team architecture

The Week 1 relationship is:

```text
                         TEAM A
              ┌─────────────────────────┐
              │                         │
              │ M2: Radiation           │
              │ src/env/radiation.py    │
              │                         │
              └────────────┬────────────┘
                           │
                     used later by
                           │
                           ▼
              ┌─────────────────────────┐
              │ M3: Task Generator      │
              │ task_generator.py        │
              └─────────────────────────┘


              ┌─────────────────────────┐
              │ M3: PSPLIB Parser       │
              │ psplib_loader.py        │
              └────────────┬────────────┘
                           │
                           ▼
                   Task definitions
                           │
                           ▼
                    Task / scheduler
```

The two components are initially independent, but both eventually feed the simulation environment.

---

# 4. M2 — Radiation Model

## 4.1 Why do we need it?

A satellite computing system should not model failures only as arbitrary random events such as:

```python
if random() < 0.1:
    node.fail()
```

That produces a generic random failure.

The project instead wants a simplified **radiation-driven stochastic failure model**.

The roadmap defines three radiation effects:

| Failure mode | Characteristic dose | Intended effect |
|---|---:|---|
| SDC | 17 rad | Corrupt the computation/result |
| HBM | 44 rad | Reboot the node |
| SEFI | 5000 rad | Destroy the node |

The purpose is to replace arbitrary failure generation with a reproducible stochastic model based on the project's radiation assumptions.

---

# 5. Radiation concepts you need to understand

## 5.1 Radiation dose

A radiation dose represents an amount of deposited ionizing radiation.

For this project, dose increases with exposure time using the simplified assumption:

```text
dose rate = 0.01 rad / second
```

Therefore:

```text
dose = exposure_time × 0.01
```

Examples:

```text
100 s   → 1 rad
500 s   → 5 rad
1000 s  → 10 rad
```

This is a project-level modeling assumption, not a full physical spacecraft radiation model.

---

# 6. Exponential distribution

The roadmap requires:

```python
np.random.exponential(
    scale=characteristic_dose / 0.01
)
```

This is the central technical idea of M2.

For an exponential distribution:

```text
mean = scale
```

Therefore:

```text
scale = characteristic_dose / 0.01
```

## SDC

```text
17 / 0.01 = 1700 seconds
```

So:

```python
time_to_failure(17.0)
```

has an expected value of about:

```text
1700 seconds
```

## HBM

```text
44 / 0.01 = 4400 seconds
```

## SEFI

```text
5000 / 0.01 = 500000 seconds
```

### Important

A single call is **not** expected to return exactly `1700`.

For example, valid samples could be:

```text
100
500
1200
2400
4000
```

The mean over many samples approaches the theoretical mean.

---

# 7. Why exponential distribution?

For this project, exponential sampling provides a simple model for a random waiting time until a radiation event.

Conceptually:

```text
Radiation environment
        │
        ▼
 Stochastic event process
        │
        ▼
 Time until event
        │
        ▼
 Failure mode
        │
        ├── SDC
        ├── HBM
        └── SEFI
```

This allows the simulator to generate random but reproducible failure events instead of hardcoding something like:

```text
node fails at t = 500 s
```

Later, those events can stress resilient scheduling.

---

# 8. Random seeds and reproducibility

Scientific experiments need to be repeatable.

Without a fixed seed:

```python
np.random.exponential(...)
```

can produce different sequences every run.

With:

```python
rng = np.random.default_rng(42)
```

the pseudorandom sequence can be reproduced.

This matters because the project will later compare strategies statistically. If every experiment uses completely different random events, differences between strategies become harder to interpret.

---

# 9. M2 implementation

Create:

```text
src/
└── env/
    └── radiation.py
```

Recommended implementation:

```python
from __future__ import annotations

from enum import Enum
import numpy as np


class FailureMode(str, Enum):
    SDC = "SDC"
    HBM = "HBM"
    SEFI = "SEFI"


class RadiationModel:
    """
    Simplified stochastic radiation model used by the project.

    Project assumptions:
        dose rate = 0.01 rad/s

        SDC = 17 rad
        HBM = 44 rad
        SEFI = 5000 rad
    """

    DOSE_RATE = 0.01

    CHARACTERISTIC_DOSES = {
        FailureMode.SDC: 17.0,
        FailureMode.HBM: 44.0,
        FailureMode.SEFI: 5000.0,
    }

    def __init__(self, seed: int | None = None):
        self.rng = np.random.default_rng(seed)
        self.cumulative_dose = 0.0

    def time_to_failure(self, characteristic_dose: float) -> float:
        """
        Return a random time until a radiation event.

        The project requires:
            scale = characteristic_dose / 0.01
        """
        if characteristic_dose <= 0:
            raise ValueError("characteristic_dose must be > 0")

        scale = characteristic_dose / self.DOSE_RATE

        return float(self.rng.exponential(scale=scale))

    def add_exposure(self, seconds: float) -> float:
        """
        Increase cumulative radiation dose:

            dose += seconds * 0.01
        """
        if seconds < 0:
            raise ValueError("seconds must be >= 0")

        self.cumulative_dose += seconds * self.DOSE_RATE
        return self.cumulative_dose

    def reset(self) -> None:
        """Reset cumulative dose."""
        self.cumulative_dose = 0.0

    @staticmethod
    def characteristic_dose(mode: FailureMode) -> float:
        return RadiationModel.CHARACTERISTIC_DOSES[mode]
```

---

# 10. M2 example

```python
from src.env.radiation import RadiationModel, FailureMode


model = RadiationModel(seed=42)

sdc_time = model.time_to_failure(17.0)
hbm_time = model.time_to_failure(44.0)
sefi_time = model.time_to_failure(5000.0)

print("SDC failure time:", sdc_time)
print("HBM failure time:", hbm_time)
print("SEFI failure time:", sefi_time)

model.add_exposure(100)

print("Cumulative dose:", model.cumulative_dose)
```

After `100` seconds of exposure:

```text
cumulative_dose = 1.0 rad
```

---

# 11. M2 tests

Create:

```text
tests/test_radiation.py
```

```python
import numpy as np

from src.env.radiation import (
    RadiationModel,
    FailureMode,
)


def test_sdc_mean():
    model = RadiationModel(seed=42)

    samples = [
        model.time_to_failure(17.0)
        for _ in range(10_000)
    ]

    mean = np.mean(samples)

    print("Observed SDC mean:", mean)

    # The theoretical mean is 1700 s.
    assert 1500 < mean < 1900


def test_characteristic_doses():
    assert RadiationModel.characteristic_dose(FailureMode.SDC) == 17.0
    assert RadiationModel.characteristic_dose(FailureMode.HBM) == 44.0
    assert RadiationModel.characteristic_dose(FailureMode.SEFI) == 5000.0


def test_cumulative_dose():
    model = RadiationModel(seed=42)

    model.add_exposure(100)
    assert model.cumulative_dose == 1.0

    model.add_exposure(200)
    assert model.cumulative_dose == 3.0


def test_reset():
    model = RadiationModel(seed=42)

    model.add_exposure(100)
    model.reset()

    assert model.cumulative_dose == 0.0
```

Run:

```bash
pytest tests/test_radiation.py -v
```

---

# 12. What M2 should NOT build in Week 1

Do not turn this into a complete radiation-physics simulator.

The Week 1 task does not require modeling:

- particle spectra
- detailed spacecraft shielding
- particle transport
- semiconductor radiation transport
- real hardware telemetry

The immediate requirement is the specified exponential model, the three characteristic doses, cumulative dose, and reproducibility.

The detailed operational effects of SDC/HBM/SEFI can be connected to node/task behavior later.

---

# 13. M3 — PSPLIB Parser

## 13.1 What is PSPLIB?

PSPLIB means:

> **Project Scheduling Problem Library**

It is a benchmark collection for project scheduling problems.

This project uses PSPLIB because realistic scheduling problems contain more than independent tasks. They can include:

- task durations
- resource requirements
- precedence relationships

This gives the project a structured scheduling benchmark.

---

# 14. Why PSPLIB matters

A scheduler eventually needs to answer two separate questions.

### Question 1

```text
Where should the task execute?
```

For example:

```text
LEO-1
LEO-2
GS-Tunisia
Cloud-AWS
```

### Question 2

```text
Can the task start now?
```

Suppose:

```text
Task 1 ─────┐
            ├──> Task 5
Task 2 ─────┘
```

Then task 5 cannot start until tasks 1 and 2 satisfy their precedence constraints.

PSPLIB gives these relationships in a standard benchmark format.

---

# 15. Output required from M3

The parser should return:

```python
[
    {
        "id": 1,
        "duration": 0,
        "predecessors": [],
        "resources": [0, 0, 0, 0],
    },
    {
        "id": 2,
        "duration": 8,
        "predecessors": [1],
        "resources": [4, 0, 0, 0],
    },
]
```

The roadmap explicitly specifies the keys:

```text
id
duration
predecessors
resources
```

This structure is an intermediate representation between the raw benchmark file and the later scheduler.

---

# 16. The most important PSPLIB idea: successors vs predecessors

A precedence relation can be represented as:

```text
1 → 5
2 → 5
```

This means:

```text
1 is a predecessor of 5
2 is a predecessor of 5
```

The scheduler-friendly output should therefore be:

```python
{
    "id": 5,
    "predecessors": [1, 2]
}
```

The Week 1 acceptance requirement explicitly checks this relationship.

---

# 17. Example of reversing the dependency graph

Suppose the input gives:

```text
1 → 4
2 → 4
3 → 5
4 → 6
5 → 6
```

Then the parser should produce:

```python
1: []
2: []
3: []
4: [1, 2]
5: [3]
6: [4, 5]
```

The transformation is:

```text
successor relation
       │
       ▼
reverse each edge
       │
       ▼
predecessor list
```

For every relation:

```python
source -> target
```

add:

```python
source
```

to:

```python
predecessors[target]
```

---

# 18. Duration and resources

## Duration

Represents the processing duration of a task in the benchmark.

Example:

```python
"duration": 12
```

Later the simulator can use this information as part of execution timing.

## Resources

Represents the resource-demand fields from the PSPLIB instance.

Example:

```python
"resources": [4, 2, 0, 0]
```

The parser should preserve these values.

---

# 19. M3 implementation

Create:

```text
src/
└── env/
    └── psplib_loader.py
```

Recommended implementation:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any


def _split_fields(line: str) -> list[str]:
    """
    Accept whitespace-separated or semicolon-separated fields.
    """
    return line.replace(";", " ").split()


def _find_section(lines: list[str], section_name: str) -> int:
    section_name = section_name.lower()

    for i, line in enumerate(lines):
        if section_name in line.lower():
            return i

    raise ValueError(
        f"Section '{section_name}' not found"
    )


def load_psplib(path: str | Path) -> list[dict[str, Any]]:
    """
    Load one PSPLIB instance.

    Returned schema:

        {
            "id": int,
            "duration": int,
            "predecessors": list[int],
            "resources": list[int]
        }
    """

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"PSPLIB file not found: {path}"
        )

    lines = path.read_text(
        encoding="utf-8",
        errors="ignore"
    ).splitlines()

    # =========================================================
    # 1. PRECEDENCE RELATIONS
    # =========================================================

    precedence_idx = _find_section(
        lines,
        "PRECEDENCE RELATIONS"
    )

    predecessors: dict[int, list[int]] = {}

    i = precedence_idx + 1

    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        if "REQUESTS/DURATIONS" in line.upper():
            break

        parts = _split_fields(line)

        # Logical format:
        # job_id  mode  number_of_successors  successor_1 ...
        if parts and parts[0].isdigit() and len(parts) >= 4:
            job_id = int(parts[0])
            number_successors = int(parts[2])

            successors = [
                int(x)
                for x in parts[3:3 + number_successors]
            ]

            predecessors.setdefault(job_id, [])

            for successor in successors:
                predecessors.setdefault(successor, [])
                predecessors[successor].append(job_id)

        i += 1

    # =========================================================
    # 2. REQUESTS / DURATIONS
    # =========================================================

    requests_idx = _find_section(
        lines,
        "REQUESTS/DURATIONS"
    )

    tasks: dict[int, dict[str, Any]] = {}

    i = requests_idx + 1

    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        parts = _split_fields(line)

        # Logical format:
        # job_id mode duration resource_1 resource_2 ...
        if parts and parts[0].isdigit() and len(parts) >= 4:
            job_id = int(parts[0])
            mode = int(parts[1])
            duration = int(parts[2])

            # Week 1 uses a single-mode instance.
            if mode == 1:
                resources = [
                    int(x)
                    for x in parts[3:]
                ]

                tasks[job_id] = {
                    "id": job_id,
                    "duration": duration,
                    "predecessors": sorted(
                        predecessors.get(job_id, [])
                    ),
                    "resources": resources,
                }

        i += 1

    return [
        tasks[job_id]
        for job_id in sorted(tasks)
    ]
```

---

# 20. M3 parser pipeline

The parsing process is:

```text
                    j30.sm
                      │
                      ▼
                Read text file
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
 PRECEDENCE RELATIONS      REQUESTS/DURATIONS
          │                       │
          ▼                       ▼
      successors             duration
          │                  resources
          ▼
     reverse edges
          │
          ▼
     predecessors
          │
          └───────────┬───────────┘
                      ▼
               Task dictionaries
```

The parser joins the data by task ID.

---

# 21. M3 test

Create:

```text
tests/test_psplib_loader.py
```

```python
from src.env.psplib_loader import load_psplib


def test_j30():
    tasks = load_psplib("data/j30.sm")

    assert len(tasks) == 30

    assert tasks[0]["id"] == 1
    assert tasks[0]["predecessors"] == []

    task_5 = next(
        task
        for task in tasks
        if task["id"] == 5
    )

    assert task_5["predecessors"] == [1, 2]
```

Run:

```bash
pytest tests/test_psplib_loader.py -v
```

The project acceptance checks are:

```python
len(load_psplib("data/j30.sm")) == 30
```

and:

```python
task_1["predecessors"] == []
task_5["predecessors"] == [1, 2]
```

---

# 22. Important PSPLIB caution

The roadmap expects a `j30.sm` input that produces 30 tasks.

PSPLIB is a benchmark library containing multiple J30 instances, so use the exact instance/file supplied by the project or repository.

Do not silently substitute a different benchmark instance if your team already has a required `j30.sm`.

---

# 23. Shared project schema

The onboarding document defines a shared Pydantic `Task` model with fields including:

```python
class Task(BaseModel):
    id: str
    arrival_time: float
    cpu_units: float
    ram_units: float
    priority: int = 1
    data_size_mb: float = 1.0
    state: TaskState = TaskState.PENDING
    assigned_node: str | None = None
    start_time: float | None = None
    completion_time: float | None = None
```

M3 should keep its parser output simple and compatible with later conversion into this common project representation.

Do not invent incompatible field names such as:

```python
{
    "task_number": 5,
    "exec_time": 10,
    "parents": [1, 2]
}
```

when the specified intermediate output is:

```python
{
    "id": 5,
    "duration": 10,
    "predecessors": [1, 2],
    "resources": [...]
}
```

---

# 24. How M2 and M3 eventually connect

A simplified future pipeline is:

```text
PSPLIB
  │
  ▼
psplib_loader.py
  │
  ▼
Tasks + dependencies
  │
  ▼
Task Generator / Benchmark Loader
  │
  ▼
Orchestrator
  │
  ├─────────────────────┐
  │                     │
  ▼                     ▼
Task scheduling      Radiation events
                           │
                           ▼
                      Node affected
                           │
                           ▼
                     Re-scheduling
```

Example:

```text
Task 1 ──┐
         ├──> Task 5
Task 2 ──┘

Task 5 assigned to LEO-1

         radiation event
                │
                ▼
             LEO-1 fails
                │
                ▼
        affected/orphaned task
                │
                ▼
        scheduler chooses another node
```

So:

- **M3 supplies realistic task structure.**
- **M2 supplies stochastic failure conditions.**

---

# 25. Repository structure for Week 1

A useful Team A layout is:

```text
orbit-scheduler/
│
├── data/
│   └── j30.sm
│
├── src/
│   └── env/
│       ├── radiation.py
│       └── psplib_loader.py
│
├── tests/
│   ├── test_radiation.py
│   └── test_psplib_loader.py
│
├── requirements.txt
└── README.md
```

---

# 26. Environment setup

The project onboarding specifies Python 3.11+ and a shared `requirements.txt`.

Typical setup:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Then:

```bash
pip install -r requirements.txt
```

The full project requirements include:

```text
simpy
pydantic
pandas
numpy
pyyaml
matplotlib
plotly
torch
stable-baselines3
skyfield
```

M2 mainly needs NumPy in Week 1; M3 mostly uses Python's standard library plus the shared project environment.

---

# 27. Git workflow

The project specifies:

```text
main
  │
  ▼
develop
  │
  ▼
team-a-data
   ├── feature/radiation
   └── feature/psplib
```

The intended review workflow is:

```text
M2 writes radiation
       │
       ▼
feature/radiation
       │
       ▼
PR → team-a-data
       │
       ▼
M3 reviews
```

and:

```text
M3 writes PSPLIB parser
       │
       ▼
feature/psplib
       │
       ▼
PR → team-a-data
       │
       ▼
M2 reviews
```

Do not merge your own PR.

---

# 28. M2 Git steps

```bash
git checkout team-a-data
git pull
git checkout -b feature/radiation
```

Implement:

```text
src/env/radiation.py
tests/test_radiation.py
```

Run:

```bash
pytest tests/test_radiation.py -v
```

Commit:

```bash
git add src/env/radiation.py tests/test_radiation.py
git commit -m "feat: add radiation failure model"
```

Push:

```bash
git push -u origin feature/radiation
```

Create a PR to:

```text
team-a-data
```

Then M3 reviews it.

---

# 29. M3 Git steps

```bash
git checkout team-a-data
git pull
git checkout -b feature/psplib
```

Implement:

```text
src/env/psplib_loader.py
tests/test_psplib_loader.py
data/j30.sm
```

Run:

```bash
pytest tests/test_psplib_loader.py -v
```

Commit:

```bash
git add src/env/psplib_loader.py tests/test_psplib_loader.py data/j30.sm
git commit -m "feat: add PSPLIB loader"
```

Push:

```bash
git push -u origin feature/psplib
```

Create a PR to:

```text
team-a-data
```

Then M2 reviews it.

---

# 30. Code review checklist

## General

```text
[ ] Imports work
[ ] No absolute local paths
[ ] No unnecessary dependencies
[ ] Names are clear
[ ] Errors are understandable
[ ] Tests exist
[ ] Tests pass
```

## M2

```text
[ ] SDC = 17 rad
[ ] HBM = 44 rad
[ ] SEFI = 5000 rad
[ ] scale = characteristic_dose / 0.01
[ ] random seed supported
[ ] cumulative dose exists
[ ] statistical sanity test exists
```

## M3

```text
[ ] Input file is found
[ ] PRECEDENCE section is parsed
[ ] REQUESTS/DURATIONS is parsed
[ ] successors become predecessors
[ ] duration is extracted
[ ] resources are preserved
[ ] tasks are sorted
[ ] expected 30-task acceptance test passes
```

---

# 31. Full Team A test

After both PRs are integrated:

```bash
pytest -v
```

You should have all Team A Week 1 tests passing.

Also test imports:

```bash
python -c "from src.env.radiation import RadiationModel"
```

```bash
python -c "from src.env.psplib_loader import load_psplib"
```

---

# 32. Manual M2 smoke test

```bash
python -c "from src.env.radiation import RadiationModel; m=RadiationModel(seed=42); print(m.time_to_failure(17.0)); m.add_exposure(100); print(m.cumulative_dose)"
```

You should see:

- a non-negative random failure time
- `1.0` for cumulative dose after 100 seconds

---

# 33. Manual M3 smoke test

```bash
python -c "from src.env.psplib_loader import load_psplib; tasks=load_psplib('data/j30.sm'); print(len(tasks)); print(tasks[0]); print(next(t for t in tasks if t['id']==5))"
```

The important checks are:

```text
30 tasks
task 1 has no predecessors
task 5 has predecessors [1, 2]
```

---

# 34. Common M2 mistakes

## Mistake 1 — Treating 1700 as a fixed result

Wrong:

```text
time_to_failure(17) == 1700
```

Correct:

```text
mean(time_to_failure(17)) ≈ 1700
```

over many samples.

## Mistake 2 — No reproducibility

Avoid relying only on the global random state.

Prefer:

```python
rng = np.random.default_rng(42)
```

## Mistake 3 — Wrong scale

The project requires:

```python
scale = characteristic_dose / 0.01
```

Do not accidentally use:

```python
scale = characteristic_dose * 0.01
```

Those have completely different meanings.

---

# 35. Common M3 mistakes

## Mistake 1 — Keeping successors

Input:

```text
1 → 5
2 → 5
```

Required:

```python
5["predecessors"] == [1, 2]
```

## Mistake 2 — Ignoring duration

The parser is not only a dependency parser.

It also needs:

```text
duration
resources
```

## Mistake 3 — Mixing parsing and scheduling

The parser should answer:

> "What does the benchmark file contain?"

It should not answer:

> "Which node should execute this task?"

Allocation decisions belong to the scheduler/strategy layer.

---

# 36. Scientific purpose of M2

You can explain M2 scientifically as:

> The radiation model introduces a stochastic failure process into the simulated orbital computing environment. Instead of using arbitrary failure times, the project samples time-to-event from an exponential distribution parameterized by characteristic dose. Three failure modes are modeled: SDC, HBM, and SEFI. The cumulative dose and deterministic seed support reproducible experiments. The resulting events will later be used to test resilience of task allocation and re-scheduling strategies.

---

# 37. Scientific purpose of M3

You can explain M3 scientifically as:

> The PSPLIB parser introduces realistic scheduling structure into the benchmark environment. PSPLIB instances contain task durations, resource requirements, and precedence relationships. The parser converts the benchmark format into a simple internal representation using task IDs, durations, predecessor lists, and resource demands. This allows later scheduling components to reason about dependencies rather than treating all tasks as independent.

---

# 38. How to explain your roles in a presentation

## M2 — spoken English

> "I am responsible for the radiation model. Our goal is to replace arbitrary random failures with a stochastic radiation-based model. We use an exponential distribution for the time to a radiation event. The characteristic doses are 17 rad for SDC, 44 rad for HBM, and 5000 rad for SEFI. The model also tracks cumulative dose and supports fixed random seeds for reproducibility. Later, this model will generate realistic failure scenarios for evaluating scheduling resilience."

## M3 — spoken English

> "I am responsible for the PSPLIB parser. PSPLIB provides benchmark scheduling instances containing task durations, resource requirements, and precedence constraints. Our parser extracts this information and converts successors into predecessor lists. The output is a standard internal structure with an ID, duration, predecessors, and resources. This gives the scheduler realistic task dependencies for future benchmark evaluation."

---

# 39. What happens in Week 2?

According to the roadmap:

### M2

Moves to:

```text
src/env/node.py
src/env/link.py
```

with node resources and communication links.

### M3

Moves to:

```text
src/env/task_generator.py
```

and generates four profiles:

```text
Burst
Energy
Radiation
Mixed
```

The Radiation profile will use the M2 radiation component.

---

# 40. What happens later?

The project eventually compares:

```text
Strategy 1 → Always Ground
Strategy 2 → Always Orbital
Strategy 3 → Greedy
```

and later additional strategies.

Results will be generated for multiple profiles and random seeds, then summarized into CSV files and figures for the paper and final pitch.

Team A's Week 1 components are therefore foundations for:

```text
benchmark realism
       +
failure realism
       ↓
better simulation
       ↓
meaningful strategy comparison
```

---

# 41. Final Week 1 checklist

## M2

```text
[ ] radiation.py created
[ ] RadiationModel implemented
[ ] SDC = 17 rad
[ ] HBM = 44 rad
[ ] SEFI = 5000 rad
[ ] exponential time-to-failure
[ ] cumulative dose
[ ] fixed seed support
[ ] unit tests
[ ] tests pass
[ ] PR submitted
[ ] M3 review completed
```

## M3

```text
[ ] correct j30.sm obtained
[ ] psplib_loader.py created
[ ] precedence parsed
[ ] duration parsed
[ ] resources parsed
[ ] successors converted to predecessors
[ ] output schema correct
[ ] unit tests
[ ] len(...) == 30
[ ] task 1 predecessors == []
[ ] task 5 predecessors == [1, 2]
[ ] PR submitted
[ ] M2 review completed
```

## Team A

```text
[ ] both PRs merged into team-a-data
[ ] pytest -v passes
[ ] both modules import correctly
[ ] no hardcoded personal paths
[ ] README/documentation updated
```

---

# 42. Final mental model

Remember the whole Week 1 in one picture:

```text
                         PROJECT
                            │
                Dynamic workload allocation
                            │
             ┌──────────────┴──────────────┐
             │                             │
             ▼                             ▼
        TASK STRUCTURE                FAILURES
             │                             │
             ▼                             ▼
        M3 — PSPLIB                   M2 — Radiation
             │                             │
             │                             │
   dependencies / duration         stochastic event time
       / resources                 cumulative dose
             │                             │
             └──────────────┬──────────────┘
                            ▼
                     Future simulator
                            │
                            ▼
                     Allocation strategies
                            │
                            ▼
                    Performance evaluation
```

### The key sentence

> **M3 describes the workload and its dependencies; M2 describes how radiation can make the computing environment fail. Together, they create more realistic conditions for the future dynamic scheduling simulator.**

---

# 43. Primary project source

The uploaded project roadmap is the authority for the Week 1 responsibilities and acceptance criteria.

Key roadmap sections used in this guide:

- Week 1 task allocation
- M2 radiation requirements
- M3 PSPLIB parser requirements
- repository and branch workflow
- shared Pydantic task schema
- Week 2/3 integration context
- experimental design and workload profiles

For implementation decisions, follow the repository's shared project documents when they define a more specific interface than this guide.

---

# 44. External resources

## PSPLIB official data

https://www.om-db.wi.tum.de/psplib/getdata.php?mode=sm

## PSPLIB parser/reference project

https://github.com/PyJobShop/PSPLIB

## NumPy exponential distribution documentation

https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.exponential.html

These are reference resources; the project roadmap remains the primary specification for what Team A must deliver in Week 1.
