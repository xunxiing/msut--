<template>
  <div class="resource-editor">
    <el-form :model="form" label-position="top" @submit.prevent>
      <el-form-item label="作品名称" v-if="showTitle">
        <el-input v-model="form.title" maxlength="80" show-word-limit :size="size" />
      </el-form-item>
      <el-form-item label="简介">
        <el-input v-model="form.description" type="textarea" :rows="2" maxlength="300" show-word-limit />
      </el-form-item>
      <el-form-item label="使用方法">
        <el-input v-model="form.usage" type="textarea" :rows="rows" placeholder="安装步骤、使用说明" />
      </el-form-item>
      <div class="ai-bar" v-if="showAI">
        <el-button :loading="aiLoading" @click="onAIOptimize" type="success" plain round :size="size">
          <el-icon class="el-icon--left"><MagicStick /></el-icon>
          AI 优化
        </el-button>
        <span v-if="aiTags.length" class="ai-tags">
          <el-tag v-for="t in aiTags" :key="t" size="small" effect="plain" round>{{ t }}</el-tag>
        </span>
      </div>
    </el-form>

    <el-divider content-position="left" v-if="files.length">已有文件 ({{ files.length }})</el-divider>
    <div v-if="files.length" class="file-list">
      <div v-for="f in files" :key="f.id" class="file-item">
        <el-icon class="file-icon"><Document /></el-icon>
        <span class="file-name" :title="f.original_name">{{ f.original_name }}</span>
        <span class="file-size">{{ formatSize(f.size) }}</span>
        <el-button text circle size="small" @click="$emit('download', f)"><el-icon><Download /></el-icon></el-button>
        <el-button text circle size="small" @click="$emit('removeFile', f)" style="color: var(--el-color-danger)"><el-icon><Delete /></el-icon></el-button>
      </div>
    </div>

    <el-divider content-position="left">添加文件</el-divider>
    <el-upload
      ref="uploadRef"
      v-model:file-list="newFiles"
      :with-credentials="true"
      :multiple="true"
      :auto-upload="false"
      :limit="10"
      name="files"
      drag
    >
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div class="el-upload__text">拖拽或<em>点击选择</em></div>
      <template #tip><div class="el-upload__tip">最多 10 个，单个不超过 50MB</div></template>
    </el-upload>

    <el-divider content-position="left">封面 / 图片</el-divider>
    <div v-if="images.length" class="cover-grid">
      <div v-for="img in images" :key="img.id" class="cover-item" :class="{ 'is-cover': img.id === coverFileId }" @click="$emit('setCover', img.id)">
        <img :src="toImageUrl(img.url_path)" :alt="img.original_name" class="cover-thumb" />
        <span v-if="img.id === coverFileId" class="cover-badge">封面</span>
      </div>
    </div>
    <el-upload
      ref="coverRef"
      v-model:file-list="newImages"
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
</template>

<script setup lang="ts">
import { ref, watch, type PropType } from 'vue'
import type { UploadInstance, UploadUserFile } from 'element-plus'
import { ElMessage } from 'element-plus'
import { optimizeContent, type ResourceFile } from '../api/resources'
import { UploadFilled, MagicStick, Plus, Document, Download, Delete } from '@element-plus/icons-vue'

const props = defineProps({
  title: { type: String, default: '' },
  description: { type: String, default: '' },
  usage: { type: String, default: '' },
  files: { type: Array as PropType<ResourceFile[]>, default: () => [] },
  images: { type: Array as PropType<ResourceFile[]>, default: () => [] },
  coverFileId: { type: Number as PropType<number | null>, default: null },
  showTitle: { type: Boolean, default: true },
  showAI: { type: Boolean, default: true },
  size: { type: String as PropType<'default' | 'small' | 'large'>, default: 'default' },
  rows: { type: Number, default: 4 },
})

const emit = defineEmits<{
  (e: 'update:title', v: string): void
  (e: 'update:description', v: string): void
  (e: 'update:usage', v: string): void
  (e: 'download', f: ResourceFile): void
  (e: 'removeFile', f: ResourceFile): void
  (e: 'setCover', id: number): void
  (e: 'newFiles', files: UploadUserFile[]): void
  (e: 'newImages', files: UploadUserFile[]): void
}>()

const form = ref({
  title: props.title,
  description: props.description,
  usage: props.usage,
})

watch(() => props.title, (v) => { if (v !== form.value.title) form.value.title = v })
watch(() => props.description, (v) => { if (v !== form.value.description) form.value.description = v })
watch(() => props.usage, (v) => { if (v !== form.value.usage) form.value.usage = v })

watch(() => form.value.title, (v) => emit('update:title', v))
watch(() => form.value.description, (v) => emit('update:description', v))
watch(() => form.value.usage, (v) => emit('update:usage', v))

const newFiles = ref<UploadUserFile[]>([])
const newImages = ref<UploadUserFile[]>([])
const uploadRef = ref<UploadInstance>()
const coverRef = ref<UploadInstance>()
const aiLoading = ref(false)
const aiTags = ref<string[]>([])

watch(newFiles, (v) => emit('newFiles', v), { deep: true })
watch(newImages, (v) => emit('newImages', v), { deep: true })

async function onAIOptimize() {
  if (!form.value.title.trim()) { ElMessage.warning('请先输入标题'); return }
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
    ElMessage.success('已优化内容')
  } catch (e: any) { ElMessage.error(e?.response?.data?.error || 'AI 优化失败') }
  finally { aiLoading.value = false }
}

function toImageUrl(path?: string | null) {
  if (!path) return ''
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  if (path.startsWith('/uploads/')) return path
  return path
}

function formatSize(bytes: number) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}

defineExpose({
  getNewFiles: () => newFiles.value,
  getNewImages: () => newImages.value,
  clearNewFiles: () => { newFiles.value = [] },
  clearNewImages: () => { newImages.value = [] },
  abortAll: () => {
    if (uploadRef.value) newFiles.value.forEach((f) => { if ((f as any).status === 'uploading') uploadRef.value!.abort(f as any) })
    if (coverRef.value) newImages.value.forEach((f) => { if ((f as any).status === 'uploading') coverRef.value!.abort(f as any) })
  },
})
</script>

<style scoped>
.resource-editor { padding: 0 4px; }
.ai-bar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
.ai-tags { display: flex; gap: 4px; flex-wrap: wrap; }

.file-list { display: flex; flex-direction: column; gap: 8px; }
.file-item { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 8px; background: var(--el-fill-color-light); }
.file-icon { color: var(--el-text-color-secondary); flex-shrink: 0; }
.file-name { flex: 1; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-size { font-size: 12px; color: var(--el-text-color-placeholder); flex-shrink: 0; }

.cover-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 8px; margin-bottom: 12px; }
.cover-item { position: relative; border-radius: 8px; overflow: hidden; border: 2px solid transparent; cursor: pointer; transition: all 0.2s; aspect-ratio: 1; }
.cover-item:hover { transform: scale(1.02); }
.cover-item.is-cover { border-color: var(--el-color-primary); }
.cover-thumb { width: 100%; height: 100%; object-fit: cover; }
.cover-badge { position: absolute; bottom: 4px; left: 4px; font-size: 10px; background: var(--el-color-primary); color: white; padding: 1px 6px; border-radius: 999px; }
</style>
