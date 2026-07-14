# Moat v0.7.0-beta 完善计划

**目标**: 实现 Claude Code Hook + 完善算子实际能力

**日期**: 2026-07-08  
**版本**: v0.7.0-beta → v0.7.0-beta.1

---

## 📊 当前状态

### ✅ 测试覆盖
- **全部通过**: 801/801 (100%)
  - `tests/verification/`: 48/48 ✅
  - `tests/` 其他: 758/758 ✅

### ⚠️ 待完善功能

#### A. Claude Code Hook (P0)
**现状**: `moat gatekeeper` 命令有 `start/stop/status` 占位符，未实现
**需求**: 自动生成 `.claude/settings.json` 并集成 Hook 机制

#### B. 算子实际能力完善 (P0)
**现状**: 算子测试通过，但实际扫描能力是**占位实现**

| 算子 | 测试状态 | 实际能力 | 问题 |
|------|---------|---------|------|
| `api_response_spec` | ✅ | 硬编码 | `_check_response_format()` 返回假数据 |
| `framework_usage` | ✅ | 部分实现 | 只检查 Pydantic，未检查其他框架特性 |
| `runtime_evidence` | ✅ | 基础实现 | 只收集证据，不执行实际验证 |
| `directory_responsibility` | ✅ | 完整 | - |
| `architecture_health_score` | ✅ | 完整 | - |
| `minimal_module_drill` | ✅ | 完整 | - |
| `truth_document` | ✅ | 完整 | - |

---

## 🎯 实施计划

### 第一阶段：算子实际能力 (B) (2-3天)

#### B1. api_response_spec 完整实现 (0.5天)
**目标**: 真实扫描 API 端点并验证响应格式

**实现步骤**:
1. **FastAPI 响应模型扫描**
   - 扫描 `response_model` 参数
   - 检查返回值类型注解
   - 验证 `JSONResponse` 使用

2. **HTTP 状态码检查**
   - 解析 `@app.get/post/put/delete` 装饰器
   - 提取状态码（默认 200/201）
   - 检查 `HTTPException(status_code=xxx)`

3. **统一响应格式验证**
   - 扫描 `{"data": ..., "total": ...}` 模式
   - 检查 `success/error` 字段统一性

**验收标准**:
```python
# 测试实际扫描能力
result = APIResponseSpecOperator().verify(context)
assert result.evidence["total_endpoints_checked"] > 0
assert any(e["response_check"]["has_standard_response"] for e in result.evidence["checked_endpoints"])
```

---

#### B2. framework_usage 增强 (0.5天)
**目标**: 检查框架推荐机制的充分利用

**实现步骤**:
1. **FastAPI 特性检查**
   - ✅ Pydantic BaseModel (已实现)
   - ❌ `@app.exception_handler` 缺失
   - ❌ `Depends()` 依赖注入缺失
   - ❌ `APIRouter` 路由分组缺失
   - ❌ `BackgroundTasks` 后台任务缺失

2. **Django 特性检查**
   - ❌ Django Forms/Serializers
   - ❌ `get_object_or_404()`
   - ❌ Class-based Views

3. **Flask 特性检查**
   - ❌ Flask-Marshmallow
   - ❌ `@app.errorhandler`

**验收标准**:
```python
# 检测 FastAPI 依赖注入
assert "framework_usage" in result.evidence
checks = result.evidence["framework_usage"]["usage_checks"]
assert any(c["feature"] == "FastAPI Depends" for c in checks)
```

---

#### B3. runtime_evidence 实际执行 (1天)
**目标**: 从"收集证据"升级到"执行验证"

**实现步骤**:
1. **依赖验证**
   - 尝试 `pip install -r requirements.txt` (dry-run)
   - 检查版本冲突

2. **启动验证**
   - 检查 `python main.py` 是否能启动
   - 设置超时（3秒）
   - 捕获启动日志

3. **健康检查**
   - 尝试 `GET /health` 或 `GET /healthz`
   - 验证响应状态码
   - 记录响应时间

4. **数据库连接**
   - 检查 `DATABASE_URL` 配置
   - 尝试连接（可选）

**验收标准**:
```python
result = RuntimeEvidenceOperator().verify(context)
assert "execution_evidence" in result.evidence
assert result.evidence["execution_evidence"]["startup"]["success"] is True
```

---

### 第二阶段：Claude Code Hook 集成 (A) (2-3天)

#### A1. 自动生成 `.claude/settings.json` (1天)
**目标**: 在 `moat init` 或 `moat gatekeeper setup` 时自动生成配置

**实现步骤**:
1. **读取项目配置**
   ```python
   config = {
     "project_type": "fastapi",
     "checks": ["syntax", "race_condition", "architecture"]
   }
   ```

2. **生成 Hook 规则**
   ```json
   {
     "hooks": {
       "PreToolUse": [
         {
           "matcher": "Write|Edit",
           "hooks": [
             {
               "type": "command",
               "command": "moat gatekeeper check --file ${file}"
             }
           ]
         }
       ]
     }
   }
   ```

3. **写入 `.claude/settings.json`**
   ```python
   settings_path = project_path / ".claude" / "settings.json"
   settings_path.write_text(json.dumps(config, indent=2))
   ```

**验收标准**:
```bash
moat init
cat .claude/settings.json | jq '.hooks'
# 应有 PreToolUse 和 PostToolUse hooks
```

---

#### A2. Gatekeeper 文件监听 (1-2天)
**目标**: 后台监听文件变化并自动检查

**实现步骤**:
1. **文件监听器**
   ```python
   from watchdog.observers import Observer
   
   class FileChangeHandler(FileSystemEventHandler):
       def on_modified(self, event):
           if event.src_path.endswith('.py'):
               self.gatekeeper.check_file(event.src_path)
   ```

2. **实时反馈**
   - 修改文件 → 触发检查 → 显示结果
   - 错误立即通知（终端通知）

3. **守护进程管理**
   ```bash
   moat gatekeeper start  # 后台运行
   moat gatekeeper stop   # 停止
   moat gatekeeper status # 查看状态
   ```

**验收标准**:
```bash
# 后台运行
moat gatekeeper start

# 编辑一个文件
vim api/routes.py

# 终端应有通知
```

---

#### A3. Claude Code 集成文档 (0.5天)
**目标**: 文档化 Hook 使用方式

**文档内容**:
- `.claude/settings.json` 配置说明
- Hook 触发时机（PreToolUse/PostToolUse）
- 自定义规则示例
- 与 CI/CD 配合使用

---

## 📋 实施顺序

### Day 1 (今天)
1. ✅ **B1**: api_response_spec 完整实现
2. ✅ **B2**: framework_usage 增强

### Day 2 (明天)
3. ✅ **B3**: runtime_evidence 实际执行
4. ✅ **A1**: 自动生成 `.claude/settings.json`

### Day 3 (后天)
5. ✅ **A2**: Gatekeeper 文件监听
6. ✅ **A3**: Claude Code 集成文档
7. ✅ **测试修复**: 修复任何失败的测试
8. ✅ **版本升级**: v0.7.0-beta.1 + CHANGELOG

---

## 🎯 成功指标

### 算子能力验证
```bash
# 测试实际扫描能力
python3 -c "
from moat.verification.operators import APIResponseSpecOperator
result = APIResponseSpecOperator().verify(context)
print(result.evidence['total_endpoints_checked'])  # > 0
print(result.evidence['checked_endpoints'][0]['response_check'])  # 真实数据
"
```

### Claude Code Hook 验证
```bash
# 生成配置
moat init
cat .claude/settings.json | grep hooks  # 存在

# 测试守门
moat gatekeeper check --file api/routes.py  # 返回真实结果
```

### 测试覆盖率
```bash
python3 -m pytest tests/ -v  # 100% 通过 (801/801)
```

---

## 🚀 下一步

请确认：
1. **这个计划是否合理？**
2. **要不要先查看某个算子的完整实现？**
3. **Claude Code Hook 的配置格式是否需要调整？**

准备好了就开始实施！💪
