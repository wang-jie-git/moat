#!/bin/bash
# Moat 一键安装脚本
# 用于测试安装配置是否正确

set -e

echo "🚀 Moat v0.4.0 一键安装脚本"
echo "================================"
echo ""

# 检测 Python 版本
echo "📋 检查 Python 版本..."
python_version=$(python3 --version 2>&1)
echo "   ✅ $python_version"

# 检测 pip
echo "📋 检查 pip..."
if command -v pip3 &> /dev/null; then
    echo "   ✅ pip3 已安装"
    PIP=pip3
elif command -v pip &> /dev/null; then
    echo "   ✅ pip 已安装"
    PIP=pip
else
    echo "   ❌ pip 未安装"
    exit 1
fi

echo ""
echo "📦 选择安装方式:"
echo "   1) 基础安装（核心功能）"
echo "   2) 完整安装（所有功能）"
echo "   3) 自定义安装"
echo ""
read -p "请输入选项 (1-3): " choice

case $choice in
    1)
        echo "📦 安装基础版本..."
        $PIP install -e .
        ;;
    2)
        echo "📦 安装完整版本..."
        $PIP install -e ".[all]"
        ;;
    3)
        echo "📦 自定义安装..."
        echo "可用选项:"
        echo "   dashboard - Web 看板"
        echo "   sidecar   - Sidecar 守护进程"
        echo "   vscode    - VS Code 插件辅助"
        read -p "请输入要安装的选项（用空格分隔）: " extras
        $PIP install -e ".[$extras]"
        ;;
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac

echo ""
echo "✅ 安装完成！"
echo ""
echo "📋 验证安装..."

# 验证 moat 命令
if command -v moat &> /dev/null; then
    echo "   ✅ moat 命令可用"
    moat --version
else
    echo "   ⚠️  moat 命令未找到，可能需要手动配置 PATH"
fi

echo ""
echo "🎉 安装完成！"
echo ""
echo "下一步:"
echo "  1. 初始化: moat init"
echo "  2. 运行检查: moat check"
echo "  3. 查看帮助: moat --help"
echo ""
echo "文档: https://github.com/wang-jie-git/moat"
echo ""
