<template>
  <el-popover placement="bottom-end" trigger="click" width="320" @show="refresh">
    <template #reference>
      <button class="bell-button" aria-label="通知">
        <el-badge :value="count" :hidden="count === 0" class="bell-badge">
          <el-icon><Bell /></el-icon>
        </el-badge>
      </button>
    </template>

    <div class="notification-panel">
      <div class="panel-header">
        <span class="title">通知</span>
        <span class="total">{{ total }} 条</span>
      </div>
      <div v-if="loading" class="panel-loading">
        <el-skeleton animated :rows="3" />
      </div>
      <div v-else>
        <div v-if="items.length" class="panel-list">
          <button
            v-for="item in items"
            :key="item.id"
            class="panel-item"
            @click="goTo(item)"
          >
            <div class="item-title">{{ formatTitle(item) }}</div>
            <div class="item-meta">
              <span class="actor">{{ formatActor(item.actor) }}</span>
              <span class="time">{{ formatTime(item.created_at) }}</span>
            </div>
          </button>
        </div>
        <div v-else class="panel-empty">暂无通知</div>
      </div>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Bell } from '@element-plus/icons-vue'
import { listUnreadNotifications, type NotificationItem } from '../api/notifications'

const router = useRouter()
const items = ref<NotificationItem[]>([])
const loading = ref(false)
const total = ref(0)
const count = computed(() => total.value)
let timer: number | null = null

async function refresh() {
  loading.value = true
  try {
    const data = await listUnreadNotifications()
    items.value = data.items || []
    total.value = data.total || 0
  } catch {
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function formatActor(actor: NotificationItem['actor']) {
  return actor.name || actor.username || '用户'
}

function formatTitle(item: NotificationItem) {
  const title = item.resource?.title || item.comment?.content || item.content || ''
  switch (item.type) {
    case 'resource_like':
      return `你的作品收到点赞：${title}`
    case 'comment_like':
      return `你的评论收到点赞：${title}`
    case 'comment_reply':
      return `你的评论收到回复：${title}`
    default:
      return title
  }
}

function formatTime(value: string) {
  return value ? value.replace('T', ' ').replace('Z', '') : ''
}

function goTo(item: NotificationItem) {
  if (item.resource?.slug) {
    router.push(`/share/${item.resource.slug}`)
  }
}

onMounted(() => {
  refresh()
  timer = window.setInterval(refresh, 30000)
})

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<style scoped>
.bell-button {
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px 8px;
  color: #475569;
}

.bell-button:hover {
  color: #111827;
}

.notification-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-header .title {
  font-weight: 600;
  color: #0f172a;
}

.panel-header .total {
  font-size: 12px;
  color: #94a3b8;
}

.panel-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.panel-item {
  text-align: left;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
  background: #f8fafc;
  cursor: pointer;
}

.panel-item:hover {
  background: #eef2ff;
}

.item-title {
  font-size: 13px;
  color: #0f172a;
  margin-bottom: 6px;
}

.item-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #64748b;
}

.panel-empty {
  text-align: center;
  font-size: 13px;
  color: #94a3b8;
  padding: 10px 0;
}
</style>
