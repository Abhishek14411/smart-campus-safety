"""
AI Smart Campus Safety & Monitoring System - Crowd Density Analyzer
===================================================================
MODULE 2: Crowd Counting & Density Classification
- Analyzes currently detected persons count
- Classifies density into configurable levels: LOW, MEDIUM, HIGH
- Detects high density threshold breaches for safety alerts
- Configurable thresholds sourced from config.py
"""

from dataclasses import dataclass
from typing import List, Tuple
import config
from .person_detector import TrackedPerson


@dataclass
class CrowdMetrics:
    """
    Data container for current crowd statistics.
    """
    count: int
    level: str             # 'LOW', 'MEDIUM', 'HIGH'
    is_high_density: bool
    status_color: Tuple[int, int, int]  # BGR color for HUD/UI (e.g. Green, Yellow, Red)
    description: str


class CrowdAnalyzer:
    """
    Classifies crowd levels based on configurable thresholds.
    """

    def __init__(
        self,
        low_max: int = config.CROWD_LOW_MAX,
        medium_max: int = config.CROWD_MEDIUM_MAX
    ):
        self.low_max = low_max
        self.medium_max = medium_max

    def update_thresholds(self, low_max: int, medium_max: int) -> None:
        """
        Dynamically updates crowd thresholds at runtime.
        """
        self.low_max = max(1, low_max)
        self.medium_max = max(self.low_max + 1, medium_max)

    def analyze(self, tracked_people: List[TrackedPerson]) -> CrowdMetrics:
        """
        Analyzes the list of detected persons and computes crowd density metrics.
        """
        count = len(tracked_people)

        if count <= self.low_max:
            level = "LOW"
            is_high = False
            # Emerald Green in BGR
            status_color = (60, 180, 75)
            description = f"Normal campus flow ({count} people)"
        elif count <= self.medium_max:
            level = "MEDIUM"
            is_high = False
            # Amber / Gold in BGR
            status_color = (0, 180, 240)
            description = f"Moderate occupancy ({count} people)"
        else:
            level = "HIGH"
            is_high = True
            # Bright Red in BGR
            status_color = (0, 0, 240)
            description = f"Crowd Density High! ({count} people)"

        return CrowdMetrics(
            count=count,
            level=level,
            is_high_density=is_high,
            status_color=status_color,
            description=description
        )
