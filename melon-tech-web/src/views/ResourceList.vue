<template>
  <div class="file-library-container">
    <!-- Header Section -->
    <div class="library-header">
      <div class="header-content">
        <h2 class="page-title">文件资源库</h2>
        <p class="page-subtitle">探索、分享和管理您的所有文档资源</p>
      </div>
      <div class="header-actions">
        <el-input
          v-model="queryDraft"
          placeholder="搜索资源..."
          class="search-input"
          clearable
          @clear="handleClearSearch"
          @keyup.enter="applySearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" class="upload-btn" @click="$router.push('/upload')">
          <el-icon><Upload /></el-icon>
          <span>上传文件</span>
        </el-button>
        <el-button class="refresh-btn" @click="refreshAll">刷新列表</el-button>
      </div>
    </div>

    <!-- Content Section -->
    <div class="library-content">
      <div class="stream-toolbar">
        <div class="stream-left">
          <el-text class="muted-text">
            显示 {{ combinedTotal }} 条
          </el-text>
        </div>
        <div class="stream-right">
          <el-text class="muted-text">{{ combinedPageSize }}/页</el-text>
        </div>
      </div>

      <div class="stream-list">
        <div v-if="combinedPaged.length > 0" class="resource-grid">
          <div
            v-for="it in combinedPaged"
            :key="it.key"
            class="resource-card-wrapper"
            @click="handleOpen(it)"
          >
            <el-card class="resource-card" shadow="hover">
              <div class="card-body">
                <div class="card-icon" :class="{ 'has-cover': getCoverPath(it) }">
                  <template v-if="getCoverPath(it)">
                    <img
                      class="card-cover-image"
                      :src="getCoverPath(it)!"
                      alt="cover"
                      loading="lazy"
                      referrerpolicy="no-referrer"
                      @error="markCoverBroken(it.key)"
                    />
                  </template>
                  <template v-else>
                    <el-icon><Document /></el-icon>
                  </template>
                </div>

                <div class="card-info">
                  <div class="info-top">
                    <div class="title-row">
                      <h3 class="resource-title" :title="getTitle(it)">{{ getTitle(it) }}</h3>
                      <div class="author-info-mini">
                        <template v-if="it.source === 'internal'">
                          <el-avatar :size="15" class="author-avatar">{{ (it.internal as any).author_username?.[0]?.toUpperCase() || 'U' }}</el-avatar>
                          <span class="author-name">{{ (it.internal as any).author_username || 'Unknown' }}</span>
                        </template>
                        <template v-else>
                          <span class="source-tag">外站</span>
                        </template>
                      </div>
                    </div>
                    <p class="resource-desc">
                      {{ getDescription(it) }}
                    </p>
                  </div>

                  <div class="info-bottom">
                    <div class="card-meta">
                      <span class="date">{{ getDate(it) }}</span>
                      <template v-if="it.source === 'internal'">
                        <div
                          class="like-action"
                          :class="{ 'is-active': likesMap[it.internal.id]?.liked }"
                          @click.stop="toggleLike(it.internal.id)"
                        >
                          <el-icon>
                            <component :is="likesMap[it.internal.id]?.liked ? StarFilled : Star" />
                          </el-icon>
                          <span class="like-count">{{ likesMap[it.internal.id]?.likes || 0 }}</span>
                        </div>
                      </template>
                      <template v-else>
                        <span class="ext-size">{{ it.external.size || '-' }}</span>
                      </template>
                    </div>
                  </div>
                </div>
              </div>
            </el-card>
          </div>
        </div>

        <el-empty v-if="!loadingAny && combinedTotal === 0" description="暂无资源" :image-size="200" />

        <div class="pagination-wrapper" v-if="combinedTotal > 0">
          <el-pagination
            background
            layout="prev, pager, next"
            :page-size="combinedPageSize"
            :current-page="combinedPage"
            :total="combinedTotal"
            @current-change="handleCombinedPageChange"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Upload, Document, Star, StarFilled } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { listResources, type ResourceItem } from '../api/resources'
import { getResourceLikes, likeResource, unlikeResource, type LikeInfo } from '../api/likes'
import { useAuth } from '../stores/auth'
import { listExternalResources, externalPreviewUrl, type ExternalFileInfo } from '../api/external'

const queryDraft = ref('')
const query = ref('')

const combinedPage = ref(1)
const combinedPageSize = 15

const items = ref<ResourceItem[]>([])
const internalTotal = ref(0)
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
  return sorted.filter(f => {
    const n = String(f.name || '').toLowerCase()
    return n.includes(q)
  })
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

function getDescription(it: CombinedItem) {
  return it.source === 'internal' ? (it.internal.description || '暂无描述') : (it.external.name || '暂无描述')
}

function getDate(it: CombinedItem) {
  return it.source === 'internal' ? formatDate(it.internal.created_at) : (it.external.date || '-')
}

function getCoverPath(it: CombinedItem): string | null {
  if (brokenCovers.value[it.key]) return null
  if (it.source === 'internal') {
    return toImageUrl((it.internal as any).coverUrlPath) || null
  }
  const fid = getExternalFileId(it.external)
  return fid ? externalPreviewUrl(fid) : null
}

function markCoverBroken(key: string) {
  if (!brokenCovers.value[key]) {
    brokenCovers.value = { ...brokenCovers.value, [key]: true }
  }
}

function handleCombinedPageChange(p: number) {
  combinedPage.value = p
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function handleOpen(it: CombinedItem) {
  if (it.source === 'internal') {
    router.push(`/share/${it.internal.slug}`)
    return
  }
  const fid = getExternalFileId(it.external)
  if (fid) router.push({ name: 'external-resource', query: { file: fid } })
}

function applySearch() {
  query.value = queryDraft.value.trim()
  combinedPage.value = 1
  refreshAll()
}

function handleClearSearch() {
  queryDraft.value = ''
  applySearch()
}

async function refreshAll() {
  await Promise.all([refreshInternal(), refreshExternal()])
}

async function refreshInternal() {
  loading.value = true
  try {
    const all: ResourceItem[] = []
    const reqPageSize = 200
    let p = 1
    let t = 0
    while (true) {
      const data: any = await listResources({ q: query.value || undefined, page: p, pageSize: reqPageSize })
      const chunk = (data?.items || []) as ResourceItem[]
      if (p === 1) t = Number(data?.total || 0)
      all.push(...chunk)
      if (t > 0 && all.length >= t) break
      if (!chunk.length) break
      p += 1
      if (p > 200) break
    }
    items.value = all
    internalTotal.value = t || all.length
  } catch {
    ElMessage.error('获取本站资源失败')
  } finally {
    loading.value = false
  }
}

async function refreshExternal() {
  externalLoading.value = true
  try {
    let page = 1
    const pageSize = 25
    let total = 0
    const allFiles: ExternalFileInfo[] = []
    do {
      const r = await listExternalResources({ page, pageSize, sort: 'date', order: 'desc', search: query.value || undefined })
      total = r.total
      allFiles.push(...(r.files || []))
      page++
    } while (allFiles.length < total && page <= 50)
    externalAll.value = allFiles
    brokenCovers.value = {}
  } catch (e: any) {
    const msg = String(e?.message || '外站列表获取失败')
    ElMessage.error(msg)
  } finally {
    externalLoading.value = false
  }
}

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString()
}

async function toggleLike(id: number) {
  try {
    if (!auth.user) {
      ElMessage.warning('请先登录')
      return
    }
    const current = likesMap.value[id] || { id, likes: 0, liked: false }
    if (current.liked) {
      const r = await unlikeResource(id)
      likesMap.value = { ...likesMap.value, [id]: { id, likes: r.likes, liked: r.liked } }
    } else {
      const r = await likeResource(id)
      likesMap.value = { ...likesMap.value, [id]: { id, likes: r.likes, liked: r.liked } }
    }
  } catch (e: any) {
    const msg = e?.response?.data?.error || '操作失败'
    ElMessage.error(msg)
  }
}

let lastLikesKey = ''
async function refreshLikesForVisible() {
  const ids = combinedPaged.value
    .filter(it => it.source === 'internal')
    .map(it => it.internal.id)
  if (!ids.length) return
  const key = [...new Set(ids)].sort((a, b) => a - b).join(',')
  if (!key || key === lastLikesKey) return
  lastLikesKey = key

  try {
    const likes = await getResourceLikes(ids)
    const m: Record<number, LikeInfo> = { ...likesMap.value }
    likes.forEach(i => {
      m[i.id] = i
    })
    likesMap.value = m
  } catch {
    // ignore
  }
}

watch(combinedPaged, () => {
  refreshLikesForVisible()
})

watch([query], () => {
  combinedPage.value = 1
})

onMounted(() => {
  queryDraft.value = query.value
  refreshAll()
})
</script>

<style scoped>
.file-library-container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 32px;
  min-height: 80vh;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color: #1e293b;
}

.library-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 48px;
  flex-wrap: wrap;
  gap: 24px;
}

.header-content .page-title {
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 8px 0;
  letter-spacing: -0.02em;
}

.header-content .page-subtitle {
  font-size: 15px;
  color: #64748b;
  margin: 0;
  font-weight: 400;
}

.header-actions {
  display: flex;
  gap: 15px;
  align-items: center;
}

.search-input {
  width: 280px;
  transition: width 0.3s ease;
}

.search-input:focus-within {
  width: 320px;
}

:deep(.el-input__wrapper) {
  box-shadow: none !important;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 8px 12px;
  background-color: #f9fafb;
  transition: all 0.2s;
}

:deep(.el-input__wrapper.is-focus) {
  background-color: #fff;
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 3px rgba(var(--el-color-primary-rgb), 0.1) !important;
}

.upload-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: #10b981;
  border-color: #10b981;
  border-radius: 10px;
  padding: 10px 20px;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(15, 185, 129, 0.2);
  transition: all 0.2s ease;
}

.upload-btn:hover {
  background-color: #059669;
  border-color: #059669;
  transform: translateY(-1px);
  box-shadow: 0 6px 15px rgba(15, 185, 129, 0.3);
}

.refresh-btn {
  border-radius: 10px;
  padding: 10px 18px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #0f172a;
  transition: all 0.2s ease;
}

.refresh-btn:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
  transform: translateY(-1px);
}

.stream-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 15px;
  margin: 0 0 14px 0;
}

.stream-left,
.stream-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stream-list {
  border-radius: 15px;
}

.muted-text {
  color: #64748b;
}

.source-tag {
  font-size: 11px;
  color: #6366f1;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.18);
  padding: 2px 8px;
  border-radius: 999px;
  white-space: nowrap;
}

.ext-size {
  font-size: 12px;
  color: #0f172a;
  background: rgba(15, 23, 42, 0.04);
  border: 1px solid rgba(15, 23, 42, 0.08);
  padding: 3px 10px;
  border-radius: 999px;
}

.resource-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 24px;
}

.resource-card-wrapper {
  height: 100%;
}

.resource-card {
  height: 150px;
  border: 1px solid #f1f5f9;
  border-radius: 15px;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  background: #fff;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

.resource-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 40px -12px rgba(0, 0, 0, 0.08);
  border-color: rgba(15, 185, 129, 0.2);
}

.resource-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 15px;
}

.card-body {
  display: flex;
  gap: 15px;
  flex: 1;
  height: 100%;
}

.card-icon {
  width: 128px;
  height: 100%;
  border-radius: 12px;
  background: #ecfdf5;
  color: #10b981;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48px;
  flex-shrink: 0;
  transition: transform 0.3s ease;
}

.card-icon.has-cover {
  padding: 0;
  background: #0f172a;
  overflow: hidden;
}

.card-cover-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.resource-card:hover .card-icon {
  transform: scale(1.05);
  background: #d1fae5;
}

.card-info {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 2px 0;
}

.title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  gap: 8px;
}

.resource-title {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.author-info-mini {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.author-avatar {
  background: #f1f5f9;
  color: #64748b;
  font-size: 10px;
  font-weight: 600;
  border: 1px solid #e2e8f0;
}

.author-name {
  font-size: 12px;
  color: #94a3b8;
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resource-desc {
  font-size: 14px;
  color: #64748b;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
}

.info-bottom {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-top: auto;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 15px;
  flex-wrap: wrap;
}

.date {
  font-size: 13px;
  color: #94a3b8;
}

.like-action {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  color: #94a3b8;
  padding: 6px 12px;
  border-radius: 20px;
  background: #f8fafc;
  border: 1px solid transparent;
}

.like-action:hover {
  background: linear-gradient(135deg, #e0f2fe 0%, #f0f9ff 100%);
  color: #0ea5e9;
  transform: translateY(-1px);
}

.like-action.is-active {
  background: linear-gradient(135deg, #312e81 0%, #4338ca 100%);
  color: #fbbf24;
  border-color: rgba(251, 191, 36, 0.3);
  box-shadow: 0 4px 12px rgba(67, 56, 202, 0.3);
}

.like-action.is-active .el-icon {
  filter: drop-shadow(0 0 4px rgba(251, 191, 36, 0.5));
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.1); }
  100% { transform: scale(1); }
}

.like-count {
  font-size: 13px;
  font-weight: 600;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 64px;
}

@media (max-width: 768px) {
  .file-library-container {
    padding: 16px;
    width: 100%;
    overflow-x: hidden;
  }

  .library-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
    margin-bottom: 24px;
    width: 100%;
  }

  .header-actions {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .resource-card-wrapper {
    max-width: 100%;
  }

  .el-pagination {
    flex-wrap: wrap;
    justify-content: center;
    --el-pagination-button-width: 32px;
  }

  .search-input {
    width: 100%;
  }

  .search-input:focus-within {
    width: 100%;
  }

  .resource-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .card-body {
    flex-direction: row;
    align-items: center;
  }

  .card-icon {
    width: 80px;
    height: 80px;
    border-radius: 8px;
    flex-shrink: 0;
  }

  .card-info {
    min-width: 0;
    padding-left: 0;
  }

  .resource-card {
    height: auto;
  }

  .resource-card :deep(.el-card__body) {
    padding: 12px;
  }

  .stream-toolbar {
    flex-wrap: wrap;
    gap: 8px;
  }

  .resource-desc {
    line-clamp: 2;
    -webkit-line-clamp: 2;
  }

  .author-avatar {
    width: 16px;
    height: 16px;
    font-size: 10px;
  }
}
</style>
