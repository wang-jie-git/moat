"""
Moat CLI — 护城河命令行工具

用法:
  moat check          改代码前/后检查（默认快速模式 < 5 秒）
  moat check --full   完整检查（所有文件，可能很慢）
  moat check --diff   增量检查（AST 对比 + 影响域分析 < 10 秒）
  moat check --leak   泄露风险检测（AI 工具跨目录读取、敏感文件暴露）
  moat check --scan-ai  🕵️ 扫描 AI 工具系统配置（~/.claude/ ~/.grok/ ~/.codex/）
  moat accept         8 步架构验收
  moat ci             自动生成 CI/CD 工作流
  moat notify         发送检查结果到 Slack / 飞书
  moat report         生成报告（支持 text / md / json / pdf）
  moat watch          实时监控日志错误
  moat init           初始化到当前项目
  moat dashboard      启动 Web 错误看板
  moat adapter        安装 AI 工具适配器
  moat baseline       管理基线数据
  moat verify         架构验收
"""

import argparse
import sys
import os
from pathlib import Path


def cmd_check(args):
    """运行四层门禁检查

    支持三种模式：
    - moat check（默认）：快速检查（只检查修改的文件）< 5 秒
    - moat check --full：完整检查（所有文件 + 复杂规则）可能很慢
    - moat check --diff：增量检查（AST 对比 + 影响域分析）< 10 秒
    - moat check --leak：代码泄露风险检测 < 3 秒
    """
    from moat.runner import run_all_checks

    # AI 工具系统配置扫描模式
    if args.scan_ai:
        print(f"\n🕵️  AI 工具系统配置安全审计...")
        from moat.verification.operators.leakage_detection import LeakageDetectionOperator
        from moat.verification.types import VerificationContext

        op = LeakageDetectionOperator()
        ctx = VerificationContext(project_path=Path(args.project))
        ctx.config["scan_ai"] = True
        result = op.verify(ctx)

        print(f"\n{'=' * 55}")
        print(f"  🛡️  AI 工具审计报告")
        print(f"{'=' * 55}")
        for v in result.violations:
            sev = "🔴" if v.severity.value == "critical" else "🟡" if v.severity.value == "warning" else "ℹ️"
            print(f"  {sev} [{v.severity.value.upper()}] {v.message}")
            if v.file_path:
                print(f"     📍 {v.file_path}")
            if v.suggestion:
                print(f"     💡 {v.suggestion}")
            if v.evidence and "dangerous_commands" in v.evidence:
                for cmd in v.evidence["dangerous_commands"]:
                    print(f"        ⚠️  {cmd}")
            print()

        if result.suggestions:
            print("📋 建议:")
            for s in result.suggestions:
                print(f"  {s}")
        print()

        return 0 if result.passed else 1

    # 泄露检测模式
    if args.leak:
        print(f"\n🔒 代码泄露风险检测...")
        from moat.verification.operators.leakage_detection import LeakageDetectionOperator
        from moat.verification.types import VerificationContext

        op = LeakageDetectionOperator()
        ctx = VerificationContext(project_path=Path(args.project))
        result = op.verify(ctx)

        print(f"\n{'=' * 55}")
        if result.passed:
            print(f"  ✅ 未检测到代码泄露风险")
        else:
            print(f"  ❌ 发现 {len(result.violations)} 个泄露风险")
            for v in result.violations:
                severity = "🔴" if v.severity.value == "critical" else "🟡"
                print(f"  {severity} [{v.severity.value.upper()}] {v.message}")
                if v.file_path:
                    print(f"     📍 {v.file_path}")
                if v.suggestion:
                    print(f"     💡 {v.suggestion}")
        print(f"{'=' * 55}\n")

        if result.suggestions:
            print("📋 建议:")
            for s in result.suggestions:
                print(f"  {s}")
        print()

        return 0 if result.passed else 1

    # 优先使用 --diff 模式（增量检查）
    if args.diff:
        # 增量检查模式（AST 对比 + 影响域分析）
        from moat.ast.diff import diff_project
        from moat.ast.builder import build_skeleton
        from moat.pain.scorer import calculate_total_pain

        root = Path(args.project)

        # 1. 构建骨架图
        print(f"\n🔨 构建项目骨架图...")
        skeleton = build_skeleton(str(root))
        print(f"   ✅ {skeleton.to_dict()['stats']['total_functions']} 个函数, "
              f"{skeleton.to_dict()['stats']['total_calls']} 个调用")

        # 2. 对比变更
        print(f"\n📊 分析代码变更...")
        changes = diff_project(str(root))

        if not changes:
            print(f"   ✅ 未检测到变更")
            return 0

        print(f"   ⚡ 检测到 {len(changes)} 个变更:\n")
        for change in changes:
            print(f"   {change['type']:10s} | {change['file']}:{change.get('line', '?')} "
                  f"::{change.get('function', '?')}")

        # 3. 影响域分析
        print(f"\n💡 影响域分析:")
        impacts = skeleton.analyze_impacts(changes, skeleton.to_dict())

        if impacts:
            for impact in impacts:
                change = impact.get("change", {})
                callers = impact.get("callers", [])
                risk_level = impact.get("risk_level", "unknown")
                print(f"\n   📍 {change.get('file', '?')}::{change.get('function', '?')}")
                print(f"      影响 {len(callers)} 个调用方:")
                for caller in callers[:5]:  # 最多显示 5 个
                    print(f"        - {caller}")
                if len(callers) > 5:
                    print(f"        ... 还有 {len(callers) - 5} 个")
                print(f"      风险等级: {risk_level}")
        else:
            print(f"   ✅ 未检测到直接影响")

        # 4. Pain Score 评估
        print(f"\n😣 痛觉评估:")
        errors_as_dict = [{"type": c["type"], "file": c["file"], "message": c.get("function", "")}
                          for c in changes]
        pain_result = calculate_total_pain(errors_as_dict)

        print(f"   总分: {pain_result['total_score']}/100 ({pain_result['overall_level']})")
        print(f"   建议: {pain_result['recommended_action']}")

        # 5. 返回建议
        if pain_result['overall_level'] in ('CRITICAL', 'HIGH'):
            print(f"\n⚠️  建议: 运行完整检查以确保没有引入问题")
            print(f"   moat check --full")
            return 1
        else:
            print(f"\n✅ 变更风险较低，但仍建议运行完整检查")
            return 0

    # 根据参数选择检查模式
    elif args.full:
        # 完整检查模式
        print(f"\n🔍 完整检查模式（所有文件 + 复杂规则）...")

        # 加载配置并添加 skip_architecture
        from moat.runner import _load_config
        config = _load_config(Path(args.project))
        if args.skip_architecture:
            config["skip_architecture"] = True

        # 这里需要临时修改 config，简化处理：通过环境变量传递
        import os
        if args.skip_architecture:
            os.environ["MOAT_SKIP_ARCHITECTURE"] = "true"

        # 战术建议 1：异步触发优化检查
        enable_optimization = getattr(args, 'optimize', False)
        result = run_all_checks(args.project, mode="full", enable_optimization=enable_optimization)

        if enable_optimization:
            print(f"\n⚡ 已启用代码优化检查（Ponytail 集成）")
        return 0 if result.is_success() else 1

    elif args.quick:
        # 快速检查模式（默认）
        print(f"\n⚡ 快速检查模式（只检查修改的文件）...")
        enable_optimization = getattr(args, 'optimize', False)
        result = run_all_checks(args.project, mode="quick", enable_optimization=enable_optimization)

        if enable_optimization:
            print(f"\n⚡ 已启用代码优化检查（Ponytail 集成）")
        return 0 if result.is_success() else 1

    else:
        # 默认：快速检查模式
        enable_optimization = getattr(args, 'optimize', False)
        result = run_all_checks(args.project, mode="quick", enable_optimization=enable_optimization)
        return 0 if result.is_success() else 1


def cmd_watch(args):
    """实时监控日志错误"""
    from moat.monitor import start_monitor
    log_path = args.log or _detect_log_path(args.project)
    if not log_path:
        print("❌ 找不到日志文件，请用 --log 指定路径")
        return 1
    start_monitor(Path(log_path), args.color, args.filter)


def cmd_init(args):
    """初始化 Moat 到当前项目"""
    from moat.discovery import init_project
    init_project(Path(args.project), interactive=not args.no_interactive)
    return 0


def cmd_baseline(args):
    """管理基线"""
    from moat.baseline import BaselineManager
    bm = BaselineManager(Path(args.project))
    if args.action == "save":
        bm.save()
        print(f"✅ 基线已保存 ({bm.baseline_path})")
    elif args.action == "show":
        bm.show()
    elif args.action == "diff":
        bm.diff()
    return 0


def cmd_dashboard(args):
    """启动 Web 看板"""
    from moat.dashboard.server import start_dashboard
    start_dashboard(
        project=Path(args.project),
        host=args.host,
        port=args.port,
        log_path=args.log or _detect_log_path(args.project),
    )
    return 0


def cmd_gatekeeper(args) -> int:
    """Gatekeeper守门"""
    from moat.gatekeeper.cli import cmd_gatekeeper
    return cmd_gatekeeper(args)


def cmd_verify(args) -> int:
    """架构验收"""
    from moat.verification.verify_cli import cmd_verify
    return cmd_verify(args)


def cmd_accept(args) -> int:
    """🏗 架构验收 8 步法 — 生成标准化验收报告 + 真元文档

    用法:
        moat accept                         # 完整验收（使用内置默认规则）
        moat accept --generate-rules        # 生成 architect.yml 模板
        moat accept --output report.md      # 指定输出文件
        moat accept --json                  # JSON 格式输出
        moat accept --fail-on-score 60      # 评分阈值门禁
        moat accept --rules architect.yml   # 使用自定义规则文件
    """
    from pathlib import Path
    from moat.checks.acceptance import (
        RuleRegistry,
        ArchitectRunner,
        AcceptanceReportGenerator,
    )

    project_root = Path(args.project).resolve()

    # 生成规则模板
    if args.generate_rules:
        from moat.checks.acceptance.rule_registry import RuleRegistry
        path = RuleRegistry.save_template(project_root)
        print(f"✅ 架构规则模板已生成: {path}")
        print(f"   编辑 {path.name} 后运行 moat accept 开始验收")
        return 0

    # 执行验收
    rules_path = args.rules
    runner = ArchitectRunner(project_root, rules_path=rules_path)
    report = runner.run(diff_mode=args.diff)

    # 生成报告
    gen = AcceptanceReportGenerator(report)

    output_path = args.output
    if output_path:
        fmt = "json" if output_path.endswith(".json") else "md"
        saved = gen.save(output_path, fmt=fmt)
        print(f"\n📄 报告已保存: {saved}")

    if args.json:
        import json
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))

    # 门禁模式
    if args.fail_on_score is not None:
        threshold = args.fail_on_score
        if report.overall_score < threshold:
            print(f"\n❌ 架构评分 {report.overall_score:.0f}/100 低于阈值 {threshold}")
            return 1

    # CRITICAL 违规拦截
    critical = sum(1 for r in report.rules for v in r.violations if v.get("severity") == "CRITICAL")
    if critical > 0:
        print(f"\n❌ 发现 {critical} 个 CRITICAL 违规")
        return 1

    return 0 if report.passed else 1


def cmd_report(args):
    """生成检查报告"""
    from moat.report import generate_report
    from moat.runner import MoatResult

    root = Path(args.project)

    # 运行检查并获取结果
    from moat.runner import run_all_checks
    result = MoatResult()

    # 临时替换 runner 的打印函数来捕获结果
    import io
    from contextlib import redirect_stdout

    # 简单起见，直接运行检查并生成报告
    # 实际应该修改 runner 返回结果
    result = run_all_checks(str(root))

    # 生成报告
    report = generate_report(
        project_root=str(root),
        format=args.format,
        copy=args.copy,
        output_path=args.output,
    )

    if not result.is_success() and args.copy:
        return 0  # 复制成功就算成功
    return 0 if result.is_success() else 1


def cmd_architecture(args):
    """生成架构健康报告（L2）"""
    from moat.architecture_report import generate_architecture_report

    root = Path(args.project)

    # 生成报告
    report = generate_architecture_report(
        project_root=str(root),
        format=args.format,
        copy=args.copy,
    )

    print(report)
    return 0


def cmd_adapter(args):
    """安装 AI 适配器"""
    from moat.adapters import install_claude_adapter, install_precommit_hook

    if args.type == "claude" or args.type == "all":
        install_claude_adapter(Path(args.project))
    if args.type == "precommit" or args.type == "all":
        install_precommit_hook(Path(args.project))
    print("✅ 适配器安装完成")
    return 0


# ── moat-memory 命令 ──────────────────────────────────

def _get_memory(args):
    """获取 MoatMemory 实例。"""
    from moat.memory.moat_memory import MoatMemory
    return MoatMemory(args.project)


def cmd_memory(args):
    """📖 项目记忆管理。"""
    memory = _get_memory(args)

    if args.action == "stats":
        stats = memory.stats()
        if getattr(args, 'json', False):
            import json
            print(json.dumps(stats, indent=2))
        else:
            print("📊 moat-memory 统计:")
            print(f"  红线 (redlines):   {stats.get('redlines', 0)}")
            print(f"  踩坑 (lessons):    {stats.get('lessons', 0)}")
            print(f"  模版 (templates):  {stats.get('templates', 0)}")
            print(f"  技能 (skills):     {stats.get('skills', 0)}")
        return 0

    if args.action == "list":
        if not args.type:
            print("请指定记忆类型: redlines / lessons / templates / skills")
            return 1

        if args.type == "redlines":
            items = memory.list_redlines(category=getattr(args, 'category', None))
        elif args.type == "lessons":
            items = memory.list_lessons(limit=getattr(args, 'limit', 20))
        elif args.type == "templates":
            items = memory.list_templates(domain=getattr(args, 'domain', None))
        elif args.type == "skills":
            items = memory.list_skills(tool=getattr(args, 'tool', None))
        else:
            items = []

        if getattr(args, 'json', False):
            import json
            print(json.dumps(items, indent=2, ensure_ascii=False))
            return 0

        if not items:
            print(f"📭 没有 {args.type}")
            return 0

        print(f"📖 {args.type} ({len(items)} 条):")
        for item in items:
            item_id = item.get("id", "?")[:12]
            title = item.get("title", item.get("domain", "?"))[:60]
            if args.type == "lessons":
                summary = str(item.get("error_summary", ""))[:60]
                print(f"  [{item_id}] {title}")
                print(f"        {summary}")
            elif args.type == "redlines":
                sev = item.get("severity", "?")
                print(f"  [{sev}] {title}")
            elif args.type == "templates":
                dom = item.get("domain", "?")
                imp = item.get("importance", "?")
                print(f"  [{item_id}] ({dom}, ★{imp}) {title}")
            elif args.type == "skills":
                tool = item.get("tool", "?")
                print(f"  [{tool}] {str(item.get('instruction', ''))[:80]}")
        return 0

    if args.action == "show":
        if not args.id:
            print("请指定 --id")
            return 1
        for list_fn in [
            lambda: memory.list_redlines(),
            lambda: memory.list_lessons(limit=999),
            lambda: memory.list_templates(),
            lambda: memory.list_skills(),
        ]:
            for item in list_fn():
                if item.get("id", "").startswith(args.id):
                    import json
                    print(json.dumps(item, indent=2, ensure_ascii=False))
                    return 0
        print(f"未找到 ID 包含 '{args.id}' 的记忆")
        return 1

    if args.action == "delete":
        if not args.type or not args.id:
            print("请指定记忆类型和 --id")
            return 1
        if args.type == "redlines":
            ok = memory.remove_redline(args.id)
        elif args.type == "lessons":
            ok = memory.remove_lesson(args.id)
        elif args.type == "templates":
            ok = memory.remove_template(args.id)
        else:
            print(f"不支持删除 {args.type}")
            return 1
        print(f"{'✅' if ok else '❌'} 删除 {'成功' if ok else '失败'}")
        return 0

    return 0


def cmd_redline(args):
    """📏 管理项目红线。"""
    memory = _get_memory(args)

    if args.action == "list":
        items = memory.list_redlines()
        if not items:
            print("📭 没有红线")
            return 0
        print("📏 项目红线:")
        for rl in items:
            icon = {"critical": "🔴", "warning": "🟡", "info": "ℹ️"}.get(rl.get("severity", "warning"), "⚠️")
            print(f"  {icon} [{rl.get('id', '?')[:12]}] {rl['title']}")
            print(f"     {rl['description']}")
        return 0

    if args.action == "add":
        if not args.title:
            print("请指定红线标题")
            return 1
        rid = memory.add_redline(
            title=args.title,
            description=args.description or args.title,
            severity=args.severity,
            category=args.category,
            file_glob=getattr(args, 'file_glob', None),
        )
        print(f"✅ 红线已添加: {rid}")
        return 0

    if args.action == "remove":
        if not args.id:
            print("请指定 --id")
            return 1
        ok = memory.remove_redline(args.id)
        print(f"{'✅' if ok else '❌'} 删除{'成功' if ok else '失败'}")
        return 0

    return 0


def cmd_template(args):
    """📋 管理经验模版。"""
    memory = _get_memory(args)

    if args.action == "list":
        items = memory.list_templates(domain=getattr(args, 'domain', None))
        if not items:
            print("📭 没有模版")
            return 0
        print("📋 经验模版:")
        for t in items:
            tid = t.get("id", "?")[:12]
            dom = t.get("domain", "?")
            imp = t.get("importance", "?")
            print(f"  [{tid}] ({dom}, ★{imp}) {t.get('title', '?')}")
        return 0

    if args.action == "show":
        if not args.id:
            print("请指定 --id")
            return 1
        items = memory.list_templates()
        for t in items:
            if t.get("id", "").startswith(args.id):
                import json
                print(json.dumps(t, indent=2, ensure_ascii=False))
                return 0
        print(f"未找到 ID 包含 '{args.id}' 的模版")
        return 1

    if args.action == "add":
        if not args.title:
            print("请指定模版标题")
            return 1
        tags_list = [t.strip() for t in args.tags.split(",")] if getattr(args, 'tags', None) else []
        tid = memory.add_template(
            domain=args.domain,
            title=args.title,
            source=args.source,
            importance=args.importance,
            tags=tags_list,
        )
        print(f"✅ 模版已添加: {tid}")
        return 0

    if args.action == "remove":
        if not args.id:
            print("请指定 --id")
            return 1
        ok = memory.remove_template(args.id)
        print(f"{'✅' if ok else '❌'} 删除{'成功' if ok else '失败'}")
        return 0

    if args.action == "extract":
        print("🔍 从项目经验提取模版...")
        print("   功能开发中，敬请期待。")
        return 0

    if args.action == "import":
        if not args.file:
            print("请指定 --file")
            return 1
        import json
        try:
            with open(args.file) as f:
                data = json.load(f)
            memory.add_template(
                domain=data.get("domain", "general"),
                title=data.get("title", ""),
                source="imported",
                importance=data.get("importance", 5),
                tags=data.get("tags", []),
            )
            print(f"✅ 模版已导入")
        except (json.JSONDecodeError, IOError) as e:
            print(f"❌ 导入失败: {e}")
            return 1
        return 0

    return 0


def cmd_fix(args):
    """AI 辅助修复"""
    from moat.fixer import generate_fix_report
    from moat.runner import run_all_checks

    root = Path(args.project)

    # 先运行检查获取错误列表
    print(f"\n🔍 运行检查以获取错误列表...")
    result = run_all_checks(str(root))

    if result.is_success():
        print("\n✅ 未发现错误，无需修复")
        return 0

    # 使用检查结果中的错误列表
    print(f"\n🔧 生成修复建议...")

    # 生成修复报告（传入错误列表）
    report = generate_fix_report(
        project_root=str(root),
        errors=result.errors,
        dry_run=not args.no_dry_run,
        format=args.format,
    )

    print(report)

    if args.copy:
        try:
            import pyperclip
            pyperclip.copy(report)
            print("\n✅ 报告已复制到剪贴板")
        except ImportError:
            print("\n⚠️  未安装 pyperclip，跳过复制")

    return 0


def cmd_sidecar(args):
    """Sidecar 守护进程管理"""
    from moat.sidecar.daemon import SidecarDaemon

    root = Path(args.project)
    daemon = SidecarDaemon(root)

    if args.action == "start":
        return daemon.start(foreground=args.foreground)
    elif args.action == "stop":
        return daemon.stop()
    elif args.action == "restart":
        return daemon.restart()
    elif args.action == "status":
        print(daemon.status())
        return 0
    return 1


def cmd_rules_explain(args):
    """解释规则详情

    让用户在 3 秒内理解：
    1. 为什么报错
    2. 如何修复
    3. 如何关闭此检查
    """
    rule_id = args.rule_id.upper()

    # 规则库（应该从配置文件读取，这里简化处理）
    rules_db = {
        # 安全规则
        "SQL-001": {
            "name": "SQL 注入检测",
            "description": "检测 SQL 字符串拼接导致的注入风险",
            "severity": "CRITICAL",
            "why": "SQL 注入是 OWASP Top 10 第一安全风险，可能导致数据泄露、数据篡改甚至服务器被控制",
            "fix": "使用参数化查询：cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
            "disable": '在 .moat/config.json 中设置 {"rules": {"sql_injection": false}}',
        },
        "API-001": {
            "name": "API 缺少鉴权",
            "description": "检测 API 路由缺少鉴权装饰器",
            "severity": "CRITICAL",
            "why": "未鉴权的 API 可能导致未授权访问，造成数据泄露",
            "fix": "添加鉴权装饰器：@login_required 或 @require_permission('admin')",
            "disable": '在 .moat/config.json 中设置 {"rules": {"api_auth": false}}',
        },
        # 复杂度规则
        "COMPLEX-001": {
            "name": "圈复杂度超标",
            "description": "函数圈复杂度超过阈值（默认 10）",
            "severity": "MEDIUM",
            "why": "高复杂度函数难以理解和维护，Bug 率随复杂度指数增长",
            "fix": "将复杂函数拆分为多个小函数（每个 < 10 复杂度）",
            "disable": '在 .moat/config.json 中设置 {"optimization": {"max_complexity": 15}}',
        },
        "COMPLEX-002": {
            "name": "函数过长",
            "description": "函数长度超过阈值（默认 50 行）",
            "severity": "LOW",
            "why": "长函数难以理解、测试和维护",
            "fix": "按逻辑块拆分函数，提取辅助函数",
            "disable": '在 .moat/config.json 中设置 {"optimization": {"max_function_length": 80}}',
        },
        "COMPLEX-003": {
            "name": "认知复杂度超标",
            "description": "函数认知复杂度超过阈值（默认 15）",
            "severity": "MEDIUM",
            "why": "高认知复杂度意味着代码难以被人理解，增加维护成本",
            "fix": "减少嵌套层级，使用卫语句（Guard Clauses），提取复杂逻辑到独立函数",
            "disable": '在 .moat/config.json 中设置 {"optimization": {"max_cognitive_complexity": 20}}',
        },
        # YAGNI 规则
        "YAGNI-001": {
            "name": "未使用的导入",
            "description": "检测未使用的 import 语句",
            "severity": "LOW",
            "why": "未使用的导入增加依赖负担，降低代码可读性",
            "fix": "删除未使用的导入，或使用工具（如 autoflake）自动清理",
            "disable": '在 .moat/config.json 中设置 {"optimization": {"check_yagni": false}}',
        },
        "YAGNI-002": {
            "name": "未处理的 TODO/FIXME",
            "description": "检测过多的 TODO/FIXME 注释",
            "severity": "LOW",
            "why": "过多的 TODO 表明代码未完成或技术债积累",
            "fix": "实现 TODO 对应的功能，或删除已过时的 TODO",
            "disable": '在 .moat/config.json 中设置 {"optimization": {"check_yagni": false}}',
        },
        "YAGNI-004": {
            "name": "死代码检测",
            "description": "检测无法访问的代码（return/raise 后）",
            "severity": "MEDIUM",
            "why": "死代码增加代码体积，误导读者",
            "fix": "删除 return/raise 后的代码，或将 cleanup 逻辑移到 finally",
            "disable": '在 .moat/config.json 中设置 {"optimization": {"check_dead_code": false}}',
        },
    }

    if rule_id not in rules_db:
        print(f"❌ 未知规则: {rule_id}")
        print(f"\n💡 可用规则:")
        for rid, rinfo in sorted(rules_db.items()):
            print(f"  {rid:12s} - {rinfo['name']}")
        print(f"\n更多帮助: moat rules list")
        return 1

    rule = rules_db[rule_id]

    # 输出格式化说明
    print(f"\n{'='*60}")
    print(f"  📖 规则详情: {rule_id}")
    print(f"{'='*60}\n")

    print(f"**名称**: {rule['name']}")
    print(f"**严重性**: {rule['severity']}")
    print(f"**描述**: {rule['description']}\n")

    print(f"**为什么报错**:")
    print(f"  {rule['why']}\n")

    print(f"**修复方法**:")
    print(f"  {rule['fix']}\n")

    print(f"**关闭此检查**:")
    print(f"  {rule['disable']}\n")

    print(f"{'='*60}")
    print(f"  💡 提示: 如果这是误报，请考虑关闭此规则")
    print(f"{'='*60}\n")

    return 0

def cmd_test(args) -> int:
    """AI 测试生成（已废弃，使用 moat immune）"""
    from moat.ai_test.cli import cmd_test
    return cmd_test(args)


def cmd_immune(args) -> int:
    """Moat Immune - AI 工程化测试体系"""
    from moat.immune.cli import cmd_immune
    return cmd_immune(args)


def cmd_ci(args) -> int:
    """生成 CI/CD 工作流文件"""
    from moat.ci_generator import cmd_ci
    return cmd_ci(args)


def cmd_audit(args) -> int:
    """🔐 AI 工具权限审计 — 检测权限过载、生成瘦身建议"""
    from moat.audit import cmd_audit
    return cmd_audit(args)


def cmd_notify(args) -> int:
    """发送通知到 webhook"""
    from moat.notifier import cmd_notify
    return cmd_notify(args)


def cmd_evolution(args):
    """进化指标管理"""
    from moat.evolution_cli import cmd_evolution
    return cmd_evolution(args)


def _detect_log_path(project: str) -> str | None:
    """自动检测项目日志路径"""
    candidates = [
        "logs/backend.log",
        "log/backend.log",
        "logs/app.log",
        "log/app.log",
        "var/log/app.log",
    ]
    for c in candidates:
        p = Path(project) / c
        if p.exists():
            return str(p)
    return None


def _shared_args(parser: argparse.ArgumentParser):
    """添加共享参数到子命令"""
    parser.add_argument("--project", default=".",
                        help="项目根目录 (默认: 当前目录)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="详细输出")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="moat",
        description="Moat — AI 编码护城河。防止 AI 改代码时搞坏系统。",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # check
    p_check = sub.add_parser("check", help="运行四层门禁检查")
    _shared_args(p_check)
    p_check.add_argument("--diff", action="store_true",
                         help="增量检查模式（对比 Git 变更 + AST 影响域分析）")
    p_check.add_argument("--quick", action="store_true",
                         help="快速检查模式（只检查修改的文件，默认）")
    p_check.add_argument("--full", action="store_true",
                         help="完整检查模式（所有文件 + 复杂规则，可能很慢）")
    p_check.add_argument("--legacy", action="store_true",
                         help="使用旧版 L1 检查（向后兼容）")
    p_check.add_argument("--skip-architecture", action="store_true",
                         help="跳过 L2 架构检查（提升性能，完整模式有效）")
    p_check.add_argument("--optimize", action="store_true",
                         help="启用代码优化检查（Ponytail 集成：YAGNI、复杂度、标准库优先）")
    p_check.add_argument("--leak", action="store_true",
                         help="🔒 代码泄露风险检测 — 检测 AI 工具跨目录读取、敏感文件暴露")
    p_check.add_argument("--scan-ai", action="store_true",
                         help="🕵️ 扫描 AI 工具系统配置（~/.claude/ ~/.grok/）— 检测数据窃取风险")

    # watch
    p_watch = sub.add_parser("watch", help="实时监控日志错误")
    _shared_args(p_watch)
    p_watch.add_argument("--log", "-l", help="日志文件路径")
    p_watch.add_argument("--no-color", dest="color", action="store_false",
                         help="禁用颜色输出")
    p_watch.add_argument("--filter", "-f", default="ERROR|Traceback|Process exited|Bridge died",
                         help="过滤模式 (默认: 错误/异常)")

    # init
    p_init = sub.add_parser("init", help="初始化 Moat 到当前项目")
    _shared_args(p_init)
    p_init.add_argument("--no-interactive", action="store_true",
                        help="非交互模式（使用自动检测配置）")

    # report
    p_report = sub.add_parser("report", help="生成检查报告")
    _shared_args(p_report)
    p_report.add_argument("--format", choices=["text", "md", "json", "pdf"], default="text",
                          help="输出格式（默认: text, 新增: pdf）")
    p_report.add_argument("--copy", action="store_true",
                          help="复制报告到剪贴板")
    p_report.add_argument("--output", "-o", default="",
                          help="输出文件路径（PDF 模式必填）")

    # 🆕 rules - 规则管理
    p_rules = sub.add_parser("rules", help="规则管理")
    p_rules_sub = p_rules.add_subparsers(dest="rules_action", help="规则操作")

    # rules explain
    p_rules_explain = p_rules_sub.add_parser("explain", help="解释规则详情（为什么报错/如何修复/如何关闭）")
    p_rules_explain.add_argument("rule_id", help="规则 ID（如 SQL-001, COMPLEX-001）")

    # 🏗 accept - 架构验收 8 步法
    p_accept = sub.add_parser("accept", help="🏗 架构验收 8 步法（生成标准化验收报告 + 真元文档）")
    _shared_args(p_accept)
    p_accept.add_argument("--generate-rules", action="store_true",
                          help="生成 architect.yml 规则模板")
    p_accept.add_argument("--rules", "-r",
                          help="自定义规则文件路径（默认: architect.yml）")
    p_accept.add_argument("--output", "-o", default="",
                          help="输出报告文件路径（默认: 打印到终端）")
    p_accept.add_argument("--json", action="store_true",
                          help="JSON 格式输出")
    p_accept.add_argument("--fail-on-score", type=int, metavar="SCORE",
                          help="架构评分低于此阈值则失败")
    p_accept.add_argument("--diff", action="store_true",
                          help="增量验收模式（只检查 git 修改的文件）")

    # 🆕 ci — 生成 CI/CD 工作流
    p_ci = sub.add_parser("ci", help="⚡ 生成 CI/CD 工作流（GitHub Actions / GitLab CI）")
    _shared_args(p_ci)
    p_ci.add_argument("--platform", choices=["github", "gitlab"], default=None,
                      help="CI 平台（默认: 交互选择）")

    # 🆕 audit — AI 工具权限审计
    p_audit = sub.add_parser("audit", help="🔐 AI 工具权限审计 — 检测权限过载、生成瘦身建议")
    _shared_args(p_audit)
    p_audit.add_argument("--permissions", action="store_true",
                         help="审计 AI 工具权限配置")
    p_audit.add_argument("--tool", choices=["claude", "codex", "grok"], default=None,
                         help="指定工具（默认: 全部）")
    p_audit.add_argument("--fix", action="store_true",
                         help="生成权限瘦身建议")

    # 🆕 notify — 发送通知到 webhook
    p_notify = sub.add_parser("notify", help="🔔 发送检查结果到 Slack / 飞书 / Discord")
    _shared_args(p_notify)
    p_notify.add_argument("--webhook", "-w", default="",
                          help="Webhook URL（或设置 MOAT_WEBHOOK_URL 环境变量）")
    p_notify.add_argument("--report", "-r", default="",
                          help="检查报告 JSON 文件路径")
    p_notify.add_argument("--fail-on-score", type=int, metavar="SCORE",
                          help="发送门禁告警（评分低于此值）")

    # 🆕 architecture - 架构健康报告
    p_arch = sub.add_parser("architecture", help="生成架构健康报告（L2）")
    _shared_args(p_arch)
    p_arch.add_argument("--format", choices=["text", "md", "json"], default="text",
                        help="输出格式（默认: text）")
    p_arch.add_argument("--copy", action="store_true",
                        help="复制报告到剪贴板")

    # baseline
    p_baseline = sub.add_parser("baseline", help="管理基线")
    _shared_args(p_baseline)
    p_baseline.add_argument("action", choices=["save", "show", "diff"],
                            help="基线操作")

    # dashboard
    p_dash = sub.add_parser("dashboard", help="启动 Web 错误看板")
    _shared_args(p_dash)
    p_dash.add_argument("--host", default="127.0.0.1", help="监听地址")
    p_dash.add_argument("--port", "-p", type=int, default=9876, help="监听端口")
    p_dash.add_argument("--log", "-l", help="日志文件路径")

    # fix
    p_fix = sub.add_parser("fix", help="AI 辅助修复")
    _shared_args(p_fix)
    p_fix.add_argument("--no-dry-run", action="store_true",
                       help="实际修复（默认为演练模式）")
    p_fix.add_argument("--format", choices=["text", "md", "json"], default="text",
                       help="输出格式（默认: text）")
    p_fix.add_argument("--copy", action="store_true",
                       help="复制报告到剪贴板")

    # sidecar
    p_sidecar = sub.add_parser("sidecar", help="Sidecar 实时感知守护进程")
    _shared_args(p_sidecar)
    p_sidecar.add_argument("action", choices=["start", "stop", "restart", "status"],
                           help="操作")
    p_sidecar.add_argument("--foreground", action="store_true",
                           help="前台运行（仅 start）")

    # adapter
    p_adapter = sub.add_parser("adapter", help="安装 AI 适配器")
    _shared_args(p_adapter)
    p_adapter.add_argument("type", choices=["claude", "precommit", "all"],
                           default="all", nargs="?",
                           help="适配器类型")

    # ── moat-memory 命令 ──

    # memory
    p_memory = sub.add_parser("memory", help="📖 项目记忆管理（红线/踩坑/模版）")
    _shared_args(p_memory)
    p_memory.add_argument("action", choices=["list", "show", "delete", "stats"],
                          help="操作")
    p_memory.add_argument("type", nargs="?",
                          choices=["redlines", "lessons", "templates", "skills"],
                          help="记忆类型（仅 list/delete）")
    p_memory.add_argument("--id", help="记忆 ID（仅 show/delete）")
    p_memory.add_argument("--limit", type=int, default=20, help="返回条数（默认 20）")
    p_memory.add_argument("--category", help="按分类过滤（仅 redlines）")
    p_memory.add_argument("--domain", help="按领域过滤（仅 templates）")
    p_memory.add_argument("--tool", help="按工具过滤（仅 skills）")
    p_memory.add_argument("--json", action="store_true", help="JSON 格式输出")

    # redline
    p_redline = sub.add_parser("redline", help="📏 管理项目红线")
    _shared_args(p_redline)
    p_redline.add_argument("action", choices=["add", "remove", "list"],
                           help="操作")
    p_redline.add_argument("title", nargs="?", help="红线标题（仅 add）")
    p_redline.add_argument("--description", "-d", help="具体描述")
    p_redline.add_argument("--severity", choices=["critical", "warning", "info"],
                           default="warning", help="严重程度")
    p_redline.add_argument("--category", choices=["architecture", "security", "style", "dependency", "general"],
                           default="general", help="分类")
    p_redline.add_argument("--file-glob", help="适用文件（glob 模式）")
    p_redline.add_argument("--id", help="红线 ID（仅 remove）")

    # template
    p_template = sub.add_parser("template", help="📋 管理经验模版")
    _shared_args(p_template)
    p_template.add_argument("action", choices=["list", "show", "add", "remove", "extract", "import"],
                            help="操作")
    p_template.add_argument("title", nargs="?", help="模版标题（仅 add）")
    p_template.add_argument("--domain", default="general", help="领域分类")
    p_template.add_argument("--source", default="manual", help="来源")
    p_template.add_argument("--importance", type=int, default=5, help="重要性 1-10")
    p_template.add_argument("--tags", help="标签（逗号分隔）")
    p_template.add_argument("--file", help="文件路径（import/extract）")
    p_template.add_argument("--id", help="模版 ID（仅 show/remove）")

    # evolution
    p_evolution = sub.add_parser("evolution", help="进化指标管理")
    _shared_args(p_evolution)
    p_evolution.add_argument("action", choices=["report", "adjust", "record"],
                            help="操作")
    p_evolution.add_argument("--window", type=int, default=24,
                            help="报告时间窗口（小时，默认: 24）")
    p_evolution.add_argument("--format", choices=["text", "json"], default="text",
                            help="输出格式（默认: text）")
    p_evolution.add_argument("--auto", action="store_true",
                            help="自动调整配置")
    p_evolution.add_argument("--pain-threshold", type=int,
                            help="调整 Pain Score 阈值")
    p_evolution.add_argument("--false-positive-tolerance", type=int,
                            help="调整误报容忍度")
    p_evolution.add_argument("--metric-type", choices=[
        "refactor_success", "performance_improvement", "bug_fix_time",
        "false_positive_rate", "dev_velocity"
    ], help="手动记录指标类型（仅 record）")
    p_evolution.add_argument("--value", type=float,
                            help="指标值（仅 record）")

    # verify
    p_verify = sub.add_parser("verify", help="架构验收")
    _shared_args(p_verify)
    p_verify.add_argument("--all", action="store_true", default=True,
                          help="执行完整验收（所有算子）")
    p_verify.add_argument("--operator", "-o",
                          help="执行单个算子（如: directory_responsibility）")
    p_verify.add_argument("--json", action="store_true",
                          help="JSON输出")
    p_verify.add_argument("--fail-on-score", type=int, metavar="SCORE",
                          help="架构评分低于此阈值则失败")

    # gatekeeper
    from moat.gatekeeper.cli import add_gatekeeper_parser
    add_gatekeeper_parser(sub)

    # immune (Moat Immune - AI 工程化测试体系)
    from moat.immune.cli import add_immune_parser
    add_immune_parser(sub)

    # test (已废弃，使用 moat immune unit)
    from moat.ai_test.cli import add_test_parser
    add_test_parser(sub)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    commands = {
        "check": cmd_check,
        "accept": cmd_accept,
        "ci": cmd_ci,
        "audit": cmd_audit,
        "notify": cmd_notify,
        "watch": cmd_watch,
        "init": cmd_init,
        "report": cmd_report,
        "rules": lambda args: cmd_rules_explain(args) if hasattr(args, 'rule_id') else cmd_rules_explain(args),
        "architecture": cmd_architecture,
        "fix": cmd_fix,
        "baseline": cmd_baseline,
        "dashboard": cmd_dashboard,
        "sidecar": cmd_sidecar,
        "evolution": cmd_evolution,
        "adapter": cmd_adapter,
        "verify": cmd_verify,
        "memory": cmd_memory,
        "redline": cmd_redline,
        "template": cmd_template,
        "gatekeeper": cmd_gatekeeper,
        "immune": cmd_immune,
        "test": cmd_test,
    }

    sys.exit(commands[args.command](args))


if __name__ == "__main__":
    main()