/**
 * Moat Dashboard — 传感器监控前端
 * 
 * 简单直观的看板，适合非专业用户使用。
 * 功能：实时事件流、组件健康热力图、一键操作
 */

// ── 状态 ──────────────────────────────────
const STATE = {
  sensors: null,
  timer: null,
};

// ── DOM 引用 ──────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ── 格式化 ──────────────────────────────────
function timeAgo(ts) {
  const diff = Date.now() - new Date(ts).getTime();
  const sec = Math.floor(diff / 1000);
  if (sec < 10) return '刚刚';
  if (sec < 60) return `${sec} 秒前`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min} 分钟前`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h} 小时前`;
  return new Date(ts).toLocaleDateString();
}

function formatTime(ts) {
  if (!ts) return '-';
  const d = new Date(ts);
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function formatMs(ms) {
  if (ms < 1) return '<1ms';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function escapeHtml(text) {
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}

// ── Toast 通知 ────────────────────────────
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('fade-out');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// ── 加载传感器数据 ────────────────────────
async function loadSensors() {
  try {
    const res = await fetch('/api/moat/sensors');
    const data = await res.json();
    STATE.sensors = data;
    renderStats(data.stats);
    renderEvents(data.events || []);
    renderHealth(data.health);
    updateHeaderStatus(data);
  } catch (e) {
    console.error('加载传感器数据失败:', e);
  }
}

// ── 渲染统计卡片 ──────────────────────────
function renderStats(stats) {
  if (!stats) return;
  
  setValue('stat-total', stats.total_components || 0, 'white');
  setValue('stat-healthy', stats.healthy || 0, 'green');
  setValue('stat-degraded', stats.degraded || 0, 'yellow');
  setValue('stat-panics', stats.panics_last_hour || 0, 'red');
}

function setValue(id, val, color) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = val;
  el.className = 'value ' + color;
}

// ── 更新头部状态 ──────────────────────────
function updateHeaderStatus(data) {
  const dot = document.getElementById('status-dot');
  const text = document.getElementById('status-text');
  if (!dot || !text) return;

  const panics = data.stats?.panics_last_hour || 0;
  const degraded = data.stats?.degraded || 0;

  if (panics > 0) {
    dot.className = 'status-dot red';
    text.textContent = `${panics} 个组件异常`;
  } else if (degraded > 0) {
    dot.className = 'status-dot yellow';
    text.textContent = `${degraded} 个组件降级`;
  } else {
    dot.className = 'status-dot green';
    text.textContent = '全部正常';
  }
}

// ── 渲染事件流 ────────────────────────────
function renderEvents(events) {
  const container = document.getElementById('event-list');
  if (!container) return;

  const badge = document.getElementById('event-badge');
  if (badge) badge.textContent = events.length;

  if (events.length === 0) {
    container.innerHTML = `
      <div class="event-empty">
        <div class="big-emoji">✅</div>
        <div>还没有传感器事件</div>
        <div style="font-size:12px;color:#484f58;margin-top:4px;">
          运行 moat sensor inject 后重启服务就会有了
        </div>
      </div>`;
    return;
  }

  // 只显示最近的错误事件（非 OK），以及最近的几条 OK
  const errorEvents = events.filter(e => e.status !== 'OK');
  const okEvents = events.filter(e => e.status === 'OK').slice(-2);
  const displayEvents = [...errorEvents, ...okEvents].slice(0, 50);

  container.innerHTML = displayEvents.map(e => {
    const statusClass = e.status === 'PANIC' ? 'panic' : e.status === 'DEGRADED' ? 'degraded' : 'ok';
    const statusLabel = e.status === 'PANIC' ? '🔴' : e.status === 'DEGRADED' ? '🟡' : '🟢';
    const errInfo = e.error ? `<span class="err-type">${escapeHtml(e.error_type || '')}: ${escapeHtml(e.error)}</span>` : '';
    
    return `
      <div class="event-item">
        <div class="event-status ${statusClass}"></div>
        <div class="event-content">
          <div class="event-component">
            ${statusLabel} ${escapeHtml(e.component_id)}
            ${errInfo}
          </div>
          ${e.duration_ms > 0 ? `<div class="event-message">耗时: ${formatMs(e.duration_ms)}</div>` : ''}
        </div>
        <div class="event-time">${timeAgo(e.timestamp)}</div>
      </div>`;
  }).join('');
}

// ── 渲染健康热力图 ──────────────────────
function renderHealth(health) {
  const grid = document.getElementById('health-grid');
  if (!grid) return;

  const badge = document.getElementById('health-badge');
  const details = health?.details || {};
  const componentIds = Object.keys(details);

  if (badge) badge.textContent = componentIds.length;

  if (componentIds.length === 0) {
    grid.innerHTML = `
      <div class="health-empty">
        <div style="font-size:32px;margin-bottom:8px;">📡</div>
        <div>暂无传感器数据</div>
        <div class="no-sensors-note" style="margin-top:8px;">
          在代码中添加 <code>@moat_sensor</code> 装饰器即可激活监控
        </div>
      </div>`;
    return;
  }

  grid.innerHTML = componentIds.map(id => {
    const state = details[id];
    // 支持两种格式：新格式有 status，旧格式用 consecutive_failures
    const status = state.status || 'OK';
    const hasError = status === 'PANIC' || status === 'DEGRADED';
    const isPanic = status === 'PANIC';
    
    const stripClass = isPanic ? 'red' : hasError ? 'yellow' : 'green';
    const statusText = isPanic ? '🔴 崩溃' : hasError ? '🟡 降级' : '🟢 正常';
    const statusClass = isPanic ? 'red' : hasError ? 'yellow' : 'green';
    
    let extraInfo = '';
    if (state.error) {
      extraInfo = `<div style="font-size:10px;color:#f85149;margin-top:2px;">${escapeHtml(state.error)}</div>`;
    } else if (state.last_error) {
      extraInfo = `<div style="font-size:10px;color:#f85149;margin-top:2px;">${escapeHtml(state.last_error)}</div>`;
    }

    return `
      <div class="health-card" onclick="showComponentDetail('${escapeHtml(id)}')">
        <div class="hc-strip ${stripClass}"></div>
        <div class="hc-name">${escapeHtml(id)}</div>
        <div class="hc-status ${statusClass}">${statusText}</div>
        ${extraInfo}
      </div>`;
  }).join('');
}

// ── 组件详情弹窗 ──────────────────────────
async function showComponentDetail(componentId) {
  try {
    const res = await fetch(`/api/moat/sensors/${encodeURIComponent(componentId)}`);
    const data = await res.json();
    renderModal(data);
  } catch (e) {
    showToast('加载详情失败: ' + e.message, 'error');
  }
}

function renderModal(data) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

  const state = data.state || {};
  const events = data.events || [];
  const isHealthy = data.is_healthy !== false;
  const failures = state.consecutive_failures || 0;

  const healthLabel = isHealthy ? (failures > 0 ? '🟡 降级' : '🟢 健康') : '🔴 异常';
  const healthClass = isHealthy ? (failures > 0 ? 'yellow' : 'green') : 'red';

  // 最近事件列表
  const eventsHtml = events.length === 0
    ? '<div style="color:#484f58;padding:12px;text-align:center;font-size:12px;">暂无事件记录</div>'
    : events.map(e => {
        const statusClass = e.status === 'PANIC' ? 'panic' : e.status === 'DEGRADED' ? 'degraded' : 'ok';
        return `
          <div class="modal-event-item">
            <span>
              <span class="me-status ${statusClass}">${e.status}</span>
              ${e.error ? `<span class="me-err">${escapeHtml(e.error)}</span>` : ''}
            </span>
            <span>
              ${e.duration_ms > 0 ? formatMs(e.duration_ms) + ' ' : ''}
              <span class="me-time">${formatTime(e.timestamp)}</span>
            </span>
          </div>`;
      }).join('');

  overlay.innerHTML = `
    <div class="modal">
      <div class="modal-header">
        <h2>📦 ${escapeHtml(data.component_id)}</h2>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">✕</button>
      </div>
      <div class="modal-body">
        <div class="modal-info-grid">
          <span class="label">状态</span>
          <span class="value ${healthClass}">${healthLabel}</span>
          
          <span class="label">连续失败</span>
          <span class="value">${failures} 次</span>
          
          <span class="label">上次成功</span>
          <span class="value">${state.last_success ? formatTime(state.last_success * 1000) : '-'}</span>
          
          <span class="label">上次失败</span>
          <span class="value">${state.last_failure ? formatTime(state.last_failure * 1000) : '-'}</span>
        </div>

        <div class="modal-section-title">📋 事件历史（最近 ${events.length} 条）</div>
        <div class="modal-events">${eventsHtml}</div>
      </div>
    </div>`;

  document.body.appendChild(overlay);
  // 点击外部关闭
  setTimeout(() => {
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
  }, 0);
}
window.showComponentDetail = showComponentDetail;

// ── 一键操作 ─────────────────────────────
async function injectDemo() {
  const btn = document.querySelector('button[onclick="injectDemo()"]');
  if (!btn) return;
  btn.disabled = true;
  btn.textContent = '⏳ 注入中...';
  try {
    const res = await fetch('/api/moat/sensors/demo', { method: 'POST' });
    const data = await res.json();
    showToast('✅ 已注入 ' + data.injected + ' 条演示事件', 'success');
    loadSensors();
  } catch (e) {
    showToast('注入失败: ' + e.message, 'error');
  }
  btn.disabled = false;
  btn.textContent = '🧪 注入演示数据';
}

async function runCheck() {
  const btn = document.getElementById('btn-check');
  if (!btn) return;
  btn.disabled = true;
  btn.textContent = '⏳ 检查中...';
  try {
    const res = await fetch('/api/moat/check', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('✅ 检查通过，一切正常', 'success');
    } else {
      showToast('❌ 检查发现异常', 'error');
    }
  } catch (e) {
    showToast('检查失败: ' + e.message, 'error');
  }
  btn.disabled = false;
  btn.textContent = '🔍 运行检查';
}

async function saveBaseline() {
  const btn = document.getElementById('btn-baseline');
  if (!btn) return;
  btn.disabled = true;
  btn.textContent = '⏳ 保存中...';
  try {
    const res = await fetch('/api/moat/baseline/save', { method: 'POST' });
    await res.json();
    showToast('✅ 基线已保存', 'success');
  } catch (e) {
    showToast('保存失败: ' + e.message, 'error');
  }
  btn.disabled = false;
  btn.textContent = '💾 保存基线';
}

async function resetSensors() {
  if (!confirm('确定清空所有传感器事件？')) return;
  try {
    const res = await fetch('/api/moat/sensors/reset', { method: 'POST' });
    await res.json();
    showToast('✅ 已清空', 'success');
    loadSensors();
  } catch (e) {
    showToast('清空失败: ' + e.message, 'error');
  }
}

// 暴露到全局
window.runCheck = runCheck;
window.saveBaseline = saveBaseline;
window.resetSensors = resetSensors;

// ── 初始化 ─────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // 首次加载
  loadSensors();

  // 状态栏项目名
  fetch('/api/moat/status')
    .then(r => r.json())
    .then(data => {
      const el = document.getElementById('project-name');
      if (el) el.textContent = data.project || '-';
    })
    .catch(() => {});

  // 每 3 秒自动刷新
  STATE.timer = setInterval(loadSensors, 3000);
});
