<template>
  <div class="page-bg">
    <WelcomeGuide />
    <div class="container">
      <div class="header-section">
        <div class="header-left">
          <h1>作品管理中心</h1>
          <p class="subtitle">管理您的存档文件与教程文档</p>
        </div>
        <div class="header-right">
          <div class="tab-switch-wrapper">
            <div 
              class="tab-item" 
              :class="{ active: activeTab === 'resources' }"
              @click="activeTab = 'resources'"
            >
              <el-icon><Folder /></el-icon>
              <span>存档文件</span>
            </div>
            <div 
              class="tab-item" 
              :class="{ active: activeTab === 'tutorials' }"
              @click="activeTab = 'tutorials'"
            >
              <el-icon><Document /></el-icon>
              <span>教程文档</span>
            </div>
          </div>
          <el-button
            circle
            :loading="activeTab === 'resources' ? resourcesLoading : tutorialsLoading"
            @click="onRefresh"
          >
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- 资源存档管理 -->
      <template v-if="activeTab === 'resources'">
        <el-skeleton v-if="resourcesLoading" animated :rows="4" class="grid-skeleton" />
        <template v-else>
          <div v-if="!resourceItems.length" class="empty-state">
            <el-empty description="暂时没有上传的存档">
              <el-button type="primary" size="large" @click="$router.push('/upload')">
                <el-icon class="el-icon--left"><Upload /></el-icon>
                立即上传
              </el-button>
            </el-empty>
          </div>
          
          <div v-else class="works-grid">
            <!-- 新增卡片 -->
            <div class="work-card add-card" @click="$router.push('/upload')">
              <div class="add-icon">
                <el-icon><Plus /></el-icon>
              </div>
              <span>上传新存档</span>
            </div>

            <div
              v-for="item in resourceItems"
              :key="item.id"
              class="work-card"
            >
              <div class="card-content" @click="$router.push(`/share/${item.slug}`)">
                <div class="card-icon">
                  <el-icon><FolderOpened /></el-icon>
                </div>
                <div class="card-info">
                  <h3 class="work-title" :title="item.title">{{ item.title }}</h3>
                  <div class="work-meta">
                    <span>{{ item.files.length }} 个文件</span>
                    <span class="separator">•</span>
                    <span>{{ formatDate(item.created_at) }}</span>
                  </div>
                  <div class="work-desc" :title="item.description || '暂无简介'">
                    {{ item.description || '暂无简介' }}
                  </div>
                </div>
              </div>
              
              <div class="card-actions">
                <el-tooltip content="复制链接" placement="top">
                  <el-button text circle size="small" @click.stop="copy(item.shareUrl)">
                    <el-icon><Link /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-dropdown trigger="click" @command="(cmd) => handleResourceCommand(cmd, item)">
                  <el-button text circle size="small" @click.stop>
                    <el-icon><MoreFilled /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="preview">预览详情</el-dropdown-item>
                      <el-dropdown-item command="addFile">添加文件</el-dropdown-item>
                      <el-dropdown-item command="edit">编辑信息</el-dropdown-item>
                      <el-dropdown-item command="delete" divided style="color: var(--el-color-danger)">删除</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>
          </div>
        </template>
      </template>

      <!-- 教程文档管理 -->
      <template v-else>
        <el-skeleton v-if="tutorialsLoading" animated :rows="4" class="grid-skeleton" />
        <template v-else>
          <div v-if="!tutorialItems.length" class="empty-state">
            <el-empty description="暂时没有创建的教程">
              <el-button type="primary" size="large" @click="openTutorialCreate">
                <el-icon class="el-icon--left"><EditPen /></el-icon>
                开始创作
              </el-button>
            </el-empty>
          </div>
          
          <div v-else class="works-grid">
            <!-- 新增卡片 -->
            <div class="work-card add-card" @click="openTutorialCreate">
              <div class="add-icon">
                <el-icon><EditPen /></el-icon>
              </div>
              <span>新建教程</span>
            </div>

            <div
              v-for="t in tutorialItems"
              :key="t.id"
              class="work-card"
            >
              <div class="card-content" @click="$router.push({ path: '/tutorials/library', query: { id: t.id } })">
                <div class="card-icon tutorial-icon">
                  <el-icon><Reading /></el-icon>
                </div>
                <div class="card-info">
                  <h3 class="work-title" :title="t.title">{{ t.title }}</h3>
                  <div class="work-meta">
                    <span>{{ formatDate(t.created_at) }}</span>
                  </div>
                  <div class="work-desc" :title="t.description || '暂无简介'">
                    {{ t.description || '暂无简介' }}
                  </div>
                </div>
              </div>

              <div class="card-actions">
                <el-button text circle size="small" @click.stop="$router.push({ path: '/tutorials/library', query: { id: t.id } })">
                  <el-icon><View /></el-icon>
                </el-button>
                <el-dropdown trigger="click" @command="(cmd) => handleTutorialCommand(cmd, t)">
                  <el-button text circle size="small" @click.stop>
                    <el-icon><MoreFilled /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="view">查看文档</el-dropdown-item>
                      <el-dropdown-item command="edit">编辑内容</el-dropdown-item>
                      <el-dropdown-item command="delete" divided style="color: var(--el-color-danger)">删除</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>
          </div>
        </template>
      </template>

      <!-- 资源信息编辑弹窗 -->
      <el-dialog v-model="edit.visible" title="编辑信息" width="520px" @closed="resetEdit" align-center class="custom-dialog">
        <el-form :model="edit" label-position="top" ref="editFormRef">
          <el-form-item label="简介">
            <el-input
              v-model="edit.description"
              type="textarea"
              :rows="3"
              maxlength="300"
              show-word-limit
              placeholder="请输入简介"
            />
          </el-form-item>
          <el-form-item label="使用说明">
            <el-input v-model="edit.usage" type="textarea" :rows="6" placeholder="请输入使用说明" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="edit.visible = false">取消</el-button>
          <el-button type="primary" :loading="edit.loading" @click="submitEdit">保存</el-button>
        </template>
      </el-dialog>

      <!-- 上传文件弹窗 -->
      <el-dialog
        v-model="upload.visible"
        :title="`向 ${upload.title} 添加文件`"
        width="560px"
        @closed="resetUpload"
        align-center
        class="custom-dialog"
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
          <el-button @click="upload.visible = false">取消</el-button>
          <el-button type="primary" :loading="upload.submitting" @click="submitUpload">
            开始上传
          </el-button>
        </template>
      </el-dialog>

      <!-- 教程编辑 / 新建弹窗 -->
      <el-dialog
        v-model="tutorialEdit.visible"
        :title="tutorialEdit.isCreating ? '新增教程' : '编辑教程'"
        width="800px"
        @closed="resetTutorialEdit"
        align-center
        class="custom-dialog"
      >
        <el-form label-position="top" @submit.prevent>
          <el-form-item label="标题">
            <el-input v-model="tutorialEdit.title" placeholder="例如：甜瓜游乐场模组安装全流程" size="large" />
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
              :autosize="{ minRows: 12, maxRows: 24 }"
              placeholder="在这里粘贴或编写完整教程文本（支持 Markdown 格式）"
              class="content-editor"
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="tutorialEdit.visible = false">取消</el-button>
          <el-button type="primary" :loading="tutorialEdit.loading" @click="submitTutorialEdit">
            {{ tutorialEdit.isCreating ? '保存为教程' : '保存修改' }}
          </el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, onBeforeUnmount } from 'vue'
import { onBeforeRouteLeave, useRouter } from 'vue-router'
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
import { 
  UploadFilled, 
  Folder, 
  Document, 
  Refresh, 
  Plus, 
  FolderOpened, 
  Link, 
  MoreFilled, 
  Upload,
  Reading,
  EditPen,
  View
} from '@element-plus/icons-vue'
import WelcomeGuide from '../components/WelcomeGuide.vue'
import dayjs from 'dayjs'

const router = useRouter()
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

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  return dayjs(dateStr).format('YYYY-MM-DD')
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

function handleResourceCommand(command: string, item: MyResourceItem) {
  switch (command) {
    case 'preview':
      router.push(`/share/${item.slug}`)
      break
    case 'addFile':
      openUpload(item)
      break
    case 'edit':
      openEdit(item)
      break
    case 'delete':
      confirmRemove(item)
      break
  }
}

function handleTutorialCommand(command: string, item: MyTutorialItem) {
  switch (command) {
    case 'view':
      router.push({ path: '/tutorials/library', query: { id: item.id } })
      break
    case 'edit':
      openTutorialEdit(item)
      break
    case 'delete':
      confirmTutorialRemove(item)
      break
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
  background: #f5f7fa;
  min-height: 100vh;
  padding-bottom: 40px;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.header-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 32px;
}

.header-left h1 {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 8px 0;
}

.subtitle {
  color: #909399;
  font-size: 14px;
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.tab-switch-wrapper {
  background: white;
  padding: 4px;
  border-radius: 12px;
  display: flex;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.tab-item {
  padding: 8px 20px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #606266;
  font-weight: 500;
  transition: all 0.3s ease;
}

.tab-item.active {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}

.tab-item:hover:not(.active) {
  background: #f5f7fa;
}

.works-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 24px;
}

.work-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  transition: all 0.3s ease;
  border: 1px solid transparent;
  position: relative;
  display: flex;
  flex-direction: column;
  height: 200px;
}

.work-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0,0,0,0.06);
  border-color: var(--el-color-primary-light-8);
}

.add-card {
  border: 2px dashed #e4e7ed;
  background: transparent;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: #909399;
}

.add-card:hover {
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  transform: translateY(-4px);
}

.add-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #f0f2f5;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  transition: all 0.3s ease;
}

.add-card:hover .add-icon {
  background: white;
  color: var(--el-color-primary);
}

.card-content {
  flex: 1;
  cursor: pointer;
  display: flex;
  flex-direction: column;
}

.card-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  margin-bottom: 16px;
}

.card-icon.tutorial-icon {
  background: var(--el-color-warning-light-9);
  color: var(--el-color-warning);
}

.card-info {
  flex: 1;
  overflow: hidden;
}

.work-title {
  margin: 0 0 8px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.work-meta {
  font-size: 12px;
  color: #909399;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.work-desc {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-actions {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f0f2f5;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.work-card:hover .card-actions {
  opacity: 1;
}

.empty-state {
  padding: 60px 0;
  text-align: center;
}

@media (max-width: 768px) {
  .header-section {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .header-right {
    width: 100%;
    justify-content: space-between;
  }
  
  .card-actions {
    opacity: 1;
  }
}
</style>
