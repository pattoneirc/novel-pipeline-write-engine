# Novel Pipeline Write Engine — 重构文档

> 版本：v0.6.5 → 重构后
> 日期：2026-05-29（初始重构） / 2026-07-03（后续改进）

---

## 一、重构总览

### 1.1 重构目标

解决项目积累的架构债务和文档失真问题，提升可维护性、可安装性和代码质量。

### 1.2 重构前后对比

| 指标 | 重构前 | 重构后 | 变化 |
|------|--------|--------|------|
| novel.py 行数 | 4937 | ~342 | -93% |
| 重复 `count_chinese()` | 10 处 | 1 处 | -90% |
| 重复 `split_paragraphs()` | 8 处 | 1 处 | -87% |
| 重复 `split_sentences()` | 4 处 | 1 处 | -75% |
| 重复 `load_config()` | 11 处 | 1 处（+config_utils） | -91% |
| 重复 `get_db_path()` | 4 处 | 1 处 | -75% |
| bare `except: pass` | 3 处 | 0 处 | -100% |
| CLI 命令模块 | 1 个巨型文件 | 14 个独立模块 | +13 |
| 数据库迁移文件 | 1 个（004） | 4 个（001-004） | +3 |
| FTS5 检索分数 | 固定 1.0 | BM25 真实分数 | 修复 |
| pip 安装 | 不支持 | `pip install -e .` | 新增 |
| 文档失真 | 6 处 | 0 处 | -100% |
| 测试通过 | 296/296 | 296/296 | 零回归 |

---

## 二、修改内容详述

### 2.1 P0：提取公共工具函数

**新建文件**：`scripts/utils.py`

统一了 6 个在项目中被大量重复实现的工具函数：

| 函数 | 统一前重复数 | 统一后签名 | 说明 |
|------|-------------|-----------|------|
| `count_chinese()` | 10 处 | `(text: str) -> int` | 统计 CJK 字符数，10 处实现完全一致 |
| `split_paragraphs()` | 8 处（3 种逻辑） | `(text: str, min_chars: int = 0) -> list[str]` | `min_chars=0` 退化为简单分割，`>0` 启用短段落合并 |
| `split_sentences()` | 4 处（3 种逻辑） | `(text: str, min_length: int = 2) -> list[str]` | 预编译正则，`min_length` 参数化 |
| `load_config()` | 11 处 | `(config_path: Optional[str] = None) -> dict` | 委托给 `config_utils.load_json_config` |
| `get_db_path()` | 4 处 | `(config: dict) -> str` | 含 workspace slot 机制 + 绝对路径解析 |
| `get_novel_id()` | 2 处 | `(config: dict, slug: str) -> Optional[int]` | 从 SQLite 查询 novel ID |

**受影响的文件**（改为 `from utils import ...`）：

```
scripts/bridge_evidence_guard.py
scripts/chapter_rewriter.py
scripts/editor_revision_guard.py
scripts/guard_orchestrator.py
scripts/patch_planner.py
scripts/perplexity_quality_guard.py
scripts/qgp_baseline.py
scripts/revision_diff_report.py
scripts/revision_task_generator.py
scripts/style_variation_guard.py
src/report/html_report_builder.py
src/task_card/task_card_builder.py
```

### 2.2 P0：修复 bare except: pass

3 处 `except: pass` 改为 `except Exception:`，避免吞掉 `KeyboardInterrupt`/`SystemExit`/`MemoryError`：

| 文件 | 行号 | 修改 |
|------|------|------|
| `novel.py` | ~1151 | `except: pass` → `except Exception: pass` |
| `novel.py` | ~1162 | `except: pass` → `except Exception: pass` |
| `scripts/chapter_pipeline.py` | ~777 | `except: pass` → `except Exception: pass` |

### 2.3 P0：拆分 novel.py

**核心变更**：将 4937 行的单文件入口拆分为 14 个独立命令模块 + 1 个薄调度器。

**新建目录结构**：

```
src/cli/commands/
├── __init__.py          # 包标识
├── common.py            # 共享状态（PROJECT_ROOT, load_project_config, cfg_path）
├── status.py            # cmd_status, cmd_doctor
├── demo.py              # cmd_demo
├── report.py            # cmd_report, cmd_guards, cmd_check, cmd_wc
├── init.py              # cmd_init
├── writing.py           # cmd_pre, cmd_post, cmd_review, cmd_export
├── agents.py            # cmd_agents, cmd_rag
├── story.py             # cmd_story, cmd_query, cmd_learn, cmd_board, cmd_genre, cmd_style
├── db.py                # cmd_db + 16 个 _db_* 辅助函数
├── outline.py           # cmd_outline + 13 个 _outline_* 辅助函数
├── help_cmd.py          # cmd_scc_help
├── menu.py              # cmd_menu, cmd_chapters, cmd_menu_show, cmd_menu_text, cmd_setup
└── stability.py         # cmd_stability_check
```

**novel.py 重写后**：仅保留 `main()` 函数（argparse + 命令分发）和从各模块的导入，约 342 行。

**common.py 职责**：

- 定义 `PROJECT_ROOT`、`SCRIPTS_DIR`、`SRC_GUARDS_DIR` 全局路径
- 统一 `sys.path` 修改（仅此一处）
- 提供 `load_project_config()` 和 `cfg_path()` 辅助函数

### 2.4 P1：配置 pyproject.toml 包安装

**修改文件**：`pyproject.toml`

从仅含 pytest 配置扩展为完整的 Python 包定义：

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "novel-pipeline-write-engine"
version = "0.6.5"
requires-python = ">=3.10"
dependencies = ["pyyaml>=6.0"]

[project.optional-dependencies]
rag = ["chromadb>=0.4.0"]
dev = ["pytest>=7.0", "pytest-timeout>=2.0"]

[project.scripts]
novel = "novel_pipeline.cli_entry:main"

[tool.setuptools.packages.find]
include = ["scripts*", "src*", "novel_pipeline*"]

[tool.setuptools.package-data]
"*" = ["*.sql", "*.json", "*.yaml", "*.yml"]
"novel_pipeline" = ["VERSION"]
```

**新建文件**：

- `novel_pipeline/__init__.py` — 包标识
- `novel_pipeline/version.py` — 版本号统一源（pip 安装后使用）
- `novel_pipeline/VERSION` — 版本号文件副本（pip 安装后读取）
- `novel_pipeline/cli_entry.py` — pip 安装后的 CLI 入口点（内联 main() 函数）

**安装方式**：

```bash
pip install -e .          # 开发模式安装
pip install -e ".[dev]"   # 含开发依赖
pip install -e ".[rag]"   # 含 RAG 依赖
```

**pip 安装后使用**：

```bash
novel --version        # 查看版本
novel status           # 环境诊断
novel guards           # 列出所有门禁
novel demo             # 运行演示
novel start            # 交互式菜单
```

### 2.4.1 pip 安装兼容性修复

pip 安装后，项目根目录的 `version.py`、`novel.py` 不在 `sys.path` 中，导致导入失败。需要以下修复：

#### 问题 1：`from version import get_version` 失败

**原因**：`version.py` 在项目根目录，pip 安装后不在 Python 搜索路径中。

**修复**：8 个命令模块改为兼容导入：

```python
try:
    from novel_pipeline.version import get_version
except ImportError:
    from version import get_version
```

**受影响文件**：

```
src/cli/commands/status.py
src/cli/commands/demo.py
src/cli/commands/report.py
src/cli/commands/init.py
src/cli/commands/story.py
src/cli/commands/help_cmd.py
src/cli/commands/menu.py
src/cli/commands/stability.py
```

#### 问题 2：`from novel import main` 失败

**原因**：`novel.py` 在项目根目录，pip 安装后不可导入。

**修复**：`novel_pipeline/cli_entry.py` 直接内联 `main()` 函数（argparse + 命令分发），不再依赖根目录的 `novel.py`。两个入口共享相同的命令模块，行为一致。

#### 问题 3：`PROJECT_ROOT` 指向 site-packages

**原因**：`common.py` 通过 `Path(__file__).parent.parent.parent.parent` 推导项目根目录，pip 安装后指向 `site-packages/`。

**修复**：新增 `_detect_project_root()` 自动检测逻辑：

```python
_CANDIDATE_MARKERS = ["config.example.json", "VERSION", "novel.py"]

def _detect_project_root() -> Path:
    # 1. 先尝试 __file__ 推导（开发模式）
    root = Path(__file__).resolve().parent.parent.parent.parent
    if any((root / m).exists() for m in _CANDIDATE_MARKERS):
        return root
    # 2. 回退到 CWD 及其父目录（pip 安装模式）
    cwd = Path.cwd().resolve()
    if any((cwd / m).exists() for m in _CANDIDATE_MARKERS):
        return cwd
    for p in [cwd] + list(cwd.parents):
        if any((p / m).exists() for m in _CANDIDATE_MARKERS):
            return p
    return root
```

#### 问题 4：`VERSION` 文件未包含在 wheel 中

**原因**：`VERSION` 在项目根目录，不在任何 Python 包内。

**修复**：
- 复制 `VERSION` 到 `novel_pipeline/VERSION`
- `novel_pipeline/version.py` 读取 `Path(__file__).parent / "VERSION"`（pip 模式）或 `Path(__file__).parent.parent / "VERSION"`（开发模式）
- `pyproject.toml` 配置 `"novel_pipeline" = ["VERSION"]` 确保打包时包含

### 2.5 P1：合并 scripts/ 和 src/ 重复模块

| 重复模块 | 合并方式 |
|----------|---------|
| `scripts/task_card_builder.py` ↔ `src/task_card/task_card_builder.py` | scripts 版改为薄包装，委托给 src 版 |
| `src/report/html_report_builder.py` 中的 load_config/get_db_path/get_novel_id | 删除本地定义，从 `utils` 导入 |
| `src/task_card/task_card_builder.py` 中的 load_config/get_db_path/get_novel_id | 同上 |
| `src/guards/voice_pack_guard.py` 中的 `_load_yaml_pack`/`_load_json_pack` | 提取到 `src/guards/pack_utils.py` |
| `src/guards/meme_pack_guard.py` 中的 `_load_yaml_pack`/`_load_json_pack` | 同上 |

**新建文件**：`src/guards/pack_utils.py` — 统一的 YAML/JSON 包加载器

### 2.6 P1：修复文档失真

| 修正项 | 旧值 | 新值 | 文件 |
|--------|------|------|------|
| 数据库表数量 | 26 表 | 21 表 | README.md |
| 声纹包数量 | 41 个 | 21 个 | README.md |
| 测试文件数量 | 43 个 | 46 个 | README.md |
| voice_packs 目录结构 | base/registers/dialects/memes/bindings/samples | registers/dialects/memes/english | README.md |
| 缺失文档引用 | 5 个 404 链接 | 已移除 | README.md |
| ROADMAP 当前版本 | v0.5.5 | v0.6.5 | docs/ROADMAP.md |
| orchestrator 版本号 | 硬编码 "0.5.5" | `get_version()` | scripts/agents/orchestrator.py |

### 2.7 P2：修复数据库迁移管理

**新建文件**：

| 文件 | 说明 |
|------|------|
| `database/migrations/001_initial_schema.sql` | 通用记忆底座（projects, settings, memories, memory_logs） |
| `database/migrations/002_novel_business.sql` | 小说业务层（novels, volumes, chapters 等 11 张表） |
| `database/migrations/003_version_promise.sql` | 版本与承诺 + 卷级章节规划 + FTS5 索引 |
| `scripts/migrate_db.py` | 迁移运行器（--status / --dry-run / --config） |

**修改文件**：

| 文件 | 修改 |
|------|------|
| `database/schema.sql` | 末尾新增 `schema_migrations` 表 + `INSERT OR IGNORE` 版本记录 |
| `database/migrations/004_voice_memory.sql` | 移除旧的 `schema_migrations` 定义（已统一至 schema.sql） |
| `scripts/init_db.py` | 适配新 `schema_migrations` 结构 |

**迁移运行器用法**：

```bash
python scripts/migrate_db.py --config config.json   # 执行未应用的迁移
python scripts/migrate_db.py --status                # 查看当前迁移状态
python scripts/migrate_db.py --dry-run               # 预览不执行
```

### 2.8 P2：修复 RAG FTS5 score

**修改文件**：

| 文件 | 修改 |
|------|------|
| `scripts/rag/fts5_retriever.py` | 两处 `item["score"] = 1.0` → 使用 BM25 真实分数 |
| `scripts/fts_health.py` | `safe_fts_search` 新增 `with_rank` 参数 |

**技术细节**：FTS5 的 `rank` 列返回负数（越小越相关），取负 `-rank` 后得到正数分数，与向量检索的余弦相似度方向一致。

---

## 三、项目结构

```
novel-pipeline-write-engine/
│
├── novel.py                          # CLI 入口（薄调度器，~342行）
├── version.py                        # 版本号统一源
├── VERSION                           # 当前版本号：v0.6.5
├── pyproject.toml                    # 包定义 + pytest 配置
├── requirements.txt                  # 核心依赖（pytest, pyyaml）
├── requirements-rag.txt              # RAG 依赖（chromadb）
├── config.example.json               # 配置模板
├── config.example.yaml               # 配置模板（YAML）
│
├── novel_pipeline/                   # pip 安装入口包
│   ├── __init__.py
│   ├── VERSION                       # 版本号文件副本（pip 安装后读取）
│   ├── version.py                    # 版本号统一源（兼容 pip/开发两种模式）
│   └── cli_entry.py                  # pip 安装后的 CLI 入口（内联 main()）
│
├── src/                              # 模块化源码
│   ├── __init__.py
│   ├── cli/
│   │   ├── __init__.py               # 包标识（v0.6.5.1 补齐）
│   │   ├── commands/                 # CLI 命令模块（拆分自 novel.py）
│   │   │   ├── __init__.py
│   │   │   ├── common.py            # 共享状态 + 辅助函数
│   │   │   ├── status.py            # status / doctor
│   │   │   ├── demo.py              # demo
│   │   │   ├── report.py            # report / guards / check / wc
│   │   │   ├── init.py              # init
│   │   │   ├── writing.py           # pre / post / review / export
│   │   │   ├── agents.py            # agents / rag
│   │   │   ├── story.py             # story / query / learn / board / genre / style
│   │   │   ├── db.py                # db（workspace 管理）
│   │   │   ├── outline.py           # outline（大纲管理）
│   │   │   ├── help_cmd.py          # scc-help
│   │   │   ├── menu.py              # menu / chapters / setup
│   │   │   └── stability.py         # stability-check
│   │   └── commands_status.py       # 旧版 status（兼容）
│   ├── guards/
│   │   ├── __init__.py
│   │   ├── pack_utils.py            # 统一的 YAML/JSON 包加载器
│   │   ├── reader_pull_guard.py     # 追读力门禁
│   │   ├── voice_pack_guard.py      # 声纹包门禁
│   │   └── meme_pack_guard.py       # 梗包门禁
│   ├── meme/
│   │   ├── __init__.py
│   │   ├── meme_pack_loader.py      # 梗包加载器
│   │   └── meme_pack_validator.py   # 梗包校验器
│   ├── voice/
│   │   ├── __init__.py
│   │   ├── voice_pack_loader.py     # 声纹包加载器
│   │   └── voice_pack_validator.py  # 声纹包校验器
│   ├── report/
│   │   ├── __init__.py               # 包标识（v0.6.5.1 补齐）
│   │   └── html_report_builder.py   # HTML 报告生成
│   └── task_card/
│       ├── __init__.py               # 包标识（v0.6.5.1 补齐）
│       └── task_card_builder.py     # 写前任务卡
│
├── scripts/                          # 核心业务脚本
│   ├── path_setup.py                # 集中式路径设置（ensure_paths）
│   ├── config_utils.py              # 配置工具（normalize_config, load_json_config）
│   ├── utils.py                     # 公共工具函数（count_chinese, split_paragraphs 等）
│   ├── guard_registry.py            # 门禁注册中心（21 guards）
│   ├── guard_result.py              # GuardResult / GuardSummary 数据结构
│   ├── guard_orchestrator.py        # 门禁总控调度
│   ├── chapter_pipeline.py          # 主流水线（pre / post / review / volume）
│   ├── chapter_rewriter.py          # 章节改写
│   ├── init_db.py                   # 数据库初始化
│   ├── migrate_db.py                # 迁移运行器
│   ├── check_schema.py              # Schema 完整性检查
│   ├── doctor.py                    # 环境诊断
│   ├── health_check.py              # 健康检查
│   ├── fts_health.py                # FTS5 自愈
│   ├── export_novel.py              # 导出小说
│   ├── backup_db.py                 # 备份数据库
│   ├── task_card_builder.py         # 任务卡（薄包装 → src/task_card/）
│   ├── report_builder.py            # 报告构建
│   ├── patch_planner.py             # 补丁规划
│   ├── revision_loop_controller.py  # 改稿闭环控制
│   ├── revision_task_generator.py   # 改稿任务生成
│   ├── revision_diff_report.py      # 改稿差异报告
│   ├── final_submission_report.py   # 最终提交报告
│   ├── quality_policy.py            # 质量策略
│   ├── risk_score.py                # 风险评分
│   ├── path_resolver.py             # 路径解析
│   ├── cross_platform_check.py      # 跨平台自检
│   ├── anti_ai_patterns.py          # AI 腔统一规则库
│   ├── consequence_lexicon.py       # 可见后果词库
│   ├── qgp_baseline.py              # QGP 基线
│   ├── scc_menu_renderer.py         # SCC 菜单渲染
│   ├── hermes_menu.py               # Hermes 菜单
│   ├── voice_memory_store.py        # 声纹记忆存储
│   ├── voice_profile_loader.py      # 声纹配置加载
│   ├── import_outline_skeleton.py   # 导入标题骨架
│   ├── import_voice_packs.py        # 导入声纹包
│   ├── import_voice_profiles.py     # 导入声纹配置
│   ├── export_voice_profiles.py     # 导出声纹配置
│   ├── verify_execution_receipt.py  # 执行收据验证
│   ├── guard_contract_utils.py      # 门禁契约工具
│   ├── report_deduplicator.py       # 报告去重
│   │
│   │   # 21 个门禁脚本
│   ├── continuity_evidence_guard.py
│   ├── canon_evidence_guard.py
│   ├── hallucination_guard.py
│   ├── scene_delta_guard.py
│   ├── padding_guard.py
│   ├── show_dont_tell_guard.py
│   ├── character_voice_guard.py
│   ├── dialogue_beat_guard.py
│   ├── classical_register_guard.py
│   ├── perplexity_quality_guard.py
│   ├── editor_revision_guard.py
│   ├── concrete_anchor_guard.py
│   ├── scene_causality_guard.py
│   ├── dialogue_naturalness_guard.py
│   ├── style_variation_guard.py
│   ├── compliance_selfcheck_guard.py
│   ├── bridge_evidence_guard.py
│   ├── concrete_hook_guard.py
│   ├── agent_run_guard.py
│   │
│   ├── guards/
│   │   ├── __init__.py
│   │   └── punctuation_guard.py
│   │
│   ├── agents/                      # 多 Agent 审稿团
│   │   ├── __init__.py
│   │   ├── base_agent.py            # Agent 基类
│   │   ├── orchestrator.py          # 编排器
│   │   ├── context_agent.py         # 上下文 Agent
│   │   ├── voice_agent.py           # 声纹 Agent
│   │   ├── anti_ai_agent.py         # 反 AI 腔 Agent
│   │   ├── plot_agent.py            # 剧情 Agent
│   │   ├── continuity_agent.py      # 连续性 Agent
│   │   ├── reader_pull_agent.py     # 追读力 Agent
│   │   ├── setting_agent.py         # 设定 Agent
│   │   ├── chief_editor.py          # 主编
│   │   └── disabled_example_agent.py
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── registry.py              # 工作区注册
│   │   └── slot_manager.py          # Slot 管理
│   │
│   ├── genre/
│   │   ├── __init__.py
│   │   ├── genre_agent.py           # 题材 Agent
│   │   ├── genre_loader.py          # 题材加载器
│   │   ├── genre_reporter.py        # 题材报告器
│   │   ├── genre_rules.py           # 题材规则
│   │   ├── style_loader.py          # 风格加载器
│   │   └── style_rules.py           # 风格规则
│   │
│   ├── outline/
│   │   ├── __init__.py
│   │   ├── outline_manager.py       # 大纲管理器
│   │   └── similarity.py            # 相似度计算
│   │
│   ├── rag/                         # RAG 检索模块
│   │   ├── __init__.py
│   │   ├── rag_config.py            # RAG 配置
│   │   ├── fts5_retriever.py        # FTS5 全文检索
│   │   ├── vector_retriever.py      # 向量检索
│   │   ├── hybrid_retriever.py      # 混合检索（RRF）
│   │   ├── rag_indexer.py           # 索引导入
│   │   └── rag_query.py             # 统一查询入口
│   │
│   └── story/
│       ├── __init__.py
│       ├── story_init.py            # Story 初始化
│       ├── contract_builder.py      # 契约构建
│       ├── commit_builder.py        # 提交构建
│       └── story_health.py          # Story 健康
│
├── database/
│   ├── schema.sql                   # SQLite schema（21 表 + 6 FTS5 + schema_migrations）
│   └── migrations/
│       ├── 001_initial_schema.sql   # 通用记忆底座
│       ├── 002_novel_business.sql   # 小说业务层
│       ├── 003_version_promise.sql  # 版本与承诺 + FTS5
│       └── 004_voice_memory.sql     # 声纹记忆
│
├── configs/                         # 配置文件
│   ├── agents.yaml                  # Agent 配置
│   ├── scc_menu.json                # SCC 菜单
│   └── jury/                        # 陪审团配置
│       ├── jury.default.yaml
│       ├── jury.light.yaml
│       ├── jury.strict.yaml
│       ├── jury.webnovel.yaml
│       └── agents/                  # 21 个陪审员配置
│
├── genre_packs/                     # 10 种题材包
├── style_packs/                     # 9 种风格包
├── voice_packs/                     # 声纹资产
│   ├── registers/                   # 5 个语体包
│   ├── dialects/                    # 6 个方言包
│   ├── memes/                       # 2 个梗包
│   └── english/                     # 4 个英语包
├── templates/                       # 模板
│   ├── genres/                      # 5 种题材模板
│   ├── voice_pack/                  # 2 个声纹模板
│   └── meme_pack/                   # 2 个梗包模板
│
├── tests/                           # 46 个测试文件，296 个测试用例
│   ├── conftest.py                   # pytest 统一路径配置（v0.6.5.1）
├── docs/                            # 文档
├── examples/                        # 示例
│   ├── demo_novel/
│   ├── demo_chapters/
│   └── demo_reports/
│
└── install.bat / install.sh         # 安装脚本
```

---

## 四、模块依赖关系

### 4.1 分层架构图

```
┌─────────────────────────────────────────────────────────┐
│                     用户入口层                            │
│  novel.py (开发模式)  │  novel_pipeline/ (pip 安装模式)  │
│  python novel.py      │  novel (CLI 命令)               │
│  共享同一套命令模块 ←──┘                                 │
└──────────┬───────────┴──────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────┐
│                  CLI 命令层                               │
│  src/cli/commands/                                       │
│  common → status │ demo │ report │ init │ writing │      │
│          agents │ story │ db │ outline │ help │ menu │   │
│          stability                                      │
└──────────┬──────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────┐
│                 核心业务层                                │
│  scripts/                                                │
│  config_utils ← utils ← chapter_pipeline                │
│                ← guard_registry ← guard_orchestrator     │
│                ← guard_result                            │
│                ← init_db / migrate_db / check_schema     │
│                ← export_novel / backup_db / doctor       │
└──────────┬──────────────────────────────────────────────┘
           │
     ┌─────┴──────┬────────────┬────────────┐
     ▼            ▼            ▼            ▼
┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ 门禁层   │ │ Agent层  │ │ RAG层    │ │ Story层  │
│ 21个     │ │ 8个      │ │ 6个      │ │ 4个      │
│ guard    │ │ agent    │ │ rag      │ │ story    │
│ 脚本     │ │ +编排器  │ │ 模块     │ │ 模块     │
└────┬────┘ └────┬─────┘ └────┬─────┘ └──────────┘
     │           │            │
     ▼           ▼            ▼
┌─────────────────────────────────────────────────────────┐
│                  基础设施层                               │
│  src/guards/ (pack_utils, reader_pull, voice, meme)      │
│  src/voice/  (voice_pack_loader, validator)              │
│  src/meme/   (meme_pack_loader, validator)               │
│  src/report/ (html_report_builder)                       │
│  src/task_card/ (task_card_builder)                      │
└─────────────────────────────────────────────────────────┘
```

### 4.2 核心依赖链

#### 入口 → 命令 → 业务

```
开发模式: python novel.py
pip 模式: novel (→ novel_pipeline.cli_entry:main)
    │
    └→ src/cli/commands/common.py (_detect_project_root 自动检测项目根目录)
         └→ scripts/config_utils.py
    └→ src/cli/commands/writing.py
         └→ scripts/chapter_pipeline.py
              └→ scripts/guard_registry.py
              │    └→ scripts/guard_result.py
              │    └→ 21 个 guard 脚本
              │         └→ scripts/utils.py (count_chinese, split_paragraphs 等)
              │         └→ scripts/config_utils.py
              └→ scripts/init_db.py
                   └→ database/schema.sql
                   └→ database/migrations/*.sql
```

#### 门禁注册与执行

```
guard_registry.py (统一注册入口)
  ├→ Level 1 (硬门禁): continuity_evidence, canon_evidence, hallucination, scene_delta
  ├→ Level 2 (软门禁): padding, anti_ai, show_dont_tell, character_voice,
  │                    dialogue_beat, classical_register, perplexity_quality,
  │                    editor_revision, concrete_anchor, scene_causality,
  │                    dialogue_naturalness, style_variation, punctuation,
  │                    reader_pull, voice_pack, meme_pack
  └→ Level 3 (合规): compliance_selfcheck

运行模式:
  draft     → 4 个 Level 1 门禁
  standard  → 13 个门禁 (Level 1 + 部分 Level 2)
  submission→ 20 个门禁 (全部)
```

#### Agent 审稿团

```
orchestrator.py
  ├→ ContextAgent     (动作承接 / 硬状态 / 钩子 / 真空续写)
  ├→ VoiceAgent       (语体污染 / 方言越界 / 梗滥用 / 叙述污染)
  ├→ AntiAIAgent      (模板句 / 总结腔 / 说明书腔 / 重复 / 过度解释)
  ├→ PlotAgent        (因果断裂 / 伏笔遗忘 / 冲突消失 / 节奏)
  ├→ ContinuityAgent  (伤势遗忘 / 位置矛盾 / 物品消失 / 时间线)
  ├→ ReaderPullAgent  (钩子 / 兑现 / 悬念 / 爽点 / 代价)
  ├→ SettingAgent     (设定矛盾 / 能力膨胀 / 世界规则 / 物品追踪)
  └→ ChiefEditor      (去重 / 排序 / 分类 / 综合评分)
```

#### RAG 检索

```
rag_query.py (统一查询入口)
  ├→ fts5_retriever.py    (FTS5 全文检索, BM25 评分)
  ├→ vector_retriever.py  (向量检索, chromadb, 优雅降级)
  └→ hybrid_retriever.py  (混合检索, RRF 融合)
       └→ rag_config.py   (配置)
       └→ rag_indexer.py  (索引构建)
```

### 4.3 公共模块依赖关系

```
scripts/config_utils.py          ← 被所有需要配置的模块导入
  提供: normalize_config(), load_json_config(), resolve_path()

scripts/utils.py                 ← 被 12+ 个 guard 和工具脚本导入
  提供: count_chinese(), split_paragraphs(), split_sentences(),
        load_config(), get_db_path(), get_novel_id()
  依赖: config_utils

scripts/guard_result.py          ← 被 guard_registry 和所有 guard 导入
  提供: GuardResult, GuardSummary, GuardFinding,
        finding(), result_pass(), result_warn(), result_fail()

src/guards/pack_utils.py         ← 被 voice_pack_guard 和 meme_pack_guard 导入
  提供: _load_yaml_pack(), _load_json_pack()

novel_pipeline/version.py        ← 被 8 个 CLI 命令模块导入（pip 安装模式）
  提供: get_version(), get_version_tuple()
  读取: novel_pipeline/VERSION

src/cli/commands/common.py       ← 被所有 CLI 命令模块导入
  提供: PROJECT_ROOT, SCRIPTS_DIR, SRC_GUARDS_DIR,
        load_project_config(), cfg_path()
  依赖: config_utils
  特性: _detect_project_root() 自动检测开发/pip 两种模式
```

---

## 五、数据流

### 5.1 写作流水线

```
用户执行: python novel.py pre 1
    │
    ▼
cmd_pre() [src/cli/commands/writing.py]
    │
    ├→ 加载配置 (common.py → config_utils.py)
    ├→ 连接 SQLite (utils.get_db_path)
    ├→ 读取上章摘要 (chapter_pipeline.py)
    ├→ 读取标题骨架 (chapter_plans 表)
    ├→ 生成写前任务卡 (task_card_builder.py)
    │
    ▼
输出: 任务卡 (承接/推进/禁止 + Voice/Meme 提醒)

═══════════════════════════════════════

用户完成写作后: python novel.py post 1
    │
    ▼
cmd_post() [src/cli/commands/writing.py]
    │
    ├→ 加载配置 + 连接 SQLite
    ├→ 读取章节文件
    ├→ 运行 21 个门禁 (guard_registry.py)
    │   ├→ Level 1 硬门禁 (FAIL 阻止入库)
    │   └→ Level 2 软门禁 (WARN 不阻止)
    ├→ 生成 guard_summary.json (真相源)
    ├→ 入库 (chapters/chunks/summaries/FTS5)
    ├→ 更新 chapter_plans 状态
    │
    ▼
输出: 门禁报告 + 入库确认
```

### 5.2 门禁执行流

```
guard_registry.run_standard_guards(content, chapter_no, mode="standard")
    │
    ├→ 检查 FTS5 健康 (fts_health.py)
    │   └→ 损坏时尝试 rebuild / fallback
    │
    ├→ 按 mode 选择门禁列表
    │
    ├→ 逐个执行 run_single_guard()
    │   ├→ importlib 动态导入
    │   ├→ 适配不同函数签名
    │   ├→ _adapt_legacy_dict() 统一结果格式
    │   └→ Level 2 门禁 FAIL → 降级为 WARN
    │
    ├→ 保存各门禁报告 (chapter_XXX_guard_report.json)
    │
    └→ 保存 guard_summary.json (真相源)
```

---

## 六、配置体系

### 6.1 配置加载链

```
config.json (用户配置)
    │
    ▼ 不存在时回退
config.example.json (模板)
    │
    ▼
config_utils.normalize_config()
    │  ├→ 合并 paths/novel/gates 嵌套结构到顶层
    │  ├→ 填充默认值 (db_path, novels_root 等)
    │  └→ 规范化 word_count 规则
    │
    ▼
运行时配置 dict
```

### 6.2 关键配置项

| 配置键 | 默认值 | 说明 |
|--------|--------|------|
| `db_path` | `./data/novel_memory.db` | SQLite 数据库路径 |
| `novels_root` | `./novels` | 小说文件根目录 |
| `exports_root` | `./exports` | 导出目录 |
| `reports_root` | `./exports/reports` | 报告目录 |
| `default_novel_slug` | `demo_novel` | 默认小说标识 |
| `default_genre` | `xianxia` | 默认题材 |
| `default_style` | `webnovel` | 默认风格 |
| `word_count` | (按章节类型分级) | 字数门禁规则 |
| `quality_policy.run_mode` | `standard` | 门禁运行模式 |

---

## 七、数据库 Schema

### 7.1 表清单（21 表 + 6 FTS5）

| 分层 | 表名 | 说明 |
|------|------|------|
| **通用记忆** | `projects` | 项目 |
| | `settings` | 设置 |
| | `memories` | 记忆 |
| | `memory_logs` | 记忆日志 |
| **小说业务** | `novels` | 小说 |
| | `volumes` | 卷 |
| | `chapters` | 章节 |
| | `chapter_chunks` | 章节切片 |
| | `characters` | 角色 |
| | `worldbuilding` | 世界观 |
| | `plot_threads` | 剧情线 |
| | `writing_rules` | 写作规则 |
| | `chapter_summaries` | 章节摘要 |
| | `continuity_checks` | 连续性检查 |
| | `novel_logs` | 小说日志 |
| **版本与承诺** | `chapter_versions` | 章节版本 |
| | `reader_promises` | 读者承诺 |
| **卷级规划** | `volume_plans` | 卷规划 |
| | `chapter_plans` | 章节规划 |
| | `title_history` | 标题历史 |
| **迁移管理** | `schema_migrations` | 迁移版本记录 |
| **声纹记忆** | `voice_packs` | 声纹包 |
| | `character_voice_profiles` | 角色声纹 |
| | `character_voice_observations` | 声纹观察 |
| | `character_voice_examples` | 声纹示例 |
| | `character_voice_history` | 声纹历史 |
| **FTS5 索引** | `memory_fts` | 记忆全文索引 |
| | `novel_chapter_fts` | 章节全文索引 |
| | `novel_chunk_fts` | 切片全文索引 |
| | `novel_character_fts` | 角色全文索引 |
| | `novel_world_fts` | 世界观全文索引 |
| | `novel_plot_fts` | 剧情线全文索引 |

### 7.2 迁移版本

| 版本 | 名称 | 内容 |
|------|------|------|
| 001 | `initial_schema` | 通用记忆底座（4 表） |
| 002 | `novel_business` | 小说业务层（11 表） |
| 003 | `version_promise` | 版本/承诺/规划 + FTS5（6 表 + 6 FTS5） |
| 004 | `voice_memory` | 声纹记忆（5 表） |

---

## 八、已知遗留问题

以下问题未在初始重构中处理，部分已在后续改进（§九）中解决。

| 优先级 | 问题 | 建议 | 状态 |
|--------|------|------|------|
| 中 | `sys.path.insert` 仍在 43 个测试文件中使用 | 测试改用 `conftest.py` 统一配置 | ✅ **已解决**（§九 2.2） |
| 中 | `scripts/` 下约 100 处 `except Exception` 无日志 | 逐步添加 `logging.warning` | ⚠️ **部分解决**（§九 2.3），7 处关键点已添加日志 |
| 中 | `scripts/` 类型标注覆盖率约 15% | 逐步补全 | ⚠️ 仍需投入 |
| 低 | `disabled_example_agent.py` 是空壳 | 清理或实现 | ✅ **已解决**（§九 2.4），改为文档式模板 |
| 低 | `novel.py` 中硬编码 Windows 路径示例 | 改为跨平台示例 | ✅ **已解决**（v0.6.2 跨平台发布） |
| 低 | `src/cli/commands_status.py` 旧文件 | 更新引用后删除 | ⚠️ 仍被 `health_check.py` 引用，暂不能删除 |
| 低 | RAG 模块无测试 | 补充测试 | ⚠️ 仍未覆盖 |
| 低 | `novel.py` 中 `from version import get_version` 无 try/except | 与 8 个命令模块保持一致，改为兼容导入；开发模式下风险极低（总是在项目根运行） | ⚠️ 待修复 |
| 低 | `novel.py` 与 `cli_entry.py` 的 argparse + 命令分发逻辑约 250 行重复 | 提取到 `src/cli/argparse_config.py` 共享，或让 `novel.py` 也通过 `novel_pipeline.cli_entry:main` 调用 | ⚠️ 待修复 |
| 低 | `VERSION` 与 `novel_pipeline/VERSION` 需手动同步 | 升级版本号时必须同时更新两处；可改为 `get_version()` 多候选路径自动回退，或构建脚本自动同步 | ⚠️ 待修复 |


## 九、v0.6.5.1 后续改进（2026-07-03）

### 9.1 改进总览

在初始重构基础上，进一步解决 sys.path 散布、dead import、silent except 等代码卫生问题。

| 指标 | 改进前 | 改进后 | 变化 |
|------|--------|--------|------|
| 非引导文件中的 `sys.path.insert` | 55 处 | 0 处 | -100% |
| 测试文件中的 `sys.path.insert` | 41 处 | 2 处（仅 conftest.py 引导） | -95% |
| dead `import sys` | 31 处 | 0 处 | -100% |
| 关键 silent except 加日志 | 0 处 | 7 处 | +7 |
| 缺失 `__init__.py` | 3 个目录 | 0 个 | 修复 |
| pyproject.toml 依赖一致性 | 1 处缺失 | 0 处 | 修复 |
| 测试通过 | 296/296 | 296/296 | 零回归 |

### 9.2 修改内容详述

#### 9.2.1 P0：集中化 sys.path 管理

**核心变更**：将散落在 55 个文件中的 `sys.path.insert` 内联代码集中到 2 个引导文件。

**新建 `scripts/path_setup.py`** — 统一的路径设置模块：

```python
def ensure_paths() -> None:
    """将项目标准目录加入 sys.path。"""
    root = Path(__file__).resolve().parent.parent
    _add_path(root)                     # 项目根
    _add_path(root / "scripts")         # scripts/
    _add_path(root / "src")             # src/
    _add_path(root / "src" / "guards")  # src/guards/
    _add_path(root / "src" / "cli")     # src/cli/
```

**scripts/ 文件整改**（7 个文件，内联 sys.path.insert → `from path_setup import ensure_paths; ensure_paths()`）：

| 文件 | 改进前 | 改进后 |
|------|--------|--------|
| `scripts/agents/smoke_test.py` | `sys.path.insert(0, str(PROJECT_ROOT))` | `ensure_paths()` |
| `scripts/guard_registry.py` | 3 行 sys.path.insert（project_root + script_dir + script_dir/guards） | `ensure_paths()` |
| `scripts/health_check.py` | 2 处 sys.path.insert（src_path + scripts_dir） | `ensure_paths()` |
| `scripts/rag/fts5_retriever.py` | `sys.path.insert(0, str(_SCRIPT_DIR))` | `ensure_paths()` |
| `scripts/report_builder.py` | `sys.path.insert(0, str(PROJECT_ROOT))` | `ensure_paths()` |
| `scripts/risk_score.py` | `sys.path.insert(0, str(SCRIPT_DIR))` | `ensure_paths()` |
| `scripts/task_card_builder.py` | `sys.path.insert(0, str(_src))` | `ensure_paths()` |

**src/ 文件整改**（5 个文件）：

| 文件 | 改进前 | 改进后 |
|------|--------|--------|
| `src/cli/commands/common.py` | 2 行 sys.path.insert（SCRIPTS_DIR + SRC_GUARDS_DIR） | `ensure_paths()` |
| `src/cli/commands_status.py` | 函数内 3 行 sys.path.insert | `ensure_paths()` |
| `src/guards/voice_pack_guard.py` | 3 行 sys.path.insert | `ensure_paths()` |
| `src/report/html_report_builder.py` | 2 处共 5 行 sys.path.insert（PROJECT_ROOT + scripts_dir） | `ensure_paths()` |
| `src/task_card/task_card_builder.py` | 3 行 sys.path.insert | `ensure_paths()` |

**不可消除的引导代码**（7 处，全部为入口/引导文件自身）：

```
novel.py:24                  — CLI 入口引导（需添加 src/cli/ 才能 import commands.*）
novel_pipeline/cli_entry.py:15 — pip 安装入口引导（同上）
src/cli/commands/common.py:29  — 命令共享层引导（需添加 scripts/ 才能 import path_setup）
scripts/path_setup.py:6,39    — 路径设置模块自身的内部实现
tests/conftest.py:6,16        — 测试配置模块自身的引导
```

#### 9.2.2 P1：统一测试路径配置

**新建 `tests/conftest.py`** — pytest 自动加载，将 `scripts/` 和 `scripts/guards/` 加入 sys.path：

```python
_root = Path(__file__).resolve().parent.parent
for _sub in ["scripts", "scripts/guards"]:
    _p = str(_root / _sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)
```

**清理 41 个测试文件**：删除各文件中 5 种不同的 `sys.path.insert` 写法：

| 原写法 | 文件数 | 处理 |
|--------|--------|------|
| `sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))` | 23 | 删除该行 |
| `sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))` | 12 | 删除该行 |
| `sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))` | 4 | 删除该行 |
| `sys.path.insert(0, "scripts")` | 2 | 删除该行 |
| `sys.path.insert(0, ..., 'scripts', 'guards')` | 1 | 删除该行 |

**后续清理 dead `import sys`**（31 个文件）：删除 `sys.path.insert` 后，`import sys` 变为未使用。逐一删除 `import sys` 或从多导入行中移除 `sys,`。

#### 9.2.3 P1：关键 silent except 治理

为 7 个最容易掩藏问题的 `except Exception: pass` 添加 `[WARN]` 日志输出：

| 文件 | 位置 | 改进 |
|------|------|------|
| `scripts/chapter_pipeline.py:777` | FTS DELETE 异常静默 | `print("[WARN] FTS cleanup failed for chapter {ch_id}")` |
| `scripts/chapter_pipeline.py:1233` | prev_brief JSON 解析异常静默 | `print("[WARN] failed to parse prev_brief")` |
| `scripts/utils.py:72` | workspace registry 读取异常静默 | `print("[WARN] workspace registry read failed, falling back to config")` |
| `src/cli/commands/common.py:65` | _get_active_db_path 异常静默 | `print("[WARN] workspace registry read failed")` |
| `src/cli/commands/common.py:119` | _check_outline_gate 异常静默 | `print("[WARN] outline check failed")` |
| `scripts/cross_platform_check.py:90` | 文件读取异常静默 | `print("[WARN] failed to read {file}")` |
| `scripts/character_voice_guard.py:317` | 语体包加载异常静默 | `print("[WARN] failed to load dialect pack")` |

#### 9.2.4 P2：清理 disabled_example_agent.py

将空壳示例改为清晰的文档式模板，包含：
- 明确的用途说明（"作为创建新 Agent 的模板"）
- 如何启用的指引（"在 configs/agents.yaml 中配置"）
- 带 TODO 的占位审稿逻辑供复制使用

#### 9.2.5 P2：补齐缺失的 `__init__.py`

3 个目录缺少包标识文件（Python 3.3+ 隐式命名空间包虽然可用，但某些静态分析工具会报错）：

| 目录 | 文件 |
|------|------|
| `src/cli/` | `src/cli/__init__.py` |
| `src/report/` | `src/report/__init__.py` |
| `src/task_card/` | `src/task_card/__init__.py` |

#### 9.2.6 P2：修复 pyproject.toml 依赖一致性

`requirements-rag.txt` 中声明了 `sentence-transformers>=2.2.0`，但 `pyproject.toml` 的 `[project.optional-dependencies] rag` 中缺失。

**修复**：`pyproject.toml` 中 `rag` 可选依赖补充：
```toml
rag = [
    "chromadb>=0.4.0",
    "sentence-transformers>=2.2.0",
]
```

### 9.3 更新后的 sys.path 架构

```
                    ┌──────────────────────────┐
                    │  novel.py (CLI入口)       │  仅1行引导:
                    │  cli_entry.py (pip入口)   │  sys.path + src/cli/
                    └──────────┬───────────────┘
                               │
                    ┌──────────▼───────────────┐
                    │  src/cli/commands/       │  仅1行引导:
                    │  common.py               │  sys.path + scripts/
                    │  → ensure_paths()        │  然后 path_setup 接管
                    └──────────┬───────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                 ▼
       scripts/           src/                 tests/
       path_setup.py    (无引导代码)           conftest.py
       ensure_paths()                          (2行引导,自动加载)
              │
              ▼
       统一添加: project_root, scripts/, src/, src/guards/, src/cli/
```
