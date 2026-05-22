// Variables globales
let fullData = null;
let currentFilteredData = null;
let cpuChart, netChart, pktChart;

// DOM elements
const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');
const loadingDiv = document.getElementById('loading');
const statsGrid = document.getElementById('statsGrid');
const infoRow = document.getElementById('infoRow');
const alertPanel = document.getElementById('alertPanel');
const alertList = document.getElementById('alertList');
const anomalyTableContainer = document.getElementById('anomalyTableContainer');
const anomalyTableBody = document.querySelector('#anomalyTable tbody');
const filterBar = document.getElementById('filterBar');
const dateFrom = document.getElementById('dateFrom');
const dateTo = document.getElementById('dateTo');
const applyRangeBtn = document.getElementById('applyRangeBtn');
const resetRangeBtn = document.getElementById('resetRangeBtn');
const resetZoomBtn = document.getElementById('resetZoomBtn');
const anomalyCard = document.getElementById('anomalyCard');

// Modal
const modal = document.getElementById('detailModal');
const modalDetails = document.getElementById('modalDetails');
const closeModal = document.querySelector('.close');

// Historial
let history = [];

function loadHistory() {
    const stored = localStorage.getItem('aiops_history');
    if (stored) { try { history = JSON.parse(stored); } catch(e) { history = []; } }
    renderHistory();
}
function saveHistory() { localStorage.setItem('aiops_history', JSON.stringify(history)); }
function addToHistory(filename, stats, anomalyCount, totalRows) {
    history.unshift({ id: Date.now(), timestamp: new Date().toISOString(), filename, stats, anomalyCount, totalRows });
    if (history.length > 20) history.pop();
    saveHistory();
    renderHistory();
}
function renderHistory() {
    const historyList = document.getElementById('historyList');
    if (!historyList) return;
    if (!history.length) { historyList.innerHTML = '<p style="text-align:center; color:gray;">No hay análisis previos.</p>'; return; }
    historyList.innerHTML = history.map(item => `
        <div class="history-item">
            <div><strong>${escapeHtml(item.filename)}</strong><br><small>${new Date(item.timestamp).toLocaleString()}</small><br>Anomalías: ${item.anomalyCount}/${item.totalRows} (${((item.anomalyCount/item.totalRows)*100).toFixed(1)}%)</div>
            <div class="history-actions"><button onclick="loadHistoryAnalysis(${item.id})">Cargar</button></div>
        </div>
    `).join('');
}
function loadHistoryAnalysis(id) {
    const record = history.find(h => h.id === id);
    if (record?.stats?.data) {
        fullData = record.stats.data;
        computeAndDisplay(fullData);
        document.querySelector('[data-tab="dashboard"]').click();
    } else alert('No se pudo cargar el análisis');
}
function escapeHtml(str) { return str.replace(/[&<>]/g, m => m === '&' ? '&amp;' : m === '<' ? '&lt;' : '&gt;'); }

// Función principal
function computeAndDisplay(data) {
    fullData = data;
    const anomalies = data.filter(d => d.is_anomaly);
    const total = data.length;
    const anomalyCount = anomalies.length;
    const avgCpu = (data.reduce((a,b)=>a+b.cpu_usage,0)/total).toFixed(2);

    document.getElementById('totalRecords').innerText = total;
    document.getElementById('anomalyCount').innerText = anomalyCount;
    document.getElementById('anomalyPct').innerText = ((anomalyCount/total)*100).toFixed(2)+'%';
    document.getElementById('avgCpu').innerText = avgCpu+'%';
    statsGrid.style.display = 'grid';
    infoRow.style.display = 'flex';
    filterBar.style.display = 'flex';

    // Rangos normales percentil 5-95
    const percentile = (arr, p) => {
        const sorted = [...arr].sort((a,b)=>a-b);
        const idx = (p/100)*(sorted.length-1);
        const low = Math.floor(idx), high = Math.ceil(idx);
        return low===high ? sorted[low] : sorted[low]*(1-(idx-low)) + sorted[high]*(idx-low);
    };
    const cpuVals = data.map(d=>d.cpu_usage), netVals = data.map(d=>d.network_in_kb), pktVals = data.map(d=>d.packet_rate);
    const cpuLow = percentile(cpuVals,5).toFixed(2), cpuHigh = percentile(cpuVals,95).toFixed(2);
    const netLow = percentile(netVals,5).toFixed(2), netHigh = percentile(netVals,95).toFixed(2);
    const pktLow = percentile(pktVals,5).toFixed(2), pktHigh = percentile(pktVals,95).toFixed(2);
    document.getElementById('rangesGrid').innerHTML = `
        <div class="range-item">📊 CPU: ${cpuLow}% - ${cpuHigh}%</div>
        <div class="range-item">🌐 Red: ${netLow} KB - ${netHigh} KB</div>
        <div class="range-item">📦 Paquetes: ${pktLow} - ${pktHigh}</div>
    `;

    // Alertas en forma de tarjetas compactas
    const alertItems = anomalies.slice(0,12).map(anom => {
        let metric = '';
        if (anom.cpu_usage < cpuLow || anom.cpu_usage > cpuHigh) metric += 'CPU ';
        if (anom.network_in_kb < netLow || anom.network_in_kb > netHigh) metric += 'Red ';
        if (anom.packet_rate < pktLow || anom.packet_rate > pktHigh) metric += 'Paquetes';
        if (!metric) metric = 'Múltiples';
        return `<div>⚠️ ${anom.timestamp} — <strong>${metric.trim()}</strong> (CPU:${anom.cpu_usage}%, Red:${anom.network_in_kb} KB, Paq:${anom.packet_rate})</div>`;
    }).join('');
    alertList.innerHTML = alertItems || '<div>✅ No se detectaron anomalías.</div>';
    alertPanel.style.display = 'block';

    // Tabla anomalías
    anomalyTableBody.innerHTML = anomalies.slice(0,20).map(anom => {
        let bad = '';
        if (anom.cpu_usage < cpuLow || anom.cpu_usage > cpuHigh) bad += 'CPU ';
        if (anom.network_in_kb < netLow || anom.network_in_kb > netHigh) bad += 'Red ';
        if (anom.packet_rate < pktLow || anom.packet_rate > pktHigh) bad += 'Paq';
        return `<tr><td>${anom.timestamp}</td><td>${anom.cpu_usage}</td><td>${anom.network_in_kb}</td><td>${anom.packet_rate}</td><td>${bad}</td></tr>`;
    }).join('');
    anomalyTableContainer.style.display = 'block';

    // Configurar fechas mín/máx
    if (data.length) {
        const first = data[0].timestamp.replace(' ', 'T').slice(0,19);
        const last = data[data.length-1].timestamp.replace(' ', 'T').slice(0,19);
        dateFrom.value = first; dateTo.value = last;
        dateFrom.min = first; dateFrom.max = last;
        dateTo.min = first; dateTo.max = last;
    }
    applyDateFilter();

    // Modal de desglose
    let cpuAnom=0, netAnom=0, pktAnom=0;
    anomalies.forEach(anom => {
        if (anom.cpu_usage < cpuLow || anom.cpu_usage > cpuHigh) cpuAnom++;
        if (anom.network_in_kb < netLow || anom.network_in_kb > netHigh) netAnom++;
        if (anom.packet_rate < pktLow || anom.packet_rate > pktHigh) pktAnom++;
    });
    modalDetails.innerHTML = `
        <p><strong>Total anomalías:</strong> ${anomalies.length}</p>
        <ul><li>🔴 <strong>CPU:</strong> ${cpuAnom}</li><li>🟢 <strong>Red:</strong> ${netAnom}</li><li>🟠 <strong>Paquetes:</strong> ${pktAnom}</li></ul>
        <hr><small>Rangos normales: CPU ${cpuLow}-${cpuHigh}% · Red ${netLow}-${netHigh} KB · Paq ${pktLow}-${pktHigh}</small>
    `;
}

// Filtro por fecha
function applyDateFilter() {
    if (!fullData) return;
    const from = new Date(dateFrom.value);
    const to = new Date(dateTo.value);
    to.setSeconds(to.getSeconds()+1);
    const filtered = fullData.filter(d => {
        const dDate = new Date(d.timestamp.replace(' ', 'T'));
        return dDate >= from && dDate <= to;
    });
    currentFilteredData = filtered;
    renderCharts(filtered);
}
function resetDateFilter() {
    if (fullData?.length) {
        const first = fullData[0].timestamp.replace(' ', 'T').slice(0,19);
        const last = fullData[fullData.length-1].timestamp.replace(' ', 'T').slice(0,19);
        dateFrom.value = first; dateTo.value = last;
        applyDateFilter();
    }
}
applyRangeBtn.addEventListener('click', applyDateFilter);
resetRangeBtn.addEventListener('click', resetDateFilter);

// Gráficos
function renderCharts(data) {
    if (!data || data.length === 0) return;
    const datasets = (metric, label, color) => {
        const normal = data.filter(p => !p.is_anomaly).map(p => ({x: p.timestamp, y: p[metric]}));
        const anomalies = data.filter(p => p.is_anomaly).map(p => ({x: p.timestamp, y: p[metric]}));
        return [
            { label: `${label} (normal)`, data: normal, borderColor: color, borderWidth: 1.5, pointRadius: 1.5, tension: 0.1, fill: false, showLine: true },
            { label: 'Anomalías', data: anomalies, borderColor: 'red', backgroundColor: 'red', pointRadius: 5, showLine: false, type: 'scatter' }
        ];
    };
    const cpuDs = datasets('cpu_usage', 'CPU %', '#3498db');
    const netDs = datasets('network_in_kb', 'Red KB', '#2ecc71');
    const pktDs = datasets('packet_rate', 'Paquetes', '#e67e22');

    function create(ctx, label, ds) {
        return new Chart(ctx, {
            type: 'line',
            data: { datasets: ds },
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: { x: { type: 'time', time: { tooltipFormat: 'YYYY-MM-DD HH:mm:ss', unit: 'minute' }, title: { display: true, text: 'Tiempo' } },
                           y: { title: { display: true, text: label } } },
                plugins: { zoom: { pan: { enabled: true, mode: 'x' }, zoom: { wheel: { enabled: true }, mode: 'x' } } }
            }
        });
    }
    if (cpuChart) cpuChart.destroy();
    if (netChart) netChart.destroy();
    if (pktChart) pktChart.destroy();
    cpuChart = create(document.getElementById('cpuChart'), 'Uso de CPU (%)', cpuDs);
    netChart = create(document.getElementById('networkChart'), 'Tráfico de Red (KB)', netDs);
    pktChart = create(document.getElementById('packetChart'), 'Tasa de Paquetes', pktDs);
}
function resetZoom() { if(cpuChart) cpuChart.resetZoom(); if(netChart) netChart.resetZoom(); if(pktChart) pktChart.resetZoom(); }
resetZoomBtn.addEventListener('click', resetZoom);

// Subida CSV
uploadBtn.addEventListener('click', async () => {
    if (!fileInput.files.length) return alert('Selecciona un archivo CSV');
    const file = fileInput.files[0];
    const formData = new FormData(); formData.append('file', file);
    loadingDiv.style.display = 'block';
    try {
        const res = await fetch('/upload', { method:'POST', body:formData });
        if (!res.ok) throw new Error(await res.text());
        const json = await res.json();
        const data = json.data;
        const anomalyCount = data.filter(d=>d.is_anomaly).length;
        addToHistory(file.name, { data }, anomalyCount, data.length);
        computeAndDisplay(data);
    } catch(err) { alert('Error: '+err.message); }
    finally { loadingDiv.style.display = 'none'; }
});

// Navegación y modal
anomalyCard?.addEventListener('click', ()=>modal.style.display='block');
closeModal.onclick = ()=>modal.style.display='none';
window.onclick = e => { if(e.target==modal) modal.style.display='none'; };
document.querySelectorAll('[data-tab]').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const tab = link.getAttribute('data-tab');
        document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
        document.getElementById(`${tab}Tab`).classList.add('active');
        document.querySelectorAll('[data-tab]').forEach(l=>l.classList.remove('active'));
        link.classList.add('active');
        if(tab==='history') renderHistory();
    });
});
document.getElementById('clearHistoryBtn')?.addEventListener('click',()=>{ if(confirm('Borrar todo?')){ history=[]; saveHistory(); renderHistory(); } });
loadHistory();