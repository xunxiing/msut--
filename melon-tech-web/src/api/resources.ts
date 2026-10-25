import axios from "axios"
import { http } from "./http"

export type ResourceFile = {
  id: number
  original_name: string
  stored_name?: string
  size: number
  mime: string
  url_path: string
  created_at?: string
}

export type ResourceItem = {
  id: number
  slug: string
  title: string
  description: string
  usage: string
  created_at: string
  author_username?: string
  author_avatar?: string
  files: ResourceFile[]
  imageFiles?: ResourceFile[]
  coverFileId?: number | null
  coverUrlPath?: string | null
  tags?: string[]
  shareUrl: string
  likes?: number
  downloadCount?: number
  download_count?: number
  dailyScore?: number
}

export type MyResourceItem = ResourceItem

export type OptimizeResult = {
  title: string
  description: string
  usage: string
  tags: string[]
}

export async function optimizeContent(data: { title: string; description: string; usage: string; resourceId?: number }): Promise<OptimizeResult> {
  const res = await http.post("/resources/optimize", data)
  return res.data
}

export async function classifyResource(rid: number): Promise<{ tags: string[] }> {
  const res = await http.post(`/resources/${rid}/classify`)
  return res.data
}

export type ResourceImagesResponse = {
  items: ResourceFile[]
  coverFileId?: number | null
}

export async function listResources(params: { q?: string; page?: number; pageSize?: number; sort?: string } = {}) {
  const { data } = await http.get("/resources", { params })
  return data
}

export async function getResource(slug: string) {
  const { data } = await http.get(`/resources/${slug}`)
  return data as ResourceItem
}

export async function createResource(payload: { title: string; description?: string; usage?: string }) {
  const { data } = await http.post("/resources", payload)
  return data as { id: number; slug: string; shareUrl: string }
}

export async function uploadFiles(resourceId: number, files: File[]) {
  const fd = new FormData()
  fd.append("resourceId", String(resourceId))
  files.forEach(f => fd.append("files", f))
  const { data } = await http.post("/files/upload", fd)
  return data
}

// Files above this size are uploaded through the chunked/resumable API
export const RESUMABLE_THRESHOLD = 4 * 1024 * 1024

export interface ResumableUploadOpts {
  saveWatermark?: boolean
  onProgress?: (pct: number) => void
  signal?: AbortSignal
}

export async function uploadFileResumable(
  resourceId: number,
  file: File,
  opts: ResumableUploadOpts = {},
) {
  const resumeKey = `${file.name}:${file.size}:${file.lastModified}`
  const { data: init } = await http.post("/uploads/init", {
    resourceId,
    filename: file.name,
    mime: file.type || "application/octet-stream",
    size: file.size,
    saveWatermark: !!opts.saveWatermark,
    resumeKey,
  })
  const { uploadId, chunkSize, chunkCount } = init
  const received: number[] = init.received || []
  const done = new Set<number>(received)
  const chunkBytes = (i: number) => Math.min(chunkSize, file.size - i * chunkSize)
  let doneBytes = 0
  for (const i of done) doneBytes += chunkBytes(i)
  opts.onProgress?.(Math.min(99, Math.round((doneBytes / file.size) * 100)))
  for (let i = 0; i < chunkCount; i++) {
    if (opts.signal?.aborted) throw new Error("aborted")
    if (done.has(i)) continue
    const blob = file.slice(i * chunkSize, i * chunkSize + chunkBytes(i))
    let attempt = 0
    for (;;) {
      try {
        await http.post(`/uploads/${uploadId}/chunk?index=${i}`, blob, {
          headers: { "Content-Type": "application/octet-stream" },
          onUploadProgress: (ev) => {
            const pct = Math.min(99, Math.round(((doneBytes + (ev.loaded || 0)) / file.size) * 100))
            opts.onProgress?.(pct)
          },
        })
        break
      } catch (e) {
        attempt++
        if (attempt >= 3) throw e
        await new Promise(r => setTimeout(r, 1000 * attempt))
      }
    }
    doneBytes += chunkBytes(i)
    done.add(i)
    opts.onProgress?.(Math.min(99, Math.round((doneBytes / file.size) * 100)))
  }
  const { data } = await http.post(`/uploads/${uploadId}/complete`)
  opts.onProgress?.(100)
  return data as {
    ok: boolean
    files: { id: number; originalName: string; size: number; mime: string | null; urlPath: string }[]
  }
}

// Browser-direct upload to R2 via a presigned URL: single cross-border hop,
// real progress bar, no server relay. On failure (e.g. CORS-blocked WebView)
// the caller falls back to the chunked path.
export async function uploadFileDirect(
  resourceId: number,
  file: File,
  opts: ResumableUploadOpts = {},
) {
  const mime = file.type || "application/octet-stream"
  const { data: pre } = await http.post("/uploads/presign", {
    filename: file.name,
    mime,
    size: file.size,
  })
  for (let attempt = 1; ; attempt++) {
    try {
      await axios.put(pre.url, file, {
        headers: pre.headers,
        onUploadProgress: (ev: any) => {
          const pct = Math.min(
            99,
            Math.round(((ev.loaded || 0) / (ev.total || file.size)) * 100),
          )
          opts.onProgress?.(pct)
        },
      })
      break
    } catch (e) {
      if (attempt >= 3) throw e
      await new Promise((r) => setTimeout(r, 1000 * attempt))
    }
  }
  const { data } = await http.post("/uploads/commit", {
    resourceId,
    key: pre.key,
    filename: file.name,
    mime,
    size: file.size,
    saveWatermark: !!opts.saveWatermark,
  })
  opts.onProgress?.(100)
  return data as {
    ok: boolean
    files: { id: number; originalName: string; size: number; mime: string | null; urlPath: string }[]
  }
}

// Upload a mixed batch: small files in one legacy request, large files via
// presigned direct-to-R2 upload (chunked/resumable as fallback).
export async function uploadFilesMixed(
  resourceId: number,
  files: File[],
  opts: ResumableUploadOpts = {},
) {
  const small: File[] = []
  const large: File[] = []
  for (const f of files) (f.size > RESUMABLE_THRESHOLD ? large : small).push(f)
  if (small.length) await uploadFiles(resourceId, small)
  for (const f of large) {
    try {
      await uploadFileDirect(resourceId, f, opts)
    } catch {
      // Direct PUT failed (CORS / expired signature) -> resumable chunks
      await uploadFileResumable(resourceId, f, opts)
    }
  }
}

export async function listMyResources() {
  const { data } = await http.get("/my/resources")
  return data.items as MyResourceItem[]
}

export async function updateResourceMeta(id: number, payload: { description?: string; usage?: string }) {
  const { data } = await http.patch(`/resources/${id}`, payload)
  return data as ResourceItem
}

export async function deleteResource(id: number) {
  const { data } = await http.delete(`/resources/${id}`)
  return data as { ok: boolean }
}

export async function setResourceCover(id: number, fileId: number | null) {
  const { data } = await http.patch(`/resources/${id}/cover`, { fileId })
  return data as { ok: boolean; coverFileId: number | null }
}

export async function listResourceImages(id: number) {
  const { data } = await http.get(`/resources/${id}/images`)
  return data as ResourceImagesResponse
}

export type CreatorStats = {
  user: { id: number; username: string; avatar_url: string; signature: string }
  resource_count: number
  total_downloads: number
  top_resources: { id: number; slug: string; title: string; download_count: number; created_at: string }[]
}

export async function getCreatorStats(username: string) {
  const { data } = await http.get(`/creators/${username}/stats`)
  return data as CreatorStats
}

export type DailyRecommendationResponse = {
  date: string
  is_manual: boolean
  hero: ResourceItem | null
  picks: ResourceItem[]
  total_candidates: number
}

export async function getDailyRecommendations(date?: string): Promise<DailyRecommendationResponse> {
  const { data } = await http.get('/resources/daily', { params: { date } })
  return data
}

export async function verifyDailyAdminPassword(password: string): Promise<{ ok: boolean }> {
  const { data } = await http.post('/resources/daily/admin/verify', { password })
  return data
}

export async function overrideDailyRecommendations(payload: {
  date: string
  hero_id?: number | null
  picked_ids: number[]
  password: string
}): Promise<{ ok: boolean; message: string }> {
  const { data } = await http.post('/resources/daily/admin/override', payload)
  return data
}

export async function resetDailyRecommendations(date: string, password: string): Promise<{ ok: boolean; message: string }> {
  const { data } = await http.delete('/resources/daily/admin/override', { params: { date, password } })
  return data
}
