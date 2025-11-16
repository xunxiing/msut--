<template>
  <div class="tutorial-layout">
    <aside class="tutorial-sidebar">
      <div class="sidebar-header">
        <h1 class="sidebar-title">教程中心 · 文档库</h1>
        <p class="sidebar-subtitle">集中浏览与管理所有教程</p>
      </div>

      <el-input
        v-model="keyword"
        size="small"
        clearable
        placeholder="搜索教程标题或简介"
        class="sidebar-search"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>

      <div class="sidebar-list">
        <el-skeleton v-if="listLoading" :rows="6" animated />
        <template v-else>
          <div
            v-for="item in filteredTutorials"
            :key="item.id"
            :class="['tutorial-item', { active: item.id === selectedId }]"
            @click="onSelectTutorial(item.id)"
          >
            <div class="ti-title">{{ item.title }}</div>
            <div class="ti-desc">{{ item.description || '暂无简介' }}</div>
            <div class="ti-meta">{{ formatDate(item.created_at) }}</div>
          </div>
          <div v-if="!filteredTutorials.length" class="sidebar-empty">
            暂无教程或未找到匹配结果
          </div>
        </template>
      </div>
    </aside>

    <main class="tutorial-main">
      <div class="main-header">
        <div class="main-header-text">
          <h2 v-if="selectedTutorial" class="main-title">
            {{ selectedTutorial.title }}
          </h2>
          <h2 v-else class="main-title">请选择左侧一篇教程</h2>
          <p v-if="selectedTutorial" class="main-desc">
            {{ selectedTutorial.description || '暂无简介' }}
          </p>
        </div>
        <el-button size="small" @click="goBackToRAG">
          返回 AI 搜索
        </el-button>
      </div>

      <div v-if="detailLoading" class="main-loading">
        <el-skeleton :rows="10" animated />
      </div>
      <div v-else-if="selectedLines.length" class="main-body">
        <p v-for="(line, idx) in selectedLines" :key="idx">
          {{ line }}
        </p>
      </div>
      <div v-else class="main-placeholder">
        <p>从左侧选择一篇教程，以查看详细内容。</p>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import {
  listTutorials,
  getTutorial,
  type TutorialDetail,
  type TutorialItem,
} from '../api/tutorials'

const router = useRouter()

const tutorials = ref<TutorialItem[]>([])
const listLoading = ref(false)
const selectedId = ref<number | null>(null)
const selectedTutorial = ref<TutorialDetail | null>(null)
const detailLoading = ref(false)
const keyword = ref('')

const filteredTutorials = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) {
    return tutorials.value
  }
  return tutorials.value.filter((item) => {
    const text = `${item.title} ${item.description || ''}`.toLowerCase()
    return text.includes(kw)
  })
})

const selectedLines = computed(() => {
  const content = selectedTutorial.value?.content
  if (!content) return []
  return content.split(/\r?\n/).filter(Boolean)
})

function formatDate(value: string) {
  if (!value) return ''
  return value.slice(0, 10)
}

async function loadTutorialList() {
  listLoading.value = true
  try {
    const data = await listTutorials({ page: 1, pageSize: 50 })
    tutorials.value = data.items
    if (!selectedId.value && data.items.length > 0) {
      const first = data.items[0]
      if (first) {
        await onSelectTutorial(first.id)
      }
    }
  } catch (e: any) {
    const msg = e?.response?.data?.error || '加载教程列表失败'
    ElMessage.error(msg)
  } finally {
    listLoading.value = false
  }
}

async function onSelectTutorial(id: number) {
  if (selectedId.value === id && selectedTutorial.value) return
  selectedId.value = id
  detailLoading.value = true
  try {
    const detail = await getTutorial(id)
    selectedTutorial.value = detail
  } catch (e: any) {
    const msg = e?.response?.data?.error || '加载教程详情失败'
    ElMessage.error(msg)
  } finally {
    detailLoading.value = false
  }
}

function goBackToRAG() {
  router.push('/tutorials')
}

onMounted(() => {
  loadTutorialList()
})
</script>

<style scoped>
.tutorial-layout {
  display: flex;
  min-height: calc(100vh - 60px);
  background: #f3f4f6;
}

.tutorial-sidebar {
  width: 280px;
  max-width: 320px;
  flex-shrink: 0;
  padding: 20px 16px;
  border-right: 1px solid #e5e7eb;
  background: #ffffff;
  box-shadow: 2px 0 6px rgba(15, 23, 42, 0.04);
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  margin-bottom: 16px;
}

.sidebar-title {
  margin: 0 0 4px;
  font-size: 18px;
}

.sidebar-subtitle {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
}

.sidebar-search {
  margin-bottom: 12px;
}

.sidebar-list {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.tutorial-item {
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 6px;
  transition: background 0.15s ease, box-shadow 0.15s ease;
}

.tutorial-item:hover {
  background: #f3f4ff;
}

.tutorial-item.active {
  background: #e0f2fe;
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.4);
}

.ti-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 2px;
}

.ti-desc {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 2px;
}

.ti-meta {
  font-size: 11px;
  color: #9ca3af;
}

.sidebar-empty {
  margin-top: 16px;
  font-size: 13px;
  color: #9ca3af;
}

.tutorial-main {
  flex: 1;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
}

.main-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.main-header-text {
  flex: 1;
  min-width: 0;
}

.main-title {
  margin: 0 0 4px;
  font-size: 22px;
}

.main-desc {
  margin: 0;
  font-size: 14px;
  color: #6b7280;
}

.main-loading {
  background: #ffffff;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

.main-body {
  background: #ffffff;
  border-radius: 16px;
  padding: 18px 20px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
  flex: 1;
  overflow-y: auto;
  font-size: 14px;
  line-height: 1.6;
}

.main-body p {
  margin: 0 0 8px;
}

.main-placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  font-size: 14px;
}

@media (max-width: 900px) {
  .tutorial-layout {
    flex-direction: column;
  }
  .tutorial-sidebar {
    width: 100%;
    max-width: none;
    border-right: none;
    border-bottom: 1px solid #e5e7eb;
    box-shadow: 0 1px 4px rgba(15, 23, 42, 0.06);
  }
}
</style>
