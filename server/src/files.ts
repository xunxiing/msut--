import type { Request, Response } from "express"
import { db } from "./db.js"
import multer from "multer"
import path from "node:path"
import fs from "node:fs"
import { customAlphabet } from "nanoid"
import slugify from "slugify"

const nanoid = customAlphabet("0123456789abcdefghijklmnopqrstuvwxyz", 10)
const uploadDir = path.resolve(process.cwd(), "uploads")
if (!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir)

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, uploadDir),
  filename: (_req, file, cb) => {
    const ext = path.extname(file.originalname)
    cb(null, `${Date.now()}-${nanoid()}${ext}`)
  },
})
export const upload = multer({
  storage,
  limits: { fileSize: 50 * 1024 * 1024 }
})

const PUBLIC_BASE = process.env.PUBLIC_BASE_URL || "http://127.0.0.1:5173"

function requireUserId(req: Request) {
  const uid = (req as any).user?.uid
  if (!uid) {
    const err: any = new Error("未登录")
    err.status = 401
    throw err
  }
  return uid
}

function getShareUrl(slug: string) {
  return `${PUBLIC_BASE}/share/${slug}`
}

function sendError(res: Response, error: unknown, fallback: string) {
  const status = (error as any)?.status || 500
  const message = status === 500 ? fallback : ((error as any)?.message || fallback)
  res.status(status).json({ error: message })
}

export function createResource(req: Request, res: Response) {
  const { title, description = "", usage = "" } = req.body || {}
  if (!title || typeof title !== "string") return res.status(400).json({ error: "标题必填" })

  const base = (slugify as any)(title, { lower: true, strict: true }) || `res-${nanoid()}`
  let slug = base
  let i = 1
  while (db.prepare(`SELECT 1 FROM resources WHERE slug = ?`).get(slug)) {
    slug = `${base}-${i++}`
  }

  const createdBy = (req as any).user?.uid || null
  const info = db.prepare(`
    INSERT INTO resources (slug, title, description, usage, created_by)
    VALUES (?, ?, ?, ?, ?)
  `).run(slug, title, description, usage, createdBy)

  const id = Number(info.lastInsertRowid)
  res.json({ id, slug, title, description, usage, shareUrl: getShareUrl(slug) })
}

export function uploadToResource(req: Request, res: Response) {
  try {
    const resourceId = Number(req.body.resourceId)
    if (!resourceId) return res.status(400).json({ error: "缺少 resourceId" })

    const uid = requireUserId(req)
    const resource = db.prepare(`SELECT id, created_by FROM resources WHERE id = ?`).get(resourceId) as any
    if (!resource) return res.status(404).json({ error: "资源不存在" })
    if (resource.created_by !== uid) return res.status(403).json({ error: "无法操作其他用户的资源" })

    const files = (req.files as Express.Multer.File[]) || []
    if (!files.length) return res.status(400).json({ error: "没有文件" })

    const stmt = db.prepare(`
      INSERT INTO resource_files (resource_id, original_name, stored_name, mime, size, url_path)
      VALUES (?, ?, ?, ?, ?, ?)
    `)

    const saved = files.map(f => {
      const urlPath = `/uploads/${f.filename}`
      const info = stmt.run(resourceId, f.originalname, f.filename, f.mimetype, f.size, urlPath)
      return {
        id: Number(info.lastInsertRowid),
        originalName: f.originalname,
        size: f.size,
        mime: f.mimetype,
        urlPath
      }
    })

    res.json({ ok: true, files: saved })
  } catch (error) {
    console.error("Upload error:", error)
    sendError(res, error, "上传失败")
  }
}

export function listMyResources(req: Request, res: Response) {
  try {
    const uid = requireUserId(req)
    const resources = db.prepare(`
      SELECT id, slug, title, description, usage, created_at
      FROM resources
      WHERE created_by = ?
      ORDER BY id DESC
    `).all(uid) as any[]

    const fileStmt = db.prepare(`
      SELECT id, original_name, stored_name, mime, size, url_path, created_at
      FROM resource_files
      WHERE resource_id = ?
      ORDER BY id DESC
    `)

    const items = resources.map(resource => ({
      ...resource,
      files: fileStmt.all(resource.id),
      shareUrl: getShareUrl(resource.slug)
    }))

    res.json({ items })
  } catch (error) {
    sendError(res, error, "获取资源失败")
  }
}

export function updateResource(req: Request, res: Response) {
  try {
    const uid = requireUserId(req)
    const resourceId = Number(req.params.id)
    if (!resourceId) return res.status(400).json({ error: "资源 ID 无效" })

    const resource = db.prepare(`SELECT id, slug, created_by FROM resources WHERE id = ?`).get(resourceId) as any
    if (!resource) return res.status(404).json({ error: "资源不存在" })
    if (resource.created_by !== uid) return res.status(403).json({ error: "无法操作其他用户的资源" })

    const { description, usage } = req.body || {}
    const updates: string[] = []
    const params: any[] = []

    if (typeof description === "string") {
      updates.push("description = ?")
      params.push(description)
    }
    if (typeof usage === "string") {
      updates.push("usage = ?")
      params.push(usage)
    }

    if (!updates.length) return res.status(400).json({ error: "没有需要更新的字段" })

    params.push(resourceId)
    db.prepare(`UPDATE resources SET ${updates.join(", ")} WHERE id = ?`).run(...params)

    const updated = db.prepare(`
      SELECT id, slug, title, description, usage, created_at
      FROM resources WHERE id = ?
    `).get(resourceId) as any

    res.json({ ...updated, shareUrl: getShareUrl(updated.slug) })
  } catch (error) {
    sendError(res, error, "更新失败")
  }
}

export function deleteResource(req: Request, res: Response) {
  try {
    const uid = requireUserId(req)
    const resourceId = Number(req.params.id)
    if (!resourceId) return res.status(400).json({ error: "资源 ID 无效" })

    const resource = db.prepare(`SELECT id, created_by FROM resources WHERE id = ?`).get(resourceId) as any
    if (!resource) return res.status(404).json({ error: "资源不存在" })
    if (resource.created_by !== uid) return res.status(403).json({ error: "无法操作其他用户的资源" })

    const files = db.prepare(`
      SELECT stored_name FROM resource_files WHERE resource_id = ?
    `).all(resourceId) as Array<{ stored_name: string }>

    const tx = db.transaction((id: number) => {
      db.prepare(`DELETE FROM resource_files WHERE resource_id = ?`).run(id)
      db.prepare(`DELETE FROM resources WHERE id = ?`).run(id)
    })
    tx(resourceId)

    files.forEach(file => {
      const filePath = path.join(uploadDir, file.stored_name)
      if (fs.existsSync(filePath)) {
        try {
          fs.unlinkSync(filePath)
        } catch (unlinkError) {
          console.error("Delete file error:", unlinkError)
        }
      }
    })

    res.json({ ok: true })
  } catch (error) {
    sendError(res, error, "删除失败")
  }
}

export function getResource(req: Request, res: Response) {
  const slug = req.params.slug
  const r = db.prepare(`SELECT * FROM resources WHERE slug = ?`).get(slug) as any
  if (!r) return res.status(404).json({ error: "未找到资源" })
  const files = db.prepare(`
    SELECT id, original_name, stored_name, mime, size, url_path, created_at
    FROM resource_files WHERE resource_id = ? ORDER BY id DESC
  `).all(r.id)
  res.json({ ...r, files, shareUrl: getShareUrl(r.slug) })
}

export function listResources(req: Request, res: Response) {
  const q = String(req.query.q || "").trim()
  const page = Math.max(1, Number(req.query.page || 1))
  const pageSize = Math.min(50, Math.max(1, Number(req.query.pageSize || 12)))
  const offset = (page - 1) * pageSize

  const where = q ? "WHERE title LIKE ? OR description LIKE ?" : ""
  const args = q ? [
    `%${q}%`,
    `%${q}%`
  ] : []

  const total = db.prepare(`SELECT COUNT(1) as c FROM resources ${where}`).get(...args) as any
  const items = db.prepare(`
    SELECT id, slug, title, description, created_at
    FROM resources
    ${where}
    ORDER BY id DESC
    LIMIT ? OFFSET ?
  `).all(...args, pageSize, offset)

  res.json({ items, page, pageSize, total: total.c })
}

export function downloadFile(req: Request, res: Response) {
  const id = Number(req.params.id)
  const row = db.prepare(`
    SELECT original_name, stored_name FROM resource_files WHERE id = ?
  `).get(id) as any
  if (!row) return res.status(404).json({ error: "文件不存在" })
  const filePath = path.join(uploadDir, row.stored_name)
  if (!fs.existsSync(filePath)) return res.status(404).json({ error: "文件丢了" })
  res.setHeader("Content-Disposition", `attachment; filename*=UTF-8''${encodeURIComponent(row.original_name)}`)
  return res.sendFile(filePath)
}

