# Moat v0.7.0-beta 完善计划（修订版）

**目标**: 实现 Claude Code Hook + 完善算子实际能力

**日期**: 2026-07-08  
**版本**: v0.7.0-beta → v0.7.0-beta.1

---

## 📊 当前状态

### ✅ 测试覆盖
- **全部通过**: 801/801 (100%)

### ⚠️ 待完善功能

#### A. Claude Code Hook (P0)
**现状**: `moat gatekeeper` 命令有 `start/stop/status` 占位符，未实现
**需求**: 自动生成 `.claude/settings.json` 并集成 Hook 机制

#### B. 算子实际能力完善 (P0)
**优先级调整**: B3 降级为"轻量级验证"

| 算子 | 测试状态 | 实际能力 | 优先级 |
|------|---------|---------|--------|
| `api_response_spec` | ✅ | 硬编码 | **P0 - Day 1** |
| `framework_usage` | ✅ | 部分实现 | **P0 - Day 1** |
| `runtime_evidence` | ✅ | 基础实现 | **P1 - Day 2 (轻量级)** |
| `directory_responsibility` | ✅ | 完整 | - |
| `architecture_health_score` | ✅ | 完整 | - |
| `minimal_module_drill` | ✅ | 完整 | - |
| `truth_document` | ✅ | 完整 | - |

---

## 🎯 实施计划（修订版）

### Day 1（今天）：算子核心能力

#### B1. api_response_spec 完整实现 (2小时)
**目标**: 真实扫描 API 端点并验证响应格式

**小步快跑策略**:
- 先覆盖 FastAPI 最常见模式
- 不追求完美通用，能检测主流场景即可
- 遇到代码异构场景后续迭代

**实现步骤**:
1. **扫描 FastAPI 装饰器**
   - `@app.get("/path")` → GET /path
   - `@router.post("/path")` → POST /path
   - 提取路径和方法

2. **检查响应模型**
   - `response_model=UserResponse`
   - 返回值类型注解
   - `JSONResponse(content=...)`

3. **状态码检查**
   - 默认 GET→200, POST→201, DELETE→204
   - `HTTPException(status_code=xxx)`
   - `return JSONResponse(status_code=xxx)`

**验收标准**:
- 能扫描真实 FastAPI 项目
- 能识别 80% 的主流端点定义
- 发现无 `response_model` 的端点给出建议

---

#### B2. framework_usage 增强 (2小时)
**目标**: 检查 FastAPI 框架特性充分利用

**小步快跑策略**:
- 先做 FastAPI（当前最流行）
- Django/Flask 后续迭代
- 只检查高价值特性

**实现步骤**:
1. **FastAPI Pydantic** ✅ (已实现)
2. **FastAPI 异常处理** ❌ → 新增
   - 检测 `@app.exception_handler`
   - 建议统一异常处理
3. **FastAPI 依赖注入** ❌ → 新增
   - 检测 `Depends()`
   - 建议鉴权/数据库依赖使用 Depends
4. **FastAPI APIRouter** ❌ → 新增
   - 检测 `APIRouter()`
   - 建议按模块分组路由

**验收标准**:
- 能检测未使用 `Depends()` 的鉴权代码
- 能检测单个文件中路由过多的情况
- 给出具体的改进建议

---

### Day 2（明天）：轻量级验证 + Claude Hook

#### B3. runtime_evidence 轻量级验证 (1小时)
**目标**: 不实际执行，只做"尝试性检查"

**轻量级策略**:
- 不执行 `pip install`（避免环境问题）
- 不启动服务（避免端口冲突）
- 只做"存在性检查"+"语法验证"

**实现步骤**:
1. **启动命令检查**
   - 检测 `python main.py` 是否能通过语法检查
   - `python -m py_compile main.py`
   
2. **配置文件检查**
   - `.env.example` 是否存在
   - 必要环境变量是否已定义

3. **依赖检查（只检查，不安装）**
   - `requirements.txt` 是否存在
   - 检查是否有明显版本冲突（同一包多个版本）

**失败处理**:
- 所有检查失败只给 **WARNING**，不给 ERROR
- 不阻塞 CI/CD
- 给出"如何修复"的建议

---

#### A1. Claude Code Hook 集成 (2小时)
**目标**: 自动生成 `.claude/settings.json` + 交互式选项

**小步快跑策略**:
- 先做自动生成配置
- 不做后台守护进程（后续版本）
- 交互式选项提升开箱体验

**实现步骤**:
1. **`moat init` 增强**
   ```python
   # 检测到 Claude Code 项目后询问
   "是否将 Moat 守护进程集成至 Claude Code？(Y/n)"
   ```

2. **自动生成 `.claude/settings.json`**
   ```json
   {
     "hooks": {
       "PreToolUse": [
         {
           "matcher": "Write|Edit",
           "hooks": [
             {
               "type": "command",
               "command": "moat gatekeeper check --file ${file}",
               "timeout": 5000
             }
           ]
         }
       ]
     }
   }
   ```

3. **配置说明文档**
   - Hook 触发时机
   - 如何自定义规则
   - 如何禁用特定 Hook

**验收标准**:
```bash
moat init
# 询问是否集成 Claude Code
cat .claude/settings.json | jq '.hooks.PreToolUse'
# 能看到 moat gatekeeper check 命令
```

---

### Day 3（后天）：测试 + 文档 + 发布

#### A2. Gatekeeper 文件监听 (可选)
**目标**: 如果需要，实现基础的文件监听

**评估**: 
- 如果 Day 1-2 时间充裕 → 实现
- 如果时间紧张 → 延后到 v0.7.1

---

#### A3. 文档 + 测试修复
1. **更新 CHANGELOG.md**
   - v0.7.0-beta.1 更新日志
   
2. **更新 README.md**
   - 算子实际能力说明
   - Claude Code Hook 使用指南

3. **测试覆盖**
   - 确保 801/801 通过
   - 新增算子集成测试

4. **版本升级**
   - `__version__ = "0.7.0-beta.1"`
   - Git tag: `v0.7.0-beta.1`

---

## 🎯 成功指标

### 算子能力验证
```bash
# B1: api_response_spec
python3 -c "
from moat.verification.operators import APIResponseSpecOperator
result = APIResponseSpecOperator().verify(context)
assert result.evidence['total_endpoints_checked'] > 0  # 真实扫描
assert result.evidence['checked_endpoints'][0].get('method') == 'GET'  # 真实数据
"
```

```bash
# B2: framework_usage
python3 -c "
result = FrameworkUsageOperator().verify(context)
checks = result.evidence['usage_checks']
assert any(c['feature'] == 'FastAPI Depends' for c in checks)  # 真实检测
assert any(c['feature'] == 'FastAPI ExceptionHandler' for c in checks)  # 真实检测
"
```

### Claude Code Hook 验证
```bash
moat init
cat .claude/settings.json | jq '.hooks'  # 存在且配置正确
```

### 测试覆盖
```bash
python3 -m pytest tests/ -v  # 100% 通过 (801/801)
```

---

## 📋 实施原则

### 小步快跑
- ✅ 先覆盖 80% 主流场景
- ❌ 不强求 100% 完美通用
- ✅ 遇到异构场景后续迭代

### 稳健优先
- ✅ 算子检查失败只给 WARNING
- ❌ 不阻塞 CI/CD
- ✅ 给出清晰的修复建议

### 用户体验
- ✅ `moat init` 交互式询问
- ✅ 自动生成配置
- ✅ 开箱即用

---

## 🚀 立即行动

**现在开始 Day 1：**
1. B1: api_response_spec 完整实现
2. B2: framework_usage 增强

准备好写代码了！💻
