# moat-memory 设计方案

## 现状分析

### moat 现有记忆系统

```
仓库: github.com/wang-jie-git/moat  版本: v1.1.10
路径: /Users/mac/Desktop/moat/
```

已有模块 | 功能 | 与 moat-memory 的关系
--------|------|---------------------
`moat/memory/bridge.py` | SQLite 共享存储，含 12 张表（bug_memories, fix_history, weak_points, insights, fix_patterns, smart_hints 等） | 复用其 SQLite 基础设施，扩展表结构
`moat/memory/filter.py` | 记忆写入过滤器（pain score 阈值、去重） | 复用其过滤逻辑
`moat/memory/sync.py` | 与 One Memory 双向同步 | 保留不动，与 moat-memory 正交
`moat/adapters/` | 安装到 CLAUDE.md / .cursor/rules.mdc | 扩展：加入 memory 读取指令

### 缺失的部分

当前 moat 的记忆只记录了 **bug 和 fix**（pain score 驱动）。缺少：

| 类型 | 当前 | 目标 |
|------|------|------|
| 红线 (redlines) | `.moat/moat.json` 有 5 条自动探测规则，但 AI 读不到 | 写入 memory.db + adapter 注入 AI 上下文 |
| 踩坑 (lessons) | 只有 bug_memories 表（pain score 过滤，门槛高） | 记录每次 check 失败作为轻量级 lessons |
| 模版 (templates) | 不存在 | 从 git diff + check 通过合成经验模版 |
| 技能 (skills) | `moat init` 生成 CLAUDE.md 引用 | 增量更新，保持同步 |

---

## 设计

### 一、新表结构（扩展 memory.db）

向 `SharedStorageBridge._create_tables()` 新增 4 张表：

```sql
-- 红线：项目特定的架构规则
CREATE TABLE IF NOT EXISTS redlines (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,              -- 红线标题
    description TEXT NOT NULL,         -- 具体描述
    severity TEXT DEFAULT 'warning',   -- 'critical' | 'warning' | 'info'
    category TEXT DEFAULT 'general',   -- 'architecture' | 'security' | 'style' | 'dependency'
    source TEXT DEFAULT 'auto',        -- 'auto' | 'manual' | 'template'
    file_glob TEXT,                    -- 适用文件（可选）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 踩坑：每次 check 失败的结构化记录
CREATE TABLE IF NOT EXISTS lessons (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,              -- 简短标题
    failed_tests TEXT NOT NULL,       -- JSON 数组：失败测试列表
    error_summary TEXT NOT NULL,      -- 错误摘要
    failure_count INTEGER DEFAULT 1,
    principles TEXT,                  -- JSON 数组：应该遵守的原则
    negative_examples TEXT,           -- JSON 数组：不该做的事
    content_hash TEXT,                -- 去重哈希
    captured_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 模版：经验总结 / 思维框架
CREATE TABLE IF NOT EXISTS templates (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,             -- 领域（如：api_design, error_handling）
    title TEXT NOT NULL,              -- 模版标题
    source TEXT DEFAULT 'manual',     -- 'manual' | 'auto_extracted'
    elements TEXT,                    -- JSON 对象：核心要素
    principles TEXT,                  -- JSON 数组：设计原则
    negative_examples TEXT,           -- JSON 数组：反模式
    tags TEXT,                        -- JSON 数组：标签
    importance INTEGER DEFAULT 5,     -- 1-10
    content_hash TEXT,                -- 去重哈希
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AI 工具技能：告诉 AI 如何与 moat 互动
CREATE TABLE IF NOT EXISTS skills (
    id TEXT PRIMARY KEY,
    tool TEXT NOT NULL,               -- 'claude' | 'codex' | 'opencode' | 'cursor'
    instruction TEXT NOT NULL,         -- 具体指令
    priority INTEGER DEFAULT 0,       -- 优先级（高优先先注入）
    is_active INTEGER DEFAULT 1,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 二、数据来源

记忆类型 | 谁产生 | 何时产生
---------|--------|---------
**红线** | moat init 自动探测 + `moat redline add` 手动 | init 时创建，后续手动补充
**踩坑** | `moat check` 失败时自动 | 每次 check 失败
**模版** | `moat template extract` 从 git diff 合成 | 手动触发
**技能** | `moat adapter install` 时同步 | 安装适配器时

### 三、CLI 命令

```
moat memory                 查看记忆统计概览
moat memory list <type>     列出某类记忆（redlines / lessons / templates / skills）
moat memory show <id>       查看单条记忆详情
moat memory delete <id>     删除记忆

moat redline add            手动添加红线
moat redline remove <id>    删除红线

moat template extract       从 git diff 合成为经验模版
moat template import <file> 导入外部模版

moat adapter install        安装/更新适配器（包括插入 memory 读取指令）
```

### 四、AI 工具读取链路

修改 `moat/adapters/`，在生成的 CLAUDE.md 和 .cursor/rules.mdc 中加入：

```
## moat-memory 项目记忆
这个项目有以下记忆可供参考（.moat/memory.db）：

1. 红线 — 项目架构规则和编码边界
2. 踩坑 — 之前 MOAT 检查失败的历史
3. 模版 — 项目积累的经验总结

改代码前，运行以下命令查看相关记忆：
  moat memory list redlines  # 红线
  moat memory list lessons   # 踩坑
  moat memory list templates # 模版
```

这样 AI 工具启动时就能看到 moat 的记忆提示，并通过 `moat memory` CLI 命令读取具体内容。

### 五、实现步骤

| 步骤 | 文件 | 改动 |
|------|------|------|
| 1 | `moat/memory/bridge.py` | 新增 4 张表 + CRUD 方法 |
| 2 | `moat/memory/moat_memory.py`（新文件） | 高层封装：write_lesson, get_redlines 等 |
| 3 | `moat/runner.py` | check 失败后自动 `write_lesson()` |
| 4 | `moat/cli.py` | 新增 `cmd_memory`, `cmd_redline`, `cmd_template` |
| 5 | `moat/adapters/` | 更新生成的指令，加入 memory 读取提示 |
| 6 | `moat/discovery.py` | init 时预置几条通用红线 |

### 六、不做的事

- 不与 One Memory 的 sync.py 耦合（moat-memory 是 moat 自有的记忆，独立运行）
- 不引入新的 Python 依赖（只用 sqlite3）
- 不改动已有的 bug_memories / fix_history 表（向下兼容）
