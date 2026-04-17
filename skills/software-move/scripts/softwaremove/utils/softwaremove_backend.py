"""Backend logic for SoftwareMove CLI."""
from __future__ import annotations

import os
import platform
import shutil
import string
import subprocess
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple


LogFn = Optional[Callable[[str], None]]
ProgressFn = Optional[Callable[[int, int, str], None]]


def check_running_processes(directory_path: str) -> List[str]:
    """Check if any process is using files in the given directory."""
    if platform.system() != "Windows":
        return []
    try:
        import ctypes
        from ctypes import wintypes

        # Try to find processes using files in the directory
        result = subprocess.run(
            ["powershell", "-Command",
             f"Get-Process | Where-Object {{ $_.Modules.FileName -like '{directory_path}*' -or $_.Path -like '{directory_path}*' }} | Select-Object -ExpandProperty ProcessName -Unique"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return [p.strip() for p in result.stdout.strip().split('\n') if p.strip()]
    except (OSError, subprocess.SubprocessError):
        pass
    return []


def is_file_locked(filepath: str) -> bool:
    """Check if a file is locked by another process."""
    try:
        with open(filepath, 'rb'):
            pass
        return False
    except (PermissionError, OSError):
        return True


def remove_empty_directories(path: str, log_cb: LogFn = None) -> bool:
    """Remove empty directories recursively from bottom to top."""
    if not os.path.isdir(path):
        return False

    removed_all = True
    # Walk bottom-up to remove empty directories
    for root, dirs, files in os.walk(path, topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                # Check if directory is empty
                if os.path.isdir(dir_path) and not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    _log(log_cb, f"Removed empty directory: {dir_path}")
            except (OSError, PermissionError) as e:
                _log(log_cb, f"Failed to remove directory {dir_path}: {e}")
                removed_all = False

    # Try to remove the root directory itself if empty
    try:
        if os.path.isdir(path) and not os.listdir(path):
            os.rmdir(path)
            _log(log_cb, f"Removed empty source directory: {path}")
            return True
    except (OSError, PermissionError) as e:
        _log(log_cb, f"Source directory not empty or cannot be removed: {path} - {e}")
        removed_all = False

    return removed_all


# ---------------------------------------------------------------------------
# Disk and registry helpers
# ---------------------------------------------------------------------------

def get_all_disks() -> List[str]:
    disks: List[str] = []
    if platform.system() == "Windows":
        for letter in string.ascii_uppercase:
            disk_path = f"{letter}:\\"
            try:
                shutil.disk_usage(disk_path)
                disks.append(letter)
            except (OSError, PermissionError):
                continue
    return disks


def get_disk_info(disk_letter: str) -> Dict[str, int]:
    if platform.system() == "Windows":
        disk_path = f"{disk_letter}:\\"
        try:
            total, used, free = shutil.disk_usage(disk_path)
            return {"total": total, "used": used, "free": free}
        except (OSError, ValueError):
            return {"total": 0, "used": 0, "free": 0}
    return {"total": 0, "used": 0, "free": 0}


def list_installed() -> List[Dict[str, str]]:
    if platform.system() != "Windows":
        return []
    try:
        import winreg
    except (ImportError, OSError):
        return []

    software_list: List[Dict[str, str]] = []
    registry_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    for hkey, path in registry_paths:
        try:
            key = winreg.OpenKey(hkey, path)
            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    subkey = winreg.OpenKey(key, subkey_name)
                    info: Dict[str, str] = {}
                    try:
                        info["name"] = winreg.QueryValueEx(subkey, "DisplayName")[0]
                    except (FileNotFoundError, OSError):
                        continue
                    if not info["name"] or info["name"].startswith("KB"):
                        winreg.CloseKey(subkey)
                        continue
                    try:
                        info["publisher"] = winreg.QueryValueEx(subkey, "Publisher")[0]
                    except (FileNotFoundError, OSError):
                        info["publisher"] = ""
                    try:
                        info["install_location"] = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                    except (FileNotFoundError, OSError):
                        try:
                            info["install_location"] = winreg.QueryValueEx(subkey, "InstallPath")[0]
                        except (FileNotFoundError, OSError):
                            info["install_location"] = ""
                    try:
                        info["uninstall_string"] = winreg.QueryValueEx(subkey, "UninstallString")[0]
                    except (FileNotFoundError, OSError):
                        info["uninstall_string"] = ""
                    try:
                        info["display_version"] = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                    except (FileNotFoundError, OSError):
                        info["display_version"] = ""
                    try:
                        info["install_date"] = winreg.QueryValueEx(subkey, "InstallDate")[0]
                    except (FileNotFoundError, OSError):
                        info["install_date"] = ""

                    if info.get("install_location"):
                        software_list.append(info)
                    winreg.CloseKey(subkey)
                except (OSError, ValueError):
                    continue
            winreg.CloseKey(key)
        except (OSError, FileNotFoundError):
            continue

    seen = set()
    unique = []
    for sw in software_list:
        name = sw.get("name")
        if name and name not in seen:
            seen.add(name)
            unique.append(sw)
    return unique


# ---------------------------------------------------------------------------
# Formatting and filters
# ---------------------------------------------------------------------------

SYSTEM_DIRECTORY_KEYWORDS = [
    r"\windows",
    r"\windows\system32",
    r"\windows\syswow64",
    r"\windows\winsxs",
    r"\windows\installer",
    r"\windows\assembly",
    r"\windows\microsoft.net",
    r"\program files\windows",
    r"\program files (x86)\windows",
    r"\program files\common files",
    r"\program files (x86)\common files",
    r"\program files\microsoft",
    r"\program files (x86)\microsoft",
    r"\program files\windows defender",
    r"\program files\windows mail",
    r"\program files\windows media player",
    r"\program files\windows photo viewer",
    r"\program files\windows sidebar",
    r"\program files\windows nt",
    r"\program files\microsoft office\root",
    r"\temp",
    r"\tmp",
    r"\cache",
    r"\programdata\microsoft",
    r"\programdata\windows",
]


def is_system_directory(path: str) -> bool:
    if not path:
        return False
    normalized = path.lower().replace("/", "\\").rstrip("\\")
    for keyword in SYSTEM_DIRECTORY_KEYWORDS:
        keyword = keyword.lower()
        if keyword in normalized:
            if normalized.endswith(keyword) or f"\\{keyword}\\" in normalized or normalized.startswith(keyword + "\\"):
                return True
    parts = normalized.split("\\")
    if len(parts) >= 2 and parts[1] in ["windows", "programdata"]:
        return True
    if "program files" in normalized:
        if "windows" in normalized or normalized.count("microsoft") > 1:
            return True
    return False


def is_valid_software_directory(path: str) -> bool:
    if not path or not os.path.exists(path):
        return False
    if is_system_directory(path):
        return False
    return True


def get_directory_size(path: str) -> int:
    total_size = 0
    if not os.path.exists(path):
        return 0
    if os.path.isfile(path):
        return os.path.getsize(path)
    for dirpath, _, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                total_size += os.path.getsize(filepath)
            except (OSError, FileNotFoundError, PermissionError):
                continue
    return total_size


def get_directory_modify_time(path: str) -> Optional[datetime]:
    try:
        if os.path.exists(path):
            return datetime.fromtimestamp(os.path.getmtime(path))
    except (OSError, PermissionError):
        return None
    return None


def format_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0B"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    idx = 0
    while size >= 1024 and idx < len(units) - 1:
        size /= 1024
        idx += 1
    if idx == 0:
        return f"{int(size)}{units[idx]}"
    return f"{size:.1f}{units[idx]}"


def format_time_ago(modify_time: Optional[datetime]) -> str:
    if modify_time is None:
        return "未知"
    now = datetime.now()
    delta = now - modify_time
    if delta.days == 0:
        return "今天"
    if delta.days == 1:
        return "昨天"
    if delta.days < 7:
        return f"{delta.days} 天前"
    if delta.days < 30:
        weeks = delta.days // 7
        return f"{weeks} 周前"
    if delta.days < 365:
        months = delta.days // 30
        return f"{months} 个月前"
    years = delta.days // 365
    return f"{years} 年前"


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

def scan_software_on_disk(disk_letter: str) -> List[Dict]:
    disk_path = f"{disk_letter}:\\"
    software_list: List[Dict] = []
    installed_software = list_installed()
    for software in installed_software:
        install_location = software.get("install_location", "").strip()
        if install_location and install_location.upper().startswith(disk_path.upper()):
            if not is_valid_software_directory(install_location):
                continue
            if os.path.exists(install_location):
                size = get_directory_size(install_location)
                if size > 0:
                    modify_time = get_directory_modify_time(install_location)
                    software_info = {
                        "name": software.get("name", ""),
                        "install_location": install_location,
                        "size": size,
                        "size_str": format_size(size),
                        "modify_time": modify_time,
                        "modify_time_str": format_time_ago(modify_time),
                        "publisher": software.get("publisher", ""),
                        "version": software.get("display_version", ""),
                    }
                    software_list.append(software_info)
    software_list.sort(key=lambda x: x.get("size", 0), reverse=True)
    return software_list


# ---------------------------------------------------------------------------
# Move + restore
# ---------------------------------------------------------------------------

def check_software_moveable(source_path: str, software_name: str) -> Dict:
    """Check if software can be safely moved. Returns dict with warnings and errors."""
    result = {
        "moveable": True,
        "errors": [],
        "warnings": [],
        "details": {},
    }

    # Check 1: Source path exists
    if not os.path.exists(source_path):
        result["moveable"] = False
        result["errors"].append(f"源路径不存在: {source_path}")
        return result

    # Check 2: Source path is a directory
    if not os.path.isdir(source_path):
        result["moveable"] = False
        result["errors"].append(f"源路径不是目录: {source_path}")
        return result

    # Check 3: Check if software is currently running
    running_processes = check_running_processes(source_path)
    if running_processes:
        result["warnings"].append(f"⚠️ 检测到以下进程正在运行，请先关闭: {', '.join(running_processes)}")
        result["details"]["running_processes"] = running_processes

    # Check 4: UWP/MSIX app detection
    is_uwp_reg = _check_uwp_registry(source_path)
    if is_uwp_reg:
        result["warnings"].append("⚠️ 检测为 UWP/MSIX 应用，junction 链接可能不支持，建议先测试")
        result["details"]["is_uwp"] = True
    else:
        result["details"]["is_uwp"] = False

    # Check 5: Registry dependencies
    reg_refs = _check_registry_references(source_path, software_name)
    if reg_refs:
        result["warnings"].append(f"⚠️ 注册表中存在 {len(reg_refs)} 个路径引用，迁移后需更新注册表")
        result["details"]["registry_refs"] = reg_refs[:5]

    # Check 6: Locked files
    locked = _check_locked_files(source_path)
    if locked:
        result["moveable"] = False
        result["errors"].append(f"发现 {len(locked)} 个文件被占用，无法搬迁。请先关闭相关软件后再试。")
        result["details"]["locked_files"] = locked[:5]  # Only show first 5

    # Check 7: System directory files (should be empty after fix)
    sys_files = _check_system_files(source_path)
    if sys_files:
        result["warnings"].append(f"⚠️ 发现 {len(sys_files)} 个系统文件，迁移后程序可能无法运行")
        result["details"]["system_files"] = sys_files[:5]

    # Determine overall moveability
    if is_uwp_reg:
        result["moveable"] = False
        result["errors"].append("UWP 应用不支持 junction 链接方式，建议使用注册表路径修改方式")

    return result


def _check_uwp_app(software_name: str) -> bool:
    """Check if software is a UWP/MSIX app."""
    if not software_name:
        return False
    try:
        import winreg
        # Search registry for PackageRootFolder or MSIX indicators
        search_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppModel"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Appx"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\AppPaths"),
        ]
        name_lower = software_name.lower()
        for hkey, path in search_paths:
            try:
                key = winreg.OpenKey(hkey, path)
                for i in range(min(winreg.QueryInfoKey(key)[0], 100)):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        if name_lower in subkey_name.lower() or subkey_name.lower() in name_lower:
                            winreg.CloseKey(key)
                            return True
                    except (OSError, ValueError):
                        pass
                winreg.CloseKey(key)
            except (OSError, FileNotFoundError):
                pass
    except (ImportError, OSError):
        pass
    return False


def _check_registry_references(source_path: str, software_name: str) -> List[str]:
    """Check for registry paths that reference the source directory."""
    refs = []
    if not source_path:
        return refs
    try:
        import winreg
        source_lower = source_path.lower().replace("/", "\\")

        # Common registry paths to check
        search_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE"),
        ]

        for hkey, base_path in search_paths:
            try:
                _search_registry_recursive(hkey, base_path, source_lower, refs, max_depth=3)
            except (OSError, RuntimeError):
                pass
    except (ImportError, OSError):
        pass
    return refs[:10]  # Limit results


def _search_registry_recursive(hkey, path: str, search_term: str, results: List, max_depth: int, depth: int = 0):
    """Recursively search registry for path references."""
    if depth > max_depth:
        return
    try:
        import winreg
        key = winreg.OpenKey(hkey, path)
        try:
            for i in range(min(winreg.QueryInfoKey(key)[1], 50)):  # Check values
                try:
                    val = winreg.EnumValue(key, i)
                    if val[1] and isinstance(val[1], str) and search_term in val[1].lower():
                        results.append(f"{path}\\{val[0]}")
                except (OSError, ValueError):
                    pass
        except (OSError, ValueError):
            pass

        try:
            for i in range(min(winreg.QueryInfoKey(key)[0], 20)):  # Check subkeys
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    _search_registry_recursive(hkey, f"{path}\\{subkey_name}", search_term, results, max_depth, depth + 1)
                except (OSError, ValueError):
                    pass
        except (OSError, ValueError):
            pass
        winreg.CloseKey(key)
    except (OSError, FileNotFoundError):
        pass


def _check_locked_files(source_path: str) -> List[str]:
    """Check for files that are locked by running processes."""
    locked = []
    for root, dirs, files in os.walk(source_path):
        for f in files:
            filepath = os.path.join(root, f)
            try:
                with open(filepath, 'rb'):
                    pass
            except (PermissionError, OSError):
                locked.append(os.path.relpath(filepath, source_path))
    return locked


def _check_uwp_registry(source_path: str) -> bool:
    """Check if software is registered as UWP/MSIX in registry or located in typical UWP dirs."""
    if not source_path:
        return False
    source_lower = source_path.lower().replace("/", "\\")

    # Heuristic 1: Common UWP/MSIX install locations
    uwp_locations = [
        "\\windowsapps\\",
        "\\appdata\\local\\packages\\",
        "\\appdata\\local\\microsoft\\windowsapps\\",
        "\\program files\\windowsapps\\",
    ]
    for loc in uwp_locations:
        if loc in source_lower:
            return True

    # Heuristic 2: Registry check for PackageRootFolder
    try:
        import winreg
        search_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Appx"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppModel"),
        ]
        for hkey, path in search_paths:
            try:
                key = winreg.OpenKey(hkey, path)
                for i in range(winreg.QueryInfoKey(key)[1]):
                    try:
                        name, val, _ = winreg.EnumValue(key, i)
                        if name == "PackageRootFolder" and isinstance(val, str):
                            if source_lower.startswith(val.lower().replace("/", "\\")):
                                winreg.CloseKey(key)
                                return True
                    except (OSError, ValueError):
                        pass
                winreg.CloseKey(key)
            except (OSError, FileNotFoundError):
                pass
    except (ImportError, OSError):
        pass
    return False


def _check_system_files(source_path: str) -> List[str]:
    """Check for system DLLs in system directories that shouldn't be moved."""
    sys_files = []
    system_dirs = [
        r'C:\Windows\System32',
        r'C:\Windows\SysWOW64',
        r'C:\Windows\WinSxS',
    ]
    for root, dirs, files in os.walk(source_path):
        # Skip if already in a subdir that looks system
        rel = os.path.relpath(root, source_path).lower()
        if any(sd.lower() in root.lower() for sd in system_dirs):
            for f in files:
                sys_files.append(os.path.join(rel, f))
    return sys_files


def move_software(
    source_path: str,
    target_path: str,
    software_name: str,
    software_size: int,
    link_mode: str = "auto",
    progress_cb: ProgressFn = None,
    log_cb: LogFn = None,
) -> Dict:
    mover = _Mover(
        source_path=source_path,
        target_path=target_path,
        software_name=software_name,
        software_size=software_size,
        link_mode=link_mode,
        progress_cb=progress_cb,
        log_cb=log_cb,
    )
    return mover.run()


def restore_software(
    source_path: str,
    target_path: str,
    software_name: str,
    progress_cb: ProgressFn = None,
    log_cb: LogFn = None,
) -> Dict:
    restorer = _Restorer(
        source_path=source_path,
        target_path=target_path,
        software_name=software_name,
        progress_cb=progress_cb,
        log_cb=log_cb,
    )
    return restorer.run()


def _log(log_cb: LogFn, message: str) -> None:
    if log_cb:
        log_cb(message)


def _progress(progress_cb: ProgressFn, current: int, total: int, name: str) -> None:
    if progress_cb:
        progress_cb(current, total, name)


def _is_system_file(filepath: str) -> bool:
    filename = os.path.basename(filepath).lower()
    system_files = [
        "desktop.ini",
        "thumbs.db",
        "$recycle.bin",
        "system volume information",
        "pagefile.sys",
        "hiberfil.sys",
        "swapfile.sys",
    ]
    return filename in system_files


def _move_file_with_retry(source: str, target: str, retries: int = 3, log_cb: LogFn = None) -> bool:
    """Move a file with retry on locked files. Returns True if successful, False if skipped."""
    import time
    last_err = None
    for attempt in range(retries):
        try:
            shutil.move(source, target)
            return True
        except (OSError, PermissionError) as exc:
            last_err = exc
            if attempt < retries - 1:
                time.sleep(0.5)
    # Cross-device shutil.move may have partially copied the file before failing.
    # Clean up any leftover target to avoid incomplete migration.
    if os.path.exists(target):
        try:
            if os.path.isdir(target):
                shutil.rmtree(target, ignore_errors=True)
            else:
                os.remove(target)
        except (OSError, PermissionError):
            pass
    _log(log_cb, f"跳过锁定文件: {source} -> {target} ({last_err})")
    return False


def _count_files(path: str) -> int:
    if os.path.isfile(path):
        return 1
    count = 0
    for _, _, files in os.walk(path):
        count += len(files)
    return max(count, 1)


def _get_file_attributes(path: str) -> Optional[int]:
    if platform.system() != "Windows":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        GetFileAttributesW = ctypes.windll.kernel32.GetFileAttributesW
        GetFileAttributesW.argtypes = [wintypes.LPCWSTR]
        GetFileAttributesW.restype = wintypes.DWORD
        attrs = GetFileAttributesW(os.path.normpath(path))
        if attrs == 0xFFFFFFFF:
            return None
        return int(attrs)
    except (ImportError, OSError, AttributeError):
        return None


def _path_exists_or_link(path: str) -> bool:
    if os.path.exists(path) or os.path.islink(path):
        return True
    attrs = _get_file_attributes(path)
    return attrs is not None


def _target_has_entries(path: str) -> bool:
    try:
        with os.scandir(path) as entries:
            return next(entries, None) is not None
    except (OSError, PermissionError, StopIteration):
        return False


def _create_link(link_path: str, target_path: str, link_mode: str, log_cb: LogFn) -> None:
    link_mode = (link_mode or "auto").lower()
    if link_mode == "none":
        _log(log_cb, "Link creation skipped (link_mode=none)")
        return

    # Prefer junction for "auto" mode - symlink has path issues in MSYS2/Git Bash
    if link_mode == "auto":
        link_mode = "junction"

    if link_mode == "symlink":
        is_admin = False
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except (ImportError, OSError, AttributeError):
            is_admin = False
        try:
            os.symlink(target_path, link_path, target_is_directory=os.path.isdir(target_path))
            _log(log_cb, "Symbolic link created")
            return
        except OSError as exc:
            raise RuntimeError(f"Failed to create symlink: {exc}")

    if link_mode == "junction":
        if not os.path.isdir(target_path):
            raise RuntimeError("Junction only supports directories")
        try:
            # Ensure parent directory exists for the link
            link_parent = os.path.dirname(link_path)
            if link_parent and not os.path.exists(link_parent):
                os.makedirs(link_parent, exist_ok=True)

            result = subprocess.run(
                ["cmd", "/D", "/c", "mklink", "/J", link_path, target_path],
                check=True,
                capture_output=True,
                encoding="utf-8",
                errors="ignore",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            _log(log_cb, f"Junction created: {link_path} -> {target_path}")
            return
        except subprocess.CalledProcessError as exc:
            error_msg = exc.stderr if exc.stderr else str(exc)
            raise RuntimeError(f"Failed to create junction: {error_msg}")

    raise RuntimeError(f"Unsupported link_mode: {link_mode}")


class _Mover:
    def __init__(
        self,
        source_path: str,
        target_path: str,
        software_name: str,
        software_size: int,
        link_mode: str,
        progress_cb: ProgressFn,
        log_cb: LogFn,
    ):
        self.source_path = source_path
        self.target_path = target_path
        self.software_name = software_name
        self.software_size = software_size
        self.link_mode = link_mode
        self.progress_cb = progress_cb
        self.log_cb = log_cb
        self.moved_files: List[tuple[str, str]] = []
        self.skipped_files: List[str] = []
        self.rollback_needed = False
        self.original_source_path = source_path
        self.backup_path: Optional[str] = None
        self.link_created = False
        self.rollback_done = False

    def run(self) -> Dict:
        try:
            _log(self.log_cb, f"Move start: {self.software_name}")
            _log(self.log_cb, f"Source: {self.source_path}")
            _log(self.log_cb, f"Target: {self.target_path}")

            if not _path_exists_or_link(self.source_path):
                raise RuntimeError(f"Source path not found: {self.source_path}")

            # Check if already a link (skip migration)
            if is_link_or_junction(self.source_path):
                real_path = os.path.realpath(self.source_path)
                if not os.path.exists(real_path):
                    raise RuntimeError(
                        f"Source path is a broken junction/link: {self.source_path} -> {real_path}"
                    )
                _log(self.log_cb, f"Source is already a link pointing to: {real_path}")
                return {
                    "ok": True,
                    "skipped": True,
                    "source_path": self.source_path,
                    "target_path": real_path,
                    "software_name": self.software_name,
                    "software_size": self.software_size,
                    "message": "Source is already a link/junction",
                }

            target_parent = os.path.dirname(self.target_path)
            if target_parent and not os.path.exists(target_parent):
                os.makedirs(target_parent, exist_ok=True)

            if _path_exists_or_link(self.target_path):
                raise RuntimeError(
                    f"Target path already exists: {self.target_path}. "
                    "Please choose an empty destination path."
                )

            total_files = _count_files(self.source_path)
            _log(self.log_cb, f"Total files: {total_files}")

            # Step 1: Move files from source to target
            self._move_directory(self.source_path, self.target_path, total_files)

            # If any files were skipped, rollback immediately to keep atomicity
            if self.skipped_files:
                _log(self.log_cb, f"Move aborted: {len(self.skipped_files)} files were skipped (locked or permission denied). Rolling back...")
                self._rollback()
                return {
                    "ok": False,
                    "error": f"{len(self.skipped_files)} files could not be moved (likely locked by running processes). Please close the related software and try again.",
                    "skipped_files": self.skipped_files,
                }

            # Step 2: Remove empty directories in source
            _log(self.log_cb, "Cleaning up empty directories...")
            cleanup_success = remove_empty_directories(self.source_path, self.log_cb)

            if not cleanup_success:
                # Some directories couldn't be removed - rename source and continue
                backup_path = f"{self.source_path}_backup_{int(datetime.now().timestamp())}"
                rename_success = False
                try:
                    os.rename(self.source_path, backup_path)
                    _log(self.log_cb, f"Renamed source to backup: {backup_path}")
                    self.source_path = backup_path
                    self.backup_path = backup_path
                    rename_success = True
                except OSError as e:
                    _log(self.log_cb, f"Warning: Could not rename source directory: {e}")

                if not rename_success:
                    error_detail = f"Source directory could not be cleaned or renamed: {self.original_source_path}"
                    _log(self.log_cb, "Rolling back due to uncleanable source directory...")
                    self._rollback()
                    return {
                        "ok": False,
                        "error": error_detail,
                    }
            else:
                # Source directory was fully removed, use original path for link
                _log(self.log_cb, "Source directory cleaned successfully")

            # Step 3: Create junction link
            link_path = self.original_source_path
            _log(self.log_cb, f"Creating junction link: {link_path} -> {self.target_path}")
            try:
                _create_link(link_path, self.target_path, self.link_mode, self.log_cb)
                self.link_created = self.link_mode.lower() != "none"
                verify_result = verify_move(
                    link_path,
                    self.target_path,
                    expected_size=self.software_size,
                )
                if not verify_result.get("ok"):
                    raise RuntimeError("; ".join(verify_result.get("errors", ["Move verification failed"])))
            except Exception as link_exc:
                # Link creation failed - rollback
                _log(self.log_cb, f"Failed to create junction: {link_exc}")
                _log(self.log_cb, "Rolling back...")
                self._rollback()
                raise RuntimeError(f"Failed to create junction link: {link_exc}")

            # Step 4: Clean up backup if exists
            if self.backup_path:
                if os.path.exists(self.backup_path):
                    try:
                        if os.path.isdir(self.backup_path):
                            shutil.rmtree(self.backup_path, ignore_errors=True)
                        else:
                            os.remove(self.backup_path)
                        _log(self.log_cb, "Backup removed")
                    except Exception as e:
                        _log(self.log_cb, f"Warning: Could not remove backup: {e}")

            result = {
                "ok": True,
                "source_path": link_path,
                "target_path": self.target_path,
                "software_name": self.software_name,
                "software_size": self.software_size,
            }
            if self.skipped_files:
                result["skipped_files"] = self.skipped_files
                result["warning"] = f"{len(self.skipped_files)} files were skipped during move"
            return result
        except Exception as exc:
            if self.rollback_needed or self.link_created or self.backup_path:
                self._rollback()
            return {"ok": False, "error": str(exc)}

    def _move_directory(self, source: str, target: str, total_files: int) -> None:
        current_file = 0
        if os.path.isfile(source):
            if _is_system_file(source):
                return
            if _move_file_with_retry(source, target, log_cb=self.log_cb):
                current_file += 1
                _progress(self.progress_cb, current_file, total_files, os.path.basename(source))
                self.moved_files.append((source, target))
                self.rollback_needed = True
            return

        os.makedirs(target, exist_ok=True)
        for root, _, files in os.walk(source):
            rel_path = os.path.relpath(root, source)
            target_dir = target if rel_path == "." else os.path.join(target, rel_path)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            for file in files:
                source_file = os.path.join(root, file)
                if _is_system_file(source_file):
                    current_file += 1
                    _progress(self.progress_cb, current_file, total_files, file)
                    continue
                target_file = os.path.join(target_dir, file)
                if _move_file_with_retry(source_file, target_file, log_cb=self.log_cb):
                    current_file += 1
                    _progress(self.progress_cb, current_file, total_files, file)
                    self.moved_files.append((source_file, target_file))
                    self.rollback_needed = True
                else:
                    self.skipped_files.append(os.path.relpath(source_file, self.source_path))
                    current_file += 1
                    _progress(self.progress_cb, current_file, total_files, file)

    def _rollback(self) -> None:
        if self.rollback_done:
            return
        if self.link_created and is_link_or_junction(self.original_source_path):
            try:
                _remove_link(self.original_source_path)
            except (OSError, PermissionError):
                pass

        rollback_success = True
        for source_file, target_file in reversed(self.moved_files):
            try:
                if os.path.exists(target_file):
                    target_dir = os.path.dirname(source_file)
                    if target_dir and not os.path.exists(target_dir):
                        os.makedirs(target_dir, exist_ok=True)
                    shutil.move(target_file, source_file)
                if os.path.exists(target_file):
                    rollback_success = False
            except (OSError, shutil.Error):
                rollback_success = False
                continue

        if self.backup_path and os.path.exists(self.backup_path):
            try:
                self._merge_backup_into_source()
            except (OSError, shutil.Error):
                pass

        # Clean up target only if all tracked files were successfully rolled back.
        # If rollback was partial, leave target intact so the user can recover.
        if os.path.exists(self.target_path) and os.path.isdir(self.target_path):
            try:
                if rollback_success:
                    shutil.rmtree(self.target_path, ignore_errors=True)
                    _log(self.log_cb, f"Removed target directory after successful rollback: {self.target_path}")
                else:
                    _log(self.log_cb, f"Warning: target directory still contains files after partial rollback: {self.target_path}")
            except (OSError, PermissionError):
                pass

        self.link_created = False
        self.rollback_done = True

    def _merge_backup_into_source(self) -> None:
        if not self.backup_path:
            return

        for root, _, files in os.walk(self.backup_path):
            rel_path = os.path.relpath(root, self.backup_path)
            target_dir = self.original_source_path if rel_path == "." else os.path.join(self.original_source_path, rel_path)
            os.makedirs(target_dir, exist_ok=True)
            for file in files:
                source_file = os.path.join(root, file)
                target_file = os.path.join(target_dir, file)
                if not os.path.exists(target_file):
                    shutil.move(source_file, target_file)

        shutil.rmtree(self.backup_path, ignore_errors=True)


class _Restorer:
    def __init__(
        self,
        source_path: str,
        target_path: str,
        software_name: str,
        progress_cb: ProgressFn,
        log_cb: LogFn,
    ):
        self.source_path = source_path
        self.target_path = target_path
        self.software_name = software_name
        self.progress_cb = progress_cb
        self.log_cb = log_cb

    def run(self) -> Dict:
        try:
            _log(self.log_cb, f"Restore start: {self.software_name}")
            _log(self.log_cb, f"From: {self.source_path}")
            _log(self.log_cb, f"To: {self.target_path}")

            if not os.path.exists(self.source_path):
                raise RuntimeError(f"Source path not found: {self.source_path}")

            target_parent = os.path.dirname(self.target_path)
            if target_parent and not os.path.exists(target_parent):
                os.makedirs(target_parent, exist_ok=True)

            if os.path.exists(self.target_path):
                if is_link_or_junction(self.target_path):
                    _remove_link(self.target_path)
                else:
                    raise RuntimeError(f"Target already exists: {self.target_path}")

            total_files = _count_files(self.source_path)
            self._move_directory(self.source_path, self.target_path, total_files)

            if os.path.exists(self.source_path):
                if os.path.isdir(self.source_path):
                    shutil.rmtree(self.source_path, ignore_errors=True)
                else:
                    os.remove(self.source_path)

            return {"ok": True, "source_path": self.source_path, "target_path": self.target_path}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _move_directory(self, source: str, target: str, total_files: int) -> None:
        current_file = 0
        if os.path.isfile(source):
            shutil.move(source, target)
            current_file += 1
            _progress(self.progress_cb, current_file, total_files, os.path.basename(source))
            return
        os.makedirs(target, exist_ok=True)
        for root, _, files in os.walk(source):
            rel_path = os.path.relpath(root, source)
            target_dir = target if rel_path == "." else os.path.join(target, rel_path)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            for file in files:
                source_file = os.path.join(root, file)
                target_file = os.path.join(target_dir, file)
                shutil.move(source_file, target_file)
                current_file += 1
                _progress(self.progress_cb, current_file, total_files, file)


def is_link_or_junction(path: str) -> bool:
    if os.path.islink(path):
        return True
    attrs = _get_file_attributes(path)
    if attrs is not None and attrs & 0x400:
        return True
    try:
        abs_path = os.path.abspath(path)
        real_path = os.path.realpath(path)
        if abs_path != real_path:
            return True
    except (OSError, ValueError):
        pass
    return False


def _remove_link(path: str) -> None:
    if os.path.isdir(path):
        try:
            os.remove(path)
            return
        except (OSError, PermissionError):
            os.rmdir(path)
    else:
        os.remove(path)


def verify_move(source_path: str, target_path: str, expected_size: int = 0) -> Dict:
    """Verify that a move completed correctly.

    Checks:
    - target_path exists
    - source_path is a link/junction (if it exists)
    - link points to target_path
    - target directory size
    """
    result = {
        "ok": False,
        "source_path": source_path,
        "target_path": target_path,
        "target_exists": False,
        "target_size": 0,
        "target_has_entries": False,
        "is_link": False,
        "link_points_to": None,
        "errors": [],
    }

    if not os.path.exists(target_path):
        result["errors"].append(f"Target path does not exist: {target_path}")
        return result

    result["target_exists"] = True
    result["target_size"] = get_directory_size(target_path)
    result["target_has_entries"] = _target_has_entries(target_path)

    if expected_size > 0 and result["target_size"] == 0 and not result["target_has_entries"]:
        result["errors"].append(f"Target path is empty after move: {target_path}")
        return result

    if _path_exists_or_link(source_path):
        if is_link_or_junction(source_path):
            result["is_link"] = True
            real = os.path.realpath(source_path)
            real_norm = os.path.normpath(real).lower()
            target_norm = os.path.normpath(target_path).lower()
            result["link_points_to"] = real
            if real_norm != target_norm:
                result["errors"].append(
                    f"Source junction/link points to {real}, expected {target_path}"
                )
                return result
        else:
            result["errors"].append(
                f"Source path still exists and is not a junction/link: {source_path}"
            )
            return result

    result["ok"] = True
    return result
