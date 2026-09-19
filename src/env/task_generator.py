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

import logging
import os
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from src.env.radiation import RadiationModel


# ---------------------------------------------------------------------------
# Config loading with fallback
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "experiment.yaml"
_PROFILE_DEFAULTS = {
    "burst": {
        "n_tasks": 150,
        "cpu_min": 5.0,
        "cpu_max": 15.0,
        "ram_min": 1.0,
        "ram_max": 8.0,
        "data_size_min": 0.5,
        "data_size_max": 5.0,
        "arrival_time": 0.0,
    },
    "energy": {
        "n_tasks": 100,
        "cpu_min": 15.0,
        "cpu_max": 20.0,
        "ram_min": 2.0,
        "ram_max": 16.0,
        "data_size_min": 1.0,
        "data_size_max": 10.0,
        "duration_s": 7200.0,
        "energy_budget_min": 5.0,
        "energy_budget_max": 50.0,
    },
    "radiation": {
        "n_tasks": 80,
        "cpu_min": 5.0,
        "cpu_max": 20.0,
        "ram_min": 1.0,
        "ram_max": 8.0,
        "data_size_min": 0.5,
        "data_size_max": 5.0,
        "arrival_window": 3600.0,
    },
    "mixed": {
        "n_tasks": 200,
        "cpu_min": 3.0,
        "cpu_max": 18.0,
        "ram_min": 1.0,
        "ram_max": 12.0,
        "data_size_min": 0.5,
        "data_size_max": 8.0,
        "arrival_window": 5000.0,
        "urgent_ratio": 0.20,
        "deadline_s": 0.1,
    },
}

_CONFIG_CACHE: dict[str, dict[str, Any]] | None = None


def _load_profile_config(profile_name: str) -> dict[str, Any]:
    """Load profile configuration from config/experiment.yaml with fallback."""
    global _CONFIG_CACHE

    if _CONFIG_CACHE is None:
        try:
            if _CONFIG_PATH.exists():
                with open(_CONFIG_PATH, "r") as f:
                    data = yaml.safe_load(f) or {}
                _CONFIG_CACHE = data.get("profiles", {})
            else:
                _CONFIG_CACHE = {}
                logging.warning(
                    "Config file not found at %s, using hardcoded defaults",
                    _CONFIG_PATH,
                )
        except Exception as e:
            _CONFIG_CACHE = {}
            logging.warning(
                "Failed to load config from %s: %s, using hardcoded defaults",
                _CONFIG_PATH,
                e,
            )

    # Merge with defaults (defaults as fallback for missing keys)
    config = _CONFIG_CACHE.get(profile_name, {})
    defaults = _PROFILE_DEFAULTS.get(profile_name, {})
    # Defaults take precedence for missing keys
    merged = {**defaults, **config}
    return merged


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _create_task_dict(
    task_id: str,
    arrival_time: float,
    cpu_units: float,
    ram_units: float,
    priority: int = 1,
    data_size_mb: float = 1.0,
    **extra_fields,
) -> dict:
    """Build a base task dict, merging optional profile-specific fields."""
    task = {
        "id": task_id,
        "arrival_time": arrival_time,
        "cpu_units": cpu_units,
        "ram_units": ram_units,
        "priority": priority,
        "data_size_mb": data_size_mb,
    }
    task.update(extra_fields)
    return task


# ---------------------------------------------------------------------------
# Profile 1: Burst Heavy
# ---------------------------------------------------------------------------

def generate_burst(
    n: int | None = None,
    seed: int = 42,
) -> list[dict]:
    """Generate a burst workload: all tasks arrive at t=0.

    Simulates a sudden flood of compute requests (e.g., a batch of
    satellite imagery arriving simultaneously after an orbital pass).

    Args:
        n: Number of tasks to generate (default: read from config, fallback 150).
        seed: Random seed for reproducibility.

    Returns:
        List of task dictionaries with:
            - id: "burst_0", "burst_1", ...
            - arrival_time: 0.0 (all simultaneous)
            - cpu_units: uniform random in [cpu_min, cpu_max]
            - ram_units: uniform random in [ram_min, ram_max]
            - priority: 1 (normal)
            - data_size_mb: uniform random in [data_size_min, data_size_max]
    """
    config = _load_profile_config("burst")
    n = n if n is not None else config["n_tasks"]

    rng = np.random.default_rng(seed)

    tasks = []
    for i in range(n):
        tasks.append(
            _create_task_dict(
                task_id=f"burst_{i}",
                arrival_time=config["arrival_time"],
                cpu_units=float(rng.uniform(config["cpu_min"], config["cpu_max"])),
                ram_units=float(rng.uniform(config["ram_min"], config["ram_max"])),
                priority=1,
                data_size_mb=float(
                    rng.uniform(config["data_size_min"], config["data_size_max"])
                ),
            )
        )

    return tasks


# ---------------------------------------------------------------------------
# Profile 2: Energy Constrained
# ---------------------------------------------------------------------------

def generate_energy(
    n: int | None = None,
    duration: float | None = None,
    seed: int = 42,
) -> list[dict]:
    """Generate an energy-constrained workload spread over a time window.

    Simulates tasks that arrive progressively over 2 hours (7200s),
    each carrying an energy budget that the scheduler must respect.

    Args:
        n: Number of tasks to generate (default: read from config, fallback 100).
        duration: Time window in seconds (default: read from config, fallback 7200s).
        seed: Random seed for reproducibility.

    Returns:
        List of task dictionaries with:
            - id: "energy_0", "energy_1", ...
            - arrival_time: uniform random in [0, duration]
            - cpu_units: uniform random in [cpu_min, cpu_max]
            - ram_units: uniform random in [ram_min, ram_max]
            - priority: 1 (normal)
            - data_size_mb: uniform random in [data_size_min, data_size_max]
            - energy_budget: uniform random in [energy_budget_min, energy_budget_max] (Joules)
    """
    config = _load_profile_config("energy")
    n = n if n is not None else config["n_tasks"]
    duration = duration if duration is not None else config["duration_s"]

    rng = np.random.default_rng(seed)

    tasks = []
    for i in range(n):
        tasks.append(
            _create_task_dict(
                task_id=f"energy_{i}",
                arrival_time=float(rng.uniform(0, duration)),
                cpu_units=float(rng.uniform(config["cpu_min"], config["cpu_max"])),
                ram_units=float(rng.uniform(config["ram_min"], config["ram_max"])),
                priority=1,
                data_size_mb=float(
                    rng.uniform(config["data_size_min"], config["data_size_max"])
                ),
                energy_budget=float(
                    rng.uniform(config["energy_budget_min"], config["energy_budget_max"])
                ),
            )
        )

    # Sort by arrival time for natural ordering
    tasks.sort(key=lambda t: t["arrival_time"])

    return tasks


# ---------------------------------------------------------------------------
# Profile 3: Radiation
# ---------------------------------------------------------------------------

def generate_radiation(
    n: int | None = None,
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
        n: Number of tasks to generate (default: read from config, fallback 80).
        seed: Random seed for reproducibility.

    Returns:
        List of task dictionaries with:
            - id: "radiation_0", "radiation_1", ...
            - arrival_time: uniform random in [0, arrival_window]
            - cpu_units: uniform random in [cpu_min, cpu_max]
            - ram_units: uniform random in [ram_min, ram_max]
            - priority: 1 (normal)
            - data_size_mb: uniform random in [data_size_min, data_size_max]
            - failure_mode: "SDC", "HBM", or "SEFI"
            - failure_time: sampled time-to-failure in seconds
    """
    config = _load_profile_config("radiation")
    n = n if n is not None else config["n_tasks"]

    rng = np.random.default_rng(seed)
    rad_model = RadiationModel(seed=seed)

    tasks = []
    for i in range(n):
        # Sample which failure mode would occur first
        mode, failure_time = rad_model.next_failure()

        tasks.append(
            _create_task_dict(
                task_id=f"radiation_{i}",
                arrival_time=float(rng.uniform(0, config["arrival_window"])),
                cpu_units=float(rng.uniform(config["cpu_min"], config["cpu_max"])),
                ram_units=float(rng.uniform(config["ram_min"], config["ram_max"])),
                priority=1,
                data_size_mb=float(
                    rng.uniform(config["data_size_min"], config["data_size_max"])
                ),
                failure_mode=mode.value,  # "SDC", "HBM", or "SEFI"
                failure_time=float(failure_time),
            )
        )

    # Sort by arrival time
    tasks.sort(key=lambda t: t["arrival_time"])

    return tasks


# ---------------------------------------------------------------------------
# Profile 4: Mixed
# ---------------------------------------------------------------------------

def generate_mixed(
    n: int | None = None,
    high_priority_ratio: float | None = None,
    seed: int = 42,
) -> list[dict]:
    """Generate a mixed workload with high-priority and deadline constraints.

    20% of tasks are marked as high-priority (priority=2) with a tight
    deadline of 0.1s (100ms). This profile tests whether the scheduler
    can differentiate urgent from normal tasks.

    Args:
        n: Number of tasks to generate (default: read from config, fallback 200).
        high_priority_ratio: Fraction of tasks with priority=2 (default: read from config, fallback 0.20).
        seed: Random seed for reproducibility.

    Returns:
        List of task dictionaries with:
            - id: "mixed_0", "mixed_1", ...
            - arrival_time: uniform random in [0, arrival_window]
            - cpu_units: uniform random in [cpu_min, cpu_max]
            - ram_units: uniform random in [ram_min, ram_max]
            - priority: 1 (normal) or 2 (high)
            - data_size_mb: uniform random in [data_size_min, data_size_max]
            - deadline: deadline_s for high-priority tasks, None for normal tasks
    """
    config = _load_profile_config("mixed")
    n = n if n is not None else config["n_tasks"]
    high_priority_ratio = (
        high_priority_ratio if high_priority_ratio is not None else config["urgent_ratio"]
    )

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

        tasks.append(
            _create_task_dict(
                task_id=f"mixed_{i}",
                arrival_time=float(rng.uniform(0, config["arrival_window"])),
                cpu_units=float(rng.uniform(config["cpu_min"], config["cpu_max"])),
                ram_units=float(rng.uniform(config["ram_min"], config["ram_max"])),
                priority=2 if is_high else 1,
                data_size_mb=float(
                    rng.uniform(config["data_size_min"], config["data_size_max"])
                ),
                deadline=config["deadline_s"] if is_high else None,
            )
        )

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