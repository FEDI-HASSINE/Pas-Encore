from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field, ConfigDict, AliasChoices


class Node(BaseModel):
    """Physical compute node representation (Orbital Satellite, Ground Station, or Cloud).

    Attributes:
        id: Unique identifier for the node (e.g., 'LEO-1', 'GS-Tunisia', 'Cloud-AWS').
        cpu_capacity: Total compute capacity (units). Aliased as 'cpu'.
        ram_capacity: Total memory capacity (GB/units). Aliased as 'ram'.
        energy_cost: Relative energy cost per compute unit. Aliased as 'energy'.
        cpu_utilized: Current instantaneous CPU usage.
        active_tasks: List of currently running tasks on this node.
    """

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: str
    cpu_capacity: float = Field(
        default=10.0,
        validation_alias=AliasChoices("cpu_capacity", "cpu"),
        description="Total CPU capacity",
    )
    ram_capacity: float = Field(
        default=32.0,
        validation_alias=AliasChoices("ram_capacity", "ram"),
        description="Total RAM capacity",
    )
    energy_cost: float = Field(
        default=1.0,
        validation_alias=AliasChoices("energy_cost", "energy"),
        description="Energy cost per CPU unit",
    )
    cpu_utilized: float = Field(
        default=0.0,
        description="Current CPU utilization",
    )
    active_tasks: list[Any] = Field(
        default_factory=list,
        description="List of tasks currently executing on this node",
    )
    node_type: str = Field(
        default="",
        description="Node type (Orbital Satellite, Ground Station, Terrestrial Cloud)",
    )
    startup_penalty: float = Field(
        default=0.0,
        description="Startup energy penalty",
    )
    sensor_noise: float = Field(
        default=0.0,
        description="Sensor telemetry noise percentage",
    )

    def __init__(
        self,
        id: str | None = None,
        cpu_capacity: float | None = None,
        ram_capacity: float | None = None,
        energy_cost: float | None = None,
        cpu_utilized: float = 0.0,
        active_tasks: list[Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize Node, supporting positional arguments and keyword aliases."""
        data: dict[str, Any] = dict(kwargs)
        if id is not None:
            data["id"] = id
        if cpu_capacity is not None and "cpu" not in data and "cpu_capacity" not in data:
            data["cpu_capacity"] = cpu_capacity
        if ram_capacity is not None and "ram" not in data and "ram_capacity" not in data:
            data["ram_capacity"] = ram_capacity
        if energy_cost is not None and "energy" not in data and "energy_cost" not in data:
            data["energy_cost"] = energy_cost
        if cpu_utilized != 0.0 and "cpu_utilized" not in data:
            data["cpu_utilized"] = cpu_utilized
        if active_tasks is not None and "active_tasks" not in data:
            data["active_tasks"] = active_tasks

        super().__init__(**data)

    @staticmethod
    def _extract_cpu_units(task: Any) -> float:
        """Extract CPU requirement from task object, dictionary, or numeric value."""
        if isinstance(task, (int, float)):
            return float(task)
        if hasattr(task, "cpu_units"):
            return float(getattr(task, "cpu_units"))
        if isinstance(task, dict):
            if "cpu_units" in task:
                return float(task["cpu_units"])
            if "cpu" in task:
                return float(task["cpu"])
            if "duration" in task:
                # If psplib task without explicit cpu_units, default to 1.0
                return float(task.get("cpu_units", 1.0))
        return float(getattr(task, "cpu_units", 1.0))

    def add_task(self, task: Any) -> float:
        """Add a task to the node and increment cpu_utilized.

        Args:
            task: Task instance, dict, or numeric CPU requirement.

        Returns:
            The updated cpu_utilized value.
        """
        cpu_units = self._extract_cpu_units(task)
        self.active_tasks.append(task)
        self.cpu_utilized += cpu_units
        return self.cpu_utilized

    def remove_task(self, task: Any) -> float:
        """Remove a task from the node and decrement cpu_utilized.

        Args:
            task: Task instance, dict, or numeric CPU requirement.

        Returns:
            The updated cpu_utilized value.
        """
        cpu_units = self._extract_cpu_units(task)
        if task in self.active_tasks:
            self.active_tasks.remove(task)
        self.cpu_utilized = max(0.0, self.cpu_utilized - cpu_units)
        return self.cpu_utilized

    def is_available(self, required_cpu: float = 1.0) -> bool:
        """Check if node has enough capacity to accept additional CPU load."""
        return (self.cpu_utilized + required_cpu) <= self.cpu_capacity

    def reset(self) -> None:
        """Reset node utilization and clear active tasks."""
        self.cpu_utilized = 0.0
        self.active_tasks.clear()
