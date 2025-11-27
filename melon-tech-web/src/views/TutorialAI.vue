<template>
  <div class="agent-page" :class="{ 'is-mobile': isMobile }">
    <!-- Mobile Backdrop -->
    <div 
      v-if="isMobile && (!isSidebarCollapsed || !isRightPanelCollapsed)" 
      class="mobile-backdrop"
      @click="closeAllPanels"
    ></div>

    <div class="sidebar-wrapper" :class="{ 'collapsed': isSidebarCollapsed }">
      <AgentSidebar
        v-show="!isSidebarCollapsed"
        :sessions="sessions"
        :current-session-id="currentSessionId"
        :loading="sessionsLoading"
        @new-chat="handleNewChat"
        @select-session="handleSelectSession"
      />
    </div>

    <div class="agent-main">
      <button
        type="button"
        class="sidebar-toggle"
        @click="toggleSidebar"
      >
        <span class="sidebar-toggle-icon">☰</span>
        <span v-if="!isMobile">{{ isSidebarCollapsed ? '展开导航' : '收起导航' }}</span>
      </button>

      <AgentChatWindow
        :messages="messages"
        :thinking="isThinking"
        :rag-mode="useRagMode"
        @send="handleAsk"
        @toggle-rag="toggleRagMode"
      />

      <el-button
        class="right-panel-toggle"
        size="small"
        plain
        @click="toggleRightPanel"
      >
        {{ isRightPanelCollapsed ? '展开任务状态' : '收起任务状态' }}
      </el-button>
    </div>

    <div class="right-panel-wrapper" :class="{ 'collapsed': isRightPanelCollapsed }">
      <AgentRightPanel
        v-show="!isRightPanelCollapsed"
        :status="runStatus"
        :current-run-id="currentRunId"
        :result-url="resultUrl"
        :result-name="resultName"
        :tool-preview="currentToolPreview"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import AgentSidebar from '../components/agent/AgentSidebar.vue'
import AgentChatWindow from '../components/agent/AgentChatWindow.vue'
import AgentRightPanel from '../components/agent/AgentRightPanel.vue'
import {
  listSessions,
  getSessionMessages,
  askAgent,
  getRunStatus,
  type AgentSession,
  type AgentMessage
} from '../api/agent'
import { searchAndAsk } from '../api/tutorials'

// State
const sessions = ref<AgentSession[]>([])
const sessionsLoading = ref(false)
const currentSessionId = ref<number>()
const messages = ref<AgentMessage[]>([])
const isThinking = ref(false)
const useRagMode = ref(false)

// Layout State
const isMobile = ref(false)
const isSidebarCollapsed = ref(false)
const isRightPanelCollapsed = ref(false)

// Run Status
const currentRunId = ref<number>()
const runStatus = ref('idle')
const resultUrl = ref('')
const resultName = ref('')
let pollTimer: number | undefined
const AGENT_STATE_KEY = 'msut-agent-state'
const currentToolPreview = ref<{ name: string; arguments: string } | null>(null)

interface PersistedAgentState {
  sessionId?: number
  runId?: number
}

function checkMobile() {
  const mobile = window.innerWidth < 768
  isMobile.value = mobile
  
  // Only auto-collapse on initial load or resize to mobile
  // We don't want to auto-expand on resize to desktop if user intentionally collapsed it
  if (mobile) {
    isSidebarCollapsed.value = true
    isRightPanelCollapsed.value = true
  } else {
    // On desktop, default to expanded if it was just a resize
    // Ideally we might want to persist user preference, but for now:
    // If we are switching from mobile to desktop, let's expand them
    // This logic can be refined if we want strict persistence
    if (isSidebarCollapsed.value && isRightPanelCollapsed.value) {
       isSidebarCollapsed.value = false
       isRightPanelCollapsed.value = false
    }
  }
}

async function loadSessions() {
  sessionsLoading.value = true
  try {
    sessions.value = await listSessions()
  } catch (e) {
    console.error('Failed to load sessions', e)
  } finally {
    sessionsLoading.value = false
  }
}

function extractToolPreview(allMessages: AgentMessage[]): { name: string; arguments: string } | null {
  // 从最新消息往前找，优先使用 assistant 的 tool_calls，再退回到 tool 消息里的 tool_args。
  for (let i = allMessages.length - 1; i >= 0; i--) {
    const msg = allMessages[i]
    
    // 检查msg是否为空或未定义
    if (!msg) continue

    if (msg.role === 'assistant') {
      const payload: any = (msg as any).payload
      const toolCalls = payload && Array.isArray(payload.tool_calls) ? payload.tool_calls : []
      if (toolCalls.length > 0) {
        const first = toolCalls[0] || {}
        const fnInfo = first.function || {}
        const name = typeof fnInfo.name === 'string' ? fnInfo.name : ''
        let args: any = fnInfo.arguments ?? ''
        if (!name) continue
        if (typeof args === 'string' && args) {
          try {
            const parsed = JSON.parse(args)
            if (parsed && typeof parsed.dsl === 'string') {
              args = parsed.dsl
            }
          } catch {
            // ignore JSON parse errors, keep raw string
          }
        }
        if (typeof args === 'string' && args.trim()) {
          return { name, arguments: args }
        }
      }
    }

    if (msg.role === 'tool') {
      const name = msg.toolName || 'generate_melsave'
      let args: any = msg.toolArgs ?? ''
      if (typeof args === 'string' && args) {
        try {
          const parsed = JSON.parse(args)
          if (parsed && typeof parsed.dsl === 'string') {
            args = parsed.dsl
          }
        } catch {
          // ignore
        }
      }
      if (name && typeof args === 'string' && args.trim()) {
        return { name, arguments: args }
      }
    }
  }
  return null
}

function persistAgentState(partial?: Partial<PersistedAgentState>) {
  if (typeof window === 'undefined') return
  const current: PersistedAgentState = {
    sessionId: currentSessionId.value,
    runId: currentRunId.value
  }
  const next: PersistedAgentState = { ...current, ...partial }
  try {
    window.localStorage.setItem(AGENT_STATE_KEY, JSON.stringify(next))
  } catch {
    // ignore storage errors
  }
}

async function restoreAgentState() {
  if (typeof window === 'undefined') return
  let raw: string | null = null
  try {
    raw = window.localStorage.getItem(AGENT_STATE_KEY)
  } catch {
    raw = null
  }
  if (!raw) return

  let parsed: PersistedAgentState | null = null
  try {
    parsed = JSON.parse(raw) as PersistedAgentState
  } catch {
    parsed = null
  }
  if (!parsed || !parsed.sessionId) return

  const sessionId = parsed.sessionId
  // Ensure the session still exists
  if (!sessions.value.some((s) => s.id === sessionId)) {
    return
  }

  currentSessionId.value = sessionId
  try {
    messages.value = await getSessionMessages(sessionId)
    currentToolPreview.value = extractToolPreview(messages.value)
  } catch (e) {
    console.error('Failed to restore messages', e)
  }

  const runId = parsed.runId
  if (!runId) return

  try {
    const status = await getRunStatus(runId)
    currentRunId.value = status.runId
    runStatus.value = status.status
    resultUrl.value = status.resultUrl || ''
    resultName.value = status.resultName || ''

    // If the run is still in progress, resume polling and show thinking indicator
    if (status.status === 'pending' || status.status === 'running') {
      isThinking.value = true
      startPolling(status.runId)
    }
  } catch (e) {
    console.error('Failed to restore run status', e)
    try {
      window.localStorage.removeItem(AGENT_STATE_KEY)
    } catch {
      // ignore
    }
  }
}

async function handleNewChat() {
  currentSessionId.value = undefined
  messages.value = []
  currentRunId.value = undefined
  runStatus.value = 'idle'
  resultUrl.value = ''
  resultName.value = ''
  persistAgentState({ sessionId: undefined, runId: undefined })
  if (isMobile.value) {
    isSidebarCollapsed.value = true
  }
}

function toggleRagMode() {
  useRagMode.value = !useRagMode.value
  if (useRagMode.value) {
    stopPolling()
    runStatus.value = 'idle'
    currentRunId.value = undefined
    resultUrl.value = ''
    resultName.value = ''
    persistAgentState({ runId: undefined })
  }
}

function toggleSidebar() {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
  if (isMobile.value && !isSidebarCollapsed.value) {
    isRightPanelCollapsed.value = true // Close other panel on mobile
  }
}

function toggleRightPanel() {
  isRightPanelCollapsed.value = !isRightPanelCollapsed.value
  if (isMobile.value && !isRightPanelCollapsed.value) {
    isSidebarCollapsed.value = true // Close other panel on mobile
  }
}

function closeAllPanels() {
  if (isMobile.value) {
    isSidebarCollapsed.value = true
    isRightPanelCollapsed.value = true
  }
}

async function handleSelectSession(id: number) {
  if (currentSessionId.value === id) return
  
  currentSessionId.value = id
  currentRunId.value = undefined // Reset run status when switching
  runStatus.value = 'idle'
  resultUrl.value = ''
  resultName.value = ''
  
  if (isMobile.value) {
    isSidebarCollapsed.value = true
  }

  try {
    messages.value = await getSessionMessages(id)
    persistAgentState({ sessionId: id, runId: undefined })
    currentToolPreview.value = extractToolPreview(messages.value)
  } catch (e) {
    ElMessage.error('加载消息失败')
  }
}

async function handleAsk(text: string) {
  // Optimistic update
  const tempMsg: AgentMessage = {
    id: Date.now(),
    role: 'user',
    content: text,
    created_at: new Date().toISOString()
  }
  messages.value.push(tempMsg)
  isThinking.value = true

  if (useRagMode.value) {
    try {
      const res = await searchAndAsk({ query: text, mode: 'both' })
      const answerText =
        (res.answer && res.answer.text) ||
        '暂时没有基于教程内容找到合适的回答，请尝试换一种问法。'

      const reply: AgentMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: answerText,
        created_at: new Date().toISOString()
      }
      messages.value.push(reply)
    } catch (e) {
      ElMessage.error('RAG 模式请求失败')
    } finally {
      isThinking.value = false
    }
    currentToolPreview.value = null
    return
  }

  try {
    const res = await askAgent(currentSessionId.value, text)
    
    if (res.created) {
      // If a new session was created, reload list and set ID
      await loadSessions()
      currentSessionId.value = res.sessionId
    }
    
    currentRunId.value = res.runId
    runStatus.value = res.status
    persistAgentState({ sessionId: currentSessionId.value, runId: currentRunId.value })
    startPolling(res.runId)
    
  } catch (e) {
    ElMessage.error('发送失败')
    isThinking.value = false
  }
}

function startPolling(runId: number) {
  if (pollTimer) clearInterval(pollTimer)
  
  pollTimer = window.setInterval(async () => {
    try {
      const status = await getRunStatus(runId)
      runStatus.value = status.status
      resultUrl.value = status.resultUrl || ''
      resultName.value = status.resultName || ''
      persistAgentState({ runId: runId })
      
      // Refresh messages to see updates (tool calls, partial answers, etc.)
      if (currentSessionId.value) {
        messages.value = await getSessionMessages(currentSessionId.value)
        currentToolPreview.value = extractToolPreview(messages.value)
      }

      if (status.status === 'succeeded' || status.status === 'failed') {
        stopPolling()
        isThinking.value = false
        persistAgentState({ runId: runId })
        // 任务结束后仍保留最后一次工具输入，方便查看；如需清空可在此处置空。
        if (status.status === 'failed') {
          ElMessage.error(status.error || '任务执行失败')
        }
      }
    } catch (e) {
      console.error('Poll failed', e)
    }
  }, 1000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = undefined
  }
}

onMounted(async () => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  await loadSessions()
  await restoreAgentState()
})

onBeforeUnmount(() => {
  stopPolling()
  window.removeEventListener('resize', checkMobile)
})
</script>

<style scoped>
.agent-page {
  height: calc(100vh - 78px); /* Adjust based on your header height */
  display: flex;
  background: #ffffff;
  overflow: hidden;
  position: relative;
}

.agent-main {
  flex: 1;
  display: flex;
  position: relative;
  min-width: 0; /* Prevent flex item from overflowing */
}

/* Sidebar Wrapper */
.sidebar-wrapper {
  width: 260px;
  flex-shrink: 0;
  transition: width 0.3s ease, transform 0.3s ease;
  overflow: hidden;
  border-right: 1px solid #e5e7eb;
  background: #fff;
}

.sidebar-wrapper.collapsed {
  width: 0;
  border-right: none;
}

/* Right Panel Wrapper */
.right-panel-wrapper {
  width: 300px;
  flex-shrink: 0;
  transition: width 0.3s ease, transform 0.3s ease;
  overflow: hidden;
  border-left: 1px solid #e5e7eb;
  background: #fff;
  min-width: 0;
}

.right-panel-wrapper.collapsed {
  width: 0;
  border-left: none;
  min-width: 0;
}

.sidebar-toggle {
  position: absolute;
  top: 16px;
  left: 16px;
  z-index: 10;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 999px;
  border: none;
  background: #111827;
  color: #ffffff;
  font-size: 12px;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25);
  transition: left 0.3s ease;
}

.sidebar-toggle-icon {
  font-size: 14px;
}

.sidebar-toggle:hover {
  background: #000000;
}

.right-panel-toggle {
  position: absolute;
  top: 50%;
  right: 0;
  transform: translateY(-50%);
  z-index: 10;
  border-radius: 16px 0 0 16px;
}

/* Mobile Styles */
.mobile-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 40;
}

@media (max-width: 768px) {
  .sidebar-wrapper {
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    width: 280px; /* Slightly wider on mobile */
    z-index: 50;
    transform: translateX(0);
    border-right: 1px solid #e5e7eb;
    box-shadow: 2px 0 8px rgba(0,0,0,0.1);
  }

  .sidebar-wrapper.collapsed {
    width: 280px; /* Keep width for animation */
    transform: translateX(-100%);
    border-right: none;
  }

  .right-panel-wrapper {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    width: 300px;
    z-index: 50;
    transform: translateX(0);
    border-left: 1px solid #e5e7eb;
    box-shadow: -2px 0 8px rgba(0,0,0,0.1);
    min-width: 0;
  }

  .right-panel-wrapper.collapsed {
    width: 300px;
    transform: translateX(100%);
    border-left: none;
    min-width: 0;
  }
}
</style>
