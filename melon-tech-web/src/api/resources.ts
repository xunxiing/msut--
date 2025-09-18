import { http } from './http'

export type ResourceItem = {
  id: number
  slug: string
  title: string
  description: string
  usage: string
  created_at: string
  files: Array<{ id: number; original_name: string; size: number; mime: string; url_path: string }>
  shareUrl: string
}

export async function listResources(params: { q?: string; page?: number; pageSize?: number } = {}) {
  const { data } = await http.get('/resources', { params })
  return data
}

export async function getResource(slug: string) {
  const { data } = await http.get(`/resources/${slug}`)
  return data as ResourceItem
}

export async function createResource(payload: { title: string; description?: string; usage?: string }) {
  const { data } = await http.post('/resources', payload)
  return data as { id: number; slug: string; shareUrl: string }
}

export async function uploadFiles(resourceId: number, files: File[]) {
  const fd = new FormData()
  fd.append('resourceId', String(resourceId))
  files.forEach(f => fd.append('files', f))
  const { data } = await http.post('/files/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return data
}
