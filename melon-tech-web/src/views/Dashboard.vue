<template>
  <div class="settings-container">
    <el-card class="settings-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">个人设置</span>
          <el-button text circle @click="refresh" :loading="refreshing" class="refresh-btn">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
      </template>

      <el-skeleton v-if="loading" animated :rows="6" />

      <template v-else>
        <el-alert v-if="error" :title="error" type="error" show-icon class="mb-4" />

        <div v-if="profile" class="profile-content">
          <!-- 头部：头像与基本信息 -->
          <div class="profile-header">
            <div class="avatar-section">
              <el-avatar :size="100" :src="profile.avatarUrl || undefined" class="profile-avatar">
                {{ avatarFallback }}
              </el-avatar>
              <el-upload
                class="avatar-uploader"
                action="/api/auth/avatar/upload"
                :show-file-list="false"
                :with-credentials="true"
                accept="image/*"
                :before-upload="beforeAvatarUpload"
                :on-success="onAvatarSuccess"
                :on-error="onAvatarError"
              >
                <div class="camera-badge">
                  <el-icon><Camera /></el-icon>
                </div>
              </el-upload>
            </div>
            
            <div class="info-section">
              <h2 class="username">{{ profile.name }}</h2>
              <p class="user-id">ID: {{ profile.username }}</p>
            </div>
          </div>

          <!-- 表单区域 -->
          <el-form label-position="top" class="settings-form" @submit.prevent>
            <div class="form-group">
              <label class="custom-label">个性签名</label>
              <div class="custom-textarea-wrapper">
                <el-input
                  v-model="signature"
                  type="textarea"
                  :autosize="{ minRows: 4, maxRows: 6 }"
                  maxlength="200"
                  show-word-limit
                  placeholder="写点什么介绍一下自己吧…"
                  class="custom-textarea"
                />
              </div>
            </div>

            <div class="actions">
              <el-button type="primary" :loading="saving" @click="save" size="large" round class="action-btn save-btn">
                保存修改
              </el-button>
              <el-button plain type="danger" @click="onLogout" size="large" round class="action-btn logout-btn">
                退出登录
              </el-button>
            </div>
          </el-form>
        </div>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { http } from '../api/http'
import { useAuth } from '../stores/auth'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { Refresh, Camera } from '@element-plus/icons-vue'

type Profile = {
  id: number
  username: string
  name: string
  avatarUrl: string
  signature: string
}

const auth = useAuth()
const router = useRouter()

const loading = ref(true)
const refreshing = ref(false)
const saving = ref(false)
const error = ref('')

const profile = ref<Profile | null>(null)
const signature = ref('')

const avatarFallback = computed(() => {
  const n = profile.value?.name || ''
  return n ? n.slice(0, 1) : '?'
})

const refresh = async () => {
  refreshing.value = true
  error.value = ''
  try {
    const { data } = await http.get('/auth/profile')
    profile.value = data.user || null
    signature.value = profile.value?.signature || ''
  } catch (e: any) {
    error.value = e?.response?.data?.error || '加载失败'
  } finally {
    refreshing.value = false
    loading.value = false
  }
}

const save = async () => {
  if (!profile.value) return
  saving.value = true
  try {
    const { data } = await http.patch('/auth/profile', { signature: signature.value })
    const next = (data?.user || profile.value) as Profile | null
    if (next) {
      profile.value = next
      signature.value = next.signature || ''
    }
    ElMessage.success('已保存')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.error || '保存失败')
  } finally {
    saving.value = false
  }
}

const beforeAvatarUpload = (file: File) => {
  const okType = ['image/png', 'image/jpeg', 'image/gif', 'image/webp'].includes(file.type)
  if (!okType) {
    ElMessage.error('只支持 PNG/JPG/GIF/WebP')
    return false
  }
  const okSize = file.size <= 5 * 1024 * 1024
  if (!okSize) {
    ElMessage.error('头像最大 5MB')
    return false
  }
  return true
}

const onAvatarSuccess = (resp: any) => {
  if (profile.value && resp?.avatarUrl) {
    profile.value.avatarUrl = resp.avatarUrl
  }
  ElMessage.success('头像已更新')
}

const onAvatarError = () => {
  ElMessage.error('头像上传失败')
}

const onLogout = async () => {
  await auth.logout()
  ElMessage.success('已退出')
  router.replace('/login')
}

onMounted(refresh)
</script>

<style scoped>
.settings-container {
  max-width: 500px;
  margin: 20px auto;
  padding: 0 16px;
}

/* 卡片样式优化 */
.settings-card {
  border-radius: 20px;
  background: #ffffff;
  border: none;
  box-shadow: 0 10px 40px -10px rgba(0,0,0,0.05);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
}

.title {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a1a;
  letter-spacing: -0.5px;
}

.refresh-btn {
  color: #888;
}

.refresh-btn:hover {
  color: var(--el-color-primary);
  background-color: var(--el-color-primary-light-9);
}

/* 个人信息头部 */
.profile-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 24px 0 32px;
}

.avatar-section {
  position: relative;
  margin-bottom: 16px;
}

.profile-avatar {
  border: 4px solid #fff;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-size: 36px;
  font-weight: 600;
}

.avatar-uploader {
  position: absolute;
  bottom: 0;
  right: 0;
}

/* 相机小图标 */
.camera-badge {
  width: 32px;
  height: 32px;
  background: var(--el-color-primary);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  border: 3px solid #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  cursor: pointer;
  transition: transform 0.2s;
}

.camera-badge:active {
  transform: scale(0.9);
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.username {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #1f2937;
}

.user-id {
  margin: 0;
  font-size: 14px;
  color: #9ca3af;
  font-family: 'Menlo', 'Monaco', monospace;
  background: #f3f4f6;
  padding: 2px 8px;
  border-radius: 6px;
  display: inline-block;
}

/* 表单样式定制 */
.form-group {
  margin-bottom: 24px;
}

.custom-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #4b5563;
  margin-bottom: 8px;
  margin-left: 4px;
}

.custom-textarea-wrapper {
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,0.03);
  transition: box-shadow 0.2s;
}

.custom-textarea-wrapper:focus-within {
  box-shadow: 0 4px 16px rgba(var(--el-color-primary-rgb), 0.15);
}

/* 覆盖 Element Plus 输入框样式 */
:deep(.custom-textarea .el-textarea__inner) {
  border-radius: 12px;
  padding: 12px;
  background-color: #f9fafb;
  border: 1px solid #e5e7eb;
  font-size: 15px;
  line-height: 1.6;
  transition: all 0.2s;
  box-shadow: none !important; /* 移除默认阴影 */
}

:deep(.custom-textarea .el-textarea__inner:focus) {
  background-color: #fff;
  border-color: var(--el-color-primary);
}

/* 按钮组 */
.actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 32px;
}

.action-btn {
  width: 100%;
  font-weight: 600;
  height: 44px;
  margin-left: 0 !important; /* 强制移除 Element Plus 按钮左侧默认 margin */
}

.save-btn {
  box-shadow: 0 4px 12px rgba(var(--el-color-primary-rgb), 0.3);
}

.logout-btn {
  background: #fff;
}

/* 移动端适配 */
@media (max-width: 480px) {
  .settings-container {
    padding: 0 12px;
    margin-top: 12px;
  }
  
  .settings-card {
    border-radius: 16px;
  }

  .profile-header {
    padding: 16px 0 24px;
  }

  .username {
    font-size: 20px;
  }
  
  .actions {
    grid-template-columns: 1fr;
    gap: 12px;
  }
}

/* 暗黑模式适配 */
@media (prefers-color-scheme: dark) {
  .settings-card {
    background: #1e1e1e;
    box-shadow: none;
    border: 1px solid #333;
  }
  
  .title {
    color: #e5e7eb;
  }

  .profile-avatar {
    border-color: #1e1e1e;
  }
  
  .camera-badge {
    border-color: #1e1e1e;
  }
  
  .username {
    color: #f3f4f6;
  }
  
  .user-id {
    background: #2d2d2d;
    color: #9ca3af;
  }
  
  .custom-label {
    color: #d1d5db;
  }
  
  :deep(.custom-textarea .el-textarea__inner) {
    background-color: #2d2d2d;
    border-color: #404040;
    color: #e5e7eb;
  }
  
  :deep(.custom-textarea .el-textarea__inner:focus) {
    background-color: #1a1a1a;
    border-color: var(--el-color-primary);
  }
  
  .logout-btn {
    background: transparent;
  }
}
</style>
