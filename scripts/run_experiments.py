"""Week 3 automated experiment campaign.

Runs:
    4 workload profiles
    x 3 allocation strategies
    x 5 random seeds
    = 60 simulations

Outputs:
    results/results_burst.csv
    results/results_energy.csv
    results/results_radiation.csv
    results/results_mixed.csv

    results/summary_burst.csv
    results/summary_energy.csv
    results/summary_radiation.csv
    results/summary_mixed.csv

    results/pvalues_burst.csv
"""

from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

from scipy.stats import ttest_ind


# ---------------------------------------------------------------------------
# Repository path
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Official simulation entry point
# ---------------------------------------------------------------------------

from run_sim import run_single


# ---------------------------------------------------------------------------
# Experiment configuration
# ---------------------------------------------------------------------------

PROFILES = [
    "burst",
    "energy",
    "radiation",
    "mixed",
]

STRATEGIES = [
    1,
    2,
    3,
]

SEEDS = [
    1,
    2,
    3,
    4,
    5,
]

RESULTS_DIR = REPO_ROOT / "results"


# ---------------------------------------------------------------------------
# Complete experiment campaign
# ---------------------------------------------------------------------------

def run_experiments() -> dict[str, list[dict]]:
    """Run 4 profiles x 3 strategies x 5 seeds = 60 simulations."""

    all_results = {
        profile: []
        for profile in PROFILES
    }

    total_runs = (
        len(PROFILES)
        * len(STRATEGIES)
        * len(SEEDS)
    )

    current_run = 0

    print("=" * 70)
    print("Week 3 Experiment Campaign")
    print("=" * 70)
    print(f"Profiles   : {len(PROFILES)}")
    print(f"Strategies : {len(STRATEGIES)}")
    print(f"Seeds      : {len(SEEDS)}")
    print(f"Total runs : {total_runs}")
    print("=" * 70)

    for profile in PROFILES:
        for strategy_id in STRATEGIES:
            for seed in SEEDS:

                current_run += 1

                print(
                    f"[{current_run:02d}/{total_runs}] "
                    f"profile={profile:<9} "
                    f"strategy=S{strategy_id} "
                    f"seed={seed}"
                )

                result = run_single(
                    profile=profile,
                    strategy_id=strategy_id,
                    seed=seed,
                )

                all_results[
                    profile
                ].append(result)

                print(
                    "         "
                    f"M_T={result['M_T']:.4f}  "
                    f"M_L={result['M_L']:.4f}  "
                    f"completed="
                    f"{result['Completed_Tasks']}"
                )

    return all_results


# ---------------------------------------------------------------------------
# Raw results
# ---------------------------------------------------------------------------

def save_profile_results(
    profile: str,
    results: list[dict],
) -> Path:
    """Save the 15 runs for one workload profile."""

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        RESULTS_DIR
        / f"results_{profile}.csv"
    )

    fieldnames = [
        "Strategy",
        "Seed",
        "M_T",
        "M_L",
    ]

    with output_file.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for result in results:
            writer.writerow(
                {
                    "Strategy":
                        f"S{result['Strategy']}",
                    "Seed":
                        result["Seed"],
                    "M_T":
                        result["M_T"],
                    "M_L":
                        result["M_L"],
                }
            )

    return output_file


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------

def calculate_summary(
    results: list[dict],
) -> list[dict]:
    """Calculate mean and sample standard deviation by strategy."""

    summary = []

    for strategy_id in STRATEGIES:

        strategy_results = [
            result
            for result in results
            if result["Strategy"] == strategy_id
        ]

        mt_values = [
            result["M_T"]
            for result in strategy_results
        ]

        ml_values = [
            result["M_L"]
            for result in strategy_results
        ]

        summary.append(
            {
                "Strategy":
                    f"S{strategy_id}",
                "M_T_Mean":
                    statistics.mean(mt_values),
                "M_T_Std":
                    statistics.stdev(mt_values),
                "M_L_Mean":
                    statistics.mean(ml_values),
                "M_L_Std":
                    statistics.stdev(ml_values),
            }
        )

    return summary


def save_summary(
    profile: str,
    results: list[dict],
) -> Path:
    """Save mean and standard deviation for one profile."""

    summary = calculate_summary(
        results
    )

    output_file = (
        RESULTS_DIR
        / f"summary_{profile}.csv"
    )

    fieldnames = [
        "Strategy",
        "M_T_Mean",
        "M_T_Std",
        "M_L_Mean",
        "M_L_Std",
    ]

    with output_file.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(summary)

    return output_file


# ---------------------------------------------------------------------------
# Burst Student tests
# ---------------------------------------------------------------------------

def calculate_burst_pvalues(
    burst_results: list[dict],
) -> list[dict]:
    """Run the three pairwise Student t-tests on Burst M_T."""

    comparisons = [
        (1, 2),
        (1, 3),
        (2, 3),
    ]

    rows = []

    for strategy_a, strategy_b in comparisons:

        values_a = [
            result["M_T"]
            for result in burst_results
            if result["Strategy"] == strategy_a
        ]

        values_b = [
            result["M_T"]
            for result in burst_results
            if result["Strategy"] == strategy_b
        ]

        test = ttest_ind(
            values_a,
            values_b,
            equal_var=True,
        )

        p_value = float(
            test.pvalue
        )

        rows.append(
            {
                "Comparison":
                    f"S{strategy_a}_vs_S{strategy_b}",
                "Strategy_A":
                    f"S{strategy_a}",
                "Strategy_B":
                    f"S{strategy_b}",
                "M_T_Mean_A":
                    statistics.mean(values_a),
                "M_T_Mean_B":
                    statistics.mean(values_b),
                "T_Statistic":
                    float(test.statistic),
                "P_Value":
                    p_value,
                "Significant_0.05":
                    p_value < 0.05,
            }
        )

    return rows


def save_burst_pvalues(
    burst_results: list[dict],
) -> Path:
    """Save the three Burst Student tests."""

    rows = calculate_burst_pvalues(
        burst_results
    )

    output_file = (
        RESULTS_DIR
        / "pvalues_burst.csv"
    )

    fieldnames = [
        "Comparison",
        "Strategy_A",
        "Strategy_B",
        "M_T_Mean_A",
        "M_T_Mean_B",
        "T_Statistic",
        "P_Value",
        "Significant_0.05",
    ]

    with output_file.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)

    return output_file


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_results(
    all_results: dict[str, list[dict]],
) -> None:
    """Validate the expected 60-run experiment matrix."""

    expected_total = (
        len(PROFILES)
        * len(STRATEGIES)
        * len(SEEDS)
    )

    actual_total = sum(
        len(results)
        for results in all_results.values()
    )

    if actual_total != expected_total:
        raise RuntimeError(
            f"Expected {expected_total} runs, "
            f"got {actual_total}"
        )

    for profile in PROFILES:

        results = all_results[
            profile
        ]

        if len(results) != 15:
            raise RuntimeError(
                f"{profile}: expected 15 runs, "
                f"got {len(results)}"
            )

        for strategy_id in STRATEGIES:

            strategy_results = [
                result
                for result in results
                if result["Strategy"] == strategy_id
            ]

            if len(strategy_results) != 5:
                raise RuntimeError(
                    f"{profile} S{strategy_id}: "
                    "expected 5 seeds, "
                    f"got {len(strategy_results)}"
                )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Run, validate and save the complete campaign."""

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_results = run_experiments()

    validate_results(
        all_results
    )

    print()
    print("=" * 70)
    print("Saving experiment results")
    print("=" * 70)

    for profile in PROFILES:

        results_file = save_profile_results(
            profile,
            all_results[profile],
        )

        summary_file = save_summary(
            profile,
            all_results[profile],
        )

        print(
            f"{profile:<9}: "
            f"{results_file.name}, "
            f"{summary_file.name}"
        )

    pvalues_file = save_burst_pvalues(
        all_results["burst"]
    )

    print(
        f"Burst tests: {pvalues_file.name}"
    )

    print("=" * 70)
    print("Experiment campaign completed.")
    print("Total runs: 60")
    print(
        f"Results directory: {RESULTS_DIR}"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()