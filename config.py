"""
AI Smart Campus Safety & Monitoring System - Configuration
==========================================================
All system thresholds, video source configurations, model settings,
and alert parameters are centralized here for easy tuning.
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
VIDEOS_DIR = BASE_DIR / "videos"
UPLOADS_DIR = BASE_DIR / "uploads"
MODELS_DIR = BASE_DIR / "models"

# Ensure essential directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Database configuration
DATABASE_PATH = str(DATA_DIR / "campus_safety.db")

# Upload Configuration
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov'}
MAX_UPLOAD_SIZE_MB = 100
MAX_CONTENT_LENGTH = MAX_UPLOAD_SIZE_MB * 1024 * 1024  # 100 MB max file size

# Model Configuration
# Uses lightweight YOLOv8 nano model optimized for laptop CPU performance
YOLO_MODEL_NAME = "yolov8n.pt"
MODEL_CONFIDENCE_THRESHOLD = 0.40  # Minimum detection confidence (0.0 - 1.0)
IOU_THRESHOLD = 0.45               # NMS IoU threshold

# Video Processing & Display Settings
FRAME_WIDTH = 640                  # Processing width in pixels
FRAME_HEIGHT = 360                 # Processing height in pixels
TARGET_FPS = 25                    # Target processing frames per second
PROCESS_EVERY_N_FRAMES = 1         # Frame skipping factor (1 = process every frame)

# Video Sources
# 'video': Pre-recorded MP4 video file
# 'webcam': Laptop / USB webcam (Device Index 0)
DEFAULT_VIDEO_SOURCE_TYPE = "video"
DEFAULT_VIDEO_PATH = str(VIDEOS_DIR / "campus.mp4")
WEBCAM_INDEX = 0

# Module 2: Crowd Counting & Density Levels
# Configurable thresholds for crowd classification
# LOW: 0 to CROWD_LOW_MAX
# MEDIUM: (CROWD_LOW_MAX + 1) to CROWD_MEDIUM_MAX
# HIGH: (CROWD_MEDIUM_MAX + 1) and above
CROWD_LOW_MAX = 5
CROWD_MEDIUM_MAX = 12
# Any count > CROWD_MEDIUM_MAX is classified as HIGH

# Module 3: Restricted Area (ROI) Configuration
# Rectangle coordinates in format: [x1, y1, x2, y2]
# Default is set to a top-right corner zone of the 640x360 frame
RESTRICTED_AREA_NAME = "Server Room / Restricted Gate"
RESTRICTED_AREA_COORDS = [420, 40, 620, 240]  # [x1, y1, x2, y2]

# Module 4: Abnormal Movement Detection Heuristic
# Pixel displacement per frame threshold to detect unusually rapid movement (running/sprinting)
RAPID_MOVEMENT_THRESHOLD = 28.0    # Pixels per frame displacement
CONSECUTIVE_FRAMES_REQUIRED = 3     # Must persist for N consecutive frames before alert
MAX_TRACK_HISTORY = 30              # Max position history kept per tracked person

# Module 5: Alert Cooldowns (Debounce Timers in Seconds)
# Prevents creating duplicate alerts every second for continuous conditions
ALERT_COOLDOWN_CROWD = 20.0         # Seconds between High Crowd alerts
ALERT_COOLDOWN_RESTRICTED = 15.0    # Seconds per Person ID for Restricted Area alerts
ALERT_COOLDOWN_MOVEMENT = 15.0      # Seconds per Person ID for Rapid Movement alerts

# Web Server Settings
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000
DEBUG_MODE = False
