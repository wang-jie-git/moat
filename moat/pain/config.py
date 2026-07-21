"""
Sensor 配置 — 决定哪些目录/文件安装传感器

约定:
  1. 项目根目录下的 moat.sensor.yml（或 yaml）自动加载
  2. CLI `moat sensor init` 自动检测项目类型并生成推荐配置
  3. 配置字段均为可选，缺省使用保守默认值
"""

import os
from pathlib import Path
from typing import Optional

# 默认配置（无配置时的保守行为）
DEFAULT_CONFIG = {
    "sensor": {
        "auto_inject": False,
        "include": [],
        "exclude": [
            "**/test_*.py",
            "**/conftest.py",
            "**/__init__.py",
            "**/migrations/**",
            "**/node_modules/**",
            "**/.venv/**",
            "**/venv/**",
            "**/site-packages/**",
            "**/__pycache__/**",
        ],
        "critical_patterns": [
            "*payment*",
            "*auth*",
            "*login*",
            "*checkout*",
            "*stripe*",
            "*database*",
            "*transaction*",
            "*webhook*",
        ],
        "alert": {
            "webhook": "",
        },
    }
}


def detect_project_type(project_root: str = ".") -> str:
    """自动检测项目类型（跳过大型目录）"""
    root = Path(project_root).resolve()

    clues = {
        "FastAPI": [
            root / "main.py",
            root / "app" / "main.py",
            root / "backend" / "main.py",
        ],
        "Django": [
            root / "manage.py",
        ],
        "Flask": [
            root / "app.py",
            root / "application.py",
        ],
        "CLI 工具": [
            root / "setup.py",
            root / "setup.cfg",
            root / "pyproject.toml",
        ],
        "数据处理": [
            root / "notebooks",
        ],
    }

    def _fast_rglob(pattern: str) -> list:
        """快速 rglob，跳过大型目录"""
        skip_names = {'.git', 'node_modules', '__pycache__', '.venv', 'venv',
                      '.next', 'dist', 'build', '.cache', '.moat', 'site-packages',
                      'release', 'codegraph', '.codegraph', '.upstream-openharness'}
        results = []
        try:
            for entry in root.iterdir():
                if entry.name in skip_names or entry.name.startswith('.'):
                    continue
                if entry.is_dir():
                    # 对一级子目录做有限深度搜索（最多 3 层）
                    results.extend(_fast_rglob_in_dir(entry, pattern, 0, 3, skip_names))
                elif entry.match(pattern):
                    results.append(entry)
        except PermissionError:
            pass
        return results

    def _fast_rglob_in_dir(directory: Path, pattern: str, depth: int, max_depth: int, skip_names: set) -> list:
        if depth > max_depth:
            return []
        results = []
        try:
            for entry in directory.iterdir():
                if entry.name in skip_names:
                    continue
                if entry.is_dir():
                    results.extend(_fast_rglob_in_dir(entry, pattern, depth + 1, max_depth, skip_names))
                elif entry.match(pattern):
                    results.append(entry)
        except PermissionError:
            pass
        return results

    for ptype, paths in clues.items():
        for p in paths:
            if p.exists():
                return ptype
            if p.name == "manage.py":
                matches = _fast_rglob("manage.py")
                if matches:
                    return ptype

    # 检查 packages 结构
    packages_dir = root / "packages"
    if packages_dir.is_dir():
        return "Monorepo"

    # 回退
    py_files = list(root.rglob("*.py"))
    if py_files:
        return "Python 项目"
    return "未知"


def suggest_include_patterns(project_type: str) -> list[str]:
    """根据项目类型推荐 include 模式"""
    suggestions = {
        "FastAPI": [
            "app/routes/**/*.py",
            "app/api/**/*.py",
            "app/services/**/*.py",
            "app/db/**/*.py",
            "app/tasks/**/*.py",
        ],
        "Django": [
            "*/views.py",
            "*/serializers.py",
            "*/services/**/*.py",
            "*/tasks.py",
            "*/management/commands/**/*.py",
        ],
        "Flask": [
            "app/routes.py",
            "app/*/routes.py",
            "app/services/**/*.py",
            "app/models/**/*.py",
        ],
        "Monorepo": [
            "packages/*/src/**/*.py",
            "packages/*/api/**/*.py",
            "packages/*/services/**/*.py",
        ],
        "CLI 工具": [
            "src/**/cli.py",
            "src/**/commands/**/*.py",
            "src/**/handlers/**/*.py",
        ],
        "数据处理": [
            "src/**/*.py",
            "scripts/**/*.py",
        ],
    }
    return suggestions.get(project_type, ["src/**/*.py"])


# ── 配置加载 ──────────────────────────────────────────────

def load_config(project_root: str = ".") -> dict:
    """加载 moat.sensor.yml，不存在则返回默认配置"""
    root = Path(project_root).resolve()

    for name in ("moat.sensor.yml", "moat.sensor.yaml", ".moat/sensor.yml"):
        path = root / name
        if path.exists():
            try:
                import yaml
                with open(path) as f:
                    cfg = yaml.safe_load(f)
                return _merge_config(DEFAULT_CONFIG, cfg or {})
            except ImportError:
                print("⚠️  需要安装 PyYAML: pip install pyyaml")
                return DEFAULT_CONFIG
            except Exception as e:
                print(f"⚠️  配置文件解析失败: {e}")
                return DEFAULT_CONFIG

    return dict(DEFAULT_CONFIG)  # 深拷贝


def save_config(config: dict, project_root: str = "."):
    """保存配置到 moat.sensor.yml"""
    root = Path(project_root).resolve()
    path = root / "moat.sensor.yml"
    try:
        import yaml
        with open(path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, indent=2, allow_unicode=True)
        print(f"✅ 配置已写入 {path}")
    except ImportError:
        print("⚠️  需要安装 PyYAML: pip install pyyaml")


def _merge_config(base: dict, override: dict) -> dict:
    """合并配置（只覆盖用户提供的字段）"""
    result = dict(base)
    sensor = dict(result.get("sensor", {}))
    override_sensor = override.get("sensor", {})
    for k in ("auto_inject", "include", "exclude", "critical_patterns"):
        if k in override_sensor:
            sensor[k] = override_sensor[k]
    if "alert" in override_sensor:
        alert = dict(sensor.get("alert", {}))
        alert.update(override_sensor["alert"])
        sensor["alert"] = alert
    if override_sensor.get("include"):
        sensor["auto_inject"] = True
    result["sensor"] = sensor
    return result
