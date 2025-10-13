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
  author_name?: string
  author_username?: string
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
