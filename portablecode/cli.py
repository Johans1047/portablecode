from __future__ import annotations

import os
import pathlib
import sys

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from . import __version__
from .archive import create_archive, extract_archive, list_archive_contents
from .discover import discover_files, format_file_size
from .paths import get_config_dir, get_data_dir, get_home_dir, get_platform
from .transform import transform_from_placeholders
from .types import (
    FileEntry,
    TIER_INFO,
    DiffResult,
    DiffChangedFile,
    Tier,
)

console = Console()


def _group_by_tier(files: list[FileEntry]) -> dict[int, list[FileEntry]]:
    groups: dict[int, list[FileEntry]] = {}
    for f in files:
        groups.setdefault(int(f.tier), []).append(f)
    return groups


def _print_tier_files(tier: int, files: list[FileEntry]) -> None:
    info = TIER_INFO[tier]
    color = {1: "green", 2: "yellow", 3: "dark_orange", 4: "red", 5: "dim"}[tier]
    console.print(f"\n  [bold {color}]Tier {tier}: {info['name']}[/]")
    for f in files:
        console.print(f"    [dim]{f.relative_path} ({format_file_size(f.size)})[/]")


# ─── EXPORT ────────────────────────────────────────────────────────────────────

@click.command()
@click.option("-o", "--output", default=None, help="Output file path")
@click.option("--include-auth", is_flag=True, default=False, help="Include sensitive auth.json")
@click.option("--include-db", is_flag=True, default=False, help="Include opencode.db database")
@click.option("--include-binaries", is_flag=True, default=False, help="Include Tier 3 binaries (same OS only)")
@click.option("--include-engram", is_flag=True, default=False, help="Include engram/gentle-ai memory database (paths will be transformed)")
def export(output: str | None, include_auth: bool, include_db: bool, include_binaries: bool, include_engram: bool) -> None:
    """Export current OpenCode configuration to an archive."""
    console.print(Panel("[bold blue]OpenCode Config Export[/]", box=box.ROUNDED))

    files = discover_files()
    config_dir = get_config_dir()

    filtered: list[FileEntry] = []
    for f in files:
        if f.action == "skip":
            continue
        if f.action == "sensitive" and not include_auth:
            console.print(f"  [yellow]Skipping sensitive file: {f.relative_path}[/]")
            continue
        if f.action == "install-separately":
            if not include_binaries:
                console.print(f"  [yellow]Skipping install-separately: {f.relative_path}[/]")
                continue
            else:
                f = FileEntry(
                    path=f.path,
                    relative_path=f.relative_path,
                    tier=f.tier,
                    size=f.size,
                    action="copy",
                )
        filtered.append(f)

    if include_binaries:
        binary_count = sum(1 for f in filtered if f.tier == Tier.INSTALL_SEPARATELY)
        if binary_count:
            console.print(
                f"\n[yellow]Including {binary_count} binary file(s). "
                "These only work on the same OS — they won't run on a different platform.[/]"
            )

    if not include_db:
        db_files = [f for f in filtered if f.relative_path == "opencode.db"]
        for db in db_files:
            console.print(
                f"  [yellow]Skipping database file: {db.relative_path} ({format_file_size(db.size)})[/]"
            )
            filtered.remove(db)

    console.print(f"\n[green]Found {len(filtered)} files to export:[/]")

    tier_counts = _group_by_tier(filtered)
    for tier_num in sorted(tier_counts):
        info = TIER_INFO[tier_num]
        count = len(tier_counts[tier_num])
        color = {1: "green", 2: "yellow", 3: "dark_orange", 4: "red", 5: "dim"}[tier_num]
        console.print(f"  [{color}]Tier {tier_num}: {count} files ({info['name']})[/]")

    out_path = output or os.path.join(config_dir, "..", "portablecode.portablecode")
    console.print(f"\n[dim]Output: {out_path}[/]")

    try:
        create_archive(filtered, out_path, include_engram=include_engram)
        size = os.path.getsize(out_path)
        console.print(f"\n[bold green]Archive created successfully![/]")
        console.print(f"   [dim]Size: {format_file_size(size)}[/]")
        if include_engram:
            from .paths import get_engram_data_dir
            engram_db = os.path.join(get_engram_data_dir(), "engram.db")
            if os.path.isfile(engram_db):
                console.print(f"   [dim]Engram memory: included (paths transformed)[/]")
        console.print(f"\n[dim]To import on another machine:[/]")
        console.print(f"   [cyan]portablecode import {os.path.basename(out_path)}[/]")
    except Exception as e:
        console.print(f"\n[bold red]Failed to create archive: {e}[/]")
        sys.exit(1)


# ─── IMPORT ────────────────────────────────────────────────────────────────────

@click.command()
@click.argument("archive")
@click.option("-f", "--force", is_flag=True, default=False, help="Overwrite existing files")
@click.option("--skip-auth", is_flag=True, default=False, help="Skip sensitive auth.json")
def import_cmd(archive: str, force: bool, skip_auth: bool) -> None:
    """Import OpenCode configuration from an archive."""
    console.print(Panel("[bold blue]OpenCode Config Import[/]", box=box.ROUNDED))

    if not os.path.isfile(archive):
        console.print(f"[red]Archive not found: {archive}[/]")
        sys.exit(1)

    config_dir = get_config_dir()
    data_dir = get_data_dir()
    home_dir = get_home_dir()
    engram_staging_exists = False

    temp_dir = os.path.join(os.path.dirname(archive) or ".", ".portablecode-import-temp")

    try:
        console.print("[dim]Extracting archive...[/]")
        manifest = extract_archive(archive, temp_dir, force)

        console.print("[green]Archive extracted successfully![/]")
        console.print(f"   [dim]Created: {manifest.created_at}[/]")
        console.print(f"   [dim]Source platform: {manifest.platform}[/]")
        console.print(f"   [dim]Current platform: {get_platform()}[/]")

        files_to_import = manifest.files
        if skip_auth:
            files_to_import = [f for f in files_to_import if f.action != "sensitive"]
            # Also print skipped ones
            for f in manifest.files:
                if f.action == "sensitive":
                    console.print(f"  [yellow]Skipping sensitive file: {f.relative_path}[/]")

        console.print(f"\n[dim]Importing {len(files_to_import)} files...[/]")

        for f in files_to_import:
            source_path = os.path.join(temp_dir, f.relative_path)
            target_path = _get_target_path(f, config_dir, data_dir)

            if not os.path.exists(source_path):
                console.print(f"  [yellow]Source not found: {f.relative_path}[/]")
                continue

            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            if f.action == "transform":
                with open(source_path, encoding="utf-8") as fh:
                    content = fh.read()
                transformed = transform_from_placeholders(content, home_dir)
                with open(target_path, "w", encoding="utf-8") as fh:
                    fh.write(transformed)
                console.print(f"  [cyan]{f.relative_path} (transformed)[/]")
            elif f.action == "transform-engram":
                from .engram import import_engram_db
                from .paths import get_engram_data_dir
                engram_dir = get_engram_data_dir()
                engram_target = os.path.join(engram_dir, "engram.db")
                engram_staging = os.path.join(engram_dir, "engram-import.db")
                os.makedirs(engram_dir, exist_ok=True)

                # Import to staging file (original may be locked by running engram)
                affected = import_engram_db(source_path, engram_staging, home_dir)
                total_rows = sum(affected.values())
                console.print(
                    f"  [cyan]{f.relative_path} (engram memory: {total_rows} rows)[/]"
                )
                console.print(
                    f"  [yellow]  -> Saved to: {engram_staging}[/]"
                )
                engram_staging_exists = True
            else:
                import shutil
                if os.path.isdir(source_path):
                    if os.path.exists(target_path):
                        shutil.rmtree(target_path)
                    shutil.copytree(source_path, target_path)
                else:
                    shutil.copy2(source_path, target_path)
                console.print(f"  [green]{f.relative_path}[/]")

        console.print("\n[bold green]Import completed successfully![/]")

        # Post-install instructions
        console.print(Panel("[bold blue]Post-Install Instructions[/]", box=box.ROUNDED))

        if manifest.platform != get_platform():
            console.print("[yellow]Source platform differs from target platform.[/]")
            console.print("[yellow]Some configurations may need manual adjustment.[/]")

        console.print("\n[cyan]1.[/] Restart OpenCode to apply changes:")
        console.print("   [dim]opencode[/]")

        if engram_staging_exists:
            from .paths import get_engram_data_dir
            engram_dir = get_engram_data_dir()
            console.print("\n[cyan]2.[/] Restore engram memory:")
            console.print("   [dim]a) Install gentle-ai/engram on this machine first (if not already)[/]")
            console.print(f"   [dim]b) Stop engram, then run:[/]")
            console.print(f"   [dim]move \"{os.path.join(engram_dir, 'engram-import.db')}\" \"{os.path.join(engram_dir, 'engram.db')}\"[/]")
            console.print(f"   [dim]c) Restart engram and OpenCode[/]")

        console.print("\n[cyan]3.[/] Verify your configuration:")
        console.print("   [dim]opencode config --list[/]")

    except Exception as e:
        console.print(f"\n[bold red]Import failed: {e}[/]")
        sys.exit(1)
    finally:
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


def _get_target_path(f: FileEntry, config_dir: str, data_dir: str) -> str:
    config_prefixes = ("skills/", "plugins/", "commands/", "tui-plugins/")
    config_names = ("opencode.json", "tui.json", "opencode-notifier.json", "auth.json")
    image_exts = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico")

    rp = f.relative_path
    if (
        rp.startswith(config_prefixes)
        or rp in config_names
        or rp in ("AGENTS.md", ".gitignore")
        or any(rp.endswith(ext) for ext in image_exts)
    ):
        return os.path.join(config_dir, rp)

    return os.path.join(data_dir, rp)


# ─── LIST ──────────────────────────────────────────────────────────────────────

@click.command()
@click.option("-a", "--archive", default=None, help="List files from an archive")
def list(archive: str | None) -> None:
    """List files that would be migrated."""
    console.print(Panel("[bold blue]OpenCode Config Files[/]", box=box.ROUNDED))

    if archive:
        console.print(f"\n[dim]Reading archive: {archive}[/]")
        try:
            manifest = list_archive_contents(archive)
            console.print("\n[green]Archive contents:[/]")
            console.print(f"   [dim]Created: {manifest.created_at}[/]")
            console.print(f"   [dim]Platform: {manifest.platform}[/]")
            console.print(f"   [dim]Files: {len(manifest.files)}[/]")

            groups = _group_by_tier(manifest.files)
            for tier_num in sorted(groups):
                _print_tier_files(tier_num, groups[tier_num])

            total = sum(f.size for f in manifest.files)
            console.print(f"\n  [blue]Total size: {format_file_size(total)}[/]")
        except Exception as e:
            console.print(f"\n[red]Failed to read archive: {e}[/]")
            sys.exit(1)
    else:
        files = discover_files()
        console.print(f"\n[green]Found {len(files)} files in current configuration:[/]")

        groups = _group_by_tier(files)
        for tier_num in sorted(groups):
            _print_tier_files(tier_num, groups[tier_num])

        total = sum(f.size for f in files)
        console.print(f"\n  [blue]Total size: {format_file_size(total)}[/]")

        console.print("\n  [dim]Actions:[/]")
        action_counts: dict[str, int] = {}
        for f in files:
            action_counts[f.action] = action_counts.get(f.action, 0) + 1
        for action, count in action_counts.items():
            console.print(f"    [dim]{action}: {count} files[/]")


# ─── DIFF ──────────────────────────────────────────────────────────────────────

@click.command()
@click.argument("archive")
def diff(archive: str) -> None:
    """Compare current configuration with an archive."""
    console.print(Panel("[bold blue]OpenCode Config Diff[/]", box=box.ROUNDED))

    if not os.path.isfile(archive):
        console.print(f"[red]Archive not found: {archive}[/]")
        sys.exit(1)

    console.print(f"\n[dim]Archive: {archive}[/]")

    try:
        manifest = list_archive_contents(archive)
        current_files = discover_files()

        console.print(f"[dim]Archive files: {len(manifest.files)}[/]")
        console.print(f"[dim]Current files: {len(current_files)}[/]")

        result = DiffResult()

        current_by_path = {f.relative_path: f for f in current_files}

        for archive_file in manifest.files:
            current_file = current_by_path.get(archive_file.relative_path)
            if not current_file:
                result.missing.append(archive_file)
            elif current_file.size != archive_file.size:
                result.changed.append(DiffChangedFile(
                    archive=archive_file,
                    current=current_file,
                    size_diff=current_file.size - archive_file.size,
                ))

        archive_paths = {f.relative_path for f in manifest.files}
        for current_file in current_files:
            if (
                current_file.relative_path not in archive_paths
                and current_file.action not in ("skip", "install-separately")
            ):
                result.extra.append(current_file)

        console.print("\n[bold green]Diff Results:[/]")

        if not result.missing and not result.extra and not result.changed:
            console.print("\n  [green]No differences found! Configurations are identical.[/]")
            return

        if result.missing:
            console.print(
                f"\n  [yellow]Files in archive but NOT in current config ({len(result.missing)}):[/]"
            )
            for f in result.missing:
                console.print(f"    [dim]- {f.relative_path} ({format_file_size(f.size)})[/]")

        if result.extra:
            console.print(
                f"\n  [cyan]Files in current config but NOT in archive ({len(result.extra)}):[/]"
            )
            for f in result.extra:
                console.print(f"    [dim]+ {f.relative_path} ({format_file_size(f.size)})[/]")

        if result.changed:
            console.print(
                f"\n  [magenta]Files with different sizes ({len(result.changed)}):[/]"
            )
            for d in result.changed:
                sign = "+" if d.size_diff > 0 else "-"
                diff_str = f"{sign}{format_file_size(abs(d.size_diff))}"
                console.print(f"    [dim]~ {d.archive.relative_path}[/]")
                console.print(f"      [dim]Archive: {format_file_size(d.archive.size)}[/]")
                console.print(
                    f"      [dim]Current: {format_file_size(d.current.size)} ({diff_str})[/]"
                )

        console.print("\n  [blue]Summary:[/]")
        console.print(f"    [dim]Missing: {len(result.missing)} files[/]")
        console.print(f"    [dim]Extra: {len(result.extra)} files[/]")
        console.print(f"    [dim]Changed: {len(result.changed)} files[/]")

        if result.missing:
            console.print("\n  [yellow]To import missing files, run:[/]")
            console.print(f"    [cyan]portablecode import {archive}[/]")

    except Exception as e:
        console.print(f"\n[red]Failed to compare: {e}[/]")
        sys.exit(1)


# ─── CLI GROUP ─────────────────────────────────────────────────────────────────

@click.group()
@click.version_option(__version__, prog_name="portablecode")
def cli() -> None:
    """Migrate OpenCode configuration between PCs."""


cli.add_command(export)
cli.add_command(import_cmd, name="import")
cli.add_command(list, name="list")
cli.add_command(diff)


if __name__ == "__main__":
    cli()
