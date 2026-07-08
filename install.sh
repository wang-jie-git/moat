#!/bin/bash
# Moat 一键安装脚本

set -e

echo "🚀 Moat 安装脚本"
echo "=================="

# 检查 Python 版本
echo "📋 检查 Python 版本..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "   检测到 Python $PYTHON_VERSION"

# 检查是否在虚拟环境中
if [ -d ".venv" ] || [ -n "$VIRTUAL_ENV" ]; then
    echo "   ✓ 检测到虚拟环境"
    INSTALL_MODE="local"
else
    echo "   ℹ️  未检测到虚拟环境"
    echo "   安装选项:"
    echo "   1) 用户目录安装 (推荐，无需 sudo)"
    echo "   2) 系统安装 (需要 sudo)"
    echo "   3) 仅创建别名"
    read -p "   请选择 (1/2/3): " choice
    
    case $choice in
        1) INSTALL_MODE="user" ;;
        2) INSTALL_MODE="system" ;;
        3) INSTALL_MODE="alias" ;;
        *) echo "   ❌ 无效选择"; exit 1 ;;
    esac
fi

# 安装
case $INSTALL_MODE in
    "local")
        echo "📦 本地安装..."
        pip install -e .
        ;;
    "user")
        echo "📦 用户目录安装..."
        pip3 install --user -e .
        ;;
    "system")
        echo "📦 系统安装..."
        sudo pip3 install -e .
        ;;
    "alias")
        echo "⚡ 创建别名..."
        SHELL_RC=""
        if [ -n "$ZSH_VERSION" ]; then
            SHELL_RC="$HOME/.zshrc"
        elif [ -n "$BASH_VERSION" ]; then
            SHELL_RC="$HOME/.bashrc"
        fi
        
        if [ -n "$SHELL_RC" ]; then
            echo 'alias moat="python3 -m moat"' >> "$SHELL_RC"
            echo "   ✓ 已添加到 $SHELL_RC"
            echo "   请运行: source $SHELL_RC"
        else
            echo "   ⚠️  无法检测 shell 类型"
            echo "   请手动添加: alias moat=\"python3 -m moat\""
        fi
        ;;
esac

# 验证安装
echo ""
echo "✅ 安装完成！"
echo ""
echo "🚀 快速开始:"
echo "   moat init              # 初始化项目"
echo "   moat check             # 运行检查"
echo "   moat verify --all      # 架构验收"
echo ""

# 如果安装了，显示版本
if command -v moat &> /dev/null || python3 -m moat --help &> /dev/null; then
    echo "📊 版本信息:"
    python3 -c "import moat; print(f'   Moat v{moat.__version__}')"
fi
