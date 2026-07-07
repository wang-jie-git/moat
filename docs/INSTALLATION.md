# 📦 安装指南

## 快速开始

### 方法 1: 一键安装（推荐）

```bash
# 安装所有功能
pip install "moat-ai[all]"
```

### 方法 2: 交互式安装

```bash
# 运行交互式安装脚本
curl -fsSL https://raw.githubusercontent.com/wang-jie-git/moat/main/scripts/install.sh | bash
```

或手动下载：

```bash
curl -O https://raw.githubusercontent.com/wang-jie-git/moat/main/scripts/install.sh
chmod +x install.sh
./install.sh
```

### 方法 3: 基础安装

```bash
# 仅核心功能（最小依赖）
pip install moat-ai
```

---

## 安装选项

### 完整安装（推荐）

```bash
pip install "moat-ai[all]"
```

**包含**:
- ✅ Web 看板（FastAPI + 前端界面）
- ✅ Sidecar 守护进程（实时文件监控 + REST API）
- ✅ VS Code 插件辅助（剪贴板复制）

### 按需安装

```bash
# Web 看板
pip install "moat-ai[dashboard]"

# Sidecar 守护进程
pip install "moat-ai[sidecar]"

# VS Code 插件辅助
pip install "moat-ai[vscode]"

# 组合示例
pip install "moat-ai[dashboard,sidecar]"
```

### 从 GitHub 安装最新版

```bash
# 基础版
pip install git+https://github.com/wang-jie-git/moat.git

# 完整版
pip install "git+https://github.com/wang-jie-git/moat.git[all]"

# 指定版本
pip install git+https://github.com/wang-jie-git/moat.git@v0.4.0
```

---

## 功能对比

| 功能 | 基础安装 | 完整安装 |
|------|---------|---------|
| 四层门禁检查 | ✅ | ✅ |
| Pain Score 评分 | ✅ | ✅ |
| AST 增量感知 | ✅ | ✅ |
| AI 辅助修复 | ✅ | ✅ |
| 进化指标系统 | ✅ | ✅ |
| Web 看板 | ❌ | ✅ |
| Sidecar 文件监控 | ❌ | ✅ |
| Sidecar REST API | ❌ | ✅ |
| 剪贴板复制 | ❌ | ✅ |
| **依赖大小** | ~5MB | ~50MB |

---

## 系统要求

### 必需

- Python 3.10+
- pip 或 pip3

### 核心依赖（自动安装）

- httpx >= 0.27

### 可选依赖

| 依赖 | 版本 | 功能 | 大小 |
|------|------|------|------|
| watchdog | >= 3.0 | 文件监控 | ~5MB |
| fastapi | >= 0.100 | Web 框架 | ~20MB |
| uvicorn | >= 0.22 | ASGI 服务器 | ~5MB |
| pyperclip | >= 1.8 | 剪贴板 | ~1MB |

---

## 验证安装

### 1. 检查版本

```bash
moat --version
# 输出: Moat v0.4.0
```

### 2. 查看帮助

```bash
moat --help
```

### 3. 运行验证脚本

```bash
# 下载验证脚本
curl -O https://raw.githubusercontent.com/wang-jie-git/moat/main/scripts/verify_install.py

# 运行验证
python3 verify_install.py
```

### 4. 测试核心功能

```bash
# 初始化项目
cd your-project
moat init

# 运行检查
moat check

# 查看进化报告
moat evolution report
```

---

## 开发模式安装

### 从源码安装

```bash
# 1. 克隆仓库
git clone https://github.com/wang-jie-git/moat.git
cd moat

# 2. 创建虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 3. 安装开发模式
pip install -e ".[all]"

# 4. 安装测试依赖
pip install -r requirements-dev.txt

# 5. 运行测试
pytest tests/
```

### 无虚拟环境安装（开发）

```bash
pip install -e .
```

---

## 常见问题

### Q: pip install 失败（权限不足）

**A**: 使用 `--user` 标志或虚拟环境

```bash
# 方法 1: 用户安装
pip install --user moat-ai

# 方法 2: 虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate
pip install moat-ai
```

### Q: moat 命令未找到

**A**: 检查 PATH 或使用 python -m

```bash
# 方法 1: 检查 PATH
echo $PATH | grep $(python3 -m site --user-base)/bin

# 方法 2: 使用 python -m
python3 -m moat check
```

### Q: 如何更新 Moat？

**A**:

```bash
# 升级到最新版
pip install --upgrade moat-ai

# 或从 GitHub 升级
pip install --upgrade git+https://github.com/wang-jie-git/moat.git
```

### Q: 如何卸载？

**A**:

```bash
# 卸载
pip uninstall moat-ai

# 卸载并清理配置文件
pip uninstall moat-ai
rm -rf ~/.moat
rm -rf .moat
```

### Q: Sidecar 启动失败（watchdog 未安装）

**A**: 安装 watchdog 依赖

```bash
pip install "moat-ai[sidecar]"
# 或
pip install watchdog
```

### Q: Web 看板无法启动（fastapi 未安装）

**A**: 安装完整依赖

```bash
pip install "moat-ai[all]"
# 或
pip install fastapi uvicorn
```

---

## 安装脚本说明

### install.sh

交互式安装脚本，支持：

1. **基础安装** — 核心功能
2. **完整安装** — 所有功能
3. **自定义安装** — 按需选择

```bash
# 下载并运行
curl -fsSL https://raw.githubusercontent.com/wang-jie-git/moat/main/scripts/install.sh | bash
```

### verify_install.py

验证安装脚本，检查：

- ✅ Python 版本
- ✅ 依赖状态
- ✅ 核心模块
- ✅ 可选功能

```bash
python3 scripts/verify_install.py
```

---

## 下一步

安装完成后：

1. **初始化项目**
   ```bash
   moat init
   ```

2. **运行检查**
   ```bash
   moat check
   ```

3. **查看进化报告**
   ```bash
   moat evolution report
   ```

4. **获取修复建议**
   ```bash
   moat fix
   ```

5. **启动 Sidecar**（需要额外依赖）
   ```bash
   pip install "moat-ai[sidecar]"
   moat sidecar start
   ```

6. **启动 Web 看板**（需要额外依赖）
   ```bash
   pip install "moat-ai[dashboard]"
   moat dashboard
   ```

---

## 相关链接

- **GitHub**: https://github.com/wang-jie-git/moat
- **PyPI**: https://pypi.org/project/moat-ai/
- **文档**: https://github.com/wang-jie-git/moat/tree/main/docs
- **Issues**: https://github.com/wang-jie-git/moat/issues
- **Release**: https://github.com/wang-jie-git/moat/releases/tag/v0.4.0
