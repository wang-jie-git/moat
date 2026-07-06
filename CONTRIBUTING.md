# Contributing to Moat

感谢你对 Moat 的兴趣! 🎉

Moat 是一个开源项目,欢迎各种形式的贡献。

## 🚀 快速开始

### 环境准备

```bash
# 1. Fork & Clone
git clone https://github.com/YOUR_USERNAME/moat.git
cd moat

# 2. 安装依赖
cd moat
pip install -e ".[dev]"  # 开发模式安装

# 3. 运行测试
python -m pytest tests/ -v
```

### 开发工作流

```bash
# 1. 创建功能分支
git checkout -b feat/your-feature

# 2. 修改代码 + 编写测试

# 3. 运行 Moat 自检
python -m moat check

# 4. 运行测试
pytest tests/

# 5. Commit (pre-commit hook 会自动跑测试)
git commit -m "feat: add your feature"

# 6. Push & Pull Request
git push origin feat/your-feature
```

## 📝 贡献方式

### 报告 Bug

使用 [Bug Report Template](https://github.com/wang-jie-git/moat/issues/new?template=bug_report.md)

请提供:
- Moat 版本 (`moat --version`)
- Python 版本 (`python --version`)
- 操作系统
- 复现步骤
- 错误日志

### 请求新功能

使用 [Feature Request Template](https://github.com/wang-jie-git/moat/issues/new?template=feature_request.md)

请提供:
- 功能描述
- 使用场景
- 可能的实现方案

### 提交代码

1. Fork 项目
2. 创建功能分支 (`git checkout -b feat/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feat/amazing-feature`)
5. 开启 Pull Request

### 代码规范

- 遵循 [PEP 8](https://peps.python.org/pep-0008/)
- 添加类型提示
- 编写测试
- 更新文档

## 🤝 行为准则

请参阅 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## 📄 许可证

贡献的代码将遵循 MIT 许可证。

---

感谢你的贡献! 🙏
