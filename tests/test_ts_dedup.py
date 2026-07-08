"""TypeScript 去重逻辑检查测试

TypeScriptDedupCheck 检测去重/防抖代码是否缺少"为什么"注释。

关键发现：
  - 匹配模式：isDuplicate=, dedupWindow=, debounce(), throttle()
  - 检查前 10 行是否有"为什么"注释
  - WHY_KEYWORDS: 为什么/why/防止/prevent/避免/avoid/时序/timing/场景/trigger/race/deadlock/目的/purpose/说明/note/原因/reason/reconnect/重连/动态/dynamic/dedupWindow

测试策略：创建含去重代码的 TS 文件，验证注释检查。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from moat.checks.typescript import TypeScriptDedupCheck


class TestTypeScriptDedupCheck:
    """测试 TypeScriptDedupCheck。"""

    def test_no_ts_files_skips(self, tmp_path: Path) -> None:
        """无 TypeScript 文件应跳过。"""
        check = TypeScriptDedupCheck(tmp_path, {})
        results = check.run()
        assert len(results) == 1
        assert results[0].type == "skip"

    def test_dedup_without_why_comment_fails(self, tmp_path: Path) -> None:
        """去重代码缺少"为什么"注释应失败。"""
        (tmp_path / "dedup.ts").write_text(
            "const isDuplicate = (a: any, b: any) => a.id === b.id;\n"
        )
        check = TypeScriptDedupCheck(tmp_path, {})
        results = check.run()
        assert any(r.type == "fail" for r in results)

    def test_dedup_with_why_comment_passes(self, tmp_path: Path) -> None:
        """去重代码有"为什么"注释应通过。"""
        code = """// 为什么：防止重放攻击（replay attack）
const isDuplicate = (a: any, b: any) => a.id === b.id;
"""
        (tmp_path / "dedup.ts").write_text(code)
        check = TypeScriptDedupCheck(tmp_path, {})
        results = check.run()
        # 有 why 注释不应报 fail
        assert not any(r.type == "fail" for r in results)

    def test_debounce_without_comment_fails(self, tmp_path: Path) -> None:
        """防抖函数缺少注释应失败。"""
        (tmp_path / "util.ts").write_text(
            "function debounce(fn: Function, delay: number) { /* ... */ }\n"
        )
        check = TypeScriptDedupCheck(tmp_path, {})
        results = check.run()
        assert any(r.type == "fail" for r in results)

    def test_debounce_with_why_comment_passes(self, tmp_path: Path) -> None:
        """防抖函数有"为什么"注释应通过。"""
        code = """// 为什么：避免频繁触发 API 请求
function debounce(fn: Function, delay: number) { /* ... */ }
"""
        (tmp_path / "util.ts").write_text(code)
        check = TypeScriptDedupCheck(tmp_path, {})
        results = check.run()
        assert not any(r.type == "fail" for r in results)

    def test_throttle_without_comment_fails(self, tmp_path: Path) -> None:
        """节流函数缺少注释应失败。"""
        (tmp_path / "util.ts").write_text(
            "function throttle(fn: Function, limit: number) { /* ... */ }\n"
        )
        check = TypeScriptDedupCheck(tmp_path, {})
        results = check.run()
        assert any(r.type == "fail" for r in results)

    def test_throttle_with_purpose_comment_passes(self, tmp_path: Path) -> None:
        """节流函数有"目的"注释应通过。"""
        code = """// 目的：限制滚动事件触发频率
function throttle(fn: Function, limit: number) { /* ... */ }
"""
        (tmp_path / "util.ts").write_text(code)
        check = TypeScriptDedupCheck(tmp_path, {})
        results = check.run()
        assert not any(r.type == "fail" for r in results)

    def test_dedupWindow_without_comment_fails(self, tmp_path: Path) -> None:
        """dedupWindow 缺少注释应失败。"""
        (tmp_path / "ws.ts").write_text(
            "const dedupWindow = 5000;\n"
        )
        check = TypeScriptDedupCheck(tmp_path, {})
        results = check.run()
        assert any(r.type == "fail" for r in results)

    def test_dedupWindow_with_timing_comment_passes(self, tmp_path: Path) -> None:
        """dedupWindow 有时序注释应通过。"""
        code = """// 时序：5 秒窗口防止消息重复发送
const dedupWindow = 5000;
"""
        (tmp_path / "ws.ts").write_text(code)
        check = TypeScriptDedupCheck(tmp_path, {})
        results = check.run()
        assert not any(r.type == "fail" for r in results)

    def test_multiple_violations_all_detected(self, tmp_path: Path) -> None:
        """多个违规应全部被检测。"""
        code = """
const isDuplicate = (a: any, b: any) => a.id === b.id;
function debounce(fn: Function, delay: number) {}
const dedupWindow = 5000;
"""
        (tmp_path / "multi.ts").write_text(code)
        check = TypeScriptDedupCheck(tmp_path, {})
        results = check.run()
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) >= 3  # 3 个违规

    def test_english_why_comment_works(self, tmp_path: Path) -> None:
        """英文 why 注释也应被识别。"""
        code = """// Why: prevent duplicate message delivery
const isDuplicate = (a: any, b: any) => a.id === b.id;
"""
        (tmp_path / "dedup.ts").write_text(code)
        check = TypeScriptDedupCheck(tmp_path, {})
        results = check.run()
        assert not any(r.type == "fail" for r in results)

    def test_reconnect_keyword_works(self, tmp_path: Path) -> None:
        """reconnect 关键词注释也应通过。"""
        code = """// reconnect: 重连时防止重复订阅
const dedupWindow = 5000;
"""
        (tmp_path / "ws.ts").write_text(code)
        check = TypeScriptDedupCheck(tmp_path, {})
        results = check.run()
        assert not any(r.type == "fail" for r in results)

    def test_result_has_file_and_line(self, tmp_path: Path) -> None:
        """失败结果应包含文件路径和行号。"""
        (tmp_path / "dedup.ts").write_text(
            "const isDuplicate = (a: any, b: any) => a.id === b.id;\n"
        )
        check = TypeScriptDedupCheck(tmp_path, {})
        results = check.run()
        fails = [r for r in results if r.type == "fail"]
        assert len(fails) >= 1
        assert fails[0].file
        assert fails[0].line >= 1
