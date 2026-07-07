# Moat 发布流程

## v0.6.1 发布清单

### ✅ 已完成

- [x] 版本号更新：0.6.0 → 0.6.1 (`pyproject.toml`, `moat/__init__.py`)
- [x] CHANGELOG.md 更新（新增 v0.6.1 章节）
- [x] Bug 修复：watchdog 可选依赖延迟导入
- [x] Bug 修复：Pydantic BaseModel 实例化跳过
- [x] 所有测试通过（81/81 ✅）
- [x] moat check 自举测试通过（21 通过，0 失败）
- [x] Git 提交：056f5a0

### 📦 发布步骤

#### 1. 安装发布工具

```bash
pip install build twine
```

#### 2. 构建分发包

```bash
cd ~/Desktop/moat
python3 -m build
```

这会生成：
- `dist/moat_ai-0.6.1-py3-none-any.whl`
- `dist/moat_ai-0.6.1.tar.gz`

#### 3. 检查分发包

```bash
twine check dist/*
```

#### 4. 测试安装

```bash
# 在测试目录安装
cd /tmp/test-moat
pip install /Users/mac/Desktop/moat/dist/moat_ai-0.6.1-py3-none-any.whl

# 验证
moat --version
moat check --help
```

#### 5. 发布到 PyPI

```bash
# 正式发布
twine upload dist/*

# 或先发布到 TestPyPI
twine upload --repository testpypi dist/*
```

#### 6. 验证发布

```bash
# 安装刚发布的版本
pip install moat-ai==0.6.1

# 验证
moat --version
```

#### 7. 创建 GitHub Release

在 GitHub 仓库创建 Release：
- Tag: `v0.6.1`
- Title: `Moat v0.6.1 — Sidecar Bug 修复`
- 复制 `CHANGELOG.md` v0.6.1 章节作为 Release Notes

### 📝 发布后检查清单

- [ ] PyPI 页面更新：https://pypi.org/project/moat-ai/
- [ ] GitHub Release 创建
- [ ] 文档网站更新（如果有）
- [ ] 通知用户（Twitter/Discord/邮件列表）

### 🔄 回滚方案

如果发布后发现问题：

```bash
# 1. 修复问题
# 2. 发布新版本
twine upload dist/moat_ai-0.6.2-py3-none-any.whl

# 3. 在 GitHub Release 中标记 v0.6.1 为 "Yanked"
```

### 📊 版本历史

- **v0.6.1** (2026-07-07) — Sidecar Bug 修复（watchdog + Pydantic）
- **v0.6.0** (2026-07-07) — TypeScript/Go 专项检查规则
- **v0.5.0** (2026-07-07) — Tree-sitter 多语言 + One Memory + 知识图谱
- **v0.4.0** (2026-07-07) — 进化指标系统 + AI 辅助修复 + Sidecar
- **v0.2.0** (2026-07-07) — TypeScript 支持 + CodeGraph 语义分析
- **v0.1.0** (2025-07-07) — 初始发布
