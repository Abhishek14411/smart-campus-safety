"""
Test 8: SQLite Database Operations Module
Verifies alert creation, retrieval, filtering, statistics, and clearing.
"""

import pytest
from database import db


@pytest.fixture(autouse=True)
def clean_db():
    db.init_db()
    db.clear_alert_history()
    yield
    db.clear_alert_history()


def test_alert_crud():
    """Verify inserting, querying, and clearing alert records."""
    # 1. Insert Alerts
    a1 = db.create_alert("Restricted Area Entry", person_id=12, people_count=3, severity="CRITICAL", details="Test Entry")
    a2 = db.create_alert("High Crowd Density", person_id=None, people_count=45, severity="HIGH", details="Test Crowd")
    a3 = db.create_alert("Unusual Rapid Movement", person_id=7, people_count=5, severity="MEDIUM", details="Test Speed")

    assert a1 is not None and a1["id"] > 0
    assert a2 is not None and a2["id"] > 0
    assert a3 is not None and a3["id"] > 0

    # 2. Query Recent Alerts
    recent = db.get_recent_alerts(10)
    assert len(recent) == 3
    # Most recent first
    assert recent[0]["alert_type"] == "Unusual Rapid Movement"

    # 3. Query with Filter
    restricted_only = db.get_alert_history(limit=10, alert_type_filter="Restricted Area Entry")
    assert len(restricted_only) == 1
    assert restricted_only[0]["person_id"] == 12

    # 4. Check Statistics
    stats = db.get_alert_statistics()
    assert stats["total_alerts"] == 3
    assert stats["restricted_count"] == 1
    assert stats["crowd_count"] == 1
    assert stats["movement_count"] == 1

    # 5. Clear History
    cleared = db.clear_alert_history()
    assert cleared is True
    assert len(db.get_recent_alerts()) == 0
    assert db.get_alert_statistics()["total_alerts"] == 0
