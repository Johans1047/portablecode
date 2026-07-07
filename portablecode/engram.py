from __future__ import annotations

import os
import re
import shutil
import sqlite3


def _escape_regex(s: str) -> str:
    return re.escape(s)


def _transform_paths_in_db(db_path: str, target_home: str, export_mode: bool) -> dict[str, int]:
    """Transform absolute paths in the engram SQLite database.

    export_mode=True:  replace machine paths with {HOME}
    export_mode=False: replace {HOME} with target_home

    Returns a dict of table -> rows affected.
    """
    if not os.path.isfile(db_path):
        return {}

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    affected: dict[str, int] = {}

    if export_mode:
        # Build replacement patterns — match ANY username (not just current)
        # Use lambdas for replacement to avoid re.sub backslash interpretation issues
        replacements = [
            (re.compile(r"C:\\Users\\[^\\]+\\"), lambda _: "{HOME}\\"),
            (re.compile(r"/home/[^/]+/"), lambda _: "{HOME}/"),
            (re.compile(r"/Users/[^/]+/"), lambda _: "{HOME}/"),
        ]

        # Tables and columns that contain paths
        path_columns = [
            ("sessions", ["directory"]),
            ("observations", ["content"]),
            ("user_prompts", ["content"]),
            ("sync_mutations", ["payload"]),
        ]

        for table, columns in path_columns:
            try:
                cur.execute(f"SELECT rowid, {', '.join(columns)} FROM [{table}]")
                rows = cur.fetchall()
            except sqlite3.OperationalError:
                continue

            updates = []
            for row in rows:
                rowid = row[0]
                new_values = []
                changed = False
                for i, col_value in enumerate(row[1:], 1):
                    if col_value is None:
                        new_values.append(None)
                        continue
                    val = str(col_value)
                    for pattern, repl_fn in replacements:
                        if pattern.search(val):
                            val = pattern.sub(repl_fn, val)
                            changed = True
                    new_values.append(val)
                if changed:
                    updates.append((*new_values, rowid))

            if updates:
                set_clause = ", ".join(f"{col} = ?" for col in columns)
                cur.executemany(
                    f"UPDATE [{table}] SET {set_clause} WHERE rowid = ?",
                    updates,
                )
                affected[table] = len(updates)

    else:
        # Import mode: replace {HOME} with target_home
        path_columns = [
            ("sessions", ["directory"]),
            ("observations", ["content"]),
            ("user_prompts", ["content"]),
            ("sync_mutations", ["payload"]),
        ]

        for table, columns in path_columns:
            try:
                cur.execute(f"SELECT rowid, {', '.join(columns)} FROM [{table}]")
                rows = cur.fetchall()
            except sqlite3.OperationalError:
                continue

            updates = []
            for row in rows:
                rowid = row[0]
                new_values = []
                changed = False
                for i, col_value in enumerate(row[1:], 1):
                    if col_value is None:
                        new_values.append(None)
                        continue
                    val = str(col_value)
                    if "{HOME}" in val:
                        val = val.replace("{HOME}", target_home)
                        changed = True
                    new_values.append(val)
                if changed:
                    updates.append((*new_values, rowid))

            if updates:
                set_clause = ", ".join(f"{col} = ?" for col in columns)
                cur.executemany(
                    f"UPDATE [{table}] SET {set_clause} WHERE rowid = ?",
                    updates,
                )
                affected[table] = len(updates)

    conn.commit()
    conn.close()
    return affected


def export_engram_db(source_path: str, target_path: str) -> dict[str, int]:
    """Copy engram DB and transform absolute paths to {HOME} placeholders."""
    target_dir = os.path.dirname(target_path)
    os.makedirs(target_dir, exist_ok=True)
    shutil.copy2(source_path, target_path)
    return _transform_paths_in_db(target_path, "", export_mode=True)


def import_engram_db(source_path: str, target_path: str, target_home: str) -> dict[str, int]:
    """Copy engram DB and replace {HOME} placeholders with target home."""
    target_dir = os.path.dirname(target_path)
    os.makedirs(target_dir, exist_ok=True)
    shutil.copy2(source_path, target_path)
    return _transform_paths_in_db(target_path, target_home, export_mode=False)
