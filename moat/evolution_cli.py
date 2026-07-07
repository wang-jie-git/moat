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

    # 2. 生成配置调整建议
    recommendations = evaluation.get("recommendation", {}).get("actions", [])

    if not recommendations:
        print("✅ 当前配置良好，无需调整")
        return 0

    print("💡 建议调整:")
    for i, action in enumerate(recommendations, 1):
        print(f"\n{i}. [{action['priority'].upper()}] {action['description']}")
        if "config_change" in action:
            print(f"   配置变更: {action['config_change']}")

    # 3. 自动应用（如果 --auto）
    if args.auto:
        print(f"\n🚀 自动应用配置调整...")
        applied = _apply_config_adjustments(recommendations, tracker.moat_dir)
        if applied:
            print(f"✅ 已应用 {len(applied)} 项配置调整")
        else:
            print(f"⚠️  没有可自动应用的配置")
    else:
        print(f"\n💡 提示: 使用 --auto 参数自动应用配置调整")

    return 0


def _apply_config_adjustments(
    recommendations: list[dict[str, Any]], moat_dir: Path
) -> list[str]:
    """应用配置调整（v0.5.0 新增）

    Args:
        recommendations: 建议列表
        moat_dir: .moat 目录

    Returns:
        已应用的调整列表
    """
    import json

    config_path = moat_dir / "config.json"
    if not config_path.exists():
        return []

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return []

    applied = []

    for action in recommendations:
        config_change = action.get("config_change", {})
        if not config_change:
            continue

        # 应用配置变更
        for key, value in config_change.items():
            if isinstance(value, dict):
                # 嵌套配置（如 weight_adjustment）
                if key not in config:
                    config[key] = {}
                config[key].update(value)
            else:
                config[key] = value

        applied.append(action["action"])

    # 保存配置
    try:
        config_path.write_text(
            json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        return []

    return applied


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
