"""Task generator for the 4 benchmark workload profiles.

Profiles:
    1. Burst   — 150 tasks arriving simultaneously at t=0 (stress test)
    2. Energy  — 100 tasks spread over 7200s with energy constraints
    3. Radiation — 80 tasks annotated with radiation failure modes (uses M2)
    4. Mixed   — 200 tasks with 20% high-priority and deadline constraints

Each function returns a list of dictionaries compatible with src.schemas.Task.

Author: M3 (Team A)
Week: 2
"""

from __future__ import annotations

import numpy as np

from src.env.radiation import RadiationModel, FailureMode


# ---------------------------------------------------------------------------
# Profile 1: Burst Heavy
# ---------------------------------------------------------------------------

def generate_burst(
    n: int = 150,
    seed: int = 42,
) -> list[dict]:
    """Generate a burst workload: all tasks arrive at t=0.

    Simulates a sudden flood of compute requests (e.g., a batch of
    satellite imagery arriving simultaneously after an orbital pass).

    Args:
        n: Number of tasks to generate (default 150).
        seed: Random seed for reproducibility.

    Returns:
        List of task dictionaries with:
            - id: "burst_0", "burst_1", ...
            - arrival_time: 0.0 (all simultaneous)
            - cpu_units: uniform random in [5, 15]
            - ram_units: uniform random in [1, 8]
            - priority: 1 (normal)
            - data_size_mb: uniform random in [0.5, 5.0]
    """
    rng = np.random.default_rng(seed)

    tasks = []
    for i in range(n):
        tasks.append({
            "id": f"burst_{i}",
            "arrival_time": 0.0,
            "cpu_units": float(rng.uniform(5, 15)),
            "ram_units": float(rng.uniform(1, 8)),
            "priority": 1,
            "data_size_mb": float(rng.uniform(0.5, 5.0)),
        })

    return tasks


# ---------------------------------------------------------------------------
# Profile 2: Energy Constrained
# ---------------------------------------------------------------------------

def generate_energy(
    n: int = 100,
    duration: float = 7200.0,
    seed: int = 42,
) -> list[dict]:
    """Generate an energy-constrained workload spread over a time window.

    Simulates tasks that arrive progressively over 2 hours (7200s),
    each carrying an energy budget that the scheduler must respect.

    Args:
        n: Number of tasks to generate (default 100).
        duration: Time window in seconds (default 7200s = 2 hours).
        seed: Random seed for reproducibility.

    Returns:
        List of task dictionaries with:
            - id: "energy_0", "energy_1", ...
            - arrival_time: uniform random in [0, duration]
            - cpu_units: uniform random in [15, 20]
            - ram_units: uniform random in [2, 16]
            - priority: 1 (normal)
            - data_size_mb: uniform random in [1.0, 10.0]
            - energy_budget: uniform random in [5.0, 50.0] (Joules)
    """
    rng = np.random.default_rng(seed)

    tasks = []
    for i in range(n):
        tasks.append({
            "id": f"energy_{i}",
            "arrival_time": float(rng.uniform(0, duration)),
            "cpu_units": float(rng.uniform(15, 20)),
            "ram_units": float(rng.uniform(2, 16)),
            "priority": 1,
            "data_size_mb": float(rng.uniform(1.0, 10.0)),
            "energy_budget": float(rng.uniform(5.0, 50.0)),
        })

    # Sort by arrival time for natural ordering
    tasks.sort(key=lambda t: t["arrival_time"])

    return tasks


# ---------------------------------------------------------------------------
# Profile 3: Radiation
# ---------------------------------------------------------------------------

def generate_radiation(
    n: int = 80,
    seed: int = 42,
) -> list[dict]:
    """Generate a radiation-annotated workload using the M2 RadiationModel.

    Each task is assigned a radiation failure mode (SDC, HBM, or SEFI)
    based on which radiation event would occur first, according to the
    exponential time-to-failure model from M2's RadiationModel.

    The failure_time field indicates the sampled time-to-failure for
    the assigned mode. Tasks where failure_time < cpu_units represent
    tasks that would be corrupted or interrupted by radiation.

    Args:
        n: Number of tasks to generate (default 80).
        seed: Random seed for reproducibility.

    Returns:
        List of task dictionaries with:
            - id: "radiation_0", "radiation_1", ...
            - arrival_time: uniform random in [0, 3600]
            - cpu_units: uniform random in [5, 20]
            - ram_units: uniform random in [1, 8]
            - priority: 1 (normal)
            - data_size_mb: uniform random in [0.5, 5.0]
            - failure_mode: "SDC", "HBM", or "SEFI"
            - failure_time: sampled time-to-failure in seconds
    """
    rng = np.random.default_rng(seed)
    rad_model = RadiationModel(seed=seed)

    tasks = []
    for i in range(n):
        # Sample which failure mode would occur first
        mode, failure_time = rad_model.next_failure()

        tasks.append({
            "id": f"radiation_{i}",
            "arrival_time": float(rng.uniform(0, 3600)),
            "cpu_units": float(rng.uniform(5, 20)),
            "ram_units": float(rng.uniform(1, 8)),
            "priority": 1,
            "data_size_mb": float(rng.uniform(0.5, 5.0)),
            "failure_mode": mode.value,  # "SDC", "HBM", or "SEFI"
            "failure_time": float(failure_time),
        })

    # Sort by arrival time
    tasks.sort(key=lambda t: t["arrival_time"])

    return tasks


# ---------------------------------------------------------------------------
# Profile 4: Mixed
# ---------------------------------------------------------------------------

def generate_mixed(
    n: int = 200,
    high_priority_ratio: float = 0.20,
    seed: int = 42,
) -> list[dict]:
    """Generate a mixed workload with high-priority and deadline constraints.

    20% of tasks are marked as high-priority (priority=2) with a tight
    deadline of 0.1s (100ms). This profile tests whether the scheduler
    can differentiate urgent from normal tasks.

    Args:
        n: Number of tasks to generate (default 200).
        high_priority_ratio: Fraction of tasks with priority=2 (default 0.20).
        seed: Random seed for reproducibility.

    Returns:
        List of task dictionaries with:
            - id: "mixed_0", "mixed_1", ...
            - arrival_time: uniform random in [0, 5000]
            - cpu_units: uniform random in [3, 18]
            - ram_units: uniform random in [1, 12]
            - priority: 1 (normal) or 2 (high)
            - data_size_mb: uniform random in [0.5, 8.0]
            - deadline: 0.1 for high-priority tasks, None for normal tasks
    """
    rng = np.random.default_rng(seed)

    n_high = int(n * high_priority_ratio)

    # Build index set for high-priority tasks
    all_indices = list(range(n))
    high_priority_indices = set(
        rng.choice(all_indices, size=n_high, replace=False)
    )

    tasks = []
    for i in range(n):
        is_high = i in high_priority_indices

        tasks.append({
            "id": f"mixed_{i}",
            "arrival_time": float(rng.uniform(0, 5000)),
            "cpu_units": float(rng.uniform(3, 18)),
            "ram_units": float(rng.uniform(1, 12)),
            "priority": 2 if is_high else 1,
            "data_size_mb": float(rng.uniform(0.5, 8.0)),
            "deadline": 0.1 if is_high else None,
        })

    # Sort by arrival time
    tasks.sort(key=lambda t: t["arrival_time"])

    return tasks


# ---------------------------------------------------------------------------
# Convenience: generate all profiles
# ---------------------------------------------------------------------------

def generate_all_profiles(seed: int = 42) -> dict[str, list[dict]]:
    """Generate all 4 workload profiles with the same seed.

    Returns:
        Dictionary mapping profile names to task lists:
            {
                "burst": [...],
                "energy": [...],
                "radiation": [...],
                "mixed": [...]
            }
    """
    return {
        "burst": generate_burst(seed=seed),
        "energy": generate_energy(seed=seed),
        "radiation": generate_radiation(seed=seed),
        "mixed": generate_mixed(seed=seed),
    }
