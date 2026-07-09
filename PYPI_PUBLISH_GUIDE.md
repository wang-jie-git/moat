# PyPI 发布指南

## 当前状态

✅ **构建完成**: `moat_ai-0.8.0a0-py3-none-any.whl` 和 `moat_ai-0.8.0a0.tar.gz`

❌ **PyPI 认证失败**: Token 可能已过期

## 手动发布步骤

### 1. 更新 PyPI Token

访问 https://pypi.org/manage/account/token/ 创建新的 API Token

### 2. 更新 .pypirc

```bash
# 编辑 .pypirc 文件
nano ~/.pypirc

# 或使用环境变量
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-你的新token
```

### 3. 发布到 PyPI

```bash
cd /Users/mac/Desktop/moat

# 方法 A: 使用 twine
twine upload dist/* -r pypi

# 方法 B: 使用 uv (推荐)
uv publish dist/*
```

### 4. 验证发布

```bash
# 等待几分钟后验证
pip install --upgrade moat-ai

# 检查版本
python3 -c "import moat; print(moat.__version__)"
```

## 自动化发布脚本

创建 `publish_pypi.sh`:

```bash
#!/bin/bash
set -e

echo "🏗️  Building distribution..."
uv build .

echo "📤  Publishing to PyPI..."
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-你的新token
twine upload dist/* -r pypi

echo "✅  Published!"
```

## 当前构建文件

```
dist/
├── moat_ai-0.8.0a0-py3-none-any.whl  (182 KB)
└── moat_ai-0.8.0a0.tar.gz            (205 KB)
```

## 注意事项

1. **版本格式**: 使用 `0.8.0a0` (alpha)，符合 PEP 440
2. **首次发布**: 如果这是首次发布包名 `moat-ai`，需要在 PyPI 注册
3. **测试发布**: 可以先发布到 TestPyPI: https://test.pypi.org/

```bash
twine upload dist/* -r testpypi
pip install --index-url https://test.pypi.org/simple/ moat-ai
```
