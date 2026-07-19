"""版本检查 — 自动检测 PyPI 最新版本

零新增依赖，使用标准库 urllib。
每天最多查一次（缓存到 .moat/version_cache.json）。
"""
import json
import os
import time
import urllib.request
from pathlib import Path


def get_current_version() -> str:
    """获取当前安装版本。"""
    try:
        from moat import __version__
        return __version__
    except ImportError:
        pass
    try:
        import importlib.metadata
        return importlib.metadata.version("moat-ai")
    except Exception:
        return "unknown"


def check_latest_version(project_root: str | Path | None = None) -> str | None:
    """检查 PyPI 最新版本。返回版本号或 None（检查失败/缓存有效期内）。"""
    current = get_current_version()
    cache_path = _get_cache_path(project_root)

    # 检查缓存
    if cache_path and cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text())
            if cache.get("version") and cache.get("checked_at"):
                # 24 小时内不重复检查
                if time.time() - cache["checked_at"] < 86400:
                    if cache["version"] != current:
                        return cache["version"]
                    return None
        except Exception:
            pass

    # 请求 PyPI
    try:
        req = urllib.request.Request(
            "https://pypi.org/pypi/moat-ai/json",
            headers={"User-Agent": "moat-ai/version-check"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            latest = data["info"]["version"]

        # 写入缓存
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps({
                "version": latest,
                "checked_at": time.time(),
            }))

        if latest != current:
            return latest
        return None

    except Exception:
        return None


def _get_cache_path(project_root: str | Path | None) -> Path | None:
    """获取缓存文件路径。"""
    if project_root:
        p = Path(project_root) / ".moat" / "version_cache.json"
        if p.parent.exists():
            return p
    # 尝试用户目录
    home = Path.home() / ".moat" / "version_cache.json"
    if home.parent.exists() or home.parent.parent.exists():
        return home
    return None


def format_version_notice(latest: str) -> str:
    """格式化版本更新提示。"""
    current = get_current_version()
    return (
        f"📦 新版本 v{latest} 可用 (当前: v{current})\n"
        f"   升级: pip install moat-ai --upgrade"
    )