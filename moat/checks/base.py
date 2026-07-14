"""
Moat 检查基类

所有语言检查（Python/TypeScript/Go...）都继承这个基类。
提供统一的接口：pass/fail/warn/skip + 结果收集。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CheckResult:
    """检查结果"""
    type: str = "info"  # pass / fail / skip / error / warn
    message: str = ""
    file: str | None = None
    line: int | None = None
    level: str = "INFO"  # INFO / WARN / ERROR
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于 JSON 输出）"""
        return {
            "type": self.type,
            "message": self.message,
            "file": self.file,
            "line": self.line,
            "level": self.level,
            "metadata": self.metadata,
        }


class Check(ABC):
    """检查基类

    使用示例:
        class MyCheck(Check):
            def run(self) -> list[CheckResult]:
                for file in self.project.rglob("**/*.py"):
                    if self._has_issue(file):
                        yield self.fail(
                            "发现问题",
                            file=str(file),
                            line=10,
                        )
                yield self.pass("检查通过")
    """

    def __init__(self, project_root: Path, config: dict[str, Any] | None = None):
        self.project = project_root.resolve()
        self.config = config or {}

    @abstractmethod
    def run(self) -> list[CheckResult]:
        """执行检查，返回结果列表"""
        ...

    # ── 便捷方法（实例方法） ──

    def pass_check(self, msg: str) -> CheckResult:
        """检查通过"""
        return CheckResult(type="pass", message=msg, level="INFO")

    def fail(self, msg: str, file: str | None = None, line: int | None = None, **kwargs) -> CheckResult:
        """检查失败"""
        return CheckResult(
            type="fail",
            message=msg,
            file=file,
            line=line,
            level="ERROR",
            metadata=kwargs,
        )

    def warn(self, msg: str, file: str | None = None, line: int | None = None) -> CheckResult:
        """警告"""
        return CheckResult(type="warn", message=msg, file=file, line=line, level="WARN")

    def skip(self, msg: str) -> CheckResult:
        """跳过"""
        return CheckResult(type="skip", message=msg, level="INFO")

    # ── 辅助方法 ──

    def _find_files(self, pattern: str) -> list[Path]:
        """查找匹配的文件"""
        return list(self.project.rglob(pattern))

    def _should_skip(self, file: Path) -> bool:
        """检查文件是否应该跳过"""
        skip_exact = {"__pycache__", ".git", "node_modules",
                       ".pytest_cache", "dist", "build", ".next", ".nuxt",
                       "target", "vendor", ".mypy_cache", ".ruff_cache"}
        for part in file.parts:
            # 虚拟环境目录（.venv, .venv.prod, venv, venv_prod 等）
            if part.startswith(".venv") or part == "venv":
                return True
            if part in skip_exact:
                return True
        return False
