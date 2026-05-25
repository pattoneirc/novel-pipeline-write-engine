"""
Novel Pipeline Dashboard — FastAPI Web Application
================================================================
Routes: 19 endpoints, all returning HTML via Jinja2 (except JSON APIs).
All page titles in Chinese.  Integrates with novel.py via subprocess.

Start:  uvicorn src.dashboard.app:app --host 0.0.0.0 --port 8080 --reload
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Path bootstrap — ensure we can import sibling dashboard modules
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # novel-pipeline-write-engine
NOVEL_PY = PROJECT_ROOT / "novel.py"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.config import load_config, get_novels_root, get_db_path

# ---------------------------------------------------------------------------
# FastAPI + Jinja2 + static files
# ---------------------------------------------------------------------------
from fastapi import FastAPI, BackgroundTasks, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # ── startup ──
    print(f"[dashboard] 启动中... 项目根目录: {PROJECT_ROOT}")
    print(f"[dashboard] novel.py 路径: {NOVEL_PY}  (存在: {NOVEL_PY.exists()})")
    print(f"[dashboard] 数据库路径: {get_db_path()}")
    print(f"[dashboard] 小说根目录: {get_novels_root()}")
    yield
    # ── shutdown ──
    print("[dashboard] 已停止。")


app = FastAPI(
    title="小说写作工作台",
    description="Novel Pipeline Write Engine — Web Dashboard",
    version="0.5.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ===================================================================
#  Helpers
# ===================================================================

@contextmanager
def get_db():
    """Yield a row-factory SQLite connection to the project database."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _run_novel_cmd(*args: str, timeout: int = 300) -> tuple[int, str, str]:
    """Run ``python novel.py <args>`` and return (rc, stdout, stderr)."""
    cmd = [sys.executable, str(NOVEL_PY)] + list(args)
    try:
        r = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"命令超时（{timeout}s）: {' '.join(args)}"
    except FileNotFoundError:
        return -1, "", f"找不到 novel.py: {NOVEL_PY}"


def _run_novel_bg(background_tasks: BackgroundTasks, *args: str, timeout: int = 300):
    """Schedule a novel.py command as a background task."""
    def _runner():
        _run_novel_cmd(*args, timeout=timeout)
    background_tasks.add_task(_runner)


def _scan_novels_from_disk() -> list[dict]:
    """Scan novels_root for novel directories.  Return list of {slug, title, chapters_count, ...}."""
    novels_root = get_novels_root()
    result = []
    if not novels_root.exists():
        return result
    for d in sorted(novels_root.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        slug = d.name
        title = d.name
        chapters_count = 0
        total_words = 0
        volumes = sorted(
            [v for v in d.iterdir() if v.is_dir() and re.match(r"第\d+卷", v.name)]
        )
        for vol in volumes:
            chs = sorted(vol.glob("第*章*.txt"))
            chapters_count += len(chs)
            for ch in chs:
                try:
                    text = ch.read_text(encoding="utf-8")
                    total_words += sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
                except Exception:
                    pass
        # Try to get title from DB
        db_title = title
        db_genre = ""
        db_status = "draft"
        try:
            with get_db() as conn:
                row = conn.execute(
                    "SELECT title, genre, status FROM novels WHERE slug=?", (slug,)
                ).fetchone()
                if row:
                    db_title = row["title"]
                    db_genre = row["genre"]
                    db_status = row["status"]
        except Exception:
            pass

        result.append(
            {
                "slug": slug,
                "title": db_title,
                "genre": db_genre,
                "status": db_status,
                "chapters_count": chapters_count,
                "total_words": total_words,
            }
        )
    return result


def _scan_chapters_from_disk(novel_slug: str) -> list[dict]:
    """Scan a novel's directory on disk for chapter files."""
    novels_root = get_novels_root()
    novel_dir = novels_root / novel_slug
    result = []
    if not novel_dir.exists():
        return result
    volumes = sorted(
        [v for v in novel_dir.iterdir() if v.is_dir() and re.match(r"第\d+卷", v.name)],
        key=lambda v: int(re.match(r"第(\d+)卷", v.name).group(1)),
    )
    for vol in volumes:
        vol_match = re.match(r"第(\d+)卷", vol.name)
        vol_no = int(vol_match.group(1)) if vol_match else 0
        chs = sorted(
            vol.glob("第*章*.txt"),
            key=lambda c: int(re.match(r"第(\d+)章", c.name).group(1))
            if re.match(r"第(\d+)章", c.name)
            else 0,
        )
        for ch in chs:
            ch_match = re.match(r"第(\d+)章_(.+)\.txt", ch.name)
            if ch_match:
                ch_no = int(ch_match.group(1))
                safe_title = ch_match.group(2)
            else:
                ch_no = 0
                safe_title = ch.name
            try:
                text = ch.read_text(encoding="utf-8")
                word_count = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
            except Exception:
                word_count = 0
            result.append(
                {
                    "chapter_no": ch_no,
                    "volume_no": vol_no,
                    "title": safe_title,
                    "file_path": str(ch),
                    "file_name": ch.name,
                    "word_count": word_count,
                    "status": "completed" if word_count > 0 else "empty",
                    "mtime": datetime.fromtimestamp(ch.stat().st_mtime).strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                }
            )
    return result


def _get_default_novel_slug() -> str:
    cfg = load_config()
    return cfg.get("default_novel_slug", "demo_novel")


# ===================================================================
#  Routes — HTML Pages
# ===================================================================

# -------------------------------------------------------------------
#  1.  GET / — Home
# -------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    novels = _scan_novels_from_disk()
    stats = {"novels": len(novels), "chapters": 0, "words": 0}
    for n in novels:
        stats["chapters"] += n["chapters_count"]
        stats["words"] += n["total_words"]

    # recent chapters (last 10 by mtime)
    recent = []
    for novel in novels[:3]:
        chs = _scan_chapters_from_disk(novel["slug"])
        sorted_chs = sorted(chs, key=lambda c: c.get("mtime", ""), reverse=True)
        for c in sorted_chs[:5]:
            c["novel_title"] = novel["title"]
            c["novel_slug"] = novel["slug"]
            recent.append(c)
    recent.sort(key=lambda c: c.get("mtime", ""), reverse=True)
    recent = recent[:10]

    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "title": "首页",
            "active_page": "home",
            "novels": novels,
            "stats": stats,
            "recent": recent,
        },
    )


# -------------------------------------------------------------------
#  2.  GET /projects/new — new project form
# -------------------------------------------------------------------
@app.get("/projects/new", response_class=HTMLResponse)
async def project_new_form(request: Request):
    return templates.TemplateResponse(
        "project_new.html",
        {
            "request": request,
            "title": "新建项目",
            "active_page": "projects",
        },
    )


# -------------------------------------------------------------------
#  3.  POST /projects/new — create project
# -------------------------------------------------------------------
@app.post("/projects/new", response_class=HTMLResponse)
async def project_new_submit(
    request: Request,
    title: str = Form(...),
    slug: str = Form(""),
    genre: str = Form(""),
    description: str = Form(""),
):
    if not slug:
        slug = re.sub(r"[^\w]", "_", title.lower())[:32]

    # 1. Insert into DB
    msg = ""
    db_ok = False
    try:
        with get_db() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO novels (slug, title, genre, description, status)
                   VALUES (?, ?, ?, ?, 'planning')""",
                (slug, title, genre, description),
            )
            conn.commit()
            db_ok = True
    except Exception as e:
        msg = f"数据库错误: {e}"

    # 2. Create directory on disk
    novels_root = get_novels_root()
    novel_dir = novels_root / slug
    try:
        novel_dir.mkdir(parents=True, exist_ok=True)
        (novel_dir / "第01卷").mkdir(exist_ok=True)
    except Exception as e:
        msg += f" 创建目录失败: {e}"

    if not msg:
        msg = f"项目「{title}」创建成功！"

    return templates.TemplateResponse(
        "project_new.html",
        {
            "request": request,
            "title": "新建项目",
            "active_page": "projects",
            "message": msg,
            "message_type": "success" if db_ok else "error",
        },
    )


# -------------------------------------------------------------------
#  4.  GET /write — write page
# -------------------------------------------------------------------
@app.get("/write", response_class=HTMLResponse)
async def write_page(request: Request, slug: str = ""):
    if not slug:
        slug = _get_default_novel_slug()
    novels = _scan_novels_from_disk()
    chapters = _scan_chapters_from_disk(slug)

    # Find current novel info
    current_novel = next((n for n in novels if n["slug"] == slug), None)
    if not current_novel and novels:
        current_novel = novels[0]
        slug = current_novel["slug"]
        chapters = _scan_chapters_from_disk(slug)

    # Determine next chapter number
    next_chapter = 1
    if chapters:
        next_chapter = max(c["chapter_no"] for c in chapters) + 1

    return templates.TemplateResponse(
        "write.html",
        {
            "request": request,
            "title": "写作",
            "active_page": "write",
            "novels": novels,
            "current_slug": slug,
            "current_novel": current_novel,
            "chapters": chapters,
            "next_chapter": next_chapter,
        },
    )


# -------------------------------------------------------------------
#  5.  POST /write/pre/<chapter_no> — trigger pre-write
# -------------------------------------------------------------------
@app.post("/write/pre/{chapter_no}")
async def write_pre(
    chapter_no: int,
    request: Request,
    background_tasks: BackgroundTasks,
    slug: str = Form(""),
    volume: str = Form("1"),
):
    if not slug:
        slug = _get_default_novel_slug()
    args = ["pre", str(chapter_no), "--slug", slug, "--volume", volume]
    rc, stdout, stderr = _run_novel_cmd(*args, timeout=120)

    return JSONResponse(
        {
            "success": rc == 0,
            "chapter_no": chapter_no,
            "stdout": stdout[-2000:],
            "stderr": stderr[-1000:],
            "message": f"第{chapter_no}章预写任务已触发" if rc == 0 else f"预写失败: {stderr[-200:]}",
        }
    )


# -------------------------------------------------------------------
#  6.  POST /write/post/<chapter_no> — trigger post-write
# -------------------------------------------------------------------
@app.post("/write/post/{chapter_no}")
async def write_post(
    chapter_no: int,
    request: Request,
    background_tasks: BackgroundTasks,
    slug: str = Form(""),
    volume: str = Form("1"),
):
    if not slug:
        slug = _get_default_novel_slug()
    args = ["post", str(chapter_no), "--slug", slug, "--volume", volume]
    rc, stdout, stderr = _run_novel_cmd(*args, timeout=300)

    return JSONResponse(
        {
            "success": rc == 0,
            "chapter_no": chapter_no,
            "stdout": stdout[-2000:],
            "stderr": stderr[-1000:],
            "message": f"第{chapter_no}章后处理已完成" if rc == 0 else f"后处理失败: {stderr[-200:]}",
        }
    )


# -------------------------------------------------------------------
#  7.  GET /library — novel library
# -------------------------------------------------------------------
@app.get("/library", response_class=HTMLResponse)
async def library(request: Request):
    novels = _scan_novels_from_disk()
    return templates.TemplateResponse(
        "library.html",
        {
            "request": request,
            "title": "书库",
            "active_page": "library",
            "novels": novels,
        },
    )


# -------------------------------------------------------------------
#  8.  GET /library/<novel_slug> — single novel detail
# -------------------------------------------------------------------
@app.get("/library/{novel_slug}", response_class=HTMLResponse)
async def library_novel(request: Request, novel_slug: str):
    chapters = _scan_chapters_from_disk(novel_slug)
    if not chapters:
        # check DB for metadata even if no chapters on disk
        novel_info = {"slug": novel_slug, "title": novel_slug}
        try:
            with get_db() as conn:
                row = conn.execute(
                    "SELECT * FROM novels WHERE slug=?", (novel_slug,)
                ).fetchone()
                if row:
                    novel_info = dict(row)
        except Exception:
            pass
    else:
        novel_info = {"slug": novel_slug, "title": novel_slug}
        try:
            with get_db() as conn:
                row = conn.execute(
                    "SELECT * FROM novels WHERE slug=?", (novel_slug,)
                ).fetchone()
                if row:
                    novel_info = dict(row)
        except Exception:
            pass

    # Group by volume
    by_volume: dict[int, list[dict]] = {}
    for ch in chapters:
        by_volume.setdefault(ch["volume_no"], []).append(ch)

    return templates.TemplateResponse(
        "library_novel.html",
        {
            "request": request,
            "title": f"书库 — {novel_info.get('title', novel_slug)}",
            "active_page": "library",
            "novel": novel_info,
            "chapters": chapters,
            "by_volume": by_volume,
        },
    )


# -------------------------------------------------------------------
#  9.  GET /review — review page
# -------------------------------------------------------------------
@app.get("/review", response_class=HTMLResponse)
async def review_page(request: Request):
    return templates.TemplateResponse(
        "review.html",
        {
            "request": request,
            "title": "审阅",
            "active_page": "review",
        },
    )


# -------------------------------------------------------------------
#  10. POST /review/scan — scan directory for review candidates
# -------------------------------------------------------------------
@app.post("/review/scan")
async def review_scan(
    request: Request,
    directory: str = Form(""),
    slug: str = Form(""),
):
    if not slug:
        slug = _get_default_novel_slug()
    if not directory:
        novels_root = get_novels_root()
        directory = str(novels_root / slug / "第01卷")

    chapters = []
    scan_dir = Path(directory)
    if scan_dir.exists():
        for f in sorted(scan_dir.glob("第*章*.txt")):
            ch_match = re.match(r"第(\d+)章_(.+)\.txt", f.name)
            ch_no = int(ch_match.group(1)) if ch_match else 0
            try:
                text = f.read_text(encoding="utf-8")
                wc = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
            except Exception:
                wc = 0
            chapters.append(
                {
                    "chapter_no": ch_no,
                    "title": f.name,
                    "word_count": wc,
                    "path": str(f),
                }
            )
    return JSONResponse(
        {
            "success": True,
            "directory": str(scan_dir.resolve()),
            "chapters": chapters,
            "count": len(chapters),
        }
    )


# -------------------------------------------------------------------
#  11. POST /review/run — run agents review
# -------------------------------------------------------------------
@app.post("/review/run")
async def review_run(
    request: Request,
    background_tasks: BackgroundTasks,
    chapter_no: int = Form(...),
    slug: str = Form(""),
    mode: str = Form("light"),
):
    if not slug:
        slug = _get_default_novel_slug()
    args = ["agents", "review", str(chapter_no), "--mode", mode, "--slug", slug]
    rc, stdout, stderr = _run_novel_cmd(*args, timeout=600)

    # Build mock structured review for JSON response
    review_data = {
        "chapter_no": chapter_no,
        "overall_score": 75,
        "status": "pass" if rc == 0 else "error",
        "checks": {
            "punctuation": {
                "name": "标点符号检查",
                "status": "pass",
                "score": 90,
                "issues": [],
            },
            "voice_consistency": {
                "name": "文风一致性",
                "status": "pass",
                "score": 85,
                "issues": [],
            },
            "reader_pull": {
                "name": "读者吸引力",
                "status": "warn",
                "score": 60,
                "issues": [
                    {"code": "RP-001", "message": "开头悬念不够强烈，建议加强冲突引入"},
                ],
            },
            "continuity": {
                "name": "前后连续性",
                "status": "pass",
                "score": 80,
                "issues": [],
            },
        },
        "summary": stdout[-2000:] if stdout else "审阅完成",
    }

    return JSONResponse(
        {
            "success": rc == 0,
            "review": review_data,
            "stdout": stdout[-2000:],
            "stderr": stderr[-1000:],
            "message": f"第{chapter_no}章审阅完成" if rc == 0 else f"审阅出错: {stderr[-200:]}",
        }
    )


# -------------------------------------------------------------------
#  12. GET /review/results/<chapter_no> — view review results
# -------------------------------------------------------------------
@app.get("/review/results/{chapter_no}", response_class=HTMLResponse)
async def review_results(request: Request, chapter_no: int):
    # Generate mock review results
    mock_review = {
        "chapter_no": chapter_no,
        "overall_score": 75,
        "status": "pass",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "checks": {
            "punctuation": {
                "name": "标点符号检查",
                "status": "pass",
                "score": 90,
                "issues": [],
                "detail": "引号配对正确，省略号格式统一，感叹号使用合理。",
            },
            "voice_consistency": {
                "name": "文风一致性",
                "status": "pass",
                "score": 85,
                "issues": [],
                "detail": "叙述风格保持一致，角色对话符合各自设定。",
            },
            "reader_pull": {
                "name": "读者吸引力",
                "status": "warn",
                "score": 60,
                "issues": [
                    {
                        "code": "RP-001",
                        "message": "开头悬念不够强烈，建议加强冲突引入。",
                        "location": "第1-5段",
                    },
                    {
                        "code": "RP-003",
                        "message": "章节结尾钩子较弱，建议埋下更强烈的期待。",
                        "location": "结尾段",
                    },
                ],
                "detail": "整体节奏偏慢，中间部分信息密度可以提升。",
            },
            "continuity": {
                "name": "前后连续性",
                "status": "pass",
                "score": 80,
                "issues": [
                    {
                        "code": "CT-002",
                        "message": "角色「张三」在本章的修为描述与前章略有出入。",
                        "location": "第3段",
                    },
                ],
                "detail": "时间线一致，角色关系继承正确，但个别细节需核实。",
            },
        },
        "chief_editor_notes": {
            "must_fix": [],
            "should_fix": ["开头悬念强化", "结尾钩子优化", "张三修为核实"],
            "keep": ["打斗场景描写精彩", "对话生动自然", "世界观细节丰富"],
        },
    }

    return templates.TemplateResponse(
        "review_results.html",
        {
            "request": request,
            "title": f"审阅结果 — 第{chapter_no}章",
            "active_page": "review",
            "review": mock_review,
        },
    )


# -------------------------------------------------------------------
#  13. GET /rag — RAG search page
# -------------------------------------------------------------------
@app.get("/rag", response_class=HTMLResponse)
async def rag_page(request: Request):
    return templates.TemplateResponse(
        "rag.html",
        {
            "request": request,
            "title": "知识检索",
            "active_page": "rag",
        },
    )


# -------------------------------------------------------------------
#  14. POST /rag/search — execute RAG query
# -------------------------------------------------------------------
@app.post("/rag/search")
async def rag_search(
    request: Request,
    query: str = Form(...),
    top_k: int = Form(5),
):
    if not query.strip():
        return JSONResponse({"success": False, "message": "请输入搜索关键词", "results": []})

    # Try RAG CLI first
    args = ["rag", "query", query]
    rc, stdout, stderr = _run_novel_cmd(*args, timeout=60)

    results = []
    mode = "fts5"

    if rc == 0 and stdout:
        # Parse RAG output
        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("Mode:"):
                mode = line.split(":")[-1].strip()
            elif line.startswith("[") and "]" in line:
                # e.g. "[12] 内容片段..."
                try:
                    bracket_end = line.index("]")
                    ch_part = line[1:bracket_end]
                    evidence = line[bracket_end + 2 :].strip()
                    results.append(
                        {"chapter_no": ch_part.strip(), "evidence": evidence[:200]}
                    )
                except (ValueError, IndexError):
                    pass
    else:
        # Fallback: FTS5 on the DB directly
        try:
            with get_db() as conn:
                # Try FTS5 first
                try:
                    rows = conn.execute(
                        "SELECT title, content, summary FROM novel_chapter_fts "
                        "WHERE novel_chapter_fts MATCH ? LIMIT ?",
                        (query, top_k),
                    ).fetchall()
                    for row in rows:
                        results.append(
                            {
                                "title": row["title"] or "",
                                "evidence": (row["content"] or row["summary"] or "")[
                                    :200
                                ],
                            }
                        )
                except Exception:
                    # FTS5 not available, fall back to LIKE
                    like_q = f"%{query}%"
                    rows = conn.execute(
                        "SELECT title, content, summary FROM chapters "
                        "WHERE content LIKE ? OR title LIKE ? OR summary LIKE ? "
                        "LIMIT ?",
                        (like_q, like_q, like_q, top_k),
                    ).fetchall()
                    for row in rows:
                        results.append(
                            {
                                "title": row["title"] or "",
                                "evidence": (row["content"] or row["summary"] or "")[
                                    :200
                                ],
                            }
                        )
        except Exception as e:
            results = [{"error": f"检索失败: {e}"}]

    return JSONResponse(
        {
            "success": True,
            "query": query,
            "mode": mode,
            "results": results,
            "count": len(results),
        }
    )


# -------------------------------------------------------------------
#  15. GET /settings — settings page
# -------------------------------------------------------------------
@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    cfg = load_config()
    settings_from_db = {}
    try:
        with get_db() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            settings_from_db = {r["key"]: r["value"] for r in rows}
    except Exception:
        pass

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "title": "设置",
            "active_page": "settings",
            "config": cfg,
            "db_settings": settings_from_db,
        },
    )


# -------------------------------------------------------------------
#  16. POST /settings — save settings
# -------------------------------------------------------------------
@app.post("/settings", response_class=HTMLResponse)
async def settings_save(
    request: Request,
    novels_root: str = Form(""),
    db_path: str = Form(""),
    default_novel_slug: str = Form(""),
    openai_api_key: str = Form(""),
    anthropic_api_key: str = Form(""),
):
    cfg = load_config()

    if novels_root:
        cfg["novels_root"] = novels_root
    if db_path:
        cfg["db_path"] = db_path
    if default_novel_slug:
        cfg["default_novel_slug"] = default_novel_slug

    # Save config.json
    config_path = PROJECT_ROOT / "config.json"
    try:
        config_path.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        save_msg = "配置已保存。"
        save_type = "success"
    except Exception as e:
        save_msg = f"保存 config.json 失败: {e}"
        save_type = "error"

    # Save DB settings
    try:
        with get_db() as conn:
            if openai_api_key:
                conn.execute(
                    "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
                    ("openai_api_key", openai_api_key),
                )
            if anthropic_api_key:
                conn.execute(
                    "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
                    ("anthropic_api_key", anthropic_api_key),
                )
            conn.commit()
    except Exception:
        pass

    settings_from_db = {}
    try:
        with get_db() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            settings_from_db = {r["key"]: r["value"] for r in rows}
    except Exception:
        pass

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "title": "设置",
            "active_page": "settings",
            "config": cfg,
            "db_settings": settings_from_db,
            "message": save_msg,
            "message_type": save_type,
        },
    )


# ===================================================================
#  JSON API Endpoints
# ===================================================================

# -------------------------------------------------------------------
#  17. GET /api/novels — JSON list of novels
# -------------------------------------------------------------------
@app.get("/api/novels")
async def api_novels():
    novels = _scan_novels_from_disk()
    return JSONResponse({"novels": novels, "count": len(novels)})


# -------------------------------------------------------------------
#  18. GET /api/chapters/<novel_slug> — JSON list of chapters
# -------------------------------------------------------------------
@app.get("/api/chapters/{novel_slug}")
async def api_chapters(novel_slug: str):
    chapters = _scan_chapters_from_disk(novel_slug)
    return JSONResponse(
        {"novel_slug": novel_slug, "chapters": chapters, "count": len(chapters)}
    )


# -------------------------------------------------------------------
#  19. GET /api/review/<chapter_no> — JSON review results
# -------------------------------------------------------------------
@app.get("/api/review/{chapter_no}")
async def api_review(chapter_no: int):
    mock_review = {
        "chapter_no": chapter_no,
        "overall_score": 75,
        "status": "pass",
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "punctuation": {"status": "pass", "score": 90, "issues": []},
            "voice_consistency": {"status": "pass", "score": 85, "issues": []},
            "reader_pull": {
                "status": "warn",
                "score": 60,
                "issues": [
                    {"code": "RP-001", "message": "开头悬念不够强烈"},
                    {"code": "RP-003", "message": "结尾钩子较弱"},
                ],
            },
            "continuity": {
                "status": "pass",
                "score": 80,
                "issues": [
                    {"code": "CT-002", "message": "部分角色细节需核实"},
                ],
            },
        },
    }
    return JSONResponse(mock_review)


# ===================================================================
#  Entry point
# ===================================================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.dashboard.app:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        reload_dirs=[str(PROJECT_ROOT / "src" / "dashboard")],
    )
