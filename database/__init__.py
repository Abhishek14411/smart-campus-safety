"""
Database package initialization.
"""
from .db import (
    init_db,
    create_alert,
    get_recent_alerts,
    get_alert_history,
    clear_alert_history,
    get_alert_statistics
)

__all__ = [
    "init_db",
    "create_alert",
    "get_recent_alerts",
    "get_alert_history",
    "clear_alert_history",
    "get_alert_statistics"
]
