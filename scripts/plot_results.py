"""Generate M_T barplot comparing S1, S2, S3 for the paper.

Reads results/summary_{profile}.csv (produced by M4's
run_experiments.py) and outputs results/graph_{profile}.png.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


STRATEGY_COLORS = {
    "S1_AlwaysGround": "#e74c3c",
    "S2_AlwaysOrbital": "#f39c12",
    "S3_Greedy": "#27ae60",
}


def plot_profile(profile: str) -> Path:
    """Generate the M_T barplot for one profile."""
    summary_path = Path("results") / f"summary_{profile}.csv"
    if not summary_path.exists():
        raise FileNotFoundError(
            f"Missing {summary_path}. Run run_experiments.py first."
        )

    df = pd.read_csv(summary_path)

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = [STRATEGY_COLORS.get(s, "#888888") for s in df["Strategy"]]
    ax.bar(
        df["Strategy"],
        df["M_T_mean"],
        yerr=df["M_T_std"],
        capsize=5,
        color=colors,
        edgecolor="black",
    )
    ax.set_ylabel("Makespan M_T (seconds)")
    ax.set_title(f"Makespan comparison — profile: {profile}")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()

    output_path = Path("results") / f"graph_{profile}.png"
    plt.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"Saved {output_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate M_T barplot for a workload profile."
    )
    parser.add_argument(
        "--profile",
        choices=["burst", "energy", "radiation", "mixed"],
        default="burst",
    )
    args = parser.parse_args()
    plot_profile(args.profile)


if __name__ == "__main__":
    main()
