<template>
  <div class="rag-page">
    <div class="rag-container">
      <div class="rag-inner">
        <header class="rag-header" v-if="!isMobile || !isReadingMode">
          <div class="rag-title-block">

          </div>
          <div class="rag-header-actions">
            <el-button link @click="startGuide" class="guide-link-btn">
              <el-icon><InfoFilled /></el-icon> 帮助说明
            </el-button>
            <el-button type="success" plain @click="goAI">AI 问答</el-button>
            <el-button type="primary" plain @click="createDialogVisible = true">新增教程</el-button>
          </div>
        </header>

        

        <div class="content-layout" :class="{ 'is-reading': isMobile && isReadingMode }">
          <!-- Left side: Tutorial List (Hidden on mobile when reading) -->
          <TutorialSidebar
            v-if="!isMobile || !isReadingMode"
            v-model="searchTerm"
            :items="filteredTutorials"
            :selected-id="selectedTutorial?.id"
            :loading="listLoading"
            :loading-more="listLoadingMore"
            @select="handleSelectTutorial"
            @scroll="onListScroll"
          />

          <!-- Right side: Tutorial Viewer -->
          <div v-if="!isMobile || isReadingMode" class="tutorial-viewer-column">
            <div v-if="isMobile" class="mobile-nav-header">
              <el-button link @click="isReadingMode = false" class="back-btn">
                <el-icon><ArrowLeft /></el-icon> 返回目录
              </el-button>
              <div class="mobile-actions">
                <el-button
                  circle
                  v-if="tocItems.length"
                  @click="mobileTocOpen = true"
                  class="toc-fab-trigger"
                >
                  <el-icon><Menu /></el-icon>
                </el-button>
              </div>
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
                  <div class="doc-body">
                    <div v-for="(para, idx) in paragraphList" :key="idx" class="para-block">
                      <div class="para-content-wrap">
                        <div v-html="marked.parse(para.text)"></div>
                        <button
                          v-if="para.hasButton"
                          class="ai-explain-btn"
                          type="button"
                          @click="onExplainParagraph(idx, para.text)"
                        >
                          ✨ AI 解释
                        </button>
                      </div>
                      <TutorialExplainCard
                        v-if="inlineExplanations[idx]"
                        :content="inlineExplanations[idx]"
                        :loading="explainingIdx === idx"
                        @close="onCloseExplain(idx)"
                      />
                    </div>
                  </div>
                  <div class="doc-footer-qna">
                    <el-divider>对本篇教程有疑问？</el-divider>
                    <el-button class="ai-qna-button full-width" type="primary" @click="goAI">
                      <el-icon class="ai-icon"><ChatDotRound /></el-icon>
                      咨询 AI 助手获取精准解答
                    </el-button>
                  </div>
                </div>
                <TutorialTOC
                  v-if="!isMobile && tocItems.length"
                  :items="tocItems"
                  :active-slug="activeChunkId"
                  @select="onSelectChunk"
                />
              </div>
              <div v-else key="placeholder" class="doc-placeholder">
                <el-icon :size="64" class="placeholder-icon"><Reading /></el-icon>
                <h3>选择一篇教程开始阅读</h3>
                <p>在这里，您可以找到所有官方指引。</p>
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
              <div class="mobile-panel-body" ref="mobileListScrollRef" @scroll="onListScroll">
                <div class="search-box">
                  <el-input
                    v-model="searchTerm"
                    placeholder="搜索教程标题或简�?"
                    clearable
                    :prefix-icon="SearchIcon"
                  />
                </div>
                <div class="tutorial-menu-wrap mobile">
                  <el-skeleton v-if="listLoading && !allTutorials.length" :rows="6" animated class="list-skeleton" />
                  <el-menu
                    v-else
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
                  <div v-if="listLoadingMore" class="list-loading-more">
                    <el-icon class="loading-icon-small"><Loading /></el-icon>
                  </div>
                </div>
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
          <div class="ai-assist-tip">
            <el-button link type="primary" :loading="aiAssisting" @click="onAiAssist">
              <el-icon><MagicStick /></el-icon> AI 辅助优化内容
            </el-button>
            <span class="tip-text">输入标题或简稿，AI 将为您扩充并美化 Markdown</span>
          </div>
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
import { computed, nextTick, onMounted, onUnmounted, ref, watch, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import {
  Search as SearchIcon, Loading, ArrowLeft, Menu,
  Reading, MagicStick, InfoFilled, ChatDotRound
} from '@element-plus/icons-vue'
import { marked, Renderer } from 'marked'
import {
  createTutorial,
  getTutorial,
  type TutorialDetail,
  listTutorials,
  type TutorialItem,
  searchAndAskStream
} from '../api/tutorials'
import {
  askAgent,
  getRunStatus,
  getSessionMessages
} from '../api/agent'
import { useAuth } from '../stores/auth'
import { driver } from 'driver.js'
import 'driver.js/dist/driver.css'

// Components
import TutorialSidebar from '../components/tutorial/TutorialSidebar.vue'
import TutorialTOC from '../components/tutorial/TutorialTOC.vue'
import TutorialExplainCard from '../components/tutorial/TutorialExplainCard.vue'

const auth = useAuth()
const router = useRouter()

const allTutorials = ref<TutorialItem[]>([])
const searchTerm = ref('')
const isMobile = ref(false)
const mobileListOpen = ref(false)
const mobileTocOpen = ref(false)
const selectedTutorial = ref<TutorialDetail | null>(null)
const isReadingMode = ref(false)
const tutorialLoading = ref(false)
const tocItems = ref<{ text: string; level: number; slug: string }[]>([])
const activeChunkId = ref<string | null>(null)
const scrollContainerRef = ref<HTMLElement | null>(null)
const listScrollRef = ref<HTMLElement | null>(null)
const mobileListScrollRef = ref<HTMLElement | null>(null)
const listPage = ref(1)
const listTotal = ref(-1)
const listLoading = ref(false)
const listLoadingMore = ref(false)
const searchQuery = ref('')
const listPageSize = 20
let searchTimer: number | undefined
let pendingSearch = false

const newTitle = ref('')
const newDesc = ref('')
const newContent = ref('')
const creating = ref(false)
const aiAssisting = ref(false)
const createDialogVisible = ref(false)

const explainingIdx = ref<number | null>(null)
const inlineExplanations = reactive<Record<number, string>>({})
const paragraphList = ref<{ text: string, hasButton: boolean }[]>([])
let explainAbortController: AbortController | null = null

const startGuide = () => {
  const driverObj = driver({
    showProgress: true,
    nextBtnText: '下一步',
    prevBtnText: '上一步',
    doneBtnText: '完成',
    steps: [
      {
        element: '.modern-search',
        popover: {
          title: '智能搜索',
          description: '输入关键词，快速在海量教程中找到您需要的指引。',
          side: "bottom",
          align: 'start'
        }
      },
      {
        element: isMobile.value ? '.tutorial-card' : '.tutorial-card-list',
        popover: {
          title: '教程目录',
          description: isMobile.value ? '点击教程卡片，即可进入沉浸式阅读模式。' : '浏览左侧目录，点击即可切换不同篇章。',
          side: "right",
          align: 'start'
        }
      },
      {
        element: '.ai-qna-button',
        popover: {
          title: 'AI 智能问答',
          description: '对教程有疑问？点击这里，AI 将根据文档内容为您精准答疑。',
          side: "left",
          align: 'center'
        }
      },
      {
        element: '.rag-header-actions .el-button--primary',
        popover: {
          title: '创作教程',
          description: '您也可以贡献智慧，支持 AI 辅助生成，让分享更简单。',
          side: "bottom",
          align: 'end'
        }
      },
    ]
  });

  driverObj.drive();
}

const filteredTutorials = computed(() => allTutorials.value)
const listHasMore = computed(() => listTotal.value < 0 || allTutorials.value.length < listTotal.value)

watch(() => selectedTutorial.value?.content, (newContent) => {
  if (!newContent) {
    paragraphList.value = []
    tocItems.value = []
    return
  }
  
  // 清空之前的解释
  for (const key in inlineExplanations) delete inlineExplanations[key]

  const rawParas = newContent.split(/\n\n/)
  let charCountSinceLastBtn = 0
  
  paragraphList.value = rawParas.map(text => {
    charCountSinceLastBtn += text.length
    let hasButton = false
    if (charCountSinceLastBtn >= 70 && text.trim().length > 10) {
      charCountSinceLastBtn = 0
      hasButton = true
    }
    return { text, hasButton }
  })

  const renderer = new Renderer()
  const items: { text: string; level: number; slug: string }[] = []
  renderer.heading = ({ text, depth }: { text: string; depth: number }) => {
    const slug = text.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-').replace(/^-+|-+$/g, '') || `h-${items.length}`
    items.push({ text, level: depth, slug })
    return `<h${depth} id="${slug}">${text}</h${depth}>`
  }
  marked.parse(newContent, { renderer })
  tocItems.value = items
}, { immediate: true })

function updateIsMobile() {
  if (typeof window === 'undefined') return
  isMobile.value = window.innerWidth <= 900
}

watch(isMobile, (val) => {
  if (!val) {
    mobileListOpen.value = false
    mobileTocOpen.value = false
  }
  nextTick(() => {
    ensureListScrollable()
  })
})

watch(mobileListOpen, (open) => {
  if (!open) return
  nextTick(() => {
    ensureListScrollable()
  })
})

watch(searchTerm, (value) => {
  if (typeof window === 'undefined') return
  if (searchTimer) {
    window.clearTimeout(searchTimer)
  }
  searchTimer = window.setTimeout(() => {
    const nextQuery = value.trim()
    searchQuery.value = nextQuery
    if (listLoading.value || listLoadingMore.value) {
      pendingSearch = true
      return
    }
    resetTutorialList()
    fetchTutorialPage()
  }, 300)
})

function resetTutorialList() {
  listPage.value = 1
  listTotal.value = -1
  allTutorials.value = []
  if (listScrollRef.value) {
    listScrollRef.value.scrollTop = 0
  }
  if (mobileListScrollRef.value) {
    mobileListScrollRef.value.scrollTop = 0
  }
}

function onListScroll(event: Event) {
  const target = event.target as HTMLElement | null
  if (!target) return
  const remaining = target.scrollHeight - target.scrollTop - target.clientHeight
  if (remaining <= 120) {
    fetchTutorialPage()
  }
}

function ensureListScrollable() {
  const target = isMobile.value ? mobileListScrollRef.value : listScrollRef.value
  if (!target || target.clientHeight === 0) return
  if (target.scrollHeight <= target.clientHeight + 20) {
    fetchTutorialPage()
  }
}

async function fetchTutorialPage() {
  if (listLoading.value || listLoadingMore.value) return
  if (listPage.value > 1 && !listHasMore.value) return

  const page = listPage.value
  if (page === 1) {
    listLoading.value = true
  } else {
    listLoadingMore.value = true
  }

  try {
    const data = await listTutorials({
      q: searchQuery.value || undefined,
      page,
      pageSize: listPageSize,
    })
    const items = data.items || []
    listTotal.value = typeof data.total === 'number' ? data.total : 0
    if (page === 1) {
      allTutorials.value = items
    } else if (items.length) {
      allTutorials.value = [...allTutorials.value, ...items]
    }
    listPage.value = page + 1
    const firstItem = items[0]
    if (page === 1 && firstItem && !selectedTutorial.value && !isMobile.value) {
      handleSelectTutorial(String(firstItem.id))
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.error || '获取教程列表失败')
  } finally {
    listLoading.value = false
    listLoadingMore.value = false
    if (pendingSearch) {
      pendingSearch = false
      resetTutorialList()
      fetchTutorialPage()
      return
    }
    nextTick(() => {
      ensureListScrollable()
    })
  }
}

async function handleSelectTutorial(id: string | number) {
  const numericId = Number(id)
  if (selectedTutorial.value?.id === numericId) {
    if (isMobile.value) isReadingMode.value = true
    return
  }

  if (isMobile.value) {
    isReadingMode.value = true
  }

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

async function onExplainParagraph(idx: number, text: string) {
  if (inlineExplanations[idx] && inlineExplanations[idx] !== '正在思考中...') return
  
  if (explainAbortController) explainAbortController.abort()
  explainAbortController = new AbortController()

  explainingIdx.value = idx
  inlineExplanations[idx] = '正在思考中...'
  
  try {
    let fullText = ''
    const query = `请深入解释一下这段教程内容，要求：语言通俗易懂，字数控制在 200 字以内：\n\n${text}`
    
    await searchAndAskStream({ query, mode: 'both' }, {
      signal: explainAbortController.signal,
      onEvent: (evt) => {
        if (evt.event === 'token' && evt.text) {
          if (inlineExplanations[idx] === '正在思考中...') {
            inlineExplanations[idx] = ''
          }
          fullText += evt.text
          inlineExplanations[idx] = fullText
        } else if (evt.event === 'error') {
          inlineExplanations[idx] = (evt as any).message || '解释出错'
        }
      }
    })
  } catch (e: any) {
    if (e.name === 'AbortError') return
    inlineExplanations[idx] = '请求 AI 失败。'
  } finally {
    explainingIdx.value = null
    explainAbortController = null
  }
}

function onCloseExplain(idx: number) {
  delete inlineExplanations[idx]
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
    resetTutorialList()
    await fetchTutorialPage()
    if (data.id) {
      handleSelectTutorial(data.id) // Select the new one
      isReadingMode.value = true
    }
  } catch (e: any) {
    const msg = e?.response?.data?.error || '保存失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    creating.value = false
  }
}

async function onAiAssist() {
  const title = newTitle.value.trim()
  const content = newContent.value.trim()
  if (!title) {
    ElMessage.warning('请先输入教程标题')
    return
  }
  
  aiAssisting.value = true
  try {
    // 借用 Agent 接口进行教程辅助创造
    // 我们发送一个特定的指令给 Agent
    const prompt = `帮我根据标题“${title}”和以下内容草稿，整理并扩充成一篇结构清晰、带有 Markdown 格式的详细教程。\n\n内容草稿：\n${content || '（暂无，请根据标题自由发挥）'}`
    
    const res = await askAgent(undefined, prompt)
    const runId = res.runId
    
    // 轮询获取结果
    let pollCount = 0
    const maxPoll = 30
    const poll = setInterval(async () => {
      pollCount++
      const status = await getRunStatus(runId)
      if (status.status === 'succeeded') {
        clearInterval(poll)
        const msgs = await getSessionMessages(status.sessionId)
        const lastMsg = msgs[msgs.length - 1]
        if (lastMsg && lastMsg.role === 'assistant') {
          newContent.value = lastMsg.content
          ElMessage.success('AI 辅助优化完成')
        }
        aiAssisting.value = false
      } else if (status.status === 'failed' || pollCount >= maxPoll) {
        clearInterval(poll)
        ElMessage.error('AI 辅助失败，请重试')
        aiAssisting.value = false
      }
    }, 1500)
    
  } catch (e: any) {
    ElMessage.error('AI 辅助请求失败')
    aiAssisting.value = false
  }
}

onMounted(() => {
  updateIsMobile()
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', updateIsMobile)
  }
  searchQuery.value = searchTerm.value.trim()
  resetTutorialList()
  fetchTutorialPage()

  // 首次进入自动触发指引
  const hasSeenGuide = localStorage.getItem('msut_tutorial_guide_seen')
  if (!hasSeenGuide) {
    setTimeout(() => {
      startGuide()
      localStorage.setItem('msut_tutorial_guide_seen', 'true')
    }, 1000)
  }
})

onUnmounted(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', updateIsMobile)
  }
  if (typeof window !== 'undefined' && searchTimer) {
    window.clearTimeout(searchTimer)
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
  background: #f1f5f9; /* 稍微加深背景色，降低整体亮度 */
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
  max-width: 1440px;
  margin: 0 auto;
  padding: 20px;
  width: 100%;
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

@media (max-width: 900px) {
  .rag-inner {
    padding: 0;
  }
}

.rag-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  flex-shrink: 0;
}

@media (max-width: 900px) {
  .rag-header {
    padding: 12px 16px;
    margin-bottom: 0;
    background: #fff;
    border-bottom: 1px solid #f1f5f9;
  }
  .rag-header-actions {
    display: none;
  }
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
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.guide-link-btn {
  margin-right: 8px;
  color: #64748b;
}

.mobile-hint {
  margin: 4px 0 10px;
  font-size: 12px;
  color: #6b7280;
}

.content-layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 24px;
  flex: 1;
  overflow: hidden;
  height: calc(100vh - 140px);
  transition: all 0.3s ease;
}

@media (max-width: 900px) {
  .content-layout {
    grid-template-columns: 1fr;
    height: calc(100vh - 57px);
    gap: 0;
  }
}

.tutorial-list-column {
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
  min-height: 0;
}

@media (max-width: 900px) {
  .tutorial-list-column {
    border-radius: 0;
    border: none;
    box-shadow: none;
  }
}
.search-box {
  padding: 16px;
  background: #fff;
  z-index: 10;
}
.modern-search :deep(.el-input__wrapper) {
  border-radius: 10px;
  box-shadow: 0 0 0 1px #e2e8f0 inset;
  padding: 4px 12px;
}
.modern-search :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--el-color-primary) inset;
}

.tutorial-menu-wrap {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px 16px;
}

.tutorial-card-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 4px;
}

.tutorial-card {
  padding: 16px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #f1f5f9;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.tutorial-card:hover {
  background: #f8fafc;
  border-color: #e2e8f0;
  transform: translateY(-1px);
}

.tutorial-card.active {
  background: #eff6ff;
  border-color: #bfdbfe;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.08);
}

.card-title {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.4;
}

.card-desc {
  margin: 0 0 8px;
  font-size: 13px;
  color: #64748b;
  display: -webkit-box;
  line-clamp: 2;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
}

.card-arrow {
  color: #cbd5e1;
  font-size: 16px;
  transition: transform 0.2s;
}

.tutorial-card:hover .card-arrow {
  transform: translateX(3px);
  color: var(--el-color-primary);
}

.empty-hint {
  text-align: center;
  padding: 40px 20px;
  color: #94a3b8;
  font-size: 14px;
}
.list-skeleton {
  padding: 12px;
}
.list-loading-more {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px 0 12px;
}
.loading-icon-small {
  font-size: 18px;
  animation: rotating 1.6s linear infinite;
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
  border-radius: 16px;
  overflow: hidden;
  position: relative;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

@media (max-width: 900px) {
  .tutorial-viewer-column {
    border-radius: 0;
    border: none;
    box-shadow: none;
  }
}

.mobile-nav-header {
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  position: sticky;
  top: 0;
  z-index: 20;
}

.back-btn {
  font-weight: 600;
  font-size: 15px;
}

.doc-viewer-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 260px;
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

@media (max-width: 900px) {
  .doc-main-content {
    padding: 20px 16px;
  }
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
  color: #64748b;
  text-align: center;
  padding: 40px;
}
.placeholder-icon {
  margin-bottom: 20px;
  color: #e2e8f0;
}
.doc-placeholder h3 {
  margin: 0 0 10px;
  color: #1e293b;
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
  line-height: 1.8; /* 增加行高，提升阅读舒适度 */
  color: #1e293b;   /* 使用蓝灰色调文字，比纯黑更柔和 */
}

.para-block {
  margin-bottom: 1.5em;
}

.para-content-wrap {
  position: relative;
}

.doc-body :deep(h1),
.doc-body :deep(h2),
.doc-body :deep(h3),
.doc-body :deep(h4) {
  margin-top: 1.8em;
  margin-bottom: 1em;
  font-weight: 700;
  color: #0f172a;
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

.doc-body :deep(.ai-explain-btn) {
  appearance: none;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  margin-left: 8px;
  transition: all 0.2s ease;
  vertical-align: middle;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.doc-body :deep(.ai-explain-btn:hover) {
  background: #dcfce7;
  border-color: #86efac;
  transform: scale(1.05);
  box-shadow: 0 4px 6px rgba(22, 101, 52, 0.1);
}

.explain-container {
  min-height: 200px;
}

.explain-source {
  background: #f8fafc;
  padding: 12px;
  border-radius: 8px;
  border-left: 4px solid #cbd5e1;
  margin-bottom: 20px;
}

.explain-source .label {
  font-size: 12px;
  color: #64748b;
  font-weight: 600;
}

.source-text {
  margin: 4px 0 0;
  font-size: 14px;
  color: #475569;
  font-style: italic;
  line-height: 1.5;
}

.explain-result {
  font-size: 16px;
  line-height: 1.7;
  color: #1e293b;
}

.explain-dialog :deep(.el-dialog__body) {
  padding-top: 10px;
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
