"""Moat Dashboard — Web 错误看板"""
import json
from pathlib import Path


def start_dashboard(project: Path, host: str = "127.0.0.1",
                    port: int = 9876, log_path: str | None = None):
    """启动 Web 看板（内嵌 FastAPI）"""
    try:
        import uvicorn
        from fastapi import FastAPI, Query
        from fastapi.responses import HTMLResponse, JSONResponse
        from fastapi.staticfiles import StaticFiles
    except ImportError:
        print("❌ 需要安装 fastapi + uvicorn: pip install fastapi uvicorn")
        return

    app = FastAPI(title="Moat Dashboard")

    # 静态文件
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    _ensure_frontend(static_dir)

    # 挂载静态文件
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    from moat.monitor import read_recent_errors
    from moat.runner import run_all_checks

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return _read_file(static_dir / "index.html")

    @app.get("/api/moat/errors")
    async def get_errors(
        lines: int = Query(100, description="返回条数"),
        level: str = Query("ERROR", description="错误级别"),
    ):
        if log_path and Path(log_path).exists():
            errors = read_recent_errors(
                Path(log_path),
                lines=lines,
                filter_pattern=level,
            )
            return {"errors": errors, "count": len(errors)}
        return {"errors": [], "count": 0, "message": "没有配置日志路径"}

    @app.get("/api/moat/status")
    async def get_status():
        from moat.baseline import BaselineManager
        bm = BaselineManager(project)
        baseline = bm.load()
        info = {
            "project": project.name,
            "has_baseline": baseline is not None,
            "baseline": baseline,
            "log_path": log_path,
            "has_log": log_path and Path(log_path).exists(),
        }
        return info

    @app.post("/api/moat/check")
    async def run_check():
        success = run_all_checks(str(project))
        return {"success": success}

    @app.get("/api/moat/baseline")
    async def get_baseline():
        from moat.baseline import BaselineManager
        bm = BaselineManager(project)
        return {"baseline": bm.load()}

    @app.post("/api/moat/baseline/save")
    async def save_baseline():
        from moat.baseline import BaselineManager
        bm = BaselineManager(project)
        data = bm.save()
        return {"success": True, "baseline": data}

    @app.get("/api/moat/health")
    async def get_health():
        """组件健康热力图数据"""
        from moat.pain.sensor import get_health_summary, get_recent_events, health_tracker
        return {
            "summary": get_health_summary(),
            "recent_events": get_recent_events(limit=20),
            "health_tracker": health_tracker.get_health_summary(),
            "health_section": health_tracker.build_health_section(include_healthy=True),
        }

    print(f"\n  Moat Dashboard 已启动")
    print(f"  http://{host}:{port}")
    print(f"  按 Ctrl+C 停止\n")
    uvicorn.run(app, host=host, port=port, log_level="error")


def _ensure_frontend(static_dir: Path):
    """确保前端文件存在"""
    html = static_dir / "index.html"
    if not html.exists():
        html.write_text(_FRONTEND_HTML)
    css = static_dir / "style.css"
    if not css.exists():
        css.write_text(_FRONTEND_CSS)
    js = static_dir / "app.js"
    if not js.exists():
        js.write_text(_FRONTEND_JS)


def _read_file(path: Path) -> str:
    try:
        return path.read_text()
    except Exception:
        return "<html><body>Error</body></html>"


_FRONTEND_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Moat Dashboard</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <header>
    <h1>Moat <span class="subtitle">AI 编码护城河</span></h1>
    <div class="status-bar">
      <span id="status-indicator" class="indicator green"></span>
      <span id="status-text">监控中</span>
      <button onclick="runCheck()" class="btn">运行检查</button>
      <button onclick="saveBaseline()" class="btn btn-secondary">保存基线</button>
    </div>
  </header>

  <main>
    <section class="summary">
      <div class="card">
        <h3>错误</h3>
        <p class="big" id="error-count">0</p>
      </div>
      <div class="card">
        <h3>警告</h3>
        <p class="big" id="warn-count">0</p>
      </div>
      <div class="card">
        <h3>项目</h3>
        <p class="big" id="project-name">-</p>
      </div>
      <div class="card">
        <h3>基线</h3>
        <p class="big" id="baseline-status">-</p>
      </div>
    </section>

    <section class="errors">
      <h2>实时错误</h2>
      <div class="toolbar">
        <select id="level-filter" onchange="loadErrors()">
          <option value="ERROR">ERROR</option>
          <option value="ERROR|WARNING">ERROR + WARN</option>
          <option value="ERROR|WARNING|INFO">全部</option>
        </select>
        <span id="last-update"></span>
      </div>
      <div id="error-list" class="error-list"></div>
    </section>

    <section class="health">
      <h2>🔥 组件健康热力图</h2>
      <div id="health-grid" class="health-grid"></div>
    </section>
  </main>

  <script src="/static/app.js"></script>
</body>
</html>"""

_FRONTEND_CSS = """* { margin:0; padding:0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #0a0a0a;
  color: #e0e0e0;
  min-height: 100vh;
}
header {
  background: #111;
  padding: 20px 30px;
  border-bottom: 1px solid #222;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
h1 { font-size: 20px; }
.subtitle { font-size: 12px; color: #888; margin-left: 10px; }
.status-bar { display: flex; align-items: center; gap: 12px; }
.indicator {
  width: 10px; height: 10px; border-radius: 50%; display: inline-block;
}
.indicator.green { background: #22c55e; }
.indicator.red { background: #ef4444; }
.indicator.yellow { background: #eab308; }
.btn {
  background: #22c55e; color: #000; border: none; padding: 6px 14px;
  border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: 500;
}
.btn-secondary { background: #333; color: #e0e0e0; }
.btn:hover { opacity: 0.85; }
main { padding: 20px 30px; }
.summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 25px; }
.card {
  background: #111; border: 1px solid #222; border-radius: 8px; padding: 15px;
}
.card h3 { font-size: 12px; color: #888; margin-bottom: 8px; }
.big { font-size: 28px; font-weight: bold; }
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
select {
  background: #111; color: #e0e0e0; border: 1px solid #333; padding: 4px 8px; border-radius: 4px;
}
#last-update { font-size: 11px; color: #666; }
.error-list { max-height: 60vh; overflow-y: auto; }
.error-item {
  padding: 10px 12px; border-bottom: 1px solid #1a1a1a; font-size: 12px;
  font-family: 'SFMono-Regular', Menlo, monospace;
}
.error-item:hover { background: #151515; }
.error-item .time { color: #666; margin-right: 10px; }
.error-item .level { padding: 1px 6px; border-radius: 3px; font-size: 10px; margin-right: 8px; }
.level-ERROR { background: rgba(239,68,68,0.2); color: #ef4444; }
.level-WARN { background: rgba(234,179,8,0.2); color: #eab308; }
.empty { color: #666; text-align: center; padding: 40px; }
.health { margin-top: 25px; }
.health h2 { font-size: 16px; margin-bottom: 12px; }
.health-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 10px; }
.health-card {
  background: #111; border: 1px solid #222; border-radius: 6px; padding: 12px;
  font-size: 12px; cursor: pointer; transition: background 0.15s;
}
.health-card:hover { background: #181818; }
.health-card strong { display: block; font-size: 13px; margin-bottom: 6px; font-family: 'SFMono-Regular', Menlo, monospace; }
.health-card span { display: block; color: #888; line-height: 1.6; }
.health-card .error-text { color: #ef4444; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.health-detail {
  position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
  background: #1a1a1a; border: 1px solid #333; border-radius: 10px;
  padding: 24px; min-width: 400px; max-width: 600px; max-height: 80vh; overflow-y: auto; z-index: 100;
}
.health-detail h3 { font-size: 16px; margin-bottom: 12px; }
.health-detail pre { background: #111; padding: 12px; border-radius: 6px; font-size: 11px; overflow-x: auto; margin-top: 8px; }
.health-detail .close { float: right; cursor: pointer; color: #888; font-size: 18px; }
.health-detail .close:hover { color: #fff; }
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 99; }
"""

_FRONTEND_JS = """let refreshInterval = null;

function log(msg) { console.log('[Moat]', msg); }

async function loadErrors() {
  const level = document.getElementById('level-filter').value;
  try {
    const r = await fetch('/api/moat/errors?lines=100&level=' + encodeURIComponent(level));
    const data = await r.json();
    renderErrors(data.errors || []);
    document.getElementById('error-count').textContent = data.count || 0;
    document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
  } catch(e) {
    log('loadErrors failed: ' + e);
  }
}

async function loadStatus() {
  try {
    const r = await fetch('/api/moat/status');
    const data = await r.json();
    document.getElementById('project-name').textContent = data.project || '-';

    if (data.has_log) {
      document.getElementById('status-indicator').className = 'indicator green';
      document.getElementById('status-text').textContent = '日志连接正常';
    } else {
      document.getElementById('status-indicator').className = 'indicator yellow';
      document.getElementById('status-text').textContent = '日志未配置';
    }

    if (data.baseline) {
      document.getElementById('baseline-status').textContent =
        data.baseline.file_count + ' 文件 / ' + data.baseline.total_lines + ' 行';
    } else {
      document.getElementById('baseline-status').textContent = '未保存';
    }
  } catch(e) {
    log('loadStatus failed: ' + e);
  }
}

function renderErrors(errors) {
  const list = document.getElementById('error-list');
  if (errors.length === 0) {
    list.innerHTML = '<div class="empty">✅ 没有错误</div>';
    return;
  }
  list.innerHTML = errors.map(e => {
    const level = e.level === 'ERROR' ? 'ERROR' : 'WARN';
    return '<div class="error-item">' +
      '<span class="time">' + (e.timestamp || '').slice(11, 19) + '</span>' +
      '<span class="level level-' + level + '">' + level + '</span>' +
      escapeHtml(e.message) +
      '</div>';
  }).join('');
}

async function runCheck() {
  try {
    const r = await fetch('/api/moat/check', { method: 'POST' });
    const data = await r.json();
    if (data.success) {
      document.getElementById('status-indicator').className = 'indicator green';
      document.getElementById('status-text').textContent = '✅ 检查通过';
    } else {
      document.getElementById('status-indicator').className = 'indicator red';
      document.getElementById('status-text').textContent = '❌ 检查失败';
    }
  } catch(e) {
    log('runCheck failed: ' + e);
  }
}

async function saveBaseline() {
  try {
    const r = await fetch('/api/moat/baseline/save', { method: 'POST' });
    const data = await r.json();
    if (data.success) {
      document.getElementById('status-text').textContent = '基线已保存';
      document.getElementById('baseline-status').textContent =
        data.baseline.file_count + ' 文件 / ' + data.baseline.total_lines + ' 行';
    }
  } catch(e) {
    log('saveBaseline failed: ' + e);
  }
}

function escapeHtml(text) {
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}

// ── 健康热力图 ──────────────────────────────────────────

async function loadHealth() {
  try {
    const r = await fetch('/api/moat/health');
    const data = await r.json();
    renderHealthGrid(data.summary, data.recent_events);
  } catch(e) {
    log('loadHealth failed: ' + e);
  }
}

function renderHealthGrid(summary, events) {
  const grid = document.getElementById('health-grid');
  if (!summary.total_events) {
    grid.innerHTML = '<div class="empty">✅ 所有组件运行正常，暂无传感器事件</div>';
    return;
  }

  const components = [
    ...(summary.panic_components || []).map(c => ({ ...c, _status: 'PANIC' })),
    ...(summary.degraded_components || []).map(c => ({ ...c, _status: 'DEGRADED' })),
    ...(summary.healthy_components || []).map(c => ({ ...c, _status: 'OK' })),
  ];

  grid.innerHTML = components.map(c => {
    const color = c._status === 'OK' ? '#22c55e' : c._status === 'DEGRADED' ? '#eab308' : '#ef4444';
    const icon = c._status === 'OK' ? '✅' : c._status === 'DEGRADED' ? '🟡' : '🔴';
    return '<div class="health-card" style="border-left: 3px solid ' + color + '" onclick="showDetail(\'' + escapeHtml(c.component_id) + '\')">' +
      '<strong>' + icon + ' ' + escapeHtml(c.component_id) + '</strong>' +
      '<span>耗时: ' + (c.last_duration_ms || 0).toFixed(1) + 'ms</span>' +
      '<span>最后活跃: ' + (c.last_seen || '').slice(11, 19) + '</span>' +
      (c._status === 'PANIC' ? '<span class="error-text">⛔ 组件已损坏</span>' : '') +
      (c._status === 'DEGRADED' ? '<span class="error-text">⚠️ 组件降级运行</span>' : '') +
      '</div>';
  }).join('');
}

function showDetail(componentId) {
  // 创建详情弹窗
  const overlay = document.createElement('div');
  overlay.className = 'overlay';
  overlay.onclick = closeDetail;
  document.body.appendChild(overlay);

  const detail = document.createElement('div');
  detail.className = 'health-detail';
  detail.innerHTML = '<span class="close" onclick="closeDetail()">✕</span><h3>📡 ' + escapeHtml(componentId) + '</h3><p id="detail-content">加载中...</p>';
  document.body.appendChild(detail);

  // 从后端获取组件详情
  fetch('/api/moat/health')
    .then(r => r.json())
    .then(data => {
      const events = (data.recent_events || []).filter(e => e.component_id === componentId);
      if (events.length === 0) {
        detail.innerHTML = '<span class="close" onclick="closeDetail()">✕</span><h3>📡 ' + escapeHtml(componentId) + '</h3><p>暂无事件记录</p>';
        return;
      }
      let html = '<span class="close" onclick="closeDetail()">✕</span><h3>📡 ' + escapeHtml(componentId) + '</h3>';
      html += '<p>共 ' + events.length + ' 条事件</p>';
      html += '<pre>' + events.map(e => '[' + e.status + '] ' + (e.error || 'OK') + ' (' + e.duration_ms + 'ms)').join('\n') + '</pre>';
      detail.innerHTML = html;
    });
}

function closeDetail() {
  document.querySelectorAll('.overlay, .health-detail').forEach(el => el.remove());
}

// 初始化
loadErrors();
loadStatus();
loadHealth();
refreshInterval = setInterval(() => {
  loadErrors();
  loadHealth();
}, 5000);
"""