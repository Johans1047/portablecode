from __future__ import annotations

import getpass
import os
import platform
import pathlib


def get_home_dir() -> str:
    return str(pathlib.Path.home())


def get_config_dir() -> str:
    return str(pathlib.Path.home() / ".config" / "opencode")


def get_data_dir() -> str:
    return str(pathlib.Path.home() / ".local" / "share" / "opencode")


def get_engram_dir() -> str:
    system = platform.system()
    home = pathlib.Path.home()

    if system == "Windows":
        return str(home / "AppData" / "Local" / "engram")
    elif system == "Darwin":
        return str(home / "Library" / "Application Support" / "engram")
    else:
        return str(home / ".local" / "share" / "engram")


def get_engram_data_dir() -> str:
    return str(pathlib.Path.home() / ".engram")


def get_platform() -> str:
    return platform.system().lower()


def get_username() -> str:
    return getpass.getuser()


def normalize_path(p: str) -> str:
    return p.replace("\\", "/")


def to_relative(absolute_path: str, base_path: str) -> str:
    norm_abs = normalize_path(absolute_path)
    norm_base = normalize_path(base_path)

    if norm_abs.startswith(norm_base):
        return norm_abs[len(norm_base) + 1:]
    return norm_abs
