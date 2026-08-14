<template>
  <div class="mobile-page">
    <div class="mobile-header">
      <h1>作品管理</h1>
      <el-button circle :loading="loading" @click="fetchResources" size="small">
        <el-icon><Refresh /></el-icon>
      </el-button>
    </div>

    <div class="tab-bar">
      <div class="tab-item" :class="{ active: activeTab === 'resources' }" @click="activeTab = 'resources'">
        <el-icon><Folder /></el-icon><span>存档</span>
      </div>
      <div class="tab-item" :class="{ active: activeTab === 'tutorials' }" @click="activeTab = 'tutorials'">
        <el-icon><Document /></el-icon><span>教程</span>
      </div>
    </div>

    <div v-if="activeTab === 'resources'" class="list-area">
      <div v-if="!loading && !resourceItems.length" class="empty">
        <el-empty description="还没有上传的存档" :image-size="80">
          <el-button type="primary" size="small" @click="$router.push('/upload')">立即上传</el-button>
        </el-empty>
      </div>
      <div v-for="item in resourceItems" :key="item.id" class="m-card" @click="openResource(item)">
        <div class="m-card-cover">
          <img v-if="(item as any).coverUrlPath" :src="toImageUrl((item as any).coverUrlPath)" alt="cover" />
          <el-icon v-else size="24"><FolderOpened /></el-icon>
        </div>
        <div class="m-card-info">
          <div class="m-card-title">{{ item.title }}</div>
          <div class="m-card-meta">{{ item.files.length }} 文件 · {{ formatDate(item.created_at) }}</div>
        </div>
        <el-icon class="m-card-arrow"><ArrowRight /></el-icon>
      </div>
      <div class="m-add-btn" @click="$router.push('/upload')">
        <el-icon><Plus /></el-icon><span>上传新存档</span>
      </div>
    </div>

    <div v-else class="list-area">
      <div v-if="!loading && !tutorialItems.length" class="empty">
        <el-empty description="还没有创建的教程" :image-size="80">
          <el-button type="primary" size="small" @click="openTutorialCreate">开始创作</el-button>
        </el-empty>
      </div>
      <div v-for="t in tutorialItems" :key="t.id" class="m-card" @click="openTutorialEdit(t)">
        <div class="m-card-cover tutorial-cover"><el-icon size="24"><Reading /></el-icon></div>
        <div class="m-card-info">
          <div class="m-card-title">{{ t.title }}</div>
          <div class="m-card-meta">{{ formatDate(t.created_at) }}</div>
        </div>
        <el-icon class="m-card-arrow"><ArrowRight /></el-icon>
      </div>
      <div class="m-add-btn" @click="openTutorialCreate">
        <el-icon><Plus /></el-icon><span>新建教程</span>
      </div>
    </div>

    <!-- Resource edit bottom sheet -->
    <el-drawer
      v-model="resourceSheet.visible"
      direction="btt"
      size="85%"
      :title="resourceSheet.title || '编辑作品'"
      @closed="resetResourceSheet"
    >
      <div v-if="resourceSheet.loading" style="padding: 24px; text-align: center"><el-skeleton animated :rows="6" /></div>
      <div v-else class="sheet-body">
        <ResourceEditor
          ref="editorRef"
          :title="resourceSheet.title"
          :description="resourceSheet.description"
          :usage="resourceSheet.usage"
          :files="resourceSheet.files"
          :images="resourceSheet.images"
          :coverFileId="resourceSheet.coverFileId"
          @update:title="resourceSheet.title = $event"
          @update:description="resourceSheet.description = $event"
          @update:usage="resourceSheet.usage = $event"
          @download="downloadFile"
          @removeFile="removeFile"
          @setCover="setCover"
          @newFiles="resourceSheet.hasNewFiles = $event.length > 0"
          @newImages="resourceSheet.hasNewImages = $event.length > 0"
        />
      </div>
      <template #footer>
        <div class="sheet-footer">
          <el-button @click="resourceSheet.visible = false">取消</el-button>
          <el-button type="primary" :loading="resourceSheet.saving" @click="saveResource">保存</el-button>
        </div>
      </template>
    </el-drawer>

    <!-- Tutorial edit bottom sheet -->
    <el-drawer
      v-model="tutorialSheet.visible"
      direction="btt"
      size="85%"
      :title="tutorialSheet.isCreating ? '新建教程' : '编辑教程'"
      @closed="resetTutorialSheet"
    >
      <div class="sheet-body">
        <el-form label-position="top" @submit.prevent>
          <el-form-item label="标题">
            <el-input v-model="tutorialSheet.title" placeholder="教程标题" size="large" />
          </el-form-item>
          <el-form-item label="简介">
            <el-input v-model="tutorialSheet.description" placeholder="一句话说明" />
          </el-form-item>
          <el-form-item label="正文 (Markdown)">
            <el-input v-model="tutorialSheet.content" type="textarea" :autosize="{ minRows: 10, maxRows: 20 }" placeholder="编写教程内容" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="sheet-footer">
          <el-button @click="tutorialSheet.visible = false">取消</el-button>
          <el-button type="primary" :loading="tutorialSheet.loading" @click="submitTutorial">保存</el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listMyResources, updateResourceMeta,
  setResourceCover, listResourceImages,
  type MyResourceItem, type ResourceFile,
} from '../api/resources'
import { http } from '../api/http'
import {
  createTutorial, getTutorial, listMyTutorials, updateTutorial,
  type MyTutorialItem,
} from '../api/tutorials'
import ResourceEditor from '../components/ResourceEditor.vue'
import { Folder, Document, Refresh, FolderOpened, Reading, Plus, ArrowRight } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const activeTab = ref<'resources' | 'tutorials'>('resources')
const loading = ref(false)
const resourceItems = ref<MyResourceItem[]>([])
const tutorialItems = ref<MyTutorialItem[]>([])
const editorRef = ref<InstanceType<typeof ResourceEditor>>()

function toImageUrl(path?: string | null) {
  if (!path) return ''
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  return path
}
function formatDate(d: string) { return d ? dayjs(d).format('MM-DD') : '' }

// ---- Resource sheet ----
const resourceSheet = reactive({
  visible: false, loading: false, saving: false,
  id: 0, title: '', description: '', usage: '',
  files: [] as ResourceFile[], images: [] as ResourceFile[],
  coverFileId: null as number | null,
  hasNewFiles: false, hasNewImages: false,
})

async function openResource(item: MyResourceItem) {
  resourceSheet.visible = true
  resourceSheet.loading = true
  resourceSheet.id = item.id
  resourceSheet.title = item.title
  resourceSheet.description = item.description || ''
  resourceSheet.usage = item.usage || ''
  resourceSheet.files = [...item.files]
  resourceSheet.coverFileId = (item as any).coverFileId ?? null
  try {
    const res = await listResourceImages(item.id)
    resourceSheet.images = res.items || []
    if (typeof res.coverFileId === 'number' || res.coverFileId === null) {
      resourceSheet.coverFileId = res.coverFileId ?? null
    }
  } catch { ElMessage.error('加载失败') }
  finally { resourceSheet.loading = false }
}

function resetResourceSheet() {
  resourceSheet.id = 0; resourceSheet.title = ''; resourceSheet.description = ''; resourceSheet.usage = ''
  resourceSheet.files = []; resourceSheet.images = []; resourceSheet.coverFileId = null
  resourceSheet.hasNewFiles = false; resourceSheet.hasNewImages = false; resourceSheet.saving = false
}

async function saveResource() {
  resourceSheet.saving = true
  try {
    await updateResourceMeta(resourceSheet.id, { description: resourceSheet.description, usage: resourceSheet.usage })
    if (resourceSheet.hasNewFiles && editorRef.value) {
      const newFiles = editorRef.value.getNewFiles()
      if (newFiles.length) {
        const fd = new FormData()
        fd.append('resourceId', String(resourceSheet.id))
        for (const f of newFiles) { const raw = (f as any).raw; if (raw) fd.append('files', raw) }
        await http.post('/files/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      }
    }
    if (resourceSheet.hasNewImages && editorRef.value) {
      const newImages = editorRef.value.getNewImages()
      if (newImages.length) {
        const fd = new FormData()
        for (const f of newImages) { const raw = (f as any).raw; if (raw) fd.append('files', raw) }
        await http.post(`/resources/${resourceSheet.id}/images/upload`, fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      }
    }
    ElMessage.success('保存成功')
    resourceSheet.visible = false
    await fetchResources()
  } catch (e: any) { ElMessage.error(e?.response?.data?.error || '保存失败') }
  finally { resourceSheet.saving = false }
}

function downloadFile(f: ResourceFile) { window.open(`/api/files/${f.id}/download`, '_blank') }

async function removeFile(f: ResourceFile) {
  try { await ElMessageBox.confirm(`删除「${f.original_name}」？`, '提示', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }) } catch { return }
  try {
    await http.delete(`/files/${f.id}`)
    resourceSheet.files = resourceSheet.files.filter(x => x.id !== f.id)
    ElMessage.success('已删除')
    await fetchResources()
  } catch (e: any) { ElMessage.error(e?.response?.data?.error || '删除失败') }
}

async function setCover(fileId: number) {
  try {
    const res = await setResourceCover(resourceSheet.id, fileId)
    resourceSheet.coverFileId = res.coverFileId ?? null
    ElMessage.success('封面已更新')
  } catch (e: any) { ElMessage.error(e?.response?.data?.error || '设置失败') }
}

// ---- Tutorial sheet ----
const tutorialSheet = reactive({
  visible: false, loading: false, isCreating: false,
  id: 0, title: '', description: '', content: '',
})

function openTutorialCreate() {
  tutorialSheet.visible = true
  tutorialSheet.isCreating = true
  tutorialSheet.id = 0; tutorialSheet.title = ''; tutorialSheet.description = ''; tutorialSheet.content = ''
}

async function openTutorialEdit(item: MyTutorialItem) {
  tutorialSheet.visible = true
  tutorialSheet.isCreating = false
  tutorialSheet.loading = true
  tutorialSheet.id = item.id; tutorialSheet.title = item.title; tutorialSheet.description = item.description || ''
  try {
    const detail = await getTutorial(item.id)
    tutorialSheet.content = detail.content || ''
  } catch (e: any) { ElMessage.error(e?.response?.data?.error || '加载失败'); tutorialSheet.visible = false }
  finally { tutorialSheet.loading = false }
}

function resetTutorialSheet() {
  tutorialSheet.id = 0; tutorialSheet.title = ''; tutorialSheet.description = ''; tutorialSheet.content = ''
  tutorialSheet.loading = false; tutorialSheet.isCreating = false
}

async function submitTutorial() {
  const title = (tutorialSheet.title || '').trim()
  const content = (tutorialSheet.content || '').trim()
  if (!title || !content) { ElMessage.warning('标题和正文不能为空'); return }
  tutorialSheet.loading = true
  try {
    if (tutorialSheet.isCreating) {
      await createTutorial({ title, description: (tutorialSheet.description || '').trim(), content })
      ElMessage.success('已保存')
      tutorialSheet.visible = false
      await fetchTutorials()
    } else {
      await updateTutorial(tutorialSheet.id, { title, description: (tutorialSheet.description || '').trim(), content })
      ElMessage.success('已保存')
      tutorialSheet.visible = false
      await fetchTutorials()
    }
  } catch (e: any) { ElMessage.error(e?.response?.data?.error || '保存失败') }
  finally { tutorialSheet.loading = false }
}

// ---- Fetch ----
async function fetchResources() {
  loading.value = true
  try { resourceItems.value = await listMyResources() }
  catch (e: any) { ElMessage.error(e?.response?.data?.error || '加载失败') }
  finally { loading.value = false }
}
async function fetchTutorials() {
  try { tutorialItems.value = await listMyTutorials() }
  catch (e: any) { ElMessage.error(e?.response?.data?.error || '加载失败') }
}
onMounted(() => { fetchResources(); fetchTutorials() })
onBeforeUnmount(() => { editorRef.value?.abortAll() })
</script>

<style scoped>
.mobile-page { max-width: 600px; margin: 0 auto; padding: 12px; }

.mobile-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.mobile-header h1 { font-size: 20px; font-weight: 700; margin: 0; }

.tab-bar { display: flex; background: var(--el-fill-color-light); border-radius: 10px; padding: 3px; margin-bottom: 12px; }
.tab-item { flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px; padding: 8px; border-radius: 8px; cursor: pointer; font-size: 14px; color: var(--el-text-color-secondary); transition: all 0.2s; }
.tab-item.active { background: var(--el-color-primary); color: white; }

.list-area { display: flex; flex-direction: column; gap: 8px; }

.m-card { display: flex; align-items: center; gap: 12px; padding: 12px; background: white; border-radius: 12px; cursor: pointer; transition: all 0.2s; border: 1px solid var(--el-border-color-lighter); }
.m-card:active { transform: scale(0.98); }

.m-card-cover { width: 48px; height: 48px; border-radius: 8px; overflow: hidden; background: var(--el-fill-color-light); display: flex; align-items: center; justify-content: center; color: var(--el-text-color-placeholder); flex-shrink: 0; }
.m-card-cover img { width: 100%; height: 100%; object-fit: cover; }
.m-card-cover.tutorial-cover { background: var(--el-color-warning-light-9); color: var(--el-color-warning); }

.m-card-info { flex: 1; overflow: hidden; }
.m-card-title { font-size: 15px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.m-card-meta { font-size: 12px; color: var(--el-text-color-placeholder); margin-top: 2px; }
.m-card-arrow { color: var(--el-text-color-placeholder); flex-shrink: 0; }

.m-add-btn { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 14px; border: 2px dashed var(--el-border-color); border-radius: 12px; color: var(--el-text-color-secondary); cursor: pointer; font-size: 14px; }
.m-add-btn:active { border-color: var(--el-color-primary); color: var(--el-color-primary); }

.empty { padding: 40px 0; text-align: center; }

.sheet-body { padding: 0 8px; }
.sheet-footer { display: flex; gap: 8px; }
.sheet-footer .el-button { flex: 1; }
</style>
