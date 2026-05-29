"""Story contract, query, learn, board, genre, style commands."""
from __future__ import annotations

import sys
from pathlib import Path
try:
    from novel_pipeline.version import get_version
except ImportError:
    from version import get_version
from .common import (
    PROJECT_ROOT, load_project_config,
    _story_exists, _story_missing_msg, _check_outline_gate,
    _get_novels_root, _get_active_db_path,
)
from config_utils import resolve_path


def cmd_story(args):
    """Story contract system: init, contract, commit, health."""
    from scripts.story import story_init, contract_builder, commit_builder, story_health

    action = getattr(args, "story_action", None)

    if action == "init":
        if _story_exists():
            print("  .story/ 目录已存在。如需重建请先删除。")
            return 0
        result = story_init.init_story(PROJECT_ROOT)
        print(f"  [OK] .story/ 已初始化")
        for item in result.get("created", []):
            print(f"    + {item}")
        print(f"\n  目录: {result['story_dir']}")
        return 0

    elif action == "contract":
        if not _story_exists():
            print(f"  {_story_missing_msg()}")
            return 1
        # No-outline gate
        if _check_outline_gate():
            return 1
        chapter_no = int(getattr(args, "chapter_no", "1") or "1")
        # Try loading previous commit for context
        prev_commit = None
        if chapter_no > 1:
            prev_commit_path = PROJECT_ROOT / ".story" / "commits" / f"chapter_{chapter_no-1:03d}_commit.json"
            if prev_commit_path.exists():
                import json as _json
                prev_commit = _json.loads(prev_commit_path.read_text(encoding="utf-8"))

        contract = contract_builder.build_contract(PROJECT_ROOT, chapter_no, prev_commit=prev_commit)
        saved = contract_builder.save_contract(PROJECT_ROOT, chapter_no, contract)
        print(f"  [OK] 第{chapter_no}章合同已生成")
        print(f"  保存至: {saved}")
        print(f"  开放伏笔: {len(contract.get('open_promises_to_keep', []))} 个")
        print(f"  活跃角色: {len(contract.get('active_characters', []))} 个")
        return 0

    elif action == "commit":
        if not _story_exists():
            print(f"  {_story_missing_msg()}")
            return 1
        chapter_no = int(getattr(args, "chapter_no", "1") or "1")
        
        # P0-2: Verify contract exists before allowing commit
        contract_path = PROJECT_ROOT / ".story" / "chapters" / f"chapter_{chapter_no:03d}_contract.json"
        if not contract_path.exists():
            print(f"  [FAIL] 第{chapter_no}章没有合同，不能提交。请先执行：python novel.py story contract {chapter_no}")
            return 1

        # Read real chapter file — use config's novels_root
        novels_dir = PROJECT_ROOT / "novels"
        if (PROJECT_ROOT / "config.json").exists():
            import json as _json
            try:
                cfg = _json.loads((PROJECT_ROOT / "config.json").read_text(encoding="utf-8"))
                nr = cfg.get("novels_root") or cfg.get("paths", {}).get("novels_root", "novels")
                novels_dir = Path(nr) if Path(nr).is_absolute() else PROJECT_ROOT / nr
            except Exception:
                pass
        slug = "demo_novel"
        # Also try the config's default slug
        slugs_to_try = [slug]
        try:
            if (PROJECT_ROOT / "config.json").exists():
                cfg2 = _json.loads((PROJECT_ROOT / "config.json").read_text(encoding="utf-8"))
                ds = cfg2.get("default_novel_slug") or cfg2.get("novel", {}).get("default_slug", "")
                if ds and ds != slug:
                    slugs_to_try.append(ds)
        except Exception:
            pass
        import re as _re
        ch_fp = None
        # Search multiple possible locations
        search_dirs = []
        for s in slugs_to_try:
            search_dirs.append(novels_dir / s / "第01卷")
            search_dirs.append(novels_dir / s)
            search_dirs.append(PROJECT_ROOT / "novels" / s / "第01卷")
        for sd in search_dirs:
            if not sd.exists(): continue
            for pattern in [f"第{chapter_no}章*.txt", f"第{chapter_no:02d}章*.txt"]:
                candidates = list(sd.glob(pattern))
                if candidates:
                    ch_fp = candidates[0]
                    break
            if ch_fp: break
        wc = 0
        ch_title = f"第{chapter_no}章"
        if ch_fp and ch_fp.exists():
            text = ch_fp.read_text(encoding="utf-8")
            wc = sum(1 for c in text if '\u4e00' <= c <= '\u9fff' or '\u3400' <= c <= '\u4dbf')
            ch_title = ch_fp.stem.replace("_", " ")
        
        commit = commit_builder.build_commit(
            PROJECT_ROOT, chapter_no,
            chapter_title=ch_title,
            word_count=wc,
            guard_summary={"note": "手动生成"} if wc == 0 else {},
        )
        saved = commit_builder.save_commit(PROJECT_ROOT, chapter_no, commit)
        print(f"  [OK] 第{chapter_no}章提交记录已生成")
        print(f"  保存至: {saved}")
        return 0

    elif action == "health":
        if not _story_exists():
            print(f"  {_story_missing_msg()}")
            return 1
        report = story_health.check_health(PROJECT_ROOT)
        print("=" * 60)
        print("  故事链健康检查")
        print("=" * 60)
        status = report["status"]
        print(f"  状态: {status}")
        print(f"  合同数: {report.get('contract_count', 0)}")
        print(f"  提交数: {report.get('commit_count', 0)}")
        print(f"  事件数: {report.get('event_count', 0)}")
        warnings = report.get("warnings", [])
        failures = report.get("failures", [])
        if failures:
            print(f"\n  失败 ({len(failures)}):")
            for iss in failures:
                print(f"    ✗ {iss}")
        if warnings:
            print(f"\n  警告 ({len(warnings)}):")
            for iss in warnings:
                print(f"    ⚠ {iss}")
        if not warnings and not failures:
            empty_hints = report.get("empty_hints", [])
            if empty_hints:
                print(f"\n  💡 提示:")
                for hint in empty_hints:
                    print(f"    · {hint}")
            else:
                print("\n  未发现问题。")
        print()
        return 0 if status == "OK" else (1 if status == "FAIL" else 0)

    else:
        print("Usage: python novel.py story {init|contract|commit|health}")
        return 1


def cmd_query(args):
    """Query project memory for matching content."""
    if not _story_exists():
        print(f"  {_story_missing_msg()}")
        return 1

    question = " ".join(getattr(args, "question", []) or [])
    if not question.strip():
        print("Usage: python novel.py query <question>")
        print("Example: python novel.py query 主角的名字是什么")
        return 1

    print(f"  查询: {question}")
    print()

    story = PROJECT_ROOT / ".story"

    # Search memory JSON files
    memory = story / "memory"
    hits = 0

    for fname, label in [("characters.json", "角色"), ("promises.json", "伏笔"),
                          ("world_facts.json", "世界观"), ("learned_rules.json", "规则")]:
        fp = memory / fname
        if not fp.exists():
            continue
        try:
            import json as _json
            data = _json.loads(fp.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for item in data:
                    text = str(item)
                    if question.lower() in text.lower() or any(kw in text for kw in question.split()):
                        hits += 1
                        preview = text[:120].replace("\n", " ")
                        print(f"  [{label}] {preview}...")
        except Exception:
            pass

    # Search event ledger
    ledger = story / "events" / "event_ledger.jsonl"
    if ledger.exists():
        try:
            for line in ledger.read_text(encoding="utf-8").strip().split("\n"):
                if not line.strip():
                    continue
                if question.lower() in line.lower() or any(kw in line for kw in question.split()):
                    hits += 1
                    import json as _json
                    evt = _json.loads(line)
                    preview = str(evt.get("event", line))[:120]
                    print(f"  [事件 ch{evt.get('chapter', '?')}] {preview}...")
        except Exception:
            pass

    # Search contracts
    chapters_dir = story / "chapters"
    if chapters_dir.exists():
        for cf in sorted(chapters_dir.glob("chapter_*_contract.json")):
            try:
                import json as _json
                text = cf.read_text(encoding="utf-8")
                if question.lower() in text.lower() or any(kw in text for kw in question.split()):
                    hits += 1
                    data = _json.loads(text)
                    ch_no = data.get('chapter_no', '?')
                    ch_title = data.get('chapter_title', '')
                    scene_goal = data.get('required_scene_goal', '')
                    open_promises = data.get('open_promises_to_keep', [])
                    forbidden = data.get('forbidden_changes', [])
                    active_chars = data.get('active_characters', [])
                    min_rules = data.get('minimum_quality_rules', {})
                    must_advance = min_rules.get('must_advance_plot', None)
                    print(f"  [合同 ch{ch_no}] {ch_title}")
                    if scene_goal:
                        print(f"    场景目标: {scene_goal}")
                    if open_promises:
                        print(f"    开放伏笔 ({len(open_promises)}):")
                        for p in open_promises[:3]:
                            print(f"      · {str(p)[:80]}")
                        if len(open_promises) > 3:
                            print(f"      ...还有 {len(open_promises)-3} 个")
                    if forbidden:
                        print(f"    禁止变更 ({len(forbidden)}):")
                        for f in forbidden[:3]:
                            print(f"      · {str(f)[:80]}")
                        if len(forbidden) > 3:
                            print(f"      ...还有 {len(forbidden)-3} 项")
                    if must_advance is not None:
                        print(f"    必须推进剧情: {'是' if must_advance else '否'}")
                    if active_chars:
                        print(f"    活跃角色: {len(active_chars)} 个")
            except Exception:
                pass

    if hits == 0:
        print("  未找到匹配的记忆。")
    else:
        print(f"\n  共 {hits} 条匹配。")
    return 0


def cmd_learn(args):
    """Add/list/remove learned writing rules."""
    if not _story_exists():
        print(f"  {_story_missing_msg()}")
        return 1

    import json as _json

    rules_file = PROJECT_ROOT / ".story" / "memory" / "learned_rules.json"
    rules = []
    if rules_file.exists():
        try:
            rules = _json.loads(rules_file.read_text(encoding="utf-8"))
        except Exception:
            rules = []

    action = getattr(args, "action", "list")
    rule_text = " ".join(getattr(args, "rule", []) or [])

    # Auto-detect: if action is not a known command, treat it as rule text
    if action not in ("add", "list", "remove"):
        rule_text = action + (" " + rule_text if rule_text else "")
        action = "add"

    if action == "list":
        if not rules:
            print("  暂无已学规则。用 python novel.py learn add <规则> 添加。")
            return 0
        print(f"  已学规则 ({len(rules)}):")
        for i, r in enumerate(rules):
            rule_str = r.get("rule", str(r))
            ch = r.get("chapter", "?")
            print(f"    [{i+1}] (ch{ch}) {rule_str}")
        return 0

    elif action == "add":
        if not rule_text.strip():
            print("Usage: python novel.py learn add <规则内容>")
            print("Example: python novel.py learn add 主角李明的口头禅是'走着瞧'")
            return 1
        from datetime import datetime
        rules.append({
            "rule": rule_text,
            "chapter": "manual",
            "added_at": datetime.now().isoformat(),
        })
        rules_file.write_text(_json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [OK] 规则已添加: {rule_text}")
        return 0

    elif action == "remove":
        if not rule_text.strip():
            print("Usage: python novel.py learn remove <number>")
            return 1
        try:
            idx = int(rule_text) - 1
            if 0 <= idx < len(rules):
                removed = rules.pop(idx)
                rules_file.write_text(_json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"  [OK] 规则已移除: {removed.get('rule', str(removed))}")
                return 0
            else:
                print(f"  无效编号: {idx+1} (共 {len(rules)} 条)")
                return 1
        except ValueError:
            print(f"  请输入有效编号。当前共 {len(rules)} 条规则。")
            return 1

    return 0


def cmd_board(args):
    """Print a readonly status board for the project."""
    print("=" * 60)
    print("  Novel Pipeline — 项目看板")
    print("=" * 60)
    print()

    # Version
    v = get_version()
    print(f"  引擎版本: {v}")

    # Story status
    if _story_exists():
        from scripts.story import story_health
        health = story_health.check_health(PROJECT_ROOT)
        status = health["status"]
        print(f"  故事链: {status}")
        print(f"    合同: {health.get('contract_count', 0)}  提交: {health.get('commit_count', 0)}  事件: {health.get('event_count', 0)}")
        issues = health.get("issues", [])
        if issues:
            for iss in issues[:3]:
                print(f"    ⚠ {iss}")
    else:
        print(f"  故事链: 未初始化 (python novel.py story init)")

    # Config
    cfg = PROJECT_ROOT / "config.json"
    if cfg.exists():
        import json as _json
        try:
            cfg_data = load_project_config()
            slug = cfg_data.get("default_novel_slug", "?")
            genre = cfg_data.get("default_genre", "?")
            style = cfg_data.get("default_style", "?")
            print(f"  当前项目: {slug}")
            print(f"  类型/风格: {genre} / {style}")

            # Word count config
            wc = cfg_data.get("word_count", {}).get("normal", {})
            if wc:
                print(f"  字数范围: {wc.get('min', '?')}-{wc.get('max', '?')} (最佳≥{wc.get('best_min', '?')})")
        except Exception:
            print(f"  配置: 读取失败")
    else:
        print(f"  配置: 未找到 config.json")

    # Chapters in novels dir
    if cfg.exists():
        import json as _json
        try:
            cfg_data = load_project_config()
            slug = cfg_data.get("default_novel_slug", "demo_novel")
            novels_root = resolve_path(PROJECT_ROOT, cfg_data.get("novels_root", "./novels"))
            ch_dir = Path(novels_root) / slug / "第01卷"
            if ch_dir.exists():
                chapters = sorted(ch_dir.glob("第*章*.txt"))
                print(f"  已完成章节: {len(chapters)}")
                if chapters:
                    latest = chapters[-1]
                    cn = sum(1 for c in latest.read_text(encoding="utf-8")
                             if '\u4e00' <= c <= '\u9fff' or '\u3400' <= c <= '\u4dbf')
                    print(f"    最新: {latest.name} ({cn} 汉字)")
            else:
                print(f"  章节目录: 未找到 {ch_dir}")
        except Exception:
            print(f"  章节: 读取失败")

    # DB status
    try:
        # P0-2: Use active slot novel.db instead of config.json db_path
        dbp = _get_active_db_path()
        if dbp.exists():
            import sqlite3
            conn = sqlite3.connect(str(dbp))
            cur = conn.execute("SELECT COUNT(*) FROM chapters")
            ch_count = cur.fetchone()[0]
            cur = conn.execute("SELECT COUNT(*) FROM characters")
            char_count = cur.fetchone()[0]
            conn.close()
            print(f"  数据库: {dbp.name} | 章节: {ch_count} | 角色: {char_count}")
        else:
            print(f"  数据库: 未找到 ({dbp})")
    except Exception:
        print(f"  数据库: 无法读取")

    print()
    print("=" * 60)
    return 0


def cmd_genre(args):
    """Genre pack management."""
    action = getattr(args, "genre_action", None)
    if action == "list":
        from scripts.genre.genre_loader import list_genres
        genres = list_genres()
        print(f"Available genres ({len(genres)}):")
        for g in genres:
            print(f"  {g}")
    elif action == "show":
        from scripts.genre.genre_loader import load_genre_pack
        gid = getattr(args, "genre_id", "generic")
        pack = load_genre_pack(gid)
        print(f"Genre: {pack.get('name', gid)} ({pack.get('genre_id', gid)})")
        print(f"  {pack.get('description', '')[:100]}")
        for key in ["core_promises", "forbidden_patterns", "agent_focus"]:
            items = pack.get(key, [])
            if items:
                print(f"  {key}:")
                for item in items[:5]:
                    print(f"    - {item}")
    else:
        print("Usage: python novel.py genre {list|show <id>}")
    return 0


def cmd_style(args):
    """Style pack management."""
    action = getattr(args, "style_action", None)
    if action == "list":
        from scripts.genre.style_loader import list_styles
        styles = list_styles()
        print(f"Available styles ({len(styles)}):")
        for s in styles:
            print(f"  {s}")
    elif action == "show":
        from scripts.genre.style_loader import load_style_pack
        sid = getattr(args, "style_id", "generic")
        pack = load_style_pack(sid)
        print(f"Style: {pack.get('name', sid)} ({pack.get('style_id', sid)})")
        print(f"  {pack.get('description', '')[:100]}")
        for key in ["narrative_features", "forbidden_patterns", "agent_focus"]:
            items = pack.get(key, [])
            if items:
                print(f"  {key}:")
                for item in items[:5]:
                    print(f"    - {item}")
    else:
        print("Usage: python novel.py style {list|show <id>}")
    return 0
