<template>
  <div class="resource-detail-container" v-if="data">
    <div class="breadcrumb-wrapper">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/resources' }">文件资源库</el-breadcrumb-item>
        <el-breadcrumb-item>{{ data.title }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <div class="detail-header-card">
      <div class="header-main">
        <div class="icon-wrapper">
          <el-icon><Document /></el-icon>
        </div>
        <div class="header-info">
          <h1 class="resource-title">{{ data.title }}</h1>
          <p class="resource-desc" v-if="data.description">{{ data.description }}</p>
          <div class="header-meta">
            <span class="meta-item">
              <el-icon><User /></el-icon>
              {{ (data as any).author_name || '未知作者' }}
            </span>
            <span class="meta-item">
              <el-icon><Calendar /></el-icon>
              {{ data.created_at }}
            </span>
          </div>
        </div>
      </div>

      <div class="header-actions">
        <div class="share-box">
          <el-input v-model="data.shareUrl" readonly class="share-input">
            <template #append>
              <el-button @click="copy(data.shareUrl)">
                <el-icon><CopyDocument /></el-icon>
                复制链接
              </el-button>
            </template>
          </el-input>
        </div>
        
        <div class="action-buttons">
          <button 
            class="like-btn-large" 
            :class="{ 'is-active': resourceLike?.liked }" 
            @click="toggleResourceLike"
          >
            <el-icon class="like-icon">
              <component :is="resourceLike?.liked ? StarFilled : Star" />
            </el-icon>
            <span class="like-text">{{ resourceLike?.liked ? '已收藏' : '收藏' }}</span>
            <span class="like-count" v-if="resourceLike?.likes">{{ resourceLike?.likes }}</span>
          </button>
        </div>
      </div>
    </div>

    <div class="detail-content">
      <el-row :gutter="24" class="top-row">
        <el-col :xs="24" :md="16">
          <div class="files-section">
            <h3 class="section-title">包含文件</h3>
            <div v-if="data.files?.length" class="file-list">
              <div v-for="f in data.files" :key="f.id" class="file-item">
                <div class="file-info-row">
                  <div class="file-icon">
                    <el-icon><Paperclip /></el-icon>
                  </div>
                  <div class="file-info">
                    <div class="file-name" :title="f.original_name">{{ f.original_name }}</div>
                    <div class="file-meta">{{ prettySize(f.size) }} · {{ f.mime || 'unknown' }}</div>
                  </div>
                </div>
                <DownloadButton
                  :href="`/api/files/${f.id}/download`"
                  :download-name="f.original_name"
                  class="download-btn-large"
                  type="primary"
                  @downloaded="handleFileDownloaded"
                >
                  <el-icon><Download /></el-icon>
                  下载
                </DownloadButton>
              </div>
            </div>
            <div v-else class="no-files-placeholder">暂无文件</div>
          </div>

          <div class="content-section">
            <h3 class="section-title">使用说明</h3>
            <div class="usage-content" v-if="data.usage">
              {{ data.usage }}
            </div>
            <div v-else class="no-files-placeholder">暂无使用说明</div>
          </div>
        </el-col>

        <el-col :xs="24" :md="8">
          <div class="images-section">
            <h3 class="section-title">封面与图片</h3>
            <div v-if="coverImageUrl || galleryImages.length" class="images-content">
              <div v-if="coverImageUrl" class="cover-preview">
                <img :src="coverImageUrl" alt="封面图片" class="cover-image" loading="lazy" />
                <span class="cover-badge">封面</span>
              </div>
              <div v-if="galleryImages.length" class="image-gallery">
                <div
                  v-for="img in galleryImages"
                  :key="img.id"
                  class="image-thumb"
                >
                  <img
                    :src="toImageUrl(img.url_path)"
                    :alt="img.original_name"
                    loading="lazy"
                  />
                </div>
              </div>
            </div>
            <div v-else class="no-files-placeholder">暂无图片</div>
          </div>
          
          <div class="download-tip">
            <el-icon><InfoFilled /></el-icon>
            <div class="tip-content">
              <h4>未登录也能下载</h4>
              <p>分享给任何人，对方打开此页即可自由下载</p>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>

  <!-- Like Popup -->
  <transition name="fade">
    <div v-if="showLikePopup" class="like-popup-overlay">
      <div class="like-popup">
        <div class="popup-content">
          <h3>觉得有用吗？</h3>
          <p>给作者点个赞支持一下吧！</p>
          <button 
            class="popup-like-btn"
            :class="{ 'is-active': resourceLike?.liked }"
            @click="handlePopupLike"
          >
            <el-icon><component :is="resourceLike?.liked ? StarFilled : Star" /></el-icon>
            {{ resourceLike?.liked ? '已点赞' : '点赞支持' }}
          </button>
        </div>
        <button class="close-popup" @click="showLikePopup = false">×</button>
        <div class="auto-close-bar"></div>
      </div>
    </div>
  </transition>

  <div v-if="!data" class="loading-skeleton">
    <el-skeleton animated :rows="6" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getResource, type ResourceFile, type ResourceItem } from '../api/resources'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getResourceLikes, likeResource, unlikeResource, type LikeInfo } from '../api/likes'
import { useAuth } from '../stores/auth'
import { 
  Document, User, Calendar, CopyDocument, 
  Star, StarFilled, Paperclip, Download, InfoFilled 
} from '@element-plus/icons-vue'
import DownloadButton from '../components/DownloadButton.vue'

const route = useRoute()
const data = ref<ResourceItem | null>(null)
const auth = useAuth()
const resourceLike = ref<LikeInfo | null>(null)
const showLikePopup = ref(false)
let popupTimer: any = null
const imageFiles = ref<ResourceFile[]>([])

function toImageUrl(path?: string | null) {
  if (!path) return ''
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  if (path.startsWith('/uploads/')) return path
  return path
}

const coverImageUrl = computed(() => {
  const detail = data.value as any
  if (!detail) return ''
  if (detail.coverUrlPath) {
    return toImageUrl(detail.coverUrlPath as string)
  }
  const coverId = detail.coverFileId ?? null
  if (coverId) {
    const cover = imageFiles.value.find(img => img.id === coverId)
    if (cover) return toImageUrl(cover.url_path)
  }
  const first = imageFiles.value[0]
  return first ? toImageUrl(first.url_path) : ''
})

const galleryImages = computed(() => {
  const detail = data.value as any
  const coverId = detail?.coverFileId ?? null
  if (!imageFiles.value.length) return []
  if (!coverId) return imageFiles.value
  return imageFiles.value.filter(img => img.id !== coverId)
})

function prettySize(n: number) {
  if (!n && n !== 0) return ''
  const units = ['B','KB','MB','GB']
  let i = 0; let v = n
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++ }
  return `${v.toFixed(1)} ${units[i]}`
}

async function fetch() {
  try {
    const detail = await getResource(route.params.slug as string)
    data.value = detail
    imageFiles.value = (detail.imageFiles || []) as ResourceFile[]
    if (detail?.id) {
      const items = await getResourceLikes([detail.id])
      resourceLike.value = items[0] || { id: detail.id, likes: 0, liked: false }
    }
  } catch (e) {
    ElMessage.error('加载资源失败')
  }
}

function copy(text: string) {
  navigator.clipboard.writeText(text).then(() => ElMessage.success('链接已复制'))
}

function handleFileDownloaded() {
  // Show like popup only if user hasn't liked the resource yet
  if (!resourceLike.value?.liked) {
    showLikePopup.value = true
    if (popupTimer) clearTimeout(popupTimer)
    popupTimer = setTimeout(() => {
      showLikePopup.value = false
    }, 3000)
  }
}

async function handlePopupLike() {
  await toggleResourceLike()
  // Close popup immediately after liking
  showLikePopup.value = false
  if (popupTimer) clearTimeout(popupTimer)
  // Don't auto close if user interacts, or maybe close after a short delay? 
  // Let's keep it simple: if they like, we can close it after a moment or let the timer handle it.
  // User requirement said "6 seconds auto disappear", so we stick to that timer mostly.
}

async function toggleResourceLike() {
  try {
    if (!auth.user) {
      ElMessage.warning('请先登录')
      return
    }
    const current = resourceLike.value
    if (!current) return
    if (current.liked) {
      const r = await unlikeResource(current.id)
      resourceLike.value = { id: current.id, likes: r.likes, liked: r.liked }
    } else {
      const r = await likeResource(current.id)
      resourceLike.value = { id: current.id, likes: r.likes, liked: r.liked }
    }
  } catch (e: any) {
    const msg = e?.response?.data?.error || '操作失败'
    ElMessage.error(msg)
  }
}

onMounted(fetch)
</script>

<style scoped>
.resource-detail-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 24px;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color: #1e293b;
}

.breadcrumb-wrapper {
  margin-bottom: 24px;
}

.detail-header-card {
  background: #fff;
  border-radius: 16px;
  padding: 32px;
  margin-bottom: 32px;
  border: 1px solid #f1f5f9;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 32px;
  flex-wrap: wrap;
}

.header-main {
  display: flex;
  gap: 24px;
  flex: 1;
  min-width: 300px;
}

.icon-wrapper {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  background: #ecfdf5;
  color: #10b981;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  flex-shrink: 0;
}

.header-info {
  flex: 1;
}

.resource-title {
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 12px 0;
  line-height: 1.3;
}

.resource-desc {
  font-size: 15px;
  color: #64748b;
  margin: 0 0 16px 0;
  line-height: 1.6;
}

.header-meta {
  display: flex;
  gap: 24px;
  color: #94a3b8;
  font-size: 14px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.header-actions {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 320px;
}

.share-input :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px #e2e8f0 inset;
}

.like-btn-large {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #64748b;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.like-btn-large:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.like-btn-large.is-active {
  background: #fee2e2;
  border-color: #fee2e2;
  color: #ef4444;
}

.like-icon {
  font-size: 18px;
}

.detail-content {
  min-height: 400px;
}

.content-section, .files-section, .images-section {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  border: 1px solid #f1f5f9;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
  margin-bottom: 24px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #0f172a;
  margin: 0 0 20px 0;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
}

.usage-content {
  font-size: 15px;
  line-height: 1.7;
  color: #334155;
  white-space: pre-wrap;
}

.images-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cover-preview {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  background: #0f172a;
}

.cover-image {
  width: 100%;
  max-height: 220px;
  object-fit: cover;
  display: block;
}

.cover-badge {
  position: absolute;
  left: 12px;
  top: 12px;
  padding: 4px 10px;
  font-size: 12px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.8);
  color: #e5e7eb;
}

.image-gallery {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.image-thumb {
  width: calc(50% - 4px);
  border-radius: 10px;
  overflow: hidden;
  background: #f1f5f9;
}

.image-thumb img {
  width: 100%;
  height: 80px;
  object-fit: cover;
  display: block;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #f1f5f9;
  transition: all 0.2s;
}

.file-item:hover {
  background: #fff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border-color: #e2e8f0;
}

.file-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: #e0f2fe;
  color: #0284c7;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.file-info {
  flex: 1;
  overflow: hidden;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  color: #334155;
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-meta {
  font-size: 12px;
  color: #94a3b8;
}

.download-tip {
  margin-top: 16px;
  padding: 16px;
  background: #f0f9ff;
  border-radius: 12px;
  display: flex;
  gap: 12px;
  color: #0369a1;
}

.download-tip .el-icon {
  font-size: 20px;
  margin-top: 2px;
}

.tip-content h4 {
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: 600;
}

.tip-content p {
  margin: 0;
  font-size: 13px;
  opacity: 0.9;
}

.no-files-placeholder {
  text-align: center;
  color: #94a3b8;
  font-size: 14px;
  padding: 20px 0;
}

.loading-skeleton {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px;
}

@media (max-width: 768px) {
  .detail-header-card {
    flex-direction: column;
    align-items: stretch;
  }
  
  .header-actions {
    width: 100%;
  }
}

.file-item {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid #f1f5f9;
  transition: all 0.2s;
}

.file-info-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.download-btn-large {
  width: 100%;
  height: 40px;
  font-size: 15px;
  border-radius: 8px;
  margin-top: 4px;
}

/* Popup Styles */
.like-popup-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  backdrop-filter: blur(2px);
}

.like-popup {
  background: #fff;
  padding: 32px;
  border-radius: 20px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15);
  width: 320px;
  text-align: center;
  position: relative;
  overflow: hidden;
  animation: popup-in 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

@keyframes popup-in {
  from { transform: scale(0.8); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.popup-content h3 {
  margin: 0 0 8px 0;
  font-size: 20px;
  color: #1e293b;
}

.popup-content p {
  margin: 0 0 24px 0;
  color: #64748b;
  font-size: 14px;
}

.popup-like-btn {
  background: linear-gradient(135deg, #312e81 0%, #4338ca 100%);
  color: #fff;
  border: none;
  padding: 12px 32px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s;
  box-shadow: 0 4px 12px rgba(67, 56, 202, 0.3);
}

.popup-like-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(67, 56, 202, 0.4);
}

.popup-like-btn.is-active {
  background: #f1f5f9;
  color: #64748b;
  box-shadow: none;
}

.close-popup {
  position: absolute;
  top: 12px;
  right: 12px;
  background: none;
  border: none;
  font-size: 24px;
  color: #94a3b8;
  cursor: pointer;
  padding: 4px;
  line-height: 1;
}

.close-popup:hover {
  color: #64748b;
}

.auto-close-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 4px;
  background: #4338ca;
  width: 100%;
  animation: progress 3s linear forwards;
}

@keyframes progress {
  from { width: 100%; }
  to { width: 0%; }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
