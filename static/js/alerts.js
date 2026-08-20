/**
 * AI Smart Campus Safety & Monitoring System
 * Academic B.Tech Project - Alert History Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  loadAlertHistory();
});

/**
 * Fetches historical safety alerts from SQLite database via /api/alerts/history.
 */
async function loadAlertHistory() {
  const filterType = document.getElementById('filter-alert-type').value;
  const tbody = document.getElementById('alerts-table-body');
  const recordLabel = document.getElementById('record-count-label');

  try {
    const url = `/api/alerts/history?limit=100&type=${encodeURIComponent(filterType)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();

    if (data.status !== 'success') throw new Error(data.message || 'Failed to fetch history');

    const alerts = data.alerts || [];
    if (recordLabel) recordLabel.textContent = `Showing ${alerts.length} of ${data.total} records`;

    // Fetch and update summary statistics cards
    fetchHistoryStats();

    if (alerts.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8" style="text-align: center; padding: 2.5rem; color: var(--text-sub);">
            No incident records found for selected filter.
          </td>
        </tr>
      `;
      return;
    }

    let rowsHtml = '';
    alerts.forEach(alert => {
      let sevBadgeClass = 'badge-yellow';
      if (alert.severity === 'CRITICAL' || alert.severity === 'HIGH') {
        sevBadgeClass = 'badge-red';
      } else if (alert.severity === 'LOW') {
        sevBadgeClass = 'badge-blue';
      }

      const pIdText = alert.person_id ? `Person #${alert.person_id}` : '<span style="color: var(--text-sub);">-</span>';
      const countText = alert.people_count !== null ? alert.people_count : '-';

      rowsHtml += `
        <tr>
          <td style="font-weight: 600; color: var(--text-muted);">#${alert.id}</td>
          <td style="color: var(--text-muted); font-size: 0.78rem;">${escapeHtml(alert.timestamp)}</td>
          <td style="font-weight: 600; color: var(--text-main);">${escapeHtml(alert.alert_type)}</td>
          <td>${pIdText}</td>
          <td>${countText}</td>
          <td style="color: var(--text-muted); font-size: 0.78rem;">${escapeHtml(alert.source)}</td>
          <td><span class="safety-badge ${sevBadgeClass}">${alert.severity}</span></td>
          <td style="color: var(--text-muted); font-size: 0.78rem;">${escapeHtml(alert.details || '-')}</td>
        </tr>
      `;
    });

    tbody.innerHTML = rowsHtml;

  } catch (err) {
    console.error('[HISTORY ERROR]', err);
    tbody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align: center; padding: 2rem; color: var(--color-red);">
          Error loading alerts: ${escapeHtml(err.message)}
        </td>
      </tr>
    `;
  }
}

/**
 * Updates the 4 statistical summary cards on the Alert History page.
 */
async function fetchHistoryStats() {
  try {
    const res = await fetch('/api/stats');
    if (!res.ok) return;
    const data = await res.json();
    if (data.status !== 'success') return;

    const stats = data.db_stats;
    const elTot = document.getElementById('stat-total-alerts');
    const elRest = document.getElementById('stat-restricted-count');
    const elCrowd = document.getElementById('stat-crowd-count');
    const elMove = document.getElementById('stat-movement-count');

    if (elTot) elTot.textContent = stats.total_alerts;
    if (elRest) elRest.textContent = stats.restricted_count;
    if (elCrowd) elCrowd.textContent = stats.crowd_count;
    if (elMove) elMove.textContent = stats.movement_count;

  } catch (e) {
    console.warn('[STATS] Failed to load history stats:', e);
  }
}

/**
 * Modal controls for clearing database history.
 */
function confirmClearHistory() {
  const modal = document.getElementById('clear-modal');
  if (modal) modal.classList.add('open');
}

function closeClearModal() {
  const modal = document.getElementById('clear-modal');
  if (modal) modal.classList.remove('open');
}

/**
 * Sends POST request to clear database alert records.
 */
async function executeClearHistory() {
  try {
    const res = await fetch('/api/alerts/clear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();
    if (data.status === 'success') {
      closeClearModal();
      loadAlertHistory();
    } else {
      alert('Failed to clear alert history: ' + data.message);
    }
  } catch (err) {
    console.error('[CLEAR ERROR]', err);
    alert('An error occurred while clearing history.');
  }
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
