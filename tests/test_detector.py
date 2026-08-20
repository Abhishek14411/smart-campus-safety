"""
Test 1: Person Detection & Tracking Module
Verifies that PersonDetector loads correctly, runs inference on image frames,
and returns structured TrackedPerson objects with anonymous IDs and bounding boxes.
"""

import numpy as np
import pytest
from detection.person_detector import PersonDetector, TrackedPerson


def test_person_detector_init():
    """Verify detector initialization and model loading."""
    detector = PersonDetector()
    assert detector is not None
    assert detector.conf_threshold > 0.0


def test_person_detector_empty_frame():
    """Verify detector handles empty or zero frames gracefully."""
    detector = PersonDetector()
    empty_frame = np.zeros((360, 640, 3), dtype=np.uint8)
    results = detector.detect_and_track(empty_frame)
    assert isinstance(results, list)
    # Blank frame should have 0 persons
    assert len(results) == 0


def test_draw_detections():
    """Verify drawing bounding boxes and tags on frame."""
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    persons = [
        TrackedPerson(track_id=1, bbox=(50, 50, 150, 200), confidence=0.85, center=(100, 125)),
        TrackedPerson(track_id=2, bbox=(250, 60, 350, 210), confidence=0.92, center=(300, 135))
    ]
    annotated = PersonDetector.draw_detections(frame, persons, violation_ids={1}, rapid_ids={2})
    assert annotated is not None
    assert annotated.shape == (360, 640, 3)
