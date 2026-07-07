import tarfile
import json
import sqlite3
import os
import tempfile
import shutil

with tarfile.open("/tmp/test.portablecode", "r:*") as t:
    manifest = json.load(t.extractfile("./manifest.json"))

    tmpdir = tempfile.mkdtemp()
    t.extractall(path=tmpdir)
    db = os.path.join(tmpdir, ".engram", "engram.db")

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    print("Observations after export:")
    cur.execute("SELECT id, content FROM observations")
    for row in cur.fetchall():
        print(f"  [{row[0]}] {row[1]}")
        assert "{HOME}" in row[1], f"FAIL: obs {row[0]} not transformed!"

    print("Sessions after export:")
    cur.execute("SELECT id, directory FROM sessions")
    for row in cur.fetchall():
        print(f"  [{row[0]}] {row[1]}")
        assert "{HOME}" in row[1], f"FAIL: session {row[0]} not transformed!"

    conn.close()
    shutil.rmtree(tmpdir)
