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


def test_history_redo_tracking(tmp_path: Path):
    history_path = tmp_path / "history.json"
    record = history.add_record(
        software_name="TestApp",
        source_path=str(tmp_path / "src"),
        target_path=str(tmp_path / "dst"),
        software_size=123,
        path=str(history_path),
    )
    assert record["id"] == 1

    assert history.mark_redone(1, 2, path=str(history_path))
    updated = history.get_record(1, str(history_path))
    assert updated and updated.get("redone") is True
    assert updated.get("superseded_by") == 2


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


def test_move_software_fails_if_target_exists(tmp_path: Path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    (src / "file.txt").write_text("hello", encoding="utf-8")
    (dst / "existing.txt").write_text("keep", encoding="utf-8")

    result = backend.move_software(
        source_path=str(src),
        target_path=str(dst),
        software_name="TestApp",
        software_size=5,
        link_mode="none",
    )

    assert result["ok"] is False
    assert "Target path already exists" in result["error"]
    assert (src / "file.txt").exists()
    assert (dst / "existing.txt").exists()
    assert not (dst / "file.txt").exists()


def test_verify_move_success(tmp_path: Path):
    from softwaremove.utils.softwaremove_backend import verify_move
    import shutil
    import subprocess

    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    (src / "file.txt").write_text("hello", encoding="utf-8")

    # Target does not exist yet
    result = verify_move(str(src), str(dst))
    assert result["ok"] is False
    assert "does not exist" in result["errors"][0]

    # Simulate a move by removing source and creating a junction
    shutil.copytree(src, dst)
    shutil.rmtree(src)
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(src), str(dst)],
        capture_output=True,
    )
    assert src.exists() and dst.exists()

    result = verify_move(str(src), str(dst))
    assert result["ok"] is True
    assert result["target_exists"] is True
    assert result["is_link"] is True
    assert result["target_size"] > 0

    # Simulate link_mode=none (source removed, no junction)
    os.remove(src)
    result = verify_move(str(src), str(dst))
    assert result["ok"] is True
    assert result["target_exists"] is True
    assert result["is_link"] is False


def test_verify_move_detects_empty_target(tmp_path: Path):
    from softwaremove.utils.softwaremove_backend import verify_move
    import shutil

    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    shutil.rmtree(src)
    dst.mkdir()

    result = verify_move(str(src), str(dst), expected_size=1)
    assert result["ok"] is False
    assert "empty after move" in result["errors"][0]


def test_rollback_cleans_partial_target(tmp_path: Path):
    """If a cross-device move partially copies a file then fails, rollback must remove it."""
    import shutil
    from softwaremove.utils.softwaremove_backend import _Mover

    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    (src / "a.txt").write_text("A", encoding="utf-8")
    (src / "b.txt").write_text("B", encoding="utf-8")

    mover = _Mover(
        source_path=str(src),
        target_path=str(dst),
        software_name="TestApp",
        software_size=10,
        link_mode="none",
        progress_cb=None,
        log_cb=None,
    )

    # Simulate one tracked successful move
    dst.mkdir(exist_ok=True)
    shutil.move(str(src / "a.txt"), str(dst / "a.txt"))
    mover.moved_files.append((str(src / "a.txt"), str(dst / "a.txt")))
    mover.rollback_needed = True

    # Simulate a "ghost" file that got copied but not tracked (cross-device partial failure)
    (dst / "ghost.txt").write_text("GHOST", encoding="utf-8")

    mover._rollback()

    # Source file should be restored
    assert (src / "a.txt").exists()
    # Target directory should be completely gone (no ghost left)
    assert not dst.exists()


def test_rollback_removes_broken_link_and_restores_files(tmp_path: Path):
    import shutil
    import subprocess
    from softwaremove.utils.softwaremove_backend import _Mover, is_link_or_junction

    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    (src / "file.txt").write_text("hello", encoding="utf-8")

    mover = _Mover(
        source_path=str(src),
        target_path=str(dst),
        software_name="TestApp",
        software_size=5,
        link_mode="junction",
        progress_cb=None,
        log_cb=None,
    )

    dst.mkdir(exist_ok=True)
    shutil.move(str(src / "file.txt"), str(dst / "file.txt"))
    mover.moved_files.append((str(src / "file.txt"), str(dst / "file.txt")))
    mover.rollback_needed = True

    shutil.rmtree(src)
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(src), str(dst)],
        capture_output=True,
    )
    assert is_link_or_junction(str(src))
    mover.link_created = True

    mover._rollback()

    assert (src / "file.txt").exists()
    assert not is_link_or_junction(str(src))
    assert not dst.exists()
