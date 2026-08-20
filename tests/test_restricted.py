"""
Test 4: Restricted Area Detection Module
Verifies that RestrictedAreaDetector accurately flags person center coordinates
falling inside the designated ROI rectangle and ignores persons outside.
"""

import numpy as np
import pytest
from detection.restricted_area import RestrictedAreaDetector
from detection.person_detector import TrackedPerson


def test_restricted_area_inside_outside():
    """Verify inside vs outside collision detection."""
    # Define ROI from (100, 100) to (300, 300)
    detector = RestrictedAreaDetector(coords=[100, 100, 300, 300], name="Lab Vault")

    # Inside points
    assert detector.is_inside((100, 100)) is True
    assert detector.is_inside((200, 200)) is True
    assert detector.is_inside((300, 300)) is True

    # Outside points
    assert detector.is_inside((99, 200)) is False
    assert detector.is_inside((301, 200)) is False
    assert detector.is_inside((200, 99)) is False
    assert detector.is_inside((200, 301)) is False
    assert detector.is_inside((500, 500)) is False


def test_restricted_area_violations():
    """Verify check_violations returns correct violating TrackedPerson objects."""
    detector = RestrictedAreaDetector(coords=[100, 100, 200, 200])

    p1 = TrackedPerson(track_id=1, bbox=(120, 120, 160, 180), confidence=0.9, center=(140, 150)) # Inside
    p2 = TrackedPerson(track_id=2, bbox=(400, 50, 450, 120), confidence=0.85, center=(425, 85))   # Outside
    p3 = TrackedPerson(track_id=3, bbox=(110, 110, 170, 190), confidence=0.95, center=(140, 150)) # Inside

    violators = detector.check_violations([p1, p2, p3])
    assert len(violators) == 2
    assert violators[0].track_id == 1
    assert violators[1].track_id == 3


def test_restricted_area_overlay_render():
    """Verify drawing the overlay on a blank frame."""
    detector = RestrictedAreaDetector(coords=[100, 50, 400, 250])
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    rendered = detector.draw_overlay(frame, violator_ids={1})
    assert rendered is not None
    assert rendered.shape == (360, 640, 3)
