# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-07-07

### Added

#### 插件化检查架构
- 新增 `moat/checks/base.py` — 统一的 `Check` 基类
- 自动检测项目类型（Python/TypeScript/Go/Rust）
- 向后兼容：Python 检查（旧风格）和新检查（基于 Check 基类）并存

#### TypeScript 检查模块（4 个新检查）
- `TypeScriptSyntaxCheck` — 语法检查（调用 `tsc --noEmit`）
- `TypeScriptDedupCheck` — 去重/防抖代码注释检查
- `TypeScriptRaceConditionCheck` — 竞态条件注释检查
- `TypeScriptTimingDocCheck` — 时序文档检查

#### CodeGraph 语义检查（Track B）
- 新增 `moat/checks/typescript/semantic.py`
- `CodeGraphClient` — CodeGraph SQLite 数据库客户端（轻量级，不依赖 codegraph 包）
- `SemanticDedupCheck` — 基于 CodeGraph 的去重逻辑检查
- `SemanticRaceConditionCheck` — 基于 CodeGraph 的竞态条件检查
- `ChangeImpactAnalyzer` — 变更影响分析器（分析符号变更的影响范围）
- 可选启用：配置 `enable_semantic_checks: true` 激活

#### 测试覆盖
- 27 个测试全部通过（新增 5 个语义检查测试）
- 覆盖 CheckResult 数据结构、Check 基类、TypeScript 检查、CodeGraph 语义检查、CLI、Monitor

### Changed
- 更新版本号：0.1.0 → 0.2.0
- 更新 `moat/checks/__init__.py` — 支持可选语义检查

### Documentation
- 更新 README.md — 加入 TypeScript 使用说明
- 更新 README.zh.md — 加入 TypeScript 使用说明
- 新增 CHANGELOG_v0.2.0.md — v0.2.0 详细升级日志

## [0.1.0] - 2025-07-07

### Added
- Initial public release
- L0: Syntax checking
- L1: Import/API/Modules/Files/Subsystems/Behavior checks
- L2: Schema validation
- L3: Correlation checks
- L4: Baseline comparison
- CLI: `moat check`, `moat init`, `moat baseline`, `moat watch`, `moat dashboard`
- Pre-commit hook integration
- GitHub Actions integration
- Claude Code adapter
- Cursor adapter

### Documentation
- README (Chinese + English)
- CONTRIBUTING.md
- CODE_OF_CONDUCT.md
- SECURITY.md

[0.2.0]: https://github.com/wang-jie-git/moat/releases/tag/v0.2.0
[0.1.0]: https://github.com/wang-jie-git/moat/releases/tag/v0.1.0
