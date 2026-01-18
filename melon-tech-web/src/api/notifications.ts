import { http } from './http'

export type NotificationItem = {
  id: number
  type: 'resource_like' | 'comment_like' | 'comment_reply'
  content?: string | null
  created_at: string
  resource?: {
    id?: number | null
    slug?: string | null
    title?: string | null
  }
  comment?: {
    id?: number | null
    content?: string | null
  }
  actor: {
    id: number
    name: string
    username: string
  }
}

export type NotificationListResponse = {
  items: NotificationItem[]
  page: number
  pageSize: number
  total: number
}

export async function listNotifications(page = 1, pageSize = 20) {
  const { data } = await http.get('/notifications', { params: { page, pageSize } })
  return data as NotificationListResponse
}

export async function listUnreadNotifications() {
  const { data } = await http.get('/notifications/unread')
  return data as { items: NotificationItem[]; total: number }
}
