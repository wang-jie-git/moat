"""增强的配置加载器（v1.0.8）

支持多源配置：
1. .moat/config.json（推荐）
2. .moat/moat.json（兼容）
3. pyproject.toml [tool.moat] 节
4. package.json moat 字段
5. .moatignore 忽略文件

优先级（从高到低）：
1. .moatignore
2. pyproject.toml / package.json
3. .moat/config.json
4. .moat/moat.json
"""
import json
import re
from pathlib import Path
from typing import Any


def load_enhanced_config(project_root: Path) -> dict[str, Any]:
    """加载增强配置

    从多个源合并配置，优先级从高到低：
    1. .moatignore
    2. pyproject.toml / package.json
    3. .moat/config.json
    4. .moat/moat.json

    Args:
        project_root: 项目根目录

    Returns:
        合并后的配置字典
    """
    config = {}

    # 1. 加载 .moatignore
    moatignore = _load_moatignore(project_root)
    if moatignore:
        config.setdefault("ignore", {})
        config["ignore"]["patterns"] = moatignore

    # 2. 加载项目级配置
    project_config = _load_project_level_config(project_root)
    if project_config:
        config = _deep_merge(config, project_config)

    # 3. 加载 .moat/config.json
    local_config = _load_json_config(project_root / ".moat" / "config.json")
    if local_config:
        config = _deep_merge(config, local_config)

    # 4. 加载 .moat/moat.json（兼容旧格式）
    moat_json_config = _load_json_config(project_root / ".moat" / "moat.json")
    if moat_json_config:
        config = _deep_merge(config, moat_json_config)

    return config


def _load_moatignore(project_root: Path) -> list[str] | None:
    """加载 .moatignore 文件

    Args:
        project_root: 项目根目录

    Returns:
        忽略模式列表
    """
    moatignore_path = project_root / ".moatignore"
    if not moatignore_path.exists():
        return None

    try:
        patterns = []
        for line in moatignore_path.read_text(encoding="utf-8").split("\n"):
            line = line.strip()
            # 跳过空行和注释
            if line and not line.startswith("#"):
                patterns.append(line)
        return patterns if patterns else None
    except Exception:
        return None


def _load_project_level_config(project_root: Path) -> dict[str, Any] | None:
    """加载项目级配置（pyproject.toml / package.json）

    Args:
        project_root: 项目根目录

    Returns:
        配置字典或 None
    """
    config = {}

    # 尝试 pyproject.toml
    pyproject_path = project_root / "pyproject.toml"
    if pyproject_path.exists():
        pyproject_config = _load_pyproject_toml(pyproject_path)
        if pyproject_config:
            config = _deep_merge(config, pyproject_config)

    # 尝试 package.json
    package_json_path = project_root / "package.json"
    if package_json_path.exists():
        package_config = _load_package_json(package_json_path)
        if package_config:
            config = _deep_merge(config, package_config)

    return config if config else None


def _load_pyproject_toml(pyproject_path: Path) -> dict[str, Any] | None:
    """从 pyproject.toml 加载配置

    Args:
        pyproject_path: pyproject.toml 路径

    Returns:
        配置字典或 None
    """
    try:
        # 优先使用 tomllib（Python 3.11+）
        try:
            import tomllib
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
        except ImportError:
            # 降级到 tomli
            try:
                import tomli as tomllib
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
            except ImportError:
                # 降级到正则解析
                return _load_pyproject_toml_regex(pyproject_path)

        # 提取 [tool.moat]
        moat_config = data.get("tool", {}).get("moat", {})
        return moat_config if moat_config else None

    except Exception:
        return None


def _load_pyproject_toml_regex(pyproject_path: Path) -> dict[str, Any] | None:
    """使用正则解析 pyproject.toml（降级方案）

    Args:
        pyproject_path: pyproject.toml 路径

    Returns:
        配置字典或 None
    """
    try:
        content = pyproject_path.read_text(encoding="utf-8")

        # 查找 [tool.moat]
        config = {}
        if "[tool.moat]" in content:
            # 提取配置项
            pattern = r'(?:enabled_rules|rules|ignore|severity)\s*=\s*(\[[^\]]*\])'
            matches = re.findall(pattern, content)

            for match in matches:
                try:
                    value = json.loads(match)
                    config["rules"] = value
                except Exception:
                    pass

            return config if config else None

    except Exception:
        pass

    return None


def _load_package_json(package_json_path: Path) -> dict[str, Any] | None:
    """从 package.json 加载配置

    Args:
        package_json_path: package.json 路径

    Returns:
        配置字典或 None
    """
    try:
        with open(package_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 提取 moat 字段
        moat_config = data.get("moat", {})
        return moat_config if moat_config else None

    except Exception:
        return None


def _load_json_config(config_path: Path) -> dict[str, Any] | None:
    """加载 JSON 配置文件

    Args:
        config_path: 配置文件路径

    Returns:
        配置字典或 None
    """
    if not config_path.exists():
        return None

    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """深度合并字典

    Args:
        base: 基础字典
        override: 覆盖字典

    Returns:
        合并后的字典
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def should_ignore_file(file_path: Path, project_root: Path, config: dict[str, Any]) -> bool:
    """检查文件是否应该被忽略

    Args:
        file_path: 文件路径
        project_root: 项目根目录
        config: 配置字典

    Returns:
        是否应该忽略
    """
    # 检查 .moatignore
    ignore_patterns = config.get("ignore", {}).get("patterns", [])
    if ignore_patterns:
        rel_path = str(file_path.relative_to(project_root))
        for pattern in ignore_patterns:
            if re.match(pattern, rel_path) or pattern in rel_path:
                return True

    # 检查内置忽略规则
    skip_patterns = {
        ".venv", "venv", "__pycache__", ".git",
        "node_modules", ".next", ".nuxt", "dist", "build",
    }
    file_str = str(file_path)
    if any(pattern in file_str for pattern in skip_patterns):
        return True

    # 检查规则配置中的忽略列表
    rules_config = config.get("rules", {})
    if rules_config.get("skip_test_files", True):
        if "test" in file_path.name.lower() or "tests" in file_path.parts:
            return True

    return False
