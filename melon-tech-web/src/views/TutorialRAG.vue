<template>
  <div class="rag-page">
    <div class="rag-container">
      <div class="rag-inner">
        <header class="rag-header">
          <div class="rag-title-block">
            <h1>教程中心 · 文档库</h1>
            <p class="rag-subtitle">
              集中浏览与管理所有教程
            </p>
          </div>
          <div class="rag-header-actions">
            <el-button @click="goUpload">上传文件</el-button>
            <el-button type="primary" plain @click="createDialogVisible = true">新增教程</el-button>
          </div>
        </header>

        <div class="content-layout">
          <!-- Left side: Tutorial List -->
          <div class="tutorial-list-column">
            <div class="search-box">
              <el-input
                v-model="searchTerm"
                placeholder="搜索教程标题或简介"
                clearable
                :prefix-icon="SearchIcon"
              />
            </div>
            <el-menu
              :default-active="selectedTutorial ? String(selectedTutorial.id) : ''"
              class="tutorial-menu"
              @select="handleSelectTutorial"
            >
              <el-menu-item
                v-for="tutorial in filteredTutorials"
                :key="tutorial.id"
                :index="String(tutorial.id)"
              >
                <template #title>
                  <div class="menu-item-content">
                    <span class="item-title">{{ tutorial.title }}</span>
                    <span class="item-date">{{ formatDate(tutorial.created_at) }}</span>
                  </div>
                </template>
              </el-menu-item>
            </el-menu>
          </div>

          <!-- Right side: Tutorial Viewer -->
          <div class="tutorial-viewer-column">
            <transition name="fade-slide" mode="out-in">
              <div v-if="tutorialLoading" key="loading" class="doc-loading">
                <el-icon class="loading-icon"><Loading /></el-icon>
                <p>正在加载教程...</p>
              </div>
              <div v-else-if="selectedTutorial" key="viewer" class="doc-viewer-layout">
                <div class="doc-main-content">
                  <div class="doc-header">
                    <h1>{{ selectedTutorial.title }}</h1>
                    <p class="doc-desc">{{ selectedTutorial.description || '暂无简介' }}</p>
                  </div>
                  <div class="doc-body" v-html="renderedMarkdown"></div>
                </div>
                <div v-if="chunks.length" class="doc-toc-sidebar">
                  <h3 class="toc-title">内容导航</h3>
                  <ul class="toc-list">
                    <li
                      v-for="chunk in chunks"
                      :key="chunk.id"
                      class="toc-item"
                      :class="{ active: chunk.id === activeChunkId }"
                      @click="onSelectChunk(chunk.id)"
                    >
                      <a :href="`#chunk-${chunk.id}`">{{ chunk.title }}</a>
                    </li>
                  </ul>
                </div>
              </div>
              <div v-else key="placeholder" class="doc-placeholder">
                <p>从左侧选择一篇教程以开始阅读。</p>
              </div>
            </transition>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="createDialogVisible" title="新增教程" width="640px">
      <p class="qc-intro">
        适合整理图文教程或攻略，保存后可被搜索与 AI 使用。
      </p>
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="标题">
          <el-input v-model="newTitle" placeholder="例如：甜瓜游乐场模组安装全流程" />
        </el-form-item>
        <el-form-item label="简介（可选）">
          <el-input v-model="newDesc" placeholder="一句话说明这篇教程主要讲什么" />
        </el-form-item>
        <el-form-item label="正文内容 (Markdown)">
          <el-input
            v-model="newContent"
            type="textarea"
            :autosize="{ minRows: 8, maxRows: 16 }"
            placeholder="在这里粘贴或编写完整教程文本（支持 Markdown 格式）"
          />
        </el-form-item>
        <div class="qc-actions">
          <el-button @click="createDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="creating" @click="onCreateTutorial">
            保存为教程
          </el-button>
        </div>
      </el-form>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { Search as SearchIcon, Loading } from '@element-plus/icons-vue'
import { marked } from 'marked'
import {
  createTutorial,
  getTutorial,
  type TutorialDetail,
  getTutorialChunks,
  type TutorialChunk,
  listTutorials,
  type TutorialItem,
} from '../api/tutorials'
import { useAuth } from '../stores/auth'

const auth = useAuth()
const router = useRouter()

const allTutorials = ref<TutorialItem[]>([])
const searchTerm = ref('')
const selectedTutorial = ref<TutorialDetail | null>(null)
const tutorialLoading = ref(false)
const chunks = ref<TutorialChunk[]>([])
const chunkLoading = ref(false) // Kept for potential future use
const activeChunkId = ref<number | null>(null)

const newTitle = ref('')
const newDesc = ref('')
const newContent = ref('')
const creating = ref(false)
const createDialogVisible = ref(false)

const filteredTutorials = computed(() => {
  if (!searchTerm.value) {
    return allTutorials.value
  }
  const lowerCaseSearch = searchTerm.value.toLowerCase()
  return allTutorials.value.filter(
    (t: TutorialItem) =>
      t.title.toLowerCase().includes(lowerCaseSearch) ||
      (t.description && t.description.toLowerCase().includes(lowerCaseSearch))
  )
})

const renderedMarkdown = computed(() => {
  if (selectedTutorial.value?.content) {
    return marked(selectedTutorial.value.content)
  }
  return ''
})

async function fetchAllTutorials() {
  try {
    const data = await listTutorials()
    allTutorials.value = data.items || []
    // Auto-select the first tutorial if list is not empty
    if (allTutorials.value.length > 0 && !selectedTutorial.value && allTutorials.value[0]) {
      handleSelectTutorial(String(allTutorials.value[0].id))
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.error || '获取教程列表失败')
  }
}

async function handleSelectTutorial(id: string | number) {
  const numericId = Number(id)
  if (selectedTutorial.value?.id === numericId) return

  tutorialLoading.value = true
  selectedTutorial.value = null
  chunks.value = []
  try {
    const detail = await getTutorial(numericId)
    selectedTutorial.value = detail
  } catch (e: any) {
    const msg = e?.response?.data?.error || '加载教程失败'
    ElMessage.error(msg)
  } finally {
    tutorialLoading.value = false
  }
}

function onSelectChunk(chunkId: number) {
  activeChunkId.value = chunkId
  const element = document.getElementById(`chunk-${chunkId}`)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth' })
  }
}

watch(
  () => selectedTutorial.value?.id,
  async (tutorialId) => {
    if (!tutorialId) {
      chunks.value = []
      activeChunkId.value = null
      return
    }
    chunkLoading.value = true
    try {
      const data = await getTutorialChunks(tutorialId)
      chunks.value = data.chunks || []
      if (chunks.value.length > 0 && chunks.value[0]) {
        activeChunkId.value = chunks.value[0].id
      }
    } catch (e: any) {
      // Non-critical error, just log it or show a subtle warning
      console.error('加载分块结构失败:', e)
      chunks.value = []
      activeChunkId.value = null
    } finally {
      chunkLoading.value = false
    }
  }
)

function goUpload() {
  router.push('/upload')
}

async function onCreateTutorial() {
  if (!auth.user) {
    ElMessage.warning('请先登录后再创建教程')
    return
  }
  const title = newTitle.value.trim()
  const content = newContent.value.trim()
  if (!title || !content) {
    ElMessage.warning('标题和正文内容不能为空')
    return
  }
  creating.value = true
  try {
    const data = await createTutorial({ title, description: newDesc.value.trim(), content })
    ElMessage.success('教程已保存')
    newTitle.value = ''
    newDesc.value = ''
    newContent.value = ''
    createDialogVisible.value = false
    await fetchAllTutorials() // Refresh list
    if (data.id) {
      handleSelectTutorial(data.id) // Select the new one
    }
  } catch (e: any) {
    const msg = e?.response?.data?.error || '保存失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    creating.value = false
  }
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

onMounted(() => {
  fetchAllTutorials()
})
</script>

<style scoped>
.rag-page {
  height: 100vh;
  overflow: hidden;
  background: #f3f4f6;
  display: flex;
  flex-direction: column;
}
.rag-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.rag-inner {
  max-width: 1400px;
  margin: 0 auto;
  padding: 16px;
  width: 100%;
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}
.rag-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
  flex-shrink: 0;
}
.rag-title-block h1 {
  margin: 0 0 6px;
  font-size: 22px;
}
.rag-subtitle {
  margin: 0;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}
.rag-header-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.content-layout {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 24px;
  flex: 1;
  overflow: hidden;
  height: calc(100vh - 120px); /* Adjust based on header height */
}

.tutorial-list-column {
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #e5e7eb;
}
.search-box {
  padding: 12px;
  border-bottom: 1px solid #e5e7eb;
}
.tutorial-menu {
  flex: 1;
  overflow-y: auto;
  border-right: none;
}
.menu-item-content {
  display: flex;
  flex-direction: column;
  width: 100%;
}
.item-title {
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.item-date {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.tutorial-viewer-column {
  background: #ffffff;
  border-radius: 12px;
  overflow: hidden;
  position: relative;
  border: 1px solid #e5e7eb;
}

.doc-viewer-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 240px;
  gap: 24px;
  height: 100%;
  overflow: hidden;
}
.doc-main-content {
  padding: 24px 32px;
  overflow-y: auto;
}
.doc-toc-sidebar {
  padding: 24px 16px;
  border-left: 1px solid #e5e7eb;
  overflow-y: auto;
  background: #f9fafb;
}
.toc-title {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 600;
}
.toc-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.toc-item a {
  display: block;
  padding: 6px 10px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  text-decoration: none;
  border-radius: 6px;
  transition: background 0.2s, color 0.2s;
}
.toc-item a:hover {
  background: #eef2ff;
  color: #4f46e5;
}
.toc-item.active a {
  background: #e0e7ff;
  color: #4338ca;
  font-weight: 600;
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

.doc-loading,
.doc-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--el-text-color-secondary);
  text-align: center;
}
.loading-icon {
  font-size: 32px;
  margin-bottom: 16px;
  animation: rotating 2s linear infinite;
}
@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.doc-header {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e5e7eb;
}
.doc-header h1 {
  margin: 0 0 8px;
  font-size: 28px;
}
.doc-desc {
  margin: 0;
  font-size: 15px;
  color: var(--el-text-color-secondary);
}

.doc-body {
  font-size: 16px;
  line-height: 1.7;
  color: #333;
}
.doc-body :deep(h1),
.doc-body :deep(h2),
.doc-body :deep(h3),
.doc-body :deep(h4) {
  margin-top: 1.5em;
  margin-bottom: 0.8em;
  font-weight: 600;
}
.doc-body :deep(h1) { font-size: 1.8em; }
.doc-body :deep(h2) { font-size: 1.5em; border-bottom: 1px solid #eee; padding-bottom: 0.3em; }
.doc-body :deep(h3) { font-size: 1.25em; }
.doc-body :deep(p) {
  margin-bottom: 1em;
}
.doc-body :deep(ul),
.doc-body :deep(ol) {
  padding-left: 1.5em;
  margin-bottom: 1em;
}
.doc-body :deep(li) {
  margin-bottom: 0.5em;
}
.doc-body :deep(code) {
  background-color: #f3f4f6;
  padding: 0.2em 0.4em;
  margin: 0;
  font-size: 85%;
  border-radius: 6px;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
}
.doc-body :deep(pre) {
  background-color: #f3f4f6;
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
  margin-bottom: 1em;
}
.doc-body :deep(pre) code {
  background: none;
  padding: 0;
}
.doc-body :deep(blockquote) {
  border-left: 4px solid #e5e7eb;
  padding-left: 1em;
  margin-left: 0;
  color: #6b7280;
}
.doc-body :deep(a) {
  color: #4f46e5;
  text-decoration: none;
  font-weight: 500;
}
.doc-body :deep(a:hover) {
  text-decoration: underline;
}

.qc-intro {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.qc-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
</style>
