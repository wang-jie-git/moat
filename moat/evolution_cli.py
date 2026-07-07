"""Evolution Metrics CLI — 进化指标系统命令行接口"""

import sys
from pathlib import Path
from typing import Any


def cmd_evolution(args):
    """进化指标命令"""
    from moat.evolution_metrics import EvolutionTracker

    root = Path(args.project)
    moat_dir = root / ".moat"
    tracker = EvolutionTracker(moat_dir)

    if args.action == "report":
        return _cmd_report(tracker, args)
    elif args.action == "adjust":
        return _cmd_adjust(tracker, args)
    elif args.action == "record":
        return _cmd_record(tracker, args)
    else:
        print(f"❌ 未知操作: {args.action}")
        return 1


def _cmd_report(tracker, args) -> int:
    """生成进化报告"""
    from moat.evolution_metrics import EvolutionEvaluator

    window_hours = args.window or 24

    print(f"\n📊 进化指标报告（最近 {window_hours} 小时）\n")

    # 生成报告
    report = tracker.get_evolution_report(window_hours)
    print(report)

    # JSON 输出
    if args.format == "json":
        evaluation = tracker.evaluator.evaluate_evolution(window_hours)
        import json
        print("\nJSON 输出:")
        print(json.dumps(evaluation, indent=2, ensure_ascii=False))

    return 0


def _cmd_adjust(tracker, args) -> int:
    """调整进化配置"""
    from moat.evolution_metrics import EvolutionEvaluator

    print(f"\n🔧 调整进化配置\n")

    # 1. 评估当前状态
    evaluation = tracker.evaluator.evaluate_evolution(window_hours=24)
    fatigue_status = evaluation.get("fatigue_status", {})

    print(f"当前状态: {fatigue_status.get('status', 'unknown')}")
    print(f"负向指标占比: {fatigue_status.get('negative_ratio', 0):.1%}")
    print(f"{fatigue_status.get('message', '')}\n")

    # 2. 自动调整
    if args.auto:
        recommendations = evaluation.get("recommendation", {}).get("actions", [])
        if recommendations:
            print("💡 自动调整建议:")
            for action in recommendations:
                print(f"  - [{action['priority']}] {action['description']}")
                if "config_change" in action:
                    print(f"    配置变更: {action['config_change']}")

            # TODO: 实际应用配置变更
            print("\n⚠️  自动调整功能尚未实现，请手动调整配置")
        else:
            print("✅ 当前配置良好，无需调整")
    else:
        # 手动调整
        if args.pain_threshold:
            print(f"调整 Pain Score 阈值: {args.pain_threshold}")
            # TODO: 更新 .moat/config.json
        if args.false_positive_tolerance:
            print(f"调整误报容忍度: {args.false_positive_tolerance}")

    return 0


def _cmd_record(tracker, args) -> int:
    """手动记录指标"""
    from moat.evolution_metrics import EvolutionMetric
    import time

    metric_type = args.metric_type
    value = args.value

    metric = EvolutionMetric(
        id=f"manual_{int(time.time() * 1000)}",
        type=metric_type,
        value=value,
        weight=0.1,
        timestamp=time.time(),
        context={"source": "manual", "user": "cli"},
        is_positive=True,
    )

    tracker.metrics_store.add_metric(metric)
    print(f"✅ 已记录指标: {metric_type} = {value}")
    return 0
