"""Report, guards, check, and wc commands."""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
try:
    from novel_pipeline.version import get_version
except ImportError:
    from version import get_version
from .common import PROJECT_ROOT, SRC_GUARDS_DIR, load_project_config
from config_utils import resolve_path


def cmd_report():
    """Show most recent guard reports and exports."""
    print("=" * 60)
    v = get_version()
    print(f"  Novel Pipeline - Write Engine {v}")
    print("  Reports")
    print("=" * 60)
    print()

    cfg_data = load_project_config()
    reports_dir = resolve_path(PROJECT_ROOT, cfg_data.get("reports_root", "./exports/reports"))
    if not reports_dir.exists():
        print("  No reports directory found.")
        print(f"  Expected: {reports_dir}")
        return 0

    all_reports = sorted(reports_dir.rglob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not all_reports:
        print("  No report files found.")
        return 0

    print(f"  Found {len(all_reports)} report files in {reports_dir}")
    print()

    for rp in all_reports[:10]:
        mtime = datetime.fromtimestamp(rp.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        size = rp.stat().st_size
        size_str = f"{size:,}B" if size < 1024 else f"{size/1024:.1f}KB"
        status = "?"
        try:
            data = json.loads(rp.read_text(encoding="utf-8"))
            status = data.get("status", data.get("overall_status", "?"))
        except Exception:
            pass
        rel_path = rp.relative_to(reports_dir)
        print(f"  [{status:5s}] {mtime}  {size_str:>8s}  {rel_path}")

    if len(all_reports) > 10:
        print(f"\n  ... and {len(all_reports) - 10} more reports.")

    print()
    return 0

def cmd_guards():
    """List registered guards and their status."""
    print("=" * 60)
    v = get_version()
    print(f"  Novel Pipeline - Write Engine {v}")
    print("  Guard Registry")
    print("=" * 60)
    print()

    # Core guards from registry
    print("  [Core Guards — scripts/]")
    try:
        from guard_registry import GUARD_RUNNERS, GUARD_LEVELS, MODE_GUARDS
        for name in sorted(GUARD_RUNNERS):
            level = GUARD_LEVELS.get(name, "?")
            print(f"    L{level} {name}")
    except ImportError:
        print("    (guard_registry not importable)")

    print()
    print("  [v0.5.0 Guards — src/guards/]")
    v050_guards = ["reader_pull_guard", "voice_pack_guard", "meme_pack_guard"]
    for name in v050_guards:
        fp = SRC_GUARDS_DIR / f"{name}.py"
        exists = "OK" if fp.exists() else "MISSING"
        print(f"    [{exists}] {name}")

    print()
    print("  [Guard Modes]")
    try:
        from guard_registry import MODE_GUARDS
        for mode, guards in MODE_GUARDS.items():
            print(f"    {mode}: {len(guards)} guards")
    except ImportError:
        pass

    print()
    return 0


def cmd_check(file_path: str):
    """Run v0.5.0 guards on a chapter file."""
    fp = Path(file_path)
    if not fp.exists():
        print(f"[ERROR] File not found: {fp}")
        return 1

    content = fp.read_text(encoding="utf-8")
    print("=" * 60)
    print(f"  Checking: {fp.name}")
    print("=" * 60)
    print()

    # Reader pull guard
    print("--- reader_pull_guard ---")
    try:
        from src.guards.reader_pull_guard import run_reader_pull_check
        rp_report = run_reader_pull_check(content, chapter_no=1)
        status = rp_report["status"]
        issues = len(rp_report.get("issues", []))
        print(f"  Status: {status} ({issues} issues)")
        if issues:
            for iss in rp_report.get("issues", [])[:5]:
                print(f"    [{iss['code']}] {iss['message'][:80]}")
    except ImportError as e:
        print(f"  [WARN] reader_pull_guard not available: {e}")
    except Exception as e:
        print(f"  [WARN] reader_pull_guard error: {e}")

    print()

    # Voice pack guard
    print("--- voice_pack_guard ---")
    try:
        from src.guards.voice_pack_guard import run_voice_pack_check
        vp_dir = str(PROJECT_ROOT / "voice_packs")
        vp_report = run_voice_pack_check(content, chapter_no=1, voice_packs_dir=vp_dir)
        status = vp_report["status"]
        issues = len(vp_report.get("issues", [])) or len(vp_report.get("warnings", []))
        print(f"  Status: {status} ({issues} issues)")
        extra = vp_report.get("extra_checks", {})
        for check_name, check_issues in extra.items():
            if check_issues:
                print(f"    {check_name}: {len(check_issues)} issues")
    except ImportError as e:
        print(f"  [WARN] voice_pack_guard not available: {e}")
    except Exception as e:
        print(f"  [WARN] voice_pack_guard error: {e}")

    print()

    # Meme pack guard
    print("--- meme_pack_guard ---")
    try:
        from src.guards.meme_pack_guard import run_meme_pack_check
        mp_dir = str(PROJECT_ROOT / "voice_packs")
        mp_report = run_meme_pack_check(content, chapter_no=1, meme_packs_dir=mp_dir)
        status = mp_report["status"]
        issues = len(mp_report.get("issues", []))
        print(f"  Status: {status} ({issues} issues)")
        for iss in mp_report.get("issues", [])[:5]:
            print(f"    [{iss['code']}] {iss['message'][:80]}")
    except ImportError as e:
        print(f"  [WARN] meme_pack_guard not available: {e}")
    except Exception as e:
        print(f"  [WARN] meme_pack_guard error: {e}")

    print()
    print("=" * 60)
    return 0


def cmd_wc(file_path: str = None):
    """Count Chinese characters in a chapter file.

    Supports both file paths and chapter numbers:
      python novel.py wc 1              # resolves to 第01卷/第1章*.txt
      python novel.py wc chapter.txt    # existing behavior
    """
    if not file_path:
        print("Usage: python novel.py wc <chapter_file.txt|chapter_number>")
        return 1

    fp = None
    # If arg is all digits, resolve to chapter file path
    if file_path.isdigit():
        chapter_no = int(file_path)
        try:
            cfg_data = load_project_config()
            slug = cfg_data.get("default_novel_slug", "demo_novel")
            novels_root = resolve_path(PROJECT_ROOT, cfg_data.get("novels_root", "./novels"))
            ch_dir = Path(novels_root) / slug / "第01卷"
            candidates = list(ch_dir.glob(f"第{chapter_no}章*.txt"))
            if not candidates:
                candidates = list(ch_dir.glob(f"第{chapter_no:02d}章*.txt"))
            if candidates:
                fp = candidates[0]
            else:
                print(f"[ERROR] Chapter {chapter_no} not found in {ch_dir}")
                return 1
        except Exception as e:
            print(f"[ERROR] Could not resolve chapter {file_path}: {e}")
            return 1
    else:
        fp = Path(file_path)

    if not fp.exists():
        print(f"[ERROR] File not found: {fp}")
        return 1
    text = fp.read_text(encoding="utf-8")
    # Count Chinese chars only (U+4E00-U+9FFF plus common CJK extensions)
    cn = sum(1 for c in text if '\u4e00' <= c <= '\u9fff' or '\u3400' <= c <= '\u4dbf')
    total = len(text)
    print(f"  {fp.name}")
    print(f"  汉字: {cn}  |  总字符: {total}  |  占比: {cn*100//total if total else 0}%")
    # Read word_count thresholds from config
    wc_min = 1300; wc_best_min = 1900; wc_max = 3300  # defaults
    try:
        cfg_path = PROJECT_ROOT / "config.json"
        if cfg_path.exists():
            cfg_data = load_project_config()
            wc_cfg = cfg_data.get("word_count", {})
            normal = wc_cfg.get("normal", {})
            wc_min = normal.get("min", wc_min)
            wc_best_min = normal.get("best_min", wc_best_min)
            wc_max = normal.get("max", wc_max)
    except Exception:
        pass
    # Quick check against limits
    if cn < wc_min:
        print(f"  ⚠️  低于最低线 ({wc_min})，需补 {wc_min-cn} 字+")
    elif cn < wc_best_min:
        print(f"  ✅ 通过最低线，距最佳范围还差 {wc_best_min-cn} 字")
    elif cn <= wc_max:
        print(f"  ✅ 在正常范围内")
    else:
        print(f"  ⚠️  超过上限 ({wc_max})")
    return 0
