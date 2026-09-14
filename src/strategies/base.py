"""Allocation strategy interface for the orbital scheduler.

Every strategy (S1 to S5) must inherit from AllocationStrategy and
implement the `allocate` method.

NOTE: AllocationDecision is temporarily defined here. Once
`src/schemas.py` is published by M2, this class MUST be removed and
imported from `src.schemas` instead. Do not duplicate it elsewhere.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AllocationDecision:
    """Result of a routing decision."""

    task_id: str
    chosen_node_id: str
    score: float | None = None
    reason: str = ""


class AllocationStrategy(ABC):
    """Common interface for all allocation strategies."""

    @abstractmethod
    def allocate(self, task, current_time: float) -> AllocationDecision:
        """Choose a node to execute the given task.

        Args:
            task: The task to allocate.
            current_time: Current simulation time (SimPy env.now).

        Returns:
            AllocationDecision describing the chosen node.
        """
        raise NotImplementedError