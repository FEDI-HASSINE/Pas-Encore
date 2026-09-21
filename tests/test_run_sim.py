"""Tests for run_sim.py CLI entry point.

Validates that all 12 combinations (4 profiles x 3 strategies) run
without errors.
"""

import subprocess
import sys

import pytest


PROFILES = ["burst", "energy", "radiation", "mixed"]
STRATEGIES = [1, 2, 3]


@pytest.mark.parametrize("profile", PROFILES)
@pytest.mark.parametrize("strategy", STRATEGIES)
def test_run_sim_combination(profile, strategy):
    """Each of the 12 profile x strategy combinations must exit cleanly."""
    result = subprocess.run(
        [
            sys.executable,
            "run_sim.py",
            "--profile", profile,
            "--strategy", str(strategy),
            "--seed", "42",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"run_sim.py --profile {profile} --strategy {strategy} failed:\n"
        f"STDOUT:\n{result.stdout[-500:]}\n"
        f"STDERR:\n{result.stderr[-500:]}"
    )


def test_run_sim_help():
    """run_sim.py --help should print usage and exit 0."""
    result = subprocess.run(
        [sys.executable, "run_sim.py", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "--profile" in result.stdout
    assert "--strategy" in result.stdout
