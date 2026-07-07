# 进化指标系统集成指南

## 🎯 核心价值

解决 Gemini 提出的"神经衰弱"问题：防止系统自我进化时变得越来越保守。

---

## 📊 六大进化指标

### 1. 重构成功率（Refactor Success Rate）✅
**含义**: 重构后测试通过且 Pain Score 降低的比例

**采集方式**:
```python
from moat.evolution_metrics import EvolutionTracker

tracker = EvolutionTracker(Path(".moat"))

# 重构完成后记录
tracker.record_refactor_success(
    files_changed=5,
    tests_passed=True,
    pain_score_before=65.0,
    pain_score_after=25.0,
    context={"refactor_type": "extract_method"}
)
```

**评分逻辑**:
- 测试通过：+0.5 分
- Pain Score 降低：+0-0.5 分（根据改善比例）
- 满分：1.0

---

### 2. 性能提升率（Performance Improvement Rate）🚀
**含义**: 代码优化带来的性能改善

**采集方式**:
```python
# 性能优化后记录
tracker.record_performance_improvement(
    metric_name="api_response_time",
    before=250.0,  # 250ms
    after=80.0,    # 80ms
    unit="ms",
    context={"endpoint": "/api/users"}
)
```

**评分逻辑**:
- 提升比例 = (before - after) / before
- 满分：提升 100%+（性能翻倍）

---

### 3. Bug 修复时效（Bug Fix Time）🐛
**含义**: 从 Bug 发现到修复的耗时

**采集方式**:
```python
# Bug 修复后记录
tracker.record_bug_fix(
    bug_type="race_condition",
    fix_time_seconds=7200,  # 2 小时
    pain_score=75.0,
    context={"severity": "high"}
)
```

**评分逻辑**:
- 1 小时内修复：1.0 分
- 24 小时后修复：0.0 分
- 严重 Bug 加权（Pain Score 越高，修复得分越高）

---

### 4. 误报率（False Positive Rate）⚠️
**含义**: Moat 误报的比例（负向指标）

**采集方式**:
```python
# 用户标记误报时记录
tracker.record_false_positive(
    error_type="race_condition",
    file_path="src/utils.py",
    context={"user_comment": "这是合法的缓存更新逻辑"}
)
```

**负向权重**: -0.15（误报会降低总体得分）

---

### 5. 开发效率（Dev Velocity）⚡
**含义**: 代码提交频率、PR 合并速度等

**采集方式**（建议通过 Git hooks 或 CI 集成）:
```python
# 每日统计
tracker.record_dev_velocity(
    commits_count=15,
    prs_merged=3,
    avg_pr_review_time_hours=4.5,
    context={"team_size": 5}
)
```

**评分逻辑**:
- 基于历史基线计算相对效率
- 0-1 分

---

### 6. Pain Score 趋势📈
**含义**: 项目整体 Pain Score 的变化趋势

**自动采集**: 每次 `moat check` 后自动记录

**趋势分析**:
- 持续下降 = 正向 ✅
- 持续上升 = 负向 ⚠️
- 波动 = 正常 👍

---

## 🧠 "神经衰弱"检测机制

### 检测逻辑

```python
evaluation = tracker.evaluator.evaluate_evolution(window_hours=24)

# 负向指标占比计算
negative_ratio = (
    abs(false_positive_weight * false_positive_score) /
    total_absolute_weights
)

# 状态判断
if negative_ratio >= 0.5:
    status = "critical"  # 神经衰弱严重
elif negative_ratio >= 0.3:
    status = "warning"   # 趋向保守
elif negative_ratio <= 0.3:
    status = "encourage" # 鼓励创新
```

### 应对策略

#### 🔴 神经衰弱严重（负向占比 ≥ 50%）
```json
{
  "actions": [
    {
      "action": "reduce_pain_threshold",
      "priority": "high",
      "config_change": {"pain_threshold": 40}
    },
    {
      "action": "increase_false_positive_tolerance",
      "priority": "high",
      "config_change": {"false_positive_tolerance": 3}
    }
  ]
}
```

**效果**: 降低 Pain Score 阈值，允许更多代码通过检查

#### 🟡 趋向保守（负向占比 30-50%）
```json
{
  "actions": [
    {
      "action": "adjust_pain_weights",
      "priority": "medium",
      "config_change": {
        "weight_adjustment": {
          "core_business": -5,
          "auth_payment": -5
        }
      }
    }
  ]
}
```

**效果**: 轻微降低高风险类别的权重

#### 🟢 鼓励创新（负向占比 ≤ 30%）
```json
{
  "actions": [
    {
      "action": "enable_innovation_mode",
      "priority": "low",
      "config_change": {
        "experimental_code_tolerance": true
      }
    }
  ]
}
```

**效果**: 降低对实验性代码的拦截强度

---

## 🔄 集成到现有架构

### 1. 集成到 Pain Scorer

```python
from moat.pain.scorer import calculate_pain_score
from moat.evolution_metrics import EvolutionTracker

# 每次检查后更新进化指标
def check_with_evolution_tracking(project_root: str):
    tracker = EvolutionTracker(Path(project_root) / ".moat")

    # 1. 运行检查
    errors = run_all_checks(project_root)

    # 2. 计算 Pain Score
    pain_scores = [calculate_pain_score(e) for e in errors]

    # 3. 自动记录 Pain Score 趋势
    avg_pain = sum(s["score"] for s in pain_scores) / len(pain_scores) if pain_scores else 0
    tracker.record_pain_score_trend(avg_pain)

    # 4. 评估进化方向
    evaluation = tracker.evaluator.evaluate_evolution()
    if evaluation["fatigue_status"]["status"] in ["warning", "critical"]:
        print(f"⚠️  {evaluation['fatigue_status']['message']}")
        print("建议调整:")
        for action in evaluation["recommendation"]["actions"]:
            print(f"  - {action['description']}")

    return errors
```

### 2. 集成到 Feedback Loop

```python
from moat.pain.feedback import FeedbackStore
from moat.evolution_metrics import EvolutionTracker

# 将用户反馈同步到进化指标
def sync_feedback_to_evolution(feedback_store: FeedbackStore, tracker: EvolutionTracker):
    for feedback in feedback_store.feedback:
        if feedback.user_rating == "false_positive":
            # 误报也是进化指标（负向）
            tracker.record_false_positive(
                error_type=feedback.error_type,
                file_path=feedback.file_pattern,
            )
```

### 3. CLI 命令

```bash
# 查看进化报告
moat evolution report

# 输出示例
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

### 场景 3: 配置调整
```bash
# 如果系统神经衰弱，自动降低阈值
moat evolution adjust --auto

# 手动调整
moat evolution adjust --pain-threshold 40
```

---

## 🎯 关键设计决策

### Q1: 为什么误报率是负向指标？

**A**: 误报本身不是坏事，但**持续的、大量的误报**意味着系统在"过度反应"，这是"神经衰弱"的前兆。

### Q2: 如何定义"好的进化"？

**A**: 六大指标的平衡：
- **重构成功率** > 0.7（70% 的重构都成功）
- **性能提升率** > 0.5（平均提升 50%）
- **Bug 修复时效** < 4 小时（高严重性 Bug）
- **误报率** < 0.2（20% 以下）
- **开发效率** 不下降（与历史基线对比）

### Q3: 如何避免"过度优化"？

**A**: 进化指标系统会检测"过拟合"：
- 如果连续 7 天负向指标上升 → 警告
- 如果连续 30 天负向指标上升 → 触发自动调整

---

## 📚 参考资料

- Gemini 建议的核心洞察："防止神经衰弱"
- Moat 现有架构：`moat/pain/feedback.py`（用户反馈闭环）
- Moat 现有架构：`moat/evolution.py`（元知识反向驱动）
- One Memory 梦境引擎：提供高维 Insight

---

## 🚀 下一步

1. **短期**（1-2 天）：集成到 `moat check` 命令，自动采集 Pain Score 趋势
2. **中期**（1 周）：CLI 命令 `moat evolution report`
3. **长期**（2 周）：自动调整配置（根据进化指标动态调整 Pain Score 阈值）

---

**记住**: 进化的方向性比进化速度更重要。🚀
