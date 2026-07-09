# 🎉 Moat v0.8.0a0 — PyPI 发布成功！

**发布时间**: 2026-07-09 18:36
**版本**: v0.8.0a0
**PyPI**: https://pypi.org/project/moat-ai/0.8.0a0/

---

## ✅ 发布完成

### PyPI 信息

- **包名**: `moat-ai`
- **版本**: `0.8.0a0`
- **PyPI 页面**: https://pypi.org/project/moat-ai/0.8.0a0/
- **发布包**:
  - ✅ `moat_ai-0.8.0a0-py3-none-any.whl` (220.1 KB)
  - ✅ `moat_ai-0.8.0a0.tar.gz` (244.4 KB)

### 安装命令

```bash
pip install moat-ai==0.8.0a0
```

### 验证安装

```bash
python3 -c "import moat; print(moat.__version__)"
# 输出: 0.8.0a0
```

---

## 📦 本版本新功能

### 1. Karpathy Principles Constitution 🏛️

将 Andrey Karpathy 的软件工程原则转化为硬规则：

#### ✅ Surgical Changes (手术刀式修改)
```python
from moat.rules import SurgicalChangesChecker

checker = SurgicalChangesChecker(max_diff_lines=100)
violations = checker.check_diff(Path.cwd())
```

#### ✅ Simplicity First (简单优先)
```python
from moat.rules.simplicity_checker import SimplicityChecker

checker = SimplicityChecker()
violations = checker.check_file("foo.py", content)
```

### 2. 规则系统架构

```yaml
# moat/rules/karpathy_principles.yaml
principles:
  surgical_changes:
    thresholds:
      max_diff_lines: 100
      max_files_changed: 3
```

### 3. 测试覆盖

- ✅ **822/822 测试通过 (100%)**
- ✅ **16 个新测试** (规则系统)

---

## 🚀 快速开始

### 安装

```bash
# 最新版本
pip install moat-ai

# 指定版本
pip install moat-ai==0.8.0a0
```

### 使用新功能

```bash
# 查看原则定义
python3 -c "from moat.rules import PrinciplesLoader; print(PrinciplesLoader().load_principles())"

# 检查 Git diff
python3 -c "
from pathlib import Path
from moat.rules import SurgicalChangesChecker

checker = SurgicalChangesChecker()
violations = checker.check_diff(Path.cwd())
"
```

---

## 📊 版本对比

| 项目 | v0.7.0-beta.1 | v0.8.0a0 |
|------|--------------|---------|
| **测试数** | 806 | **822 (+16)** |
| **测试通过率** | 100% | **100%** |
| **规则系统** | ❌ | **✅** |
| **Karpathy 原则** | ❌ | **✅ 2/4** |
| **PyPI** | ✅ v0.7.0b1 | **✅ v0.8.0a0** |

---

## 🔗 相关链接

- **PyPI**: https://pypi.org/project/moat-ai/
- **GitHub**: https://github.com/wang-jie-git/moat
- **文档**: https://github.com/wang-jie-git/moat/blob/main/KARPATHY_PRINCIPLES.md
- **更新日志**: https://github.com/wang-jie-git/moat/blob/main/CHANGELOG.md

---

**🎊 发布成功！所有人都可以安装使用了！**
