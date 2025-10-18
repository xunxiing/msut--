<template>
  <div class="container">
    <el-steps :active="step" finish-status="success" align-center class="mb">
      <el-step title="填写信息" />
      <el-step title="上传文件" />
      <el-step title="完成" />
    </el-steps>

    <el-card v-if="step === 0" class="card">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="96px" @submit.prevent>
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" maxlength="80" show-word-limit />
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="form.description" type="textarea" :rows="3" maxlength="300" show-word-limit />
        </el-form-item>
        <el-form-item label="使用方法">
          <el-input v-model="form.usage" type="textarea" :rows="6" placeholder="如何安装、如何使用，写清楚，减少问答" />
        </el-form-item>
        <el-space>
          <el-button type="primary" @click="onCreate" :loading="loading">下一步</el-button>
          <el-button @click="$router.back()">取消</el-button>
        </el-space>
      </el-form>
    </el-card>

    <el-card v-else-if="step === 1" class="card">
      <template #header>上传文件</template>
      <el-alert type="info" :closable="false" class="mb" show-icon title="可选：为 .melsave 存档提取并保存水印，便于后续检测匹配" />
      <el-form @submit.prevent label-width="0">
        <el-form-item>
          <el-checkbox v-model="saveWatermark">保存 .melsave 水印到数据库</el-checkbox>
        </el-form-item>
      </el-form>
      <el-upload
        ref="uploadRef"
        v-model:file-list="fileList"
        :action="`/api/files/upload`"
        :data="{ resourceId: resourceId, saveWatermark }"
        :with-credentials="true"
        :multiple="true"
        :auto-upload="false"
        :limit="10"
        name="files"
        drag
        @success="handleSuccess"
        @error="handleError"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">把文件拖到这里，或 <em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">支持最多 10 个文件，单文件不超过 50MB</div>
        </template>
      </el-upload>

      <el-space class="mt">
        <el-button type="primary" @click="submitUpload">开始上传</el-button>
      </el-space>
    </el-card>

    <el-result v-else icon="success" title="分享创建完成" sub-title="未登录的用户也能通过链接访问并下载">
      <template #extra>
        <el-input v-model="shareUrl" readonly style="max-width:520px; margin:0 auto 12px;" />
        <el-space>
          <el-button type="primary" @click="copy(shareUrl)">复制链接</el-button>
          <el-button @click="$router.push(`/share/${slug}`)">查看详情</el-button>
          <el-button @click="$router.push('/resources')">返回列表</el-button>
        </el-space>
      </template>
    </el-result>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { FormInstance, FormRules, UploadInstance, UploadUserFile } from 'element-plus'
import { ElMessage } from 'element-plus'
import { createResource } from '../api/resources'
import { UploadFilled } from '@element-plus/icons-vue'

const step = ref(0)
const formRef = ref<FormInstance>()
const uploadRef = ref<UploadInstance>()
const loading = ref(false)
const form = ref({ title: '', description: '', usage: '' })
const rules: FormRules = { title: [{ required: true, message: '请输入标题', trigger: 'blur' }] }

const resourceId = ref<number | null>(null)
const slug = ref('')
const shareUrl = ref('')

const fileList = ref<UploadUserFile[]>([])
const uploaded = ref(false)
const saveWatermark = ref<boolean>(false)

async function onCreate() {
  await formRef.value?.validate()
  loading.value = true
  try {
    const res = await createResource(form.value)
    resourceId.value = res.id
    slug.value = res.slug
    shareUrl.value = res.shareUrl
    step.value = 1
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.error || '创建失败')
  } finally {
    loading.value = false
  }
}

function submitUpload() {
  if (!fileList.value.length) return ElMessage.warning('请先选择文件')
  uploaded.value = false
  uploadRef.value?.submit()
}

function handleSuccess(_response: any, _file: UploadUserFile, uploadFiles: UploadUserFile[]) {
  const finished = uploadFiles.every(item => item.status === 'success')
  if (finished && !uploaded.value) {
    uploaded.value = true
    ElMessage.success('文件上传成功')
    step.value = 2
  }
}

function handleError() {
  ElMessage.error('文件上传失败')
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
</script>

<style scoped>
.container { max-width: 860px; margin: 0 auto; padding: 16px; }
.card { border-radius: 14px; }
.mb { margin-bottom: 12px; }
.mt { margin-top: 10px; }
</style>
