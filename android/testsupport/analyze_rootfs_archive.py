#!/usr/bin/env python3
"""Audit a GOAR rootfs tar.gz before Android installation.

This performs archive-level checks independently from extraction, producing
machine-readable evidence about names, GNU-expanded links, target ordering, and
links that would escape the PRoot guest filesystem.
"""
from __future__ import annotations

import json
import posixpath
import sys
import tarfile
from collections import Counter
from pathlib import PurePosixPath


def normalize_member_name(name: str) -> str:
    normalized = name.removeprefix("./")
    if normalized in ("", "."):
        return ""
    if normalized.startswith("/") or "\\" in normalized:
        raise ValueError(f"unsafe archive member name: {name!r}")
    parts = PurePosixPath(normalized).parts
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"unsafe archive member name: {name!r}")
    return normalized


def normalize_hard_target(target: str) -> str:
    normalized = target.removeprefix("./")
    if normalized.startswith("/") or "\\" in normalized:
        raise ValueError(f"unsafe hard-link target: {target!r}")
    return normalize_member_name(normalized)


def relative_symlink_is_inside(member_name: str, target: str) -> bool:
    if not target or "\\" in target:
        return False
    if target.startswith("/"):
        # Absolute symlinks are guest-root paths; never permit host staging paths.
        return not target.startswith("/data/") and not target.startswith("/proc/") and not target.startswith("/sys/")
    joined = posixpath.normpath(posixpath.join(posixpath.dirname(member_name), target))
    return joined not in ("", ".") and not joined.startswith("../") and joined != ".."


def member_kind(member: tarfile.TarInfo) -> str:
    if member.isdir():
        return "directory"
    if member.isreg():
        return "regular"
    if member.issym():
        return "symlink"
    if member.islnk():
        return "hardlink"
    if member.ischr():
        return "character"
    if member.isblk():
        return "block"
    if member.isfifo():
        return "fifo"
    return f"other:{member.type!r}"


def audit(path: str) -> dict:
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()

    records: list[dict] = []
    regular_positions: dict[str, int] = {}
    errors: list[str] = []
    kinds: Counter[str] = Counter()

    for index, member in enumerate(members):
        kind = member_kind(member)
        kinds[kind] += 1
        try:
            name = normalize_member_name(member.name)
        except ValueError as exc:
            errors.append(str(exc))
            name = member.name
        record = {"index": index, "name": name, "kind": kind, "linkname": member.linkname or ""}
        records.append(record)
        if kind == "regular" and name:
            regular_positions[name] = index

    forward_hardlinks: list[dict] = []
    hardlink_targets_missing: list[dict] = []
    symlink_escapes: list[dict] = []
    staging_symlinks: list[dict] = []
    for record in records:
        if record["kind"] == "hardlink":
            try:
                target = normalize_hard_target(record["linkname"])
            except ValueError as exc:
                errors.append(str(exc))
                continue
            target_index = regular_positions.get(target)
            if target_index is None:
                hardlink_targets_missing.append({**record, "normalized_target": target})
            elif target_index > record["index"]:
                forward_hardlinks.append({**record, "normalized_target": target, "target_index": target_index})
        elif record["kind"] == "symlink":
            target = record["linkname"]
            if not relative_symlink_is_inside(record["name"], target):
                symlink_escapes.append(record)
            if target.startswith("/data/data/"):
                staging_symlinks.append(record)

    return {
        "archive": path,
        "entries": len(records),
        "types": dict(sorted(kinds.items())),
        "hardlink_count": kinds["hardlink"],
        "forward_hardlinks": forward_hardlinks,
        "hardlink_targets_missing": hardlink_targets_missing,
        "symlink_escapes": symlink_escapes,
        "staging_symlinks": staging_symlinks,
        "errors": errors,
        "pass": not errors and not hardlink_targets_missing and not symlink_escapes and not staging_symlinks,
    }


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: analyze_rootfs_archive.py archive.tar.gz")
    result = audit(sys.argv[1])
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
