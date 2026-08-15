<template>
  <div class="chat-window">
    <div class="messages-area" ref="messagesContainer" @click="handleMessagesClick">
      <div v-if="messages.length === 0" class="welcome-state">
        <div class="welcome-icon">
          <el-icon><Service /></el-icon>
        </div>
        <h2>智能助手</h2>
        <p>我可以帮您生成芯片代码、回答教程问题或执行其他任务。</p>
        <div class="welcome-examples">
          <button v-for="ex in examples" :key="ex" class="example-chip" @click="useExample(ex)">{{ ex }}</button>
        </div>
      </div>

      <div v-else class="message-list">
        <template v-for="msg in messages" :key="msg.id || msg.created_at">
          <div class="message-row" :class="getRowClass(msg)">
            <div class="avatar-col">
              <el-avatar v-if="msg.role === 'user'" :icon="UserFilled" class="user-avatar" :size="36" />
              <div v-else class="ai-avatar">
                <el-icon><Service /></el-icon>
              </div>
            </div>

            <div class="content-wrapper">
              <div class="role-label">{{ msg.role === 'user' ? '你' : 'AI 助手' }}</div>

              <div v-if="msg.role === 'tool'" class="timeline-trace">
                <div class="trace-node">
                  <div class="trace-icon-col">
                    <div class="trace-icon trace-icon-tool">
                      <el-icon><Tools /></el-icon>
                    </div>
                    <div class="trace-line"></div>
                  </div>
                  <div class="trace-content-col">
                    <div class="trace-label">工具调用 · {{ msg.toolName || getToolName(msg) }}</div>
                    <div v-if="getToolFile(msg)" class="trace-file-row">
                      <el-icon class="trace-file-icon"><Document /></el-icon>
                      <span class="trace-file-name">{{ getToolFile(msg)?.filename || '生成文件.melsave' }}</span>
                      <DownloadButton
                        :href="getToolFile(msg)?.url || ''"
                        :download-name="getToolFile(msg)?.filename || ''"
                        as="link"
                        type="primary"
                        size="small"
                      >
                        下载
                      </DownloadButton>
                    </div>
                    <div v-if="getDisplayContent(msg)" class="trace-desc">{{ getDisplayContent(msg) }}</div>
                  </div>
                </div>
              </div>

              <div v-else class="bubble" v-html="renderMarkdown(getDisplayContent(msg))"></div>

              <div
                v-if="msg.role === 'assistant' && hasThinking(msg)"
                class="timeline-trace"
              >
                <div class="trace-node">
                  <div class="trace-icon-col">
                    <div class="trace-icon trace-icon-think" @click="toggleThinking(msg)">
                      <el-icon><Cpu /></el-icon>
                    </div>
                    <div class="trace-line" :class="{ collapsed: !isThinkingExpanded(msg) }"></div>
                  </div>
                  <div class="trace-content-col">
                    <div class="trace-header" @click="toggleThinking(msg)">
                      <span class="trace-label clickable">思考过程</span>
                      <el-icon class="trace-arrow" :class="{ rotated: isThinkingExpanded(msg) }">
                        <ArrowDown />
                      </el-icon>
                    </div>
                    <div v-show="isThinkingExpanded(msg)" class="trace-body">
                      <pre class="trace-text">{{ getThinkingText(msg) }}</pre>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>

        <div v-if="thinking" class="message-row ai-row">
          <div class="avatar-col">
            <div class="ai-avatar">
              <el-icon><Service /></el-icon>
            </div>
          </div>
          <div class="content-wrapper">
            <div class="role-label">AI 助手</div>
            <div class="timeline-trace">
              <div class="trace-node">
                <div class="trace-icon-col">
                  <div class="trace-icon trace-icon-loading">
                    <span class="pulse-dot"></span>
                  </div>
                </div>
                <div class="trace-content-col">
                  <div class="trace-label trace-label-muted">思考中...</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="input-area">
      <div class="mode-toggle-row">
        <button
          type="button"
          class="mode-toggle-button"
          :class="{ active: ragMode }"
          @click="emit('toggle-rag')"
        >
          <span class="mode-toggle-pill">
            <span class="mode-toggle-dot"></span>
            <span class="mode-toggle-text">
              {{ ragMode ? 'AI+RAG 模式' : 'Agent 模式' }}
            </span>
          </span>
        </button>
      </div>
      <div class="input-box">
        <el-input
          v-model="inputValue"
          type="textarea"
          :rows="1"
          :autosize="{ minRows: 1, maxRows: 6 }"
          placeholder="输入您的问题..."
          resize="none"
          @keydown.enter.prevent="handleEnter"
          :disabled="thinking"
        />
        <el-button
          type="primary"
          :icon="Position"
          circle
          :disabled="!inputValue.trim() || thinking"
          @click="handleSend"
          class="send-btn"
        />
      </div>
      <div class="footer-tip">内容由 AI 生成，请仔细甄别</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { UserFilled, Service, Position, Cpu, ArrowDown, Tools, Document } from '@element-plus/icons-vue'
import { marked } from 'marked'
import type { AgentMessage } from '../../api/agent'
import DownloadButton from '../DownloadButton.vue'
import { triggerFileDownload } from '../../utils/fileDownload'

const props = defineProps<{
  messages: AgentMessage[]
  thinking?: boolean
  ragMode?: boolean
}>()

const emit = defineEmits<{
  (e: 'send', text: string): void
  (e: 'toggle-rag'): void
}>()

const inputValue = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const thinkingExpanded = ref<Record<number, boolean>>({})

const examples = [
  '帮我生成一个歼10C的芯片',
  '怎么创建联动开关？',
  '生成一个简易计时器',
]

function useExample(text: string) {
  inputValue.value = text
  handleSend()
}

function getRowClass(msg: AgentMessage) {
  if (msg.role === 'user') return 'user-row'
  return 'ai-row'
}

function getPayload(msg: AgentMessage): any | undefined {
  return (msg as any).payload
}

function hasThinking(msg: AgentMessage) {
  const payload = getPayload(msg)
  return !!(payload && typeof payload === 'object' && payload.thinking)
}

function getThinkingText(msg: AgentMessage) {
  const payload = getPayload(msg)
  const thinking = payload && typeof payload === 'object' ? payload.thinking : ''
  if (typeof thinking === 'string') return thinking
  if (!thinking) return ''
  try {
    return JSON.stringify(thinking, null, 2)
  } catch {
    return String(thinking)
  }
}

function isThinkingExpanded(msg: AgentMessage) {
  const id = msg.id || 0
  return !!thinkingExpanded.value[id]
}

function toggleThinking(msg: AgentMessage) {
  const id = msg.id || 0
  if (!id) return
  thinkingExpanded.value[id] = !thinkingExpanded.value[id]
}

function getToolName(msg: AgentMessage) {
  const payload = getPayload(msg)
  if (payload && typeof payload === 'object' && typeof payload.toolName === 'string') {
    return payload.toolName
  }
  return 'generate_melsave'
}

function getToolFile(msg: AgentMessage): { filename?: string; url?: string } | null {
  const payload = getPayload(msg)
  if (!payload || typeof payload !== 'object') return null
  const file = (payload as any).file
  if (!file || typeof file !== 'object') return null
  const url = (file as any).url
  if (!url || typeof url !== 'string') return null
  return {
    filename: (file as any).filename,
    url,
  }
}

function getDisplayContent(msg: AgentMessage) {
  if (msg.role === 'tool') {
    const payload = getPayload(msg)
    if (payload && typeof payload === 'object' && typeof (payload as any).message === 'string') {
      return (payload as any).message as string
    }
  }
  return msg.content || ''
}

function renderMarkdown(text: string) {
  if (!text) return ''
  return marked.parse(text)
}

function isDownloadUrl(href: string) {
  if (!href) return false
  try {
    const url = new URL(href, window.location.origin)
    const path = url.pathname.toLowerCase()
    return (
      path.endsWith('.melsave') ||
      path.startsWith('/api/files/') ||
      path.startsWith('/uploads/') ||
      path.startsWith('/msut/agent/')
    )
  } catch {
    return false
  }
}

function handleMessagesClick(event: MouseEvent) {
  const target = event.target as HTMLElement | null
  if (!target) return
  const anchor = target.closest('a') as HTMLAnchorElement | null
  if (!anchor) return
  const href = anchor.getAttribute('href') || ''
  if (!isDownloadUrl(href)) return
  event.preventDefault()
  triggerFileDownload(href, '')
}

function handleSend() {
  const text = inputValue.value.trim()
  if (!text) return
  inputValue.value = ''
  emit('send', text)
}

function handleEnter(e: KeyboardEvent) {
  if (!e.shiftKey) {
    handleSend()
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

watch(() => props.messages.length, scrollToBottom)
watch(() => props.thinking, scrollToBottom)
</script>

<style scoped>
.chat-window {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  height: 100%;
  overflow: hidden;
  position: relative;
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
}

.messages-area::-webkit-scrollbar {
  width: 5px;
}
.messages-area::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}
.messages-area::-webkit-scrollbar-track {
  background: transparent;
}

.welcome-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  padding-bottom: 8%;
}

.welcome-icon {
  width: 72px;
  height: 72px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  color: white;
  font-size: 36px;
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.25);
}

.welcome-state h2 {
  color: #111827;
  margin: 0 0 8px;
  font-weight: 700;
  font-size: 24px;
}

.welcome-state p {
  margin: 0 0 24px;
  font-size: 15px;
}

.welcome-examples {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  max-width: 480px;
}

.example-chip {
  padding: 8px 16px;
  border-radius: 999px;
  background: #fff;
  border: 1px solid #e5e7eb;
  font-size: 13px;
  color: #4b5563;
  cursor: pointer;
  transition: all 0.2s;
}

.example-chip:hover {
  border-color: #6366f1;
  color: #6366f1;
  background: #f5f3ff;
}

.message-list {
  display: flex;
  flex-direction: column;
  gap: 28px;
  padding-bottom: 20px;
  max-width: 820px;
  margin: 0 auto;
  width: 100%;
}

.message-row {
  display: flex;
  gap: 14px;
  min-width: 0;
}

.user-row {
  flex-direction: row-reverse;
}

.user-row .content-wrapper {
  align-items: flex-end;
}

.avatar-col {
  flex-shrink: 0;
}

.user-avatar {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
}

.ai-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 18px;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.15);
}

.content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  max-width: 78%;
}

.role-label {
  font-size: 12px;
  color: #9ca3af;
  font-weight: 500;
  padding: 0 2px;
}

.bubble {
  padding: 12px 16px;
  border-radius: 14px;
  font-size: 15px;
  line-height: 1.7;
  word-break: break-word;
}

.user-row .bubble {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border-bottom-right-radius: 4px;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.15);
}

.ai-row .bubble {
  background: #f9fafb;
  color: #1f2937;
  border-bottom-left-radius: 4px;
  border: 1px solid #e5e7eb;
}

.bubble :deep(p) { margin: 0 0 0.8em; }
.bubble :deep(p:last-child) { margin-bottom: 0; }
.bubble :deep(pre) {
  background: #f3f4f6;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
  font-size: 14px;
}
.bubble :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  background: rgba(0,0,0,0.06);
  padding: 2px 5px;
  border-radius: 4px;
  font-size: 14px;
}
.bubble :deep(h1), .bubble :deep(h2), .bubble :deep(h3) {
  margin: 0.6em 0 0.4em;
  font-weight: 600;
}
.bubble :deep(ul), .bubble :deep(ol) {
  padding-left: 1.5em;
  margin: 0.4em 0;
}
.bubble :deep(blockquote) {
  border-left: 3px solid #d1d5db;
  padding-left: 12px;
  margin: 0.4em 0;
  color: #6b7280;
}
.user-row .bubble :deep(code) {
  background: rgba(255,255,255,0.2);
}

/* Timeline trace — minimalist vertical flow */
.timeline-trace {
  display: flex;
  flex-direction: column;
}

.trace-node {
  display: flex;
  gap: 14px;
}

.trace-icon-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}

.trace-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
}

.trace-icon-tool {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #10b981;
}

.trace-icon-think {
  background: #f5f3ff;
  border: 1px solid #ddd6fe;
  color: #8b5cf6;
  cursor: pointer;
  transition: all 0.2s;
}

.trace-icon-think:hover {
  background: #ede9fe;
}

.trace-icon-loading {
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #9ca3af;
  animation: pulse 1.4s infinite ease-in-out both;
}

@keyframes pulse {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.trace-line {
  width: 1px;
  flex: 1;
  min-height: 12px;
  background: #e5e7eb;
  margin-top: 4px;
  margin-bottom: 4px;
}

.trace-line.collapsed {
  min-height: 0;
  height: 0;
}

.trace-content-col {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  padding-bottom: 4px;
  padding-top: 4px;
}

.trace-header {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  user-select: none;
}

.trace-label {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  line-height: 1.4;
}

.trace-label.clickable {
  cursor: pointer;
}

.trace-label-muted {
  color: #9ca3af;
  font-weight: 400;
  font-style: italic;
}

.trace-arrow {
  font-size: 12px;
  color: #9ca3af;
  transition: transform 0.3s ease;
}

.trace-arrow.rotated {
  transform: rotate(180deg);
}

.trace-file-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.trace-file-icon {
  font-size: 16px;
  color: #6366f1;
  flex-shrink: 0;
}

.trace-file-name {
  font-size: 14px;
  color: #1f2937;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 220px;
}

.trace-desc {
  font-size: 14px;
  color: #6b7280;
  line-height: 1.5;
}

.trace-body {
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #f3f4f6;
  padding: 12px 14px;
  max-height: 320px;
  overflow-y: auto;
}

.trace-body::-webkit-scrollbar {
  width: 5px;
}
.trace-body::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}
.trace-body::-webkit-scrollbar-track {
  background: transparent;
}

.trace-text {
  margin: 0;
  white-space: pre-wrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #4b5563;
}

.input-area {
  padding: 16px 20px 20px;
  background: #ffffff;
  border-top: 1px solid #e5e7eb;
}

.mode-toggle-row {
  display: flex;
  justify-content: flex-start;
  margin-bottom: 10px;
}

.mode-toggle-button {
  border: none;
  padding: 0;
  background: transparent;
  cursor: pointer;
  font: inherit;
}

.mode-toggle-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 999px;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  transition: all 0.2s ease;
  color: #4b5563;
}

.mode-toggle-button.active .mode-toggle-pill {
  background: #f5f3ff;
  border-color: #8b5cf6;
  color: #6d28d9;
}

.mode-toggle-dot {
  width: 18px;
  height: 18px;
  border-radius: 999px;
  background: #e5e7eb;
  transition: all 0.2s ease;
}

.mode-toggle-button.active .mode-toggle-dot {
  background: #8b5cf6;
}

.mode-toggle-text {
  font-size: 13px;
  font-weight: 500;
}

.input-box {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  background: #f9fafb;
  padding: 10px;
  border-radius: 16px;
  border: 1px solid #e5e7eb;
  transition: all 0.2s;
}

.input-box:focus-within {
  border-color: #8b5cf6;
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
}

.input-box :deep(.el-textarea__inner) {
  box-shadow: none !important;
  background: transparent;
  padding: 4px;
  font-size: 15px;
}

.send-btn {
  flex-shrink: 0;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  border: none;
}

.footer-tip {
  text-align: center;
  font-size: 12px;
  color: #9ca3af;
  margin-top: 8px;
}

@media (max-width: 768px) {
  .messages-area {
    padding: 16px 12px;
  }
  .message-list {
    gap: 20px;
  }
  .content-wrapper {
    max-width: 84%;
  }
  .ai-avatar, .user-avatar {
    width: 32px;
    height: 32px;
    font-size: 16px;
  }
  .trace-file-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  .welcome-icon {
    width: 56px;
    height: 56px;
    font-size: 28px;
    border-radius: 16px;
  }
  .welcome-state h2 {
    font-size: 20px;
  }
}
</style>
