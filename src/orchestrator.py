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

from src.env.topology import build_topology
from src.schemas import AllocationDecision, Task, TaskState
from src.strategies.base import AllocationStrategy


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class Orchestrator:
    """Main simulation orchestrator.

    Pulls tasks from a pending store, asks a strategy where to run them,
    and simulates their execution on the target node.
    """

    def __init__(
        self,
        env: simpy.Environment,
        pending_store: simpy.Store,
        strategy: AllocationStrategy,
        nodes: dict,
    ) -> None:
        self.env = env
        self.pending_store = pending_store
        self.strategy = strategy
        self.nodes = nodes
        self.decision_count = 0
        self.completed_tasks: list[Task] = []

    def run(self):
        """Main orchestration loop."""
        while True:
            task = yield self.pending_store.get()
            decision = self.strategy.allocate(task, self.env.now)
            self.decision_count += 1

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

    def execute_task(self, node, task: Task):
        """Simulate execution of a task on a node."""
        node.cpu_utilized += task.cpu_units
        try:
            yield self.env.timeout(task.cpu_units)
        finally:
            node.cpu_utilized -= task.cpu_units
            # --- Mark task as completed ---
            task.state = TaskState.COMPLETED
            task.completion_time = self.env.now
            task.assigned_node = node.id
            self.completed_tasks.append(task)


def task_arrival(env: simpy.Environment, pending_store: simpy.Store,
                 num_tasks: int = 5):
    """Emit one dummy Task per simulated second."""

    i = 0
    while num_tasks is None or i < num_tasks:
        yield env.timeout(1)
        task = Task(
            id=f"task_{i}",
            arrival_time=env.now,
            cpu_units=1.0,
            ram_units=1.0,
        )
        yield pending_store.put(task)
        logger.info("Task %s arrived at t=%s", task.id, env.now)
        i += 1


def main() -> None:
    logger.info("Simulation démarrée à t=0")

    env = simpy.Environment()
    pending_store = simpy.Store(env)

    nodes, links = build_topology()

    # Local smoke-test strategy: always route to LEO-1.
    class _SmokeStrategy(AllocationStrategy):
        def allocate(self, task: Task, current_time: float) -> AllocationDecision:
            return AllocationDecision(
                task_id=task.id,
                chosen_node_id="LEO-1",
                score=1.0,
                reason="Smoke: always LEO-1",
            )

    strategy = _SmokeStrategy()
    orchestrator = Orchestrator(env, pending_store, strategy, nodes)

    env.process(orchestrator.run())
    env.process(task_arrival(env, pending_store, num_tasks=5))

    env.run(until=10)

    logger.info("Simulation ended at t=%s", env.now)
    logger.info("Total decisions: %s", orchestrator.decision_count)
    logger.info(
        "LEO-1 CPU used: %s / %s",
        nodes["LEO-1"].cpu_utilized,
        nodes["LEO-1"].cpu_capacity,
    )


if __name__ == "__main__":
    main()
