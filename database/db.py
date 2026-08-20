"""
AI Smart Campus Safety & Monitoring System - Database Layer
============================================================
Handles SQLite database operations for persisting safety alerts and system events.
Uses parameterized queries and connection context managers for thread safety.
"""

import sqlite3
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import config


def get_connection() -> sqlite3.Connection:
    """
    Creates and returns a SQLite connection configured for WAL mode and dictionary rows.
    """
    db_path = Path(config.DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(db_path), timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrency in multi-threaded Flask apps
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    return conn


def init_db() -> None:
    """
    Initializes the SQLite database and creates the 'alerts' table if it does not exist.
    """
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    person_id INTEGER,
                    people_count INTEGER,
                    source TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    details TEXT
                );
            """)
            # Create indices for quick sorting and filtering
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts (timestamp DESC);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts (alert_type);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts (severity);")
    finally:
        conn.close()


def create_alert(
    alert_type: str,
    person_id: Optional[int] = None,
    people_count: Optional[int] = None,
    source: str = "Camera 01 (Campus Main)",
    severity: str = "MEDIUM",
    status: str = "ACTIVE",
    details: str = ""
) -> Optional[Dict[str, Any]]:
    """
    Inserts a new safety alert record into the database.
    
    Parameters:
    - alert_type: Description of alert (e.g. 'Restricted Area Entry', 'High Crowd Density', 'Unusual Rapid Movement')
    - person_id: Tracking ID of person involved (if applicable)
    - people_count: Total people detected at moment of alert
    - source: Video or camera source name
    - severity: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    - status: 'ACTIVE', 'ACKNOWLEDGED', 'RESOLVED'
    - details: Optional human-readable description
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    try:
        with conn:
            cursor = conn.execute("""
                INSERT INTO alerts (timestamp, alert_type, person_id, people_count, source, severity, status, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, alert_type, person_id, people_count, source, severity, status, details))
            
            alert_id = cursor.lastrowid
            
        return {
            "id": alert_id,
            "timestamp": timestamp,
            "alert_type": alert_type,
            "person_id": person_id,
            "people_count": people_count,
            "source": source,
            "severity": severity,
            "status": status,
            "details": details
        }
    except Exception as e:
        print(f"[DB ERROR] Failed to create alert: {e}")
        return None
    finally:
        conn.close()


def get_recent_alerts(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieves the most recent alerts ordered by timestamp descending.
    """
    conn = get_connection()
    try:
        cursor = conn.execute("""
            SELECT id, timestamp, alert_type, person_id, people_count, source, severity, status, details
            FROM alerts
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB ERROR] Failed to fetch recent alerts: {e}")
        return []
    finally:
        conn.close()


def get_alert_history(limit: int = 100, offset: int = 0, alert_type_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves historical alerts with optional filtering and pagination.
    """
    conn = get_connection()
    try:
        if alert_type_filter and alert_type_filter.upper() != "ALL":
            cursor = conn.execute("""
                SELECT id, timestamp, alert_type, person_id, people_count, source, severity, status, details
                FROM alerts
                WHERE alert_type = ?
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """, (alert_type_filter, limit, offset))
        else:
            cursor = conn.execute("""
                SELECT id, timestamp, alert_type, person_id, people_count, source, severity, status, details
                FROM alerts
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB ERROR] Failed to fetch alert history: {e}")
        return []
    finally:
        conn.close()


def clear_alert_history() -> bool:
    """
    Safely deletes all alert records from the database.
    """
    conn = get_connection()
    try:
        with conn:
            conn.execute("DELETE FROM alerts;")
            # Vacuum or reset sequence
            conn.execute("DELETE FROM sqlite_sequence WHERE name='alerts';")
        return True
    except Exception as e:
        print(f"[DB ERROR] Failed to clear alert history: {e}")
        return False
    finally:
        conn.close()


def get_alert_statistics() -> Dict[str, Any]:
    """
    Computes summary metrics from the alerts table for the dashboard.
    """
    conn = get_connection()
    try:
        cursor = conn.execute("""
            SELECT 
                COUNT(*) AS total_alerts,
                SUM(CASE WHEN severity = 'HIGH' OR severity = 'CRITICAL' THEN 1 ELSE 0 END) AS high_severity_count,
                SUM(CASE WHEN alert_type LIKE '%Restricted%' THEN 1 ELSE 0 END) AS restricted_count,
                SUM(CASE WHEN alert_type LIKE '%Crowd%' THEN 1 ELSE 0 END) AS crowd_count,
                SUM(CASE WHEN alert_type LIKE '%Movement%' THEN 1 ELSE 0 END) AS movement_count
            FROM alerts
        """)
        row = cursor.fetchone()
        if row:
            return {
                "total_alerts": row["total_alerts"] or 0,
                "high_severity_count": row["high_severity_count"] or 0,
                "restricted_count": row["restricted_count"] or 0,
                "crowd_count": row["crowd_count"] or 0,
                "movement_count": row["movement_count"] or 0,
            }
        return {"total_alerts": 0, "high_severity_count": 0, "restricted_count": 0, "crowd_count": 0, "movement_count": 0}
    except Exception as e:
        print(f"[DB ERROR] Failed to compute stats: {e}")
        return {"total_alerts": 0, "high_severity_count": 0, "restricted_count": 0, "crowd_count": 0, "movement_count": 0}
    finally:
        conn.close()
