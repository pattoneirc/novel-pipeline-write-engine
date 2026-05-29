#!/usr/bin/env python3
"""
conftest.py — pytest 统一配置

自动将 scripts/ 和 scripts/guards/ 加入 sys.path，
使所有测试文件无需各自写 sys.path.insert(0, ...) 样板代码。
"""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
for _sub in ["scripts", "scripts/guards"]:
    _p = str(_root / _sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)
