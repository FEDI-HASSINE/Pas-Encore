"""Tests for the static baseline allocation strategies."""

from src.schemas import Task
from src.strategies.s1_always_ground import AlwaysGroundStrategy
from src.strategies.s2_always_orbital import AlwaysOrbitalStrategy


def _task(task_id: str = "task-1") -> Task:
    return Task(
        id=task_id,
        arrival_time=0.0,
        cpu_units=1.0,
        ram_units=1.0,
    )


def test_always_ground_routes_every_task_to_cloud() -> None:
    strategy = AlwaysGroundStrategy()

    first = strategy.allocate(_task("task-1"), current_time=0.0)
    second = strategy.allocate(_task("task-2"), current_time=100.0)

    assert first.chosen_node_id == "Cloud-AWS"
    assert second.chosen_node_id == "Cloud-AWS"
    assert first.task_id == "task-1"
    assert second.task_id == "task-2"


def test_always_orbital_routes_every_task_to_leo_1() -> None:
    strategy = AlwaysOrbitalStrategy()

    first = strategy.allocate(_task("task-1"), current_time=0.0)
    second = strategy.allocate(_task("task-2"), current_time=100.0)

    assert first.chosen_node_id == "LEO-1"
    assert second.chosen_node_id == "LEO-1"
    assert first.task_id == "task-1"
    assert second.task_id == "task-2"
