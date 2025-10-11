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
  files: ResourceFile[]
  shareUrl: string
}

export type MyResourceItem = ResourceItem

export async function listResources(params: { q?: string; page?: number; pageSize?: number } = {}) {
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
  const { data } = await http.post("/files/upload", fd, {
    headers: { "Content-Type": "multipart/form-data" }
  })
  return data
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

// -------- New: advanced list, stats, like/favorite --------
export async function advancedListResources(params: { q?: string; page?: number; pageSize?: number; sort?: 'hot' | 'time' | 'likes'; days?: number } = {}) {
  const { data } = await http.get('/resources/advanced', { params })
  return data as {
    items: Array<{ id: number; slug: string; title: string; description: string; created_at: string; likeCount: number; downloadCount: number }>
    page: number; pageSize: number; total: number
  }
}

export async function getResourceStats(id: number, days = 7) {
  const { data } = await http.get(`/resources/${id}/stats`, { params: { days } })
  return data as { likes: number; favorites: number; downloads: number; liked?: boolean; favorited?: boolean }
}

export async function likeResource(id: number) {
  const { data } = await http.post(`/resources/${id}/like`)
  return data as { ok: boolean; liked: boolean; likeCount: number }
}

export async function unlikeResource(id: number) {
  const { data } = await http.delete(`/resources/${id}/like`)
  return data as { ok: boolean; liked: boolean; likeCount: number }
}

export async function favoriteResource(id: number) {
  const { data } = await http.post(`/resources/${id}/favorite`)
  return data as { ok: boolean; favorited: boolean; favoriteCount: number }
}

export async function unfavoriteResource(id: number) {
  const { data } = await http.delete(`/resources/${id}/favorite`)
  return data as { ok: boolean; favorited: boolean; favoriteCount: number }
}
