from datetime import datetime, timezone
import pytest

from src.env.link import Link, skyfield_is_visible


def test_link_acceptance_criterion():
    """Acceptance criterion: Link('LEO-1', 'GS').is_active(0) returns True."""
    link = Link("LEO-1", "GS")
    assert link.is_active(0) is True


def test_link_attributes():
    """Verify link stores node endpoints and bandwidth."""
    link = Link("LEO-1", "GS-Tunisia", bandwidth=15.0)
    assert link.node1 == "LEO-1"
    assert link.node2 == "GS-Tunisia"
    assert link.bandwidth == 15.0


def test_link_leo1_pass_schedule():
    """Verify LEO-1 to GS contact window (600s active every 5400s)."""
    link = Link("LEO-1", "GS")

    # Active during first pass [0, 600)
    assert link.is_active(0) is True
    assert link.is_active(100.0) is True
    assert link.is_active(599.9) is True

    # Inactive outside pass [600, 5400)
    assert link.is_active(600.0) is False
    assert link.is_active(2000.0) is False
    assert link.is_active(5399.0) is False

    # Active during second pass [5400, 6000)
    assert link.is_active(5400.0) is True
    assert link.is_active(5700.0) is True
    assert link.is_active(6000.0) is False


def test_link_leo2_pass_schedule():
    """Verify LEO-2 to GS contact window (600s active every 5400s, offset by 2700s)."""
    link = Link("LEO-2", "GS-Tunisia")

    # Inactive before offset
    assert link.is_active(0) is False
    assert link.is_active(2699.0) is False

    # Active during pass [2700, 3300)
    assert link.is_active(2700.0) is True
    assert link.is_active(3000.0) is True
    assert link.is_active(3299.0) is True

    # Inactive after pass
    assert link.is_active(3300.0) is False


def test_link_terrestrial_always_active():
    """Verify GS-Tunisia to Cloud-AWS is always active with 100 Mbps."""
    link = Link("GS-Tunisia", "Cloud-AWS")
    assert link.bandwidth == 100.0
    assert link.always_active is True
    assert link.is_active(0) is True
    assert link.is_active(500) is True
    assert link.is_active(10000) is True


def test_link_isl_always_active():
    """Verify Inter-Satellite Link (LEO-1 to LEO-2) is always active with 50 Mbps."""
    link = Link("LEO-1", "LEO-2")
    assert link.bandwidth == 50.0
    assert link.always_active is True
    assert link.is_active(0) is True
    assert link.is_active(700) is True
    assert link.is_active(25000) is True


def test_link_custom_visibility_window():
    """Verify user can supply a custom visibility window (duration, period, offset)."""
    # Active for 100s every 1000s with offset 50s -> active in [50, 150)
    link = Link("nodeA", "nodeB", bandwidth=20.0, visibility_window=(100.0, 1000.0, 50.0))
    assert link.is_active(0) is False
    assert link.is_active(50) is True
    assert link.is_active(120) is True
    assert link.is_active(150) is False
    assert link.is_active(1050) is True


def test_link_custom_is_active_fn():
    """Verify user can supply a custom is_active callback function."""
    link = Link("nodeA", "nodeB", is_active_fn=lambda t: t >= 500)
    assert link.is_active(100) is False
    assert link.is_active(500) is True
    assert link.is_active(1000) is True


def test_skyfield_is_visible_stub():
    """Verify skyfield_is_visible stub runs offline using skyfield.api.load and dummy TLE."""
    vis0 = skyfield_is_visible(0)
    assert isinstance(vis0, bool)
    assert vis0 is True

    vis800 = skyfield_is_visible(800)
    assert isinstance(vis800, bool)
    assert vis800 is False

    # Test with datetime object
    dt = datetime(2020, 11, 25, 13, 9, 0, tzinfo=timezone.utc)
    vis_dt = skyfield_is_visible(dt)
    assert vis_dt is True


def test_link_with_skyfield():
    """Verify Link can optionally use Skyfield for visibility determination."""
    link = Link("LEO-1", "GS", use_skyfield=True)
    assert link.is_active(0) is True
    assert link.is_active(800) is False
