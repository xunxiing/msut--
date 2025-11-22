<template>
  <div class="agent-sidebar">
    <div class="sidebar-header">
      <el-button type="primary" class="new-chat-btn" @click="$emit('new-chat')">
        <el-icon><Plus /></el-icon> 新建会话
      </el-button>
    </div>

    <div class="session-list">
      <div v-if="loading" class="loading-state">
        <el-skeleton :rows="5" animated />
      </div>
      <div v-else-if="sessions.length === 0" class="empty-state">
        <p>暂无历史会话</p>
      </div>
      <div v-else class="sessions-wrapper">
        <div
          v-for="session in sessions"
          :key="session.id"
          class="session-item"
          :class="{ active: currentSessionId === session.id }"
          @click="$emit('select-session', session.id)"
        >
          <div class="session-icon">
            <el-icon><ChatDotRound /></el-icon>
          </div>
          <div class="session-info">
            <div class="session-title">{{ session.title || '新会话' }}</div>
            <div class="session-time">{{ formatTime(session.updated_at) }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Plus, ChatDotRound } from '@element-plus/icons-vue'
import type { AgentSession } from '../../api/agent'

defineProps<{
  sessions: AgentSession[]
  currentSessionId?: number
  loading?: boolean
}>()

defineEmits<{
  (e: 'new-chat'): void
  (e: 'select-session', id: number): void
}>()

function formatTime(timeStr: string) {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  // Less than 24 hours
  if (diff < 24 * 60 * 60 * 1000) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
  // Less than 7 days
  if (diff < 7 * 24 * 60 * 60 * 1000) {
    return `${Math.floor(diff / (24 * 60 * 60 * 1000))}天前`
  }
  return date.toLocaleDateString()
}
</script>

<style scoped>
.agent-sidebar {
  width: 260px;
  height: 100%;
  background: #ffffff;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #f3f4f6;
}

.new-chat-btn {
  width: 100%;
  justify-content: center;
  height: 40px;
  font-weight: 500;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.loading-state {
  padding: 16px;
}

.empty-state {
  text-align: center;
  color: #9ca3af;
  padding-top: 40px;
  font-size: 14px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 4px;
  border: 1px solid transparent;
}

.session-item:hover {
  background: #f9fafb;
}

.session-item.active {
  background: #eff6ff;
  border-color: #dbeafe;
}

.session-icon {
  color: #6b7280;
  display: flex;
  align-items: center;
}

.session-item.active .session-icon {
  color: #3b82f6;
}

.session-info {
  flex: 1;
  min-width: 0;
}

.session-title {
  font-size: 14px;
  color: #374151;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
  font-weight: 500;
}

.session-item.active .session-title {
  color: #1d4ed8;
}

.session-time {
  font-size: 12px;
  color: #9ca3af;
}
</style>
