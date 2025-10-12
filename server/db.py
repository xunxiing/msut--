import os
import sqlite3
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parent
# 尝试使用环境变量中指定的数据库路径，如果不存在则使用默认路径
data_dir = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
DB_FILE = data_dir / "data.sqlite"


def _ensure_db_file() -> None:
    # 确保数据目录存在
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    # 确保数据库文件存在
    if not DB_FILE.exists():
        DB_FILE.touch()
        print(f"Created new database file at {DB_FILE}")


def get_connection() -> sqlite3.Connection:
    _ensure_db_file()
    db_path = str(DB_FILE)
    try:
        conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
    except sqlite3.OperationalError as e:
        # Extra diagnostics to help in containerized deployments
        try:
            print(f"[db] connect failed to {db_path}: {e}")
            print(f"[db] ensuring parent dir exists: {DB_FILE.parent}")
            DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        except Exception as _:
            pass
        # Attempt to (re)create the file if it doesn't exist
        try:
            Path(db_path).touch(exist_ok=True)
        except Exception as _:
            pass
        # Final attempt using URI with rwc (read-write-create)
        conn = sqlite3.connect(f"file:{db_path}?mode=rwc", uri=True, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def run_migrations(conn: Optional[sqlite3.Connection] = None) -> None:
    owns = False
    if conn is None:
        print(f"Running migrations on database: {DB_FILE}")
        conn = get_connection()
        owns = True
    try:
        cur = conn.cursor()
        # Check if migration from email->username is needed
        cur.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='users' AND sql LIKE '%email TEXT NOT NULL UNIQUE%'
            """
        )
        row = cur.fetchone()
        if row is not None:
            print("Executing DB migration: email -> username for users table")
            cur.executescript(
                """
                CREATE TABLE IF NOT EXISTS users_new (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT NOT NULL UNIQUE,
                  password_hash TEXT NOT NULL,
                  name TEXT NOT NULL,
                  created_at TEXT NOT NULL DEFAULT (datetime('now')),
                  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                INSERT INTO users_new (id, username, password_hash, name, created_at, updated_at)
                SELECT id, email, password_hash, name, created_at, updated_at FROM users;

                DROP TABLE users;
                ALTER TABLE users_new RENAME TO users;
                """
            )
            print("DB migration completed")

        # Initialize schema
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL UNIQUE,
              password_hash TEXT NOT NULL,
              name TEXT NOT NULL,
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TRIGGER IF NOT EXISTS trg_users_updated_at
            AFTER UPDATE ON users
            FOR EACH ROW BEGIN
              UPDATE users SET updated_at = datetime('now') WHERE id = OLD.id;
            END;

            CREATE TABLE IF NOT EXISTS resources (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              slug TEXT NOT NULL UNIQUE,
              title TEXT NOT NULL,
              description TEXT DEFAULT '',
              usage TEXT DEFAULT '',
              created_by INTEGER,
              created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS resource_files (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              resource_id INTEGER NOT NULL,
              original_name TEXT NOT NULL,
              stored_name TEXT NOT NULL,
              mime TEXT,
              size INTEGER,
              url_path TEXT NOT NULL,
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
            );

            -- Per-file likes (one like per user per file)
            CREATE TABLE IF NOT EXISTS resource_file_likes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              file_id INTEGER NOT NULL,
              user_id INTEGER NOT NULL,
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              UNIQUE(file_id, user_id),
              FOREIGN KEY (file_id) REFERENCES resource_files(id) ON DELETE CASCADE,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        conn.commit()
    finally:
        if owns:
            conn.close()
