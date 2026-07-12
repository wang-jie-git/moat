# Moat --diff Bug 修复报告

**时间**: 2026-07-12 17:35
**Bug**: `moat check --diff` 出现 KeyError: 'callers'
**版本**: moat v1.1.1

---

## 🔍 问题诊断

### 错误信息

```bash
$ moat check --diff
...
💡 影响域分析:

   📍 moat/ast/builder.py::build_skeleton
Traceback (most recent call last):
  ...
  File "/usr/local/lib/python3.14/site-packages/moat/cli.py", line 68
    print(f"      影响 {len(impact['callers'])} 个调用方:")
                            ~~~~^^
KeyError: 'callers'
```

### 根因分析

**字段名不匹配**：

| 位置 | 代码 | 字段名 |
|------|------|--------|
| **cli.py:68-70** | `impact['callers']` | ❌ 期望 `callers` |
| **builder.py:286-292** | 返回字典 | ✅ 实际 `direct_callers` + `indirect_callers` |

**builder.py 返回的 impact 结构**：
```python
{
    "change": change,
    "direct_callers": [...],     # ✅ 有
    "indirect_callers": [...],   # ✅ 有
    "total_callers": 0,          # ✅ 有
    # ❌ 没有 'callers' 字段
}
```

**cli.py 期望的访问方式**：
```python
print(f"      影响 {len(impact['callers'])} 个调用方:")  # ❌ KeyError
for caller in impact["callers"][:5]:
    print(f"        - {caller}")
```

---

## 🔧 修复方案

### 方案：添加 `callers` 兼容字段

在 `builder.py:analyze_impacts()` 中添加 `callers` 字段，合并 `direct_callers` + `indirect_callers`

**修改文件**: `moat/ast/builder.py`

```python
# 修复前
if direct_callers or indirect_callers:
    impacts.append({
        "change": change,
        "direct_callers": direct_callers,
        "indirect_callers": indirect_callers,
        "total_callers": total_callers,
        "confidence_weight": round(confidence_weight, 2),
        "risk_level": risk_level,
    })

# 修复后
if direct_callers or indirect_callers:
    all_callers = direct_callers + indirect_callers  # 合并所有调用方
    impacts.append({
        "change": change,
        "callers": all_callers,  # ✅ 新增：兼容 cli.py 的访问方式
        "direct_callers": direct_callers,
        "indirect_callers": indirect_callers,
        "total_callers": total_callers,
        "confidence_weight": round(confidence_weight, 2),
        "risk_level": risk_level,
    })
```

### 兼容性

- ✅ **向后兼容**：保留 `direct_callers` / `indirect_callers`
- ✅ **新增字段**：`callers` = `direct_callers` + `indirect_callers`
- ✅ **cli.py 无需修改**：直接访问 `impact['callers']`

---

## ✅ 修复验证

### 修复前

```bash
$ moat check --diff
...
💡 影响域分析:

   📍 moat/ast/builder.py::build_skeleton
Traceback (most recent call last):
  ...
KeyError: 'callers'  # ❌ 崩溃
```

### 修复后

```bash
$ moat check --diff
...
💡 影响域分析:

   📍 moat/ast/builder.py::build_skeleton
      影响 1 个调用方:
        - {'caller': 'moat/cli.py::cmd_check', 'confidence': 1.0}
      风险等级: low

😣 痛觉评估:
   总分: 0.0/100 (LOW)
   建议: 可选修复（不影响核心功能）

✅ 变更风险较低，但仍建议运行完整检查
```

### 受影响文件

| 文件 | 路径 | 修改内容 |
|------|------|----------|
| **moat/ast/builder.py** | `/usr/local/lib/python3.14/site-packages/moat/ast/builder.py` | 添加 `callers` 字段 |

---

## 📊 影响范围

### 修改的函数

| 函数 | 行号 | 影响 |
|------|------|------|
| `analyze_impacts()` | 236 | ✅ 核心修复 |
| `build_skeleton()` | 298 | 间接影响（被调用） |
| `to_dict()` | 313 | 间接影响（被调用） |
| `to_json()` | 318 | 间接影响（被调用） |

### 影响域分析

```
moat/ast/builder.py::build_skeleton
    └── 被 moat/cli.py::cmd_check 调用 (confidence: 1.0)
    └── 风险等级: low
```

---

## 🧪 测试

### 测试脚本

创建 `tests/test_diff_bugfix.py`：

```python
#!/usr/bin/env python3
"""验证 moat --diff 修复"""
import subprocess
import sys

def test_diff_bug_fix():
    result = subprocess.run(
        ["moat", "check", "--diff", "--project", "/Users/mac/Desktop/moat"],
        capture_output=True,
        text=True,
        timeout=120
    )

    if result.returncode == 0:
        print("✅ --diff 模式正常运行")
        return True
    else:
        print("❌ --diff 模式失败")
        print(result.stderr)
        return False

if __name__ == "__main__":
    success = test_diff_bug_fix()
    sys.exit(0 if success else 1)
```

### 测试结果

```bash
$ python3 tests/test_diff_bugfix.py
✅ --diff 模式正常运行
```

---

## 📝 后续建议

### 短期（P0）

1. **验证修复完整性**
   - 在 oh-agent-panel 运行 `moat check --diff`
   - 确认不再出现 KeyError

2. **添加单元测试**
   - 在 moat 测试套件中添加 `test_analyze_impacts_returns_callers`
   - 确保字段名一致性

### 中期（P1）

1. **统一字段命名**
   - 考虑将所有 `*_callers` 字段统一为 `callers`
   - 或添加类型提示/document 明确字段结构

2. **添加类型检查**
   - 使用 Pydantic 或 TypedDict 定义 impact 结构
   - 避免字段名拼写错误

### 长期（P2）

1. **改进错误处理**
   - 在 cli.py 添加字段存在性检查
   - 提供更友好的错误提示

---

## 🔗 相关文件

| 文件 | 路径 |
|------|------|
| **修复文件** | `/usr/local/lib/python3.14/site-packages/moat/ast/builder.py:284-293` |
| **调用方** | `/usr/local/lib/python3.14/site-packages/moat/cli.py:68-72` |
| **测试脚本** | `/Users/mac/Desktop/moat/tests/test_diff_bugfix.py` |

---

**修复完成时间**: 2026-07-12 17:35
**修复状态**: ✅ 已验证
**影响范围**: 仅影响 `moat check --diff` 模式
**向后兼容**: ✅ 是
