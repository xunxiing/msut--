<template>
  <div class="ai-page">
    <div class="ai-container">
      <div class="ai-inner">
        <header class="ai-header">
          <div class="ai-title-block">
          </div>
          <div class="ai-header-actions">
            <el-button @click="goBack">返回教程列表</el-button>
          </div>
        </header>

        <div class="chat-layout">
          <div class="chat-messages" ref="messagesContainer">
            <div v-if="messages.length === 0" class="empty-state">
              <el-icon class="empty-icon"><ChatDotRound /></el-icon>
              <h3>有什么可以帮您？</h3>
              <p>您可以询问关于教程的任何问题，例如：</p>
              <div class="suggestion-chips">
                <el-tag
                  v-for="q in suggestions"
                  :key="q"
                  class="suggestion-chip"
                  effect="plain"
                  round
                  @click="ask(q)"
                >
                  {{ q }}
                </el-tag>
              </div>
            </div>

            <div
              v-for="(msg, index) in messages"
              :key="index"
              class="message-row"
              :class="{ 'user-row': msg.role === 'user', 'ai-row': msg.role === 'ai' }"
            >
              <div class="message-avatar">
                <el-avatar v-if="msg.role === 'user'" :icon="UserFilled" class="user-avatar" />
                <div v-else class="ai-avatar">
                  <el-icon><Service /></el-icon>
                </div>
              </div>
              <div class="message-content">
                <div class="message-bubble" v-html="renderMarkdown(msg.content)"></div>
                <div v-if="msg.sources && msg.sources.length" class="message-sources">
                  <p class="sources-title">参考来源：</p>
                  <ul class="sources-list">
                    <li v-for="(source, sIdx) in msg.sources" :key="sIdx">
                      <a :href="`/tutorials?id=${source.tutorialId}`" target="_blank" class="source-link">
                        {{ source.title }}
                      </a>
                    </li>
                  </ul>
                </div>
              </div>
            </div>

            <div v-if="loading && !streaming" class="message-row ai-row">
              <div class="message-avatar">
                <div class="ai-avatar">
                  <el-icon><Service /></el-icon>
                </div>
              </div>
              <div class="message-content">
                <div class="message-bubble loading-bubble">
                  <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                </div>
              </div>
            </div>
          </div>

          <div class="chat-input-area">
            <div class="input-wrapper">
              <el-input
                v-model="inputQuery"
                type="textarea"
                :rows="1"
                :autosize="{ minRows: 1, maxRows: 6 }"
                placeholder="输入您的问题..."
                resize="none"
                @keydown.enter.prevent="handleEnter"
              />
              <el-button type="primary" :icon="Position" circle :disabled="!inputQuery.trim() || loading" @click="handleSend" />
            </div>
            <p class="disclaimer">AI 回答可能存在误差，请以原始教程内容为准。</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ChatDotRound, UserFilled, Service, Position } from '@element-plus/icons-vue'
import { marked } from 'marked'
import { searchAndAsk, searchAndAskStream, type TutorialSearchResult } from '../api/tutorials'
import { ElMessage } from 'element-plus'

const router = useRouter()

type Message = {
  role: 'user' | 'ai'
  content: string
  sources?: TutorialSearchResult[]
}

const messages = ref<Message[]>([])
const inputQuery = ref('')
const loading = ref(false)
const streaming = ref(false)
const messagesContainer = ref<HTMLElement | null>(null)
const streamController = ref<AbortController | null>(null)

const suggestions = [
  '如何安装模组？',
  '怎么制作自定义人物？',
  '游戏崩溃了怎么办？'
]

onBeforeUnmount(() => {
  streamController.value?.abort()
})

function goBack() {
  router.push('/tutorials')
}

function renderMarkdown(text: string) {
  return marked.parse(text)
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

async function tryStreamAnswer(query: string, aiMsg: Message) {
  streamController.value?.abort()
  const controller = new AbortController()
  streamController.value = controller

  streaming.value = true
  let hasContent = false
  let streamError = false

  try {
    const result = await searchAndAskStream(
      { query, mode: 'qa' },
      {
        signal: controller.signal,
        onEvent: (evt) => {
          const type = (evt as Record<string, unknown>).event
          if (type === 'meta' && Array.isArray((evt as any).sources)) {
            aiMsg.sources = (evt as any).sources
          } else if (type === 'token') {
            const chunk = (evt as any).text
            if (chunk) {
              aiMsg.content += String(chunk)
              hasContent = true
              scrollToBottom()
            }
          } else if (type === 'error') {
            streamError = true
          }
        },
      },
    )

    if (streamError) {
      return false
    }

    if (!result.streamed) {
      if (result.data?.answer) {
        aiMsg.content = result.data.answer.text
        aiMsg.sources = result.data.answer.sources || []
      } else {
        aiMsg.content = '抱歉，我没有找到相关的答案。'
      }
      return true
    }

    if (!hasContent) {
      aiMsg.content = '抱歉，我没有找到相关的答案。'
    }
    return true
  } catch (err: any) {
    if (err?.name === 'AbortError') {
      return true
    }
    return false
  } finally {
    streaming.value = false
  }
}

async function ask(query: string) {
  if (loading.value) return

  messages.value.push({ role: 'user', content: query })
  scrollToBottom()

  const aiMsg: Message = { role: 'ai', content: '' }
  messages.value.push(aiMsg)
  scrollToBottom()

  loading.value = true
  try {
    const handled = await tryStreamAnswer(query, aiMsg)
    if (!handled || !aiMsg.content) {
      const res = await searchAndAsk({ query, mode: 'qa' })
      if (res.answer) {
        aiMsg.content = res.answer.text
        aiMsg.sources = res.answer.sources
      } else {
        aiMsg.content = '抱歉，我没有找到相关的答案。'
      }
    }
  } catch (e: any) {
    ElMessage.error('请求失败，请稍后重试')
    aiMsg.content = '抱歉，发生了一些错误，请稍后重试。'
  } finally {
    loading.value = false
    streaming.value = false
    scrollToBottom()
  }
}

function handleSend() {
  const q = inputQuery.value.trim()
  if (!q) return
  inputQuery.value = ''
  ask(q)
}

function handleEnter(e: KeyboardEvent) {
  if (!e.shiftKey) {
    handleSend()
  }
}
</script>

<style scoped>
.ai-page {
  min-height: calc(100vh - 56px);
  height: calc(100vh - 56px);
  overflow: hidden;
  background: #f3f4f6;
  display: flex;
  flex-direction: column;
  padding: 12px 12px 24px;
  box-sizing: border-box;
}
.ai-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}
.ai-inner {
  max-width: 1000px;
  margin: 0 auto;
  padding: 16px;
  width: 100%;
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
  box-sizing: border-box;
  min-height: 0;
}
.ai-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
  flex-shrink: 0;
}
.ai-title-block h1 {
  margin: 0 0 6px;
  font-size: 22px;
}
.ai-subtitle {
  margin: 0;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.chat-layout {
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  max-width: 100%;
  min-height: 0;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  min-height: 0;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-secondary);
  text-align: center;
  padding-bottom: 10%;
}
.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
  color: #d1d5db;
}
.empty-state h3 {
  margin: 0 0 8px;
  font-size: 18px;
  color: #374151;
}
.suggestion-chips {
  display: flex;
  gap: 8px;
  margin-top: 16px;
  flex-wrap: wrap;
  justify-content: center;
}
.suggestion-chip {
  cursor: pointer;
  transition: all 0.2s;
}
.suggestion-chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.message-row {
  display: flex;
  gap: 16px;
  max-width: 85%;
  width: 100%;
}
.user-row {
  align-self: flex-end;
  flex-direction: row-reverse;
}
.ai-row {
  align-self: flex-start;
}

.message-avatar {
  flex-shrink: 0;
}
.user-avatar {
  background: #3b82f6;
}
.ai-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #10b981;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 20px;
}

.message-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0; /* Prevent overflow */
}

.message-bubble {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 15px;
  line-height: 1.6;
  word-break: break-word;
}
.user-row .message-bubble {
  background: #3b82f6;
  color: white;
  border-bottom-right-radius: 4px;
}
.ai-row .message-bubble {
  background: #f3f4f6;
  color: #1f2937;
  border-bottom-left-radius: 4px;
}

.message-bubble :deep(p) {
  margin: 0 0 0.8em;
}
.message-bubble :deep(p:last-child) {
  margin-bottom: 0;
}
.message-bubble :deep(ul), .message-bubble :deep(ol) {
  padding-left: 1.5em;
  margin-bottom: 0.8em;
}
.message-bubble :deep(code) {
  background: rgba(0,0,0,0.1);
  padding: 2px 4px;
  border-radius: 4px;
  font-family: monospace;
}
.user-row .message-bubble :deep(code) {
  background: rgba(255,255,255,0.2);
}

.message-sources {
  font-size: 12px;
  color: #6b7280;
  background: #f9fafb;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid #f3f4f6;
}
.sources-title {
  margin: 0 0 4px;
  font-weight: 600;
}
.sources-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.source-link {
  color: #3b82f6;
  text-decoration: none;
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.source-link:hover {
  text-decoration: underline;
}

.loading-bubble {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 16px 20px;
}
.dot {
  width: 6px;
  height: 6px;
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

.chat-input-area {
  padding: 20px;
  border-top: 1px solid #e5e7eb;
  background: #ffffff;
}
.input-wrapper {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  background: #f9fafb;
  padding: 8px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  transition: border-color 0.2s;
}
.input-wrapper:focus-within {
  border-color: #3b82f6;
  background: #ffffff;
}
.input-wrapper :deep(.el-textarea__inner) {
  box-shadow: none !important;
  background: transparent;
  padding: 8px;
}
.disclaimer {
  margin: 8px 0 0;
  font-size: 12px;
  color: #9ca3af;
  text-align: center;
}
</style>
