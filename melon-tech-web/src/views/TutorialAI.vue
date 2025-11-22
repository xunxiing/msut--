<template>
  <div class="agent-page">
    <AgentSidebar
      :sessions="sessions"
      :current-session-id="currentSessionId"
      :loading="sessionsLoading"
      @new-chat="handleNewChat"
      @select-session="handleSelectSession"
    />
    
    <AgentChatWindow
      :messages="messages"
      :thinking="isThinking"
      @send="handleAsk"
    />
    
    <AgentRightPanel
      :status="runStatus"
      :current-run-id="currentRunId"
      :result-url="resultUrl"
      :result-name="resultName"
    />
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

// State
const sessions = ref<AgentSession[]>([])
const sessionsLoading = ref(false)
const currentSessionId = ref<number>()
const messages = ref<AgentMessage[]>([])
const isThinking = ref(false)

// Run Status
const currentRunId = ref<number>()
const runStatus = ref('idle')
const resultUrl = ref('')
const resultName = ref('')
let pollTimer: number | undefined

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

async function handleNewChat() {
  currentSessionId.value = undefined
  messages.value = []
  currentRunId.value = undefined
  runStatus.value = 'idle'
  resultUrl.value = ''
  resultName.value = ''
}

async function handleSelectSession(id: number) {
  if (currentSessionId.value === id) return
  
  currentSessionId.value = id
  currentRunId.value = undefined // Reset run status when switching
  runStatus.value = 'idle'
  resultUrl.value = ''
  resultName.value = ''
  
  try {
    messages.value = await getSessionMessages(id)
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

  try {
    const res = await askAgent(currentSessionId.value, text)
    
    if (res.created) {
      // If a new session was created, reload list and set ID
      await loadSessions()
      currentSessionId.value = res.sessionId
    }
    
    currentRunId.value = res.runId
    runStatus.value = res.status
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
      
      // Refresh messages to see updates (tool calls, partial answers, etc.)
      if (currentSessionId.value) {
        messages.value = await getSessionMessages(currentSessionId.value)
      }

      if (status.status === 'succeeded' || status.status === 'failed') {
        stopPolling()
        isThinking.value = false
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

onMounted(() => {
  loadSessions()
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<style scoped>
.agent-page {
  height: calc(100vh - 56px); /* Adjust based on your header height */
  display: flex;
  background: #ffffff;
  overflow: hidden;
}
</style>
