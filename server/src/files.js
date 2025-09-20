import { db } from './db.js';
import multer from 'multer';
import path from 'node:path';
import fs from 'node:fs';
import { customAlphabet } from 'nanoid';
import slugify from 'slugify';
const nanoid = customAlphabet('0123456789abcdefghijklmnopqrstuvwxyz', 10);
const uploadDir = path.resolve(process.cwd(), 'uploads');
if (!fs.existsSync(uploadDir))
    fs.mkdirSync(uploadDir);
const storage = multer.diskStorage({
    destination: (_req, _file, cb) => cb(null, uploadDir),
    filename: (_req, file, cb) => {
        const ext = path.extname(file.originalname);
        cb(null, `${Date.now()}-${nanoid()}${ext}`);
    },
});
export const upload = multer({
    storage,
    limits: { fileSize: 50 * 1024 * 1024 } // 50MB
});
const PUBLIC_BASE = process.env.PUBLIC_BASE_URL || 'http://127.0.0.1:5173';
// 创建资源（需要登录）
export function createResource(req, res) {
    const { title, description = '', usage = '' } = req.body || {};
    if (!title || typeof title !== 'string')
        return res.status(400).json({ error: '标题必填' });
    // 生成唯一 slug
    const base = slugify(title, { lower: true, strict: true }) || `res-${nanoid()}`;
    let slug = base;
    let i = 1;
    while (db.prepare(`SELECT 1 FROM resources WHERE slug = ?`).get(slug)) {
        slug = `${base}-${i++}`;
    }
    const createdBy = req.user?.uid || null;
    const info = db.prepare(`
    INSERT INTO resources (slug, title, description, usage, created_by)
    VALUES (?, ?, ?, ?, ?)
  `).run(slug, title, description, usage, createdBy);
    const id = Number(info.lastInsertRowid);
    const shareUrl = `${PUBLIC_BASE}/share/${slug}`;
    res.json({ id, slug, title, description, usage, shareUrl });
}
// 上传文件到资源（需要登录）
export function uploadToResource(req, res) {
    try {
        const resourceId = Number(req.body.resourceId);
        if (!resourceId)
            return res.status(400).json({ error: '缺少 resourceId' });
        const resource = db.prepare(`SELECT * FROM resources WHERE id = ?`).get(resourceId);
        if (!resource)
            return res.status(404).json({ error: '资源不存在' });
        const files = req.files || [];
        if (!files.length)
            return res.status(400).json({ error: '没有文件' });
        const stmt = db.prepare(`
      INSERT INTO resource_files (resource_id, original_name, stored_name, mime, size, url_path)
      VALUES (?, ?, ?, ?, ?, ?)
    `);
        const saved = files.map(f => {
            const urlPath = `/uploads/${f.filename}`;
            stmt.run(resourceId, f.originalname, f.filename, f.mimetype, f.size, urlPath);
            return {
                originalName: f.originalname,
                size: f.size,
                mime: f.mimetype,
                urlPath
            };
        });
        res.json({ ok: true, files: saved });
    }
    catch (error) {
        console.error('Upload error:', error);
        res.status(500).json({ error: '上传失败' });
    }
}
// 资源详情（公开）
export function getResource(req, res) {
    const slug = req.params.slug;
    const r = db.prepare(`SELECT * FROM resources WHERE slug = ?`).get(slug);
    if (!r)
        return res.status(404).json({ error: '未找到资源' });
    const files = db.prepare(`
    SELECT id, original_name, stored_name, mime, size, url_path, created_at
    FROM resource_files WHERE resource_id = ? ORDER BY id DESC
  `).all(r.id);
    const shareUrl = `${PUBLIC_BASE}/share/${r.slug}`;
    res.json({ ...r, files, shareUrl });
}
// 资源列表（公开，简单分页）
export function listResources(req, res) {
    const q = String(req.query.q || '').trim();
    const page = Math.max(1, Number(req.query.page || 1));
    const pageSize = Math.min(50, Math.max(1, Number(req.query.pageSize || 12)));
    const offset = (page - 1) * pageSize;
    const where = q ? `WHERE title LIKE ? OR description LIKE ?` : ``;
    const args = q ? [`%${q}%`, `%${q}%`] : [];
    const total = db.prepare(`SELECT COUNT(1) as c FROM resources ${where}`).get(...args);
    const items = db.prepare(`
    SELECT id, slug, title, description, created_at
    FROM resources
    ${where}
    ORDER BY id DESC
    LIMIT ? OFFSET ?
  `).all(...args, pageSize, offset);
    res.json({ items, page, pageSize, total: total.c });
}
// 下载具体文件（公开）
export function downloadFile(req, res) {
    const id = Number(req.params.id);
    const row = db.prepare(`
    SELECT original_name, stored_name FROM resource_files WHERE id = ?
  `).get(id);
    if (!row)
        return res.status(404).json({ error: '文件不存在' });
    const filePath = path.join(uploadDir, row.stored_name);
    if (!fs.existsSync(filePath))
        return res.status(404).json({ error: '文件丢了' });
    res.setHeader('Content-Disposition', `attachment; filename*=UTF-8''${encodeURIComponent(row.original_name)}`);
    return res.sendFile(filePath);
}
//# sourceMappingURL=files.js.map