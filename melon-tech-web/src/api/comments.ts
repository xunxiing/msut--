import { http } from './http'

export type CommentUser = {
  id: number
  name: string
  username: string
}

export type CommentItem = {
  id: number
  resource_id: number
  user_id: number
  parent_id: number | null
  content: string
  created_at: string
  updated_at: string
  user: CommentUser
  likes: number
  liked: boolean
  children?: CommentItem[]
}

export type CommentListResponse = {
  items: CommentItem[]
  page: number
  pageSize: number
  total: number
}

export async function listResourceComments(resourceId: number, page = 1, pageSize = 20) {
  const { data } = await http.get(`/resources/${resourceId}/comments`, { params: { page, pageSize } })
  return data as CommentListResponse
}

export async function createComment(resourceId: number, payload: { content: string; parentId?: number | null }) {
  const { data } = await http.post(`/resources/${resourceId}/comments`, payload)
  return data as { item: CommentItem }
}

export async function updateComment(id: number, payload: { content: string }) {
  const { data } = await http.patch(`/comments/${id}`, payload)
  return data as { item: CommentItem }
}

export async function deleteComment(id: number) {
  const { data } = await http.delete(`/comments/${id}`)
  return data as { ok: boolean }
}

export async function likeComment(id: number) {
  const { data } = await http.post(`/comments/${id}/like`)
  return data as { liked: boolean; likes: number }
}

export async function unlikeComment(id: number) {
  const { data } = await http.delete(`/comments/${id}/like`)
  return data as { liked: boolean; likes: number }
}
