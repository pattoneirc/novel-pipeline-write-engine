"""Shared state and helpers for CLI commands."""
from __future__ import annotations

import sys
import json
from pathlib import Path

_CANDIDATE_MARKERS = ["config.example.json", "VERSION", "novel.py"]


def _detect_project_root() -> Path:
    root = Path(__file__).resolve().parent.parent.parent.parent
    if any((root / m).exists() for m in _CANDIDATE_MARKERS):
        return root
    cwd = Path.cwd().resolve()
    if any((cwd / m).exists() for m in _CANDIDATE_MARKERS):
        return cwd
    for p in [cwd] + list(cwd.parents):
        if any((p / m).exists() for m in _CANDIDATE_MARKERS):
            return p
    return root


PROJECT_ROOT = _detect_project_root()
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
SRC_GUARDS_DIR = PROJECT_ROOT / "src" / "guards"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
from path_setup import ensure_paths; ensure_paths()

from config_utils import normalize_config, load_json_config, resolve_path


def load_project_config() -> dict:
    cfg_path = PROJECT_ROOT / "config.json"
    if cfg_path.exists():
        return load_json_config(cfg_path, PROJECT_ROOT)
    return load_json_config(PROJECT_ROOT / "config.example.json", PROJECT_ROOT)


def cfg_path(key: str, default: str) -> Path:
    cfg = load_project_config()
    return resolve_path(PROJECT_ROOT, cfg.get(key, default))


def _get_workspace_dir() -> Path:
    return PROJECT_ROOT / "workspace"


def _get_active_db_path() -> Path:
    import json as _json
    ws_dir = _get_workspace_dir()
    registry_file = ws_dir / "registry.json"

    if registry_file.exists():
        try:
            registry = _json.loads(registry_file.read_text(encoding="utf-8"))
            active = registry.get("active_slot", "")
            if active:
                slot_db = ws_dir / active / "novel.db"
                if slot_db.exists():
                    return slot_db
        except Exception:
            print("[WARN] common._get_active_db_path: workspace registry read failed")

    try:
        cfg_data = load_project_config()
        db = cfg_data.get("db_path", "./data/novel_memory.db")
        p = Path(db)
        if not p.is_absolute():
            p = PROJECT_ROOT / db
        return p
    except Exception:
        return PROJECT_ROOT / "data" / "novel_memory.db"


def _get_default_slug(cfg_path=None):
    try:
        return load_project_config().get("default_novel_slug", "demo_novel")
    except Exception:
        return "demo_novel"


def _get_novels_root(cfg_path=None):
    try:
        cfg = load_project_config()
        return str(resolve_path(PROJECT_ROOT, cfg.get("novels_root", "./novels")))
    except Exception:
        return str(PROJECT_ROOT / "novels")


def _get_outline_dir():
    nr = Path(_get_novels_root())
    return str(nr.parent / "大纲")


def _get_outline_manager():
    from scripts.outline.outline_manager import OutlineManager
    return OutlineManager(PROJECT_ROOT)


def _check_outline_gate() -> int:
    try:
        mgr = _get_outline_manager()
        if not mgr.has_active_outline():
            outline_dir = Path(_get_outline_dir())
            print("=" * 60)
            print("  ⛔ 没有激活的大纲")
            print("=" * 60)
            print()
            print("  当前小说没有激活大纲，不能开写。")
            print()
            print(f"  💡 把大纲.txt放到：{outline_dir}/你的小说名/大纲.txt")
            print()
            print(f"  然后运行 python novel.py outline add")
            return 1
    except Exception:
        print("[WARN] common._check_outline_gate: outline check failed")
    return 0


def _story_exists() -> bool:
    return (PROJECT_ROOT / ".story").exists()


def _story_missing_msg() -> str:
    return "请先运行 python novel.py story init"
