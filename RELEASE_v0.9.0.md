# Moat v0.9.0 发布说明

**发布日期**: 2026-07-10
**版本**: v0.9.0 (Stable)
**关键词**: 契约测试系统 + AI 工程化测试体系 + Claude Code Hook

---

## 🎉 核心更新

### 🛡️ Moat Immune Phase 2 — 契约测试系统（战略级能力）

**跨越服务边界的检查能力，这是从"工具"到"系统"的关键跃迁**

#### OpenAPI → Pact 契约生成

从 OpenAPI 规范自动生成 Pact 契约文件，实现消费者驱动契约测试。

```bash
# 从 OpenAPI 规范生成 Pact 契约
moat immune contract generate --api=openapi.json

# 自动生成文件
tests/integration/contracts/get_api_users.json
tests/integration/contracts/post_api_users.json
```

**特性**：
- ✅ 支持 OpenAPI 3.0.x 规范
- ✅ 自动生成消费者驱动契约
- ✅ Pact 文件格式验证（Pact Specification v3.0.0）
- ✅ 自动保存到 One Memory

#### 破坏性变更智能检测

不只是告警，还能**精确诊断问题**，检测 AI 最容易犯的错误：

| 检测项 | 描述 | 场景 |
|--------|------|------|
| **字段类型变更** | `price: Integer → String` | AI 不看 API 文档直接盲写 |
| **必选字段删除** | `required: [name, email] → [name]` | AI 贪快最容易删的字段 |
| **字段格式变更** | `email` 格式被删除 | 格式化约束丢失 |
| **响应字段删除** | 消费者依赖的字段被删除 | 后端改 API 未通知前端 |
| **状态码变更** | `201 → 200` | HTTP 语义变更 |

```python
# 示例：检测字段类型变更
old = APIContract(
    request_schema={"properties": {"price": {"type": "integer"}}}
)
new = APIContract(
    request_schema={"properties": {"price": {"type": "string"}}}
)

is_breaking = storage._is_breaking_change(old, new)
# True → 检测到破坏性变更
```

#### One Memory 深度集成

契约基线作为"架构宪法"持久化存储：

- ✅ `contract_baselines` 表存储基线元数据
- ✅ `api_contracts` 表存储单个契约
- ✅ 跨会话、跨时间的契约追踪
- ✅ 基线版本管理（v1.0.0 → v2.0.0）

```python
# 保存基线
storage.save_baseline(baseline)

# 加载基线
loaded = storage.load_baseline("user-service")

# 检测变更
changes = storage.detect_changes("user-service", new_contracts)
# [
#   {"type": "breaking", "endpoint": "/api/users", "method": "POST", ...},
#   {"type": "modified", "endpoint": "/api/users/{id}", "method": "GET", ...}
# ]
```

#### 主动干预建议

不只告诉你"哪里坏了"，还告诉你"怎么修"：

```
检测到破坏性变更: POST /api/products

字段类型变更 [price]: integer → string
删除必选字段: email

这会影响以下文件:
  - frontend/api/product.ts
  - backend/tests/test_products.py

建议:
  1. 字段类型变更修复建议:
     - 保持类型一致，恢复原来的类型
     - 如果确实需要变更，考虑版本化：/v2/api/products

  2. 必选字段删除修复建议:
     - 恢复必选字段（保持向后兼容）
     - 如果确实不需要，请先标记为 optional
     - 更新前端代码并通知所有依赖方

如果确认变更正确，请运行：
  $ moat immune contract update
```

#### Claude Code Hook 集成

API 变更时自动拦截，阻止破坏性代码提交：

```python
# Claude 准备提交 API 代码时
# 1. 触发 moat immune contract check
# 2. 检测到破坏性变更
# 3. Hook 阻止提交
# 4. 输出完整破坏性变更报告
```

**CLI 命令**：

```bash
# 初始化契约基线
moat immune contract init

# 检查契约变更
moat immune contract check

# 从 OpenAPI 规范生成 Pact 契约
moat immune contract generate --api=openapi.json

# 更新基线（确认变更正确后）
moat immune contract update
```

### 🎫 Phase 1 — AI 测试门票 (Gatekeeper)

**测试覆盖率守门规则，强制"测试门票"机制**

- ✅ **CRITICAL 级别拦截**: 阻止无测试的业务代码提交
- ✅ **HIGH 级别告警**: 提示测试覆盖率不足
- ✅ **模块级粒度控制**: 不同模块可配置不同阈值
- ✅ **AI 辅助生成测试**: 通过 Claude API 自动生成 pytest 测试
- ✅ **单元测试集成**: `moat check` 时自动验证测试存在性

```bash
# 运行检查（包含测试门票验证）
moat check

# 输出示例
❌ CRITICAL: [测试门票] services/payment.py 缺少单元测试
   → services/payment.py 必须有对应的 tests/services/test_payment.py
```

### 🏛️ Karpathy Principles Constitution (v0.8.0)

- ✅ **Surgical Changes 规则**: Git diff 行数监控，修改过大自动告警
  - 单文件最大修改: 100 行
  - 最多修改文件数: 3 个
- ✅ **Simplicity First 规则**: 代码复杂度检查
  - 文件大小检查: 500 行
  - 函数长度检查: 50 行
  - 类方法数量检查: 15 个
- ✅ **规则系统架构**: 配置驱动的规则系统（YAML）

---

## 📊 测试覆盖

### v0.9.0 新增测试

- ✅ **20 个集成测试**: `tests/integration/test_contract_full_integration.py`
  - OpenAPI → Contract 生成
  - Pact 文件生成和格式验证
  - 破坏性变更检测（5 种场景）
  - One Memory 存储和加载
  - Claude Code Hook 集成
  - 主动干预建议
  - 端到端集成测试

- ✅ **增强 `_is_breaking_change()`**: 检测字段类型变更、必选字段删除
- ✅ **新增 `_detect_schema_diffs()`**: 精确诊断差异
- ✅ **新增 `_generate_fix_suggestions()`**: 主动干预建议
- ✅ **One Memory 新增表**: `contract_baselines` 和 `api_contracts`
- ✅ **新增 Bridge 方法**: `store_contract_baseline()`, `query_contract_baseline()`, `store_api_contract()`, `query_api_contracts()`

---

## 🔧 技术细节

### 新增文件

```
moat/
├── tests/
│   ├── fixtures/
│   │   └── mock_openapi_specs/
│   │       ├── complete_openapi.json  # 基线版本（8 个端点）
│   │       └── broken_contract.json   # AI 错误样本（含字段类型变更 + 必选字段删除）
│   └── integration/
│       └── test_contract_full_integration.py  # 完整集成测试（20 个测试）
└── moat/
    ├── immune/
    │   └── contract/
    │       ├── contracts.py  # 增强破坏性变更检测 + 主动干预建议
    │       └── cli.py  # CLI 命令
    └── memory/
        └── bridge.py  # 新增契约表和方法
```

### 增强的核心功能

#### 1. 破坏性变更检测增强

**之前**：只检查字段名称

**现在**：检查字段名称、类型、格式、required 标记

```python
def _is_breaking_change(self, old: APIContract, new: APIContract) -> bool:
    """判断是否破坏性变更

    检查项：
    1. 响应状态码变更
    2. 请求字段删除（包括 required 字段）
    3. 响应字段删除
    4. 字段类型变更（AI 最容易犯的错误）
    5. 字段格式变更（如 email → text）
    """
```

#### 2. 主动干预建议

```python
def _generate_fix_suggestions(change: dict[str, Any]) -> list[str]:
    """生成修复建议"""
```

输出包含：
- 问题描述
- 影响文件分析
- 具体修复步骤
- CLI 命令提示

#### 3. One Memory 契约表

```sql
-- 契约基线表
CREATE TABLE contract_baselines (
    id TEXT PRIMARY KEY,
    service_name TEXT NOT NULL,
    version TEXT NOT NULL,
    baseline_hash TEXT NOT NULL,
    contract_count INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(service_name, version)
);

-- API 契约表
CREATE TABLE api_contracts (
    id TEXT PRIMARY KEY,
    service_name TEXT NOT NULL,
    version TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    contract_hash TEXT NOT NULL,
    request_schema TEXT,
    response_schema TEXT,
    status_code INTEGER,
    description TEXT,
    is_breaking BOOLEAN DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    last_modified TIMESTAMP,
    FOREIGN KEY (service_name, version) REFERENCES contract_baselines(service_name, version)
);
```

---

## 🚀 升级指南

### 从 v0.8.0 升级

```bash
# 1. 更新到最新版
pip install --upgrade moat-ai

# 2. 重新初始化（可选，升级契约表）
moat init

# 3. 验证安装
python3 -m moat --version
# 输出: 0.9.0
```

### 新增依赖

无新增依赖，v0.9.0 完全向后兼容。

---

## 📚 使用场景

### 场景 1: 初始化契约基线

```bash
# 1. 从 OpenAPI 规范生成契约
moat immune contract generate --api=openapi.json

# 2. 契约自动保存到 One Memory
✅ 契约基线已保存

# 3. 同时生成 Pact 文件
✅ tests/integration/contracts/get_api_users.json
✅ tests/integration/contracts/post_api_users.json
```

### 场景 2: 检测 API 变更

```python
# 1. 加载旧基线
old_baseline = storage.load_baseline("user-service")

# 2. 解析新 API 规范
new_contracts = generator.from_openapi(new_openapi_spec)

# 3. 检测变更
changes = storage.detect_changes("user-service", new_contracts)

# 4. 输出
for change in changes:
    if change["is_breaking"]:
        print(f"❌ 破坏性变更: {change['method']} {change['endpoint']}")
    else:
        print(f"✅ 非破坏性变更: {change['method']} {change['endpoint']}")
```

### 场景 3: Claude Code Hook 集成

```python
# Claude 修改 API 时，自动触发

# 1. Moat Gatekeeper 检测到 API 文件变更
# 2. 触发契约检查
changes = storage.detect_changes(service_name, new_contracts)

# 3. 如果有破坏性变更，阻止提交
if any(c["is_breaking"] for c in changes):
    print("❌ 检测到破坏性 API 变更！")
    print("   - 违反了上次和前端的契约约定")
    print("   - 请更新契约并通知消费者")
    sys.exit(1)  # 阻止提交
```

---

## 🎯 战略价值

### 为什么契约测试能拉开差距？

**Lint 工具只能看本地文件，但契约测试能跨越服务边界。**

```
传统 Lint 工具:
代码 → 检查语法 → 通过/失败

Moat Immune 契约测试:
API A → 契约基线 → API B 变更检测 → "你违反了这个契约！"
```

**这就是从"工具"到"系统"的关键跃迁。**

### AI 隐蔽错误检测能力

| 错误类型 | AI 犯错误原因 | Moat 检测能力 |
|---------|-------------|-------------|
| **字段类型变更** | AI 不看 API 文档直接盲写 | ✅ 精确检测 + 修复建议 |
| **必选字段删除** | AI 贪快最容易删的字段 | ✅ 精确检测 + 影响分析 |
| **字段格式变更** | AI 忽略格式化约束 | ✅ 精确检测 + 修复建议 |
| **响应字段删除** | AI 只关注功能实现 | ✅ 精确检测 + 消费者影响分析 |

---

## 📈 统计数据

- **新增代码**: ~1200 行
- **新增测试**: 20 个集成测试（100% 通过）
- **新增 CLI 命令**: 4 个（`moat immune contract {init,check,generate,update}`）
- **新增 One Memory 表**: 2 个（`contract_baselines`, `api_contracts`）
- **新增 Bridge 方法**: 4 个（存储和查询契约）

---

## 🐛 Bug 修复

- ✅ **字段类型变更检测**: `_is_breaking_change()` 现在检查字段类型和格式
- ✅ **必选字段删除检测**: 增强 `required` 字段对比
- ✅ **One Memory 集成**: 修复 `store_node` 和 `query_nodes` 方法不存在的问题

---

## 📝 贡献者

- **作者**: One Team
- **核心贡献**: wangjiezhong

---

## 🔗 相关链接

- **PyPI**: https://pypi.org/project/moat-ai/
- **GitHub**: https://github.com/wang-jie-git/moat
- **文档**: https://github.com/wang-jie-git/moat/blob/main/README.md
- **更新日志**: https://github.com/wang-jie-git/moat/blob/main/CHANGELOG.md

---

**Moat v0.9.0 — 从"工具"到"系统"的跃迁** 🚀
