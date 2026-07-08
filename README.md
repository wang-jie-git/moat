# Moat: 多语言感知 + 深度记忆 + 智能进化 🚀

> [中文](https://github.com/wang-jie-git/moat/blob/main/README.zh.md) | English
> **当前版本**: v0.7.0-beta.1 | [更新日志](CHANGELOG.md) | [发布说明](https://github.com/wang-jie-git/moat/releases)

Moat 不仅仅是一个静态代码校验工具，它是你代码库的**"多语言智能神经系统"**。
在 AI 辅助编程成为常态的今天，我们不仅需要 AI 帮我们写代码，更需要一个能够：
- 感知**多语言**代码变更（Python/TypeScript/Go/Rust）
- 记住**架构教训**（One Memory 深度集成）
- 随项目演进而**自我进化**（知识图谱 + 智能提示）
- 验收**架构质量**（规则、示例、证据驱动的验收系统）

## 🎉 最新更新 (v0.7.0-beta.1)

### 🎯 算子能力增强

- ✅ **api_response_spec 完整实现**: 真实扫描 API 端点并验证响应格式
  - 解析 FastAPI 装饰器 (`@app.get`, `@router.post`)
  - 检查响应模型和 HTTP 状态码
  - 检测统一响应格式
- ✅ **framework_usage 算子增强**: 检查框架特性充分利用
  - FastAPI: Pydantic + ExceptionHandler + Depends + APIRouter + BackgroundTasks
  - Django: ORM + Forms/Serializers + get_object_or_404
  - Flask: Marshmallow + errorhandler
- ✅ **Claude Code Hook 集成**: 自动生成 `.claude/settings.json`
  - 交互式配置询问
  - PreToolUse + PostToolUse Hooks
  - 开箱即用

### 📦 安装方式

#### 方式 1: 一键安装（推荐）

```bash
cd /Users/mac/Desktop/moat
./install.sh
```

#### 方式 2: 创建别名

```bash
# Bash/Zsh
echo 'alias moat="python3 -m moat"' >> ~/.bashrc
source ~/.bashrc
```

#### 方式 3: 直接使用

```bash
python3 -m moat --help
python3 -m moat check
python3 -m moat verify --all
```

[查看完整更新日志 →](CHANGELOG.md)

## 🛡️ 为什么需要 Moat？

AI 编码极快，但"副作用"往往滞后。当你修改一段代码时，你是否担心：

- AI 破坏了系统的核心业务逻辑？
- 修改了一处代码，却引发了远处难以追踪的"痛感"（Bug）？
- 随着项目变大，你是否在重复修复同样的架构漏洞？

Moat 解决这一切。它通过实时 AST 感知、痛觉评分系统（Pain Score）和 One Memory 记忆引擎，构建了一个闭环的自我防御机制。

## ✨ 核心特性

### 🌐 多语言感知 (Multi-language Perception)
基于 Tree-sitter 的多语言 AST 解析，支持 Python/TypeScript/Go/Rust 等。

### 😣 痛觉评分 (Pain Score)
自动识别鉴权、竞态、核心 API 等敏感区域，对风险进行 0-100 分量化。

### 💾 深度记忆 (Deep Memory)
与 One Memory 无缝集成，自动触发梦境引擎、双向同步、记忆质量报告。

### 🧬 智能进化 (Smart Evolution)
知识图谱记忆扩展：修复历史追踪、薄弱点识别、修复模式推荐、智能提示。

### ⚡ 实时守护 (Sidecar Daemon)
轻量级守护进程，在编辑器（VS Code）中实时反馈。

### 🎯 架构验收系统 (Architecture Verification)
基于"规则、示例、证据"的架构验收方法论，7步验收流程确保架构质量。

### 🚧 实时架构守门 (Architecture Gatekeeper)
文件写入前的实时架构规则检查，三层豁免机制平衡严格性与灵活性。

## 🚀 快速上手

### 安装

#### 一键安装（推荐）⭐

```bash
# 安装所有功能（包括 Web 看板、Sidecar、VS Code 辅助）
pip install "moat-ai[all]"
```

#### 基础安装

```bash
# 仅核心功能
pip install moat-ai
```

#### 从 GitHub 安装

```bash
# 最新版
pip install git+https://github.com/wang-jie-git/moat.git

# 完整版
pip install "git+https://github.com/wang-jie-git/moat.git[all]"
```

### 开始使用

```bash
# 1. 初始化项目
cd your-project
moat init

# 2. 运行检查
moat check

# 3. 架构验收（NEW!）
moat verify

# 4. 查看进化报告
moat evolution report

# 5. 获取 AI 修复建议
moat fix
```

**说明**: Moat 会在后台感知变动，并通过 VS Code 插件提供实时反馈。

---

## 📦 安装选项对比

| 功能 | 基础版 | 完整版 |
|------|--------|--------|
| 四层门禁检查 | ✅ | ✅ |
| Pain Score 评分 | ✅ | ✅ |
| AST 增量感知 | ✅ | ✅ |
| AI 辅助修复 | ✅ | ✅ |
| 进化指标系统 | ✅ | ✅ |
| **架构验收系统** | **✅** | **✅** |
| Web 看板 | ❌ | ✅ |
| Sidecar 守护进程 | ❌ | ✅ |
| 剪贴板复制 | ❌ | ✅ |
| **依赖大小** | ~5MB | ~50MB |

### 按需安装

```bash
# Web 看板
pip install "moat-ai[dashboard]"

# Sidecar 守护进程
pip install "moat-ai[sidecar]"

# VS Code 插件辅助
pip install "moat-ai[vscode]"
```

---

## 🔍 架构验收（v0.7.0-beta）

基于口播视频文案《怎么验收AI搭建的后端架构》设计，实现"规则、示例、证据"驱动的架构验收系统。

### 核心命令

```bash
# 完整验收（7步流程）
moat verify

# 单项验收
moat verify --operator directory_responsibility

# JSON输出
moat verify --json

# CI/CD集成：评分低于60分则失败
moat verify --fail-on-score 60
```

### 7步验收流程

1. **目录责任验收** — 验证每个目录的责任是否清晰
2. **最小模块演练** — 验证架构规则能否落地
3. **接口响应规范** — 验证接口返回是否规范统一
4. **框架利用检查** — 验证是否充分利用框架能力
5. **运行证据包** — 固化项目运行方式
6. **架构健康度评分** — 量化架构质量（0-100分）
7. **实施真元文档** — 生成架构权威文档

### 架构健康度评分

| 分数 | 等级 | 行动 |
|------|------|------|
| 80-100 | 优秀 | ✅ 继续开发 |
| 70-79 | 良好 | ✅ 继续（建议优化到80+） |
| 60-69 | 一般 | ⚠️ 优化后再新增功能 |
| <60 | 不健康 | ❌ 禁止新增功能 |

### 详细文档

📄 [ARCHITECTURAL_AUDIT_PROTOCOL.md](ARCHITECTURAL_AUDIT_PROTOCOL.md) — 架构验收方法论

📄 [moat-v0.7.0-architecture-upgrade.md](../Documents/ObsidianVault/2.项目/Moat\ AI编码护城河_backup_20260707_195416/3.技术文档/moat-v0.7.0-architecture-upgrade.md) — v0.7.0架构升级方案

---

## 🚧 实时架构守门（v0.7.0-beta）

实时架构规则检查系统，在文件写入前验证架构合规性。

### 核心命令

```bash
# 列出所有规则
moat gatekeeper rules

# 检查单个文件
moat gatekeeper check --file api/users.py

# 启动守护进程（开发中）
moat gatekeeper start
```

### 4条核心规则

| 规则ID | 规则名称 | 严重程度 | 说明 |
|--------|---------|---------|------|
| `directory_responsibility` | 目录责任 | ERROR | 文件应放在符合其职责的目录 |
| `layer_separation` | 分层架构 | ERROR | 检查import是否违反分层 |
| `naming_convention` | 命名规范 | WARNING | 文件命名应符合规范 |
| `framework_usage` | 框架利用 | WARNING | 优先使用框架推荐机制 |

### 三层豁免机制（"免死金牌"）

当确实需要临时绕过规则时，可以使用三层豁免机制：

#### 1. 行内注释（优先级最高）

```python
# 在违规代码行附近添加
data = json.loads(request.body)  # moat-ignore: framework_usage
```

#### 2. 文件注释

```python
# 在文件头部添加
# moat-ignore: directory_responsibility
# 说明：本文件需要直接访问数据库（临时方案）
```

#### 3. 配置豁免

在 `.moat/gatekeeper_config.json` 中配置：

```json
{
  "ignore_rules": {
    "framework_usage": ["legacy/*.py", "third_party/*"],
    "naming_convention": ["migrations/*"]
  }
}
```

**设计原则**：
- ✅ 默认拦截
- ✅ 显式豁免
- ✅ 审计追踪
- ✅ 定期清理提醒

---

## 📦 安装选项对比

| 功能 | 基础版 | 完整版 |
|------|--------|--------|
| 四层门禁检查 | ✅ | ✅ |
| Pain Score 评分 | ✅ | ✅ |
| AST 增量感知 | ✅ | ✅ |
| AI 辅助修复 | ✅ | ✅ |
| 进化指标系统 | ✅ | ✅ |
| **架构验收系统** | **✅** | **✅** |
| **实时架构守门** | **✅** | **✅** |
| Web 看板 | ❌ | ✅ |
| Sidecar 守护进程 | ❌ | ✅ |
| 剪贴板复制 | ❌ | ✅ |
| **依赖大小** | ~5MB | ~50MB |

- [安装指南](docs/INSTALLATION.md) — 详细安装选项和常见问题
- [CHANGELOG](CHANGELOG.md) — 版本更新日志
- [贡献指南](CONTRIBUTING.md) — 如何贡献代码
- [使用指南](USAGE.md) — **快速开始和常用命令**


## 🚀 快速开始使用

### 三种使用方式

#### 方式 1: 直接使用（无需安装）

```bash
# 在 moat 项目目录下
cd /Users/mac/Desktop/moat

# 通过 python -m 运行
python3 -m moat --help
python3 -m moat check
python3 -m moat verify --all
```

#### 方式 2: 一键安装（推荐）

```bash
# 在 moat 项目目录下
cd /Users/mac/Desktop/moat

# 运行安装脚本
./install.sh

# 选择安装方式:
# 1) 本地安装（虚拟环境）
# 2) 用户目录安装（推荐，~/.local/bin/moat）
# 3) 系统安装（需要 sudo）
# 4) 仅创建别名（快速方案）
```

#### 方式 3: 创建别名（最快）

```bash
# Bash/Zsh
echo 'alias moat="python3 -m moat"' >> ~/.bashrc
# 或
echo 'alias moat="python3 -m moat"' >> ~/.zshrc

# 重新加载配置
source ~/.bashrc  # 或 source ~/.zshrc

# 现在可以直接使用
moat --help
moat check
```

### 常用命令

#### 1. 初始化项目

```bash
# 进入你的项目
cd your-project

# 初始化 Moat
moat init

# 如果有 .claude 目录，会询问是否集成 Claude Code:
# 🤖 Claude Code 集成:
# 是否将 Moat 守护进程集成至 Claude Code？(Y/n): y
# ✓ Claude Code Hook 已启用
# ✓ 已生成 .claude/settings.json
```

#### 2. 运行检查

```bash
# 完整检查（四层门禁）
moat check

# 增量检查（只检查变更）
moat check --diff
```

#### 3. 架构验收（v0.7.0-beta 新功能）

```bash
# 完整验收（7个算子）
moat verify --all

# 单个算子
moat verify --operator api_response_spec      # API 响应规范
moat verify --operator framework_usage        # 框架利用检查
moat verify --operator directory_responsibility  # 目录责任

# JSON 输出（用于 CI/CD）
moat verify --json

# 评分低于 60 分则失败（用于 CI/CD）
moat verify --fail-on-score 60
```

**7个算子**:
1. `directory_responsibility` — 目录责任验收
2. `minimal_module_drill` — 最小模块演练
3. `api_response_spec` — 接口响应规范验收 ⭐ 新增强
4. `framework_usage` — 框架利用检查 ⭐ 新增强
5. `runtime_evidence` — 运行证据包生成
6. `architecture_health_score` — 架构健康度评分
7. `truth_document` — 实施真元文档生成

#### 4. 守门系统

```bash
# 列出所有规则
moat gatekeeper rules

# 检查单个文件
moat gatekeeper check --file api/users.py
```

#### 5. 其他命令

```bash
# 实时监控日志
moat watch --log logs/backend.log

# 生成报告
moat report
moat report --copy  # 复制到剪贴板

# AI 辅助修复
moat fix

# 进化指标
moat evolution report

# 基线管理
moat baseline show
```

### Claude Code Hook 使用

安装后，`.claude/settings.json` 会自动包含：

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "moat gatekeeper check --file ${file}",
        "timeout": 5000
      }]
    }],
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "moat check --diff",
        "timeout": 10000
      }]
    }]
  }
}
```

**效果**:
- **PreToolUse**: Claude Code 写文件前自动检查架构规则
- **PostToolUse**: Claude Code 写文件后自动运行增量检查

[查看完整使用指南 →](USAGE.md)


## 🌟 演进路线

| 阶段 | 定义 | 功能 |
|------|------|------|
| v0.1 | 护城河 | 基础的校验与基线对比 |
| v0.2 | 神经突触 | AST 增量感知与痛觉评分 |
| v0.3 | 具身进化 | AI 辅助修复 + VS Code 集成 + Sidecar 守护进程 |
| v0.4 | 自我进化 | 进化指标系统 + 神经衰弱防护 + 智能自适应调整 |
| v0.5 | 多语言感知 | Tree-sitter 多语言 + One Memory 深度集成 + 知识图谱 |
| v0.6 | 稳定与优化 | Sidecar Bug 修复 + 可选依赖优雅降级 + 测试覆盖增强 |
| **v0.7** | **架构验收与守门** | **架构验收系统 + 实时守门 + 基线管理** |

### v0.7.x 版本说明

#### v0.7.0-beta (2026-07-08) — 架构验收与守门

**架构验收系统 (`moat verify`)**：
- ✅ **7步验收流程**: 基于口播视频文案设计
  - 目录责任验收
  - 最小模块演练
  - 接口响应规范验收
  - 框架利用检查
  - 运行证据包生成
  - 架构健康度评分（0-100分）
  - 实施真元文档生成
- ✅ **算子化架构**: 7个独立算子，灵活组合
- ✅ **证据链完整**: 每个违规都有规则来源→违反代码→修复建议

**实时架构守门 (`moat gatekeeper`)**：
- ✅ **4条核心规则**: 目录责任、分层架构、命名规范、框架利用
- ✅ **三层豁免机制**: 行内注释 → 文件注释 → 配置豁免
- ✅ **审计日志**: 所有检查记录可追溯

**架构基线管理**：
- ✅ 创建/列出/对比/回滚/删除架构基线
- ✅ 支持版本演进可追溯

**测试覆盖**：
- ✅ 全部测试: 801/801 通过 (100%)
- ✅ verification模块: 43/43 通过 (100%)
- ✅ gatekeeper模块: 29/29 通过 (100%)
- ✅ baseline模块: 6/6 通过 (100%)

**文档**：
- ✅ ARCHITECTURAL_AUDIT_PROTOCOL.md — 架构验收方法论
- ✅ moat-v0.7.0-architecture-upgrade.md — 架构升级方案

#### v0.6.1 (2026-07-07) — Sidecar Bug 修复
- ✅ **watchdog 可选依赖修复**: 延迟导入 + 优雅降级
- ✅ **Pydantic BaseModel 跳过**: 检测并跳过需要必填字段的模型实例化
- ✅ **测试覆盖增强**: 81/81 单元测试通过 (100%)
- ✅ **自举测试优化**: moat check 通过率提升至 21/21 (100%)

#### v0.6.0 (2026-07-07) — 多语言感知 + 深度记忆 + 智能进化
- 🌐 **Tree-sitter 多语言支持**: Python/TypeScript/Go/Rust
- 💾 **One Memory 深度集成**: 梦境引擎 + 双向同步
- 🧬 **知识图谱记忆扩展**: 修复历史 + 薄弱点识别 + 智能提示
- 📊 **进化指标自动采集**: 配置自动调整 + 神经衰弱检测

## 🤝 社区共创

Moat 是一个由 AI 驱动、开发者治理的实验性项目。我们坚信：**代码质量不应靠死板的规则维持，而应靠系统的"智能免疫"来保障**。

如果你对 AI 工程化、具身智能开发环境感兴趣，欢迎加入我们。即使你只是提交一个 Bug 报告，也是在参与这个数字生命的进化过程。

### 近期更新

- **v0.7.0-beta** (2026-07-08) — 架构验收系统 + 实时守门 + 基线管理
- **v0.6.1** (2026-07-07) — Sidecar Bug 修复
- **v0.6.0** (2026-07-07) — 多语言感知 + 深度记忆 + 智能进化
- **v0.5.0** (2026-07-07) — 多语言感知 + 深度记忆 + 智能进化

---

# Moat — AI 编码护城河

## 为什么

AI 改代码很快。AI 搞坏系统也很快。

修一个 bug 出三个 bug 的根本原因：**改代码的人不熟悉系统的所有子系统**。Moat 的四层防线在改代码前/后各跑一次，12 秒内告诉你系统有没有被搞坏。

## 安装

### 基础安装

```bash
# 从 PyPI 安装（核心功能）
pip install moat-ai

# 直接从 GitHub 安装最新版
pip install git+https://github.com/wang-jie-git/moat.git
```

### 完整安装（推荐）

```bash
# 一键安装所有功能
pip install "moat-ai[all]"
```

包括：Web 看板 + Sidecar 守护进程 + VS Code 插件辅助

### 按需安装

```bash
# Web 看板（FastAPI + 前端界面）
pip install "moat-ai[dashboard]"

# Sidecar 守护进程（实时文件监控 + REST API）
pip install "moat-ai[sidecar]"

# VS Code 插件辅助（剪贴板复制）
pip install "moat-ai[vscode]"
```

### 功能对比

| 功能 | 基础安装 | 完整安装 |
|------|---------|---------|
| 四层门禁检查 | ✅ | ✅ |
| Pain Score 评分 | ✅ | ✅ |
| AI 辅助修复 | ✅ | ✅ |
| 进化指标系统 | ✅ | ✅ |
| 实时文件监控 | ❌ | ✅ |
| Sidecar REST API | ❌ | ✅ |
| Web 看板 | ❌ | ✅ |
| 剪贴板复制 | ❌ | ✅ |

### 依赖说明

**核心依赖**（自动安装）：
- Python 3.10+
- httpx >= 0.27

**可选依赖**（按需安装）：
- **watchdog** — Sidecar 文件监控
- **fastapi + uvicorn** — Web 看板 + Sidecar API
- **pyperclip** — 剪贴板复制


## 使用

### 1. 初始化

```bash
cd your-project
moat init
```

自动检测项目结构，保存基线数据，生成 AI 适配规则。

### 2. 改代码前/后检查

```bash
moat check
```

12 秒跑完四层防线：

| 层级 | 作用 |
|------|------|
| **L0 语法** | 所有 Python/TypeScript 文件无语法错误 |
| **L1 存活** | import 正常、API 能返回 200、核心模块可实例化、关键文件存在 |
| **L2 结构** | API 返回的 JSON 字段符合契约（防前后端断裂） |
| **L3 关联** | 改了 A，B 还能用（防修一个出三个） |
| **L4 基线** | 文件数不减少、代码量不退化（防隐性删除） |

**TypeScript 专项检查**（v0.2.0+）：

| 检查项 | 作用 |
|--------|------|
| **语法检查** | 调用 `tsc --noEmit` 验证 TypeScript 语法 |
| **去重检查** | 去重/防抖代码必须有"为什么"注释 |
| **竞态检查** | 竞态关键逻辑必须有时序注释 |
| **时序文档** | 时序图文档必须存在（可选） |
| **语义分析** | 基于 CodeGraph 的深度语义检查（可选） |

**启用 TypeScript 检查**：

```bash
# 1. 安装 TypeScript
npm install -g typescript

# 2. 运行检查（自动检测 TypeScript 文件）
moat check
```

**启用语义检查**（需要 CodeGraph）：

```json
// .moat/config.json
{
  "typescript": {
    "tsc_path": "npx tsc",
    "tsconfig": "tsconfig.json",
    "enable_semantic_checks": true
  }
}
```

语义检查提供：
- **变更影响分析**：修改函数前，知道会影响哪些调用方
- **依赖图查询**：基于 CodeGraph 知识图谱的深度语义分析
- **竞态检测**：识别竞态条件和时序问题

### 3. 实时监控

```bash
moat watch --log logs/backend.log
```

服务器运行中实时监控日志错误，分级着色显示。

### 4. Web 看板

```bash
moat dashboard
```

浏览器打开 `http://localhost:9876` 查看错误看板：

- 实时错误列表（自动刷新）
- 运行/保存基线
- 项目状态总览

### 5. AI 适配器

```bash
# 安装所有 AI 工具适配器
moat adapter all

# 只安装 CLAUDE.md
moat adapter claude

# 只安装 pre-commit hook
moat adapter precommit
```

各 AI 工具（Claude Code、Cursor、Codex、Copilot）在改代码时自动遵从 Moat 铁律。

### 6. AI 辅助修复

```bash
# 生成修复建议（演练模式）
moat fix

# 实际应用修复
moat fix --no-dry-run

# 复制报告到剪贴板
moat fix --copy
```

为每个检测到的问题提供详细的修复建议：
- 基于策略库的智能建议
- 代码示例
- 修复置信度
- 支持自动修复简单问题

### 7. 实时感知（Sidecar）

```bash
# 启动 Sidecar 守护进程
moat sidecar start

# 查看状态
moat sidecar status

# 停止
moat sidecar stop

# 前台运行（调试）
moat sidecar start --foreground
```

Sidecar 在后台运行，实时监控文件变化并自动运行增量检查。

### 8. 基线管理

```bash
# 保存当前状态为基线
moat baseline save

# 查看基线
moat baseline show

# 对比当前与基线
moat baseline diff
```

## 完整示例

```bash
# 初始化
cd /path/to/project
moat init

# 改代码前
moat check

# 改代码...
# 改代码后
moat check

# 通过后提交
git add .
git commit -m "fix: ..."

# 服务器运行时实时监控
moat watch --log logs/backend.log
```

## 与 CI 集成

在 GitHub Actions 中添加：

```yaml
- name: Moat Check
  run: |
    pip install moat
    moat check
```

## 与 AI 工具集成

### Claude Code

`moat adapter claude` 自动更新 `CLAUDE.md`，写入铁律。之后 Claude Code 改代码前/后自动跑 `moat check`。

### Cursor

`moat adapter all` 创建 `.cursor/rules.mdc`，Cursor 在改代码时自动遵守。

### Pre-commit

`moat adapter precommit` 安装 git pre-commit hook，每次 `git commit` 前自动检查。

## 常见问题

### Q: 报错了怎么办？

A: `moat check` 报错说明系统有地方坏了。修到通过为止，不要跳过。

### Q: 什么情况下需要更新基线？

A: 如果你**有意地**增加了文件、减少了文件、重构了模块——这些是允许的改动。改完后：

```bash
moat baseline save
```

### Q: 需要服务器运行吗？

A: L1 API 检查需要服务器运行。其他检查不需要。也可以只用 `moat check` 做静态检查。

## 项目结构

```
moat/
├── moat/
│   ├── cli.py              # CLI 入口
│   ├── runner.py           # 检查运行器
│   ├── monitor.py          # 实时监控
│   ├── baseline.py         # 基线管理
│   ├── discovery.py        # 项目自动发现
│   ├── contract.py         # CONTRACT 生成
│   ├── checks/             # 四层检查实现
│   │   ├── l1_import.py    # L1: import 链
│   │   ├── l1_api.py       # L1: API 端点
│   │   ├── l1_modules.py   # L1: 核心模块
│   │   ├── l1_files.py     # L1: 文件完整性
│   │   ├── l1_subsystems.py # L1: 子系统
│   │   ├── l1_behavior.py  # L1: 行为验证
│   │   ├── l2_schema.py    # L2: 结构检查
│   │   ├── l3_correlation.py # L3: 关联检查
│   │   └── l4_baseline.py  # L4: 基线对比
│   ├── dashboard/
│   │   ├── server.py       # FastAPI Web 看板
│   │   └── static/         # 前端文件
│   └── adapters/
│       └── __init__.py     # AI 适配器
├── pyproject.toml           # 构建配置
├── README.md
└── LICENSE
```

---

## English

<a name="moat--ai-coding-guardrails"></a>
# Moat — AI Coding Guardrails

> [中文](#moat--ai-编码护城河) | English

Run once **before** code changes, run again **after** code changes. Both must pass before commit.

Prevent AI tools from "fixing one bug and introducing three more."

## Why

AI writes code fast. AI breaks systems fast.

The root cause of "fix one, break three": **The code modifier (human or AI) doesn't know all subsystems**.

Moat's four-layer defense runs before and after code changes, telling you in 12 seconds if the system is broken.

## Installation

```bash
# From PyPI (recommended)
pip install moat-ai

# With Web Dashboard
pip install "moat-ai[dashboard]"

# Directly from GitHub
pip install git+https://github.com/wang-jie-git/moat.git
```

## Usage

### 1. Initialize

```bash
cd your-project
moat init
```

Auto-detects project structure, saves baseline data, generates AI adapter rules.

### 2. Check Before/After Code Changes

```bash
moat check
```

Completes four-layer defense in 12 seconds:

| Layer | Purpose |
|-------|---------|
| **L0 Syntax** | All Python files pass syntax check |
| **L1 Survival** | Imports work, APIs return 200, core modules instantiate, critical files exist |
| **L2 Structure** | API JSON fields match contract (prevents frontend/backend breaks) |
| **L3 Correlation** | Modified A doesn't break B (prevents "fix one, break three") |
| **L4 Baseline** | File count doesn't decrease, code quality doesn't regress (prevents silent deletions) |

### 3. Live Monitoring

```bash
moat watch --log logs/backend.log
```

Real-time log error monitoring with color-coded severity levels.

### 4. Web Dashboard

```bash
moat dashboard
```

Open `http://localhost:9876` in your browser to view the error dashboard:

- Real-time error list (auto-refresh)
- Run/save baseline
- Project status overview

### 5. AI Adapters

```bash
# Install all AI tool adapters
moat adapter all

# Install Claude Code adapter only
moat adapter claude

# Install pre-commit hook only
moat adapter precommit
```

AI tools (Claude Code, Cursor, Codex, Copilot) automatically follow Moat's rules when modifying code.

### 6. Baseline Management

```bash
# Save current state as baseline
moat baseline save

# View baseline
moat baseline show

# Compare current vs baseline
moat baseline diff
```

## Complete Example

```bash
# Initialize
cd /path/to/project
moat init

# Check before code changes
moat check

# Make changes...
# Check after code changes
moat check

# Commit if passed
git add .
git commit -m "fix: ..."

# Monitor server logs in real-time
moat watch --log logs/backend.log
```

## CI Integration

Add to GitHub Actions:

```yaml
- name: Moat Check
  run: |
    pip install moat
    moat check
```

## AI Tool Integration

### Claude Code

`moat adapter claude` auto-updates `CLAUDE.md` with Moat rules. Claude Code will then run `moat check` before and after code changes.

### Cursor

`moat adapter all` creates `.cursor/rules.mdc`, and Cursor will follow Moat rules when modifying code.

### Pre-commit

`moat adapter precommit` installs a git pre-commit hook that runs checks before every commit.

## FAQ

### Q: What if checks fail?

A: If `moat check` fails, it means something is broken in your system. Fix until it passes. Don't skip.

### Q: When should I update the baseline?

A: If you **intentionally** add files, remove files, or refactor modules — these are allowed changes. After completing:

```bash
moat baseline save
```

### Q: Do I need a running server?

A: L1 API checks require a running server. Other checks don't. You can also use `moat check` for static analysis only.

## Project Structure

```
moat/
├── moat/
│   ├── cli.py              # CLI Entry
│   ├── runner.py           # Check Runner
│   ├── monitor.py          # Live Monitoring
│   ├── baseline.py         # Baseline Management
│   ├── discovery.py        # Project Auto-Discovery
│   ├── contract.py         # CONTRACT Generation
│   ├── checks/             # Four-layer Defense
│   │   ├── l1_import.py    # L1: Import Chain
│   │   ├── l1_api.py       # L1: API Endpoints
│   │   ├── l1_modules.py   # L1: Core Modules
│   │   ├── l1_files.py     # L1: File Integrity
│   │   ├── l1_subsystems.py # L1: Subsystems
│   │   ├── l1_behavior.py  # L1: Behavior Validation
│   │   ├── l2_schema.py    # L2: Structure Check
│   │   ├── l3_correlation.py # L3: Correlation Check
│   │   └── l4_baseline.py  # L4: Baseline Comparison
│   ├── dashboard/
│   │   ├── server.py       # FastAPI Web Dashboard
│   │   └── static/         # Frontend
│   ├── ast/                  # AST 感知层
│   │   ├── builder.py       # 骨架图构建器
│   │   ├── diff.py          # AST 增量对比器
│   │   └── tree_sitter.py   # Tree-sitter 多语言支持
│   ├── pain/                 # 痛觉评分层
│   │   ├── scorer.py        # Pain Score 算法
│   │   └── feedback.py      # 自我校准机制
│   ├── memory/               # 记忆层
│   │   ├── filter.py        # 记忆写入过滤器
│   │   ├── bridge.py        # SQLite 共享桥接器
│   │   └── sync.py          # One Memory 双向同步
│   ├── evolution.py          # 元知识反向驱动
│   ├── dashboard/            # Web 看板
│   │   ├── server.py       # FastAPI Web Dashboard
│   │   └── static/         # Frontend
│   ├── sidecar/              # Sidecar 守护进程
│   │   ├── watcher.py      # 文件监控
│   │   └── daemon.py       # REST API
│   └── adapters/             # AI 工具适配器
│       └── __init__.py     # AI Adapters
├── pyproject.toml           # Build Config
├── README.md
└── LICENSE
```

## License

MIT © 2026 One Team
# Test change
