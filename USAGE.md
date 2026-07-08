# Moat v0.7.0-beta.1 使用指南

## 📦 安装状态

✅ **当前版本**: v0.7.0-beta.1 已安装  
📍 **运行方式**: `python3 -m moat`（还未安装到全局 PATH）

---

## 🚀 三种使用方式

### 方式 1: 直接使用（当前）

```bash
# 通过 python -m 运行
python3 -m moat --help
python3 -m moat check
python3 -m moat verify --all
```

**优点**: 无需额外安装，直接可用  
**缺点**: 命令较长

---

### 方式 2: 创建别名（推荐）

在 shell 配置文件中添加别名：

```bash
# Bash/Zsh
echo 'alias moat="python3 -m moat"' >> ~/.bashrc
# 或
echo 'alias moat="python3 -m moat"' >> ~/.zshrc

# 重新加载配置
source ~/.bashrc  # 或 source ~/.zshrc

# 现在可以直接使用
moat --help
moat check
```

**优点**: 简单快捷，全局可用  
**缺点**: 需要手动配置

---

### 方式 3: 安装到全局（正式使用）

```bash
# 安装到用户目录（无需 sudo）
pip3 install --user -e .

# 或安装到系统目录（需要 sudo）
sudo pip3 install -e .
```

**优点**: 像正常命令一样使用 `moat`  
**缺点**: 需要安装依赖

---

## 📖 常用命令

### 1. 初始化项目

```bash
# 进入你的项目
cd your-project

# 运行初始化
python3 -m moat init

# 如果有 .claude 目录，会询问：
# 🤖 Claude Code 集成:
# 是否将 Moat 守护进程集成至 Claude Code？(Y/n): y
# ✓ Claude Code Hook 已启用
# ✓ 已生成 .claude/settings.json
```

**生成的文件**:
- `.moat/config.json` — 项目配置
- `.moat/claude.md` — AI 适配规则
- `.moat/baseline.json` — 基线数据
- `.claude/settings.json` — Claude Code Hook 配置（可选）

---

### 2. 运行检查

```bash
# 完整检查（四层门禁）
python3 -m moat check

# 增量检查（只检查变更）
python3 -m moat check --diff

# 只检查特定项目
python3 -m moat check --project /path/to/project
```

---

### 3. 架构验收（v0.7.0-beta 新功能）

```bash
# 完整验收（7个算子）
python3 -m moat verify --all

# 单个算子
python3 -m moat verify --operator api_response_spec
python3 -m moat verify --operator framework_usage
python3 -m moat verify --operator directory_responsibility

# JSON 输出（用于 CI/CD）
python3 -m moat verify --json

# 评分低于 60 分则失败（用于 CI/CD）
python3 -m moat verify --fail-on-score 60

# 详细输出
python3 -m moat verify --verbose
```

**7个算子**:
1. `directory_responsibility` — 目录责任验收
2. `minimal_module_drill` — 最小模块演练
3. `api_response_spec` — 接口响应规范验收 ⭐ 新增强
4. `framework_usage` — 框架利用检查 ⭐ 新增强
5. `runtime_evidence` — 运行证据包生成
6. `architecture_health_score` — 架构健康度评分
7. `truth_document` — 实施真元文档生成

---

### 4. 守门系统

```bash
# 列出所有规则
python3 -m moat gatekeeper rules

# 检查单个文件
python3 -m moat gatekeeper check --file api/users.py

# 启动守护进程（待实现）
python3 -m moat gatekeeper start
```

---

### 5. 其他命令

```bash
# 实时监控日志
python3 -m moat watch --log logs/backend.log

# 生成报告
python3 -m moat report
python3 -m moat report --copy  # 复制到剪贴板

# AI 辅助修复
python3 -m moat fix

# 进化指标
python3 -m moat evolution report

# 基线管理
python3 -m moat baseline show
```

---

## 🎯 快速开始示例

### 示例 1: 在你的项目中使用

```bash
# 1. 进入项目
cd ~/my-project

# 2. 初始化
python3 -m moat init

# 3. 运行检查
python3 -m moat check

# 4. 架构验收
python3 -m moat verify --all
```

### 示例 2: 查看 API 端点扫描结果

```bash
python3 -m moat verify --operator api_response_spec

# 输出示例：
# 🔍 检查接口响应规范...
#     发现 5 个API文件
#         扫描 12 个端点
#              ✅ GET /users (200)
#              ✅ POST /users (201)
#              ⚠️  GET /profile (缺少 response_model)
```

### 示例 3: 查看框架特性检测

```bash
python3 -m moat verify --operator framework_usage

# 输出示例：
# 🔍 检查框架能力利用...
#     扫描 15 个Python文件...
#     检测到 1 个框架
#     违规:
#         - 未使用框架推荐机制: FastAPI Depends (依赖注入)
#           文件: api/routes.py
#           建议: 使用 Depends() 实现鉴权依赖
```

---

## 🤖 Claude Code Hook 使用

### 自动生成配置

```bash
moat init
# 会询问是否集成 Claude Code
# 输入 y 即可自动生成 .claude/settings.json
```

### 生成的配置

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "moat gatekeeper check --file ${file}",
        "timeout": 5000
      }]
    }],
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "moat check --diff",
        "timeout": 10000
      }]
    }]
  }
}
```

**效果**:
- **PreToolUse**: Claude Code 写文件前自动检查架构规则
- **PostToolUse**: Claude Code 写文件后自动运行增量检查

---

## 📦 正式安装（可选）

如果你想全局使用 `moat` 命令：

```bash
# 方式 1: 安装到用户目录
pip3 install --user -e /Users/mac/Desktop/moat

# 方式 2: 创建符号链接
ln -s /Users/mac/Desktop/moat/moat/__main__.py /usr/local/bin/moat
chmod +x /usr/local/bin/moat

# 现在可以直接使用
moat --help
moat check
```

---

## ❓ 常见问题

### Q1: 为什么 `moat` 命令找不到？

**A**: 当前版本未安装到全局，使用：
```bash
python3 -m moat
```

或创建别名：
```bash
alias moat="python3 -m moat"
```

### Q2: 如何更新到最新版本？

**A**: 从 GitHub 拉取最新代码：
```bash
cd /Users/mac/Desktop/moat
git pull origin main
```

### Q3: 算子扫描不到我的 API？

**A**: 算子默认扫描以下目录：
- `api/**/*.py`
- `app/**/*.py`
- `routers/**/*.py`
- `**/routes.py`
- `**/views.py`

如果你的 API 文件在其他位置，可以手动指定项目路径：
```bash
python3 -m moat verify --operator api_response_spec --project /your/project
```

### Q4: Claude Code Hook 不生效？

**A**: 检查：
1. `.claude/settings.json` 是否存在
2. Claude Code 是否支持 Hooks（需要 Claude Code 0.2.0+）
3. 配置格式是否正确

---

## 📚 更多资源

- **完整文档**: https://github.com/wang-jie-git/moat
- **更新日志**: CHANGELOG.md
- **架构验收方法**: ARCHITECTURAL_AUDIT_PROTOCOL.md
- **问题反馈**: https://github.com/wang-jie-git/moat/issues

---

**版本**: v0.7.0-beta.1  
**安装状态**: ✅ 可用（通过 python3 -m moat）
