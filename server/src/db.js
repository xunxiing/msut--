import Database from 'better-sqlite3';
import path from 'node:path';
import fs from 'node:fs';
const dbFile = path.resolve(process.cwd(), 'data.sqlite');
if (!fs.existsSync(dbFile))
    fs.writeFileSync(dbFile, '');
// 显式类型注解以避免导出类型命名问题
export const db = new Database(dbFile);
// 初始化表
db.exec(`
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
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
  url_path TEXT NOT NULL, -- 例如 /uploads/abc123.zip
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
);
`);
//# sourceMappingURL=db.js.map