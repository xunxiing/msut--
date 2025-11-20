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
          v-model="q"
          placeholder="搜索资源..."
          class="search-input"
          clearable
          @clear="fetch"
          @keyup.enter="fetch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" class="upload-btn" @click="$router.push('/upload')">
          <el-icon><Upload /></el-icon>
          <span>上传文件</span>
        </el-button>
      </div>
    </div>

    <!-- Content Section -->
    <div class="library-content" v-loading="loading">
      <div v-if="items.length > 0" class="resource-grid">
        <div
          v-for="r in items"
          :key="r.id"
          class="resource-card-wrapper"
          @click="$router.push(`/share/${r.slug}`)"
        >
          <el-card class="resource-card" shadow="hover">
            <div class="card-body">
              <div class="card-icon">
                <el-icon><Document /></el-icon>
              </div>
              <div class="card-info">
                <h3 class="resource-title" :title="r.title">{{ r.title }}</h3>
                <p class="resource-desc">{{ r.description || '暂无描述' }}</p>
              </div>
            </div>
            <div class="card-footer">
              <div class="author-info">
                <el-avatar :size="24" class="author-avatar">{{ (r as any).author_name?.[0]?.toUpperCase() || 'U' }}</el-avatar>
                <span class="author-name">{{ (r as any).author_name || 'Unknown' }}</span>
              </div>
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
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Upload, Document, Star, StarFilled } from '@element-plus/icons-vue'
import { listResources, type ResourceItem } from '../api/resources'
import { getResourceLikes, likeResource, unlikeResource, type LikeInfo } from '../api/likes'
import { useAuth } from '../stores/auth'

const q = ref('')
const items = ref<ResourceItem[]>([])
const page = ref(1)
const pageSize = ref(12)
const total = ref(0)
const loading = ref(false)
const likesMap = ref<Record<number, LikeInfo>>({})
const auth = useAuth()

async function fetch() {
  loading.value = true
  try {
    const data = await listResources({ q: q.value, page: page.value, pageSize: pageSize.value })
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

function handlePageChange(p: number) {
  page.value = p
  fetch()
  window.scrollTo({ top: 0, behavior: 'smooth' })
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

onMounted(fetch)
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

.resource-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 24px;
}

.resource-card-wrapper {
  height: 100%;
}

.resource-card {
  height: 100%;
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
  padding: 24px;
}

.card-body {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  flex: 1;
}

.card-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: #ecfdf5;
  color: #10b981;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  flex-shrink: 0;
  transition: transform 0.3s ease;
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
  justify-content: center;
}

.resource-title {
  font-size: 17px;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 6px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 20px;
  border-top: 1px solid #f1f5f9;
  margin-top: auto;
}

.author-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.author-avatar {
  background: #f1f5f9;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px #e2e8f0;
}

.author-name {
  font-size: 13px;
  font-weight: 500;
  color: #475569;
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
