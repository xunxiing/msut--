<template>
  <div class="rag-page">
    <div class="rag-container">
      <div class="rag-inner">
        <header class="rag-header">
          <div class="rag-title-block">

          </div>
          <div class="rag-header-actions">
            <el-button @click="goUpload">上传文件</el-button>
            <el-button type="success" plain @click="goAI">AI 问答</el-button>
            <el-button type="primary" plain @click="createDialogVisible = true">新增教程</el-button>
          </div>
        </header>

        <p v-if="isMobile" class="mobile-hint">
          手机端默认收起左侧“教程列表”和右侧“内容导航”，可通过下方按钮随时展开查看。
        </p>

        <div class="content-layout">
          <!-- Left side: Tutorial List -->
          <div v-if="!isMobile" class="tutorial-list-column">
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
                  </div>
                </template>
              </el-menu-item>
            </el-menu>
          </div>

          <!-- Right side: Tutorial Viewer -->
          <div class="tutorial-viewer-column">
            <div v-if="isMobile" class="mobile-toolbar">
              <el-button size="small" @click="mobileListOpen = true">
                打开教程列表
              </el-button>
              <el-button
                size="small"
                v-if="tocItems.length"
                @click="mobileTocOpen = true"
              >
                打开内容导航
              </el-button>
            </div>
            <transition name="fade-slide" mode="out-in">
              <div v-if="tutorialLoading" key="loading" class="doc-loading">
                <el-icon class="loading-icon"><Loading /></el-icon>
                <p>正在加载教程...</p>
              </div>
              <div
                v-else-if="selectedTutorial"
                key="viewer"
                class="doc-viewer-layout"
                :class="{ 'doc-viewer-mobile': isMobile }"
              >
                <div class="doc-main-content" ref="scrollContainerRef">
                  <div class="doc-header">
                    <h1>{{ selectedTutorial.title }}</h1>
                    <p class="doc-desc">{{ selectedTutorial.description || '暂无简介' }}</p>
                  </div>
                  <div class="doc-body" v-html="renderedMarkdown"></div>
                </div>
                <div v-if="!isMobile && tocItems.length" class="doc-toc-sidebar">
                  <h3 class="toc-title">内容导航</h3>
                  <div class="toc-scroll-indicator-container">
                    <div class="toc-scroll-indicator" :style="getScrollIndicatorStyle()"></div>
                    <ul class="toc-list" ref="tocListRef">
                      <li
                        v-for="(item, idx) in tocItems"
                        :key="idx"
                        class="toc-item"
                        :class="{ active: activeChunkId === item.slug }"
                        @click="onSelectChunk(item.slug)"
                      >
                        <a :href="`#${item.slug}`" @click.prevent="onSelectChunk(item.slug)" :style="{ paddingLeft: (item.level - 1) * 12 + 10 + 'px' }">
                          {{ item.text }}
                        </a>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
              <div v-else key="placeholder" class="doc-placeholder">
                <p>从左侧选择一篇教程以开始阅读。</p>
              </div>
            </transition>
          </div>
        </div>

        <!-- Mobile: tutorial list overlay -->
        <transition name="fade-slide">
          <div
            v-if="isMobile && mobileListOpen"
            class="mobile-panel-overlay"
            @click.self="mobileListOpen = false"
          >
            <div class="mobile-panel">
              <div class="mobile-panel-header">
                <span class="mobile-panel-title">教程列表</span>
                <button class="mobile-panel-close" type="button" @click="mobileListOpen = false">
                  关闭
                </button>
              </div>
              <div class="mobile-panel-body">
                <div class="search-box">
                  <el-input
                    v-model="searchTerm"
                    placeholder="搜索教程标题或简�?"
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
                      </div>
                    </template>
                  </el-menu-item>
                </el-menu>
              </div>
            </div>
          </div>
        </transition>

        <!-- Mobile: TOC overlay -->
        <transition name="fade-slide">
          <div
            v-if="isMobile && mobileTocOpen && tocItems.length"
            class="mobile-panel-overlay"
            @click.self="mobileTocOpen = false"
          >
            <div class="mobile-panel">
              <div class="mobile-panel-header">
                <span class="mobile-panel-title">内容导航</span>
                <button class="mobile-panel-close" type="button" @click="mobileTocOpen = false">
                  关闭
                </button>
              </div>
              <div class="mobile-panel-body">
                <ul class="toc-list">
                  <li
                    v-for="(item, idx) in tocItems"
                    :key="idx"
                    class="toc-item"
                    :class="{ active: activeChunkId === item.slug }"
                    @click="onSelectChunk(item.slug); mobileTocOpen = false"
                  >
                    <a
                      :href="`#${item.slug}`"
                      @click.prevent="onSelectChunk(item.slug); mobileTocOpen = false"
                      :style="{ paddingLeft: (item.level - 1) * 12 + 10 + 'px' }"
                    >
                      {{ item.text }}
                    </a>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </transition>
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
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { Search as SearchIcon, Loading } from '@element-plus/icons-vue'
import { marked, Renderer } from 'marked'
import {
  createTutorial,
  getTutorial,
  type TutorialDetail,
  listTutorials,
  type TutorialItem,
} from '../api/tutorials'
import { useAuth } from '../stores/auth'

const auth = useAuth()
const router = useRouter()

const allTutorials = ref<TutorialItem[]>([])
const searchTerm = ref('')
const isMobile = ref(false)
const mobileListOpen = ref(false)
const mobileTocOpen = ref(false)
const selectedTutorial = ref<TutorialDetail | null>(null)
const tutorialLoading = ref(false)
const tocItems = ref<{ text: string; level: number; slug: string }[]>([])
const activeChunkId = ref<string | null>(null)
const scrollContainerRef = ref<HTMLElement | null>(null)
const tocListRef = ref<HTMLElement | null>(null)

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
  if (!selectedTutorial.value?.content) return ''
  
  const renderer = new Renderer()
  const items: { text: string; level: number; slug: string }[] = []
  
  renderer.heading = ({ text, depth }: { text: string; depth: number }) => {
    const level = depth
    const slug = text.toLowerCase()
      .replace(/[^\w\u4e00-\u9fa5]+/g, '-')
      .replace(/^-+|-+$/g, '') || `heading-${items.length}`
      
    items.push({ text, level, slug })
    return `<h${level} id="${slug}">${text}</h${level}>`
  }
  
  // Update tocItems as a side effect
  setTimeout(() => {
    tocItems.value = items
  }, 0)

  return marked.parse(selectedTutorial.value.content, { renderer })
})

function updateIsMobile() {
  if (typeof window === 'undefined') return
  isMobile.value = window.innerWidth <= 900
}

watch(isMobile, (val) => {
  if (!val) {
    mobileListOpen.value = false
    mobileTocOpen.value = false
  }
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

  mobileListOpen.value = false
  tutorialLoading.value = true
  selectedTutorial.value = null
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

function onSelectChunk(slug: string) {
  activeChunkId.value = slug
  const element = document.getElementById(slug)
  if (element && scrollContainerRef.value) {
    const containerRect = scrollContainerRef.value.getBoundingClientRect()
    const elementRect = element.getBoundingClientRect()
    const scrollTop = scrollContainerRef.value.scrollTop
    const targetScrollTop = scrollTop + (elementRect.top - containerRect.top) - 20 // 20px offset from top
    
    scrollContainerRef.value.scrollTo({
      top: targetScrollTop,
      behavior: 'smooth'
    })
  }
}

function getScrollIndicatorStyle() {
  if (!activeChunkId.value || tocItems.value.length === 0 || !tocListRef.value) {
    return { display: 'none' }
  }

  const activeIndex = tocItems.value.findIndex(item => item.slug === activeChunkId.value)
  if (activeIndex === -1) {
    return { display: 'none' }
  }

  const listEl = tocListRef.value
  const items = listEl.querySelectorAll<HTMLElement>('.toc-item')
  const activeEl = items[activeIndex]
  if (!activeEl) {
    return { display: 'none' }
  }

  const listRect = listEl.getBoundingClientRect()
  const itemRect = activeEl.getBoundingClientRect()
  const topPosition = itemRect.top - listRect.top
  
  return {
    transform: `translateY(${topPosition}px)`,
    height: `${itemRect.height}px`,
    display: 'block'
  }
}

function updateActiveSectionOnScroll() {
  if (!scrollContainerRef.value || tocItems.value.length === 0) return

  const container = scrollContainerRef.value
  const containerRect = container.getBoundingClientRect()
  const containerTop = containerRect.top + 100 // 100px offset to trigger earlier
  const containerBottom = containerRect.bottom - 100

  let currentActiveSlug: string | null = null
  let maxVisibleArea = 0

  // Find the most visible section
  for (const item of tocItems.value) {
    const element = document.getElementById(item.slug)
    if (!element) continue

    const elementRect = element.getBoundingClientRect()
    const visibleTop = Math.max(elementRect.top, containerTop)
    const visibleBottom = Math.min(elementRect.bottom, containerBottom)
    
    if (visibleTop < visibleBottom) {
      const visibleArea = visibleBottom - visibleTop
      if (visibleArea > maxVisibleArea) {
        maxVisibleArea = visibleArea
        currentActiveSlug = item.slug
      }
    }
  }

  // If no section is visible, find the closest one above the viewport
  if (!currentActiveSlug) {
    let minDistance = Infinity
    for (const item of tocItems.value) {
      const element = document.getElementById(item.slug)
      if (!element) continue

      const elementRect = element.getBoundingClientRect()
      const distance = containerTop - elementRect.bottom
      if (distance > 0 && distance < minDistance) {
        minDistance = distance
        currentActiveSlug = item.slug
      }
    }
  }

  if (currentActiveSlug && currentActiveSlug !== activeChunkId.value) {
    activeChunkId.value = currentActiveSlug
  }
}

// 当正文容器挂载/变更时，绑定滚动监听
watch(
  scrollContainerRef,
  (el, oldEl) => {
    if (oldEl) {
      oldEl.removeEventListener('scroll', updateActiveSectionOnScroll)
    }
    if (el) {
      el.addEventListener('scroll', updateActiveSectionOnScroll, { passive: true })
      // 初次绑定时根据当前滚动位置计算一次
      setTimeout(updateActiveSectionOnScroll, 50)
    }
  }
)

// 当目录项变化时，自动选中一个默认的激活项，并同步指示条
watch(
  tocItems,
  () => {
    if (!tocItems.value.length) {
      activeChunkId.value = null
      return
    }

    // 当前激活项无效或为空时，默认选中第一个小节
    if (!activeChunkId.value || !tocItems.value.some(item => item.slug === activeChunkId.value)) {
      activeChunkId.value = tocItems.value?.[0]?.slug ?? ''
    }

    // 目录变化后，根据当前滚动位置更新激活项（防止只停留在第一个）
    setTimeout(updateActiveSectionOnScroll, 0)
  }
)

function goUpload() {
  router.push('/upload')
}

function goAI() {
  router.push('/tutorials/ai')
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

onMounted(() => {
  updateIsMobile()
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', updateIsMobile)
  }
  fetchAllTutorials()
})

onUnmounted(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', updateIsMobile)
  }
  if (scrollContainerRef.value) {
    scrollContainerRef.value.removeEventListener('scroll', updateActiveSectionOnScroll)
  }
})
</script>

<style scoped>
.rag-page {
  height: calc(100vh - 80px);
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

.mobile-hint {
  margin: 4px 0 10px;
  font-size: 12px;
  color: #6b7280;
}

.content-layout {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 24px;
  flex: 1;
  overflow: hidden;
  height: calc(100vh - 120px); /* Adjust based on header height */
}

@media (max-width: 900px) {
  .content-layout {
    grid-template-columns: minmax(0, 1fr);
    height: auto;
  }
}

.tutorial-list-column {
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #e5e7eb;
  min-height: 0; /* Important for nested flex scrolling */
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
.doc-viewer-layout.doc-viewer-mobile {
  grid-template-columns: minmax(0, 1fr);
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
  position: relative;
}
.toc-title {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 600;
}
.toc-scroll-indicator-container {
  position: relative;
}
.toc-scroll-indicator {
  position: absolute;
  left: -16px;
  width: 3px;
  height: 32px;
  background: #10b981; /* Green 500 */
  border-radius: 0 3px 3px 0;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 1;
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
  background: #ecfdf5; /* Green 50 */
  color: #10b981;    /* Green 500 */
}
.toc-item.active a {
  background: #d1fae5; /* Green 100 */
  color: #059669;    /* Green 600 */
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
  color: #3b82f6; /* Blue 500 */
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

.mobile-toolbar {
  display: flex;
  gap: 8px;
  padding: 12px 16px 0;
}

.mobile-panel-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: 12px;
  z-index: 3000;
}

.mobile-panel {
  width: 100%;
  max-width: 520px;
  max-height: 80vh;
  background: #ffffff;
  border-radius: 16px 16px 12px 12px;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.25);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.mobile-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid #e5e7eb;
}

.mobile-panel-title {
  font-size: 14px;
  font-weight: 600;
}

.mobile-panel-close {
  border: none;
  background: transparent;
  font-size: 13px;
  color: #6b7280;
  padding: 4px 8px;
  border-radius: 999px;
}

.mobile-panel-close:hover {
  background: #f3f4f6;
}

.mobile-panel-body {
  padding: 10px 12px 12px;
  flex: 1;
  overflow-y: auto;
}
</style>
