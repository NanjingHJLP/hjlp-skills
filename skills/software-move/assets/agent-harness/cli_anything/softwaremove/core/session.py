"""Session state management with safe JSON writes."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

DEFAULT_SESSION = {
    "last_disk": None,
    "last_scan": [],
    "last_target": None,
}


def default_session_path() -> str:
    base = Path.home() / ".cli-anything-softwaremove"
    return str(base / "session.json")


def _json_default(obj: Any) -> str:
    """Handle non-serializable objects during JSON dump."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')


def _locked_save_json(path: str, data: Dict[str, Any], **dump_kwargs) -> None:
    try:
        f = open(path, "r+", encoding="utf-8")
    except FileNotFoundError:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        f = open(path, "w", encoding="utf-8")
    with f:
        locked = False
        try:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            locked = True
        except (ImportError, OSError):
            pass
        try:
            f.seek(0)
            f.truncate()
            json.dump(data, f, ensure_ascii=False, indent=2, default=_json_default, **dump_kwargs)
            f.flush()
        finally:
            if locked:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def load_session(path: str | None = None) -> Dict[str, Any]:
    path = path or default_session_path()
    if not os.path.exists(path):
        return dict(DEFAULT_SESSION)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return dict(DEFAULT_SESSION)
    merged = dict(DEFAULT_SESSION)
    merged.update(data)
    return merged


def save_session(data: Dict[str, Any], path: str | None = None) -> str:
    path = path or default_session_path()
    _locked_save_json(path, data)
    return path
