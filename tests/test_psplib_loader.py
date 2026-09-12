import pytest

from src.env.psplib_loader import load_psplib


def test_j30():
    tasks = load_psplib("data/j3010_1.sm")

    # 30 real tasks (supersource and supersink excluded)
    assert len(tasks) == 30

    # First real task is job 2 (job 1 = supersource, filtered)
    assert tasks[0]["id"] == 2

    # Task 5's only predecessor is task 4
    task_5 = next(
        task
        for task in tasks
        if task["id"] == 5
    )
    assert task_5["predecessors"] == [4]


def test_j30_no_supersource_sink():
    """Verify supersource (job 1) and supersink (job 32) are excluded."""
    tasks = load_psplib("data/j3010_1.sm")
    ids = {t["id"] for t in tasks}

    assert 1 not in ids, "Supersource (job 1) should be filtered"
    assert 32 not in ids, "Supersink (job 32) should be filtered"


def test_j30_duration():
    tasks = load_psplib("data/j3010_1.sm")

    # All remaining tasks have duration > 0 or non-zero resources
    task_2 = next(t for t in tasks if t["id"] == 2)
    assert task_2["duration"] == 2


def test_j30_resources():
    tasks = load_psplib("data/j3010_1.sm")

    task_2 = next(t for t in tasks if t["id"] == 2)
    assert task_2["resources"] == [1, 2, 4, 0]


def test_j30_predecessor_reversal():
    """Verify that successors are correctly reversed into predecessors."""
    tasks = load_psplib("data/j3010_1.sm")
    task_map = {t["id"]: t for t in tasks}

    # Task 10 has predecessors [2, 9]
    assert task_map[10]["predecessors"] == [2, 9]

    # Task 18 has predecessors [6, 7, 17]
    assert task_map[18]["predecessors"] == [6, 7, 17]


def test_j30_schema():
    """Verify every task has exactly the 4 required keys."""
    tasks = load_psplib("data/j3010_1.sm")

    required_keys = {"id", "duration", "predecessors", "resources"}

    for task in tasks:
        assert set(task.keys()) == required_keys


def test_j30_sorted():
    """Verify tasks are returned sorted by ID."""
    tasks = load_psplib("data/j3010_1.sm")
    ids = [t["id"] for t in tasks]
    assert ids == sorted(ids)


# =========================================================
# Error tests (Fix #7)
# =========================================================

def test_missing_file():
    """Verify FileNotFoundError for non-existent file."""
    with pytest.raises(FileNotFoundError):
        load_psplib("data/inexistant.sm")


def test_missing_section(tmp_path):
    """Verify ValueError for file missing required sections."""
    f = tmp_path / "bad.sm"
    f.write_text("AUCUNE SECTION")
    with pytest.raises(ValueError):
        load_psplib(f)


def test_empty_file(tmp_path):
    """Verify ValueError for empty file."""
    f = tmp_path / "empty.sm"
    f.write_text("")
    with pytest.raises(ValueError):
        load_psplib(f)
