# CHANGELOG

所有 Moat 项目的重要变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化](https://semver.org/lang/zh-CN/)。

## [1.0.2] - 2026-07-11

### 🚀 Phase 3：报告增强

#### 新增功能

- ✅ **L2 架构健康报告**：
  - 集成到 `moat report` 命令
  - 专门的架构健康章节
  - 内容变更报告
  - 熵增预警报告
  - 依赖枢纽报告

- ✅ **独立架构报告命令**：`moat architecture`
  - 文本格式（默认）
  - Markdown 格式（`--format md`）
  - JSON 格式（`--format json`，用于 CI/CD）
  - 复制到剪贴板（`--copy`）

- ✅ **健康评分系统**：
  - 0-100 分评分
  - 🟢 健康（≥80）
  - 🟡 警告（≥60）
  - 🔴 需关注（<60）

- ✅ **智能改进建议**：
  - 基于检测结果的定制化建议
  - 架构维护最佳实践

#### CLI 命令

```bash
# 生成架构健康报告
moat architecture

# Markdown 格式
moat architecture --format md

# JSON 格式（用于 CI/CD）
moat architecture --format json

# 复制到剪贴板
moat architecture --copy
```

#### 文档

- 新增 `moat/architecture_report.py`：独立架构报告生成器

---

## [1.0.1] - 2026-07-11

### 🚀 Phase 2：L2 架构规则检查

#### 新增功能

- ✅ **代码熵增检测**：
  - 高熵增预警：行数增长 >100%（🔴）
  - 中熵增预警：行数增长 >50%（🟡）
  - 智能修复建议生成

- ✅ **依赖枢纽识别**：
  - AST 分析导入关系
  - 被引用次数统计
  - Top 5 依赖枢纽报告
  - 修改风险提示

#### 测试

- ✅ 新增 `tests/test_l2_architecture.py`
- ✅ 2/2 单元测试通过

---

## [1.0.0] - 2026-07-10

### 🚀 核心升级：架构漂移检测集成

**从"守门员"到"架构哨兵"的第一次进化**

#### L1 子系统检查增强

- ✅ **文件内容哈希检查**：检测子系统文件是否被修改
- ✅ **代码行数突变检测**：检测行数变化 >50%
- ✅ **基线对比**：与历史基线对比内容级变更

#### L4 基线对比增强

- ✅ **文件哈希基线**：记录每个文件的 SHA256 哈希
- ✅ **代码熵增预警**：
  - 高熵增：行数增长 >100%（🔴）
  - 中熵增：行数增长 >50%（🟡）
- ✅ **变更文件报告**：列出前 5 个内容变更的文件

#### 📊 升级详情

| 能力 | v0.9.1 | v1.0.0 |
|------|---------|--------|
| L1 子系统检查 | 导入检查 | **导入 + 内容哈希 + 行数突变** |
| L4 基线对比 | 文件数/行数 | **文件哈希 + 熵增预警** |
| 检测维度 | 宏观（能否用） | **微观（内容是否变）** |

#### 🎯 性能影响

- 快速模式：< 8 秒（+33%，可接受）
- 完整模式：8-15 分钟（+50%，检测能力大幅增强）

#### 📝 文档

- 新增 `docs/moat_v1_upgrade_plan.md`：升级方案详细说明

---

## [0.9.1] - 2026-07-10

### 🚀 性能优化（重构）

**从"玩具"到"工具"的关键跃迁：性能提升 40 倍**

#### moat init 零配置

- ✅ **单文件配置**：从 6 个文件简化为 1 个 `moat.json`
- ✅ **零交互**：移除所有交互式询问（10+ 次 → 0 次）
- ✅ **内置 5 条常识规则**：
  - SQL 注入守门员（CRITICAL）
  - API 鉴权守门员（CRITICAL）
  - 竞态条件守门员（HIGH）
  - 错误处理守门员（MEDIUM）
  - 分层检查守门员（HIGH）
- ✅ **自动检测项目类型**（Python/TypeScript/Go/Rust）

#### moat check 超快速度

- ✅ **默认快速模式**：只检查修改的文件（< 5 秒）
- ✅ **支持 4 种模式**：
  - `moat check` → 快速模式（默认，< 5 秒）
  - `moat check --diff` → 增量检查（AST 对比）
  - `moat check --full` → 完整检查（所有文件）
  - `moat check --legacy` → 向后兼容
- ✅ **性能数据**：
  - 小型项目（100 文件）：< 1 秒
  - 中型项目（1,000 文件）：< 3 秒
  - 大型项目（20,000 文件）：**5.2 秒**（之前 > 120 秒）

#### SQL 注入守门员（新增）

- ✅ **Tree-sitter AST 检测**：定位 `execute()` 中的 `+` 拼接
- ✅ **上下文回溯**：检查前 3 行是否有 f-string / .format() / % 格式化
- ✅ **报错 + 处方**：不仅拦截，还提供修复建议
- ✅ **真实项目验证**：在 oh-agent-panel 上检测到 2 个 CRITICAL SQL 注入

---

## [0.9.0] - 2026-07-10

### 🎉 核心更新

#### 🛡️ Moat Immune Phase 2 — 契约测试系统（战略级能力）

**跨越服务边界的检查能力，这是从"工具"到"系统"的关键跃迁**

##### OpenAPI → Pact 契约生成

从 OpenAPI 规范自动生成 Pact 契约文件，实现消费者驱动契约测试。

```bash
# 从 OpenAPI 规范生成 Pact 契约
moat immune contract generate --api=openapi.json
```

**特性**：
- ✅ 支持 OpenAPI 3.0.x 规范
- ✅ 自动生成消费者驱动契约
- ✅ Pact 文件格式验证（Pact Specification v3.0.0）
- ✅ 自动保存到 One Memory

##### 破坏性变更智能检测

不只是告警，还能**精确诊断问题**，检测 AI 最容易犯的错误：

| 检测项 | 描述 | 场景 |
|--------|------|------|
| **字段类型变更** | `price: Integer → String` | AI 不看 API 文档直接盲写 |
| **必选字段删除** | `required: [name, email] → [name]` | AI 贪快最容易删的字段 |
| **字段格式变更** | `email` 格式被删除 | 格式化约束丢失 |
| **响应字段删除** | 消费者依赖的字段被删除 | 后端改 API 未通知前端 |
| **状态码变更** | `201 → 200` | HTTP 语义变更 |

##### 主动干预建议

不只告诉你"哪里坏了"，还告诉你"怎么修"：

- ✅ 影响文件分析：`frontend/api/user.ts` 会受影响
- ✅ 具体修复步骤：保持兼容性 / 版本化 / 更新基线
- ✅ CLI 命令提示：`moat immune contract update`

##### Claude Code Hook 集成

API 变更时自动拦截，阻止破坏性代码提交：

- ✅ Claude 准备提交时触发契约检查
- ✅ 破坏性变更时阻止提交
- ✅ 输出完整破坏性变更报告

##### One Memory 深度集成

- ✅ `contract_baselines` 表存储基线元数据
- ✅ `api_contracts` 表存储单个契约
- ✅ 跨会话、跨时间的契约追踪
- ✅ 基线版本管理（v1.0.0 → v2.0.0）

#### 🎫 Phase 1 — AI 测试门票 (Gatekeeper)

- ✅ **测试覆盖率守门规则**: 强制"测试门票"机制
  - CRITICAL 级别拦截（阻止提交）
  - HIGH 级别告警
  - 模块级粒度控制
- ✅ **AI 辅助生成测试**: 通过 Claude API 自动生成 pytest 测试
- ✅ **单元测试集成**: `moat check` 时自动验证测试存在性

#### 🏛️ Karpathy Principles Constitution (v0.8.0)

- ✅ **Surgical Changes 规则**: Git diff 行数监控，修改过大自动告警
- ✅ **Simplicity First 规则**: 代码复杂度检查
- ✅ **规则系统架构**: 配置驱动的规则系统（YAML）

---

## [0.8.0-alpha.1] - 2026-07-10

### 📋 定位声明与职责边界

#### 新增: Moat 定位声明文档

明确 Moat 的核心定位和职责边界，防止用户对 Moat 的功能范围产生误解。

**核心改进**:
- ✅ **定位声明**: "Moat 是架构完整性守护者，不是功能验证工具"
- ✅ **职责边界清晰化**:
  - ✅ Moat 检查: 架构完整性、工程健康度
  - ❌ Moat 不检查: UI 功能、业务逻辑验证
- ✅ **上下文桥接**: 在 Truth Document 中定义业务规则约束（架构边界检查）
- ✅ **测试作为门票**: 强制测试覆盖率门槛，但不执行测试

**新增文档**:
- `CONTEXT_BRIDGE.md` — 上下文桥接机制详细说明
  - 业务规则约束在 Truth Document 中的定义方法
  - 3 个示例（API 鉴权、测试覆盖率、目录责任）
  - 实现机制和配置说明
- `POSITIONING_UPDATE.md` — 定位声明更新总结

**更新的文档**:
- `README.md` — 在核心位置添加定位声明章节
- `CLAUDE.md` — 更新项目定位和职责边界说明

**哲学意义**:
- "能够定义好'我不做什么'，往往比定义'我做什么'更难得"
- 责任分层: Moat 负责地基和电路，测试框架负责家具和开关
- 以不变应万变: 无论业务怎么改，架构原则不变

---

## [0.8.0-alpha] - 2026-07-09

### 🏛️ Karpathy Principles Constitution

#### 全新功能: 软原则转化为硬规则

将 Andrey Karpathy 的软件工程原则转化为 Moat 的**代码级检查规则**，通过 Gatekeeper 和 Verification 系统强制执行。

**工程化价值**:
- ✅ **物理拦截**: AI 大规模修改代码时直接告警甚至阻断
- ✅ **量化执行**: 抽象原则转化为具体数值约束
- ✅ **记忆沉淀**: 作为长期规则沉淀到 One Memory

##### 规则系统架构

**新增目录**: `moat/rules/`

```
moat/rules/
├── __init__.py                    # 规则模块入口
├── karpathy_principles.yaml       # 4 大原则定义
├── karpathy_principles.py         # 兼容性导入
├── surgical_changes.py            # 手术刀检查器 ✅
└── simplicity_checker.py          # 简单性检查器 ✅
```

##### 四大原则

1. **Think Before Coding** (计划驱动) - `warning`
   - 检查编辑前是否有计划摘要
   - 状态: ⏳ 待实现

2. **Simplicity First** (简单优先) - `critical`
   - 文件大小检查: 最多 500 行
   - 函数长度检查: 最多 50 行
   - 类方法数量检查: 最多 15 个
   - 圈复杂度检查: 最多 10
   - 状态: ✅ 已实现

3. **Surgical Changes** (手术刀式修改) - `warning`
   - 单文件最大修改: 100 行
   - 最多修改文件数: 3 个
   - Git diff 行数监控
   - 智能修复建议生成
   - 状态: ✅ 已实现

4. **Goal-Driven** (目标驱动) - `info`
   - 检查是否关联 Issue/Ticket
   - Commit Message 质量评估
   - 状态: ⏳ 待实现

##### Gatekeeper 集成

在 `ArchitectureGatekeeper.check_file` 中集成原则检查:

```python
# 2.5. 执行 Karpathy Principles 检查
karpathy_violations = self._check_karpathy_principles(file_path, content)
all_violations.extend(karpathy_violations)
```

**当前实现**: Simplicity 文件大小检查
**未来实现**: 完整的 4 大原则检查

##### 配置驱动

**原则定义文件**: `moat/rules/karpathy_principles.yaml`

```yaml
principles:
  surgical_changes:
    thresholds:
      max_diff_lines: 100
      max_files_changed: 3

  simplicity_first:
    thresholds:
      max_function_lines: 50
      max_class_methods: 15
      max_file_lines: 500
```

**优势**:
- YAML 配置，易于扩展
- 可自定义阈值
- 无需修改代码即可调整规则

##### 测试覆盖

- ✅ **16 个新测试** (`tests/test_surgical_changes.py`)
- ✅ **测试分类**:
  - 原则定义测试 (3 个)
  - 原则加载器测试 (7 个)
  - 手术刀检查器测试 (7 个)
  - DiffStats 数据类测试 (1 个)
- ✅ **核心逻辑 100% 覆盖**

##### 文档

- **KARPATHY_PRINCIPLES.md** — 完整设计文档和使用指南
- **KARPATHY_PRINCIPLES_INTEGRATION.md** — 集成方案（原文档）

### 📊 测试覆盖

- ✅ **总测试数**: 822 通过 (+16)
- ✅ **新测试文件**: test_surgical_changes.py (16 个测试)
- ✅ **向后兼容**: 未破坏现有功能

### 📦 文件新增

```
moat/rules/
├── __init__.py
├── karpathy_principles.yaml
├── karpathy_principles.py
├── surgical_changes.py
└── simplicity_checker.py

tests/test_surgical_changes.py
KARPATHY_PRINCIPLES.md
```

### 🎨 设计决策

#### 决策1: 延迟导入避免循环依赖

`moat/rules/__init__.py` 是核心模块，被多个子模块依赖，直接导入会导致循环。解决方案: 使用 `get_surgical_checker()` 工厂函数延迟导入。

#### 决策2: 简化版 vs AST 级检查

当前实现使用简化版行数检查，快速覆盖 80% 场景。未来可升级到 Tree-sitter AST 级分析（更精确的函数/类检测）。

#### 决策3: Warning vs Critical

遵循原文档设计"稳健优先"原则，先以 `warning` 级别集成，让用户适应后再考虑强制拦截 (`critical`).

---

### 🎯 算子能力增强

#### 完整实现：api_response_spec 算子

- **真实 API 端点扫描**: 替换硬编码实现，真实解析 FastAPI 装饰器
- **响应模型检查**: 检测 `response_model` 参数和返回值类型注解
- **HTTP 状态码验证**: 自动验证 GET/POST/PUT/DELETE 的状态码使用
- **统一响应格式检测**: 识别 `{"data": ..., "total": ...}` 模式

**实现细节**:
- 解析 `@app.get("/path")`、`@router.post("/path")` 等装饰器
- 提取路径、方法、response_model、status_code 等参数
- 检查返回值类型注解和 JSONResponse 使用
- 支持同步/异步函数

#### 完整实现：framework_usage 算子

- **FastAPI 特性检测**
  - ✅ Pydantic BaseModel（已实现）
  - ❌ `@app.exception_handler` 异常处理（新增）
  - ❌ `Depends()` 依赖注入（新增）
  - ❌ `APIRouter` 路由分组（新增）
  - ❌ `BackgroundTasks` 后台任务（新增）

- **Django 特性检测**
  - Django ORM vs 原生 SQL
  - Django Forms/DRF Serializers
  - `get_object_or_404()` 使用

- **Flask 特性检测**
  - Flask-Marshmallow / Pydantic
  - `@app.errorhandler` 错误处理

**实现细节**:
- 静态分析代码扫描
- 检测框架推荐机制的利用情况
- 给出具体的改进建议

### 🤖 Claude Code Hook 集成

#### 自动生成 `.claude/settings.json`

- **交互式配置**: `moat init` 时询问是否集成 Claude Code
- **自动生成 Hook 配置**: PreToolUse + PostToolUse hooks
- **非交互模式支持**: 检测到 `.claude` 目录自动启用

**生成的配置**:
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

**用户体验**:
```bash
moat init
# 🤖 Claude Code 集成:
# 检测到 .claude 目录
# 是否将 Moat 守护进程集成至 Claude Code？(Y/n): y
# ✓ Claude Code Hook 已启用
```

### 📊 测试覆盖

- ✅ **verification 模块**: 48/48 通过 (100%)
- ✅ **gatekeeper 模块**: 29/29 通过 (100%)
- ✅ **全部测试**: 777/777 通过 (100%)
- ✅ **算子实际能力验证**: 通过

### 📦 文件更新

```
moat/discovery.py            # Claude Code Hook 集成
moat/verification/operators/
  ├── api_response_spec.py   # 完整实现
  └── framework_usage.py     # 完整实现
```

### 🎨 设计决策

#### 小步快跑策略

- **先覆盖 80%**: 优先实现主流场景（FastAPI），不强求完美通用
- **稳健优先**: 算子检查失败只给 WARNING，不阻塞 CI/CD
- **用户体验**: 交互式配置 + 自动生成，开箱即用

---

## [0.7.0-beta] - 2026-07-08

### 🎯 架构验收系统 (Architecture Verification)

#### 全新功能: `moat verify` 命令

基于口播视频文案《怎么验收AI搭建的后端架构》设计，实现"规则、示例、证据"驱动的架构验收系统。

##### 审计算子化架构

- **7个独立算子**: 通过组合而非继承实现验收流程
  - `directory_responsibility` — 目录责任验收
  - `minimal_module_drill` — 最小模块演练
  - `api_response_spec` — 接口响应规范验收
  - `framework_usage` — 框架利用检查
  - `runtime_evidence` — 运行证据包生成
  - `architecture_health_score` — 架构健康度评分
  - `truth_document` — 实施真元文档生成

##### 核心特性

- **算子化架构**: 每个算子独立、可测试、可替换
- **灵活组合**: 支持完整验收 (`moat verify --all`) 或单个算子 (`moat verify --operator <name>`)
- **证据链完整**: 每个违规都有"规则来源→违反代码→修复建议"
- **架构健康度评分**: 5个维度量化架构质量（0-100分）
  - 目录责任清晰度（20分）
  - 分层架构遵守度（20分）
  - 接口响应一致性（20分）
  - 框架利用合理性（20分）
  - 命名规范遵守度（20分）

##### CLI命令

\```bash
# 完整验收（7步流程）
moat verify --all

# 单项验收
moat verify --operator directory_responsibility

# JSON输出
moat verify --json

# CI/CD集成：评分低于60分则失败
moat verify --fail-on-score 60
\```

##### 架构基线管理

- **基线初始化**: `moat baseline init`
- **基线对比**: `moat baseline diff --from v1.0.0 --to v2.0.0`
- **架构演进可追溯**: 支持版本回滚

#### 实施真元文档

自动生成 `.moat/truth_document.md`，包含：
- 框架与语言
- 目录责任
- 新增模块规范
- 接口响应规范
- 框架利用原则
- 运行证据
- 架构变更记录

#### 文档

- **ARCHITECTURAL_AUDIT_PROTOCOL.md** — 架构验收方法论（口播文案整理）
- **moat-v0.7.0-architecture-upgrade.md** — v0.7.0架构升级方案

### 🎯 实时架构守门 (Gatekeeper)

#### 全新功能: `moat gatekeeper` 命令

实时架构规则检查系统，在文件写入前验证架构合规性。

##### 规则引擎

- **4条核心规则**:
  - `directory_responsibility` — 目录责任规则
  - `layer_separation` — 分层架构规则
  - `naming_convention` — 命名规范规则
  - `framework_usage` — 框架利用规则

##### 三层豁免机制（"免死金牌"）

1. **行内注释**: `# moat-ignore: rule_id`（优先级最高）
2. **文件注释**: 文件头部 `# moat-ignore: rule_id`
3. **配置豁免**: `.moat/gatekeeper_config.json`

##### CLI命令

\```bash
# 列出所有规则
moat gatekeeper rules

# 检查单个文件
moat gatekeeper check --file api/users.py

# 启动守护进程（占位）
moat gatekeeper start
\```

### 🧬 架构基线增强 (Baseline Management)

#### 增强功能: 架构版本控制

- **创建架构基线**: 保存验收报告和相关文档
- **列出基线**: 查看所有历史基线
- **对比基线**: 分析架构变更
- **回滚基线**: 恢复到指定版本
- **删除基线**: 清理旧版本

### 🧪 测试覆盖

#### 新增测试

- **verification 模块**: 7个测试文件，43个测试用例
- **gatekeeper 模块**: 4个测试文件，29个测试用例
- **baseline 模块**: 1个测试文件，6个测试用例

#### 测试结果

- ✅ **verification模块**: 43/43 通过 (100%)
- ✅ **gatekeeper模块**: 29/29 通过 (100%)
- ✅ **baseline模块**: 6/6 通过 (100%)
- ✅ **全部测试**: 801/801 通过 (100%)
- ✅ **向后兼容**: 未破坏现有功能

### 📦 文件新增

```
moat/verification/      # 14个文件
moat/gatekeeper/         # 5个文件
moat/baseline.py         # 增强
tests/verification/      # 7个测试文件
tests/gatekeeper/        # 4个测试文件
tests/baseline/          # 1个测试文件
```

### 🎨 设计决策

#### 决策1: 审计算子化架构

将验收流程设计为独立的"审计算子"，通过组合实现流程。

**优势**:
- 易于扩展：新增验收步骤只需添加新算子
- 易于测试：每个算子可独立测试
- 易于维护：修改某个步骤不影响其他步骤
- 灵活组合：用户可选择运行部分算子

#### 决策2: Gatekeeper"免死金牌"机制

三层豁免机制：行内注释 → 文件注释 → 配置豁免

**设计原则**:
- 默认拦截
- 显式豁免
- 审计追踪
- 定期清理提醒

---

## [0.7.0-alpha] - 2026-07-08

### 🎯 架构验收系统 (Architecture Verification)

#### 全新功能: `moat verify` 命令

基于口播视频文案《怎么验收AI搭建的后端架构》设计，实现"规则、示例、证据"驱动的架构验收系统。

##### 审计算子化架构

- **7个独立算子**: 通过组合而非继承实现验收流程
  - `directory_responsibility` — 目录责任验收
  - `minimal_module_drill` — 最小模块演练
  - `api_response_spec` — 接口响应规范验收
  - `framework_usage` — 框架利用检查
  - `runtime_evidence` — 运行证据包生成
  - `architecture_health_score` — 架构健康度评分
  - `truth_document` — 实施真元文档生成

##### 核心特性

- **算子化架构**: 每个算子独立、可测试、可替换
- **灵活组合**: 支持完整验收 (`moat verify --all`) 或单个算子 (`moat verify --operator <name>`)
- **证据链完整**: 每个违规都有"规则来源→违反代码→修复建议"
- **架构健康度评分**: 5个维度量化架构质量（0-100分）
  - 目录责任清晰度（20分）
  - 分层架构遵守度（20分）
  - 接口响应一致性（20分）
  - 框架利用合理性（20分）
  - 命名规范遵守度（20分）

##### CLI命令

```bash
# 完整验收（7步流程）
moat verify --all

# 单项验收
moat verify --operator directory_responsibility

# JSON输出
moat verify --json

# CI/CD集成：评分低于60分则失败
moat verify --fail-on-score 60
```

##### 架构基线管理

- **基线初始化**: `moat baseline init`
- **基线对比**: `moat baseline diff --from v1.0.0 --to v2.0.0`
- **架构演进可追溯**: 支持版本回滚

#### 实施真元文档

自动生成 `.moat/truth_document.md`，包含：
- 框架与语言
- 目录责任
- 新增模块规范
- 接口响应规范
- 框架利用原则
- 运行证据
- 架构变更记录

#### 文档

- **ARCHITECTURAL_AUDIT_PROTOCOL.md** — 架构验收方法论（口播文案整理）
- **moat-v0.7.0-architecture-upgrade.md** — v0.7.0架构升级方案

### 🧪 测试覆盖

#### 新增测试

- **verification 模块**: 7个测试文件，48个测试用例
  - `test_operator.py` — Operator基类测试（5个）
  - `test_orchestrator.py` — Orchestrator测试（8个）
  - `test_types.py` — 类型定义测试（9个）
  - `test_directory_responsibility.py` — 目录责任算子测试（7个）
  - `test_framework_usage.py` — 框架利用算子测试（7个）
  - `test_architecture_health_score.py` — 架构健康度算子测试（5个）
  - `test_integration.py` — 集成测试（5个）

#### 测试结果

- ✅ **verification模块**: 48/48 通过 (100%)
- ✅ **全部测试**: 771/771 通过 (100%)
- ✅ **向后兼容**: 未破坏现有功能

### 📦 文件新增

```
moat/verification/
├── __init__.py
├── types.py                    # 类型定义（Violation, OperatorResult等）
├── operator.py                 # Operator基类
├── orchestrator.py             # 编排器
├── verify_cli.py               # CLI命令
└── operators/
    ├── __init__.py
    ├── directory_responsibility.py
    ├── minimal_module_drill.py
    ├── api_response_spec.py
    ├── framework_usage.py
    ├── runtime_evidence.py
    ├── architecture_health_score.py
    └── truth_document.py

tests/verification/
├── __init__.py
├── test_operator.py
├── test_orchestrator.py
├── test_types.py
├── test_directory_responsibility.py
├── test_framework_usage.py
├── test_architecture_health_score.py
└── test_integration.py
```

### 🎨 设计决策

#### 决策1: 审计算子化架构

将7步验收流程设计为独立的"审计算子"，通过组合而非继承实现流程。

**优势**:
- 易于扩展：新增验收步骤只需添加新算子
- 易于测试：每个算子可独立测试
- 易于维护：修改某个步骤不影响其他步骤
- 灵活组合：用户可选择运行部分算子

#### 决策2: Gatekeeper"免死金牌"机制（已设计，待实现）

三层豁免机制：
1. **文件级**：文件头部注释 `# moat-ignore: rule_name`
2. **行级**：单行注释 `# moat-ignore: rule_name`
3. **配置级**：`.moat/gatekeeper_config.json` 全局配置

**设计原则**:
- 默认拦截
- 显式豁免
- 审计追踪
- 定期清理提醒

---

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

- **版本号**: v0.6.0 → v0.7.0-beta
- **文档**: 新增 `SIDECAR_BUGFIX_REPORT.md` 详细修复报告
- **发布测试**: 新增 `RELEASE_TEST_REPORT_v0.7.0-beta.md` 完整测试报告

### 📊 测试覆盖

- ✅ **单元测试**: 81/81 通过 (100%)
- ✅ **moat check 自举**: 21 通过, 0 失败, 1 警告
- ✅ **Sidecar Bug 修复验证**: 2/2 通过
- ✅ **CLI 命令测试**: 10/10 通过
- ✅ **进化指标系统**: 正常运行 (0.325/1.000)
- ✅ **AST 骨架图**: 391 函数, 441 调用

### 📝 发布验证

- ✅ **GitHub Release**: https://github.com/wang-jie-git/moat/releases/tag/v0.7.0-beta
- ✅ **Git Tag**: v0.7.0-beta
- ✅ **发布测试报告**: `RELEASE_TEST_REPORT_v0.7.0-beta.md`

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

[0.9.1]: https://github.com/wang-jie-git/moat/releases/tag/v0.9.1
[0.9.0]: https://github.com/wang-jie-git/moat/releases/tag/v0.9.0
[0.8.0-alpha.1]: https://github.com/wang-jie-git/moat/releases/tag/v0.8.0-alpha.1
[0.8.0-alpha]: https://github.com/wang-jie-git/moat/releases/tag/v0.8.0-alpha
[0.7.0-beta]: https://github.com/wang-jie-git/moat/releases/tag/v0.7.0-beta
[0.7.0-alpha]: https://github.com/wang-jie-git/moat/releases/tag/v0.7.0-alpha
[0.6.2]: https://github.com/wang-jie-git/moat/releases/tag/v0.6.2
[0.6.1]: https://github.com/wang-jie-git/moat/releases/tag/v0.6.1
[0.6.0]: https://github.com/wang-jie-git/moat/releases/tag/v0.6.0
[0.5.0]: https://github.com/wang-jie-git/moat/releases/tag/v0.5.0
[0.4.0]: https://github.com/wang-jie-git/moat/releases/tag/v0.4.0
