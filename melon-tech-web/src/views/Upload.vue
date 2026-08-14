<template>
  <div class="container">
    <el-card class="card">
      <template #header>
        <span style="font-weight:600;font-size:18px">上传作品</span>
      </template>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="96px" @submit.prevent>
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" maxlength="80" show-word-limit placeholder="给作品起个名字" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="form.description" type="textarea" :rows="3" maxlength="300" show-word-limit placeholder="一句话描述你的作品" />
        </el-form-item>
        <el-form-item label="使用方法">
          <el-input v-model="form.usage" type="textarea" :rows="4" placeholder="如何安装、如何使用，写清楚，减少问答" />
        </el-form-item>

        <el-form-item>
          <el-button :loading="aiLoading" @click="onAIOptimize" type="success" plain>
            <el-icon class="el-icon--left"><MagicStick /></el-icon>
            AI 一键优化
          </el-button>
        </el-form-item>

        <el-divider content-position="left">存档文件</el-divider>

        <el-form-item label="水印">
          <el-checkbox v-model="saveWatermark">保存 .melsave 水印到数据库（便于后续检测）</el-checkbox>
        </el-form-item>

        <el-upload
          ref="uploadRef"
          v-model:file-list="fileList"
          :with-credentials="true"
          :multiple="true"
          :auto-upload="false"
          :limit="10"
          name="files"
          drag
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">把存档文件拖到这里，或 <em>点击选择</em></div>
          <template #tip>
            <div class="el-upload__tip">支持最多 10 个文件，单文件不超过 50MB</div>
          </template>
        </el-upload>

        <el-divider content-position="left">封面 / 展示图片（可选）</el-divider>

        <el-upload
          ref="coverUploadRef"
          v-model:file-list="coverFileList"
          :with-credentials="true"
          :multiple="true"
          :auto-upload="false"
          :limit="10"
          name="files"
          accept="image/*"
          drag
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">把图片拖到这里，或 <em>点击选择</em></div>
          <template #tip>
            <div class="el-upload__tip">支持 PNG/JPG 等图片格式，单文件不超过 50MB</div>
          </template>
        </el-upload>

        <el-divider />

        <el-form-item>
          <el-button type="primary" @click="onSubmit" :loading="submitting" size="large">
            提交作品
          </el-button>
          <el-button @click="$router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-result v-if="done" icon="success" title="分享创建完成" sub-title="未登录的用户也能通过链接访问并下载">
      <template #extra>
        <el-input v-model="shareUrl" readonly style="max-width:520px; margin:0 auto 12px;" />
        <el-space wrap class="result-actions">
          <el-button type="primary" @click="copy(shareUrl)">复制链接</el-button>
          <el-button @click="$router.push(`/share/${slug}`)">查看详情</el-button>
          <el-button @click="$router.push('/resources')">返回列表</el-button>
        </el-space>
      </template>
    </el-result>
  </div>
</template>

<script setup lang="ts">
import { ref, onBeforeUnmount } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import type { FormInstance, FormRules, UploadInstance, UploadUserFile } from 'element-plus'
import { ElMessage } from 'element-plus'
import { createResource, optimizeContent } from '../api/resources'
import { http } from '../api/http'
import { UploadFilled, MagicStick } from '@element-plus/icons-vue'

const formRef = ref<FormInstance>()
const uploadRef = ref<UploadInstance>()
const coverUploadRef = ref<UploadInstance>()
const submitting = ref(false)
const aiLoading = ref(false)
const done = ref(false)
const form = ref({ title: '', description: '', usage: '' })
const rules: FormRules = { title: [{ required: true, message: '请输入标题', trigger: 'blur' }] }

const slug = ref('')
const shareUrl = ref('')

const fileList = ref<UploadUserFile[]>([])
const coverFileList = ref<UploadUserFile[]>([])
const saveWatermark = ref<boolean>(false)

async function onAIOptimize() {
  if (!form.value.title.trim()) {
    ElMessage.warning('请先输入标题')
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
    if (result.tags?.length) {
      ElMessage.success(`AI 已优化内容，生成标签：${result.tags.join('、')}`)
    } else {
      ElMessage.success('AI 已优化内容')
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

    const formData = new FormData()
    formData.append('resourceId', String(resourceId))
    formData.append('saveWatermark', String(saveWatermark.value))
    for (const f of fileList.value) {
      const raw = (f as any).raw
      if (raw) formData.append('files', raw)
    }
    await http.post('/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    if (coverFileList.value.length) {
      const coverFormData = new FormData()
      for (const f of coverFileList.value) {
        const raw = (f as any).raw
        if (raw) coverFormData.append('files', raw)
      }
      await http.post(`/resources/${resourceId}/images/upload`, coverFormData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    }

    done.value = true
    ElMessage.success('作品上传成功')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.error || '上传失败')
  } finally {
    submitting.value = false
  }
}

async function copy(text: string) {
  if (!text) return
  try {
    if (typeof navigator !== 'undefined' && navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.left = '-9999px'
      document.body.appendChild(textarea)
      textarea.focus()
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    ElMessage.success('已复制')
  } catch (error) {
    console.error(error)
    ElMessage.error('复制失败，请手动复制')
  }
}

function abortAllUploads() {
  if (uploadRef.value) {
    fileList.value.forEach((f) => {
      if (f.status === 'uploading') {
        uploadRef.value!.abort(f as any)
      }
    })
  }
  if (coverUploadRef.value) {
    coverFileList.value.forEach((f) => {
      if (f.status === 'uploading') {
        coverUploadRef.value!.abort(f as any)
      }
    })
  }
}
onBeforeRouteLeave(() => {
  abortAllUploads()
})
onBeforeUnmount(() => {
  abortAllUploads()
})
</script>

<style scoped>
.container { max-width: 860px; margin: 0 auto; padding: 16px; }
.card { border-radius: 14px; }
.mb { margin-bottom: 12px; }
.mt { margin-top: 10px; }

@media (max-width: 640px) {
  :deep(.result-actions .el-space__item) { flex: 1 1 calc(50% - 8px); }
  :deep(.result-actions .el-button) { width: 100%; }
}
</style>
