#!/bin/bash
set -e

python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.engram/engram.db')
cur = conn.cursor()
cur.execute('CREATE TABLE observations (id INTEGER PRIMARY KEY, sync_id TEXT, type TEXT, title TEXT, content TEXT, project TEXT, scope TEXT)')
cur.execute('CREATE TABLE sessions (id TEXT PRIMARY KEY, project TEXT, directory TEXT)')
cur.execute(\"INSERT INTO observations (sync_id, type, title, content, project, scope) VALUES ('obs-1', 'architecture', 'decision', 'Used /home/pedro/projects/myapp/src/auth.py for auth', 'myapp', 'project')\")
cur.execute(\"INSERT INTO observations (sync_id, type, title, content, project, scope) VALUES ('obs-2', 'bugfix', 'fix', 'Windows path C:\\\\Users\\\\Juan\\\\code\\\\api\\\\main.py was broken', 'api', 'project')\")
cur.execute(\"INSERT INTO sessions (id, project, directory) VALUES ('ses-1', 'myapp', '/home/pedro/projects/myapp')\")
conn.commit()
conn.close()
print('Created mock engram DB with cross-user paths')
"
