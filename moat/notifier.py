"""通知推送 — `moat notify` 发送检查结果到 Slack / 飞书

用法:
  moat notify --webhook https://hooks.slack.com/...    # Slack
  moat notify --webhook https://open.feishu.cn/...     # 飞书
  moat notify --report moat-report.json                # 指定报告文件
  moat notify --fail-on-score 60                        # 门禁模式
"""

import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import urllib.request
    import urllib.error
except ImportError:
    pass


def _detect_platform(webhook_url: str) -> str:
    """自动检测 webhook 平台"""
    host = urlparse(webhook_url).hostname or ""
    if "hooks.slack.com" in host:
        return "slack"
    if "open.feishu.cn" in host or "feishu.cn" in host:
        return "feishu"
    if "discord.com" in host:
        return "discord"
    return "unknown"


def _load_report(report_path: str | None, project_root: Path) -> dict[str, Any] | None:
    """加载检查报告"""
    if report_path:
        path = Path(report_path)
        if not path.exists():
            print(f"❌ 报告文件不存在: {path}")
            return None
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError as e:
            print(f"❌ 报告文件解析失败: {e}")
            return None

    # 自动查找最近的报告
    candidates = [
        project_root / "moat-report.json",
        project_root / ".moat" / "last-report.json",
        project_root / "ACCEPTANCE_REPORT.md",
    ]
    for c in candidates:
        if c.exists():
            if c.suffix == ".json":
                try:
                    return json.loads(c.read_text())
                except json.JSONDecodeError:
                    pass
            else:
                # 返回文件路径作为文本报告
                return {"report_path": str(c)}

    return None


def _build_slack_message(report: dict[str, Any] | None, fail_on_score: int | None) -> str:
    """构建 Slack 消息（Block Kit 格式）"""
    score = report.get("overall_score", "N/A") if report else "N/A"
    passed = report.get("passed", False) if report else False
    status = "✅ 通过" if passed else "❌ 未通过"
    violations = report.get("total_violations", 0) if report else 0
    critical = report.get("critical_violations", 0) if report else 0

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"🛡️ Moat 检查报告 {status}"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*评分:*\n{score}/100"},
                {"type": "mrkdwn", "text": f"*状态:*\n{status}"},
                {"type": "mrkdwn", "text": f"*违规:*\n{ violations }"},
                {"type": "mrkdwn", "text": f"*CRITICAL:*\n{ critical }"},
            ]
        }
    ]

    # 门禁检查
    if fail_on_score is not None and isinstance(score, (int, float)):
        if score < fail_on_score:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"🚨 *门禁拦截*: 评分 {score} 低于阈值 {fail_on_score}"}
            })

    # 违规详情
    if report and report.get("operators"):
        violations_text = ""
        for op in report.get("operators", []):
            if not op.get("passed", True):
                v_count = len(op.get("violations", []))
                violations_text += f"• *{op.get('operator_name', '?')}*: {v_count} 个违规\n"
                for v in op.get("violations", [])[:3]:
                    violations_text += f"  - {v.get('message', '')}\n"
        if violations_text:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*违规详情:*\n{violations_text}"}
            })

    # 建议
    if report and report.get("suggestions"):
        suggestions = report.get("suggestions", [])
        if isinstance(suggestions, list):
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*建议:*\n{'\\n'.join(suggestions[:3])}"}
            })

    return json.dumps({"blocks": blocks})


def _build_feishu_message(report: dict[str, Any] | None, fail_on_score: int | None) -> str:
    """构建飞书消息（卡片格式）"""
    score = report.get("overall_score", "N/A") if report else "N/A"
    passed = report.get("passed", False) if report else False
    status = "✅ 通过" if passed else "❌ 未通过"
    violations = report.get("total_violations", 0) if report else 0
    critical = report.get("critical_violations", 0) if report else 0

    elements = [
        {
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**评分:** {score}/100 | **状态:** {status} | **违规:** {violations} | **CRITICAL:** {critical}"}
        }
    ]

    if fail_on_score is not None and isinstance(score, (int, float)):
        if score < fail_on_score:
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"🚨 门禁拦截: 评分 {score} 低于阈值 {fail_on_score}"}
            })

    return json.dumps({
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"tag": "plain_text", "content": f"🛡️ Moat 检查报告 {status}"}},
            "elements": elements,
        }
    })


def _build_discord_message(report: dict[str, Any] | None, fail_on_score: int | None) -> str:
    """构建 Discord 消息（Embed 格式）"""
    score = report.get("overall_score", "N/A") if report else "N/A"
    passed = report.get("passed", False) if report else False
    color = 0x00FF00 if passed else 0xFF0000

    embed = {
        "title": "🛡️ Moat 检查报告",
        "color": color,
        "fields": [
            {"name": "评分", "value": f"{score}/100", "inline": True},
            {"name": "状态", "value": "✅ 通过" if passed else "❌ 未通过", "inline": True},
        ]
    }

    if report:
        violations = report.get("total_violations", 0)
        critical = report.get("critical_violations", 0)
        embed["fields"].append({"name": "违规", "value": str(violations), "inline": True})
        embed["fields"].append({"name": "CRITICAL", "value": str(critical), "inline": True})

    return json.dumps({"embeds": [embed]})


def _send_webhook(url: str, payload: str, platform: str) -> bool:
    """发送 webhook 请求"""
    try:
        import urllib.request
        data = payload.encode("utf-8")
        headers = {"Content-Type": "application/json"}

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            if resp.status == 200:
                return True
            else:
                print(f"❌ Webhook 返回 {resp.status}: {body}")
                return False
    except Exception as e:
        print(f"❌ Webhook 发送失败: {e}")
        return False


def cmd_notify(args) -> int:
    """发送检查结果到 webhook

    用法:
        moat notify --webhook <url>
        moat notify --webhook <url> --report moat-report.json
        moat notify --webhook <url> --fail-on-score 60
    """
    webhook_url = args.webhook
    if not webhook_url:
        # 尝试从环境变量读取
        webhook_url = os.environ.get("MOAT_WEBHOOK_URL", "")
    if not webhook_url:
        print("❌ 请提供 --webhook URL 或设置 MOAT_WEBHOOK_URL 环境变量")
        print("   用法: moat notify --webhook https://hooks.slack.com/...")
        return 1

    project_root = Path(args.project).resolve()
    report = _load_report(args.report, project_root)

    if report is None:
        print("⚠️  未找到检查报告，发送简单通知")
        report = {}

    platform = _detect_platform(webhook_url)
    print(f"📤 发送到 {platform} webhook...")

    if platform == "slack":
        payload = _build_slack_message(report, args.fail_on_score)
    elif platform == "feishu":
        payload = _build_feishu_message(report, args.fail_on_score)
    elif platform == "discord":
        payload = _build_discord_message(report, args.fail_on_score)
    else:
        # 通用 JSON 格式
        payload = json.dumps({"report": report})

    success = _send_webhook(webhook_url, payload, platform)
    if success:
        print(f"✅ 通知发送成功")
        return 0
    else:
        print(f"❌ 通知发送失败")
        return 1