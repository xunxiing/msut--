import { http } from './http'

export type FileLikeInfo = { id: number; likes: number; liked: boolean }

export async function getFileLikes(ids: number[]) {
  if (!ids.length) return [] as FileLikeInfo[]
  const { data } = await http.get('/files/likes', { params: { ids: ids.join(',') } })
  return (data.items || []) as FileLikeInfo[]
}

export async function likeFile(id: number) {
  const { data } = await http.post(`/files/${id}/like`)
  return data as { liked: boolean; likes: number }
}

export async function unlikeFile(id: number) {
  const { data } = await http.delete(`/files/${id}/like`)
  return data as { liked: boolean; likes: number }
}

