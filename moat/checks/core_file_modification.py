"""
Core File Modification Check — 核心文件修改检测

检测是否修改了受保护的核心文件，防止未经授权的改动。

设计原则：
- 白名单机制：只保护明确指定的核心文件
- 模式匹配：支持文件名模式匹配
- 可配置：用户可以在 .moat/moat.json 中自定义核心文件列表
- Git diff 感知：只检查实际修改的文件，不检查所有文件

触发条件：
- 任何涉及核心文件的修改都会触发 CRITICAL 级别的警告
"""

from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from moat.checks.base import Check, CheckResult

logger = logging.getLogger(__name__)


@dataclass
class CoreFileConfig:
    """核心文件配置"""
    name: str
    patterns: List[str]
    description: str
    severity: str = "critical"  # critical, warning, info
    requires_approval: bool = True  # 是否需要用户批准


# 默认核心文件列表（One 项目）
# 这些文件定义了产品的核心架构，修改前必须获得用户明确许可
DEFAULT_CORE_FILES = [
    CoreFileConfig(
        name="app_entry",
        patterns=["App.tsx", "App.jsx", "App.vue"],
        description="应用入口文件 - 路由配置、全局布局",
        severity="critical",
        requires_approval=True,
    ),
    CoreFileConfig(
        name="chat_page",
        patterns=["ChatPage.tsx", "ChatPage.jsx", "ChatPage.vue"],
        description="主对话页面 - WebSocket 生命周期管理",
        severity="critical",
        requires_approval=True,
    ),
    CoreFileConfig(
        name="server_entry",
        patterns=["server.py", "main.py", "app.py", "server.js"],
        description="后端入口文件 - 路由注册、服务启动",
        severity="critical",
        requires_approval=True,
    ),
    CoreFileConfig(
        name="websocket_logic",
        patterns=["*websocket*", "*ws*handler*", "*bridge*"],
        description="WebSocket 连接逻辑 - 连接管理、重连机制",
        severity="critical",
        requires_approval=True,
    ),
    CoreFileConfig(
        name="openharness_bridge",
        patterns=["*openharness*bridge*", "*engine*bridge*"],
        description="OpenHarness 引擎桥接层",
        severity="critical",
        requires_approval=True,
    ),
    CoreFileConfig(
        name="auth_config",
        patterns=["*auth*", "*permission*"],
        description="认证和权限配置",
        severity="critical",
        requires_approval=True,
    ),
]


class CoreFileModificationCheck(Check):
    """核心文件修改检测

    检测是否修改了受保护的核心文件，防止未经授权的改动。

    使用示例：
        check = CoreFileModificationCheck(Path.cwd(), config)
        result = check.run()
    """

    check_type = "core_file_modification"
    description = "检测是否修改了受保护的核心文件"

    def __init__(self, project_root: Path = None, config: Dict[str, Any] = None):
        # 兼容两种初始化方式：
        # 1. CoreFileModificationCheck(config) — 从 __init__.py 调用（第一个参数是 dict）
        # 2. CoreFileModificationCheck(project_root, config) — 标准 Check 基类

        # 如果第一个参数是 dict，说明是方式 1
        if isinstance(project_root, dict):
            config = project_root
            project_root = None

        # 如果 project_root 仍然为 None，使用当前目录
        if project_root is None:
            project_root = Path.cwd()

        super().__init__(project_root, config or {})
        self.severity = self.config.get("severity", "critical")
        self.core_files = self._load_core_files()
        self.enabled = self.config.get("enabled", True)

    def _load_core_files(self) -> List[CoreFileConfig]:
        """加载核心文件配置

        优先级：
        1. 用户自定义配置（.moat/moat.json）
        2. 默认核心文件列表
        """
        user_config = self.config.get("core_files", [])
        if user_config:
            return [
                CoreFileConfig(
                    name=c.get("name", "unknown"),
                    patterns=c.get("patterns", []),
                    description=c.get("description", ""),
                    severity=c.get("severity", "critical"),
                    requires_approval=c.get("requires_approval", True),
                )
                for c in user_config
            ]
        return DEFAULT_CORE_FILES

    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """检查文件路径是否匹配模式

        支持：
        - 精确匹配："App.tsx"
        - 通配符："*websocket*", "*bridge*"
        - 正则表达式（如果以 ^ 开头）
        """
        if pattern.startswith("^"):
            # 正则表达式
            return bool(re.match(pattern, file_path))
        elif "*" in pattern:
            # 通配符模式
            regex = pattern.replace("*", ".*")
            return bool(re.search(regex, file_path, re.IGNORECASE))
        else:
            # 精确匹配（不区分大小写）
            return file_path.lower() == pattern.lower()

    def _find_core_file(self, file_path: str) -> Optional[CoreFileConfig]:
        """查找文件是否匹配任何核心文件规则"""
        for core_file in self.core_files:
            for pattern in core_file.patterns:
                if self._matches_pattern(file_path, pattern):
                    return core_file
        return None

    def get_changed_files(self, repo_path: Path) -> List[str]:
        """获取已修改的文件列表（来自 git diff）"""
        try:
            import subprocess

            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                files = [f.strip() for f in result.stdout.split("\n") if f.strip()]
                return files
            else:
                logger.warning(f"Failed to get git diff: {result.stderr}")
                return []
        except Exception as e:
            logger.warning(f"Failed to get changed files: {e}")
            return []

    def run(self) -> list[CheckResult]:
        """运行核心文件修改检测

        Returns:
            list[CheckResult]: 检查结果列表
        """
        if not self.enabled:
            return [CheckResult(
                type="pass",
                message="核心文件修改检测已禁用",
            )]

        # 获取修改的文件列表
        diff_files = self.get_changed_files(self.project)

        if not diff_files:
            return [CheckResult(
                type="pass",
                message="没有检测到文件修改",
            )]

        # 检查是否有核心文件被修改
        violations = []
        for file_path in diff_files:
            core_file = self._find_core_file(file_path)
            if core_file:
                violations.append({
                    "file": file_path,
                    "core_file_name": core_file.name,
                    "description": core_file.description,
                    "severity": core_file.severity,
                    "requires_approval": core_file.requires_approval,
                })

        if not violations:
            return [CheckResult(
                type="pass",
                message=f"检查了 {len(diff_files)} 个文件，没有核心文件被修改",
            )]

        # 生成违规报告
        violation_messages = []
        for v in violations:
            msg = f"[{v['severity'].upper()}] {v['file']}\n"
            msg += f"  核心文件类型: {v['core_file_name']}\n"
            msg += f"  说明: {v['description']}\n"
            if v['requires_approval']:
                msg += f"  ⚠️  修改此文件需要用户明确批准\n"
            violation_messages.append(msg)

        message = f"检测到 {len(violations)} 个核心文件被修改:\n" + "\n".join(violation_messages)

        # 如果有 critical 级别的违规，返回 FAIL
        has_critical = any(v['severity'] == 'critical' for v in violations)
        status = "fail" if has_critical else "warn"

        return [CheckResult(
            type=status,
            message=message,
            metadata={
                "violations": violations,
                "total_violations": len(violations),
                "files_checked": len(diff_files),
            },
        )]

    def get_core_files(self) -> List[CoreFileConfig]:
        """获取当前保护的核心文件列表"""
        return self.core_files

    def add_core_file(self, name: str, patterns: List[str], description: str, severity: str = "critical") -> None:
        """动态添加核心文件规则

        Args:
            name: 规则名称
            patterns: 文件名模式列表
            description: 描述
            severity: 严重级别
        """
        self.core_files.append(
            CoreFileConfig(
                name=name,
                patterns=patterns,
                description=description,
                severity=severity,
            )
        )


# 便捷函数
def check_core_files(repo_path: Path, diff_files: List[str] = None, config: Dict[str, Any] = None) -> CheckResult:
    """便捷函数：检查核心文件修改

    Args:
        repo_path: Git 仓库路径
        diff_files: 待检查的文件列表
        config: 配置字典

    Returns:
        CheckResult: 检查结果
    """
    check = CoreFileModificationCheck(config)
    return check.run(repo_path, diff_files)
