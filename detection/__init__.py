"""
Detection modules package for AI Smart Campus Safety System.
"""
from .person_detector import PersonDetector, TrackedPerson
from .crowd_analyzer import CrowdAnalyzer, CrowdMetrics
from .restricted_area import RestrictedAreaDetector
from .movement_analyzer import MovementAnalyzer
from .alert_manager import AlertManager

__all__ = [
    "PersonDetector",
    "TrackedPerson",
    "CrowdAnalyzer",
    "CrowdMetrics",
    "RestrictedAreaDetector",
    "MovementAnalyzer",
    "AlertManager"
]
