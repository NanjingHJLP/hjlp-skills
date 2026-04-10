"""Move history storage."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def default_history_path() -> str:
    base = Path.home() / ".cli-anything-softwaremove"
    return str(base / "move_history.json")


def _load(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        return []
    return []


def _save(path: str, history: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def load_history(path: Optional[str] = None) -> List[Dict[str, Any]]:
    path = path or default_history_path()
    history = _load(path)
    history.sort(key=lambda x: x.get("move_timestamp", 0), reverse=True)
    return history


def add_record(
    software_name: str,
    source_path: str,
    target_path: str,
    software_size: int,
    path: Optional[str] = None,
    move_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    path = path or default_history_path()
    history = load_history(path)
    if move_time is None:
        move_time = datetime.now()
    new_record = {
        "id": (max([r.get("id", 0) for r in history]) + 1) if history else 1,
        "software_name": software_name,
        "source_path": source_path,
        "target_path": target_path,
        "software_size": software_size,
        "move_time": move_time.strftime("%Y-%m-%d %H:%M:%S"),
        "move_timestamp": move_time.timestamp(),
        "restored": False,
    }
    history.append(new_record)
    _save(path, history)
    return new_record


def mark_restored(record_id: int, path: Optional[str] = None) -> bool:
    path = path or default_history_path()
    history = load_history(path)
    updated = False
    for record in history:
        if record.get("id") == record_id:
            record["restored"] = True
            record["restore_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updated = True
            break
    if updated:
        _save(path, history)
    return updated


def delete_record(record_id: int, path: Optional[str] = None) -> bool:
    path = path or default_history_path()
    history = load_history(path)
    new_history = [r for r in history if r.get("id") != record_id]
    if len(new_history) == len(history):
        return False
    _save(path, new_history)
    return True


def get_record(record_id: int, path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    history = load_history(path)
    for record in history:
        if record.get("id") == record_id:
            return record
    return None


def latest_record(path: Optional[str] = None, restored: Optional[bool] = None) -> Optional[Dict[str, Any]]:
    history = load_history(path)
    for record in history:
        if restored is None or record.get("restored") is restored:
            return record
    return None
