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
        # Use a slightly more concurrency-friendly configuration:
        # - check_same_thread=False: allow usage across async contexts
        # - timeout: busy timeout in seconds when the DB is locked
        # - isolation_level=None: autocommit by default; explicit BEGIN used where needed
        conn = sqlite3.connect(
            db_path,
            check_same_thread=False,
            timeout=30,
            isolation_level=None,
        )
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
        conn = sqlite3.connect(
            f"file:{db_path}?mode=rwc",
            uri=True,
            check_same_thread=False,
            timeout=30,
            isolation_level=None,
        )
    # Per-connection pragmas for better concurrency and safety.
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except Exception:
        # If WAL is not supported (e.g., network FS), continue with default.
        pass
    try:
        conn.execute("PRAGMA foreign_keys=ON")
    except Exception:
        pass
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

            CREATE TABLE IF NOT EXISTS auth_refresh_tokens (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              token_hash TEXT NOT NULL UNIQUE,
              expires_at INTEGER NOT NULL,
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              last_used_at TEXT,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_auth_refresh_tokens_user ON auth_refresh_tokens(user_id);

            CREATE TABLE IF NOT EXISTS resources (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              slug TEXT NOT NULL UNIQUE,
              title TEXT NOT NULL,
              description TEXT DEFAULT '',
              usage TEXT DEFAULT '',
              created_by INTEGER,
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              -- Optional cover image for resource cards
              cover_file_id INTEGER
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

            -- Optional per-file watermark info for .melsave uploads
            CREATE TABLE IF NOT EXISTS file_watermarks (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              file_id INTEGER NOT NULL UNIQUE,
              watermark_u64 INTEGER NOT NULL,
              seq_len INTEGER NOT NULL,
              embedded_watermark INTEGER,
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              FOREIGN KEY (file_id) REFERENCES resource_files(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_file_watermarks_wm ON file_watermarks(watermark_u64);

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

            -- Per-resource likes (one like per user per resource)
            CREATE TABLE IF NOT EXISTS resource_likes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              resource_id INTEGER NOT NULL,
              user_id INTEGER NOT NULL,
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              UNIQUE(resource_id, user_id),
              FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            -- 独立教程内容（用于文档系统 + RAG）
            CREATE TABLE IF NOT EXISTS tutorials (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              slug TEXT NOT NULL UNIQUE,
              title TEXT NOT NULL,
              description TEXT DEFAULT '',
              content TEXT NOT NULL,
              created_by INTEGER,
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              updated_at TEXT NOT NULL DEFAULT (datetime('now')),
              FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE TRIGGER IF NOT EXISTS trg_tutorials_updated_at
            AFTER UPDATE ON tutorials
            FOR EACH ROW BEGIN
              UPDATE tutorials SET updated_at = datetime('now') WHERE id = OLD.id;
            END;

            -- 教程分块向量，用于语义检索 / RAG
            CREATE TABLE IF NOT EXISTS tutorial_embeddings (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              tutorial_id INTEGER NOT NULL,
              chunk_index INTEGER NOT NULL,
              chunk_text TEXT NOT NULL,
              embedding_json TEXT NOT NULL,
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              FOREIGN KEY (tutorial_id) REFERENCES tutorials(id) ON DELETE CASCADE
            );
            """
        )
        cur.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_tutorials_slug ON tutorials(slug);
            CREATE INDEX IF NOT EXISTS idx_tutorial_embeddings_tutorial ON tutorial_embeddings(tutorial_id);
            """
        )
        # Extra columns for resources (idempotent, added for image cover support)
        cur.execute("PRAGMA table_info(resources)")
        res_cols = [row["name"] for row in cur.fetchall() or []]
        if "cover_file_id" not in res_cols:
            cur.execute("ALTER TABLE resources ADD COLUMN cover_file_id INTEGER")
        # Extra columns for tutorial chunk optimization (idempotent)
        cur.execute("PRAGMA table_info(tutorial_embeddings)")
        cols = [row["name"] for row in cur.fetchall() or []]
        if "chunk_title" not in cols:
            cur.execute("ALTER TABLE tutorial_embeddings ADD COLUMN chunk_title TEXT")
        if "optimized_chunk_text" not in cols:
            cur.execute("ALTER TABLE tutorial_embeddings ADD COLUMN optimized_chunk_text TEXT")
        if "optimized_at" not in cols:
            cur.execute("ALTER TABLE tutorial_embeddings ADD COLUMN optimized_at TEXT")
        # Agent chat storage (sessions, runs, messages)
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS agent_sessions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              title TEXT,
              last_status TEXT DEFAULT 'idle',
              last_error TEXT,
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              updated_at TEXT NOT NULL DEFAULT (datetime('now')),
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TRIGGER IF NOT EXISTS trg_agent_sessions_updated_at
            AFTER UPDATE ON agent_sessions
            FOR EACH ROW BEGIN
              UPDATE agent_sessions SET updated_at = datetime('now') WHERE id = OLD.id;
            END;

            CREATE TABLE IF NOT EXISTS agent_runs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id INTEGER NOT NULL,
              user_id INTEGER NOT NULL,
              status TEXT NOT NULL,
              model TEXT,
              result_path TEXT,
              result_name TEXT,
              error TEXT,
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              updated_at TEXT NOT NULL DEFAULT (datetime('now')),
              FOREIGN KEY (session_id) REFERENCES agent_sessions(id) ON DELETE CASCADE,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TRIGGER IF NOT EXISTS trg_agent_runs_updated_at
            AFTER UPDATE ON agent_runs
            FOR EACH ROW BEGIN
              UPDATE agent_runs SET updated_at = datetime('now') WHERE id = OLD.id;
            END;

            CREATE TABLE IF NOT EXISTS agent_messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id INTEGER NOT NULL,
              run_id INTEGER,
              role TEXT NOT NULL,
              content TEXT NOT NULL,
              tool_name TEXT,
              tool_args TEXT,
              tool_call_id TEXT,
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              FOREIGN KEY (session_id) REFERENCES agent_sessions(id) ON DELETE CASCADE,
              FOREIGN KEY (run_id) REFERENCES agent_runs(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_agent_messages_session ON agent_messages(session_id, id);
            CREATE INDEX IF NOT EXISTS idx_agent_runs_session ON agent_runs(session_id);
            """
        )
        conn.commit()
    finally:
        if owns:
            conn.close()
