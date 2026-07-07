from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Literal


class Tier(IntEnum):
    COPY = 1
    TRANSFORM = 2
    INSTALL_SEPARATELY = 3
    SENSITIVE = 4
    SKIP = 5


TIER_INFO: dict[int, dict[str, str]] = {
    Tier.COPY: {"name": "Copy as-is", "description": "Will be copied without modification"},
    Tier.TRANSFORM: {"name": "Transform", "description": "Path placeholders will be applied"},
    Tier.INSTALL_SEPARATELY: {"name": "Install separately", "description": "Must be installed on target system"},
    Tier.SENSITIVE: {"name": "Sensitive", "description": "Contains credentials (opt-in)"},
    Tier.SKIP: {"name": "Skip", "description": "Will not be included in archive"},
}

TIER1_PATTERNS = [
    "AGENTS.md",
    "skills/**",
    "plugins/**",
    "commands/**",
    "tui-plugins/**",
    ".gitignore",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.svg",
    "*.ico",
]

TIER2_PATTERNS = [
    "opencode.json",
    "tui.json",
    "opencode-notifier.json",
]

TIER3_PATTERNS = [
    "engram.exe",
    "engram",
    "codebase-memory-mcp.exe",
    "codebase-memory-mcp",
]

TIER4_PATTERNS = [
    "auth.json",
]

TIER5_PATTERNS = [
    "node_modules/**",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "opencode.db",
    "opencode.db-wal",
    "opencode.db-shm",
    "snapshot/**",
    "delegations/**",
    "log/**",
    "storage/**",
    "tool-output/**",
    ".engram/**",
]


Action = Literal["copy", "transform", "skip", "install-separately", "sensitive"]


@dataclass
class FileEntry:
    path: str
    relative_path: str
    tier: Tier
    size: int
    action: Action


@dataclass
class TransformRecord:
    original: str
    placeholder: str


@dataclass
class ArchiveManifest:
    version: str = "1.0.0"
    created_at: str = ""
    platform: str = ""
    files: list[FileEntry] = field(default_factory=list)
    transformed_paths: list[TransformRecord] = field(default_factory=list)


@dataclass
class DiffChangedFile:
    archive: FileEntry
    current: FileEntry
    size_diff: int


@dataclass
class DiffResult:
    missing: list[FileEntry] = field(default_factory=list)
    extra: list[FileEntry] = field(default_factory=list)
    changed: list[DiffChangedFile] = field(default_factory=list)
