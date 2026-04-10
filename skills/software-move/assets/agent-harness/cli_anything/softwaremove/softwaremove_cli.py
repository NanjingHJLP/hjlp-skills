"""cli-anything-softwaremove - CLI harness for SoftwareMove."""
from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

import click

from cli_anything.softwaremove.core import disk as disk_core
from cli_anything.softwaremove.core import history as history_core
from cli_anything.softwaremove.core import move as move_core
from cli_anything.softwaremove.core import scan as scan_core
from cli_anything.softwaremove.core import session as session_core
from cli_anything.softwaremove.utils.softwaremove_backend import check_software_moveable, format_size, get_directory_size
from cli_anything.softwaremove.utils.repl_skin import ReplSkin

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def output(data, as_json: bool) -> None:
    if as_json:
        click.echo(json.dumps(data, indent=2, default=str))
    elif isinstance(data, dict):
        for k, v in data.items():
            click.echo(f"{k}: {v}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                click.echo(json.dumps(item, default=str))
            else:
                click.echo(str(item))
    else:
        click.echo(str(data))


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON")
@click.option("--history-path", default=None, type=click.Path(), help="Custom history file path")
@click.option("--session", "session_path", default=None, type=click.Path(), help="Custom session file path")
@click.pass_context
def cli(ctx: click.Context, as_json: bool, history_path: str | None, session_path: str | None):
    """cli-anything-softwaremove - move installed software between disks."""
    ctx.ensure_object(dict)
    session_path = session_path or session_core.default_session_path()
    session = session_core.load_session(session_path)
    ctx.obj.update(
        {
            "as_json": as_json,
            "history_path": history_path,
            "session_path": session_path,
            "session": session,
        }
    )
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


def main():
    cli(obj={})


@cli.command(hidden=True)
@click.pass_context
def repl(ctx: click.Context):
    """Interactive REPL mode."""
    skin = ReplSkin("softwaremove", version="1.0.0")
    skin.print_banner()

    pt_session = skin.create_prompt_session()
    while True:
        try:
            line = skin.get_input(pt_session, project_name="softwaremove")
        except (EOFError, KeyboardInterrupt):
            break

        line = line.strip()
        if not line:
            continue
        if line in ("exit", "quit"):
            break
        if line == "help":
            skin.help({
                "disk list/info": "Disk discovery and stats",
                "scan disk/installed": "Scan installed software",
                "move start": "Move software to a new location",
                "history list/show/restore/undo/redo": "Move history and recovery",
            })
            continue

        try:
            args = shlex.split(line)
            cli.main(args=args, obj=dict(ctx.obj), standalone_mode=False)
        except click.exceptions.UsageError as e:
            skin.error(str(e))
        except RuntimeError as e:
            skin.error(str(e))
        except SystemExit:
            pass
        except Exception as e:
            skin.error(f"Unexpected error: {e}")

    skin.print_goodbye()


# ---------------------------------------------------------------------------
# Disk
# ---------------------------------------------------------------------------

@cli.group()
@click.pass_context
def disk(ctx: click.Context):
    """Disk utilities."""


@disk.command("list")
@click.pass_context
def disk_list(ctx: click.Context):
    """List disks available on this machine."""
    disks = disk_core.list_disks()
    output(disks, ctx.obj["as_json"])


@disk.command("info")
@click.argument("letter")
@click.pass_context
def disk_info(ctx: click.Context, letter: str):
    """Show disk usage for a drive letter."""
    info = disk_core.disk_info(letter.upper())
    info_fmt = {
        "letter": letter.upper(),
        "total": info["total"],
        "used": info["used"],
        "free": info["free"],
        "total_str": format_size(info["total"]),
        "used_str": format_size(info["used"]),
        "free_str": format_size(info["free"]),
    }
    output(info_fmt, ctx.obj["as_json"])


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

@cli.group()
@click.pass_context
def scan(ctx: click.Context):
    """Scan installed software."""


@scan.command("disk")
@click.argument("letter")
@click.pass_context
def scan_disk(ctx: click.Context, letter: str):
    """Scan installed software on a disk."""
    items = scan_core.scan_disk(letter.upper())
    session = ctx.obj["session"]
    session["last_disk"] = letter.upper()
    session["last_scan"] = items
    session_core.save_session(session, ctx.obj["session_path"])
    output(items, ctx.obj["as_json"])


@scan.command("installed")
@click.pass_context
def scan_installed(ctx: click.Context):
    """List installed software from registry."""
    items = scan_core.scan_installed()
    output(items, ctx.obj["as_json"])


# ---------------------------------------------------------------------------
# Move
# ---------------------------------------------------------------------------

@cli.group()
@click.pass_context
def move(ctx: click.Context):
    """Move software directories."""


@move.command("start")
@click.option("--source", "source_path", required=True, type=click.Path(), help="Source install path")
@click.option("--target", "target_path", required=True, type=click.Path(), help="Target path")
@click.option("--name", "software_name", default=None, help="Software name for history")
@click.option("--size", "software_size", default=None, type=int, help="Software size in bytes")
@click.option(
    "--link-mode",
    type=click.Choice(["auto", "symlink", "junction", "none"], case_sensitive=False),
    default="auto",
    show_default=True,
    help="Link mode after move",
)
@click.option("--no-record", is_flag=True, default=False, help="Skip history recording")
@click.option("--yes", is_flag=True, default=False, help="Skip confirmation prompt")
@click.pass_context
def move_start(
    ctx: click.Context,
    source_path: str,
    target_path: str,
    software_name: str | None,
    software_size: int | None,
    link_mode: str,
    no_record: bool,
    yes: bool,
):
    """Move a software directory to a new location."""
    as_json = ctx.obj["as_json"]
    if not as_json and not yes:
        if not click.confirm(f"Move {source_path} -> {target_path}?", default=False):
            output({"ok": False, "error": "user cancelled"}, as_json)
            return

    if software_name is None:
        software_name = Path(source_path).name
    if software_size is None:
        software_size = get_directory_size(source_path)

    result = move_core.move(
        source_path=source_path,
        target_path=target_path,
        software_name=software_name,
        software_size=software_size,
        link_mode=link_mode,
        history_path=ctx.obj["history_path"],
        record_history=not no_record,
    )
    output(result, as_json)


@move.command("check")
@click.option("--source", "source_path", required=True, type=click.Path(), help="Source install path")
@click.option("--name", "software_name", default=None, help="Software name")
@click.pass_context
def move_check(ctx: click.Context, source_path: str, software_name: str | None):
    """Check if software can be safely moved (UWP, registry refs, locked files)."""
    as_json = ctx.obj["as_json"]
    if software_name is None:
        software_name = Path(source_path).name
    result = check_software_moveable(source_path, software_name)
    output(result, as_json)


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

@cli.group()
@click.pass_context
def history(ctx: click.Context):
    """Move history operations."""


@history.command("list")
@click.pass_context
def history_list(ctx: click.Context):
    """List move history."""
    records = history_core.load_history(ctx.obj["history_path"])
    output(records, ctx.obj["as_json"])


@history.command("show")
@click.option("--id", "record_id", required=True, type=int)
@click.pass_context
def history_show(ctx: click.Context, record_id: int):
    """Show a single history record."""
    record = history_core.get_record(record_id, ctx.obj["history_path"])
    if not record:
        output({"ok": False, "error": f"record {record_id} not found"}, ctx.obj["as_json"])
        return
    output(record, ctx.obj["as_json"])


@history.command("restore")
@click.option("--id", "record_id", required=True, type=int)
@click.pass_context
def history_restore(ctx: click.Context, record_id: int):
    """Restore a moved software directory by record id."""
    result = move_core.restore(record_id, ctx.obj["history_path"])
    output(result, ctx.obj["as_json"])


@history.command("undo")
@click.pass_context
def history_undo(ctx: click.Context):
    """Restore the latest non-restored record."""
    record = history_core.latest_record(ctx.obj["history_path"], restored=False)
    if not record:
        output({"ok": False, "error": "no active records"}, ctx.obj["as_json"])
        return
    result = move_core.restore(record["id"], ctx.obj["history_path"])
    output(result, ctx.obj["as_json"])


@history.command("redo")
@click.option("--id", "record_id", required=False, type=int)
@click.option(
    "--link-mode",
    type=click.Choice(["auto", "symlink", "junction", "none"], case_sensitive=False),
    default="auto",
    show_default=True,
)
@click.pass_context
def history_redo(ctx: click.Context, record_id: int | None, link_mode: str):
    """Re-run a move based on a restored record."""
    if record_id is None:
        record = history_core.latest_record(ctx.obj["history_path"], restored=True)
        if not record:
            output({"ok": False, "error": "no restored records"}, ctx.obj["as_json"])
            return
        record_id = record["id"]
    result = move_core.redo(record_id, ctx.obj["history_path"], link_mode=link_mode)
    output(result, ctx.obj["as_json"])


@history.command("delete")
@click.option("--id", "record_id", required=True, type=int)
@click.pass_context
def history_delete(ctx: click.Context, record_id: int):
    """Delete a history record."""
    ok = history_core.delete_record(record_id, ctx.obj["history_path"])
    output({"ok": ok, "id": record_id}, ctx.obj["as_json"])
