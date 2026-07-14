# Moat 演进计划：从"校验工具"到"自我感知神经系统"

## 📊 当前状态评估

### 已有基础（优势）
- ✅ 插件化检查架构（Check 基类）
- ✅ CodeGraph 集成（语义分析基础）
- ✅ 报告生成器（moat report）
- ✅ 交互式引导（moat init）
- ✅ 清晰的代码结构

### 当前缺失
- ❌ AST 增量感知
- ❌ 痛觉日志标准化（Pain Score）
- ❌ AI 辅助修复
- ❌ 核心业务探测
- ❌ Sidecar 实时感知
- ❌ 知识图谱记忆
- ❌ 插件 API 系统

---

## 🎯 三阶段演进路线图

### 第一阶段：神经突触建设（基础感知）

**目标**：让 Moat 拥有"空间感"

**时间估计**：2-3 周

**核心功能**：
1. **AST 增量感知**（tree-sitter 集成）
2. **痛觉日志标准化**（Pain Score）

**交付物**：
- `moat/ast/` — AST 感知模块
- `moat/pain/` — 痛觉评分模块
- 增强的 `moat check --diff`（增量检查）

---

### 第二阶段：构建免疫循环（反馈与交互）

**目标**：让用户"理性修复"

**时间估计**：3-4 周

**核心功能**：
1. **修复引导**（moat fix --report）
2. **核心业务探测**（moat init 增强）
3. **AI 辅助修复**（--ai-fix 参数）

**交付物**：
- `moat/fix.py` — AI 修复引导器
- `moat/core_areas.py` — 核心业务探测
- 增强的 `moat report --ai-fix`

---

### 第三阶段：进化为"具身智能大脑"

**目标**："伴随式感知"

**时间估计**：4-6 周

**核心功能**：
1. **Sidecar 实时感知**
2. **知识图谱记忆**（.moat/memory.db）
3. **智能进化提示**（架构薄弱点识别）

**交付物**：
- `moat/sidecar.py` — 守护进程
- `moat/memory.py` — 知识记忆模块
- `moat/evolution.py` — 智能进化分析器
- VS Code 插件原型

---

## 🏗️ 架构设计原则

### 规则与逻辑分离（避免维护地狱）

**Rule Engine（规则引擎）**：
```
moat/rules/
├── syntax/          # 语法检查规则
├── semantic/        # 语义检查规则
├── race_condition/  # 竞态检测规则
├── architecture/    # 架构检查规则
└── custom/          # 用户自定义规则
```

**Core（核心骨架）**：
```
moat/
├── cli.py           # CLI 入口
├── runner.py        # 检查调度器
├── ast/             # AST 感知层
├── pain/            # 痛觉评分层
├── fix/             # 修复引导层
├── memory/          # 知识记忆层
└── sidecar/         # 实时感知层
```

**原则**：
1. 核心代码只负责**调度**
2. 具体检查规则放在独立的插件模块
3. 规则报错不影响核心运行
4. 社区可以贡献规则插件

---

## 📋 第一阶段详细设计（神经突触建设）

### 1.1 AST 增量感知

**目标**：
- 构建项目"骨架图"（函数调用图）
- 增量对比（修改前/后 AST）
- 精准影响域分析

**实现方案**：

```python
# moat/ast/builder.py
class ASTBuilder:
    """AST 构建器"""

    def build_project_graph(self) -> dict:
        """
        构建项目骨架图
        Returns:
            {
                "functions": {
                    "func_name": {
                        "file": "path/to/file.py",
                        "line": 42,
                        "calls": ["other_func", "another_func"],
                        "callers": ["caller_func"]
                    }
                }
            }
        """
```

```python
# moat/ast/diff.py
class ASTDiffer:
    """AST 增量对比器"""

    def diff(self, old_code: str, new_code: str) -> list[Change]:
        """
        对比修改前后的 AST
        Returns:
            [
                Change(
                    type="function_modified",
                    function="A",
                    file="src/a.py",
                    line=42,
                    impacts=["B", "C"]  # 影响的调用方
                )
            ]
        """
```

**使用示例**：
```bash
# 构建骨架图（init 时自动执行）
moat ast build

# 检查变更影响
moat check --diff
# 输出：
# 📊 检测到变更:
#   ✏️  修改了: src/api/users.py::get_user (line 42)
#   💡 影响范围:
#     - src/services/auth.py::validate_user (line 15)
#     - src/handlers/profile.py::load_profile (line 28)
#   ⚠️  建议检查: 验证用户鉴权逻辑是否正常
```

---

### 1.2 痛觉日志标准化

**目标**：
- moat report 输出 JSON
- Pain Score 计算
- 危险系数评估

**Pain Score 算法**：

```python
# moat/pain/scorer.py
class PainScorer:
    """痛觉评分器"""

    def calculate(self, error: dict, context: dict) -> float:
        """
        计算错误危险系数（0-100）

        权重规则：
        - 核心业务文件：+30
        - 鉴权/支付逻辑：+40
        - API 端点：+20
        - 竞态条件：+25
        - 语法错误：+15
        - 文档缺失：+5
        """
```

**输出格式**：
```json
{
  "timestamp": "2026-07-07T17:00:00Z",
  "pain_score": 85,
  "level": "CRITICAL",
  "errors": [
    {
      "type": "race_condition",
      "file": "src/auth/session.py",
      "line": 142,
      "message": "pendingMessageRef 缺少时序注释",
      "pain_contribution": 40,
      "impact_scope": ["session_handler", "token_refresh"],
      "fix_suggestion": "添加 @critical 注释说明时序依赖"
    }
  ],
  "summary": {
    "total_pain": 85,
    "critical_areas": ["auth", "payment"],
    "recommended_action": "立即修复"
  }
}
```

**使用示例**：
```bash
# 生成 JSON 报告
moat report --format json

# 生成并复制到剪贴板
moat report --copy --format json

# Pain Score 阈值告警
moat check --max-pain 50
# 如果 Pain Score > 50，立即失败
```

---

## 📋 第二阶段详细设计（免疫循环）

### 2.1 核心业务探测

**增强 moat init**：

```python
# moat/core_areas.py
class CoreAreaDetector:
    """核心业务探测"""

    def detect(self, project_root: Path) -> list[CoreArea]:
        """
        自动检测核心业务区域

        识别模式：
        - 鉴权（auth, login, session, token）
        - 支付（payment, checkout, billing）
        - 数据核心（database, model, repository）
        - API 网关（gateway, router, middleware）
        """
```

**交互流程**：
```
🏰 Moat — 交互式初始化

📊 检测到项目类型: ✓ Python, ✓ TypeScript

🐍 检测到 Python 框架: fastapi

⚡ 核心业务探测:
  检测到以下核心区域:
    ✓ src/auth/         (鉴权)
    ✓ src/payment/      (支付)
    ✓ src/api/          (API 网关)

  请标记敏感级别:
    [1] 极高敏感度（失败立即告警）: auth/*
    [2] 高敏感度（失败警告）: payment/*
    [3] 普通: api/*
```

**配置存储**：
```json
{
  "core_areas": [
    {
      "pattern": "src/auth/**/*.py",
      "sensitivity": "critical",
      "pain_multiplier": 2.0
    },
    {
      "pattern": "src/payment/**/*.py",
      "sensitivity": "high",
      "pain_multiplier": 1.5
    }
  ]
}
```

---

### 2.2 AI 辅助修复

**moat fix --report**：

```bash
# 生成修复补丁
moat fix --report report.json

# 预览修复建议
moat fix --report report.json --dry-run

# 自动应用修复
moat fix --report report.json --apply
```

**工作流**：
```
1. moat check → 失败
2. moat report --copy → 复制报告
3. moat fix --report report.json → AI 分析
4. 生成补丁预览
5. 用户确认 → moat fix --apply
6. 自动应用修复
7. moat check → 验证
```

---

## 📋 第三阶段详细设计（具身智能大脑）

### 3.1 Sidecar 实时感知

**架构**：
```
┌─────────────────────────────────────────────────┐
│                  IDE / Editor                    │
│  ┌─────────────┐  ┌──────────────────────────┐  │
│  │ File Save   │→ │ Moat Sidecar (Daemon)    │  │
│  └─────────────┘  │  - Watch file changes    │  │
│                   │  - Run lightweight checks│  │
│                   │  - Emit pain events      │  │
│                   └──────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

**VS Code 集成**：
```typescript
// vscode-moat-extension/
export class MoatSidecar {
  // 监听文件保存
  vscode.workspace.onDidSaveTextDocument(async (doc) => {
    const pain = await this.checkFile(doc.uri.fsPath);
    this.showPainLens(doc, pain);
  });

  // 悬浮窗展示
  private showPainLens(doc: TextDocument, pain: number) {
    if (pain > 50) {
      this.showErrorDecoration(doc, "🔴 High Pain: " + pain);
    } else if (pain > 20) {
      this.showWarningDecoration(doc, "🟡 Medium Pain: " + pain);
    }
  }
}
```

---

### 3.2 知识图谱记忆

**.moat/memory.db**：
```sql
-- 历史 Bug 记录
CREATE TABLE bugs (
    id TEXT PRIMARY KEY,
    file_path TEXT,
    line INTEGER,
    error_type TEXT,
    pain_score INTEGER,
    fix_count INTEGER,  -- 修复次数
    first_seen TIMESTAMP,
    last_seen TIMESTAMP
);

-- 修复模式
CREATE TABLE fix_patterns (
    id TEXT PRIMARY KEY,
    error_signature TEXT,
    fix_template TEXT,
    success_rate FLOAT,
    usage_count INTEGER
);

-- 架构薄弱点
CREATE TABLE weak_points (
    id TEXT PRIMARY KEY,
    file_path TEXT,
    issue_type TEXT,
    frequency INTEGER,  -- 出现频率
    recommendation TEXT
);
```

**智能提示**：
```
💡 Moat 智能分析:

这个位置 (src/auth/session.py:142) 在最近 30 天内出现了 8 次错误。
这可能是你的架构薄弱点。

建议:
1. 重构 session 管理逻辑
2. 提取公共工具函数
3. 添加单元测试覆盖

是否需要生成重构建议？(y/N)
```

---

## 🚀 立即开始的行动项

### 优先级 1（本周）
1. ✅ 集成 tree-sitter（AST 感知）
2. ✅ 实现 Pain Score 算法
3. ✅ moat check --diff 基础版本

### 优先级 2（下周）
4. ✅ moat report --format json
5. ✅ 核心业务探测（moat init 增强）
6. ✅ moat fix --report 原型

### 优先级 3（未来）
7. Sidecar 守护进程
8. .moat/memory.db
9. VS Code 插件

---

## 💡 关键决策点

### Q1: tree-sitter vs ast（Python 内置）
**建议**：tree-sitter
- ✅ 语言无关（支持 Python/TS/Go/Rust...）
- ✅ 增量解析性能更好
- ✅ 更精确的语法树

### Q2: 守护进程 vs Watchman
**建议**：守护进程
- ✅ 跨平台（Linux/macOS/Windows）
- ✅ 更灵活（可扩展更多功能）
- ⚠️ 需要处理后台进程管理

### Q3: 本地 LLM vs OpenAI API
**建议**：两者都支持
- ✅ 本地 LLM（Ollama）用于隐私场景
- ✅ OpenAI API 用于高质量修复

---

## 📊 成功指标

### 第一阶段成功标准
- [ ] AST 增量对比准确率 > 90%
- [ ] Pain Score 与真实 Bug 相关性 > 80%
- [ ] moat check --diff 速度 < 2s

### 第二阶段成功标准
- [ ] AI 修复建议采纳率 > 60%
- [ ] 用户从报错到修复的时间减少 50%
- [ ] moat fix --apply 成功率 > 70%

### 第三阶段成功标准
- [ ] Sidecar 后台 CPU 占用 < 5%
- [ ] 架构薄弱点识别准确率 > 75%
- [ ] 用户留存率提升 30%

---

**现在开始实施第一阶段！** 🚀
