/**
 * Moat Dashboard v2 — 传感器监控面板
 * 开发者友好的实时监控界面
 */

// ── State ──────────────────────────────────

// ── State ──────────────────────────────────
const STATE = {
  data: null, filter: 'all', search: '', timer: null, mode: 'normal',
  healthSearch: '', paused: false, memTab: 'evolution',
  propSearch: '', propCategory: '', propRisk: '', propStatus: '',
  propOffset: 0, propLimit: 20, currentView: 'dashboard',
  leakFilter: 'all', leakSearch: '', leakCategory: '', leakScanAi: false,
  acceptDiffMode: true, acceptScoreGate: 0,
};

// ── View Switching ─────────────────────────
function switchView(view) {
  STATE.currentView = view;
  // Update nav
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.view === view);
  });
  // Update sections
  document.querySelectorAll('.view-section').forEach(el => {
    el.classList.toggle('active', el.id === 'view-' + view);
  });
  // Update title
  const titles = {
    dashboard: '📊 仪表盘',
    sensors: '📡 传感器',
    memory: '🧠 记忆系统',
    evolution: '📝 进化提案',
    leak: '🔒 泄漏检测',
    accept: '🏗️ 架构验收',
    project: '📂 项目信息',
  };
  const titleEl = document.getElementById('view-title');
  if (titleEl) titleEl.textContent = titles[view] || view;

  // Load content on first visit
  if (view === 'memory') loadMemoryView();
  else if (view === 'evolution') loadEvolutionView();
  else if (view === 'project') loadProjectFull();
  else if (view === 'sensors') loadSensorStats();
  else if (view === 'leak') loadLeakCheckView();
  else if (view === 'accept') loadAcceptView();

  // Close mobile menu
  document.querySelector('.sidebar')?.classList.remove('mobile-open');
}

function toggleMobileMenu() {
  document.querySelector('.sidebar')?.classList.toggle('mobile-open');
}

// ── View Loaders ───────────────────────────
async function loadMemoryView() {
  const el = document.getElementById('memory-full-content');
  if (!el) return;
  el.innerHTML = '<div style="color:var(--text-muted);padding:20px;text-align:center;">加载中...</div>';
  try {
    const [memR, evoR] = await Promise.all([
      fetch('/api/moat/memory'),
      fetch('/api/moat/evolution?limit=5')
    ]);
    const mem = await memR.json();
    const evo = await evoR.json();
    renderMemoryFullView(el, mem, evo);
  } catch (e) {
    el.innerHTML = '<div class="mem-unavailable"><div class="emoji">❌</div><div>加载失败</div></div>';
  }
}

function renderMemoryFullView(el, mem, evo) {
  const ms = mem.available ? mem.stats : { redlines: 0, lessons: 0, templates: 0, skills: 0, total: 0 };
  const es = evo.available ? evo.stats : { pending: 0, accepted: 0, rejected: 0, total: 0 };
  // 局部兜底：避免引用未定义变量导致 ReferenceError
  const scoreGate = typeof STATE !== 'undefined' ? (STATE.acceptScoreGate || 0) : 0;
  const lastAccept = typeof STATE !== 'undefined' ? (STATE.lastAcceptResult || {}) : {};
  const d = lastAccept || {};
  const score = d.score ?? d.overall_score ?? 100;
  const gateFailed = scoreGate > 0 && score < scoreGate;

  // 红线
  const redlines = (mem.recent_redlines || []).map(r => {
    const sev = r.severity || 'info';
    const icon = sev === 'critical' ? '🔴' : sev === 'warning' ? '🟡' : '🔵';
    const cat = r.category || 'general';
    const src = r.source || '';
    const created = r.created_at ? r.created_at.slice(0, 10) : '';
    return `<div class="mem-item mem-severity-${sev}" onclick='showMemoryDetail(JSON.parse(decodeURIComponent("${encodeURIComponent(JSON.stringify(r))}")), "redline")' style="cursor:pointer;">
      <div class="mem-item-title">${icon} ${escapeHtml(r.title || '未命名')} <span class="mem-badge cat-${cat}">${cat}</span>${src ? `<span class="mem-badge source-${src}">${src}</span>` : ''}</div>
      <div class="mem-item-desc">${escapeHtml((r.description || '').slice(0, 150))}</div>
      ${created ? `<div class="mem-item-meta"><span>📅 ${created}</span></div>` : ''}
    </div>`;
  }).join('') || '<div style="color:var(--text-muted);font-size:11px;padding:12px;text-align:center;">暂无红线</div>';

  // 踩坑
  const lessons = (mem.recent_lessons || []).map(l => {
    const created = l.created_at ? l.created_at.slice(0, 10) : '';
    return `<div class="mem-item mem-severity-warning" onclick='showMemoryDetail(JSON.parse(decodeURIComponent("${encodeURIComponent(JSON.stringify(l))}")), "lesson")' style="cursor:pointer;">
      <div class="mem-item-title">⚠️ ${escapeHtml((l.error_summary || l.title || '未知错误').slice(0, 80))}</div>
      <div class="mem-item-desc">${escapeHtml((l.error_summary || '').slice(0, 150))}</div>
      ${created ? `<div class="mem-item-meta"><span>📅 ${created}</span></div>` : ''}
    </div>`;
  }).join('') || '<div style="color:var(--text-muted);font-size:11px;padding:12px;text-align:center;">暂无踩坑</div>';

  // 模板
  const templates = (mem.recent_templates || []).map(t => {
    const created = t.created_at ? t.created_at.slice(0, 10) : '';
    return `<div class="mem-item" style="cursor:pointer;">
      <div class="mem-item-title">📋 ${escapeHtml(t.template_name || t.title || '未命名')}</div>
      <div class="mem-item-desc" style="font-family:monospace;font-size:11px;">${escapeHtml((t.content || t.description || '').slice(0, 200))}</div>
      ${created ? `<div class="mem-item-meta"><span>📅 ${created}</span></div>` : ''}
    </div>`;
  }).join('') || '<div style="color:var(--text-muted);font-size:11px;padding:12px;text-align:center;">暂无模板</div>';

  // 技能
  const skills = (mem.recent_skills || []).map(s => {
    const created = s.created_at ? s.created_at.slice(0, 10) : '';
    return `<div class="mem-item" style="cursor:pointer;">
      <div class="mem-item-title">🛠️ ${escapeHtml(s.skill_name || s.title || '未命名')}</div>
      <div class="mem-item-desc">${escapeHtml((s.description || '').slice(0, 150))}</div>
      ${created ? `<div class="mem-item-meta"><span>📅 ${created}</span></div>` : ''}
    </div>`;
  }).join('') || '<div style="color:var(--text-muted);font-size:11px;padding:12px;text-align:center;">暂无技能</div>';

  // 最近提案
  const evoProps = (evo.proposals || []).slice(0, 5).map(p => {
    const risk = p.risk === 'high' ? '🔴' : p.risk === 'medium' ? '🟡' : '🟢';
    return `<div class="mem-item" style="cursor:pointer;" onclick="showProposalDetail(${JSON.stringify(p).replace(/"/g, '&quot;')})">
      <div class="mem-item-title">${risk} ${escapeHtml(p.title || '未命名').slice(0, 80)} <span class="mem-badge cat-${p.category || 'other'}">${p.category || 'other'}</span></div>
    </div>`;
  }).join('') || '';

  const statsCards = [
    { icon: '🔴', label: '红线', value: ms.redlines, color: 'var(--red)' },
    { icon: '⚠️', label: '踩坑', value: ms.lessons, color: 'var(--yellow)' },
    { icon: '📋', label: '模板', value: ms.templates, color: 'var(--blue)' },
    { icon: '🛠️', label: '技能', value: ms.skills, color: 'var(--green)' },
    { icon: '📝', label: '提案', value: es.total, color: 'white' },
  ];

  el.innerHTML = `
    <div class="panel" style="grid-column:1/-1;">
      <div class="panel-header"><h2>📊 记忆概览</h2></div>
      <div class="panel-body" style="padding:16px;">
        <div style="display:flex;gap:12px;flex-wrap:wrap;">
          ${statsCards.map(c => `
            <div style="flex:1;min-width:80px;text-align:center;padding:12px 8px;background:var(--bg-primary);border-radius:8px;border:1px solid var(--border);">
              <div style="font-size:24px;font-weight:700;color:${c.color};">${c.value}</div>
              <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">${c.icon} ${c.label}</div>
            </div>
          `).join('')}
        </div>
        ${gateFailed ? `
        <div style="background:var(--red-bg);border:1px solid var(--red);border-radius:6px;padding:10px 14px;margin-top:12px;display:flex;align-items:center;gap:8px;">
          <span style="font-size:18px;">🚫</span>
          <div>
            <div style="font-weight:600;font-size:13px;color:var(--red);">未通过评分门禁</div>
            <div style="font-size:11px;color:var(--text-muted);">得分 ${score}/100 低于设定的门禁阈值 ${scoreGate}/100</div>
          </div>
        </div>` : scoreGate > 0 ? `
        <div style="background:rgba(34,197,94,0.1);border:1px solid var(--green);border-radius:6px;padding:10px 14px;margin-top:12px;display:flex;align-items:center;gap:8px;">
          <span style="font-size:18px;">✅</span>
          <div>
            <div style="font-weight:600;font-size:13px;color:var(--green);">通过评分门禁</div>
            <div style="font-size:11px;color:var(--text-muted);">得分 ${score}/100 ≥ 门禁阈值 ${scoreGate}/100</div>
          </div>
        </div>` : ''}
      </div>
    </div>

    <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap;">
      <button class="btn btn-primary" id="accept-scan-btn" onclick="runAcceptCheck()" style="font-size:13px;padding:6px 16px;" title="重新执行架构验收，使用当前设置的增量/完整模式">🔍 重新验收</button>
      <button class="btn" onclick="generateAcceptRules()" style="font-size:13px;padding:6px 16px;" title="生成 architect.yml 规则定义文件，可自定义修改后让验收按你的规则执行">📄 生成规则模板</button>
      <button class="btn" id="accept-export-btn" onclick="exportAcceptReport()" style="display:none;font-size:13px;padding:6px 16px;" title="导出 Markdown 格式的完整验收报告">📄 导出</button>
      <span style="font-size:11px;color:var(--text-muted);align-self:center;margin-left:4px;" title="${d.diff_mode !== false ? '只检测有变更的文件，速度更快' : '扫描全部文件，更全面但耗时更长'}">
        ${d.diff_mode !== false ? '⚡ 增量模式' : '🔄 完整模式'}
        ${scoreGate > 0 ? `| 🎯 门禁 ${scoreGate}分` : ''}
      </span>
    </div>

    <div class="panel">
      <div class="panel-header"><h2>🔴 红线（${ms.redlines}）</h2></div>
      <div class="panel-body" style="padding:12px;max-height:350px;overflow-y:auto;">${redlines}</div>
    </div>

    <div class="panel">
      <div class="panel-header"><h2>⚠️ 踩坑（${ms.lessons}）</h2></div>
      <div class="panel-body" style="padding:12px;max-height:350px;overflow-y:auto;">${lessons}</div>
    </div>

    <div class="panel">
      <div class="panel-header"><h2>📋 模板（${ms.templates}）</h2></div>
      <div class="panel-body" style="padding:12px;max-height:350px;overflow-y:auto;">${templates}</div>
    </div>

    <div class="panel">
      <div class="panel-header"><h2>🛠️ 技能（${ms.skills}）</h2></div>
      <div class="panel-body" style="padding:12px;max-height:350px;overflow-y:auto;">${skills}</div>
    </div>

    <div class="panel">
      <div class="panel-header">
        <h2>📝 最近提案（${es.total}）</h2>
        <a href="#" onclick="switchView('evolution');return false;" style="color:var(--blue);font-size:11px;text-decoration:none;">查看全部 →</a>
      </div>
      <div class="panel-body" style="padding:12px;max-height:350px;overflow-y:auto;">${evoProps || '<div style="color:var(--text-muted);font-size:11px;text-align:center;padding:12px;">暂无提案</div>'}</div>
    </div>

    <div class="panel" style="grid-column:1/-1;">
      <div class="panel-header">
        <h2>🔤 向量模型配置</h2>
        <button class="btn btn-sm" onclick="loadEmbeddingConfig()">🔄 刷新</button>
      </div>
      <div class="panel-body" id="embedding-config-body" style="padding:16px;">
        <div style="color:var(--text-muted);font-size:12px;text-align:center;">加载中...</div>
      </div>
    </div>
  `;
  // Load embedding config
  loadEmbeddingConfig();
}

async function loadEvolutionView() {
  const el = document.getElementById('evolution-full-content');
  if (!el) return;
  el.innerHTML = '<div style="color:var(--text-muted);padding:20px;text-align:center;">加载中...</div>';
  try {
    const params = new URLSearchParams();
    if (STATE.propSearch) params.set('search', STATE.propSearch);
    if (STATE.propCategory) params.set('category', STATE.propCategory);
    if (STATE.propRisk) params.set('risk', STATE.propRisk);
    if (STATE.propStatus) params.set('status', STATE.propStatus);
    params.set('limit', String(STATE.propLimit));
    params.set('offset', String(STATE.propOffset));
    const r = await fetch(`/api/moat/evolution?${params}`);
    const d = await r.json();
    renderEvolutionFullView(el, d);
  } catch (e) {
    el.innerHTML = '<div class="mem-unavailable"><div class="emoji">❌</div><div>加载失败</div></div>';
    console.error(e);
  }
}

function renderEvolutionFullView(el, d) {
  if (!d.available || d.proposals.length === 0) {
    el.innerHTML = '<div class="mem-unavailable" style="padding:40px;"><div class="emoji">🧠</div><div>暂无修改提案</div></div>';
    return;
  }
  const props = d.proposals;
  const s = d.stats;
  const filteredTotal = d.filtered_total ?? props.length;
  const totalPages = Math.ceil(filteredTotal / STATE.propLimit);
  const currentPage = Math.floor(STATE.propOffset / STATE.propLimit) + 1;

  const statusBar = s.total > 0 ? `
    <div style="display:flex;height:4px;border-radius:2px;overflow:hidden;gap:2px;margin-bottom:8px;">
      <div style="flex:${s.pending || 0};background:var(--yellow);border-radius:2px;" title="待处理: ${s.pending || 0}"></div>
      <div style="flex:${s.applied || 0};background:var(--green);border-radius:2px;" title="已应用: ${s.applied || 0}"></div>
      <div style="flex:${s.rejected || 0};background:var(--text-muted);border-radius:2px;" title="已拒绝: ${s.rejected || 0}"></div>
    </div>
    <div style="display:flex;gap:12px;font-size:11px;color:var(--text-muted);margin-bottom:12px;">
      <span>🟡 待处理 ${s.pending || 0}</span>
      <span>🟢 已应用 ${s.applied || 0}</span>
      <span>⚪ 已拒绝 ${s.rejected || 0}</span>
      <span style="margin-left:auto;">📦 总计 ${s.total}${filteredTotal < s.total ? `（筛选后 ${filteredTotal}）` : ''}</span>
    </div>` : '';

  const cats = d.cat_breakdown || [];
  const catHtml = cats.length > 0 ? `
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px;">
      <span class="pi-tag${!STATE.propCategory ? ' active' : ''}" style="font-size:11px;cursor:pointer;" onclick="STATE.propCategory='';loadEvolutionView();">全部</span>
      ${cats.map(c => `<span class="pi-tag${STATE.propCategory === c.name ? ' active' : ''}" style="font-size:11px;cursor:pointer;" onclick="STATE.propCategory='${escapeHtml(c.name)}';STATE.propOffset=0;loadEvolutionView();">${escapeHtml(c.name)} (${c.count})</span>`).join('')}
    </div>` : '';

  const filterBar = `
    <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap;">
      <input type="text" id="evo-search-input" placeholder="🔍 搜索提案..." value="${escapeHtml(STATE.propSearch)}"
        style="flex:1;min-width:150px;background:var(--bg-primary);border:1px solid var(--border);color:var(--text-primary);padding:6px 10px;border-radius:6px;font-size:13px;outline:none;"
        onkeydown="if(event.key==='Enter'){STATE.propSearch=this.value;STATE.propOffset=0;loadEvolutionView();}">
      <select class="prop-filter-select" onchange="STATE.propRisk=this.value;STATE.propOffset=0;loadEvolutionView();" style="font-size:12px;background:var(--bg-primary);border:1px solid var(--border);color:var(--text-primary);padding:4px 8px;border-radius:6px;outline:none;cursor:pointer;">
        <option value="">所有风险</option>
        <option value="high" ${STATE.propRisk === 'high' ? 'selected' : ''}>🔴 高风险</option>
        <option value="medium" ${STATE.propRisk === 'medium' ? 'selected' : ''}>🟡 中风险</option>
        <option value="low" ${STATE.propRisk === 'low' ? 'selected' : ''}>🟢 低风险</option>
      </select>
      <select class="prop-filter-select" onchange="STATE.propStatus=this.value;STATE.propOffset=0;loadEvolutionView();" style="font-size:12px;background:var(--bg-primary);border:1px solid var(--border);color:var(--text-primary);padding:4px 8px;border-radius:6px;outline:none;cursor:pointer;">
        <option value="">所有状态</option>
        <option value="pending" ${STATE.propStatus === 'pending' ? 'selected' : ''}>🟡 待处理</option>
        <option value="applied" ${STATE.propStatus === 'applied' ? 'selected' : ''}>✅ 已应用</option>
        <option value="rejected" ${STATE.propStatus === 'rejected' ? 'selected' : ''}>❌ 已拒绝</option>
      </select>
      <button class="btn btn-sm" onclick="STATE.propSearch='';STATE.propCategory='';STATE.propRisk='';STATE.propStatus='';STATE.propOffset=0;document.getElementById('evo-search-input').value='';loadEvolutionView();" title="清除筛选">✕ 清除</button>
    </div>`;

  const proposalsHtml = props.map(p => {
    const risk = p.risk || 'low';
    const riskIcon = risk === 'high' ? '🔴' : risk === 'medium' ? '🟡' : '🟢';
    const status = p.status || 'pending';
    const statusIcon = status === 'applied' ? '✅' : status === 'rejected' ? '❌' : '🟡';
    const cat = p.category || 'other';
    const fileShort = p.file_path ? p.file_path.split('/').slice(-2).join('/') : '';
    const created = p.created_at ? p.created_at.slice(0, 10) : '';
    return `<div class="mem-item" style="cursor:pointer;" onclick="showProposalDetail(${JSON.stringify(p).replace(/"/g, '&quot;')})">
      <div class="mem-item-title">
        ${statusIcon} ${escapeHtml(p.title || '未命名')}
        <span class="mem-badge cat-${cat}">${cat}</span>
        <span class="mem-badge source-template" style="font-size:9px;">${riskIcon} ${risk}</span>
      </div>
      <div class="mem-item-desc">${escapeHtml((p.description || '').slice(0, 120))}</div>
      <div class="mem-item-meta">
        ${fileShort ? `<span>📄 ${escapeHtml(fileShort)}</span>` : ''}
        ${created ? `<span>📅 ${created}</span>` : ''}
        <span>👆 查看详情</span>
      </div>
    </div>`;
  }).join('');

  const pagination = totalPages > 1 ? `
    <div style="display:flex;align-items:center;justify-content:center;gap:12px;margin-top:12px;font-size:12px;">
      <button class="btn btn-sm" onclick="if(STATE.propOffset>0){STATE.propOffset-=STATE.propLimit;loadEvolutionView();}" ${STATE.propOffset <= 0 ? 'disabled style="opacity:0.4"' : ''}>◀ 上一页</button>
      <span style="color:var(--text-muted);">${currentPage} / ${totalPages}</span>
      <button class="btn btn-sm" onclick="if(STATE.propOffset+STATE.propLimit<filteredTotal){STATE.propOffset+=STATE.propLimit;loadEvolutionView();}" ${STATE.propOffset+STATE.propLimit >= filteredTotal ? 'disabled style="opacity:0.4"' : ''}>下一页 ▶</button>
    </div>` : '';

  el.innerHTML = `
    <div class="panel">
      <div class="panel-header">
        <h2>📝 进化提案</h2>
        <div style="font-size:20px;font-weight:700;color:white;">${s.total}</div>
      </div>
      <div class="panel-body" style="padding:16px;">
        ${statusBar}
        ${filterBar}
        ${catHtml}
        <div style="max-height:400px;overflow-y:auto;">${proposalsHtml}</div>
        ${pagination}
      </div>
    </div>
  `;
}

async function loadProjectFull() {
  const el = document.getElementById('project-full-content');
  if (!el) return;
  el.innerHTML = '<div style="color:var(--text-muted);padding:20px;text-align:center;">加载中...</div>';
  try {
    const r = await fetch('/api/moat/project-info');
    const d = await r.json();
    renderProjectFullView(el, d);
  } catch (e) {
    el.innerHTML = '<div class="mem-unavailable"><div class="emoji">❌</div><div>加载失败</div></div>';
  }
}

function renderProjectFullView(el, d) {
  // Reuse existing project info rendering but in full view
  const inner = document.createElement('div');
  inner.id = 'project-info';
  document.getElementById('project-full-content')?.appendChild(inner);
  // Remove after render
  renderProjectInfo(d);
  if (inner.parentNode) inner.parentNode.removeChild(inner);

  // Actually just render directly
  const langs = (d.languages || []).map(l => {
    const pct = d.total_files > 0 ? ((l.count / d.total_files) * 100).toFixed(1) : 0;
    const barW = Math.min(100, Math.max(2, pct));
    return `<div style="display:flex;align-items:center;gap:8px;padding:4px 0;">
      <span style="width:80px;font-size:12px;color:var(--text-secondary);">${escapeHtml(l.name)}</span>
      <div style="flex:1;height:8px;background:var(--bg-primary);border-radius:4px;overflow:hidden;">
        <div style="height:100%;width:${barW}%;background:var(--blue);border-radius:4px;"></div>
      </div>
      <span style="width:50px;text-align:right;font-size:11px;color:var(--text-muted);">${l.count}</span>
    </div>`;
  }).join('');

  const gitInfo = d.git ? `
    <div style="margin-top:12px;">
      <div class="mem-detail-row"><span class="dl">分支</span><span class="dv">${escapeHtml(d.git.branch || '-')}</span></div>
      <div class="mem-detail-row"><span class="dl">最后提交</span><span class="dv" style="font-size:11px;">${escapeHtml(d.git.last_commit || '-')}</span></div>
      <div class="mem-detail-row"><span class="dl">状态</span><span class="dv">${d.git.dirty ? '<span class="pi-tag dirty">有未提交修改</span>' : '<span class="pi-tag git">干净</span>'}</span></div>
    </div>` : '';

  el.innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
      <div class="panel">
        <div class="panel-header"><h2>📂 基本信息</h2></div>
        <div class="panel-body" style="padding:16px;">
          <div class="mem-detail-row"><span class="dl">项目名</span><span class="dv" style="font-size:16px;font-weight:600;">${escapeHtml(d.name || '-')}</span></div>
          <div class="mem-detail-row"><span class="dl">类型</span><span class="dv"><span class="pi-tag">${escapeHtml(d.project_type || '-')}</span></span></div>
          <div class="mem-detail-row"><span class="dl">路径</span><span class="dv mono" style="font-size:11px;">${escapeHtml(d.path || '-')}</span></div>
          <div class="mem-detail-row"><span class="dl">大小</span><span class="dv">${escapeHtml(d.size || '-')}</span></div>
          <div class="mem-detail-row"><span class="dl">总文件</span><span class="dv" style="font-size:16px;font-weight:600;">${d.total_files || 0}</span></div>
          <div class="mem-detail-row"><span class="dl">总行数</span><span class="dv" style="font-size:16px;font-weight:600;">${(d.total_lines || 0).toLocaleString()}</span></div>
          ${gitInfo}
        </div>
      </div>
      <div class="panel">
        <div class="panel-header"><h2>🔤 语言分布</h2></div>
        <div class="panel-body" style="padding:16px;">${langs || '<div style="color:var(--text-muted);">暂无数据</div>'}</div>
      </div>
    </div>
  `;
}

async function loadSensorStats() {
  const el = document.getElementById('sensor-stats');
  if (!el) return;
  try {
    const r = await fetch('/api/moat/sensors');
    const d = await r.json();
    const s = d.stats || {};
    el.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:16px;">
        <div style="text-align:center;padding:16px;background:var(--bg-primary);border-radius:8px;border:1px solid var(--border);">
          <div style="font-size:28px;font-weight:700;color:white;">${s.total_components || 0}</div>
          <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">📦 监控组件</div>
        </div>
        <div style="text-align:center;padding:16px;background:var(--bg-primary);border-radius:8px;border:1px solid var(--border);">
          <div style="font-size:28px;font-weight:700;color:var(--green);">${s.injected_sensors || 0}</div>
          <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">📡 已注入传感器</div>
        </div>
        <div style="text-align:center;padding:16px;background:var(--bg-primary);border-radius:8px;border:1px solid var(--border);">
          <div style="font-size:28px;font-weight:700;color:var(--green);">${s.healthy || 0}</div>
          <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">✅ 运行正常</div>
        </div>
        <div style="text-align:center;padding:16px;background:var(--bg-primary);border-radius:8px;border:1px solid var(--border);">
          <div style="font-size:28px;font-weight:700;color:var(--yellow);">${s.degraded || 0}</div>
          <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">⚠️ 降级运行</div>
        </div>
        <div style="text-align:center;padding:16px;background:var(--bg-primary);border-radius:8px;border:1px solid var(--border);">
          <div style="font-size:28px;font-weight:700;color:var(--red);">${s.panics_last_hour || 0}</div>
          <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">🚨 近期告警</div>
        </div>
        <div style="text-align:center;padding:16px;background:var(--bg-primary);border-radius:8px;border:1px solid var(--border);">
          <div style="font-size:28px;font-weight:700;color:var(--blue);">${s.events_total || 0}</div>
          <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">📊 总事件数</div>
        </div>
      </div>
    `;
  } catch (e) {
    el.innerHTML = '<div style="color:var(--text-muted);padding:20px;text-align:center;">加载失败</div>';
  }
}

// ── DOM Shortcuts ──────────────────────────
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);

// ── Helpers ────────────────────────────────
function escapeHtml(t) {
  const d = document.createElement('div');
  d.textContent = t;
  return d.innerHTML;
}

function shortId(id, maxLen) {
  if (!id || id.length <= maxLen) return id;
  const parts = id.split(':');
  const file = parts[0] || '';
  const func = parts[1] || '';
  if (file.length > 30) {
    return '...' + file.slice(-27) + ':' + func;
  }
  return id.slice(0, maxLen - 3) + '...';
}

// ── Embedding Config ─────────────────────
async function loadEmbeddingConfig() {
  const el = document.getElementById('embedding-config-body');
  if (!el) return;
  try {
    const r = await fetch('/api/moat/embedding-config');
    const d = await r.json();
    renderEmbeddingConfig(el, d);
  } catch (e) {
    el.innerHTML = '<div style="color:var(--text-muted);padding:12px;text-align:center;">加载失败</div>';
  }
}

function renderEmbeddingConfig(el, d) {
  const cfg = d.config || {};
  const hasConfig = cfg.base_url || cfg.model;
  const maskedKey = cfg.api_key ? cfg.api_key.slice(0, 8) + '...' + cfg.api_key.slice(-4) : '';
  el.innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">
      <div class="mem-detail-row"><span class="dl">接口地址</span><span class="dv mono" style="font-size:11px;">${escapeHtml(cfg.base_url || '未配置')}</span></div>
      <div class="mem-detail-row"><span class="dl">模型</span><span class="dv">${escapeHtml(cfg.model || '未配置')}</span></div>
      <div class="mem-detail-row"><span class="dl">API Key</span><span class="dv">${cfg.api_key ? '🔑 ' + maskedKey : '未配置'}</span></div>
      <div class="mem-detail-row"><span class="dl">状态</span><span class="dv">${hasConfig ? '<span style="color:var(--green);">✅ 已配置</span>' : '<span style="color:var(--text-muted);">⏸ 未配置</span>'}</span></div>
    </div>
    <div style="border-top:1px solid var(--border);padding-top:12px;">
      <div style="font-size:13px;font-weight:500;margin-bottom:8px;">✏️ 编辑配置</div>
      <div style="display:flex;flex-direction:column;gap:8px;">
        <div style="display:flex;gap:8px;align-items:center;">
          <span style="font-size:11px;color:var(--text-secondary);width:80px;">Base URL</span>
          <input type="text" id="emb-base-url" value="${escapeHtml(cfg.base_url || '')}" placeholder="https://api.openai.com/v1"
            style="flex:1;background:var(--bg-primary);border:1px solid var(--border);color:var(--text-primary);padding:6px 10px;border-radius:6px;font-size:12px;outline:none;">
        </div>
        <div style="display:flex;gap:8px;align-items:center;">
          <span style="font-size:11px;color:var(--text-secondary);width:80px;">模型名</span>
          <input type="text" id="emb-model" value="${escapeHtml(cfg.model || '')}" placeholder="text-embedding-3-small"
            style="flex:1;background:var(--bg-primary);border:1px solid var(--border);color:var(--text-primary);padding:6px 10px;border-radius:6px;font-size:12px;outline:none;">
        </div>
        <div style="display:flex;gap:8px;align-items:center;">
          <span style="font-size:11px;color:var(--text-secondary);width:80px;">API Key</span>
          <input type="password" id="emb-api-key" value="${escapeHtml(cfg.api_key || '')}" placeholder="sk-..."
            style="flex:1;background:var(--bg-primary);border:1px solid var(--border);color:var(--text-primary);padding:6px 10px;border-radius:6px;font-size:12px;outline:none;">
        </div>
        <div style="display:flex;gap:8px;justify-content:flex-end;">
          <button class="btn btn-sm" onclick="document.getElementById('emb-base-url').value='';document.getElementById('emb-model').value='';document.getElementById('emb-api-key').value='';">✕ 清空</button>
          <button class="btn btn-primary btn-sm" onclick="saveEmbeddingConfig()">💾 保存配置</button>
        </div>
      </div>
    </div>`;
}

async function saveEmbeddingConfig() {
  const baseUrl = document.getElementById('emb-base-url')?.value?.trim() || '';
  const model = document.getElementById('emb-model')?.value?.trim() || '';
  const apiKey = document.getElementById('emb-api-key')?.value?.trim() || '';
  try {
    const r = await fetch('/api/moat/embedding-config', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({base_url: baseUrl, model: model, api_key: apiKey}),
    });
    const d = await r.json();
    if (d.success) {
      toast('✅ 向量模型配置已保存', 'success');
      loadEmbeddingConfig();
    } else {
      toast('❌ 保存失败: ' + (d.error || '未知错误'), 'error');
    }
  } catch (e) {
    toast('❌ 保存失败: ' + e.message, 'error');
  }
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
    const r = await fetch('/api/moat/sensors?t=' + Date.now());
    STATE.data = await r.json();
    render();
    document.getElementById('last-updated').textContent = fmtTime(new Date().toISOString());
  } catch (e) {
    console.error('加载失败:', e);
  }
}

// ── Load Project Info ───────────────────
async function loadProjectInfo() {
  const el = document.getElementById('project-info');
  if (!el) return;
  el.innerHTML = '<div style="color:var(--text-muted);padding:12px;">加载中...</div>';
  try {
    const r = await fetch('/api/moat/project-info');
    const d = await r.json();
    renderProjectInfo(d);
  } catch (e) {
    el.innerHTML = '<div class="mem-unavailable"><div class="emoji">❌</div><div>加载失败</div></div>';
  }
}

// ── Load Memory (tab-aware) ──────────────
function loadMemoryTab() {
  if (STATE.memTab === 'evolution') {
    loadEvolution();
  } else if (STATE.memTab === 'all') {
    loadAllMemory();
  } else {
    loadMemory();
  }
}

function onMemTabChange(val) {
  STATE.memTab = val;
  STATE.propSearch = '';
  STATE.propCategory = '';
  STATE.propRisk = '';
  STATE.propStatus = '';
  STATE.propOffset = 0;
  loadMemoryTab();
}

// ── Proposal Filter ──────────────────────
function onPropFilter(key, val) {
  const stateKey = 'prop' + key.charAt(0).toUpperCase() + key.slice(1);
  STATE[stateKey] = val;
  STATE.propOffset = 0;
  loadEvolution();
}

// ── Load All Memory ─────────────────────
async function loadAllMemory() {
  const el = document.getElementById('memory-info');
  if (!el) return;
  el.innerHTML = '<div style="color:var(--text-muted);padding:12px;">加载中...</div>';
  try {
    const [memR, evoR] = await Promise.all([
      fetch('/api/moat/memory'),
      fetch('/api/moat/evolution?limit=5')
    ]);
    const mem = await memR.json();
    const evo = await evoR.json();
    renderAllMemory(mem, evo);
  } catch (e) {
    el.innerHTML = '<div class="mem-unavailable"><div class="emoji">❌</div><div>加载失败</div></div>';
    console.error(e);
  }
}

function renderAllMemory(mem, evo) {
  const el = document.getElementById('memory-info');
  if (!el) return;
  const ms = mem.available ? mem.stats : { redlines: 0, lessons: 0, templates: 0, skills: 0, total: 0 };
  const es = evo.available ? evo.stats : { pending: 0, applied: 0, rejected: 0, total: 0 };
  const redlines = (mem.recent_redlines || []).map(r => {
    const sev = r.severity || 'info';
    const icon = sev === 'critical' ? '🔴' : sev === 'warning' ? '🟡' : '🔵';
    const cat = r.category || 'general';
    return `<div class="mem-item mem-severity-${sev}" onclick='showMemoryDetail(JSON.parse(decodeURIComponent("${encodeURIComponent(JSON.stringify(r))}")), "redline")' style="cursor:pointer;">
      <div class="mem-item-title">${icon} ${escapeHtml(r.title || '未命名')} <span class="mem-badge cat-${cat}">${cat}</span></div>
      <div class="mem-item-desc">${escapeHtml((r.description || '').slice(0, 120))}</div>
    </div>`;
  }).join('') || '<div style="color:var(--text-muted);font-size:11px;padding:4px 0;">暂无红线</div>';
  const lessons = (mem.recent_lessons || []).map(l => {
    return `<div class="mem-item mem-severity-warning" onclick='showMemoryDetail(JSON.parse(decodeURIComponent("${encodeURIComponent(JSON.stringify(l))}")), "lesson")' style="cursor:pointer;">
      <div class="mem-item-title">⚠️ ${escapeHtml((l.error_summary || l.title || '未知错误').slice(0, 80))}</div>
    </div>`;
  }).join('') || '<div style="color:var(--text-muted);font-size:11px;padding:4px 0;">暂无踩坑</div>';
  const evoProps = (evo.proposals || []).slice(0, 5).map(p => {
    const risk = p.risk === 'high' ? '🔴' : p.risk === 'medium' ? '🟡' : '🟢';
    return `<div class="mem-item" style="cursor:pointer;" onclick="showProposalDetail(${JSON.stringify(p).replace(/"/g, '&quot;')})">
      <div class="mem-item-title">${risk} ${escapeHtml(p.title || '未命名').slice(0, 60)} <span class="mem-badge cat-${p.category || 'other'}">${p.category || 'other'}</span></div>
    </div>`;
  }).join('') || '';
  el.innerHTML = `
    <div style="margin-bottom:12px;">
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;">
        <div style="flex:1;min-width:70px;text-align:center;padding:8px 4px;background:var(--bg-primary);border-radius:6px;border:1px solid var(--border);">
          <div style="font-size:18px;font-weight:700;color:var(--red);">${ms.redlines}</div>
          <div style="font-size:10px;color:var(--text-muted);">🔴 红线</div>
        </div>
        <div style="flex:1;min-width:70px;text-align:center;padding:8px 4px;background:var(--bg-primary);border-radius:6px;border:1px solid var(--border);">
          <div style="font-size:18px;font-weight:700;color:var(--yellow);">${ms.lessons}</div>
          <div style="font-size:10px;color:var(--text-muted);">⚠️ 踩坑</div>
        </div>
        <div style="flex:1;min-width:70px;text-align:center;padding:8px 4px;background:var(--bg-primary);border-radius:6px;border:1px solid var(--border);">
          <div style="font-size:18px;font-weight:700;color:var(--blue);">${ms.templates}</div>
          <div style="font-size:10px;color:var(--text-muted);">📋 模板</div>
        </div>
        <div style="flex:1;min-width:70px;text-align:center;padding:8px 4px;background:var(--bg-primary);border-radius:6px;border:1px solid var(--border);">
          <div style="font-size:18px;font-weight:700;color:var(--green);">${ms.skills}</div>
          <div style="font-size:10px;color:var(--text-muted);">🛠️ 技能</div>
        </div>
        <div style="flex:1;min-width:70px;text-align:center;padding:8px 4px;background:var(--bg-primary);border-radius:6px;border:1px solid var(--border);">
          <div style="font-size:18px;font-weight:700;color:white;">${es.total}</div>
          <div style="font-size:10px;color:var(--text-muted);">📝 提案</div>
        </div>
      </div>
    </div>
    <div class="mem-section-title">🔴 红线（${ms.redlines}）</div>
    <div style="max-height:150px;overflow-y:auto;margin-bottom:10px;">${redlines}</div>
    <div class="mem-section-title">⚠️ 踩坑（${ms.lessons}）</div>
    <div style="max-height:100px;overflow-y:auto;margin-bottom:10px;">${lessons}</div>
    <div class="mem-section-title">📝 最近提案（${es.total}）</div>
    <div style="max-height:150px;overflow-y:auto;">${evoProps || '<div style="color:var(--text-muted);font-size:11px;padding:4px 0;">暂无提案</div>'}</div>
    ${evoProps ? '<div style="text-align:center;margin-top:6px;"><a href="#" onclick="onMemTabChange(\'evolution\');return false;" style="color:var(--blue);font-size:11px;text-decoration:none;">查看全部' + es.total + '条提案 →</a></div>' : ''}
  `;
}

// ── Load Evolution (代码修改历史) ────────
async function loadEvolution() {
  const el = document.getElementById('memory-info');
  if (!el) return;
  el.innerHTML = '<div style="color:var(--text-muted);padding:12px;">加载中...</div>';
  try {
    const params = new URLSearchParams();
    if (STATE.propSearch) params.set('search', STATE.propSearch);
    if (STATE.propCategory) params.set('category', STATE.propCategory);
    if (STATE.propRisk) params.set('risk', STATE.propRisk);
    if (STATE.propStatus) params.set('status', STATE.propStatus);
    params.set('limit', String(STATE.propLimit));
    params.set('offset', String(STATE.propOffset));
    const r = await fetch(`/api/moat/evolution?${params}`);
    const d = await r.json();
    renderEvolution(d);
  } catch (e) {
    el.innerHTML = '<div class="mem-unavailable"><div class="emoji">❌</div><div>加载失败</div></div>';
    console.error(e);
  }
}

function renderEvolution(d) {
  const el = document.getElementById('memory-info');
  if (!el) return;

  if (!d.available || (d.proposals.length === 0 && d.json_proposals.length === 0)) {
    el.innerHTML = `
      <div class="mem-unavailable">
        <div class="emoji">🧠</div>
        <div style="font-size:14px;font-weight:500;color:var(--text-secondary);margin-bottom:4px;">暂无修改历史</div>
        <div style="font-size:12px;color:var(--text-muted);">进化系统会自动扫描代码并生成改进提案</div>
      </div>`;
    return;
  }

  const props = d.proposals.length > 0 ? d.proposals : d.json_proposals;
  const s = d.stats;
  const filteredTotal = d.filtered_total ?? props.length;
  const totalPages = Math.ceil(filteredTotal / STATE.propLimit);
  const currentPage = Math.floor(STATE.propOffset / STATE.propLimit) + 1;

  // 状态统计
  const statusBar = s.total > 0 ? `
    <div style="display:flex;height:4px;border-radius:2px;overflow:hidden;gap:2px;margin-bottom:8px;">
      <div style="flex:${s.pending || 0};background:var(--yellow);border-radius:2px;" title="待处理: ${s.pending || 0}"></div>
      <div style="flex:${s.applied || 0};background:var(--green);border-radius:2px;" title="已应用: ${s.applied || 0}"></div>
      <div style="flex:${s.rejected || 0};background:var(--text-muted);border-radius:2px;" title="已拒绝: ${s.rejected || 0}"></div>
    </div>
    <div style="display:flex;gap:12px;font-size:10px;color:var(--text-muted);margin-bottom:10px;">
      <span>🟡 待处理 ${s.pending || 0}</span>
      <span>🟢 已应用 ${s.applied || 0}</span>
      <span>⚪ 已拒绝 ${s.rejected || 0}</span>
      <span style="margin-left:auto;">📦 总计 ${s.total}</span>
    </div>` : '';

  // 分类统计（可点击筛选）
  const cats = d.cat_breakdown || [];
  const catHtml = cats.length > 0 ? `
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;">
      <span class="pi-tag${!STATE.propCategory ? ' active' : ''}" style="font-size:10px;cursor:pointer;" onclick="onPropFilter('category', '')">全部</span>
      ${cats.map(c => `<span class="pi-tag${STATE.propCategory === c.name ? ' active' : ''}" style="font-size:10px;cursor:pointer;" onclick="onPropFilter('category', '${escapeHtml(c.name)}')">${escapeHtml(c.name)} (${c.count})</span>`).join('')}
    </div>` : '';

  // 搜索 + 筛选栏
  const filterBar = `
    <div style="display:flex;gap:6px;margin-bottom:10px;flex-wrap:wrap;">
      <input type="text" id="prop-search-input" placeholder="🔍 搜索提案..." value="${escapeHtml(STATE.propSearch)}"
        style="flex:1;min-width:100px;background:var(--bg-primary);border:1px solid var(--border);color:var(--text-primary);padding:4px 8px;border-radius:4px;font-size:12px;outline:none;"
        onkeydown="if(event.key==='Enter'){STATE.propSearch=this.value;STATE.propOffset=0;loadEvolution();}">
      <select class="prop-filter-select" onchange="onPropFilter('risk', this.value)" style="font-size:11px;background:var(--bg-primary);border:1px solid var(--border);color:var(--text-primary);padding:3px 6px;border-radius:4px;outline:none;cursor:pointer;">
        <option value="">所有风险</option>
        <option value="high" ${STATE.propRisk === 'high' ? 'selected' : ''}>🔴 高风险</option>
        <option value="medium" ${STATE.propRisk === 'medium' ? 'selected' : ''}>🟡 中风险</option>
        <option value="low" ${STATE.propRisk === 'low' ? 'selected' : ''}>🟢 低风险</option>
      </select>
      <select class="prop-filter-select" onchange="onPropFilter('status', this.value)" style="font-size:11px;background:var(--bg-primary);border:1px solid var(--border);color:var(--text-primary);padding:3px 6px;border-radius:4px;outline:none;cursor:pointer;">
        <option value="">所有状态</option>
        <option value="pending" ${STATE.propStatus === 'pending' ? 'selected' : ''}>🟡 待处理</option>
        <option value="applied" ${STATE.propStatus === 'applied' ? 'selected' : ''}>✅ 已应用</option>
        <option value="rejected" ${STATE.propStatus === 'rejected' ? 'selected' : ''}>❌ 已拒绝</option>
      </select>
      <button class="btn btn-sm" onclick="STATE.propSearch='';STATE.propCategory='';STATE.propRisk='';STATE.propStatus='';STATE.propOffset=0;document.getElementById('prop-search-input').value='';loadEvolution();" title="清除筛选">✕ 清除</button>
    </div>`;

  // 提案列表
  const proposalsHtml = props.map(p => {
    const risk = p.risk || 'low';
    const riskIcon = risk === 'high' ? '🔴' : risk === 'medium' ? '🟡' : '🟢';
    const status = p.status || 'pending';
    const statusIcon = status === 'applied' ? '✅' : status === 'rejected' ? '❌' : '🟡';
    const cat = p.category || 'other';
    const fileShort = p.file_path ? p.file_path.split('/').slice(-2).join('/') : '';
    const created = p.created_at ? (p.created_at.slice(0, 10)) : '';
    return `<div class="mem-item" style="cursor:pointer;" onclick="showProposalDetail(${JSON.stringify(p).replace(/"/g, '&quot;')})">
      <div class="mem-item-title">
        ${statusIcon} ${escapeHtml(p.title || '未命名')}
        <span class="mem-badge cat-${cat}">${cat}</span>
        <span class="mem-badge source-template" style="font-size:9px;">${riskIcon} ${risk}</span>
      </div>
      <div class="mem-item-desc">${escapeHtml((p.description || '').slice(0, 100))}</div>
      <div class="mem-item-meta">
        ${fileShort ? `<span>📄 ${escapeHtml(fileShort)}</span>` : ''}
        ${created ? `<span>📅 ${created}</span>` : ''}
        <span>👆 查看详情</span>
      </div>
    </div>`;
  }).join('');

  // 分页控制
  const pagination = totalPages > 1 ? `
    <div style="display:flex;align-items:center;justify-content:center;gap:8px;margin-top:8px;font-size:11px;">
      <button class="btn btn-sm" onclick="if(STATE.propOffset>0){STATE.propOffset-=STATE.propLimit;loadEvolution();}" ${STATE.propOffset <= 0 ? 'disabled style="opacity:0.4"' : ''}>◀ 上一页</button>
      <span style="color:var(--text-muted);">${currentPage} / ${totalPages}</span>
      <button class="btn btn-sm" onclick="if(STATE.propOffset+STATE.propLimit<filteredTotal){STATE.propOffset+=STATE.propLimit;loadEvolution();}" ${STATE.propOffset+STATE.propLimit >= filteredTotal ? 'disabled style="opacity:0.4"' : ''}>下一页 ▶</button>
    </div>` : '';

  const filteredLabel = filteredTotal < s.total ? `（筛选后 ${filteredTotal} 条）` : '';

  el.innerHTML = `
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap;">
      <div style="font-size:24px;font-weight:700;">${s.total}</div>
      <div style="font-size:12px;color:var(--text-muted);">条修改提案 ${filteredLabel}</div>
      ${d.db_path ? `<code style="font-size:9px;color:var(--text-muted);background:var(--bg-primary);padding:2px 6px;border-radius:3px;">${escapeHtml(d.db_path.split('/').slice(-3).join('/'))}</code>` : ''}
    </div>
    ${statusBar}
    ${filterBar}
    ${catHtml}
    <div style="max-height:320px;overflow-y:auto;">${proposalsHtml}</div>
    ${pagination}
    </div>
  `;
}

// ── Proposal Detail Modal ───────────────
function showProposalDetail(p) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.onclick = e => { if (e.target === overlay) overlay.remove(); };

  const risk = p.risk || 'low';
  const riskIcon = risk === 'high' ? '🔴' : risk === 'medium' ? '🟡' : '🟢';
  const riskLabel = risk === 'high' ? '高风险' : risk === 'medium' ? '中风险' : '低风险';
  const status = p.status || 'pending';
  const statusLabel = status === 'applied' ? '✅ 已应用' : status === 'rejected' ? '❌ 已拒绝' : '🟡 待处理';
  const created = p.created_at ? p.created_at.slice(0, 19).replace('T', ' ') : '-';
  const applied = p.applied_at ? p.applied_at.slice(0, 19).replace('T', ' ') : '未应用';

  overlay.innerHTML = `
    <div class="modal" style="max-width:560px;">
      <div class="modal-header">
        <h2>📝 ${escapeHtml(p.title || '提案详情')}</h2>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">✕</button>
      </div>
      <div class="modal-body">
        <div class="mem-detail-section">
          <h3>📋 基本信息</h3>
          <div class="mem-detail-row"><span class="dl">标题</span><span class="dv">${escapeHtml(p.title || '未命名')}</span></div>
          <div class="mem-detail-row"><span class="dl">状态</span><span class="dv">${statusLabel}</span></div>
          <div class="mem-detail-row"><span class="dl">风险等级</span><span class="dv">${riskIcon} ${riskLabel}</span></div>
          <div class="mem-detail-row"><span class="dl">分类</span><span class="dv"><span class="mem-badge cat-${p.category || 'other'}">${escapeHtml(p.category || 'other')}</span></span></div>
          <div class="mem-detail-row"><span class="dl">文件</span><span class="dv mono">${escapeHtml(p.file_path || '-')}</span></div>
          <div class="mem-detail-row"><span class="dl">创建时间</span><span class="dv">${created}</span></div>
          <div class="mem-detail-row"><span class="dl">应用时间</span><span class="dv">${applied}</span></div>
          ${p.score != null ? `<div class="mem-detail-row"><span class="dl">评分</span><span class="dv">${p.score}</span></div>` : ''}
        </div>
        <div class="mem-detail-section">
          <h3>📝 描述</h3>
          <div style="font-size:13px;color:var(--text-primary);line-height:1.6;white-space:pre-wrap;">${escapeHtml(p.description || '无描述')}</div>
        </div>
        ${p.patch ? `<div class="mem-detail-section">
          <h3>🔧 补丁</h3>
          <pre style="font-size:11px;color:var(--text-primary);background:#0d1117;padding:8px;border-radius:4px;overflow-x:auto;max-height:200px;">${escapeHtml(p.patch)}</pre>
        </div>` : ''}
      </div>
    </div>`;
  document.body.appendChild(overlay);
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
  const otherComp = s.other_components || 0;
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

  // 显示其他项目传感器数
  const otherLabel = document.getElementById('other-sensors-label');
  if (otherLabel) {
    if (otherComp > 0) {
      otherLabel.textContent = '其他项目: ' + otherComp + ' 个传感器（未显示）';
      otherLabel.style.display = 'block';
    } else {
      otherLabel.style.display = 'none';
    }
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
  let ids = Object.keys(details);

  // 健康网格搜索
  if (STATE.healthSearch) {
    const q = STATE.healthSearch.toLowerCase();
    ids = ids.filter(id => id.toLowerCase().includes(q));
  }

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

function onHealthSearch(val) {
  STATE.healthSearch = val;
  if (STATE.data?.health) renderHealth(STATE.data.health);
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
    const r = await fetch(`/api/moat/sensors/detail?component_id=${encodeURIComponent(componentId)}`);
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
  const stats = data.stats || {};
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
        <h2 title="${escapeHtml(data.component_id)}">📦 ${escapeHtml(shortId(data.component_id, 60))}</h2>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">✕ 关闭</button>
      </div>
      <div class="modal-body">
        <div class="modal-section">
          <div class="modal-section-title">组件信息</div>
          <div class="info-grid">
            <span class="label">状态</span>
            <span class="value ${statusClass}">${statusLabel}</span>
            <span class="label">连续失败</span>
            <span class="value">${failures} 次</span>
            <span class="label">上次成功</span>
            <span class="value">${lastSuc}</span>
            <span class="label">上次失败</span>
            <span class="value">${lastFail}</span>
            ${data.file_path ? `<span class="label">文件路径</span><span class="value mono" style="font-size:11px;">${escapeHtml(data.file_path)}</span>` : ''}
            ${data.func_name ? `<span class="label">函数名</span><span class="value mono">${escapeHtml(data.func_name)}</span>` : ''}
          </div>
        </div>
        ${stats.total_events > 0 ? `
        <div class="modal-section">
          <div class="modal-section-title">统计</div>
          <div class="stats-grid">
            <div class="stat-card"><div class="num">${stats.total_events}</div><div class="lbl">总事件</div></div>
            <div class="stat-card stat-ok"><div class="num">${stats.ok || 0}</div><div class="lbl">✅ 正常</div></div>
            <div class="stat-card stat-degraded"><div class="num">${stats.degraded || 0}</div><div class="lbl">🟡 降级</div></div>
            <div class="stat-card stat-panic"><div class="num">${stats.panic || 0}</div><div class="lbl">🔴 崩溃</div></div>
            <div class="stat-card"><div class="num">${stats.avg_duration_ms || 0}ms</div><div class="lbl">平均耗时</div></div>
            <div class="stat-card stat-ok"><div class="num">${stats.success_rate || 0}%</div><div class="lbl">成功率</div></div>
          </div>
        </div>` : ''}
        <div class="modal-section">
          <div class="modal-section-title">事件历史 (${events.length})</div>
          <div class="modal-event-list">${eventsHtml}</div>
        </div>
      </div>
    </div>`;

  document.body.appendChild(overlay);
}

// ── Project Switcher ────────────────────────
async function loadProjectList() {
  try {
    const r = await fetch('/api/moat/projects');
    const d = await r.json();
    const list = document.getElementById('project-dropdown-list');
    const name = document.getElementById('project-name');
    if (!list) return;
    if (name) {
      const cur = d.projects.find(p => p.current);
      name.textContent = cur ? cur.name : (d.current || 'unknown').split('/').pop();
    }
    list.innerHTML = d.projects.map(p => `
      <div class="project-dropdown-item${p.current ? ' active' : ''}" onclick="switchProject('${escapeHtml(p.path)}')">
        <span class="project-icon">${p.current ? '📂' : '📁'}</span>
        <span>${escapeHtml(p.name)}</span>
        ${p.current ? '<span class="check">✓</span>' : ''}
      </div>
    `).join('');
  } catch (e) {
    console.error('Project list error:', e);
  }
}

async function switchProject(path) {
  try {
    const r = await fetch('/api/moat/projects/switch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    });
    const d = await r.json();
    if (d.success) {
      document.getElementById('project-dropdown').style.display = 'none';
      // Update project name
      const name = document.getElementById('project-name');
      if (name) name.textContent = d.project;
      // Reload all project-specific data
      loadData();
      loadProjectInfo();
      loadProjectList();
      // Also reload the status badge
      fetch('/api/moat/status').then(r => r.json()).then(s => {
        const badge = document.getElementById('status-badge');
        if (badge) badge.textContent = '📂 ' + (s.project || d.project);
      }).catch(() => {});
      // Clear all cached data
      _cachedLeakData = null;
      _cachedEvolutionData = null;
      // If on project-specific views, reload them
      if (STATE.currentView === 'leak') loadLeakCheckView();
      else if (STATE.currentView === 'evolution') loadEvolutionView();
      else if (STATE.currentView === 'project') loadProjectFull();
      else if (STATE.currentView === 'memory') loadMemoryView();
      else if (STATE.currentView === 'sensors') loadSensorStats();
      toast('✅ 已切换到: ' + d.project, 'success');
    } else {
      toast('❌ 切换失败: ' + (d.error || '未知错误'), 'error');
    }
  } catch (e) {
    toast('❌ 切换失败: ' + e.message, 'error');
  }
}

async function checkVersion() {
  try {
    const r = await fetch('/api/moat/version');
    const d = await r.json();
    const el = document.getElementById('sidebar-version');
    if (el) {
      const a = el.querySelector('a');
      if (a) {
        a.textContent = 'v' + d.current;
        a.href = d.pypi_url;
        // 红点
        const existingDot = el.querySelector('.version-dot');
        if (existingDot) existingDot.remove();
        if (d.update_available) {
          const dot = document.createElement('span');
          dot.className = 'version-dot';
          dot.style.cssText = 'display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--red);margin-left:4px;vertical-align:super;';
          a.after(dot);
          a.title = `📦 v${d.latest} 可用!`;
        } else {
          a.title = `v${d.current} ✓ 已是最新`;
        }
      }
    }
    // 更新提示框
    const existing = document.getElementById('version-update-toast');
    if (existing) existing.remove();
    if (d.update_available) {
      const toast = document.createElement('div');
      toast.id = 'version-update-toast';
      toast.style.cssText = `
        position:fixed; bottom:60px; right:20px; z-index:9999;
        background:var(--bg-primary); border:1px solid var(--red); border-radius:8px;
        padding:16px 20px; font-size:13px; max-width:340px;
        box-shadow:0 4px 16px rgba(0,0,0,0.4);
        animation: slideUp 0.3s ease;
      `;
      toast.innerHTML = `
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
          <span style="font-size:20px;">📦</span>
          <span style="font-weight:600;font-size:15px;">有新版本</span>
        </div>
        <div style="font-size:12px;color:var(--text-muted);margin-bottom:10px;">
          v${d.current} → <strong style="color:var(--yellow);font-size:14px;">v${d.latest}</strong>
        </div>
        <div style="display:flex;gap:8px;">
          <button class="btn btn-primary" style="font-size:12px;padding:6px 16px;cursor:pointer;" onclick="doUpgrade()">
            ⬆️ 点击更新
          </button>
          <button class="btn" style="font-size:12px;padding:6px 16px;cursor:pointer;" onclick="this.parentElement.parentElement.remove()">
            稍后
          </button>
        </div>
        <div id="upgrade-status" style="font-size:11px;color:var(--text-muted);margin-top:8px;display:none;"></div>
      `;
      document.body.appendChild(toast);
    }
  } catch (e) {
    // 静默失败
  }
}

async function doUpgrade() {
  const statusEl = document.getElementById('upgrade-status');
  const toast = document.getElementById('version-update-toast');
  if (!statusEl || !toast) return;
  statusEl.style.display = 'block';
  statusEl.textContent = '⏳ 正在升级 moat-ai... (约 30-60 秒)';
  // 禁用按钮
  const btns = toast.querySelectorAll('button');
  btns.forEach(b => b.disabled = true);
  try {
    const r = await fetch('/api/moat/upgrade', { method: 'POST' });
    const d = await r.json();
    if (d.success) {
      statusEl.innerHTML = '✅ 升级成功！<span style="font-size:10px;color:var(--text-muted);">请刷新页面</span>';
      // 3 秒后提示刷新
      setTimeout(() => {
        statusEl.innerHTML += ' <a href="javascript:location.reload()" style="color:var(--blue);">🔄 立即刷新</a>';
      }, 3000);
    } else {
      statusEl.innerHTML = '❌ 升级失败: ' + escapeHtml(d.error || d.stderr || '未知错误');
      btns.forEach(b => b.disabled = false);
    }
  } catch (e) {
    statusEl.innerHTML = '❌ 升级失败: ' + escapeHtml(e.message);
    btns.forEach(b => b.disabled = false);
  }
}

function toggleProjectDropdown() {
  const dd = document.getElementById('project-dropdown');
  const arrow = document.querySelector('.project-arrow');
  if (!dd) return;
  const isOpen = dd.style.display !== 'none';
  dd.style.display = isOpen ? 'none' : 'block';
  if (arrow) arrow.classList.toggle('open', !isOpen);
  if (!isOpen) loadProjectList();
}

// Close dropdown when clicking outside
document.addEventListener('click', function(e) {
  const selector = document.getElementById('project-selector');
  const dd = document.getElementById('project-dropdown');
  if (selector && dd && !selector.contains(e.target)) {
    dd.style.display = 'none';
    const arrow = document.querySelector('.project-arrow');
    if (arrow) arrow.classList.remove('open');
  }
});

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

// ── Project Info ───────────────────────
function renderProjectInfo(d) {
  const el = document.getElementById('project-info');
  if (!el) return;

  const git = d.git || {};
  const langs = d.languages || [];

  // 语言条形图数据
  const langColors = {
    Python: '#3572A5', JavaScript: '#f1e05a', TypeScript: '#3178c6',
    TSX: '#3178c6', JSX: '#61dafb', JSON: '#40d47e', YAML: '#cb171e',
    Markdown: '#083fa1', CSS: '#563d7c', HTML: '#e34c26', Shell: '#89e051',
    SQL: '#e38c00', Go: '#00ADD8', Rust: '#dea584', Java: '#b07219', Ruby: '#701516',
  };
  const totalLang = langs.reduce((s, l) => s + l.count, 0);
  const langBarHtml = langs.length > 0
    ? `<div class="lang-bar">${langs.map(l => {
        const pct = (l.count / totalLang * 100).toFixed(1);
        const color = langColors[l.name] || '#8b949e';
        return `<div class="lang-bar-seg" style="width:${pct}%;background:${color};" title="${l.name}: ${l.count} files"></div>`;
      }).join('')}</div>
      <div style="margin-top:4px;display:flex;gap:8px;flex-wrap:wrap;">
        ${langs.map(l => {
          const color = langColors[l.name] || '#8b949e';
          return `<span style="font-size:11px;color:${color};">● ${l.name} (${l.count})</span>`;
        }).join('')}
      </div>`
    : '<div style="font-size:12px;color:var(--text-muted);">未检测到代码文件</div>';

  el.innerHTML = `
    <div class="pi-row">
      <span class="pi-label">项目名</span>
      <span class="pi-value mono">${escapeHtml(d.name)}</span>
    </div>
    <div class="pi-row">
      <span class="pi-label">路径</span>
      <span class="pi-value mono" style="font-size:11px;word-break:break-all;">${escapeHtml(d.path)}</span>
    </div>
    <div class="pi-row">
      <span class="pi-label">类型</span>
      <span class="pi-value"><span class="pi-tag">${escapeHtml(d.project_type)}</span></span>
    </div>
    <div class="pi-row">
      <span class="pi-label">文件数</span>
      <span class="pi-value">${d.total_files} 个文件</span>
    </div>
    <div class="pi-row">
      <span class="pi-label">代码行数</span>
      <span class="pi-value">${d.total_lines > 0 ? d.total_lines.toLocaleString() + ' 行' : '统计中...'}</span>
    </div>
    <div class="pi-row">
      <span class="pi-label">项目大小</span>
      <span class="pi-value">${escapeHtml(d.size)}</span>
    </div>
    <div class="pi-row">
      <span class="pi-label">语言分布</span>
      <span class="pi-value" style="flex:1;">${langBarHtml}</span>
    </div>
    ${git.has_git ? `
    <div class="pi-row">
      <span class="pi-label">Git</span>
      <span class="pi-value">
        <span class="pi-tag git">🌿 ${escapeHtml(git.branch)}</span>
        ${git.dirty ? '<span class="pi-tag dirty">⚠️ 有未提交改动</span>' : '<span class="pi-tag git">✅ 干净</span>'}
      </span>
    </div>
    ${git.last_commit ? `<div class="pi-row"><span class="pi-label">最新提交</span><span class="pi-value mono" style="font-size:11px;">${escapeHtml(git.last_commit)}</span></div>` : ''}
    ` : ''}
  `;
}

// ── Memory Detail Modal ─────────────
function showMemoryDetail(item, type) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.onclick = e => { if (e.target === overlay) overlay.remove(); };

  const sev = item.severity || 'info';
  const cat = item.category || 'general';
  const src = item.source || 'unknown';
  const created = item.created_at ? item.created_at.slice(0, 19).replace('T', ' ') : '-';
  const updated = item.updated_at ? item.updated_at.slice(0, 19).replace('T', ' ') : '-';

  let bodyHtml = '';
  if (type === 'redline') {
    bodyHtml = `
      <div class="mem-detail-section">
        <h3>📋 基本信息</h3>
        <div class="mem-detail-row"><span class="dl">标题</span><span class="dv">${escapeHtml(item.title || '未命名')}</span></div>
        <div class="mem-detail-row"><span class="dl">严重程度</span><span class="dv">${sev === 'critical' ? '🔴 致命' : sev === 'warning' ? '🟡 警告' : '🔵 信息'}</span></div>
        <div class="mem-detail-row"><span class="dl">分类</span><span class="dv"><span class="mem-badge cat-${cat}">${cat}</span></span></div>
        <div class="mem-detail-row"><span class="dl">来源</span><span class="dv"><span class="mem-badge source-${src}">${src}</span></span></div>
        <div class="mem-detail-row"><span class="dl">创建时间</span><span class="dv">${created}</span></div>
        <div class="mem-detail-row"><span class="dl">更新时间</span><span class="dv">${updated}</span></div>
      </div>
      ${item.description ? `
      <div class="mem-detail-section">
        <h3>📝 描述</h3>
        <div style="font-size:13px;color:var(--text-primary);line-height:1.6;">${escapeHtml(item.description)}</div>
      </div>` : ''}
      ${item.file_glob ? `
      <div class="mem-detail-section">
        <h3>📁 关联文件</h3>
        <code style="font-size:12px;color:var(--blue);">${escapeHtml(item.file_glob)}</code>
      </div>` : ''}
    `;
  } else if (type === 'template' || type === 'skill') {
    const title = item.title || item.name || '未命名';
    const icon = type === 'template' ? '📋' : '🛠️';
    const elements = item.elements || {};
    const steps = elements.steps || [];
    const usage = elements.usage || '';
    const principles = item.principles || [];
    const negExamples = item.negative_examples || [];
    const importance = item.importance || '';
    const domain = item.domain || item.category || '';

    let contentHtml = '';
    // 步骤
    if (steps.length > 0) {
      contentHtml += `<div style="margin-bottom:10px;"><strong>📋 步骤</strong><ol style="margin:6px 0 0 16px;padding:0;font-size:12px;">`;
      contentHtml += steps.map(s => `<li style="margin-bottom:4px;">${escapeHtml(s)}</li>`).join('');
      contentHtml += `</ol></div>`;
    }
    // 用法
    if (usage) {
      contentHtml += `<div style="margin-bottom:10px;"><strong>💡 用法</strong><div style="font-size:12px;margin-top:4px;">${escapeHtml(usage)}</div></div>`;
    }
    // 原则
    if (principles.length > 0) {
      contentHtml += `<div style="margin-bottom:10px;"><strong>📏 原则</strong><ul style="margin:6px 0 0 16px;padding:0;font-size:12px;">`;
      contentHtml += principles.map(p => `<li style="margin-bottom:3px;">${escapeHtml(p)}</li>`).join('');
      contentHtml += `</ul></div>`;
    }
    // 反例
    if (negExamples.length > 0) {
      contentHtml += `<div style="margin-bottom:10px;"><strong>⚠️ 反例</strong>`;
      negExamples.forEach(ex => {
        contentHtml += `<div style="font-size:11px;background:var(--red-bg);padding:6px 8px;border-radius:4px;margin-top:4px;"><div style="color:var(--red);">❌ ${escapeHtml(ex.scenario || '')}</div><div style="color:var(--green);margin-top:2px;">✅ ${escapeHtml(ex.better_approach || '')}</div></div>`;
      });
      contentHtml += `</div>`;
    }

    bodyHtml = `
      <div class="mem-detail-section">
        <h3>${icon} 基本信息</h3>
        <div class="mem-detail-row"><span class="dl">名称</span><span class="dv" style="font-weight:600;">${escapeHtml(title)}</span></div>
        ${domain ? `<div class="mem-detail-row"><span class="dl">领域</span><span class="dv">${escapeHtml(domain)}</span></div>` : ''}
        ${importance ? `<div class="mem-detail-row"><span class="dl">重要性</span><span class="dv">${'★'.repeat(Math.min(importance, 10))} (${importance})</span></div>` : ''}
        <div class="mem-detail-row"><span class="dl">来源</span><span class="dv">${item.source === 'template' ? '📦 内置' : '🔄 自动提取'}</span></div>
        <div class="mem-detail-row"><span class="dl">创建时间</span><span class="dv">${created}</span></div>
      </div>
      ${contentHtml ? `
      <div class="mem-detail-section">
        <h3>📝 详细内容</h3>
        ${contentHtml}
      </div>` : ''}
      ${item.tags && item.tags.length ? `
      <div class="mem-detail-section">
        <h3>🏷️ 标签</h3>
        <div style="display:flex;gap:4px;flex-wrap:wrap;">${item.tags.map(t => `<span class="mem-badge" style="font-size:11px;">${escapeHtml(t)}</span>`).join(' ')}</div>
      </div>` : ''}
    `;
  } else {
    bodyHtml = `
      <div class="mem-detail-section">
        <h3>📋 基本信息</h3>
        <div class="mem-detail-row"><span class="dl">错误</span><span class="dv">${escapeHtml((item.error_summary || item.title || '').slice(0, 100))}</span></div>
        <div class="mem-detail-row"><span class="dl">时间</span><span class="dv">${created}</span></div>
      </div>
      ${item.error_summary ? `
      <div class="mem-detail-section">
        <h3>📝 详情</h3>
        <pre style="font-size:12px;color:var(--text-primary);background:var(--bg-primary);padding:8px;border-radius:4px;overflow-x:auto;white-space:pre-wrap;">${escapeHtml(item.error_summary)}</pre>
      </div>` : ''}
    `;
  }

  const headerIcon = type === 'redline' ? '🔴' : type === 'template' ? '📋' : type === 'skill' ? '🛠️' : '⚠️';
  overlay.innerHTML = `
    <div class="modal" style="max-width:520px;">
      <div class="modal-header">
        <h2>${headerIcon} ${escapeHtml(item.title || item.name || item.error_summary || '记忆详情')}</h2>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">✕</button>
      </div>
      <div class="modal-body">${bodyHtml}</div>
    </div>`;
  document.body.appendChild(overlay);
}

// ── Memory ─────────────────────────────
function renderMemory(d) {
  const el = document.getElementById('memory-info');
  if (!el) return;

  if (!d.available) {
    el.innerHTML = `
      <div class="mem-unavailable">
        <div class="emoji">🧠</div>
        <div style="font-size:14px;font-weight:500;color:var(--text-secondary);margin-bottom:4px;">记忆系统未初始化</div>
        <div style="font-size:12px;">运行 <code style="background:var(--bg-primary);padding:2px 6px;border-radius:3px;">moat memory init</code> 启用</div>
      </div>`;
    return;
  }

  const s = d.stats;
  const rStats = d.redline_stats || {};

  // 红线列表
  const recentRedlines = (d.recent_redlines || []).map(r => {
    const sev = r.severity || 'info';
    const icon = sev === 'critical' ? '🔴' : sev === 'warning' ? '🟡' : '🔵';
    const cat = r.category || 'general';
    const src = r.source || '';
    const created = r.created_at ? r.created_at.slice(0, 10) : '';
    return `<div class="mem-item mem-severity-${sev}" onclick='showMemoryDetail(JSON.parse(decodeURIComponent("${encodeURIComponent(JSON.stringify(r))}")), "redline")' style="cursor:pointer;">
      <div class="mem-item-title">
        ${icon} ${escapeHtml(r.title || '未命名')}
        ${cat !== 'general' ? `<span class="mem-badge cat-${cat}">${cat}</span>` : ''}
        ${src ? `<span class="mem-badge source-${src}">${src}</span>` : ''}
      </div>
      <div class="mem-item-desc">${escapeHtml((r.description || '').slice(0, 80))}</div>
      <div class="mem-item-meta">
        ${created ? `<span>📅 ${created}</span>` : ''}
        <span>👆 点击查看详情</span>
      </div>
    </div>`;
  }).join('');

  // 踩坑列表
  const recentLessons = (d.recent_lessons || []).map(l => {
    const created = l.created_at ? l.created_at.slice(0, 10) : '';
    return `<div class="mem-item mem-severity-warning" onclick='showMemoryDetail(JSON.parse(decodeURIComponent("${encodeURIComponent(JSON.stringify(l))}")), "lesson")' style="cursor:pointer;">
      <div class="mem-item-title">⚠️ ${escapeHtml((l.error_summary || l.title || '未知错误').slice(0, 60))}</div>
      <div class="mem-item-desc">${escapeHtml((l.error_summary || '').slice(0, 100))}</div>
      <div class="mem-item-meta">
        ${created ? `<span>📅 ${created}</span>` : ''}
        <span>👆 点击查看详情</span>
      </div>
    </div>`;
  }).join('');

  // 红线按严重性统计条
  const severityTotal = (rStats.critical || 0) + (rStats.warning || 0) + (rStats.info || 0);
  const severityBar = severityTotal > 0 ? `
    <div style="margin-bottom:12px;">
      <div style="display:flex;height:4px;border-radius:2px;overflow:hidden;gap:2px;">
        <div style="flex:${rStats.critical || 0};max-width:100%;background:var(--red);border-radius:2px;" title="致命: ${rStats.critical || 0}"></div>
        <div style="flex:${rStats.warning || 0};max-width:100%;background:var(--yellow);border-radius:2px;" title="警告: ${rStats.warning || 0}"></div>
        <div style="flex:${rStats.info || 0};max-width:100%;background:var(--blue);border-radius:2px;" title="信息: ${rStats.info || 0}"></div>
      </div>
      <div style="display:flex;gap:12px;margin-top:4px;font-size:10px;color:var(--text-muted);">
        <span>🔴 致命 ${rStats.critical || 0}</span>
        <span>🟡 警告 ${rStats.warning || 0}</span>
        <span>🔵 信息 ${rStats.info || 0}</span>
      </div>
    </div>` : '';

  el.innerHTML = `
    <div class="mem-stats">
      <div class="mem-stat">
        <div class="num red">${s.redlines}</div>
        <div class="lbl">🔴 红线</div>
      </div>
      <div class="mem-stat">
        <div class="num yellow">${s.lessons}</div>
        <div class="lbl">⚠️ 踩坑</div>
      </div>
      <div class="mem-stat">
        <div class="num blue">${s.templates}</div>
        <div class="lbl">📋 模板</div>
      </div>
      <div class="mem-stat">
        <div class="num green">${s.skills}</div>
        <div class="lbl">🛠️ 技能</div>
      </div>
    </div>
    ${recentRedlines ? `<div class="mem-section-title">🔴 红线（${s.redlines}）</div>${severityBar}${recentRedlines}` : ''}
    ${recentLessons ? `<div class="mem-section-title">⚠️ 踩坑（${s.lessons}）</div>${recentLessons}` : ''}
    ${renderTemplatesSection(d)}
    ${renderSkillsSection(d)}
    ${!recentRedlines && !recentLessons && s.templates === 0 && s.skills === 0 ? '<div style="text-align:center;padding:16px;color:var(--text-muted);font-size:12px;">记忆系统运行正常，暂无记录</div>' : ''}
  `;
}

function renderTemplatesSection(d) {
  const templates = d.recent_templates || [];
  if (templates.length === 0) return '';
  const items = templates.map(t => {
    const title = t.title || t.name || '未命名模板';
    const desc = (t.description || t.content || '').slice(0, 100);
    const created = t.created_at ? t.created_at.slice(0, 10) : '';
    return `<div class="mem-item mem-severity-info" onclick='showMemoryDetail(JSON.parse(decodeURIComponent("${encodeURIComponent(JSON.stringify(t))}")), "template")' style="cursor:pointer;">
      <div class="mem-item-title">📋 ${escapeHtml(title)}</div>
      <div class="mem-item-desc">${escapeHtml(desc)}</div>
      <div class="mem-item-meta">
        ${created ? `<span>📅 ${created}</span>` : ''}
        <span>👆 点击查看详情</span>
      </div>
    </div>`;
  }).join('');
  return `<div class="mem-section-title">📋 模板（${templates.length}）</div>${items}`;
}

function renderSkillsSection(d) {
  const skills = d.recent_skills || [];
  if (skills.length === 0) return '';
  const items = skills.map(s => {
    const title = s.title || s.name || '未命名技能';
    const desc = (s.description || s.content || '').slice(0, 100);
    const created = s.created_at ? s.created_at.slice(0, 10) : '';
    return `<div class="mem-item mem-severity-info" onclick='showMemoryDetail(JSON.parse(decodeURIComponent("${encodeURIComponent(JSON.stringify(s))}")), "skill")' style="cursor:pointer;">
      <div class="mem-item-title">🛠️ ${escapeHtml(title)}</div>
      <div class="mem-item-desc">${escapeHtml(desc)}</div>
      <div class="mem-item-meta">
        ${created ? `<span>📅 ${created}</span>` : ''}
        <span>👆 点击查看详情</span>
      </div>
    </div>`;
  }).join('');
  return `<div class="mem-section-title">🛠️ 技能（${skills.length}）</div>${items}`;
}

// ── Leak Detection ─────────────────────────
let _cachedLeakData = null;
let _cachedEvolutionData = null;

async function runLeakCheck() {
  const el = document.getElementById('leak-full-content');
  if (!el) return;
  const btn = document.getElementById('leak-scan-btn');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ 扫描中...'; }
  const modeLabel = STATE.leakScanAi ? '系统模式' : '项目模式';
  el.innerHTML = '<div class="leak-scanning"><div class="spinner"></div><div>正在扫描泄露风险（' + modeLabel + '）...</div><div style="font-size:11px;margin-top:8px;">检测 AI 工具痕迹、敏感文件、符号链接、硬编码路径</div></div>';
  try {
    const r = await fetch('/api/moat/leak-check?scan_ai=' + STATE.leakScanAi + '&t=' + Date.now());
    const d = await r.json();
    if (!d.available) {
      el.innerHTML = '<div class="leak-empty"><div class="emoji">⚠️</div><div>泄露检测不可用</div><div style="font-size:11px;color:var(--text-muted);margin-top:8px;">' + escapeHtml(d.error || 'moat check --leak 未安装或不可用') + '</div></div>';
      return;
    }
    _cachedLeakData = d;
    renderLeakView(el, d);
  } catch (e) {
    el.innerHTML = '<div class="leak-empty"><div class="emoji">❌</div><div>扫描失败</div><div style="font-size:11px;color:var(--text-muted);margin-top:8px;">' + escapeHtml(String(e)) + '</div></div>';
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '🔍 开始扫描'; }
  }
}

function loadLeakCheckView() {
  const el = document.getElementById('leak-full-content');
  if (!el) return;
  if (_cachedLeakData) {
    renderLeakView(el, _cachedLeakData);
  } else {
    el.innerHTML = '<div style="color:var(--text-muted);padding:40px;text-align:center;"><div style="font-size:48px;margin-bottom:12px;">🔒</div><div style="font-size:14px;margin-bottom:8px;">代码泄露风险检测</div><div style="font-size:12px;color:var(--text-muted);margin-bottom:20px;">检测 AI 工具痕迹、敏感文件暴露、符号链接泄露、硬编码路径</div><button class="btn btn-primary" onclick="runLeakCheck()" style="font-size:14px;padding:8px 24px;">🔍 开始扫描</button></div>';
  }
}

function renderLeakView(el, d) {
  const total = d.total_violations || 0;
  const sev = d.by_severity || {};
  const cat = d.by_category || {};
  const violations = d.violations || [];
  const score = d.score ?? 100;
  const passed = d.passed;
  const ts = d.timestamp ? d.timestamp.slice(0, 19).replace('T', ' ') : '';

  const scoreGate = STATE.acceptScoreGate || 0;
  const gateFailed = scoreGate > 0 && score < scoreGate;

  const scoreClass = score >= 80 ? 'good' : score >= 50 ? 'warn' : 'bad';
  const statusIcon = passed ? '✅' : '❌';
  const statusColor = passed ? 'var(--green)' : 'var(--red)';

  // Severity breakdown
  const sevMap = { critical: '🔴', high: '🟠', medium: '🟡', low: '⚪' };
  const catEntries = Object.entries(cat);
  const sevEntries = Object.entries(sev).filter(([k]) => sevMap[k]);

  // Client-side filtering
  let filtered = [...violations];
  if (STATE.leakFilter !== 'all') {
    filtered = filtered.filter(v => (v.severity || 'low') === STATE.leakFilter);
  }
  if (STATE.leakSearch) {
    const q = STATE.leakSearch.toLowerCase();
    filtered = filtered.filter(v =>
      (v.message || '').toLowerCase().includes(q) ||
      (v.file_path || '').toLowerCase().includes(q) ||
      (v.recommendation || '').toLowerCase().includes(q)
    );
  }
  if (STATE.leakCategory) {
    filtered = filtered.filter(v => (v.category || '') === STATE.leakCategory);
  }

  // Build violation items
  const vHtml = filtered.length > 0 ? filtered.map(v => {
    const sevIcon = sevMap[v.severity] || '⚪';
    const sevClass = 'severity-' + (v.severity || 'low');
    const loc = v.file_path ? v.file_path : '';
    const suggestion = v.recommendation || '';
    return `<div class="leak-v-item ${sevClass}" onclick="showLeakDetail(${JSON.stringify(v).replace(/"/g, '&quot;')})">
      <div class="leak-v-icon">${sevIcon}</div>
      <div class="leak-v-content">
        <div class="leak-v-title">${escapeHtml(v.message || '未知风险')}</div>
        ${v.category ? `<div class="leak-v-detail">分类: ${escapeHtml(v.category)}${v.rule ? ' · 规则: ' + escapeHtml(v.rule) : ''}</div>` : ''}
        ${loc ? `<div class="leak-v-file">📄 ${escapeHtml(loc)}${v.line ? ':' + v.line : ''}</div>` : ''}
        ${suggestion ? `<div class="leak-v-suggestion">💡 ${escapeHtml(suggestion)}</div>` : ''}
      </div>
    </div>`;
  }).join('') : '<div class="leak-empty"><div class="emoji">✅</div><div>未找到匹配项</div><div style="font-size:11px;color:var(--text-muted);margin-top:8px;">尝试调整筛选条件</div></div>';

  const sevCards = sevEntries.map(([k, v]) => `
    <div class="leak-stat-card ${k}">
      <div class="num" style="color:${k === 'critical' ? 'var(--red)' : k === 'high' ? '#d29922' : k === 'medium' ? 'var(--yellow)' : 'var(--text-muted)'}">${v}</div>
      <div class="lbl">${sevMap[k] || ''} ${k}</div>
    </div>
  `).join('');

  const catHtml = catEntries.length > 0 ? `
    <div class="leak-cat-bar">
      ${catEntries.map(([k, v]) => `<span class="leak-cat-tag" style="cursor:pointer;" onclick="STATE.leakCategory='${STATE.leakCategory === k ? '' : escapeHtml(k)}';renderLeakView(document.getElementById('leak-full-content'), _cachedLeakData);">${STATE.leakCategory === k ? '✓ ' : ''}${escapeHtml(k)} (${v})</span>`).join('')}
      ${STATE.leakCategory ? `<span class="leak-cat-tag" style="cursor:pointer;border-color:var(--blue);color:var(--blue);" onclick="STATE.leakCategory='';renderLeakView(document.getElementById('leak-full-content'), _cachedLeakData);">✕ 清除分类</span>` : ''}
    </div>` : '';

  // Filter bar
  const filterBar = `
    <div class="leak-filter-bar">
      <input type="text" id="leak-search-input" placeholder="🔍 搜索违规..." value="${escapeHtml(STATE.leakSearch)}"
        onkeydown="if(event.key==='Enter'){STATE.leakSearch=this.value;renderLeakView(document.getElementById('leak-full-content'), _cachedLeakData);}">
      <select onchange="STATE.leakFilter=this.value;renderLeakView(document.getElementById('leak-full-content'), _cachedLeakData);">
        <option value="all" ${STATE.leakFilter === 'all' ? 'selected' : ''}>所有严重度</option>
        <option value="critical" ${STATE.leakFilter === 'critical' ? 'selected' : ''}>🔴 严重</option>
        <option value="high" ${STATE.leakFilter === 'high' ? 'selected' : ''}>🟠 高</option>
        <option value="medium" ${STATE.leakFilter === 'medium' ? 'selected' : ''}>🟡 中</option>
        <option value="low" ${STATE.leakFilter === 'low' ? 'selected' : ''}>⚪ 低</option>
      </select>
      <span class="leak-filter-count">${filtered.length} / ${violations.length} 项</span>
      <button class="btn btn-sm" onclick="STATE.leakSearch='';STATE.leakFilter='all';STATE.leakCategory='';document.getElementById('leak-search-input').value='';renderLeakView(document.getElementById('leak-full-content'), _cachedLeakData);" title="清除筛选">✕ 清除</button>
    </div>`;

  // Show export button
  const exportBtn = document.getElementById('leak-export-btn');
  if (exportBtn) exportBtn.style.display = 'inline-block';

  const modeLabel = _cachedLeakData?.scan_ai ? '🖥️ 系统模式' : '📁 项目模式';

  el.innerHTML = `
    <div class="panel" style="margin-bottom:16px;">
      <div class="panel-header">
        <h2>📊 扫描结果</h2>
        ${ts ? `<span class="leak-timestamp">🕐 ${escapeHtml(ts)}</span>` : ''}
        <span style="font-size:11px;color:var(--text-muted);margin-left:8px;">${modeLabel}</span>
      <div class="panel-body" style="padding:16px;">
        <div style="display:flex;gap:16px;align-items:center;margin-bottom:16px;flex-wrap:wrap;">
          <div style="text-align:center;">
            <div class="leak-score-ring ${scoreClass}">${score}</div>
            <div style="font-size:11px;color:var(--text-muted);">安全评分</div>
          </div>
          <div style="flex:1;min-width:150px;">
            <div style="font-size:16px;font-weight:600;color:${statusColor};">${statusIcon} ${passed ? '通过' : '发现风险'}</div>
            <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">共 ${total} 项违规</div>
          </div>
        </div>
        <div class="leak-summary">${sevCards}</div>
        ${catHtml}
      </div>
    </div>

    <div class="panel">
      <div class="panel-header">
        <h2>📋 违规详情</h2>
        <span class="badge">${filtered.length}</span>
      </div>
      <div class="panel-body" style="padding:12px;">
        ${filterBar}
        <div class="leak-v-list">${vHtml}</div>
      </div>
    </div>
  `;
}

function toggleLeakMode() {
  STATE.leakScanAi = !STATE.leakScanAi;
  const toggle = document.getElementById('leak-mode-toggle');
  if (!toggle) return;
  toggle.querySelectorAll('.leak-mode-btn').forEach(el => {
    el.classList.toggle('active', (el.dataset.mode === 'system') === STATE.leakScanAi);
  });
  // 自动重新扫描
  runLeakCheck();
}

function toggleLeakScope() {
  const body = document.getElementById('leak-scope-body');
  const toggle = document.getElementById('leak-scope-toggle');
  if (!body || !toggle) return;
  body.classList.toggle('collapsed');
  toggle.classList.toggle('collapsed');
}

function exportLeakReport() {
  const d = _cachedLeakData;
  if (!d) return;
  const violations = d.violations || [];
  const sev = d.by_severity || {};
  const ts = d.timestamp ? d.timestamp.slice(0, 19).replace('T', ' ') : new Date().toISOString().slice(0, 19).replace('T', ' ');

  let report = `# Moat 泄漏检测报告\n\n`;
  report += `**扫描时间**: ${ts}\n`;
  report += `**安全评分**: ${d.score ?? 'N/A'}/100\n`;
  report += `**结果**: ${d.passed ? '✅ 通过' : '❌ 发现风险'}\n`;
  report += `**违规总数**: ${d.total_violations || 0}\n\n`;
  report += `## 严重度分布\n\n`;
  report += `| 严重度 | 数量 |\n|--------|------|\n`;
  for (const [k, v] of Object.entries(sev)) {
    if (v > 0) report += `| ${k} | ${v} |\n`;
  }
  report += `\n## 违规详情\n\n`;
  report += `| 严重度 | 消息 | 文件 | 建议 |\n|--------|------|------|------|\n`;
  for (const v of violations) {
    const msg = (v.message || '').replace(/\n/g, ' ');
    const file = (v.file_path || '');
    const sug = (v.recommendation || '').replace(/\n/g, ' ');
    report += `| ${v.severity || 'low'} | ${msg} | ${file} | ${sug} |\n`;
  }

  // Download as file
  const blob = new Blob([report], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `moat-leak-report-${ts.slice(0, 10)}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function showLeakDetail(v) {
  const sevMap = { critical: '🔴', high: '🟠', medium: '🟡', low: '⚪' };
  const icon = sevMap[v.severity] || '⚪';
  const loc = v.file_path ? `${escapeHtml(v.file_path)}${v.line ? ':' + v.line : ''}` : '无';
  const bodyHtml = `
    <div class="info-grid">
      <div class="label">严重程度</div><div class="value ${v.severity === 'critical' ? 'red' : v.severity === 'high' ? 'yellow' : ''}">${icon} ${v.severity || '未知'}</div>
      <div class="label">分类</div><div class="value">${escapeHtml(v.category || '其他')}</div>
      <div class="label">规则</div><div class="value">${escapeHtml(v.rule || '无')}</div>
      ${v.file_path ? `<div class="label">文件</div><div class="value" style="font-family:monospace;font-size:11px;">${loc}</div>` : ''}
      <div class="label" style="align-self:start;">描述</div><div class="value">${escapeHtml(v.message || '无')}</div>
      ${v.recommendation ? `<div class="label" style="align-self:start;">建议</div><div class="value" style="color:var(--yellow);">${escapeHtml(v.recommendation)}</div>` : ''}
    </div>
  `;
  showModal('🔒 泄露详情', bodyHtml);
}

// ── Accept (架构验收) ───────────────────────
let _cachedAcceptData = null;

function loadAcceptView() {
  const el = document.getElementById('accept-full-content');
  if (!el) return;
  if (_cachedAcceptData) {
    renderAcceptView(el, _cachedAcceptData);
  } else {
    el.innerHTML = `<div style="color:var(--text-muted);padding:40px;text-align:center;">
      <div style="font-size:48px;margin-bottom:12px;">🏗️</div>
      <div style="font-size:14px;margin-bottom:8px;">架构验收 8 步法</div>
      <div style="font-size:12px;color:var(--text-muted);margin-bottom:20px;">规则验收 → 目录责任 → 模块演练 → 接口规范 → 框架利用 → 运行证据 → 文档收口 → 版本基线</div>
      <div style="display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-bottom:16px;">
        <button class="btn btn-primary" onclick="runAcceptCheck()" style="font-size:14px;padding:8px 24px;">🔍 开始验收</button>
        <button class="btn" onclick="generateAcceptRules()" style="font-size:14px;padding:8px 24px;" title="生成 architect.yml 规则定义文件，可自定义修改后让验收按你的规则执行">📄 生成规则模板</button>
      </div>
      <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;font-size:12px;color:var(--text-muted);">
        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;background:var(--bg-secondary);padding:4px 10px;border-radius:4px;border:1px solid var(--border-light);" title="勾选后只检测有变更的文件，速度更快（推荐日常使用）；取消勾选则扫描全部文件，更全面但耗时更长">
          <input type="checkbox" id="accept-diff-toggle" checked onchange="STATE.acceptDiffMode=this.checked;" ${STATE.acceptDiffMode !== false ? 'checked' : ''}>
          ⚡ 增量模式（快）
        </label>
        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;background:var(--bg-secondary);padding:4px 10px;border-radius:4px;border:1px solid var(--border-light);" title="设置最低验收分数（0-100），验收结果低于此分数时会显示红色警告，帮助团队把控质量底线">
          <span>🎯 评分门禁</span>
          <input type="number" id="accept-score-gate" value="${STATE.acceptScoreGate || 0}" min="0" max="100" style="width:50px;padding:2px 4px;font-size:12px;border:1px solid var(--border-light);border-radius:3px;background:var(--bg-primary);color:var(--text-primary);" onchange="STATE.acceptScoreGate=parseInt(this.value)||0;">
          <span style="font-size:10px;color:var(--text-muted);">分</span>
        </label>
      </div>

      <div style="margin-top:24px;padding:16px 20px;background:var(--bg-secondary);border-radius:8px;text-align:left;max-width:520px;margin-left:auto;margin-right:auto;">
        <div style="font-size:13px;font-weight:600;color:var(--text-primary);margin-bottom:10px;">📖 使用说明</div>
        <div style="font-size:12px;color:var(--text-muted);line-height:1.7;">
          <div style="margin-bottom:8px;"><strong>1. 开始验收</strong> — 点击「🔍 开始验收」，自动执行 8 步架构检查，大约 1-3 分钟</div>
          <div style="margin-bottom:8px;"><strong>2. 增量 vs 完整</strong> — 日常用「⚡ 增量模式」只检查变更文件（快）；完整检查时取消勾选，扫描全部文件（全面）</div>
          <div style="margin-bottom:8px;"><strong>3. 评分门禁</strong> — 设置最低分数（如 60 分），验收结果低于阈值会显示红色警告，帮助团队把控质量。不设置（默认 0）→ 门禁关闭，只正常展示评分，不会触发门禁检查</div>
          <div style="margin-bottom:8px;"><strong>4. 自定义规则</strong> — 点击「📄 生成规则模板」生成 architect.yml，修改后验收将按你的规则执行</div>
          <div><strong>5. 查看详情</strong> — 每条规则可点击查看违规详情、证据和人工核查项；验收完成后可导出完整报告</div>
        </div>
      </div>
    </div>`;
  }
}

async function runAcceptCheck() {
  const el = document.getElementById('accept-full-content');
  if (!el) return;
  const btn = document.getElementById('accept-scan-btn');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ 验收中...'; }
  const diffMode = STATE.acceptDiffMode !== false;
  const modeLabel = diffMode ? '⚡ 增量模式' : '🔄 完整模式';
  el.innerHTML = '<div class="leak-scanning"><div class="spinner"></div><div>正在执行架构验收...</div><div style="font-size:11px;margin-top:8px;color:var(--yellow);">⏱ 可能需要 1-3 分钟，请耐心等待</div><div style="font-size:11px;margin-top:4px;">' + modeLabel + ' | 检查规则、目录、模块、接口、框架、运行时、文档、基线</div></div>';
  try {
    const r = await fetch('/api/moat/accept?diff=' + diffMode + '&t=' + Date.now());
    const d = await r.json();
    if (!d.available) {
      el.innerHTML = '<div class="leak-empty"><div class="emoji">⚠️</div><div>架构验收不可用</div><div style="font-size:11px;color:var(--text-muted);margin-top:8px;">' + escapeHtml(d.error || '未知错误') + '</div></div>';
      return;
    }
    _cachedAcceptData = d;
    renderAcceptView(el, d);
  } catch (e) {
    el.innerHTML = '<div class="leak-empty"><div class="emoji">❌</div><div>验收失败</div><div style="font-size:11px;color:var(--text-muted);margin-top:8px;">' + escapeHtml(String(e)) + '</div></div>';
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '🔍 开始验收'; }
  }
}

async function generateAcceptRules() {
  try {
    const r = await fetch('/api/moat/accept/generate-rules', { method: 'POST' });
    const d = await r.json();
    if (d.success) {
      toast('✅ ' + d.message, 'success');
    } else {
      toast('❌ 生成失败: ' + (d.error || '未知错误'), 'error');
    }
  } catch (e) {
    toast('❌ 生成失败: ' + e.message, 'error');
  }
}

function renderAcceptView(el, d) {
  const score = d.overall_score ?? 0;
  const passed = d.passed;
  const totalAuto = d.total_auto || 0;
  const totalManual = d.total_manual || 0;
  const passedAuto = d.passed_auto || 0;
  const execTime = d.execution_time || 0;
  const ts = d.timestamp ? d.timestamp.slice(0, 19).replace('T', ' ') : '';
  const rules = d.rules || [];
  const proj = d.project || '';
  const totalViolations = d.total_violations || 0;
  const totalEvidence = d.total_evidence || 0;
  const totalManualItems = d.total_manual_items || 0;

  const scoreClass = score >= 80 ? 'good' : score >= 50 ? 'warn' : 'bad';
  const statusIcon = passed ? '✅' : '❌';
  const statusColor = passed ? 'var(--green)' : 'var(--red)';

  // 按步骤分组
  const stepNames = {1:'规则验收',2:'目录责任',3:'模块演练',4:'接口规范',5:'框架利用',6:'运行证据',7:'文档收口',8:'版本基线'};
  const byStep = {};
  rules.forEach(r => {
    const s = r.step || 0;
    if (!byStep[s]) byStep[s] = [];
    byStep[s].push(r);
  });

  const rulesHtml = Object.keys(byStep).sort().map(step => {
    const stepName = stepNames[step] || '步骤 ' + step;
    const stepRules = byStep[step];
    const items = stepRules.map(r => {
      const rPassed = r.passed === true;
      const icon = rPassed ? '✅' : '❌';
      const cls = rPassed ? 'severity-low' : 'severity-critical';
      const title = r.title || r.id || '未命名';
      const violations = r.violations || [];
      const evidence = r.evidence || [];
      const manualItems = r.manual_check_items || [];
      const hasViolations = violations.length > 0;
      const hasEvidence = evidence.length > 0;
      const hasManual = manualItems.length > 0;
      return `<div class="leak-v-item ${cls}" onclick='showAcceptRuleDetail(JSON.parse(decodeURIComponent("${encodeURIComponent(JSON.stringify(r))}")), "rule")' style="cursor:pointer;">
        <div class="leak-v-icon">${icon}</div>
        <div class="leak-v-content">
          <div class="leak-v-title">${escapeHtml(title)}</div>
          <div class="leak-v-detail" style="font-size:11px;color:var(--text-muted);">
            ${r.suggestion ? escapeHtml(r.suggestion.slice(0, 120)) : ''}
            <span style="margin-left:8px;">⚡ ${r.execution_time ? r.execution_time + 's' : '-'}</span>
          </div>
          <div style="display:flex;gap:6px;margin-top:4px;flex-wrap:wrap;">
            ${hasViolations ? `<span style="font-size:10px;color:var(--red);background:var(--red-bg);padding:1px 6px;border-radius:8px;">🔴 ${violations.length} 违规</span>` : ''}
            ${hasEvidence ? `<span style="font-size:10px;color:var(--blue);background:rgba(88,166,255,0.1);padding:1px 6px;border-radius:8px;">📎 ${evidence.length} 证据</span>` : ''}
            ${hasManual ? `<span style="font-size:10px;color:var(--yellow);background:var(--yellow-bg);padding:1px 6px;border-radius:8px;">👤 ${manualItems.length} 人工核查</span>` : ''}
            <span style="font-size:10px;color:var(--text-muted);">👆 查看详情</span>
          </div>
        </div>
      </div>`;
    }).join('');
    return `
      <div style="margin-bottom:8px;">
        <div style="font-size:11px;font-weight:600;color:var(--text-secondary);padding:6px 12px;background:var(--bg-tertiary);border-radius:4px;margin-bottom:4px;">步骤 ${step}: ${stepName}</div>
        ${items}
      </div>`;
  }).join('') || '<div class="leak-empty"><div class="emoji">📋</div><div>暂无规则验收数据</div></div>';

  // Show export button
  const exportBtn = document.getElementById('accept-export-btn');
  if (exportBtn) exportBtn.style.display = 'inline-block';

  el.innerHTML = `
    <div class="panel" style="margin-bottom:16px;">
      <div class="panel-header">
        <h2>📊 验收结果</h2>
        ${ts ? `<span class="leak-timestamp">🕐 ${escapeHtml(ts)}</span>` : ''}
        <span style="font-size:11px;color:var(--text-muted);margin-left:8px;">📂 ${escapeHtml(proj)}</span>
      </div>
      <div class="panel-body" style="padding:16px;">
        <div style="display:flex;gap:16px;align-items:center;margin-bottom:16px;flex-wrap:wrap;">
          <div style="text-align:center;">
            <div class="leak-score-ring ${scoreClass}">${score}</div>
            <div style="font-size:11px;color:var(--text-muted);">架构评分</div>
          </div>
          <div style="flex:1;min-width:150px;">
            <div style="font-size:16px;font-weight:600;color:${statusColor};">${statusIcon} ${passed ? '通过' : '未通过'}</div>
            <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">⏱ ${execTime}s</div>
          </div>
        </div>
        <div class="leak-summary">
          <div class="leak-stat-card passed"><div class="num" style="color:var(--green);">${passedAuto}/${totalAuto}</div><div class="lbl">✅ 自动检查通过</div></div>
          <div class="leak-stat-card"><div class="num">${rules.length}</div><div class="lbl">📋 规则总数</div></div>
          <div class="leak-stat-card ${totalViolations > 0 ? 'failed' : 'passed'}"><div class="num" style="color:${totalViolations > 0 ? 'var(--red)' : 'var(--green)'};">${totalViolations}</div><div class="lbl">🔴 违规总数</div></div>
          <div class="leak-stat-card"><div class="num">${totalEvidence}</div><div class="lbl">📎 证据总数</div></div>
          <div class="leak-stat-card"><div class="num">${totalManualItems}</div><div class="lbl">👤 人工核查项</div></div>
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-header">
        <h2>📋 规则验收明细</h2>
        <span class="badge">${rules.length} 规则</span>
      </div>
      <div class="panel-body" style="padding:8px;">
        ${rulesHtml}
      </div>
    </div>
  `;
}

function showModal(title, bodyHtml) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.onclick = e => { if (e.target === overlay) overlay.remove(); };
  overlay.innerHTML = `
    <div class="modal" style="max-width:620px;">
      <div class="modal-header">
        <h2>${escapeHtml(title)}</h2>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">✕ 关闭</button>
      </div>
      <div class="modal-body">${bodyHtml}</div>
    </div>
  `;
  document.body.appendChild(overlay);
}

function showAcceptRuleDetail(r) {
  const rPassed = r.passed === true;
  const icon = rPassed ? '✅' : '❌';
  const title = r.title || r.id || '未命名规则';
  const violations = r.violations || [];
  const evidence = r.evidence || [];
  const manualItems = r.manual_check_items || [];

  const MAX_DISPLAY = 20;

  let violationsHtml = '';
  if (violations.length > 0) {
    const display = violations.slice(0, MAX_DISPLAY);
    violationsHtml = display.map(v => {
      const vMsg = v.message || (typeof v === 'string' ? v : JSON.stringify(v));
      return `<div style="padding:6px 10px;border-left:2px solid var(--red);margin-bottom:4px;font-size:12px;background:var(--bg-primary);border-radius:4px;">🔴 ${escapeHtml(typeof vMsg === 'string' ? vMsg.slice(0, 300) : JSON.stringify(vMsg).slice(0, 300))}</div>`;
    }).join('');
    if (violations.length > MAX_DISPLAY) {
      violationsHtml += `<div style="padding:6px;font-size:11px;color:var(--text-muted);text-align:center;">⋯ 还有 ${violations.length - MAX_DISPLAY} 条违规</div>`;
    }
  }

  let evidenceHtml = '';
  if (evidence.length > 0) {
    const display = evidence.slice(0, MAX_DISPLAY);
    evidenceHtml = display.map(e => {
      return `<div style="padding:4px 8px;font-size:11px;font-family:monospace;color:var(--blue);margin-bottom:2px;word-break:break-all;">📎 ${escapeHtml(String(e).slice(0, 300))}</div>`;
    }).join('');
    if (evidence.length > MAX_DISPLAY) {
      evidenceHtml += `<div style="padding:4px;font-size:11px;color:var(--text-muted);text-align:center;">⋯ 还有 ${evidence.length - MAX_DISPLAY} 条证据</div>`;
    }
  }

  let manualHtml = '';
  if (manualItems.length > 0) {
    manualHtml = manualItems.map(m => {
      return `<div style="padding:4px 8px;font-size:12px;color:var(--yellow);margin-bottom:2px;">👤 ${escapeHtml(String(m))}</div>`;
    }).join('');
  }

  const bodyHtml = `
    <div class="mem-detail-section">
      <div class="mem-detail-row"><span class="dl">状态</span><span class="dv">${icon} ${rPassed ? '通过' : '未通过'}</span></div>
      <div class="mem-detail-row"><span class="dl">规则 ID</span><span class="dv mono">${escapeHtml(r.id || '')}</span></div>
      <div class="mem-detail-row"><span class="dl">步骤</span><span class="dv">${r.step || 0}</span></div>
      <div class="mem-detail-row"><span class="dl">标题</span><span class="dv" style="font-weight:600;">${escapeHtml(title)}</span></div>
      <div class="mem-detail-row"><span class="dl">自动检查</span><span class="dv">${r.auto_checked ? '✅ 是' : '❌ 否'}</span></div>
      <div class="mem-detail-row"><span class="dl">执行耗时</span><span class="dv">${r.execution_time ? r.execution_time + 's' : '-'}</span></div>
      ${r.suggestion ? `<div class="mem-detail-row" style="align-self:start;"><span class="dl">结论</span><span class="dv">${escapeHtml(r.suggestion)}</span></div>` : ''}
    </div>
    ${violationsHtml ? `<div class="modal-section" style="margin-top:12px;"><div class="modal-section-title">🔴 违规详情 (${violations.length})</div>${violationsHtml}</div>` : ''}
    ${evidenceHtml ? `<div class="modal-section" style="margin-top:12px;"><div class="modal-section-title">📎 证据 (${evidence.length})</div>${evidenceHtml}</div>` : ''}
    ${manualHtml ? `<div class="modal-section" style="margin-top:12px;"><div class="modal-section-title">👤 人工核查项 (${manualItems.length})</div>${manualHtml}</div>` : ''}
  `;
  showModal('🏗️ ' + title, bodyHtml);
}

function exportAcceptReport() {
  const d = _cachedAcceptData;
  if (!d) return;
  const rules = d.rules || [];
  const ts = d.timestamp ? d.timestamp.slice(0, 19).replace('T', ' ') : new Date().toISOString().slice(0, 19).replace('T', ' ');

  const stepNames = {1:'规则验收',2:'目录责任',3:'模块演练',4:'接口规范',5:'框架利用',6:'运行证据',7:'文档收口',8:'版本基线'};

  let report = `# Moat 架构验收报告\n\n`;
  report += `**项目**: ${d.project || '未知'}\n`;
  report += `**验收时间**: ${ts}\n`;
  report += `**架构评分**: ${d.overall_score ?? 'N/A'}/100\n`;
  report += `**结果**: ${d.passed ? '✅ 通过' : '❌ 未通过'}\n`;
  report += `**自动检查**: ${d.passed_auto || 0}/${d.total_auto || 0}\n`;
  report += `**执行耗时**: ${d.execution_time || 0}s\n`;
  report += `**规则总数**: ${rules.length}\n`;
  report += `**违规总数**: ${d.total_violations || 0}\n`;
  report += `**证据总数**: ${d.total_evidence || 0}\n`;
  report += `**人工核查项**: ${d.total_manual_items || 0}\n\n`;

  // 按步骤分组
  const byStep = {};
  rules.forEach(r => {
    const s = r.step || 0;
    if (!byStep[s]) byStep[s] = [];
    byStep[s].push(r);
  });

  for (const step of Object.keys(byStep).sort()) {
    const stepName = stepNames[step] || '步骤 ' + step;
    report += `## 步骤 ${step}: ${stepName}\n\n`;
    for (const r of byStep[step]) {
      const status = r.passed === true ? '✅ 通过' : '❌ 未通过';
      const title = r.title || r.id || '未知';
      report += `### ${status}: ${title}\n\n`;
      report += `- **规则 ID**: ${r.id || ''}\n`;
      report += `- **自动检查**: ${r.auto_checked ? '是' : '否'}\n`;
      report += `- **执行耗时**: ${r.execution_time ? r.execution_time + 's' : '-'}\n`;
      if (r.suggestion) report += `- **结论**: ${r.suggestion}\n`;

      const violations = r.violations || [];
      if (violations.length > 0) {
        report += `\n**违规项 (${violations.length})**:\n`;
        for (const v of violations) {
          const vMsg = v.message || (typeof v === 'string' ? v : JSON.stringify(v));
          report += `  - 🔴 ${typeof vMsg === 'string' ? vMsg : JSON.stringify(vMsg)}\n`;
        }
      }

      const evidence = r.evidence || [];
      if (evidence.length > 0) {
        report += `\n**证据**:\n`;
        for (const e of evidence) {
          report += `  - 📎 ${String(e)}\n`;
        }
      }

      const manualItems = r.manual_check_items || [];
      if (manualItems.length > 0) {
        report += `\n**人工核查项**:\n`;
        for (const m of manualItems) {
          report += `  - 👤 ${String(m)}\n`;
        }
      }
      report += '\n---\n\n';
    }
  }

  const blob = new Blob([report], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `moat-accept-report-${ts.slice(0, 10)}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

document.addEventListener('DOMContentLoaded', () => {
  loadData();
  loadProjectInfo();
  // Load project list (also sets project name)
  loadProjectList();
  // 版本检查
  checkVersion();
  // Load sensor stats for sidebar
  loadSensorStats();
  // Auto-refresh toggle
  const rs = document.getElementById('refresh-status');
  if (rs) {
    rs.addEventListener('click', () => {
      STATE.paused = !STATE.paused;
      rs.classList.toggle('paused', STATE.paused);
      rs.textContent = STATE.paused ? '⏸ 暂停' : '🔄 3s';
      if (!STATE.paused) loadData();
    });
  }
  // Auto-refresh every 3s
  STATE.timer = setInterval(() => {
    if (!STATE.paused) {
      loadData();
      // 每 30 秒刷新一次项目信息
      if (Date.now() % 30000 < 3100) {
        loadProjectInfo();
      }
    }
  }, 3000);
});
