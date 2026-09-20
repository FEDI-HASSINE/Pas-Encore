"""Always Orbital allocation strategy (Strategy 2)."""

from __future__ import annotations

from src.schemas import AllocationDecision, Task
from src.strategies.base import AllocationStrategy


class AlwaysOrbitalStrategy(AllocationStrategy):
    """Route every task to the first orbital node."""

    def allocate(
        self,
        task: Task,
        current_time: float,
    ) -> AllocationDecision:
        """Return a decision targeting ``LEO-1``."""
        return AllocationDecision(
            task_id=task.id,
            chosen_node_id="LEO-1",
            reason="S2 Always Orbital: route task to LEO-1.",
        )
