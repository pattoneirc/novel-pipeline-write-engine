#!/usr/bin/env python3
"""
outline_manager.py — 大纲管理器 v0.6.5

管理当前活跃 slot 下的大纲：
- 添加 / 导入 / 列出 / 查看 / 切换 / 对比 / 回滚 / 删除 / 分类
- 每个大纲存储为 JSON 文件，保存在 workspace/slots/<slot>/outlines/
- 支持 outline_versions 数组实现版本历史与回滚
- 通过 project.json 的 active_outline 字段标记当前激活大纲
- 所有输出使用中文
"""

import json
import shutil
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple


class OutlineManager:
    """大纲管理器：增删改查、版本管理、回滚"""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.workspace_dir = self.project_root / "workspace"

    # ──────────────────────────────────────────────
    #  内部工具方法
    # ──────────────────────────────────────────────

    def _get_registry(self) -> Dict:
        """读取 workspace/registry.json"""
        rf = self.workspace_dir / "registry.json"
        if not rf.exists():
            return {"active_slot": "", "slots": []}
        return json.loads(rf.read_text(encoding="utf-8"))

    def _save_registry(self, data: Dict) -> None:
        rf = self.workspace_dir / "registry.json"
        rf.parent.mkdir(parents=True, exist_ok=True)
        rf.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _get_active_slot(self) -> Optional[str]:
        reg = self._get_registry()
        return reg.get("active_slot", "")

    def _get_slot_dir(self, slot_id: str = None) -> Path:
        sid = slot_id or self._get_active_slot()
        return self.workspace_dir / sid

    def _get_project_json(self, slot_id: str = None) -> Dict:
        sf = self._get_slot_dir(slot_id) / "project.json"
        if sf.exists():
            return json.loads(sf.read_text(encoding="utf-8"))
        return {
            "name": "未命名项目",
            "title": "未命名项目",
            "active_outline": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

    def _save_project_json(self, data: Dict, slot_id: str = None) -> None:
        sf = self._get_slot_dir(slot_id) / "project.json"
        sf.parent.mkdir(parents=True, exist_ok=True)
        sf.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _outlines_dir(self, slot_id: str = None) -> Path:
        d = self._get_slot_dir(slot_id) / "outlines"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _read_outline_file(self, outline_id: str, slot_id: str = None) -> Optional[Dict]:
        fp = self._outlines_dir(slot_id) / f"{outline_id}.json"
        if not fp.exists():
            return None
        return json.loads(fp.read_text(encoding="utf-8"))

    def _write_outline_file(self, outline_id: str, data: Dict, slot_id: str = None) -> None:
        fp = self._outlines_dir(slot_id) / f"{outline_id}.json"
        fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _delete_outline_file(self, outline_id: str, slot_id: str = None) -> bool:
        fp = self._outlines_dir(slot_id) / f"{outline_id}.json"
        if fp.exists():
            fp.unlink()
            return True
        return False

    def _list_outline_ids(self, slot_id: str = None) -> List[str]:
        od = self._outlines_dir(slot_id)
        ids = []
        for f in sorted(od.glob("*.json")):
            if f.stem != ".gitkeep":
                ids.append(f.stem)
        return ids

    def _generate_outline_id(self, title: str = "") -> str:
        """根据标题生成简短ID"""
        import re
        base = re.sub(r'[^a-z0-9\u4e00-\u9fff]', '_', title.lower().strip())
        base = base[:20] if base else "outline"
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{base}_{ts}"

    def _snapshot_version(self, old_data: Dict) -> List[Dict]:
        """创建一个版本快照，追加到版本历史"""
        versions = old_data.get("outline_versions", [])
        snapshot = {
            "version": len(versions) + 1,
            "title": old_data.get("title", ""),
            "content": old_data.get("content", ""),
            "tags": old_data.get("tags", []),
            "genre": old_data.get("genre", ""),
            "style": old_data.get("style", ""),
            "chapter_count": old_data.get("chapter_count", 0),
            "volume_count": old_data.get("volume_count", 1),
            "saved_at": datetime.now().isoformat(),
        }
        versions.append(snapshot)
        return versions

    # ──────────────────────────────────────────────
    #  1. 添加大纲
    # ──────────────────────────────────────────────

    def add_outline(self, content: str, title: str = "",
                    genre: str = "", style: str = "",
                    tags: list = None,
                    similarity_result: Dict = None) -> Dict:
        """
        添加新大纲（从文本内容）。
        自动生成 ID 和 metadata。
        返回: {"id": ..., "title": ..., "created": True/False, "similarity": {...}}
        """
        active = self._get_active_slot()
        if not active:
            return {"status": "error", "message": "没有活跃的工作区。请先运行 python novel.py db init"}

        # 提取标题（优先使用传入标题，其次取首行非空非#行）
        if not title:
            for line in content.strip().split("\n"):
                line = line.strip().lstrip("#").strip()
                if line:
                    title = line[:40]
                    break
        if not title:
            title = "未命名大纲"

        outline_id = self._generate_outline_id(title)

        # 解析章节数、卷数
        chapter_count = 0
        volume_count = 1
        for line in content.split("\n"):
            line = line.strip()
            if "第" in line and ("章" in line or "卷" in line):
                if "卷" in line:
                    # 粗略计数
                    pass
                if "章" in line:
                    chapter_count += 1

        data = {
            "id": outline_id,
            "title": title,
            "content": content,
            "tags": tags or [],
            "genre": genre,
            "style": style,
            "chapter_count": chapter_count,
            "volume_count": volume_count,
            "versions_count": 0,
            "outline_versions": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "source": "add",
        }

        if similarity_result:
            data["similarity_check"] = similarity_result

        self._write_outline_file(outline_id, data)

        # 自动设为激活大纲
        proj = self._get_project_json()
        proj["active_outline"] = outline_id
        proj["updated_at"] = datetime.now().isoformat()
        self._save_project_json(proj)

        result = {
            "status": "ok",
            "id": outline_id,
            "title": title,
            "created": True,
            "chapter_count": chapter_count,
            "volume_count": volume_count,
        }
        if similarity_result:
            result["similarity"] = similarity_result

        return result

    # ──────────────────────────────────────────────
    #  2. 导入大纲（指定标题）
    # ──────────────────────────────────────────────

    def import_outline(self, content: str, title: str,
                       genre: str = "", style: str = "",
                       tags: list = None) -> Dict:
        """导入大纲，需要指定标题"""
        return self.add_outline(
            content=content,
            title=title,
            genre=genre,
            style=style,
            tags=tags,
        )

    # ──────────────────────────────────────────────
    #  3. 列出所有大纲
    # ──────────────────────────────────────────────

    def list_outlines(self) -> List[Dict]:
        """列出当前 slot 所有大纲"""
        active = self._get_active_slot()
        if not active:
            return []

        proj = self._get_project_json()
        active_id = proj.get("active_outline", "")

        result = []
        for oid in self._list_outline_ids():
            data = self._read_outline_file(oid)
            if data:
                is_active = (oid == active_id)
                result.append({
                    "id": oid,
                    "title": data.get("title", ""),
                    "chapter_count": data.get("chapter_count", 0),
                    "volume_count": data.get("volume_count", 1),
                    "versions_count": len(data.get("outline_versions", [])),
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                    "active": is_active,
                    "genre": data.get("genre", ""),
                    "style": data.get("style", ""),
                    "tags": data.get("tags", []),
                })
        return result

    # ──────────────────────────────────────────────
    #  4. 当前大纲
    # ──────────────────────────────────────────────

    def current_outline(self) -> Optional[Dict]:
        """获取当前激活大纲"""
        active = self._get_active_slot()
        if not active:
            return None
        proj = self._get_project_json()
        oid = proj.get("active_outline")
        if not oid:
            return None
        data = self._read_outline_file(oid)
        if data:
            data["active"] = True
        return data

    # ──────────────────────────────────────────────
    #  5. 切换大纲
    # ──────────────────────────────────────────────

    def switch_outline(self, outline_id: str) -> Dict:
        """切换到指定大纲"""
        data = self._read_outline_file(outline_id)
        if not data:
            available = self._list_outline_ids()
            return {
                "status": "error",
                "message": f"大纲 {outline_id} 不存在",
                "available": available,
            }

        proj = self._get_project_json()
        old_id = proj.get("active_outline", "")
        proj["active_outline"] = outline_id
        proj["updated_at"] = datetime.now().isoformat()
        self._save_project_json(proj)

        return {
            "status": "ok",
            "outline_id": outline_id,
            "title": data.get("title", ""),
            "previous": old_id,
        }

    # ──────────────────────────────────────────────
    #  6. 对比两个大纲
    # ──────────────────────────────────────────────

    def diff_outlines(self, id1: str, id2: str) -> Dict:
        """对比两个已存储的大纲，调用相似度引擎"""
        d1 = self._read_outline_file(id1)
        d2 = self._read_outline_file(id2)

        if not d1:
            return {"status": "error", "message": f"大纲 {id1} 不存在"}
        if not d2:
            return {"status": "error", "message": f"大纲 {id2} 不存在"}

        from scripts.outline.similarity import OutlineSimilarity

        sim = OutlineSimilarity()
        result = sim.compare(
            title1=d1.get("title", ""),
            title2=d2.get("title", ""),
            content1=d1.get("content", ""),
            content2=d2.get("content", ""),
            genre1=d1.get("genre", ""),
            genre2=d2.get("genre", ""),
            style1=d1.get("style", ""),
            style2=d2.get("style", ""),
        )

        result["outline1"] = {"id": id1, "title": d1.get("title", "")}
        result["outline2"] = {"id": id2, "title": d2.get("title", "")}

        return result

    # ──────────────────────────────────────────────
    #  7. 回滚大纲到上一版本
    # ──────────────────────────────────────────────

    def rollback_outline(self, outline_id: str) -> Dict:
        """回滚大纲到上一个版本"""
        data = self._read_outline_file(outline_id)
        if not data:
            return {"status": "error", "message": f"大纲 {outline_id} 不存在"}

        versions = data.get("outline_versions", [])
        if len(versions) < 1:
            return {
                "status": "error",
                "message": f"大纲「{data.get('title', outline_id)}」没有可回滚的历史版本",
                "versions_count": 0,
            }

        # 取最后一个版本
        prev = versions.pop()
        old_title = data.get("title", "")
        old_content = data.get("content", "")

        # 恢复
        data["title"] = prev.get("title", old_title)
        data["content"] = prev.get("content", old_content)
        data["tags"] = prev.get("tags", data.get("tags", []))
        data["genre"] = prev.get("genre", data.get("genre", ""))
        data["style"] = prev.get("style", data.get("style", ""))
        data["chapter_count"] = prev.get("chapter_count", data.get("chapter_count", 0))
        data["volume_count"] = prev.get("volume_count", data.get("volume_count", 1))
        data["updated_at"] = datetime.now().isoformat()
        data["versions_count"] = len(versions)
        # 版本列表已移除最后一个
        data["outline_versions"] = versions

        self._write_outline_file(outline_id, data)

        return {
            "status": "ok",
            "outline_id": outline_id,
            "title": data["title"],
            "rolled_back_to": f"v{prev.get('version', '?')}",
            "saved_at": prev.get("saved_at", ""),
            "versions_remaining": len(versions),
        }

    # ──────────────────────────────────────────────
    #  8. 删除大纲
    # ──────────────────────────────────────────────

    def delete_outline(self, outline_id: str) -> Dict:
        """删除指定大纲"""
        data = self._read_outline_file(outline_id)
        if not data:
            return {"status": "error", "message": f"大纲 {outline_id} 不存在"}

        # 检查是否是当前激活大纲
        proj = self._get_project_json()
        active_id = proj.get("active_outline")

        self._delete_outline_file(outline_id)

        # 如果删除的是当前激活大纲，重置 active_outline
        if active_id == outline_id:
            remaining = self._list_outline_ids()
            next_active = remaining[0] if remaining else None
            proj["active_outline"] = next_active
            proj["updated_at"] = datetime.now().isoformat()
            self._save_project_json(proj)
            return {
                "status": "ok",
                "outline_id": outline_id,
                "title": data.get("title", ""),
                "deleted": True,
                "new_active": next_active,
            }

        return {
            "status": "ok",
            "outline_id": outline_id,
            "title": data.get("title", ""),
            "deleted": True,
        }

    # ──────────────────────────────────────────────
    #  9. 与文件对比
    # ──────────────────────────────────────────────

    def compare_with_file(self, file_path: str) -> Dict:
        """将当前激活大纲与外部文件对比"""
        fp = Path(file_path)
        if not fp.exists():
            return {"status": "error", "message": f"文件不存在: {file_path}"}

        current = self.current_outline()
        if not current:
            return {"status": "error", "message": "当前没有激活的大纲。请先添加大纲。"}

        file_content = fp.read_text(encoding="utf-8")

        from scripts.outline.similarity import OutlineSimilarity

        sim = OutlineSimilarity()
        result = sim.compare(
            title1=current.get("title", ""),
            title2=fp.stem,
            content1=current.get("content", ""),
            content2=file_content,
            genre1=current.get("genre", ""),
            genre2="",
            style1=current.get("style", ""),
            style2="",
        )

        result["outline1"] = {"id": current.get("id", ""), "title": current.get("title", "")}
        result["outline2"] = {"file": str(fp), "title": fp.stem}

        return result

    # ──────────────────────────────────────────────
    #  10. 检查是否有激活大纲
    # ──────────────────────────────────────────────

    def has_active_outline(self) -> bool:
        """检查当前 slot 是否有激活的大纲"""
        current = self.current_outline()
        return current is not None

    # ──────────────────────────────────────────────
    #  11. 更新大纲内容（带版本快照）
    # ──────────────────────────────────────────────

    def update_outline(self, outline_id: str, new_content: str,
                       title: str = "", genre: str = "", style: str = "",
                       tags: list = None) -> Dict:
        """更新大纲，自动创建版本快照"""
        old = self._read_outline_file(outline_id)
        if not old:
            return {"status": "error", "message": f"大纲 {outline_id} 不存在"}

        # 创建版本快照
        versions = self._snapshot_version(old)

        # 更新
        old["content"] = new_content
        old["tags"] = tags or old.get("tags", [])
        old["genre"] = genre or old.get("genre", "")
        old["style"] = style or old.get("style", "")
        if title:
            old["title"] = title
        old["outline_versions"] = versions
        old["versions_count"] = len(versions)
        old["updated_at"] = datetime.now().isoformat()

        # 重算章节数
        chapter_count = 0
        for line in new_content.split("\n"):
            if "第" in line and "章" in line:
                chapter_count += 1
        old["chapter_count"] = chapter_count

        self._write_outline_file(outline_id, old)

        return {
            "status": "ok",
            "outline_id": outline_id,
            "title": old["title"],
            "chapter_count": chapter_count,
            "versions_count": len(versions),
        }

    # ──────────────────────────────────────────────
    #  12. 分类大纲：升级/同作/新作/需确认
    # ──────────────────────────────────────────────

    def classify_outline(self, outline_id: str) -> Dict:
        """获取大纲的分类信息"""
        data = self._read_outline_file(outline_id)
        if not data:
            return {"status": "error", "message": f"大纲 {outline_id} 不存在"}

        sc = data.get("similarity_check", None)

        info = {
            "id": outline_id,
            "title": data.get("title", ""),
            "genre": data.get("genre", ""),
            "style": data.get("style", ""),
            "chapter_count": data.get("chapter_count", 0),
            "volume_count": data.get("volume_count", 1),
            "created_at": data.get("created_at", ""),
            "versions_count": len(data.get("outline_versions", [])),
        }

        if sc:
            info["classification"] = sc.get("classification", "未知")
            info["similarity_score"] = sc.get("similarity_score", 0)
            info["recommendation"] = sc.get("recommendation", "未知")
            info["detail"] = sc.get("detail", {})

        return info
