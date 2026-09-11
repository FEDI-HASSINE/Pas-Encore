from src.env.psplib_loader import load_psplib


def test_j30():
    tasks = load_psplib("data/j3010_1.sm")

    # j3010_1.sm has 32 jobs (30 activities + supersource + supersink)
    assert len(tasks) == 32

    # Task 1 is the supersource — no predecessors
    assert tasks[0]["id"] == 1
    assert tasks[0]["predecessors"] == []

    # Task 5's only predecessor is task 4
    task_5 = next(
        task
        for task in tasks
        if task["id"] == 5
    )
    assert task_5["predecessors"] == [4]


def test_j30_duration():
    tasks = load_psplib("data/j3010_1.sm")

    assert tasks[0]["duration"] == 0
    assert tasks[-1]["duration"] == 0

    task_2 = next(t for t in tasks if t["id"] == 2)
    assert task_2["duration"] == 2


def test_j30_resources():
    tasks = load_psplib("data/j3010_1.sm")

    assert tasks[0]["resources"] == [0, 0, 0, 0]

    task_2 = next(t for t in tasks if t["id"] == 2)
    assert task_2["resources"] == [1, 2, 4, 0]


def test_j30_predecessor_reversal():
    """Verify that successors are correctly reversed into predecessors."""
    tasks = load_psplib("data/j3010_1.sm")
    task_map = {t["id"]: t for t in tasks}

    assert task_map[10]["predecessors"] == [2, 9]
    assert task_map[18]["predecessors"] == [6, 7, 17]
    assert task_map[32]["predecessors"] == [29, 30, 31]


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
