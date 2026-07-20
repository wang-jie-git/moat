/**
 * Moat Dashboard v2 — 传感器监控面板
 * 开发者友好的实时监控界面
 */

// ── State ──────────────────────────────────
const STATE = { data: null, filter: 'all', search: '', timer: null };

// ── DOM Shortcuts ──────────────────────────
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);

// ── Helpers ────────────────────────────────
function escapeHtml(t) {
  const d = document.createElement('div');
  d.textContent = t;
  return d.innerHTML;
}

function timeAgo(ts) {
  const diff = Date.now() - new Date(ts).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 5) return '刚刚';
  if (s < 60) return `${s}秒前`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}分钟前`;
  const h = Math.floor(m / 60);
  return `${h}小时前`;
}

function fmtTime(ts) {
  if (!ts) return '-';
  const d = new Date(ts);
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function fmtMs(ms) {
  if (ms == null) return '';
  if (ms < 1) return '<1ms';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

// ── Toast ──────────────────────────────────
function toast(msg, type = 'info') {
  const c = document.getElementById('toast-container');
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => { t.classList.add('fade-out'); setTimeout(() => t.remove(), 250); }, 3000);
}

// ── Load Data ─────────────────────────────
async function loadData() {
  try {
    const r = await fetch('/api/moat/sensors');
    STATE.data = await r.json();
    render();
    document.getElementById('last-updated').textContent = fmtTime(new Date().toISOString());
  } catch (e) {
    console.error('加载失败:', e);
  }
}

// ── Render All ────────────────────────────
function render() {
  const d = STATE.data;
  if (!d) return;
  renderStats(d.stats);
  renderStatus(d.stats, d.health);
  renderEvents(d.events || []);
  renderHealth(d.health);
}

// ── Stats ─────────────────────────────────
function renderStats(s) {
  if (!s) return;
  const cards = [
    ['stat-total', s.total_components, 'white', '个组件', '📦'],
    ['stat-ok', s.healthy, 'green', '运行正常', '✅'],
    ['stat-degraded', s.degraded, 'yellow', '降级运行', '⚠️'],
    ['stat-panics', s.panics_last_hour, 'red', '近期告警', '🚨'],
    ['stat-events', s.events_total, 'blue', '总事件数', '📊'],
  ];
  cards.forEach(([id, val, color, sub, icon]) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.querySelector('.value').textContent = val ?? 0;
    el.querySelector('.value').className = 'value ' + color;
    el.querySelector('.sub').textContent = sub;
    el.querySelector('.icon-bg').textContent = icon;
  });
}

// ── Header Status ─────────────────────────
function renderStatus(stats) {
  const badge = document.getElementById('status-badge');
  const dot = document.getElementById('status-dot');
  if (!badge || !dot) return;
  const p = stats?.panics_last_hour || 0;
  const d = stats?.degraded || 0;
  if (p > 0) {
    badge.className = 'status-badge red';
    dot.className = 'status-dot red';
    badge.innerHTML = `<span class="status-dot red"></span> ${p} 个组件异常`;
  } else if (d > 0) {
    badge.className = 'status-badge yellow';
    dot.className = 'status-dot yellow';
    badge.innerHTML = `<span class="status-dot yellow"></span> ${d} 个组件降级`;
  } else {
    badge.className = 'status-badge green';
    dot.className = 'status-dot green';
    badge.innerHTML = `<span class="status-dot green"></span> 全部正常`;
  }
}

// ── Events ────────────────────────────────
function renderEvents(events) {
  const container = document.getElementById('event-list');
  const badge = document.getElementById('event-badge');
  if (!container) return;

  // Filter
  let filtered = [...events];
  if (STATE.filter !== 'all') {
    filtered = filtered.filter(e => e.status === STATE.filter.toUpperCase());
  }
  if (STATE.search) {
    const q = STATE.search.toLowerCase();
    filtered = filtered.filter(e =>
      e.component_id.toLowerCase().includes(q) ||
      (e.error || '').toLowerCase().includes(q)
    );
  }

  if (badge) badge.textContent = filtered.length;

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="event-empty">
        <div class="emoji">${events.length === 0 ? '📡' : '🔍'}</div>
        <div class="title">${events.length === 0 ? '暂无传感器事件' : '没有匹配的事件'}</div>
        <div class="hint">${events.length === 0 ? '运行项目后传感器事件会自动显示在这里' : '试试修改筛选条件'}</div>
      </div>`;
    return;
  }

  container.innerHTML = filtered.map(e => {
    const cls = e.status === 'PANIC' ? 'panic' : e.status === 'DEGRADED' ? 'degraded' : 'ok';
    const icon = e.status === 'PANIC' ? '🔴' : e.status === 'DEGRADED' ? '🟡' : '🟢';
    const err = e.error ? `<div class="event-error">${escapeHtml(e.error)}</div>` : '';
    const dur = e.duration_ms > 0 ? `<div class="event-duration">⏱ ${fmtMs(e.duration_ms)}</div>` : '';
    return `
      <div class="event-item">
        <div class="event-icon ${cls}">${icon}</div>
        <div class="event-body">
          <div class="event-component">
            ${escapeHtml(e.component_id)}
            <span class="event-status-label ${cls}">${e.status}</span>
          </div>
          ${err}
          ${dur}
        </div>
        <div class="event-time">${timeAgo(e.timestamp)}</div>
      </div>`;
  }).join('');
}

// ── Health ────────────────────────────────
function renderHealth(health) {
  const grid = document.getElementById('health-grid');
  const badge = document.getElementById('health-badge');
  if (!grid) return;

  const details = health?.details || {};
  const ids = Object.keys(details);

  if (badge) badge.textContent = ids.length;

  if (ids.length === 0) {
    grid.innerHTML = `
      <div class="health-empty">
        <div class="emoji" style="font-size:36px;">📡</div>
        <div class="title">等待传感器数据</div>
        <div class="hint">运行 <code style="background:#1c2128;padding:2px 6px;border-radius:3px;">moat sensor inject --no-dry-run</code> 安装传感器后重启服务</div>
      </div>`;
    return;
  }

  grid.innerHTML = ids.map(id => {
    const state = details[id];
    const status = state.status || 'OK';
    const isPanic = status === 'PANIC';
    const isBad = status === 'DEGRADED';
    const strip = isPanic ? 'red' : isBad ? 'yellow' : 'green';
    const label = isPanic ? '🔴 崩溃' : isBad ? '🟡 降级' : '🟢 正常';
    const cls = isPanic ? 'red' : isBad ? 'yellow' : 'green';
    const err = state.error ? `<div class="error-text">${escapeHtml(state.error)}</div>` : '';
    return `
      <div class="health-card" onclick="showDetail('${escapeHtml(id)}')">
        <div class="strip ${strip}"></div>
        <div class="name">${escapeHtml(id)}</div>
        <div class="status ${cls}">${label}</div>
        ${err}
      </div>`;
  }).join('');
}

// ── Filter Events ─────────────────────────
function setFilter(status) {
  STATE.filter = status;
  $$('.filter-btn').forEach(b => b.classList.toggle('active', b.dataset.filter === status));
  renderEvents(STATE.data?.events || []);
}

function onSearch(val) {
  STATE.search = val;
  renderEvents(STATE.data?.events || []);
}

// ── Detail Modal ──────────────────────────
async function showDetail(componentId) {
  try {
    const r = await fetch(`/api/moat/sensors/${encodeURIComponent(componentId)}`);
    const data = await r.json();
    renderModal(data);
  } catch (e) {
    toast('加载详情失败: ' + e.message, 'error');
  }
}

function renderModal(data) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.onclick = e => { if (e.target === overlay) overlay.remove(); };

  const state = data.state || {};
  const events = data.events || [];
  const healthy = data.is_healthy !== false;
  const failures = state.consecutive_failures || 0;

  const statusLabel = !healthy ? '🔴 异常' : failures > 0 ? '🟡 降级' : '🟢 健康';
  const statusClass = !healthy ? 'red' : failures > 0 ? 'yellow' : 'green';
  const lastSuc = state.last_success ? fmtTime(state.last_success * 1000) : '-';
  const lastFail = state.last_failure ? fmtTime(state.last_failure * 1000) : '-';

  const eventsHtml = events.length === 0
    ? '<div class="modal-empty">暂无事件记录</div>'
    : events.map(e => {
        const cls = (e.status || '').toLowerCase();
        return `<div class="modal-event-item">
          <span>
            <span class="me-status ${cls}">${e.status}</span>
            <span class="me-err">${escapeHtml(e.error || '')}</span>
          </span>
          <span>
            <span class="me-dur">${e.duration_ms > 0 ? fmtMs(e.duration_ms) : ''}</span>
            <span class="me-time">${fmtTime(e.timestamp)}</span>
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
        <div class="modal-section">
          <div class="modal-section-title">组件状态</div>
          <div class="info-grid">
            <span class="label">状态</span>
            <span class="value ${statusClass}">${statusLabel}</span>
            <span class="label">连续失败</span>
            <span class="value">${failures} 次</span>
            <span class="label">上次成功</span>
            <span class="value">${lastSuc}</span>
            <span class="label">上次失败</span>
            <span class="value">${lastFail}</span>
          </div>
        </div>
        <div class="modal-section">
          <div class="modal-section-title">事件历史 (${events.length})</div>
          <div class="modal-event-list">${eventsHtml}</div>
        </div>
      </div>
    </div>`;

  document.body.appendChild(overlay);
}

// ── Actions ───────────────────────────────
async function runCheck() {
  const btn = document.getElementById('btn-check'); if (!btn) return;
  btn.disabled = true; btn.innerHTML = '⏳ 运行中...';
  try {
    const r = await fetch('/api/moat/check', { method: 'POST' });
    const d = await r.json();
    toast(d.success ? '✅ 检查通过' : '❌ 检查发现异常', d.success ? 'success' : 'error');
  } catch (e) { toast('检查失败: ' + e.message, 'error'); }
  btn.disabled = false; btn.innerHTML = '🔍 运行检查';
}

async function saveBaseline() {
  const btn = document.getElementById('btn-baseline'); if (!btn) return;
  btn.disabled = true; btn.innerHTML = '⏳ 保存中...';
  try {
    await fetch('/api/moat/baseline/save', { method: 'POST' });
    toast('✅ 基线已保存', 'success');
  } catch (e) { toast('保存失败: ' + e.message, 'error'); }
  btn.disabled = false; btn.innerHTML = '💾 保存基线';
}

async function resetEvents() {
  if (!confirm('确定清空所有传感器事件？')) return;
  try {
    await fetch('/api/moat/sensors/reset', { method: 'POST' });
    toast('✅ 已清空', 'success');
    loadData();
  } catch (e) { toast('清空失败: ' + e.message, 'error'); }
}

function showHelp() {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `
    <div class="modal" style="max-width:520px;">
      <div class="modal-header">
        <h2>📖 使用帮助</h2>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">✕</button>
      </div>
      <div class="modal-body">
        <div class="help-section">
          <h3>🟢 这是什么？</h3>
          <p>实时监控项目代码的运行状态。给核心函数装上「传感器」后，异常会自动上报到这里。</p>
        </div>
        <div class="help-section">
          <h3>🎨 颜色含义</h3>
          <p><span style="color:var(--green)">🟢 正常</span> — 运行良好 &nbsp; <span style="color:var(--yellow)">🟡 降级</span> — 有异常但未崩溃 &nbsp; <span style="color:var(--red)">🔴 异常</span> — 需要处理</p>
        </div>
        <div class="help-section">
          <h3>🔧 如何安装传感器</h3>
          <p><code>moat sensor init</code> — 初始化配置</p>
          <p><code>moat sensor inject</code> — 预览要安装的位置</p>
          <p><code>moat sensor inject --no-dry-run</code> — 执行注入</p>
          <p><span style="font-size:12px;color:var(--text-muted);">完成后重启项目，传感器事件会自动出现在 Dashboard</span></p>
        </div>
        <div class="help-section">
          <h3>🖱️ 交互说明</h3>
          <p>• 点击组件卡片 — 查看详情和历史</p>
          <p>• 🔍 筛选 — 按状态/关键词过滤事件</p>
          <p>• 🔄 每 3 秒自动刷新数据</p>
        </div>
      </div>
    </div>`;
  document.body.appendChild(overlay);
}

// ── Init ──────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadData();
  // Load project name
  fetch('/api/moat/status')
    .then(r => r.json())
    .then(d => { const el = document.getElementById('project-name'); if (el) el.textContent = d.project || '-'; })
    .catch(() => {});
  // Auto-refresh every 3s
  STATE.timer = setInterval(loadData, 3000);
});
