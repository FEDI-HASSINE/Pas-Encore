"""Standardised metrics for the orbital scheduler.

Implements the four core metrics defined in
docs/03_EVALUATION_METRICS_SPECIFICATION.md:
  - M_T : Makespan (total wall-clock time to finish all tasks)
  - M_L : Load balance (std-dev of per-node CPU utilization)
  - M_R : Resilience (fraction of tasks recovered after failure)
  - M_E : Efficiency (energy + transmission cost per completed task)

All functions are pure: they do not mutate their inputs.
"""

from __future__ import annotations

import statistics
from typing import Iterable

from src.schemas import Task, TaskState


def compute_mt(tasks: Iterable[Task]) -> float:
    """Compute the makespan M_T.

    M_T = max(completion_time) - min(arrival_time)

    Args:
        tasks: iterable of Task objects. Only COMPLETED tasks with a
               non-None completion_time are considered.

    Returns:
        The makespan as a float (seconds). Returns 0.0 if no task
        has been completed.
    """
    completed = [
        t
        for t in tasks
        if t.state == TaskState.COMPLETED and t.completion_time is not None
    ]
    if not completed:
        return 0.0

    latest = max(t.completion_time for t in completed)
    earliest = min(t.arrival_time for t in completed)
    return float(max(0.0, latest - earliest))


def compute_ml(nodes: dict) -> float:
    """Compute the load-balance metric M_L.

    M_L = standard deviation of per-node CPU utilization ratios.
    Lower is better (0.0 = perfectly balanced).

    Args:
        nodes: dict mapping node_id -> Node (with .cpu_utilized and
               .cpu_capacity attributes).

    Returns:
        The std-dev of utilization ratios as a float. Returns 0.0 if
        there is 0 or 1 node, or if all capacities are 0.
    """
    ratios = []
    for node in nodes.values():
        capacity = getattr(node, "cpu_capacity", 0.0)
        if capacity > 0:
            used = getattr(node, "cpu_utilized", 0.0)
            ratios.append(used / capacity)

    if len(ratios) < 2:
        return 0.0
    return float(statistics.pstdev(ratios))


def compute_mr(completed: int, orphaned: int) -> float:
    """Compute the resilience metric M_R.

    M_R = completed_after_failure / total_orphaned_tasks

    Returns 1.0 if there were no failures (perfect resilience) and
    0.0 if every orphaned task was lost. If orphaned == 0, returns
    1.0 to indicate "no failures observed".
    """
    if orphaned <= 0:
        return 1.0
    return float(min(1.0, max(0.0, completed / orphaned)))


def compute_me(
    total_energy: float,
    total_transmission: float,
    completed_count: int,
) -> float:
    """Compute the efficiency metric M_E.

    M_E = (energy + transmission) / completed_tasks

    Lower is better. Returns 0.0 if no task was completed.
    """
    if completed_count <= 0:
        return 0.0
    return float((total_energy + total_transmission) / completed_count)


def compute_all(
    tasks: Iterable[Task],
    nodes: dict,
    orphaned_count: int = 0,
    total_energy: float = 0.0,
    total_transmission: float = 0.0,
) -> dict:
    """Convenience wrapper returning all four metrics at once."""
    tasks_list = list(tasks)
    completed = [t for t in tasks_list if t.state == TaskState.COMPLETED]
    return {
        "M_T": compute_mt(tasks_list),
        "M_L": compute_ml(nodes),
        "M_R": compute_mr(len(completed), orphaned_count),
        "M_E": compute_me(total_energy, total_transmission, len(completed)),
    }