"""
AI Smart Campus Safety & Monitoring System - Centralized Alert Manager
======================================================================
MODULE 5: Centralized Alert Management & Debounce System
- Coordinates alert generation from Crowd Analyzer, Restricted Area, and Movement Analyzer
- Enforces strict debounce / cooldown timers to prevent duplicate alert spamming
- Persists valid safety events into SQLite database
- Maintains thread-safe in-memory cache for live dashboard streaming
"""

import time
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
import config
from database import db
from .person_detector import TrackedPerson
from .crowd_analyzer import CrowdMetrics


class AlertManager:
    """
    Central alert manager with per-event and per-ID cooldown management.
    """

    def __init__(self):
        # Timestamp trackers for cooldowns:
        # last_crowd_alert_time: float
        self.last_crowd_alert_time: float = 0.0
        # last_restricted_alert_times: Dict[int, float] (person_id -> timestamp)
        self.last_restricted_alert_times: Dict[int, float] = {}
        # last_movement_alert_times: Dict[int, float] (person_id -> timestamp)
        self.last_movement_alert_times: Dict[int, float] = {}

        # In-memory recent alerts buffer for low-latency dashboard polling
        self.recent_alerts_cache: deque = deque(maxlen=20)
        self.source_name: str = "Camera 01 (Campus Main)"

    def set_source_name(self, name: str) -> None:
        """
        Updates the active camera/source label.
        """
        self.source_name = name

    def process_events(
        self,
        crowd_metrics: CrowdMetrics,
        violators: List[TrackedPerson],
        rapid_person_ids: set,
        total_people: int
    ) -> List[Dict[str, Any]]:
        """
        Evaluates current analytics state against cooldown timers and triggers
        database persistence for new qualifying events.
        
        Returns:
        - List of newly generated alerts during this frame.
        """
        now = time.time()
        new_alerts = []

        # -------------------------------------------------------------
        # 1. Evaluate High Crowd Density Alert
        # -------------------------------------------------------------
        if crowd_metrics.is_high_density:
            time_since_last = now - self.last_crowd_alert_time
            if time_since_last >= config.ALERT_COOLDOWN_CROWD:
                self.last_crowd_alert_time = now
                alert = db.create_alert(
                    alert_type="High Crowd Density",
                    person_id=None,
                    people_count=crowd_metrics.count,
                    source=self.source_name,
                    severity="HIGH",
                    status="ACTIVE",
                    details=f"High crowd density detected: {crowd_metrics.count} persons visible."
                )
                if alert:
                    self.recent_alerts_cache.appendleft(alert)
                    new_alerts.append(alert)

        # -------------------------------------------------------------
        # 2. Evaluate Restricted Area Violations
        # -------------------------------------------------------------
        for violator in violators:
            tid = violator.track_id
            last_alert = self.last_restricted_alert_times.get(tid, 0.0)
            if (now - last_alert) >= config.ALERT_COOLDOWN_RESTRICTED:
                self.last_restricted_alert_times[tid] = now
                alert = db.create_alert(
                    alert_type="Restricted Area Entry",
                    person_id=tid,
                    people_count=total_people,
                    source=self.source_name,
                    severity="CRITICAL",
                    status="ACTIVE",
                    details=f"Person #{tid} entered restricted perimeter '{config.RESTRICTED_AREA_NAME}'."
                )
                if alert:
                    self.recent_alerts_cache.appendleft(alert)
                    new_alerts.append(alert)

        # -------------------------------------------------------------
        # 3. Evaluate Unusual Rapid Movement Alerts
        # -------------------------------------------------------------
        for tid in rapid_person_ids:
            last_alert = self.last_movement_alert_times.get(tid, 0.0)
            if (now - last_alert) >= config.ALERT_COOLDOWN_MOVEMENT:
                self.last_movement_alert_times[tid] = now
                alert = db.create_alert(
                    alert_type="Unusual Rapid Movement",
                    person_id=tid,
                    people_count=total_people,
                    source=self.source_name,
                    severity="MEDIUM",
                    status="ACTIVE",
                    details=f"Unusual rapid movement detected for Person #{tid} across consecutive frames."
                )
                if alert:
                    self.recent_alerts_cache.appendleft(alert)
                    new_alerts.append(alert)

        # Cleanup old cooldown map entries to avoid unbounded growth
        if len(self.last_restricted_alert_times) > 100:
            self.last_restricted_alert_times = {
                k: v for k, v in self.last_restricted_alert_times.items()
                if (now - v) < config.ALERT_COOLDOWN_RESTRICTED * 2
            }
        if len(self.last_movement_alert_times) > 100:
            self.last_movement_alert_times = {
                k: v for k, v in self.last_movement_alert_times.items()
                if (now - v) < config.ALERT_COOLDOWN_MOVEMENT * 2
            }

        return new_alerts

    def get_live_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Returns recent alerts directly from the fast memory buffer or database.
        """
        if self.recent_alerts_cache:
            return list(self.recent_alerts_cache)[:limit]
        return db.get_recent_alerts(limit)
