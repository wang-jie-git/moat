"""
Moat — AI 编码护城河

设置脚本（兼容模式）
"""

from setuptools import setup, find_packages

setup(
    name="moat-ai",
    version="0.9.0",
    description="AI 编码护城河 — 跨语言感知 + 深度记忆 + 智能进化 + 架构验收 + AI 工程化测试体系",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="One Team",
    license="Apache-2.0",
    url="https://github.com/wang-jie-git/moat",
    packages=find_packages(exclude=["tests", "tests.*"]),
    python_requires=">=3.10",
    install_requires=[
        "httpx>=0.27",
        "pyyaml>=6.0",
    ],
    extras_require={
        "dashboard": ["fastapi>=0.100", "uvicorn>=0.22"],
        "sidecar": ["watchdog>=3.0", "fastapi>=0.100", "uvicorn>=0.22"],
        "vscode": ["pyperclip>=1.8"],
        "all": ["fastapi>=0.100", "uvicorn>=0.22", "watchdog>=3.0", "pyperclip>=1.8"],
    },
    entry_points={
        "console_scripts": [
            "moat=moat.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    keywords="ai testing guardrails code-quality python self-evolving",
)
