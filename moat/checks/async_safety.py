"""
异步安全检测 — 消防水带模式（Fire-and-Forget Anti-Pattern）

检测场景：
1. asyncio.create_task() 返回值被丢弃 → 功能完全失效
2. 同步函数中调用异步函数（await 在 sync 函数中）
3. 异步函数返回值被丢弃（调用方不 await 也不存储）

事故映射（2026-07-20 Bug #1）：
    # ❌ 返回值被丢弃，功能完全失效
    asyncio.create_task(self._async_inject_structure_feedback(...))
    # 只记录了日志，没有验证是否真的注入了
"""
import ast
import logging
from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult
from moat.checks.fail_open import fail_open

logger = logging.getLogger(__name__)


class AsyncSafetyCheck(Check):
    """异步安全检测器

    检查项：
    1. 消防水带模式：asyncio.create_task 返回值被丢弃
    2. 异步函数返回值被丢弃（调用方不 await）
    3. 同步函数内调用 async 函数（await 在 sync 中）

    设计原则：
    - 只检查修改的文件（快速模式）
    - 只报告高风险模式（避免噪音）
    - 每条结果附带修复建议
    """

    def __init__(self, project_root: Path, config: dict[str, Any] | None = None):
        super().__init__(project_root, config)
        self.name = "AsyncSafetyCheck"
        self.config = config or {}

    def run(self) -> list[CheckResult]:
        """运行异步安全检测"""
        results = []

        changed_files = self._get_changed_files()
        if not changed_files:
            return [self.pass_check("没有检测到修改的文件")]

        for file_path in changed_files:
            if file_path.suffix != ".py":
                continue
            file_results = self._check_file(file_path)
            results.extend(file_results)

        if not results:
            results.append(self.pass_check("异步安全检测通过"))

        return results

    def _get_changed_files(self) -> list[Path]:
        """获取修改的文件列表（git diff）"""
        import subprocess
        try:
            files = []
            # 已暂存 + 未暂存
            for ref in ["HEAD", "--cached"]:
                result = subprocess.run(
                    ["git", "diff", ref, "--name-only", "--diff-filter=ACMR"],
                    cwd=str(self.project.resolve()),
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().split("\n"):
                        if line:
                            fp = self.project / line
                            if fp.exists() and fp.suffix == ".py":
                                files.append(fp)
            return list(set(files))
        except Exception:
            return []

    @fail_open(default_return=[])
    def _check_file(self, file_path: Path) -> list[CheckResult]:
        """检查单个文件"""
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
        results = []
        rel_path = str(file_path.relative_to(self.project))

        # 1. 检查 fire-and-forget: asyncio.create_task 返回值被丢弃
        faf_results = self._check_fire_and_forget(tree, rel_path, content)
        results.extend(faf_results)

        # 2. 检查异步函数返回值被丢弃
        discarded_results = self._check_discarded_await(tree, rel_path, content)
        results.extend(discarded_results)

        # 3. 检查同步函数内调用 async 函数（不使用 await）
        sync_async_results = self._check_sync_calls_async(tree, rel_path)
        results.extend(sync_async_results)

        return results

    def _check_fire_and_forget(self, tree: ast.AST, rel_path: str, content: str) -> list[CheckResult]:
        """检测消防水带模式：asyncio.create_task 返回值被丢弃

        检测模式：
        - 表达式语句中调用 asyncio.create_task(xxx)
        - 即：create_task 的返回值没有被赋值或 await
        """
        results = []

        for node in ast.walk(tree):
            # 匹配：asyncio.create_task(xxx) 作为表达式语句
            if isinstance(node, ast.Expr):
                call = node.value
                if isinstance(call, ast.Call) and _is_create_task_call(call):
                    results.append(self.fail(
                        "消防水带模式：asyncio.create_task 返回值被丢弃，功能可能完全失效",
                        file=rel_path,
                        line=call.lineno,
                        suggestion=(
                            "将 create_task 的返回值赋值给变量，或使用 await：\n"
                            "    # ❌ 错误：返回值被丢弃\n"
                            "    asyncio.create_task(foo())\n"
                            "    # ✅ 正确：保留引用\n"
                            "    task = asyncio.create_task(foo())\n"
                            "    # ✅ 或在适当位置 await\n"
                            "    await task"
                        ),
                    ))

        return results

    def _check_discarded_await(self, tree: ast.AST, rel_path: str, content: str) -> list[CheckResult]:
        """检测异步函数返回值被丢弃

        检测模式：
        - await xxx() 作为表达式语句（不赋值）
        - 但函数名包含 get/fetch/load/find 等"获取"语义
        """
        results = []
        fetch_keywords = {"get", "fetch", "load", "find", "read", "query", "retrieve", "collect"}

        for node in ast.walk(tree):
            if isinstance(node, ast.Expr):
                expr = node.value
                # 匹配：await xxx() 作为表达式
                if isinstance(expr, ast.Await) and isinstance(expr.value, ast.Call):
                    func_name = _get_call_name(expr.value)
                    if func_name and any(k in func_name.lower() for k in fetch_keywords):
                        results.append(self.warn(
                            f"异步函数 {func_name} 的返回值被丢弃，确认是否需要保留结果",
                            file=rel_path,
                            line=expr.lineno,
                        ))

        return results

    def _check_sync_calls_async(self, tree: ast.AST, rel_path: str) -> list[CheckResult]:
        """检测同步函数中调用异步函数（不使用 await）

        检测模式：
        - 同步函数（非 async def）中调用 async 函数
        - 调用时不使用 await
        - 返回 coroutine 对象而不是执行结果
        """
        # 收集当前文件中的 async 函数名
        async_funcs = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                async_funcs.add(node.name)

        results = []

        for node in ast.walk(tree):
            # 只在同步函数中检查
            if isinstance(node, ast.FunctionDef) and not isinstance(node, ast.AsyncFunctionDef):
                sync_func_name = node.name
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        func_name = _get_call_name(child)
                        if func_name in async_funcs:
                            # 检查调用是否被 await
                            if not self._is_awaited(child, node):
                                results.append(self.fail(
                                    f"同步函数 {sync_func_name} 中调用异步函数 "
                                    f"{func_name} 但未使用 await，返回 coroutine 对象",
                                    file=rel_path,
                                    line=child.lineno,
                                    suggestion=(
                                        f"在 {func_name}() 前添加 await：\n"
                                        f"    # ✅ 正确\n"
                                        f"    result = await {func_name}()\n"
                                        f"    或：\n"
                                        f"    # 如果必须保持同步，使用：\n"
                                        f"    import asyncio\n"
                                        f"    result = asyncio.run({func_name}())"
                                    ),
                                ))

        return results

    def _is_awaited(self, call: ast.Call, parent_func: ast.FunctionDef) -> bool:
        """检查函数调用是否被 await（只检查 ast.Await，不检查赋值）"""
        for node in ast.walk(parent_func):
            if isinstance(node, ast.Await) and node.value is call:
                return True
        return False


# ── 辅助函数 ──


def _is_create_task_call(call: ast.Call) -> bool:
    """判断是否是 asyncio.create_task 调用"""
    func = call.func
    if isinstance(func, ast.Attribute):
        # asyncio.create_task(xxx)
        if func.attr == "create_task":
            return True
        # loop.create_task(xxx)
        if func.attr == "create_task":
            return True
    return False


def _get_call_name(call: ast.Call) -> str | None:
    """获取函数调用的名称"""
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        # self.foo() 或 module.foo()
        return func.attr
    return None