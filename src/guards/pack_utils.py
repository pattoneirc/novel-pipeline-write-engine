#!/usr/bin/env python3
"""
pack_utils.py — Unified pack loading for voice_pack_guard and meme_pack_guard.

Consolidates the duplicated _load_yaml_pack / _load_json_pack functions
that were previously copy-pasted across voice_pack_guard.py and
meme_pack_guard.py.

Each loader returns a dict with ALL known fields; consumers simply use
the fields they need and ignore the rest.
"""

import json
from pathlib import Path
from typing import Optional


def _load_yaml_pack(path: Path) -> Optional[dict]:
    """Try to load a YAML pack file, extracting all known fields."""
    try:
        import yaml
    except ImportError:
        return None

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return None
    except Exception:
        return None

    pack_id = raw.get("id") or raw.get("name") or path.stem

    markers = (raw.get("variants", []) + raw.get("allowed_terms", []) +
               raw.get("preferred", []) + raw.get("signature_phrases", []))

    freq = raw.get("frequency", {})
    max_per_chapter = (freq.get("max_per_chapter", 5)
                       if isinstance(freq, dict)
                       else raw.get("overuse_warning_threshold", 5))
    cooldown_chapters = (freq.get("cooldown_chapters", 3)
                         if isinstance(freq, dict)
                         else raw.get("cooldown_chapters", 3))

    sev_limit = raw.get("severity_limit", {})
    max_scene_seriousness = (sev_limit.get("max_scene_seriousness", "medium")
                             if isinstance(sev_limit, dict)
                             else raw.get("max_scene_seriousness", "medium"))

    return {
        "pack_id": pack_id,
        "type": raw.get("type", ""),
        "name": raw.get("name", raw.get("display_name", "")),
        "markers": markers,
        "soft_markers": raw.get("soft_markers", raw.get("allowed_markers", [])),
        "danger_markers": (raw.get("banned_terms", []) + raw.get("banned_markers", []) +
                           raw.get("danger_markers", [])),
        "overuse_warning_threshold": max_per_chapter,
        "dialect_level": (raw.get("level", 0) if isinstance(raw.get("level"), int)
                          else raw.get("dialect_level", 0)),
        "max_density_per_1000_chars": raw.get("max_density_per_1000_chars"),
        "cooldown_chapters": cooldown_chapters,
        "allowed_roles": raw.get("allowed_roles", []),
        "forbidden_roles": raw.get("forbidden_roles", []),
        "severity_limit": sev_limit,
        "max_scene_seriousness": max_scene_seriousness,
    }


def _load_json_pack(path: Path) -> Optional[dict]:
    """Load a JSON pack file, extracting all known fields."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    return {
        "pack_id": raw.get("pack_id", path.stem),
        "type": raw.get("type", ""),
        "name": raw.get("name", ""),
        "markers": raw.get("allowed_markers", raw.get("markers", [])),
        "soft_markers": raw.get("soft_markers", []),
        "danger_markers": raw.get("danger_markers", []) + raw.get("banned_markers", []),
        "overuse_warning_threshold": raw.get("overuse_warning_threshold", 5),
        "dialect_level": raw.get("dialect_level", 0),
        "max_density_per_1000_chars": raw.get("max_density_per_1000_chars"),
        "cooldown_chapters": raw.get("cooldown_chapters", 3),
        "allowed_roles": raw.get("allowed_roles", raw.get("suitable_archetypes", [])),
        "forbidden_roles": raw.get("forbidden_roles", raw.get("forbidden_archetypes", [])),
        "severity_limit": raw.get("severity_limit", {}),
        "max_scene_seriousness": raw.get("max_scene_seriousness", "medium"),
    }
