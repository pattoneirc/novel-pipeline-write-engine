"""/story/health — Check story chain health."""
import json
from pathlib import Path
from typing import List

STORY_DIR = ".story"


def check_health(project_root: Path) -> dict:
    """Run story health checks and return report."""
    story = project_root / STORY_DIR
    issues = []
    ok = True

    # Check story dir exists
    if not story.exists():
        return {"ok": False, "issues": ["Story directory not initialized. Run: python novel.py story init"]}

    # Check master setting
    ms = story / "master_setting.json"
    if not ms.exists():
        issues.append("master_setting.json missing")
        ok = False

    # Check memory files
    memory = story / "memory"
    for fname in ["characters.json", "promises.json", "world_facts.json"]:
        if not (memory / fname).exists():
            issues.append(f"memory/{fname} missing")

    # Check for broken chapter chain
    chapters_dir = story / "chapters"
    commits_dir = story / "commits"
    if chapters_dir.exists() and commits_dir.exists():
        contracts = sorted(chapters_dir.glob("chapter_*_contract.json"))
        commits = sorted(commits_dir.glob("chapter_*_commit.json"))
        if len(contracts) > len(commits):
            issues.append(f"Warning: {len(contracts)} contracts but only {len(commits)} commits — {len(contracts)-len(commits)} uncommitted chapters")
        # Check for gaps
        contract_nums = [int(f.stem.split("_")[1]) for f in contracts]
        commit_nums = [int(f.stem.split("_")[1]) for f in commits]
        if contract_nums:
            expected = set(range(1, max(contract_nums) + 1))
            missing = expected - set(contract_nums)
            if missing:
                issues.append(f"Missing contracts for chapters: {sorted(missing)}")

        # Check each commit for empty/invalid data
        for cf in commits:
            try:
                commit = json.loads(cf.read_text(encoding="utf-8"))
                ch = commit.get("chapter_no", "?")
                wc = commit.get("word_count", 0)
                title = commit.get("title", "")
                events = commit.get("events", [])
                guard = commit.get("guard_summary", {})
                has_only_placeholder = (
                    wc <= 0
                    and not events
                    and guard.get("note") == "手动生成"
                    and not guard.get("status")
                )
                if wc <= 0:
                    issues.append(f"Empty commit: ch{ch} word_count={wc} — 章节文件可能未找到或为空")
                if not title:
                    issues.append(f"Empty commit: ch{ch} title missing")
                if has_only_placeholder:
                    issues.append(f"Placeholder commit: ch{ch} 仅有占位数据，word_count=0, events=[]")
            except Exception as e:
                issues.append(f"Broken commit file: {cf.name} — {e}")

    # Check open promises
    promises_file = memory / "promises.json"
    if promises_file.exists():
        promises = json.loads(promises_file.read_text(encoding="utf-8"))
        open_promises = [p for p in promises if not p.get("resolved")]
        if open_promises:
            issues.append(f"Open promises: {len(open_promises)} — chapters: {set(p['chapter'] for p in open_promises)}")

    # Check event ledger
    ledger = story / "events" / "event_ledger.jsonl"
    if ledger.exists():
        lines = ledger.read_text(encoding="utf-8").strip().split("\n")
        event_count = len([l for l in lines if l.strip()])
    else:
        event_count = 0

    return {
        "ok": len(issues) == 0,
        "story_dir": str(story),
        "issues": issues,
        "contract_count": len(list((story/"chapters").glob("chapter_*_contract.json"))) if (story/"chapters").exists() else 0,
        "commit_count": len(list((story/"commits").glob("chapter_*_commit.json"))) if (story/"commits").exists() else 0,
        "event_count": event_count,
    }
