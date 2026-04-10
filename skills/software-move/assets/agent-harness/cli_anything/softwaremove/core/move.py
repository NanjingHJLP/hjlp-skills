"""Move and restore operations."""
from __future__ import annotations

from typing import Dict, Optional

from cli_anything.softwaremove.core import history
from cli_anything.softwaremove.utils.softwaremove_backend import move_software, restore_software


def move(
    source_path: str,
    target_path: str,
    software_name: str,
    software_size: int,
    link_mode: str = "auto",
    history_path: Optional[str] = None,
    record_history: bool = True,
) -> Dict:
    result = move_software(
        source_path=source_path,
        target_path=target_path,
        software_name=software_name,
        software_size=software_size,
        link_mode=link_mode,
    )
    if record_history and result.get("ok"):
        record = history.add_record(
            software_name=software_name,
            source_path=source_path,
            target_path=result["target_path"],
            software_size=software_size,
            path=history_path,
        )
        result["history_record"] = record
    return result


def restore(record_id: int, history_path: Optional[str] = None) -> Dict:
    record = history.get_record(record_id, history_path)
    if not record:
        return {"ok": False, "error": f"record {record_id} not found"}
    result = restore_software(
        source_path=record["target_path"],
        target_path=record["source_path"],
        software_name=record["software_name"],
    )
    if result.get("ok"):
        history.mark_restored(record_id, history_path)
    return result


def redo(record_id: int, history_path: Optional[str] = None, link_mode: str = "auto") -> Dict:
    record = history.get_record(record_id, history_path)
    if not record:
        return {"ok": False, "error": f"record {record_id} not found"}
    result = move_software(
        source_path=record["source_path"],
        target_path=record["target_path"],
        software_name=record["software_name"],
        software_size=record.get("software_size", 0),
        link_mode=link_mode,
    )
    if result.get("ok"):
        history.add_record(
            software_name=record["software_name"],
            source_path=record["source_path"],
            target_path=result["target_path"],
            software_size=record.get("software_size", 0),
            path=history_path,
        )
    return result
