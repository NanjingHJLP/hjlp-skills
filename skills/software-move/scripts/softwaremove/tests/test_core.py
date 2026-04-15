import json
import os
from pathlib import Path

from softwaremove.core import history
from softwaremove.utils import softwaremove_backend as backend


def test_format_size():
    assert backend.format_size(0) == "0B"
    assert backend.format_size(1024).endswith("KB")
    assert backend.format_size(1024 * 1024).endswith("MB")


def test_history_roundtrip(tmp_path: Path):
    history_path = tmp_path / "history.json"
    record = history.add_record(
        software_name="TestApp",
        source_path=str(tmp_path / "src"),
        target_path=str(tmp_path / "dst"),
        software_size=123,
        path=str(history_path),
    )
    assert record["id"] == 1

    loaded = history.load_history(str(history_path))
    assert len(loaded) == 1
    assert loaded[0]["software_name"] == "TestApp"

    assert history.mark_restored(1, str(history_path))
    updated = history.get_record(1, str(history_path))
    assert updated and updated.get("restored") is True

    assert history.delete_record(1, str(history_path))
    assert history.load_history(str(history_path)) == []


def test_move_software_link_none(tmp_path: Path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    (src / "file.txt").write_text("hello", encoding="utf-8")

    result = backend.move_software(
        source_path=str(src),
        target_path=str(dst),
        software_name="TestApp",
        software_size=5,
        link_mode="none",
    )
    assert result["ok"] is True
    assert (dst / "file.txt").exists()
