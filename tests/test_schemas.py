"""Tests for src/schemas.py — shared Pydantic models."""

import pytest
from pydantic import ValidationError

from src.schemas import (
    AllocationDecision,
    NodeState,
    RunTelemetry,
    StrategyID,
    Task,
    TaskState,
)


# --- StrategyID ---
def test_strategy_ids_are_1_to_5():
    assert StrategyID.ALWAYS_GROUND == 1
    assert StrategyID.ALWAYS_ORBITAL == 2
    assert StrategyID.GREEDY == 3
    assert StrategyID.DYNAMIC_RESILIENT == 4
    assert StrategyID.RL_AGENT == 5


# --- TaskState ---
def test_task_states_are_0_to_5():
    assert TaskState.PENDING == 0
    assert TaskState.ORPHANED == 5


# --- Task ---
def test_task_minimal_creation():
    t = Task(id="t1", arrival_time=0.0, cpu_units=5.0, ram_units=10.0)
    assert t.id == "t1"
    assert t.state == TaskState.PENDING
    assert t.priority == 1
    assert t.data_size_mb == 1.0
    assert t.assigned_node is None
    assert t.start_time is None
    assert t.completion_time is None


def test_task_rejects_missing_required_fields():
    with pytest.raises(ValidationError):
        Task(id="t2", arrival_time=0.0, cpu_units=5.0)  # missing ram_units


def test_task_state_transition_is_tracked():
    t = Task(id="t3", arrival_time=0.0, cpu_units=1.0, ram_units=1.0)
    t.state = TaskState.EXECUTING
    t.assigned_node = "LEO-1"
    assert t.state == TaskState.EXECUTING
    assert t.assigned_node == "LEO-1"


# --- NodeState ---
def test_nodestate_defaults():
    n = NodeState(
        id="LEO-1",
        cpu_capacity=10.0,
        ram_capacity=32.0,
        energy_cost_per_cpu=2.0,
    )
    assert n.cpu_utilized == 0.0
    assert n.ram_utilized == 0.0
    assert n.available is True


# --- AllocationDecision ---
def test_allocation_decision_defaults():
    d = AllocationDecision(task_id="t1", chosen_node_id="LEO-1")
    assert d.score is None
    assert d.reason == ""


def test_allocation_decision_with_score_and_reason():
    d = AllocationDecision(
        task_id="t1",
        chosen_node_id="LEO-2",
        score=0.87,
        reason="Greedy: best CPU headroom",
    )
    assert d.score == 0.87
    assert "Greedy" in d.reason


# --- RunTelemetry ---
def test_run_telemetry_defaults():
    r = RunTelemetry(
        run_id="run_001",
        strategy=StrategyID.GREEDY,
        profile="burst",
    )
    assert r.metrics == {}
    assert r.truncation_flag is False


# --- Cross-class consistency ---
def test_task_and_decision_share_id_type():
    t = Task(id="tX", arrival_time=0.0, cpu_units=1.0, ram_units=1.0)
    d = AllocationDecision(task_id=t.id, chosen_node_id="LEO-1")
    assert d.task_id == t.id
    assert isinstance(d.task_id, str)
