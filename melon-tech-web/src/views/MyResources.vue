<template>
  <div class="page-bg">
    <div class="container">
      <el-card shadow="never" class="outer-card">
        <template #header>
          <div class="card-header">
            <span>作品管理中心</span>
            <div class="card-header-right">
              <el-radio-group v-model="activeTab" size="small" class="tab-switch">
                <el-radio-button label="resources">存档文件</el-radio-button>
                <el-radio-button label="tutorials">教程文档</el-radio-button>
              </el-radio-group>
              <el-button
                size="small"
                @click="onRefresh"
                :loading="activeTab === 'resources' ? resourcesLoading : tutorialsLoading"
              >
                刷新
              </el-button>
            </div>
          </div>
        </template>

        <!-- 资源存档管理 -->
        <template v-if="activeTab === 'resources'">
          <el-skeleton v-if="resourcesLoading" animated :rows="4" />
          <template v-else>
            <el-empty v-if="!resourceItems.length" description="暂时没有上传的存档">
              <el-button type="primary" @click="$router.push('/upload')">去上传</el-button>
            </el-empty>
            <el-space
              v-else
              direction="vertical"
              alignment="stretch"
              style="width: 100%"
              size="large"
            >
              <el-card
                v-for="item in resourceItems"
                :key="item.id"
                shadow="hover"
                class="resource-card"
              >
                <template #header>
                  <div class="resource-header">
                    <div>
                      <div class="title">{{ item.title }}</div>
                      <div class="meta">
                        创建于 {{ item.created_at }} · 文件 {{ item.files.length }} 个
                      </div>
                    </div>
                    <el-space size="small" wrap class="actions">
                      <el-button size="small" @click="copy(item.shareUrl)">复制链接</el-button>
                      <el-button size="small" @click="$router.push(`/share/${item.slug}`)">预览</el-button>
                      <el-button size="small" @click="openUpload(item)">添加文件</el-button>
                      <el-button size="small" type="primary" @click="openEdit(item)">编辑信息</el-button>
                      <el-button
                        size="small"
                        type="danger"
                        :loading="resourceDeletingId === item.id"
                        @click="confirmRemove(item)"
                      >
                        删除
                      </el-button>
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
        </template>

        <!-- 教程文档管理 -->
        <template v-else>
          <el-skeleton v-if="tutorialsLoading" animated :rows="4" />
          <template v-else>
            <el-empty v-if="!tutorialItems.length" description="暂时没有创建的教程">
              <el-button type="primary" @click="openTutorialCreate">新增教程</el-button>
            </el-empty>
            <el-space
              v-else
              direction="vertical"
              alignment="stretch"
              style="width: 100%"
              size="large"
            >
              <el-card
                v-for="t in tutorialItems"
                :key="t.id"
                shadow="hover"
                class="resource-card"
              >
                <template #header>
                  <div class="resource-header">
                    <div>
                      <div class="title">{{ t.title }}</div>
                      <div class="meta">
                        创建于 {{ t.created_at }}
                        <span v-if="t.updated_at && t.updated_at !== t.created_at">
                          · 更新于 {{ t.updated_at }}
                        </span>
                      </div>
                    </div>
                    <el-space size="small" wrap class="actions">
                      <el-button
                        size="small"
                        @click="$router.push({ path: '/tutorials/library', query: { id: t.id } })"
                      >
                        查看
                      </el-button>
                      <el-button size="small" type="primary" @click="openTutorialEdit(t)">
                        编辑
                      </el-button>
                      <el-button
                        size="small"
                        type="danger"
                        :loading="tutorialDeletingId === t.id"
                        @click="confirmTutorialRemove(t)"
                      >
                        删除
                      </el-button>
                    </el-space>
                  </div>
                </template>

                <div class="section">
                  <div class="section-title">简介</div>
                  <div v-if="t.description" class="section-content">{{ t.description }}</div>
                  <el-empty v-else description="暂无简介" />
                </div>
              </el-card>
            </el-space>
            <div class="tutorial-footer-actions">
              <el-button type="primary" plain size="small" @click="openTutorialCreate">
                新增教程
              </el-button>
            </div>
          </template>
        </template>
      </el-card>

      <!-- 资源信息编辑弹窗 -->
      <el-dialog v-model="edit.visible" title="编辑信息" width="520px" @closed="resetEdit">
        <el-form :model="edit" label-width="84px" ref="editFormRef">
          <el-form-item label="简介">
            <el-input
              v-model="edit.description"
              type="textarea"
              :rows="3"
              maxlength="300"
              show-word-limit
            />
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

      <!-- 上传文件弹窗 -->
      <el-dialog
        v-model="upload.visible"
        :title="`向 ${upload.title} 添加文件`"
        width="560px"
        @closed="resetUpload"
      >
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
            <el-button type="primary" :loading="upload.submitting" @click="submitUpload">
              开始上传
            </el-button>
          </el-space>
        </template>
      </el-dialog>

      <!-- 教程编辑 / 新建弹窗 -->
      <el-dialog
        v-model="tutorialEdit.visible"
        :title="tutorialEdit.isCreating ? '新增教程' : '编辑教程'"
        width="640px"
        @closed="resetTutorialEdit"
      >
        <el-form label-position="top" @submit.prevent>
          <el-form-item label="标题">
            <el-input v-model="tutorialEdit.title" placeholder="例如：甜瓜游乐场模组安装全流程" />
          </el-form-item>
          <el-form-item label="简介（可选）">
            <el-input
              v-model="tutorialEdit.description"
              placeholder="一句话说明这篇教程主要讲什么"
            />
          </el-form-item>
          <el-form-item label="正文内容 (Markdown)">
            <el-input
              v-model="tutorialEdit.content"
              type="textarea"
              :autosize="{ minRows: 8, maxRows: 16 }"
              placeholder="在这里粘贴或编写完整教程文本（支持 Markdown 格式）"
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-space>
            <el-button @click="tutorialEdit.visible = false">取消</el-button>
            <el-button type="primary" :loading="tutorialEdit.loading" @click="submitTutorialEdit">
              {{ tutorialEdit.isCreating ? '保存为教程' : '保存修改' }}
            </el-button>
          </el-space>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, onBeforeUnmount } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import type { FormInstance, UploadInstance, UploadUserFile } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listMyResources,
  updateResourceMeta,
  deleteResource,
  type MyResourceItem,
} from '../api/resources'
import {
  createTutorial,
  deleteTutorial,
  getTutorial,
  listMyTutorials,
  updateTutorial,
  type MyTutorialItem,
} from '../api/tutorials'
import { UploadFilled } from '@element-plus/icons-vue'

const activeTab = ref<'resources' | 'tutorials'>('resources')

const resourceItems = ref<MyResourceItem[]>([])
const resourcesLoading = ref(false)
const resourceDeletingId = ref<number | null>(null)

const tutorialItems = ref<MyTutorialItem[]>([])
const tutorialsLoading = ref(false)
const tutorialDeletingId = ref<number | null>(null)

const editFormRef = ref<FormInstance>()
const edit = reactive({
  visible: false,
  loading: false,
  id: 0,
  description: '',
  usage: '',
})

const uploadRef = ref<UploadInstance>()
const upload = reactive({
  visible: false,
  resourceId: 0,
  title: '',
  fileList: [] as UploadUserFile[],
  submitting: false,
})

const tutorialEdit = reactive({
  visible: false,
  loading: false,
  isCreating: false,
  id: 0,
  title: '',
  description: '',
  content: '',
})

async function fetchResources() {
  resourcesLoading.value = true
  try {
    resourceItems.value = await listMyResources()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.error || '获取存档数据失败')
  } finally {
    resourcesLoading.value = false
  }
}

async function fetchTutorials() {
  tutorialsLoading.value = true
  try {
    tutorialItems.value = await listMyTutorials()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.error || '获取教程列表失败')
  } finally {
    tutorialsLoading.value = false
  }
}

function onRefresh() {
  if (activeTab.value === 'resources') {
    fetchResources()
  } else {
    fetchTutorials()
  }
}

onMounted(() => {
  fetchResources()
  fetchTutorials()
})

function prettySize(n: number) {
  if (n === null || n === undefined) return ''
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
      usage: edit.usage,
    })
    const index = resourceItems.value.findIndex(r => r.id === edit.id)
    if (index !== -1) {
      resourceItems.value[index] = { ...resourceItems.value[index], ...updated }
    }
    ElMessage.success('保存成功')
    edit.visible = false
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.error || '保存失败')
  } finally {
    edit.loading = false
  }
}

async function removeResource(item: MyResourceItem) {
  resourceDeletingId.value = item.id
  try {
    await deleteResource(item.id)
    resourceItems.value = resourceItems.value.filter(r => r.id !== item.id)
    ElMessage.success('已删除')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.error || '删除失败')
  } finally {
    resourceDeletingId.value = null
  }
}

async function confirmRemove(item: MyResourceItem) {
  try {
    await ElMessageBox.confirm('确定删除这个存档吗？', '提示', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await removeResource(item)
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
    fetchResources()
  }
}

function handleUploadError() {
  upload.submitting = false
  ElMessage.error('上传失败')
}

function download(id: number) {
  window.open(`/api/files/${id}/download`, '_blank')
}

function openTutorialCreate() {
  tutorialEdit.visible = true
  tutorialEdit.isCreating = true
  tutorialEdit.id = 0
  tutorialEdit.title = ''
  tutorialEdit.description = ''
  tutorialEdit.content = ''
}

async function openTutorialEdit(item: MyTutorialItem) {
  tutorialEdit.visible = true
  tutorialEdit.isCreating = false
  tutorialEdit.loading = true
  tutorialEdit.id = item.id
  tutorialEdit.title = item.title
  tutorialEdit.description = item.description || ''
  try {
    const detail = await getTutorial(item.id)
    tutorialEdit.content = detail.content || ''
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.error || '加载教程内容失败')
    tutorialEdit.visible = false
  } finally {
    tutorialEdit.loading = false
  }
}

function resetTutorialEdit() {
  tutorialEdit.id = 0
  tutorialEdit.title = ''
  tutorialEdit.description = ''
  tutorialEdit.content = ''
  tutorialEdit.loading = false
  tutorialEdit.isCreating = false
}

async function submitTutorialEdit() {
  const title = (tutorialEdit.title || '').trim()
  const content = (tutorialEdit.content || '').trim()
  if (!title || !content) {
    ElMessage.warning('标题和正文内容不能为空')
    return
  }
  tutorialEdit.loading = true
  try {
    if (tutorialEdit.isCreating) {
      await createTutorial({
        title,
        description: (tutorialEdit.description || '').trim(),
        content,
      })
      ElMessage.success('教程已保存')
      tutorialEdit.visible = false
      await fetchTutorials()
    } else {
      const detail = await updateTutorial(tutorialEdit.id, {
        title,
        description: (tutorialEdit.description || '').trim(),
        content,
      })
      const index = tutorialItems.value.findIndex(t => t.id === detail.id)
      if (index !== -1) {
        const target = tutorialItems.value[index]
        if (target) {
          target.title = detail.title
          target.description = detail.description
          target.updated_at = detail.updated_at
        }
      }
      ElMessage.success('修改已保存')
      tutorialEdit.visible = false
    }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.error || '保存教程失败')
  } finally {
    tutorialEdit.loading = false
  }
}

async function removeTutorial(item: MyTutorialItem) {
  tutorialDeletingId.value = item.id
  try {
    await deleteTutorial(item.id)
    tutorialItems.value = tutorialItems.value.filter(t => t.id !== item.id)
    ElMessage.success('已删除')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.error || '删除失败')
  } finally {
    tutorialDeletingId.value = null
  }
}

async function confirmTutorialRemove(item: MyTutorialItem) {
  try {
    await ElMessageBox.confirm('确定删除这个教程吗？', '提示', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await removeTutorial(item)
}

// 确保路由切换或组件卸载时中止后台上传
function abortAllUploads() {
  if (!uploadRef.value) return
  ;(upload.fileList || []).forEach((f) => {
    if ((f as any).status === 'uploading') {
      uploadRef.value!.abort(f as any)
    }
  })
}

onBeforeRouteLeave(() => {
  abortAllUploads()
})

onBeforeUnmount(() => {
  abortAllUploads()
})
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
  overflow: visible;
  isolation: isolate;
}

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
  left: 0;
  right: 0;
  top: 0;
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

.card-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.tab-switch {
  margin-right: 4px;
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

.tutorial-footer-actions {
  margin-top: 12px;
  text-align: right;
}

@media (max-width: 640px) {
  .resource-header {
    align-items: flex-start;
  }
  .actions {
    width: 100%;
    justify-content: flex-start;
  }
  :deep(.actions .el-space__item) {
    flex: 1 1 calc(33.333% - 8px);
  }
  :deep(.actions .el-button) {
    width: 100%;
  }

  .share-row {
    flex-wrap: wrap;
  }
  :deep(.share-row .el-input) {
    flex: 1 0 100%;
  }
}

@media (max-width: 420px) {
  :deep(.actions .el-space__item) {
    flex: 1 1 calc(50% - 8px);
  }
}
</style>
