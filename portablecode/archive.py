from __future__ import annotations

import io
import json
import os
import pathlib
import shutil
import tarfile
import tempfile

from .paths import get_platform, get_engram_data_dir
from .transform import transform_to_placeholders
from .types import ArchiveManifest, FileEntry, TransformRecord


def _copy_directory_recursive(src: str, dest: str) -> None:
    os.makedirs(dest, exist_ok=True)
    for entry in os.scandir(src):
        src_path = entry.path
        dest_path = os.path.join(dest, entry.name)
        if entry.is_dir(follow_symlinks=False):
            _copy_directory_recursive(src_path, dest_path)
        else:
            shutil.copy2(src_path, dest_path)


def create_archive(files: list[FileEntry], output_path: str, include_engram: bool = False) -> None:
    manifest = ArchiveManifest(
        version="1.0.0",
        created_at=__import__("datetime").datetime.utcnow().isoformat() + "Z",
        platform=get_platform(),
    )

    output_dir = os.path.dirname(output_path) or "."
    temp_dir = os.path.join(output_dir, ".portablecode-temp")

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)

    try:
        for file in files:
            if file.action in ("skip", "install-separately"):
                continue

            target_path = os.path.join(temp_dir, file.relative_path)
            target_dir = os.path.dirname(target_path)
            os.makedirs(target_dir, exist_ok=True)

            if file.action == "transform":
                with open(file.path, encoding="utf-8") as f:
                    content = f.read()
                transformed, records = transform_to_placeholders(content)
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(transformed)
                manifest.transformed_paths.extend(records)
            elif os.path.isdir(file.path):
                _copy_directory_recursive(file.path, target_path)
            else:
                shutil.copy2(file.path, target_path)

            manifest.files.append(file)

        # Handle engram database
        if include_engram:
            engram_db = os.path.join(get_engram_data_dir(), "engram.db")
            if os.path.isfile(engram_db):
                from .engram import export_engram_db

                engram_target = os.path.join(temp_dir, ".engram", "engram.db")
                affected = export_engram_db(engram_db, engram_target)
                engram_size = os.path.getsize(engram_db)
                manifest.files.append(FileEntry(
                    path=engram_db,
                    relative_path=".engram/engram.db",
                    tier=2,
                    size=engram_size,
                    action="transform-engram",
                ))
                for table, count in affected.items():
                    manifest.transformed_paths.append(TransformRecord(
                        original=f"[engram:{table}]",
                        placeholder=f"{count} rows transformed",
                    ))

        # Write manifest
        manifest_path = os.path.join(temp_dir, "manifest.json")
        manifest_data = {
            "version": manifest.version,
            "created_at": manifest.created_at,
            "platform": manifest.platform,
            "files": [
                {
                    "path": f.path,
                    "relative_path": f.relative_path,
                    "tier": int(f.tier),
                    "size": f.size,
                    "action": f.action,
                }
                for f in manifest.files
            ],
            "transformed_paths": [
                {"original": t.original, "placeholder": t.placeholder}
                for t in manifest.transformed_paths
            ],
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        # Create tar.gz
        with tarfile.open(output_path, "w:gz") as tar:
            tar.add(temp_dir, arcname=".")

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def _file_entry_from_dict(d: dict) -> FileEntry:
    from .types import Tier
    return FileEntry(
        path=d["path"],
        relative_path=d["relative_path"],
        tier=Tier(d["tier"]),
        size=d["size"],
        action=d["action"],
    )


def _transform_record_from_dict(d: dict) -> TransformRecord:
    return TransformRecord(original=d["original"], placeholder=d["placeholder"])


def extract_archive(
    archive_path: str, target_dir: str, force: bool = False
) -> ArchiveManifest:
    if not os.path.isfile(archive_path):
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    if os.path.exists(target_dir) and not force:
        raise FileExistsError(
            f"Target directory already exists: {target_dir}. Use --force to overwrite."
        )

    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)

    os.makedirs(target_dir, exist_ok=True)

    with tarfile.open(archive_path, "r:*") as tar:
        tar.extractall(path=target_dir, filter="data")

    manifest_path = os.path.join(target_dir, "manifest.json")
    if not os.path.isfile(manifest_path):
        raise ValueError("Invalid archive: missing manifest.json")

    with open(manifest_path, encoding="utf-8") as f:
        data = json.load(f)

    return ArchiveManifest(
        version=data.get("version", "1.0.0"),
        created_at=data.get("created_at", ""),
        platform=data.get("platform", ""),
        files=[_file_entry_from_dict(fd) for fd in data.get("files", [])],
        transformed_paths=[
            _transform_record_from_dict(td) for td in data.get("transformed_paths", [])
        ],
    )


def list_archive_contents(archive_path: str) -> ArchiveManifest:
    if not os.path.isfile(archive_path):
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    temp_dir = tempfile.mkdtemp(prefix=".portablecode-list-")

    try:
        with tarfile.open(archive_path, "r:*") as tar:
            tar.extractall(path=temp_dir, filter="data")

        manifest_path = os.path.join(temp_dir, "manifest.json")
        if not os.path.isfile(manifest_path):
            raise ValueError("Invalid archive: missing manifest.json")

        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)

        return ArchiveManifest(
            version=data.get("version", "1.0.0"),
            created_at=data.get("created_at", ""),
            platform=data.get("platform", ""),
            files=[_file_entry_from_dict(fd) for fd in data.get("files", [])],
            transformed_paths=[
                _transform_record_from_dict(td)
                for td in data.get("transformed_paths", [])
            ],
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
