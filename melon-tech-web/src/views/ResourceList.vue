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
          v-model="searchModel"
          :placeholder="activeTab === 'internal' ? '搜索本站资源...' : '搜索外站资源（按名称/文件名）'"
          class="search-input"
          clearable
          @clear="handleSearch"
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button v-if="activeTab === 'internal'" type="primary" class="upload-btn" @click="$router.push('/upload')">
          <el-icon><Upload /></el-icon>
          <span>上传文件</span>
        </el-button>
        <el-button v-else class="refresh-btn" :loading="externalLoading" @click="refreshExternal">刷新外站</el-button>
      </div>
    </div>

    <!-- Content Section -->
    <div class="library-content" v-loading="activeTab === 'internal' && loading">
      <el-tabs v-model="activeTab" class="resource-tabs">
        <el-tab-pane label="本站资源" name="internal">
      <div v-if="items.length > 0" class="resource-grid">
        <div
          v-for="r in items"
          :key="r.id"
          class="resource-card-wrapper"
          @click="$router.push(`/share/${r.slug}`)"
        >
          <el-card class="resource-card" shadow="hover">
            <div class="card-body">
              <div class="card-icon" :class="{ 'has-cover': (r as any).coverUrlPath }">
                <template v-if="(r as any).coverUrlPath">
                  <img
                    class="card-cover-image"
                    :src="toImageUrl((r as any).coverUrlPath)"
                    alt="cover"
                    loading="lazy"
                  />
                </template>
                <template v-else>
                  <el-icon><Document /></el-icon>
                </template>
              </div>
              <div class="card-info">
                <div class="info-top">
                  <div class="title-row">
                    <h3 class="resource-title" :title="r.title">{{ r.title }}</h3>
                    <div class="author-info-mini">
                      <el-avatar :size="16" class="author-avatar">{{ (r as any).author_name?.[0]?.toUpperCase() || 'U' }}</el-avatar>
                      <span class="author-name">{{ (r as any).author_name || 'Unknown' }}</span>
                    </div>
                  </div>
                  <p class="resource-desc">{{ r.description || '暂无描述' }}</p>
                </div>
                <div class="info-bottom">
                  <div class="card-meta">
                    <span class="date">{{ formatDate(r.created_at) }}</span>
                    <div
                      class="like-action"
                      :class="{ 'is-active': likesMap[r.id]?.liked }"
                      @click.stop="toggleLike(r.id)"
                    >
                      <el-icon>
                        <component :is="likesMap[r.id]?.liked ? StarFilled : Star" />
                      </el-icon>
                      <span class="like-count">{{ likesMap[r.id]?.likes || 0 }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </el-card>
        </div>
      </div>

      <el-empty v-else description="暂无资源" :image-size="200" />

      <!-- Pagination -->
      <div class="pagination-wrapper" v-if="total > 0">
        <el-pagination
          background
          layout="prev, pager, next"
          :page-size="pageSize"
          :current-page="page"
          :total="total"
          @current-change="handlePageChange"
        />
      </div>
        </el-tab-pane>

        <el-tab-pane label="外站资源（me.loveall.icu）" name="external">
          <div class="external-box">
            <el-alert
              title="外站资源按日期倒序展示（最新在前）；下载/预览为外站直连，不会通过本站文件 API 转发。"
              type="info"
              show-icon
              :closable="false"
              class="external-alert"
            />

            <div class="external-toolbar">
              <div class="external-toolbar-left">
                <el-text class="external-muted">共 {{ externalTotal }} 个资源</el-text>
              </div>
              <div class="external-toolbar-right">
                <el-select v-model="externalPageSize" class="external-page-size">
                  <el-option :value="12" label="12/页" />
                  <el-option :value="24" label="24/页" />
                  <el-option :value="48" label="48/页" />
                </el-select>
              </div>
            </div>

            <div class="external-list" v-loading="externalLoading">
              <div v-if="externalPaged.length > 0" class="resource-grid">
                <div
                  v-for="f in externalPaged"
                  :key="f.full_name"
                  class="resource-card-wrapper"
                  @click="$router.push({ name: 'external-resource', query: { file: f.full_name } })"
                >
                  <el-card class="resource-card external-card" shadow="hover">
                    <div class="card-body">
                      <div class="card-icon has-cover external-cover">
                        <template v-if="externalPreviewUrl(f) && !brokenExternalPreviews[f.full_name]">
                          <img
                            class="card-cover-image"
                            :src="externalPreviewUrl(f)"
                            alt="preview"
                            loading="lazy"
                            referrerpolicy="no-referrer"
                            @error="markExternalPreviewBroken(f.full_name)"
                          />
                        </template>
                        <template v-else>
                          <div class="external-cover-empty">
                            <el-icon><Document /></el-icon>
                          </div>
                        </template>
                        <div class="external-badge">外站</div>
                      </div>
                      <div class="card-info">
                        <div class="info-top">
                          <div class="title-row">
                            <h3 class="resource-title" :title="f.name || f.full_name">{{ f.name || f.full_name }}</h3>
                            <div class="author-info-mini">
                              <span class="external-domain">me.loveall.icu</span>
                            </div>
                          </div>
                          <p class="resource-desc">{{ f.full_name }}</p>
                        </div>
                        <div class="info-bottom">
                          <div class="card-meta">
                            <span class="date">{{ f.date || '-' }}</span>
                            <span class="external-size">{{ f.size || prettySize(f.size_bytes) }}</span>
                            <div class="external-mini-actions" @click.stop>
                              <el-button size="small" @click="goExternalDetail(f.full_name)">详情</el-button>
                              <el-button size="small" type="primary" @click="openExternalDownload(externalDownloadUrl(f))">下载</el-button>
                              <el-button
                                v-if="externalPreviewUrl(f) && !brokenExternalPreviews[f.full_name]"
                                size="small"
                                @click="openExternalPreview(externalPreviewUrl(f))"
                              >
                                预览
                              </el-button>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </el-card>
                </div>
              </div>

              <el-empty v-else description="暂无外站资源（或被筛选隐藏）" :image-size="160" />

              <div class="pagination-wrapper" v-if="externalTotal > 0">
                <el-pagination
                  background
                  layout="prev, pager, next"
                  :page-size="externalPageSize"
                  :current-page="externalPage"
                  :total="externalTotal"
                  @current-change="handleExternalPageChange"
                />
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
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

const internalQ = ref('')
const externalQ = ref('')
const items = ref<ResourceItem[]>([])
const page = ref(1)
const pageSize = ref(12)
const total = ref(0)
const loading = ref(false)
const likesMap = ref<Record<number, LikeInfo>>({})
const auth = useAuth()
const router = useRouter()

const activeTab = ref<'internal' | 'external'>('internal')

const externalLoading = ref(false)
const externalAll = ref<MeLoveallFileInfo[]>([])
const externalPage = ref(1)
const externalPageSize = ref(24)
const brokenExternalPreviews = ref<Record<string, true>>({})

const searchModel = computed({
  get: () => (activeTab.value === 'internal' ? internalQ.value : externalQ.value),
  set: (v: string) => {
    if (activeTab.value === 'internal') internalQ.value = v
    else externalQ.value = v
  },
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

async function fetch() {
  loading.value = true
  try {
    const data = await listResources({ q: internalQ.value, page: page.value, pageSize: pageSize.value })
    items.value = data.items
    total.value = data.total
    
    if (items.value.length > 0) {
      const ids = items.value.map(r => r.id)
      const likes = await getResourceLikes(ids)
      const m: Record<number, LikeInfo> = {}
      likes.forEach(i => { m[i.id] = i })
      likesMap.value = m
    }
  } catch (error) {
    ElMessage.error('获取资源列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  if (activeTab.value === 'internal') {
    page.value = 1
    fetch()
    return
  }
  externalPage.value = 1
}

function handlePageChange(p: number) {
  page.value = p
  fetch()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function parseExternalDate(s: string) {
  const v = Date.parse(s)
  return Number.isFinite(v) ? v : 0
}

const externalFiltered = computed(() => {
  const q = externalQ.value.trim().toLowerCase()
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

const externalTotal = computed(() => externalFiltered.value.length)

const externalPaged = computed(() => {
  const start = (externalPage.value - 1) * externalPageSize.value
  return externalFiltered.value.slice(start, start + externalPageSize.value)
})

function handleExternalPageChange(p: number) {
  externalPage.value = p
  window.scrollTo({ top: 0, behavior: 'smooth' })
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
    externalPage.value = 1
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

watch(activeTab, (tab) => {
  if (tab === 'external' && externalAll.value.length === 0) {
    refreshExternal()
  }
})

watch([externalQ, externalPageSize], () => {
  if (activeTab.value === 'external') externalPage.value = 1
})

onMounted(() => {
  fetch()
  if (activeTab.value === 'external') refreshExternal()
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
  gap: 16px;
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
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2);
  transition: all 0.2s ease;
}

.upload-btn:hover {
  background-color: #059669;
  border-color: #059669;
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(16, 185, 129, 0.3);
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

.resource-tabs :deep(.el-tabs__header) {
  margin: 0 0 20px 0;
}

.external-box {
  max-width: 1280px;
  margin: 0 auto;
}

.external-alert {
  margin-bottom: 16px;
}

.external-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin: 0 0 14px 0;
}

.external-muted {
  color: #64748b;
}

.external-page-size {
  width: 110px;
}

.external-list {
  border-radius: 16px;
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
  height: 160px;
  border: 1px solid #f1f5f9;
  border-radius: 16px;
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
  border-color: rgba(16, 185, 129, 0.2);
}

.resource-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.card-body {
  display: flex;
  gap: 16px;
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
  gap: 16px;
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
