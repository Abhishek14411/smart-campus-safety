"""
Test 9 & 10: Flask REST APIs & Video Upload/Control Error Handling
Verifies Flask endpoints for video uploads, format validation, analysis controls
(START, STOP, RESET), real-time stats, alert queries, and config updates.
"""

import io
import json
import pytest
from app import app
from database import db
import config


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        db.init_db()
        yield client


def test_index_and_alerts_routes(client):
    """Verify HTML pages load with 200 OK."""
    res_dash = client.get('/')
    assert res_dash.status_code == 200
    assert b"AI Smart Campus Safety" in res_dash.data
    assert b"Start Analysis" in res_dash.data

    res_hist = client.get('/alerts')
    assert res_hist.status_code == 200
    assert b"Historical Safety Alerts" in res_hist.data


def test_api_stats(client):
    """Verify /api/stats returns structured telemetry JSON."""
    res = client.get('/api/stats')
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "telemetry" in data
    assert "people_count" in data["telemetry"]
    assert "analysis_state" in data["telemetry"]


def test_api_video_upload_valid_and_invalid(client):
    """Verify video upload validation for allowed vs disallowed extensions."""
    # 1. Invalid Extension (.txt)
    data_invalid = {
        'video': (io.BytesIO(b"fake data"), 'test_document.txt')
    }
    res_inv = client.post('/api/video/upload', data=data_invalid, content_type='multipart/form-data')
    assert res_inv.status_code == 400
    assert "Unsupported video format" in res_inv.get_json()["message"]

    # 2. Valid Extension (.mp4)
    data_valid = {
        'video': (io.BytesIO(b"fake mp4 video bytes"), 'campus_test.mp4')
    }
    res_val = client.post('/api/video/upload', data=data_valid, content_type='multipart/form-data')
    assert res_val.status_code == 200
    assert res_val.get_json()["status"] == "success"
    assert res_val.get_json()["filename"] == "campus_test.mp4"


def test_api_video_controls_lifecycle(client):
    """Verify Start -> Stop -> Reset control lifecycle."""
    # Load sample video first
    res_sample = client.post('/api/video/sample')
    assert res_sample.status_code == 200

    # Start analysis
    res_start = client.post('/api/video/start')
    assert res_start.status_code == 200
    assert res_start.get_json()["status"] == "success"

    # Stop analysis
    res_stop = client.post('/api/video/stop')
    assert res_stop.status_code == 200

    # Reset analysis
    res_reset = client.post('/api/video/reset')
    assert res_reset.status_code == 200
    assert res_reset.get_json()["status"] == "success"


def test_api_config_get_and_post(client):
    """Verify /api/config GET and dynamic POST update."""
    res_get = client.get('/api/config')
    assert res_get.status_code == 200
    cfg = res_get.get_json()["config"]
    assert "crowd_low_max" in cfg
    assert "restricted_coords" in cfg

    payload = {
        "crowd_low_max": 8,
        "crowd_medium_max": 18,
        "restricted_coords": [100, 100, 300, 300],
        "rapid_movement_threshold": 32.5,
        "consecutive_frames_req": 4
    }
    res_post = client.post('/api/config', data=json.dumps(payload), content_type='application/json')
    assert res_post.status_code == 200
    assert res_post.get_json()["status"] == "success"


def test_api_alerts_history_and_clear(client):
    """Verify /api/alerts/history and /api/alerts/clear."""
    db.create_alert("Restricted Area Entry", person_id=99, people_count=2, severity="HIGH")

    res = client.get('/api/alerts/history')
    assert res.status_code == 200
    data = res.get_json()
    assert data["count"] >= 1

    res_clear = client.post('/api/alerts/clear')
    assert res_clear.status_code == 200
    assert res_clear.get_json()["status"] == "success"

    res_after = client.get('/api/alerts/history')
    assert res_after.get_json()["count"] == 0
