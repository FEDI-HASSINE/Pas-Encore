"""Shared Pydantic state models for the orbital scheduler.

This is the SINGLE SOURCE OF TRUTH for all data structures exchanged
between:
  - the task generator (M3)   -> Task
  - the environment nodes (M2) -> NodeState
  - the strategies (M3, M4)    -> AllocationDecision, StrategyID
  - the orchestrator (M4)      -> RunTelemetry
  - the metrics calculator (M1) -> RunTelemetry

Do NOT duplicate these classes elsewhere. If a new field is needed,
modify the model here, update the corresponding tests, and inform the
team via the PR description.
"""

from enum import IntEnum
from typing import Any, Optional

from pydantic import BaseModel, Field


class StrategyID(IntEnum):
    """Identifier for each allocation strategy (S1 to S5)."""

    ALWAYS_GROUND = 1
    ALWAYS_ORBITAL = 2
    GREEDY = 3
    DYNAMIC_RESILIENT = 4
    RL_AGENT = 5


class TaskState(IntEnum):
    """Lifecycle states of a task."""

    PENDING = 0
    SCHEDULED = 1
    EXECUTING = 2
    COMPLETED = 3
    FAILED = 4
    ORPHANED = 5


class Task(BaseModel):
    """A computational task to be scheduled on a node."""

    id: str
    arrival_time: float
    cpu_units: float
    ram_units: float
    priority: int = 1
    data_size_mb: float = 1.0
    state: TaskState = TaskState.PENDING
    assigned_node: Optional[str] = None
    start_time: Optional[float] = None
    completion_time: Optional[float] = None

<<<<<<< HEAD
=======
    # --- Profile-specific optional metadata ---
    # Populated by src/env/task_generator.py for the Energy, Mixed,
    # and Radiation profiles. Consumed by the orchestrator and the
    # metrics calculator for resilience analysis (M_R).
    energy_budget: Optional[float] = None
    deadline: Optional[float] = None
    failure_mode: Optional[str] = None
    failure_time: Optional[float] = None

>>>>>>> 0e2a8f61881414aad4ed65106a5528d33b79c2f9

class NodeState(BaseModel):
    """Plain data snapshot of a node's state.

    The rich Node class (src/env/node.py) provides behavior; this
    schema is a lightweight data-transfer representation used by
    telemetry and reporting.
    """

    id: str
    cpu_capacity: float
    cpu_utilized: float = 0.0
    ram_capacity: float
    ram_utilized: float = 0.0
    energy_cost_per_cpu: float
    available: bool = True


class AllocationDecision(BaseModel):
    """Result of a routing decision produced by a strategy."""

    task_id: str
    chosen_node_id: str
    score: Optional[float] = None
    reason: str = ""


class RunTelemetry(BaseModel):
    """Aggregated metrics and decisions for one simulation run."""

    run_id: str
    strategy: StrategyID
    profile: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    truncation_flag: bool = False
