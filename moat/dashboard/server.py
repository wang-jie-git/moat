"""Moat Dashboard — Web 传感器看板"""
import asyncio
import json
import os
import time
from pathlib import Path


def start_dashboard(initial_project: Path, host: str = "127.0.0.1",
                    port: int = 9876, log_path: str | None = None):
    """启动 Web 看板（内嵌 FastAPI）"""
    _project_ref = [initial_project]
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
        bm = BaselineManager(_project_ref[0])
        baseline = bm.load()
        return {
            "project": _project_ref[0].name,
            "has_baseline": baseline is not None,
            "has_log": log_path and Path(log_path).exists(),
            "baseline": baseline,
        }

    @app.get("/api/moat/projects")
    async def list_projects():
        """发现可扫描的项目"""
        home = Path.home()
        candidates = []
        # 桌面
        desktop = home / "Desktop"
        if desktop.exists():
            for item in sorted(desktop.iterdir()):
                if item.is_dir() and not item.name.startswith('.'):
                    git_dir = item / ".git"
                    if git_dir.exists() or (item / "package.json").exists() or (item / "pyproject.toml").exists():
                        candidates.append({
                            "name": item.name,
                            "path": str(item),
                            "current": str(item) == str(_project_ref[0]),
                        })
        # 项目目录
        projects_dir = home / "Projects"
        if projects_dir.exists():
            for item in sorted(projects_dir.iterdir()):
                if item.is_dir() and not item.name.startswith('.'):
                    git_dir = item / ".git"
                    if git_dir.exists() or (item / "package.json").exists() or (item / "pyproject.toml").exists():
                        # 去重
                        if not any(c["path"] == str(item) for c in candidates):
                            candidates.append({
                                "name": item.name,
                                "path": str(item),
                                "current": str(item) == str(_project_ref[0]),
                            })
        return {"projects": candidates, "current": str(_project_ref[0])}

    @app.post("/api/moat/projects/switch")
    async def switch_project(data: dict):
        """切换当前项目"""
        path = data.get("path", "")
        if not path:
            return {"success": False, "error": "缺少 path 参数"}
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return {"success": False, "error": f"路径不存在: {p}"}
        _project_ref[0] = p
        return {"success": True, "project": p.name, "path": str(p)}

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

        # 过滤：只保留属于当前项目的传感器
        project_root = str(_project_ref[0].resolve())
        project_sensors = {}
        other_sensors = {}
        for cid, e in latest.items():
            # component_id 格式: "relative/file.py:func_name"
            comp_file = cid.split(":")[0] if ":" in cid else cid
            full_path = str(_project_ref[0] / comp_file)
            if full_path.startswith(project_root) and Path(full_path).exists():
                project_sensors[cid] = e
            else:
                # 也检查是否以绝对路径形式存储
                if comp_file.startswith(project_root) and Path(comp_file).exists():
                    project_sensors[cid] = e
                else:
                    other_sensors[cid] = e

        healthy_count = sum(1 for e in project_sensors.values() if e["status"] == "OK")
        degraded_count = sum(1 for e in project_sensors.values() if e["status"] == "DEGRADED")
        panic_count = sum(1 for e in project_sensors.values() if e["status"] == "PANIC")
        panics = [e for e in file_events if e.get("status") == "PANIC"]

        # 读取注入元数据
        injected_count = 0
        injection_meta_file = _project_ref[0] / ".moat" / "injection_meta.json"
        if not injection_meta_file.exists():
            injection_meta_file = Path.home() / ".moat" / "injection_meta.json"
        if injection_meta_file.exists():
            try:
                import json
                meta = json.loads(injection_meta_file.read_text())
                injected_count = meta.get("total_injected", 0)
            except Exception:
                pass

        # 过滤事件列表
        project_cids = set(project_sensors.keys())
        project_events = [e for e in events if e.get("component_id") in project_cids]

        return {
            "stats": {
                "total_components": len(project_sensors),
                "healthy": healthy_count,
                "degraded": degraded_count,
                "panics_last_hour": len(panics),
                "events_total": len(project_events),
                "injected_sensors": injected_count,
                "other_components": len(other_sensors),
            },
            "events": project_events,
            "health": {
                "healthy": [cid for cid in project_sensors if project_sensors[cid]["status"] == "OK"],
                "degraded": [cid for cid in project_sensors if project_sensors[cid]["status"] == "DEGRADED"],
                "panic": [cid for cid in project_sensors if project_sensors[cid]["status"] == "PANIC"],
                "details": {cid: e for cid, e in project_sensors.items()},
            },
            "health_section": "",
            "project": _project_ref[0].name,
        }

    @app.get("/api/moat/sensors/detail")
    async def get_component_detail(component_id: str = Query(...)):
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
            target=lambda q: q.put(run_all_checks(str(_project_ref[0]))),
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

                config = load_config(str(_project_ref[0]))
                sensor_cfg = config.get("sensor", {})
                auto_inject = sensor_cfg.get("auto_inject", False)
                include = sensor_cfg.get("include", [])

                # 先跑 dry-run
                dry_results, _, _ = inject_project(str(_project_ref[0]), config=config, dry_run=True)
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

                config = load_config(str(_project_ref[0]))
                results, backup_root, backup_count = inject_project(
                    str(_project_ref[0]), config=config, dry_run=False
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
                    "project": _project_ref[0].name,
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
                ptype = detect_project_type(str(_project_ref[0]))
                abs_path = _project_ref[0].resolve()
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

        abs_path = _project_ref[0].resolve()
        ptype = detect_project_type(str(_project_ref[0]))

        # 统计文件数和语言分布（快速 scadir 扫描，跳过大型目录）
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
                     '.moat', 'dist', 'build', '.next', '.cache', 'site-packages',
                     'release', '.codegraph', '.upstream-openharness', '.agents',
                     '.backups', '.claude', '.codex', '.drift-baseline', '.gstack',
                     '.one', '.opencode', '.pytest_cache', '.ruff_cache', '.vscode',
                     '.github', '.openharness', '.venv_test'}

        def _scan_dir(dir_path: Path, depth: int = 0, max_depth: int = 4):
            nonlocal total_files, total_lines
            if depth > max_depth:
                return
            try:
                for entry in dir_path.iterdir():
                    if entry.name in skip_dirs or entry.name.startswith('.'):
                        continue
                    if entry.is_dir():
                        _scan_dir(entry, depth + 1, max_depth)
                    elif entry.is_file():
                        ext = entry.suffix.lower()
                        lang = lang_ext_map.get(ext)
                        if lang:
                            total_files += 1
                            lang_counts[lang] = lang_counts.get(lang, 0) + 1
                            if lang in ('Python', 'JavaScript', 'TypeScript', 'TSX', 'JSX', 'Go', 'Rust', 'Java', 'Ruby', 'Shell'):
                                try:
                                    total_lines += sum(1 for _ in entry.open(encoding='utf-8', errors='ignore'))
                                except Exception:
                                    pass
            except PermissionError:
                pass

        await asyncio.to_thread(_scan_dir, abs_path)

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
                br = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                                    cwd=str(abs_path), capture_output=True, text=True, timeout=5)
                git_info["branch"] = br.stdout.strip() if br.returncode == 0 else ""
                cm = subprocess.run(["git", "log", "-1", "--format=%h %s (%cr)"],
                                    cwd=str(abs_path), capture_output=True, text=True, timeout=5)
                git_info["last_commit"] = cm.stdout.strip() if cm.returncode == 0 else ""
                st = subprocess.run(["git", "status", "--porcelain"],
                                    cwd=str(abs_path), capture_output=True, text=True, timeout=5)
                git_info["dirty"] = bool(st.stdout.strip()) if st.returncode == 0 else False
        except Exception:
            pass

        # 项目大小（只统计代码文件）
        try:
            total_size = 0
            for entry in abs_path.iterdir():
                if entry.name in skip_dirs or entry.name.startswith('.'):
                    continue
                if entry.is_dir():
                    for f in entry.rglob('*'):
                        if f.is_file() and f.suffix.lower() in lang_ext_map:
                            try:
                                total_size += f.stat().st_size
                            except Exception:
                                pass
                elif entry.is_file() and entry.suffix.lower() in lang_ext_map:
                    total_size += entry.stat().st_size
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
            mem = MoatMemory(str(_project_ref[0]))

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
                "db_path": str(_project_ref[0] / ".moat" / "memory.db"),
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
                "recent_templates": templates[-5:] if templates else [],
                "recent_skills": skills[-5:] if skills else [],
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "stats": {"redlines": 0, "lessons": 0, "templates": 0, "skills": 0, "total": 0},
            }

    @app.get("/api/moat/evolution")
    async def get_evolution(
        search: str = Query(""),
        category: str = Query(""),
        risk: str = Query(""),
        status: str = Query(""),
        limit: int = Query(20),
        offset: int = Query(0),
    ):
        """进化系统：代码修改历史（proposals），支持搜索/筛选/分页"""
        try:
            common_paths = [
                _project_ref[0] / "packages" / "backend" / "src" / "data" / "evolution" / "proposals.db",
                _project_ref[0] / "data" / "evolution" / "proposals.db",
                _project_ref[0] / "packages" / "backend" / "data" / "evolution" / "proposals.db",
            ]
            proposals_db = None
            for p in common_paths:
                if p.exists():
                    proposals_db = p
                    break

            if not proposals_db:
                json_dir = _project_ref[0] / "data" / "evolution" / "proposals"
                json_proposals = []
                if json_dir.exists():
                    import glob as gb
                    for f in sorted(json_dir.glob("*.json"))[:20]:
                        try:
                            data = json.loads(f.read_text())
                            json_proposals.append(data)
                        except Exception:
                            pass
                return {
                    "available": bool(json_proposals),
                    "db_path": "",
                    "db_available": False,
                    "total_proposals": len(json_proposals),
                    "json_proposals": json_proposals,
                    "proposals": [],
                    "stats": {"pending": 0, "applied": 0, "rejected": 0, "total": len(json_proposals)},
                    "cat_breakdown": [],
                }

            import sqlite3
            conn = sqlite3.connect(str(proposals_db))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # 统计状态（全量，不受筛选影响）
            cur.execute("SELECT status, COUNT(*) as cnt FROM proposals GROUP BY status")
            stats = {"pending": 0, "applied": 0, "rejected": 0, "total": 0}
            for row in cur.fetchall():
                stats[row["status"]] = row["cnt"]
                stats["total"] += row["cnt"]

            # 全量分类统计
            cur.execute("SELECT category, COUNT(*) as cnt FROM proposals GROUP BY category ORDER BY cnt DESC")
            cat_breakdown = [{"name": row["category"], "count": row["cnt"]} for row in cur.fetchall()]

            # 构建筛选条件
            where_clauses = []
            params = []
            if search:
                where_clauses.append("(title LIKE ? OR description LIKE ? OR file_path LIKE ?)")
                params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
            if category:
                where_clauses.append("category = ?")
                params.append(category)
            if risk:
                where_clauses.append("risk = ?")
                params.append(risk)
            if status:
                where_clauses.append("status = ?")
                params.append(status)

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            # 筛选后总数
            cur.execute(f"SELECT COUNT(*) as cnt FROM proposals WHERE {where_sql}", params)
            filtered_total = cur.fetchone()["cnt"]

            # 获取筛选后提案
            cur.execute(f"""
                SELECT proposal_id, title, description, risk, category, status,
                       file_path, score, created_at, applied_at
                FROM proposals WHERE {where_sql}
                ORDER BY created_at DESC LIMIT ? OFFSET ?
            """, params + [limit, offset])
            cols = [desc[0] for desc in cur.description]
            proposals = [dict(zip(cols, row)) for row in cur.fetchall()]
            conn.close()

            # 每种分类在筛选后的数量
            if category or search or risk or status:
                conn2 = sqlite3.connect(str(proposals_db))
                conn2.row_factory = sqlite3.Row
                cur2 = conn2.cursor()
                cur2.execute(f"SELECT category, COUNT(*) as cnt FROM proposals WHERE {where_sql} GROUP BY category ORDER BY cnt DESC", params)
                cat_breakdown = [{"name": row["category"], "count": row["cnt"]} for row in cur2.fetchall()]
                conn2.close()

            return {
                "available": True,
                "db_path": str(proposals_db),
                "db_available": True,
                "total_proposals": stats["total"],
                "filtered_total": filtered_total,
                "proposals": proposals,
                "stats": stats,
                "cat_breakdown": cat_breakdown,
                "json_proposals": [],
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "total_proposals": 0,
                "proposals": [],
                "stats": {"pending": 0, "applied": 0, "rejected": 0, "total": 0},
            }

    @app.post("/api/moat/baseline/save")
    async def save_baseline():
        from moat.baseline import BaselineManager
        bm = BaselineManager(_project_ref[0])
        data = bm.save()
        return {"success": True, "baseline": data}

    @app.get("/api/moat/embedding-config")
    async def get_embedding_config():
        """读取向量模型配置"""
        settings_path = Path.home() / '.openharness' / 'one_settings.json'
        try:
            config = {}
            if settings_path.exists():
                data = json.loads(settings_path.read_text(encoding='utf-8'))
                config['base_url'] = data.get('embedding_base_url', '')
                config['api_key'] = data.get('embedding_api_key', '')
                config['model'] = data.get('embedding_model', '')
                # Also check nested
                if not config['base_url']:
                    config['base_url'] = data.get('embedding', {}).get('base_url', '')
                if not config['api_key']:
                    config['api_key'] = data.get('embedding', {}).get('api_key', '')
                if not config['model']:
                    config['model'] = data.get('embedding', {}).get('model', '')
            # 环境变量覆盖
            config['base_url'] = os.environ.get('OPENHARNESS_EMBEDDING_BASE_URL', config['base_url'])
            config['api_key'] = os.environ.get('OPENHARNESS_EMBEDDING_API_KEY', config['api_key'])
            config['model'] = os.environ.get('OPENHARNESS_EMBEDDING_MODEL', config['model'])
            return {"available": True, "config": config}
        except Exception as e:
            return {"available": False, "error": str(e), "config": {"base_url": "", "api_key": "", "model": ""}}

    @app.post("/api/moat/embedding-config")
    async def save_embedding_config(data: dict):
        """保存向量模型配置到 one_settings.json"""
        try:
            settings_path = Path.home() / '.openharness' / 'one_settings.json'
            existing = {}
            if settings_path.exists():
                existing = json.loads(settings_path.read_text(encoding='utf-8'))
            # 更新 embedding 配置
            url = data.get('base_url', '').strip()
            key = data.get('api_key', '').strip()
            model = data.get('model', '').strip()
            if url:
                existing['embedding_base_url'] = url
            if key:
                existing['embedding_api_key'] = key
            if model:
                existing['embedding_model'] = model
            # Also update nested
            if 'embedding' not in existing:
                existing['embedding'] = {}
            if url:
                existing['embedding']['base_url'] = url
            if key:
                existing['embedding']['api_key'] = key
            if model:
                existing['embedding']['model'] = model
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            settings_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
            return {"success": True, "config": {"base_url": url, "api_key": key, "model": model}}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.get("/api/moat/version")
    async def check_version():
        """检查当前版本和 PyPI 最新版本"""
        import importlib, moat
        importlib.reload(moat)
        import urllib.request, json as jlib
        current = moat.__version__
        latest = current
        update_available = False
        try:
            req = urllib.request.Request(
                "https://pypi.org/pypi/moat-ai/json",
                headers={"User-Agent": "MoatDashboard/1.0"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = jlib.loads(resp.read().decode())
                latest = data["info"]["version"]
                # 比较版本号
                def _ver(v):
                    return tuple(int(x) for x in v.split("."))
                update_available = _ver(latest) > _ver(current)
        except Exception:
            pass
        return {
            "current": current,
            "latest": latest,
            "update_available": update_available,
            "pypi_url": "https://pypi.org/project/moat-ai/",
        }

    @app.post("/api/moat/upgrade")
    async def run_upgrade():
        """升级 moat-ai 到最新版本"""
        import subprocess, sys, threading, queue

        result_queue: queue.Queue = queue.Queue()

        def _run():
            try:
                # 使用 uv pip 确保环境一致（系统 Python 的 pip 可能与 uv 管理的 Python 不兼容）
                proc = subprocess.run(
                    ["uv", "pip", "install", "--upgrade", "moat-ai"],
                    capture_output=True, text=True, timeout=120,
                )
                result_queue.put({
                    "success": proc.returncode == 0,
                    "stdout": proc.stdout[-1000:],
                    "stderr": proc.stderr[-500:],
                    "returncode": proc.returncode,
                })
            except subprocess.TimeoutExpired:
                result_queue.put({"success": False, "error": "升级超时（>120秒）"})
            except Exception as e:
                result_queue.put({"success": False, "error": str(e)})

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        try:
            return result_queue.get(timeout=130)
        except queue.Empty:
            return {"success": False, "error": "升级超时"}

    @app.get("/api/moat/leak-check")
    async def run_leak_check(scan_ai: bool = Query(False)):
        """执行泄露检测扫描"""
        try:
            from moat.verification.operators.leakage_detection import LeakageDetectionOperator
            from moat.verification.types import VerificationContext
            import datetime

            ctx = VerificationContext(project_path=_project_ref[0], config={"scan_ai": scan_ai})
            op = LeakageDetectionOperator()
            result = op.verify(ctx)

            # 统计
            total = len(result.violations)
            by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0, "warning": 0}
            by_category = {}
            for v in result.violations:
                sev = v.severity.value if hasattr(v.severity, 'value') else str(v.severity)
                sev_lower = sev.lower()
                if sev_lower in by_severity:
                    by_severity[sev_lower] += 1
                cat = v.rule or 'other'
                by_category[cat] = by_category.get(cat, 0) + 1

            violations_data = []
            for v in result.violations:
                violations_data.append({
                    "severity": v.severity.value if hasattr(v.severity, 'value') else str(v.severity),
                    "category": v.rule or 'other',
                    "message": v.message,
                    "file_path": str(v.file_path) if v.file_path else '',
                    "line": v.line,
                    "recommendation": v.suggestion or '',
                    "rule": v.rule or '',
                })

            return {
                "available": True,
                "total_violations": total,
                "by_severity": by_severity,
                "by_category": by_category,
                "score": getattr(result, 'score', 0),
                "passed": getattr(result, 'passed', total == 0),
                "violations": violations_data[:100],
                "timestamp": datetime.datetime.now().isoformat(),
                "scan_ai": scan_ai,
            }
        except Exception as e:
            return {"available": False, "error": str(e), "total_violations": 0, "violations": []}

    @app.get("/api/moat/accept")
    async def run_accept(diff: bool = Query(True), timeout_seconds: int = Query(60)):
        """🏗 架构验收 8 步法"""
        import datetime, json
        try:
            from moat.checks.acceptance import ArchitectRunner
            from pathlib import Path
            runner = ArchitectRunner(_project_ref[0])
            report = runner.run(diff_mode=diff)

            # 从 report 对象提取完整规则数据（to_dict 只返回计数，不返回详情）
            rules_data = []
            for r in getattr(report, 'rules', []):
                rule_data = r.to_dict() if hasattr(r, 'to_dict') else {}
                # 补充实际证据和违规详情（to_dict 只返回计数）
                if hasattr(r, 'evidence'):
                    rule_data['evidence'] = [str(e)[:500] for e in (r.evidence or [])]
                if hasattr(r, 'violations'):
                    rule_data['violations'] = (r.violations or [])[:50]
                if hasattr(r, 'manual_check_items'):
                    rule_data['manual_check_items'] = (r.manual_check_items or [])
                # 补充 passed 的布尔值
                if 'passed' in rule_data and rule_data['passed'] is None:
                    rule_data['passed'] = False
                rules_data.append(rule_data)

            data = report.to_dict() if hasattr(report, 'to_dict') else {
                "overall_score": getattr(report, 'overall_score', 0),
                "passed": getattr(report, 'passed', False),
                "total_auto": getattr(report, 'total_auto', 0),
                "total_manual": getattr(report, 'total_manual', 0),
                "passed_auto": getattr(report, 'passed_auto', 0),
                "execution_time": getattr(report, 'execution_time', 0),
                "version": getattr(report, 'version', '1.0'),
                "rules": [],
            }
            # 替换精简 rules 为完整 rules
            data['rules'] = rules_data
            # 重新统计违规总数
            total_violations = sum(len(r.get('violations', [])) for r in rules_data)
            total_evidence = sum(len(r.get('evidence', [])) for r in rules_data)
            total_manual = sum(len(r.get('manual_check_items', [])) for r in rules_data)
            data['total_violations'] = total_violations
            data['total_evidence'] = total_evidence
            data['total_manual_items'] = total_manual

            return {
                "available": True,
                "project": _project_ref[0].name,
                "timestamp": datetime.datetime.now().isoformat(),
                "diff_mode": diff,
                **data,
            }
        except Exception as e:
            import traceback
            return {"available": False, "error": str(e) + "\n" + traceback.format_exc()}

    @app.post("/api/moat/accept/generate-rules")
    async def generate_accept_rules():
        """生成 architect.yml 规则模板"""
        try:
            from moat.checks.acceptance.rule_registry import RuleRegistry
            path = RuleRegistry.save_template(_project_ref[0])
            return {
                "success": True,
                "path": str(path),
                "message": f"✅ 已生成: {path.name}",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

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
