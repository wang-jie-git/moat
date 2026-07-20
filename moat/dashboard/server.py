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
        """运行代码检查（后台线程 + 5 秒超时）"""
        import threading, queue

        result_queue: queue.Queue = queue.Queue()
        check_thread = threading.Thread(
            target=lambda q: q.put(run_all_checks(str(project))),
            args=(result_queue,),
            daemon=True,
        )
        check_thread.start()

        # 等 5 秒
        try:
            result = result_queue.get(timeout=5)
            success = bool(result)
            return {"success": success, "timed_out": False}
        except queue.Empty:
            return {"success": False, "timed_out": True, "message": "检查超时（超过 5 秒），已在后台继续运行"}

    @app.post("/api/moat/inject")
    async def inject_sensors():
        """为项目注入传感器（默认 dry-run 预览）"""
        import threading, queue, json

        result_queue: queue.Queue = queue.Queue()

        def _run():
            try:
                from moat.ast.injector import inject_project
                from moat.pain.config import load_config

                config = load_config(str(project))
                sensor_cfg = config.get("sensor", {})
                auto_inject = sensor_cfg.get("auto_inject", False)
                include = sensor_cfg.get("include", [])

                # 先跑 dry-run
                dry_results, _, _ = inject_project(str(project), config=config, dry_run=True)
                total_files = len(dry_results)
                injected_files = [r for r in dry_results if r.get("injected", 0) > 0]
                total_injected = sum(r.get("injected", 0) for r in dry_results)
                skipped_files = [r for r in dry_results if r.get("injected", 0) == 0 and not r.get("error")]
                errors = [r for r in dry_results if r.get("error")]

                result_queue.put({
                    "success": True,
                    "dry_run": True,
                    "total_files": total_files,
                    "injected_files": len(injected_files),
                    "total_injected": total_injected,
                    "skipped_files": len(skipped_files),
                    "errors": len(errors),
                    "error_details": [r["error"] for r in errors[:10]],
                    "sample_files": [r["file"] for r in injected_files[:20]],
                    "auto_inject": auto_inject,
                    "include_patterns": include,
                    "has_config": bool(include),
                })
            except Exception as e:
                result_queue.put({"success": False, "error": str(e)})

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        try:
            return result_queue.get(timeout=15)
        except queue.Empty:
            return {"success": False, "timed_out": True, "message": "扫描超时，项目文件过多"}

    @app.post("/api/moat/inject/execute")
    async def inject_sensors_execute():
        """执行注入（非 dry-run）"""
        import threading, queue

        result_queue: queue.Queue = queue.Queue()

        def _run():
            try:
                from moat.ast.injector import inject_project
                from moat.pain.config import load_config

                config = load_config(str(project))
                results, backup_root, backup_count = inject_project(
                    str(project), config=config, dry_run=False
                )

                total_injected = sum(r.get("injected", 0) for r in results)
                errors = [r for r in results if r.get("error")]

                result_queue.put({
                    "success": True,
                    "total_files": len(results),
                    "total_injected": total_injected,
                    "errors": len(errors),
                    "error_details": [r["error"] for r in errors[:10]],
                    "backup_timestamp": backup_root.name if backup_root else "",
                    "backup_files": backup_count,
                })
            except Exception as e:
                result_queue.put({"success": False, "error": str(e)})

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        try:
            return result_queue.get(timeout=30)
        except queue.Empty:
            return {"success": False, "timed_out": True, "message": "注入超时"}

    @app.post("/api/moat/inject/restart")
    async def inject_restart():
        """推荐项目重启命令"""
        import threading, queue

        result_queue: queue.Queue = queue.Queue()

        def _run():
            try:
                from moat.pain.config import detect_project_type
                ptype = detect_project_type(str(project))
                abs_path = project.resolve()
                cmd = ""

                if ptype == "FastAPI":
                    cmd = "pkill -f 'uvicorn' 2>/dev/null; nohup uvicorn app.main:app --reload &"
                elif ptype == "Django":
                    cmd = "pkill -f 'manage.py' 2>/dev/null; nohup python manage.py runserver &"
                elif ptype == "Monorepo":
                    cmd = f"cd {abs_path} && PYTHONPATH=\"packages/openharness-engine/src:packages/backend/src\" nohup python3 -m one_backend.server &"
                elif ptype in ("CLI 工具", "Python 项目"):
                    cmd = "pkill -f 'python3.*main' 2>/dev/null; nohup python3 main.py &"
                else:
                    cmd = "重启你的项目"

                result_queue.put({
                    "success": True,
                    "project_type": ptype,
                    "restart_cmd": cmd,
                })
            except Exception as e:
                result_queue.put({
                    "success": False,
                    "error": str(e),
                    "restart_cmd": "重启你的项目",
                    "project_type": "未知",
                })

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        try:
            return result_queue.get(timeout=15)
        except queue.Empty:
            return {"success": False, "restart_cmd": "重启你的项目", "project_type": "未知"}

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
