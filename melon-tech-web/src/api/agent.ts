import axios from 'axios'

const api = axios.create({
    baseURL: '/api/agent',
    headers: {
        'Content-Type': 'application/json',
    },
})

export interface AgentSession {
    id: number
    title: string
    last_status: string
    last_error?: string
    last_message?: string
    created_at: string
    updated_at: string
}

export interface AgentMessage {
    id: number
    role: 'user' | 'assistant' | 'tool' | 'system'
    content: string
    toolName?: string
    toolArgs?: string
    toolCallId?: string
    runId?: number
    created_at: string
    payload?: any
}

export interface AgentRunStatus {
    runId: number
    sessionId: number
    status: 'pending' | 'running' | 'succeeded' | 'failed'
    resultUrl?: string
    resultName?: string
    error?: string
    created_at: string
    updated_at: string
}

export async function listSessions(): Promise<AgentSession[]> {
    const res = await api.get('/sessions')
    return res.data.items
}

export async function createSession(title?: string): Promise<AgentSession> {
    const res = await api.post('/sessions', { title })
    return res.data
}

export async function getSessionMessages(sessionId: number, limit = 50): Promise<AgentMessage[]> {
    const res = await api.get(`/sessions/${sessionId}/messages`, { params: { limit } })
    return res.data.items
}

export async function askAgent(sessionId: number | undefined, message: string): Promise<{ sessionId: number; runId: number; created: boolean; status: string }> {
    const res = await api.post('/ask', { sessionId, message })
    return res.data
}

export async function getRunStatus(runId: number): Promise<AgentRunStatus> {
    const res = await api.get(`/runs/${runId}`)
    return res.data
}
