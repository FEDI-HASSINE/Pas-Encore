"""Allocation strategy interface for the orbital scheduler.

Every strategy (S1 to S5) inherits from AllocationStrategy and
implements the `allocate` method.

AllocationDecision is imported from src.schemas — do NOT redefine it
locally.
"""

from abc import ABC, abstractmethod

from src.schemas import AllocationDecision


class AllocationStrategy(ABC):
    """Common interface for all allocation strategies."""

    @abstractmethod
    def allocate(self, task, current_time: float) -> AllocationDecision:
        """Choose a node to execute the given task.

        Args:
            task: The task to allocate (src.schemas.Task once available;
                  duck-typed until then).
            current_time: Current simulation time (SimPy env.now).

        Returns:
            AllocationDecision describing the chosen node.
        """
        raise NotImplementedError
