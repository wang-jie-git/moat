"""Moat Dashboard — Web 传感器看板"""
import time
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

        # 读取注入元数据
        injected_count = 0
        injection_meta_file = Path.home() / ".moat" / "injection_meta.json"
        if injection_meta_file.exists():
            try:
                import json
                meta = json.loads(injection_meta_file.read_text())
                injected_count = meta.get("total_injected", 0)
            except Exception:
                pass

        return {
            "stats": {
                "total_components": len(latest),
                "healthy": healthy_count,
                "degraded": degraded_count,
                "panics_last_hour": len(panics),
                "events_total": len(file_events),
                "injected_sensors": injected_count,
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
        ]

        # 统计
        total = len(component_events)
        ok_count = sum(1 for e in component_events if e.get("status") == "OK")
        degraded_count = sum(1 for e in component_events if e.get("status") == "DEGRADED")
        panic_count = sum(1 for e in component_events if e.get("status") == "PANIC")
        avg_duration = 0.0
        durations = [e.get("duration_ms", 0) for e in component_events if e.get("duration_ms", 0) > 0]
        if durations:
            avg_duration = sum(durations) / len(durations)

        # 解析函数名和文件路径
        parts = component_id.split(":", 1)
        file_path = parts[0] if len(parts) > 1 else component_id
        func_name = parts[1] if len(parts) > 1 else ""

        return {
            "component_id": component_id,
            "file_path": file_path,
            "func_name": func_name,
            "state": state,
            "is_healthy": health_tracker.is_healthy(component_id),
            "stats": {
                "total_events": total,
                "ok": ok_count,
                "degraded": degraded_count,
                "panic": panic_count,
                "avg_duration_ms": round(avg_duration, 1),
                "success_rate": round((ok_count / total * 100) if total > 0 else 0, 1),
            },
            "events": component_events[-20:],
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
        import threading, queue, json
        from pathlib import Path

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

                # 保存注入元数据到共享文件
                meta_dir = Path.home() / ".moat"
                meta_dir.mkdir(parents=True, exist_ok=True)
                meta_file = meta_dir / "injection_meta.json"
                meta = {
                    "total_injected": total_injected,
                    "injected_files": len([r for r in results if r.get("injected", 0) > 0]),
                    "project": project.name,
                    "timestamp": time.time(),
                }
                try:
                    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
                except Exception:
                    pass

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

    @app.get("/api/moat/project-info")
    async def get_project_info():
        """项目基本信息：类型、文件数、语言分布、Git 状态"""
        from moat.pain.config import detect_project_type

        abs_path = project.resolve()
        ptype = detect_project_type(str(project))

        # 统计文件数和语言分布
        lang_ext_map = {
            '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
            '.tsx': 'TSX', '.jsx': 'JSX', '.json': 'JSON', '.yaml': 'YAML',
            '.yml': 'YAML', '.md': 'Markdown', '.css': 'CSS', '.html': 'HTML',
            '.sh': 'Shell', '.sql': 'SQL', '.go': 'Go', '.rs': 'Rust',
            '.java': 'Java', '.rb': 'Ruby',
        }
        lang_counts: dict[str, int] = {}
        total_files = 0
        total_lines = 0
        skip_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv',
                     '.moat', 'dist', 'build', '.next', '.cache'}

        for f in abs_path.rglob('*'):
            if not f.is_file():
                continue
            # 跳过不需要的目录
            parts = f.relative_to(abs_path).parts
            if any(p in skip_dirs for p in parts):
                continue
            ext = f.suffix.lower()
            lang = lang_ext_map.get(ext)
            if lang:
                total_files += 1
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
                # 统计行数（仅代码文件）
                if lang in ('Python', 'JavaScript', 'TypeScript', 'TSX', 'JSX', 'Go', 'Rust', 'Java', 'Ruby', 'Shell'):
                    try:
                        total_lines += sum(1 for _ in f.open(encoding='utf-8', errors='ignore'))
                    except Exception:
                        pass

        # 语言排序
        languages = sorted(lang_counts.items(), key=lambda x: -x[1])
        top_languages = [{"name": n, "count": c} for n, c in languages[:8]]

        # Git 信息
        git_info = {"branch": "", "last_commit": "", "dirty": False, "has_git": False}
        try:
            import subprocess
            r = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                               cwd=str(abs_path), capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and "true" in r.stdout.lower():
                git_info["has_git"] = True
                # 分支
                br = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                                    cwd=str(abs_path), capture_output=True, text=True, timeout=5)
                git_info["branch"] = br.stdout.strip() if br.returncode == 0 else ""
                # 最近 commit
                cm = subprocess.run(["git", "log", "-1", "--format=%h %s (%cr)"],
                                    cwd=str(abs_path), capture_output=True, text=True, timeout=5)
                git_info["last_commit"] = cm.stdout.strip() if cm.returncode == 0 else ""
                # 是否有未提交改动
                st = subprocess.run(["git", "status", "--porcelain"],
                                    cwd=str(abs_path), capture_output=True, text=True, timeout=5)
                git_info["dirty"] = bool(st.stdout.strip()) if st.returncode == 0 else False
        except Exception:
            pass

        # 项目大小
        try:
            total_size = sum(f.stat().st_size for f in abs_path.rglob('*') if f.is_file()
                            and not any(p in skip_dirs for p in f.relative_to(abs_path).parts))
            size_str = f"{total_size / 1024 / 1024:.1f} MB" if total_size > 1024 * 1024 else f"{total_size / 1024:.0f} KB"
        except Exception:
            size_str = "未知"

        return {
            "name": abs_path.name,
            "path": str(abs_path),
            "project_type": ptype,
            "total_files": total_files,
            "total_lines": total_lines,
            "languages": top_languages,
            "git": git_info,
            "size": size_str,
        }

    @app.get("/api/moat/memory")
    async def get_memory():
        """Moat 记忆系统状态：红线、踩坑、模板、技能"""
        try:
            from moat.memory.moat_memory import MoatMemory
            mem = MoatMemory(str(project))

            redlines = mem.list_redlines()
            lessons = mem.bridge.query_lessons()
            templates = mem.bridge.query_templates()
            skills = mem.bridge.query_skills()

            # 红线按严重性分组
            redline_stats = {"critical": 0, "warning": 0, "info": 0}
            for r in redlines:
                sev = r.get("severity", "info")
                if sev in redline_stats:
                    redline_stats[sev] += 1

            return {
                "available": True,
                "db_path": str(project / ".moat" / "memory.db"),
                "stats": {
                    "redlines": len(redlines),
                    "lessons": len(lessons),
                    "templates": len(templates),
                    "skills": len(skills),
                    "total": len(redlines) + len(lessons) + len(templates) + len(skills),
                },
                "redline_stats": redline_stats,
                "recent_lessons": lessons[-5:] if lessons else [],
                "recent_redlines": redlines[-5:] if redlines else [],
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "stats": {"redlines": 0, "lessons": 0, "templates": 0, "skills": 0, "total": 0},
            }

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
