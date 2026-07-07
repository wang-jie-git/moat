"""TypeScript 专项检查 — any 类型滥用检测"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult


class TypeScriptAnyTypeCheck(Check):
    """TypeScript any 类型滥用检查

    检测并警告 any 类型的滥用：
    - 变量声明使用 any
    - 函数参数/返回值使用 any
    - 类型断言使用 any
    """

    name = "typescript_any_type"
    description = "TypeScript any 类型滥用检查"

    def __init__(self, project_root: Path, config: dict[str, Any] | None = None):
        super().__init__(project_root, config)
        self.allowed_patterns = self.config.get(
            "allowed_any_patterns",
            [
                r"// @ts-ignore",  # ts-ignore 注释
                r"// @ts-expect-error",  # ts-expect-error 注释
            ],
        )

    def run(self) -> list[CheckResult]:
        results = []

        # 1. 检查是否有 TypeScript 文件
        ts_files = self._find_ts_files()
        if not ts_files:
            return [self.skip("项目中没有 TypeScript 文件")]

        # 2. 扫描所有 TypeScript 文件
        any_uses = []
        for file_path in ts_files:
            if self._should_skip(file_path):
                continue

            try:
                source = file_path.read_text(encoding="utf-8")
                file_any_uses = self._find_any_uses(source, file_path)
                any_uses.extend(file_any_uses)
            except Exception:
                continue

        # 3. 评估结果
        if not any_uses:
            return [self.pass_check("未发现 any 类型滥用")]

        # 按文件分组
        by_file: dict[str, list[dict[str, Any]]] = {}
        for use in any_uses:
            file_str = str(use["file"].relative_to(self.project))
            if file_str not in by_file:
                by_file[file_str] = []
            by_file[file_str].append(use)

        # 生成报告
        total_any = len(any_uses)
        affected_files = len(by_file)

        if total > 20:
            results.append(self.fail(
                f"发现 {total} 处 any 类型滥用（{affected_files} 个文件）\n"
                f"建议：尽可能使用 unknown 或具体类型替代 any",
                file=list(by_file.keys())[0],
            ))
        elif total > 5:
            results.append(self.warn(
                f"发现 {total} 处 any 类型滥用（{affected_files} 个文件）\n"
                f"建议：重构为 unknown 或具体类型",
                file=list(by_file.keys())[0],
            ))
        else:
            results.append(self.warn(
                f"发现 {total} 处 any 类型滥用（{affected_files} 个文件）",
            ))

        # 详细报告
        if total_any <= 10:
            for file_str, uses in by_file.items():
                for use in uses[:3]:  # 每文件最多 3 条
                    results.append(self.warn(
                        f"any 类型: {use.get('context', 'unknown')}",
                        file=use["file"],
                        line=use.get("line"),
                    ))

        return results

    def _find_any_uses(self, source: str, file_path: Path) -> list[dict[str, Any]]:
        """查找 any 类型使用

        Args:
            source: 源代码
            file_path: 文件路径

        Returns:
            any 使用列表
        """
        import re

        uses = []

        # 排除注释和字符串
        lines = source.split("\n")
        for line_num, line in enumerate(lines, 1):
            # 跳过注释行
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("* "):
                continue

            # 跳过 @ts-ignore/@ts-expect-error 注释
            if "@ts-" in line:
                continue

            # 查找 any 类型
            # 匹配模式：
            # 1. : any
            # 2. : any[]
            # 3. : any<...> (极少见，但可能)
            patterns = [
                r":\s*any\b",  # : any
                r":\s*any\s*[\[\<]",  # : any[] 或 : any<
            ]

            for pattern in patterns:
                for match in re.finditer(pattern, line):
                    # 检查是否在字符串中
                    if self._in_string(line, match.start()):
                        continue

                    uses.append({
                        "file": file_path,
                        "line": line_num,
                        "context": line.strip()[:80],
                    })
                    break  # 每行只报告一次

        return uses

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
