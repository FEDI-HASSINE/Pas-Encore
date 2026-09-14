import simpy

from src.orchestrator import Orchestrator
from src.strategies.base import AllocationDecision, AllocationStrategy


class DummyTask:
    def __init__(self, task_id, cpu_units):
        self.id = task_id
        self.cpu_units = cpu_units


class DummyNode:
    def __init__(self, node_id):
        self.id = node_id
        self.cpu_utilized = 0.0


class DummyStrategy(AllocationStrategy):
    def __init__(self, node_id):
        self.node_id = node_id

    def allocate(self, task, current_time):
        return AllocationDecision(
            task_id=task.id,
            chosen_node_id=self.node_id,
            score=1.0,
            reason="test",
        )


def test_orchestrator_executes_task():
    env = simpy.Environment()
    pending_store = simpy.Store(env)

    node = DummyNode("LEO-1")
    nodes = {"LEO-1": node}

    strategy = DummyStrategy("LEO-1")

    orchestrator = Orchestrator(
        env=env,
        pending_store=pending_store,
        strategy=strategy,
        nodes=nodes,
    )

    env.process(orchestrator.run())

    task = DummyTask(
        task_id="task_1",
        cpu_units=3,
    )

    pending_store.put(task)

    env.run(until=1)

    assert node.cpu_utilized == 3

    env.run(until=4)

    assert node.cpu_utilized == 0
    assert orchestrator._decision_count == 1


def test_orchestrator_drops_task_when_node_missing():
    env = simpy.Environment()
    pending_store = simpy.Store(env)

    nodes = {}

    strategy = DummyStrategy("MISSING-NODE")

    orchestrator = Orchestrator(
        env=env,
        pending_store=pending_store,
        strategy=strategy,
        nodes=nodes,
    )

    env.process(orchestrator.run())

    task = DummyTask(
        task_id="task_missing",
        cpu_units=2,
    )

    pending_store.put(task)

    env.run(until=1)

    assert orchestrator._decision_count == 1