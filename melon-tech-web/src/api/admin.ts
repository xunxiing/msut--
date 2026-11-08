import axios from "axios"

const ADMIN_TOKEN_KEY = "msut_admin_token"

export function getAdminToken(): string {
  return sessionStorage.getItem(ADMIN_TOKEN_KEY) || ""
}

export function setAdminToken(token: string): void {
  sessionStorage.setItem(ADMIN_TOKEN_KEY, token)
}

export function clearAdminToken(): void {
  sessionStorage.removeItem(ADMIN_TOKEN_KEY)
}

const adminHttp = axios.create({
  baseURL: "/api/admin",
  headers: {
    "Content-Type": "application/json",
  },
})

adminHttp.interceptors.request.use((config) => {
  const token = getAdminToken()
  if (token) {
    config.headers["X-Admin-Token"] = token
  }
  return config
})

export type AdminMetrics = {
  usersCount: number
  resourcesCount: number
  filesCount: number
  filesSizeBytes: number
  likesCount: number
  commentsCount: number
}

export type AdminSystemInfo = {
  dbSizeBytes: number
  r2Configured: boolean
  r2Bucket: string
  r2PublicUrl: string
  ragConfigured: boolean
  ragModel: string
  agentModel: string
  httpsEnabled: boolean
  adminPath: string
}

export type AdminRecentUser = {
  id: number
  username: string
  avatarUrl: string
  signature: string
  createdAt: string
  resourceCount: number
}

export type AdminRecentResource = {
  id: number
  slug: string
  title: string
  createdAt: string
  authorName: string
  coverUrl: string
  likes: number
  filesCount: number
  downloadCount: number
  shareUrl: string
}

export type AdminStatsResponse = {
  ok: boolean
  metrics: AdminMetrics
  recentUsers: AdminRecentUser[]
  recentResources: AdminRecentResource[]
  systemInfo: AdminSystemInfo
}

export type AdminResourceItem = {
  id: number
  slug: string
  title: string
  description: string
  createdAt: string
  coverUrl: string
  authorId: number | null
  authorName: string
  tags: string[]
  downloadCount: number
  likesCount: number
  commentsCount: number
  filesCount: number
  totalSizeBytes: number
  shareUrl: string
}

export type AdminUserItem = {
  id: number
  username: string
  avatarUrl: string
  signature: string
  createdAt: string
  resourceCount: number
  commentCount: number
}

export type AdminDailyCandidate = {
  id: number
  slug: string
  title: string
  author: string
  coverUrl: string
  likes: number
  filesCount: number
  downloadCount: number
  dailyScore: number
  shareUrl: string
}

export type AdminDailyStatus = {
  ok: boolean
  date: string
  isManual: boolean
  heroId: number | null
  pickedIds: number[]
  candidates: AdminDailyCandidate[]
}

export async function adminLogin(password: string): Promise<{ ok: boolean; token: string; adminPath: string }> {
  const res = await adminHttp.post("/login", { password })
  if (res.data?.token) {
    setAdminToken(res.data.token)
  }
  return res.data
}

export async function adminCheck(): Promise<{ ok: boolean; adminPath: string }> {
  const res = await adminHttp.get("/check")
  return res.data
}

export async function fetchAdminStats(): Promise<AdminStatsResponse> {
  const res = await adminHttp.get("/stats")
  return res.data
}

export async function fetchAdminResources(params: {
  page?: number
  page_size?: number
  q?: string
  sort_by?: string
}): Promise<{ ok: boolean; total: number; page: number; pageSize: number; items: AdminResourceItem[] }> {
  const res = await adminHttp.get("/resources", { params })
  return res.data
}

export async function deleteAdminResource(id: number): Promise<{ ok: boolean; message: string }> {
  const res = await adminHttp.delete(`/resources/${id}`)
  return res.data
}

export async function updateAdminResource(
  id: number,
  data: { title?: string; description?: string }
): Promise<{ ok: boolean; message: string }> {
  const res = await adminHttp.patch(`/resources/${id}`, data)
  return res.data
}

export async function fetchAdminUsers(params: {
  page?: number
  page_size?: number
  q?: string
}): Promise<{ ok: boolean; total: number; page: number; pageSize: number; items: AdminUserItem[] }> {
  const res = await adminHttp.get("/users", { params })
  return res.data
}

export async function deleteAdminUser(id: number): Promise<{ ok: boolean; message: string }> {
  const res = await adminHttp.delete(`/users/${id}`)
  return res.data
}

export async function fetchAdminDaily(date?: string): Promise<AdminDailyStatus> {
  const res = await adminHttp.get("/daily", { params: { date } })
  return res.data
}

export async function overrideAdminDaily(payload: {
  date: string
  hero_id: number | null
  picked_ids: number[]
}): Promise<{ ok: boolean; message: string }> {
  const res = await adminHttp.post("/daily/override", payload)
  return res.data
}

export async function resetAdminDaily(date: string): Promise<{ ok: boolean; message: string }> {
  const res = await adminHttp.delete("/daily/override", { params: { date } })
  return res.data
}
