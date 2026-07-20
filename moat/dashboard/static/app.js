/**
 * Moat Dashboard v2 — 传感器监控面板
 * 开发者友好的实时监控界面
 */

// ── State ──────────────────────────────────
const STATE = { data: null, filter: 'all', search: '', timer: null, mode: 'normal' };

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

  // 显示已注入传感器数量
  const injected = s.injected_sensors || 0;
  const statInjected = document.getElementById('stat-injected');
  if (statInjected) {
    statInjected.querySelector('.value').textContent = injected;
    statInjected.querySelector('.value').className = 'value ' + (injected > 0 ? 'blue' : 'white');
    statInjected.querySelector('.sub').textContent = '个传感器已注入';
  }
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
  // 普通模式：只显示非 OK 的事件
  if (STATE.mode === 'normal') {
    filtered = filtered.filter(e => e.status !== 'OK');
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
        <div class="hint">${events.length === 0 ? '运行项目后传感器事件会自动显示在这里' : STATE.mode === 'normal' ? '普通模式只显示异常，切换到「详细」查看全部' : '试试修改筛选条件'}</div>
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

// ── Mode Toggle ──────────────────────────
function toggleMode() {
  STATE.mode = STATE.mode === 'normal' ? 'detailed' : 'normal';
  $$('.mode-btn').forEach(b => b.classList.toggle('active', b.dataset.mode === STATE.mode));
  renderEvents(STATE.data?.events || []);
  toast(STATE.mode === 'normal' ? '🔇 普通模式：只显示异常' : '📡 详细模式：显示所有事件', 'info');
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
  btn.disabled = true; btn.innerHTML = '⏳ 扫描中...';
  try {
    const r = await fetch('/api/moat/check', { method: 'POST' });
    const d = await r.json();
    if (d.timed_out) {
      toast('⏱️ ' + d.message, 'info');
    } else if (d.success) {
      toast('✅ 检查通过，未发现问题', 'success');
    } else {
      toast('❌ 检查发现异常', 'error');
    }
  } catch (e) { toast('连接失败: ' + e.message, 'error'); }
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
          <p>• 🔇/📡 模式切换 — 普通模式只看异常，详细模式看全部</p>
          <p>• 🔄 每 3 秒自动刷新数据</p>
        </div>
      </div>
    </div>`;
  document.body.appendChild(overlay);
}

// ── Inject Sensors ────────────────────────
async function injectSensors() {
  // Show loading overlay
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `
    <div class="modal" style="max-width:600px;">
      <div class="modal-header">
        <h2>📡 传感器注入</h2>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">✕</button>
      </div>
      <div class="modal-body" style="text-align:center;padding:40px;">
        <div style="font-size:24px;margin-bottom:16px;">⏳ 正在扫描项目...</div>
        <div style="color:var(--text-muted);">分析代码结构，计算可注入的传感器数量</div>
      </div>
    </div>`;
  document.body.appendChild(overlay);

  try {
    const r = await fetch('/api/moat/inject', { method: 'POST' });
    const data = await r.json();

    if (!data.success) {
      overlay.querySelector('.modal-body').innerHTML = `
        <div style="font-size:24px;margin-bottom:16px;">❌ 扫描失败</div>
        <div style="color:var(--text-muted);">${data.error || data.message || '未知错误'}</div>`;
      return;
    }

    if (!data.has_config) {
      overlay.querySelector('.modal-body').innerHTML = `
        <div style="font-size:24px;margin-bottom:16px;">⚠️ 未配置传感器</div>
        <div style="color:var(--text-muted);margin-bottom:16px;">项目还没有 moat.sensor.yml 配置文件</div>
        <div style="margin-bottom:16px;">请先在终端运行：</div>
        <code style="display:block;background:#1c2128;padding:8px;border-radius:4px;margin-bottom:16px;">moat sensor init</code>
        <div style="color:var(--text-muted);font-size:13px;">初始化后会自动检测项目类型并生成推荐配置</div>`;
      return;
    }

    if (data.total_injected === 0) {
      overlay.querySelector('.modal-body').innerHTML = `
        <div style="font-size:24px;margin-bottom:16px;">📡 无需注入</div>
        <div style="color:var(--text-muted);">扫描了 ${data.total_files} 个文件，所有函数已安装传感器或无需注入</div>`;
      return;
    }

    // Show preview
    const sampleHtml = (data.sample_files || []).map(f => {
      const short = f.split('/').slice(-2).join('/');
      return `<div style="font-size:13px;color:var(--text-muted);padding:2px 0;">📄 ${escapeHtml(short)}</div>`;
    }).join('');

    overlay.querySelector('.modal-body').innerHTML = `
      <div style="text-align:left;">
        <div style="display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap;">
          <div class="stat-card" style="flex:1;min-width:80px;padding:12px;text-align:center;">
            <div style="font-size:28px;font-weight:700;color:var(--green);">${data.total_injected}</div>
            <div style="font-size:12px;color:var(--text-muted);">传感器</div>
          </div>
          <div class="stat-card" style="flex:1;min-width:80px;padding:12px;text-align:center;">
            <div style="font-size:28px;font-weight:700;color:var(--white);">${data.injected_files}</div>
            <div style="font-size:12px;color:var(--text-muted);">被修改文件</div>
          </div>
          <div class="stat-card" style="flex:1;min-width:80px;padding:12px;text-align:center;">
            <div style="font-size:28px;font-weight:700;color:var(--text-muted);">${data.total_files}</div>
            <div style="font-size:12px;color:var(--text-muted);">扫描文件</div>
          </div>
          <div class="stat-card" style="flex:1;min-width:80px;padding:12px;text-align:center;">
            <div style="font-size:28px;font-weight:700;color:${data.errors > 0 ? 'var(--red)' : 'var(--green)'};">${data.errors}</div>
            <div style="font-size:12px;color:var(--text-muted);">错误</div>
          </div>
        </div>

        <!-- ⚠️ 风险提示 -->
        <div style="background:rgba(210,153,34,0.08);border:1px solid rgba(210,153,34,0.3);border-radius:8px;padding:14px 16px;margin-bottom:16px;">
          <div style="font-size:14px;font-weight:600;color:var(--yellow);margin-bottom:8px;">⚠️ 注入前请注意</div>
          <ul style="margin:0;padding-left:18px;font-size:13px;color:var(--text-secondary);line-height:1.8;">
            <li>会修改 <strong style="color:var(--yellow);">${data.injected_files}</strong> 个源文件，添加 <strong style="color:var(--yellow);">${data.total_injected}</strong> 个 <code>@moat_sensor</code> 装饰器</li>
            <li>注入后需要<strong style="color:var(--yellow);">重启项目服务</strong>，传感器才会生效</li>
            <li>如果不想用了，可以随时通过 <code style="background:#1c2128;padding:1px 5px;border-radius:3px;">moat sensor revert</code> 回退</li>
          </ul>
        </div>

        <div style="display:flex;gap:8px;align-items:center;margin-bottom:16px;padding:10px 14px;background:var(--bg-tertiary);border-radius:6px;">
          <span style="font-size:12px;color:var(--text-muted);">🔒 注入前会自动备份文件，随时可回退</span>
          <span style="font-size:12px;color:var(--blue);margin-left:auto;">
            <code style="background:#1c2128;padding:1px 5px;border-radius:3px;font-size:11px;">moat sensor revert &lt;时间戳&gt;</code>
          </span>
        </div>

        <div style="margin-bottom:12px;font-size:13px;color:var(--text-muted);">注入范围（来自 moat.sensor.yml）：</div>
        <div style="margin-bottom:16px;">
          ${(data.include_patterns || []).map(p => `<code style="background:#1c2128;padding:2px 6px;border-radius:3px;margin:2px;">${escapeHtml(p)}</code>`).join(' ')}
        </div>
        ${sampleHtml ? `<div style="margin-bottom:12px;font-size:13px;color:var(--text-muted);">部分文件预览：</div><div style="margin-bottom:16px;max-height:120px;overflow-y:auto;">${sampleHtml}</div>` : ''}
        ${data.error_details && data.error_details.length > 0 ? `
          <div style="margin-bottom:12px;font-size:13px;color:var(--red);">⚠️ ${data.error_details.length} 个文件扫描出错：</div>
          <div style="margin-bottom:16px;max-height:80px;overflow-y:auto;font-size:12px;color:var(--red);">
            ${data.error_details.map(e => `<div>${escapeHtml(e)}</div>`).join('')}
          </div>` : ''}
        <!-- ✅ 确认按钮放在顶部 -->
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-bottom:16px;padding:12px 0;border-bottom:1px solid var(--border);">
          <button class="btn" onclick="this.closest('.modal-overlay').remove()">取消</button>
          <button class="btn btn-primary" style="font-size:15px;padding:8px 24px;" onclick="executeInject(this.closest('.modal-overlay'))">✅ 确认注入</button>
        </div>
      </div>`;
  } catch (e) {
    overlay.querySelector('.modal-body').innerHTML = `
      <div style="font-size:24px;margin-bottom:16px;">❌ 连接失败</div>
      <div style="color:var(--text-muted);">${e.message}</div>`;
  }
}

async function executeInject(overlay) {
  overlay.querySelector('.modal-body').innerHTML = `
    <div style="text-align:center;padding:20px;">
      <div style="font-size:24px;margin-bottom:16px;">⏳ 正在注入...</div>
      <div style="color:var(--text-muted);">先备份文件，再自动添加 @moat_sensor 装饰器</div>
    </div>`;

  try {
    const r = await fetch('/api/moat/inject/execute', { method: 'POST' });
    const data = await r.json();

    if (!data.success) {
      overlay.querySelector('.modal-body').innerHTML = `
        <div style="text-align:center;padding:20px;">
          <div style="font-size:24px;margin-bottom:16px;">❌ 注入失败</div>
          <div style="color:var(--text-muted);">${data.error || data.message || '未知错误'}</div>
        </div>`;
      return;
    }

    // 获取重启建议
    let restartHtml = '<div style="text-align:center;color:var(--text-muted);font-size:13px;padding:8px;">检测重启方式...</div>';
    fetch('/api/moat/inject/restart', { method: 'POST' })
      .then(r => r.json())
      .then(rst => {
        const area = document.getElementById('restart-btn-area');
        if (!area) return;
        area.innerHTML = `
          <div style="padding:12px 14px;background:var(--bg-tertiary);border-radius:6px;margin-top:8px;">
            <div style="font-size:13px;color:var(--text-muted);margin-bottom:6px;">
              🔄 重启项目（<code style="background:#1c2128;padding:1px 4px;border-radius:3px;font-size:11px;">${rst.project_type}</code>）
            </div>
            <code id="restart-cmd" style="display:block;background:#0d1117;padding:8px 12px;border-radius:4px;font-size:13px;word-break:break-all;border:1px solid var(--border);">${escapeHtml(rst.restart_cmd)}</code>
            <button class="btn" style="margin-top:6px;font-size:12px;" onclick="copyCmd()">📋 复制命令</button>
          </div>`;
      })
      .catch(() => {});

    overlay.querySelector('.modal-body').innerHTML = `
      <div style="text-align:left;">
        <div style="text-align:center;">
          <div style="font-size:36px;margin-bottom:12px;">✅</div>
          <div style="font-size:20px;font-weight:600;margin-bottom:8px;">注入完成</div>
        </div>
        <div style="display:flex;gap:12px;margin:16px 0;flex-wrap:wrap;">
          <div class="stat-card" style="flex:1;min-width:80px;padding:12px;text-align:center;">
            <div style="font-size:28px;font-weight:700;color:var(--green);">${data.total_injected}</div>
            <div style="font-size:12px;color:var(--text-muted);">传感器已安装</div>
          </div>
          <div class="stat-card" style="flex:1;min-width:80px;padding:12px;text-align:center;">
            <div style="font-size:28px;font-weight:700;color:var(--white);">${data.backup_files}</div>
            <div style="font-size:12px;color:var(--text-muted);">文件已备份</div>
          </div>
          <div class="stat-card" style="flex:1;min-width:80px;padding:12px;text-align:center;">
            <div style="font-size:28px;font-weight:700;color:var(--white);">${data.total_files}</div>
            <div style="font-size:12px;color:var(--text-muted);">扫描文件</div>
          </div>
        </div>
        ${data.backup_timestamp ? `
          <div style="font-size:13px;color:var(--text-muted);text-align:center;margin-bottom:12px;">
            备份编号：<code style="background:#1c2128;padding:2px 6px;border-radius:3px;">${data.backup_timestamp}</code>
            <span style="margin-left:8px;">回退：</span>
            <code style="background:#1c2128;padding:2px 6px;border-radius:3px;">moat sensor revert ${data.backup_timestamp}</code>
          </div>` : ''}
        <div id="restart-btn-area" style="margin-bottom:12px;"></div>
        <div style="display:flex;gap:8px;justify-content:flex-end;border-top:1px solid var(--border);padding-top:16px;margin-top:8px;">
          <button class="btn btn-primary" onclick="this.closest('.modal-overlay').remove();loadData();">知道了</button>
        </div>
      </div>`;
  } catch (e) {
    overlay.querySelector('.modal-body').innerHTML = `
      <div style="text-align:center;padding:20px;">
        <div style="font-size:24px;margin-bottom:16px;">❌ 连接失败</div>
        <div style="color:var(--text-muted);">${e.message}</div>
      </div>`;
  }
}

function copyCmd() {
  const el = document.getElementById('restart-cmd');
  if (!el) return;
  navigator.clipboard.writeText(el.textContent).then(() => {
    toast('📋 已复制到剪贴板', 'success');
  }).catch(() => {});
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
