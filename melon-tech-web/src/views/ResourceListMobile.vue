<template>
  <div class="m-res-container">
    <!-- 搜索栏 -->
    <div class="m-search-bar">
      <div class="m-search-wrap">
        <el-input
          v-model="queryDraft"
          placeholder="搜索模组..."
          size="large"
          clearable
          @clear="handleClearSearch"
          @keyup.enter="applySearch"
          @focus="onFocus"
          @blur="onBlurHide"
        >
          <template #prefix>
            <el-icon :size="18"><Search /></el-icon>
          </template>
        </el-input>
        <transition name="suggest-fade">
          <div v-if="showSuggest && suggestions.length" class="m-suggest">
            <div
              v-for="s in suggestions"
              :key="s.slug || s.name"
              class="m-suggest-item"
              @mousedown.prevent="pickSuggestion(s)"
            >
              <img v-if="s.cover" :src="s.cover" class="m-suggest-cover" />
              <div class="m-suggest-info">
                <div class="m-suggest-title">{{ s.title }}</div>
                <div v-if="s.tags?.length" class="m-suggest-tags">
                  <span v-for="t in s.tags" :key="t" class="m-suggest-tag">{{ t }}</span>
                </div>
              </div>
            </div>
          </div>
        </transition>
      </div>
      <el-button type="primary" size="large" @click="applySearch" class="m-search-btn">
        <el-icon><Search /></el-icon>
      </el-button>
      <el-button type="success" size="large" @click="$router.push('/upload')" v-if="auth.user" class="m-upload-btn">
        <el-icon><Upload /></el-icon>
      </el-button>
    </div>

    <!-- 统计 -->
    <div class="m-stats">
      <span>{{ combinedTotal }} 个模组</span>
      <el-button text size="small" @click="refreshAll" :loading="loadingAny">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <!-- 列表 -->
    <div class="m-list">
      <div
        v-for="it in combinedPaged"
        :key="it.key"
        class="m-card"
        @click="handleOpen(it)"
      >
        <!-- 封面 -->
        <div class="m-card-cover">
          <img
            v-if="getCoverPath(it)"
            :src="getCoverPath(it)!"
            alt="cover"
            loading="lazy"
            referrerpolicy="no-referrer"
            @error="markCoverBroken(it.key)"
          />
          <el-icon v-else :size="28" class="m-card-placeholder"><Document /></el-icon>
        </div>

        <!-- 信息 -->
        <div class="m-card-info">
          <div class="m-card-title">{{ getTitle(it) }}</div>
          <div class="m-card-meta">
            <template v-if="it.source === 'internal'">
              <span class="m-card-author">{{ (it.internal as any).author_username || '未知' }}</span>
              <span class="m-card-dot">·</span>
              <span class="m-card-date">{{ getDate(it) }}</span>
              <span class="m-card-dot" v-if="likesMap[it.internal.id]?.likes">·</span>
              <span class="m-card-likes" v-if="likesMap[it.internal.id]?.likes">
                ⭐ {{ likesMap[it.internal.id]?.likes }}
              </span>
              <span class="m-card-dot" v-if="(it.internal as any).download_count">·</span>
              <span class="m-card-downloads" v-if="(it.internal as any).download_count">
                ⬇ {{ (it.internal as any).download_count }}
              </span>
            </template>
            <template v-else>
              <span class="m-card-ext">外站</span>
              <span class="m-card-dot">·</span>
              <span class="m-card-size">{{ it.external.size || '-' }}</span>
            </template>
          </div>
        </div>
        <el-icon class="m-card-arrow"><ArrowRight /></el-icon>
      </div>

      <div v-if="loadingAny" class="m-loading">加载中...</div>
      <div v-if="!loadingAny && combinedTotal === 0" class="m-empty">暂无资源</div>
    </div>

    <!-- 分页 -->
    <div class="m-pagination" v-if="combinedTotal > 0">
      <el-button
        size="small"
        :disabled="combinedPage <= 1"
        @click="handleCombinedPageChange(combinedPage - 1)"
      >上一页</el-button>
      <span class="m-page-info">{{ combinedPage }}/{{ Math.ceil(combinedTotal / combinedPageSize) }}</span>
      <el-button
        size="small"
        :disabled="combinedPage >= Math.ceil(combinedTotal / combinedPageSize)"
        @click="handleCombinedPageChange(combinedPage + 1)"
      >下一页</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Upload, Document, ArrowRight, Refresh } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { listResources, type ResourceItem } from '../api/resources'
import { getResourceLikes, type LikeInfo } from '../api/likes'
import { useAuth } from '../stores/auth'
import { listExternalResources, externalPreviewUrl, type ExternalFileInfo } from '../api/external'

const queryDraft = ref('')
const query = ref('')
const showSuggest = ref(false)
const suggestions = ref<any[]>([])
let suggestTimer: ReturnType<typeof setTimeout> | null = null

async function fetchSuggestions(q: string) {
  if (!q.trim()) { suggestions.value = []; return }
  try {
    const data: any = await listResources({ q, page: 1, pageSize: 8 })
    suggestions.value = (data.items || []).map((it: any) => ({
      title: it.title,
      slug: it.slug,
      cover: it.coverUrlPath,
      tags: it.tags,
      isExternal: false,
    }))
    const ext = await listExternalResources({ page: 1, pageSize: 5, search: q })
    for (const f of ext.files) {
      const fid = getExternalFileId(f)
      suggestions.value.push({
        title: f.name,
        name: fid,
        cover: f.preview_url,
        isExternal: true,
      })
    }
  } catch { suggestions.value = [] }
}

function onDraftInput() {
  if (suggestTimer) clearTimeout(suggestTimer)
  suggestTimer = setTimeout(() => fetchSuggestions(queryDraft.value), 300)
}

function pickSuggestion(s: any) {
  showSuggest.value = false
  if (s.isExternal) {
    router.push({ name: 'external-resource', query: { file: s.name } })
  } else {
    router.push(`/share/${s.slug}`)
  }
}

function onFocus() {
  showSuggest.value = true
  const wrap = document.querySelector('.m-search-wrap')
  if (wrap) wrap.classList.add('focused')
}
function onBlurHide() {
  setTimeout(() => { showSuggest.value = false }, 200)
  const wrap = document.querySelector('.m-search-wrap')
  if (wrap) wrap.classList.remove('focused')
}
const combinedPage = ref(1)
const combinedPageSize = 15

const items = ref<ResourceItem[]>([])
const loading = ref(false)
const likesMap = ref<Record<number, LikeInfo>>({})
const auth = useAuth()
const router = useRouter()

const externalLoading = ref(false)
const externalAll = ref<ExternalFileInfo[]>([])
const brokenCovers = ref<Record<string, true>>({})
const loadingAny = computed(() => loading.value || externalLoading.value)

function toImageUrl(path?: string | null) {
  if (!path) return ''
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  if (path.startsWith('/uploads/')) return path
  return path
}

function parseDate(s: string) {
  const v = Date.parse(s)
  return Number.isFinite(v) ? v : 0
}

function getExternalFileId(f: ExternalFileInfo): string {
  const match = f.download_url?.match(/[?&]file=([^&]+)/)
  if (match) return decodeURIComponent(match[1]!)
  return ''
}

type CombinedItem =
  | { source: 'internal'; key: string; ts: number; internal: ResourceItem }
  | { source: 'external'; key: string; ts: number; external: ExternalFileInfo }

const externalFiltered = computed(() => {
  const sorted = [...externalAll.value].sort((a, b) => {
    const da = parseDate(a.date || '')
    const db = parseDate(b.date || '')
    if (da !== db) return db - da
    return String(a.name || '').localeCompare(String(b.name || ''), 'zh-Hans-CN')
  })
  return sorted
})

const combinedAll = computed<CombinedItem[]>(() => {
  const out: CombinedItem[] = []
  for (const r of items.value) {
    out.push({ source: 'internal', key: `i:${r.id}`, ts: parseDate(r.created_at || ''), internal: r })
  }
  for (const f of externalFiltered.value) {
    out.push({ source: 'external', key: `e:${getExternalFileId(f)}`, ts: parseDate(f.date || ''), external: f })
  }
  out.sort((a, b) => b.ts - a.ts || a.key.localeCompare(b.key, 'zh-Hans-CN'))
  return out
})

const combinedTotal = computed(() => combinedAll.value.length)
const combinedPaged = computed(() => {
  const start = (combinedPage.value - 1) * combinedPageSize
  return combinedAll.value.slice(start, start + combinedPageSize)
})

function getTitle(it: CombinedItem) {
  return it.source === 'internal' ? it.internal.title : it.external.name
}
function getDate(it: CombinedItem) {
  return it.source === 'internal' ? formatDate(it.internal.created_at) : (it.external.date || '-')
}
function getCoverPath(it: CombinedItem): string | null {
  if (brokenCovers.value[it.key]) return null
  if (it.source === 'internal') return toImageUrl((it.internal as any).coverUrlPath) || null
  const fid = getExternalFileId(it.external)
  return fid ? externalPreviewUrl(fid) : null
}
function markCoverBroken(key: string) {
  if (!brokenCovers.value[key]) brokenCovers.value = { ...brokenCovers.value, [key]: true }
}
function handleCombinedPageChange(p: number) {
  combinedPage.value = p
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
function handleOpen(it: CombinedItem) {
  if (it.source === 'internal') { router.push(`/share/${it.internal.slug}`); return }
  const fid = getExternalFileId(it.external)
  if (fid) router.push({ name: 'external-resource', query: { file: fid } })
}
function applySearch() { query.value = queryDraft.value.trim(); combinedPage.value = 1; refreshAll() }
function handleClearSearch() { queryDraft.value = ''; applySearch() }
async function refreshAll() { await Promise.all([refreshInternal(), refreshExternal()]) }

async function refreshInternal() {
  loading.value = true
  try {
    const all: ResourceItem[] = []
    let p = 1
    let t = 0
    while (true) {
      const data: any = await listResources({ q: query.value || undefined, page: p, pageSize: 200 })
      const chunk = (data?.items || []) as ResourceItem[]
      if (p === 1) t = Number(data?.total || 0)
      all.push(...chunk)
      if (t > 0 && all.length >= t) break
      if (!chunk.length) break
      p += 1
      if (p > 200) break
    }
    items.value = all
  } catch { ElMessage.error('获取资源失败') }
  finally { loading.value = false }
}

async function refreshExternal() {
  externalLoading.value = true
  try {
    let page = 1
    let total = 0
    const allFiles: ExternalFileInfo[] = []
    do {
      const r = await listExternalResources({ page, pageSize: 25, sort: 'date', order: 'desc', search: query.value || undefined })
      total = r.total
      allFiles.push(...(r.files || []))
      page++
    } while (allFiles.length < total && page <= 50)
    externalAll.value = allFiles
    brokenCovers.value = {}
  } catch (e: any) { ElMessage.error(String(e?.message || '外站列表获取失败')) }
  finally { externalLoading.value = false }
}

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString()
}

let lastLikesKey = ''
async function refreshLikesForVisible() {
  const ids = combinedPaged.value.filter(it => it.source === 'internal').map(it => it.internal.id)
  if (!ids.length) return
  const key = [...new Set(ids)].sort((a, b) => a - b).join(',')
  if (!key || key === lastLikesKey) return
  lastLikesKey = key
  try {
    const likes = await getResourceLikes(ids)
    const m: Record<number, LikeInfo> = { ...likesMap.value }
    likes.forEach(i => { m[i.id] = i })
    likesMap.value = m
  } catch { /* ignore */ }
}

watch(combinedPaged, () => refreshLikesForVisible())
watch([query], () => { combinedPage.value = 1 })
watch(queryDraft, () => onDraftInput())
onMounted(() => { queryDraft.value = query.value; refreshAll() })
</script>

<style scoped>
.m-res-container {
  padding: 12px;
  max-width: 100%;
}

.m-search-wrap {
  position: relative;
  flex: 1;
}

.m-suggest {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 100;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 6px 20px rgba(0,0,0,.15);
  max-height: 320px;
  overflow-y: auto;
  margin-top: 4px;
  border: 1px solid #e5e7eb;
}

.m-suggest-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  transition: background .15s ease;
}
.m-suggest-item:last-child { border-bottom: none }
.m-suggest-item:active { background: #f5f5f5 }
.m-suggest-item:hover { background: #f8faff }

.m-suggest-cover {
  width: 36px;
  height: 36px;
  border-radius: 6px;
  object-fit: cover;
  flex-shrink: 0;
}

.m-suggest-info { flex: 1; min-width: 0; }
.m-suggest-title {
  font-size: 14px;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.m-suggest-tags { display: flex; gap: 4px; margin-top: 2px; flex-wrap: wrap; }
.m-suggest-tag {
  font-size: 11px;
  color: #6366f1;
  background: #eef2ff;
  padding: 1px 6px;
  border-radius: 4px;
}

.m-search-bar {
  display: flex;
  gap: 8px;
  align-items: stretch;
  margin-bottom: 12px;
}
.m-search-bar :deep(.el-input__wrapper) {
  border-radius: 10px;
  padding: 4px 12px;
  transition: box-shadow .25s ease, border-color .25s ease;
}
.m-search-bar :deep(.el-input__wrapper.is-focus),
.m-search-wrap.focused :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 2px rgba(99,102,241,.3);
  border-color: #6366f1;
}
.m-search-bar :deep(.el-input__inner) {
  font-size: 16px;
  height: 40px;
}
.m-search-btn {
  border-radius: 10px;
  flex-shrink: 0;
}
.m-upload-btn {
  border-radius: 10px;
  flex-shrink: 0;
}

.suggest-fade-enter-active,
.suggest-fade-leave-active {
  transition: opacity .2s ease, transform .2s ease;
}
.suggest-fade-enter-from,
.suggest-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.m-stats {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  padding: 0 2px;
}

.m-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.m-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 14px;
  cursor: pointer;
  transition: background .2s;
}
.m-card:active {
  background: var(--el-fill-color);
}

.m-card-cover {
  width: 56px;
  height: 56px;
  border-radius: 10px;
  overflow: hidden;
  background: var(--el-color-success-light-9);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.m-card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.m-card-placeholder {
  color: var(--el-color-success);
}

.m-card-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.m-card-title {
  font-size: 15px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.m-card-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.m-card-author, .m-card-date, .m-card-size, .m-card-likes, .m-card-downloads {
  white-space: nowrap;
}
.m-card-ext {
  font-size: 11px;
  color: #6366f1;
  background: rgba(99, 102, 241, 0.08);
  padding: 1px 6px;
  border-radius: 999px;
}
.m-card-dot {
  color: var(--el-text-color-placeholder);
}

.m-card-arrow {
  color: var(--el-text-color-placeholder);
  flex-shrink: 0;
}

.m-loading, .m-empty {
  text-align: center;
  padding: 40px 0;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.m-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 20px;
}
.m-page-info {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
</style>
