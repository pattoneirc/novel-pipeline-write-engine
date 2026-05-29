-- ============================================================
-- 003_version_promise.sql — 版本与承诺 + 卷级章节规划 + FTS5
-- 对应 schema.sql 第三、四、五节
-- ============================================================

CREATE TABLE IF NOT EXISTS chapter_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id),
    chapter_id INTEGER,
    chapter_no INTEGER NOT NULL,
    version_no INTEGER NOT NULL DEFAULT 1,
    version_status TEXT DEFAULT 'draft',
    title TEXT DEFAULT '',
    content TEXT NOT NULL,
    word_count INTEGER DEFAULT 0,
    change_reason TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reader_promises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id),
    promise_title TEXT NOT NULL,
    promise_detail TEXT NOT NULL,
    introduced_chapter INTEGER,
    expected_payoff_range TEXT DEFAULT '',
    payoff_chapter INTEGER,
    status TEXT DEFAULT 'open',
    importance INTEGER DEFAULT 3,
    reader_emotion TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS volume_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id),
    volume_no INTEGER NOT NULL,
    planned_title TEXT DEFAULT '',
    final_title TEXT DEFAULT '',
    title_status TEXT DEFAULT 'planned',
    suggested_chapters INTEGER DEFAULT 25,
    min_chapters INTEGER DEFAULT 20,
    max_chapters INTEGER DEFAULT 29,
    volume_goal TEXT DEFAULT '',
    opening_state TEXT DEFAULT '',
    ending_target TEXT DEFAULT '',
    must_complete TEXT DEFAULT '',
    unresolved_hooks_to_next TEXT DEFAULT '',
    outline_version INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(novel_id, volume_no)
);

CREATE TABLE IF NOT EXISTS chapter_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id),
    volume_no INTEGER NOT NULL,
    chapter_no INTEGER NOT NULL,
    planned_title TEXT DEFAULT '',
    final_title TEXT DEFAULT '',
    title_status TEXT DEFAULT 'planned',
    plan_status TEXT DEFAULT 'planned',
    chapter_goal TEXT DEFAULT '',
    main_event TEXT DEFAULT '',
    character_focus TEXT DEFAULT '',
    conflict_point TEXT DEFAULT '',
    must_include TEXT DEFAULT '',
    plot_threads_to_advance TEXT DEFAULT '',
    reader_promises_to_advance TEXT DEFAULT '',
    ending_hook_direction TEXT DEFAULT '',
    continuity_from_previous TEXT DEFAULT '',
    title_change_reason TEXT DEFAULT '',
    actual_word_count INTEGER DEFAULT 0,
    actual_summary TEXT DEFAULT '',
    completion_status TEXT DEFAULT '',
    ingested_at TEXT DEFAULT '',
    outline_version INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(novel_id, volume_no, chapter_no)
);

CREATE TABLE IF NOT EXISTS title_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id),
    volume_no INTEGER,
    chapter_no INTEGER,
    old_title TEXT DEFAULT '',
    new_title TEXT DEFAULT '',
    title_type TEXT DEFAULT 'chapter',
    change_reason TEXT DEFAULT '',
    changed_at TEXT DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    title, content, tags,
    content='memories', content_rowid='id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS novel_chapter_fts USING fts5(
    title, content, summary,
    content='chapters', content_rowid='id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS novel_chunk_fts USING fts5(
    content, summary, tags,
    content='chapter_chunks', content_rowid='id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS novel_character_fts USING fts5(
    name, alias, identity, personality, tags,
    content='characters', content_rowid='id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS novel_world_fts USING fts5(
    title, content, tags,
    content='worldbuilding', content_rowid='id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS novel_plot_fts USING fts5(
    title, content,
    content='plot_threads', content_rowid='id'
);
