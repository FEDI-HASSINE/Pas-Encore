"""Greedy score-based allocation strategy (Strategy 3).

The strategy evaluates the currently available compute nodes for each
incoming task and selects the node with the highest suitability score.

The score is based on three criteria defined by the project specification:
    - current CPU load,
    - estimated energy consumption,
    - communication latency.

The weights follow the roadmap specification (docs/01_PROJECT_DESCRIPTION.md,
Section 3.2): CPU=0.4, Energy=0.4, Communication=0.2.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from src.schemas import AllocationDecision, Task
from src.strategies.base import AllocationStrategy


# ---------------------------------------------------------------------------
# Module-level constants with config fallback
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "experiment.yaml"

_DEFAULT_GREEDY_WEIGHTS = {
    "weight_cpu": 0.4,
    "weight_energy": 0.4,
    "weight_communication": 0.2,
    "bits_per_byte": 8.0,
}

_GREEDY_WEIGHTS_CACHE: dict[str, float] | None = None


def _load_greedy_weights() -> dict[str, float]:
    """Load greedy strategy weights from config/experiment.yaml with fallback."""
    global _GREEDY_WEIGHTS_CACHE

    if _GREEDY_WEIGHTS_CACHE is None:
        try:
            if _CONFIG_PATH.exists():
                with open(_CONFIG_PATH, "r") as f:
                    data = yaml.safe_load(f) or {}
                _GREEDY_WEIGHTS_CACHE = data.get("strategies", {}).get("greedy", {})
            else:
                _GREEDY_WEIGHTS_CACHE = {}
                logging.warning(
                    "Config file not found at %s, using hardcoded greedy defaults",
                    _CONFIG_PATH,
                )
        except Exception as e:
            _GREEDY_WEIGHTS_CACHE = {}
            logging.warning(
                "Failed to load greedy config from %s: %s, using hardcoded defaults",
                _CONFIG_PATH,
                e,
            )

    # Merge with defaults (defaults take precedence for missing keys)
    merged = {**_DEFAULT_GREEDY_WEIGHTS, **_GREEDY_WEIGHTS_CACHE}
    return merged


# Load weights at module import time
_WEIGHTS = _load_greedy_weights()
WEIGHT_CPU = _WEIGHTS["weight_cpu"]
WEIGHT_ENERGY = _WEIGHTS["weight_energy"]
WEIGHT_COMMUNICATION = _WEIGHTS["weight_communication"]
BITS_PER_BYTE = _WEIGHTS["bits_per_byte"]


class GreedyStrategy(AllocationStrategy):
    """Reactive score-based allocation strategy."""

    def __init__(self, nodes: dict, links: list | None = None) -> None:
        self.nodes = nodes
        self.links = links or []

    @staticmethod
    def _normalize_costs(costs: dict[str, float]) -> dict[str, float]:
        """Convert raw costs into suitability values between 0 and 1.

        Lower raw cost produces higher suitability.

        If all finite costs are equal, they receive suitability 1.0.
        Infinite costs receive suitability 0.0.
        """
        finite_values = [
            value
            for value in costs.values()
            if value != float("inf")
        ]

        if not finite_values:
            return {
                node_id: 0.0
                for node_id in costs
            }

        minimum = min(finite_values)
        maximum = max(finite_values)

        if minimum == maximum:
            return {
                node_id: (
                    0.0
                    if value == float("inf")
                    else 1.0
                )
                for node_id, value in costs.items()
            }

        return {
            node_id: (
                0.0
                if value == float("inf")
                else 1.0
                - (
                    (value - minimum)
                    / (maximum - minimum)
                )
            )
            for node_id, value in costs.items()
        }

    def _communication_cost(
        self,
        node_id: str,
        task: Task,
        current_time: float,
    ) -> float:
        """Estimate communication cost for a task.

        LIMITATION: The current Task schema has no source_node field, so
        this is a deterministic approximation based on data_size_mb and
        the best active link bandwidth at the candidate node. It is NOT
        an end-to-end source->destination latency model.

        Future work (Phase 3): add a source_node field to Task and compute
        the actual path cost.

        Estimated transmission time:
            data_size_mb * BITS_PER_BYTE / bandwidth_mbps

        A node without an active communication link receives infinite
        communication cost.
        """
        active_bandwidths = []

        for link in self.links:
            connected = (
                link.node1 == node_id
                or link.node2 == node_id
            )

            if connected and link.is_active(current_time):
                active_bandwidths.append(link.bandwidth)

        if not active_bandwidths:
            return float("inf")

        best_bandwidth = max(active_bandwidths)

        if best_bandwidth <= 0:
            return float("inf")

        return (
            task.data_size_mb * BITS_PER_BYTE
        ) / best_bandwidth

    def allocate(
        self,
        task: Task,
        current_time: float,
    ) -> AllocationDecision:
        """Choose the most suitable available node for a task."""

        # -------------------------------------------------------------
        # Candidate filtering
        # -------------------------------------------------------------
        available_nodes = [
            node
            for node in self.nodes.values()
            if node.is_available(task.cpu_units)
        ]

        if not available_nodes:
            return AllocationDecision(
                task_id=task.id,
                chosen_node_id="",
                score=None,
                reason="No node has enough available CPU capacity.",
            )

        # -------------------------------------------------------------
        # 1. CPU cost
        # -------------------------------------------------------------
        # Projected utilization after assigning the incoming task.
        # Lower is better.
        cpu_costs = {}

        for node in available_nodes:
            if node.cpu_capacity <= 0:
                cpu_costs[node.id] = float("inf")
                continue

            projected_cpu_load = (
                node.cpu_utilized + task.cpu_units
            ) / node.cpu_capacity

            cpu_costs[node.id] = projected_cpu_load

        # -------------------------------------------------------------
        # 2. Energy cost
        # -------------------------------------------------------------
        # Estimated execution energy.
        # Lower is better.
        energy_costs = {}

        for node in available_nodes:
            estimated_energy = (
                task.cpu_units * node.energy_cost
            )

            energy_costs[node.id] = estimated_energy

        # -------------------------------------------------------------
        # 3. Communication cost
        # -------------------------------------------------------------
        # Estimated transmission time through the best currently
        # active link associated with each candidate.
        communication_costs = {}

        for node in available_nodes:
            communication_costs[node.id] = (
                self._communication_cost(
                    node_id=node.id,
                    task=task,
                    current_time=current_time,
                )
            )

        # -------------------------------------------------------------
        # Normalize costs into suitability values
        # -------------------------------------------------------------
        cpu_suitability = self._normalize_costs(
            cpu_costs
        )

        energy_suitability = self._normalize_costs(
            energy_costs
        )

        communication_suitability = self._normalize_costs(
            communication_costs
        )

        # -------------------------------------------------------------
        # Composite suitability score
        # -------------------------------------------------------------
        # Weights follow the roadmap specification (docs/01_PROJECT_DESCRIPTION.md,
        # Section 3.2): CPU=0.4, Energy=0.4, Communication=0.2.
        #
        # Higher final score is better.
        scores = {}

        for node in available_nodes:
            node_id = node.id

            scores[node_id] = (
                WEIGHT_CPU * cpu_suitability[node_id]
                + WEIGHT_ENERGY * energy_suitability[node_id]
                + WEIGHT_COMMUNICATION * communication_suitability[node_id]
            )

        # -------------------------------------------------------------
        # Greedy decision
        # -------------------------------------------------------------
        # Highest instantaneous suitability score wins.
        #
        # Node ID is used as a deterministic tie-breaker so repeated
        # simulations produce the same result.
        chosen_node_id = max(
            scores,
            key=lambda node_id: (
                scores[node_id],
                node_id,
            ),
        )

        chosen_score = scores[chosen_node_id]

        # -------------------------------------------------------------
        # Return shared project decision model
        # -------------------------------------------------------------
        return AllocationDecision(
            task_id=task.id,
            chosen_node_id=chosen_node_id,
            score=chosen_score,
            reason=(
                "Greedy S3: highest suitability score "
                f"(CPU={cpu_suitability[chosen_node_id]:.3f}, "
                f"energy={energy_suitability[chosen_node_id]:.3f}, "
                f"communication="
                f"{communication_suitability[chosen_node_id]:.3f})."
            ),
        )