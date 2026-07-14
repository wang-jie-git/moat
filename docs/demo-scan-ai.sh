#!/bin/bash
# Moat AI Tool Permissions Audit Demo
# 演示：扫描 Claude Code / Codex 的权限配置

echo "═══════════════════════════════════════════"
echo "  🔒  moat check --scan-ai"
echo "  AI 工具行为审计"
echo "═══════════════════════════════════════════"
echo ""

# 1. 扫描 AI 工具配置
moat check --scan-ai 2>&1 || true

echo ""
echo "═══════════════════════════════════════════"

sleep 1

echo ""
echo "═══════════════════════════════════════════"
echo "  📋  moat audit --permissions"
echo "  AI 代理权限审计"
echo "═══════════════════════════════════════════"
echo ""

# 2. 权限审计
moat audit --permissions 2>&1 || true

echo ""
echo "═══════════════════════════════════════════"
echo "  ✅  权限瘦身建议已生成"
echo "  删除闲置高危权限 → 减少攻击面"
echo "═══════════════════════════════════════════"