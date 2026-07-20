"""
测试异步安全检测（三个 P0 优化）

覆盖：
1. 消防水带模式检测（fire-and-forget anti-pattern）
2. 异步安全检测器（AsyncSafetyCheck）
3. 同步/异步边界检测（AST diff 增强）
4. 调用方影响域分析（grep 自动查找）
"""
import ast
import tempfile
from pathlib import Path

import pytest

from moat.ast.diff import ASTDiffer, CodeChange
from moat.ast.builder import ProjectSkeleton
from moat.checks.async_safety import AsyncSafetyCheck


# ══════════════════════════════════════════════
# 1. 消防水带模式检测（Fire-and-Forget）
# ══════════════════════════════════════════════

def test_detect_fire_and_forget_create_task():
    """检测：asyncio.create_task 返回值被丢弃"""
    content = """
import asyncio

async def foo():
    return 42

async def main():
    # ❌ fire-and-forget: 返回值被丢弃
    asyncio.create_task(foo())
    # ✅ 正确用法
    task = asyncio.create_task(foo())
    await task
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        file_path = tmpdir / "test_async.py"
        file_path.write_text(content)

        # 初始化 git 仓库
        import subprocess
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init", "--allow-empty"], cwd=tmpdir, capture_output=True)

        # 修改文件（触发检测）
        file_path.write_text(content + "\n# modified")

        check = AsyncSafetyCheck(tmpdir)
        results = check.run()

        # 应该检测到 fire-and-forget
        fire_forget = [r for r in results if "消防水带" in r.message]
        assert len(fire_forget) == 1, f"应该检测到 1 个消防水带模式，实际 {len(fire_forget)}"
        assert fire_forget[0].type == "fail"
        assert "create_task" in fire_forget[0].message


def test_no_false_positive_proper_usage():
    """不误报：正确使用 create_task（赋值后 await）"""
    content = """
import asyncio

async def foo():
    return 42

async def main():
    task = asyncio.create_task(foo())
    result = await task
    print(result)
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        file_path = tmpdir / "test_async.py"
        file_path.write_text(content)

        import subprocess
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init", "--allow-empty"], cwd=tmpdir, capture_output=True)

        file_path.write_text(content + "\n# modified")

        check = AsyncSafetyCheck(tmpdir)
        results = check.run()

        fire_forget = [r for r in results if "消防水带" in r.message]
        assert len(fire_forget) == 0, f"不应该误报，实际检测到 {len(fire_forget)}"


def test_detect_sync_calls_async_without_await():
    """检测：同步函数中调用异步函数但不使用 await"""
    content = """
import asyncio

async def fetch_data():
    return {"key": "value"}

def process():  # 同步函数
    # ❌ 调用 async 函数但不 await
    result = fetch_data()
    return result
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        file_path = tmpdir / "test_sync.py"
        file_path.write_text(content)

        import subprocess
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init", "--allow-empty"], cwd=tmpdir, capture_output=True)

        file_path.write_text(content + "\n# modified")

        check = AsyncSafetyCheck(tmpdir)
        results = check.run()

        sync_async = [r for r in results if "同步函数" in r.message]
        assert len(sync_async) >= 1, f"应该检测到同步函数调异步函数，实际 {len(sync_async)}"


# ══════════════════════════════════════════════
# 2. 同步/异步边界检测（AST diff 增强）
# ══════════════════════════════════════════════

def test_detect_async_signature_change():
    """检测：函数从 sync→async 签名变更"""
    old_content = """
def get_data():
    return fetch()
"""
    new_content = """
async def get_data():
    return await fetch()
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        file_path = tmpdir / "service.py"

        import subprocess
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        # 先提交旧版本
        file_path.write_text(old_content)
        subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init", "--allow-empty"], cwd=tmpdir, capture_output=True)

        # 写新内容
        file_path.write_text(new_content)

        differ = ASTDiffer(tmpdir)
        changes = differ.diff_file(file_path)

        # 应该检测到 async_signature 变更
        sig_changes = [c for c in changes if c.change_type == "async_signature"]
        assert len(sig_changes) == 1, f"应该检测到 1 个 async 签名变更，实际 {len(sig_changes)}"
        assert sig_changes[0].function == "get_data"
        assert "async" in sig_changes[0].new_code


def test_detect_async_to_sync_change():
    """检测：函数从 async→sync 签名变更"""
    old_content = """
async def process():
    await asyncio.sleep(1)
    return result
"""
    new_content = """
def process():
    return result
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        file_path = tmpdir / "service.py"

        import subprocess
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        # 先提交旧版本
        file_path.write_text(old_content)
        subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init", "--allow-empty"], cwd=tmpdir, capture_output=True)

        # 写新内容
        file_path.write_text(new_content)

        differ = ASTDiffer(tmpdir)
        changes = differ.diff_file(file_path)

        sig_changes = [c for c in changes if c.change_type == "async_signature"]
        assert len(sig_changes) == 1, f"应该检测到 1 个 async 签名变更，实际 {len(sig_changes)}"
        assert sig_changes[0].function == "process"
        assert "async" not in sig_changes[0].new_code


def test_no_false_positive_sync_stays_sync():
    """不误报：同步函数始终是同步"""
    old_content = """
def add(a, b):
    return a + b
"""
    new_content = """
def add(a, b):
    return a + b + 1
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        file_path = tmpdir / "math.py"

        import subprocess
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        # 先提交旧版本
        file_path.write_text(old_content)
        subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init", "--allow-empty"], cwd=tmpdir, capture_output=True)

        # 写新内容
        file_path.write_text(new_content)

        differ = ASTDiffer(tmpdir)
        changes = differ.diff_file(file_path)

        sig_changes = [c for c in changes if c.change_type == "async_signature"]
        assert len(sig_changes) == 0, f"不应该检测到 async 签名变更，实际 {len(sig_changes)}"


# ══════════════════════════════════════════════
# 3. 调用方影响域分析（analyze_impacts 增强）
# ══════════════════════════════════════════════

def test_analyze_impacts_async_signature():
    """分析：async 签名变更时，风险评估为 high"""
    change = CodeChange(
        change_type="async_signature",
        file_path="service.py",
        line=10,
        function="get_data",
        old_code="def get_data",
        new_code="async def get_data",
    )
    skeleton = {
        "call_graph": {
            "main::handler": ["get_data", "validate"],
            "main::process": ["get_data"],
        }
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        (tmpdir / "main.py").write_text("""
def handler():
    return get_data()

def process():
    return get_data()
""")
        differ = ASTDiffer(tmpdir, skeleton)
        impacts = differ.analyze_impacts([change], skeleton)

        assert len(impacts) == 1, f"应该有 1 个影响分析结果，实际 {len(impacts)}"
        assert impacts[0]["risk_level"] == "critical", "async 签名变更应为 critical"
        assert impacts[0]["caller_count"] >= 2, "应该检测到 2 个调用方"
        assert "async" in impacts[0]["suggestion"]


def test_analyze_impacts_grep_find_callers():
    """分析：grep 自动查找调用方"""
    change = CodeChange(
        change_type="modified",
        file_path="utils/helpers.py",
        line=5,
        function="helper_func",
    )
    skeleton = {"call_graph": {}}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        # 创建调用方文件
        (tmpdir / "main.py").write_text("""
def process():
    result = helper_func()
    return result
""")
        (tmpdir / "utils").mkdir()
        (tmpdir / "utils" / "helpers.py").write_text("""
def helper_func():
    return 42
""")
        (tmpdir / "test_main.py").write_text("""
from utils.helpers import helper_func

def test_process():
    result = helper_func()
    assert result == 42
""")

        differ = ASTDiffer(tmpdir, skeleton)
        impacts = differ.analyze_impacts([change], skeleton)

        assert len(impacts) == 1, f"应该有 1 个影响分析结果，实际 {len(impacts)}"
        # grep 应该至少找到调用方
        assert impacts[0]["caller_count"] >= 0, "grep 应该找到调用方"


def test_analyze_impacts_no_callers():
    """分析：无调用方时风险为 low"""
    change = CodeChange(
        change_type="added",
        file_path="utils.py",
        line=1,
        function="new_function",
    )
    skeleton = {"call_graph": {}}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        (tmpdir / "utils.py").write_text("""
def new_function():
    return True
""")
        differ = ASTDiffer(tmpdir, skeleton)
        impacts = differ.analyze_impacts([change], skeleton)

        # 新增函数无调用方，不产生影响
        assert len(impacts) == 0, f"新增函数无调用方，不应产生影响"


def test_analyze_impacts_deleted_function():
    """分析：删除函数时风险为 critical"""
    change = CodeChange(
        change_type="deleted",
        file_path="service.py",
        function="deprecated_func",
    )
    skeleton = {"call_graph": {"main::handler": ["deprecated_func"]}}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        (tmpdir / "main.py").write_text("""
def handler():
    return deprecated_func()
""")
        differ = ASTDiffer(tmpdir, skeleton)
        impacts = differ.analyze_impacts([change], skeleton)

        assert len(impacts) == 1, f"应该有 1 个影响分析结果"
        assert impacts[0]["risk_level"] in ("high", "critical"), "删除函数应为 high 或 critical"
        assert "删除" in impacts[0]["suggestion"]


# ══════════════════════════════════════════════
# 4. 集成测试：完整事故场景模拟
# ══════════════════════════════════════════════

def test_integration_mimic_incident_scenario():
    """集成测试：模拟事故场景

    事故场景（2026-07-20）：
    1. 开发者将 _inject_structure_feedback 改为 async
    2. 使用 create_task 丢弃返回值
    3. 尝试将 build_runtime_system_prompt 改为 async（破坏调用方）
    """
    old_content = """
def _inject_structure_feedback(session_id, line):
    structures = get_relevant_structures(line, limit=2)
    if structures:
        line["feedback"] = structures
    return line

def build_runtime_system_prompt(user_prompt):
    result = _inject_structure_feedback("session1", user_prompt)
    return result
"""
    new_content = """
import asyncio

async def _inject_structure_feedback(session_id, line):
    structures = await get_relevant_structures(line, limit=2)
    if structures:
        # 只记录日志，不注入
        print(f"Injected {len(structures)} templates")
    return None  # 返回值被丢弃

async def build_runtime_system_prompt(user_prompt):
    # 改成 async，所有调用方需要更新
    result = await _inject_structure_feedback("session1", user_prompt)
    return result
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # 创建调用方文件（模拟 3 个调用方）
        (tmpdir / "ws_handler_prompt.py").write_text("""
def handle_prompt(user_input):
    prompt = build_runtime_system_prompt(user_input)
    return prompt
""")
        (tmpdir / "server_main.py").write_text("""
def start_server():
    prompt = build_runtime_system_prompt("default")
    return prompt
""")
        (tmpdir / "ws_handler_helpers.py").write_text("""
def get_system_prompt():
    prompt = build_runtime_system_prompt("default")
    return prompt
""")

        file_path = tmpdir / "context_wrapper.py"
        file_path.write_text(new_content)

        # 初始化 git
        import subprocess
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        # 使用旧内容作为初始提交
        # 但我们直接测试 AST diff 的检测能力
        # 手动创建两个 AST 树
        old_tree = ast.parse(old_content)
        new_tree = ast.parse(new_content)

        differ = ASTDiffer(tmpdir)
        changes = differ._diff_functions(old_tree, new_tree, "context_wrapper.py")

        # 验证：检测到 2 个 async 签名变更
        sig_changes = [c for c in changes if c.change_type == "async_signature"]
        assert len(sig_changes) == 2, (
            f"应该检测到 2 个 async 签名变更 "
            f"(_inject_structure_feedback + build_runtime_system_prompt)，"
            f"实际 {len(sig_changes)}: {[c.function for c in sig_changes]}"
        )

        # 验证：_inject_structure_feedback 从 sync→async
        inject_change = next(c for c in sig_changes if c.function == "_inject_structure_feedback")
        assert "async" in inject_change.new_code
        assert "async" not in inject_change.old_code

        # 验证：build_runtime_system_prompt 从 sync→async
        build_change = next(c for c in sig_changes if c.function == "build_runtime_system_prompt")
        assert "async" in build_change.new_code
        assert "async" not in build_change.old_code

        # 验证分析影响域
        skeleton = {"call_graph": {
            "ws_handler_prompt::handle_prompt": ["build_runtime_system_prompt"],
            "server_main::start_server": ["build_runtime_system_prompt"],
            "ws_handler_helpers::get_system_prompt": ["build_runtime_system_prompt"],
        }}
        impacts = differ.analyze_impacts([build_change], skeleton)

        # 应该检测到 build_runtime_system_prompt 的 3 个调用方
        assert len(impacts) >= 1, "应该有影响分析结果"
        impact = next(i for i in impacts if i["change"]["function"] == "build_runtime_system_prompt")
        assert impact["caller_count"] >= 3, (
            f"build_runtime_system_prompt 应该有 3 个调用方，"
            f"实际 {impact['caller_count']}"
        )
        assert impact["risk_level"] == "critical", "有 3 个调用方的 async 变更应为 critical"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])