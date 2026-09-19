"""Tests for the Greedy score-based allocation strategy (S3)."""

import pytest

from src.env.topology import build_topology
from src.schemas import Task
from src.strategies.greedy import GreedyStrategy


def _make_task(
    task_id: str = "task-1",
    cpu_units: float = 2.0,
    data_size_mb: float = 10.0,
) -> Task:
    """Create a simple task for GreedyStrategy tests."""
    return Task(
        id=task_id,
        arrival_time=0.0,
        cpu_units=cpu_units,
        ram_units=1.0,
        data_size_mb=data_size_mb,
    )


def test_greedy_strategy_can_be_created():
    """S3 should accept the real project nodes and links."""
    nodes, links = build_topology()

    strategy = GreedyStrategy(nodes, links)

    assert strategy.nodes is nodes
    assert strategy.links is links


def test_greedy_filters_nodes_without_cpu_capacity():
    """Nodes without enough remaining CPU must not be candidates."""
    nodes, links = build_topology()

    nodes["LEO-1"].cpu_utilized = 9.0
    nodes["LEO-2"].cpu_utilized = 9.0
    nodes["GS-Tunisia"].cpu_utilized = 19.0
    nodes["Cloud-AWS"].cpu_utilized = 99.0

    strategy = GreedyStrategy(nodes, links)
    task = _make_task(cpu_units=2.0)

    decision = strategy.allocate(
        task,
        current_time=0.0,
    )

    assert decision.chosen_node_id == ""
    assert decision.score is None
    assert "No node" in decision.reason


def test_projected_cpu_cost_prefers_less_loaded_node():
    """Projected CPU utilization must favor a less-loaded equivalent node."""
    nodes, links = build_topology()

    # Isolate the two equivalent LEO nodes.
    nodes["GS-Tunisia"].cpu_utilized = 20.0
    nodes["Cloud-AWS"].cpu_utilized = 100.0

    # LEO-1 is heavily loaded.
    nodes["LEO-1"].cpu_utilized = 8.0

    # LEO-2 is idle.
    nodes["LEO-2"].cpu_utilized = 0.0

    strategy = GreedyStrategy(nodes, links)
    task = _make_task(cpu_units=1.0)

    # At t=3000, LEO-2 has its scheduled ground link active.
    # Both LEO nodes also have the always-active ISL, so their best
    # communication bandwidth is identical (50 Mbps).
    #
    # Their energy costs are also identical. CPU load is therefore
    # the criterion that differentiates them.
    decision = strategy.allocate(
        task,
        current_time=3000.0,
    )

    assert decision.chosen_node_id == "LEO-2"
    assert decision.score is not None


def test_communication_cost_uses_active_link_bandwidth():
    """Communication estimate should use the best active connected link."""
    nodes, links = build_topology()

    strategy = GreedyStrategy(nodes, links)
    task = _make_task(
        cpu_units=1.0,
        data_size_mb=10.0,
    )

    # Cloud-AWS has a permanent 100 Mbps link to GS-Tunisia.
    cost = strategy._communication_cost(
        node_id="Cloud-AWS",
        task=task,
        current_time=0.0,
    )

    # 10 MB = 80 megabits.
    # 80 / 100 Mbps = 0.8 seconds.
    assert cost == pytest.approx(0.8)


def test_normalization_converts_lower_cost_to_higher_suitability():
    """Lower costs should become higher normalized suitability values."""
    costs = {
        "A": 1.0,
        "B": 2.0,
        "C": 3.0,
    }

    suitability = GreedyStrategy._normalize_costs(
        costs
    )

    assert suitability["A"] == pytest.approx(1.0)
    assert suitability["B"] == pytest.approx(0.5)
    assert suitability["C"] == pytest.approx(0.0)


def test_normalization_handles_infinite_cost():
    """An unreachable communication candidate should receive zero suitability."""
    costs = {
        "reachable": 1.0,
        "unreachable": float("inf"),
    }

    suitability = GreedyStrategy._normalize_costs(
        costs
    )

    assert suitability["reachable"] == pytest.approx(1.0)
    assert suitability["unreachable"] == pytest.approx(0.0)


def test_greedy_returns_real_allocation_decision():
    """S3 must return a scored decision for a normal incoming task."""
    nodes, links = build_topology()

    strategy = GreedyStrategy(nodes, links)
    task = _make_task()

    decision = strategy.allocate(
        task,
        current_time=0.0,
    )

    assert decision.task_id == task.id
    assert decision.chosen_node_id in nodes
    assert decision.score is not None
    assert 0.0 <= decision.score <= 1.0
    assert "Greedy S3" in decision.reason


def test_greedy_is_deterministic_for_same_state():
    """Identical state and task should produce the same decision."""
    nodes, links = build_topology()

    strategy = GreedyStrategy(nodes, links)
    task = _make_task()

    first = strategy.allocate(
        task,
        current_time=0.0,
    )

    second = strategy.allocate(
        task,
        current_time=0.0,
    )

    assert first.chosen_node_id == second.chosen_node_id
    assert first.score == pytest.approx(second.score)