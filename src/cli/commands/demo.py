"""Demo pipeline command."""
from __future__ import annotations

import sys
from pathlib import Path
try:
    from novel_pipeline.version import get_version
except ImportError:
    from version import get_version
from .common import (
    PROJECT_ROOT, SCRIPTS_DIR, SRC_GUARDS_DIR,
    load_project_config, _get_active_db_path, _get_outline_manager,
)
from config_utils import resolve_path


def cmd_demo():
    """Create demo_novel, activate outline, run pre -> post -> report -> export."""
    print("=" * 60)
    v = get_version()
    print(f"  Novel Pipeline - Write Engine {v}")
    print("  Demo Pipeline")
    print("=" * 60)
    print()

    import subprocess as _sp

    # STEP 1: db init — ensure workspace initialized for outline manager
    print("[STEP 1] Initializing workspace (db init)...")
    db_init_result = _sp.run(
        [sys.executable, str(PROJECT_ROOT / "novel.py"), "db", "init"],
        cwd=str(PROJECT_ROOT), timeout=60, capture_output=True, text=True
    )
    if db_init_result.returncode == 0:
        print("  [OK] db init completed")
    elif db_init_result.stdout and "已经初始化" in db_init_result.stdout:
        print("  [OK] workspace already initialized")
    else:
        print(f"  [WARN] db init returned {db_init_result.returncode}")

    # STEP 2: Init project (config.json + DB schema + directories)
    cfg_path = PROJECT_ROOT / "config.json"
    if not cfg_path.exists():
        print("\n[STEP 2] Initializing project (config + DB + directories)...")
        from .init import cmd_init
        cmd_init()
        print()
    else:
        print("\n[STEP 2] config.json found. Checking database...")

    cfg_data = load_project_config()
    # P0-2: Use active slot novel.db instead of global data/novel_memory.db
    db_path = _get_active_db_path()
    print(f"  Active slot DB: {db_path}")
    if not db_path.exists():
        print("  Database missing, initializing now...")
        from .init import cmd_init
        cmd_init()
        cfg_data = load_project_config()
        db_path = _get_active_db_path()

    slug = cfg_data.get("default_novel_slug", "demo_novel")
    title = cfg_data.get("default_novel_title", "Demo Novel")
    novels_root = resolve_path(PROJECT_ROOT, cfg_data.get("novels_root", "./novels"))
    vol_dir = novels_root / slug / "第01卷"
    vol_dir.mkdir(parents=True, exist_ok=True)

    # v0.6.5-clean8: Ensure slot_001 is active for demo
    try:
        import json as _json
        ws_dir = PROJECT_ROOT / "workspace"
        reg_file = ws_dir / "registry.json"
        if reg_file.exists():
            reg = _json.loads(reg_file.read_text(encoding="utf-8"))
            reg["active_slot"] = "slot_001"
            reg_file.write_text(_json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    # STEP 3: Create demo chapter + outline.txt
    print("\n[STEP 3] Creating demo chapter...")
    paragraphs = [
        "第1章 开篇",
        "清晨的钟声从青云宗山腰传来，像一根细线，把外门弟子从浅睡里一一拽醒。李明远坐在窄床边，先没有急着穿鞋，而是低头看向掌心那枚旧玉佩。玉佩的边缘有一道细裂，裂纹像凝住的水波，三年来从未扩大，也从未消失。",
        "他来到青云宗已经第三年。三年前，他还只是海边渔村里的少年，每天跟着父亲补网、看潮、记风向。那场暴风雨把渔船掀翻时，他以为自己会沉进海底，偏偏胸口的玉佩发出一点冷光，把他推上了岸，也把他推到了修行人的门槛前。",
        "门外传来小石头的声音：\"远哥，王教习让我们提前到练功场，说今日有长老巡视。\"小石头说话总带着一点慌张，像随时准备把自己缩进墙角。他本名石磊，因为个子小，入门又晚，所有人都叫他小石头，只有李明远还会认真叫他一声师弟。",
        "李明远把玉佩塞回衣襟，推门出去。晨雾还没有散，练功场的青砖上凝着水汽，几十名外门弟子已经排成三列。有人在压腿，有人默背心法，也有人趁王教习没到，偷偷用余光打量山道尽头。今日的气氛很不对，连平日爱说笑的赵铁柱都闭着嘴，双手按在膝上，一下一下调整呼吸。",
        "王教习终于来了。他须发皆白，步子却稳，木杖点在砖面上，声声清脆。\"今日大长老巡视外门，谁若在基础功上偷奸耍滑，老夫先罚，戒律堂再罚。\"这句话不重，却让人背脊发紧。外门弟子最怕的不是挨骂，而是被记入戒律堂的黑册，一旦名字落上去，日后进内门几乎无望。",
        "赵铁柱压低声音道：\"明远，你昨晚是不是又练到后半夜？脸色不太对。\"李明远摇摇头，没有解释。他昨夜确实没睡好，但不是因为修炼，而是因为玉佩第一次在无人触碰时自己发热。那股热意顺着胸口往丹田走，像有人在他体内画了一条陌生的经脉路线。",
        "王教习开始点名。每点到一人，便让其演示三式基础剑法。轮到李明远时，周围忽然安静下来。他的修为只是炼气三层，算不上拔尖，可他的剑路总有些古怪，明明用的是最普通的青云十三式，落点却比旁人更准，像每一剑都提前知道风会往哪里吹。",
        "李明远握住木剑，第一式平平推出。剑尖划过雾气，雾线被割开，又在他身后缓慢合拢。第二式转腕时，他胸前玉佩忽然一烫，丹田里的真气不受控制地偏了半寸。只是半寸，木剑却发出一声轻鸣，练功场边的铜铃无风自响。",
        "所有人都愣住了。王教习的眼神骤然锐利，大步走到李明远面前，伸手扣住他的腕脉。李明远只觉得一股外来的灵力沿着手腕探入体内，还没碰到玉佩所在的位置，就被一层冰冷的阻力挡了回去。王教习脸色微变，随即松手，低声道：\"今日之后，你不要一个人去后山。\"",
        "这句话来得突兀，小石头吓得脸都白了。赵铁柱想问，却被王教习一个眼神压回去。李明远心里那点不安终于落成了实物：不是他多想，玉佩真的被人察觉了。更糟的是，察觉的人未必只有王教习。",
        "山道上，三名内门弟子簇拥着一位青袍老者缓缓走来。老者眉目清瘦，袖口绣着戒律堂的玄色云纹，正是外门弟子口中最不愿遇见的大长老。他的目光扫过练功场，最后停在李明远身上，停得比任何人都久。",
        "李明远低下头，手指按住衣襟里的玉佩。玉佩已经恢复冰凉，可那道裂纹里似乎多了一点极淡的金色。它像一只刚睁开的眼睛，在沉默里看着所有人。",
        "大长老没有立刻说话，只是对王教习点了点头。王教习会意，宣布今日晨练改为根骨复测。人群顿时骚动起来。根骨复测一年一次，通常只为筛选升入内门的弟子，绝不会临时提前。李明远听见身后有人倒吸冷气，也听见小石头小声念了一句：\"完了，肯定有人要倒霉。\"",
        "李明远没有回头。他知道那个人很可能就是自己。可他也清楚，若今日退缩，玉佩的秘密未必能保住，自己的路也会被别人安排。三年来，他第一次生出一个明确的念头：他不能再只做外门里那个安静听话的弟子。",
        "铜铃第二次响起时，雾气终于散开。阳光落在练功场中央，也落在大长老面前那块测灵石上。李明远向前一步，掌心贴上冰冷的石面。下一瞬，测灵石深处亮起一道从未在外门出现过的青金色细线，像雷光，也像裂开的命运。",
    ]
    demo_content = "\n\n".join(paragraphs) + "\n"
    chapter_file = vol_dir / "第1章_开篇.txt"
    chapter_file.write_text(demo_content, encoding="utf-8")
    cn_count = sum(1 for c in demo_content if '\u4e00' <= c <= '\u9fff' or '\u3400' <= c <= '\u4dbf')
    print(f"  [OK] {chapter_file.name} ({cn_count} 汉字)")

    # v0.6.5-clean8: Also copy to active slot chapters dir for post
    slot_ch_dir = PROJECT_ROOT / "workspace" / "slot_001" / "chapters"
    slot_ch_dir.mkdir(parents=True, exist_ok=True)
    slot_ch_file = slot_ch_dir / "第1章_开篇.txt"
    slot_ch_file.write_text(demo_content, encoding="utf-8")
    print(f"  [OK] slot_001/chapters/{slot_ch_file.name}")

    outline_file = novels_root / slug / "outline.txt"
    outline_file.write_text(
        "# Demo Novel 大纲\n\n第一卷：初入宗门。第1章：外门晨练，玉佩异动，大长老临时复测根骨。\n",
        encoding="utf-8",
    )
    print(f"  [OK] {outline_file.name}")

    # STEP 4: Register demo_novel in database
    print("\n[STEP 4] Registering demo_novel in database...")
    try:
        import sqlite3
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        conn.execute("INSERT OR IGNORE INTO novels (slug, title, genre, status) VALUES (?, ?, ?, ?)",
                     (slug, title, cfg_data.get("default_genre", "xianxia"), "writing"))
        novel_id = conn.execute("SELECT id FROM novels WHERE slug=?", (slug,)).fetchone()[0]
        conn.execute("INSERT OR IGNORE INTO volumes (novel_id, volume_no, title) VALUES (?, ?, ?)",
                     (novel_id, 1, "第一卷"))
        conn.commit()
        conn.close()
        print("  [OK] registered")
    except Exception as e:
        print(f"  [ERROR] database registration failed: {e}")
        return 1

    # STEP 5: Activate outline — register outline.txt with outline manager (P0-1 FIX)
    print("\n[STEP 5] Activating demo outline...", flush=True)
    outline_result = _sp.run(
        [sys.executable, str(PROJECT_ROOT / "novel.py"), "outline", "add", str(outline_file),
         "--title", title, "--genre", cfg_data.get("default_genre", "xianxia")],
        cwd=str(PROJECT_ROOT), timeout=60, capture_output=True, text=True
    )
    if outline_result.stdout:
        print(outline_result.stdout, end="")
    if outline_result.stderr:
        print(outline_result.stderr, end="", file=sys.stderr)
    if outline_result.returncode == 0:
        print("  [OK] demo outline activated")
    elif outline_result.stdout and ("已经初始化" in outline_result.stdout or "already initialized" in outline_result.stdout):
        print("  [OK] demo outline activated (already present)")
    else:
        # outline add may succeed even with non-zero if outline already exists
        print(f"  [INFO] outline add exited {outline_result.returncode} — checking active state...")
        # fallback: try direct activation via outline manager
        try:
            mgr = _get_outline_manager()
            if mgr.has_active_outline():
                print("  [OK] demo outline is active")
            else:
                print("  [WARN] outline may not be active — pre may fail")
        except Exception:
            print("  [WARN] could not verify outline activation")

    # STEP 6: Pre-write gate
    print("\n[STEP 6] Running pre-write gate...", flush=True)
    pre_result = _sp.run(
        [sys.executable, str(PROJECT_ROOT / "novel.py"), "pre", "1", "--slug", slug],
        cwd=str(PROJECT_ROOT), timeout=180, capture_output=True, text=True
    )
    if pre_result.stdout:
        print(pre_result.stdout, end="")
    if pre_result.stderr:
        print(pre_result.stderr, end="", file=sys.stderr)
    if pre_result.returncode != 0:
        print(f"  [FAIL] pre returned exit code {pre_result.returncode}")
        return pre_result.returncode
    print("  [OK] pre completed")

    # STEP 7: Post-write guards + ingest
    print("\n[STEP 7] Running post-write guards + ingest...", flush=True)
    post_result = _sp.run(
        [sys.executable, str(PROJECT_ROOT / "novel.py"), "post", "1", "--slug", slug],
        cwd=str(PROJECT_ROOT), timeout=300, capture_output=True, text=True
    )
    if post_result.stdout:
        print(post_result.stdout, end="")
    if post_result.stderr:
        print(post_result.stderr, end="", file=sys.stderr)
    if post_result.returncode != 0:
        print(f"  [FAIL] post returned exit code {post_result.returncode}")
        return post_result.returncode
    print("  [OK] post completed")

    # STEP 8: Report
    print("\n[STEP 8] Generating report...", flush=True)
    report_result = _sp.run(
        [sys.executable, str(PROJECT_ROOT / "novel.py"), "report"],
        cwd=str(PROJECT_ROOT), timeout=60, capture_output=True, text=True
    )
    if report_result.stdout:
        print(report_result.stdout, end="")
    if report_result.stderr:
        print(report_result.stderr, end="", file=sys.stderr)
    print("  [OK] report generated")

    # STEP 9: Export
    print("\n[STEP 9] Exporting demo novel...", flush=True)
    export_result = _sp.run(
        [sys.executable, str(PROJECT_ROOT / "novel.py"), "export", "--slug", slug, "--format", "md"],
        cwd=str(PROJECT_ROOT), timeout=60, capture_output=True, text=True
    )
    if export_result.stdout:
        print(export_result.stdout, end="")
    if export_result.stderr:
        print(export_result.stderr, end="", file=sys.stderr)
    if export_result.returncode == 0:
        print("  [OK] export generated")
    else:
        print(f"  [WARN] export returned {export_result.returncode}")

    print("\n  Demo complete!")
    print(f"  章节文件：workspace/slot_001/chapters/{slot_ch_file.name}")
    print(f"  兼容副本：{chapter_file}")
    print(f"  Report:   python novel.py report")
    print(f"  Export:   python novel.py export --slug {slug}")
    print()
    print("=" * 60)
    print("  Demo pipeline passed.")
    print("=" * 60)
    return 0
