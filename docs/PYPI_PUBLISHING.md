# PyPI 发布指南

## 📋 发布前检查清单

### 1. 准备工作

- [ ] 注册 PyPI 账号: https://pypi.org/account/register/
- [ ] 创建 API Token: https://pypi.org/manage/account/token/
- [ ] 安装发布工具:
  ```bash
  pip install build twine
  ```

### 2. 版本检查

- [x] pyproject.toml 配置正确
- [x] 版本号: 0.4.0
- [x] README.md 格式正确（Markdown）
- [x] LICENSE 文件存在
- [x] 所有测试通过: 45/45 ✅

### 3. 构建测试

```bash
# 清理旧构建
rm -rf dist build *.egg-info

# 构建包
python -m build

# 检查构建结果
ls -lh dist/
# 应该看到:
# moat_ai-0.4.0-py3-none-any.whl
# moat_ai-0.4.0.tar.gz
```

### 4. 本地测试

```bash
# 安装构建的包
pip install dist/moat_ai-0.4.0-py3-none-any.whl

# 测试功能
moat --version
moat check
```

---

## 🚀 发布到 PyPI

### 方法 1: 使用 twine（推荐）

```bash
# 1. 上传到 TestPyPI（测试）
twine upload --repository testpypi dist/*

# 2. 测试安装
pip install --index-url https://test.pypi.org/simple/ moat-ai

# 3. 确认无误后，上传到正式 PyPI
twine upload dist/*
```

### 方法 2: 使用 GitHub Actions

创建 `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install build twine

      - name: Build package
        run: python -m build

      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

---

## ⚙️ PyPI 配置说明

### pyproject.toml 关键配置

```toml
[project]
name = "moat-ai"
version = "0.4.0"
description = "AI 编码护城河 — 第一个自我进化的 AI 编码守护者"
readme = "README.md"
license = {text = "Apache-2.0"}
authors = [
    {name = "One Team"},
]
requires-python = ">=3.10"
keywords = ["ai", "testing", "guardrails", "code-quality", "python"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    ...
]

[project.optional-dependencies]
dashboard = ["fastapi>=0.100", "uvicorn>=0.22"]
sidecar = ["watchdog>=3.0", "fastapi>=0.100", "uvicorn>=0.22"]
vscode = ["pyperclip>=1.8"]
all = ["moat-ai[dashboard,sidecar,vscode]"]

[project.urls]
Homepage = "https://github.com/wang-jie-git/moat"
Source = "https://github.com/wang-jie-git/moat"

[project.scripts]
moat = "moat.cli:main"
```

### MANIFEST.in（可选）

如果需要包含额外文件（如文档、脚本）：

```txt
include README.md
include LICENSE
include CHANGELOG.md
recursive-include docs *.md
recursive-include scripts *.sh *.py
```

---

## 📝 发布流程

### 第一次发布

```bash
# 1. 确保所有测试通过
pytest tests/

# 2. 构建包
python -m build

# 3. 检查构建
twine check dist/*

# 4. 上传到 TestPyPI
twine upload --repository testpypi dist/*

# 5. 测试安装
pip install --index-url https://test.pypi.org/simple/ moat-ai

# 6. 确认无误后，上传到正式 PyPI
twine upload dist/*
```

### 后续版本发布

```bash
# 1. 更新版本号
# 编辑 pyproject.toml:
# version = "0.4.1"

# 2. 更新 CHANGELOG.md

# 3. 构建
python -m build

# 4. 上传
twine upload dist/*
```

---

## 🔐 安全建议

### API Token 管理

**不要硬编码 Token 在代码中！**

#### 推荐方式 1: 环境变量

```bash
# 设置环境变量
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-xxxxxxxxxxxxxxxxxxxx

# 上传
twine upload dist/*
```

#### 推荐方式 2: .pypirc 文件

```bash
# 创建或编辑 ~/.pypirc
cat > ~/.pypirc <<EOF
[distutils]
index-servers =
    pypi

[pypi]
username = __token__
password = pypi-xxxxxxxxxxxxxxxxxxxx
EOF

# 设置权限（仅自己可读）
chmod 600 ~/.pypirc

# 上传（自动使用 .pypirc）
twine upload dist/*
```

#### 推荐方式 3: GitHub Secrets（CI/CD）

```yaml
# GitHub Actions
env:
  TWINE_USERNAME: __token__
  TWINE_PASSWORD: \${{ secrets.PYPI_API_TOKEN }}
```

---

## ✅ 发布后验证

### 1. 检查 PyPI 页面

访问: https://pypi.org/project/moat-ai/

应该看到:
- ✅ 包名: moat-ai
- ✅ 版本: 0.4.0
- ✅ Description
- ✅ README 渲染
- ✅ 安装命令

### 2. 测试安装

```bash
# 从 PyPI 安装
pip install moat-ai

# 验证
moat --version
# 输出: Moat v0.4.0
```

### 3. 检查下载统计

```bash
# PyPI Stats
# 访问: https://pypistats.org/packages/moat-ai
```

---

## 🔄 版本管理策略

### 语义化版本

```
v0.4.0  →  v0.4.1  # Bug 修复
        →  v0.5.0  # 新功能（向后兼容）
        →  v1.0.0  # 稳定版
```

### 发布频率建议

- **Beta 阶段**: 每月发布
- **RC 阶段**: 每周发布
- **稳定版**: 按需发布

---

## 📊 PyPI vs GitHub 发布对比

| 特性 | GitHub | PyPI |
|------|--------|------|
| 安装便捷性 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 更新频率 | 实时 | 每次发布 |
| 版本管理 | Git tags | PyPI versions |
| 依赖解析 | ❌ | ✅ |
| 可发现性 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 安全性 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 离线安装 | ❌ | ✅ |
| 适合阶段 | 开发/测试 | 生产/稳定 |

---

## 🎯 建议

### 当前阶段（v0.4.0）

**建议**: **暂不发布到 PyPI**

**理由**:
1. 项目仍在快速发展
2. GitHub 安装已足够方便
3. 可以更快地修复和迭代

### 合适时机

**建议**: **v0.5.0 或 v1.0.0 时发布**

**标志**:
- API 稳定
- 文档完善
- 有足够的用户反馈
- 团队准备好长期维护

---

## 📚 参考资料

- **PyPI**: https://pypi.org/
- **Packaging Guide**: https://packaging.python.org/
- **Twine Docs**: https://twine.readthedocs.io/
- **Build Docs**: https://pypa-build.readthedocs.io/
