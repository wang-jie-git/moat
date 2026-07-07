# CHANGELOG

所有 Moat 项目的重要变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.4.0] - 2026-07-07

### 🎉 里程碑: 第一个自我进化的 AI 编码守护者

Moat 不再是一个静态代码校验工具，而是进化成了"具身智能神经系统"。

### ✨ 新增功能

#### 进化指标系统（防止"神经衰弱"）

- **六大进化指标**:
  - ✅ 重构成功率（Refactor Success Rate）
  - ✅ 性能提升率（Performance Improvement Rate）
  - ✅ Bug 修复时效（Bug Fix Time）
  - ✅ 误报率（False Positive Rate，负向指标）
  - ✅ 开发效率（Dev Velocity）
  - ✅ Pain Score 趋势

- **神经衰弱检测机制**:
  - 🔴 Critical（负向占比 ≥ 50%）→ 降低 Pain Score 阈值
  - 🟡 Warning（30-50%）→ 轻微调整权重
  - 🟢 Encourage（≤ 15%）→ 鼓励创新

- **智能调整策略**:
  - 自动推荐配置变更
  - 防止系统过度保守
  - 保持进化方向性

- **CLI 命令**: `moat evolution report/adjust/record`

#### AI 辅助修复

- **修复策略库**（12+ 种策略）
- **修复建议生成**: 基于策略库的智能建议 + 代码示例 + 置信度评分
- **CLI 命令**: `moat fix [--no-dry-run] [--copy] [--format json]`

#### Sidecar 守护进程

- **守护进程管理**: PID/日志/状态文件 + start/stop/restart/status
- **实时文件监控**: watchdog + 防抖 + 自动排除
- **增量检查自动化**: 文件变更时自动运行检查 + Pain Score 实时评估
- **FastAPI REST API**（8 个端点）

#### VS Code 插件

- **集成命令**（8 个）: moat.check, moat.fix, moat.sidecar.*, moat.init, moat.report
- **编辑器集成**: 右键菜单 + 诊断显示 + Webview 修复详情 + 保存时自动检查
- **Sidecar API 集成**: 优先 API + 优雅降级

### 🔄 改进

- **README 开篇**: 全新定位"第一个自我进化的 AI 编码守护者"
- **License**: MIT → Apache 2.0（更好的专利保护和品牌保护）

### 📚 文档

- `docs/EVOLUTION_METRICS.md` — 进化指标系统核心概念
- `docs/EVOLUTION_METRICS_GUIDE.md` — 集成指南
- `docs/GEMINI_INSIGHT_IMPLEMENTATION.md` — Gemini 洞察实现报告

### 🧪 测试

- ✅ 新增 `tests/test_evolution_metrics.py`（10 个测试）
- ✅ 新增 `tests/test_fixer.py`（5 个测试）
- ✅ **总通过率**: 45/45 (100%)

## [0.3.0] - 2026-07-07

### ✨ 新增功能

#### 混沌测试集
- 随机注入故障
- 自动验证检测能力

#### 三大隐形坑防御机制
- **记忆写入过滤器**: 防止碎片化
- **SQLite 共享存储桥接器**: 跨语言通信
- **元知识反向驱动**: 主动进化

### 🔄 改进
- **上下文感知报告**: `.moat/architecture_intent.md`
- **DX 优化**: `moat check --diff` + `moat report --copy`

### 🧪 测试
- ✅ 30/30 测试通过

## [0.2.0] - 2026-07-07

### ✨ 新增功能

#### 第二阶段：构建免疫循环
- **交互式引导**（`moat init`）: 自动检测项目类型
- **核心业务探测**（`moat/core_areas.py`）: 6 大核心区域
- **详尽失败报告**（`moat/report.py`）: AI 修复建议 + JSON 输出

#### 深层进化
- **Pain Score 自我校准**（`moat/pain/feedback.py`）
- **混沌测试集**（`moat/testing/chaos.py`）

### 🔄 改进
- **插件化检查架构**: 基于 Check 基类的可插拔系统
- **TypeScript 检查**: 4 个专项检查
- **CodeGraph 集成**: 语义分析

### 🧪 测试
- ✅ 30/30 测试通过

## [0.1.0] - 2026-07-07

### ✨ 初始版本

- **四层门禁检查**: L0 语法 → L1 存活 → L2 结构 → L3 关联 → L4 基线
- **实时监控**（`moat watch`）
- **Web 看板**（`moat dashboard`）
- **AI 适配器**（Claude Code + Cursor + Pre-commit）

### 🧪 测试
- ✅ 30/30 测试通过

[0.4.0]: https://github.com/wang-jie-git/moat/releases/tag/v0.4.0
[0.3.0]: https://github.com/wang-jie-git/moat/releases/tag/v0.3.0
[0.2.0]: https://github.com/wang-jie-git/moat/releases/tag/v0.2.0
[0.1.0]: https://github.com/wang-jie-git/moat/releases/tag/v0.1.0
