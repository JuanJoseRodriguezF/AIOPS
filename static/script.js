let currentRunId = null;
let currentData = [];
let charts = {};

const $ = (id) => document.getElementById(id);
const fileInput = $('fileInput');
const uploadBtn = $('uploadBtn');
const loading = $('loading');
const contaminationInput = $('contaminationInput');
const contaminationValue = $('contaminationValue');

contaminationInput?.addEventListener('input', () => {
    contaminationValue.textContent = `${Math.round(Number(contaminationInput.value) * 100)}%`;
});

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}

async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    if (!response.ok) {
        const error = await response.text();
        throw new Error(error);
    }
    return response.json();
}

uploadBtn.addEventListener('click', async () => {
    if (!fileInput.files.length) {
        alert('Selecciona un archivo CSV antes de analizar.');
        return;
    }
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    loading.style.display = 'block';
    uploadBtn.disabled = true;

    try {
        const contamination = Number(contaminationInput.value);
        const result = await fetchJson(`/upload?contamination=${contamination}`, { method: 'POST', body: formData });
        currentRunId = result.run_id;
        currentData = result.data || [];
        renderAnalysis(result);
        await loadHistory();
        await loadAlerts();
    } catch (error) {
        alert('Error procesando el archivo: ' + error.message);
    } finally {
        loading.style.display = 'none';
        uploadBtn.disabled = false;
    }
});

function renderAnalysis(result) {
    const metrics = result.metrics || {};
    $('statsGrid').style.display = 'grid';
    $('contextPanel').style.display = 'grid';
    $('anomalyTableContainer').style.display = 'block';

    $('totalRecords').textContent = metrics.total_records ?? '-';
    $('anomalyCount').textContent = metrics.anomaly_count ?? '-';
    $('anomalyPct').textContent = `${metrics.anomaly_pct ?? 0}% de los registros`;
    $('avgCpu').textContent = `${metrics.avg_cpu ?? 0}%`;
    $('avgLatency').textContent = `${metrics.avg_response_time_ms ?? 0} ms`;
    $('failedAuth').textContent = metrics.failed_auth_attempts_total ?? 0;
    $('activeRunLabel').textContent = `Análisis #${result.run_id} · ${result.model || 'ML'} · sensibilidad ${Math.round((result.contamination || 0) * 100)}%`;

    $('featureList').innerHTML = (result.features || []).map(f => `<span>${escapeHtml(f)}</span>`).join('') || '<span>Sin variables reportadas</span>';
    $('labelSummary').innerHTML = Object.entries(result.label_summary || {}).map(([key, value]) => `<span>${escapeHtml(key)}: ${value}</span>`).join('') || '<span>Dataset sin etiquetas</span>';
    $('inlineAlerts').innerHTML = (result.alerts || []).slice(0, 5).map(a => `<div class="mini-alert ${escapeHtml(a.severity)}"><strong>${escapeHtml(a.severity)}</strong> ${escapeHtml(a.description)}</div>`).join('') || '<div class="mini-alert ok">Sin alertas críticas</div>';

    renderCharts(currentData);
    renderAnomalyTable(currentData);
}

function renderAnomalyTable(data) {
    const anomalies = data.filter(item => item.is_anomaly).slice(0, 50);
    $('anomalyTableBody').innerHTML = anomalies.map(row => `
        <tr>
            <td>${escapeHtml(row.timestamp)}</td>
            <td>${escapeHtml(row.device_id || 'N/A')}</td>
            <td>${escapeHtml(row.device_type || 'N/A')}</td>
            <td>${escapeHtml(row.cpu_usage)}</td>
            <td>${escapeHtml(row.memory_usage ?? 'N/A')}</td>
            <td>${escapeHtml(row.network_in_kb)} / ${escapeHtml(row.network_out_kb ?? 'N/A')}</td>
            <td>${escapeHtml(row.failed_auth_attempts ?? 0)}</td>
            <td><span class="risk-pill">${Number(row.anomaly_score || 0).toFixed(3)}</span></td>
            <td>${escapeHtml(row.label || 'Sin etiqueta')}</td>
        </tr>
    `).join('') || '<tr><td colspan="9">No se detectaron anomalías.</td></tr>';
}

function renderCharts(data) {
    if (!data.length || typeof Chart === 'undefined') return;

    const normal = data.filter(d => !d.is_anomaly);
    const anomalous = data.filter(d => d.is_anomaly);

    const lineDataset = (items, metric, label, options = {}) => ({
        label,
        data: items.map(d => ({ x: d.timestamp, y: Number(d[metric] || 0) })),
        borderWidth: options.borderWidth || 1.8,
        pointRadius: options.pointRadius ?? 0,
        tension: 0.25,
        fill: false,
        borderColor: options.color,
        backgroundColor: options.color,
    });

    const anomalyDataset = (metric) => ({
        label: 'Anomalías',
        data: anomalous.map(d => ({ x: d.timestamp, y: Number(d[metric] || 0) })),
        type: 'scatter',
        pointRadius: 4,
        borderColor: '#ef4444',
        backgroundColor: '#ef4444',
    });

    createChart('resourceChart', [
        lineDataset(normal, 'cpu_usage', 'CPU normal', { color: '#38bdf8' }),
        lineDataset(normal, 'memory_usage', 'Memoria normal', { color: '#a78bfa' }),
        anomalyDataset('cpu_usage'),
    ], 'Recursos (%)');

    createChart('networkChart', [
        lineDataset(normal, 'network_in_kb', 'Red entrada', { color: '#22c55e' }),
        lineDataset(normal, 'network_out_kb', 'Red salida', { color: '#14b8a6' }),
        anomalyDataset('network_in_kb'),
    ], 'KB');

    createChart('trafficChart', [
        lineDataset(normal, 'packet_rate', 'Paquetes', { color: '#f59e0b' }),
        lineDataset(normal, 'avg_response_time_ms', 'Respuesta ms', { color: '#fb7185' }),
        anomalyDataset('packet_rate'),
    ], 'Valor');

    createChart('riskChart', [
        lineDataset(data, 'anomaly_score', 'Puntaje de riesgo', { color: '#eab308', pointRadius: 1 }),
        anomalyDataset('anomaly_score'),
    ], 'Riesgo relativo');
}

function createChart(canvasId, datasets, yLabel) {
    if (charts[canvasId]) charts[canvasId].destroy();
    const ctx = $(canvasId);
    charts[canvasId] = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { labels: { color: '#cbd5e1' } },
            },
            scales: {
                x: {
                    type: 'time',
                    ticks: { color: '#94a3b8', maxTicksLimit: 6 },
                    grid: { color: 'rgba(148,163,184,.12)' },
                },
                y: {
                    title: { display: true, text: yLabel, color: '#94a3b8' },
                    ticks: { color: '#94a3b8' },
                    grid: { color: 'rgba(148,163,184,.12)' },
                }
            }
        }
    });
}

async function loadHistory() {
    const result = await fetchJson('/analyses');
    const items = result.items || [];
    $('historyList').innerHTML = items.map(item => `
        <article class="history-item">
            <div>
                <strong>${escapeHtml(item.filename)}</strong>
                <small>Análisis #${item.id} · ${new Date(item.uploaded_at).toLocaleString()} · ${escapeHtml(item.model_name)}</small>
            </div>
            <div class="history-metrics">
                <span>${item.total_records} registros</span>
                <span class="danger-text">${item.anomaly_count} anomalías</span>
                <span>${Number(item.anomaly_pct).toFixed(2)}%</span>
                <button onclick="loadAnalysis(${item.id})">Ver</button>
            </div>
        </article>
    `).join('') || '<p class="empty-state">Todavía no hay análisis guardados en la base de datos.</p>';
}

async function loadAnalysis(id) {
    const run = await fetchJson(`/analyses/${id}`);
    const result = {
        run_id: run.id,
        model: run.model_name,
        contamination: run.contamination,
        features: run.features,
        label_summary: run.true_label_summary,
        metrics: {
            total_records: run.total_records,
            anomaly_count: run.anomaly_count,
            anomaly_pct: Number(run.anomaly_pct).toFixed(2),
            avg_cpu: average(run.observations, 'cpu_usage').toFixed(2),
            avg_response_time_ms: average(run.observations, 'avg_response_time_ms').toFixed(2),
            failed_auth_attempts_total: sum(run.observations, 'failed_auth_attempts'),
        },
        alerts: run.alerts,
        data: run.observations,
    };
    currentRunId = run.id;
    currentData = run.observations || [];
    renderAnalysis(result);
    document.querySelector('[data-tab="dashboard"]').click();
}

async function loadAlerts() {
    const result = await fetchJson('/alerts');
    const items = result.items || [];
    $('alertList').innerHTML = items.map(alert => `
        <article class="alert-item ${escapeHtml(alert.severity)}">
            <div>
                <span>${escapeHtml(alert.severity)}</span>
                <strong>${escapeHtml(alert.title)}</strong>
                <p>${escapeHtml(alert.description)}</p>
                <small>Archivo: ${escapeHtml(alert.filename)} · ${new Date(alert.created_at).toLocaleString()}</small>
            </div>
        </article>
    `).join('') || '<p class="empty-state">No hay alertas guardadas.</p>';
}

function average(items, field) {
    const vals = items.map(x => Number(x[field])).filter(x => !Number.isNaN(x));
    return vals.length ? vals.reduce((a,b) => a + b, 0) / vals.length : 0;
}

function sum(items, field) {
    return items.map(x => Number(x[field] || 0)).reduce((a,b) => a + b, 0);
}

$('refreshBtn').addEventListener('click', async () => { await loadHistory(); await loadAlerts(); });
$('refreshAlertsBtn').addEventListener('click', loadAlerts);
$('clearHistoryBtn').addEventListener('click', async () => {
    if (!confirm('Esto eliminará análisis, observaciones y alertas de la base SQLite local. ¿Continuar?')) return;
    await fetchJson('/analyses', { method: 'DELETE' });
    currentRunId = null;
    currentData = [];
    await loadHistory();
    await loadAlerts();
    alert('Base local eliminada.');
});

document.querySelectorAll('[data-tab]').forEach(link => {
    link.addEventListener('click', (event) => {
        event.preventDefault();
        const tab = link.dataset.tab;
        document.querySelectorAll('[data-tab]').forEach(item => item.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(item => item.classList.remove('active'));
        link.classList.add('active');
        $(`${tab}Tab`).classList.add('active');
        if (tab === 'history') loadHistory();
        if (tab === 'alerts') loadAlerts();
    });
});

loadHistory().catch(console.error);
loadAlerts().catch(console.error);
