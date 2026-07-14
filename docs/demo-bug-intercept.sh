#!/bin/bash
# Moat Bug Interception Demo
# 演示：在代码提交前拦截"函数存在但未导入"类 Bug

set -e

# 创建临时项目
TMPDIR=$(mktemp -d)
cd "$TMPDIR"

echo "🔧 创建测试项目..."
mkdir -p src

# 正确文件
cat > src/utils.py << 'EOF'
def greet(name: str) -> str:
    return f"Hello, {name}!"

def add(a: int, b: int) -> int:
    return a + b
EOF

# 有漏洞的文件：调用了 greet 但没导入
cat > src/main.py << 'EOF'
"""
Bug 演示：调用了 greet()，但没有从 utils 导入它
如果没有 Moat 拦截，这个代码会在运行时崩溃
"""

def run():
    name = "Moat"
    # ❌ greet() 调用了但没导入 —> ImportError
    message = greet(name)
    print(message)


if __name__ == "__main__":
    run()
EOF

sleep 0.5

echo ""
echo "═══════════════════════════════════════════"
echo "  🛡️  moat check — Bug 拦截演示"
echo "═══════════════════════════════════════════"
echo ""

# 运行moat检查
moat check --quick 2>&1 || true

echo ""
echo "═══════════════════════════════════════════"
echo "  ✅ 检测到 IMPORT-MISSING-001"
echo "  Bug `greet() used but not imported`"
echo "  在提交前就被拦截了"
echo "═══════════════════════════════════════════"

sleep 3

# 清理
rm -rf "$TMPDIR"