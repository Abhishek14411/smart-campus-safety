/**
 * AI Smart Campus Safety & Monitoring System
 * Academic B.Tech Project - Live Dashboard Controller
 */

let pollingInterval = null;
let summaryModalShown = false;

document.addEventListener('DOMContentLoaded', () => {
  console.log('[DASHBOARD] Initializing telemetry polling...');
  fetchStats();
  fetchRecentAlerts();
  
  // High-frequency telemetry polling every 800ms
  pollingInterval = setInterval(() => {
    fetchStats();
    fetchRecentAlerts();
  }, 800);
});

/**
 * Fetches real-time telemetry metrics and updates UI cards, meters, and buttons.
 */
async function fetchStats() {
  try {
    const res = await fetch('/api/stats');
    if (!res.ok) return;
    const data = await res.json();
    if (data.status !== 'success') return;

    const t = data.telemetry;
    
    // 1. People Detected Card
    const elPeople = document.getElementById('val-people-count');
    if (elPeople) elPeople.textContent = t.people_count;

    // 2. Crowd Level Card
    const elCrowd = document.getElementById('val-crowd-level');
    const elCrowdDesc = document.getElementById('sub-crowd-desc');
    if (elCrowd) {
      elCrowd.textContent = t.crowd_level;
      if (t.crowd_level === 'HIGH') {
        elCrowd.style.color = 'var(--color-red)';
      } else if (t.crowd_level === 'MEDIUM') {
        elCrowd.style.color = 'var(--color-orange)';
      } else {
        elCrowd.style.color = 'var(--color-green)';
      }
    }
    if (elCrowdDesc) elCrowdDesc.textContent = t.crowd_description || 'Campus occupancy level';

    // 3. Restricted Area Card
    const elRestricted = document.getElementById('val-restricted-display');
    if (elRestricted) {
      elRestricted.textContent = t.restricted_status;
      if (t.restricted_status.includes('ENTRY')) {
        elRestricted.style.color = 'var(--color-red)';
      } else {
        elRestricted.style.color = 'var(--color-green)';
      }
    }

    // 4. Movement Status Card
    const elMovement = document.getElementById('val-movement-display');
    if (elMovement) {
      elMovement.textContent = t.movement_status;
      if (t.movement_status.includes('UNUSUAL')) {
        elMovement.style.color = 'var(--color-red)';
      } else {
        elMovement.style.color = 'var(--color-green)';
      }
    }

    // Legacy/hidden elements for full compatibility
    const elAlerts = document.getElementById('val-active-alerts');
    if (elAlerts) elAlerts.textContent = t.active_alerts_count;

    const elSys = document.getElementById('val-system-status');
    if (elSys) elSys.textContent = t.overall_system_status;

    // Meta Bar & System Info Updates
    const elFps = document.getElementById('meta-fps');
    if (elFps) elFps.textContent = `${t.fps.toFixed(1)} FPS`;

    const elInfoFps = document.getElementById('info-fps');
    if (elInfoFps) elInfoFps.textContent = `${t.fps.toFixed(1)} FPS`;

    const elSource = document.getElementById('meta-source-label');
    if (elSource) elSource.textContent = `Source: ${t.source_label}`;

    const elInfoSource = document.getElementById('info-source');
    if (elInfoSource) elInfoSource.textContent = t.source_label;

    const elInfoStatus = document.getElementById('info-status');
    if (elInfoStatus) elInfoStatus.textContent = t.analysis_state;

    const elSelectedLabel = document.getElementById('label-selected-video');
    if (elSelectedLabel && t.selected_video_name) {
      elSelectedLabel.textContent = t.selected_video_name;
    }

    // State Badge & Button Sync
    const elStateBadge = document.getElementById('analysis-state-badge');
    const btnStart = document.getElementById('btn-start-analysis');
    const btnStop = document.getElementById('btn-stop-analysis');

    if (t.analysis_state === 'ANALYZING') {
      if (elStateBadge) {
        elStateBadge.textContent = 'ANALYZING';
        elStateBadge.className = 'safety-badge badge-green';
      }
      if (btnStart) btnStart.disabled = true;
      if (btnStop) btnStop.disabled = false;
      summaryModalShown = false;
    } else if (t.analysis_state === 'STOPPED') {
      if (elStateBadge) {
        elStateBadge.textContent = 'PAUSED';
        elStateBadge.className = 'safety-badge badge-yellow';
      }
      if (btnStart) btnStart.disabled = false;
      if (btnStop) btnStop.disabled = true;
    } else if (t.analysis_state === 'COMPLETED') {
      if (elStateBadge) {
        elStateBadge.textContent = 'COMPLETED';
        elStateBadge.className = 'safety-badge badge-green';
      }
      if (btnStart) btnStart.disabled = false;
      if (btnStop) btnStop.disabled = true;

      // Trigger completion summary modal once
      if (t.session_summary && !summaryModalShown) {
        summaryModalShown = true;
        showCompleteModal(t.session_summary);
      }
    } else {
      // IDLE
      if (elStateBadge) {
        elStateBadge.textContent = 'STANDBY';
        elStateBadge.className = 'safety-badge badge-yellow';
      }
      if (btnStart) btnStart.disabled = false;
      if (btnStop) btnStop.disabled = true;
    }

    // Safety Status Sub-panel Badges
    updateSafetyBadge('badge-crowd-status', t.crowd_level, t.crowd_level === 'HIGH' ? 'red' : (t.crowd_level === 'MEDIUM' ? 'yellow' : 'green'));
    updateSafetyBadge('badge-movement-status', t.movement_status, t.movement_status.includes('UNUSUAL') ? 'red' : 'green');
    updateSafetyBadge('badge-restricted-status', t.restricted_status, t.restricted_status.includes('ENTRY') ? 'red' : 'green');

  } catch (err) {
    console.warn('[TELEMETRY] Polling error:', err);
  }
}

/**
 * Helper to update badge text and style dynamically.
 */
function updateSafetyBadge(elementId, text, colorClass) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.textContent = text;
  el.className = `safety-badge badge-${colorClass}`;
}

/**
 * Fetches recent alerts and renders them in the clean sidebar feed.
 */
async function fetchRecentAlerts() {
  try {
    const res = await fetch('/api/alerts/recent?limit=10');
    if (!res.ok) return;
    const data = await res.json();
    if (data.status !== 'success') return;

    const container = document.getElementById('alerts-feed-container');
    const countLabel = document.getElementById('live-alert-count-label');
    if (!container) return;

    const alerts = data.alerts || [];
    if (countLabel) countLabel.textContent = `${alerts.length} Events`;

    if (alerts.length === 0) {
      container.innerHTML = `
        <div class="no-alerts" id="no-alerts-msg">
          No active safety alerts.<br>Campus perimeter is clear.
        </div>
      `;
      return;
    }

    // Render clean alert items
    let html = '';
    alerts.forEach(alert => {
      const pIdText = alert.person_id ? `Person #${alert.person_id}` : 'General';
      let sevClass = 'badge-yellow';
      if (alert.severity === 'CRITICAL' || alert.severity === 'HIGH') {
        sevClass = 'badge-red';
      } else if (alert.severity === 'LOW') {
        sevClass = 'badge-blue';
      }

      html += `
        <div class="alert-item severity-${alert.severity}">
          <div class="alert-top">
            <span class="alert-type">${escapeHtml(alert.alert_type)}</span>
            <span class="alert-time">${escapeHtml(alert.timestamp.split(' ')[1] || alert.timestamp)}</span>
          </div>
          <div class="alert-body">${escapeHtml(alert.details || alert.alert_type)}</div>
          <div class="alert-footer">
            <span class="alert-id-tag">${pIdText}</span>
            <span class="safety-badge ${sevClass}">${alert.severity}</span>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;

  } catch (err) {
    console.warn('[ALERTS] Fetch error:', err);
  }
}

// -------------------------------------------------------------
// Video File Upload & Playback Actions
// -------------------------------------------------------------

/**
 * Handles uploading a video file via the hidden file input.
 */
async function handleFileUpload(input) {
  if (!input.files || input.files.length === 0) return;
  const file = input.files[0];

  // Validate extension
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['mp4', 'avi', 'mov'].includes(ext)) {
    alert('Unsupported video format. Please select an MP4, AVI or MOV file.');
    input.value = '';
    return;
  }

  // Validate size (100MB limit)
  if (file.size > 100 * 1024 * 1024) {
    alert('Video is too large. Please select a video under 100MB.');
    input.value = '';
    return;
  }

  const formData = new FormData();
  formData.append('video', file);

  const label = document.getElementById('label-selected-video');
  if (label) label.textContent = `Uploading ${file.name}...`;

  try {
    const res = await fetch('/api/video/upload', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (res.ok && data.status === 'success') {
      if (label) label.textContent = data.filename;
      console.log('[UPLOAD SUCCESS]', data.message);
      refreshVideoStream();
    } else {
      alert(data.message || 'Failed to upload video.');
      if (label) label.textContent = 'Upload Failed';
    }
  } catch (err) {
    console.error('[UPLOAD ERROR]', err);
    alert('An error occurred during upload.');
    if (label) label.textContent = 'Upload Error';
  }
}

/**
 * Loads the default campus sample video.
 */
async function loadSampleVideo() {
  try {
    const res = await fetch('/api/video/sample', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'success') {
      const label = document.getElementById('label-selected-video');
      if (label) label.textContent = 'campus.mp4';
      console.log('[SAMPLE VIDEO LOADED]');
      refreshVideoStream();
    }
  } catch (e) {
    console.error('[SAMPLE LOAD ERROR]', e);
  }
}

/**
 * Starts AI analysis.
 */
async function startAnalysis() {
  try {
    const res = await fetch('/api/video/start', { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.status === 'success') {
      console.log('[ANALYSIS STARTED]', data.message);
      refreshVideoStream();
      fetchStats();
    } else {
      alert(data.message || 'Failed to start analysis.');
    }
  } catch (err) {
    console.error('[START ERROR]', err);
  }
}

/**
 * Stops/pauses AI analysis safely.
 */
async function stopAnalysis() {
  try {
    const res = await fetch('/api/video/stop', { method: 'POST' });
    const data = await res.json();
    console.log('[ANALYSIS STOPPED]', data.message);
    fetchStats();
  } catch (err) {
    console.error('[STOP ERROR]', err);
  }
}

/**
 * Resets the session and clears telemetry.
 */
async function resetAnalysis() {
  try {
    const res = await fetch('/api/video/reset', { method: 'POST' });
    const data = await res.json();
    console.log('[ANALYSIS RESET]', data.message);
    refreshVideoStream();
    fetchStats();
  } catch (err) {
    console.error('[RESET ERROR]', err);
  }
}

function refreshVideoStream() {
  const img = document.getElementById('live-stream-img');
  if (img) {
    img.src = `/video_feed?t=${Date.now()}`;
  }
}

// -------------------------------------------------------------
// Summary Modal Handlers
// -------------------------------------------------------------

function showCompleteModal(summary) {
  const modal = document.getElementById('analysis-complete-modal');
  if (!modal || !summary) return;

  document.getElementById('summary-video-name').textContent = summary.video_name || 'campus.mp4';
  document.getElementById('summary-duration').textContent = `${summary.frames_processed} frames (${summary.duration_sec}s)`;
  document.getElementById('summary-max-people').textContent = summary.max_people;
  document.getElementById('summary-max-crowd').textContent = summary.max_crowd_level;
  document.getElementById('summary-total-alerts').textContent = `${summary.total_alerts}`;
  document.getElementById('summary-restricted-alerts').textContent = summary.restricted_alerts;
  document.getElementById('summary-crowd-alerts').textContent = summary.crowd_alerts;
  document.getElementById('summary-movement-alerts').textContent = summary.movement_alerts;

  modal.classList.add('open');
}

function closeCompleteModal() {
  const modal = document.getElementById('analysis-complete-modal');
  if (modal) modal.classList.remove('open');
}

// -------------------------------------------------------------
// Settings Configuration Modal
// -------------------------------------------------------------

async function openSettingsModal() {
  const modal = document.getElementById('settings-modal');
  if (!modal) return;
  
  try {
    const res = await fetch('/api/config');
    const data = await res.json();
    if (data.status === 'success') {
      const cfg = data.config;
      document.getElementById('cfg-crowd-low').value = cfg.crowd_low_max;
      document.getElementById('cfg-crowd-med').value = cfg.crowd_medium_max;
      if (cfg.restricted_coords && cfg.restricted_coords.length === 4) {
        document.getElementById('cfg-roi-x1').value = cfg.restricted_coords[0];
        document.getElementById('cfg-roi-y1').value = cfg.restricted_coords[1];
        document.getElementById('cfg-roi-x2').value = cfg.restricted_coords[2];
        document.getElementById('cfg-roi-y2').value = cfg.restricted_coords[3];
      }
      document.getElementById('cfg-speed').value = cfg.rapid_movement_threshold;
      document.getElementById('cfg-frames').value = cfg.consecutive_frames_req;
    }
  } catch (e) {
    console.warn('[CONFIG] Failed to load current configuration:', e);
  }
  
  modal.classList.add('open');
}

function closeSettingsModal() {
  const modal = document.getElementById('settings-modal');
  if (modal) modal.classList.remove('open');
}

async function saveSettings(event) {
  event.preventDefault();
  
  const payload = {
    crowd_low_max: parseInt(document.getElementById('cfg-crowd-low').value),
    crowd_medium_max: parseInt(document.getElementById('cfg-crowd-med').value),
    restricted_coords: [
      parseInt(document.getElementById('cfg-roi-x1').value),
      parseInt(document.getElementById('cfg-roi-y1').value),
      parseInt(document.getElementById('cfg-roi-x2').value),
      parseInt(document.getElementById('cfg-roi-y2').value)
    ],
    rapid_movement_threshold: parseFloat(document.getElementById('cfg-speed').value),
    consecutive_frames_req: parseInt(document.getElementById('cfg-frames').value)
  };

  try {
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === 'success') {
      closeSettingsModal();
      console.log('[SETTINGS] Updated successfully.');
    } else {
      alert('Error updating configuration: ' + data.message);
    }
  } catch (err) {
    console.error('[SETTINGS ERROR]', err);
    alert('Failed to save settings.');
  }
}

function handleStreamError(img) {
  console.warn('[STREAM] MJPEG stream reconnecting...');
  setTimeout(() => {
    img.src = `/video_feed?retry=${Date.now()}`;
  }, 1500);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
