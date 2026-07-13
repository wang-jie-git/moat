#!/usr/bin/env python3
"""
验证 moat --diff 修复
"""

import subprocess
import sys

def test_diff_bug_fix():
    """测试 --diff 模式是否还会出现 KeyError"""
    print("🧪 测试 moat check --diff 修复")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    result = subprocess.run(
        ["moat", "check", "--diff", "--project", "."],
        cwd="/Users/mac/Desktop/moat",
        capture_output=True,
        text=True,
        timeout=60
    )

    print("STDOUT:")
    print(result.stdout)

    if result.returncode == 0:
        print("✅ --diff 模式正常运行（无错误）")
        return True
    else:
        print("❌ --diff 模式失败")
        print("STDERR:")
        print(result.stderr)
        return False

if __name__ == "__main__":
    success = test_diff_bug_fix()
    sys.exit(0 if success else 1)
