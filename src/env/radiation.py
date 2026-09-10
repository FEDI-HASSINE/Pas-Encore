from __future__ import annotations

from enum import Enum
import numpy as np


class FailureMode(str, Enum):
    SDC = "SDC"
    HBM = "HBM"
    SEFI = "SEFI"


class RadiationModel:
    """
    Simplified stochastic radiation model used by the project.

    Project assumptions:
        dose rate = 0.01 rad/s

        SDC = 17 rad
        HBM = 44 rad
        SEFI = 5000 rad
    """

    DOSE_RATE = 0.01

    CHARACTERISTIC_DOSES = {
        FailureMode.SDC: 17.0,
        FailureMode.HBM: 44.0,
        FailureMode.SEFI: 5000.0,
    }

    def __init__(self, seed: int | None = None):
        self.rng = np.random.default_rng(seed)
        self.cumulative_dose = 0.0

    def time_to_failure(self, characteristic_dose: float) -> float:
        """
        Return a random time until a radiation event.

        The project requires:
            scale = characteristic_dose / 0.01
        """
        if characteristic_dose <= 0:
            raise ValueError("characteristic_dose must be > 0")

        scale = characteristic_dose / self.DOSE_RATE

        return float(self.rng.exponential(scale=scale))

    def add_exposure(self, seconds: float) -> float:
        """
        Increase cumulative radiation dose:

            dose += seconds * 0.01
        """
        if seconds < 0:
            raise ValueError("seconds must be >= 0")

        self.cumulative_dose += seconds * self.DOSE_RATE
        return self.cumulative_dose

    def reset(self) -> None:
        """Reset cumulative dose."""
        self.cumulative_dose = 0.0

    @staticmethod
    def characteristic_dose(mode: FailureMode) -> float:
        return RadiationModel.CHARACTERISTIC_DOSES[mode]
