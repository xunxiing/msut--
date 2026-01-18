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
          :placeholder="searchPlaceholder"
          class="search-input"
          clearable
          @clear="handleClearSearch"
          @keyup.enter="applySearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button v-if="showInternal" type="primary" class="upload-btn" @click="$router.push('/upload')">
          <el-icon><Upload /></el-icon>
          <span>上传文件</span>
        </el-button>
        <el-button class="refresh-btn" :loading="loadingAny" @click="refreshAll">刷新列表</el-button>
      </div>
    </div>

    <!-- Content Section -->
    <div class="library-content">
      <div class="source-switch">
        <el-radio-group v-model="sourceFilter" size="large" class="source-switch-group">
          <el-radio-button label="all">全部</el-radio-button>
          <el-radio-button label="internal">本站</el-radio-button>
          <el-radio-button label="external">外站</el-radio-button>
        </el-radio-group>
      </div>

      <div class="stream-toolbar">
        <div class="stream-left">
          <el-text class="external-muted">
            显示 {{ combinedTotal }} 条
            <span v-if="showInternal">（本站 {{ internalTotal }}）</span>
            <span v-if="showExternal">（外站 {{ externalTotalRaw }}）</span>
          </el-text>
        </div>
        <div class="stream-right">
          <el-text class="external-muted">15/页</el-text>
        </div>
      </div>

      <div class="stream-list" v-loading="loadingAny">
        <div v-if="combinedPaged.length > 0" class="resource-grid">
          <div
            v-for="it in combinedPaged"
            :key="it.key"
            class="resource-card-wrapper"
            @click="handleOpen(it)"
          >
            <el-card class="resource-card" :class="{ 'external-card': it.source === 'external' }" shadow="hover">
              <div class="card-body">
                <template v-if="it.source === 'internal'">
                  <div class="card-icon" :class="{ 'has-cover': (it.internal as any).coverUrlPath }">
                    <template v-if="(it.internal as any).coverUrlPath">
                      <img
                        class="card-cover-image"
                        :src="toImageUrl((it.internal as any).coverUrlPath)"
                        alt="cover"
                        loading="lazy"
                      />
                    </template>
                    <template v-else>
                      <el-icon><Document /></el-icon>
                    </template>
                  </div>
                </template>
                <template v-else>
                  <div class="card-icon has-cover external-cover">
                    <template v-if="externalPreviewUrl(it.external) && !brokenExternalPreviews[it.external.full_name]">
                      <img
                        class="card-cover-image"
                        :src="externalPreviewUrl(it.external)"
                        alt="preview"
                        loading="lazy"
                        referrerpolicy="no-referrer"
                        @error="markExternalPreviewBroken(it.external.full_name)"
                      />
                    </template>
                    <template v-else>
                      <div class="external-cover-empty">
                        <el-icon><Document /></el-icon>
                      </div>
                    </template>
                    <div class="external-badge">外站</div>
                  </div>
                </template>

                <div class="card-info">
                  <div class="info-top">
                    <div class="title-row">
                      <template v-if="it.source === 'internal'">
                        <h3 class="resource-title" :title="it.internal.title">{{ it.internal.title }}</h3>
                        <div class="author-info-mini">
                          <el-avatar :size="15" class="author-avatar">{{ (it.internal as any).author_name?.[0]?.toUpperCase() || 'U' }}</el-avatar>
                          <span class="author-name">{{ (it.internal as any).author_name || 'Unknown' }}</span>
                        </div>
                      </template>
                      <template v-else>
                        <h3 class="resource-title" :title="it.external.name || it.external.full_name">{{ it.external.name || it.external.full_name }}</h3>
                        <div class="author-info-mini">
                          <span class="external-domain">me.loveall.icu</span>
                        </div>
                      </template>
                    </div>
                    <p class="resource-desc">
                      {{ it.source === 'internal' ? (it.internal.description || '暂无描述') : it.external.full_name }}
                    </p>
                  </div>

                  <div class="info-bottom">
                    <div class="card-meta">
                      <template v-if="it.source === 'internal'">
                        <span class="date">{{ formatDate(it.internal.created_at) }}</span>
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
                        <span class="date">{{ it.external.date || '-' }}</span>
                        <span class="external-size">{{ it.external.size || prettySize(it.external.size_bytes) }}</span>
                        <div class="external-mini-actions" @click.stop>
                          <el-button size="small" @click="goExternalDetail(it.external.full_name)">详情</el-button>
                          <el-button size="small" type="primary" @click="openExternalDownload(externalDownloadUrl(it.external))">下载</el-button>
                          <el-button
                            v-if="externalPreviewUrl(it.external) && !brokenExternalPreviews[it.external.full_name]"
                            size="small"
                            @click="openExternalPreview(externalPreviewUrl(it.external))"
                          >
                            预览
                          </el-button>
                        </div>
                      </template>
                    </div>
                  </div>
                </div>
              </div>
            </el-card>
          </div>
        </div>

        <el-empty v-else description="暂无资源" :image-size="200" />

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
import { listMeLoveallResources, meLoveallDownloadUrl, meLoveallPreviewUrl, type MeLoveallFileInfo } from '../api/meLoveall'

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

const sourceFilter = ref<'all' | 'internal' | 'external'>('all')
const showInternal = computed(() => sourceFilter.value !== 'external')
const showExternal = computed(() => sourceFilter.value !== 'internal')

const searchPlaceholder = computed(() => {
  if (sourceFilter.value === 'internal') return '搜索本站资源...'
  if (sourceFilter.value === 'external') return '搜索外站资源（按名称/文件名）...'
  return '搜索本站/外站资源...'
})

const externalLoading = ref(false)
const externalAll = ref<MeLoveallFileInfo[]>([])
const brokenExternalPreviews = ref<Record<string, true>>({})

const loadingAny = computed(() => {
  return (showInternal.value && loading.value) || (showExternal.value && externalLoading.value)
})

function toImageUrl(path?: string | null) {
  if (!path) return ''
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  if (path.startsWith('/uploads/')) return path
  return path
}

function prettySize(n: number) {
  if (!n && n !== 0) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let v = n
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i++
  }
  return `${v.toFixed(1)} ${units[i]}`
}

function resolveExternalUrl(raw: string | null) {
  if (!raw) return ''
  try {
    return new URL(raw, 'https://me.loveall.icu').toString()
  } catch {
    return raw
  }
}

function parseExternalDate(s: string) {
  const v = Date.parse(s)
  return Number.isFinite(v) ? v : 0
}

function parseInternalDate(s: string) {
  const v = Date.parse(s)
  return Number.isFinite(v) ? v : 0
}

type CombinedItem =
  | { source: 'internal'; key: string; ts: number; internal: ResourceItem }
  | { source: 'external'; key: string; ts: number; external: MeLoveallFileInfo }

const externalFiltered = computed(() => {
  const q = query.value.trim().toLowerCase()
  const sorted = [...externalAll.value].sort((a, b) => {
    const da = parseExternalDate(a.date || '')
    const db = parseExternalDate(b.date || '')
    if (da !== db) return db - da
    return String(a.full_name || '').localeCompare(String(b.full_name || ''), 'zh-Hans-CN')
  })
  if (!q) return sorted
  return sorted.filter(f => {
    const n = String(f.name || '').toLowerCase()
    const fn = String(f.full_name || '').toLowerCase()
    return n.includes(q) || fn.includes(q)
  })
})

const externalTotalRaw = computed(() => externalFiltered.value.length)

const combinedAll = computed<CombinedItem[]>(() => {
  const out: CombinedItem[] = []
  if (showInternal.value) {
    for (const r of items.value) {
      out.push({ source: 'internal', key: `i:${r.id}`, ts: parseInternalDate(r.created_at || ''), internal: r })
    }
  }
  if (showExternal.value) {
    for (const f of externalFiltered.value) {
      out.push({ source: 'external', key: `e:${f.full_name}`, ts: parseExternalDate(f.date || ''), external: f })
    }
  }
  out.sort((a, b) => b.ts - a.ts || a.key.localeCompare(b.key, 'zh-Hans-CN'))
  return out
})

const combinedTotal = computed(() => combinedAll.value.length)

const combinedPaged = computed(() => {
  const start = (combinedPage.value - 1) * combinedPageSize
  return combinedAll.value.slice(start, start + combinedPageSize)
})

function handleCombinedPageChange(p: number) {
  combinedPage.value = p
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function handleOpen(it: CombinedItem) {
  if (it.source === 'internal') {
    router.push(`/share/${it.internal.slug}`)
    return
  }
  router.push({ name: 'external-resource', query: { file: it.external.full_name } })
}

function applySearch() {
  query.value = queryDraft.value.trim()
  combinedPage.value = 1
  if (showInternal.value) refreshInternal()
  if (showExternal.value && externalAll.value.length === 0) refreshExternal()
}

function handleClearSearch() {
  queryDraft.value = ''
  applySearch()
}

async function refreshAll() {
  const tasks: Promise<any>[] = []
  if (showInternal.value) tasks.push(refreshInternal())
  if (showExternal.value) tasks.push(refreshExternal())
  await Promise.all(tasks)
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
  } catch (error) {
    ElMessage.error('获取本站资源失败')
  } finally {
    loading.value = false
  }
}

function externalPreviewUrl(f: MeLoveallFileInfo) {
  // Prefer the API preview endpoint because it URL-encodes filenames and is less likely
  // to be blocked by hotlink rules on static preview paths.
  return meLoveallPreviewUrl(f.full_name)
}

function externalDownloadUrl(f: MeLoveallFileInfo) {
  return resolveExternalUrl(f.download_url) || meLoveallDownloadUrl(f.full_name)
}

function markExternalPreviewBroken(fileName: string) {
  if (!fileName) return
  if (brokenExternalPreviews.value[fileName]) return
  brokenExternalPreviews.value = { ...brokenExternalPreviews.value, [fileName]: true }
}

async function refreshExternal() {
  externalLoading.value = true
  try {
    const r = await listMeLoveallResources()
    externalAll.value = r.files || []
    brokenExternalPreviews.value = {}
  } catch (e: any) {
    const msg = String(e?.message || '外站列表获取失败')
    if (msg.toLowerCase().includes('network')) {
      ElMessage.error('外站网络错误：请检查代理/防火墙或外站服务状态')
    } else {
      ElMessage.error(msg)
    }
  } finally {
    externalLoading.value = false
  }
}

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString()
}

function goExternalDetail(fileName: string) {
  router.push({ name: 'external-resource', query: { file: fileName } })
}

function openExternalDownload(href: string) {
  if (!href) return
  window.open(href, '_blank', 'noopener,noreferrer')
}

function openExternalPreview(href: string) {
  if (!href) return
  window.open(href, '_blank', 'noopener,noreferrer')
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

watch(sourceFilter, () => {
  combinedPage.value = 1
  if (showInternal.value && items.value.length === 0) refreshInternal()
  if (showExternal.value && externalAll.value.length === 0) refreshExternal()
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
  box-shadow: 0 0 0 1px #e2e8f0 inset;
  border-radius: 10px;
  padding: 8px 12px;
  background-color: #f8fafc;
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px var(--el-color-success) inset;
  background-color: #fff;
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

.source-switch {
  display: flex;
  justify-content: center;
  margin: 0 0 22px 0;
}

.source-switch-group :deep(.el-radio-button__inner) {
  padding: 10px 18px;
  border-radius: 12px;
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

.external-muted {
  color: #64748b;
}


.resource-card.external-card {
  border-color: rgba(99, 102, 241, 0.18);
}

.resource-card.external-card:hover {
  border-color: rgba(99, 102, 241, 0.35);
  box-shadow: 0 22px 44px -14px rgba(79, 70, 229, 0.18);
}

.card-icon.external-cover {
  background: radial-gradient(120px 120px at 30% 30%, rgba(99, 102, 241, 0.55), rgba(15, 23, 42, 1));
  color: #e0e7ff;
  position: relative;
}

.external-cover-empty {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 44px;
  opacity: 0.85;
}

.external-badge {
  position: absolute;
  left: 10px;
  top: 10px;
  padding: 4px 10px;
  font-size: 12px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.65);
  color: #e0e7ff;
  border: 1px solid rgba(224, 231, 255, 0.22);
  backdrop-filter: blur(6px);
}

.external-domain {
  font-size: 12px;
  color: #4f46e5;
  background: rgba(79, 70, 229, 0.08);
  border: 1px solid rgba(79, 70, 229, 0.18);
  padding: 3px 10px;
  border-radius: 999px;
  white-space: nowrap;
}

.external-size {
  font-size: 12px;
  color: #0f172a;
  background: rgba(15, 23, 42, 0.04);
  border: 1px solid rgba(15, 23, 42, 0.08);
  padding: 3px 10px;
  border-radius: 999px;
}

.external-mini-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
  margin-left: auto;
}

.resource-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
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
  .library-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 20px;
  }
  
  .header-actions {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-input {
    width: 100%;
  }
  
  .search-input:focus-within {
    width: 100%;
  }
}
</style>
