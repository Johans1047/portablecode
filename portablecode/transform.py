from __future__ import annotations

import os
import pathlib
import re

from .paths import get_username
from .types import TransformRecord


def _escape_regex(s: str) -> str:
    return re.escape(s)


def transform_to_placeholders(content: str) -> tuple[str, list[TransformRecord]]:
    username = get_username()
    records: list[TransformRecord] = []
    transformed = content

    # Windows paths: C:\Users\*\... -> {HOME}\...
    # Matches any username, not just the current one
    win_pattern = re.compile(r"C:\\Users\\[^\\]+\\", re.IGNORECASE)
    for m in win_pattern.finditer(transformed):
        records.append(TransformRecord(original=m.group(), placeholder="{HOME}\\"))
    transformed = win_pattern.sub(lambda _: "{HOME}\\", transformed)

    # Linux paths: /home/*/... -> {HOME}/...
    linux_pattern = re.compile(r"/home/[^/]+/")
    for m in linux_pattern.finditer(transformed):
        records.append(TransformRecord(original=m.group(), placeholder="{HOME}/"))
    transformed = linux_pattern.sub(lambda _: "{HOME}/", transformed)

    # macOS paths: /Users/*/... -> {HOME}/...
    mac_pattern = re.compile(r"/Users/[^/]+/")
    for m in mac_pattern.finditer(transformed):
        records.append(TransformRecord(original=m.group(), placeholder="{HOME}/"))
    transformed = mac_pattern.sub(lambda _: "{HOME}/", transformed)

    return transformed, records


def transform_from_placeholders(content: str, target_home: str) -> str:
    return content.replace("{HOME}", target_home)


def transform_file(
    source_path: str,
    target_path: str,
    is_import: bool,
    target_home: str | None = None,
) -> tuple[bool, list[TransformRecord]]:
    with open(source_path, encoding="utf-8") as f:
        content = f.read()

    if is_import:
        if not target_home:
            raise ValueError("Target home directory required for import transformation")
        transformed = transform_from_placeholders(content, target_home)
        records: list[TransformRecord] = []
    else:
        transformed, records = transform_to_placeholders(content)

    if transformed != content:
        target_dir = os.path.dirname(target_path)
        os.makedirs(target_dir, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(transformed)
        return True, records

    return False, records
