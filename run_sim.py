#!/usr/bin/env python
"""Unified simulation entry point with CLI argument parsing.

Usage examples:
    python run_sim.py --profile burst --strategy 1
    python run_sim.py --profile radiation --strategy 3 --seed 123
    python run_sim.py --profile mixed --strategy 2 --duration 6000

This script wires together:
    - Task Generator  (src/env/task_generator.py)  — M3
    - Topology        (src/env/topology.py)        — M2
    - Strategies S1-S3 (src/strategies/)            — M3 & M4
    - Orchestrator    (src/orchestrator.py)         — M4

Author: M3 (Team A) — Week 4
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

import simpy

# Ensure repo root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.env.task_generator import (
    generate_burst,
    generate_energy,
    generate_radiation,
    generate_mixed,
)
from src.env.topology import build_topology
from src.metrics.calculator import compute_all, compute_ml_from_samples
from src.orchestrator import Orchestrator
from src.schemas import Task, TaskState
from src.strategies.s1_always_ground import AlwaysGroundStrategy
from src.strategies.s2_always_orbital import AlwaysOrbitalStrategy
from src.strategies.greedy import GreedyStrategy


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Profile -> generator mapping
# ---------------------------------------------------------------------------

PROFILE_GENERATORS = {
    "burst": generate_burst,
    "energy": generate_energy,
    "radiation": generate_radiation,
    "mixed": generate_mixed,
}

STRATEGY_NAMES = {
    1: "S1_AlwaysGround",
    2: "S2_AlwaysOrbital",
    3: "S3_Greedy",
}


# ---------------------------------------------------------------------------
# Strategy factory
# ---------------------------------------------------------------------------

def build_strategy(strategy_id: int, topology):
    """Instantiate the requested strategy."""
    if strategy_id == 1:
        return AlwaysGroundStrategy()
    elif strategy_id == 2:
        return AlwaysOrbitalStrategy()
    elif strategy_id == 3:
        return GreedyStrategy(nodes=topology.nodes, links=topology.links)
    else:
        raise ValueError(f"Unknown strategy ID: {strategy_id}. Must be 1, 2, or 3.")





# ---------------------------------------------------------------------------
# Task feeder process
# ---------------------------------------------------------------------------

def feed_tasks(env: simpy.Environment, store: simpy.Store,
               raw_tasks: list[dict], strategy_name: str):
    """Convert raw task dicts to Task objects and feed them into the store.

    Args:
        env: SimPy environment
        store: Pending task store
        raw_tasks: List of raw task dicts from generator
        strategy_name: Name of strategy (for logging)
    """
    sorted_tasks = sorted(raw_tasks, key=lambda t: t["arrival_time"])

    for raw in sorted_tasks:
        # Wait until arrival time
        wait = raw["arrival_time"] - env.now
        if wait > 0:
            yield env.timeout(wait)

        task = Task(
            id=raw["id"],
            arrival_time=raw["arrival_time"],
            cpu_units=raw["cpu_units"],
            ram_units=raw["ram_units"],
            priority=raw.get("priority", 1),
            data_size_mb=raw.get("data_size_mb", 1.0),
            energy_budget=raw.get("energy_budget"),
            deadline=raw.get("deadline"),
            failure_mode=raw.get("failure_mode"),
            failure_time=raw.get("failure_time"),
        )
        yield store.put(task)


# ---------------------------------------------------------------------------
# Results saving
# ---------------------------------------------------------------------------

def save_results(profile: str, strategy_id: int, seed: int,
                 orchestrator: Orchestrator, duration: float,
                 metrics: dict):
    """Save run results to results/ directory."""
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    filename = results_dir / f"results_{profile}.csv"
    file_exists = filename.exists()

    with open(filename, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Strategy", "Seed", "Decisions", "Duration",
                             "M_T", "M_L", "M_R", "M_E"])
        writer.writerow([
            STRATEGY_NAMES[strategy_id],
            seed,
            orchestrator.decision_count,
            duration,
            metrics["M_T"],
            metrics["M_L"],
            metrics["M_R"],
            metrics["M_E"],
        ])

    logger.info("Results appended to %s", filename)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run_single(
    profile: str,
    strategy_id: int,
    seed: int,
    duration: float | None = None,
) -> dict:
    """Run one simulation and return its metrics/results.

    This exposes the simulation pipeline for automated experiment
    campaigns while keeping the CLI behaviour in main().
    """

    if profile not in PROFILE_GENERATORS:
        raise ValueError(
            f"Unknown profile: {profile}"
        )

    if strategy_id not in STRATEGY_NAMES:
        raise ValueError(
            f"Unknown strategy: {strategy_id}"
        )

    # 1. Build topology
    topology = build_topology()
    nodes = topology.nodes

    # 2. Generate workload
    generator = PROFILE_GENERATORS[profile]
    raw_tasks = generator(seed=seed)

    # 3. Build allocation strategy
    strategy = build_strategy(
        strategy_id,
        topology,
    )

    strategy_name = STRATEGY_NAMES[
        strategy_id
    ]

    # 4. Create simulation
    env = simpy.Environment()
    pending_store = simpy.Store(env)

    orchestrator = Orchestrator(
        env,
        pending_store,
        strategy,
        nodes,
    )

    env.process(
        orchestrator.run()
    )

    env.process(
        orchestrator.sample_utilization()
    )

    env.process(
        feed_tasks(
            env,
            pending_store,
            raw_tasks,
            strategy_name,
        )
    )

    # 5. Determine simulation duration
    if duration is not None:
        sim_duration = duration
    else:
        max_arrival = (
            max(
                task["arrival_time"]
                for task in raw_tasks
            )
            if raw_tasks
            else 0.0
        )

        max_cpu = (
            max(
                task["cpu_units"]
                for task in raw_tasks
            )
            if raw_tasks
            else 0.0
        )

        sim_duration = (
            max_arrival
            + max_cpu
            + 100
        )

    env.run(
        until=sim_duration
    )

    # 6. Compute metrics
    metrics = compute_all(
        tasks=orchestrator.completed_tasks,
        nodes=nodes,
        orphaned_count=0,
        total_energy=0.0,
        total_transmission=0.0,
    )

    avg_utilization = (
        orchestrator.average_utilization()
    )

    metrics["M_L"] = (
        compute_ml_from_samples(
            avg_utilization
        )
    )

    return {
        "Profile": profile,
        "Strategy": strategy_id,
        "Strategy_Name": strategy_name,
        "Seed": seed,
        "M_T": float(metrics["M_T"]),
        "M_L": float(metrics["M_L"]),
        "M_R": float(metrics["M_R"]),
        "M_E": float(metrics["M_E"]),
        "Completed_Tasks": len(
            orchestrator.completed_tasks
        ),
        "Simulation_Time": float(env.now),
    }
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="OrbitScheduler Simulation — Dynamic Workload Allocation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python run_sim.py --profile burst --strategy 1
  python run_sim.py --profile radiation --strategy 3 --seed 123
  python run_sim.py --profile mixed --strategy 2 --duration 6000
        """,
    )
    parser.add_argument(
        "--profile",
        type=str,
        required=True,
        choices=["burst", "energy", "radiation", "mixed"],
        help="Workload profile to simulate",
    )
    parser.add_argument(
        "--strategy",
        type=int,
        required=True,
        choices=[1, 2, 3],
        help="Allocation strategy: 1=AlwaysGround, 2=AlwaysOrbital, 3=Greedy",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Simulation duration in seconds (default: auto based on profile)",
    )

    args = parser.parse_args(argv)
    strategy_name = STRATEGY_NAMES[args.strategy]

    # --- Banner ---
    logger.info("=" * 60)
    logger.info("OrbitScheduler Simulation")
    logger.info("  Profile  : %s", args.profile)
    logger.info("  Strategy : %s (%s)", args.strategy, strategy_name)
    logger.info("  Seed     : %s", args.seed)
    logger.info("=" * 60)

    # --- 1. Build topology ---
    topology = build_topology()
    nodes = topology.nodes
    logger.info("Topology: %d nodes, %d links",
                len(topology.nodes), len(topology.links))

    # --- 2. Generate tasks ---
    generator = PROFILE_GENERATORS[args.profile]
    raw_tasks = generator(seed=args.seed)
    logger.info("Generated %d tasks for profile '%s'",
                len(raw_tasks), args.profile)

    # --- 3. Build strategy ---
    strategy = build_strategy(args.strategy, topology)
    logger.info("Strategy: %s", strategy_name)

    # --- 4. SimPy environment ---
    env = simpy.Environment()
    pending_store = simpy.Store(env)

    orchestrator = Orchestrator(env, pending_store, strategy, nodes)
    env.process(orchestrator.run())
    env.process(orchestrator.sample_utilization())
    env.process(feed_tasks(env, pending_store, raw_tasks, strategy_name))

    # --- 5. Determine simulation duration ---
    if args.duration is not None:
        sim_duration = args.duration
    else:
        max_arrival = max(t["arrival_time"] for t in raw_tasks) if raw_tasks else 0
        max_cpu = max(t["cpu_units"] for t in raw_tasks) if raw_tasks else 0
        sim_duration = max_arrival + max_cpu + 100  # buffer

    logger.info("Simulation running for %.1f seconds...", sim_duration)
    env.run(until=sim_duration)

    # --- 6. Compute metrics ---
    metrics = compute_all(
        tasks=orchestrator.completed_tasks,
        nodes=nodes,
        orphaned_count=0,
        total_energy=0.0,
        total_transmission=0.0,
    )
    avg_util = orchestrator.average_utilization()
    metrics["M_L"] = compute_ml_from_samples(avg_util)

    logger.info("=" * 60)
    logger.info("Simulation completed at t=%.1f", env.now)
    logger.info("Total decisions: %d", orchestrator.decision_count)
    logger.info("Completed tasks: %d", len(orchestrator.completed_tasks))
    for nid, node in nodes.items():
        logger.info("  %s: cpu_utilized=%.1f / %.1f",
                     nid, node.cpu_utilized, node.cpu_capacity)
    logger.info("  Metrics: M_T=%.2f, M_L=%.4f, M_R=%.4f, M_E=%.4f",
                 metrics["M_T"], metrics["M_L"], metrics["M_R"], metrics["M_E"])
    logger.info("=" * 60)

    # --- 7. Save CSV ---
    save_results(args.profile, args.strategy, args.seed,
                 orchestrator, env.now, metrics)


if __name__ == "__main__":
    main()
