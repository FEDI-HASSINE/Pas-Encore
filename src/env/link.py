from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Callable

from skyfield.api import load, EarthSatellite, wgs84

# Pre-defined dummy TLE representing a synthetic LEO-1 orbit
DUMMY_TLE_LINE1 = "1 25544U 98067A   20330.54791667  .00000936  00000-0  24714-4 0  9993"
DUMMY_TLE_LINE2 = "2 25544  51.6451 147.2727 0001882  55.5397  94.9452 15.49386345257125"

# Reference epoch and subpoint coordinates where satellite is visible at t=0
_REFERENCE_EPOCH = datetime(2020, 11, 25, 13, 9, 0, tzinfo=timezone.utc)
_DEFAULT_STATION_LAT = 22.77
_DEFAULT_STATION_LON = 45.80


def skyfield_is_visible(
    t: float | int | datetime,
    min_elevation_deg: float = 0.0,
    station_lat: float = _DEFAULT_STATION_LAT,
    station_lon: float = _DEFAULT_STATION_LON,
    line1: str = DUMMY_TLE_LINE1,
    line2: str = DUMMY_TLE_LINE2,
) -> bool:
    """Evaluate geometric visibility of a LEO satellite relative to a ground station using Skyfield.

    This function acts as the Phase 1/Week 2 stub preparing integration for M3 (Phase 3).
    It uses `skyfield.api.load` with `builtin=True` and a dummy TLE to operate completely
    offline without external network calls.

    Args:
        t: Simulation time in seconds from epoch, or a datetime object.
        min_elevation_deg: Minimum elevation in degrees above the horizon for contact (default 0.0).
        station_lat: Latitude of ground station.
        station_lon: Longitude of ground station.
        line1: First line of two-line element set.
        line2: Second line of two-line element set.

    Returns:
        True if the satellite elevation exceeds `min_elevation_deg`, False otherwise.
    """
    ts = load.timescale(builtin=True)
    sat = EarthSatellite(line1, line2, "LEO-STUB", ts)
    station = wgs84.latlon(station_lat, station_lon)

    if isinstance(t, (int, float)):
        sim_dt = _REFERENCE_EPOCH + timedelta(seconds=float(t))
    elif isinstance(t, datetime):
        sim_dt = t if t.tzinfo is not None else t.replace(tzinfo=timezone.utc)
    else:
        raise TypeError(f"t must be float, int, or datetime, got {type(t)}")

    skyfield_time = ts.from_datetime(sim_dt)
    relative_position = (sat - station).at(skyfield_time)
    alt, _, _ = relative_position.altaz()

    return bool(alt.degrees > min_elevation_deg)


class Link:
    """Communication link between two nodes in the space-ground continuum.

    Supports fixed bandwidth and periodic orbital contact windows (e.g., LEO passes)
    as defined in Table 2 of the Experimental Design specification:
        - LEO-1 <-> GS-Tunisia: 10 Mbps, Active for 600s every 5400s (offset 0s, active at t=0).
        - LEO-2 <-> GS-Tunisia: 10 Mbps, Active for 600s every 5400s (offset 2700s).
        - GS-Tunisia <-> Cloud-AWS: 100 Mbps, Always Active.
        - LEO-1 <-> LEO-2 (ISL): 50 Mbps, Always Active.

    Attributes:
        node1: ID of first endpoint.
        node2: ID of second endpoint.
        bandwidth: Communication throughput in Mbps.
        visibility_window: Optional tuple of (duration, period, offset) in seconds.
        always_active: If True, link never experiences contact blackout.
        use_skyfield: If True, uses Skyfield geometric propagation for visibility.
        is_active_fn: Custom callback function taking current_time and returning bool.
    """

    def __init__(
        self,
        node1: str | Any,
        node2: str | Any,
        bandwidth: float | None = None,
        visibility_window: tuple[float, float, float] | None = None,
        always_active: bool | None = None,
        use_skyfield: bool = False,
        is_active_fn: Callable[[float], bool] | None = None,
    ) -> None:
        self.node1 = getattr(node1, "id", str(node1))
        self.node2 = getattr(node2, "id", str(node2))
        self.use_skyfield = use_skyfield
        self.is_active_fn = is_active_fn

        n1_upper = self.node1.upper()
        n2_upper = self.node2.upper()

        # Check for Inter-Satellite Link (ISL)
        is_isl = ("LEO" in n1_upper or "SAT" in n1_upper) and ("LEO" in n2_upper or "SAT" in n2_upper)
        # Check for Terrestrial link (Ground Station to Cloud)
        is_ground_cloud = ("GS" in n1_upper and "CLOUD" in n2_upper) or ("CLOUD" in n1_upper and "GS" in n2_upper)

        if always_active is not None:
            self.always_active = always_active
        elif is_isl or is_ground_cloud:
            self.always_active = True
        else:
            self.always_active = False

        # Set bandwidth default based on topology specification
        if bandwidth is not None:
            self.bandwidth = float(bandwidth)
        elif is_ground_cloud:
            self.bandwidth = 100.0
        elif is_isl:
            self.bandwidth = 50.0
        else:
            self.bandwidth = 10.0

        # Set visibility schedule (duration, period, offset)
        if visibility_window is not None:
            self.visibility_window = visibility_window
        elif not self.always_active:
            # Check for LEO-2 vs LEO-1 schedule
            if "LEO-2" in n1_upper or "LEO-2" in n2_upper:
                self.visibility_window = (600.0, 5400.0, 2700.0)
            else:
                # Default LEO pass: 600s active every 5400s starting at t=0
                self.visibility_window = (600.0, 5400.0, 0.0)
        else:
            self.visibility_window = None

    def is_active(self, current_time: float | int = 0.0) -> bool:
        """Check if link is currently active at simulation time current_time.

        Args:
            current_time: Time in seconds from simulation start.

        Returns:
            True if the link is active/connected, False otherwise.
        """
        t = float(current_time)

        if self.is_active_fn is not None:
            return bool(self.is_active_fn(t))

        if self.use_skyfield:
            return skyfield_is_visible(t)

        if self.always_active:
            return True

        if self.visibility_window is not None:
            duration, period, offset = self.visibility_window
            if period <= 0:
                return True
            norm_t = (t - offset) % period
            return norm_t < duration

        return True
