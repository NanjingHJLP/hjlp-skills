"""Move and restore operations."""
from __future__ import annotations

from typing import Callable, Dict, Optional

from softwaremove.core import history
from softwaremove.utils.softwaremove_backend import move_software, restore_software, verify_move

ProgressFn = Optional[Callable[[int, int, str], None]]


def move(
    source_path: str,
    target_path: str,
    software_name: str,
    software_size: int,
    link_mode: str = "auto",
    history_path: Optional[str] = None,
    record_history: bool = True,
    progress_cb: ProgressFn = None,
) -> Dict:
    result = move_software(
        source_path=source_path,
        target_path=target_path,
        software_name=software_name,
        software_size=software_size,
        link_mode=link_mode,
        progress_cb=progress_cb,
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
        new_record = history.add_record(
            software_name=record["software_name"],
            source_path=record["source_path"],
            target_path=result["target_path"],
            software_size=record.get("software_size", 0),
            path=history_path,
        )
        history.mark_redone(record_id, new_record["id"], path=history_path)
        result["history_record"] = new_record
    return result


def verify(source_path: str | None = None, target_path: str | None = None, record_id: int | None = None, history_path: Optional[str] = None) -> Dict:
    """Verify a completed move by paths or by history record id."""
    if record_id is not None:
        record = history.get_record(record_id, history_path)
        if not record:
            return {"ok": False, "error": f"record {record_id} not found"}
        source_path = record["source_path"]
        target_path = record["target_path"]

    if not source_path or not target_path:
        return {"ok": False, "error": "source_path and target_path are required"}

    return verify_move(source_path, target_path)
