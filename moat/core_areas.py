"""核心业务探测模块

自动识别项目中的核心业务区域（鉴权、支付、API 等），
允许用户标记敏感级别，用于 Pain Score 权重计算。
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CoreArea:
    """核心业务区域"""
    pattern: str  # 路径匹配模式（如 "src/auth/**/*.py"）
    name: str  # 区域名称（如 "鉴权"）
    sensitivity: str  # 敏感级别（critical/high/medium/low）
    pain_multiplier: float  # Pain Score 乘数（1.0-3.0）
    description: str = ""  # 描述

    def __post_init__(self):
        """验证数据"""
        valid_sensitivities = {"critical", "high", "medium", "low"}
        if self.sensitivity not in valid_sensitivities:
            raise ValueError(f"Invalid sensitivity: {self.sensitivity}")
        if not (1.0 <= self.pain_multiplier <= 3.0):
            raise ValueError(f"Invalid pain_multiplier: {self.pain_multiplier}")


class CoreAreaDetector:
    """核心业务探测器

    识别模式：
    - 鉴权（auth, login, session, token）
    - 支付（payment, checkout, billing）
    - 数据核心（database, model, repository）
    - API 网关（gateway, router, middleware）
    """

    # 核心业务关键词映射
    CORE_AREA_PATTERNS = {
        "鉴权": {
            "keywords": ["auth", "login", "session", "token", "credential", "permission"],
            "sensitivity": "critical",
            "pain_multiplier": 2.5,
            "description": "用户鉴权与会话管理",
        },
        "支付": {
            "keywords": ["payment", "checkout", "billing", "stripe", "paypal", "invoice"],
            "sensitivity": "critical",
            "pain_multiplier": 2.5,
            "description": "支付与计费逻辑",
        },
        "数据核心": {
            "keywords": ["database", "model", "repository", "dao", "entity", "schema"],
            "sensitivity": "high",
            "pain_multiplier": 2.0,
            "description": "数据访问与存储层",
        },
        "API 网关": {
            "keywords": ["api", "router", "gateway", "middleware", "controller", "endpoint"],
            "sensitivity": "high",
            "pain_multiplier": 2.0,
            "description": "API 路由与中间件",
        },
        "配置中心": {
            "keywords": ["config", "setting", "env", "secret"],
            "sensitivity": "high",
            "pain_multiplier": 2.0,
            "description": "配置与密钥管理",
        },
        "用户核心": {
            "keywords": ["user", "account", "profile", "member"],
            "sensitivity": "medium",
            "pain_multiplier": 1.5,
            "description": "用户账户与资料",
        },
    }

    def __init__(self, project_root: Path):
        self.project = project_root.resolve()

    def detect(self, auto_confirm: bool = False) -> list[CoreArea]:
        """检测核心业务区域

        Args:
            auto_confirm: 是否自动确认（非交互模式）

        Returns:
            核心业务区域列表
        """
        detected_areas = []

        # 扫描项目文件
        for area_name, area_config in self.CORE_AREA_PATTERNS.items():
            matched_paths = self._find_matching_paths(area_config["keywords"])

            if matched_paths:
                # 生成路径模式（简化版）
                pattern = self._generate_pattern(matched_paths)

                detected_areas.append(CoreArea(
                    pattern=pattern,
                    name=area_name,
                    sensitivity=area_config["sensitivity"],
                    pain_multiplier=area_config["pain_multiplier"],
                    description=area_config["description"],
                ))

        if not auto_confirm and detected_areas:
            detected_areas = self._interactive_confirm(detected_areas)

        return detected_areas

    def _find_matching_paths(self, keywords: list[str]) -> list[str]:
        """查找匹配的路径"""
        matched = set()

        for keyword in keywords:
            # 查找包含关键词的目录
            for d in self.project.rglob("*"):
                if d.is_dir() and keyword in d.name.lower():
                    # 排除虚拟环境等
                    if any(p in d.parts for p in (".venv", "venv", "__pycache__", "node_modules")):
                        continue
                    matched.add(str(d.relative_to(self.project)))

        return sorted(matched)

    def _generate_pattern(self, paths: list[str]) -> str:
        """生成路径匹配模式"""
        if not paths:
            return ""

        # 提取公共前缀
        parts = paths[0].split("/")
        if len(parts) > 1:
            return "/".join(parts[:-1]) + "/**/*"

        return paths[0] + "/**/*"

    def _interactive_confirm(self, areas: list[CoreArea]) -> list[CoreArea]:
        """交互式确认核心区域"""
        import sys

        if sys.stdin.isatty():
            try:
                print(f"\n⚡ 核心业务探测:")
                print(f"   检测到以下核心区域:\n")

                for idx, area in enumerate(areas, 1):
                    print(f"   {idx}. ✓ {area.pattern}")
                    print(f"      {area.name} ({area.sensitivity}) — {area.description}")

                print(f"\n   请标记敏感级别:")
                print(f"   [1] 极高敏感度（失败立即告警）: 所有区域")
                print(f"   [2] 高敏感度（失败警告）: 除用户核心外")
                print(f"   [3] 普通敏感度")
                print(f"   [Enter] 保持默认\n")

                choice = input(f"   请输入选项 [1-3/Enter]: ").strip()

                if choice == "1":
                    # 全部设为 critical
                    for area in areas:
                        area.sensitivity = "critical"
                        area.pain_multiplier = 2.5
                    print(f"   ✓ 所有区域已标记为极高敏感度")
                elif choice == "2":
                    # 数据核心/API/支付/鉴权 设为 high，用户核心保持 medium
                    for area in areas:
                        if area.name in ("数据核心", "API 网关", "配置中心"):
                            area.sensitivity = "high"
                            area.pain_multiplier = 2.0
                        elif area.name in ("鉴权", "支付"):
                            area.sensitivity = "critical"
                            area.pain_multiplier = 2.5
                    print(f"   ✓ 核心区域已标记为高敏感度")
                elif choice == "3":
                    # 全部设为 medium
                    for area in areas:
                        area.sensitivity = "medium"
                        area.pain_multiplier = 1.5
                    print(f"   ✓ 所有区域已标记为普通敏感度")
                else:
                    print(f"   ✓ 保持默认配置")

            except Exception:
                pass

        return areas

    def to_config(self, areas: list[CoreArea]) -> dict[str, Any]:
        """转换为配置字典"""
        return {
            "core_areas": [
                {
                    "pattern": area.pattern,
                    "name": area.name,
                    "sensitivity": area.sensitivity,
                    "pain_multiplier": area.pain_multiplier,
                    "description": area.description,
                }
                for area in areas
            ]
        }


def detect_core_areas(project_root: str = ".", auto_confirm: bool = False) -> list[CoreArea]:
    """便捷函数：检测核心业务区域

    Args:
        project_root: 项目根目录
        auto_confirm: 是否自动确认

    Returns:
        核心业务区域列表
    """
    root = Path(project_root).resolve()
    detector = CoreAreaDetector(root)
    return detector.detect(auto_confirm=auto_confirm)
