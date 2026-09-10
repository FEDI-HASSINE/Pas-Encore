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

    # The theoretical mean is 1700 s.
    assert 1500 < mean < 1900


def test_characteristic_doses():
    assert RadiationModel.characteristic_dose(FailureMode.SDC) == 17.0
    assert RadiationModel.characteristic_dose(FailureMode.HBM) == 44.0
    assert RadiationModel.characteristic_dose(FailureMode.SEFI) == 5000.0


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