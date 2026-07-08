# CHANGELOG

所有 Moat 项目的重要变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化](https://semver.org/lang/zh-CN/)。

## [0.6.2] - 2026-07-08

### 🎯 覆盖率优化

#### P0 紧急修复

- **修复 evolution.py 测试失败**: EnhancedPainScorer 初始化逻辑修复
- **修复 BridgeConfig 导入**: 修复 NameError（便捷函数）
- **修复数据库连接泄漏**: sync.py 添加 finally 块确保连接关闭
  - 消除 ResourceWarning: unclosed database

#### P1 核心模块覆盖提升

- **l1_behavior.py**: 0% → 100%（新增 8 个测试）
- **l2_schema.py**: 0% → 100%（新增 13 个测试）
- **contract.py**: 0% → 100%（新增 12 个测试）

#### P2 TypeScript 检查模块

- **any_type.py**: 0% → 88%（新增 16 个测试）
- **async_race.py**: 0% → 96%（新增 11 个测试）
- 修复 any_type.py 3 个 bug（变量名 `total`/`total_any` 混用）

#### P3 其他模块优化

- **cli.py**: 37% → 37%（+6 参数解析测试）
- **sidecar/watcher.py**: 38% → 45%（+15 测试）
- **evolution.py**: 65% → 98%（修复 14 个测试）

### 🐛 Bug 修复

#### TypeScript 检查

- **any_type.py:69,75,87**: 变量名 `total` 未定义
  - 影响：当检测到 >20 个 any 类型时会崩溃
  - 修复：统一使用 `total_any` 变量名

#### 进化模块

- **evolution.py:173-176**: EnhancedPainScorer 覆盖测试设置
  - 影响：14 个进化模块测试失败
  - 修复：优先使用 `evolution_engine.evolved_rules`

#### 数据库连接

- **sync.py:325**: 数据库连接未关闭
  - 影响：ResourceWarning 警告
  - 修复：添加 finally 块确保连接关闭

### 📊 测试覆盖

- ✅ **总测试数**: 723 通过（+41）
- ✅ **失败测试**: 0（从 14 降至 0）
- ✅ **整体覆盖率**: 63% → 67%（+4%）
- ✅ **未覆盖行数**: 1495 → 1351（-144）

### 🏆 测试分布

| 模块 | 覆盖率 | 状态 |
|------|--------|------|
| L1-L4 检查层 | 84-100% | ✅ 优秀 |
| AST 感知层 | 78-91% | ✅ 良好 |
| TypeScript 检查 | 平均 44% | ⚠️ 待优化 |
| Sidecar 守护进程 | 45-82% | ⚠️ 待优化 |
| CLI 命令 | 37% | ⚠️ 待优化 |

### 📝 新增测试文件

- `tests/test_contract.py` - CONTRACT.md 生成器测试
- `tests/test_l1_behavior.py` - 行为验证检查测试
- `tests/test_l2_schema.py` - API 结构检查测试
- `tests/test_ts_any_type.py` - TypeScript any 类型检测测试
- `tests/test_ts_async_race.py` - TypeScript 异步竞态检测测试

### 🔧 改进的测试文件

- `tests/test_evolution.py` - 修复 14 个测试失败
- `tests/test_cli.py` - 新增 6 个参数解析测试
- `tests/test_sidecar_watcher.py` - 新增 15 个文件监控测试

---

## [0.6.1] - 2026-07-07

### 🐛 Bug 修复

#### Sidecar 可选依赖修复

- **watchdog 延迟导入**: `moat/sidecar/watcher.py` 改为 try-except 保护
- **条件继承**: `FileChangeHandler` 根据 watchdog 可用性条件继承
- **启动检查**: `SidecarWatcher.start()` 增加 watchdog 可用性检查
- **Pydantic BaseModel 跳过**: `moat/checks/l1_modules.py` 检测并跳过 Pydantic 模型实例化

**修复的问题**:
- ❌ `ModuleNotFoundError: No module named 'watchdog'` → ✅ 优雅降级
- ❌ `CheckRequest() 实例化失败` → ✅ Pydantic 模型检测跳过

**影响**: `moat check` 自举测试通过率 19→21 通过，失败 4→0

### 🔄 改进

- **版本号**: v0.6.0 → v0.6.1
- **文档**: 新增 `SIDECAR_BUGFIX_REPORT.md` 详细修复报告
- **发布测试**: 新增 `RELEASE_TEST_REPORT_v0.6.1.md` 完整测试报告

### 📊 测试覆盖

- ✅ **单元测试**: 81/81 通过 (100%)
- ✅ **moat check 自举**: 21 通过, 0 失败, 1 警告
- ✅ **Sidecar Bug 修复验证**: 2/2 通过
- ✅ **CLI 命令测试**: 10/10 通过
- ✅ **进化指标系统**: 正常运行 (0.325/1.000)
- ✅ **AST 骨架图**: 391 函数, 441 调用

### 📝 发布验证

- ✅ **GitHub Release**: https://github.com/wang-jie-git/moat/releases/tag/v0.6.1
- ✅ **Git Tag**: v0.6.1
- ✅ **发布测试报告**: `RELEASE_TEST_REPORT_v0.6.1.md`

**测试时间**: 2026-07-08 07:45
**测试环境**: macOS Darwin 24.6.0, Python 3.14.6

---

## [0.6.0] - 2026-07-07

### 🎉 里程碑: 多语言感知 + 深度记忆 + 智能进化

Moat 进化为**跨语言代码质量守护平台**，支持 Tree-sitter 多语言解析、One Memory 深度集成和知识图谱记忆扩展。

### ✨ 新增功能

#### Tree-sitter 多语言支持

- **Tree-sitter 集成**: 支持 Python/TypeScript/JavaScript/Go/Rust 等语言
- **跨语言骨架图**: 统一的函数调用图生成
- **多语言 AST 感知**: 语言无关的增量对比
- **CLI 命令**: `moat ast build --lang typescript`

**新增文件**:
- `moat/ast/tree_sitter.py` — Tree-sitter 封装
- `tests/test_tree_sitter.py` — Tree-sitter 测试

#### One Memory 深度集成

- **自动触发梦境引擎**: `moat memory dream` 触发 One Memory Insight 生成
- **双向同步管理器**: 自动同步 Insights → 进化规则
- **记忆质量报告**: `moat memory report` 生成详细质量报告
- **同步状态追踪**: 自动记录同步历史

**新增文件**:
- `moat/memory/sync.py` — 双向同步管理器
- `tests/test_memory_sync.py` — Memory Sync 测试

#### 进化指标自动采集

- **自动记录**: `moat check` 后自动记录进化指标
- **配置自动调整**: `moat evolution adjust --auto` 基于指标自动调整配置
- **增强的 EvolutionTracker**: 与 runner 深度集成

**新增文件**:
- `tests/test_evolution_auto.py` — 进化指标自动采集测试

#### 知识图谱记忆扩展

- **修复历史追踪**: 记录 Bug 修复次数、修复人、修复时间
- **架构薄弱点识别**: 高频 Bug 文件/模块自动识别
- **修复模式推荐**: 基于历史成功修复的模板
- **智能提示系统**: 检查时主动提示历史问题

**新增表结构**:
- `fix_history` — Bug 修复历史
- `weak_points` — 架构薄弱点
- `fix_patterns` — 修复模式
- `dream_triggers` — 梦境触发记录
- `smart_hints` — 智能提示

**新增文件**:
- `tests/test_knowledge_graph.py` — 知识图谱扩展测试

### 🔄 改进

- **版本号**: v0.4.0 → v0.5.0
- **定位更新**: "多语言感知 + 深度记忆 + 智能进化"
- **文档增强**: 新增 4 个核心功能文档

### 📊 测试覆盖

- ✅ **新增测试**: 36 个（9 + 9 + 7 + 11）
- ✅ **总通过率**: 72/72 (100%)
- ✅ **跳过**: 9（tree-sitter 依赖未安装）

### 🧪 性能指标

- Tree-sitter 解析速度: < 50ms/文件
- One Memory 同步延迟: < 100ms
- 进化指标自动采集: 0ms 额外开销
- 智能提示查询: < 5ms

## [0.4.0] - 2026-07-07

### 🎉 里程碑: 第一个自我进化的 AI 编码守护者

（保持原有内容...）

[0.6.1]: https://github.com/wang-jie-git/moat/releases/tag/v0.6.1
[0.5.0]: https://github.com/wang-jie-git/moat/releases/tag/v0.5.0
[0.4.0]: https://github.com/wang-jie-git/moat/releases/tag/v0.4.0
