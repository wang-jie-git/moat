# Moat v0.2.0 升级日志

## 🎉 新功能

### 1. 插件化检查架构

**目标**: 支持多语言检查（Python/TypeScript/Go/Rust...）

**变更**:
- ✅ 新增 `moat/checks/base.py` — 统一的 `Check` 基类
- ✅ 所有检查（新/旧）通过统一接口运行
- ✅ 自动检测项目类型，只运行相关检查
- ✅ 向后兼容：Python 检查（旧风格）和新检查并存

**使用示例**:
```python
from moat.checks.base import Check, CheckResult

class MyCheck(Check):
    def run(self) -> list[CheckResult]:
        # 自定义检查逻辑
        return [self.pass_check("OK")]
```

---

### 2. TypeScript 检查模块

**目标**: 支持 TypeScript/React 项目

**新增检查**（4 个）:
1. **TypeScriptSyntaxCheck** — 语法检查（调用 `tsc --noEmit`）
2. **TypeScriptDedupCheck** — 去重/防抖代码注释检查
3. **TypeScriptRaceConditionCheck** — 竞态条件注释检查
4. **TypeScriptTimingDocCheck** — 时序文档检查

**检查项**:
- ✅ 去重/防抖代码必须有"为什么"注释
- ✅ 竞态关键逻辑（handleStop/pendingMessageRef 等）必须有时序注释
- ✅ 禁止硬编码固定窗口（除非有注释说明）
- ✅ 时序图文档必须存在（可选）

---

### 3. 向后兼容性

**保证**:
- ✅ Python 检查（原有 6 个）完全保留
- ✅ 旧风格检查（返回 `list[dict]`）和新风格检查（基于 `Check` 基类）并存
- ✅ 配置格式兼容（`.moat/config.json`）

---

## 🔧 技术细节

### Check 基类设计

```python
@dataclass
class CheckResult:
    """统一的结果格式"""
    type: str  # pass / fail / skip / warn
    message: str
    file: str | None = None
    line: int | None = None
    level: str = "INFO"  # INFO / WARN / ERROR
    metadata: dict[str, Any] = field(default_factory=dict)
```

### 项目类型检测

```python
def detect_project_type(project_root: Path) -> dict[str, bool]:
    return {
        "python": any(root.rglob("*.py")),
        "typescript": any(root.rglob("*.ts")) or any(root.rglob("*.tsx")),
        "go": any(root.rglob("*.go")),
        "rust": any(root.rglob("*.rs")),
    }
```

### 检查运行器

```python
def run_all_checks(project_root: str = ".") -> bool:
    # 1. 检测项目类型
    project_type = detect_project_type(root)

    # 2. 创建检查实例
    checks = create_check_instances(project_type, root, config)

    # 3. 运行所有检查
    for name, check in checks:
        print(f"▸ {name}...")
        results = check.run()
        # ...
```

---

## 📊 测试覆盖

| 类别 | 测试数 | 状态 |
|------|--------|------|
| CheckResult 数据结构 | 6 | ✅ 通过 |
| Check 基类 | 3 | ✅ 通过 |
| TypeScript 检查 | 2 | ✅ 通过 |
| CLI | 7 | ✅ 通过 |
| Monitor | 3 | ✅ 通过 |
| 原有测试 | 1 | ✅ 通过 |
| **总计** | **22** | **✅ 全部通过** |

---

## 🚀 使用方式

### 1. 安装

```bash
# 从 PyPI
pip install moat-ai

# 从 GitHub
pip install git+https://github.com/wang-jie-git/moat.git
```

### 2. 初始化

```bash
cd your-project
moat init
```

### 3. 运行检查

```bash
# 自动检测项目类型并运行相关检查
moat check

# 指定项目
moat check --project /path/to/project
```

### 4. 配置 TypeScript 检查

创建 `.moat/config.json`:

```json
{
  "typescript": {
    "tsc_path": "npx tsc",
    "tsconfig": "tsconfig.json",
    "require_timing_doc": true
  }
}
```

---

## 📝 迁移指南

### 从 v0.1.x 升级

**无需任何改动**，完全向后兼容。

如果需要启用 TypeScript 检查：

```bash
# 1. 安装 TypeScript
npm install -g typescript

# 2. 运行检查（自动检测 TypeScript 文件）
moat check
```

---

## 🔜 下一步（Roadmap）

### v0.2.1（计划）
- [ ] 集成 CodeGraph 作为可选依赖
- [ ] 依赖图生成器
- [ ] 变更影响分析器

### v0.3.0（计划）
- [ ] Go/Rust 检查模块
- [ ] 插件 Marketplace
- [ ] 自定义检查 DSL

### v0.4.0（计划）
- [ ] AI 辅助检查生成
- [ ] 智能基线对比
- [ ] Web Dashboard 增强

---

## 🤝 贡献

欢迎提交 Issue 和 PR！

- [GitHub](https://github.com/wang-jie-git/moat)
- [文档](https://github.com/wang-jie-git/moat/blob/main/README.md)

---

**Moat v0.2.0** — 让 AI 编程不再"越改越乱" 🏰
