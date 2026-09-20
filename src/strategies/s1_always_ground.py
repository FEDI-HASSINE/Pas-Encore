"""Always Ground allocation strategy (Strategy 1)."""

from __future__ import annotations

from src.schemas import AllocationDecision, Task
from src.strategies.base import AllocationStrategy


class AlwaysGroundStrategy(AllocationStrategy):
    """Route every task to the terrestrial cloud node."""

    def allocate(
        self,
        task: Task,
        current_time: float,
    ) -> AllocationDecision:
        """Return a decision targeting ``Cloud-AWS``."""
        return AllocationDecision(
            task_id=task.id,
            chosen_node_id="Cloud-AWS",
            reason="S1 Always Ground: route task to Cloud-AWS.",
        )
