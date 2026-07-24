#!/usr/bin/env python3
"""测试核心文件修改检测功能"""

import tempfile
import subprocess
from pathlib import Path
from moat.checks.core_file_modification import CoreFileModificationCheck

def test_direct_check():
    """直接测试 CoreFileModificationCheck"""
    print("=" * 60)
    print("测试 1: 直接测试 CoreFileModificationCheck")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # 初始化 git 仓库
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_path, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_path, check=True)

        # 创建初始文件
        (repo_path / "test.txt").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_path, check=True, capture_output=True)

        print(f"\n📁 测试仓库: {repo_path}")

        # 测试 1: 修改非核心文件
        print("\n1️⃣ 修改非核心文件 (utils.js)...")
        (repo_path / "utils.js").write_text("console.log('test')")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)

        check = CoreFileModificationCheck(repo_path)
        result_list = check.run()
        result = result_list[0] if result_list else None

        if result and result.type == "pass":
            print(f"   ✅ PASS: {result.message}")
        else:
            print(f"   ❌ FAIL: 应该通过，但得到: {result.message if result else 'no result'}")

        subprocess.run(["git", "commit", "-m", "update utils"], cwd=repo_path, check=True, capture_output=True)

        # 测试 2: 修改核心文件（App.tsx）
        print("\n2️⃣ 修改核心文件 (App.tsx)...")
        (repo_path / "App.tsx").write_text("export default function App() {}")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)

        check = CoreFileModificationCheck(repo_path)
        result_list = check.run()
        result = result_list[0] if result_list else None

        if result and result.type == "fail":
            print(f"   ✅ FAIL (预期): {result.message[:100]}...")
            if "App.tsx" in result.message:
                print(f"   ✅ 检测到 App.tsx")
            else:
                print(f"   ❌ 未检测到 App.tsx")
            if "需要用户明确批准" in result.message:
                print(f"   ✅ 包含批准提示")
            else:
                print(f"   ❌ 缺少批准提示")
        else:
            print(f"   ❌ 应该失败，但得到: {result.message if result else 'no result'}")

        print("\n" + "=" * 60)


def test_via_runner():
    """通过 runner.py 测试（模拟真实场景）"""
    print("\n" + "=" * 60)
    print("测试 2: 通过 runner.py 模拟真实场景")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # 初始化 git 仓库
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_path, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_path, check=True)

        # 创建初始文件
        (repo_path / "test.txt").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_path, check=True, capture_output=True)

        print(f"\n📁 测试仓库: {repo_path}")

        # 修改核心文件
        print("\n1️⃣ 修改核心文件 (App.tsx) 并通过 moat check 检查...")
        (repo_path / "App.tsx").write_text("export default function App() {}")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)

        # 调用 moat check
        import sys
        original_cwd = Path.cwd()
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from moat.runner import run_all_checks

            # 切换到测试仓库
            import os
            os.chdir(repo_path)

            print("\n▶️  运行 moat check...\n")
            result = run_all_checks(project_root=str(repo_path), mode="quick", enable_optimization=False)

            print("\n" + "-" * 60)
            print(f"结果: {result.summary()}")
            print("-" * 60)

            if result.failed > 0:
                print("✅ 检测到失败（核心文件修改被拦截）")
            else:
                print("❌ 未检测到失败（核心文件修改未被拦截）")

        except Exception as e:
            print(f"❌ 运行失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            os.chdir(original_cwd)

        print("\n" + "=" * 60)


if __name__ == "__main__":
    test_direct_check()
    test_via_runner()
    print("\n✅ 所有测试完成")
