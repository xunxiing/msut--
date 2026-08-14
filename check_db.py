import sqlite3, os
db = 'server/data/data.sqlite'
print(f'DB size: {os.path.getsize(db) / 1024 / 1024:.1f} MB')
conn = sqlite3.connect(db)
for table in ['users','resources','resource_files','agent_runs','notifications']:
    try:
        c = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
        print(f'  {table}: {c} rows')
    except: pass
r2 = conn.execute("SELECT COUNT(*) FROM resource_files WHERE url_path LIKE 'http%'").fetchone()[0]
total = conn.execute('SELECT COUNT(*) FROM resource_files').fetchone()[0]
print(f'  resource_files with R2 URL: {r2}/{total}')
av = conn.execute("SELECT COUNT(*) FROM users WHERE avatar_url LIKE 'http%'").fetchone()[0]
avt = conn.execute("SELECT COUNT(*) FROM users WHERE avatar_url IS NOT NULL AND avatar_url != ''").fetchone()[0]
print(f'  avatars with R2 URL: {av}/{avt}')
