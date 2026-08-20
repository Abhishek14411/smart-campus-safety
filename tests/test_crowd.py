"""
Test 2 & 3: People Counting & Crowd Level Classification
Verifies that CrowdAnalyzer correctly counts people and transitions across
LOW, MEDIUM, and HIGH density thresholds.
"""

import pytest
from detection.crowd_analyzer import CrowdAnalyzer
from detection.person_detector import TrackedPerson


def make_mock_people(count: int):
    """Helper to generate mock TrackedPerson objects."""
    return [
        TrackedPerson(
            track_id=i + 1,
            bbox=(i * 10, 10, i * 10 + 30, 80),
            confidence=0.90,
            center=(i * 10 + 15, 45)
        )
        for i in range(count)
    ]


def test_crowd_levels():
    """Verify LOW, MEDIUM, and HIGH crowd level classifications."""
    analyzer = CrowdAnalyzer(low_max=5, medium_max=12)

    # 1. Test LOW level (0 to 5 people)
    metrics_0 = analyzer.analyze([])
    assert metrics_0.count == 0
    assert metrics_0.level == "LOW"
    assert metrics_0.is_high_density is False

    metrics_4 = analyzer.analyze(make_mock_people(4))
    assert metrics_4.count == 4
    assert metrics_4.level == "LOW"
    assert metrics_4.is_high_density is False

    # 2. Test MEDIUM level (6 to 12 people)
    metrics_6 = analyzer.analyze(make_mock_people(6))
    assert metrics_6.count == 6
    assert metrics_6.level == "MEDIUM"
    assert metrics_6.is_high_density is False

    metrics_12 = analyzer.analyze(make_mock_people(12))
    assert metrics_12.count == 12
    assert metrics_12.level == "MEDIUM"
    assert metrics_12.is_high_density is False

    # 3. Test HIGH level (> 12 people)
    metrics_15 = analyzer.analyze(make_mock_people(15))
    assert metrics_15.count == 15
    assert metrics_15.level == "HIGH"
    assert metrics_15.is_high_density is True


def test_dynamic_threshold_updates():
    """Verify updating crowd thresholds dynamically changes classification."""
    analyzer = CrowdAnalyzer(low_max=2, medium_max=4)
    assert analyzer.analyze(make_mock_people(3)).level == "MEDIUM"
    assert analyzer.analyze(make_mock_people(5)).level == "HIGH"

    # Update thresholds
    analyzer.update_thresholds(low_max=10, medium_max=20)
    assert analyzer.analyze(make_mock_people(5)).level == "LOW"
    assert analyzer.analyze(make_mock_people(15)).level == "MEDIUM"
    assert analyzer.analyze(make_mock_people(25)).level == "HIGH"
