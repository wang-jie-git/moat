"""API 端点检查 — L1: 子系统 API 是否存活"""
import subprocess
import sys
import json
from pathlib import Path


def detect_api_type(project_root: Path) -> str | None:
    """自动检测项目使用的 API 框架"""
    has_fastapi = any(f.name == "server.py" or "fastapi" in f.read_text(errors="ignore").lower()
                      for f in project_root.rglob("*.py")
                      if "fastapi" in f.read_text(errors="ignore").lower())
    if has_fastapi:
        return "fastapi"
    has_flask = any("flask" in f.read_text(errors="ignore").lower()
                    for f in project_root.rglob("*.py"))
    if has_flask:
        return "flask"
    return None


def find_server_module(project_root: Path) -> str | None:
    """尝试找到 FastAPI app 所在的模块"""
    # 常见入口
    candidates = [
        "server", "main", "app", "api", "backend.server",
        "one_backend.server", "src.server", "src.main",
    ]
    for mod in candidates:
        # 尝试启动一个简单的导入测试
        result = subprocess.run(
            [sys.executable, "-c", f"import {mod}; print('OK')"],
            capture_output=True, text=True, timeout=10,
            cwd=str(project_root),
        )
        if result.returncode == 0:
            return mod
    return None


def run_api_check(project_root: Path, base_url: str = "http://localhost:8000") -> list[dict]:
    """检查核心 API 端点（需要服务器运行中）"""
    import httpx

    errors = []
    # 尝试发现的端点
    discovered_endpoints = _discover_endpoints(project_root)

    try:
        r = httpx.get(f"{base_url}/openapi.json", timeout=5)
        if r.status_code == 200:
            schema = r.json()
            for path, methods in schema.get("paths", {}).items():
                for method in methods:
                    discovered_endpoints.append({
                        "path": path,
                        "method": method.upper(),
                        "name": methods[method].get("summary", ""),
                    })
    except Exception:
        pass  # 没有 OpenAPI schema，用自动发现的

    if not discovered_endpoints:
        return errors  # 静默跳过

    with httpx.Client(base_url=base_url, timeout=5) as client:
        for ep in discovered_endpoints[:50]:  # 最多测 50 个
            try:
                method = ep["method"].lower()
                resp = getattr(client, method)(ep["path"])
                if resp.status_code >= 500:
                    errors.append({
                        "file": ep["path"],
                        "level": "L1",
                        "type": "api_error",
                        "message": f"{ep['method']} {ep['path']} → {resp.status_code}: {resp.text[:200]}",
                    })
            except httpx.TimeoutException:
                errors.append({
                    "file": ep["path"],
                    "level": "L1",
                    "type": "api_timeout",
                    "message": f"{ep['method']} {ep['path']} → Timeout",
                })
            except Exception as e:
                errors.append({
                    "file": ep["path"],
                    "level": "L1",
                    "type": "api_exception",
                    "message": f"{ep['method']} {ep['path']} → {e}",
                })

    return errors


def _discover_endpoints(project_root: Path) -> list[dict]:
    """从路由文件中发现端点"""
    endpoints = []
    for f in project_root.rglob("*.py"):
        if any(p in f.parts for p in (".venv", "venv", "__pycache__", ".git")):
            continue
        text = f.read_text(errors="ignore")
        # FastAPI router decorators
        for line in text.split("\n"):
            line = line.strip()
            # @router.get(...) or @app.get(...)
            if "@" in line and ("get(" in line or "post(" in line or
                                "put(" in line or "delete(" in line or
                                "patch(" in line):
                # Extract path
                for method in ["get", "post", "put", "delete", "patch"]:
                    if f".{method}(" in line:
                        start = line.index(f".{method}(") + len(method) + 1
                        end = line.index(")", start) if ")" in line[start:] else len(line)
                        path = line[start:end].strip("\"'")
                        if path and path.startswith("/"):
                            endpoints.append({
                                "path": path,
                                "method": method.upper(),
                                "name": "",
                            })
                        break
    return endpoints