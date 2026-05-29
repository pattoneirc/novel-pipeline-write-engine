#!/usr/bin/env python3
"""Shared utility functions for Novel Pipeline.

Consolidates duplicated helpers (count_chinese, split_paragraphs,
split_sentences, load_config, get_db_path, get_novel_id) that were
previously copy-pasted across 10+ files.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Optional

from config_utils import normalize_config, load_json_config, resolve_path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_SENTENCE_SPLIT_RE = re.compile(r"[。！？；\n]+")


def count_chinese(text: str) -> int:
    return len([c for c in text if "\u4e00" <= c <= "\u9fff"])


def split_paragraphs(text: str, min_chars: int = 0) -> list[str]:
    raw = [p.strip() for p in text.split("\n") if p.strip()]
    if min_chars <= 0:
        return raw
    merged: list[str] = []
    buf = ""
    for p in raw:
        cn = count_chinese(p)
        if cn < min_chars:
            buf += p
            if count_chinese(buf) >= min_chars:
                merged.append(buf)
                buf = ""
        else:
            if buf:
                merged.append(buf)
                buf = ""
            merged.append(p)
    if buf:
        merged.append(buf)
    return [p for p in merged if count_chinese(p) >= min_chars]


def split_sentences(text: str, min_length: int = 2) -> list[str]:
    raw = _SENTENCE_SPLIT_RE.split(text)
    return [s.strip() for s in raw if s.strip() and len(s.strip()) >= min_length]


def load_config(config_path: Optional[str] = None, project_root: Optional[Path] = None) -> dict:
    root = project_root or PROJECT_ROOT
    return load_json_config(config_path, root)


def get_db_path(config: dict, project_root: Optional[Path] = None) -> str:
    root = project_root or PROJECT_ROOT
    try:
        ws_dir = root / "workspace"
        registry_file = ws_dir / "registry.json"
        if registry_file.exists():
            registry = json.loads(registry_file.read_text(encoding="utf-8"))
            active = registry.get("active_slot", "")
            if active:
                slot_db = ws_dir / active / "novel.db"
                if slot_db.exists():
                    return str(slot_db)
    except Exception:
        print("[WARN] utils.get_db_path: workspace registry read failed, falling back to config db_path")
    db = config.get("db_path", str(root / "data" / "novel_memory.db"))
    p = Path(db)
    if not p.is_absolute():
        p = root / db
    return str(p)


def get_novel_id(config: dict, slug: str = "demo_novel") -> Optional[int]:
    import sqlite3
    db_path = get_db_path(config)
    if not Path(db_path).exists():
        return None
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.execute("SELECT id FROM novels WHERE slug = ?", (slug,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None
