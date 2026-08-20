"""
AI Smart Campus Safety & Monitoring System - Person Detection & Tracking
========================================================================
MODULE 1: YOLO Person Detection & Tracking
- Uses Ultralytics YOLO (lightweight model, e.g. yolov8n.pt)
- Detects ONLY person class (class ID 0)
- Assigns persistent, anonymous tracking IDs (e.g., Person #1, Person #4)
- Calculates bounding box center coordinates for spatial analysis
- Fully CPU-friendly on standard Windows laptops
"""

import os
from dataclasses import dataclass
from typing import List, Tuple, Optional
import cv2
import numpy as np
from ultralytics import YOLO
import config


@dataclass
class TrackedPerson:
    """
    Represents an anonymously detected and tracked person in a video frame.
    """
    track_id: int
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    confidence: float
    center: Tuple[int, int]           # (cx, cy)


class PersonDetector:
    """
    YOLOv8-based Person Detector and Tracker for anonymous campus safety monitoring.
    """

    def __init__(
        self,
        model_name: str = config.YOLO_MODEL_NAME,
        conf_threshold: float = config.MODEL_CONFIDENCE_THRESHOLD,
        iou_threshold: float = config.IOU_THRESHOLD
    ):
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.model_name = model_name
        self.model = None
        self._next_fallback_id = 1000
        self._id_mapping = {}  # maps ephemeral indices if tracker fails
        
        self._load_model()

    def _load_model(self) -> None:
        """
        Loads the YOLO model. If local model not present, Ultralytics downloads it automatically.
        """
        try:
            print(f"[YOLO] Loading model '{self.model_name}'...")
            self.model = YOLO(self.model_name)
            print("[YOLO] Model loaded successfully.")
        except Exception as e:
            print(f"[YOLO ERROR] Failed to load model '{self.model_name}': {e}")
            raise

    def detect_and_track(self, frame: np.ndarray) -> List[TrackedPerson]:
        """
        Runs YOLO person detection and multi-object tracking on the input frame.
        
        Parameters:
        - frame: OpenCV BGR image (np.ndarray)
        
        Returns:
        - List of TrackedPerson objects for all detected people.
        """
        if self.model is None or frame is None or frame.size == 0:
            return []

        tracked_people: List[TrackedPerson] = []

        try:
            # Run YOLO track with persist=True, filtering strictly for class 0 (person)
            results = self.model.track(
                source=frame,
                persist=True,
                classes=[0],  # Class 0 is 'person' in COCO dataset
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                verbose=False
            )

            if not results or len(results) == 0:
                return []

            result = results[0]
            boxes = result.boxes

            if boxes is None or len(boxes) == 0:
                return []

            for i, box in enumerate(boxes):
                # Ensure it's a person class
                cls_id = int(box.cls[0].item()) if box.cls is not None else 0
                if cls_id != 0:
                    continue

                conf = float(box.conf[0].item()) if box.conf is not None else 0.0

                # Extract bounding box coordinates [x1, y1, x2, y2]
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                x1, y1, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])

                # Extract Tracking ID
                if box.id is not None:
                    track_id = int(box.id[0].item())
                else:
                    # Fallback ID assignment if tracking ID is momentarily unassigned
                    track_id = self._get_fallback_id(x1, y1, x2, y2)

                # Compute center point of person (useful for ROI and movement tracking)
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)

                tracked_people.append(
                    TrackedPerson(
                        track_id=track_id,
                        bbox=(x1, y1, x2, y2),
                        confidence=conf,
                        center=(cx, cy)
                    )
                )

        except Exception as e:
            print(f"[YOLO TRACKING ERROR] Error during inference: {e}")

        return tracked_people

    def _get_fallback_id(self, x1: int, y1: int, x2: int, y2: int) -> int:
        """
        Simple centroid matching fallback if the YOLO tracker does not return an ID.
        """
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        best_id = None
        min_dist = 60.0  # Max pixel distance for fallback association

        for tid, prev_center in list(self._id_mapping.items()):
            dist = np.hypot(cx - prev_center[0], cy - prev_center[1])
            if dist < min_dist:
                min_dist = dist
                best_id = tid

        if best_id is None:
            best_id = self._next_fallback_id
            self._next_fallback_id += 1

        self._id_mapping[best_id] = (cx, cy)
        # Keep id_mapping bounded
        if len(self._id_mapping) > 100:
            self._id_mapping.clear()

        return best_id

    @staticmethod
    def draw_detections(
        frame: np.ndarray,
        tracked_people: List[TrackedPerson],
        violation_ids: Optional[set] = None,
        rapid_ids: Optional[set] = None
    ) -> np.ndarray:
        """
        Renders bounding boxes, tracking ID tags, confidence scores, and center points
        onto the video frame with a clean modern HUD style.
        """
        if frame is None or not tracked_people:
            return frame

        violation_ids = violation_ids or set()
        rapid_ids = rapid_ids or set()

        for person in tracked_people:
            x1, y1, x2, y2 = person.bbox
            cx, cy = person.center
            tid = person.track_id
            conf = person.confidence

            # Determine color scheme:
            # Red/Orange if in violation or rapid movement, otherwise Cyan/Emerald
            if tid in violation_ids:
                box_color = (0, 0, 240)      # Bright Red BGR
                tag_bg = (0, 0, 180)
                status_text = " [RESTRICTED]"
            elif tid in rapid_ids:
                box_color = (0, 140, 255)    # Orange BGR
                tag_bg = (0, 100, 200)
                status_text = " [FAST]"
            else:
                box_color = (235, 180, 0)    # Modern Cyan/Teal BGR (235, 180, 0)
                tag_bg = (180, 120, 0)
                status_text = ""

            # Draw primary bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2, lineType=cv2.LINE_AA)

            # Draw corner accents for futuristic HUD look
            corner_len = min(15, (x2 - x1) // 4, (y2 - y1) // 4)
            if corner_len > 3:
                thick = 3
                # Top-Left
                cv2.line(frame, (x1, y1), (x1 + corner_len, y1), box_color, thick)
                cv2.line(frame, (x1, y1), (x1, y1 + corner_len), box_color, thick)
                # Top-Right
                cv2.line(frame, (x2, y1), (x2 - corner_len, y1), box_color, thick)
                cv2.line(frame, (x2, y1), (x2, y1 + corner_len), box_color, thick)
                # Bottom-Left
                cv2.line(frame, (x1, y2), (x1 + corner_len, y2), box_color, thick)
                cv2.line(frame, (x1, y2), (x1, y2 - corner_len), box_color, thick)
                # Bottom-Right
                cv2.line(frame, (x2, y2), (x2 - corner_len, y2), box_color, thick)
                cv2.line(frame, (x2, y2), (x2, y2 - corner_len), box_color, thick)

            # Draw center point dot
            cv2.circle(frame, (cx, cy), 4, box_color, -1, lineType=cv2.LINE_AA)
            cv2.circle(frame, (cx, cy), 6, (255, 255, 255), 1, lineType=cv2.LINE_AA)

            # Draw Label Tag (Anonymous Person ID + Confidence)
            label = f"Person #{tid} ({int(conf * 100)}%){status_text}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.42
            thickness = 1
            (w, h), baseline = cv2.getTextSize(label, font, font_scale, thickness)

            tag_y1 = max(0, y1 - h - 6)
            tag_y2 = max(h + 6, y1)
            cv2.rectangle(frame, (x1, tag_y1), (x1 + w + 8, tag_y2), tag_bg, -1)
            cv2.putText(
                frame,
                label,
                (x1 + 4, tag_y2 - 4),
                font,
                font_scale,
                (255, 255, 255),
                thickness,
                lineType=cv2.LINE_AA
            )

        return frame
