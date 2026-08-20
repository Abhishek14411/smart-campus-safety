"""
Live System Health, Video Upload & AI Analysis Verification Script
"""
import urllib.request
import urllib.parse
import json
import time

def verify_live():
    base_url = "http://127.0.0.1:5000"
    print(f"[*] Testing Live Video Control Endpoints at {base_url}...")

    # 1. Main Dashboard Page
    with urllib.request.urlopen(f"{base_url}/") as res:
        assert res.status == 200
        html = res.read().decode('utf-8')
        assert "AI Smart Campus Safety" in html
        assert "Start Analysis" in html
        print("  [OK] GET / -> HTTP 200 (Dashboard with Video Upload & Controls)")

    # 2. Select Sample Campus Video
    req = urllib.request.Request(f"{base_url}/api/video/sample", data=b"{}", headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as res:
        assert res.status == 200
        data = json.loads(res.read().decode('utf-8'))
        assert data["status"] == "success"
        print("  [OK] POST /api/video/sample -> Selected:", data["filename"])

    # 3. Start Analysis
    req = urllib.request.Request(f"{base_url}/api/video/start", data=b"{}", headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as res:
        assert res.status == 200
        data = json.loads(res.read().decode('utf-8'))
        assert data["status"] == "success"
        print("  [OK] POST /api/video/start ->", data["message"])

    # Wait a few frames for AI detection to run
    print("  [*] Running AI inference on campus video (waiting 2 seconds)...")
    time.sleep(2.0)

    # 4. Check Telemetry Stats during active analysis
    with urllib.request.urlopen(f"{base_url}/api/stats") as res:
        assert res.status == 200
        data = json.loads(res.read().decode('utf-8'))
        t = data["telemetry"]
        print("  [OK] Active Analysis Telemetry:")
        print(f"       State: {t['analysis_state']} | Video: {t['selected_video_name']}")
        print(f"       People Detected: {t['people_count']} | Crowd: {t['crowd_level']}")
        print(f"       Restricted Area: {t['restricted_status']} | Movement: {t['movement_status']}")
        print(f"       Processing FPS: {t['fps']}")

    # 5. Stop Analysis
    req = urllib.request.Request(f"{base_url}/api/video/stop", data=b"{}", headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as res:
        assert res.status == 200
        data = json.loads(res.read().decode('utf-8'))
        print("  [OK] POST /api/video/stop ->", data["message"])

    # 6. Reset Analysis
    req = urllib.request.Request(f"{base_url}/api/video/reset", data=b"{}", headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as res:
        assert res.status == 200
        data = json.loads(res.read().decode('utf-8'))
        print("  [OK] POST /api/video/reset ->", data["message"])

    time.sleep(0.5)

    # 7. Check Telemetry after Reset
    with urllib.request.urlopen(f"{base_url}/api/stats") as res:
        assert res.status == 200
        data = json.loads(res.read().decode('utf-8'))
        state = data["telemetry"]["analysis_state"]
        print(f"  [OK] Telemetry state after reset: {state}")
        assert state in ["IDLE", "STANDBY"]
        print("  [OK] System returned to STANDBY/IDLE state.")

    print("\n[SUCCESS] All live Video Upload & Playback Control workflows verified successfully!")

if __name__ == "__main__":
    verify_live()
