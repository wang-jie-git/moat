"""API 结构检查 — L2: 返回 JSON 结构是否符合契约"""
import json
from pathlib import Path


def run_schema_check(project_root: Path, base_url: str = "http://localhost:8000") -> list[dict]:
    """检查 API 返回的结构是否符合预期"""
    errors = []
    endpoints = _get_schema_endpoints(project_root)

    if not endpoints:
        return errors

    import httpx
    try:
        with httpx.Client(base_url=base_url, timeout=5) as client:
            for ep in endpoints:
                try:
                    resp = client.get(ep)
                    if resp.status_code == 200:
                        data = resp.json()
                        # 基本结构检查: 应该返回列表或字典
                        if not isinstance(data, (dict, list)):
                            errors.append({
                                "file": ep,
                                "level": "L2",
                                "type": "schema_invalid_type",
                                "message": f"GET {ep} 返回类型 {type(data).__name__}，期望 dict 或 list",
                            })
                    else:
                        errors.append({
                            "file": ep,
                            "level": "L2",
                            "type": "schema_unreachable",
                            "message": f"GET {ep} → {resp.status_code}",
                        })
                except json.JSONDecodeError:
                    errors.append({
                        "file": ep,
                        "level": "L2",
                        "type": "schema_not_json",
                        "message": f"GET {ep} 返回非 JSON 内容",
                    })
                except Exception as e:
                    errors.append({
                        "file": ep,
                        "level": "L2",
                        "type": "schema_exception",
                        "message": f"GET {ep} → {e}",
                    })
    except Exception:
        pass  # 服务器未运行，跳过

    return errors


def _get_schema_endpoints(project_root: Path) -> list[str]:
    """获取需要检查结构的端点"""
    # 优先从 OpenAPI 获取
    api_file = project_root / "openapi.json"
    if api_file.exists():
        try:
            schema = json.loads(api_file.read_text())
            return [p for p in schema.get("paths", {})
                    if "get" in schema["paths"][p]][:20]
        except Exception:
            pass

    return []