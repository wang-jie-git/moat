# Moat: The First Self-Evolving AI Coding Guardian 🚀

> [中文](https://github.com/wang-jie-git/moat/blob/main/README.md) | English

Moat 不仅仅是一个静态代码校验工具，它是你代码库的**"具身智能"神经系统**。
在 AI 辅助编程成为常态的今天，我们不仅需要 AI 帮我们写代码，更需要一个能够感知"代码痛觉"、记住"架构教训"、并随项目演进而"自我进化"的守护者。

## 🛡️ 为什么需要 Moat？

AI 编码极快，但"副作用"往往滞后。当你修改一段代码时，你是否担心：

- AI 破坏了系统的核心业务逻辑？
- 修改了一处代码，却引发了远处难以追踪的"痛感"（Bug）？
- 随着项目变大，你是否在重复修复同样的架构漏洞？

Moat 解决这一切。它通过实时 AST 感知、痛觉评分系统（Pain Score）和 One Memory 记忆引擎，构建了一个闭环的自我防御机制。

## ✨ 核心特性

### 🧠 神经感知系统 (Neural Perception)
基于 AST 的骨架图分析，精准定位每一次变更的影响域（Impact Analysis）。

### 😣 痛觉评分 (Pain Score)
自动识别鉴权、竞态、核心 API 等敏感区域，对风险进行 0-100 分量化，让"危险"可视化。

### 💾 持久化记忆 (Long-term Memory)
与 One Memory 无缝集成，像海马体一样记录 Bug 演变与修复历史。

### ⚡ 实时守护 (Sidecar Daemon)
轻量级守护进程，在编辑器（VS Code）中实时反馈，无需人工触发。

### 🧬 自我进化 (Self-Evolution)
系统不仅检测错误，还会通过进化指标监控"神经衰弱"，并根据重构表现自动调整防御阈值。

## 🚀 快速上手

```bash
# 1. 安装
pip install moat-ai

# 2. 初始化你的守护者
moat init

# 3. 开始你的 AI 协作
# Moat 会在后台感知变动，并通过 VS Code 插件提供实时反馈
```

## 🌟 演进路线

| 阶段 | 定义 | 功能 |
|------|------|------|
| v0.1 | 护城河 | 基础的校验与基线对比 |
| v0.2 | 神经突触 | AST 增量感知与痛觉评分 |
| v0.3 | 具身进化 | AI 辅助修复 + VS Code 集成 + Sidecar 守护进程 |
| v0.4 | 自我进化 | 进化指标系统 + 神经衰弱防护 + 智能自适应调整 |

## 🤝 社区共创

Moat 是一个由 AI 驱动、开发者治理的实验性项目。我们坚信：**代码质量不应靠死板的规则维持，而应靠系统的"智能免疫"来保障**。

如果你对 AI 工程化、具身智能开发环境感兴趣，欢迎加入我们。即使你只是提交一个 Bug 报告，也是在参与这个数字生命的进化过程。

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
│   └── adapters/
│       └── __init__.py     # AI Adapters
├── pyproject.toml           # Build Config
├── README.md
└── LICENSE
```

## License

MIT © 2026 One Team
