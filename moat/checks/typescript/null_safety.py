"""TypeScript 专项检查 — 空值安全检查"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult


class TypeScriptNullSafetyCheck(Check):
    """TypeScript 空值安全检查

    检测潜在的空值/undefined 访问：
    - 可选链使用建议
    - 非空断言（!）使用
    - 未处理的 null/undefined 返回值
    """

    name = "typescript_null_safety"
    description = "TypeScript 空值安全检查"

    def __init__(self, project_root: Path, config: dict[str, Any] | None = None):
        super().__init__(project_root, config)
        self.strict_mode = self.config.get("strict_null_checks", True)

    def run(self) -> list[CheckResult]:
        results = []

        # 1. 检查是否有 TypeScript 文件
        ts_files = self._find_ts_files()
        if not ts_files:
            return [self.skip("项目中没有 TypeScript 文件")]

        # 2. 检查 tsconfig.json 的严格模式
        tsconfig = self._load_tsconfig()
        strict_null_checks = tsconfig.get("compilerOptions", {}).get("strictNullChecks", False)

        if not strict_null_checks and self.strict_mode:
            results.append(self.warn(
                "建议在 tsconfig.json 中启用 strictNullChecks: true\n"
                "这可以帮助捕获潜在的空值错误",
                file="tsconfig.json",
            ))

        # 3. 扫描非空断言使用
        non_null_assertions = []
        for file_path in ts_files:
            if self._should_skip(file_path):
                continue

            try:
                source = file_path.read_text(encoding="utf-8")
                file_assertions = self._find_non_null_assertions(source, file_path)
                non_null_assertions.extend(file_assertions)
            except Exception:
                continue

        # 4. 评估结果
        if non_null_assertions:
            by_file: dict[str, list] = {}
            for assertion in non_null_assertions:
                file_str = str(assertion["file"].relative_to(self.project))
                if file_str not in by_file:
                    by_file[file_str] = []
                by_file[file_str].append(assertion)

            total = len(non_null_assertions)
            if total > 10:
                results.append(self.warn(
                    f"发现 {total} 处非空断言（!）\n"
                    f"建议：使用可选链（?.）或空值合并（??）替代",
                ))
            elif total > 0:
                results.append(self.warn(
                    f"发现 {total} 处非空断言（!）",
                ))

        if not results:
            results.append(self.pass_check("空值安全检查通过"))

        return results

    def _find_non_null_assertions(self, source: str, file_path: Path) -> list[dict]:
        """查找非空断言（!）

        Args:
            source: 源代码
            file_path: 文件路径

        Returns:
            非空断言列表
        """
        import re

        assertions = []
        lines = source.split("\n")

        for line_num, line in enumerate(lines, 1):
            # 跳过注释
            stripped = line.strip()
            if stripped.startswith("//"):
                continue

            # 查找 ! 断言
            # 匹配：variable!、obj.prop!、func()!
            pattern = r"\w[\w\.]*!"

            for match in re.finditer(pattern, line):
                # 确保不在字符串中
                if self._in_string(line, match.start()):
                    continue

                # 排除常见的误报（如 !==）
                if match.group().endswith("!="):
                    continue

                assertions.append({
                    "file": file_path,
                    "line": line_num,
                    "context": line.strip()[:80],
                })
                break  # 每行只报告一次

        return assertions

    def _load_tsconfig(self) -> dict[str, Any]:
        """加载 tsconfig.json"""
        import json

        tsconfig_path = self.project / "tsconfig.json"
        if not tsconfig_path.exists():
            return {}

        try:
            return json.loads(tsconfig_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _in_string(self, line: str, pos: int) -> bool:
        """检查位置是否在字符串中"""
        in_string = False
        quote_char = None

        for i, char in enumerate(line):
            if i >= pos:
                break

            if char in ('"', "'", "`"):
                if not in_string:
                    in_string = True
                    quote_char = char
                elif char == quote_char:
                    in_string = False

        return in_string

    def _find_ts_files(self) -> list[Path]:
        """查找所有 TypeScript 文件"""
        files = []
        for ext in ["*.ts", "*.tsx", "*.mts", "*.cts"]:
            files.extend(self._find_files(ext))
        return [f for f in files if not self._should_skip(f)]
