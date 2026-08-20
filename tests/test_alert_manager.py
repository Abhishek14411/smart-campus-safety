"""
Test 5: Alert Manager Debounce & Deduplication Logic
Verifies that AlertManager enforces cooldown intervals so sustained events
do not generate hundreds of duplicate alerts.
"""

import time
import pytest
from detection.alert_manager import AlertManager
from detection.crowd_analyzer import CrowdMetrics
from detection.person_detector import TrackedPerson
from database import db
import config


@pytest.fixture(autouse=True)
def setup_test_db():
    """Ensure database is initialized and cleared before testing."""
    db.init_db()
    db.clear_alert_history()
    yield
    db.clear_alert_history()


def test_restricted_area_alert_cooldown():
    """
    Verify that a person staying inside a restricted area generates exactly 1 alert,
    and duplicate alerts are suppressed during the cooldown window.
    """
    manager = AlertManager()
    violator = TrackedPerson(track_id=42, bbox=(10, 10, 50, 50), confidence=0.9, center=(30, 30))
    crowd_normal = CrowdMetrics(count=1, level="LOW", is_high_density=False, status_color=(0, 255, 0), description="")

    # Frame 1: Initial entry -> Generates 1 alert
    alerts_f1 = manager.process_events(
        crowd_metrics=crowd_normal,
        violators=[violator],
        rapid_person_ids=set(),
        total_people=1
    )
    assert len(alerts_f1) == 1
    assert alerts_f1[0]["alert_type"] == "Restricted Area Entry"
    assert alerts_f1[0]["person_id"] == 42

    # Frame 2 to 50: Continuous frames with same person inside restricted area
    # All duplicate alerts must be suppressed by cooldown
    for _ in range(50):
        dup_alerts = manager.process_events(
            crowd_metrics=crowd_normal,
            violators=[violator],
            rapid_person_ids=set(),
            total_people=1
        )
        assert len(dup_alerts) == 0

    # Total alerts in database should still be exactly 1
    recent = db.get_recent_alerts(10)
    assert len(recent) == 1


def test_crowd_high_alert_cooldown():
    """Verify that continuous HIGH crowd density is debounced."""
    manager = AlertManager()
    crowd_high = CrowdMetrics(count=30, level="HIGH", is_high_density=True, status_color=(0, 0, 255), description="")

    # Frame 1: High crowd triggered -> 1 alert generated
    alerts1 = manager.process_events(crowd_high, violators=[], rapid_person_ids=set(), total_people=30)
    assert len(alerts1) == 1
    assert alerts1[0]["alert_type"] == "High Crowd Density"

    # Subsequent immediate frames should not generate spam alerts
    for _ in range(30):
        alerts_dup = manager.process_events(crowd_high, violators=[], rapid_person_ids=set(), total_people=30)
        assert len(alerts_dup) == 0
