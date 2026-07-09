"""
Karpathy Principles 加载器

从 karpathy_principles.yaml 加载原则定义。
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from moat.rules import Principle, PrincipleViolation, PrinciplesLoader

# 为了向后兼容，导出相同接口
__all__ = ["PrinciplesLoader", "Principle", "PrincipleViolation"]
