"""
AI Smart Campus Safety & Monitoring System - Restricted Area ROI Detection
==========================================================================
MODULE 3: Restricted Area (ROI) Entry Detection
- Defines a configurable rectangular zone for restricted/sensitive campus areas
  (e.g., Server Room, Lab Core, Hazardous Electrical Room, Off-limits Gate)
- Analyzes center coordinates (cx, cy) of all tracked persons
- Detects unauthorized presence inside the boundary
- Renders glowing visual warning zone and entry indicators on video
"""

from typing import List, Tuple, Set, Optional
import cv2
import numpy as np
import config
from .person_detector import TrackedPerson


class RestrictedAreaDetector:
    """
    Monitors a configurable 2D bounding region for unauthorized personnel entry.
    """

    def __init__(
        self,
        coords: Optional[List[int]] = None,
        name: str = config.RESTRICTED_AREA_NAME
    ):
        self.name = name
        self.coords = coords or list(config.RESTRICTED_AREA_COORDS)

    def set_coordinates(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """
        Updates the restricted area boundary coordinates.
        Ensures proper ordering (x1 < x2, y1 < y2).
        """
        min_x = min(x1, x2)
        max_x = max(x1, x2)
        min_y = min(y1, y2)
        max_y = max(y1, y2)
        self.coords = [min_x, min_y, max_x, max_y]

    def is_inside(self, point: Tuple[int, int]) -> bool:
        """
        Tests if a coordinate (cx, cy) falls within the rectangular ROI.
        """
        px, py = point
        x1, y1, x2, y2 = self.coords
        return (x1 <= px <= x2) and (y1 <= py <= y2)

    def check_violations(self, tracked_people: List[TrackedPerson]) -> List[TrackedPerson]:
        """
        Returns a list of TrackedPerson instances whose center point is inside the restricted area.
        """
        violators = []
        for person in tracked_people:
            if self.is_inside(person.center):
                violators.append(person)
        return violators

    def draw_overlay(
        self,
        frame: np.ndarray,
        violator_ids: Optional[Set[int]] = None
    ) -> np.ndarray:
        """
        Draws a semi-transparent warning overlay for the restricted zone on the video frame.
        """
        if frame is None or len(self.coords) != 4:
            return frame

        x1, y1, x2, y2 = self.coords
        h, w = frame.shape[:2]

        # Clamp coordinates to frame dimensions
        x1 = max(0, min(x1, w - 1))
        x2 = max(0, min(x2, w - 1))
        y1 = max(0, min(y1, h - 1))
        y2 = max(0, min(y2, h - 1))

        if x2 <= x1 or y2 <= y1:
            return frame

        has_active_violation = bool(violator_ids and len(violator_ids) > 0)

        # Color selection: Bright Red if actively breached, Red-Orange if clear
        if has_active_violation:
            zone_color = (0, 0, 240)       # BGR Red
            fill_color = (0, 0, 200)
            status_text = "! RESTRICTED AREA - BREACH DETECTED !"
        else:
            zone_color = (0, 100, 240)     # BGR Orange-Red
            fill_color = (0, 50, 180)
            status_text = f"RESTRICTED AREA: {self.name}"

        # 1. Draw translucent colored overlay fill inside ROI
        overlay = frame.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), fill_color, -1)
        alpha = 0.22 if not has_active_violation else 0.38
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

        # 2. Draw border
        thickness = 3 if has_active_violation else 2
        cv2.rectangle(frame, (x1, y1), (x2, y2), zone_color, thickness, lineType=cv2.LINE_AA)

        # 3. Draw hazard stripes / corner brackets
        corner_len = min(20, (x2 - x1) // 3, (y2 - y1) // 3)
        bracket_thick = 4
        # Top-Left
        cv2.line(frame, (x1, y1), (x1 + corner_len, y1), zone_color, bracket_thick)
        cv2.line(frame, (x1, y1), (x1, y1 + corner_len), zone_color, bracket_thick)
        # Top-Right
        cv2.line(frame, (x2, y1), (x2 - corner_len, y1), zone_color, bracket_thick)
        cv2.line(frame, (x2, y1), (x2, y1 + corner_len), zone_color, bracket_thick)
        # Bottom-Left
        cv2.line(frame, (x1, y2), (x1 + corner_len, y2), zone_color, bracket_thick)
        cv2.line(frame, (x1, y2), (x1, y2 - corner_len), zone_color, bracket_thick)
        # Bottom-Right
        cv2.line(frame, (x2, y2), (x2 - corner_len, y2), zone_color, bracket_thick)
        cv2.line(frame, (x2, y2), (x2, y2 - corner_len), zone_color, bracket_thick)

        # 4. Render Banner Title above or inside the top of the zone
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.44
        text_thick = 1
        (tw, th), baseline = cv2.getTextSize(status_text, font, font_scale, text_thick)

        banner_y1 = max(0, y1 - th - 8)
        banner_y2 = y1
        cv2.rectangle(frame, (x1, banner_y1), (x1 + tw + 10, banner_y2), zone_color, -1)
        cv2.putText(
            frame,
            status_text,
            (x1 + 5, y1 - 4),
            font,
            font_scale,
            (255, 255, 255),
            text_thick,
            lineType=cv2.LINE_AA
        )

        return frame
