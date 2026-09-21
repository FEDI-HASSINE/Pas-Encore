"""Tests for src/metrics/calculator.py."""

import pytest

from src.schemas import Task, TaskState
from src.metrics.calculator import (
    compute_all,
    compute_me,
    compute_ml,
    compute_mr,
    compute_mt,
)


class _FakeNode:
    def __init__(self, cpu_utilized: float, cpu_capacity: float):
        self.cpu_utilized = cpu_utilized
        self.cpu_capacity = cpu_capacity


def _task(tid: str, arrival: float, completion: float, state=TaskState.COMPLETED):
    return Task(
        id=tid,
        arrival_time=arrival,
        cpu_units=1.0,
        ram_units=1.0,
        state=state,
        completion_time=completion,
    )


# --- compute_mt ---

def test_compute_mt_basic():
    tasks = [_task("t1", 0.0, 10.0), _task("t2", 5.0, 20.0)]
    assert compute_mt(tasks) == pytest.approx(20.0)


def test_compute_mt_no_completed():
    tasks = [_task("t1", 0.0, 10.0, state=TaskState.PENDING)]
    assert compute_mt(tasks) == 0.0


def test_compute_mt_empty():
    assert compute_mt([]) == 0.0


# --- compute_ml ---

def test_compute_ml_perfect_balance():
    nodes = {"n1": _FakeNode(50.0, 100.0), "n2": _FakeNode(50.0, 100.0)}
    assert compute_ml(nodes) == pytest.approx(0.0)


def test_compute_ml_imbalanced():
    nodes = {"n1": _FakeNode(100.0, 100.0), "n2": _FakeNode(0.0, 100.0)}
    assert compute_ml(nodes) > 0.0


def test_compute_ml_single_node():
    assert compute_ml({"n1": _FakeNode(50.0, 100.0)}) == 0.0


# --- compute_mr ---

def test_compute_mr_perfect():
    assert compute_mr(10, 10) == 1.0


def test_compute_mr_zero():
    assert compute_mr(0, 10) == 0.0


def test_compute_mr_no_orphans():
    assert compute_mr(0, 0) == 1.0


# --- compute_me ---

def test_compute_me_basic():
    assert compute_me(100.0, 50.0, 10) == pytest.approx(15.0)


def test_compute_me_zero_completed():
    assert compute_me(100.0, 50.0, 0) == 0.0


# --- compute_all ---

def test_compute_all_returns_four_keys():
    tasks = [_task("t1", 0.0, 10.0)]
    nodes = {"n1": _FakeNode(50.0, 100.0)}
    result = compute_all(tasks, nodes)
    assert set(result.keys()) == {"M_T", "M_L", "M_R", "M_E"}