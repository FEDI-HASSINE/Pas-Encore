"""Greedy score-based allocation strategy (Strategy 3).

The strategy evaluates the currently available compute nodes for each
incoming task and selects the node with the highest suitability score.

The score is based on three criteria defined by the project specification:
    - current CPU load,
    - estimated energy consumption,
    - communication latency.

The three criteria are equally weighted. This weighting is an implementation
choice because the project specification defines the criteria but does not
prescribe exact weights.
"""

from __future__ import annotations

from src.schemas import AllocationDecision, Task
from src.strategies.base import AllocationStrategy


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
        """Estimate communication time from the node's active links.

        Task currently has no source-node field, so an exact end-to-end
        communication latency cannot be calculated.

        As a deterministic approximation, use the best currently active
        link connected to the candidate node.

        Estimated transmission time:
            data_size_mb * 8 / bandwidth_mbps

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

        return (
            task.data_size_mb * 8.0
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
        # Equal weighting:
        #   CPU           = 1/3
        #   Energy        = 1/3
        #   Communication = 1/3
        #
        # Higher final score is better.
        scores = {}

        for node in available_nodes:
            node_id = node.id

            scores[node_id] = (
                cpu_suitability[node_id]
                + energy_suitability[node_id]
                + communication_suitability[node_id]
            ) / 3.0

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