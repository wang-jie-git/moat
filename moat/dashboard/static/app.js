let refreshInterval = null;

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

// 初始化
loadErrors();
loadStatus();
refreshInterval = setInterval(loadErrors, 5000);