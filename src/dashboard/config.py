"""Dashboard configuration — reads from project config.json and env."""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def load_config():
    cfg_path = PROJECT_ROOT / "config.json"
    if cfg_path.exists():
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    return {}

def get_novels_root():
    cfg = load_config()
    return Path(cfg.get("novels_root", str(PROJECT_ROOT / "novels")))

def get_db_path():
    cfg = load_config()
    return cfg.get("db_path", str(PROJECT_ROOT / "data" / "novel_memory.db"))
