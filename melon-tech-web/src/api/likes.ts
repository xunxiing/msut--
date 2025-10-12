import { http } from './http'

export type LikeInfo = { id: number; likes: number; liked: boolean }

// Resource (collection) likes
export async function getResourceLikes(ids: number[]) {
  if (!ids.length) return [] as LikeInfo[]
  const { data } = await http.get('/resources/likes', { params: { ids: ids.join(',') } })
  return (data.items || []) as LikeInfo[]
}

export async function likeResource(id: number) {
  const { data } = await http.post(`/resources/${id}/like`)
  return data as { liked: boolean; likes: number }
}

export async function unlikeResource(id: number) {
  const { data } = await http.delete(`/resources/${id}/like`)
  return data as { liked: boolean; likes: number }
}

// (Legacy) File likes kept unused but available
export async function getFileLikes(ids: number[]) {
  if (!ids.length) return [] as LikeInfo[]
  const { data } = await http.get('/files/likes', { params: { ids: ids.join(',') } })
  return (data.items || []) as LikeInfo[]
}
export async function likeFile(id: number) {
  const { data } = await http.post(`/files/${id}/like`)
  return data as { liked: boolean; likes: number }
}
export async function unlikeFile(id: number) {
  const { data } = await http.delete(`/files/${id}/like`)
  return data as { liked: boolean; likes: number }
}
