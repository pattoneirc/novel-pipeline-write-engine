"""Init command."""
from __future__ import annotations

try:
    from novel_pipeline.version import get_version
except ImportError:
    from version import get_version
from .common import PROJECT_ROOT, load_project_config
from config_utils import resolve_path


def cmd_init():
    """Initialize project: create directories, copy config, init DB."""
    print("=" * 60)
    v = get_version()
    print(f"  Novel Pipeline - Write Engine {v}")
    print("  Initialize Project")
    print("=" * 60)
    print()

    cfg_path = PROJECT_ROOT / "config.json"
    if not cfg_path.exists():
        example = PROJECT_ROOT / "config.example.json"
        if example.exists():
            import shutil
            shutil.copy(example, cfg_path)
            print("  [OK] config.json created from config.example.json")
        else:
            print("  [WARN] config.example.json not found")
    else:
        print("  [OK] config.json already exists")

    cfg_data = load_project_config()

    print()
    print("  Initializing database...")
    try:
        from init_db import init_db as db_init
        db_path = resolve_path(PROJECT_ROOT, cfg_data.get("db_path", "./data/novel_memory.db"))
        schema = PROJECT_ROOT / "database" / "schema.sql"
        if not schema.exists():
            print("  [WARN] schema.sql not found, skipping DB init")
        else:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            db_init(str(db_path), str(schema))
            print(f"  [OK] Database initialized: {db_path}")
    except Exception as e:
        print(f"  [WARN] DB init error: {e}")

    dirs = [
        cfg_data.get("novels_root", "./novels"),
        cfg_data.get("outputs_root", "./outputs"),
        str(Path(cfg_data.get("outputs_root", "./outputs")) / "task_cards"),
        str(Path(cfg_data.get("outputs_root", "./outputs")) / "reviews"),
        cfg_data.get("exports_root", "./exports"),
        cfg_data.get("reports_root", "./exports/reports"),
        cfg_data.get("tmp_root", "./tmp"),
    ]
    for d in dirs:
        p = resolve_path(PROJECT_ROOT, d)
        p.mkdir(parents=True, exist_ok=True)
        print(f"  [OK] Directory ready: {p.relative_to(PROJECT_ROOT) if p.is_relative_to(PROJECT_ROOT) else p}")

    print()
    print("  Project initialized. Run 'python novel.py demo' to test.")
    return 0
