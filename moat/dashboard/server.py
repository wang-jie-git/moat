"""Moat Dashboard — Web 传感器看板"""
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

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    from moat.monitor import read_recent_errors
    from moat.runner import run_all_checks

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return _read_file(static_dir / "index.html")

    @app.get("/api/moat/errors")
    async def get_errors(
        lines: int = Query(100),
        level: str = Query("ERROR"),
    ):
        if log_path and Path(log_path).exists():
            errors = read_recent_errors(Path(log_path), lines=lines, filter_pattern=level)
            return {"errors": errors, "count": len(errors)}
        return {"errors": [], "count": 0}

    @app.get("/api/moat/status")
    async def get_status():
        from moat.baseline import BaselineManager
        bm = BaselineManager(project)
        baseline = bm.load()
        return {
            "project": project.name,
            "has_baseline": baseline is not None,
            "has_log": log_path and Path(log_path).exists(),
            "baseline": baseline,
        }

    @app.get("/api/moat/sensors")
    async def get_sensors():
        """传感器完整数据：统计 + 事件 + 健康"""
        from moat.pain.sensor import get_recent_events, _read_events_from_file

        events = get_recent_events(limit=50)
        file_events = _read_events_from_file(limit=1000)

        # 按组件聚合最新状态（基于文件事件）
        latest: dict[str, dict] = {}
        for e in file_events:
            latest[e["component_id"]] = e

        healthy_count = sum(1 for e in latest.values() if e["status"] == "OK")
        degraded_count = sum(1 for e in latest.values() if e["status"] == "DEGRADED")
        panic_count = sum(1 for e in latest.values() if e["status"] == "PANIC")
        panics = [e for e in file_events if e.get("status") == "PANIC"]

        return {
            "stats": {
                "total_components": len(latest),
                "healthy": healthy_count,
                "degraded": degraded_count,
                "panics_last_hour": len(panics),
                "events_total": len(file_events),
            },
            "events": events,
            "health": {
                "healthy": [cid for cid, e in latest.items() if e["status"] == "OK"],
                "degraded": [cid for cid, e in latest.items() if e["status"] == "DEGRADED"],
                "panic": [cid for cid, e in latest.items() if e["status"] == "PANIC"],
                "details": {cid: e for cid, e in latest.items()},
            },
            "health_section": "",
        }

    @app.get("/api/moat/sensors/{component_id}")
    async def get_component_detail(component_id: str):
        """单个组件详情"""
        from moat.pain.sensor import health_tracker, _read_events_from_file

        state = health_tracker.get_component_state(component_id)

        # 从文件读取该组件的事件
        all_events = _read_events_from_file(limit=500)
        component_events = [
            e for e in all_events
            if e.get("component_id") == component_id
        ][-20:]

        return {
            "component_id": component_id,
            "state": state,
            "is_healthy": health_tracker.is_healthy(component_id),
            "events": component_events,
        }

    @app.post("/api/moat/sensors/reset")
    async def reset_sensors():
        """清空传感器事件（内存 + 共享文件）"""
        from moat.pain.sensor import _event_bus, _error_history, EVENT_FILE
        import os
        _event_bus.clear()
        _error_history.clear()
        if os.path.exists(EVENT_FILE):
            os.remove(EVENT_FILE)
        return {"success": True}

    @app.post("/api/moat/check")
    async def run_check():
        success = run_all_checks(str(project))
        return {"success": success}

    @app.post("/api/moat/baseline/save")
    async def save_baseline():
        from moat.baseline import BaselineManager
        bm = BaselineManager(project)
        data = bm.save()
        return {"success": True, "baseline": data}

    print(f"\n  ╔══════════════════════════════════════╗")
    print(f"  ║     Moat Dashboard — 传感器看板      ║")
    print(f"  ╠══════════════════════════════════════╣")
    print(f"  ║  📍 http://{host}:{port}               ║")
    print(f"  ║  ⌨️  Ctrl+C 停止                      ║")
    print(f"  ╚══════════════════════════════════════╝\n")
    uvicorn.run(app, host=host, port=port, log_level="error")


def _ensure_frontend(static_dir: Path):
    html = static_dir / "index.html"
    if not html.exists():
        html.write_text("<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Moat</title><link rel='stylesheet' href='/static/style.css'></head><body><div id='app'></div><script src='/static/app.js'></script></body></html>")
    css = static_dir / "style.css"
    if not css.exists():
        css.write_text("")
    js = static_dir / "app.js"
    if not js.exists():
        js.write_text("")


def _read_file(path: Path) -> str:
    try:
        return path.read_text()
    except Exception:
        return "<html><body>Error</body></html>"
