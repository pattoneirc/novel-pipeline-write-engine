#!/usr/bin/env python3
"""
slot_manager.py — DB Slot 生命周期管理 v0.6.5

管理单个 DB slot 的目录结构、创建、删除、备份和恢复。
支持自动创建 slot_004 当已有 3 个满 slot 时。
"""
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

from scripts.db.registry import Registry


# Standard slot subdirectory structure
SLOT_SUBDIRS = ["outlines", "chapters", "reports", "exports", "backups"]


class SlotManager:
    """Manages the lifecycle of individual DB slots."""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.workspace_dir = self.project_root / "workspace"
        self.registry = Registry(project_root)

    def get_slot_dir(self, slot_id: str) -> Path:
        """Get the directory path for a slot."""
        return self.workspace_dir / slot_id

    def slot_exists(self, slot_id: str) -> bool:
        """Check if a slot directory exists."""
        return self.get_slot_dir(slot_id).exists()

    def init_workspace(self, force: bool = False) -> Dict:
        """
        Initialize the workspace with registry and 3 default slots.
        Returns a status dict.
        """
        result = {"status": "ok", "created": [], "message": ""}

        if self.registry.exists() and not force:
            result["status"] = "already_initialized"
            result["message"] = "workspace/ 已经初始化"
            return result

        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Initialize registry
        registry_data = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "active_slot": "slot_001",
            "slots": [
                {
                    "id": "slot_001",
                    "name": "默认工作区",
                    "description": "默认项目工作区",
                    "status": "active",
                    "created_at": datetime.now().isoformat(),
                    "project_count": 0,
                }
            ],
        }
        self.registry.save(registry_data)
        result["created"].append("registry.json")

        # Create 3 initial slots
        for i in range(1, 4):
            slot_id = f"slot_{i:03d}"
            created = self.create_slot(slot_id, ensure_registry=(i == 1))
            result["created"].append(slot_id)

        result["message"] = f"workspace 初始化完成，创建了 {len(result['created'])-1} 个 slot"
        return result

    def create_slot(self, slot_id: str, ensure_registry: bool = True,
                    name: str = "", description: str = "") -> Dict:
        """
        Create a new slot directory and its structure.
        Returns dict with slot info.
        """
        slot_dir = self.get_slot_dir(slot_id)
        slot_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        for subdir in SLOT_SUBDIRS:
            (slot_dir / subdir).mkdir(parents=True, exist_ok=True)

        # Create project.json
        slot_name = name or slot_id.replace("_", " ").title()
        proj_data = {
            "name": slot_name,
            "title": slot_name,
            "active_outline": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        proj_file = slot_dir / "project.json"
        proj_file.write_text(
            json.dumps(proj_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # Add to registry
        if ensure_registry:
            self.registry.add_slot(
                slot_id=slot_id,
                name=slot_name,
                description=description,
                status="active",
                project_count=1,
            )

        return {
            "id": slot_id,
            "name": slot_name,
            "dir": str(slot_dir),
            "created": True,
        }

    def create_slot_auto(self, name: str, description: str = "") -> Dict:
        """
        Auto-create a new slot with auto-generated ID.
        Auto-creates slot_004 when 3 slots exist but slot_004 is missing.
        """
        slots = self.registry.list_slots()
        slot_count = len(slots)

        # Auto-create slot_004 if needed (when 3 full slots exist)
        if slot_count >= 3:
            existing_ids = {s.get("id") for s in slots}
            # Ensure slots 1-3 exist if count >= 3
            for i in range(1, 4):
                sid = f"slot_{i:03d}"
                if sid not in existing_ids and not self.slot_exists(sid):
                    self.create_slot(sid)

        slot_id = self.registry.get_next_slot_id()
        return self.create_slot(slot_id, ensure_registry=True,
                                name=name, description=description)

    def delete_slot(self, slot_id: str) -> Dict:
        """
        Delete a slot (directory + registry entry).
        Protected: won't delete slot_001 or the active slot.
        """
        result = {"status": "ok", "message": ""}

        active = self.registry.get_active_slot()
        if slot_id == active:
            result["status"] = "error"
            result["message"] = f"不能删除当前活跃的 slot ({slot_id})"
            return result

        if slot_id == "slot_001":
            result["status"] = "error"
            result["message"] = "slot_001 是默认工作区，不能删除"
            return result

        # Remove from registry
        removed = self.registry.remove_slot(slot_id)

        # Remove directory
        slot_dir = self.get_slot_dir(slot_id)
        if slot_dir.exists():
            shutil.rmtree(slot_dir)
            result["message"] = f"Slot {slot_id} 已删除（目录和注册表）"
            result["removed_dir"] = True
        else:
            result["message"] = f"Slot {slot_id} 已从注册表移除（目录不存在）"
            result["removed_dir"] = False

        result["removed_registry"] = removed
        return result

    def backup_slot(self, slot_id: Optional[str] = None) -> Dict:
        """
        Backup a slot's project.json to its backup directory.
        Returns dict with backup info.
        """
        active = slot_id or self.registry.get_active_slot()
        if not active:
            return {"status": "error", "message": "无活跃 slot"}

        slot_dir = self.get_slot_dir(active)
        proj_file = slot_dir / "project.json"
        backup_dir = slot_dir / "backups"

        if not proj_file.exists():
            # Create project.json if missing
            self.create_slot(active)
            proj_file = slot_dir / "project.json"

        backup_dir.mkdir(parents=True, exist_ok=True)

        proj = json.loads(proj_file.read_text(encoding="utf-8"))
        proj["backed_up_at"] = datetime.now().isoformat()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"backup_{timestamp}.json"
        backup_file.write_text(
            json.dumps(proj, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        return {
            "status": "ok",
            "slot_id": active,
            "backup_file": str(backup_file),
            "timestamp": timestamp,
        }

    def restore_slot(self, slot_id: str, backup_id: Optional[str] = None) -> Dict:
        """
        Restore a slot's project.json from backup.
        Returns dict with restore info.
        """
        slot_dir = self.get_slot_dir(slot_id)
        backup_dir = slot_dir / "backups"

        if not backup_dir.exists():
            return {"status": "error", "message": f"{slot_id} 没有备份目录"}

        backups = sorted(backup_dir.glob("backup_*.json"), reverse=True)
        if not backups:
            return {"status": "error", "message": f"{slot_id} 没有可用的备份文件"}

        # Find target backup
        target = backups[0]  # Default: latest
        if backup_id:
            found = [b for b in backups if backup_id in b.name]
            if not found:
                return {
                    "status": "error",
                    "message": f"未找到备份 {backup_id}",
                    "available": [b.name for b in backups],
                }
            target = found[0]

        # Restore
        backup_data = json.loads(target.read_text(encoding="utf-8"))
        proj_file = slot_dir / "project.json"
        proj_file.write_text(
            json.dumps(backup_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # Update registry
        self.registry.update_slot_status(slot_id, "active")
        self.registry.add_slot(
            slot_id=slot_id,
            name=backup_data.get("name", backup_data.get("title", slot_id)),
            description=backup_data.get("description", ""),
            status="active",
        )

        return {
            "status": "ok",
            "slot_id": slot_id,
            "restored_from": target.name,
            "backup_time": datetime.fromtimestamp(
                target.stat().st_mtime
            ).strftime("%Y-%m-%d %H:%M"),
        }

    def ensure_slot_004(self) -> Optional[str]:
        """
        Ensure slot_004 exists when 3 slots are present.
        Auto-creates it if missing. Returns slot_id or None.
        """
        slots = self.registry.list_slots()
        if len(slots) >= 3:
            existing_ids = {s.get("id") for s in slots}
            if "slot_004" not in existing_ids and not self.slot_exists("slot_004"):
                result = self.create_slot("slot_004", ensure_registry=True,
                                          name="工作区 4")
                return result.get("id")
        return None

    def switch_to(self, slot_id: str) -> Dict:
        """
        Switch the active slot. Auto-registers if directory exists but not in registry.
        """
        slot_dir = self.get_slot_dir(slot_id)

        if not slot_dir.exists():
            return {
                "status": "error",
                "message": f"Slot {slot_id} 不存在",
                "available": [s.get("id") for s in self.registry.list_slots()],
            }

        # Auto-register if missing
        if not self.registry.get_slot(slot_id):
            self.registry.add_slot(slot_id, slot_id)

        old = self.registry.get_active_slot()
        self.registry.set_active_slot(slot_id)

        result = {"status": "ok", "slot_id": slot_id, "previous": old}

        # Load project info
        proj_file = slot_dir / "project.json"
        if proj_file.exists():
            proj = json.loads(proj_file.read_text(encoding="utf-8"))
            result["project"] = {
                "title": proj.get("title", proj.get("name", slot_id)),
                "outline": proj.get("active_outline", ""),
            }

        return result
