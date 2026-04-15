"""Disk operations."""
from __future__ import annotations

from typing import Dict, List

from softwaremove.utils.softwaremove_backend import get_all_disks, get_disk_info


def list_disks() -> List[str]:
    return get_all_disks()


def disk_info(letter: str) -> Dict[str, int]:
    return get_disk_info(letter)
