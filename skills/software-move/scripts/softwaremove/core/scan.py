"""Scan operations."""
from __future__ import annotations

from typing import List, Dict

from softwaremove.utils.softwaremove_backend import scan_software_on_disk, list_installed


def scan_disk(letter: str) -> List[Dict]:
    return scan_software_on_disk(letter)


def scan_installed() -> List[Dict]:
    return list_installed()
