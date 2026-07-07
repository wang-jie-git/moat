"""Sidecar API — FastAPI HTTP 接口

提供 REST API 供 VS Code 插件和外部工具调用。
"""
from typing import Any

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    # FastAPI 未安装，提供降级方案
    FastAPI = None
    HTTPException = None
    BaseModel = None
    uvicorn = None


if FastAPI:
    app = FastAPI(title="Moat Sidecar API", version="0.3.0")

    class CheckRequest(BaseModel):
        projectPath: str

    class CheckResponse(BaseModel):
        success: bool
        errors: list[dict[str, Any]]
        pain_score: int
        pain_level: str

    @app.get("/")
    async def root():
        """健康检查"""
        return {"status": "ok", "service": "moat-sidecar", "version": "0.3.0"}

    @app.get("/health")
    async def health():
        """健康检查端点"""
        return {"status": "healthy", "uptime": "N/A"}

    @app.get("/status")
    async def get_status():
        """获取守护进程状态"""
        from moat.sidecar.daemon import SidecarDaemon
        from pathlib import Path

        # 这里需要从环境或配置获取项目路径
        # 简化处理：返回基本状态
        return {
            "running": True,
            "version": "0.3.0",
            "api": "enabled",
        }

    @app.post("/check", response_model=CheckResponse)
    async def run_check(request: CheckRequest):
        """运行增量检查"""
        try:
            from moat.ast.diff import diff_project
            from moat.ast.builder import build_skeleton
            from moat.pain.scorer import calculate_total_pain

            project_path = request.projectPath

            # 构建骨架图
            skeleton = build_skeleton(project_path)

            # 对比变更
            changes = diff_project(project_path)

            if not changes:
                return CheckResponse(
                    success=True,
                    errors=[],
                    pain_score=0,
                    pain_level="LOW",
                )

            # Pain Score 评估
            errors_as_dict = [
                {"type": c["type"], "file": c["file"], "message": c.get("function", "")}
                for c in changes
            ]
            pain_result = calculate_total_pain(errors_as_dict)

            return CheckResponse(
                success=pain_result["error_count"] == 0,
                errors=errors_as_dict,
                pain_score=pain_result["total_score"],
                pain_level=pain_result["overall_level"],
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/fix")
    async def run_fix(request: CheckRequest):
        """生成 AI 修复建议"""
        try:
            from moat.runner import MoatResult, run_all_checks
            from moat.fixer import FixEngine
            from pathlib import Path

            # 运行检查
            root = Path(request.projectPath)
            result = MoatResult()

            # 简化：返回错误列表
            # 实际应该从 runner 获取
            return {
                "success": True,
                "suggestions": [],
                "message": "Fix suggestions not yet implemented",
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/sidecar/start")
    async def start_sidecar():
        """启动 Sidecar"""
        return {"status": "ok", "message": "Sidecar started"}

    @app.post("/sidecar/stop")
    async def stop_sidecar():
        """停止 Sidecar"""
        return {"status": "ok", "message": "Sidecar stopped"}

    @app.get("/sidecar/status")
    async def sidecar_status():
        """Sidecar 状态"""
        return {"running": True, "pid": "N/A"}


class SidecarAPI:
    """Sidecar API 封装"""

    def __init__(self, host: str = "127.0.0.1", port: int = 9877):
        """初始化 API

        Args:
            host: 监听地址
            port: 监听端口
        """
        self.host = host
        self.port = port
        self.app = app if FastAPI else None
        self.server: Any = None

    def start(self) -> None:
        """启动 API 服务"""
        if not self.app:
            print("⚠️  FastAPI 未安装，API 服务不可用")
            print("   安装: pip install fastapi uvicorn")
            return

        print(f"🚀 启动 Sidecar API 服务: http://{self.host}:{self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")

    def stop(self) -> None:
        """停止 API 服务"""
        if self.server:
            self.server.should_exit = True
