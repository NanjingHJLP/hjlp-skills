import json
import os
import subprocess
import sys
from pathlib import Path


def _resolve_cli(name: str):
    """Resolve installed CLI command; falls back to python -m for dev."""
    import shutil
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = name.replace("cli-anything-", "cli_anything.") + "." + name.split("-")[-1] + "_cli"
    return [sys.executable, "-m", module]


class TestCLIFullE2E:
    CLI_BASE = _resolve_cli("cli-anything-softwaremove")

    def _run(self, args, check=True):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True,
            text=True,
            check=check,
        )

    def test_move_and_undo(self, tmp_path: Path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        history_path = tmp_path / "history.json"
        src.mkdir()
        (src / "file.txt").write_text("hello", encoding="utf-8")

        move_result = self._run(
            [
                "--json",
                "--history-path",
                str(history_path),
                "move",
                "start",
                "--source",
                str(src),
                "--target",
                str(dst),
                "--link-mode",
                "none",
                "--yes",
            ]
        )
        data = json.loads(move_result.stdout)
        assert data["ok"] is True
        assert (dst / "file.txt").exists()

        undo_result = self._run(
            [
                "--json",
                "--history-path",
                str(history_path),
                "history",
                "undo",
            ]
        )
        undo_data = json.loads(undo_result.stdout)
        assert undo_data["ok"] is True
        assert (src / "file.txt").exists()

    def test_history_list_json(self, tmp_path: Path):
        history_path = tmp_path / "history.json"
        result = self._run(["--json", "--history-path", str(history_path), "history", "list"])
        data = json.loads(result.stdout)
        assert isinstance(data, list)
