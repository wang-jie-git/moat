#!/bin/bash

echo "=========================================="
echo "🧪 Moat 架构重构验证"
echo "=========================================="
echo ""

# 1. 验证目录结构
echo "1️⃣  验证目录结构..."
if [ -d "moat/immune/unit" ] && [ -d "moat/immune/contract" ] && [ -d "moat/immune/bdd" ] && [ -d "moat/immune/visual" ] && [ -d "moat/immune/pipeline" ]; then
    echo "   ✅ moat/immune/ 目录结构完整"
else
    echo "   ❌ moat/immune/ 目录结构不完整"
    exit 1
fi

# 2. 验证文件存在性
echo ""
echo "2️⃣  验证关键文件..."
files=(
    "moat/immune/__init__.py"
    "moat/immune/cli.py"
    "moat/immune/unit/__init__.py"
    "moat/immune/unit/generator.py"
    "moat/immune/contract/__init__.py"
    "moat/immune/bdd/__init__.py"
    "moat/immune/visual/__init__.py"
    "moat/immune/pipeline/__init__.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file 缺失"
        exit 1
    fi
done

# 3. 验证 CLI 命令
echo ""
echo "3️⃣  验证 CLI 命令..."
if python3 -m moat immune --help > /dev/null 2>&1; then
    echo "   ✅ moat immune 命令可用"
else
    echo "   ❌ moat immune 命令不可用"
    exit 1
fi

# 4. 验证测试
echo ""
echo "4️⃣  运行测试..."
if python3 -m pytest tests/test_ai_test_gate.py -q --tb=short > /tmp/test_output.txt 2>&1; then
    echo "   ✅ 测试通过"
    tail -n 3 /tmp/test_output.txt | head -n 1
else
    echo "   ❌ 测试失败"
    cat /tmp/test_output.txt
    exit 1
fi

# 5. 验证 Gatekeeper 规则
echo ""
echo "5️⃣  验证 Gatekeeper 规则..."
if python3 -c "from moat.gatekeeper.rules import RuleEngine; print('   ✅', len(RuleEngine().rules), '个规则已加载')" > /dev/null 2>&1; then
    python3 -c "from moat.gatekeeper.rules import RuleEngine; print('   ✅', len(RuleEngine().rules), '个规则已加载')"
else
    echo "   ❌ 规则加载失败"
    exit 1
fi

# 6. 验证向后兼容性
echo ""
echo "6️⃣  验证向后兼容性..."
if python3 -m moat test --help > /dev/null 2>&1; then
    echo "   ✅ moat test 命令仍可用（兼容保留）"
else
    echo "   ❌ moat test 命令不可用"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ 所有验证通过！架构重构成功！"
echo "=========================================="
