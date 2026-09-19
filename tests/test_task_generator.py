"""Unit tests for the task generator (M3 Week 2).

Tests validate:
    - Correct number of tasks per profile
    - Schema compatibility with src.schemas.Task
    - Profile-specific fields (energy_budget, failure_mode, deadline)
    - Acceptance criteria from the roadmap
"""

import pytest
from src.env.task_generator import (
    generate_burst,
    generate_energy,
    generate_radiation,
    generate_mixed,
    generate_all_profiles,
)
from src.schemas import Task


# ========================================================================
# Profile 1: Burst
# ========================================================================

class TestBurst:

    def test_burst_count(self):
        """AC: generate_burst() returns 150 tasks."""
        tasks = generate_burst()
        assert len(tasks) == 150

    def test_burst_all_at_t0(self):
        """All burst tasks arrive at t=0."""
        tasks = generate_burst()
        assert all(t["arrival_time"] == 0.0 for t in tasks)

    def test_burst_cpu_range(self):
        """CPU units are in [5, 15]."""
        tasks = generate_burst()
        assert all(5.0 <= t["cpu_units"] <= 15.0 for t in tasks)

    def test_burst_schema_compatible(self):
        """Each burst task can be loaded into a Pydantic Task."""
        tasks = generate_burst()
        for t in tasks[:5]:  # Test first 5 for speed
            task_obj = Task(
                id=t["id"],
                arrival_time=t["arrival_time"],
                cpu_units=t["cpu_units"],
                ram_units=t["ram_units"],
            )
            assert task_obj.id == t["id"]

    def test_burst_reproducible(self):
        """Same seed produces same tasks."""
        t1 = generate_burst(seed=99)
        t2 = generate_burst(seed=99)
        assert t1 == t2


# ========================================================================
# Profile 2: Energy
# ========================================================================

class TestEnergy:

    def test_energy_count(self):
        """AC: generate_energy() returns 100 tasks."""
        tasks = generate_energy()
        assert len(tasks) == 100

    def test_energy_spread_over_time(self):
        """Tasks are spread over 7200s."""
        tasks = generate_energy()
        assert any(t["arrival_time"] > 0 for t in tasks)
        assert all(0 <= t["arrival_time"] <= 7200 for t in tasks)

    def test_energy_cpu_range(self):
        """CPU units are in [15, 20]."""
        tasks = generate_energy()
        assert all(15.0 <= t["cpu_units"] <= 20.0 for t in tasks)

    def test_energy_has_budget(self):
        """Each energy task has an energy_budget field."""
        tasks = generate_energy()
        assert all("energy_budget" in t for t in tasks)
        assert all(t["energy_budget"] > 0 for t in tasks)

    def test_energy_sorted_by_arrival(self):
        """Tasks are sorted by arrival_time."""
        tasks = generate_energy()
        times = [t["arrival_time"] for t in tasks]
        assert times == sorted(times)


# ========================================================================
# Profile 3: Radiation
# ========================================================================

class TestRadiation:

    def test_radiation_count(self):
        """AC: generate_radiation() returns 80 tasks."""
        tasks = generate_radiation()
        assert len(tasks) == 80

    def test_radiation_has_failure_mode(self):
        """AC: generate_radiation() includes tasks with failure_mode != None."""
        tasks = generate_radiation()
        assert all("failure_mode" in t for t in tasks)
        assert all(t["failure_mode"] in ("SDC", "HBM", "SEFI") for t in tasks)

    def test_radiation_has_failure_time(self):
        """Each radiation task has a failure_time field > 0."""
        tasks = generate_radiation()
        assert all("failure_time" in t for t in tasks)
        assert all(t["failure_time"] > 0 for t in tasks)

    def test_radiation_uses_m2_model(self):
        """failure_mode values match M2's FailureMode enum."""
        from src.env.radiation import FailureMode
        tasks = generate_radiation()
        valid_modes = {fm.value for fm in FailureMode}
        for t in tasks:
            assert t["failure_mode"] in valid_modes


# ========================================================================
# Profile 4: Mixed
# ========================================================================

class TestMixed:

    def test_mixed_count(self):
        """AC: generate_mixed() returns 200 tasks."""
        tasks = generate_mixed()
        assert len(tasks) == 200

    def test_mixed_high_priority_ratio(self):
        """AC: ~20% of tasks have priority==2, i.e. exactly 40 tasks."""
        tasks = generate_mixed()
        n_high = sum(1 for t in tasks if t["priority"] == 2)
        assert n_high == 40  # Exactly 20% of 200

    def test_mixed_high_priority_have_deadline(self):
        """High-priority tasks have deadline=0.1."""
        tasks = generate_mixed()
        for t in tasks:
            if t["priority"] == 2:
                assert t["deadline"] == 0.1

    def test_mixed_normal_no_deadline(self):
        """Normal-priority tasks have deadline=None."""
        tasks = generate_mixed()
        for t in tasks:
            if t["priority"] == 1:
                assert t["deadline"] is None

    def test_mixed_sorted_by_arrival(self):
        """Tasks are sorted by arrival_time."""
        tasks = generate_mixed()
        times = [t["arrival_time"] for t in tasks]
        assert times == sorted(times)


# ========================================================================
# All Profiles
# ========================================================================

class TestAllProfiles:

    def test_generate_all_profiles(self):
        """generate_all_profiles returns a dict with 4 keys."""
        profiles = generate_all_profiles()
        assert set(profiles.keys()) == {"burst", "energy", "radiation", "mixed"}

    def test_all_profiles_counts(self):
        """Each profile has the expected number of tasks."""
        profiles = generate_all_profiles()
        assert len(profiles["burst"]) == 150
        assert len(profiles["energy"]) == 100
        assert len(profiles["radiation"]) == 80
        assert len(profiles["mixed"]) == 200

    def test_all_tasks_have_required_fields(self):
        """Every task across all profiles has id, arrival_time, cpu_units, ram_units."""
        profiles = generate_all_profiles()
        required_keys = {"id", "arrival_time", "cpu_units", "ram_units"}
        for profile_name, tasks in profiles.items():
            for t in tasks:
                missing = required_keys - set(t.keys())
                assert not missing, (
                    f"Profile '{profile_name}', task '{t.get('id', '?')}' "
                    f"missing fields: {missing}"
                )
