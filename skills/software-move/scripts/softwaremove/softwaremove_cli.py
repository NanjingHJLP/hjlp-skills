"""softwaremove - CLI harness for SoftwareMove."""
from __future__ import annotations

import json
import os
import shlex
import sys
from pathlib import Path

import click

from softwaremove.core import disk as disk_core
from softwaremove.core import history as history_core
from softwaremove.core import move as move_core
from softwaremove.core import scan as scan_core
from softwaremove.core import session as session_core
from softwaremove.utils.softwaremove_backend import check_software_moveable, format_size, get_directory_size
from softwaremove.utils.repl_skin import ReplSkin

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def print_admin_status():
    """Print current admin status for user awareness."""
    if sys.platform == "win32":
        if is_admin():
            click.secho("[Administrator] ", fg="green", nl=False)
        else:
            click.secho("[User] ", fg="yellow", nl=False)


def is_admin() -> bool:
    """Check if running with administrator privileges on Windows."""
    if sys.platform != "win32":
        return True  # Non-Windows, assume admin
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def require_admin(reason: str = ""):
    """Restart the current script with admin privileges if not already running as admin.

    Args:
        reason: Reason for requiring admin privileges (shown to user)
    """
    if is_admin():
        return

    if sys.platform != "win32":
        return

    import ctypes

    if not reason:
        reason = "This operation requires administrator privileges to create junction links in system directories."

    click.secho(f"⚠️  {reason}", fg="yellow")
    click.echo("Requesting administrator privileges...")

    script = sys.argv[0]
    # pip entry_points on Windows generate an .exe wrapper; sys.argv[0] is the exe.
    # For .py scripts we must run them via python.exe; for exe wrappers we run directly.
    is_python_script = script.endswith(".py") or script.endswith(".pyw")

    try:
        if is_python_script:
            params = " ".join([f'"{arg}"' for arg in sys.argv])
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        else:
            params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
            ctypes.windll.shell32.ShellExecuteW(None, "runas", script, params, None, 1)
        sys.exit(0)  # Exit the non-admin instance
    except Exception as e:
        click.secho(f"Failed to request admin privileges: {e}", fg="red")
        click.echo("Please run this command as Administrator manually.")
        sys.exit(1)


def needs_admin_for_path(path: str) -> bool:
    r"""Check if a path likely requires admin privileges to modify.

    System directories that typically require admin:
    - C:\Program Files
    - C:\Program Files (x86)
    - C:\Windows
    - C:\ProgramData (sometimes)
    """
    if sys.platform != "win32":
        return False

    path_lower = path.lower().replace("/", "\\")
    system_paths = [
        r"c:\program files",
        r"c:\programdata",
        r"c:\windows",
    ]

    for sys_path in system_paths:
        if path_lower.startswith(sys_path):
            return True
    return False


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
@click.option("--elevate", is_flag=True, default=False, hidden=True, help="Request admin privileges at startup")
@click.pass_context
def cli(ctx: click.Context, as_json: bool, history_path: str | None, session_path: str | None, elevate: bool):
    """softwaremove - move installed software between disks."""
    # Print admin status for user awareness
    if not as_json:
        print_admin_status()

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
    # Check if --elevate flag is present in command line
    # If so, request admin privileges immediately at startup
    if "--elevate" in sys.argv:
        if not is_admin():
            require_admin("This operation requires administrator privileges.")
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
@click.option("--check", "do_check", is_flag=True, default=False, help="Run check before move")
@click.option("--admin", "require_admin_flag", is_flag=True, default=False, help="Request admin privileges if needed")
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
    do_check: bool,
    require_admin_flag: bool,
):
    """Move a software directory to a new location."""
    as_json = ctx.obj["as_json"]

    if software_name is None:
        software_name = Path(source_path).name

    # Check if admin is needed for the source path
    needs_admin = needs_admin_for_path(source_path) or needs_admin_for_path(target_path)

    # Auto-request admin if:
    # 1. User explicitly requested with --admin flag
    # 2. Path needs admin and we're not already admin
    if require_admin_flag or (needs_admin and not is_admin()):
        require_admin(
            f"Creating junction link in '{source_path}' requires administrator privileges."
        )
        # If we reach here, admin elevation failed but we can still try

    # Run pre-check if requested or if verbose mode
    if do_check or not as_json:
        check_result = check_software_moveable(source_path, software_name)

        if not check_result["moveable"]:
            if not as_json:
                click.secho("✗ Cannot move software:", fg="red", bold=True)
                for err in check_result["errors"]:
                    click.echo(f"  - {err}")
            output({"ok": False, "error": "Pre-check failed", "details": check_result}, as_json)
            return

        # Warn about running processes
        if check_result["details"].get("running_processes"):
            if not as_json:
                click.secho("⚠️  WARNING: The following processes are running:", fg="red", bold=True)
                for proc in check_result["details"]["running_processes"]:
                    click.echo(f"  - {proc}")
                click.echo()

            if not yes:
                if not as_json:
                    if not click.confirm("Continue anyway? (Files may be skipped if locked)", default=False):
                        output({"ok": False, "error": "user cancelled"}, as_json)
                        return

    if not as_json and not yes:
        if not click.confirm(f"Move {source_path} -> {target_path}?", default=False):
            output({"ok": False, "error": "user cancelled"}, as_json)
            return

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

    # Pretty print result if not JSON
    if not as_json:
        if result.get("ok"):
            click.secho("✓ Move completed successfully", fg="green")
            if result.get("skipped"):
                click.echo(f"  (Skipped: {result.get('message', '')})")
            else:
                click.echo(f"  Source: {result.get('source_path')}")
                click.echo(f"  Target: {result.get('target_path')}")
                click.echo(f"  Size: {format_size(result.get('software_size', 0))}")
            if result.get("skipped_files"):
                skipped = result["skipped_files"]
                click.secho(f"  ⚠️  Warning: {len(skipped)} files were skipped (locked/occupied)", fg="yellow")
                for f in skipped[:5]:
                    click.echo(f"    - {f}")
                if len(skipped) > 5:
                    click.echo(f"    ... and {len(skipped) - 5} more")
        else:
            error_msg = result.get('error', 'Unknown error')
            click.secho(f"✗ Move failed: {error_msg}", fg="red")

            skipped = result.get("skipped_files", [])
            if skipped:
                click.secho(f"\n  {len(skipped)} files could not be moved (likely occupied by running processes):", fg="yellow")
                for f in skipped[:5]:
                    click.echo(f"    - {f}")
                if len(skipped) > 5:
                    click.echo(f"    ... and {len(skipped) - 5} more")
                click.echo("\n  Please close the related software and try again, or run with --admin.")

            # Suggest admin if permission denied
            if "拒绝访问" in error_msg or "access" in error_msg.lower() or "permission" in error_msg.lower():
                click.echo()
                click.secho("💡 Tip: This error may be due to insufficient permissions.", fg="yellow")
                click.echo("   Try running with --admin flag:")
                click.echo(f'   softwaremove move start --source "{source_path}" --target "{target_path}" --admin')

    output(result, as_json)


@move.command("check")
@click.option("--source", "source_path", required=True, type=click.Path(), help="Source install path")
@click.option("--name", "software_name", default=None, help="Software name")
@click.pass_context
def move_check(ctx: click.Context, source_path: str, software_name: str | None):
    """Check if software can be safely moved (UWP, registry refs, locked files, running processes)."""
    as_json = ctx.obj["as_json"]
    if software_name is None:
        software_name = Path(source_path).name

    if not as_json:
        click.echo(f"Checking {software_name}...")
        click.echo(f"Source: {source_path}")
        click.echo()

    result = check_software_moveable(source_path, software_name)

    if not as_json:
        # Human-readable output
        if result["moveable"]:
            click.secho("✓ Can be moved", fg="green")
        else:
            click.secho("✗ Cannot be moved", fg="red")

        if result["errors"]:
            click.secho("\nErrors:", fg="red")
            for err in result["errors"]:
                click.echo(f"  - {err}")

        if result["warnings"]:
            click.secho("\nWarnings:", fg="yellow")
            for warn in result["warnings"]:
                click.echo(f"  - {warn}")

        if result["details"].get("running_processes"):
            click.secho("\n⚠️  Running processes detected:", fg="red", bold=True)
            for proc in result["details"]["running_processes"]:
                click.echo(f"  - {proc}")
            click.secho("\nPlease close these processes before moving!", fg="red")

        if result["details"].get("locked_files"):
            click.secho(f"\n⚠️  {len(result['details']['locked_files'])} locked files will be skipped", fg="yellow")

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
@click.option("--admin", "require_admin_flag", is_flag=True, default=False, help="Request admin privileges if needed")
@click.pass_context
def history_restore(ctx: click.Context, record_id: int, require_admin_flag: bool):
    """Restore a moved software directory by record id."""
    record = history_core.get_record(record_id, ctx.obj["history_path"])
    if not record:
        output({"ok": False, "error": f"record {record_id} not found"}, ctx.obj["as_json"])
        return

    if require_admin_flag or (needs_admin_for_path(record["source_path"]) and not is_admin()):
        require_admin(f"Restoring to '{record['source_path']}' requires administrator privileges.")

    result = move_core.restore(record_id, ctx.obj["history_path"])
    output(result, ctx.obj["as_json"])


@history.command("undo")
@click.option("--admin", "require_admin_flag", is_flag=True, default=False, help="Request admin privileges if needed")
@click.pass_context
def history_undo(ctx: click.Context, require_admin_flag: bool):
    """Restore the latest non-restored record."""
    record = history_core.latest_record(ctx.obj["history_path"], restored=False)
    if not record:
        output({"ok": False, "error": "no active records"}, ctx.obj["as_json"])
        return

    if require_admin_flag or (needs_admin_for_path(record["source_path"]) and not is_admin()):
        require_admin(f"Restoring to '{record['source_path']}' requires administrator privileges.")

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
@click.option("--admin", "require_admin_flag", is_flag=True, default=False, help="Request admin privileges if needed")
@click.pass_context
def history_redo(ctx: click.Context, record_id: int | None, link_mode: str, require_admin_flag: bool):
    """Re-run a move based on a restored record."""
    if record_id is None:
        record = history_core.latest_record(ctx.obj["history_path"], restored=True)
        if not record:
            output({"ok": False, "error": "no restored records"}, ctx.obj["as_json"])
            return
        record_id = record["id"]

    record = history_core.get_record(record_id, ctx.obj["history_path"])
    if record and (require_admin_flag or (needs_admin_for_path(record["source_path"]) and not is_admin())):
        require_admin(f"Re-moving to '{record['source_path']}' requires administrator privileges.")

    result = move_core.redo(record_id, ctx.obj["history_path"], link_mode=link_mode)
    output(result, ctx.obj["as_json"])


@history.command("delete")
@click.option("--id", "record_id", required=True, type=int)
@click.pass_context
def history_delete(ctx: click.Context, record_id: int):
    """Delete a history record."""
    ok = history_core.delete_record(record_id, ctx.obj["history_path"])
    output({"ok": ok, "id": record_id}, ctx.obj["as_json"])
