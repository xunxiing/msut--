import sqlite3
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "data.sqlite"


def _ensure_db_file() -> None:
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DB_FILE.exists():
        DB_FILE.touch()


def get_connection() -> sqlite3.Connection:
    _ensure_db_file()
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def run_migrations(conn: Optional[sqlite3.Connection] = None) -> None:
    owns = False
    if conn is None:
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
            """
        )
        conn.commit()
    finally:
        if owns:
            conn.close()
