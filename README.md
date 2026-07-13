# Moat — AI 编码守门员 🚀 / AI Coding Gatekeeper

> **当前版本**: v1.1.3 | [更新日志](CHANGELOG.md)
>
> [![PyPI version](https://img.shields.io/pypi/v/moat-ai.svg?style=flat-square&color=brightgreen)](https://pypi.org/project/moat-ai/)
> [![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg?style=flat-square)](LICENSE)
> [![Python](https://img.shields.io/badge/python-3.10+-blue.svg?style=flat-square)](pyproject.toml)
> [![Tests](https://img.shields.io/badge/tests-1009%20passed-brightgreen?style=flat-square)](tests/)
[![CI](https://github.com/wang-jie-git/moat/actions/workflows/ci.yml/badge.svg)](https://github.com/wang-jie-git/moat/actions/workflows/ci.yml)
>
> **English**: Moat is a real-time AI coding gatekeeper. It runs locally in your terminal and CI, catching architecture breaks, security leaks, and regression bugs *before* AI-generated code hits your repo. Zero config, <0.2s per check.

**一句话**: AI 写代码太快，Bug 也埋得太快。Moat 是你本地化的架构守门员，零配置，实时拦截。
**In one line**: AI writes code fast — and breaks things faster. Moat is your local gatekeeper that catches the breaks before they land.

---

## 🎯 Why Moat? / 为什么选择 Moat?

| Feature | Other Lint Tools | Moat |
|---------|-----------------|------|
| **Architecture Guard** / 架构守护 | ❌ | ✅ (Real-time Gatekeeper) |
| **Security Injection** / 安全注入拦截 | ❌ (High noise) | ✅ (Zero false positives) |
| **Import Completeness** / 导入完整性检查 | ❌ | ✅ (ImportCompletenessChecker, AST 静态分析) |
| **Performance** / 性能开销 | High | **< 0.2s** (per check) |
| **AI Context Integration** | ❌ | ✅ (MCP / Claude Code Hook) |
| **Hardcoded Secret Detection** | ❌ | ✅ (SECRETS-001, 10+ patterns) |
| **Dependency Security Scan** | ❌ | ✅ (DEPS-001, built-in DB) |
| **Unused Export Detection** | ❌ | ✅ (UNUSED-001, Python/TS/Go) |
| **Fail-open Strategy** | ❌ | ✅ (External failures never block) |
| **Test Coverage** | ❌ | ✅ **99.8%+** (1009/1011 tests) |

---

## 📍 Where is Moat? / Moat 的定位与安装方式

### Where does it live? / Moat 到底"长"在哪里？

**Physical location**: Moat is a standard Python package. Install it via `pip install moat-ai` into your project's virtual environment, or as a global tool.
**物理位置**: Moat 是一个标准的 Python 包。你可以通过 `pip install moat-ai` 将其安装在**被开发项目的虚拟环境（venv）**中，或者作为全局工具安装。

**Where it runs**: On your **local machine** (terminal or daemon), never on Claude/Cursor's cloud servers. Your code never leaves your machine.
**运行位置**: 它运行在**开发者的本地机器上**（终端或守护进程），而不是运行在 Claude/Cursor 的云端服务器里。你的代码永远不会离开你的机器。

### How does Moat work with Claude/Cursor? / Moat 是怎么和 Claude/Cursor 配合的？

Moat is a **CLI tool**. Claude/Cursor can use it in these ways:
Moat 本质上是一个 **CLI 工具**（命令行工具）。Claude/Cursor 可以通过以下方式使用 Moat：

#### 方式 1: 直接调用 CLI 命令（当前，推荐）

Claude 可以直接在终端中执行 Moat 的命令：

```bash
# Claude 执行这些命令
moat check --full              # 运行完整检查
moat architecture --format json # 生成架构健康报告
moat gatekeeper check --file app.py # 检查单个文件
```

**这就是你现在使用 Moat 的方式**：Claude 就像在终端里打字一样，调用 `moat` 命令，然后根据返回结果给出建议或修复代码。

**优点**:
- ✅ 简单直接，不需要额外配置
- ✅ 立即可用
- ✅ 充分利用 Moat 的全部能力

---

#### 方式 2: Sidecar 守护进程（实时监控）

Moat 可以运行一个 Sidecar 守护进程，提供实时监控和 API 访问：

```bash
# 启动 Sidecar
moat sidecar start

# 通过 REST API 访问
curl http://localhost:7777/api/health
```

**适用场景**: 持续集成环境或实时监控需求。

---

#### 方式 3: 静态规则注入（被动指导）

Moat 可以在你的项目中生成规则文件，告诉 AI 工具遵守架构约束：

```bash
# 为 Claude 生成规则
moat adapter claude
# → 生成 CLAUDE.md，包含 Moat 的使用规则

# 为 Cursor 生成规则
moat adapter all
# → 生成 .cursor/rules.mdc
```

**这是"被动指导"**：AI 工具会读取这些规则文件，但不会实时调用 Moat。

---

### 用户感知的"安装路径" (产品差异化点)

Moat 是一种**"非侵入式的工程赋能"**：

1. **终端用户 (CLI)**: `pip install moat-ai` → `moat init`。此时它就是一个命令行工具，你手动运行 `moat check` 就像运行 `git status` 一样。

2. **AI 深度玩家 (Claude/Cursor)**:
   - **步骤**: Claude 直接执行 `moat check`、`moat architecture` 等命令。
   - **体验**: AI 在改代码前后会自动调用 Moat 检查，就像人类开发者一样。

3. **编辑器极客 (VS Code/Cursor 用户)**:
   - **步骤**: 配置 pre-commit hook 或使用 Sidecar。
   - **体验**: 提交前自动检查，或实时监控架构健康度。

### 为什么这么设计是最好的？

- **不被平台绑架**: Moat 是一个独立的 CLI 工具。如果有一天 Claude 倒闭了，Moat 还在，你依然可以在终端里使用它。
- **数据安全**: 因为 Moat 运行在本地，代码不需要发给任何"Moat 云"去检查，这让企业用户和开源项目非常放心。
- **简单直接**: 不需要复杂的 MCP 配置，不需要理解协议，直接执行命令就能用。

**You own the code, you own the guard.**

---

## 🔑 "最后的清醒时刻"——Moat 的灵魂

> **AI 是一个会撒谎、会贪快、会产生幻觉的个体。只要 AI 是在"预测下一个 Token"，它就永远会有"记忆盲区"和"偷懒倾向"。**
>
> **Moat 真正的价值在于：它是 AI 的"刹车片"。**
>
> 哪怕 AI 再强，只要它在高速运行，它就需要物理意义上的"刹车"。你不必做那个驾驶员，你只需要做好那个无论 AI 怎么踩油门，都能在最关键的转弯处发出警报并自动降速的"刹车系统"。

**为什么这个定位如此重要**:
- ❌ **玩具 vs 工具**: 如果你把 Moat 定义为"AI 工程操作系统"或"自我进化系统"，它是一个玩具。如果你把它定义为"刹车片"，它是一个工具。
- ❌ **AI 会变强，但不会变诚实**: 未来的 AI 能力更强，但它仍然会有"偷懒倾向"（为了速度牺牲质量）和"记忆盲区"（上下文窗口之外就是黑暗）。
- ✅ **"刹车"的永恒价值**: 无论 AI 怎么进化，物理定律不变——高速运动需要刹车，复杂系统需要检查点，连续输出需要暂停验证。

**这个反思把项目从"玩具"拉回到"工具"的轨道上。这是 Moat 生命力最旺盛的时刻。**

---

---

## 📚 更多文档

- [快速开始](快速开始.md) — 5分钟上手教程
- [常见问题](常见问题.md) — FAQ 和故障排除
- [项目地图](项目地图.md) — 完整功能全景图
- [CHANGELOG](CHANGELOG.md) — 版本更新日志
- [贡献指南](CONTRIBUTING.md) — 如何贡献代码
- [ROADMAP](ROADMAP.md) — 未来路线图

---

## Quick command reference / 完整命令参考

```bash
# 核心检查
moat check [--quick|--full|--diff|--legacy] [--optimize]  # 4种检查模式 + 优化检查 ✨ v1.0.6
moat check [--quick|--full|--diff|--legacy]  # 4种检查模式 ✨ v1.0.3
moat init                                     # 零配置初始化 ✨ v1.0.3
moat watch                                    # 实时监控日志
moat report                                   # 生成检查报告
moat baseline [save|show|diff]               # 基线管理

# 优化检查（Ponytail 集成）✨ v1.0.6
moat check --quick --optimize                 # 快速检查 + 优化规则
moat check --full --optimize                  # 完整检查 + 优化规则
moat report                                   # 技术债务报告（自动分类展示）

# 优化规则配置
# max_complexity: 圈复杂度阈值（默认 10）
# max_function_length: 函数长度阈值（默认 50 行）
# max_cognitive_complexity: 认知复杂度阈值（默认 15）
# check_yagni: 是否启用 YAGNI 检查（默认 true）
# check_dead_code: 是否启用死代码检测（默认 true）
# check_duplicate_code: 是否启用重复代码检测（默认 false）
# check_stdlib: 是否启用标准库检查（默认 true）

# 进化指标
moat evolution report                         # 查看进化报告
moat evolution adjust                         # 自动调整配置
moat evolution record                         # 手动记录指标

# AI 修复
moat fix [--no-dry-run|--copy]               # AI 辅助修复

# Sidecar 守护进程
moat sidecar start                            # 启动守护进程
moat sidecar status                           # 查看状态
moat sidecar stop                             # 停止守护进程

# AI 适配器
moat adapter claude                           # 安装 Claude Code 适配器
moat adapter all                              # 安装所有 AI 工具适配器
moat adapter precommit                        # 安装 pre-commit hook

# Web 看板
moat dashboard [--port 8080]                  # 启动 Web 看板

# 架构验收
moat verify --all                             # 运行全部验收算子
moat verify --operator <name>                 # 运行单个算子

# 守门员规则 ✨ v1.0.3
moat rules list                               # 列出所有规则
moat gatekeeper check --file <path>          # 检查单个文件
```


## Evolution roadmap / 演进路线

| 版本 | 发布日期 | 核心理念 | 关键特性 |
|------|---------|---------|---------|
| v0.1 | 2026-07-07 | 护城河 | 四层门禁检查（L0-L4）、实时监控、Web看板、AI适配器 |
| v0.2 | 2026-07-07 | 神经突触 | AST 增量感知、痛觉评分（Pain Score）、TypeScript 检查 |
| v0.3 | 2026-07-07 | 具身进化 | AI 辅助修复、混沌测试集、三大隐形坑防御 |
| v0.4 | 2026-07-07 | 自我进化 | 进化指标系统、神经衰弱防护、智能自适应调整 |
| v0.5 | 2026-07-07 | 多语言感知 | Tree-sitter 多语言支持、知识图谱记忆、One Memory 集成 |
| v0.6 | 2026-07-07 | 深度记忆 | One Memory 深度集成、智能同步、记忆写入过滤器 |
| v0.7 | 2026-07-08 | 架构验收 | 审计算子化架构（7个算子）、Gatekeeper 实时守门、Sidecar 守护进程 |
| v0.8 | 2026-07-09 | 原则具象化 | Karpathy Principles Constitution、手术刀检查器、简单性检查器 |
| **v0.9** | **2026-07-10** | **极速重构** | **零配置（18倍）、超快检查（40倍）、守门员规则（5条）、Bug 检测实战** |
| **v1.0** | **2026-07-11** | **架构哨兵** | **L2 架构检查（熵增+依赖枢纽）、架构健康报告、性能优化（缓存+并行）、4.3x 加速** |
| **v1.0.8** | **2026-07-11** | **精准拦截 + 性能飞跃** | **SECRETS-001 硬编码密钥检测、SQL-002 增强 SQL 注入检测（ORM 支持）、DEPS-001 依赖项安全检测、UNUSED-001 未使用导出检测、API-002 增强鉴权检测、LRU 缓存优化（1.7x 加速）、AST diff 增量扫描、增强报告生成器、多源配置支持** |
| **v1.1.1** | **2026-07-12** | **质量提升 + Bug 修复** | **测试覆盖率 96.9% → 99.6%+（+26 测试）、8 个关键 Bug 修复、ThinkingBlock 兼容性修复、macOS 路径修复、TypeScript 检测增强、发布到 GitHub & PyPI** |
| **v1.1.2** | **2026-07-12** | **Moat Immune 修复 + 知识资产库** | **ThinkingBlock AttributeError 三层防护、+42 个测试、知识资产库（防御模式/Bug 模式/修复策略）、文档站点 + CI 自动化** |
| **v1.1.3** | **2026-07-13** | **导入完备性检查** | **ImportCompletenessChecker 算子（AST 静态分析）、性能优化（跳过超大文件/单体文件）、跨文件引用提示、Makefile/dev 依赖/SRE 污染修复、1009/1011 测试通过** |

## Community / 社区共创

Moat 是一个由 AI 驱动、开发者治理的实验性项目。我们坚信：**代码质量不应靠死板的规则维持，而应靠系统的"智能免疫"来保障**。

如果你对 AI 工程化、具身智能开发环境感兴趣，欢迎加入我们。即使你只是提交一个 Bug 报告，也是在参与这个数字生命的进化过程。

---

# Moat — AI 编码护城河

## 为什么

AI writes code fast. AI breaks your system faster.

The root cause of "fix one, break three": **The code modifier (human or AI) doesn't know all subsystems**.
AI 改代码很快。AI 搞坏系统也很快。

修一个 bug 出三个 bug 的根本原因：**改代码的人不熟悉系统的所有子系统**。Moat 的四层防线在改代码前/后各跑一次，12 秒内告诉你系统有没有被搞坏。

## Install / 安装

### From PyPI (recommended) / 从 PyPI 安装（推荐）

```bash
# 基础安装（包含守门员规则）
pip install moat-ai

# 完整安装（包含 Web 看板 + Sidecar + VS Code 辅助）
pip install "moat-ai[all]"
```

### From GitHub / 从 GitHub 安装

```bash
# 基础安装
pip install git+https://github.com/wang-jie-git/moat.git

# 完整安装
pip install "git+https://github.com/wang-jie-git/moat.git[all]"
```

### Optional extras / 按需安装

```bash
# Web 看板（FastAPI + 前端界面）
pip install "moat-ai[dashboard]"

# Sidecar 守护进程（实时文件监控 + REST API）
pip install "moat-ai[sidecar]"

# VS Code 插件辅助（剪贴板复制）
pip install "moat-ai[vscode]"
```

### 包含内容 / What's included

**Base install** (~5MB) / **基础安装**：
- ✅ 4-layer gate check (L0-L4) / 四层门禁检查
- ✅ Gatekeeper rules (8 security rules) / 守门员规则系统
- ✅ Pain Score / 痛觉评分
- ✅ AI-assisted fix / AI 辅助修复
- ✅ Evolution metrics / 进化指标系统
- ✅ 4 check modes (quick/full/diff/legacy)
- ✅ Zero-config init / 零配置初始化
- ✅ **Hardcoded secret detection** (SECRETS-001) ✨ v1.0.8
- ✅ **Dependency security scan** (DEPS-001) ✨ v1.0.8
- ✅ **Enhanced SQL injection detection** (SQL-002) ✨ v1.0.8
- ✅ **Unused export detection** (UNUSED-001) ✨ v1.0.8
- ✅ **LRU cache optimization** (1.7x speedup) ✨ v1.0.8

**Full install** (~50MB, adds on top of base) / **完整安装**：
- Web dashboard (FastAPI + frontend) / Web 看板
- Sidecar daemon (real-time monitoring + REST API)
- VS Code assistant (clipboard copy) / 插件辅助

### 依赖说明

**核心依赖**（自动安装）：
- Python 3.10+
- httpx >= 0.27
- pyyaml >= 6.0
- tree-sitter >= 0.20.0（守门员规则必需）

**可选依赖**（按需安装）：
- **watchdog** — Sidecar 文件监控
- **fastapi + uvicorn** — Web 看板 + Sidecar API
- **pyperclip** — 剪贴板复制


## Usage / 使用

### 1. Init / 初始化

```bash
cd your-project
moat init
```

自动检测项目结构，保存基线数据，生成 AI 适配规则。
Auto-detects project structure, saves baseline data, generates AI adapter rules.

### 2. Check before/after code changes / 改代码前/后检查

```bash
moat check
```

Runs all 4 defense layers + gatekeeper rules in ~12 seconds:
12 秒跑完四层防线 + 守门员规则：

| Layer | What it does / 作用 |
|-------|-------------------|
| **L0 Syntax** | No syntax errors in Python/TypeScript files / 语法零错误 |
| **L1 Survival** | Imports work, APIs return 200, core modules instantiate, key files exist / 骨架存活 |
| **L2 Structure** | API JSON fields match contracts (prevent frontend-backend mismatch), code entropy detection / 结构完整 |
| **L3 Correlation** | Changed A doesn't break B (prevents "fix one, break three") / 关联安全 |
| **L4 Baseline** | File count doesn't shrink, code volume doesn't regress, hash comparison / 基线不退化 |
| **Gatekeeper Rules** | SQL injection, hardcoded secrets, API auth, race conditions, error handling, dep security, unused exports / 守门员规则 |

**TypeScript-specific checks** (v0.2.0+) / **TypeScript 专项检查**：

| Check / 检查项 | What it does / 作用 |
|----------------|-------------------|
| **Syntax** / 语法 | Runs `tsc --noEmit` to validate / 验证语法 |
| **Dedup** / 去重 | Dedup/debounce code must have "why" comments / 必须有注释说明 |
| **Race condition** / 竞态 | Race-critical logic must have timing comments / 必须有时序注释 |
| **Timing docs** / 时序文档 | Sequence diagram must exist (optional) / 时序图文档必须存在 |
| **Semantic analysis** / 语义分析 | CodeGraph-based deep semantic check (optional) |

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

### 3. Real-time monitoring / 实时监控

```bash
moat watch --log logs/backend.log
```

服务器运行中实时监控日志错误，分级着色显示。

**过滤规则**：
```bash
# 自定义过滤关键词
moat watch --log logs/backend.log --filter "ERROR|Traceback|ImportError"

# 只监控 ERROR 和 Traceback
moat watch -l logs/app.log -f "ERROR|Traceback"
```

**后台持久化运行**：

```bash
# 方法 1: nohup（推荐，简单）
nohup moat watch --log logs/backend.log > logs/moat_watch.log 2>&1 &

# 方法 2: screen（可以重新连接）
screen -S moat_watch
moat watch --log logs/backend.log
# Ctrl+A+D 分离，screen -r moat_watch 恢复

# 方法 3: tmux（现代替代品）
tmux new -s moat_watch
moat watch --log logs/backend.log
# Ctrl+B+D 分离，tmux attach -t moat_watch 恢复

# 停止后台监控
pkill -f "moat watch"
```

### 4. Auto-config / 自动运行配置

Moat 支持多种自动运行模式，通过在 `.moat/moat.json` 中配置：

```json
{
  "check_on_commit": true,       // ✅ 提交时自动检查（推荐）
  "auto_monitor": true,           // ✅ 启动时自动监控日志
  "auto_check_on_save": false     // ❌ 保存时检查（可选，耗性能）
}
```

#### 提交时自动检查

**工作原理**：
```bash
git add .
git commit -m "feat: 新增功能"
# ⚡ Moat 自动检查中...
# ✅ 通过 → 继续提交
# ❌ 失败 → 阻止提交
```

**启用方式**：
1. `moat init` 自动配置 git pre-commit hook
2. 或手动配置：`moat adapter precommit`

**优点**：
- ✅ 零配置（moat init 自动启用）
- ✅ 不影响开发速度
- ✅ 确保提交的代码质量

#### 保存时自动检查（可选）

**工作原理**：
```json
{
  "auto_check_on_save": true
}
```

保存文件时自动触发检查，适合对质量要求极高的项目。

**缺点**：
- ⚠️  可能影响编辑器性能
- ⚠️  增加系统开销

#### VS Code / Cursor 编辑器集成

**VS Code 配置**（`.vscode/tasks.json`）：
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Moat: 检查当前文件",
      "type": "shell",
      "command": "moat check --quick",
      "group": "build",
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    },
    {
      "label": "Moat: 全量检查",
      "type": "shell",
      "command": "moat check --full",
      "group": "test",
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    }
  ]
}
```

**快捷键绑定**（`.vscode/keybindings.json`）：
```json
{
  "key": "ctrl+shift+m",
  "command": "workbench.action.tasks.runTask",
  "args": "Moat: 检查当前文件"
}
```

**效果**：
- 按 `Ctrl+Shift+M` → 检查当前文件
- 保存时 → 可选触发检查

#### 推荐工作流

**日常开发**：
1. **启动监控**（一次启动，持续运行）
   ```bash
   nohup moat watch --log logs/backend.log > logs/moat_watch.log 2>&1 &
   ```

2. **开发代码** → 编辑器显示语法错误

3. **Moat 实时监控** → 后台捕获运行时错误

4. **提交代码** → `git commit` 触发 Moat 检查

5. **推送** → `git push`

**完整示例**：
```bash
# 1. 初始化（只需一次）
moat init

# 2. 启动监控（后台运行）
nohup moat watch --log logs/backend.log > logs/moat_watch.log 2>&1 &

# 3. 开发...

# 4. 提交前自动检查
git add .
git commit -m "feat: 新增功能"
# Moat 自动拦截有问题的提交

# 5. 推送
git push
```

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

### 9. 架构健康检查（v1.0+）

```bash
# 生成架构健康报告
moat architecture

# Markdown 格式（适合文档）
moat architecture --format md

# JSON 格式（适合 CI/CD）
moat architecture --format json

# 复制到剪贴板
moat architecture --copy
```

**功能特性**：
- **健康评分**：0-100 分量化架构健康度
- **代码熵增检测**：识别增长过快的文件（>50% 黄色预警，>100% 红色预警）
- **依赖枢纽识别**：统计被引用最多的核心模块
- **文件内容变更**：基于哈希的变更检测
- **智能改进建议**：基于检测结果的定制化建议

**使用场景**：
- 每周运行一次，监控架构健康度
- 发现潜在的技术债务
- 识别需要重构的模块
- 评估架构演进质量

## 完整示例

### 日常开发流程

```bash
# 1. 初始化（首次使用）
cd /path/to/project
moat init

# 2. 改代码前检查
moat check

# 3. 改代码...
# vim src/api/users.py

# 4. 改代码后检查
moat check

# 5. 通过后提交
git add .
git commit -m "fix: ..."
```

### 每周架构健康检查

```bash
# 1. 生成架构健康报告
moat architecture --format md > architecture_health.md

# 2. 查看健康评分和问题
cat architecture_health.md

# 3. 如果发现问题，生成详细报告
moat check --full

# 4. 保存新的基线（如果已修复问题）
moat baseline save
```

### CI/CD 集成

```bash
# GitHub Actions 中使用 --skip-architecture 加速
moat check --full --skip-architecture

# 或单独运行架构检查（每周一次）
moat architecture --format json > architecture_report.json
```

### 服务器运行时监控

```bash
# 实时监控日志
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
│   └── adapters/
│       └── __init__.py     # AI Adapters
├── pyproject.toml           # Build Config
├── README.md
└── LICENSE
```

## License

Apache 2.0 © 2026 One Team
