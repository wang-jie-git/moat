# Moat v0.6.1 — Sidecar Bug 修复

**发布日期**: 2026-07-07
**版本**: v0.6.1
**Git Tag**: [v0.6.1](https://github.com/wang-jie-git/moat/releases/tag/v0.6.1)

---

## 🐛 Bug 修复

### 修复 Sidecar 可选依赖问题（4 个 Bug）

**问题**: Moat 自举测试发现 sidecar 模块导入失败

#### Bug 1 & 4: watchdog 缺失导致 import 失败

**文件**: `moat/sidecar/watcher.py`

**问题**:
```python
# 修复前：直接导入（失败）
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer
```

**错误信息**:
```
ModuleNotFoundError: No module named 'watchdog'
```

**解决**:
```python
# 修复后：延迟导入 + try-except 保护
try:
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    from watchdog.observers import Observer
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    FileSystemEventHandler = object  # 占位符
    Observer = None
```

**影响**:
- 类定义改为条件继承：`class FileChangeHandler(FileSystemEventHandler if WATCHDOG_AVAILABLE else object)`
- `start()` 方法增加 watchdog 可用性检查
- 提供友好的安装提示

#### Bug 2: daemon.py 间接失败

**文件**: `moat/sidecar/daemon.py`

**问题**: 导入 `watcher.py` 时失败

**解决**: 随 `watcher.py` 修复自动解决

#### Bug 3: Pydantic BaseModel 实例化失败

**文件**: `moat/checks/l1_modules.py`

**问题**:
```python
# 修复前：尝试无参数实例化所有类
instance = cls()  # ❌ Pydantic BaseModel 需要必填字段
```

**错误信息**:
```
ValidationError: 1 validation error for CheckRequest
projectPath
  Field required [type=missing, input_value={}, input_type=dict]
```

**解决**:
```python
# 修复后：检测 Pydantic BaseModel 并跳过
try:
    from pydantic import BaseModel
    if issubclass(cls, BaseModel):
        # 跳过实例化检查
        continue
except ImportError:
    pass  # Pydantic 未安装，继续正常逻辑
```

---

## ✅ 验证结果

### Moat Check

**修复前**:
```
通过: 19, 失败: 4, 警告: 1
```

**修复后**:
```
通过: 21, 失败: 0, 警告: 1
✅ MOAT 全部通过，系统健康。
```

### 单元测试

```
============================== 81 passed in 0.59s ===============================
```

**测试通过率**: 100% (81/81)

---

## 📦 安装

### 一键安装（推荐）

```bash
pip install "moat-ai[all]"
```

### 基础安装

```bash
pip install moat-ai
```

### Sidecar 功能（可选）

```bash
pip install "moat-ai[sidecar]"
```

---

## 🚀 快速开始

```bash
# 完整检查
moat check

# 增量检查
moat check --diff

# 初始化到当前项目
moat init

# 生成报告
moat report --copy
```

---

## 📊 完整变更日志

### v0.6.0 — TypeScript/Go 专项检查规则

- TypeScript 专项检查（5 个）：any 类型、空值安全、异步竞态、导出完整性、性能反模式
- Go 专项检查（3 个）：error 处理、goroutine 泄露、并发安全

### v0.5.0 — 多语言感知 + 深度记忆 + 智能进化

- **Tree-sitter 多语言支持**: Python/TypeScript/Go/Rust/JavaScript
- **One Memory 深度集成**: 自动触发梦境引擎、双向同步
- **进化指标自动采集**: moat check 后自动记录
- **知识图谱记忆扩展**: 修复历史、薄弱点识别、修复模式推荐

---

## 📝 版本历史

- **v0.6.1** (2026-07-07) — Sidecar Bug 修复
- **v0.6.0** (2026-07-07) — TypeScript/Go 专项检查
- **v0.5.0** (2026-07-07) — 多语言感知 + 深度记忆
- **v0.4.0** (2026-07-07) — 进化指标 + Sidecar
- **v0.2.0** (2026-07-07) — TypeScript 支持
- **v0.1.0** (2025-07-07) — 初始发布

---

## 🔗 相关链接

- **GitHub**: https://github.com/wang-jie-git/moat
- **PyPI**: https://pypi.org/project/moat-ai/
- **文档**: https://github.com/wang-jie-git/moat/blob/main/README.md
- **问题反馈**: https://github.com/wang-jie-git/moat/issues

---

## 💡 贡献者

感谢所有为这个版本做出贡献的开发者！

---

**发布**: 2026-07-07 23:40
**状态**: ✅ 已完成
