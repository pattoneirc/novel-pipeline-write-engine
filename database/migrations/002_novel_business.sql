-- ============================================================
-- 002_novel_business.sql — 小说业务层
-- 对应 schema.sql 第二节
-- ============================================================

CREATE TABLE IF NOT EXISTS novels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    genre TEXT DEFAULT '',
    theme TEXT DEFAULT '',
    description TEXT DEFAULT '',
    target_words INTEGER DEFAULT 0,
    current_words INTEGER DEFAULT 0,
    status TEXT DEFAULT 'planning',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS volumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id),
    volume_no INTEGER NOT NULL,
    title TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    target_words INTEGER DEFAULT 0,
    UNIQUE(novel_id, volume_no)
);

CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id),
    volume_id INTEGER REFERENCES volumes(id),
    chapter_no INTEGER NOT NULL,
    title TEXT DEFAULT '',
    content TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    word_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'draft',
    file_path TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(novel_id, chapter_no)
);

CREATE TABLE IF NOT EXISTS chapter_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id),
    chapter_id INTEGER NOT NULL REFERENCES chapters(id),
    chunk_no INTEGER NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id),
    name TEXT NOT NULL,
    alias TEXT DEFAULT '',
    role TEXT DEFAULT '',
    identity TEXT DEFAULT '',
    personality TEXT DEFAULT '',
    motivation TEXT DEFAULT '',
    ability TEXT DEFAULT '',
    relationship TEXT DEFAULT '',
    arc TEXT DEFAULT '',
    status TEXT DEFAULT 'active',
    tags TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS worldbuilding (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id),
    category TEXT DEFAULT '',
    title TEXT NOT NULL,
    content TEXT DEFAULT '',
    importance INTEGER DEFAULT 3,
    tags TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS plot_threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id),
    title TEXT NOT NULL,
    content TEXT DEFAULT '',
    thread_type TEXT DEFAULT '伏笔',
    introduced_chapter INTEGER,
    resolved_chapter INTEGER,
    status TEXT DEFAULT 'open',
    importance INTEGER DEFAULT 3
);

CREATE TABLE IF NOT EXISTS writing_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id),
    title TEXT NOT NULL,
    content TEXT DEFAULT '',
    rule_type TEXT DEFAULT 'other',
    importance INTEGER DEFAULT 3,
    status TEXT DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS chapter_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id),
    chapter_id INTEGER NOT NULL REFERENCES chapters(id),
    short_summary TEXT DEFAULT '',
    long_summary TEXT DEFAULT '',
    key_events TEXT DEFAULT '',
    characters_involved TEXT DEFAULT '',
    new_settings TEXT DEFAULT '',
    foreshadowing TEXT DEFAULT '',
    continuity_notes TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(novel_id, chapter_id)
);

CREATE TABLE IF NOT EXISTS continuity_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id),
    chapter_id INTEGER NOT NULL REFERENCES chapters(id),
    check_type TEXT DEFAULT 'continuity',
    issue TEXT DEFAULT '',
    suggestion TEXT DEFAULT '',
    severity INTEGER DEFAULT 1,
    status TEXT DEFAULT 'open',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS novel_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    target_type TEXT,
    target_id INTEGER,
    detail TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now'))
);
