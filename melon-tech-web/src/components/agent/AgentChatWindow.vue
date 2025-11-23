<template>
  <div class="agent-chat-window">
    <div class="messages-area" ref="messagesContainer">
      <div v-if="messages.length === 0" class="welcome-state">
        <div class="welcome-icon">
          <el-icon><Service /></el-icon>
        </div>
        <h2>我是您的智能助手</h2>
        <p>我可以帮您生成芯片代码、回答教程问题或执行其他任务。</p>
      </div>
      
      <div v-else class="message-list">
        <div
          v-for="msg in messages"
          :key="msg.id || msg.created_at"
          class="message-row"
          :class="getRowClass(msg)"
        >
          <div class="avatar">
            <el-avatar v-if="msg.role === 'user'" :icon="UserFilled" class="user-avatar" :size="36" />
            <div v-else class="ai-avatar">
              <el-icon><Service /></el-icon>
            </div>
          </div>
          
          <div class="content-wrapper">
            <div class="bubble" v-html="renderMarkdown(msg.content)"></div>
            <div v-if="msg.role === 'tool'" class="tool-output">
              <el-tag size="small" type="info">工具调用: {{ msg.toolName }}</el-tag>
            </div>
            <div
              v-if="msg.role === 'assistant' && hasThinking(msg)"
              class="thinking-debug"
            >
              <div class="thinking-header" @click="toggleThinking(msg)">
                <span class="thinking-label">思考过程</span>
                <span class="thinking-toggle">
                  {{ isThinkingExpanded(msg) ? '收起' : '展开' }}
                </span>
              </div>
              <div v-if="isThinkingExpanded(msg)" class="thinking-body">
                <pre class="thinking-text">{{ getThinkingText(msg) }}</pre>
              </div>
            </div>
          </div>
        </div>

        <div v-if="thinking" class="message-row ai-row">
          <div class="avatar">
            <div class="ai-avatar">
              <el-icon><Service /></el-icon>
            </div>
          </div>
          <div class="content-wrapper">
            <div class="bubble thinking-bubble">
              <span class="dot"></span><span class="dot"></span><span class="dot"></span>
              <span class="thinking-text">思考中...</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="input-area">
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
      <div class="footer-tip">
        内容由 AI 生成，请仔细甄别
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { UserFilled, Service, Position } from '@element-plus/icons-vue'
import { marked } from 'marked'
import type { AgentMessage } from '../../api/agent'

const props = defineProps<{
  messages: AgentMessage[]
  thinking?: boolean
}>()

const emit = defineEmits<{
  (e: 'send', text: string): void
}>()

const inputValue = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const thinkingExpanded = ref<Record<number, boolean>>({})

function getRowClass(msg: AgentMessage) {
  if (msg.role === 'user') return 'user-row'
  return 'ai-row'
}

function hasThinking(msg: AgentMessage) {
  const payload: any = (msg as any).payload
  return !!(payload && typeof payload === 'object' && payload.thinking)
}

function getThinkingText(msg: AgentMessage) {
  const payload: any = (msg as any).payload
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

function renderMarkdown(text: string) {
  if (!text) return ''
  return marked.parse(text)
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
.agent-chat-window {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f9fafb;
  height: 100%;
  overflow: hidden;
  position: relative;
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
}

.welcome-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  padding-bottom: 10%;
}

.welcome-icon {
  width: 64px;
  height: 64px;
  background: #e0e7ff;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  color: #4f46e5;
  font-size: 32px;
}

.welcome-state h2 {
  color: #111827;
  margin: 0 0 12px;
  font-weight: 600;
}

.message-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding-bottom: 20px;
}

.message-row {
  display: flex;
  gap: 16px;
  max-width: 85%;
}

.user-row {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.ai-row {
  align-self: flex-start;
}

.avatar {
  flex-shrink: 0;
}

.user-avatar {
  background: #3b82f6;
}

.ai-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 18px;
  box-shadow: 0 2px 4px rgba(16, 185, 129, 0.2);
}

.content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.bubble {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 15px;
  line-height: 1.6;
  word-break: break-word;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.user-row .bubble {
  background: #3b82f6;
  color: white;
  border-bottom-right-radius: 4px;
}

.ai-row .bubble {
  background: #ffffff;
  color: #1f2937;
  border-bottom-left-radius: 4px;
  border: 1px solid #e5e7eb;
}

.bubble :deep(p) {
  margin: 0 0 0.8em;
}
.bubble :deep(p:last-child) {
  margin-bottom: 0;
}
.bubble :deep(pre) {
  background: #f3f4f6;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}
.bubble :deep(code) {
  font-family: monospace;
  background: rgba(0,0,0,0.05);
  padding: 2px 4px;
  border-radius: 4px;
}
.user-row .bubble :deep(code) {
  background: rgba(255,255,255,0.2);
}

.tool-output {
  font-size: 12px;
  opacity: 0.8;
}

.thinking-debug {
  margin-top: 4px;
  padding: 6px 10px;
  border-radius: 8px;
  background: #f3f4f6;
  border: 1px dashed #d1d5db;
  font-size: 12px;
  color: #4b5563;
}

.thinking-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
}

.thinking-label {
  color: #6b7280;
}

.thinking-toggle {
  color: #3b82f6;
}

.thinking-body {
  margin-top: 4px;
  max-height: 200px;
  overflow-y: auto;
}

.thinking-text {
  margin: 0;
  white-space: pre-wrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

.thinking-bubble {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #6b7280;
  font-style: italic;
  background: #e5e7eb;
  border-radius: 12px;
  border: 1px solid #d1d5db;
}

.dot {
  width: 4px;
  height: 4px;
  background: #9ca3af;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}
.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }
@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.input-area {
  padding: 20px;
  background: #ffffff;
  border-top: 1px solid #e5e7eb;
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
  border-color: #3b82f6;
  background: #ffffff;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

.input-box :deep(.el-textarea__inner) {
  box-shadow: none !important;
  background: transparent;
  padding: 4px;
  font-size: 15px;
}

.send-btn {
  flex-shrink: 0;
}

.footer-tip {
  text-align: center;
  font-size: 12px;
  color: #9ca3af;
  margin-top: 8px;
}
</style>
