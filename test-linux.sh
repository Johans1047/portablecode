#!/bin/bash
set -e

echo "============================================="
echo "  portablecode — FULL CONTAINER TEST (Linux)"
echo "============================================="
echo ""

echo "--- Machine Info ---"
echo "User:    $(whoami)"
echo "Home:    $HOME"
echo "OS:      $(uname -sr)"
echo "Python:  $(python3 --version)"
echo ""

echo "--- Mock Data Setup ---"
echo "Config dir:  ~/.config/opencode/ ($(find ~/.config/opencode -type f | wc -l) files)"
echo "Data dir:    ~/.local/share/opencode/ ($(find ~/.local/share/opencode -type f 2>/dev/null | wc -l) files)"
echo "Engram DB:   ~/.engram/engram.db ($(du -h ~/.engram/engram.db | cut -f1))"
echo ""

echo "--- [1/5] LIST current config ---"
python3 -m portablecode.cli list
echo ""

echo "--- [2/5] Engram DB raw contents (BEFORE export) ---"
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.engram/engram.db')
cur = conn.cursor()
print('Sessions:')
cur.execute('SELECT id, project, directory FROM sessions')
for r in cur.fetchall(): print(f'  {r}')
print()
print('Observations:')
cur.execute('SELECT id, content FROM observations')
for r in cur.fetchall(): print(f'  [{r[0]}] {r[1]}')
conn.close()
"
echo ""

echo "--- [3/5] EXPORT with --include-engram ---"
python3 -m portablecode.cli export -o /tmp/export.portablecode --include-engram
echo ""

echo "--- [4/5] Inspect archive + verify path transformation ---"
python3 -c "
import tarfile, json, sqlite3, os, tempfile, shutil

print('=== Archive Contents ===')
with tarfile.open('/tmp/export.portablecode', 'r:*') as t:
    manifest = json.load(t.extractfile('./manifest.json'))
    print(f'Version:     {manifest[\"version\"]}')
    print(f'Platform:    {manifest[\"platform\"]}')
    print(f'Created:     {manifest[\"created_at\"]}')
    print(f'Files:       {len(manifest[\"files\"])}')
    for f in manifest['files']:
        tier_label = {1:'T1-copy', 2:'T2-transform', 3:'T3-binary', 4:'T4-sensitive', 5:'T5-exclude'}[f['tier']]
        print(f'  [{tier_label:11s}] {f[\"relative_path\"]}')
    tp = manifest.get('transformed_paths', [])
    print(f'Transformed: {len(tp)} paths')
    for rec in tp[:5]:
        print(f'  \"{rec[\"original\"]}\" -> \"{rec[\"placeholder\"]}\"')
    if len(tp) > 5:
        print(f'  ... and {len(tp)-5} more')
    print()
    print('Archive entries:')
    for m in t.getmembers():
        print(f'  {m.name:40s} ({m.size:>6} bytes)')

print()
print('=== Verify Engram DB inside archive ===')
tmpdir = tempfile.mkdtemp()
with tarfile.open('/tmp/export.portablecode', 'r:*') as t:
    t.extractall(path=tmpdir)
    db = os.path.join(tmpdir, '.engram', 'engram.db')
    conn = sqlite3.connect(db)
    cur = conn.cursor()

    all_ok = True
    print('Observations:')
    cur.execute('SELECT id, content FROM observations')
    for r in cur.fetchall():
        has_home = '{HOME}' in r[1]
        status = 'OK' if has_home else 'FAIL'
        print(f'  [{r[0]}] {r[1]}  ... {status}')
        if not has_home: all_ok = False

    print('Sessions:')
    cur.execute('SELECT id, directory FROM sessions')
    for r in cur.fetchall():
        has_home = '{HOME}' in r[1]
        status = 'OK' if has_home else 'FAIL'
        print(f'  [{r[0]}] {r[1]}  ... {status}')
        if not has_home: all_ok = False

    conn.close()
    shutil.rmtree(tmpdir)

    if all_ok:
        print()
        print('ALL PATHS TRANSFORMED CORRECTLY')
    else:
        print()
        print('SOME PATHS NOT TRANSFORMED!')
        exit(1)
"
echo ""

echo "--- [5/5] IMPORT (fresh install simulation) ---"
# Wipe existing config to simulate fresh machine
rm -rf /root/.config/opencode/skills
rm -rf /root/.config/opencode/plugins
rm -rf /root/.config/opencode/commands
rm -f /root/.config/opencode/opencode.json
rm -f /root/.config/opencode/AGENTS.md
rm -rf /root/.engram

echo "Config before import: $(find /root/.config/opencode -type f 2>/dev/null | wc -l) files"
echo "Engram before import: $(ls /root/.engram/engram.db 2>/dev/null && echo 'exists' || echo 'none')"
echo ""

python3 -m portablecode.cli import /tmp/export.portablecode
echo ""

echo "--- Engram DB after import ({HOME} -> /root) ---"
python3 -c "
import sqlite3, os
# Import saves to staging file
db_path = '/root/.engram/engram-import.db'
if not os.path.isfile(db_path):
    db_path = '/root/.engram/engram.db'
print(f'Reading: {db_path}')
conn = sqlite3.connect(db_path)
cur = conn.cursor()
print('Sessions:')
cur.execute('SELECT id, project, directory FROM sessions')
for r in cur.fetchall(): print(f'  {r}')
print()
print('Observations:')
cur.execute('SELECT id, content FROM observations')
for r in cur.fetchall(): print(f'  [{r[0]}] {r[1]}')
conn.close()
"
echo ""

echo "--- Imported file tree ---"
find /root/.config/opencode /root/.local/share/opencode /root/.engram -type f 2>/dev/null | sort | while read f; do
    size=$(du -h "$f" | cut -f1)
    echo "  $size  $f"
done
echo ""

echo "============================================="
echo "  ALL TESTS PASSED"
echo "============================================="
