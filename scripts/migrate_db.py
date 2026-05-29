#!/usr/bin/env python3
"""
migrate_db.py — 数据库迁移运行器

用法:
  python scripts/migrate_db.py --config config.json
  python scripts/migrate_db.py --status
  python scripts/migrate_db.py --dry-run
  python scripts/migrate_db.py --db-path ./data/novel_memory.db
"""

import sqlite3
import sys
import argparse
import json
import re
from pathlib import Path

try:
    from config_utils import normalize_config
except Exception:
    def normalize_config(cfg):
        return cfg


SCHEMA_MIGRATIONS_DDL = """\
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT DEFAULT (datetime('now'))
);\
"""


def load_config(config_path=None):
    cfg = {"db_path": "./data/novel_memory.db"}
    if config_path and Path(config_path).exists():
        with open(config_path, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
        cfg.update(normalize_config(user_cfg))
    return normalize_config(cfg)


def find_migrations_dir():
    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir.parent / "database" / "migrations",
        script_dir.parent.parent / "database" / "migrations",
        Path("database/migrations"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def discover_migrations(migrations_dir):
    """Discover migration files and return sorted list of (version, name, path)."""
    migrations = []
    for f in sorted(migrations_dir.glob("*.sql")):
        parts = f.stem.split("_", 1)
        if len(parts) != 2:
            continue
        try:
            version = int(parts[0])
        except ValueError:
            continue
        name = parts[1]
        migrations.append((version, name, f))
    migrations.sort(key=lambda x: x[0])
    return migrations


def ensure_migrations_table(conn):
    conn.execute(SCHEMA_MIGRATIONS_DDL)
    conn.commit()


def get_applied_versions(conn):
    cur = conn.cursor()
    cur.execute("SELECT version FROM schema_migrations")
    return {r[0] for r in cur.fetchall()}


def get_current_version(conn):
    cur = conn.cursor()
    cur.execute("SELECT MAX(version) FROM schema_migrations")
    row = cur.fetchone()
    return row[0] if row and row[0] is not None else 0


def split_sql(sql):
    """Split SQL text into individual statements, stripping comments."""
    lines = []
    for line in sql.split("\n"):
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        lines.append(line)
    full = "\n".join(lines)
    statements = []
    for stmt in full.split(";"):
        stmt = stmt.strip()
        if stmt:
            statements.append(stmt)
    return statements


def run_migration(conn, version, name, filepath, dry_run=False):
    with open(filepath, "r", encoding="utf-8") as f:
        sql = f.read()

    if dry_run:
        stmts = split_sql(sql)
        print(f"  [DRY-RUN] v{version:03d}_{name}: {len(stmts)} statements")
        return True

    try:
        statements = split_sql(sql)
        for stmt in statements:
            conn.execute(stmt)
        conn.execute(
            "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
            (version, name),
        )
        conn.commit()
        print(f"  [OK] v{version:03d}_{name}")
        return True
    except Exception as e:
        conn.rollback()
        print(f"  [FAIL] v{version:03d}_{name}: {e}")
        return False


def show_status(conn, all_migrations):
    applied = get_applied_versions(conn)
    current = get_current_version(conn)

    print(f"\n迁移状态 (当前版本: {current})")
    print(f"{'版本':<8} {'名称':<25} {'状态':<10} {'应用时间'}")
    print("-" * 70)

    for version, name, path in all_migrations:
        if version in applied:
            cur = conn.cursor()
            cur.execute(
                "SELECT applied_at FROM schema_migrations WHERE version = ?",
                (version,),
            )
            row = cur.fetchone()
            applied_at = row[0] if row else "-"
            print(f"{version:<8} {name:<25} {'已应用':<10} {applied_at}")
        else:
            print(f"{version:<8} {name:<25} {'待执行':<10} -")

    pending = sum(1 for v, _, _ in all_migrations if v not in applied)
    print(f"\n已应用: {len(applied)}  待执行: {pending}")


def main():
    parser = argparse.ArgumentParser(
        description="Novel Pipeline — 数据库迁移运行器"
    )
    parser.add_argument(
        "--config", default=None, help="配置文件路径 (默认: config.json)"
    )
    parser.add_argument(
        "--db-path", default=None, help="数据库路径 (覆盖配置文件)"
    )
    parser.add_argument(
        "--status", action="store_true", help="查看当前迁移状态"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="预览将要执行的迁移"
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.db_path:
        cfg["db_path"] = args.db_path

    db_path = Path(cfg["db_path"])
    migrations_dir = find_migrations_dir()

    if not migrations_dir:
        print("[FAIL] 找不到 database/migrations/ 目录")
        sys.exit(1)

    all_migrations = discover_migrations(migrations_dir)
    if not all_migrations:
        print("[WARN] 没有发现迁移文件")
        sys.exit(0)

    if not db_path.exists():
        print(f"[FAIL] 数据库文件不存在: {db_path}")
        print("  请先运行 python scripts/init_db.py 初始化数据库")
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    try:
        ensure_migrations_table(conn)

        if args.status:
            show_status(conn, all_migrations)
            return

        applied = get_applied_versions(conn)
        pending = [(v, n, p) for v, n, p in all_migrations if v not in applied]

        if not pending:
            current = get_current_version(conn)
            print(f"所有迁移已应用 (当前版本: {current})")
            return

        mode = "预览" if args.dry_run else "执行"
        print(f"\n{mode}迁移 (数据库: {db_path})")
        print(f"待执行: {len(pending)} 个迁移\n")

        success = True
        for version, name, path in pending:
            if not run_migration(conn, version, name, path, dry_run=args.dry_run):
                success = False
                break

        if success:
            new_version = get_current_version(conn)
            if args.dry_run:
                print(f"\n预览完成，以上迁移将在实际运行时执行")
            else:
                print(f"\n迁移完成 (当前版本: {new_version})")
        else:
            print(f"\n迁移失败，请检查错误信息")
            sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
