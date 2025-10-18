<template>
  <div class="page-bg">
    <div class="container">
      <el-card shadow="never" class="outer-card">
        <template #header>
          <div class="card-header">
            <span>我的存档</span>
            <el-button size="small" @click="fetch" :loading="loading">刷新</el-button>
          </div>
        </template>

        <el-skeleton v-if="loading" animated :rows="4" />
        <template v-else>
          <el-empty v-if="!items.length" description="暂时没有上传的存档">
            <el-button type="primary" @click="$router.push('/upload')">去上传</el-button>
          </el-empty>
          <el-space v-else direction="vertical" alignment="stretch" style="width: 100%" size="large">
            <el-card v-for="item in items" :key="item.id" shadow="hover" class="resource-card">
              <template #header>
                <div class="resource-header">
                  <div>
                    <div class="title">{{ item.title }}</div>
                    <div class="meta">创建于 {{ item.created_at }} · 文件 {{ item.files.length }} 个</div>
                  </div>
                  <el-space size="small">
                    <el-button size="small" @click="copy(item.shareUrl)">复制链接</el-button>
                    <el-button size="small" @click="$router.push(`/share/${item.slug}`)">预览</el-button>
                    <el-button size="small" @click="openUpload(item)">添加文件</el-button>
                    <el-button size="small" type="primary" @click="openEdit(item)">编辑信息</el-button>
                    <el-button size="small" type="danger" :loading="deletingId === item.id" @click="confirmRemove(item)">删除</el-button>
                  </el-space>
                </div>
              </template>

              <div class="section">
                <div class="section-title">简介</div>
                <div v-if="item.description" class="section-content">{{ item.description }}</div>
                <el-empty v-else description="暂无简介" />
              </div>

              <div class="section">
                <div class="section-title">使用说明</div>
                <div v-if="item.usage" class="section-content">{{ item.usage }}</div>
                <el-empty v-else description="暂无使用说明" />
              </div>

              <div class="section">
                <div class="section-title">分享链接</div>
                <div class="share-row">
                  <el-input v-model="item.shareUrl" readonly />
                  <el-button size="small" @click="copy(item.shareUrl)">复制</el-button>
                  <el-button size="small" @click="$router.push(`/share/${item.slug}`)">打开</el-button>
                </div>
              </div>

              <div class="section">
                <div class="section-title">文件列表</div>
                <el-empty v-if="!item.files.length" description="暂无文件" />
                <el-table v-else :data="item.files" size="small" border>
                  <el-table-column prop="original_name" label="文件名" min-width="220">
                    <template #default="scope">
                      <span :title="scope.row.original_name">{{ scope.row.original_name }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="大小" width="120">
                    <template #default="scope">
                      {{ prettySize(scope.row.size) }}
                    </template>
                  </el-table-column>
                  <el-table-column prop="mime" label="类型" width="160" />
                  <el-table-column label="上传时间" width="180">
                    <template #default="scope">
                      {{ scope.row.created_at || '' }}
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="120">
                    <template #default="scope">
                      <el-button size="small" @click="download(scope.row.id)">下载</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </el-card>
          </el-space>
        </template>
      </el-card>

      <el-dialog v-model="edit.visible" title="编辑信息" width="520px" @closed="resetEdit">
        <el-form :model="edit" label-width="84px" ref="editFormRef">
          <el-form-item label="简介">
            <el-input v-model="edit.description" type="textarea" :rows="3" maxlength="300" show-word-limit />
          </el-form-item>
          <el-form-item label="使用说明">
            <el-input v-model="edit.usage" type="textarea" :rows="6" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-space>
            <el-button @click="edit.visible = false">取消</el-button>
            <el-button type="primary" :loading="edit.loading" @click="submitEdit">保存</el-button>
          </el-space>
        </template>
      </el-dialog>

      <el-dialog v-model="upload.visible" :title="`为 ${upload.title} 添加文件`" width="560px" @closed="resetUpload">
        <el-upload
          ref="uploadRef"
          v-model:file-list="upload.fileList"
          :action="'/api/files/upload'"
          :data="{ resourceId: upload.resourceId }"
          :with-credentials="true"
          :auto-upload="false"
          :limit="10"
          name="files"
          drag
          @success="handleUploadSuccess"
          @error="handleUploadError"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">拖动或 <em>点击选择</em> 文件</div>
          <template #tip>
            <div class="el-upload__tip">单个文件最大 50MB，最多一次 10 个</div>
          </template>
        </el-upload>
        <template #footer>
          <el-space>
            <el-button @click="upload.visible = false">取消</el-button>
            <el-button type="primary" :loading="upload.submitting" @click="submitUpload">开始上传</el-button>
          </el-space>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import type { FormInstance, UploadInstance, UploadUserFile } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listMyResources, updateResourceMeta, deleteResource, type MyResourceItem } from '../api/resources'
import { UploadFilled } from '@element-plus/icons-vue'

const items = ref<MyResourceItem[]>([])
const loading = ref(false)
const deletingId = ref<number | null>(null)

const editFormRef = ref<FormInstance>()
const edit = reactive({
  visible: false,
  loading: false,
  id: 0,
  description: '',
  usage: ''
})

const uploadRef = ref<UploadInstance>()
const upload = reactive({
  visible: false,
  resourceId: 0,
  title: '',
  fileList: [] as UploadUserFile[],
  submitting: false
})

async function fetch() {
  loading.value = true
  try {
    items.value = await listMyResources()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.error || '获取数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetch)

function prettySize(n: number) {
  if (!n && n !== 0) return ''
  const units = ['B', 'KB', 'MB', 'GB']
  let idx = 0
  let value = n
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024
    idx++
  }
  return `${value.toFixed(1)} ${units[idx]}`
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
    ElMessage.success('链接已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

function openEdit(item: MyResourceItem) {
  edit.visible = true
  edit.id = item.id
  edit.description = item.description || ''
  edit.usage = item.usage || ''
}

function resetEdit() {
  editFormRef.value?.clearValidate?.()
  edit.id = 0
  edit.description = ''
  edit.usage = ''
  edit.loading = false
}

async function submitEdit() {
  edit.loading = true
  try {
    const updated = await updateResourceMeta(edit.id, {
      description: edit.description,
      usage: edit.usage
    })
    const index = items.value.findIndex(r => r.id === edit.id)
    if (index !== -1) {
      items.value[index] = { ...items.value[index], ...updated }
    }
    ElMessage.success('保存成功')
    edit.visible = false
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.error || '保存失败')
  } finally {
    edit.loading = false
  }
}

async function remove(item: MyResourceItem) {
  deletingId.value = item.id
  try {
    await deleteResource(item.id)
    items.value = items.value.filter(r => r.id !== item.id)
    ElMessage.success('已删除')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.error || '删除失败')
  } finally {
    deletingId.value = null
  }
}

async function confirmRemove(item: MyResourceItem) {
  try {
    await ElMessageBox.confirm('确定删除这个存档吗？', '提示', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  await remove(item)
}

function openUpload(item: MyResourceItem) {
  upload.visible = true
  upload.resourceId = item.id
  upload.title = item.title
  upload.fileList = []
}

function resetUpload() {
  upload.fileList = []
  upload.resourceId = 0
  upload.title = ''
  upload.submitting = false
}

function submitUpload() {
  if (!upload.fileList.length) {
    ElMessage.warning('请先选择文件')
    return
  }
  upload.submitting = true
  uploadRef.value?.submit()
}

function handleUploadSuccess(_response: any, _file: UploadUserFile, uploadFiles: UploadUserFile[]) {
  const finished = uploadFiles.every(item => item.status === 'success')
  if (finished) {
    upload.submitting = false
    upload.visible = false
    ElMessage.success('上传成功')
    fetch()
  }
}

function handleUploadError() {
  upload.submitting = false
  ElMessage.error('上传失败')
}

function download(id: number) {
  window.open(`/api/files/${id}/download`, '_blank')
}
</script>

<style scoped>
.page-bg {
  background: var(--el-color-success-light-9);
  min-height: 100vh;
}

.container {
  max-width: 1160px;
  margin: 0 auto;
  padding: 16px;
  position: relative;
  /* 让背景可以延伸到容器外，避免两侧留白 */
  overflow: visible;
  isolation: isolate;
}

/* 顶部绿色背景全宽延伸 */
.container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100vw;
  height: 100%;
  background:
    radial-gradient(1200px 600px at 50% -200px, var(--el-color-success-light-7), transparent 70%),
    linear-gradient(180deg, rgba(16,185,129,.06), rgba(255,255,255,0));
  z-index: -2;
}

.container::after {
  content: '';
  position: absolute;
  left: 0; right: 0; top: 0;
  height: 360px;
  background:
    radial-gradient(400px 200px at 15% -30px, rgba(16,185,129,.12), transparent 70%),
    radial-gradient(400px 200px at 85% -30px, rgba(16,185,129,.12), transparent 70%);
  filter: blur(20px);
  pointer-events: none;
  z-index: -1;
}

.outer-card {
  border-radius: 14px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.resource-card {
  border-radius: 14px;
}
.resource-header {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.title {
  font-size: 18px;
  font-weight: 700;
}
.meta {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.section {
  margin-top: 16px;
}
.section-title {
  font-weight: 600;
  margin-bottom: 6px;
}
.section-content {
  line-height: 1.6;
  white-space: pre-wrap;
}
.share-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
</style>
