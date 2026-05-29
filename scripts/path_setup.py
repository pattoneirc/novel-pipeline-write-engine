#!/usr/bin/env python3
"""
path_setup.py — 集中式路径设置模块

确保 scripts/、src/、src/guards/ 等标准路径在 sys.path 中，
消除各模块各自内联的 sys.path.insert 重复代码。

用法：
    from path_setup import ensure_paths
    ensure_paths()
"""

import sys
from pathlib import Path


def ensure_paths() -> None:
    """将项目标准目录加入 sys.path（如果尚未加入）。

    覆盖路径（相对于项目根）：
      - scripts/
      - src/
      - src/guards/
      - src/cli/
    """
    # 检测项目根：此文件在 scripts/ 下
    root = Path(__file__).resolve().parent.parent

    _add_path(root)                     # 项目根
    _add_path(root / "scripts")         # scripts/
    _add_path(root / "src")             # src/
    _add_path(root / "src" / "guards")  # src/guards/
    _add_path(root / "src" / "cli")     # src/cli/


def _add_path(path: Path) -> None:
    p = str(path.resolve())
    if p not in sys.path:
        sys.path.insert(0, p)
