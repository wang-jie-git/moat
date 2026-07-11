# Moat v1.0.8 开发计划

> **版本**: v1.0.8
> **目标**: 增强守门员规则 + 性能优化 + 体验改进
> **时间**: 2026-07-11

---

## 🎯 v1.0.8 目标

### 核心主题：**精准拦截 + 性能飞跃**

v1.0.7 建立了"不打扰"的基础设施（Fail-open、规则解释、误报率统计）。
v1.0.8 的目标是**在这之上提升拦截精度和性能**。

---

## 📋 功能清单

### 1️⃣ 新的守门员规则

#### 1.1 硬编码密钥检测（SECRETS-001）🆕

**优先级**: P0（安全相关）
**严重性**: CRITICAL

**检测模式**：
- AWS Access Key ID
- GitHub Token
- API Key 硬编码
- 密码明文
- Private Key 泄漏

**实现思路**：
```python
# 使用正则 + 上下文分析
patterns = {
    "aws_key": r'AKIA[0-9A-Z]{16}',
    "github_token": r'ghp_[0-9a-zA-Z]{36}',
    "generic_api_key": r'api[_-]?key["\s:]+["\']([a-zA-Z0-9_\-]+)["\']',
}

# 排除 false positive：
# - 测试文件（test_*.py, *.test.ts）
# - 示例文件（example*, demo*）
# - 环境变量读取（os.getenv, process.env）
```

**文件**: `moat/checks/secrets.py`（新建）

---

#### 1.2 依赖项安全漏洞检测（DEPS-001）🆕

**优先级**: P1
**严重性**: HIGH

**检测模式**：
- Python：检查 `requirements.txt`、`pyproject.toml`
- Node.js：检查 `package.json`
- 使用本地漏洞数据库或在线 API（如 GitHub Advisory）

**实现思路**：
- 使用 `pip-audit` 或 `safety`（可选依赖）
- 或集成 GitHub Advisory API（免费）
- 生成建议升级版本

**文件**: `moat/checks/dependency_security.py`（新建）

---

#### 1.3 未使用的导出检测（UNUSED-001）🆕

**优先级**: P2
**严重性**: LOW

**检测模式**：
- Python：未使用的 `__all__` 导出
- TypeScript/Go：未使用的导出函数/类型

**实现思路**：
- 基于 AST 分析
- 检测模块级 `__all__` 列表
- 检查是否有外部导入使用

**文件**: `moat/checks/unused_exports.py`（新建）

---

#### 1.4 增强 SQL 注入检测（SQL-002）🔧

**优先级**: P1
**严重性**: CRITICAL

**改进点**：
- 支持 ORM 框架（Django ORM, SQLAlchemy）
- 检测 `filter()` 中的字符串拼接
- 支持更多数据库驱动（asyncpg, psycopg2）

**检测模式**：
```python
# Django ORM
User.objects.raw(f"SELECT * FROM users WHERE id = {user_id}")

# SQLAlchemy
session.execute(f"SELECT * FROM users WHERE id = {user_id}")

# asyncpg
await conn.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

**文件**: `moat/checks/sql_injection.py`（增强）

---

#### 1.5 增强 API 鉴权检测（API-002）🔧

**优先级**: P2
**严重性**: HIGH

**改进点**：
- 支持 FastAPI（已有部分）
- 支持 Flask、Django REST Framework
- 支持 Express.js（TypeScript）
- 支持 Gin/Fiber（Go）

**文件**: `moat/checks/api_auth.py`（增强）

---

### 2️⃣ 性能优化

#### 2.1 缓存优化（P1）

**目标**: 将 `moat check --full` 速度提升 20%

**优化点**：
- 优化 `HashCacheManager`，添加 LRU 缓存
- 并行扫描的粒度优化（按目录分组）
- 延迟加载检查器（按需初始化）

**预期效果**：
- 大型项目（>20K 文件）：从 5s → 4s

---

#### 2.2 增量扫描改进（P2）

**目标**: `moat check --diff` 更精准

**改进点**：
- 基于 AST diff 而非 git diff
- 检测函数签名变更的影响域
- 检测导入变更的影响域

---

### 3️⃣ 体验改进

#### 3.1 更好的错误报告（P2）

**改进点**：
- 错误分组（同类错误合并显示）
- 严重性排序（CRITICAL → INFO）
- 文件维度统计（每个文件的错误数）

**示例输出**：
```
📊 错误摘要（按严重性）：
  🔴 CRITICAL: 2
  🟠 HIGH: 5
  🟡 MEDIUM: 12
  🔵 LOW: 8
```

---

#### 3.2 配置增强（P3）

**新增配置项**：
- `.moat/config.json` 支持忽略规则
- 支持项目级配置（`pyproject.toml` 或 `package.json`）
- 支持目录级配置（`.moatignore`）

---

## 🚀 实施顺序

### Phase 1：P0/P1 功能（第一天）

1. **硬编码密钥检测（SECRETS-001）**
   - 创建 `moat/checks/secrets.py`
   - 实现核心检测逻辑
   - 单元测试（15 个）

2. **增强 SQL 注入检测（SQL-002）**
   - 扩展 `moat/checks/sql_injection.py`
   - 添加 ORM 检测
   - 单元测试（+10 个）

3. **依赖项安全检测（DEPS-001）**
   - 创建 `moat/checks/dependency_security.py`
   - 集成 GitHub Advisory API
   - 单元测试（10 个）

**预期成果**：3 个新检查器，+35 测试

---

### Phase 2：P2 功能（第二天）

1. **未使用的导出检测（UNUSED-001）**
2. **增强 API 鉴权检测（API-002）**
3. **更好的错误报告**

**预期成果**：2 个新检查器，用户体验提升

---

### Phase 3：性能优化 + P3 功能（第三天）

1. **缓存优化**
2. **增量扫描改进**
3. **配置增强**

**预期成果**：性能提升 20%，配置更灵活

---

## 📊 成功指标

### 测试覆盖
- **新增测试**: +80 个
- **测试通过率**: 保持 95%+
- **覆盖率**: 保持 70%+

### 性能指标
- **moat check --quick**: < 5s（保持）
- **moat check --full**: < 8s（提升 20%）
- **moat check --diff**: < 10s（保持）

### 新规则覆盖率
- **SECRETS-001**: 检测 10+ 种密钥模式
- **DEPS-001**: 支持 3+ 种依赖管理
- **UNUSED-001**: Python + TypeScript
- **SQL-002**: 支持 3+ 种 ORM
- **API-002**: 支持 4+ 种框架

---

## 📝 待讨论

1. **GitHub Advisory API 集成**：
   - 是否需要 API Key？还是使用公开端点？
   - 离线模式如何支持？

2. **误报率问题**：
   - 硬编码密钥检测容易出现误报（测试文件、示例代码）
   - 如何设计白名单机制？

3. **性能 vs 精度**：
   - 增量扫描改进会增加复杂度
   - 是否值得？

4. **规则优先级**：
   - 是否需要重新评估所有规则的优先级？
   - SQL 注入 vs 密钥泄漏，哪个更重要？

---

## 🎯 下一步

请确认：
1. ✅ 是否按这个计划开发？
2. ✅ Phase 1-3 的顺序是否合理？
3. ✅ 是否需要调整优先级？

确认后立即开始 Phase 1！
