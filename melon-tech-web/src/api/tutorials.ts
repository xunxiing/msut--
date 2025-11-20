import { http } from "./http"

export type TutorialItem = {
  id: number
  slug: string
  title: string
  description: string
  created_at: string
}

export type MyTutorialItem = {
  id: number
  slug: string
  title: string
  description: string
  created_at: string
  updated_at: string
}

export type TutorialDetail = {
  id: number
  slug: string
  title: string
  description: string
  content: string
  created_at: string
  updated_at: string
}

export type TutorialSearchResult = {
  tutorialId: number
  slug: string
  title: string
  excerpt: string
  score: number | null
}

export type TutorialChunk = {
  id: number
  index: number
  title: string
  preview: string
}

export type SearchAndAskResponse = {
  query: string
  mode: "search" | "qa" | "both"
  search: { items: TutorialSearchResult[]; tookMs: number }
  answer: { text: string; sources: TutorialSearchResult[] } | null
  ragEnabled: boolean
}

export async function createTutorial(payload: { title: string; description?: string; content: string }) {
  const { data } = await http.post("/tutorials", payload)
  return data as { id: number; slug: string; title: string; description: string }
}

export async function listTutorials(params: { q?: string; page?: number; pageSize?: number } = {}) {
  const { data } = await http.get("/tutorials", { params })
  return data as { items: TutorialItem[]; total: number; page: number; pageSize: number }
}

export async function getTutorial(id: number) {
  const { data } = await http.get(`/tutorials/${id}`)
  return data as TutorialDetail
}

export async function listMyTutorials() {
  const { data } = await http.get("/my/tutorials")
  return data.items as MyTutorialItem[]
}

export async function updateTutorial(
  id: number,
  payload: { title?: string; description?: string; content?: string },
) {
  const { data } = await http.patch(`/tutorials/${id}`, payload)
  return data as TutorialDetail
}

export async function deleteTutorial(id: number) {
  const { data } = await http.delete(`/tutorials/${id}`)
  return data as { ok: boolean }
}

export async function getTutorialChunks(id: number) {
  const { data } = await http.get(`/tutorials/${id}/chunks`)
  return data as { tutorialId: number; slug: string; title: string; chunks: TutorialChunk[] }
}

export async function searchAndAsk(params: { query: string; mode?: "search" | "qa" | "both"; limit?: number }) {
  const { data } = await http.post("/tutorials/search-and-ask", params)
  return data as SearchAndAskResponse
}

