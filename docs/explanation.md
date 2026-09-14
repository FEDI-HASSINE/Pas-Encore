# Technical Guide & Explanation: Radiation Failure Model (M2)

> **Component:** `src/env/radiation.py`  
> **Test Suite:** `src/tests/test_radiation.py`  
> **Team:** Team A — Workload & Environment Modeling  
> **Target Branch:** `feature/radiation` $\rightarrow$ `team-a-data`

---

## Table of Contents
1. [Overview & Scientific Motivation](#1-overview--scientific-motivation)
2. [Physical & Mathematical Modeling](#2-physical--mathematical-modeling)
3. [Source Code Walkthrough (`src/env/radiation.py`)](#3-source-code-walkthrough-srcenvradiationpy)
4. [Unit Tests Walkthrough (`src/tests/test_radiation.py`)](#4-unit-tests-walkthrough-srcteststest_radiationpy)
5. [How to Run Tests](#5-how-to-run-tests)
6. [How to Use the Radiation Model in Simulation](#6-how-to-use-the-radiation-model-in-simulation)

---

## 1. Overview & Scientific Motivation

In space-ground collaborative computing, orbital compute nodes (such as Low Earth Orbit satellites `LEO-1`, `LEO-2`) operate outside Earth's protective atmosphere. They are subject to continuous cosmic radiation and solar particle events.

### Why not simple random failure?
A naive simulation might use:
```python
if random.random() < 0.05:
    node.fail()
```
This naive approach has severe limitations:
- It fails to capture physical exposure time.
- It cannot distinguish between minor computational errors and fatal hardware damage.
- It cannot be reliably calibrated with space qualification data.

### The Stochastic Radiation Model
Instead, our system implements a **radiation-driven stochastic failure model**:
1. Radiation accumulates over time at a defined **dose rate**.
2. Waiting times until radiation-induced anomalies follow an **exponential distribution**.
3. Three distinct **failure modes** are modeled, each parameterized by its empirical **characteristic dose**.
4. Random number generators are isolated and **seeded** to guarantee scientific reproducibility across comparative scheduler benchmarks.

---

## 2. Physical & Mathematical Modeling

### 2.1 Dose Accumulation
Radiation dose is measured in **rad** (radiation absorbed dose). The project assumes a constant background orbital dose rate:

$$\text{Dose Rate} = 0.01\text{ rad/second}$$

Given an operational exposure duration $t$ (in seconds), cumulative radiation dose $D(t)$ is:

$$D(t) = D_0 + (t \times 0.01)$$

- $100\text{ s}$ of orbital flight $\rightarrow 1.0\text{ rad}$
- $1000\text{ s}$ of orbital flight $\rightarrow 10.0\text{ rad}$

---

### 2.2 Failure Modes & Characteristic Doses
The model categorizes radiation events into three severity levels:

| Failure Mode | Characteristic Dose ($D_c$) | Mean Time to Event ($\mathbb{E}[T]$) | Operational Impact in Simulator |
| :--- | :---: | :---: | :--- |
| **SDC** (Silent Data Corruption) | **$17\text{ rad}$** | $\frac{17}{0.01} = 1{,}700\text{ s}$ (~28 min) | Bit flip in memory/registers; corrupts task output data without crashing the node. |
| **HBM** (Hardware Bit Error / Reboot) | **$44\text{ rad}$** | $\frac{44}{0.01} = 4{,}400\text{ s}$ (~73 min) | Unrecoverable error requiring satellite computer reboot; running tasks are lost/re-queued. |
| **SEFI** (Single Event Functional Interrupt) | **$5{,}000\text{ rad}$** | $\frac{5000}{0.01} = 500{,}000\text{ s}$ (~139 hrs) | Destructive latch-up or permanent node burnout; node is permanently removed from the cluster. |

---

### 2.3 The Exponential Waiting Time Model
The waiting time $T$ until a radiation event occurs is modeled as an exponential random variable with parameter $\lambda$:

$$f(t) = \lambda e^{-\lambda t}, \quad t \ge 0$$

The expected value (scale parameter) $\beta = \mathbb{E}[T]$ is:

$$\beta = \frac{1}{\lambda} = \frac{\text{Characteristic Dose}}{\text{Dose Rate}} = \frac{D_c}{0.01}$$

- **SDC:** $\beta = \frac{17}{0.01} = 1700\text{ s}$
- **HBM:** $\beta = \frac{44}{0.01} = 4400\text{ s}$
- **SEFI:** $\beta = \frac{5000}{0.01} = 500000\text{ s}$

> **Key Takeaway:** Calling `time_to_failure(17.0)` returns a single random draw from this distribution (e.g. $230\text{ s}$, $1450\text{ s}$, or $3200\text{ s}$). Over thousands of draws, the arithmetic mean converges to $1700\text{ s}$.

---

## 3. Source Code Walkthrough (`src/env/radiation.py`)

Here is how each component of [`src/env/radiation.py`](file:///c:/Users/lenovo/Desktop/LASTAM/src/env/radiation.py) is implemented:

### 3.1 FailureMode Enumeration
```python
class FailureMode(str, Enum):
    SDC = "SDC"
    HBM = "HBM"
    SEFI = "SEFI"
```
- Inheriting from both `str` and `Enum` ensures type safety while allowing seamless serialization (e.g., in JSON logs and simulation telemetry).

---

### 3.2 RadiationModel Attributes & Initialization
```python
class RadiationModel:
    DOSE_RATE = 0.01

    CHARACTERISTIC_DOSES = {
        FailureMode.SDC: 17.0,
        FailureMode.HBM: 44.0,
        FailureMode.SEFI: 5000.0,
    }

    def __init__(self, seed: int | None = None):
        self.rng = np.random.default_rng(seed)
        self.cumulative_dose = 0.0
```
- `DOSE_RATE = 0.01`: Project baseline dose rate in rad/s.
- `CHARACTERISTIC_DOSES`: Centralized mapping of failure modes to physical doses.
- `np.random.default_rng(seed)`: Creates an **independent pseudorandom generator instance** rather than polluting the global `np.random` state. This guarantees reproducibility when comparing scheduling algorithms under identical seed conditions.
- `self.cumulative_dose`: Tracks lifetime dose absorbed by the node.

---

### 3.3 Sampling Time to Failure (`time_to_failure`)
```python
def time_to_failure(self, characteristic_dose: float) -> float:
    if characteristic_dose <= 0:
        raise ValueError("characteristic_dose must be > 0")

    scale = characteristic_dose / self.DOSE_RATE
    return float(self.rng.exponential(scale=scale))
```
- **Validation**: Rejects zero or negative doses.
- **Scale computation**: $\text{scale} = \frac{D_c}{0.01}$.
- **Sampling**: Draws a float sample from the exponential distribution.

---

### 3.4 Tracking Exposure & State Management
```python
def add_exposure(self, seconds: float) -> float:
    if seconds < 0:
        raise ValueError("seconds must be >= 0")

    self.cumulative_dose += seconds * self.DOSE_RATE
    return self.cumulative_dose

def reset(self) -> None:
    self.cumulative_dose = 0.0
```
- `add_exposure(seconds)`: Accrues dose as simulation time advances ($D \mathrel{+}= \Delta t \times 0.01$).
- `reset()`: Resets cumulative dose between simulation episodes.

---

## 4. Unit Tests Walkthrough (`src/tests/test_radiation.py`)

Located in [`src/tests/test_radiation.py`](file:///c:/Users/lenovo/Desktop/LASTAM/src/tests/test_radiation.py):

### 4.1 Statistical Sanity Test (`test_sdc_mean`)
```python
def test_sdc_mean():
    model = RadiationModel(seed=42)

    samples = [
        model.time_to_failure(17.0)
        for _ in range(10_000)
    ]

    mean = np.mean(samples)
    assert 1500 < mean < 1900
```
- **Goal**: Verifies the exponential distribution implementation without suffering from random flake.
- By the **Law of Large Numbers**, the sample mean of $10{,}000$ draws from an exponential distribution with $\mu = 1700$ has a standard error:
  $$\sigma_{\bar{X}} = \frac{1700}{\sqrt{10000}} = 17\text{ s}$$
- A tolerance band of $[1500, 1900]$ ($\pm 11.7\sigma$) ensures tests will practically never fail spuriously while strictly catching mathematical errors (such as multiplying by $0.01$ instead of dividing).

---

### 4.2 Dose Mapping Test (`test_characteristic_doses`)
```python
def test_characteristic_doses():
    assert RadiationModel.characteristic_dose(FailureMode.SDC) == 17.0
    assert RadiationModel.characteristic_dose(FailureMode.HBM) == 44.0
    assert RadiationModel.characteristic_dose(FailureMode.SEFI) == 5000.0
```
- Confirms constant definitions match the project technical specifications.

---

### 4.3 Accumulation & Reset Tests (`test_cumulative_dose`, `test_reset`)
```python
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
- Confirms deterministic linear accumulation ($100\text{ s} \times 0.01 = 1.0$, plus $200\text{ s} \times 0.01 = 2.0 \rightarrow 3.0$) and state clearing.

---

## 5. How to Run Tests

Because pytest may not be on your global PowerShell `PATH`, always execute pytest through the Python `-m` module runner:

### Run radiation tests with verbose output
```powershell
python -m pytest src/tests/test_radiation.py -v
```

### Run all tests in the workspace
```powershell
python -m pytest -v
```

Expected output:
```text
src/tests/test_radiation.py::test_sdc_mean PASSED                        [ 25%]
src/tests/test_radiation.py::test_characteristic_doses PASSED            [ 50%]
src/tests/test_radiation.py::test_cumulative_dose PASSED                 [ 75%]
src/tests/test_radiation.py::test_reset PASSED                           [100%]
============================== 4 passed in 1.73s ==============================
```

---

## 6. How to Use the Radiation Model in Simulation

### Example 1: Basic Usage
```python
from src.env.radiation import RadiationModel, FailureMode

# 1. Initialize with reproducible seed
model = RadiationModel(seed=42)

# 2. Query characteristic doses
sdc_dose = RadiationModel.characteristic_dose(FailureMode.SDC)  # 17.0

# 3. Sample time to next radiation event
next_sdc_event = model.time_to_failure(sdc_dose)
print(f"Next SDC event predicted at: {next_sdc_event:.2f} seconds")

# 4. Advance time as simulation runs
model.add_exposure(120.0)  # 2 minutes of orbital flight
print(f"Current absorbed dose: {model.cumulative_dose:.2f} rad")
```

---

### Example 2: Checking for Failures During Task Execution
In Week 2/3, a node simulator uses `RadiationModel` to verify if a task survives execution:

```python
from src.env.radiation import RadiationModel, FailureMode

class OrbitalNode:
    def __init__(self, node_id: str, seed: int = 42):
        self.node_id = node_id
        self.rad_model = RadiationModel(seed=seed)

    def execute_task(self, duration_seconds: float) -> str:
        # Check time until next SDC and HBM
        t_sdc = self.rad_model.time_to_failure(RadiationModel.characteristic_dose(FailureMode.SDC))
        t_hbm = self.rad_model.time_to_failure(RadiationModel.characteristic_dose(FailureMode.HBM))

        # Accumulate dose for this task duration
        self.rad_model.add_exposure(duration_seconds)

        if t_hbm < duration_seconds:
            return "FAILED_HBM_REBOOT"
        elif t_sdc < duration_seconds:
            return "CORRUPTED_SDC"
        else:
            return "SUCCESS"

# Test execution:
node = OrbitalNode("LEO-1", seed=10)
status = node.execute_task(duration_seconds=50.0)
print(f"Task status on LEO-1: {status}")
```
