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

export type TutorialStreamEvent =
  | { event: "meta"; query?: string; sources?: TutorialSearchResult[]; tookMs?: number }
  | { event: "token"; text?: string }
  | { event: "error"; message?: string }
  | { event: "done"; hasAnswer?: boolean; sources?: TutorialSearchResult[] }
  | Record<string, unknown>

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

export async function searchAndAskStream(
  params: { query: string; mode?: "search" | "qa" | "both"; limit?: number },
  options: { signal?: AbortSignal; onEvent?: (evt: TutorialStreamEvent) => void } = {},
) {
  const resp = await fetch("/api/tutorials/search-and-ask", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...params, stream: true }),
    signal: options.signal,
  })

  const contentType = resp.headers.get("content-type") || ""
  if (resp.ok && contentType.includes("text/event-stream") && resp.body) {
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ""
    let doneReceived = false

    const flushBuffer = (chunk: string) => {
      buffer += chunk
      const parts = buffer.split("\n\n")
      buffer = parts.pop() ?? ""
      for (const part of parts) {
        const line = part.trim()
        if (!line.startsWith("data:")) continue
        const payload = line.slice(5).trim()
        if (!payload) continue
        let evt: TutorialStreamEvent
        try {
          evt = JSON.parse(payload) as TutorialStreamEvent
        } catch (_err) {
          continue
        }
        options.onEvent?.(evt)
        const type = (evt as Record<string, unknown>).event
        if (type === "done" || type === "error") {
          doneReceived = true
        }
      }
    }

    while (true) {
      const { value, done } = await reader.read()
      const text = decoder.decode(value || new Uint8Array(), { stream: !done })
      if (text) {
        flushBuffer(text.replace(/\r/g, ""))
      }
      if (done || doneReceived) break
    }

    return { streamed: true as const }
  }

  const data = await resp.json().catch(() => null)
  if (!resp.ok) {
    const message = (data && ((data as Record<string, unknown>).error || (data as Record<string, unknown>).message)) || "请求失败"
    throw new Error(String(message))
  }
  return { streamed: false as const, data: data as SearchAndAskResponse }
}

