<template>
  <el-container class="settings-page">
    <el-main>
      <el-card>
        <template #header>设置</template>

        <el-skeleton v-if="loading" animated :rows="4" />

        <template v-else>
          <el-alert v-if="error" :title="error" type="error" show-icon />

          <el-form v-if="profile" label-width="90px" class="form" @submit.prevent>
            <el-form-item label="账号">
              <el-input :model-value="profile.username" disabled />
            </el-form-item>

            <el-form-item label="昵称">
              <el-input :model-value="profile.name" disabled />
            </el-form-item>

            <el-form-item label="头像">
              <div class="avatar-row">
                <el-avatar :size="72" :src="profile.avatarUrl || undefined">
                  {{ avatarFallback }}
                </el-avatar>
                <el-upload
                  action="/api/auth/avatar/upload"
                  :show-file-list="false"
                  :with-credentials="true"
                  :before-upload="beforeAvatarUpload"
                  :on-success="onAvatarSuccess"
                  :on-error="onAvatarError"
                >
                  <el-button type="primary">更换头像</el-button>
                </el-upload>
              </div>
              <div class="hint">支持 PNG/JPG/GIF/WebP，最大 5MB</div>
            </el-form-item>

            <el-form-item label="个性签名">
              <el-input
                v-model="signature"
                type="textarea"
                :autosize="{ minRows: 2, maxRows: 5 }"
                maxlength="200"
                show-word-limit
                placeholder="写点什么介绍一下自己吧…"
              />
            </el-form-item>

            <el-form-item>
              <el-space wrap>
                <el-button type="success" :loading="saving" @click="save">保存</el-button>
                <el-button :loading="refreshing" @click="refresh">刷新</el-button>
                <el-button type="danger" plain @click="onLogout">退出登录</el-button>
              </el-space>
            </el-form-item>
          </el-form>
        </template>
      </el-card>
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { http } from '../api/http'
import { useAuth } from '../stores/auth'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

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
.settings-page {
  min-height: 70vh;
}
.form {
  margin-top: 12px;
}
.avatar-row {
  display: flex;
  align-items: center;
  gap: 14px;
}
.hint {
  font-size: 12px;
  color: #64748b;
  margin-top: 6px;
}
</style>
