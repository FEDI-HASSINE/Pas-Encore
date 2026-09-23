"""Generate metric barplot per profile."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


STRATEGY_COLORS = {
    "S1": "#e74c3c",
    "S2": "#f39c12",
    "S3": "#27ae60",
}

# Choix de la métrique principale par profil (alignée sur docs/02)
PROFILE_METRIC = {
    "burst":     "M_T",  # makespan
    "energy":    "M_L",  # load balance
    "mixed":     "M_L",  # load balance
    "radiation": "M_L",  # load balance
}

PROFILE_LABEL = {
    "burst":     "Makespan M_T (seconds)",
    "energy":    "Load balance M_L (std-dev)",
    "mixed":     "Load balance M_L (std-dev)",
    "radiation": "Load balance M_L (std-dev)",
}


def _pick_column(df: pd.DataFrame, *candidates: str) -> str:
    for name in candidates:
        if name in df.columns:
            return name
    raise KeyError(f"None of {candidates} in {list(df.columns)}")


def plot_profile(profile: str) -> Path:
    summary_path = Path("results") / f"summary_{profile}.csv"
    df = pd.read_csv(summary_path)

    metric = PROFILE_METRIC.get(profile, "M_T")
    mean_col = _pick_column(df, f"{metric}_Mean", f"{metric}_mean")
    std_col = _pick_column(df, f"{metric}_Std", f"{metric}_std")

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = [STRATEGY_COLORS.get(s, "#888") for s in df["Strategy"]]
    ax.bar(
        df["Strategy"],
        df[mean_col],
        yerr=df[std_col],
        capsize=5,
        color=colors,
        edgecolor="black",
    )
    ax.set_ylabel(PROFILE_LABEL.get(profile, metric))
    ax.set_xlabel("Strategy")
    ax.set_title(f"{metric} comparison — profile: {profile}")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()

    output_path = Path("results") / f"graph_{profile}.png"
    plt.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"Saved {output_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        choices=["burst", "energy", "radiation", "mixed"],
        default="burst",
    )
    args = parser.parse_args()
    plot_profile(args.profile)


if __name__ == "__main__":
    main()