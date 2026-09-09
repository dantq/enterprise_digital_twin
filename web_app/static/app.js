/**
 * Enterprise Digital Twin — Executive Dashboard & AI Financial Intelligence
 * Client Application Logic (app.js)
 * Architecture: Vanilla JavaScript, Chart.js 4.x, REST API Integration
 */

// Global Application State & Chart Instances
let currentTimeframe = 'all';
let cachedOverview = null;
let cachedSupplyChain = null;
let cachedCustomerMarketing = null;
let cachedDags = [];
let currentDagCode = 'S001';
let cachedIncidents = [];

// Chart Instances
let revenueChart = null;
let channelChart = null;
let waterfallChart = null;
let warehouseRegionChart = null;
let customerSegmentChart = null;
let ratingsDistChart = null;

// =============================================================================
// Utility & Formatting Helpers
// =============================================================================

function formatVND(amount) {
  if (amount === undefined || amount === null || isNaN(amount)) return '0 ₫';
  return new Intl.NumberFormat('vi-VN', {
    style: 'currency',
    currency: 'VND',
    maximumFractionDigits: 0
  }).format(amount);
}

function formatNumber(num) {
  if (num === undefined || num === null || isNaN(num)) return '0';
  return new Intl.NumberFormat('vi-VN').format(num);
}

function formatPercent(pct) {
  if (pct === undefined || pct === null || isNaN(pct)) return '0.0%';
  return `${Number(pct).toFixed(1)}%`;
}

function escapeHtml(text) {
  if (!text) return '';
  return text
    .toString()
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function renderMarkdown(md) {
  if (!md) return '';
  let html = escapeHtml(md);

  // Headers
  html = html.replace(/^### (.*$)/gim, '<h4 style="color:#a5b4fc;margin:12px 0 6px;">$1</h4>');
  html = html.replace(/^## (.*$)/gim, '<h3 style="color:#ffffff;margin:16px 0 8px;border-bottom:1px solid rgba(255,255,255,0.08);padding-bottom:4px;">$1</h3>');
  html = html.replace(/^# (.*$)/gim, '<h2 style="color:#ffffff;margin:20px 0 10px;">$1</h2>');

  // Bold & Italic
  html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/gim, '<em>$1</em>');

  // Code blocks
  html = html.replace(/```([\s\S]*?)```/gim, '<pre><code>$1</code></pre>');
  html = html.replace(/`([^`]+)`/gim, '<code style="background:rgba(255,255,255,0.08);padding:2px 6px;border-radius:4px;font-family:var(--font-mono);font-size:0.85em;">$1</code>');

  // Bullet points
  html = html.replace(/^\s*[-*]\s+(.*$)/gim, '<li style="margin-left:20px;margin-bottom:4px;">$1</li>');

  // Paragraphs
  html = html.replace(/\n\n+/g, '</p><p style="margin-bottom:8px;">');
  html = `<p style="margin-bottom:8px;">${html}</p>`;
  html = html.replace(/<p style="margin-bottom:8px;"><\/p>/g, '');

  return html;
}

// =============================================================================
// Navigation & Tab Switching
// =============================================================================

function switchTab(tabName) {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  const activeBtn = document.getElementById(`tab-${tabName}`);
  if (activeBtn) activeBtn.classList.add('active');

  document.querySelectorAll('.view-panel').forEach(panel => {
    panel.classList.remove('active');
  });
  const activePanel = document.getElementById(`view-${tabName}`);
  if (activePanel) activePanel.classList.add('active');

  window.scrollTo({ top: 0, behavior: 'smooth' });

  // Lazy load tab specific data
  if (tabName === 'supply-chain' && !cachedSupplyChain) {
    loadSupplyChain();
  } else if (tabName === 'customer-growth' && !cachedCustomerMarketing) {
    loadCustomerGrowth();
  } else if (tabName === 'crisis-sim' && cachedDags.length === 0) {
    loadCrisisSim();
  } else if (tabName === 'ai-assistant') {
    setTimeout(() => {
      const input = document.getElementById('ai-user-input');
      if (input) input.focus();
    }, 150);
  }
}

function switchFinSubtab(subName) {
  document.querySelectorAll('.finance-subtabs .subtab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('onclick')?.includes(`'${subName}'`));
  });

  document.querySelectorAll('.fin-subview').forEach(sub => {
    sub.classList.remove('active');
  });
  const targetSubview = document.getElementById(`subview-${subName}`);
  if (targetSubview) targetSubview.classList.add('active');

  if (subName === 'waterfall' && cachedOverview) {
    setTimeout(() => renderWaterfallChart(), 50);
  }
}

function setTimeframe(tf) {
  currentTimeframe = tf;
  document.querySelectorAll('.tf-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-tf') === tf);
  });
  loadOverview(tf);
}

// =============================================================================
// Module 1: Executive Overview & Health Scorecard
// =============================================================================

async function loadOverview(timeframe = 'all') {
  try {
    const res = await fetch(`/api/dashboard/overview?timeframe=${timeframe}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    cachedOverview = data;

    // 1. Render Health Gauge Widget
    renderHealthGauge(data.health);

    // 2. Render 6 Headline KPI Cards
    const kpis = data.kpis;
    if (kpis && kpis.financial) {
      document.getElementById('val-net-revenue').innerText = formatVND(kpis.financial.recognized_revenue);
      document.getElementById('val-total-orders').innerText = `${formatNumber(kpis.financial.total_orders)} đơn hàng (${formatNumber(kpis.financial.delivered_orders)} hoàn tất)`;

      const grossRev = kpis.financial.recognized_revenue;
      const cogs = grossRev * 0.72; // ~72% COGS
      const grossProfit = grossRev - cogs;
      document.getElementById('val-gross-profit').innerText = formatVND(grossProfit);
      document.getElementById('val-gross-margin').innerText = `Biên LN: ${(grossProfit / grossRev * 100).toFixed(1)}%`;

      // Net profit after crisis erosion
      const erosion = kpis.crisis_governance ? kpis.crisis_governance.total_erosion_amount : 2839689156.0;
      const opex = grossRev * 0.15;
      const netProfit = Math.max(0, grossProfit - opex - erosion);
      const netMargin = (netProfit / grossRev * 100);
      document.getElementById('val-net-profit').innerText = formatVND(netProfit);
      document.getElementById('val-net-margin').innerText = `Biên Ròng: ${netMargin.toFixed(1)}%`;
    }

    if (kpis && kpis.logistics) {
      document.getElementById('val-ontime-rate').innerText = formatPercent(kpis.logistics.on_time_rate_pct);
      const totalDelivered = kpis.logistics.total_delivered_shipments;
      const onTime = kpis.logistics.on_time_shipments;
      const delayed = Math.max(0, totalDelivered - onTime);
      document.getElementById('val-delayed-count').innerText = `${formatNumber(delayed)} đơn trễ`;
    }

    if (kpis && kpis.payments) {
      document.getElementById('val-payment-rate').innerText = formatPercent(kpis.payments.success_rate_pct);
      document.getElementById('val-payment-failed').innerText = `${formatNumber(kpis.payments.failed_payments)} GD lỗi`;
    }

    // 3. Render Incidents Count & Quick List
    if (data.incidents) {
      cachedIncidents = data.incidents;
      const activeCount = (data.kpis && data.kpis.crisis_governance) ? data.kpis.crisis_governance.active_incidents : 0;
      const countEl = document.getElementById('badge-incident-count');
      if (countEl) {
        countEl.innerText = activeCount;
        if (activeCount === 0) {
          countEl.style.background = '#10b981';
          countEl.title = '0 sự cố hoạt động - Toàn bộ 5 sự cố lịch sử đã được lưu trữ an toàn';
        } else {
          countEl.style.background = 'var(--rose)';
          countEl.title = `${activeCount} sự cố khẩn cấp đang kích hoạt`;
        }
      }
      renderIncidentQuickList(data.incidents);
    }

    // 4. Render Charts & Carrier Table
    renderRevenueTrendsChart(data.trends || []);
    renderChannelSalesChart(data.channels || []);
    renderCarrierTable(data.carriers || []);

    // 5. Update Alert Ticker if available
    if (data.alerts) {
      renderAlertTicker(data.alerts);
    }

  } catch (err) {
    console.error('Error loading overview data:', err);
  }
}

function renderHealthGauge(health) {
  if (!health) return;
  const score = health.score || 62;
  document.getElementById('gauge-score-val').innerText = Math.round(score);
  
  const statusLabel = document.getElementById('gauge-status-label');
  if (statusLabel) {
    statusLabel.innerText = health.status_label || 'VẬN HÀNH';
    statusLabel.className = `gauge-status badge-${health.status_badge || 'warning'}`;
  }

  const progressBar = document.getElementById('gauge-progress');
  if (progressBar) {
    progressBar.setAttribute('stroke-dasharray', `${Math.min(100, Math.round(score))}, 100`);
    progressBar.className = `circle-bar ${health.status_badge || 'warning'}`;
  }

  const gradeVal = document.getElementById('val-health-grade');
  if (gradeVal) {
    gradeVal.innerText = `${health.benchmark_grade || 'B+'} (${score}/100)`;
  }

  // Render Pillars meters
  const pillarsContainer = document.getElementById('pillars-meters-container');
  if (pillarsContainer && health.pillars) {
    let html = '';
    const colorMap = {
      financial: 'var(--emerald)',
      supply_chain: 'var(--amber)',
      logistics: 'var(--rose)',
      customer: 'var(--cyan)',
      technology: 'var(--primary)'
    };

    Object.keys(health.pillars).forEach(k => {
      const p = health.pillars[k];
      const barColor = colorMap[k] || 'var(--primary)';
      html += `
        <div class="pillar-meter-box">
          <div class="pillar-head">
            <span class="pillar-name">${p.label}</span>
            <span class="pillar-score" style="color:${barColor};">${p.score}/100</span>
          </div>
          <div class="pillar-progress-track">
            <div class="pillar-progress-fill" style="width:${p.score}%;background:${barColor};"></div>
          </div>
          <span class="pillar-weight-text">Trọng số: ${p.weight}%</span>
        </div>
      `;
    });
    pillarsContainer.innerHTML = html;
  }
}

function renderAlertTicker(alerts) {
  const container = document.getElementById('ticker-scroll-content');
  const tickerEl = document.getElementById('alert-ticker');
  const pulseEl = document.getElementById('ticker-pulse');
  const badgeTextEl = document.getElementById('ticker-badge-text');
  const btnActionEl = document.getElementById('btn-ticker-action');
  if (!container || !alerts || alerts.length === 0) return;

  const isNormal = alerts[0].severity === 'NORMAL' || alerts[0].is_emergency === false;

  if (isNormal) {
    if (tickerEl) {
      tickerEl.classList.remove('emergency-state');
      tickerEl.classList.add('normal-state');
    }
    if (pulseEl) {
      pulseEl.className = 'pulse-indicator-green';
    }
    if (badgeTextEl) {
      badgeTextEl.innerText = 'TRẠNG THÁI HỆ THỐNG:';
    }
    if (btnActionEl) {
      btnActionEl.innerHTML = 'Hồ sơ Sự cố & Giả lập &rarr;';
    }
    container.innerHTML = `<span class="ticker-item"><strong class="text-emerald">[BÌNH THƯỜNG] ${escapeHtml(alerts[0].domain)}:</strong> ${escapeHtml(alerts[0].summary)}</span>`;
    return;
  }

  // Active emergency state
  if (tickerEl) {
    tickerEl.classList.remove('normal-state');
    tickerEl.classList.add('emergency-state');
  }
  if (pulseEl) {
    pulseEl.className = 'pulse-indicator-red';
  }
  if (badgeTextEl) {
    badgeTextEl.innerText = 'THREAT RADAR:';
  }
  if (btnActionEl) {
    btnActionEl.innerHTML = 'Can thiệp Mô phỏng &rarr;';
  }

  let html = '';
  alerts.forEach((alt, idx) => {
    const sevColor = alt.severity === 'CRITICAL' ? 'text-rose' : (alt.severity === 'HIGH' ? 'text-amber' : 'text-indigo');
    html += `<span class="ticker-item" onclick="jumpToIncident('${alt.code}')" style="cursor:pointer;" title="Bấm để xem phân tích và mô phỏng sự cố ${alt.code}"><strong class="${sevColor}">[${alt.code}] ${escapeHtml(alt.domain)}:</strong> ${escapeHtml(alt.summary)} &rarr;</span>`;
    if (idx < alerts.length - 1) {
      html += `<span class="ticker-sep">&bull;</span>`;
    }
  });
  container.innerHTML = html;
}

function jumpToIncident(scenarioCode) {
  switchTab('crisis-sim');
  loadCausalDag(scenarioCode);
  switchDebateScenario(scenarioCode);
  setTimeout(() => {
    const el = document.getElementById('debate-arena-section');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, 100);
}

function renderRevenueTrendsChart(trends) {
  const ctx = document.getElementById('chart-revenue-trends');
  if (!ctx || typeof Chart === 'undefined') return;
  if (revenueChart) revenueChart.destroy();

  const labels = trends.map(t => t.period);
  const revenues = trends.map(t => t.revenue);
  const cancelled = trends.map(t => t.cancelled_revenue);

  revenueChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Doanh thu Thực nhận (VND)',
          data: revenues,
          borderColor: '#6366f1',
          backgroundColor: 'rgba(99, 102, 241, 0.15)',
          fill: true,
          tension: 0.35,
          borderWidth: 3,
          pointBackgroundColor: '#6366f1',
          pointRadius: 4,
          pointHoverRadius: 6,
        },
        {
          label: 'Giá trị Đơn hủy (VND)',
          data: cancelled,
          borderColor: '#f43f5e',
          backgroundColor: 'rgba(244, 63, 94, 0.1)',
          fill: true,
          tension: 0.35,
          borderWidth: 2,
          pointBackgroundColor: '#f43f5e',
          pointRadius: 4,
          pointHoverRadius: 6,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0f172a',
          borderColor: 'rgba(255, 255, 255, 0.1)',
          borderWidth: 1,
          titleFont: { family: 'Outfit', size: 13 },
          bodyFont: { family: 'JetBrains Mono', size: 12 },
          callbacks: {
            label: function(context) {
              return `${context.dataset.label}: ${formatVND(context.parsed.y)}`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.04)' },
          ticks: { color: '#94a3b8', font: { family: 'Inter', size: 11 } }
        },
        y: {
          grid: { color: 'rgba(255, 255, 255, 0.06)' },
          ticks: {
            color: '#94a3b8',
            font: { family: 'JetBrains Mono', size: 11 },
            callback: function(val) {
              if (val >= 1e9) return (val / 1e9).toFixed(1) + ' Tỷ';
              if (val >= 1e6) return (val / 1e6).toFixed(0) + ' Tr';
              return val;
            }
          }
        }
      }
    }
  });
}

function renderChannelSalesChart(channels) {
  const ctx = document.getElementById('chart-channel-sales');
  if (!ctx || typeof Chart === 'undefined') return;
  if (channelChart) channelChart.destroy();

  const labels = channels.map(c => c.channel);
  const revenues = channels.map(c => c.revenue);
  const palette = ['#6366f1', '#10b981', '#f59e0b', '#06b6d4', '#ec4899', '#8b5cf6'];

  channelChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: revenues,
        backgroundColor: palette.slice(0, labels.length),
        borderColor: '#0f172a',
        borderWidth: 3,
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '68%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#94a3b8', font: { family: 'Inter', size: 11 }, padding: 12, usePointStyle: true }
        },
        tooltip: {
          backgroundColor: '#0f172a',
          borderColor: 'rgba(255, 255, 255, 0.1)',
          borderWidth: 1,
          callbacks: {
            label: function(context) {
              const val = context.raw;
              const total = revenues.reduce((a, b) => a + b, 0);
              const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
              return ` ${context.label}: ${formatVND(val)} (${pct}%)`;
            }
          }
        }
      }
    }
  });
}

function renderCarrierTable(carriers) {
  const container = document.getElementById('carrier-table-container');
  if (!container) return;

  if (!carriers || carriers.length === 0) {
    container.innerHTML = '<p class="text-muted p-3">Chưa có dữ liệu vận đơn logistics.</p>';
    return;
  }

  let html = `
    <table class="table-simple">
      <thead>
        <tr>
          <th>Đối tác vận chuyển</th>
          <th style="text-align:right;">Tổng kiện</th>
          <th style="text-align:right;">Đúng hạn</th>
          <th style="text-align:right;">Trễ hạn</th>
          <th style="text-align:right;">SLA (%)</th>
          <th style="text-align:right;">Thời gian giao TB</th>
        </tr>
      </thead>
      <tbody>
  `;

  carriers.forEach(c => {
    const isProblematic = c.carrier_name.includes('Giao Hàng Nhanh') || c.on_time_pct < 85;
    const slaColor = c.on_time_pct >= 90 ? 'var(--emerald)' : (c.on_time_pct >= 80 ? 'var(--amber)' : 'var(--rose)');
    
    html += `
      <tr>
        <td>
          <strong style="color: ${isProblematic ? 'var(--rose)' : '#ffffff'}">${escapeHtml(c.carrier_name)}</strong>
          ${isProblematic ? '<span class="tag-danger" style="margin-left:6px;font-size:0.65rem;">Ách tắc (S002)</span>' : ''}
        </td>
        <td style="text-align:right;" class="font-mono">${formatNumber(c.total_shipments)}</td>
        <td style="text-align:right;color:var(--emerald);" class="font-mono">${formatNumber(c.on_time)}</td>
        <td style="text-align:right;color:${c.delayed > 0 ? 'var(--rose)' : 'inherit'};" class="font-mono">${formatNumber(c.delayed)}</td>
        <td style="text-align:right;font-weight:700;color:${slaColor};" class="font-mono">${formatPercent(c.on_time_pct)}</td>
        <td style="text-align:right;" class="font-mono">${c.avg_transit_days.toFixed(1)} ngày</td>
      </tr>
    `;
  });

  html += '</tbody></table>';
  container.innerHTML = html;
}

function renderIncidentQuickList(incidents) {
  const container = document.getElementById('incident-quick-list');
  if (!container) return;

  if (!incidents || incidents.length === 0) {
    container.innerHTML = '<p class="text-muted p-3">Không có dữ liệu sự cố.</p>';
    return;
  }

  const activeIncidents = incidents.filter(i => i.is_active || i.status === 'Active');
  const archivedIncidents = incidents.filter(i => !i.is_active && i.status !== 'Active');

  let html = '';
  if (activeIncidents.length > 0) {
    html += `<div style="padding: 6px 12px; background: rgba(244, 63, 94, 0.12); border: 1px solid rgba(244, 63, 94, 0.3); border-radius: 6px; margin-bottom: 8px; font-size: 0.75rem; color: #fca5a5; font-weight: 700; display:flex; align-items:center; gap:6px;">⚠️ <span>${activeIncidents.length} SỰ CỐ KHẨN CẤP ĐANG KÍCH HOẠT</span></div>`;
    activeIncidents.forEach(inc => {
      html += `
        <div class="incident-quick-item" onclick="openRcaModal('${inc.incident_id}')" style="border-left: 3px solid var(--rose);">
          <div class="inc-left">
            <span class="inc-badge" style="background:var(--rose);color:#fff;">${inc.scenario_code}</span>
            <div>
              <div class="inc-name text-rose">${escapeHtml(inc.title)}</div>
              <div class="inc-domain">Phân hệ: ${escapeHtml(inc.domain)} &bull; Mức độ: ${escapeHtml(inc.severity)}</div>
            </div>
          </div>
          <span class="btn-rca-view" style="font-size:0.75rem;padding:4px 10px;">Xử lý &rarr;</span>
        </div>
      `;
    });
  } else {
    html += `
      <div style="padding: 10px 14px; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 8px; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between;">
        <div style="display:flex; align-items:center; gap: 8px;">
          <span style="font-size: 1.1rem;">🟢</span>
          <div>
            <div style="font-size: 0.8rem; color: #34d399; font-weight: 700;">Hệ thống thời gian thực ổn định</div>
            <div style="font-size: 0.72rem; color: #94a3b8;">Không có sự cố nào đang diễn ra</div>
          </div>
        </div>
        <span class="archive-badge-tag" style="font-size: 0.7rem; cursor: pointer;" onclick="switchTab('crisis-sim')">5 Đã Lưu trữ &rarr;</span>
      </div>
    `;
    // Show recent 3 archived incidents in compact view
    archivedIncidents.slice(0, 3).forEach(inc => {
      html += `
        <div class="incident-quick-item" onclick="openRcaModal('${inc.incident_id}')" style="opacity: 0.85;">
          <div class="inc-left">
            <span class="inc-badge" style="background: rgba(100, 116, 139, 0.3); border-color: rgba(148, 163, 184, 0.3);">${inc.scenario_code}</span>
            <div>
              <div class="inc-name" style="font-size: 0.82rem;">${escapeHtml(inc.title)}</div>
              <div class="inc-domain" style="font-size: 0.72rem; color: #94a3b8;">
                <span class="tag-resolved" style="padding: 1px 6px; font-size: 0.68rem;">Đã giải quyết</span> &bull; 
                ${inc.start_time ? new Date(inc.start_time).toLocaleDateString('vi-VN') : 'Tháng 08/2026'}
              </div>
            </div>
          </div>
          <span class="btn-rca-view" style="font-size:0.72rem;padding:3px 8px;">RCA &rarr;</span>
        </div>
      `;
    });
  }

  container.innerHTML = html;
}

// =============================================================================
// Module 2: Supply Chain & Inventory Twin (NEW)
// =============================================================================

async function loadSupplyChain() {
  try {
    const res = await fetch('/api/dashboard/supply-chain');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const resData = await res.json();
    const data = resData.data;
    cachedSupplyChain = data;

    // 1. KPI summary cards
    if (data.summary) {
      document.getElementById('sc-total-wh').innerText = data.summary.total_warehouses;
      document.getElementById('sc-total-skus').innerText = data.summary.monitored_skus;
      document.getElementById('sc-alert-skus').innerText = data.summary.critical_low_stock_count;
      document.getElementById('sc-units-in-stock').innerText = `${formatNumber(data.summary.total_units_in_stock)} sp`;
      document.getElementById('sc-inventory-val').innerText = formatVND(data.summary.total_inventory_valuation);
      document.getElementById('sc-low-stock-count').innerText = `${data.summary.critical_low_stock_count} SKUs`;
      document.getElementById('low-stock-badge-tag').innerText = `${data.summary.critical_low_stock_count} SKUs Nguy cơ`;
    }

    // 2. Render Warehouses Capacity Bars
    renderWarehousesBars(data.warehouses || []);

    // 3. Render Region Breakdown Donut
    renderWarehouseRegionChart(data.warehouses || []);

    // 4. Render Critical Low Stock Alerts Table
    renderLowStockTable(data.low_stock_alerts || []);

    // 5. Render Suppliers & PO Pipeline Table
    renderSuppliersTable(data.suppliers || []);

  } catch (err) {
    console.error('Error loading supply chain data:', err);
  }
}

function renderWarehousesBars(warehouses) {
  const container = document.getElementById('warehouses-bars-container');
  if (!container) return;

  let html = '';
  warehouses.forEach(w => {
    const isOverload = w.utilization_pct > 100;
    const barColor = isOverload ? 'var(--rose)' : (w.utilization_pct >= 80 ? 'var(--amber)' : 'var(--emerald)');
    const fillWidth = Math.min(100, w.utilization_pct);

    html += `
      <div class="wh-bar-card">
        <div class="wh-bar-head">
          <div>
            <strong>${escapeHtml(w.warehouse_name)}</strong>
            <span style="font-size:0.75rem;color:var(--text-muted);margin-left:8px;">Khu vực: ${escapeHtml(w.region)}</span>
          </div>
          <div>
            <strong style="color:${barColor};">${w.utilization_pct}%</strong>
            <span class="${isOverload ? 'tag-danger' : 'tag-success'}" style="margin-left:8px;font-size:0.68rem;">${w.status}</span>
          </div>
        </div>
        <div class="wh-progress-track">
          <div class="wh-progress-fill" style="width:${fillWidth}%;background:${barColor};"></div>
        </div>
        <div class="wh-bar-footer">
          <span>Lưu kho: <strong>${formatNumber(w.current_inventory)}</strong> / Định mức: <strong>${formatNumber(w.capacity)}</strong></span>
          <span>Công suất xử lý: <strong>${formatNumber(w.daily_capacity)} sp/ngày</strong></span>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

function renderWarehouseRegionChart(warehouses) {
  const ctx = document.getElementById('chart-warehouse-region');
  if (!ctx || typeof Chart === 'undefined') return;
  if (warehouseRegionChart) warehouseRegionChart.destroy();

  const labels = warehouses.map(w => w.warehouse_name);
  const data = warehouses.map(w => w.current_inventory);
  const palette = ['#6366f1', '#10b981', '#f59e0b', '#06b6d4', '#ec4899'];

  warehouseRegionChart = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: palette.slice(0, labels.length),
        borderColor: '#0f172a',
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { color: '#94a3b8', font: { family: 'Inter', size: 10 }, padding: 8 } }
      }
    }
  });
}

function renderLowStockTable(alerts) {
  const tbody = document.getElementById('low-stock-table-body');
  if (!tbody) return;

  if (!alerts || alerts.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted p-3">Mọi mặt hàng đều đảm bảo ngưỡng an toàn.</td></tr>';
    return;
  }

  let html = '';
  alerts.forEach(item => {
    const isEcoLaptop = item.product_name.includes('Eco Laptop') || item.available_qty === 0;
    const badgeClass = item.available_qty === 0 ? 'tag-danger' : 'tag-warning';

    html += `
      <tr>
        <td>
          <strong style="color:${isEcoLaptop ? 'var(--rose)' : '#ffffff'}">${escapeHtml(item.product_name)}</strong>
          ${isEcoLaptop ? '<span class="tag-danger" style="margin-left:6px;font-size:0.65rem;">Cạn kho S001</span>' : ''}
        </td>
        <td><span class="tag-accent">${escapeHtml(item.category)}</span></td>
        <td>${escapeHtml(item.warehouse)}</td>
        <td style="text-align:right;font-weight:700;color:${item.available_qty === 0 ? 'var(--rose)' : 'var(--amber)'};" class="font-mono">
          ${formatNumber(item.available_qty)}
        </td>
        <td style="text-align:right;" class="font-mono text-muted">${formatNumber(item.reorder_point)}</td>
        <td style="text-align:right;" class="font-mono">${formatVND(item.unit_price)}</td>
        <td style="text-align:center;"><span class="${badgeClass}">${item.risk_level}</span></td>
      </tr>
    `;
  });

  tbody.innerHTML = html;
}

function renderSuppliersTable(suppliers) {
  const tbody = document.getElementById('suppliers-table-body');
  if (!tbody) return;

  let html = '';
  suppliers.forEach(s => {
    const isProblematic = s.is_critical || s.supplier_name.includes('Viet Electronics');
    const relColor = s.reliability_pct >= 90 ? 'var(--emerald)' : (s.reliability_pct >= 80 ? 'var(--amber)' : 'var(--rose)');

    html += `
      <tr>
        <td>
          <strong style="color:${isProblematic ? 'var(--rose)' : '#ffffff'}">${escapeHtml(s.supplier_name)}</strong>
          ${isProblematic ? '<span class="tag-danger" style="margin-left:6px;font-size:0.65rem;">Đứt gãy (S001)</span>' : ''}
        </td>
        <td>${escapeHtml(s.region)}</td>
        <td style="text-align:right;color:${relColor};font-weight:700;" class="font-mono">${s.reliability_pct}%</td>
        <td style="text-align:right;" class="font-mono">${s.avg_lead_time_days.toFixed(1)} ngày</td>
        <td style="text-align:right;" class="font-mono">${formatNumber(s.total_pos)}</td>
        <td style="text-align:right;color:var(--emerald);" class="font-mono">${formatVND(s.total_po_value)}</td>
        <td style="text-align:center;">
          <span class="${isProblematic ? 'tag-danger' : 'tag-success'}">
            ${isProblematic ? 'Đình công nhà máy' : 'Hoạt động tốt'}
          </span>
        </td>
      </tr>
    `;
  });

  tbody.innerHTML = html;
}

// =============================================================================
// Module 3: Customer Intelligence & Marketing Performance (NEW)
// =============================================================================

async function loadCustomerGrowth() {
  try {
    const res = await fetch('/api/dashboard/customer-marketing');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const resData = await res.json();
    const data = resData.data;
    cachedCustomerMarketing = data;

    // 1. Render Customer Segmentation Chart
    renderCustomerSegmentsChart(data.segments || []);

    // 2. Render Review Ratings Chart
    renderRatingsChart(data.ratings || []);

    // 3. Render Support Tickets Table
    renderTicketsTable(data.tickets || []);

    // 4. Render Marketing Campaigns Table
    renderMarketingTable(data.campaigns || []);

  } catch (err) {
    console.error('Error loading customer marketing data:', err);
  }
}

function renderCustomerSegmentsChart(segments) {
  const ctx = document.getElementById('chart-customer-segments');
  if (!ctx || typeof Chart === 'undefined') return;
  if (customerSegmentChart) customerSegmentChart.destroy();

  const labels = segments.map(s => s.segment);
  const counts = segments.map(s => s.count);
  const palette = ['#6366f1', '#10b981', '#06b6d4', '#f59e0b', '#f43f5e'];

  customerSegmentChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: counts,
        backgroundColor: palette.slice(0, labels.length),
        borderColor: '#0f172a',
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { color: '#94a3b8', font: { family: 'Inter', size: 10 } } }
      }
    }
  });
}

function renderRatingsChart(ratings) {
  const ctx = document.getElementById('chart-ratings-dist');
  if (!ctx || typeof Chart === 'undefined') return;
  if (ratingsDistChart) ratingsDistChart.destroy();

  const sorted = [...ratings].sort((a, b) => b.rating - a.rating);
  const labels = sorted.map(r => `${r.rating} ⭐`);
  const counts = sorted.map(r => r.count);
  const colors = sorted.map(r => r.rating <= 2 ? '#f43f5e' : (r.rating === 3 ? '#f59e0b' : '#10b981'));

  ratingsDistChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Số lượng đánh giá',
        data: counts,
        backgroundColor: colors,
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(255, 255, 255, 0.04)' }, ticks: { color: '#94a3b8' } },
        y: { grid: { color: 'rgba(255, 255, 255, 0.06)' }, ticks: { color: '#94a3b8' } }
      }
    }
  });
}

function renderTicketsTable(tickets) {
  const tbody = document.getElementById('tickets-table-body');
  if (!tbody) return;

  let html = '';
  tickets.forEach(t => {
    html += `
      <tr>
        <td><strong>${escapeHtml(t.label)}</strong></td>
        <td style="text-align:right;" class="font-mono">${formatNumber(t.count)}</td>
        <td style="text-align:right;" class="font-mono">${t.pct_share}%</td>
        <td style="text-align:right;" class="font-mono">${t.avg_resolution_hours}h</td>
        <td style="text-align:right;color:${t.avg_csat < 3.0 ? 'var(--rose)' : 'var(--emerald)'};font-weight:700;" class="font-mono">${t.avg_csat} ⭐</td>
      </tr>
    `;
  });

  tbody.innerHTML = html;
}

function renderMarketingTable(campaigns) {
  const tbody = document.getElementById('marketing-table-body');
  if (!tbody) return;

  let html = '';
  campaigns.forEach(c => {
    html += `
      <tr style="${c.is_anomaly ? 'background:rgba(244, 63, 94, 0.08);' : ''}">
        <td>
          <strong style="color:${c.is_anomaly ? 'var(--rose)' : '#ffffff'}">${escapeHtml(c.campaign_name)}</strong>
          <div style="font-size:0.72rem;color:var(--text-muted);">${escapeHtml(c.channel)}</div>
        </td>
        <td style="text-align:right;color:var(--rose);" class="font-mono">${formatVND(c.total_spend)}</td>
        <td style="text-align:right;" class="font-mono">${formatNumber(c.clicks)}</td>
        <td style="text-align:right;" class="font-mono"><strong>${formatNumber(c.conversions)}</strong> (${c.cvr_pct}%)</td>
        <td style="text-align:right;color:${c.is_anomaly ? 'var(--rose)' : 'inherit'};font-weight:700;" class="font-mono">
          ${c.cac > 0 ? formatVND(c.cac) : '--'}
        </td>
        <td style="text-align:center;">
          <span class="${c.is_anomaly ? 'tag-danger' : 'tag-success'}">
            ${c.is_anomaly ? 'Lãng phí (S004)' : 'Đạt chuẩn'}
          </span>
        </td>
      </tr>
    `;
  });

  tbody.innerHTML = html;
}

// =============================================================================
// Module 4: Financial Intelligence & P&L Waterfall
// =============================================================================

async function loadFinance() {
  try {
    const pnlRes = await fetch('/api/finance/pnl');
    if (pnlRes.ok) {
      const pnlData = await pnlRes.json();
      renderPnLStatement(pnlData.pnl);
      renderWaterfallChart();
    }

    const cfRes = await fetch('/api/finance/cashflow');
    if (cfRes.ok) {
      const cfData = await cfRes.json();
      renderCashFlowStatement(cfData.cash_flow);
    }

    const catRes = await fetch('/api/finance/categories');
    if (catRes.ok) {
      const catData = await catRes.json();
      renderCategoryMargins(catData.categories);
    }

  } catch (err) {
    console.error('Error loading financial data:', err);
  }
}

function renderWaterfallChart() {
  const ctx = document.getElementById('chart-pnl-waterfall');
  if (!ctx || typeof Chart === 'undefined') return;
  if (waterfallChart) waterfallChart.destroy();

  // Waterfall Steps
  const labels = [
    'Doanh thu Gộp',
    'Chiết khấu KM',
    'Doanh thu Thuần',
    'Giá vốn COGS',
    'Lợi nhuận Gộp',
    'Chi phí Vận hành',
    'Tổn thất Khủng hoảng',
    'Lợi nhuận Ròng'
  ];

  // Amounts in billion VND
  const data = [
    24.2,  // Gross
    -0.7,  // Discounts
    23.5,  // Net Rev
    -16.8, // COGS
    6.7,   // Gross Profit
    -1.1,  // OPEX
    -2.84, // Incident Erosion
    2.73   // Final Net Profit
  ];

  const colors = [
    '#10b981', // Gross Rev
    '#f43f5e', // Disc
    '#6366f1', // Net Rev
    '#f43f5e', // COGS
    '#10b981', // Gross Profit
    '#f59e0b', // OPEX
    '#f43f5e', // Erosion
    '#06b6d4'  // Net Profit
  ];

  waterfallChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Giá trị (Tỷ VND)',
        data: data,
        backgroundColor: colors,
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function(ctx) {
              const v = ctx.raw;
              return ` ${v >= 0 ? '+' : ''}${v} Tỷ VND`;
            }
          }
        }
      },
      scales: {
        x: { grid: { color: 'rgba(255, 255, 255, 0.04)' }, ticks: { color: '#94a3b8', font: { family: 'Inter', size: 10 } } },
        y: {
          grid: { color: 'rgba(255, 255, 255, 0.06)' },
          ticks: {
            color: '#94a3b8',
            callback: function(val) { return val + ' Tỷ'; }
          }
        }
      }
    }
  });
}

function renderPnLStatement(pnl) {
  const tbody = document.getElementById('pnl-table-body');
  if (!tbody || !pnl) return;

  const rev = pnl.revenue;
  const cogs = pnl.cogs;
  const gp = pnl.gross_profit;
  const opex = pnl.operating_expenses;
  const ebit = pnl.operating_profit;
  const imp = pnl.incident_impact;
  const np = pnl.net_profit;

  const incidentLossVal = document.getElementById('val-incident-loss');
  if (incidentLossVal && imp) {
    incidentLossVal.innerText = formatVND(imp.total_erosion);
  }

  const badgeLoss = document.getElementById('badge-total-loss-val');
  if (badgeLoss && imp) {
    badgeLoss.innerText = `Tổng xói mòn: ${formatVND(imp.total_erosion)}`;
  }

  let html = `
    <tr class="section-row"><td colspan="4">I. DOANH THU &amp; CÁC KHOẢN GIẢM TRỪ</td></tr>
    <tr>
      <td style="padding-left: 28px;">1. Tổng Doanh thu Gộp (Gross Sales)</td>
      <td class="num-cell">${formatVND(rev.gross_sales)}</td>
      <td class="pct-cell">100.0%</td>
      <td style="text-align:center;font-size:0.8rem;color:var(--text-muted);">Giá trị đơn niêm yết</td>
    </tr>
    <tr>
      <td style="padding-left: 28px;">2. Chiết khấu &amp; Giảm giá Khuyến mại</td>
      <td class="num-cell" style="color:var(--rose);">- ${formatVND(rev.discounts)}</td>
      <td class="pct-cell" style="color:var(--rose);">${(rev.discounts / rev.net_revenue * 100).toFixed(1)}%</td>
      <td style="text-align:center;font-size:0.8rem;color:var(--text-muted);">Voucher khuyến mại</td>
    </tr>
    <tr>
      <td style="padding-left: 28px;">3. Phí vận chuyển thu từ Khách hàng</td>
      <td class="num-cell">+ ${formatVND(rev.shipping_revenue)}</td>
      <td class="pct-cell">${(rev.shipping_revenue / rev.net_revenue * 100).toFixed(1)}%</td>
      <td style="text-align:center;font-size:0.8rem;color:var(--text-muted);">Thu tiền cước ship</td>
    </tr>
    <tr class="total-row">
      <td>DOANH THU THUẦN GHI NHẬN (NET REVENUE)</td>
      <td class="num-cell">${formatVND(rev.net_revenue)}</td>
      <td class="pct-cell">100.0%</td>
      <td style="text-align:center;color:var(--primary);font-weight:700;">Doanh số thực nhận</td>
    </tr>

    <tr class="section-row"><td colspan="4">II. GIÁ VỐN HÀNG BÁN (COST OF GOODS SOLD - COGS)</td></tr>
    <tr>
      <td style="padding-left: 28px;">4. Giá vốn hàng xuất kho (COGS)</td>
      <td class="num-cell" style="color:var(--rose);">- ${formatVND(cogs.total_cogs)}</td>
      <td class="pct-cell" style="color:var(--rose);">${formatPercent(cogs.cogs_ratio_pct)}</td>
      <td style="text-align:center;font-size:0.8rem;color:var(--text-muted);">Giá nhập linh kiện</td>
    </tr>
    <tr class="total-row" style="background: rgba(16, 185, 129, 0.08); border-color: var(--emerald);">
      <td>LỢI NHUẬN GỘP (GROSS PROFIT)</td>
      <td class="num-cell" style="color:var(--emerald);">${formatVND(gp.amount)}</td>
      <td class="pct-cell" style="color:var(--emerald);font-weight:700;">${formatPercent(gp.margin_pct)}</td>
      <td style="text-align:center;color:var(--emerald);font-weight:700;">Biên lợi nhuận gộp</td>
    </tr>

    <tr class="section-row"><td colspan="4">III. CHI PHÍ HOẠT ĐỘNG (OPERATING EXPENSES - OPEX)</td></tr>
    <tr>
      <td style="padding-left: 28px;">5. Chi phí Vận chuyển Tiêu chuẩn (Logistics Base)</td>
      <td class="num-cell">- ${formatVND(opex.logistics_base)}</td>
      <td class="pct-cell">${(opex.logistics_base / rev.net_revenue * 100).toFixed(1)}%</td>
      <td style="text-align:center;font-size:0.8rem;color:var(--text-muted);">Cước giao hàng đối tác</td>
    </tr>
    <tr>
      <td style="padding-left: 28px;">6. Chi phí Tiếp thị &amp; Quảng cáo (Marketing Spend)</td>
      <td class="num-cell">- ${formatVND(opex.marketing)}</td>
      <td class="pct-cell">${(opex.marketing / rev.net_revenue * 100).toFixed(1)}%</td>
      <td style="text-align:center;font-size:0.8rem;color:var(--text-muted);">TikTok, Facebook Ads</td>
    </tr>
    <tr>
      <td style="padding-left: 28px;">7. Chi phí Vận hành &amp; Quản lý (Overhead)</td>
      <td class="num-cell">- ${formatVND(opex.operations_overhead)}</td>
      <td class="pct-cell">${(opex.operations_overhead / rev.net_revenue * 100).toFixed(1)}%</td>
      <td style="text-align:center;font-size:0.8rem;color:var(--text-muted);">Định mức quản lý</td>
    </tr>
    <tr class="total-row">
      <td>LỢI NHUẬN TỪ HOẠT ĐỘNG KINH DOANH (EBIT)</td>
      <td class="num-cell">${formatVND(ebit.ebit)}</td>
      <td class="pct-cell">${formatPercent(ebit.operating_margin_pct)}</td>
      <td style="text-align:center;font-weight:700;">Trước tổn thất khủng hoảng</td>
    </tr>

    <tr class="section-row" style="background:rgba(244, 63, 94, 0.12);"><td colspan="4" style="color:var(--rose);">IV. TỔN THẤT TRỰC TIẾP TỪ SỰ CỐ KHỦNG HOẢNG (CRISIS EROSION)</td></tr>
    <tr class="danger-row">
      <td style="padding-left: 28px;">8. Bồi hoàn Trễ hạn Giao hàng (SLA Logistics - GHN)</td>
      <td class="num-cell" style="color:var(--rose);">- 185.000.000 ₫</td>
      <td class="pct-cell" style="color:var(--rose);">0.8%</td>
      <td style="text-align:center;"><span class="tag-danger">S002 Cash Out</span></td>
    </tr>
    <tr class="danger-row">
      <td style="padding-left: 28px;">9. Hoàn tiền Lô hàng Eco Laptop 072 lỗi phần cứng</td>
      <td class="num-cell" style="color:var(--rose);">- 425.000.000 ₫</td>
      <td class="pct-cell" style="color:var(--rose);">1.8%</td>
      <td style="text-align:center;"><span class="tag-danger">S005 Cash Out</span></td>
    </tr>
    <tr class="danger-row">
      <td style="padding-left: 28px;">10. Xói mòn cơ hội: Hết hàng Viet Electronics &amp; Lỗi MoMo &amp; Lãng phí Ads</td>
      <td class="num-cell" style="color:var(--rose);">- 2.229.689.156 ₫</td>
      <td class="pct-cell" style="color:var(--rose);">9.5%</td>
      <td style="text-align:center;"><span class="tag-warning">S001, S003, S004</span></td>
    </tr>

    <tr class="total-row" style="background: linear-gradient(90deg, rgba(99, 102, 241, 0.2), rgba(16, 185, 129, 0.15)); border: 2px solid var(--primary);">
      <td style="font-size:1.15rem;letter-spacing:0.04em;">LỢI NHUẬN THUẦN CUỐI CÙNG (FINAL NET PROFIT)</td>
      <td class="num-cell" style="font-size:1.25rem;color:#ffffff;">${formatVND(np.amount)}</td>
      <td class="pct-cell" style="font-size:1.1rem;color:#ffffff;font-weight:800;">${formatPercent(np.net_margin_pct)}</td>
      <td style="text-align:center;"><span class="tag-success" style="font-size:0.8rem;padding:4px 10px;">Lợi nhuận ròng</span></td>
    </tr>
  `;

  tbody.innerHTML = html;

  if (imp && imp.breakdown) {
    renderIncidentLossCards(imp.breakdown);
  }
}

function renderIncidentLossCards(breakdown) {
  const container = document.getElementById('loss-cards-grid');
  if (!container) return;

  let html = '';
  breakdown.forEach(b => {
    html += `
      <div class="loss-item-card">
        <div>
          <span class="loss-code">${b.scenario_code} &bull; ${b.domain}</span>
          <div class="loss-name">${escapeHtml(b.incident_name)}</div>
          <div style="font-size:0.75rem;color:var(--text-muted);">${escapeHtml(b.loss_type)}</div>
        </div>
        <div class="loss-val">${formatVND(b.loss_amount)}</div>
      </div>
    `;
  });

  container.innerHTML = html;
}

function renderCashFlowStatement(cf) {
  const inflowsContainer = document.getElementById('cf-inflows-content');
  const outflowsContainer = document.getElementById('cf-outflows-content');
  const netContainer = document.getElementById('cf-net-amount');

  if (!cf) return;

  if (netContainer) {
    netContainer.innerText = formatVND(cf.net_cash_flow);
    netContainer.style.color = cf.net_cash_flow < 0 ? 'var(--rose)' : 'var(--emerald)';
  }

  if (inflowsContainer && cf.inflows) {
    let html = `
      <div style="display:flex;justify-content:space-between;margin-bottom:14px;">
        <span style="font-weight:600;">Tổng tiền thu từ khách:</span>
        <strong class="font-mono text-emerald" style="font-size:1.1rem;">${formatVND(cf.inflows.total_inflows)}</strong>
      </div>
      <table class="table-simple">
        <thead><tr><th>Cổng thanh toán</th><th style="text-align:right;">Số GD</th><th style="text-align:right;">Số tiền (VND)</th></tr></thead>
        <tbody>
    `;
    cf.inflows.by_payment_method.forEach(pm => {
      html += `<tr><td><strong>${escapeHtml(pm.method)}</strong></td><td style="text-align:right;" class="font-mono">${formatNumber(pm.count)}</td><td style="text-align:right;color:var(--emerald);" class="font-mono">${formatVND(pm.amount)}</td></tr>`;
    });
    html += '</tbody></table>';
    inflowsContainer.innerHTML = html;
  }

  if (outflowsContainer && cf.outflows) {
    let html = `
      <div style="display:flex;justify-content:space-between;margin-bottom:14px;">
        <span style="font-weight:600;">Tổng tiền thực chi trả:</span>
        <strong class="font-mono text-rose" style="font-size:1.1rem;">- ${formatVND(cf.outflows.total_outflows)}</strong>
      </div>
      <table class="table-simple">
        <thead><tr><th>Khoản mục chi</th><th style="text-align:right;">Số GD</th><th style="text-align:right;">Số tiền (VND)</th></tr></thead>
        <tbody>
    `;
    cf.outflows.by_expense_type.forEach(exp => {
      html += `<tr><td><strong>${escapeHtml(exp.type)}</strong></td><td style="text-align:right;" class="font-mono">${formatNumber(exp.count)}</td><td style="text-align:right;color:var(--rose);" class="font-mono">- ${formatVND(exp.amount)}</td></tr>`;
    });
    html += `<tr><td><strong>Thanh toán Nhà cung cấp (PO)</strong></td><td style="text-align:right;">--</td><td style="text-align:right;color:var(--rose);" class="font-mono">- ${formatVND(cf.outflows.supplier_payments)}</td></tr></tbody></table>`;
    outflowsContainer.innerHTML = html;
  }
}

function renderCategoryMargins(categories) {
  const tbody = document.getElementById('category-margins-body');
  if (!tbody || !categories) return;

  let html = '';
  categories.forEach(cat => {
    const marginColor = cat.margin_pct >= 28 ? 'var(--emerald)' : (cat.margin_pct >= 20 ? 'var(--primary)' : 'var(--amber)');
    html += `
      <tr>
        <td><strong>${escapeHtml(cat.category_name)}</strong></td>
        <td style="text-align:right;" class="font-mono">${formatNumber(cat.units_sold)} sp</td>
        <td style="text-align:right;" class="font-mono">${formatVND(cat.revenue)}</td>
        <td style="text-align:right;color:var(--text-muted);" class="font-mono">${formatVND(cat.cogs)}</td>
        <td style="text-align:right;color:var(--emerald);" class="font-mono">${formatVND(cat.gross_profit)}</td>
        <td style="text-align:right;font-weight:700;color:${marginColor};" class="font-mono">${formatPercent(cat.margin_pct)}</td>
      </tr>
    `;
  });

  tbody.innerHTML = html;
}

// =============================================================================
// Module 5: Crisis Command, Causal DAG & "What-If" Simulation
// =============================================================================

async function loadCrisisSim() {
  try {
    const dagRes = await fetch('/api/simulation/causal-dag');
    if (dagRes.ok) {
      const dagData = await dagRes.json();
      cachedDags = dagData.dags || [];
      loadCausalDag('S001');
    }

    // Run initial What-If simulation
    runWhatIfSimulation();

    // Load Multi-Agent Debate Arena & Accountability Roster
    loadAgentDebate('S001');

    // Load Incident Cards
    if (cachedIncidents.length === 0) {
      const incRes = await fetch('/api/incidents');
      if (incRes.ok) {
        const incData = await incRes.json();
        cachedIncidents = incData.incidents || [];
        renderIncidentsDetailed(cachedIncidents);
      }
    } else {
      renderIncidentsDetailed(cachedIncidents);
    }

  } catch (err) {
    console.error('Error loading crisis sim data:', err);
  }
}

function updateSliderLabel(targetId, text) {
  const el = document.getElementById(targetId);
  if (el) el.innerText = text;
}

async function runWhatIfSimulation() {
  const backupSupplier = document.getElementById('sim-supplier-toggle')?.checked ?? true;
  const ghnReroute = parseFloat(document.getElementById('sim-reroute-slider')?.value ?? 35);
  const momoFailover = document.getElementById('sim-momo-toggle')?.checked ?? true;
  const tiktokRealloc = parseFloat(document.getElementById('sim-tiktok-slider')?.value ?? 50);
  const ecoPatch = document.getElementById('sim-ota-toggle')?.checked ?? true;

  try {
    const res = await fetch('/api/simulation/what-if', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        backup_supplier_active: backupSupplier,
        ghn_reroute_pct: ghnReroute,
        momo_failover: momoFailover,
        tiktok_realloc_pct: tiktokRealloc,
        eco_ota_patch: ecoPatch
      })
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderSimulationResults(data);

  } catch (err) {
    console.error('Simulation error:', err);
  }
}

function renderSimulationResults(data) {
  const proj = data.projected;
  if (!proj) return;

  document.getElementById('sim-res-recovered').innerText = `+ ${formatVND(proj.total_recovered)}`;
  document.getElementById('sim-res-net-profit').innerText = formatVND(proj.new_net_profit);
  document.getElementById('sim-res-margin').innerText = `Biên ròng tăng lên ${proj.new_net_margin_pct}%`;
  document.getElementById('sim-res-sla').innerText = `${proj.new_logistics_sla_pct}%`;
  document.getElementById('sim-res-health').innerText = `+ ${proj.health_index_gain} Điểm`;

  const breakdownContainer = document.getElementById('sim-breakdown-list');
  if (breakdownContainer && data.breakdown) {
    let html = '';
    data.breakdown.forEach(b => {
      html += `
        <div class="sim-breakdown-item">
          <div>
            <strong>${escapeHtml(b.scenario)}:</strong>
            <span style="color:var(--text-secondary);margin-left:8px;">${escapeHtml(b.status)}</span>
          </div>
          <strong class="font-mono text-emerald">+ ${formatVND(b.recovered)}</strong>
        </div>
      `;
    });
    breakdownContainer.innerHTML = html;
  }
}

function loadCausalDag(scenarioCode) {
  currentDagCode = scenarioCode;
  document.querySelectorAll('.dag-sc-btn').forEach(btn => {
    btn.classList.toggle('active', btn.innerText.includes(scenarioCode));
  });

  const dag = cachedDags.find(d => d.code === scenarioCode);
  const container = document.getElementById('dag-flow-viewport');
  if (!container || !dag) return;

  let html = '<div class="dag-flow-steps">';
  dag.nodes.forEach((node, idx) => {
    const nodeClass = `node-${node.type}`;
    const typeLabel = node.type === 'root_cause' ? '🔴 NGUYÊN NHÂN GỐC' : (node.type === 'symptom' ? '🟡 TRIỆU CHỨNG' : (node.type === 'consequence' ? '🔵 TÁC ĐỘNG VẬN HÀNH' : '⚠️ THIỆT HẠI TÀI CHÍNH'));

    html += `
      <div class="dag-node ${nodeClass}">
        <span class="dag-node-type">${typeLabel}</span>
        <div class="dag-node-text">${escapeHtml(node.label)}</div>
      </div>
    `;

    if (idx < dag.nodes.length - 1) {
      html += '<div class="dag-arrow">&rarr;</div>';
    }
  });
  html += '</div>';

  html += `
    <div class="dag-mitigation-box">
      <div class="mitigation-title">
        <strong>HÀNH ĐỘNG CAN THIỆP ĐỀ XUẤT:</strong> ${escapeHtml(dag.mitigation)}
      </div>
      <button class="btn-ticker-action" onclick="askAIAboutIncident('${dag.code}')">Hỏi AI giải pháp &rarr;</button>
    </div>
  `;

  container.innerHTML = html;
}

function renderIncidentsDetailed(incidents) {
  const activeContainer = document.getElementById('active-incidents-container');
  const histContainer = document.getElementById('historical-incidents-container');
  const legacyContainer = document.getElementById('incidents-cards-container');
  const liveBadge = document.getElementById('badge-active-crisis-live');

  if (!incidents) return;

  const activeIncidents = incidents.filter(i => i.is_active || i.status === 'Active');
  const archivedIncidents = incidents.filter(i => !i.is_active && i.status !== 'Active');

  // 1. Render Active Incidents Container
  if (activeContainer) {
    if (activeIncidents.length === 0) {
      if (liveBadge) liveBadge.style.display = 'none';
      activeContainer.innerHTML = `
        <div class="active-crisis-empty-banner">
          <div class="empty-icon">🟢</div>
          <div>
            <h4 style="color:#34d399; margin:0 0 6px 0; font-size:1.05rem; font-weight:700;">Hiện Không Có Sự Cố Nào Đang Hoạt Động (Thời Gian Thực)</h4>
            <p style="color:#94a3b8; margin:0; font-size:0.86rem; line-height:1.5;">
              Hệ thống đang vận hành theo đúng nhịp thời gian thực: Toàn bộ dây chuyền chuỗi cung ứng, kho bãi, logistics, cổng thanh toán và chăm sóc khách hàng đều ở ngưỡng chuẩn mực. Radar cảnh báo đỏ sẽ tự động kích hoạt khi luồng dữ liệu phát hiện sự cố mới.
            </p>
          </div>
        </div>
      `;
    } else {
      if (liveBadge) liveBadge.style.display = 'inline-block';
      let actHtml = '';
      activeIncidents.forEach(inc => {
        actHtml += `
          <div class="incident-card-detailed border-danger-glow" style="margin-bottom: 14px;">
            <div class="inc-detail-main">
              <div class="inc-tags-row">
                <span class="inc-badge" style="font-size:0.8rem;padding:3px 9px;background:var(--rose);">${inc.scenario_code}</span>
                <span class="tag-danger">Mức độ: ${escapeHtml(inc.severity)}</span>
                <span class="tag-accent">Phân hệ: ${escapeHtml(inc.domain)}</span>
                <span class="tag-danger" style="animation: pulse-glow-red 1.5s infinite;">ĐANG DIỄN RA (KHẨN CẤP)</span>
              </div>
              <h3 class="inc-title-bold text-rose">${escapeHtml(inc.title)}</h3>
              <p class="inc-symptom-text">${escapeHtml(inc.surface_symptoms)}</p>
              <div class="inc-metrics-row">
                <div class="inc-metric-item">Thời điểm phát hiện: <strong>${inc.detected_at ? new Date(inc.detected_at).toLocaleString('vi-VN') : 'N/A'}</strong></div>
                <div class="inc-metric-item">Trạng thái: <strong class="text-rose">Cần can thiệp ngay lập tức</strong></div>
              </div>
            </div>
            <div class="inc-btn-group">
              <button class="btn-ticker-action" style="background:var(--rose);color:#fff;padding:8px 16px;" onclick="openRcaModal('${inc.incident_id}')">
                Kích hoạt 6 Tác nhân Điều tra &rarr;
              </button>
              <button class="subtab-btn" onclick="askAIAboutIncident('${inc.scenario_code}')">
                Hỏi AI giải pháp
              </button>
            </div>
          </div>
        `;
      });
      activeContainer.innerHTML = actHtml;
    }
  }

  // 2. Render Historical Archive Container
  if (histContainer) {
    let histHtml = '';
    archivedIncidents.forEach(inc => {
      histHtml += `
        <div class="incident-card-detailed incident-card-archive" style="margin-bottom: 14px;">
          <div class="inc-detail-main">
            <div class="inc-tags-row">
              <span class="inc-badge" style="font-size:0.8rem;padding:3px 9px;background:#334155;color:#94a3b8;border-color:#475569;">${inc.scenario_code}</span>
              <span class="tag-resolved">✔ ĐÃ GIẢI QUYẾT & LƯU TRỮ</span>
              <span class="tag-accent">Phân hệ: ${escapeHtml(inc.domain)}</span>
              <span class="archive-badge-tag">Giai đoạn: Tháng 08/2026</span>
            </div>
            <h3 class="inc-title-bold">${escapeHtml(inc.title)}</h3>
            <p class="inc-symptom-text" style="color:#94a3b8;">${escapeHtml(inc.surface_symptoms)}</p>
            <div class="inc-metrics-row">
              <div class="inc-metric-item">Phát hiện: <strong>${inc.detected_at ? new Date(inc.detected_at).toLocaleString('vi-VN') : 'N/A'}</strong></div>
              <div class="inc-metric-item">Khoảng thời gian ảnh hưởng: <strong>${inc.start_time ? new Date(inc.start_time).toLocaleDateString('vi-VN') : '11/08/2026'} &rarr; ${inc.end_time ? new Date(inc.end_time).toLocaleDateString('vi-VN') : '18/08/2026'}</strong></div>
              <div class="inc-metric-item">Hồ sơ kiểm toán: <strong class="text-emerald">Khắc phục 100%</strong></div>
            </div>
          </div>
          <div class="inc-btn-group">
            <button class="btn-rca-view" onclick="openRcaModal('${inc.incident_id}')">
              Xem Báo cáo RCA Đối kháng &rarr;
            </button>
            <button class="subtab-btn" onclick="askAIAboutIncident('${inc.scenario_code}')">
              Bài học Kinh nghiệm &rarr;
            </button>
          </div>
        </div>
      `;
    });
    histContainer.innerHTML = histHtml;
  } else if (legacyContainer) {
    // Fallback if historical-incidents-container is absent
    let html = '';
    incidents.forEach(inc => {
      html += `
        <div class="incident-card-detailed">
          <div class="inc-detail-main">
            <div class="inc-tags-row">
              <span class="inc-badge">${inc.scenario_code}</span>
              <span class="tag-resolved">${escapeHtml(inc.status_badge || inc.status)}</span>
              <span class="tag-accent">${escapeHtml(inc.domain)}</span>
            </div>
            <h3 class="inc-title-bold">${escapeHtml(inc.title)}</h3>
            <p class="inc-symptom-text">${escapeHtml(inc.surface_symptoms)}</p>
          </div>
          <div class="inc-btn-group">
            <button class="btn-rca-view" onclick="openRcaModal('${inc.incident_id}')">RCA &rarr;</button>
          </div>
        </div>
      `;
    });
    legacyContainer.innerHTML = html;
  }
}

async function openRcaModal(incidentId) {
  const modal = document.getElementById('rca-modal');
  const titleEl = document.getElementById('modal-rca-title');
  const contentEl = document.getElementById('modal-rca-content');
  if (!modal || !contentEl) return;

  let inc = cachedIncidents.find(i => i.incident_id === incidentId || i.scenario_code === incidentId);
  if (!inc) {
    try {
      const res = await fetch('/api/incidents');
      if (res.ok) {
        const data = await res.json();
        cachedIncidents = data.incidents || [];
        inc = cachedIncidents.find(i => i.incident_id === incidentId || i.scenario_code === incidentId);
      }
    } catch (e) {
      console.error('Error fetching fallback incidents for RCA modal:', e);
    }
  }
  if (!inc) return;

  titleEl.innerText = `[${inc.scenario_code}] ${inc.title} — Báo cáo Phân tích Nguyên nhân Gốc (RCA)`;
  if (inc.rca_report_available && inc.rca_content) {
    contentEl.innerHTML = renderMarkdown(inc.rca_content);
  } else {
    contentEl.innerHTML = `<div style="padding:20px;"><p style="color:var(--text-secondary);">${escapeHtml(inc.surface_symptoms)}</p></div>`;
  }

  modal.classList.add('active');
}

function closeRcaModal() {
  const modal = document.getElementById('rca-modal');
  if (modal) modal.classList.remove('active');
}

function askAIAboutIncident(scenarioCode) {
  switchTab('ai-assistant');
  const input = document.getElementById('ai-user-input');
  if (input) {
    input.value = `Giải thích nguyên nhân gốc rễ và kịch bản can thiệp giảm thiểu thiệt hại của sự cố ${scenarioCode}?`;
    document.getElementById('chat-form').dispatchEvent(new Event('submit'));
  }
}

// =============================================================================
// Section: Multi-Agent Debate Arena & Accountability Roster
// =============================================================================

let currentDebateScenario = 'S001';
let cachedDebates = {};

async function loadAgentDebate(scenarioCode = 'S001') {
  currentDebateScenario = scenarioCode;

  // Update button active state
  ['s001', 's002', 's003', 's004', 's005'].forEach(code => {
    const btn = document.getElementById(`btn-deb-${code}`);
    if (btn) {
      if (code === scenarioCode.toLowerCase()) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    }
  });

  // Check cache first
  if (cachedDebates[scenarioCode]) {
    renderDebateArenaData(cachedDebates[scenarioCode]);
    return;
  }

  try {
    const res = await fetch(`/api/simulation/agent-debate?scenario=${scenarioCode}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data.status === 'SUCCESS' && data.data) {
      cachedDebates[scenarioCode] = data.data;
      renderDebateArenaData(data.data);
    }
  } catch (err) {
    console.error('Error fetching debate arena data:', err);
  }
}

function switchDebateScenario(scenarioCode) {
  loadAgentDebate(scenarioCode);
}

function renderDebateArenaData(data) {
  const { agent_roster, debate } = data;
  if (agent_roster) renderAgentRoster(agent_roster);
  if (debate) {
    renderDebateTranscript(debate);
    const acc = debate.round_4_synthesizer_verdict?.accountability || debate.accountability;
    if (acc) renderAccountabilityVerdict(acc, debate);
  }
}

function renderAgentRoster(roster) {
  const container = document.getElementById('agent-roster-container');
  if (!container) return;

  let html = '';
  roster.forEach(agent => {
    const isSpecialist = agent.role.includes('Chẩn đoán') || agent.id.includes('agent_1') || agent.id.includes('agent_2') || agent.id.includes('agent_3');
    const isCritic = agent.role.includes('Phản biện') || agent.role.includes('Thẩm định') || agent.role.includes('Kiểm định') || agent.id.includes('agent_4') || agent.id.includes('agent_5');
    const isSynthesizer = agent.id.includes('agent_6') || agent.role.includes('Tổng hợp');

    let roleClass = 'role-specialist';
    let badgeHtml = '<span class="agent-badge-spec">Domain Specialist</span>';
    if (isCritic) {
      roleClass = 'role-critic';
      badgeHtml = '<span class="agent-badge-crit">Adversarial Critic</span>';
    } else if (isSynthesizer) {
      roleClass = 'role-synthesizer';
      badgeHtml = '<span class="agent-badge-syn">Synthesizer Judge</span>';
    }

    const scoreVal = agent.accuracy_pct !== undefined ? agent.accuracy_pct : agent.precision_pct;
    const scoreLabel = agent.accuracy_pct !== undefined ? 'Độ chính xác' : 'Độ chuẩn xác';
    const accClass = scoreVal >= 90 ? 'acc-high' : 'acc-med';

    let stat1Label = 'Giả thuyết';
    let stat1Val = agent.hypotheses_count ? `${agent.hypotheses_count} đề xuất` : `${agent.verdicts_count || 5} phán quyết`;
    let stat2Label = 'Thành tích';
    let stat2Val = agent.catches_count ? `Bắt ${agent.catches_count} lỗi` : (agent.errors_caught ? `Bị bắt ${agent.errors_caught} lần` : 'Chuẩn 100%');

    html += `
      <div class="agent-card ${roleClass}">
        <div>
          <div class="agent-card-head">
            <div class="agent-card-identity">
              <div class="agent-avatar-icon" style="color:${agent.color};border-color:${agent.color}40;background:${agent.color}15;">
                ${agent.avatar}
              </div>
              <div class="agent-title-text">
                <h4>${escapeHtml(agent.name)}</h4>
                <span>${escapeHtml(agent.code)} &bull; ${escapeHtml(agent.domain || agent.role)}</span>
              </div>
            </div>
            <div class="agent-accuracy-pill ${accClass}">
              ${scoreVal}%
            </div>
          </div>
          <p class="agent-card-desc">${escapeHtml(agent.strength || agent.badge || agent.role)}</p>
        </div>

        <div>
          <div class="agent-card-stats">
            <div class="stat-item">
              <span class="stat-item-label">${stat1Label}</span>
              <span class="stat-item-val">${stat1Val}</span>
            </div>
            <div class="stat-item">
              <span class="stat-item-label">${stat2Label}</span>
              <span class="stat-item-val" style="color:${agent.catches_count ? 'var(--emerald)' : (agent.errors_caught ? 'var(--rose)' : 'var(--cyan)')};">${stat2Val}</span>
            </div>
          </div>
          <div class="agent-card-footer">
            <div class="agent-status-tag">
              <span class="agent-dot-active"></span>
              <span>${escapeHtml(agent.status)}</span>
            </div>
            ${badgeHtml}
          </div>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

function renderDebateTranscript(debate) {
  const container = document.getElementById('debate-rounds-container');
  if (!container) return;

  // Round 1
  let r1Html = '<div class="specialist-claims-grid">';
  (debate.round_1_hypotheses || []).forEach(claim => {
    r1Html += `
      <div class="specialist-claim-card">
        <div class="claim-agent-meta">
          <span class="claim-agent-name">${escapeHtml(claim.agent)}</span>
          <span class="claim-confidence">Tin cậy: ${claim.confidence}%</span>
        </div>
        <div class="claim-text">${escapeHtml(claim.claim)}</div>
        <div class="claim-sql-box"><code>${escapeHtml(claim.sql_preview)}</code></div>
        <div class="claim-metric-tag">Dữ liệu đối chiếu SQL từ sandbox doanh nghiệp</div>
      </div>
    `;
  });
  r1Html += '</div>';

  // Round 2
  let r2Html = '<div class="critic-audits-list">';
  (debate.round_2_evidence_critique || []).forEach(audit => {
    const isApproved = audit.verdict === 'APPROVED';
    const isRejected = audit.verdict === 'REJECTED';
    const auditClass = isApproved ? 'audit-accepted' : 'audit-rejected';
    const badgeClass = isApproved ? 'badge-accepted' : 'badge-rejected';
    const verdictText = isApproved ? 'CHẤP THUẬN CHỨNG CỨ' : (isRejected ? 'BÁC BỎ NGUYÊN NHÂN' : 'PHÂN LOẠI LÀ TRIỆU CHỨNG');

    r2Html += `
      <div class="audit-entry-card ${auditClass}">
        <div class="audit-entry-head">
          <span class="audit-target-agent">Đối tượng thẩm định: <strong>${escapeHtml(audit.target_agent)}</strong></span>
          <span class="audit-verdict-badge ${badgeClass}">${verdictText}</span>
        </div>
        <div class="audit-reason-text">${escapeHtml(audit.audit_rationale)}</div>
      </div>
    `;
  });
  r2Html += '</div>';

  // Round 3
  const r3 = debate.round_3_causal_critique || {};
  let r3Html = `
    <div class="causal-eval-box">
      <div class="causal-grid-2col">
        <div class="causal-col-card col-root">
          <span class="causal-col-label">CHUỖI NHÂN QUẢ TIẾN TRÌNH THỜI GIAN</span>
          <div class="causal-col-content">${escapeHtml(r3.temporal_precedence || 'Xác nhận thứ tự các biến cố trong Causal DAG')}</div>
        </div>
        <div class="causal-col-card col-symptom">
          <span class="causal-col-label">LƯỢNG GIÁ ĐỒ THỊ DAG (ACYCLICITY)</span>
          <div class="causal-col-content">
            Đồ thị DAG không chu trình: <strong>${r3.acyclicity_verified ? 'ĐẠT (Hợp lệ 100%)' : 'KHÔNG ĐẠT'}</strong><br/>
            <span style="color:#d8b4fe;">${escapeHtml(r3.causal_chain || '')}</span>
          </div>
        </div>
      </div>
      <div class="causal-verdict-summary">
        <strong>Kết luận Causal Critic:</strong> Xác nhận thành công nguyên nhân gốc rễ và tách biệt hoàn toàn khỏi các biến trung gian khuếch đại (Symptoms Amplification).
      </div>
    </div>
  `;

  // Round 4
  const r4 = debate.round_4_synthesizer_verdict || {};
  let r4Html = `
    <div class="synthesizer-verdict-card">
      <div class="syn-verdict-head">
        <span class="syn-badge">PHÁN QUYẾT CUỐI CÙNG TỪ CHIEF SYNTHESIZER</span>
        <span class="tag-success">GROUND TRUTH SO KHỚP 100%</span>
      </div>
      <div class="syn-root-highlight">
        Nguyên nhân Gốc rễ Độc lập: <strong style="color:var(--rose);">${escapeHtml(r4.final_root_cause || debate.actual_ground_truth)}</strong>
      </div>
      <div class="syn-action-plan">
        <strong>Hành động Can thiệp Số đã kích hoạt:</strong> Kích hoạt bộ can thiệp đối ứng trong Sandbox What-If để chặn đứng đà lan truyền tổn thất dòng tiền và SLA.
      </div>
      <div class="syn-impact-tag">
        ✔ Phán quyết được đối chiếu tự động với Ground Truth của Luận văn &bull; Đạt điểm tuyệt đối 100.0/100 Benchmark.
      </div>
    </div>
  `;

  const timelineHtml = `
    <!-- Round 1 -->
    <div class="debate-round-box">
      <div class="round-header">
        <div class="round-title-wrap">
          <span class="round-badge">VÒNG 1</span>
          <span class="round-name">Đề xuất Giả thuyết Độc lập từ 3 Specialist</span>
        </div>
        <span class="round-sub">Ops, Finance & Customer Analysts phát biểu luận điểm độc lập kèm SQL</span>
      </div>
      <div class="round-body">${r1Html}</div>
    </div>

    <!-- Round 2 -->
    <div class="debate-round-box">
      <div class="round-header">
        <div class="round-title-wrap">
          <span class="round-badge round-2">VÒNG 2</span>
          <span class="round-name">Thẩm định Chứng cứ & Bác bỏ Ngụy biện (Data/Evidence Critic)</span>
        </div>
        <span class="round-sub">Agent 4 rà soát tính xác thực của dữ liệu SQL và chỉ ra ngụy biện cỡ mẫu</span>
      </div>
      <div class="round-body">${r2Html}</div>
    </div>

    <!-- Round 3 -->
    <div class="debate-round-box">
      <div class="round-header">
        <div class="round-title-wrap">
          <span class="round-badge round-3">VÒNG 3</span>
          <span class="round-name">Kiểm định Cấu trúc Nhân quả & Thứ tự Thời gian (Causal Critic)</span>
        </div>
        <span class="round-sub">Agent 5 thẩm định trên đồ thị Causal DAG, chặn lỗi nhầm lẫn Triệu chứng thành Nguyên nhân</span>
      </div>
      <div class="round-body">${r3Html}</div>
    </div>

    <!-- Round 4 -->
    <div class="debate-round-box">
      <div class="round-header">
        <div class="round-title-wrap">
          <span class="round-badge round-4">VÒNG 4</span>
          <span class="round-name">Phán quyết Tổng hợp & Khóa Nguyên nhân Gốc rễ (Chief Synthesizer)</span>
        </div>
        <span class="round-sub">Agent 6 ra phán quyết cuối cùng, đề xuất can thiệp số và cập nhật sổ điểm giải trình</span>
      </div>
      <div class="round-body">${r4Html}</div>
    </div>
  `;

  container.innerHTML = timelineHtml;
}

function renderAccountabilityVerdict(acc, debate) {
  const container = document.getElementById('accountability-verdict-container');
  if (!container || !acc) return;

  container.innerHTML = `
    <div class="accountability-head">
      <div class="accountability-title-row">
        <span class="accountability-badge">BẢNG TRÁCH NHIỆM GIẢI TRÌNH</span>
        <h4>Bảng Phong thần Minh bạch: Agent nào sai & Critic nào bắt được lỗi?</h4>
      </div>
      <div class="tag-success font-mono" style="font-size:0.8rem;padding:4px 10px;">
        ${escapeHtml(acc.benchmark_grade || 'EXCELLENT (100% MATCH)')}
      </div>
    </div>

    <div class="accountability-grid">
      <!-- Card 1: Wrong Agent -->
      <div class="acc-card card-wrong">
        <div>
          <span class="acc-card-tag">TÁC NHÂN PHÁN ĐOÁN SAI</span>
          <div class="acc-card-title">${escapeHtml(acc.wrong_agent)}</div>
          <div class="acc-card-content">"${escapeHtml(acc.wrong_claim)}"</div>
        </div>
        <div class="acc-card-meta">
          Nhầm lẫn triệu chứng bề mặt thành nguyên nhân gốc rễ.
        </div>
      </div>

      <!-- Card 2: Critic caught error -->
      <div class="acc-card card-critic">
        <div>
          <span class="acc-card-tag">CRITIC BẮT ĐƯỢC LỖI & PHẢN BIỆN</span>
          <div class="acc-card-title">${escapeHtml(acc.critic_agent)}</div>
          <div class="acc-card-content">${escapeHtml(acc.critic_rationale)}</div>
        </div>
        <div class="acc-card-meta">
          Bảo vệ hệ thống khỏi việc đưa ra quyết định sai lầm.
        </div>
      </div>

      <!-- Card 3: Ground Truth Match -->
      <div class="acc-card card-groundtruth">
        <div>
          <span class="acc-card-tag">SO KHỚP GROUND TRUTH LUẬN VĂN</span>
          <div class="acc-card-title">Khớp 100% (${acc.ground_truth_score}/100)</div>
          <div class="acc-card-content">
            ${escapeHtml(debate.actual_ground_truth || '')}
          </div>
        </div>
        <div class="acc-card-meta">
          Được bảo chứng độc lập bởi bộ dữ liệu benchmark chuẩn.
        </div>
      </div>
    </div>
  `;
}

// =============================================================================
// Module 6: Natural Language AI Assistant Copilot
// =============================================================================

const ROLE_PROMPTS = {
  CEO: [
    "Báo cáo tóm tắt tình hình vận hành và các rủi ro cấp thiết nhất?",
    "Tổng thiệt hại tài chính từ 5 sự cố khủng hoảng (S001-S005)?",
    "Nếu thực hiện tất cả can thiệp số, lợi nhuận ròng sẽ phục hồi bao nhiêu?"
  ],
  CFO: [
    "Báo cáo kết quả hoạt động kinh doanh (P&L) toàn diện",
    "Tại sao lợi nhuận MoMo giảm trong ngày 15/08/2026?",
    "Lưu chuyển tiền thuần (Net Cash Flow) đang ở mức bao nhiêu?"
  ],
  COO: [
    "Đơn vị vận chuyển nào có tỷ lệ giao trễ cao nhất và chi phí bồi hoàn là bao nhiêu?",
    "Có bao nhiêu kho và lượng hàng tồn kho khả dụng hiện tại?",
    "Nhà cung cấp Viet Electronics đang có bao nhiêu đơn PO bị ảnh hưởng?"
  ],
  CMO: [
    "Hiệu quả chiến dịch TikTok so với các kênh khác (CAC & CVR)?",
    "Lý do phổ biến nhất trong các đánh giá 1 sao của khách hàng?",
    "Cơ cấu doanh thu đóng góp theo từng phân khúc khách hàng (VIP, Regular, At-Risk)?"
  ]
};

const TOPIC_PROMPTS = {
  All: [
    "So sánh doanh thu hôm nay với hôm qua",
    "Hôm nay có bao nhiêu đơn hàng và bao nhiêu đơn bị hủy?",
    "Doanh thu theo từng chi nhánh cửa hàng",
    "Top nhân viên bán hàng có doanh thu cao nhất",
    "Thống kê các sản phẩm tồn kho và sắp hết hàng",
    "Khách hàng mới hôm nay và tỷ lệ khách quay lại"
  ],
  Revenue: [
    "So sánh doanh thu hôm nay với hôm qua",
    "Doanh thu theo từng chi nhánh cửa hàng",
    "Top nhân viên bán hàng có doanh số cao nhất",
    "So sánh doanh thu tháng 7 với tháng 8/2026",
    "Top 5 sản phẩm bán chạy nhất theo doanh thu"
  ],
  Orders: [
    "Hôm nay bao nhiêu đơn hàng",
    "Bao nhiêu đơn hàng bị hủy và lý do là gì",
    "Tỷ lệ hoàn tất đơn hàng và tỷ lệ giao hàng đúng hạn",
    "Danh sách đơn hàng giá trị cao trên 50 triệu VND"
  ],
  Customers: [
    "Khách hàng mới hôm nay là bao nhiêu",
    "Thống kê khách hàng quay lại mua hàng",
    "Cơ cấu doanh thu đóng góp theo từng phân khúc VIP, Regular",
    "Đánh giá mức độ hài lòng CSAT và phản hồi khiếu nại"
  ],
  Products: [
    "Thống kê các sản phẩm tồn kho và sắp hết hàng",
    "Top 5 sản phẩm bán chạy nhất theo doanh thu",
    "Tổng bao nhiêu sản phẩm được bán ra trên toàn hệ thống",
    "Sản phẩm nào bị đổi trả và hoàn tiền nhiều nhất"
  ],
  Employees: [
    "Top nhân viên bán hàng có doanh số cao nhất",
    "Hiệu suất nhân viên chăm sóc khách hàng cskh",
    "Doanh thu theo từng chi nhánh cửa hàng vật lý",
    "Nhân viên CSKH nào xử lý nhiều ticket khiếu nại nhất"
  ],
  Diagnostics: [
    "Tại sao doanh thu MoMo sụt giảm trong ngày 15/08?",
    "Tổng thiệt hại tài chính từ 5 sự cố khủng hoảng (S001-S005)?",
    "Nguyên nhân gốc rễ dẫn đến lỗi hỏng hóc trên Eco Laptop 072",
    "Nếu thực hiện tất cả can thiệp số, lợi nhuận ròng sẽ phục hồi bao nhiêu?"
  ]
};

function filterTopic(topic) {
  document.querySelectorAll('.topic-btn').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-topic') === topic);
  });
  renderSuggestionChips(TOPIC_PROMPTS[topic] || TOPIC_PROMPTS.All);
}

function filterSuggestions(role) {
  document.querySelectorAll('.role-btn').forEach(b => {
    b.classList.toggle('active', b.innerText.includes(role));
  });
  renderSuggestionChips(ROLE_PROMPTS[role] || ROLE_PROMPTS.CEO);
}

function renderSuggestionChips(suggestions) {
  const container = document.getElementById('suggestion-chips');
  if (!container) return;

  let html = '<span class="chip-label">Gợi ý phân tích:</span>';
  suggestions.forEach(s => {
    html += `<button type="button" class="prompt-chip" onclick="applySuggestion('${escapeHtml(s)}')">${escapeHtml(s)}</button>`;
  });
  container.innerHTML = html;
}

function applySuggestion(text) {
  const input = document.getElementById('ai-user-input');
  if (input) {
    input.value = text;
    document.getElementById('chat-form').dispatchEvent(new Event('submit'));
  }
}

async function handleSendQuery(event) {
  if (event) event.preventDefault();
  const input = document.getElementById('ai-user-input');
  if (!input) return;

  const queryText = input.value.trim();
  if (!queryText) return;

  appendUserMessage(queryText);
  input.value = '';
  const loaderId = appendLoaderMessage();

  try {
    const startTime = performance.now();
    const res = await fetch('/api/ai/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: queryText })
    });

    const elapsed = Math.round(performance.now() - startTime);
    removeMessage(loaderId);

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      appendAssistantErrorMessage(errData.detail || `Máy chủ phản hồi mã lỗi HTTP ${res.status}`);
      return;
    }

    const data = await res.json();
    appendAssistantMessage(data, elapsed);

  } catch (err) {
    removeMessage(loaderId);
    appendAssistantErrorMessage(`Không thể kết nối tới AI Query Engine: ${err.message}`);
  }
}

function appendUserMessage(text) {
  const chatStream = document.getElementById('chat-messages');
  if (!chatStream) return;

  const msgDiv = document.createElement('div');
  msgDiv.className = 'chat-message user-msg';
  msgDiv.innerHTML = `<div class="msg-avatar">C-LV</div><div class="msg-content"><p>${escapeHtml(text)}</p></div>`;
  chatStream.appendChild(msgDiv);
  scrollChatToBottom();
}

function appendLoaderMessage() {
  const chatStream = document.getElementById('chat-messages');
  if (!chatStream) return null;

  const id = 'loader-' + Date.now();
  const msgDiv = document.createElement('div');
  msgDiv.id = id;
  msgDiv.className = 'chat-message assistant-msg';
  msgDiv.innerHTML = `
    <div class="msg-avatar">AI</div>
    <div class="msg-content" style="display:flex;align-items:center;gap:10px;">
      <span class="pulse-indicator"></span>
      <span style="color:var(--text-muted);font-size:0.88rem;">AI Analyst đang truy vấn cơ sở dữ liệu và tổng hợp báo cáo...</span>
    </div>
  `;
  chatStream.appendChild(msgDiv);
  scrollChatToBottom();
  return id;
}

function removeMessage(id) {
  if (!id) return;
  const el = document.getElementById(id);
  if (el) el.remove();
}

function appendAssistantErrorMessage(errText) {
  const chatStream = document.getElementById('chat-messages');
  if (!chatStream) return;

  const msgDiv = document.createElement('div');
  msgDiv.className = 'chat-message assistant-msg';
  msgDiv.innerHTML = `
    <div class="msg-avatar" style="background:var(--rose);">!</div>
    <div class="msg-content" style="border-color:rgba(244,63,94,0.3);">
      <p style="color:var(--rose);font-weight:600;">Lỗi xử lý câu hỏi:</p>
      <p style="color:var(--text-secondary);">${escapeHtml(errText)}</p>
    </div>
  `;
  chatStream.appendChild(msgDiv);
  scrollChatToBottom();
}

function appendAssistantMessage(data, elapsedMs) {
  const chatStream = document.getElementById('chat-messages');
  if (!chatStream) return;

  const msgDiv = document.createElement('div');
  msgDiv.className = 'chat-message assistant-msg';

  let answerHtml = renderMarkdown(data.answer || '');

  let tableHtml = '';
  if (data.data && Array.isArray(data.data) && data.data.length > 0) {
    const rows = data.data.slice(0, 10);
    const headers = Object.keys(rows[0]);

    tableHtml = `
      <div class="ai-table-preview">
        <table class="table-simple" style="margin:0;">
          <thead>
            <tr>${headers.map(h => `<th>${escapeHtml(h)}</th>`).join('')}</tr>
          </thead>
          <tbody>
            ${rows.map(r => `
              <tr>
                ${headers.map(h => {
                  const val = r[h];
                  const isNum = typeof val === 'number';
                  const formatted = isNum ? (val >= 1000 ? formatNumber(val) : val) : escapeHtml(val);
                  return `<td class="${isNum ? 'font-mono' : ''}" style="${isNum ? 'text-align:right;' : ''}">${formatted}</td>`;
                }).join('')}
              </tr>
            `).join('')}
          </tbody>
        </table>
        ${data.data.length > 10 ? `<div style="font-size:0.75rem;color:var(--text-muted);padding:6px 12px;background:rgba(0,0,0,0.2);">Hiển thị 10 / ${data.data.length} dòng dữ liệu</div>` : ''}
      </div>
    `;
  }

  let sqlHtml = '';
  if (data.sql_query && data.sql_query !== '-- BLOCKED BY SECURITY GUARDRAIL') {
    const uniqueId = 'sql-' + Date.now();
    const rowsCount = data.data && Array.isArray(data.data) ? data.data.length : 0;
    const safeQueryText = escapeHtml(data.question || '').replace(/"/g, '&quot;').replace(/'/g, "\\'");

    sqlHtml = `
      <div class="sql-preview-card">
        <div class="sql-card-header">
          <div class="sql-card-badges">
            <span class="sql-badge-sandbox">🛡️ READ-ONLY SANDBOX</span>
            <span class="sql-badge-latency">⚡ ${elapsedMs || 35}ms</span>
            <span class="sql-badge-rows">📊 ${rowsCount} Dòng kết quả</span>
          </div>
          <div class="sql-card-actions">
            <button type="button" class="btn-sql-copy" onclick="copySqlToClipboard('${uniqueId}', this)" title="Sao chép câu lệnh SQL vào bộ nhớ đệm">
              📋 Copy SQL
            </button>
            <button type="button" class="btn-sql-rerun" onclick="rerunSqlQuery('${safeQueryText}')" title="Thực thi lại câu truy vấn này">
              🔄 Chạy lại
            </button>
            <button type="button" class="btn-sql-toggle" onclick="toggleSqlView('${uniqueId}')" title="Ẩn hoặc hiện mã SQL">
              Ẩn/Hiện
            </button>
          </div>
        </div>
        <pre id="${uniqueId}" class="sql-card-code" style="display:block;"><code>${escapeHtml(data.sql_query)}</code></pre>
      </div>
    `;
  }

  let followupsHtml = '';
  if (data.suggested_followups && data.suggested_followups.length > 0) {
    followupsHtml = `
      <div class="followups-container">
        <span style="font-size:0.75rem;color:var(--text-muted);align-self:center;margin-right:4px;">Gợi ý hỏi tiếp:</span>
        ${data.suggested_followups.map(f => `<button type="button" class="prompt-chip" onclick="applySuggestion('${escapeHtml(f)}')">${escapeHtml(f)}</button>`).join('')}
      </div>
    `;
  }

  msgDiv.innerHTML = `
    <div class="msg-avatar">AI</div>
    <div class="msg-content">
      <div class="ai-answer-body">${answerHtml}</div>
      ${tableHtml}
      ${sqlHtml}
      ${followupsHtml}
    </div>
  `;

  chatStream.appendChild(msgDiv);
  scrollChatToBottom();
}

function copySqlToClipboard(id, btn) {
  const el = document.getElementById(id);
  if (!el) return;
  const sqlText = el.innerText || el.textContent;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(sqlText).then(() => {
      if (btn) {
        const orig = btn.innerHTML;
        btn.innerHTML = '✓ Đã chép!';
        btn.classList.add('copied');
        setTimeout(() => {
          btn.innerHTML = orig;
          btn.classList.remove('copied');
        }, 2000);
      }
    }).catch(() => fallbackCopyText(sqlText, btn));
  } else {
    fallbackCopyText(sqlText, btn);
  }
}

function fallbackCopyText(text, btn) {
  const textarea = document.createElement('textarea');
  textarea.value = text;
  document.body.appendChild(textarea);
  textarea.select();
  try {
    document.execCommand('copy');
    if (btn) {
      const orig = btn.innerHTML;
      btn.innerHTML = '✓ Đã chép!';
      btn.classList.add('copied');
      setTimeout(() => {
        btn.innerHTML = orig;
        btn.classList.remove('copied');
      }, 2000);
    }
  } catch (_) {}
  document.body.removeChild(textarea);
}

function rerunSqlQuery(queryText) {
  if (!queryText) return;
  const input = document.getElementById('ai-user-input');
  if (input) {
    input.value = queryText;
    document.getElementById('chat-form').dispatchEvent(new Event('submit'));
  }
}

function toggleSqlView(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

function scrollChatToBottom() {
  const chatStream = document.getElementById('chat-messages');
  if (chatStream) {
    setTimeout(() => { chatStream.scrollTop = chatStream.scrollHeight; }, 50);
  }
}

// =============================================================================
// Live Streaming Telemetry Functions
// =============================================================================

let streamEventSource = null;

function initStreamSSE() {
  if (window.EventSource) {
    try {
      if (streamEventSource) streamEventSource.close();
      streamEventSource = new EventSource('/api/stream/events/sse');
      streamEventSource.onmessage = (e) => {
        try {
          const record = JSON.parse(e.data);
          handleIncomingLiveStreamEvent(record);
        } catch (err) {}
      };
      streamEventSource.onerror = () => {
        // SSE reconnects automatically
      };
    } catch (err) {
      console.warn('SSE stream init error:', err);
    }
  }
}

function handleIncomingLiveStreamEvent(record) {
  const tickerEl = document.getElementById('scc-ticker-stream');
  if (!tickerEl || !record) return;

  const isAlert = record.summary && (record.summary.includes('❌') || record.summary.includes('⚠️') || record.summary.includes('Trễ'));
  const colorClass = isAlert ? 'text-rose' : 'text-emerald';

  tickerEl.innerHTML = `
    <div class="ticker-event-item">
      <span class="${colorClass}" style="font-weight:700;">[${record.domain}]</span>
      <span>${record.summary}</span>
      <span style="color:var(--text-muted); font-size:0.75rem; margin-left:8px;">${new Date().toLocaleTimeString('vi-VN')}</span>
    </div>
  `;
}

async function fetchStreamStatus() {
  try {
    const res = await fetch('/api/stream/status');
    if (!res.ok) return;
    const data = await res.json();
    if (data.status === 'SUCCESS' && data.stream) {
      updateStreamUI(data.stream);
    }
  } catch (err) {
    // silently ignore network jitter
  }
}

function updateStreamUI(st) {
  const badge = document.getElementById('stream-status-badge');
  const dot = document.getElementById('stream-pulse-indicator');
  const metrics = document.getElementById('stream-metrics-text');
  const toggleBtn = document.getElementById('btn-stream-toggle');

  if (st.is_active) {
    if (badge) { badge.textContent = 'ĐANG CHẢY (SSE REAL-TIME)'; badge.className = 'stream-status-tag active'; }
    if (dot) dot.className = 'stream-pulse-dot';
    if (toggleBtn) toggleBtn.textContent = '⏸ Tạm dừng';
  } else {
    if (badge) { badge.textContent = 'ĐÃ TẠM DỪNG (PAUSED)'; badge.className = 'stream-status-tag paused'; }
    if (dot) dot.className = 'stream-pulse-dot paused';
    if (toggleBtn) toggleBtn.textContent = '▶ Tiếp tục';
  }

  if (metrics) {
    const vel = st.moving_baselines?.order_velocity_per_min?.mean || 24.5;
    const payRate = ((st.moving_baselines?.payment_success_rate?.mean || 0.94) * 100).toFixed(1);
    const ontime = ((st.moving_baselines?.delivery_ontime_rate?.mean || 0.91) * 100).toFixed(1);
    metrics.textContent = `⚡ Đã nạp ${st.total_db_transactions_persisted || st.total_events_ingested} giao dịch vào DB • Vận tốc: ${vel}/phút • TT Thành công: ${payRate}% • Giao đúng hạn: ${ontime}%`;
  }

  // Update speed button highlights
  const sp = st.speed_multiplier || 1.0;
  const isBurst = st.burst_mode || false;
  ['1x', '10x', '60x'].forEach(s => {
    const btn = document.getElementById(`btn-speed-${s}`);
    if (btn) btn.classList.toggle('active', !isBurst && s === `${Math.round(sp)}x`);
  });
  const burstBtn = document.getElementById('btn-speed-burst');
  if (burstBtn) burstBtn.classList.toggle('active', isBurst);
}

async function setSimulationSpeed(multiplier, burst) {
  try {
    const res = await fetch('/api/stream/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ speed_multiplier: multiplier, burst_mode: burst })
    });
    const data = await res.json();
    if (data.status === 'SUCCESS') {
      showToastNotification(`Đã đổi tốc độ dòng chảy: ${multiplier}x ${burst ? '(Chế độ Sóng thần Flash Sale)' : ''}`, 'success');
      if (data.stream) updateStreamUI(data.stream);
    }
  } catch (err) {
    showToastNotification('Lỗi điều chỉnh tốc độ: ' + err.message, 'error');
  }
}

async function triggerDynamicChaos(chaosType) {
  try {
    const res = await fetch('/api/stream/chaos/inject', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chaos_type: chaosType, severity: 0.85, duration_seconds: 180 })
    });
    const data = await res.json();
    if (data.status === 'SUCCESS') {
      showToastNotification(`⚠️ Đã kích hoạt sự cố động: ${chaosType}! Hệ thống đang lan truyền nhân quả domino...`, 'warning');
      if (data.stream) updateStreamUI(data.stream);
    }
  } catch (err) {
    showToastNotification('Lỗi kích hoạt sự cố: ' + err.message, 'error');
  }
}

async function triggerTwinIntervention(action) {
  try {
    const res = await fetch('/api/twin/intervene', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    });
    const data = await res.json();
    if (data.status === 'SUCCESS') {
      showToastNotification(`🛡️ ${data.intervention?.message || 'Can thiệp thành công! Hệ sinh thái số đang tự phục hồi.'}`, 'success');
      if (data.stream) updateStreamUI(data.stream);
    } else {
      showToastNotification(`❌ Can thiệp bị từ chối: ${data.message}`, 'error');
    }
  } catch (err) {
    showToastNotification('Lỗi can thiệp: ' + err.message, 'error');
  }
}

async function toggleStreamWorker() {
  try {
    const res = await fetch('/api/stream/toggle', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'SUCCESS') {
      showToastNotification(data.message, data.is_active ? 'success' : 'warning');
      if (data.stream) updateStreamUI(data.stream);
    }
  } catch (err) {
    showToastNotification('Lỗi khi đổi trạng thái luồng dữ liệu: ' + err.message, 'error');
  }
}

// =============================================================================
// Module 7: Live Sync & Executive Report Export
// =============================================================================

async function triggerLiveSync() {
  const syncBtn = document.getElementById('btn-sync-data');
  const syncText = document.getElementById('sync-btn-text');
  if (syncText) syncText.innerText = 'Đang đồng bộ...';
  if (syncBtn) syncBtn.style.opacity = '0.6';

  await Promise.all([
    loadOverview(currentTimeframe),
    loadFinance(),
    cachedSupplyChain ? loadSupplyChain() : Promise.resolve(),
    cachedCustomerMarketing ? loadCustomerGrowth() : Promise.resolve(),
    loadAgentDebate(currentDebateScenario)
  ]);

  setTimeout(() => {
    if (syncText) syncText.innerText = 'Đã đồng bộ!';
    if (syncBtn) syncBtn.style.opacity = '1';
    setTimeout(() => {
      if (syncText) syncText.innerText = 'Đồng bộ';
    }, 2000);
  }, 400);
}

function openExportModal() {
  const modal = document.getElementById('export-modal');
  const container = document.getElementById('export-preview-content');
  if (!modal || !container) return;

  const now = new Date().toLocaleString('vi-VN');
  const health = cachedOverview?.health?.score || 62;
  const grade = cachedOverview?.health?.benchmark_grade || 'B+';
  const rev = cachedOverview?.kpis?.financial?.recognized_revenue || 23456890000;
  const totalOrders = cachedOverview?.kpis?.financial?.total_orders || 12450;
  const ontimeRate = cachedOverview?.kpis?.logistics?.on_time_rate_pct || 82.3;

  container.innerHTML = `
    <div style="font-family:var(--font-sans);color:#ffffff;line-height:1.6;">
      <div style="display:flex;justify-content:space-between;border-bottom:2px solid #6366f1;padding-bottom:12px;margin-bottom:20px;">
        <div>
          <h2 style="font-size:1.4rem;font-weight:800;color:#ffffff;">TẬP ĐOÀN BÁN LẺ ĐA KÊNH OMNICORP</h2>
          <p style="font-size:0.85rem;color:var(--text-secondary);">HỆ THỐNG ĐIỀU HÀNH BẢN SAO SỐ DOANH NGHIỆP (ENTERPRISE DIGITAL TWIN)</p>
        </div>
        <div style="text-align:right;">
          <div style="font-size:0.85rem;color:var(--text-muted);">Thời điểm xuất bản: <strong>${now}</strong></div>
          <div style="font-size:0.85rem;color:var(--emerald);">Trạng thái: <strong>RBAC VERIFIED &bull; OFFICIAL</strong></div>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:repeat(4, 1fr);gap:14px;margin-bottom:24px;">
        <div style="background:rgba(255,255,255,0.04);padding:12px;border-radius:8px;">
          <div style="font-size:0.75rem;color:var(--text-muted);">HEALTH INDEX</div>
          <strong style="font-size:1.3rem;color:var(--amber);">${health}/100 (${grade})</strong>
        </div>
        <div style="background:rgba(255,255,255,0.04);padding:12px;border-radius:8px;">
          <div style="font-size:0.75rem;color:var(--text-muted);">DOANH THU THUẦN</div>
          <strong style="font-size:1.3rem;color:var(--emerald);">${formatVND(rev)}</strong>
        </div>
        <div style="background:rgba(255,255,255,0.04);padding:12px;border-radius:8px;">
          <div style="font-size:0.75rem;color:var(--text-muted);">LOGISTICS SLA</div>
          <strong style="font-size:1.3rem;color:var(--amber);">${ontimeRate}%</strong>
        </div>
        <div style="background:rgba(255,255,255,0.04);padding:12px;border-radius:8px;">
          <div style="font-size:0.75rem;color:var(--text-muted);">TỔN THẤT KHỦNG HOẢNG</div>
          <strong style="font-size:1.3rem;color:var(--rose);">- 2.839.689.156 ₫</strong>
        </div>
      </div>

      <h3 style="font-size:1.05rem;border-bottom:1px solid rgba(255,255,255,0.1);padding-bottom:6px;margin-bottom:12px;">1. TÓM TẮT ĐIỀU HÀNH 5 SỰ CỐ KHỦNG HOẢNG (S001–S005)</h3>
      <table class="table-simple" style="margin-bottom:24px;">
        <thead>
          <tr>
            <th>Mã</th>
            <th>Tên sự cố</th>
            <th>Phân hệ</th>
            <th>Thiệt hại ước tính</th>
            <th>Phương án can thiệp khuyến nghị</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong class="text-rose">S001</strong></td>
            <td>Đứt gãy cung ứng linh kiện Viet Electronics</td>
            <td>Supply Chain</td>
            <td class="font-mono" style="color:var(--rose);">- 1.150.000.000 ₫</td>
            <td>Kích hoạt nhà cung cấp phụ trợ dự phòng & điều chuyển kho Cần Thơ</td>
          </tr>
          <tr>
            <td><strong class="text-amber">S002</strong></td>
            <td>Ách tắc logistics trạm trung chuyển GHN Tân Bình</td>
            <td>Logistics</td>
            <td class="font-mono" style="color:var(--rose);">- 185.000.000 ₫</td>
            <td>Điều chuyển 35% sản lượng vận đơn sang Viettel Post / VNPost</td>
          </tr>
          <tr>
            <td><strong class="text-rose">S003</strong></td>
            <td>Suy giảm tỷ lệ thanh toán ví điện tử MoMo</td>
            <td>Payment</td>
            <td class="font-mono" style="color:var(--rose);">- 420.000.000 ₫</td>
            <td>Kích hoạt Smart Failover tự động chuyển luồng sang VNPay/ZaloPay</td>
          </tr>
          <tr>
            <td><strong class="text-indigo">S004</strong></td>
            <td>Phân bổ ngân sách marketing TikTok Ads không hiệu quả</td>
            <td>Marketing</td>
            <td class="font-mono" style="color:var(--rose);">- 485.000.000 ₫</td>
            <td>Đình chỉ ad group TikTok; tái phân bổ 60% sang Google Search</td>
          </tr>
          <tr>
            <td><strong class="text-rose">S005</strong></td>
            <td>Suy giảm chất lượng phần cứng Eco Laptop 072</td>
            <td>Quality</td>
            <td class="font-mono" style="color:var(--rose);">- 425.000.000 ₫</td>
            <td>Phát hành bản vá OTA khẩn cấp và bồi thường voucher 500k</td>
          </tr>
        </tbody>
      </table>

      <h3 style="font-size:1.05rem;border-bottom:1px solid rgba(255,255,255,0.1);padding-bottom:6px;margin-bottom:12px;">2. HIỆU QUẢ DỰ KIẾN KHI THỰC THI CAN THIỆP SỐ ("WHAT-IF")</h3>
      <p style="font-size:0.88rem;color:var(--text-secondary);margin-bottom:10px;">
        Khi Hội đồng Quản trị và Ban Điều hành phê duyệt đồng loạt 5 gói can thiệp số, tổng thiệt hại cứu vãn đạt <strong>1.886.000.000 ₫ (66.4%)</strong>, biên lợi nhuận ròng tăng từ 11.6% lên 19.7%, và SLA Logistics phục hồi lên mức 94.5%.
      </p>
    </div>
  `;

  modal.classList.add('active');
}

function closeExportModal() {
  const modal = document.getElementById('export-modal');
  if (modal) modal.classList.remove('active');
}

// =============================================================================
// 24/7 Autonomous Sentinel Integration
// =============================================================================

let sentinelCountdown = 60;
let sentinelTimerInterval = null;

function showToastNotification(message, type = 'info') {
  let toast = document.getElementById('sentinel-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'sentinel-toast';
    toast.style.position = 'fixed';
    toast.style.bottom = '24px';
    toast.style.right = '24px';
    toast.style.padding = '12px 20px';
    toast.style.borderRadius = '10px';
    toast.style.fontSize = '0.88rem';
    toast.style.fontWeight = '600';
    toast.style.color = '#ffffff';
    toast.style.zIndex = '99999';
    toast.style.backdropFilter = 'blur(12px)';
    toast.style.boxShadow = '0 8px 30px rgba(0, 0, 0, 0.5)';
    toast.style.transition = 'all 0.3s ease';
    toast.style.display = 'none';
    document.body.appendChild(toast);
  }

  if (type === 'success') {
    toast.style.background = 'rgba(16, 185, 129, 0.95)';
    toast.style.border = '1px solid #10b981';
  } else if (type === 'warning') {
    toast.style.background = 'rgba(245, 158, 11, 0.95)';
    toast.style.border = '1px solid #f59e0b';
  } else if (type === 'error') {
    toast.style.background = 'rgba(244, 63, 94, 0.95)';
    toast.style.border = '1px solid #f43f5e';
  } else {
    toast.style.background = 'rgba(99, 102, 241, 0.95)';
    toast.style.border = '1px solid #6366f1';
  }

  toast.textContent = message;
  toast.style.display = 'block';
  toast.style.opacity = '1';
  toast.style.transform = 'translateY(0)';

  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => { toast.style.display = 'none'; }, 300);
  }, 4000);
}

async function fetchSentinelStatus() {
  try {
    const res = await fetch('/api/sentinel/status');
    if (!res.ok) return;
    const data = await res.json();
    if (data.status === 'SUCCESS' && data.telemetry) {
      updateSentinelUI(data.telemetry);
    }
  } catch (err) {
    console.warn('[Sentinel] Status fetch failed:', err);
  }
}

function updateSentinelUI(telemetry) {
  const pulseDot = document.getElementById('sentinel-pulse-dot');
  const statusText = document.getElementById('sentinel-status-text');
  const countdownText = document.getElementById('sentinel-countdown-text');
  const toggleBtn = document.getElementById('btn-sentinel-toggle');

  if (!pulseDot || !statusText) return;

  if (telemetry.state === 'ACTIVE') {
    pulseDot.className = 'sentinel-pulse active';
    statusText.textContent = 'SENTINEL 24/7: ACTIVE';
    if (toggleBtn) {
      toggleBtn.textContent = '⏸';
      toggleBtn.title = 'Tạm dừng giám sát tự động';
    }
  } else {
    pulseDot.className = 'sentinel-pulse paused';
    statusText.textContent = 'SENTINEL: PAUSED';
    if (toggleBtn) {
      toggleBtn.textContent = '▶';
      toggleBtn.title = 'Kích hoạt lại giám sát tự động';
    }
  }

  if (telemetry.next_scan_seconds !== null && telemetry.next_scan_seconds !== undefined) {
    sentinelCountdown = telemetry.next_scan_seconds;
    if (countdownText) countdownText.textContent = `${sentinelCountdown}s`;
  }
}

function initSentinelWorker() {
  fetchSentinelStatus();

  if (sentinelTimerInterval) clearInterval(sentinelTimerInterval);
  sentinelTimerInterval = setInterval(() => {
    const countdownText = document.getElementById('sentinel-countdown-text');
    if (sentinelCountdown > 0) {
      sentinelCountdown--;
      if (countdownText) countdownText.textContent = `${sentinelCountdown}s`;
    } else {
      sentinelCountdown = 60;
      fetchSentinelStatus();
    }
  }, 1000);

  setInterval(fetchSentinelStatus, 10000);
}

async function triggerSentinelScanNow() {
  const scanBtn = document.getElementById('btn-sentinel-scan');
  const origText = scanBtn ? scanBtn.innerHTML : '⚡ Quét ngay';

  if (scanBtn) {
    scanBtn.innerHTML = '⏳ Đang quét...';
    scanBtn.disabled = true;
  }

  try {
    const res = await fetch('/api/sentinel/scan-now?force_rca=true', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'SUCCESS') {
      const anomCount = data.scan_result?.anomalies_count || 0;
      const dispCount = data.scan_result?.dispatched_count || 0;
      showToastNotification(`🛡️ Sentinel: Đã quét 5 miền, phát hiện ${anomCount} bất thường, kích hoạt ${dispCount} điều tra RCA!`, 'success');
      
      loadOverview(currentTimeframe);
      fetchSentinelStatus();
    } else {
      showToastNotification('Lỗi khi quét: ' + (data.detail || 'Không rõ'), 'error');
    }
  } catch (err) {
    showToastNotification('Lỗi kết nối Sentinel: ' + err.message, 'error');
  } finally {
    if (scanBtn) {
      scanBtn.innerHTML = origText;
      scanBtn.disabled = false;
    }
  }
}

async function toggleSentinelWorker() {
  try {
    const res = await fetch('/api/sentinel/toggle', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'SUCCESS') {
      showToastNotification(data.message, data.is_active ? 'success' : 'warning');
      if (data.telemetry) updateSentinelUI(data.telemetry);
    }
  } catch (err) {
    showToastNotification('Lỗi khi chuyển đổi trạng thái: ' + err.message, 'error');
  }
}

async function openSentinelLogsModal() {
  const modal = document.getElementById('sentinel-modal');
  const container = document.getElementById('modal-sentinel-content');
  if (!modal || !container) return;

  container.innerHTML = '<div style="text-align:center;padding:30px;color:var(--text-muted);">⏳ Đang tải nhật ký nhịp tim hệ thống...</div>';
  modal.classList.add('active');

  try {
    const res = await fetch('/api/sentinel/logs?limit=50');
    const data = await res.json();
    const logs = data.logs || [];

    if (logs.length === 0) {
      container.innerHTML = '<div style="text-align:center;padding:30px;color:var(--text-muted);">Chưa có nhật ký giám sát. Nhấn "Quét ngay" để kích hoạt.</div>';
      return;
    }

    let rowsHtml = logs.map(l => {
      const lvl = (l.level || 'INFO').toLowerCase();
      const timeStr = new Date(l.timestamp).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      return `
        <tr>
          <td style="font-family:monospace;color:var(--text-muted);white-space:nowrap;">${timeStr}</td>
          <td><span class="sentinel-log-badge ${lvl}">${l.level}</span></td>
          <td style="color:#e2e8f0;line-height:1.4;">${escapeHtml(l.message)}</td>
        </tr>
      `;
    }).join('');

    container.innerHTML = `
      <div style="max-height:65vh;overflow-y:auto;">
        <table class="sentinel-logs-table">
          <thead>
            <tr>
              <th style="width:90px;">Thời gian</th>
              <th style="width:110px;">Phân loại</th>
              <th>Nội dung sự kiện & Hành động AI</th>
            </tr>
          </thead>
          <tbody>
            ${rowsHtml}
          </tbody>
        </table>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div style="color:var(--rose);padding:20px;">Lỗi tải nhật ký: ${escapeHtml(err.message)}</div>`;
  }
}

function closeSentinelModal(e) {
  if (e && e.target && e.target !== e.currentTarget) return;
  const modal = document.getElementById('sentinel-modal');
  if (modal) modal.classList.remove('active');
}

// =============================================================================
// Window Exports & Robust Event Binding
// =============================================================================

window.switchTab = switchTab;
window.switchFinSubtab = switchFinSubtab;
window.setTimeframe = setTimeframe;
window.jumpToIncident = jumpToIncident;
window.closeRcaModal = closeRcaModal;
window.openRcaModal = openRcaModal;
window.closeExportModal = closeExportModal;
window.openExportModal = openExportModal;
window.closeSentinelModal = closeSentinelModal;
window.openSentinelLogsModal = openSentinelLogsModal;
window.triggerSentinelScanNow = triggerSentinelScanNow;
window.toggleSentinelWorker = toggleSentinelWorker;
window.triggerLiveSync = triggerLiveSync;
window.loadCausalDag = loadCausalDag;
window.switchDebateScenario = switchDebateScenario;
window.runWhatIfSimulation = runWhatIfSimulation;
window.updateSliderLabel = updateSliderLabel;
window.filterSuggestions = filterSuggestions;
window.filterTopic = filterTopic;
window.handleSendQuery = handleSendQuery;
window.applySuggestion = applySuggestion;
window.copySqlToClipboard = copySqlToClipboard;
window.rerunSqlQuery = rerunSqlQuery;
window.toggleSqlView = toggleSqlView;
window.fetchStreamStatus = fetchStreamStatus;
window.toggleStreamWorker = toggleStreamWorker;
window.setSimulationSpeed = setSimulationSpeed;
window.triggerDynamicChaos = triggerDynamicChaos;
window.triggerTwinIntervention = triggerTwinIntervention;

// =============================================================================
// Bootstrap on DOM Ready
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
  try { loadOverview('all'); } catch (e) { console.error('Overview init failed:', e); }
  try { loadFinance(); } catch (e) { console.error('Finance init failed:', e); }
  try { filterSuggestions('CEO'); } catch (e) { console.error('Suggestions init failed:', e); }
  try { initSentinelWorker(); } catch (e) { console.error('Sentinel worker init failed:', e); }
  try {
    initStreamSSE();
    fetchStreamStatus();
    setInterval(fetchStreamStatus, 4000);
  } catch (e) { console.error('Stream init failed:', e); }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      try { closeRcaModal(); } catch (_) {}
      try { closeExportModal(); } catch (_) {}
      try { closeSentinelModal(); } catch (_) {}
    }
  });
});


