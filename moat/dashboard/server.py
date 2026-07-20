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
        from moat.pain.sensor import get_health_summary, get_recent_events, health_tracker
        from moat.pain.sensor import _event_bus

        events = get_recent_events(limit=50)
        summary = get_health_summary()
        tracker_data = health_tracker.get_health_summary()

        # 统计
        total = len(tracker_data.get("details", {}))
        healthy_count = len(tracker_data.get("healthy", []))
        degraded_count = len(tracker_data.get("degraded", []))

        # 最近事件统计
        recent_panics = [e for e in _event_bus if e.status == "PANIC"]
        recent_ok = [e for e in _event_bus if e.status == "OK"]

        return {
            "stats": {
                "total_components": total,
                "healthy": healthy_count,
                "degraded": degraded_count,
                "panics_last_hour": len(recent_panics),
                "events_total": len(_event_bus),
            },
            "events": events,  # get_recent_events 已返回 dict 列表
            "health": tracker_data,
            "health_section": health_tracker.build_health_section(include_healthy=True),
        }

    @app.get("/api/moat/sensors/{component_id}")
    async def get_component_detail(component_id: str):
        """单个组件详情"""
        from moat.pain.sensor import health_tracker, _event_bus

        state = health_tracker.get_component_state(component_id)
        events = [
            e.to_dict() for e in _event_bus
            if e.component_id == component_id
        ][-20:]  # 最近 20 条

        return {
            "component_id": component_id,
            "state": state,
            "is_healthy": health_tracker.is_healthy(component_id),
            "events": events,
        }

    @app.post("/api/moat/sensors/demo")
    async def inject_demo_data():
        """注入演示数据（仅供测试 Dashboard 效果）"""
        from moat.pain.sensor import health_tracker, SensorEvent, _event_bus

        demo_events = [
            (health_tracker.record_failure, ["db.user_query", "Connection pool exhausted"]),
            (health_tracker.record_success, ["auth.verify_token"]),
            (health_tracker.record_failure, ["memory_bridge", "Timeout after 5s"]),
            (health_tracker.record_failure, ["memory_bridge", "Retry failed"]),
            (health_tracker.record_success, ["secret_sanitization"]),
            (health_tracker.record_failure, ["person_memory", "OpenAI API 429"]),
            (health_tracker.record_success, ["cache.get_user_profile"]),
            (health_tracker.record_failure, ["payment.stripe_charge", "card_declined"]),
            (health_tracker.record_failure, ["payment.stripe_charge", "insufficient_funds"]),
            (health_tracker.record_success, ["cache.get_products"]),
        ]
        for fn, args in demo_events:
            fn(*args)

        sensor_events = [
            SensorEvent("db.user_query", "DEGRADED", 3200, "Connection pool exhausted", "PoolTimeout"),
            SensorEvent("auth.verify_token", "OK", 12),
            SensorEvent("memory_bridge", "DEGRADED", 5010, "Timeout after 5s", "TimeoutError"),
            SensorEvent("memory_bridge", "DEGRADED", 5100, "Retry failed", "TimeoutError"),
            SensorEvent("secret_sanitization", "OK", 3),
            SensorEvent("person_memory", "DEGRADED", 4800, "OpenAI API 429", "RateLimitError"),
            SensorEvent("cache.get_user_profile", "OK", 8),
            SensorEvent("payment.stripe_charge", "DEGRADED", 2500, "card_declined", "StripeError"),
            SensorEvent("payment.stripe_charge", "DEGRADED", 3100, "insufficient_funds", "StripeError"),
            SensorEvent("cache.get_products", "OK", 15),
        ]
        for e in sensor_events:
            _event_bus.append(e)

        return {"success": True, "injected": len(sensor_events)}

    @app.post("/api/moat/sensors/reset")
    async def reset_sensors():
        """清空传感器事件"""
        from moat.pain.sensor import _event_bus, _error_history
        _event_bus.clear()
        _error_history.clear()
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
