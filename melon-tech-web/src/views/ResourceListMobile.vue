<template>
  <div class="m-res-container">
    <!-- 搜索栏 -->
    <div class="m-search-bar">
      <el-input
        v-model="queryDraft"
        placeholder="搜索模组..."
        clearable
        @clear="handleClearSearch"
        @keyup.enter="applySearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-button type="primary" size="small" @click="$router.push('/upload')" v-if="auth.user">
        <el-icon><Upload /></el-icon>
      </el-button>
    </div>

    <!-- 统计 -->
    <div class="m-stats">
      <span>{{ combinedTotal }} 个模组</span>
      <el-button text size="small" @click="refreshAll">刷新</el-button>
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
import { Search, Upload, Document, ArrowRight } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { listResources, type ResourceItem } from '../api/resources'
import { getResourceLikes, type LikeInfo } from '../api/likes'
import { useAuth } from '../stores/auth'
import { listExternalResources, externalPreviewUrl, type ExternalFileInfo } from '../api/external'

const queryDraft = ref('')
const query = ref('')
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
  const q = query.value.trim().toLowerCase()
  const sorted = [...externalAll.value].sort((a, b) => {
    const da = parseDate(a.date || '')
    const db = parseDate(b.date || '')
    if (da !== db) return db - da
    return String(a.name || '').localeCompare(String(b.name || ''), 'zh-Hans-CN')
  })
  if (!q) return sorted
  return sorted.filter(f => String(f.name || '').toLowerCase().includes(q))
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
onMounted(() => { queryDraft.value = query.value; refreshAll() })
</script>

<style scoped>
.m-res-container {
  padding: 12px;
  max-width: 100%;
}

.m-search-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.m-search-bar :deep(.el-input__wrapper) {
  border-radius: 10px;
}

.m-stats {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
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
.m-card-author, .m-card-date, .m-card-size, .m-card-likes {
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
