# 上下文桥接：业务规则约束

> **定位**: Moat 如何在不承担测试工具负担的前提下，向业务逻辑延伸一点点

## 🎯 核心原则

**我们检查架构边界，而非业务细节**

Moat 不应该检查：
- ❌ "模型列表是否显示了 22 个模型"
- ❌ "用户登录是否成功"
- ❌ "按钮点击是否有反应"

Moat 应该检查：
- ✅ "访问模型列表的 API 是否经过鉴权中间件"
- ✅ "登录逻辑是否在 `auth/` 目录下"
- ✅ "按钮点击处理器是否在 `ui/` 目录下"

## 📋 Truth Document 中的"业务规则约束"

在 `.moat/architecture_intent.md` 中定义架构边界规则：

### 示例 1: API 鉴权约束

```markdown
## 业务规则约束

### 规则 1: 所有模型列表 API 必须鉴权

**类型**: `auth_middleware_required`
**级别**: `ERROR`
**描述**: 访问 `/api/models` 和 `/api/available-models` 的 API 端点必须经过鉴权中间件

**检查逻辑**:
1. 在 `routers/models.py` 中查找所有路由
2. 检查是否应用了 `Depends(get_current_user)` 或类似的鉴权依赖
3. 如果没有，报告 ERROR

**理由**: 模型列表包含敏感信息（API Key、Base URL），不应公开暴露

**豁免条件**: 无
```

### 示例 2: 测试覆盖率门槛

```markdown
## 业务规则约束

### 规则 2: 新增服务必须包含测试

**类型**: `test_coverage_required`
**级别**: `CRITICAL`
**描述**: `services/` 目录下新增的 `.py` 文件，必须在 `tests/` 下有对应的测试文件

**检查逻辑**:
1. 扫描 `services/` 下的所有 `.py` 文件
2. 扫描 `tests/` 下的所有测试文件
3. 检查是否存在 `tests/test_<module_name>.py`
4. 如果不存在，报告 CRITICAL

**理由**: 业务逻辑必须可测试，无测试的新功能是债务

**豁免条件**:
- 文件标记为 `# moat-ignore: test_coverage_required`
- 在 `.moat/gatekeeper_config.json` 中配置豁免路径
```

### 示例 3: 目录责任约束

```markdown
## 业务规则约束

### 规则 3: 数据库模型必须在 models/ 目录下

**类型**: `directory_responsibility`
**级别**: `ERROR`
**描述**: 所有 SQLAlchemy ORM 模型类必须在 `database/models.py` 中定义

**检查逻辑**:
1. 扫描所有 `.py` 文件
2. 使用 AST 查找 `class XXX(Base):` 模式
3. 检查文件路径是否在 `database/models.py` 或 `database/*.py`
4. 如果不在，报告 ERROR

**理由**: 集中管理数据模型，避免散落各处导致维护困难

**豁免条件**: 迁移文件（alembic/versions/）
```

## 🔧 实现机制

### 1. Truth Document 加载

```python
# moat/context/truth_loader.py

def load_business_rules(project_root: Path) -> list[BusinessRule]:
    """从 .moat/architecture_intent.md 加载业务规则约束"""
    rules = []
    truth_file = project_root / ".moat" / "architecture_intent.md"

    if not truth_file.exists():
        return rules

    content = truth_file.read_text(encoding="utf-8")

    # 解析 ## 业务规则约束 部分
    for section in re.findall(
        r'### 规则 \d+: (.+?)\n\n(.+?)(?=\n###|\n##|\Z)',
        content,
        re.DOTALL
    ):
        rule_name = section[0]
        rule_body = section[1]

        # 解析规则属性
        rule_type = re.search(r'\*\*类型\*\*: `(.+?)`', rule_body).group(1)
        rule_level = re.search(r'\*\*级别\*\*: `(.+?)`', rule_body).group(1)
        rule_desc = re.search(r'\*\*描述\*\*: (.+?)(?:\n|$)', rule_body).group(1)

        rules.append(BusinessRule(
            name=rule_name,
            type=rule_type,
            level=rule_level,
            description=rule_desc,
            raw=rule_body
        ))

    return rules
```

### 2. 规则检查器

```python
# moat/rules/business_rules.py

class BusinessRuleChecker:
    """业务规则约束检查器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.rules = load_business_rules(project_root)

    async def check_all(self, changed_files: list[Path]) -> list[RuleViolation]:
        """检查所有业务规则"""
        violations = []

        for rule in self.rules:
            if rule.type == "auth_middleware_required":
                violations.extend(await self._check_auth_middleware(rule, changed_files))
            elif rule.type == "test_coverage_required":
                violations.extend(await self._check_test_coverage(rule, changed_files))
            elif rule.type == "directory_responsibility":
                violations.extend(await self._check_directory_responsibility(rule, changed_files))

        return violations

    async def _check_auth_middleware(self, rule: BusinessRule, files: list[Path]) -> list[RuleViolation]:
        """检查 API 是否鉴权"""
        violations = []
        protected_endpoints = ["/api/models", "/api/available-models"]

        for file_path in files:
            if "routers/models.py" not in str(file_path):
                continue

            # 解析路由装饰器
            tree = parse_ast(file_path)
            for route in tree.find_route_decorators():
                if route.path in protected_endpoints:
                    if not route.has_dependency("get_current_user"):
                        violations.append(RuleViolation(
                            rule=rule,
                            file=file_path,
                            line=route.lineno,
                            message=f"路由 {route.path} 未应用鉴权中间件"
                        ))

        return violations
```

### 3. Moat Check 集成

```bash
# 运行 Moat 检查时自动执行业务规则检查
moat check
# 输出:
# ✅ L1 语法检查
# ✅ L2 结构检查
# ✅ L3 关联检查
# ❌ L4 业务规则检查
#   ERROR: routers/models.py:45 - 路由 /api/models 未应用鉴权中间件 (规则: auth_middleware_required)
```

## 🎫 测试作为"门票"

### 实现机制

```python
# moat/rules/test_gate.py

class TestGateChecker:
    """测试覆盖率门槛检查器"""

    def __init__(self, project_root: Path, threshold: float = 0.6):
        self.project_root = project_root
        self.threshold = threshold

    def check_new_code(self, changed_files: list[Path]) -> list[RuleViolation]:
        """检查新增代码是否有对应测试"""
        violations = []

        for file_path in changed_files:
            if not file_path.suffix == ".py":
                continue

            # 跳过测试文件本身
            if "tests/" in str(file_path):
                continue

            # 检查是否在 services/ 目录下
            if "services/" not in str(file_path):
                continue

            # 查找对应的测试文件
            module_name = file_path.stem
            test_file = file_path.parent.parent / "tests" / f"test_{module_name}.py"

            if not test_file.exists():
                violations.append(RuleViolation(
                    rule=BusinessRule(
                        name="测试覆盖率门槛",
                        type="test_coverage_required",
                        level="CRITICAL",
                        description="新增服务代码必须包含测试"
                    ),
                    file=file_path,
                    line=1,
                    message=f"新增服务 {file_path.name} 缺少对应测试文件 (应为 tests/test_{module_name}.py)"
                ))

        return violations
```

### 配置

在 `.moat/config.json` 中添加：

```json
{
  "test_gate": {
    "enabled": true,
    "threshold": 0.6,
    "required_dirs": ["services/", "core/"],
    "exempt_patterns": ["*_mock.py", "*_fixture.py"]
  }
}
```

## 📊 效果

### 检查清单

| 检查项 | 类型 | Moat 职责 |
|--------|------|----------|
| 鉴权中间件是否应用 | 架构边界 | ✅ Moat 检查 |
| API 响应格式是否规范 | 架构规范 | ✅ Moat 检查 |
| 目录责任是否清晰 | 架构规范 | ✅ Moat 检查 |
| 测试文件是否存在 | 测试门票 | ✅ Moat 检查 |
| UI 渲染是否正确 | 功能验证 | ❌ 测试工具 |
| 业务逻辑是否正确 | 功能验证 | ❌ 测试工具 |

### 优势

1. **保持 Moat 的纯粹性**：不陷入 UI/功能测试的泥潭
2. **提升架构质量**：确保关键架构边界不被突破
3. **降低维护成本**：规则定义在 Truth Document 中，随业务演化更新
4. **AI 友好**：规则明确，AI 更容易理解和遵守

## 🔗 相关文档

- [Truth Document 模板](.moat/architecture_intent.md)
- [Karpathy Principles Constitution](KARPATHY_PRINCIPLES.md)
- [架构验收协议](ARCHITECTURAL_AUDIT_PROTOCOL.md)
