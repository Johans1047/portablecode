from __future__ import annotations

import os
import pathlib

from .paths import get_config_dir, get_data_dir, normalize_path
from .types import (
    FileEntry,
    Tier,
    TIER1_PATTERNS,
    TIER2_PATTERNS,
    TIER3_PATTERNS,
    TIER4_PATTERNS,
    TIER5_PATTERNS,
)


def match_pattern(filename: str, relative_path: str, pattern: str) -> bool:
    if "**" in pattern:
        prefix = pattern.replace("/**", "").replace("**/", "")
        return relative_path.startswith(prefix) or prefix in relative_path

    if pattern.startswith("*."):
        ext = pattern[1:]
        return filename.endswith(ext)

    return filename == pattern or relative_path == pattern


def classify_file(filename: str, relative_path: str) -> Tier:
    for pattern in TIER5_PATTERNS:
        if match_pattern(filename, relative_path, pattern):
            return Tier.SKIP

    for pattern in TIER4_PATTERNS:
        if match_pattern(filename, relative_path, pattern):
            return Tier.SENSITIVE

    for pattern in TIER3_PATTERNS:
        if match_pattern(filename, relative_path, pattern):
            return Tier.INSTALL_SEPARATELY

    for pattern in TIER2_PATTERNS:
        if match_pattern(filename, relative_path, pattern):
            return Tier.TRANSFORM

    for pattern in TIER1_PATTERNS:
        if match_pattern(filename, relative_path, pattern):
            return Tier.COPY

    return Tier.COPY


def classify_directory(dirname: str, relative_path: str) -> Tier:
    for pattern in TIER5_PATTERNS:
        if match_pattern(dirname, relative_path, pattern):
            return Tier.SKIP

    for pattern in TIER1_PATTERNS:
        if match_pattern(dirname, relative_path, pattern):
            return Tier.COPY

    return Tier.COPY


def get_directory_size(dir_path: str) -> int:
    total = 0
    try:
        for entry in os.scandir(dir_path):
            if entry.is_dir(follow_symlinks=False):
                total += get_directory_size(entry.path)
            else:
                total += entry.stat(follow_symlinks=False).st_size
    except OSError:
        pass
    return total


def _discover_in_directory(dir_path: str, base_path: str, files: list[FileEntry]) -> None:
    try:
        entries = list(os.scandir(dir_path))
    except OSError:
        return

    for entry in entries:
        full_path = entry.path
        relative_path = normalize_path(os.path.relpath(full_path, base_path))

        if entry.is_dir(follow_symlinks=False):
            tier = classify_directory(entry.name, relative_path)
            if tier == Tier.SKIP:
                continue
            if tier == Tier.COPY:
                files.append(FileEntry(
                    path=full_path,
                    relative_path=relative_path,
                    tier=Tier.COPY,
                    size=get_directory_size(full_path),
                    action="copy",
                ))
            else:
                _discover_in_directory(full_path, base_path, files)
        else:
            tier = classify_file(entry.name, relative_path)
            stat = entry.stat(follow_symlinks=False)

            action_map: dict[Tier, str] = {
                Tier.TRANSFORM: "transform",
                Tier.INSTALL_SEPARATELY: "install-separately",
                Tier.SENSITIVE: "sensitive",
                Tier.SKIP: "skip",
            }

            files.append(FileEntry(
                path=full_path,
                relative_path=relative_path,
                tier=tier,
                size=stat.st_size,
                action=action_map.get(tier, "copy"),
            ))


def discover_files() -> list[FileEntry]:
    files: list[FileEntry] = []
    seen_paths: set[str] = set()
    config_dir = get_config_dir()
    data_dir = get_data_dir()

    if os.path.isdir(config_dir):
        _discover_in_directory(config_dir, config_dir, files)
        seen_paths = {f.relative_path for f in files}

    if os.path.isdir(data_dir) and data_dir != config_dir:
        _discover_in_directory(data_dir, data_dir, files)
        # Deduplicate: data_dir files override config_dir if same relative path
        deduped: list[FileEntry] = []
        seen: set[str] = set()
        for f in files:
            if f.relative_path not in seen:
                deduped.append(f)
                seen.add(f.relative_path)
        files = deduped

    return files


def format_file_size(nbytes: int) -> str:
    if nbytes == 0:
        return "0 B"
    k = 1024
    sizes = ["B", "KB", "MB", "GB"]
    i = min(int(nbytes.bit_length() / 10), len(sizes) - 1)
    # More accurate: use log
    import math
    i = min(int(math.log(nbytes, k)), len(sizes) - 1)
    value = nbytes / (k ** i)
    return f"{value:.2f} {sizes[i]}"
