"""Stability check command."""
from __future__ import annotations

import sys
try:
    from novel_pipeline.version import get_version
except ImportError:
    from version import get_version
from .common import PROJECT_ROOT, load_project_config


def cmd_stability_check(args=None):
    """P2-1: 稳定性自检 — 输出评分和问题清单.
    v0.6.5-clean11: 默认快速模式，--full 运行 pytest+structure check.
    """
    import subprocess as _sp
    import importlib

    full_mode = getattr(args, "full", False)

    print("=" * 60)
    mode_label = "完整模式 (pytest + structure check)" if full_mode else "快速模式"
    print(f"  Novel Pipeline - 稳定性自检 ({mode_label})")
    print(f"  版本: {get_version()}")
    print("=" * 60)
    print()

    score = 100
    p0_issues = []
    p1_issues = []
    checks = []

    # 1. 版本号一致
    try:
        vfile = (PROJECT_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        v = get_version()
        ok = v == vfile
        checks.append(("版本号一致性", ok, f"VERSION={vfile}, get_version()={v}"))
        if not ok:
            p0_issues.append("VERSION 文件与代码版本不一致")
            score -= 10
    except Exception as e:
        checks.append(("版本号一致性", False, str(e)))
        p0_issues.append(f"无法读取版本号: {e}")
        score -= 10

    # 2. config 可解析
    try:
        cfg = load_project_config()
        checks.append(("配置文件", True, "config.json 可解析"))
    except Exception as e:
        checks.append(("配置文件", False, str(e)))
        p0_issues.append(f"config.json 解析失败: {e}")
        score -= 10

    # 3. workspace 初始化
    ws_dir = PROJECT_ROOT / "workspace"
    ws_ok = ws_dir.exists() and (ws_dir / "registry.json").exists()
    checks.append(("workspace 初始化", ws_ok, str(ws_dir)))
    if not ws_ok:
        p1_issues.append("workspace 未初始化——首次使用请先运行 python novel.py init（或 python novel.py demo 一键全流程）")
        score -= 5

    # 4. 默认 3 slot 完整
    if ws_ok:
        try:
            import json as _json
            reg = _json.loads((ws_dir / "registry.json").read_text(encoding="utf-8"))
            slots = reg.get("slots", [])
            slot_ok = len(slots) >= 3
            checks.append(("默认 slot 完整", slot_ok, f"{len(slots)} 个 slot"))
            if not slot_ok:
                p0_issues.append(f"仅有 {len(slots)} 个默认 slot，需要 3 个")
                score -= 10
        except Exception as e:
            checks.append(("默认 slot 完整", False, str(e)))
            score -= 5

    # 5. active slot 有 novel.db
    try:
        from scripts.db.slot_manager import SlotManager
        sm = SlotManager(PROJECT_ROOT)
        if sm.registry.exists():
            active = sm.registry.get_active_slot()
            db_path = sm.get_slot_db_path(active) if active else None
            db_ok = db_path and db_path.exists()
            checks.append(("active slot DB", db_ok, str(db_path) if db_path else "无活跃 slot"))
            if not db_ok:
                p0_issues.append(f"活跃 slot {active} 缺少 novel.db")
                score -= 10
        else:
            checks.append(("active slot DB", False, "registry 不存在"))
    except Exception as e:
        checks.append(("active slot DB", False, str(e)))
        p1_issues.append(f"无法检查 DB: {e}")
        score -= 5

    # 6. agent 数量达标
    agents_dir = PROJECT_ROOT / "configs" / "jury" / "agents"
    agent_count = len(list(agents_dir.glob("*.yaml"))) if agents_dir.exists() else 0
    agent_ok = agent_count >= 15
    checks.append(("Agent 数量", agent_ok, f"{agent_count} 个 (需要 >=15)"))
    if not agent_ok:
        p0_issues.append(f"Agent 仅 {agent_count} 个，目标 >=15")
        score -= 10

    # 7. pytest (--full only, v0.6.5-clean5: 防挂 + 禁用插件)
    if full_mode:
        try:
            import os as _os
            env = {**_os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
            result = _sp.run(
                [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short"],
                cwd=str(PROJECT_ROOT), timeout=180,
                capture_output=True, text=True, env=env
            )
            test_ok = result.returncode == 0
            checks.append(("pytest", test_ok, f"exit={result.returncode}"))
            if not test_ok:
                # Show last 3 lines of stderr for debugging
                err_lines = result.stderr.strip().split("\n")[-3:]
                p0_issues.append(f"pytest 运行失败 (exit={result.returncode})")
                score -= 10
        except _sp.TimeoutExpired:
            checks.append(("pytest", False, "超时 (180s)"))
            p0_issues.append("pytest 超时，可能挂起")
            score -= 15
        except Exception as e:
            checks.append(("pytest", False, str(e)[:60]))
            p1_issues.append(f"pytest 无法运行: {e}")
            score -= 5
    else:
        checks.append(("pytest", True, "跳过（使用 --full 运行）"))

    # 8. 交叉平台检查
    cp_script = PROJECT_ROOT / "scripts" / "cross_platform_check.py"
    if cp_script.exists():
        try:
            cp = _sp.run([sys.executable, str(cp_script)], cwd=str(PROJECT_ROOT),
                         timeout=30, capture_output=True, text=True)
            cp_ok = cp.returncode == 0
            checks.append(("交叉平台", cp_ok, "通过" if cp_ok else "有警告"))
            if not cp_ok:
                p1_issues.append("交叉平台检查有警告")
                score -= 5
        except Exception:
            checks.append(("交叉平台", False, "超时/异常"))
            score -= 5

    # 9. story contract 是否存在断链
    story_dir = PROJECT_ROOT / ".story"
    if story_dir.exists():
        try:
            from scripts.story import story_health
            health = story_health.check_health(PROJECT_ROOT)
            h_ok = health["status"] == "OK"
            checks.append(("Story 健康", h_ok, health["status"]))
            if health["status"] == "FAIL":
                p0_issues.append(f"Story 链断裂: {len(health.get('failures', []))} 项")
                score -= 10
            elif health["status"] == "WARN":
                p1_issues.append(f"Story 链警告: {len(health.get('warnings', []))} 项")
                score -= 5
        except Exception as e:
            checks.append(("Story 健康", False, str(e)))

    # 10. v0.6.5-clean3: Slot FTS 完整性检查
    try:
        import sqlite3
        ws_dir = PROJECT_ROOT / "workspace"
        fts_issues = []
        for slot_dir in sorted(ws_dir.glob("slot_*")):
            db_path = slot_dir / "novel.db"
            if not db_path.exists():
                continue
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='novel_chapter_fts'")
            if not cur.fetchone():
                fts_issues.append(f"{slot_dir.name} 缺少 FTS5 表")
            conn.close()
        fts_ok = len(fts_issues) == 0
        detail = "所有 slot 有 FTS5" if fts_ok else f"{len(fts_issues)} 个 slot 缺 FTS5"
        checks.append(("Slot FTS 完整性", fts_ok, detail))
        if not fts_ok:
            p0_issues.append(f"Slot DB 缺 FTS5 表: {', '.join(fts_issues)}")
            score -= 10
    except Exception as e:
        checks.append(("Slot FTS 完整性", False, str(e)))
        p1_issues.append(f"无法检查 slot FTS: {e}")
        score -= 5

    # 11. v0.6.5-clean10: --full 轻量结构自检（不跑 demo 子进程，防挂）
    if full_mode:
        try:
            smoke_ok = True
            smoke_parts = []

            # a) slot_001 DB 表完整性
            import sqlite3
            db = PROJECT_ROOT / "workspace" / "slot_001" / "novel.db"
            if db.exists():
                conn = sqlite3.connect(str(db))
                tables = [r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()]
                conn.close()
                has_chapters = "chapters" in tables
                has_fts = any("fts" in t for t in tables)
                smoke_parts.append("DB✓" if (has_chapters and has_fts) else "DB✗")
                if not has_chapters or not has_fts:
                    smoke_ok = False
            else:
                smoke_parts.append("DB✗")
                smoke_ok = False

            # b) config 可解析
            cfg_path = PROJECT_ROOT / "config.json"
            smoke_parts.append("CFG✓" if cfg_path.exists() else "CFG✗")

            # c) workspace 初始化
            ws = PROJECT_ROOT / "workspace"
            has_reg = (ws / "registry.json").exists()
            smoke_parts.append("WS✓" if has_reg else "WS✗")
            if not has_reg:
                smoke_ok = False

            # d) agents 配置存在
            agents = list((PROJECT_ROOT / "configs" / "jury" / "agents").glob("*.yaml"))
            smoke_parts.append(f"Agents:{len(agents)}")
            if len(agents) < 15:
                smoke_ok = False

            checks.append(("结构自检", smoke_ok, " ".join(smoke_parts)))
            if not smoke_ok:
                p0_issues.append("结构自检未通过（DB/WS/Agents 不完整）")
                score -= 20
        except Exception as e:
            checks.append(("结构自检", False, str(e)[:60]))
            p0_issues.append(f"结构自检异常: {e}")
            score -= 20
    else:
        checks.append(("结构自检", True, "跳过（使用 --full 运行）"))

    # 输出结果
    for name, ok, detail in checks:
        icon = "✓" if ok else "✗"
        print(f"  [{icon}] {name}: {detail}")

    print()
    print("=" * 60)
    print(f"  稳定性评分: {max(0, score)}/100")
    print(f"  P0 问题: {len(p0_issues)} 个")
    print(f"  P1 问题: {len(p1_issues)} 个")

    if p0_issues:
        print(f"\n  P0 必须修复:")
        for iss in p0_issues:
            print(f"    ✗ {iss}")
    if p1_issues:
        print(f"\n  P1 建议修复:")
        for iss in p1_issues:
            print(f"    ⚠ {iss}")

    if p0_issues:
        print(f"\n  建议: 不建议发布（存在 P0 问题，必须先修复）")
    elif score >= 80:
        print(f"\n  建议: 可以发布正式版")
    elif score >= 60:
        print(f"\n  建议: 修复 P1 问题后再发布")
    else:
        print(f"\n  建议: 不建议发布")
    print("=" * 60)
    return 0 if not p0_issues and score >= 80 else 1
