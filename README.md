# Moat — AI 编码守门员 🚀

> **当前版本**: v1.0.3 | [更新日志](CHANGELOG.md) | [发布说明](https://github.com/wang-jie-git/moat/releases)

**一句话**: AI 写代码太快，Bug 也埋得太快。Moat 是你本地化的架构守门员，零配置，实时拦截。

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

## 🔧 完整命令参考

```bash
# 核心检查
moat check [--quick|--full|--diff|--legacy]  # 4种检查模式 ✨ v1.0.3
moat init                                     # 零配置初始化 ✨ v1.0.3
moat watch                                    # 实时监控日志
moat report                                   # 生成检查报告
moat baseline [save|show|diff]               # 基线管理

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


## 🌟 演进路线

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

## 🤝 社区共创

Moat 是一个由 AI 驱动、开发者治理的实验性项目。我们坚信：**代码质量不应靠死板的规则维持，而应靠系统的"智能免疫"来保障**。

如果你对 AI 工程化、具身智能开发环境感兴趣，欢迎加入我们。即使你只是提交一个 Bug 报告，也是在参与这个数字生命的进化过程。

---

# Moat — AI 编码护城河

## 为什么

AI 改代码很快。AI 搞坏系统也很快。

修一个 bug 出三个 bug 的根本原因：**改代码的人不熟悉系统的所有子系统**。Moat 的四层防线在改代码前/后各跑一次，12 秒内告诉你系统有没有被搞坏。

## 安装

### 从 PyPI 安装（推荐）

```bash
# 基础安装（包含守门员规则）
pip install moat-ai

# 完整安装（包含 Web 看板 + Sidecar + VS Code 辅助）
pip install "moat-ai[all]"
```

### 从 GitHub 安装

```bash
# 基础安装
pip install git+https://github.com/wang-jie-git/moat.git

# 完整安装
pip install "git+https://github.com/wang-jie-git/moat.git[all]"
```

### 按需安装

```bash
# Web 看板（FastAPI + 前端界面）
pip install "moat-ai[dashboard]"

# Sidecar 守护进程（实时文件监控 + REST API）
pip install "moat-ai[sidecar]"

# VS Code 插件辅助（剪贴板复制）
pip install "moat-ai[vscode]"
```

### 包含内容

**基础安装**（~5MB）：
- ✅ 四层门禁检查（L0-L4）
- ✅ 守门员规则系统（5 条安全规则）
- ✅ Pain Score 评分
- ✅ AI 辅助修复
- ✅ 进化指标系统
- ✅ 4 种检查模式（quick/full/diff/legacy）
- ✅ 零配置初始化

**完整安装**（~50MB，在基础安装之上）：
- Web 看板（FastAPI + 前端）
- Sidecar 守护进程（实时监控 + REST API）
- VS Code 插件辅助（剪贴板复制）

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
| **L1 存活** | import 正常、API 能返回 200、核心模块可实例化、关键文件存在、**文件内容哈希校验** ✨ v1.0 |
| **L2 结构** | API 返回的 JSON 字段符合契约（防前后端断裂）、**代码熵增检测** ✨ v1.0、**依赖枢纽识别** ✨ v1.0 |
| **L3 关联** | 改了 A，B 还能用（防修一个出三个） |
| **L4 基线** | 文件数不减少、代码量不退化、**文件哈希基线对比** ✨ v1.0、**代码熵增预警** ✨ v1.0 |

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

MIT © 2026 One Team
