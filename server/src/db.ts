import Database from 'better-sqlite3'
import { resolve } from 'node:path'
import { existsSync, writeFileSync } from 'node:fs'

const dbFile = resolve(process.cwd(), 'data.sqlite')
if (!existsSync(dbFile)) writeFileSync(dbFile, '')

// 显式类型注解以避免导出类型命名问题
export const db: any = new Database(dbFile)

// 数据库迁移：检查是否需要从 email 迁移到 username
const migrationCheck = db.prepare(`
  SELECT name FROM sqlite_master
  WHERE type='table' AND name='users' AND sql LIKE '%email TEXT NOT NULL UNIQUE%'
`).get()

if (migrationCheck) {
  console.log('执行数据库迁移：将 email 字段改为 username 字段')
  
  // 1. 创建新表结构
  db.exec(`
    CREATE TABLE IF NOT EXISTS users_new (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      name TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
  `)
  
  // 2. 迁移数据
  db.exec(`
    INSERT INTO users_new (id, username, password_hash, name, created_at, updated_at)
    SELECT id, email, password_hash, name, created_at, updated_at FROM users
  `)
  
  // 3. 删除旧表
  db.exec(`DROP TABLE users`)
  
  // 4. 重命名新表
  db.exec(`ALTER TABLE users_new RENAME TO users`)
  
  console.log('数据库迁移完成')
}

// 初始化表
db.exec(`
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
  url_path TEXT NOT NULL, -- 例如 /uploads/abc123.zip
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
);
`)
