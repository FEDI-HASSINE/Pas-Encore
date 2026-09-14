"""SimPy orchestrator for the orbital task scheduler.

Run as a script:
    python src/orchestrator.py
"""

import logging
import sys
from pathlib import Path

import simpy

# Ensure the repository root is on sys.path so `src.*` imports work
# whether the script is run as `python src/orchestrator.py` or via pytest.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.strategies.base import AllocationStrategy, AllocationDecision


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class _DummyNode:
    """Temporary stand-in for M2's Node class."""

    def __init__(self, node_id: str, cpu_capacity: float = 100.0) -> None:
        self.id = node_id
        self.cpu_capacity = cpu_capacity
        self.cpu_utilized = 0.0


class _DummyStrategy(AllocationStrategy):
    """Always routes to LEO-1. For local smoke tests only."""

    def __init__(self, node: _DummyNode) -> None:
        self.node = node

    def allocate(self, task, current_time: float) -> AllocationDecision:
        return AllocationDecision(
            task_id=getattr(task, "id", "unknown"),
            chosen_node_id=self.node.id,
            score=1.0,
            reason="Dummy: always LEO-1",
        )


class Orchestrator:
    """Main simulation orchestrator."""

    def __init__(self, env, pending_store, strategy: AllocationStrategy,
                 nodes: dict) -> None:
        self.env = env
        self.pending_store = pending_store
        self.strategy = strategy
        self.nodes = nodes
        self._decision_count = 0

    def run(self):
        while True:
            task = yield self.pending_store.get()
            decision = self.strategy.allocate(task, self.env.now)
            self._decision_count += 1

            logger.info(
                "Task %s -> %s (reason: %s)",
                decision.task_id,
                decision.chosen_node_id,
                decision.reason,
            )

            node = self.nodes.get(decision.chosen_node_id)
            if node is None:
                logger.warning(
                    "Node %s not found, task %s dropped",
                    decision.chosen_node_id,
                    decision.task_id,
                )
                continue

            self.env.process(self.execute_task(node, task))

    def execute_task(self, node, task):
        cpu_units = getattr(task, "cpu_units", 1.0)
        node.cpu_utilized += cpu_units
        try:
            yield self.env.timeout(cpu_units)
        finally:
            node.cpu_utilized -= cpu_units


def task_arrival(env, pending_store, num_tasks: int = 5):
    """Emit one dummy task per simulated second."""

    class _DummyTask:
        def __init__(self, i: int) -> None:
            self.id = f"task_{i}"
            self.cpu_units = 1.0

    i = 0
    while num_tasks is None or i < num_tasks:
        yield env.timeout(1)
        task = _DummyTask(i)
        yield pending_store.put(task)
        logger.info("Task %s arrived at t=%s", task.id, env.now)
        i += 1


def main() -> None:
    logger.info("Simulation démarrée à t=0")

    env = simpy.Environment()
    pending_store = simpy.Store(env)

    leo1 = _DummyNode("LEO-1")
    nodes = {"LEO-1": leo1}

    strategy = _DummyStrategy(leo1)

    orchestrator = Orchestrator(env, pending_store, strategy, nodes)

    env.process(orchestrator.run())
    env.process(task_arrival(env, pending_store, num_tasks=5))

    env.run(until=10)

    logger.info("Simulation ended at t=%s", env.now)
    logger.info("Total decisions: %s", orchestrator._decision_count)
    logger.info("LEO-1 CPU used: %s / %s",
                leo1.cpu_utilized, leo1.cpu_capacity)


if __name__ == "__main__":
    main()