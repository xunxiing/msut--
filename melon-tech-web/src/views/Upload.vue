<template>
  <div class="upload-page">
    <div class="upload-header">
      <h1>上传作品</h1>
      <p>填写信息、选择文件，一键发布</p>
    </div>

    <div class="upload-body">
      <!-- 左侧：表单 -->
      <div class="form-section">
        <el-form :model="form" :rules="rules" ref="formRef" label-position="top" @submit.prevent>
          <el-form-item label="作品名称" prop="title">
            <el-input v-model="form.title" maxlength="80" show-word-limit placeholder="例：歼-10C 战斗机" size="large" />
          </el-form-item>

          <el-form-item label="简介">
            <el-input v-model="form.description" type="textarea" :rows="2" maxlength="300" show-word-limit placeholder="一句话概括你的作品亮点" />
          </el-form-item>

          <el-form-item label="使用方法">
            <el-input v-model="form.usage" type="textarea" :rows="3" placeholder="安装步骤、使用说明，让用户快速上手" />
          </el-form-item>

          <div class="ai-bar">
            <el-button :loading="aiLoading" @click="onAIOptimize" type="success" plain round>
              <el-icon class="el-icon--left"><MagicStick /></el-icon>
              AI 优化内容
            </el-button>
            <span v-if="aiTags.length" class="ai-tags">
              建议标签：
              <el-tag v-for="t in aiTags" :key="t" size="small" effect="plain" round>{{ t }}</el-tag>
            </span>
          </div>

          <el-divider />

          <el-form-item label="存档文件">
            <div class="upload-zone">
              <el-upload
                ref="fileUploadRef"
                v-model:file-list="fileList"
                :with-credentials="true"
                :multiple="true"
                :auto-upload="false"
                :limit="10"
                name="files"
                drag
              >
                <el-icon class="upload-icon"><UploadFilled /></el-icon>
                <div class="upload-text">拖拽存档文件到此处，或<em>点击选择</em></div>
                <div class="upload-hint">最多 10 个文件，单个不超过 50MB</div>
              </el-upload>
            </div>
          </el-form-item>

          <el-form-item label="封面 / 展示图片（可选）">
            <div class="upload-zone">
              <el-upload
                ref="coverUploadRef"
                v-model:file-list="coverFileList"
                :with-credentials="true"
                :multiple="true"
                :auto-upload="false"
                :limit="10"
                name="files"
                accept="image/*"
                list-type="picture-card"
              >
                <el-icon><Plus /></el-icon>
              </el-upload>
            </div>
          </el-form-item>

          <el-form-item>
            <el-checkbox v-model="saveWatermark">保存 .melsave 水印（便于后续检测匹配）</el-checkbox>
          </el-form-item>
        </el-form>
      </div>

      <!-- 右侧：预览/提交 -->
      <div class="side-section">
        <el-card shadow="never" class="preview-card">
          <template #header><span class="preview-title">预览</span></template>
          <div class="preview-content">
            <div class="preview-cover">
              <img v-if="coverPreview" :src="coverPreview" alt="cover" />
              <div v-else class="preview-cover-placeholder">
                <el-icon size="32"><Picture /></el-icon>
              </div>
            </div>
            <h3 class="preview-resource-title">{{ form.title || '未命名作品' }}</h3>
            <p class="preview-desc">{{ form.description || '暂无简介' }}</p>
            <div class="preview-meta">
              <span>{{ fileList.length }} 个文件</span>
              <span v-if="coverFileList.length">{{ coverFileList.length }} 张图片</span>
            </div>
          </div>
        </el-card>

        <el-button type="primary" @click="onSubmit" :loading="submitting" size="large" round class="submit-btn">
          {{ submitting ? '上传中…' : '发布作品' }}
        </el-button>
        <el-button @click="$router.back()" size="large" round plain class="cancel-btn">取消</el-button>
      </div>
    </div>

    <!-- 成功弹窗 -->
    <el-dialog v-model="successVisible" width="440px" center :show-close="false" :close-on-click-modal="false">
      <div class="success-dialog">
        <el-icon size="48" color="#67c23a"><CircleCheckFilled /></el-icon>
        <h2>发布成功</h2>
        <p>你的作品已上线，分享链接已生成</p>
        <el-input v-model="shareUrl" readonly class="share-input" />
        <div class="success-actions">
          <el-button type="primary" @click="copy(shareUrl)" round>复制链接</el-button>
          <el-button @click="goDetail" round>查看作品</el-button>
          <el-button @click="reset" round plain>继续上传</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount } from 'vue'
import { onBeforeRouteLeave, useRouter } from 'vue-router'
import type { FormInstance, FormRules, UploadInstance, UploadUserFile } from 'element-plus'
import { ElMessage } from 'element-plus'
import { createResource, optimizeContent, classifyResource } from '../api/resources'
import { http } from '../api/http'
import { UploadFilled, MagicStick, Plus, Picture, CircleCheckFilled } from '@element-plus/icons-vue'

const router = useRouter()
const formRef = ref<FormInstance>()
const fileUploadRef = ref<UploadInstance>()
const coverUploadRef = ref<UploadInstance>()

const submitting = ref(false)
const aiLoading = ref(false)
const aiTags = ref<string[]>([])
const successVisible = ref(false)

const form = ref({ title: '', description: '', usage: '' })
const rules: FormRules = {
  title: [{ required: true, message: '请输入作品名称', trigger: 'blur' }],
}

const fileList = ref<UploadUserFile[]>([])
const coverFileList = ref<UploadUserFile[]>([])
const saveWatermark = ref(false)

const slug = ref('')
const shareUrl = ref('')

const coverPreview = computed(() => {
  const first = coverFileList.value[0]
  if (!first) return ''
  return (first as any).url || ''
})

async function onAIOptimize() {
  if (!form.value.title.trim()) {
    ElMessage.warning('请先输入作品名称')
    return
  }
  aiLoading.value = true
  try {
    const result = await optimizeContent({
      title: form.value.title,
      description: form.value.description,
      usage: form.value.usage,
    })
    form.value.title = result.title
    form.value.description = result.description
    form.value.usage = result.usage
    aiTags.value = result.tags || []
    if (aiTags.value.length) {
      ElMessage.success(`已优化，建议标签：${aiTags.value.join('、')}`)
    } else {
      ElMessage.success('已优化内容')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.error || 'AI 优化失败')
  } finally {
    aiLoading.value = false
  }
}

async function onSubmit() {
  await formRef.value?.validate()
  if (!fileList.value.length) {
    ElMessage.warning('请至少选择一个存档文件')
    return
  }
  submitting.value = true
  try {
    const res = await createResource(form.value)
    const resourceId = res.id
    slug.value = res.slug
    shareUrl.value = res.shareUrl

    const fd = new FormData()
    fd.append('resourceId', String(resourceId))
    fd.append('saveWatermark', String(saveWatermark.value))
    for (const f of fileList.value) {
      const raw = (f as any).raw
      if (raw) fd.append('files', raw)
    }
    await http.post('/files/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } })

    if (coverFileList.value.length) {
      const cfd = new FormData()
      for (const f of coverFileList.value) {
        const raw = (f as any).raw
        if (raw) cfd.append('files', raw)
      }
      await http.post(`/resources/${resourceId}/images/upload`, cfd, { headers: { 'Content-Type': 'multipart/form-data' } })
    }

    if (aiTags.value.length) {
      await classifyResource(resourceId).catch(() => {})
    }

    successVisible.value = true
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.error || '上传失败，请重试')
  } finally {
    submitting.value = false
  }
}

async function copy(text: string) {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.cssText = 'position:fixed;left:-9999px'
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    ElMessage.success('已复制')
  }
}

function goDetail() {
  successVisible.value = false
  router.push(`/share/${slug.value}`)
}

function reset() {
  successVisible.value = false
  form.value = { title: '', description: '', usage: '' }
  fileList.value = []
  coverFileList.value = []
  aiTags.value = []
  saveWatermark.value = false
  slug.value = ''
  shareUrl.value = ''
}

function abortAllUploads() {
  if (fileUploadRef.value) {
    fileList.value.forEach((f) => {
      if (f.status === 'uploading') fileUploadRef.value!.abort(f as any)
    })
  }
  if (coverUploadRef.value) {
    coverFileList.value.forEach((f) => {
      if (f.status === 'uploading') coverUploadRef.value!.abort(f as any)
    })
  }
}
onBeforeRouteLeave(() => abortAllUploads())
onBeforeUnmount(() => abortAllUploads())
</script>

<style scoped>
.upload-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px 16px 48px;
}

.upload-header {
  text-align: center;
  margin-bottom: 28px;
}
.upload-header h1 {
  font-size: 26px;
  font-weight: 700;
  margin: 0 0 6px;
}
.upload-header p {
  color: var(--el-text-color-secondary);
  font-size: 14px;
  margin: 0;
}

.upload-body {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}
.form-section {
  flex: 1;
  min-width: 0;
}
.side-section {
  width: 280px;
  flex-shrink: 0;
  position: sticky;
  top: 16px;
}

.ai-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.ai-tags {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.upload-zone :deep(.el-upload-dragger) {
  width: 100%;
}

.preview-card {
  border-radius: 12px;
  margin-bottom: 16px;
}
.preview-title {
  font-weight: 600;
}
.preview-content {
  text-align: center;
}
.preview-cover {
  width: 100%;
  aspect-ratio: 16/9;
  border-radius: 8px;
  overflow: hidden;
  background: var(--el-fill-color-light);
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.preview-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.preview-cover-placeholder {
  color: var(--el-text-color-placeholder);
}
.preview-resource-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.preview-desc {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin: 0 0 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.preview-meta {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  display: flex;
  gap: 8px;
  justify-content: center;
}

.submit-btn {
  width: 100%;
  margin-bottom: 8px;
}
.cancel-btn {
  width: 100%;
}

.success-dialog {
  text-align: center;
  padding: 8px 0;
}
.success-dialog h2 {
  font-size: 20px;
  margin: 12px 0 4px;
}
.success-dialog p {
  color: var(--el-text-color-secondary);
  font-size: 14px;
  margin: 0 0 16px;
}
.share-input {
  margin-bottom: 20px;
}
.success-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .upload-body {
    flex-direction: column;
  }
  .side-section {
    width: 100%;
    position: static;
    order: -1;
  }
  .preview-card {
    margin-bottom: 12px;
  }
}
</style>
