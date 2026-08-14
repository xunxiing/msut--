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
            <div class="tab-item" :class="{ active: activeTab === 'resources' }" @click="activeTab = 'resources'">
              <el-icon><Folder /></el-icon>
              <span>存档文件</span>
            </div>
            <div class="tab-item" :class="{ active: activeTab === 'tutorials' }" @click="activeTab = 'tutorials'">
              <el-icon><Document /></el-icon>
              <span>教程文档</span>
            </div>
          </div>
          <el-button circle :loading="activeTab === 'resources' ? resourcesLoading : tutorialsLoading" @click="onRefresh">
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
            <div class="work-card add-card" @click="$router.push('/upload')">
              <div class="add-icon"><el-icon><Plus /></el-icon></div>
              <span>上传新存档</span>
            </div>
            <div v-for="item in resourceItems" :key="item.id" class="work-card">
              <div class="card-content" @click="openResourceDrawer(item)">
                <div class="card-icon" :class="{ 'has-cover': (item as any).coverUrlPath }">
                  <template v-if="(item as any).coverUrlPath">
                    <img class="card-cover-image" :src="toImageUrl((item as any).coverUrlPath)" alt="cover" loading="lazy" />
                  </template>
                  <template v-else><el-icon><FolderOpened /></el-icon></template>
                </div>
                <div class="card-info">
                  <h3 class="work-title" :title="item.title">{{ item.title }}</h3>
                  <div class="work-meta">
                    <span>{{ item.files.length }} 个文件</span>
                    <span class="separator">•</span>
                    <span>{{ formatDate(item.created_at) }}</span>
                  </div>
                  <div class="work-desc" :title="item.description || '暂无简介'">{{ item.description || '暂无简介' }}</div>
                </div>
              </div>
              <div class="card-actions">
                <el-tooltip content="复制链接" placement="top">
                  <el-button text circle size="small" @click.stop="copy(item.shareUrl)"><el-icon><Link /></el-icon></el-button>
                </el-tooltip>
                <el-tooltip content="预览详情" placement="top">
                  <el-button text circle size="small" @click.stop="$router.push(`/share/${item.slug}`)"><el-icon><View /></el-icon></el-button>
                </el-tooltip>
                <el-tooltip content="删除" placement="top">
                  <el-button text circle size="small" @click.stop="confirmRemove(item)" style="color: var(--el-color-danger)"><el-icon><Delete /></el-icon></el-button>
                </el-tooltip>
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
            <div class="work-card add-card" @click="openTutorialCreate">
              <div class="add-icon"><el-icon><EditPen /></el-icon></div>
              <span>新建教程</span>
            </div>
            <div v-for="t in tutorialItems" :key="t.id" class="work-card">
              <div class="card-content" @click="openTutorialEdit(t)">
                <div class="card-icon tutorial-icon"><el-icon><Reading /></el-icon></div>
                <div class="card-info">
                  <h3 class="work-title" :title="t.title">{{ t.title }}</h3>
                  <div class="work-meta"><span>{{ formatDate(t.created_at) }}</span></div>
                  <div class="work-desc" :title="t.description || '暂无简介'">{{ t.description || '暂无简介' }}</div>
                </div>
              </div>
              <div class="card-actions">
                <el-tooltip content="查看文档" placement="top">
                  <el-button text circle size="small" @click.stop="$router.push({ path: '/tutorials/library', query: { id: t.id } })"><el-icon><View /></el-icon></el-button>
                </el-tooltip>
                <el-tooltip content="删除" placement="top">
                  <el-button text circle size="small" @click.stop="confirmTutorialRemove(t)" style="color: var(--el-color-danger)"><el-icon><Delete /></el-icon></el-button>
                </el-tooltip>
              </div>
            </div>
          </div>
        </template>
      </template>

      <!-- 资源编辑抽屉 -->
      <el-drawer v-model="resourceDrawer.visible" size="680px" :title="resourceDrawer.title" direction="rtl" @closed="resetResourceDrawer">
        <div v-if="resourceDrawer.loading" style="padding: 40px; text-align: center">
          <el-skeleton animated :rows="6" />
        </div>
        <div v-else class="drawer-body">
          <el-form :model="resourceDrawer" label-position="top" @submit.prevent>
            <el-form-item label="作品名称">
              <el-input v-model="resourceDrawer.title" maxlength="80" show-word-limit />
            </el-form-item>
            <el-form-item label="简介">
              <el-input v-model="resourceDrawer.description" type="textarea" :rows="2" maxlength="300" show-word-limit />
            </el-form-item>
            <el-form-item label="使用方法">
              <el-input v-model="resourceDrawer.usage" type="textarea" :rows="4" />
            </el-form-item>
            <div class="drawer-ai-bar">
              <el-button :loading="resourceDrawer.aiLoading" @click="onDrawerAIOptimize" type="success" plain round size="small">
                <el-icon class="el-icon--left"><MagicStick /></el-icon>
                AI 优化
              </el-button>
            </div>
          </el-form>

          <el-divider content-position="left">已有文件 ({{ resourceDrawer.files.length }})</el-divider>
          <div v-if="resourceDrawer.files.length" class="file-list">
            <div v-for="f in resourceDrawer.files" :key="f.id" class="file-item">
              <el-icon class="file-icon"><Document /></el-icon>
              <span class="file-name" :title="f.original_name">{{ f.original_name }}</span>
              <span class="file-size">{{ formatSize(f.size) }}</span>
              <el-button text circle size="small" @click="downloadFile(f)" title="下载">
                <el-icon><Download /></el-icon>
              </el-button>
              <el-button text circle size="small" @click="removeFile(f)" title="删除" style="color: var(--el-color-danger)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
          <el-empty v-else description="暂无文件" :image-size="80" />

          <el-divider content-position="left">添加文件</el-divider>
          <el-upload ref="drawerUploadRef" v-model:file-list="resourceDrawer.newFiles" :with-credentials="true" :multiple="true" :auto-upload="false" :limit="10" name="files" drag>
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽文件到此处，或<em>点击选择</em></div>
            <template #tip><div class="el-upload__tip">最多 10 个，单个不超过 50MB</div></template>
          </el-upload>
          <el-button v-if="resourceDrawer.newFiles.length" type="primary" plain size="small" @click="submitNewFiles" :loading="resourceDrawer.uploading" style="margin-top: 8px">
            上传 {{ resourceDrawer.newFiles.length }} 个文件
          </el-button>

          <el-divider content-position="left">封面 / 图片</el-divider>
          <div v-if="resourceDrawer.images.length" class="cover-grid">
            <div v-for="img in resourceDrawer.images" :key="img.id" class="cover-item" :class="{ 'is-cover': img.id === resourceDrawer.coverFileId }" @click="setCover(img.id)">
              <img :src="toImageUrl(img.url_path)" :alt="img.original_name" class="cover-thumb" />
              <span v-if="img.id === resourceDrawer.coverFileId" class="cover-badge">封面</span>
            </div>
          </div>
          <el-upload ref="drawerCoverRef" v-model:file-list="resourceDrawer.newImages" :with-credentials="true" :multiple="true" :auto-upload="false" :limit="10" name="files" accept="image/*" list-type="picture-card">
            <el-icon><Plus /></el-icon>
          </el-upload>
          <el-button v-if="resourceDrawer.newImages.length" type="primary" plain size="small" @click="submitNewImages" :loading="resourceDrawer.uploadingImages" style="margin-top: 8px">
            上传 {{ resourceDrawer.newImages.length }} 张图片
          </el-button>
          <el-button v-if="resourceDrawer.coverFileId !== null" size="small" @click="clearCover" :loading="resourceDrawer.clearingCover" style="margin-left: 8px">清除封面</el-button>
        </div>

        <template #footer>
          <div class="drawer-footer">
            <el-button @click="resourceDrawer.visible = false">关闭</el-button>
            <el-button type="primary" :loading="resourceDrawer.saving" @click="saveResourceMeta">保存修改</el-button>
          </div>
        </template>
      </el-drawer>

      <!-- 教程编辑抽屉 -->
      <el-drawer v-model="tutorialDrawer.visible" size="680px" :title="tutorialDrawer.isCreating ? '新建教程' : '编辑教程'" direction="rtl" @closed="resetTutorialDrawer">
        <div class="drawer-body">
          <el-form label-position="top" @submit.prevent>
            <el-form-item label="标题">
              <el-input v-model="tutorialDrawer.title" placeholder="例如：甜瓜游乐场模组安装全流程" size="large" />
            </el-form-item>
            <el-form-item label="简介（可选）">
              <el-input v-model="tutorialDrawer.description" placeholder="一句话说明这篇教程主要讲什么" />
            </el-form-item>
            <el-form-item label="正文内容 (Markdown)">
              <el-input v-model="tutorialDrawer.content" type="textarea" :autosize="{ minRows: 12, maxRows: 24 }" placeholder="在这里粘贴或编写完整教程文本（支持 Markdown 格式）" class="content-editor" />
            </el-form-item>
          </el-form>
        </div>
        <template #footer>
          <div class="drawer-footer">
            <el-button @click="tutorialDrawer.visible = false">取消</el-button>
            <el-button type="primary" :loading="tutorialDrawer.loading" @click="submitTutorialEdit">
              {{ tutorialDrawer.isCreating ? '保存为教程' : '保存修改' }}
            </el-button>
          </div>
        </template>
      </el-drawer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import type { UploadInstance, UploadUserFile } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listMyResources, updateResourceMeta, deleteResource,
  setResourceCover, listResourceImages, optimizeContent,
  type MyResourceItem, type ResourceFile,
} from '../api/resources'
import { http } from '../api/http'
import {
  createTutorial, deleteTutorial, getTutorial, listMyTutorials, updateTutorial,
  type MyTutorialItem,
} from '../api/tutorials'
import {
  UploadFilled, Folder, Document, Refresh, Plus, FolderOpened, Link,
  Reading, EditPen, View, MagicStick, Download, Delete,
} from '@element-plus/icons-vue'
import WelcomeGuide from '../components/WelcomeGuide.vue'
import dayjs from 'dayjs'

const activeTab = ref<'resources' | 'tutorials'>('resources')

const resourceItems = ref<MyResourceItem[]>([])
const resourcesLoading = ref(false)
const tutorialItems = ref<MyTutorialItem[]>([])
const tutorialsLoading = ref(false)

const drawerUploadRef = ref<UploadInstance>()
const drawerCoverRef = ref<UploadInstance>()

function toImageUrl(path?: string | null) {
  if (!path) return ''
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  if (path.startsWith('/uploads/')) return path
  return path
}

function formatDate(d: string) { return d ? dayjs(d).format('YYYY-MM-DD') : '' }
function formatSize(bytes: number) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}

async function copy(text: string) {
  if (!text) return
  try { await navigator.clipboard.writeText(text); ElMessage.success('链接已复制') }
  catch {
    const ta = document.createElement('textarea'); ta.value = text; ta.style.cssText = 'position:fixed;left:-9999px'
    document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta)
    ElMessage.success('链接已复制')
  }
}

// ---- Resource drawer ----
const resourceDrawer = reactive({
  visible: false, loading: false, saving: false,
  id: 0, title: '', description: '', usage: '',
  files: [] as ResourceFile[], images: [] as ResourceFile[],
  coverFileId: null as number | null,
  newFiles: [] as UploadUserFile[], newImages: [] as UploadUserFile[],
  uploading: false, uploadingImages: false,
  aiLoading: false, clearingCover: false,
})

async function openResourceDrawer(item: MyResourceItem) {
  resourceDrawer.visible = true
  resourceDrawer.loading = true
  resourceDrawer.id = item.id
  resourceDrawer.title = item.title
  resourceDrawer.description = item.description || ''
  resourceDrawer.usage = item.usage || ''
  resourceDrawer.files = [...item.files]
  resourceDrawer.newFiles = []
  resourceDrawer.newImages = []
  resourceDrawer.coverFileId = (item as any).coverFileId ?? null
  try {
    const res = await listResourceImages(item.id)
    resourceDrawer.images = res.items || []
    if (typeof res.coverFileId === 'number' || res.coverFileId === null) {
      resourceDrawer.coverFileId = res.coverFileId ?? null
    }
  } catch { ElMessage.error('加载图片列表失败') }
  finally { resourceDrawer.loading = false }
}

function resetResourceDrawer() {
  resourceDrawer.id = 0
  resourceDrawer.title = ''
  resourceDrawer.description = ''
  resourceDrawer.usage = ''
  resourceDrawer.files = []
  resourceDrawer.images = []
  resourceDrawer.coverFileId = null
  resourceDrawer.newFiles = []
  resourceDrawer.newImages = []
  resourceDrawer.saving = false
  resourceDrawer.uploading = false
  resourceDrawer.uploadingImages = false
}

async function saveResourceMeta() {
  resourceDrawer.saving = true
  try {
    const updated = await updateResourceMeta(resourceDrawer.id, {
      description: resourceDrawer.description,
      usage: resourceDrawer.usage,
    })
    const idx = resourceItems.value.findIndex(r => r.id === resourceDrawer.id)
    if (idx !== -1) {
      resourceItems.value[idx] = { ...resourceItems.value[idx], ...updated, title: resourceDrawer.title }
    }
    ElMessage.success('保存成功')
    resourceDrawer.visible = false
  } catch (e: any) { ElMessage.error(e?.response?.data?.error || '保存失败') }
  finally { resourceDrawer.saving = false }
}

async function onDrawerAIOptimize() {
  if (!resourceDrawer.title.trim()) { ElMessage.warning('请先输入标题'); return }
  resourceDrawer.aiLoading = true
  try {
    const result = await optimizeContent({
      title: resourceDrawer.title,
      description: resourceDrawer.description,
      usage: resourceDrawer.usage,
    })
    resourceDrawer.title = result.title
    resourceDrawer.description = result.description
    resourceDrawer.usage = result.usage
    ElMessage.success('已优化内容')
  } catch (e: any) { ElMessage.error(e?.response?.data?.error || 'AI 优化失败') }
  finally { resourceDrawer.aiLoading = false }
}

async function submitNewFiles() {
  if (!resourceDrawer.newFiles.length) return
  resourceDrawer.uploading = true
  try {
    const fd = new FormData()
    fd.append('resourceId', String(resourceDrawer.id))
    for (const f of resourceDrawer.newFiles) { const raw = (f as any).raw; if (raw) fd.append('files', raw) }
    await http.post('/files/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    ElMessage.success('文件上传成功')
    resourceDrawer.newFiles = []
    await fetchResources()
    const item = resourceItems.value.find(r => r.id === resourceDrawer.id)
    if (item) resourceDrawer.files = [...item.files]
  } catch (e: any) { ElMessage.error(e?.response?.data?.error || '上传失败') }
  finally { resourceDrawer.uploading = false }
}

async function submitNewImages() {
  if (!resourceDrawer.newImages.length) return
  resourceDrawer.uploadingImages = true
  try {
    const fd = new FormData()
    for (const f of resourceDrawer.newImages) { const raw = (f as any).raw; if (raw) fd.append('files', raw) }
    await http.post(`/resources/${resourceDrawer.id}/images/upload`, fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    ElMessage.success('图片上传成功')
    resourceDrawer.newImages = []
    const res = await listResourceImages(resourceDrawer.id)
    resourceDrawer.images = res.items || []
  } catch (e: any) { ElMessage.error(e?.response?.data?.error || '上传失败') }
  finally { resourceDrawer.uploadingImages = false }
}

async function setCover(fileId: number) {
  try {
    const res = await setResourceCover(resourceDrawer.id, fileId)
    resourceDrawer.coverFileId = res.coverFileId ?? null
    const idx = resourceItems.value.findIndex(r => r.id === resourceDrawer.id)
    if (idx !== -1) {
      const cur = resourceItems.value[idx] as any
      const target = resourceDrawer.images.find(img => img.id === fileId) as any
      resourceItems.value[idx] = { ...cur, coverFileId: res.coverFileId, coverUrlPath: target?.url_path || cur.coverUrlPath }
    }
    ElMessage.success('封面已更新')
  } catch (e: any) { ElMessage.error(e?.response?.data?.error || '设置封面失败') }
}

async function clearCover() {
  resourceDrawer.clearingCover = true
  try {
    await setResourceCover(resourceDrawer.id, null)
    resourceDrawer.coverFileId = null
    const idx = resourceItems.value.findIndex(r => r.id === resourceDrawer.id)
    if (idx !== -1) {
      const cur = resourceItems.value[idx] as any
      resourceItems.value[idx] = { ...cur, coverFileId: null, coverUrlPath: null }
    }
    ElMessage.success('封面已清除')
  } catch (e: any) { ElMessage.error(e?.response?.data?.error || '清除封面失败') }
  finally { resourceDrawer.clearingCover = false }
}

function downloadFile(f: ResourceFile) {
  window.open(`/api/files/${f.id}/download`, '_blank')
}

async function removeFile(f: ResourceFile) {
  try {
    await ElMessageBox.confirm(`确定删除文件「${f.original_name}」吗？`, '提示', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
  } catch { return }
  try {
    await http.delete(`/files/${f.id}`)
    resourceDrawer.files = resourceDrawer.files.filter(x => x.id !== f.id)
    ElMessage.success('已删除')
    await fetchResources()
  } catch (e: any) { ElMessage.error(e?.response?.data?.error || '删除失败') }
}

async function confirmRemove(item: MyResourceItem) {
  try {
    await ElMessageBox.confirm('确定删除这个存档吗？', '提示', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
  } catch { return }
  try {
    await deleteResource(item.id)
    resourceItems.value = resourceItems.value.filter(r => r.id !== item.id)
    ElMessage.success('已删除')
  } catch (e: any) { ElMessage.error(e?.response?.data?.error || '删除失败') }
}

// ---- Tutorial drawer ----
const tutorialDrawer = reactive({
  visible: false, loading: false, isCreating: false,
  id: 0, title: '', description: '', content: '',
})

function openTutorialCreate() {
  tutorialDrawer.visible = true
  tutorialDrawer.isCreating = true
  tutorialDrawer.id = 0
  tutorialDrawer.title = ''
  tutorialDrawer.description = ''
  tutorialDrawer.content = ''
}

async function openTutorialEdit(item: MyTutorialItem) {
  tutorialDrawer.visible = true
  tutorialDrawer.isCreating = false
  tutorialDrawer.loading = true
  tutorialDrawer.id = item.id
  tutorialDrawer.title = item.title
  tutorialDrawer.description = item.description || ''
  try {
    const detail = await getTutorial(item.id)
    tutorialDrawer.content = detail.content || ''
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.error || '加载教程内容失败')
    tutorialDrawer.visible = false
  } finally { tutorialDrawer.loading = false }
}

function resetTutorialDrawer() {
  tutorialDrawer.id = 0
  tutorialDrawer.title = ''
  tutorialDrawer.description = ''
  tutorialDrawer.content = ''
  tutorialDrawer.loading = false
  tutorialDrawer.isCreating = false
}

async function submitTutorialEdit() {
  const title = (tutorialDrawer.title || '').trim()
  const content = (tutorialDrawer.content || '').trim()
  if (!title || !content) { ElMessage.warning('标题和正文内容不能为空'); return }
  tutorialDrawer.loading = true
  try {
    if (tutorialDrawer.isCreating) {
      await createTutorial({ title, description: (tutorialDrawer.description || '').trim(), content })
      ElMessage.success('教程已保存')
      tutorialDrawer.visible = false
      await fetchTutorials()
    } else {
      const detail = await updateTutorial(tutorialDrawer.id, { title, description: (tutorialDrawer.description || '').trim(), content })
      const idx = tutorialItems.value.findIndex(t => t.id === detail.id)
      if (idx !== -1) {
        const t = tutorialItems.value[idx]
        if (t) { t.title = detail.title; t.description = detail.description; t.updated_at = detail.updated_at }
      }
      ElMessage.success('修改已保存')
      tutorialDrawer.visible = false
    }
  } catch (e: any) { ElMessage.error(e?.response?.data?.error || '保存教程失败') }
  finally { tutorialDrawer.loading = false }
}

async function confirmTutorialRemove(item: MyTutorialItem) {
  try {
    await ElMessageBox.confirm('确定删除这个教程吗？', '提示', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
  } catch { return }
  try {
    await deleteTutorial(item.id)
    tutorialItems.value = tutorialItems.value.filter(t => t.id !== item.id)
    ElMessage.success('已删除')
  } catch (e: any) { ElMessage.error(e?.response?.data?.error || '删除失败') }
}

// ---- Fetch ----
async function fetchResources() {
  resourcesLoading.value = true
  try { resourceItems.value = await listMyResources() }
  catch (e: any) { ElMessage.error(e?.response?.data?.error || '获取存档数据失败') }
  finally { resourcesLoading.value = false }
}

async function fetchTutorials() {
  tutorialsLoading.value = true
  try { tutorialItems.value = await listMyTutorials() }
  catch (e: any) { ElMessage.error(e?.response?.data?.error || '获取教程列表失败') }
  finally { tutorialsLoading.value = false }
}

function onRefresh() {
  if (activeTab.value === 'resources') fetchResources()
  else fetchTutorials()
}

const router = useRouter()

onMounted(() => {
  if (window.innerWidth < 768) {
    router.replace('/m/my/resources')
    return
  }
  fetchResources(); fetchTutorials()
})

function abortAllUploads() {
  if (drawerUploadRef.value) {
    resourceDrawer.newFiles.forEach((f) => { if ((f as any).status === 'uploading') drawerUploadRef.value!.abort(f as any) })
  }
  if (drawerCoverRef.value) {
    resourceDrawer.newImages.forEach((f) => { if ((f as any).status === 'uploading') drawerCoverRef.value!.abort(f as any) })
  }
}
onBeforeUnmount(() => abortAllUploads())
</script>

<style scoped>
.page-bg { background: #f5f7fa; min-height: 100vh; padding-bottom: 40px; }
.container { max-width: 1200px; margin: 0 auto; padding: 24px; }

.header-section { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 32px; }
.header-left h1 { font-size: 28px; font-weight: 700; color: #1a1a1a; margin: 0 0 8px 0; }
.subtitle { color: #909399; font-size: 14px; margin: 0; }
.header-right { display: flex; align-items: center; gap: 16px; }

.tab-switch-wrapper { background: white; padding: 4px; border-radius: 12px; display: flex; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
.tab-item { padding: 8px 20px; border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 8px; color: #606266; font-weight: 500; transition: all 0.3s ease; }
.tab-item.active { background: var(--el-color-primary-light-9); color: var(--el-color-primary); }
.tab-item:hover:not(.active) { background: #f5f7fa; }

.works-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 24px; }
.work-card { background: white; border-radius: 16px; padding: 20px; transition: all 0.3s ease; border: 1px solid transparent; position: relative; display: flex; flex-direction: column; min-height: 200px; }
.work-card:hover { transform: translateY(-4px); box-shadow: 0 12px 24px rgba(0,0,0,0.06); border-color: var(--el-color-primary-light-8); }

.add-card { border: 2px dashed #e4e7ed; background: transparent; cursor: pointer; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; color: #909399; }
.add-card:hover { border-color: var(--el-color-primary); color: var(--el-color-primary); background: var(--el-color-primary-light-9); transform: translateY(-4px); }
.add-icon { width: 48px; height: 48px; border-radius: 50%; background: #f0f2f5; display: flex; align-items: center; justify-content: center; font-size: 24px; transition: all 0.3s ease; }
.add-card:hover .add-icon { background: white; color: var(--el-color-primary); }

.card-content { flex: 1; cursor: pointer; display: flex; flex-direction: column; }
.card-icon { width: 48px; height: 48px; border-radius: 12px; background: var(--el-color-primary-light-9); color: var(--el-color-primary); display: flex; align-items: center; justify-content: center; font-size: 24px; margin-bottom: 16px; }
.card-icon.has-cover { background: #0f172a; overflow: hidden; padding: 0; }
.card-cover-image { width: 100%; height: 100%; object-fit: cover; display: block; }
.card-icon.tutorial-icon { background: var(--el-color-warning-light-9); color: var(--el-color-warning); }

.card-info { flex: 1; overflow: hidden; }
.work-title { margin: 0 0 8px 0; font-size: 16px; font-weight: 600; color: #303133; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.work-meta { font-size: 12px; color: #909399; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
.work-desc { font-size: 13px; color: #606266; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

.card-actions { margin-top: 16px; padding-top: 16px; border-top: 1px solid #f0f2f5; display: flex; justify-content: flex-end; gap: 8px; opacity: 0; transition: opacity 0.3s ease; }
.work-card:hover .card-actions { opacity: 1; }

.empty-state { padding: 60px 0; text-align: center; }

/* Drawer body */
.drawer-body { padding: 0 4px; }
.drawer-ai-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.drawer-footer { display: flex; justify-content: flex-end; gap: 12px; }

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

@media (max-width: 768px) {
  .container { padding: 16px; }
  .header-section { flex-direction: column; align-items: flex-start; gap: 16px; margin-bottom: 24px; }
  .header-right { width: 100%; justify-content: space-between; gap: 12px; }
  .tab-item { padding: 8px 12px; font-size: 14px; }
  .works-grid { grid-template-columns: 1fr; gap: 16px; }
  .work-card { padding: 16px; min-height: 0; }
  .card-content { flex-direction: row; align-items: center; gap: 16px; }
  .card-icon { width: 80px; height: 80px; margin-bottom: 0; flex-shrink: 0; }
  .work-title { font-size: 15px; margin-bottom: 4px; }
  .work-meta { margin-bottom: 4px; }
  .card-actions { opacity: 1; margin-top: 12px; padding-top: 12px; }
  .add-card { flex-direction: row; height: 60px; min-height: 0; padding: 0 16px; justify-content: flex-start; gap: 12px; }
  .add-icon { width: 32px; height: 32px; font-size: 16px; }
}
</style>
