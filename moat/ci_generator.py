"""CI 集成生成器 — `moat ci` 自动生成 GitHub Actions workflow

用途：
  moat ci                    # 交互式生成（选择平台）
  moat ci --platform github  # 直接生成 GitHub Actions
  moat ci --platform gitlab  # 直接生成 GitLab CI

CI 工作流功能：
  - PR 自动触发 `moat check` 四层门禁
  - `moat check --leak` 泄露风险检测
  - `moat accept --diff --fail-on-score 60` 架构验收门禁
  - 结果以 PR Comment 形式展示
"""

from pathlib import Path
from typing import Literal

Platform = Literal["github", "gitlab"]

# ── GitHub Actions 工作流模板 ──

GITHUB_WORKFLOW = """# Moat AI 编码护城河 — CI 自动检查
# 生成命令: moat ci --platform github
# 文档: https://github.com/wang-jie-git/moat

name: Moat CI

on:
  pull_request:
    branches: [main, master, develop]
  push:
    branches: [main, master]

jobs:
  moat-check:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write  # 用于 PR Comment

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # 完整 git 历史，支持 --diff 模式

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Moat
        run: pip install moat-ai

      - name: ⚡ 快速检查
        run: moat check --quick
        continue-on-error: true

      - name: 🔒 泄露风险检测
        run: moat check --leak
        continue-on-error: true

      - name: 🏗 架构验收（增量）
        id: accept
        run: |
          moat accept --diff --fail-on-score 60 --json > moat-report.json 2>&1 || true
        continue-on-error: true

      - name: 📋 生成 PR 评论
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            let summary = '## 🛡️ Moat 检查报告\\n\\n';
            summary += '| 检查项 | 状态 |\\n';
            summary += '|--------|------|\\n';

            try {
              const report = JSON.parse(fs.readFileSync('moat-report.json', 'utf8'));
              const score = report.overall_score || 0;
              const passed = report.passed ? '✅' : '❌';
              summary += `| 架构验收 | ${passed} ${score}/100 |\\n`;

              if (report.rules) {
                for (const rule of report.rules) {
                  const icon = rule.passed ? '✅' : '❌';
                  summary += `| ${rule.title} | ${icon} |\\n`;
                }
              }
            } catch (e) {
              summary += '| 架构验收 | ⚠️ 未生成 |\\n';
            }

            // 获取 PR 的已有评论
            const { data: comments } = await github.rest.issues.listComments({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
            });

            // 查找已有的 Moat 评论并更新
            const moatComment = comments.find(c => c.body.includes('Moat 检查报告'));
            if (moatComment) {
              await github.rest.issues.updateComment({
                owner: context.repo.owner,
                repo: context.repo.repo,
                comment_id: moatComment.id,
                body: summary,
              });
            } else {
              await github.rest.issues.createComment({
                owner: context.repo.owner,
                repo: context.repo.repo,
                issue_number: context.issue.number,
                body: summary,
              });
            }
"""

GITLAB_WORKFLOW = """# Moat AI 编码护城河 — GitLab CI 自动检查
# 生成命令: moat ci --platform gitlab

stages:
  - moat-check

moat-check:
  stage: moat-check
  image: python:3.11-slim
  script:
    - pip install moat-ai
    - moat check --quick
    - moat check --leak
    - moat accept --diff --fail-on-score 60
  only:
    - merge_requests
    - main
    - master
"""


def cmd_ci(args) -> int:
    """生成 CI/CD 工作流文件

    用法:
        moat ci                     # 交互选择
        moat ci --platform github   # GitHub Actions
        moat ci --platform gitlab   # GitLab CI
    """
    from pathlib import Path

    project_root = Path(args.project).resolve()
    platform = args.platform

    if not platform:
        # 交互选择
        print("选择 CI 平台:")
        print("  1. GitHub Actions")
        print("  2. GitLab CI")
        choice = input("请输入 1 或 2 (默认: 1): ").strip()
        platform = "github" if choice != "2" else "gitlab"

    if platform == "github":
        workflow_dir = project_root / ".github" / "workflows"
        workflow_dir.mkdir(parents=True, exist_ok=True)
        workflow_path = workflow_dir / "moat.yml"
        workflow_path.write_text(GITHUB_WORKFLOW.strip() + "\n")
        print(f"✅ GitHub Actions 工作流已生成: {workflow_path}")
        print(f"   下次 push 到 PR 时自动触发检查")
    elif platform == "gitlab":
        ci_path = project_root / ".gitlab-ci.yml"
        if ci_path.exists():
            print(f"⚠️  {ci_path} 已存在，将追加 Moat 配置")
            existing = ci_path.read_text()
            if "moat" in existing.lower():
                print(f"   已存在 Moat 配置，跳过")
                return 0
            with open(ci_path, "a") as f:
                f.write("\n" + GITLAB_WORKFLOW.strip() + "\n")
            print(f"✅ Moat 配置已追加到 {ci_path}")
        else:
            ci_path.write_text(GITLAB_WORKFLOW.strip() + "\n")
            print(f"✅ GitLab CI 配置已生成: {ci_path}")

    # 自动创建 .moat/config.json（如果不存在）
    moat_config = project_root / ".moat" / "config.json"
    if not moat_config.exists():
        moat_config.parent.mkdir(parents=True, exist_ok=True)
        import json
        moat_config.write_text(json.dumps({
            "version": "1.0",
            "ci_mode": True,
            "fail_on_score": 60,
            "checks": ["quick", "leak", "accept"],
        }, indent=2))
        print(f"✅ Moat 配置已生成: {moat_config}")

    print(f"\n📋 建议配置:")
    print(f"   在 GitHub 仓库 Settings → Secrets → Actions 中添加:")
    print(f"   无额外配置需要。Moat 纯本地运行，无需 API Key。")
    return 0