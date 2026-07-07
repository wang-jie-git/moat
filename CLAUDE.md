# CLAUDE.md — Moat 项目开发指南

> **项目**: Moat (moat-ai) — AI 编码护城河
> **GitHub**: https://github.com/wang-jie-git/moat
> **版本**: v0.2.0+
> **最后更新**: 2026-07-07

---

## 🎯 项目定位

**核心价值**: 防止 AI 改代码时"越改越乱"

**哲学**: 改代码前跑一次，改代码后再跑一次。两次都通过才能提交。

**演进方向**: 从"校验工具" → "自我感知神经系统"

---

## 📊 当前状态（2026-07-07）

### 已完成 ✅

#### 第一阶段：神经突触建设
- ✅ AST 增量感知（`moat/ast/`）
  - 项目骨架图构建器（`builder.py`）
  - AST 增量对比器（`diff.py`）
  - 函数调用图生成（164 函数, 1005 调用）
  - **突触连接置信度模型**（Edge 类，置信度 0.3-1.0）
- ✅ 痛觉评分系统（`moat/pain/`）
  - Pain Score 算法（0-100 分）
  - **自我校准机制**（`feedback.py`，反馈闭环）
  - 核心业务/鉴权/API/竞态权重检测
- ✅ 增量检查命令（`moat check --diff`）
  - 对比 Git 变更
  - 影响域分析
  - Pain Score 评估

#### 第二阶段：构建免疫循环
- ✅ 交互式引导（`moat/discovery.py`）
  - 自动检测项目类型和框架
  - 智能识别：FastAPI/Flask/Django/React/Vue/Next.js
- ✅ 核心业务探测（`moat/core_areas.py`）
  - 6 大核心区域：鉴权/支付/数据核心/API 网关/配置中心/用户核心
  - 敏感级别标记（critical/high/medium/low）
- ✅ 详尽失败报告（`moat/report.py`）
  - 详细错误分析
  - AI 修复建议
  - **结构化 JSON 输出**（`--format json`）
- ✅ **上下文感知报告**
  - `.moat/architecture_intent.md` — 架构意图文档
  - 业务约束明确化

#### 深层进化
- ✅ **混沌测试集**（`moat/testing/chaos.py`）
  - 随机注入故障
  - 自动验证检测能力
- ✅ **三大隐形坑防御机制**
  - 记忆写入过滤器（`moat/memory/filter.py`）
  - SQLite 共享存储桥接器（`moat/memory/bridge.py`）
  - 元知识反向驱动（`moat/evolution.py`）

#### 基础功能
- ✅ 插件化检查架构（`moat/checks/base.py`）
- ✅ TypeScript 检查模块（4 个检查）
- ✅ CodeGraph 语义分析集成
- ✅ moat report --copy 命令
- ✅ 测试覆盖：30/30 通过

---

## 🏗️ 项目结构

```
moat/
├── moat/
│   ├── cli.py              # CLI 入口（argparse）
│   ├── runner.py           # 检查运行器
│   ├── discovery.py        # 项目自动发现 + 交互式引导
│   ├── report.py           # 报告生成器（text/md/json）
│   ├── baseline.py         # 基线管理
│   ├── monitor.py          # 实时监控
│   ├── core_areas.py       # 核心业务探测
│   ├── __init__.py         # 版本号：0.2.0
│   │
│   ├── checks/             # 检查规则（插件化架构）
│   │   ├── base.py         # Check 基类
│   │   ├── l1_*.py         # L1 检查（Python 旧风格）
│   │   ├── l2_schema.py    # L2 结构检查
│   │   ├── l3_correlation.py # L3 关联检查
│   │   ├── l4_baseline.py  # L4 基线对比
│   │   └── typescript/     # TypeScript 检查
│   │       ├── syntax.py   # 语法检查
│   │       ├── dedup.py    # 去重检查
│   │       ├── race_condition.py # 竞态检查
│   │       └── timing_doc.py # 时序文档
│   │
│   ├── ast/                # AST 感知层（第一阶段）
│   │   ├── __init__.py
│   │   ├── builder.py      # 骨架图构建器
│   │   └── diff.py         # AST 增量对比器
│   │
│   ├── pain/               # 痛觉评分层
│   │   ├── scorer.py       # Pain Score 算法
│   │   └── feedback.py     # 自我校准机制
│   │
│   ├── memory/             # 记忆层（Moat + One Memory 桥接）
│   │   ├── filter.py       # 记忆写入过滤器
│   │   └── bridge.py       # SQLite 共享桥接器
│   │
│   ├── evolution.py        # 元知识反向驱动
│   └── testing/
│       └── chaos.py        # 混沌测试集
│
├── .moat/                  # 项目配置（自动生成）
│   ├── config.json         # 项目配置
│   ├── claude.md           # AI 适配规则
│   ├── baseline.json       # 基线数据
│   ├── architecture_intent.md  # 架构意图
│   ├── memory.db           # 共享记忆库（SQLite）
│   └── evolved_rules.json  # 进化规则（自动生成）
│
├── tests/                  # 测试（30/30 通过）
├── docs/                   # 文档
├── pyproject.toml          # 构建配置
└── README.md               # 主文档
```

---

## 🎯 核心设计原则

### 1. 规则与逻辑分离（避免维护地狱）

**Rule Engine**（可插拔）:
- `moat/checks/` — 所有检查规则
- 核心代码只负责调度
- 规则报错不影响核心运行

**Core**（稳定）:
- `moat/cli.py` — CLI 入口
- `moat/runner.py` — 检查调度器
- `moat/ast/` — AST 感知层
- `moat/pain/` — 痛觉评分层

### 2. 向后兼容性优先

- ✅ Python 检查（旧风格）和新检查并存
- ✅ 配置格式兼容（`.moat/config.json`）
- ✅ 无需改动现有项目

### 3. 防御性编程

- ✅ 过滤器防止碎片化
- ✅ WAL 模式支持并发
- ✅ 混沌测试集持续验证

---

## 🔑 关键决策记录

### Q1: 为什么用 Python ast 而不是 tree-sitter？
**A**: Python ast 内置，零依赖，足够用于原型验证。未来可升级到 tree-sitter（多语言支持）。

### Q2: Pain Score 校准阈值为什么是 3 次反馈？
**A**: 避免单次误判导致权重剧烈波动，3 次反馈是统计显著性的最低要求。

### Q3: 为什么 SQLite 而不是 HTTP API 通信？
**A**:
- 零进程开销（< 1ms vs 50-100ms）
- 跨语言原生支持（Python + TypeScript）
- WAL 模式支持并发读写
- 无需维护服务进程

### Q4: 过滤阈值为什么是 Pain Score > 50？
**A**: 50 分是 MEDIUM/HIGH 分界线，避免低级错误污染记忆库。

---

## 📝 开发工作流

### 新功能开发流程

1. **创建分支**: `git checkout -b feature/xxx`
2. **编写测试**: 先写测试（TDD）
3. **实现功能**: 遵循现有架构
4. **运行测试**: `python3 -m pytest tests/ -v`
5. **更新文档**: 更新 README.md 和 CLAUDE.md
6. **提交 PR**: `git push origin feature/xxx`

### 代码风格

- **Python**: 遵循 PEP 8
- **类型提示**: 尽可能使用
- **文档字符串**: 所有公共函数/类必须有
- **测试覆盖**: 新功能必须包含测试

### 提交信息格式

```
feat(scope): 简短描述

详细说明（可选）

相关 Issue: #xxx
```

**示例**:
```
feat(evolution): 实现元知识反向驱动机制

- 新增 EvolutionEngine
- 生成 .moat/evolved_rules.json
- 增强版 Pain Scorer

测试: ✅ 30/30 通过
```

---

## 🚀 快速开始

### 安装

```bash
# 从 PyPI
pip install moat-ai

# 从 GitHub
pip install git+https://github.com/wang-jie-git/moat.git
```

### 开发环境

```bash
# 1. 克隆仓库
git clone https://github.com/wang-jie-git/moat.git
cd moat

# 2. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 3. 安装依赖
pip install -e .

# 4. 运行测试
python3 -m pytest tests/ -v
```

### 常用命令

```bash
# 检查（完整）
moat check

# 增量检查
moat check --diff

# 交互式初始化
moat init

# 生成报告
moat report --copy --format json

# 运行混沌测试
python3 -m moat.testing.chaos
```

---

## 📊 测试覆盖

**当前**: 30/30 测试通过 ✅

**测试文件**:
- `tests/test_checks.py` — 检查模块测试
- `tests/test_cli.py` — CLI 测试
- `tests/test_monitor.py` — 监控测试

**运行测试**:
```bash
python3 -m pytest tests/ -v
```

---

## 🔧 调试技巧

### 查看骨架图

```bash
python3 -c "
from moat.ast.builder import build_skeleton
skeleton = build_skeleton('.')
print(f'函数数: {skeleton.to_dict()[\"stats\"][\"total_functions\"]}')
print(f'调用数: {skeleton.to_dict()[\"stats\"][\"total_calls\"]}')
"
```

### 查看 Pain Score

```bash
python3 -c "
from moat.pain.scorer import calculate_pain_score
error = {'type': 'race_condition', 'file': 'src/auth.py', 'message': 'pendingMessageRef'}
result = calculate_pain_score(error)
print(f'Pain Score: {result[\"score\"]}/100 ({result[\"level\"]})')
"
```

### 查看记忆库统计

```bash
python3 -c "
from moat.memory.bridge import SharedStorageBridge, BridgeConfig
bridge = SharedStorageBridge(BridgeConfig(db_path='.moat/memory.db'))
bridge.initialize()
print(bridge.get_statistics())
bridge.close()
"
```

---

## 📚 重要文档

- `README.md` — 项目主文档（中文）
- `README.en.md` — 英文文档
- `CHANGELOG.md` — 版本更新日志
- `EVOLUTION_ROADMAP.md` — 三阶段演进路线图
- `DX_IMPROVEMENTS.md` — DX 优化详细说明
- `DEEP_EVOLUTION_COMPLETE.md` — 深层进化完成报告
- `THREE_PILLARS_COMPLETE.md` — 三大隐形坑防御机制
- `EVOLUTION_COMPLETE.md` — 演进完成报告

---

## 🤝 贡献指南

详见 `CONTRIBUTING.md`

### 关键联系人

- **作者**: wangjiezhong <523362775@qq.com>
- **GitHub**: https://github.com/wang-jie-git/moat

---

## 📄 许可证

MIT © 2026 One Team

---

## 💡 关键概念

### Pain Score（痛觉评分）

0-100 分评估错误危险程度：
- **CRITICAL**（≥75）：立即修复
- **HIGH**（≥50）：尽快修复
- **MEDIUM**（≥25）：计划修复
- **LOW**（<25）：可选修复

### 置信度权重

影响域分析的可信度：
- **1.0**：直接函数调用
- **0.9**：对象方法调用
- **0.7**：间接依赖
- **0.3**：动态调用

### 进化规则

梦境引擎 → Insight → 进化规则 → Moat 主动进化

---

## 🔗 相关项目

- **One Memory**: https://github.com/wang-jie-git/one-memory
  - 图+向量混合架构的持久记忆系统
  - Moat + One Memory = 质量守护 + 智能记忆

- **CodeGraph**: https://github.com/colbymchenry/codegraph
  - 代码知识图谱
  - Moat 使用 CodeGraph 进行语义分析

---

## 📞 获取帮助

- **Issues**: https://github.com/wang-jie-git/moat/issues
- **Discussions**: https://github.com/wang-jie-git/moat/discussions

---

**记住**: 改代码前跑一次，改代码后再跑一次。两次都通过才能提交。🛡️
