"""Session state management with safe atomic JSON writes."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

DEFAULT_SESSION = {
    "last_disk": None,
    "last_scan": [],
    "last_target": None,
}


def default_session_path() -> str:
    base = Path.home() / ".softwaremove"
    return str(base / "session.json")


def _json_default(obj: Any) -> str:
    """Handle non-serializable objects during JSON dump."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')


def _atomic_save_json(path: str, data: Dict[str, Any], **dump_kwargs) -> None:
    """Write JSON atomically using temp file + os.replace for cross-platform safety."""
    abs_path = os.path.abspath(path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    dir_name = os.path.dirname(abs_path)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=_json_default, **dump_kwargs)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, abs_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def load_session(path: str | None = None) -> Dict[str, Any]:
    path = path or default_session_path()
    if not os.path.exists(path):
        return dict(DEFAULT_SESSION)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_SESSION)
    merged = dict(DEFAULT_SESSION)
    merged.update(data)
    return merged


def save_session(data: Dict[str, Any], path: str | None = None) -> str:
    path = path or default_session_path()
    _atomic_save_json(path, data)
    return path
