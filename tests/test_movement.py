"""
Test 6 & 7: Abnormal Movement Velocity & Consecutive Frames Heuristic
Verifies that MovementAnalyzer calculates displacement accurately and triggers
rapid movement anomalies ONLY when high velocity persists for required consecutive frames.
"""

import pytest
from detection.movement_analyzer import MovementAnalyzer
from detection.person_detector import TrackedPerson


def test_normal_walking_movement():
    """Verify normal slow walking does not trigger rapid movement flag."""
    # Speed threshold = 25.0 px/frame, required frames = 3
    analyzer = MovementAnalyzer(speed_threshold=25.0, consecutive_frames_req=3)

    # Simulate person moving 4 pixels per frame (normal walking)
    for frame in range(10):
        person = TrackedPerson(
            track_id=1,
            bbox=(frame * 4, 100, frame * 4 + 30, 180),
            confidence=0.9,
            center=(frame * 4 + 15, 140)
        )
        rapid_ids, has_rapid = analyzer.update([person])
        assert len(rapid_ids) == 0
        assert has_rapid is False


def test_consecutive_frames_requirement():
    """
    Verify that rapid movement triggers ONLY after persisting for consecutive frames.
    A single frame spike (e.g. noise) must NOT trigger an alert.
    """
    analyzer = MovementAnalyzer(speed_threshold=25.0, consecutive_frames_req=3)

    # Frame 1: Initial position at (100, 100)
    p = TrackedPerson(1, (100, 100, 130, 180), 0.9, (115, 140))
    rapid_ids, has_rapid = analyzer.update([p])
    assert has_rapid is False

    # Frame 2: Rapid jump by +35 pixels (Frame 1 of fast movement)
    p = TrackedPerson(1, (135, 100, 165, 180), 0.9, (150, 140))
    rapid_ids, has_rapid = analyzer.update([p])
    # Should NOT trigger yet (needs 3 consecutive frames)
    assert has_rapid is False
    assert len(rapid_ids) == 0

    # Frame 3: Rapid jump by +35 pixels (Frame 2 of fast movement)
    p = TrackedPerson(1, (170, 100, 200, 180), 0.9, (185, 140))
    rapid_ids, has_rapid = analyzer.update([p])
    # Should NOT trigger yet
    assert has_rapid is False

    # Frame 4: Rapid jump by +35 pixels (Frame 3 of fast movement - threshold met!)
    p = TrackedPerson(1, (205, 100, 235, 180), 0.9, (220, 140))
    rapid_ids, has_rapid = analyzer.update([p])
    # Must now trigger!
    assert has_rapid is True
    assert 1 in rapid_ids


def test_movement_recovery_to_normal():
    """Verify rapid movement status resets when person slows back down."""
    analyzer = MovementAnalyzer(speed_threshold=20.0, consecutive_frames_req=2)

    # Trigger rapid state
    analyzer.update([TrackedPerson(1, (0, 0, 10, 10), 0.9, (0, 0))])
    analyzer.update([TrackedPerson(1, (30, 0, 40, 10), 0.9, (30, 0))])
    rapid_ids, has_rapid = analyzer.update([TrackedPerson(1, (60, 0, 70, 10), 0.9, (60, 0))])
    assert has_rapid is True

    # Slow down: move only 2 pixels
    analyzer.update([TrackedPerson(1, (62, 0, 72, 10), 0.9, (62, 0))])
    rapid_ids, has_rapid = analyzer.update([TrackedPerson(1, (64, 0, 74, 10), 0.9, (64, 0))])
    assert has_rapid is False
