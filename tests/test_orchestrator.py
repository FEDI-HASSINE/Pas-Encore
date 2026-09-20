"""Tests for src/orchestrator.py using the real Node and Task classes."""

import simpy
import pytest

from src.env.topology import build_topology
from src.schemas import AllocationDecision, Task, TaskState
from src.strategies.base import AllocationStrategy
from src.orchestrator import Orchestrator, task_arrival


class _AlwaysLEO1(AllocationStrategy):
    """Test strategy: always routes to LEO-1."""

    def allocate(self, task: Task, current_time: float) -> AllocationDecision:
        return AllocationDecision(
            task_id=task.id,
            chosen_node_id="LEO-1",
            score=1.0,
            reason="Test: always LEO-1",
        )


class _AlwaysMissing(AllocationStrategy):
    """Test strategy: always routes to a non-existent node."""

    def allocate(self, task: Task, current_time: float) -> AllocationDecision:
        return AllocationDecision(
            task_id=task.id,
            chosen_node_id="GHOST",
            reason="Test: missing node",
        )


def test_orchestrator_executes_task_and_releases_cpu():
    env = simpy.Environment()
    pending_store = simpy.Store(env)
    nodes, _ = build_topology()

    task = Task(
        id="t1",
        arrival_time=0.0,
        cpu_units=3.0,
        ram_units=1.0,
    )
    pending_store.put(task)

    orch = Orchestrator(env, pending_store, _AlwaysLEO1(), nodes)
    env.process(orch.run())
    env.run(until=1)

    # Task is executing: CPU should be 3.0 (not yet released)
    assert nodes["LEO-1"].cpu_utilized == pytest.approx(3.0)
    assert orch.decision_count == 1

    env.run(until=4)

    # Task finished: CPU should be back to 0.0
    assert nodes["LEO-1"].cpu_utilized == pytest.approx(0.0)


def test_orchestrator_drops_task_when_node_missing():
    env = simpy.Environment()
    pending_store = simpy.Store(env)
    nodes, _ = build_topology()

    task = Task(
        id="t2",
        arrival_time=0.0,
        cpu_units=1.0,
        ram_units=1.0,
    )
    pending_store.put(task)

    orch = Orchestrator(env, pending_store, _AlwaysMissing(), nodes)
    env.process(orch.run())
    env.run(until=2)

    # Decision was counted, but no node was touched
    assert orch.decision_count == 1
    for node in nodes.values():
        assert node.cpu_utilized == pytest.approx(0.0)


def test_task_arrival_generator_emits_tasks():
    env = simpy.Environment()
    pending_store = simpy.Store(env)

    env.process(task_arrival(env, pending_store, num_tasks=3))
    env.run(until=10)

    assert len(pending_store.items) == 3
    assert pending_store.items[0].id == "task_0"
    assert all(
        isinstance(t, Task) and t.state == TaskState.PENDING
        for t in pending_store.items
    )
