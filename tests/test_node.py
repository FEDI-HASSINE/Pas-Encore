import pytest
from src.env.node import Node


def test_node_acceptance_criterion():
    """Acceptance criterion: Node('LEO-1', cpu=10) has cpu_utilized == 0.0."""
    node = Node("LEO-1", cpu=10)
    assert node.id == "LEO-1"
    assert node.cpu_capacity == 10.0
    assert node.cpu_utilized == 0.0
    assert node.active_tasks == []


def test_node_pydantic_attributes():
    """Verify all required Pydantic attributes exist and match expected defaults."""
    node = Node(id="LEO-2", cpu_capacity=10.0, ram_capacity=32.0, energy_cost=2.0)
    assert node.id == "LEO-2"
    assert node.cpu_capacity == 10.0
    assert node.ram_capacity == 32.0
    assert node.energy_cost == 2.0
    assert node.cpu_utilized == 0.0
    assert isinstance(node.active_tasks, list)


def test_node_positional_initialization():
    """Verify initialization with positional arguments."""
    node = Node("GS-Tunisia", 20.0, 64.0, 0.5)
    assert node.id == "GS-Tunisia"
    assert node.cpu_capacity == 20.0
    assert node.ram_capacity == 64.0
    assert node.energy_cost == 0.5


def test_node_aliases():
    """Verify aliases 'cpu', 'ram', and 'energy' work seamlessly."""
    node = Node(id="Cloud-AWS", cpu=100.0, ram=256.0, energy=0.1)
    assert node.id == "Cloud-AWS"
    assert node.cpu_capacity == 100.0
    assert node.ram_capacity == 256.0
    assert node.energy_cost == 0.1


def test_add_task_increments_cpu_utilized():
    """Acceptance criterion: add_task(task) increments cpu_utilized."""
    node = Node("LEO-1", cpu=10)

    # 1. Add task via dict with cpu_units
    t1 = {"id": "t1", "cpu_units": 3.0}
    res = node.add_task(t1)
    assert res == 3.0
    assert node.cpu_utilized == 3.0
    assert t1 in node.active_tasks

    # 2. Add task via numeric value
    node.add_task(2.5)
    assert node.cpu_utilized == 5.5
    assert len(node.active_tasks) == 2

    # 3. Add task via object with attribute cpu_units
    class DummyTask:
        def __init__(self, task_id: str, cpu_units: float):
            self.id = task_id
            self.cpu_units = cpu_units

    t3 = DummyTask("t3", 1.5)
    node.add_task(t3)
    assert node.cpu_utilized == 7.0
    assert len(node.active_tasks) == 3


def test_remove_task_decrements_cpu_utilized():
    """Verify remove_task releases resources and updates active_tasks."""
    node = Node("LEO-1", cpu=10)
    t1 = {"id": "t1", "cpu_units": 4.0}
    t2 = {"id": "t2", "cpu_units": 2.0}

    node.add_task(t1)
    node.add_task(t2)
    assert node.cpu_utilized == 6.0
    assert len(node.active_tasks) == 2

    # Remove t1
    node.remove_task(t1)
    assert node.cpu_utilized == 2.0
    assert t1 not in node.active_tasks
    assert t2 in node.active_tasks

    # Remove t2
    node.remove_task(t2)
    assert node.cpu_utilized == 0.0
    assert node.active_tasks == []


def test_remove_task_clamping():
    """Verify cpu_utilized does not go below 0.0."""
    node = Node("LEO-1", cpu=10)
    node.add_task(1.0)
    node.remove_task(5.0)
    assert node.cpu_utilized == 0.0


def test_is_available():
    """Verify capacity checking."""
    node = Node("LEO-1", cpu=10)
    assert node.is_available(5.0) is True
    assert node.is_available(10.0) is True
    assert node.is_available(10.1) is False

    node.add_task(8.0)
    assert node.is_available(2.0) is True
    assert node.is_available(2.5) is False


def test_reset():
    """Verify reset clears active tasks and sets cpu_utilized to 0.0."""
    node = Node("LEO-1", cpu=10)
    node.add_task(5.0)
    assert node.cpu_utilized == 5.0
    assert len(node.active_tasks) == 1

    node.reset()
    assert node.cpu_utilized == 0.0
    assert node.active_tasks == []
