"""测试核心文件修改检测规则"""

import tempfile
import subprocess
from pathlib import Path
from moat.checks.core_file_modification import CoreFileModificationCheck, CoreFileConfig


def test_core_file_detection():
    """测试核心文件检测"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # 初始化 git 仓库
        subprocess.run(["git", "init"], cwd=repo_path, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_path, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_path, check=True)

        # 创建初始文件
        (repo_path / "test.txt").write_text("hello")

        # 首次提交
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_path, check=True)

        # 测试 1: 修改非核心文件
        (repo_path / "utils.js").write_text("console.log('test')")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)

        check = CoreFileModificationCheck()
        result = check.run(repo_path)
        assert result.type == "pass", f"非核心文件不应触发违规: {result.message}"

        # 提交
        subprocess.run(["git", "commit", "-m", "update utils"], cwd=repo_path, check=True)

        # 测试 2: 修改核心文件（App.tsx）
        (repo_path / "App.tsx").write_text("export default function App() {}")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)

        check = CoreFileModificationCheck()
        result = check.run(repo_path)
        assert result.type == "fail", f"修改 App.tsx 应该触发违规: {result.message}"
        assert "App.tsx" in result.message
        assert "需要用户明确批准" in result.message

        print("✅ 核心文件修改检测测试通过")


def test_custom_config():
    """测试自定义配置"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # 初始化 git 仓库
        subprocess.run(["git", "init"], cwd=repo_path, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_path, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_path, check=True)

        (repo_path / "test.txt").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_path, check=True)

        # 自定义配置：只保护 SecretFile.tsx
        config = {
            "enabled": True,
            "severity": "critical",
            "core_files": [
                {
                    "name": "secret_file",
                    "patterns": ["SecretFile.tsx"],
                    "description": "我的机密文件",
                }
            ]
        }

        # 测试 1: 修改 App.tsx（不在自定义保护列表中）
        (repo_path / "App.tsx").write_text("export default function App() {}")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)

        check = CoreFileModificationCheck(config)
        result = check.run(repo_path)
        assert result.type == "pass", f"App.tsx 不在自定义保护列表中: {result.message}"

        subprocess.run(["git", "commit", "-m", "update App"], cwd=repo_path, check=True)

        # 测试 2: 修改 SecretFile.tsx（在自定义保护列表中）
        (repo_path / "SecretFile.tsx").write_text("export const secret = 'xyz'")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)

        check = CoreFileModificationCheck(config)
        result = check.run(repo_path)
        assert result.type == "fail", f"SecretFile.tsx 应该触发违规: {result.message}"
        assert "SecretFile.tsx" in result.message

        print("✅ 自定义配置测试通过")


def test_pattern_matching():
    """测试模式匹配"""
    check = CoreFileModificationCheck()

    # 精确匹配
    assert check._matches_pattern("App.tsx", "App.tsx") == True
    assert check._matches_pattern("app.tsx", "App.tsx") == True  # 不区分大小写
    assert check._matches_pattern("Main.tsx", "App.tsx") == False

    # 通配符
    assert check._matches_pattern("WebSocketHandler.ts", "*websocket*") == True
    assert check._matches_pattern("my_bridge.py", "*bridge*") == True
    assert check._matches_pattern("test.js", "*bridge*") == False

    # 正则表达式
    assert check._matches_pattern("test.py", "^test.*") == True
    assert check._matches_pattern("main.js", "^test.*") == False

    print("✅ 模式匹配测试通过")


if __name__ == "__main__":
    test_core_file_detection()
    test_custom_config()
    test_pattern_matching()
    print("\n✅ 所有测试通过")
