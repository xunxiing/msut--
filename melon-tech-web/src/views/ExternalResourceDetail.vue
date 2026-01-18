<template>
  <div class="resource-detail-container">
    <div class="breadcrumb-wrapper">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/resources' }">资源库</el-breadcrumb-item>
        <el-breadcrumb-item>外站资源</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <div v-if="loading" class="loading-skeleton">
      <el-skeleton animated :rows="6" />
    </div>

    <div v-else-if="error" class="error-card">
      <el-alert :title="error" type="error" show-icon />
    </div>

    <div v-else-if="info" class="detail-header-card">
      <div class="header-main">
        <div class="icon-wrapper">
          <el-icon><Link /></el-icon>
        </div>
        <div class="header-info">
          <h1 class="resource-title">{{ info.name || info.full_name }}</h1>
          <p class="resource-desc">来源：me.loveall.icu（外站直连，不经过本站文件 API）</p>
          <div class="header-meta">
            <span class="meta-item">
              <el-icon><Calendar /></el-icon>
              {{ info.date || '-' }}
            </span>
            <span class="meta-item">
              <el-icon><Document /></el-icon>
              {{ prettySize(info.size_bytes) }}
            </span>
          </div>
        </div>
      </div>

      <div class="header-actions">
        <div class="share-box">
          <el-input v-model="shareUrl" readonly class="share-input">
            <template #append>
              <el-button @click="copy(shareUrl)">
                <el-icon><CopyDocument /></el-icon>
                复制链接
              </el-button>
            </template>
          </el-input>
        </div>

        <div class="action-buttons">
          <el-button type="primary" class="download-btn-large" @click="openExternalDownload(downloadHref)">
            <el-icon><Download /></el-icon>
            下载（外站）
          </el-button>
        </div>
      </div>
    </div>

    <div v-if="info" class="detail-content">
      <el-row :gutter="24" class="top-row">
        <el-col :xs="24" :md="16">
          <div class="files-section">
            <h3 class="section-title">文件信息</h3>
            <div class="file-list">
              <div class="file-item">
                <div class="file-info-row">
                  <div class="file-icon">
                    <el-icon><Paperclip /></el-icon>
                  </div>
                  <div class="file-info">
                    <div class="file-name" :title="info.full_name">{{ info.full_name }}</div>
                    <div class="file-meta">{{ prettySize(info.size_bytes) }} · ZIP</div>
                  </div>
                </div>
                <el-button class="download-btn-large" @click="openExternalDownload(downloadHref)">下载</el-button>
              </div>
            </div>
          </div>
        </el-col>

        <el-col :xs="24" :md="8">
          <div class="images-section">
            <h3 class="section-title">预览图</h3>
            <div v-if="previewSrc" class="images-content">
              <div class="cover-preview">
                <img :src="previewSrc" alt="预览图" class="cover-image" loading="lazy" />
                <span class="cover-badge">外站预览</span>
              </div>
            </div>
            <div v-else class="no-files-placeholder">暂无预览图</div>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Calendar, CopyDocument, Document, Download, Link, Paperclip } from '@element-plus/icons-vue'
import {
  getMeLoveallResourceInfo,
  meLoveallDownloadUrl,
  meLoveallPreviewUrl,
  type MeLoveallFileInfo,
} from '../api/meLoveall'

const route = useRoute()

const loading = ref(false)
const error = ref('')
const info = ref<MeLoveallFileInfo | null>(null)

const fileName = computed(() => String(route.query.file || '').trim())
const shareUrl = ref('')

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

const previewSrc = computed(() => {
  if (!info.value) return ''
  return resolveExternalUrl(info.value.preview_url) || meLoveallPreviewUrl(info.value.full_name)
})

const downloadHref = computed(() => {
  if (!info.value) return ''
  return resolveExternalUrl(info.value.download_url) || meLoveallDownloadUrl(info.value.full_name)
})

function openExternalDownload(href: string) {
  if (!href) return
  window.open(href, '_blank', 'noopener,noreferrer')
}

function copy(text: string) {
  navigator.clipboard
    .writeText(text)
    .then(() => ElMessage.success('链接已复制'))
    .catch(() => ElMessage.error('复制失败'))
}

async function fetchInfo() {
  error.value = ''
  info.value = null

  if (!fileName.value) {
    error.value = '缺少 file 参数（示例：/external?file=资源.zip）'
    return
  }

  loading.value = true
  try {
    info.value = await getMeLoveallResourceInfo(fileName.value)
    shareUrl.value = window.location.href
  } catch (e: any) {
    error.value = e?.message || '加载外站资源失败'
  } finally {
    loading.value = false
  }
}

onMounted(fetchInfo)
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
  background: #eef2ff;
  color: #6366f1;
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

.detail-content {
  min-height: 200px;
}

.files-section,
.images-section {
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

.file-info-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.file-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #eef2ff;
  color: #6366f1;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-meta {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 2px;
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
  max-height: 260px;
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

.no-files-placeholder {
  color: #94a3b8;
  font-size: 14px;
  padding: 12px 0;
}

.error-card {
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  border: 1px solid #fee2e2;
}
</style>

