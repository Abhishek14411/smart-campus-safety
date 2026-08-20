"""
AI Smart Campus Safety & Monitoring System - Flask Web Application
==================================================================
Serves the web dashboard, MJPEG live video stream, and RESTful APIs
for video uploads, analysis playback controls (START, STOP, RESET),
real-time telemetry, historical alerts, and live configuration.
"""

import os
import sys
from pathlib import Path
from flask import Flask, render_template, Response, jsonify, request
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

import config
from database import db
from detection.video_stream import VideoStreamPipeline, generate_mjpeg_stream
import generate_demo_video

# Initialize Flask App
app = Flask(__name__)
app.config['SECRET_KEY'] = 'smart-campus-safety-secret-2026'
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

# Ensure database and essential directories exist
db.init_db()
config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
config.VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

# Ensure sample demo video exists
if not Path(config.DEFAULT_VIDEO_PATH).exists():
    try:
        generate_demo_video.create_demo_video(config.DEFAULT_VIDEO_PATH)
    except Exception as e:
        print(f"[INIT WARNING] Could not auto-generate demo video: {e}")

# Initialize computer vision processing pipeline
pipeline = VideoStreamPipeline()


def allowed_file(filename: str) -> bool:
    """Checks if the uploaded file has a supported video extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


@app.errorhandler(413)
@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    """Graceful JSON response when uploaded video exceeds maximum allowed size."""
    return jsonify({
        "status": "error",
        "message": f"Video file is too large. Maximum allowed size is {config.MAX_UPLOAD_SIZE_MB}MB."
    }), 413


@app.route('/')
def index():
    """Main real-time campus monitoring dashboard."""
    return render_template('dashboard.html')


@app.route('/alerts')
def alert_history_page():
    """Historical alerts audit trail and incident log page."""
    return render_template('alerts.html')


@app.route('/video_feed')
def video_feed():
    """MJPEG streaming endpoint for the live processed video with HUD overlays."""
    return Response(
        generate_mjpeg_stream(pipeline),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


# -------------------------------------------------------------
# Video Upload & Playback Control APIs
# -------------------------------------------------------------

@app.route('/api/video/upload', methods=['POST'])
def api_upload_video():
    """
    Handles video file uploads (.mp4, .avi, .mov) and sets the uploaded video as the active input.
    """
    if 'video' not in request.files:
        return jsonify({"status": "error", "message": "No video file provided in upload request."}), 400

    file = request.files['video']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "status": "error",
            "message": "Unsupported video format. Please select an MP4, AVI or MOV file."
        }), 400

    try:
        filename = secure_filename(file.filename)
        # Prevent collision by prefixing timestamp
        saved_filename = f"upload_{int(os.path.getmtime(config.DATABASE_PATH) if os.path.exists(config.DATABASE_PATH) else 0)}_{filename}"
        save_path = config.UPLOADS_DIR / saved_filename
        file.save(str(save_path))

        # Set as active video source in IDLE state (ready to start)
        pipeline.set_video_source(str(save_path), filename)

        return jsonify({
            "status": "success",
            "message": f"Video '{filename}' uploaded successfully.",
            "filename": filename,
            "path": str(save_path)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to save video: {str(e)}"}), 500


@app.route('/api/video/sample', methods=['POST'])
def api_select_sample():
    """
    Quick-selects the pre-packaged campus demo video (videos/campus.mp4).
    """
    if not Path(config.DEFAULT_VIDEO_PATH).exists():
        generate_demo_video.create_demo_video(config.DEFAULT_VIDEO_PATH)

    pipeline.set_video_source(config.DEFAULT_VIDEO_PATH, "campus.mp4")
    return jsonify({
        "status": "success",
        "message": "Sample campus video loaded.",
        "filename": "campus.mp4"
    })


@app.route('/api/video/start', methods=['POST'])
def api_start_analysis():
    """
    Starts AI analysis on the currently selected video file from frame 0.
    """
    result = pipeline.start_analysis()
    return jsonify(result), (200 if result["status"] == "success" else 400)


@app.route('/api/video/stop', methods=['POST'])
def api_stop_analysis():
    """
    Pauses / stops active video analysis safely.
    """
    result = pipeline.stop_analysis()
    return jsonify(result)


@app.route('/api/video/reset', methods=['POST'])
def api_reset_analysis():
    """
    Resets the session state, releases OpenCV VideoCapture, and resets counters.
    """
    result = pipeline.reset_analysis()
    return jsonify(result)


@app.route('/api/source/change', methods=['POST'])
def api_change_source():
    """
    Switches between Video File mode and Laptop Webcam.
    """
    data = request.get_json(silent=True) or {}
    source_type = data.get('source_type', 'video').lower()

    if source_type == 'webcam':
        success = pipeline.switch_to_webcam()
        if success:
            return jsonify({"status": "success", "message": "Switched to Laptop Webcam.", "source_type": "webcam"})
        else:
            return jsonify({"status": "warning", "message": "Webcam could not be opened. Switched to Standby.", "source_type": "webcam"})
    else:
        pipeline.reset_analysis()
        return jsonify({"status": "success", "message": "Switched to Video Mode.", "source_type": "video"})


# -------------------------------------------------------------
# Telemetry, Alerts & Configuration APIs
# -------------------------------------------------------------

@app.route('/api/stats', methods=['GET'])
def api_stats():
    """
    Returns real-time telemetry metrics and session status for the dashboard.
    """
    telemetry = pipeline.get_telemetry()
    db_stats = db.get_alert_statistics()
    return jsonify({
        "status": "success",
        "telemetry": telemetry,
        "db_stats": db_stats
    })


@app.route('/api/alerts/recent', methods=['GET'])
def api_recent_alerts():
    """
    Returns the most recent alerts for the live alert feed widget.
    """
    limit = request.args.get('limit', default=10, type=int)
    alerts = pipeline.alert_manager.get_live_alerts(limit=limit)
    return jsonify({
        "status": "success",
        "count": len(alerts),
        "alerts": alerts
    })


@app.route('/api/alerts/history', methods=['GET'])
def api_alert_history():
    """
    Returns paginated historical alerts with optional alert_type filter.
    """
    limit = request.args.get('limit', default=50, type=int)
    offset = request.args.get('offset', default=0, type=int)
    alert_type = request.args.get('type', default=None, type=str)

    alerts = db.get_alert_history(limit=limit, offset=offset, alert_type_filter=alert_type)
    stats = db.get_alert_statistics()

    return jsonify({
        "status": "success",
        "count": len(alerts),
        "total": stats["total_alerts"],
        "alerts": alerts
    })


@app.route('/api/alerts/clear', methods=['POST'])
def api_clear_alerts():
    """
    Safely clears the alert history table upon user confirmation.
    """
    success = db.clear_alert_history()
    if success:
        pipeline.alert_manager.recent_alerts_cache.clear()
        return jsonify({"status": "success", "message": "Alert history cleared successfully."})
    else:
        return jsonify({"status": "error", "message": "Failed to clear alert history from database."}), 500


@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """
    GET: Returns current system configuration thresholds.
    POST: Updates configuration thresholds dynamically at runtime.
    """
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}

        # 1. Update Crowd Thresholds
        if 'crowd_low_max' in data and 'crowd_medium_max' in data:
            try:
                low_m = int(data['crowd_low_max'])
                med_m = int(data['crowd_medium_max'])
                pipeline.crowd_analyzer.update_thresholds(low_m, med_m)
                config.CROWD_LOW_MAX = low_m
                config.CROWD_MEDIUM_MAX = med_m
            except Exception as e:
                return jsonify({"status": "error", "message": f"Invalid crowd thresholds: {e}"}), 400

        # 2. Update Restricted Area Coordinates
        if 'restricted_coords' in data:
            try:
                coords = data['restricted_coords']
                if isinstance(coords, list) and len(coords) == 4:
                    x1, y1, x2, y2 = [int(v) for v in coords]
                    pipeline.restricted_detector.set_coordinates(x1, y1, x2, y2)
                    config.RESTRICTED_AREA_COORDS = [x1, y1, x2, y2]
            except Exception as e:
                return jsonify({"status": "error", "message": f"Invalid restricted coordinates: {e}"}), 400

        # 3. Update Movement Anomaly Thresholds
        if 'rapid_movement_threshold' in data or 'consecutive_frames_req' in data:
            try:
                speed_t = float(data.get('rapid_movement_threshold', pipeline.movement_analyzer.speed_threshold))
                frames_req = int(data.get('consecutive_frames_req', pipeline.movement_analyzer.consecutive_frames_req))
                pipeline.movement_analyzer.update_thresholds(speed_t, frames_req)
                config.RAPID_MOVEMENT_THRESHOLD = speed_t
                config.CONSECUTIVE_FRAMES_REQUIRED = frames_req
            except Exception as e:
                return jsonify({"status": "error", "message": f"Invalid movement thresholds: {e}"}), 400

        return jsonify({"status": "success", "message": "Configuration updated successfully."})

    # GET configuration
    return jsonify({
        "status": "success",
        "config": {
            "crowd_low_max": pipeline.crowd_analyzer.low_max,
            "crowd_medium_max": pipeline.crowd_analyzer.medium_max,
            "restricted_coords": pipeline.restricted_detector.coords,
            "restricted_name": pipeline.restricted_detector.name,
            "rapid_movement_threshold": pipeline.movement_analyzer.speed_threshold,
            "consecutive_frames_req": pipeline.movement_analyzer.consecutive_frames_req,
            "cooldown_crowd": config.ALERT_COOLDOWN_CROWD,
            "cooldown_restricted": config.ALERT_COOLDOWN_RESTRICTED,
            "cooldown_movement": config.ALERT_COOLDOWN_MOVEMENT,
            "source_type": pipeline.source_type,
            "yolo_model": config.YOLO_MODEL_NAME
        }
    })


def main():
    """Application entrypoint."""
    print("=" * 70)
    print(" AI SMART CAMPUS SAFETY & MONITORING SYSTEM")
    print("=" * 70)
    print(f" * Model: {config.YOLO_MODEL_NAME}")
    print(f" * Database: {config.DATABASE_PATH}")
    print(f" * Uploads Dir: {config.UPLOADS_DIR}")
    print(f" * Web Dashboard: http://{config.SERVER_HOST}:{config.SERVER_PORT}")
    print("=" * 70)

    # Start video capture pipeline thread
    pipeline.start()

    try:
        app.run(
            host=config.SERVER_HOST,
            port=config.SERVER_PORT,
            debug=config.DEBUG_MODE,
            threaded=True,
            use_reloader=False
        )
    finally:
        pipeline.stop()


if __name__ == '__main__':
    main()
