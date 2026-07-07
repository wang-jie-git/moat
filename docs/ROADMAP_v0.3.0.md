# Moat v0.3.0 开发计划

## 目标
实现三个高优先级功能，将 Moat 从"校验工具"升级为完整的 AI 编码助手生态系统。

## 功能清单

### 1. `moat fix --report`（AI 辅助修复原型）
**状态**: 🔄 进行中
**优先级**: P0

#### 目标
- 读取 `moat report` 生成的错误报告
- 为每个错误提供 AI 修复建议
- 支持自动修复简单问题
- 生成修复 PR 描述

#### 实现步骤
- [x] 创建 `moat/fixer.py`（修复引擎）
- [x] 创建 `moat/fix_strategies.py`（修复策略库）
- [ ] 添加 `moat fix` 命令到 CLI
- [ ] 集成 AI 建议生成
- [ ] 添加 `--dry-run` 模式
- [ ] 编写测试

#### 技术细节
- 复用 `report.py` 的错误分析逻辑
- 为每种错误类型定义修复策略
- 使用 LLM 生成修复建议（可选）
- 支持 Python/TypeScript 常见模式

---

### 2. Sidecar 守护进程（实时感知）
**状态**: ⏳ 待开始
**优先级**: P0

#### 目标
- 后台运行，监控文件变化
- 实时运行增量检查
- 提供 WebSocket/HTTP API
- 支持 VS Code 插件集成

#### 实现步骤
- [ ] 创建 `moat/sidecar/` 目录
- [ ] 实现 `moat/sidecar/daemon.py`（守护进程）
- [ ] 实现 `moat/sidecar/watcher.py`（文件监听）
- [ ] 实现 `moat/sidecar/api.py`（HTTP/WebSocket API）
- [ ] 添加 `moat sidecar` 命令
- [ ] 实现健康检查端点
- [ ] 编写测试

#### 技术细节
- 使用 `watchdog` 监控文件变化
- FastAPI 提供 REST API
- WebSocket 推送实时结果
- PID 文件 + 日志文件管理
- 支持 `--daemon` / `--foreground` 模式

---

### 3. VS Code 插件（编辑器集成）
**状态**: ⏳ 待开始
**优先级**: P1

#### 目标
- 在编辑器中显示错误
- 一键运行检查
- 实时反馈
- 支持 AI 修复建议

#### 实现步骤
- [ ] 创建 `vscode-moat/` 目录
- [ ] 初始化 VS Code 插件项目
- [ ] 实现 `extension.ts`（主入口）
- [ ] 实现诊断提供者
- [ ] 实现命令（`moat.check`, `moat.fix`）
- [ ] 集成 Sidecar API
- [ ] 添加配置选项
- [ ] 编写文档

#### 技术细节
- TypeScript + VS Code Extension API
- 通过 Sidecar API 与 Moat 通信
- 使用 VS Code Diagnostics API 显示错误
- 支持快速修复（Code Actions）

---

## 时间估算
- **功能 1**: 4-6 小时
- **功能 2**: 6-8 小时
- **功能 3**: 8-12 小时
- **总计**: 18-26 小时

## 依赖关系
```
功能 1（独立）
功能 2（独立，但功能 3 依赖它）
功能 3（依赖功能 2）
```

## 建议实施顺序
1. **功能 1**：独立性强，能快速带来价值
2. **功能 2**：为功能 3 提供基础设施
3. **功能 3**：最后实现，确保 Sidecar 稳定

## 成功标准
- [ ] `moat fix --help` 可用
- [ ] `moat sidecar start` 能后台运行
- [ ] VS Code 插件能在市场中安装
- [ ] 所有新功能都有测试覆盖
- [ ] 文档更新完整
