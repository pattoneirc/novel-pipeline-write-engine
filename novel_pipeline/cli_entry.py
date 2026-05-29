"""CLI entry point for pip-installed novel command."""
from __future__ import annotations

import sys
import argparse
from pathlib import Path

try:
    from novel_pipeline.version import get_version
except ImportError:
    from version import get_version

_src_cli = Path(__file__).resolve().parent.parent / "src" / "cli"
if str(_src_cli) not in sys.path:
    sys.path.insert(0, str(_src_cli))

from commands.common import PROJECT_ROOT, load_project_config, cfg_path
from commands.status import cmd_status, cmd_doctor
from commands.demo import cmd_demo
from commands.report import cmd_report, cmd_guards, cmd_check, cmd_wc
from commands.init import cmd_init
from commands.writing import cmd_pre, cmd_post, cmd_review, cmd_export
from commands.agents import cmd_agents, cmd_rag
from commands.story import cmd_story, cmd_query, cmd_learn, cmd_board, cmd_genre, cmd_style
from commands.db import cmd_db
from commands.outline import cmd_outline
from commands.help_cmd import cmd_scc_help
from commands.menu import cmd_menu, cmd_chapters, cmd_menu_show, cmd_menu_text, cmd_setup
from commands.stability import cmd_stability_check


def main():
    parser = argparse.ArgumentParser(
        description=f"Novel Pipeline - Write Engine {get_version()} CLI",
    )
    parser.add_argument('--version', action='version',
                        version=f'Novel Pipeline - Write Engine {get_version()}')
    sub = parser.add_subparsers(dest="command", help="Command to run")

    p_status = sub.add_parser("status", help="Run environment diagnostics")
    p_status.add_argument("--detail", action="store_true", help="Show detailed output")
    p_doctor = sub.add_parser("doctor", help="Run detailed environment diagnostics (alias for status --detail)")
    p_doctor.add_argument("--detail", action="store_true", default=True, help="Show detailed output (default on)")
    sub.add_parser("demo", help="Run demo pipeline")
    sub.add_parser("init", help="Initialize project directories and database")
    p_pre = sub.add_parser("pre", help="Generate pre-write task card")
    p_pre.add_argument("chapter_no", nargs="?", help="Chapter number")
    p_pre.add_argument("--slug", help="Novel slug")
    p_pre.add_argument("--volume", help="Volume number")
    p_post = sub.add_parser("post", help="Post-write: run guards and ingest")
    p_post.add_argument("chapter_no", nargs="?", help="Chapter number")
    p_post.add_argument("--slug", help="Novel slug")
    p_post.add_argument("--volume", help="Volume number")
    p_post.add_argument("--file", help="Direct chapter file path")
    p_post.add_argument("--story", action="store_true", help="Auto-generate story commit after post")
    p_review = sub.add_parser("review", help="Run guard review on a chapter")
    p_review.add_argument("chapter_no", nargs="?", help="Chapter number")
    p_review.add_argument("--slug", help="Novel slug")
    p_review.add_argument("--volume", help="Volume number")
    sub.add_parser("report", help="Show recent guard reports")
    sub.add_parser("guards", help="List registered guards")
    p_check = sub.add_parser("check", help="Run guard checks on a chapter file")
    p_check.add_argument("file_path", help="Path to chapter TXT file")
    p_agents = sub.add_parser("agents", help="Multi-agent review board")
    p_agents_sub = p_agents.add_subparsers(dest="agents_action")
    p_agents_review = p_agents_sub.add_parser("review", help="Run agent review on a chapter")
    p_agents_review.add_argument("chapter_no", nargs="?", help="Chapter number")
    p_agents_review.add_argument("--mode", default="light", choices=["light", "full"])
    p_agents_review.add_argument("--slug", help="Novel slug")
    p_agents_review.add_argument("--genre", help="Genre pack ID (e.g. xianxia, mystery)")
    p_agents_review.add_argument("--style", default=None, help="Style pack ID (e.g. webnovel, black_humor)")
    p_agents_list = p_agents_sub.add_parser("list", help="List all available agents")
    p_agents_list.add_argument("--mode", default=None, help="Filter by mode (light/full/strict/webnovel)")
    p_rag = sub.add_parser("rag", help="Vector RAG (optional)")
    p_rag_sub = p_rag.add_subparsers(dest="rag_action")
    p_rag_sub.add_parser("status", help="Check RAG status")
    p_rag_query = p_rag_sub.add_parser("query", help="Query the novel database")
    p_rag_query.add_argument("question", nargs="*", help="Question to ask")
    p_export = sub.add_parser("export", help="Export novel to single file")
    p_export.add_argument("--slug", help="Novel slug to export")
    p_export.add_argument("--format", default="md", choices=["txt", "md"])
    p_db = sub.add_parser("db", help="Multi-DB workspace management")
    p_db_sub = p_db.add_subparsers(dest="db_action")
    p_db_sub.add_parser("list", help="列出所有 DB slot")
    p_db_sub.add_parser("current", help="显示当前活跃 DB slot")
    p_db_sub.add_parser("info", help="显示当前 slot 详细信息")
    p_db_new = p_db_sub.add_parser("new", help="创建新 DB slot")
    p_db_new.add_argument("--name", required=True, help="Slot 名称")
    p_db_new.add_argument("--description", default="", help="Slot 描述")
    p_db_use = p_db_sub.add_parser("use", help="切换到指定 DB slot")
    p_db_use.add_argument("slot_id", help="Slot ID (如 slot_001)")
    p_db_delete = p_db_sub.add_parser("delete", help="安全删除 DB slot (移至回收站)")
    p_db_delete.add_argument("slot_id", help="Slot ID")
    p_db_delete.add_argument("--yes", action="store_true", help="确认删除")
    p_db_sub.add_parser("trash", help="查看回收站中的 slot")
    p_db_restore = p_db_sub.add_parser("restore", help="从备份或回收站恢复 DB slot")
    p_db_restore.add_argument("slot_id", help="Slot ID 或回收站项目名")
    p_db_restore.add_argument("--backup-id", help="备份 ID (不指定则使用最新备份)")
    p_db_restore.add_argument("--from-trash", action="store_true", help="从回收站恢复 (默认从备份恢复)")
    p_db_purge = p_db_sub.add_parser("purge", help="永久删除回收站中的 slot")
    p_db_purge.add_argument("trash_name", nargs="?", default=None, help="回收站项目名 (不指定则清空全部)")
    p_db_backup = p_db_sub.add_parser("backup", help="备份当前 DB slot")
    p_db_backup.add_argument("--slot", help="Slot ID (默认当前活跃)")
    p_db_init = p_db_sub.add_parser("init", help="初始化 workspace 目录结构")
    p_db_init.add_argument("--force", action="store_true", help="强制重新初始化")
    p_outline = sub.add_parser("outline", help="大纲管理（添加/列出/切换/对比/回滚）")
    p_outline_sub = p_outline.add_subparsers(dest="outline_action")
    p_outline_add = p_outline_sub.add_parser("add", help="添加大纲（自动相似度检测与智能处理）")
    p_outline_add.add_argument("outline_file", nargs="?", default="", help="大纲文件路径 (.txt)，留空自动扫描 大纲/")
    p_outline_add.add_argument("--title", default="", help="大纲标题")
    p_outline_add.add_argument("--genre", default="", help="题材")
    p_outline_add.add_argument("--style", default="", help="风格")
    p_outline_add.add_argument("--replace-current", action="store_true", help="高相似度时替换当前激活大纲")
    p_outline_add.add_argument("--keep-inactive", action="store_true", help="高相似度时保存但不激活")
    p_outline_add.add_argument("--dry-run", action="store_true", help="仅显示相似度分析结果，不执行实际操作")
    p_outline_import = p_outline_sub.add_parser("import", help="导入大纲（指定标题）")
    p_outline_import.add_argument("outline_file", help="大纲文件路径 (.txt)")
    p_outline_import.add_argument("--title", required=True, help="大纲标题")
    p_outline_import.add_argument("--genre", default="", help="题材")
    p_outline_import.add_argument("--style", default="", help="风格")
    p_outline_sub.add_parser("list", help="列出所有大纲")
    p_outline_sub.add_parser("current", help="显示当前激活大纲")
    p_outline_switch = p_outline_sub.add_parser("switch", help="切换激活大纲")
    p_outline_switch.add_argument("outline_id", help="大纲 ID")
    p_outline_diff = p_outline_sub.add_parser("diff", help="对比两个大纲")
    p_outline_diff.add_argument("id1", help="大纲1 ID")
    p_outline_diff.add_argument("id2", help="大纲2 ID")
    p_outline_rollback = p_outline_sub.add_parser("rollback", help="回滚大纲到上一版本")
    p_outline_rollback.add_argument("outline_id", help="大纲 ID")
    p_outline_compare = p_outline_sub.add_parser("compare", help="对比文件与当前激活大纲")
    p_outline_compare.add_argument("compare_file", help="文件路径 (.txt)")
    p_outline_delete = p_outline_sub.add_parser("delete", help="删除指定大纲")
    p_outline_delete.add_argument("delete_id", help="大纲 ID")
    p_outline_sub.add_parser("undo", help="撤销最近一次大纲添加")
    p_wc = sub.add_parser("wc", help="Count Chinese characters in a chapter file")
    p_wc.add_argument("file_path", nargs="?", help="Path to chapter TXT file")
    p_story = sub.add_parser("story", help="Story contract system")
    p_story_sub = p_story.add_subparsers(dest="story_action")
    p_story_sub.add_parser("init", help="Initialize .story/ directory")
    p_story_sub_contract = p_story_sub.add_parser("contract", help="Generate chapter contract")
    p_story_sub_contract.add_argument("chapter_no", nargs="?", default="1")
    p_story_sub_commit = p_story_sub.add_parser("commit", help="Generate chapter commit")
    p_story_sub_commit.add_argument("chapter_no", nargs="?", default="1")
    p_story_sub.add_parser("health", help="Check story chain health")
    p_query = sub.add_parser("query", help="Query project memory")
    p_query.add_argument("question", nargs="*", help="Natural language question")
    p_learn = sub.add_parser("learn", help="Writing rules learned")
    p_learn.add_argument("action", nargs="?", default="list")
    p_learn.add_argument("rule", nargs="*", help="Rule text to add")
    sub.add_parser("board", help="Readonly status board")
    p_genre = sub.add_parser("genre", help="Genre pack management")
    p_genre_sub = p_genre.add_subparsers(dest="genre_action")
    p_genre_sub.add_parser("list", help="List available genres")
    p_genre_show = p_genre_sub.add_parser("show", help="Show genre pack details")
    p_genre_show.add_argument("genre_id", help="Genre ID (e.g. xianxia)")
    p_style = sub.add_parser("style", help="Style pack management")
    p_style_sub = p_style.add_subparsers(dest="style_action")
    p_style_sub.add_parser("list", help="List available styles")
    p_style_show = p_style_sub.add_parser("show", help="Show style pack details")
    p_style_show.add_argument("style_id", help="Style ID (e.g. black_humor)")
    sub.add_parser("scc-help", help="打印中文操作手册")
    sub.add_parser("help", help="打印中文操作手册 (同 scc-help)")
    sub.add_parser("menu", help="进入交互式文本菜单")
    sub.add_parser("scc-menu", help="进入交互式文本菜单 (同 menu)")
    sub.add_parser("start", help="进入交互式文本菜单 (同 menu)")
    sub.add_parser("books", help="列出所有作品 (同 db list)")
    sub.add_parser("outlines", help="列出所有大纲 (同 outline list)")
    p_write = sub.add_parser("write", help="写前任务卡 (同 pre)")
    p_write.add_argument("chapter_no", nargs="?", help="Chapter number")
    p_submit = sub.add_parser("submit", help="写后入库 (同 post)")
    p_submit.add_argument("chapter_no", nargs="?", help="Chapter number")
    p_jury = sub.add_parser("jury", help="轻量审稿 (同 agents review --mode light)")
    p_jury.add_argument("chapter_no", nargs="?", help="Chapter number")
    p_sc = sub.add_parser("stability-check", help="运行稳定性自检，输出评分和问题清单")
    p_sc.add_argument("--full", action="store_true", help="完整模式（pytest + structure check）")
    sub.add_parser("setup", help="设置小说文件夹路径")
    sub.add_parser("chapters", help="列出当前作品所有章节")
    sub.add_parser("menu-show", help="显示普通用户菜单（纯文本）")
    sub.add_parser("menu-text", help="输出项目状态 JSON（供 Hermes 调用）")

    args = parser.parse_args()

    if args.command == "status":
        sys.exit(cmd_status(detail=getattr(args, "detail", False)))
    elif args.command == "doctor":
        sys.exit(cmd_doctor(detail=getattr(args, "detail", True)))
    elif args.command == "demo":
        sys.exit(cmd_demo())
    elif args.command == "init":
        sys.exit(cmd_init())
    elif args.command == "pre":
        sys.exit(cmd_pre(getattr(args, "chapter_no", None),
                        getattr(args, "slug", None),
                        getattr(args, "volume", None)))
    elif args.command == "post":
        sys.exit(cmd_post(getattr(args, "chapter_no", None),
                         getattr(args, "slug", None),
                         getattr(args, "volume", None),
                         getattr(args, "file", None),
                         getattr(args, "story", False)))
    elif args.command == "review":
        sys.exit(cmd_review(getattr(args, "chapter_no", None),
                           getattr(args, "slug", None),
                           getattr(args, "volume", None)))
    elif args.command == "report":
        sys.exit(cmd_report())
    elif args.command == "guards":
        sys.exit(cmd_guards())
    elif args.command == "check":
        sys.exit(cmd_check(args.file_path))
    elif args.command == "agents":
        sys.exit(cmd_agents(args))
    elif args.command == "rag":
        sys.exit(cmd_rag(args))
    elif args.command == "export":
        sys.exit(cmd_export(args.slug, args.format))
    elif args.command == "wc":
        sys.exit(cmd_wc(args.file_path))
    elif args.command == "genre":
        sys.exit(cmd_genre(args))
    elif args.command == "style":
        sys.exit(cmd_style(args))
    elif args.command == "story":
        sys.exit(cmd_story(args))
    elif args.command == "query":
        sys.exit(cmd_query(args))
    elif args.command == "learn":
        sys.exit(cmd_learn(args))
    elif args.command == "board":
        sys.exit(cmd_board(args))
    elif args.command == "db":
        sys.exit(cmd_db(args))
    elif args.command == "outline":
        sys.exit(cmd_outline(args))
    elif args.command in ("scc-help", "help"):
        sys.exit(cmd_scc_help())
    elif args.command in ("menu", "scc-menu", "start"):
        sys.exit(cmd_menu())
    elif args.command == "books":
        sys.exit(cmd_db(argparse.Namespace(db_action="list")))
    elif args.command == "outlines":
        sys.exit(cmd_outline(argparse.Namespace(outline_action="list")))
    elif args.command == "write":
        sys.exit(cmd_pre(getattr(args, "chapter_no", None), None, None))
    elif args.command == "submit":
        sys.exit(cmd_post(getattr(args, "chapter_no", None), None, None, None, False))
    elif args.command == "jury":
        ch = getattr(args, "chapter_no", None)
        if not ch:
            print("用法: novel jury <章节号>")
            sys.exit(1)
        sys.exit(cmd_agents(argparse.Namespace(agents_action="review", chapter_no=ch, mode="light", slug=None, genre=None, style=None)))
    elif args.command == "stability-check":
        sys.exit(cmd_stability_check(args))
    elif args.command == "setup":
        sys.exit(cmd_setup())
    elif args.command == "chapters":
        sys.exit(cmd_chapters())
    elif args.command == "menu-show":
        sys.exit(cmd_menu_show())
    elif args.command == "menu-text":
        sys.exit(cmd_menu_text())
    else:
        print("=" * 50)
        print(f"  Novel Pipeline - Write Engine {get_version()}")
        print("=" * 50)
        print()
        print("  你现在可以：")
        print()
        print("  0. 首次使用   →  novel setup           # 设置小说文件夹")
        print("  1. 交互菜单   →  novel start")
        print("  2. 检查环境   →  novel status")
        print("  3. 添加大纲   →  novel outline add")
        print("  4. 查看作品   →  novel books")
        print("  5. 开始写作   →  novel write 1")
        print("  6. 审稿       →  novel jury 1")
        print("  7. 导出小说   →  novel export --slug demo_novel")
        print("  8. 运行演示   →  novel demo")
        print()
        print("  详细帮助 →  novel scc-help")
        print("  交互菜单 →  novel menu")
        print("=" * 50)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        pass
