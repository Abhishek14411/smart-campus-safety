"""
AI Smart Campus Safety & Monitoring System - Abnormal Movement Detection
========================================================================
MODULE 4: Movement Velocity & Anomaly Heuristic
- Tracks spatial displacement of each anonymous person ID across consecutive frames
- Computes Euclidean pixel distance: sqrt((x2-x1)^2 + (y2-y1)^2)
- Compares displacement against a configurable speed threshold (RAPID_MOVEMENT_THRESHOLD)
- Requires rapid movement condition to persist for N consecutive frames (CONSECUTIVE_FRAMES_REQUIRED)
  to prevent momentary detection jitter or bounding box noise from causing false alarms
- Explainable heuristic suitable for college viva demonstrations
"""

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional
import cv2
import numpy as np
import config
from .person_detector import TrackedPerson


@dataclass
class TrackHistory:
    """
    Maintains coordinate and velocity history for an individual tracked person.
    """
    track_id: int
    positions: deque = field(default_factory=lambda: deque(maxlen=config.MAX_TRACK_HISTORY))
    speeds: deque = field(default_factory=lambda: deque(maxlen=config.MAX_TRACK_HISTORY))
    consecutive_rapid_count: int = 0
    is_rapid: bool = False
    last_seen_frame: int = 0


class MovementAnalyzer:
    """
    Monitors speed anomalies by analyzing displacement per frame per person ID.
    """

    def __init__(
        self,
        speed_threshold: float = config.RAPID_MOVEMENT_THRESHOLD,
        consecutive_frames_req: int = config.CONSECUTIVE_FRAMES_REQUIRED,
        max_history: int = config.MAX_TRACK_HISTORY
    ):
        self.speed_threshold = speed_threshold
        self.consecutive_frames_req = consecutive_frames_req
        self.max_history = max_history
        self.tracks: Dict[int, TrackHistory] = {}
        self.current_frame_idx: int = 0

    def update_thresholds(self, speed_threshold: float, consecutive_frames: int) -> None:
        """
        Dynamically update movement thresholds at runtime.
        """
        self.speed_threshold = max(5.0, float(speed_threshold))
        self.consecutive_frames_req = max(1, int(consecutive_frames))

    def update(self, tracked_people: List[TrackedPerson]) -> Tuple[Set[int], bool]:
        """
        Updates tracking history for each visible person and determines which IDs
        are moving unusually fast.
        
        Returns:
        - rapid_person_ids: Set of person IDs currently exhibiting sustained rapid movement.
        - any_unusual_movement: Boolean True if at least one person is in rapid state.
        """
        self.current_frame_idx += 1
        visible_ids = set()
        rapid_ids: Set[int] = set()

        for person in tracked_people:
            tid = person.track_id
            cx, cy = person.center
            visible_ids.add(tid)

            if tid not in self.tracks:
                self.tracks[tid] = TrackHistory(track_id=tid)

            history = self.tracks[tid]
            history.last_seen_frame = self.current_frame_idx

            if len(history.positions) > 0:
                prev_x, prev_y = history.positions[-1]
                # Calculate Euclidean pixel displacement
                dist = math.hypot(cx - prev_x, cy - prev_y)
                history.speeds.append(dist)

                # Check if current displacement exceeds speed threshold
                if dist >= self.speed_threshold:
                    history.consecutive_rapid_count += 1
                else:
                    # Decay or reset counter if movement returns to normal pace
                    history.consecutive_rapid_count = max(0, history.consecutive_rapid_count - 1)

                # Check if sustained rapid movement criterion is met
                if history.consecutive_rapid_count >= self.consecutive_frames_req:
                    history.is_rapid = True
                    rapid_ids.add(tid)
                else:
                    history.is_rapid = False
            else:
                # First frame for this ID
                history.speeds.append(0.0)
                history.consecutive_rapid_count = 0
                history.is_rapid = False

            history.positions.append((cx, cy))

        # Garbage collect stale tracks not seen for > 40 frames
        stale_threshold = 40
        to_delete = [
            tid for tid, h in self.tracks.items()
            if (self.current_frame_idx - h.last_seen_frame) > stale_threshold
        ]
        for tid in to_delete:
            del self.tracks[tid]

        return rapid_ids, (len(rapid_ids) > 0)

    def draw_motion_trails(
        self,
        frame: np.ndarray,
        rapid_ids: Optional[Set[int]] = None
    ) -> np.ndarray:
        """
        Renders movement trajectory trails behind tracked individuals.
        """
        if frame is None:
            return frame

        rapid_ids = rapid_ids or set()

        for tid, history in self.tracks.items():
            if (self.current_frame_idx - history.last_seen_frame) > 3:
                continue  # Skip drawing for inactive track

            pts = list(history.positions)
            if len(pts) < 2:
                continue

            # Draw trajectory path
            is_fast = tid in rapid_ids
            color = (0, 140, 255) if is_fast else (200, 150, 50)  # Orange or Soft Cyan
            
            for i in range(1, len(pts)):
                thickness = int(np.sqrt(16 * float(i) / len(pts)) + 1)
                cv2.line(frame, pts[i - 1], pts[i], color, thickness, lineType=cv2.LINE_AA)

        return frame
