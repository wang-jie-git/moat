# 🧠 进化指标系统 — 防止"神经衰弱"

## 📖 背景

Gemini 在评估 Moat 时提出了一个深刻的洞察：

> "如果系统自我优化的结果是越来越保守（比如把所有稍微复杂点的代码都标记为 Critical 阻断，导致开发效率下降），那它就陷入了**'神经衰弱'**。
> 所以，下一步进化的重点是：**定义好 '进化指标'**。"

---

## 🎯 核心问题

Moat 的现有架构已经具备：
- ✅ **自我感知**（Pain Score + AST 骨架图）
- ✅ **自我记忆**（SQLite 共享存储）
- ✅ **自我进化**（元知识反向驱动）

但缺少一个关键能力：
- ⚠️ **自我评估**（知道什么是"好的进化"）

如果没有进化指标，系统可能会：
1. **过度保守**：误报率上升 → 所有代码都被拦截 → 开发停滞
2. **过度激进**：忽略潜在风险 → 引入新 Bug
3. **方向迷失**：优化了错误的目标 → 开发效率下降

---

## ✅ 解决方案：六大进化指标

### 1. 重构成功率（Refactor Success Rate）✅
**含义**: 重构后测试通过且 Pain Score 降低的比例

**目标**: > 70%

**采集方式**:
```python
from moat.evolution_metrics import EvolutionTracker

tracker = EvolutionTracker(Path(".moat"))
tracker.record_refactor_success(
    files_changed=5,
    tests_passed=True,
    pain_score_before=65.0,
    pain_score_after=25.0
)
```

---

### 2. 性能提升率（Performance Improvement Rate）🚀
**含义**: 代码优化带来的性能改善

**目标**: > 50%（平均）

**示例**:
```python
tracker.record_performance_improvement(
    metric_name="api_response_time",
    before=250.0,  # 250ms
    after=80.0     # 80ms
)
```

---

### 3. Bug 修复时效（Bug Fix Time）🐛
**含义**: 从 Bug 发现到修复的耗时

**目标**: < 4 小时（高严重性 Bug）

**逻辑**: 修复越快得分越高，严重 Bug 加权

---

### 4. 误报率（False Positive Rate）⚠️
**含义**: Moat 误报的比例（**负向指标**）

**目标**: < 20%

**为什么是负向指标？**
- 误报本身不是坏事
- 但**持续的、大量的误报**意味着系统"过度反应"
- 这是"神经衰弱"的前兆

---

### 5. 开发效率（Dev Velocity）⚡
**含义**: 代码提交频率、PR 合并速度等

**目标**: 不下降（与历史基线对比）

**建议**: 通过 Git hooks 或 CI 集成采集

---

### 6. Pain Score 趋势📈
**含义**: 项目整体 Pain Score 的变化趋势

**采集方式**: 自动（每次 `moat check` 后）

**趋势分析**:
- 持续下降 = 正向 ✅
- 持续上升 = 负向 ⚠️
- 波动 = 正常 👍

---

## 🧠 "神经衰弱"检测机制

### 检测逻辑

```python
evaluation = tracker.evaluator.evaluate_evolution()

negative_ratio = evaluation["fatigue_status"]["negative_ratio"]
# 综合负向维度和负向权重的影响

if negative_ratio >= 0.5:
    status = "critical"  # 神经衰弱严重
elif negative_ratio >= 0.3:
    status = "warning"   # 趋向保守
elif negative_ratio <= 0.15:
    status = "encourage" # 鼓励创新
```

### 三态策略

#### 🔴 神经衰弱严重（负向占比 ≥ 50%）
**问题**: 系统过度拦截，开发效率骤降

**应对**:
- 降低 Pain Score 阈值（50 → 40）
- 提高误报容忍度（允许 3 次误报后再调整）

#### 🟡 趋向保守（负向占比 30-50%）
**问题**: 系统开始过度谨慎

**应对**:
- 轻微降低核心业务/鉴权类错误的权重（-5）

#### 🟢 鼓励创新（负向占比 ≤ 15%）
**问题**: 进化方向良好，可以更加大胆

**应对**:
- 降低对实验性代码的拦截强度
- 启用"创新模式"

---

## 📊 CLI 使用

### 查看进化报告
```bash
# 最近 24 小时
moat evolution report

# 最近 7 天
moat evolution report --window 168

# JSON 输出
moat evolution report --format json
```

**输出示例**:
```
============================================================
  进化指标报告
  时间窗口: 24 小时
============================================================

📊 综合得分: 0.723 / 1.000

📈 各维度得分:
   🟢 refactor_success: 0.85
   🟢 performance_improvement: 0.72
   🟡 bug_fix_time: 0.45
   🔴 false_positive_rate: 0.12  # 低分（误报少）是好事

🧠 神经衰弱检测:
   状态: normal
   负向指标占比: 12.5%
   👍 进化状态正常

💡 建议:
   🟢 [enable_innovation_mode] 鼓励创新：降低对实验性代码的拦截强度

============================================================
```

### 自动调整配置
```bash
moat evolution adjust --auto
```

### 手动记录指标
```bash
# 记录一次重构成功
moat evolution record --metric-type refactor_success --value 0.85
```

---

## 🔄 集成到现有架构

### 1. 集成到 `moat check`

```python
# 在 runner.py 中添加
from moat.evolution_metrics import EvolutionTracker

def run_all_checks(project_root: str = ".") -> bool:
    tracker = EvolutionTracker(Path(project_root) / ".moat")

    # ... 原有检查逻辑 ...

    # 检查完成后记录 Pain Score 趋势
    avg_pain = sum(s["score"] for s in pain_scores) / len(pain_scores)
    tracker.record_pain_score_trend(avg_pain)

    # 评估进化方向
    evaluation = tracker.evaluator.evaluate_evolution()
    if evaluation["fatigue_status"]["status"] in ["warning", "critical"]:
        print(f"⚠️  {evaluation['fatigue_status']['message']}")
```

### 2. 集成到 Feedback Loop

```python
# 在 feedback.py 中添加
from moat.evolution_metrics import EvolutionTracker

def add_feedback(self, error_type, file_pattern, user_rating, context=None):
    # ... 原有反馈逻辑 ...

    # 同步到进化指标
    if user_rating == "false_positive":
        self.tracker.record_false_positive(error_type, file_pattern)
```

### 3. 集成到 CI/CD

```yaml
# .github/workflows/evolution-check.yml
- name: Check Evolution Health
  run: |
    pip install moat
    moat evolution report --window 168

    # 如果神经衰弱严重，失败
    if moat evolution report --format json | grep -q "critical"; then
      echo "❌ 系统神经衰弱严重，需要人工介入"
      exit 1
    fi
```

---

## 📈 使用场景

### 场景 1: 每日站会
```bash
# 查看过去 24 小时的进化报告
moat evolution report

# 判断今天是否应该鼓励团队创新
# 还是需要收紧质量管控
```

### 场景 2: 迭代回顾
```bash
# 查看过去 7 天的进化趋势
moat evolution report --window 168

# 评估这个迭代的质量 vs 效率平衡
```

### 场景 3: 自动告警
```yaml
# GitHub Actions
- name: Evolution Alert
  run: |
    STATUS=$(moat evolution report --format json | jq -r '.fatigue_status.status')
    if [ "$STATUS" = "critical" ]; then
      # 发送告警到 Slack/Email
      curl -X POST $SLACK_WEBHOOK -d "⚠️ Moat 神经衰弱严重！"
    fi
```

---

## 🎯 关键设计决策

### Q1: 为什么误报率是负向指标？

**A**: 误报本身不是坏事，但**持续的、大量的误报**意味着系统在"过度反应"，这是"神经衰弱"的前兆。

### Q2: 如何定义"好的进化"？

**A**: 六大指标的平衡：
- **重构成功率** > 0.7
- **性能提升率** > 0.5
- **Bug 修复时效** < 4 小时
- **误报率** < 0.2
- **开发效率** 不下降

### Q3: 如何避免"过度优化"？

**A**: 进化指标系统会检测"过拟合"：
- 连续 7 天负向指标上升 → 警告
- 连续 30 天负向指标上升 → 触发自动调整

---

## 📚 相关文档

- **集成指南**: `docs/EVOLUTION_METRICS_GUIDE.md`
- **Moat 反馈机制**: `moat/pain/feedback.py`
- **进化引擎**: `moat/evolution.py`
- **One Memory 梦境引擎**: https://github.com/wang-jie-git/one-memory

---

## 🚀 下一步

- [ ] **短期**（1-2 天）：集成到 `moat check`，自动采集 Pain Score 趋势
- [ ] **中期**（1 周）：实现自动调整配置（根据进化指标动态调整阈值）
- [ ] **长期**（2 周）：与 One Memory 梦境引擎深度集成，让 Insight 直接驱动进化指标

---

**记住**: 进化的方向性比进化速度更重要。🚀
