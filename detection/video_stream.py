"""
AI Smart Campus Safety & Monitoring System - Video Stream Processing Pipeline
=============================================================================
Coordinates video frame acquisition (Uploaded MP4/AVI/MOV / Webcam), multi-module AI inference,
visual HUD overlay generation, playback state control (START, STOP, RESET), and MJPEG streaming.
"""

import time
import threading
from typing import Optional, Dict, Any, Generator, List
from pathlib import Path
import cv2
import numpy as np

import config
from .person_detector import PersonDetector, TrackedPerson
from .crowd_analyzer import CrowdAnalyzer, CrowdMetrics
from .restricted_area import RestrictedAreaDetector
from .movement_analyzer import MovementAnalyzer
from .alert_manager import AlertManager


class VideoStreamPipeline:
    """
    Multi-threaded computer vision pipeline executing YOLO detection, tracking,
    crowd counting, restricted area, and movement anomaly heuristics with
    full playback state control (START, STOP, RESET, COMPLETED).
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.running = False
        self.thread: Optional[threading.Thread] = None

        # Playback State Machine: "IDLE", "ANALYZING", "STOPPED", "COMPLETED"
        self.state = "IDLE"

        # Source configuration
        self.source_type = config.DEFAULT_VIDEO_SOURCE_TYPE  # "video" or "webcam"
        self.video_path = config.DEFAULT_VIDEO_PATH
        self.video_filename = "campus.mp4" if Path(config.DEFAULT_VIDEO_PATH).exists() else ""
        self.webcam_index = config.WEBCAM_INDEX
        self.cap: Optional[cv2.VideoCapture] = None
        self.last_valid_frame: Optional[np.ndarray] = None

        # Session Metrics Tracker (for end-of-video summary report)
        self.session_start_time: float = 0.0
        self.session_duration_sec: float = 0.0
        self.session_frames_processed: int = 0
        self.session_max_people: int = 0
        self.session_max_crowd_level: str = "LOW"
        self.session_total_alerts: int = 0
        self.session_restricted_alerts: int = 0
        self.session_crowd_alerts: int = 0
        self.session_movement_alerts: int = 0

        # Computer Vision Modules
        self.detector = PersonDetector()
        self.crowd_analyzer = CrowdAnalyzer()
        self.restricted_detector = RestrictedAreaDetector()
        self.movement_analyzer = MovementAnalyzer()
        self.alert_manager = AlertManager()

        # Telemetry & State Cache
        self.latest_jpeg: Optional[bytes] = None
        self.fps: float = 0.0
        self.latest_telemetry: Dict[str, Any] = {
            "people_count": 0,
            "crowd_level": "LOW",
            "crowd_description": "System Standby",
            "movement_status": "NORMAL",
            "restricted_status": "CLEAR",
            "overall_system_status": "SAFE",
            "fps": 0.0,
            "active_alerts_count": 0,
            "source_type": self.source_type.upper(),
            "source_label": self.video_filename or "No Video Selected",
            "analysis_state": self.state,
            "selected_video_name": self.video_filename,
            "session_summary": None
        }

    def start(self) -> None:
        """
        Starts the background processing thread.
        """
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()
        print("[PIPELINE] Video stream pipeline worker started.")

    def stop(self) -> None:
        """
        Stops the background processing thread and releases resources.
        """
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        self._release_capture()
        print("[PIPELINE] Video stream pipeline stopped.")

    # -------------------------------------------------------------
    # Video Playback Controls (Select, Start, Stop, Reset)
    # -------------------------------------------------------------

    def set_video_source(self, file_path: str, filename: Optional[str] = None) -> bool:
        """
        Sets a new prerecorded video file as the active source in IDLE state.
        """
        with self.lock:
            self._release_capture()
            self.video_path = file_path
            self.video_filename = filename or Path(file_path).name
            self.source_type = "video"
            self.state = "IDLE"
            self.last_valid_frame = None
            self._reset_session_metrics()
            print(f"[PIPELINE] Active video set to: {self.video_filename}")
            return True

    def start_analysis(self) -> Dict[str, Any]:
        """
        Starts or restarts AI analysis from frame 0 for the selected video.
        """
        with self.lock:
            if not self.video_path or not Path(self.video_path).exists():
                return {"status": "error", "message": "No valid video file selected."}

            self._release_capture()
            self._reset_session_metrics()
            
            # Re-initialize VideoCapture
            self.cap = cv2.VideoCapture(str(self.video_path))
            if not self.cap.isOpened():
                return {"status": "error", "message": "Failed to open video file with OpenCV."}

            self.state = "ANALYZING"
            self.session_start_time = time.time()
            self.alert_manager.set_source_name(f"Video ({self.video_filename})")
            print(f"[PIPELINE] Started AI analysis for: {self.video_filename}")
            return {"status": "success", "message": f"AI Analysis started for {self.video_filename}."}

    def stop_analysis(self) -> Dict[str, Any]:
        """
        Pauses/stops active AI processing safely.
        """
        with self.lock:
            if self.state == "ANALYZING":
                self.state = "STOPPED"
                if self.session_start_time > 0:
                    self.session_duration_sec = round(time.time() - self.session_start_time, 1)
                print("[PIPELINE] AI analysis stopped.")
                return {"status": "success", "message": "Analysis stopped."}
            return {"status": "warning", "message": "Analysis was not actively running."}

    def reset_analysis(self) -> Dict[str, Any]:
        """
        Clears the current video/session and resets the system to standby IDLE state.
        """
        with self.lock:
            self._release_capture()
            self.state = "IDLE"
            self.last_valid_frame = None
            self._reset_session_metrics()
            print("[PIPELINE] Analysis reset to IDLE.")
            return {"status": "success", "message": "Session reset. Select a video to begin."}

    def switch_to_webcam(self) -> bool:
        """
        Switches source to laptop webcam (device 0).
        """
        with self.lock:
            self._release_capture()
            self.source_type = "webcam"
            self.video_filename = "Laptop Webcam (0)"
            self._reset_session_metrics()
            self.cap = cv2.VideoCapture(self.webcam_index, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(self.webcam_index)
            if self.cap.isOpened():
                self.state = "ANALYZING"
                self.session_start_time = time.time()
                self.alert_manager.set_source_name(f"Webcam ({self.webcam_index})")
                return True
            else:
                self.state = "IDLE"
                return False

    def _reset_session_metrics(self) -> None:
        """
        Resets session summary metrics.
        """
        self.session_start_time = 0.0
        self.session_duration_sec = 0.0
        self.session_frames_processed = 0
        self.session_max_people = 0
        self.session_max_crowd_level = "LOW"
        self.session_total_alerts = 0
        self.session_restricted_alerts = 0
        self.session_crowd_alerts = 0
        self.session_movement_alerts = 0
        # Reset movement history
        self.movement_analyzer.tracks.clear()

    def _release_capture(self) -> None:
        """
        Releases the active cv2.VideoCapture object safely.
        """
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

    # -------------------------------------------------------------
    # Main Frame Processing Loop
    # -------------------------------------------------------------

    def _worker_loop(self) -> None:
        """
        Main continuous frame processing loop.
        """
        fps_timer = time.time()
        frames_in_second = 0

        while self.running:
            loop_start = time.time()
            frame = None

            with self.lock:
                current_state = self.state

            # 1. State: IDLE -> Render standby canvas
            if current_state == "IDLE":
                frame = self._generate_standby_frame()
                tracked_people = []
                crowd_metrics = self.crowd_analyzer.analyze([])
                violators = []
                has_rapid = False

            # 2. State: STOPPED -> Render paused frame
            elif current_state == "STOPPED":
                if self.last_valid_frame is not None:
                    frame = self._generate_paused_frame(self.last_valid_frame.copy())
                else:
                    frame = self._generate_standby_frame()
                tracked_people = []
                crowd_metrics = self.crowd_analyzer.analyze([])
                violators = []
                has_rapid = False

            # 3. State: COMPLETED -> Render completed summary frame
            elif current_state == "COMPLETED":
                if self.last_valid_frame is not None:
                    frame = self._generate_completed_frame(self.last_valid_frame.copy())
                else:
                    frame = self._generate_standby_frame()
                tracked_people = []
                crowd_metrics = self.crowd_analyzer.analyze([])
                violators = []
                has_rapid = False

            # 4. State: ANALYZING -> Read next frame and run AI Pipeline
            elif current_state == "ANALYZING":
                with self.lock:
                    if self.cap is not None and self.cap.isOpened():
                        ret, raw_frame = self.cap.read()
                    else:
                        ret, raw_frame = False, None

                if not ret or raw_frame is None:
                    # Video reached end!
                    with self.lock:
                        if self.source_type == "video":
                            self.state = "COMPLETED"
                            if self.session_start_time > 0:
                                self.session_duration_sec = round(time.time() - self.session_start_time, 1)
                            print(f"[PIPELINE] Video analysis completed for: {self.video_filename}")
                            if self.last_valid_frame is not None:
                                frame = self._generate_completed_frame(self.last_valid_frame.copy())
                            else:
                                frame = self._generate_standby_frame()
                        else:
                            # Webcam disconnected
                            frame = self._generate_error_frame("WEBCAM DISCONNECTED")
                    tracked_people = []
                    crowd_metrics = self.crowd_analyzer.analyze([])
                    violators = []
                    has_rapid = False
                else:
                    # Resize frame for efficient CPU inference
                    frame = cv2.resize(raw_frame, (config.FRAME_WIDTH, config.FRAME_HEIGHT))
                    self.session_frames_processed += 1

                    # AI Module 1: YOLO Person Detection and Tracking
                    tracked_people = self.detector.detect_and_track(frame)
                    people_count = len(tracked_people)

                    # Update Peak People detected in session
                    if people_count > self.session_max_people:
                        self.session_max_people = people_count

                    # AI Module 2: Crowd Density Analysis
                    crowd_metrics = self.crowd_analyzer.analyze(tracked_people)
                    if crowd_metrics.level == "HIGH" or (crowd_metrics.level == "MEDIUM" and self.session_max_crowd_level == "LOW"):
                        self.session_max_crowd_level = crowd_metrics.level

                    # AI Module 3: Restricted Area ROI Analysis
                    violators = self.restricted_detector.check_violations(tracked_people)
                    violator_ids = {p.track_id for p in violators}

                    # AI Module 4: Abnormal Movement Velocity Analysis
                    rapid_ids, has_rapid = self.movement_analyzer.update(tracked_people)

                    # AI Module 5: Centralized Alert Management
                    new_alerts = self.alert_manager.process_events(
                        crowd_metrics=crowd_metrics,
                        violators=violators,
                        rapid_person_ids=rapid_ids,
                        total_people=people_count
                    )

                    # Track session alert counts
                    for alert in new_alerts:
                        self.session_total_alerts += 1
                        atype = alert.get("alert_type", "")
                        if "Restricted" in atype:
                            self.session_restricted_alerts += 1
                        elif "Crowd" in atype:
                            self.session_crowd_alerts += 1
                        elif "Movement" in atype:
                            self.session_movement_alerts += 1

                    # Render Visual HUD overlays onto frame
                    frame = self.restricted_detector.draw_overlay(frame, violator_ids)
                    frame = self.movement_analyzer.draw_motion_trails(frame, rapid_ids)
                    frame = PersonDetector.draw_detections(frame, tracked_people, violator_ids, rapid_ids)
                    frame = self._draw_hud_telemetry(frame, crowd_metrics, len(violators), has_rapid)

                    self.last_valid_frame = frame.copy()

            # Calculate FPS
            frames_in_second += 1
            if time.time() - fps_timer >= 1.0:
                self.fps = round(frames_in_second / (time.time() - fps_timer), 1)
                frames_in_second = 0
                fps_timer = time.time()

            # Encode frame to JPEG
            if frame is not None:
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
                ret, buffer = cv2.imencode('.jpg', frame, encode_param)
                if ret:
                    self.latest_jpeg = buffer.tobytes()

            # Update Telemetry Snapshot
            has_entry = len(violators) > 0
            is_critical = (crowd_metrics.is_high_density or has_entry or has_rapid)

            session_summary = None
            if self.state == "COMPLETED" or self.state == "STOPPED":
                session_summary = {
                    "video_name": self.video_filename,
                    "frames_processed": self.session_frames_processed,
                    "duration_sec": self.session_duration_sec,
                    "max_people": self.session_max_people,
                    "max_crowd_level": self.session_max_crowd_level,
                    "total_alerts": self.session_total_alerts,
                    "restricted_alerts": self.session_restricted_alerts,
                    "crowd_alerts": self.session_crowd_alerts,
                    "movement_alerts": self.session_movement_alerts
                }

            self.latest_telemetry = {
                "people_count": len(tracked_people) if current_state == "ANALYZING" else 0,
                "crowd_level": crowd_metrics.level if current_state == "ANALYZING" else "LOW",
                "crowd_description": crowd_metrics.description if current_state == "ANALYZING" else "System Standby",
                "movement_status": ("⚠️ UNUSUAL MOVEMENT" if has_rapid else "NORMAL") if current_state == "ANALYZING" else "NORMAL",
                "restricted_status": ("⚠️ ENTRY DETECTED" if has_entry else "CLEAR") if current_state == "ANALYZING" else "CLEAR",
                "overall_system_status": ("ATTENTION REQUIRED" if is_critical else "SAFE") if current_state == "ANALYZING" else "STANDBY",
                "fps": self.fps if current_state == "ANALYZING" else 0.0,
                "active_alerts_count": len(self.alert_manager.get_live_alerts(10)),
                "source_type": self.source_type.upper(),
                "source_label": self.video_filename or "No Video Selected",
                "analysis_state": self.state,
                "selected_video_name": self.video_filename,
                "session_summary": session_summary
            }

            # Regulate frame rate
            elapsed = time.time() - loop_start
            sleep_time = max(0.005, (1.0 / config.TARGET_FPS) - elapsed)
            time.sleep(sleep_time)

    # -------------------------------------------------------------
    # HUD & Canvas Rendering Helpers
    # -------------------------------------------------------------

    def _draw_hud_telemetry(
        self,
        frame: np.ndarray,
        crowd_metrics: CrowdMetrics,
        violation_count: int,
        has_rapid: bool
    ) -> np.ndarray:
        """
        Renders sleek security-camera HUD telemetry on the top and bottom of the frame.
        """
        h, w = frame.shape[:2]

        # Top Bar
        top_bar = frame.copy()
        cv2.rectangle(top_bar, (0, 0), (w, 36), (15, 23, 42), -1)
        cv2.addWeighted(top_bar, 0.75, frame, 0.25, 0, frame)

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.40
        thick = 1

        # Recording pulse dot
        cv2.circle(frame, (16, 18), 5, (0, 0, 255), -1, lineType=cv2.LINE_AA)
        src_text = f"AI ANALYSIS [{self.video_filename[:16]}] | {time.strftime('%H:%M:%S')}"
        cv2.putText(frame, src_text, (28, 22), font, font_scale, (255, 255, 255), thick, lineType=cv2.LINE_AA)

        # People Count Badge
        count_text = f"PEOPLE: {crowd_metrics.count} | CROWD: {crowd_metrics.level}"
        cv2.putText(frame, count_text, (w - 280, 22), font, font_scale, crowd_metrics.status_color, thick, lineType=cv2.LINE_AA)

        # FPS indicator
        fps_text = f"{self.fps} FPS"
        cv2.putText(frame, fps_text, (w - 70, 22), font, font_scale, (180, 180, 180), thick, lineType=cv2.LINE_AA)

        # Bottom Bar for Critical Warnings
        if violation_count > 0 or has_rapid or crowd_metrics.is_high_density:
            bot_bar = frame.copy()
            cv2.rectangle(bot_bar, (0, h - 28), (w, h), (0, 0, 180), -1)
            cv2.addWeighted(bot_bar, 0.85, frame, 0.15, 0, frame)

            warnings = []
            if violation_count > 0:
                warnings.append("RESTRICTED AREA ENTRY")
            if has_rapid:
                warnings.append("RAPID MOVEMENT")
            if crowd_metrics.is_high_density:
                warnings.append("HIGH CROWD")

            warn_text = " [ALERT ACTIVE] " + " | ".join(warnings)
            cv2.putText(frame, warn_text, (15, h - 8), font, 0.45, (255, 255, 255), 1, lineType=cv2.LINE_AA)

        return frame

    def _generate_standby_frame(self) -> np.ndarray:
        """
        Creates a clean standby canvas before analysis begins.
        """
        frame = np.zeros((config.FRAME_HEIGHT, config.FRAME_WIDTH, 3), dtype=np.uint8)
        frame[:] = (18, 24, 38)  # Dark slate

        # Grid lines
        for y in range(0, config.FRAME_HEIGHT, 40):
            cv2.line(frame, (0, y), (config.FRAME_WIDTH, y), (28, 36, 52), 1)
        for x in range(0, config.FRAME_WIDTH, 40):
            cv2.line(frame, (x, 0), (x, config.FRAME_HEIGHT), (28, 36, 52), 1)

        font = cv2.FONT_HERSHEY_SIMPLEX
        title = "AI SMART CAMPUS SAFETY SYSTEM"
        cv2.putText(frame, title, (80, 140), font, 0.70, (6, 182, 212), 2, lineType=cv2.LINE_AA)

        if self.video_filename:
            status_text = f"Selected Video: {self.video_filename}"
            instr = "Click [ START AI ANALYSIS ] to begin processing."
            cv2.putText(frame, status_text, (80, 190), font, 0.52, (240, 240, 240), 1, lineType=cv2.LINE_AA)
            cv2.putText(frame, instr, (80, 225), font, 0.45, (16, 185, 129), 1, lineType=cv2.LINE_AA)
        else:
            instr1 = "Please choose a video file (.mp4, .avi, .mov) or use the sample video."
            instr2 = "Then click [ START AI ANALYSIS ] to run YOLO detection & tracking."
            cv2.putText(frame, instr1, (60, 190), font, 0.45, (180, 190, 205), 1, lineType=cv2.LINE_AA)
            cv2.putText(frame, instr2, (60, 220), font, 0.42, (120, 140, 160), 1, lineType=cv2.LINE_AA)

        return frame

    def _generate_paused_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Renders a PAUSED overlay on the last active frame.
        """
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (10, 15, 25), -1)
        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, "⏸️ ANALYSIS PAUSED / STOPPED", (int(w * 0.22), int(h * 0.50)), font, 0.70, (245, 158, 11), 2, lineType=cv2.LINE_AA)
        cv2.putText(frame, "Click [ START AI ANALYSIS ] to resume or [ RESET ] to clear.", (int(w * 0.15), int(h * 0.60)), font, 0.44, (200, 200, 200), 1, lineType=cv2.LINE_AA)
        return frame

    def _generate_completed_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Renders an ANALYSIS COMPLETE banner and summary card on the final frame.
        """
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (10, 15, 25), -1)
        cv2.addWeighted(overlay, 0.70, frame, 0.30, 0, frame)

        font = cv2.FONT_HERSHEY_SIMPLEX
        # Title Banner
        cv2.putText(frame, "✅ ANALYSIS COMPLETE", (int(w * 0.28), 65), font, 0.75, (16, 185, 129), 2, lineType=cv2.LINE_AA)

        # Summary Metrics Box
        box_x1, box_y1, box_x2, box_y2 = 80, 95, w - 80, h - 45
        cv2.rectangle(frame, (box_x1, box_y1), (box_x2, box_y2), (30, 42, 60), -1)
        cv2.rectangle(frame, (box_x1, box_y1), (box_x2, box_y2), (16, 185, 129), 1)

        f_scale = 0.44
        thick = 1
        cv2.putText(frame, f"Video Source: {self.video_filename}", (box_x1 + 20, box_y1 + 30), font, f_scale, (255, 255, 255), thick, lineType=cv2.LINE_AA)
        cv2.putText(frame, f"Frames Processed: {self.session_frames_processed} ({self.session_duration_sec}s)", (box_x1 + 20, box_y1 + 55), font, f_scale, (200, 210, 225), thick, lineType=cv2.LINE_AA)
        cv2.putText(frame, f"Peak People Count: {self.session_max_people}", (box_x1 + 20, box_y1 + 80), font, f_scale, (6, 182, 212), thick, lineType=cv2.LINE_AA)
        cv2.putText(frame, f"Peak Crowd Level: {self.session_max_crowd_level}", (box_x1 + 20, box_y1 + 105), font, f_scale, (245, 158, 11), thick, lineType=cv2.LINE_AA)
        cv2.putText(frame, f"Total Safety Alerts: {self.session_total_alerts}", (box_x1 + 20, box_y1 + 130), font, f_scale, (239, 68, 68), thick, lineType=cv2.LINE_AA)
        cv2.putText(frame, f"  - Restricted Area: {self.session_restricted_alerts} | Crowd: {self.session_crowd_alerts} | Movement: {self.session_movement_alerts}", (box_x1 + 20, box_y1 + 155), font, 0.38, (170, 180, 195), thick, lineType=cv2.LINE_AA)

        cv2.putText(frame, "Click [ RESET ] to analyze another video.", (int(w * 0.25), h - 20), font, 0.44, (200, 200, 200), 1, lineType=cv2.LINE_AA)
        return frame

    def _generate_error_frame(self, message: str = "VIDEO SOURCE UNAVAILABLE") -> np.ndarray:
        """
        Creates an error canvas.
        """
        frame = np.zeros((config.FRAME_HEIGHT, config.FRAME_WIDTH, 3), dtype=np.uint8)
        frame[:] = (20, 25, 35)
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, message, (60, 160), font, 0.65, (0, 100, 255), 2, lineType=cv2.LINE_AA)
        cv2.putText(frame, "Select a video or click RESET to reconfigure.", (60, 200), font, 0.45, (160, 170, 180), 1, lineType=cv2.LINE_AA)
        return frame

    def get_jpeg_frame(self) -> Optional[bytes]:
        """
        Returns the most recently encoded JPEG frame for MJPEG streaming.
        """
        return self.latest_jpeg

    def get_telemetry(self) -> Dict[str, Any]:
        """
        Returns the latest real-time telemetry dictionary.
        """
        with self.lock:
            telemetry = dict(self.latest_telemetry)
            telemetry["analysis_state"] = self.state
            return telemetry


def generate_mjpeg_stream(pipeline: VideoStreamPipeline) -> Generator[bytes, None, None]:
    """
    Generator function yielding multipart/x-mixed-replace MJPEG byte frames.
    """
    while True:
        frame_bytes = pipeline.get_jpeg_frame()
        if frame_bytes is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.035)  # ~28 fps
