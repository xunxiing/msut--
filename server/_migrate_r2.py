"""Migrate local uploads to R2 + update DB url_path/stored_name.

Usage:
  python server/_migrate_r2.py

Reads from:
  - %TEMP%/msut_migrate/uploads/   (local files)
  - %TEMP%/msut_migrate/data/data/data.sqlite  (source DB)

Writes to:
  - R2 bucket (uploads/ prefix)
  - server/data/data.sqlite  (production DB, updated in place)
"""
import os
import sys
import sqlite3
import shutil
from pathlib import Path

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Load .env
from dotenv import load_dotenv
load_dotenv()

# Import R2 storage
from server.storage import upload_file, build_public_url, _get_client, R2_BUCKET

TMP = Path(os.environ.get("TEMP", "/tmp")) / "msut_migrate"
UPLOADS_DIR = TMP / "uploads"
SRC_DB = TMP / "data" / "data" / "data.sqlite"
DST_DB = Path("server/data/data.sqlite")

R2_PREFIX = "uploads/"
CDN_BASE = os.getenv("R2_PUBLIC_URL", "").rstrip("/")

print(f"Uploads dir: {UPLOADS_DIR} ({sum(1 for _ in UPLOADS_DIR.iterdir()) if UPLOADS_DIR.exists() else 0} files)")
print(f"Source DB:   {SRC_DB}")
print(f"Dest DB:    {DST_DB}")
print(f"CDN base:   {CDN_BASE}")
print()

# Copy source DB to production location
DST_DB.parent.mkdir(parents=True, exist_ok=True)
print(f"Copying {SRC_DB} -> {DST_DB} ...")
shutil.copy2(SRC_DB, DST_DB)
# Also copy WAL and SHM if they exist
for suffix in ["-wal", "-shm"]:
    src = Path(str(SRC_DB) + suffix)
    if src.exists():
        shutil.copy2(src, Path(str(DST_DB) + suffix))
        print(f"  copied {suffix}")
print("DB copied.\n")

# Open the production DB
conn = sqlite3.connect(str(DST_DB))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Run migrations to ensure schema is up to date
print("Running DB migrations...")
sys.path.insert(0, ".")
from server.db import run_migrations
run_migrations()
print("Migrations done.\n")

# Collect all file records
rows = cur.execute(
    "SELECT id, original_name, stored_name, url_path FROM resource_files"
).fetchall()
print(f"resource_files: {len(rows)} records")

# Collect avatars from users
users = cur.execute("SELECT id, avatar_url FROM users WHERE avatar_url IS NOT NULL AND avatar_url != ''").fetchall()
print(f"users with avatars: {len(users)}")

# Collect agent run result_paths
agent_files = cur.execute(
    "SELECT id, result_path FROM agent_runs WHERE result_path IS NOT NULL AND result_path != ''"
).fetchall()
print(f"agent_runs with result_path: {len(agent_files)}")

# R2 client
client = _get_client()
print(f"R2 client ready: bucket={R2_BUCKET}\n")

uploaded = 0
skipped = 0
errors = 0

# Migrate resource_files
for row in rows:
    fid = row["id"]
    stored = row["stored_name"]
    url_path = row["url_path"]

    # Skip if already migrated (stored_name contains /)
    if "/" in stored:
        print(f"  [skip] file {fid}: already R2 ({stored})")
        skipped += 1
        continue

    local_file = UPLOADS_DIR / stored
    if not local_file.exists():
        print(f"  [WARN] file {fid}: local file not found: {local_file}")
        errors += 1
        continue

    r2_key = f"uploads/{stored}"
    try:
        # Upload to R2
        client.upload_file(str(local_file), R2_BUCKET, r2_key)
        new_url = build_public_url(r2_key)
        cur.execute(
            "UPDATE resource_files SET stored_name = ?, url_path = ? WHERE id = ?",
            (r2_key, new_url, fid),
        )
        uploaded += 1
        if uploaded % 50 == 0:
            conn.commit()
            print(f"  ... {uploaded} files uploaded")
    except Exception as e:
        print(f"  [ERR] file {fid}: {e}")
        errors += 1

# Migrate user avatars
for u in users:
    uid = u["id"]
    avatar = u["avatar_url"]
    if avatar.startswith("http"):
        print(f"  [skip] user {uid}: avatar already CDN URL")
        continue
    if not avatar.startswith("/uploads/"):
        continue
    stored = avatar.replace("/uploads/", "")
    local_file = UPLOADS_DIR / stored
    if not local_file.exists():
        print(f"  [WARN] user {uid}: avatar file not found: {local_file}")
        errors += 1
        continue
    r2_key = f"avatars/{stored}"
    try:
        client.upload_file(str(local_file), R2_BUCKET, r2_key)
        new_url = build_public_url(r2_key)
        cur.execute(
            "UPDATE users SET avatar_url = ? WHERE id = ?",
            (new_url, uid),
        )
        uploaded += 1
    except Exception as e:
        print(f"  [ERR] user {uid}: {e}")
        errors += 1

# Migrate agent run result_paths
for a in agent_files:
    rid = a["id"]
    result_path = a["result_path"]
    if result_path.startswith("http"):
        continue
    if not result_path.startswith("/uploads/agent/"):
        continue
    stored = result_path.replace("/uploads/agent/", "")
    local_file = UPLOADS_DIR / "agent" / stored
    if not local_file.exists():
        print(f"  [WARN] agent_run {rid}: file not found: {local_file}")
        errors += 1
        continue
    r2_key = f"agent/{stored}"
    try:
        client.upload_file(str(local_file), R2_BUCKET, r2_key)
        new_url = build_public_url(r2_key)
        cur.execute(
            "UPDATE agent_runs SET result_path = ? WHERE id = ?",
            (new_url, rid),
        )
        uploaded += 1
    except Exception as e:
        print(f"  [ERR] agent_run {rid}: {e}")
        errors += 1

conn.commit()
print(f"\n=== MIGRATION COMPLETE ===")
print(f"Uploaded: {uploaded}")
print(f"Skipped:  {skipped}")
print(f"Errors:   {errors}")
print(f"Total:    {len(rows) + len(users) + len(agent_files)}")
