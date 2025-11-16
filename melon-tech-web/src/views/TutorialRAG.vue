<template>
  <div class="rag-page">
    <div class="rag-container">
      <div class="rag-inner">
      <header class="rag-header">
        <div class="rag-title-block">
          <h1>教程中心 · AI 搜索与问答</h1>
          <p class="rag-subtitle">
            在这里集中管理甜瓜相关教程，一键搜索文档内容，或通过 AI 基于教程知识为你答疑解惑。
          </p>
        </div>
        <div class="rag-header-actions">
          <el-button @click="goUpload">上传文件</el-button>
          <el-button type="primary" plain @click="createDialogVisible = true">新增教程</el-button>
          <el-button type="primary" @click="goTutorialLibrary">打开教程文档库</el-button>
        </div>
      </header>

      <section class="rag-unified-container">
        <div class="rag-column rag-answer">
          <h2 class="section-title">教程内容 / AI 回答</h2>

          <div v-if="answer" class="qa-box">
            <div v-if="answer.sources && answer.sources.length" class="qa-sources-collapsible">
              <el-collapse>
                <el-collapse-item name="sources">
                  <template #title>
                    <div class="sources-title">
                      <span class="sources-icon">📚</span>
                      <span>已读取文档 ({{ answer.sources.length }})</span>
                    </div>
                  </template>
                  <ul class="sources-list">
                    <li
                      v-for="s in answer.sources"
                      :key="s.tutorialId + '-' + s.slug + '-' + s.excerpt.slice(0, 8)"
                    >
                      <strong><a :href="`/tutorials/library#${s.tutorialId}`" class="source-link" @click.prevent="goToTutorial(s.tutorialId)">{{ s.title }}</a></strong>：{{ s.excerpt }}
                    </li>
                  </ul>
                </el-collapse-item>
              </el-collapse>
            </div>
            <div class="qa-answer">
              <div class="qa-label">AI 回答</div>
              <div class="qa-text">
                <p v-for="(para, idx) in splitAnswer" :key="idx">{{ para }}</p>
              </div>
            </div>
          </div>

          <div v-if="tutorialLoading" class="doc-loading">
              <el-icon class="loading-icon"><Loading /></el-icon>
              <p>正在加载教程...</p>
            </div>
            <transition v-else name="fade-slide" mode="out-in" :duration="{ enter: 100, leave: 0 }">
              <div v-if="selectedTutorial" key="doc-viewer" class="doc-viewer">
                <div class="doc-header">
                  <h3>{{ selectedTutorial.title }}</h3>
                  <p class="doc-desc">{{ selectedTutorial.description || '暂无简介' }}</p>
                </div>
                <div class="doc-body">
                  <p v-for="(line, idx) in displayedLines" :key="idx" class="doc-line">
                    {{ line }}
                  </p>
                </div>
              </div>
              <div v-else-if="!answer" key="doc-placeholder" class="doc-placeholder">
                <p>从左侧选择一篇教程，或在下方输入问题，让 AI 帮你解答。</p>
              </div>
            </transition>
        </div>

      </section>

      <div class="rag-fixed-input-container">
        <div class="rag-query-card">
          <div class="rag-input-container">
          <div class="rag-input-wrapper-expanded">
            <el-input
              v-model="query"
              :autosize="{ minRows: 2, maxRows: 6 }"
              type="textarea"
              placeholder="输入要查找的内容或想问的问题，例如：如何安装模组"
              @keyup.enter.exact.prevent="onSearch"
              class="rag-textarea"
            />
          </div>
          <div class="rag-search-controls">
            <el-button type="primary" :loading="loading" @click="onSearch" size="default">
              <el-icon style="margin-right: 4px">
                <component :is="mode === 'qa' ? 'ChatDotRound' : 'Search'" />
              </el-icon>
              {{ mode === 'qa' ? '问问 AI' : '搜索' }}
            </el-button>
            <div class="rag-mode-dropdown-right">
              <el-dropdown @command="handleModeChange" trigger="click">
                <el-button size="default" type="info" plain>
                  <el-icon style="margin-right: 4px">
                    <component :is="mode === 'qa' ? 'ChatDotRound' : 'Search'" />
                  </el-icon>
                  {{ mode === 'qa' ? 'AI 问答' : '文档搜索' }}
                  <el-icon style="margin-left: 4px"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="search">
                      <el-icon style="margin-right: 8px"><Search /></el-icon>
                      文档搜索
                    </el-dropdown-item>
                    <el-dropdown-item command="qa">
                      <el-icon style="margin-right: 8px"><ChatDotRound /></el-icon>
                      AI 问答
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
          </div>
          <div class="rag-query-info">
            <span v-if="lastTookMs" class="hint">耗时：{{ lastTookMs }} ms</span>
            <span v-if="!ragEnabled" class="hint weak">当前仅开启文档搜索（RAG 未配置）</span>
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
          <el-form-item label="正文内容">
            <el-input
              v-model="newContent"
              type="textarea"
              :autosize="{ minRows: 6, maxRows: 14 }"
              placeholder="在这里粘贴或编写完整教程文本（支持中英文，不需要特别格式）"
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
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { Search, ChatDotRound, ArrowDown } from '@element-plus/icons-vue'
import {
  createTutorial,
  type SearchAndAskResponse,
  searchAndAsk,

  getTutorial,
  type TutorialDetail,

} from '../api/tutorials'
import { useAuth } from '../stores/auth'

const auth = useAuth()
const router = useRouter()

const mode = ref<'search' | 'qa'>('qa')
const query = ref('')
const loading = ref(false)
const lastTookMs = ref<number | null>(null)
const ragEnabled = ref(true)
// const showResults = ref(false) // 已删除搜索结果功能

const results = ref<SearchAndAskResponse['search']['items']>([])
const answer = ref<SearchAndAskResponse['answer'] | null>(null)

// const listLoading = ref(false) // 已删除搜索结果功能，不再需要

const selectedTutorial = ref<TutorialDetail | null>(null)
const tutorialLoading = ref(false)
const isDeletingText = ref(false)
const displayedLines = ref<string[]>([])

const newTitle = ref('')
const newDesc = ref('')
const newContent = ref('')
const creating = ref(false)
const createDialogVisible = ref(false)

const splitAnswer = computed(() => {
  if (!answer.value?.text) return []
  return answer.value.text.split(/\n+/).filter(Boolean)
})



async function onSearch() {
  const q = query.value.trim()
  if (!q) {
    ElMessage.warning('请输入要搜索或提问的内容')
    return
  }
  loading.value = true
  try {
    const data = await searchAndAsk({ query: q, mode: mode.value, limit: 3 })
    results.value = data.search.items || []
    answer.value = data.answer
    lastTookMs.value = data.search.tookMs
    ragEnabled.value = data.ragEnabled
  } catch (e: any) {
    const msg = e?.response?.data?.error || '搜索失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}



async function onSelectTutorial(id: number) {
  // 如果已有教程内容，先执行文字删除动画
  if (selectedTutorial.value && !isDeletingText.value) {
    isDeletingText.value = true
    tutorialLoading.value = true
    
    // 获取当前显示的所有行
    const currentLines = [...displayedLines.value]
    
    // 逐行删除文字
    for (let i = currentLines.length - 1; i >= 0; i--) {
      await new Promise(resolve => setTimeout(resolve, 50)) // 每50ms删除一行
      displayedLines.value = currentLines.slice(0, i)
    }
    
    // 清空教程内容
    selectedTutorial.value = null
    isDeletingText.value = false
  }
  
  tutorialLoading.value = true
  try {
    const detail = await getTutorial(id)
    selectedTutorial.value = detail
    // 加载完成后，立即显示新内容
    displayedLines.value = detail.content.split(/\r?\n/).filter(Boolean)
  } catch (e: any) {
    const msg = e?.response?.data?.error || '加载教程失败'
    ElMessage.error(msg)
  } finally {
    tutorialLoading.value = false
  }
}

function goUpload() {
  router.push('/upload')
}

function goTutorialLibrary() {
  router.push('/tutorials/library')
}

function goToTutorial(tutorialId: number) {
  router.push(`/tutorials/library#${tutorialId}`)
}

function handleModeChange(command: string) {
  mode.value = command as 'search' | 'qa'
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
    if (data.id) {
      await onSelectTutorial(data.id)
    }
    createDialogVisible.value = false
  } catch (e: any) {
    const msg = e?.response?.data?.error || '保存失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    creating.value = false
  }
}

// function toggleResults() {
//   showResults.value = !showResults.value
// }

// function handleSourcesChange(activeNames: string[]) {
//   // 当展开"已读取文档"时，自动显示搜索结果
//   if (activeNames.includes('sources') && !showResults.value) {
//     showResults.value = true
//   }
// }

onMounted(() => {
  // 初始化displayedLines
  if (selectedTutorial.value) {
    displayedLines.value = selectedTutorial.value.content.split(/\r?\n/).filter(Boolean)
  }
})
</script>

<style scoped>
.rag-page {
  min-height: 100vh;
  background: #f3f4f6;
  padding: 0;
  margin: 0;
}
.rag-container {
  min-height: 100vh;
  background: #ffffff;
  padding: 16px;
}
.rag-inner {
  max-width: 1200px;
  margin: 0 auto;
}
.rag-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
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
.rag-fixed-input-container {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: #ffffff;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
  padding: 24px;
  padding-bottom: 32px;
  z-index: 100;
  box-shadow: 0 -4px 12px rgba(15, 23, 42, 0.05);
}
.rag-query-card {
  padding: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  margin: 0 auto;
  max-width: 1000px;
  border: none;
}
.rag-input-container {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 12px;
}
.rag-input-wrapper-expanded {
  flex: 1;
  min-width: 0;
  margin-right: 16px;
}
.rag-search-controls {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
}
.rag-mode-dropdown-right .el-button {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.15);
}
.rag-mode-dropdown-right :deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  padding: 8px 16px;
}
.rag-input-wrapper {
  flex: 1;
  min-width: 0;
}
.rag-textarea {
  border-radius: 12px;
}
.rag-textarea :deep(.el-textarea__inner) {
  border-radius: 12px;
  border-color: #409eff;
  box-shadow: 0 0 0 1px #409eff;
  font-size: 16px; /* 防止iOS自动放大 */
}
.rag-textarea :deep(.el-textarea__inner:focus) {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}
.rag-search-button {
  flex-shrink: 0;
  padding-top: 0;
}
.rag-search-button :deep(.el-button) {
  height: 40px;
  padding: 8px 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
}
.rag-query-info {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 8px;
}
.hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.hint.weak {
  color: #9ca3af;
}
.rag-unified-container {
  padding: 24px 32px;
  border-radius: 24px;
  background: #ffffff;
  box-shadow: none;
  margin: 24px auto 80px;
  max-width: 1000px;
  border: none;
}
.rag-column {
  border-radius: 0;
  padding: 0 0 24px 0;
  background: transparent;
  box-shadow: none;
  max-width: 100%;
}
/* 过渡动画效果 - 移动设备优化 */
.fade-slide-enter-active {
  transition: opacity 0.1s ease-out;
}
.fade-slide-leave-active {
  transition: none;
  position: absolute;
  width: 100%;
}
.fade-slide-enter-from {
  opacity: 0;
}
.fade-slide-leave-to {
  opacity: 0;
}
/* 加载状态样式 */
.doc-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: var(--el-text-color-secondary);
}
.loading-icon {
  font-size: 32px;
  margin-bottom: 16px;
  animation: rotating 2s linear infinite;
}
@keyframes rotating {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}
@media (max-width: 900px) {
  .rag-header {
    flex-direction: column;
  }
  .rag-header-actions {
    align-self: flex-start;
  }
  .rag-main {
    grid-template-columns: minmax(0, 1fr);
  }
}
.section-title {
  margin: 0 0 8px;
  font-size: 15px;
}
.rag-column {
  border-radius: 16px;
  padding: 12px 14px;
  background: #ffffff;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}
.section-title {
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.toggle-icon {
  transition: transform 0.3s;
}
.toggle-icon.rotated {
  transform: rotate(90deg);
}
.full-width {
  grid-column: span 2;
}
.search-results {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.result-card {
  cursor: pointer;
}
.rc-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}
.rc-name {
  font-weight: 600;
}
.rc-score {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.rc-excerpt {
  margin: 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.search-empty {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}
.empty-state {
  text-align: center;
  max-width: 400px;
}
.empty-icon {
  margin-bottom: 16px;
  color: var(--el-color-info);
}
.empty-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 8px;
  color: var(--el-text-color-primary);
}
.empty-desc {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin: 0 0 20px;
  line-height: 1.5;
}
.empty-actions {
  display: flex;
  justify-content: center;
}
.qa-box {
  margin-bottom: 12px;
}
.qa-label {
  font-size: 12px;
  font-weight: 600;
  color: #16a34a;
  margin-bottom: 4px;
}
.qa-text {
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(16, 185, 129, 0.04);
  border: 1px solid rgba(16, 185, 129, 0.12);
  font-size: 14px;
}
.qa-text p {
  margin: 0 0 4px;
}
.qa-text p:last-child {
  margin-bottom: 0;
}
.qa-sources-collapsible {
  margin-bottom: 12px;
}
.sources-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--el-text-color-regular);
}
.sources-icon {
  font-size: 16px;
}
.sources-list {
  padding-left: 18px;
  margin: 8px 0 0;
  font-size: 12px;
}
.source-link {
  color: #409eff;
  text-decoration: none;
  transition: color 0.2s;
}
.source-link:hover {
  color: #66b1ff;
  text-decoration: underline;
}
.sources-list li {
  margin-bottom: 6px;
  line-height: 1.4;
}
.sources-list li:last-child {
  margin-bottom: 0;
}
.doc-viewer {
  margin-top: 8px;
}
.doc-header h3 {
  margin: 0 0 4px;
}
.doc-desc {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.doc-body {
  padding: 8px 10px;
  background: #f9fafb;
  border-radius: 8px;
  max-height: 420px;
  overflow: auto;
  font-size: 14px;
}
.doc-body p {
  margin: 0 0 4px;
  transition: all 0.3s ease;
}

.doc-line {
  opacity: 1;
  transform: translateY(0);
  transition: opacity 0.2s ease, transform 0.2s ease;
  margin-bottom: 4px;
  min-height: 1.2em;
}

.doc-line:last-child {
  margin-bottom: 0;
}
.doc-placeholder {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-top: 12px;
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
