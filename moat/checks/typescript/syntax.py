"""TypeScript 语法检查（调用 tsc --noEmit）"""
import subprocess
import json
from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult


class TypeScriptSyntaxCheck(Check):
    """TypeScript 语法检查

    调用 tsc --noEmit 检查 TypeScript 语法错误。
    如果没有 TypeScript 文件或 tsc 不可用，自动跳过。
    """

    def __init__(self, project_root: Path, config: dict[str, Any] | None = None):
        super().__init__(project_root, config)
        self.tsc_path = self.config.get("tsc_path", "npx tsc")
        self.tsconfig = self.config.get("tsconfig", "tsconfig.json")

    def run(self) -> list[CheckResult]:
        results = []

        # 1. 检查是否有 TypeScript 文件
        ts_files = self._find_ts_files()
        if not ts_files:
            return [self.skip("项目中没有 TypeScript 文件")]

        # 2. 检查是否有 tsconfig.json
        tsconfig_path = self.project / self.tsconfig
        if not tsconfig_path.exists():
            return [self.warn(
                f"未找到 {self.tsconfig}，TypeScript 语法检查需要 tsconfig.json",
                file=self.tsconfig,
            )]

        # 3. 运行 tsc --noEmit
        try:
            result = subprocess.run(
                f"{self.tsc_path} --noEmit --pretty false",
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.project),
            )

            if result.returncode == 0:
                return [self.pass_check(f"TypeScript 语法检查通过（{len(ts_files)} 个文件）")]

            # 解析错误输出
            errors = self._parse_tsc_errors(result.stdout + result.stderr)
            if errors:
                for error in errors[:20]:  # 最多返回 20 个错误
                    results.append(self.fail(
                        error["message"],
                        file=error.get("file"),
                        line=error.get("line"),
                    ))
            else:
                results.append(self.fail(
                    f"TypeScript 语法检查失败（{result.returncode} 个错误）\n"
                    f"输出: {result.stdout[:500]}",
                ))

        except subprocess.TimeoutExpired:
            results.append(self.fail("TypeScript 语法检查超时（>60s）"))
        except FileNotFoundError:
            results.append(self.skip("未找到 tsc，请安装 Node.js 和 TypeScript"))
        except Exception as e:
            results.append(self.fail(f"TypeScript 语法检查异常: {e}"))

        return results if results else [self.pass_check("TypeScript 语法检查通过")]

    def _find_ts_files(self) -> list[Path]:
        """查找所有 TypeScript 文件"""
        files = []
        for ext in ["*.ts", "*.tsx", "*.mts", "*.cts"]:
            files.extend(self._find_files(ext))
        return [f for f in files if not self._should_skip(f)]

    def _parse_tsc_errors(self, output: str) -> list[dict[str, Any]]:
        """解析 tsc 错误输出"""
        errors = []
        for line in output.split("\n"):
            # 格式: file(line,column): error TS####: message
            if "error" in line and ":" in line:
                parts = line.split(":")
                if len(parts) >= 3:
                    file_path = parts[0].strip()
                    line_col = parts[1].strip()
                    message = ":".join(parts[2:]).strip()

                    # 提取行号
                    line_num = None
                    if "(" in line_col and ")" in line_col:
                        try:
                            line_num = int(line_col.split("(")[1].split(",")[0])
                        except (IndexError, ValueError):
                            pass

                    errors.append({
                        "file": file_path,
                        "line": line_num,
                        "message": message,
                    })
        return errors
