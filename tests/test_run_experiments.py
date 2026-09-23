"""Tests for scripts/run_experiments.py campaign wiring.

Validates the experiment matrix configuration and the committed
result artifacts without re-running the full 60-run campaign.
"""

import csv
import pathlib
import subprocess

import pytest

from run_sim import run_single
from scripts import run_experiments as campaign


@pytest.fixture(scope="session", autouse=True)
def _restore_csvs():
    """Restore the committed CSVs before running tests."""
    subprocess.run(
        ["git", "checkout", "HEAD", "--", "results/"],
        check=False,
    )
    yield


RESULTS = pathlib.Path("results")

PROFILES = ["burst", "energy", "radiation", "mixed"]
STRATEGY_LABELS = ["S1_AlwaysGround", "S2_AlwaysOrbital", "S3_Greedy"]


def test_campaign_imports():
    """AC-1: campaign module and entry point are importable."""
    assert callable(campaign.run_experiments)
    assert callable(campaign.main)


def test_campaign_matrix_configuration():
    """AC-2: campaign covers 4 profiles x 3 strategies x 5 seeds."""
    assert campaign.PROFILES == PROFILES
    assert campaign.STRATEGIES == [1, 2, 3]
    assert campaign.SEEDS == [42, 43, 44, 45, 46]
    total = len(campaign.PROFILES) * len(campaign.STRATEGIES) * len(campaign.SEEDS)
    assert total == 60


@pytest.mark.parametrize("profile", PROFILES)
def test_results_csv_has_15_rows(profile):
    """AC-3: each results CSV has exactly 15 rows."""
    path = RESULTS / f"results_{profile}.csv"
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 15


@pytest.mark.parametrize("profile", PROFILES)
def test_results_csv_has_5_unique_seeds(profile):
    """AC-6: each results CSV covers 5 unique seeds."""
    path = RESULTS / f"results_{profile}.csv"
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    seeds = {row["Seed"] for row in rows}
    assert seeds == {"42", "43", "44", "45", "46"}


@pytest.mark.parametrize("profile", PROFILES)
def test_results_csv_covers_all_strategies(profile):
    """Each results CSV covers all 3 strategies with 5 seeds each."""
    path = RESULTS / f"results_{profile}.csv"
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    strategies = {row["Strategy"] for row in rows}
    assert strategies == set(STRATEGY_LABELS)
    for strategy in STRATEGY_LABELS:
        seeds = {row["Seed"] for row in rows if row["Strategy"] == strategy}
        assert len(seeds) == 5


@pytest.mark.parametrize("profile", PROFILES)
def test_summary_csv_has_3_rows(profile):
    """AC-4: each summary CSV has one row per strategy."""
    path = RESULTS / f"summary_{profile}.csv"
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 3
    assert {row["Strategy"] for row in rows} == {"S1", "S2", "S3"}


def test_pvalues_csv_has_3_rows():
    """AC-5: burst p-values CSV has 3 pairwise comparisons."""
    path = RESULTS / "pvalues_burst.csv"
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 3
    assert {row["Comparison"] for row in rows} == {
        "S1_vs_S2",
        "S1_vs_S3",
        "S2_vs_S3",
    }


def test_run_single_returns_expected_keys():
    """AC-7: run_single returns metrics, decisions, and duration."""
    result = run_single("burst", 1, 42)
    assert {"M_T", "M_L", "M_R", "M_E", "decisions", "duration"} <= set(
        result.keys()
    )
    assert result["decisions"] == 150


def test_run_single_is_deterministic():
    """AC-8: same (strategy, seed) gives identical M_T/M_L across reruns."""
    first = run_single("burst", 1, 42)
    second = run_single("burst", 1, 42)
    assert first["M_T"] == second["M_T"]
    assert first["M_L"] == second["M_L"]
