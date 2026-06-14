from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from textproof.models import ScanResult


def scan_directory(
    root: str | Path,
    pattern: str = "*.md",
    ignore_files: list[str] | None = None,
) -> ScanResult:
    root = Path(root)
    ignore_set = set(ignore_files or [])
    result = ScanResult()

    for dirpath, _dirnames, filenames in os.walk(root):
        for fname in filenames:
            if not fnmatch.fnmatch(fname, pattern):
                continue
            full = Path(dirpath) / fname
            rel = str(full.relative_to(root))
            if rel in ignore_set or fname in ignore_set:
                continue
            result.files.append(rel)
            group = _infer_group(fname)
            result.groups.setdefault(group, []).append(rel)

    result.files.sort()
    for v in result.groups.values():
        v.sort()
    return result


def _infer_group(filename: str) -> str:
    stem = Path(filename).stem
    parts = stem.rsplit("_", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0]
    parts = stem.rsplit("-", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0]
    return stem
