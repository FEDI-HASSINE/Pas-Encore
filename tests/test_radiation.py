import numpy as np

from src.env.radiation import (
    RadiationModel,
    FailureMode,
)


def test_sdc_mean():
    model = RadiationModel(seed=42)

    samples = [
        model.time_to_failure(17.0)
        for _ in range(10_000)
    ]

    mean = np.mean(samples)

    print("Observed SDC mean:", mean)

    # The theoretical mean is 1700 s. ±100 ≈ 6σ (Fix #10)
    assert 1600 < mean < 1800


def test_characteristic_doses():
    assert RadiationModel.CHARACTERISTIC_DOSES[FailureMode.SDC] == 17.0
    assert RadiationModel.CHARACTERISTIC_DOSES[FailureMode.HBM] == 44.0
    assert RadiationModel.CHARACTERISTIC_DOSES[FailureMode.SEFI] == 5000.0


def test_cumulative_dose():
    model = RadiationModel(seed=42)

    model.add_exposure(100)
    assert model.cumulative_dose == 1.0

    model.add_exposure(200)
    assert model.cumulative_dose == 3.0


def test_reset():
    model = RadiationModel(seed=42)

    model.add_exposure(100)
    model.reset()

    assert model.cumulative_dose == 0.0


def test_time_to_failure_conditional_on_accumulated_dose():
    """Fix #4: After 1000s exposure (10 rad), remaining for SDC (17 rad)
    is 7 rad → expected mean ≈ 700 s."""
    model = RadiationModel(seed=42)
    model.add_exposure(1000)  # 10 rad accumulated

    samples = [model.time_to_failure(17.0) for _ in range(10_000)]
    mean = np.mean(samples)

    print("Observed conditional SDC mean:", mean)
    assert 600 < mean < 800  # ~700 s expected


def test_time_to_failure_returns_zero_when_dose_exceeded():
    """If cumulative dose >= characteristic dose, failure is immediate."""
    model = RadiationModel(seed=42)
    model.add_exposure(2000)  # 20 rad > SDC 17 rad

    assert model.time_to_failure(17.0) == 0.0


def test_reproducibility():
    """Fix #11: Two instances with the same seed produce identical results."""
    m1 = RadiationModel(seed=42)
    m2 = RadiationModel(seed=42)

    assert m1.time_to_failure(17.0) == m2.time_to_failure(17.0)


def test_next_failure():
    """Fix #9: next_failure returns the earliest failure mode."""
    model = RadiationModel(seed=42)
    mode, time = model.next_failure()

    assert isinstance(mode, FailureMode)
    assert time >= 0.0
    # SDC (17 rad) has the smallest characteristic dose,
    # so it should statistically tend to fail first
