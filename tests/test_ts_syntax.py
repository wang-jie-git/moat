"""TypeScript 语法检查测试

TypeScriptSyntaxCheck 调用 `npx tsc --noEmit` 检查语法。

关键发现：
  - 无 TS 文件 → 返回 [skip]
  - 无 tsconfig.json → 返回 [warn]
  - tsc 不可用 → 返回 [skip]
  - 语法错误 → 返回 [fail] (最多 20 个)
  - 通过 → 返回 [pass]

测试策略：模拟 TS 项目，mock subprocess.run 避免依赖真实 tsc。
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from moat.checks.typescript import TypeScriptSyntaxCheck


class TestTypeScriptSyntaxCheck:
    """测试 TypeScriptSyntaxCheck。"""

    def test_no_ts_files_skips(self, tmp_path: Path) -> None:
        """无 TypeScript 文件应跳过。"""
        check = TypeScriptSyntaxCheck(tmp_path, {})
        results = check.run()
        assert len(results) == 1
        assert results[0].type == "skip"

    def test_no_tsconfig_warns(self, tmp_path: Path) -> None:
        """无 tsconfig.json 应警告。"""
        (tmp_path / "test.ts").write_text("const x = 1;\n")
        check = TypeScriptSyntaxCheck(tmp_path, {})
        results = check.run()
        assert any(r.type == "warn" for r in results)

    def test_tsc_not_found_skips(self, tmp_path: Path) -> None:
        """tsc 不可用应跳过。"""
        (tmp_path / "tsconfig.json").write_text('{"compilerOptions": {}}')
        (tmp_path / "test.ts").write_text("const x = 1;\n")
        check = TypeScriptSyntaxCheck(tmp_path, {})
        with patch("subprocess.run", side_effect=FileNotFoundError):
            results = check.run()
        assert any(r.type == "skip" for r in results)

    def test_syntax_errors_detected(self, tmp_path: Path) -> None:
        """语法错误应被检测为 fail。"""
        (tmp_path / "tsconfig.json").write_text('{"compilerOptions": {}}')
        (tmp_path / "test.ts").write_text("const x = ;\n")

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = "test.ts:1:13 - error TS1005: ';' expected.\n"
        mock_result.stderr = ""

        check = TypeScriptSyntaxCheck(tmp_path, {})
        with patch("subprocess.run", return_value=mock_result):
            results = check.run()
        assert any(r.type == "fail" for r in results)

    def test_valid_ts_passes(self, tmp_path: Path) -> None:
        """有效 TypeScript 应通过。"""
        (tmp_path / "tsconfig.json").write_text('{"compilerOptions": {}}')
        (tmp_path / "test.ts").write_text("const x: number = 1;\n")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        check = TypeScriptSyntaxCheck(tmp_path, {})
        with patch("subprocess.run", return_value=mock_result):
            results = check.run()
        assert any(r.type == "pass" for r in results)

    def test_timeout_handled(self, tmp_path: Path) -> None:
        """超时应被处理。"""
        (tmp_path / "tsconfig.json").write_text('{"compilerOptions": {}}')
        (tmp_path / "test.ts").write_text("const x = 1;\n")

        check = TypeScriptSyntaxCheck(tmp_path, {})
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("tsc", 60)):
            results = check.run()
        assert any(r.type == "fail" and "超时" in r.message for r in results)

    def test_custom_tsconfig(self, tmp_path: Path) -> None:
        """应支持自定义 tsconfig 文件名。"""
        (tmp_path / "custom.json").write_text('{"compilerOptions": {}}')
        (tmp_path / "test.ts").write_text("const x = 1;\n")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        check = TypeScriptSyntaxCheck(tmp_path, {"tsconfig": "custom.json"})
        with patch("subprocess.run", return_value=mock_result):
            results = check.run()
        assert any(r.type == "pass" for r in results)

    def test_error_has_file_and_line(self, tmp_path: Path) -> None:
        """错误应包含文件路径和行号。"""
        (tmp_path / "tsconfig.json").write_text('{"compilerOptions": {}}')
        (tmp_path / "broken.ts").write_text("const x = ;\n")

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = 'broken.ts:1:8 - error TS1005\n'
        mock_result.stderr = ""

        check = TypeScriptSyntaxCheck(tmp_path, {})
        with patch("subprocess.run", return_value=mock_result):
            results = check.run()
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) >= 1
        assert "broken.ts" in fails[0].file or fails[0].file == "broken.ts"

    def test_max_20_errors(self, tmp_path: Path) -> None:
        """最多返回 20 个错误。"""
        (tmp_path / "tsconfig.json").write_text('{"compilerOptions": {}}')
        (tmp_path / "test.ts").write_text("const x = ;\n" * 100)

        error_lines = "\n".join(f"test.ts:{i}:8 - error TS1005" for i in range(1, 101))
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = error_lines
        mock_result.stderr = ""

        check = TypeScriptSyntaxCheck(tmp_path, {})
        with patch("subprocess.run", return_value=mock_result):
            results = check.run()
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) <= 20

    def test_finds_tsx_files(self, tmp_path: Path) -> None:
        """应查找 .tsx 文件。"""
        (tmp_path / "tsconfig.json").write_text('{"compilerOptions": {}}')
        (tmp_path / "Component.tsx").write_text("export const C = () => <div />;\n")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        check = TypeScriptSyntaxCheck(tmp_path, {})
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            check.run()
            call_cwd = mock_run.call_args[1]["cwd"]
            assert (Path(call_cwd) / "Component.tsx").exists()

    def test_unexpected_exception_handled(self, tmp_path: Path) -> None:
        """未预期的异常应被捕获为 fail。"""
        (tmp_path / "tsconfig.json").write_text('{"compilerOptions": {}}')
        (tmp_path / "test.ts").write_text("const x = 1;\n")

        check = TypeScriptSyntaxCheck(tmp_path, {})
        with patch("subprocess.run", side_effect=RuntimeError("unexpected")):
            results = check.run()
        assert any(r.type == "fail" for r in results)
