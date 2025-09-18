<template>
  <el-container style="min-height: 70vh">
    <el-main>
      <el-card>
        <template #header>控制台</template>
        <p>欢迎，{{ auth.user?.name }}（{{ auth.user?.email }}）</p>
        <el-space>
          <el-button type="primary" @click="ping">测试受保护接口</el-button>
          <el-button @click="onLogout">退出登录</el-button>
        </el-space>
        <el-alert v-if="msg" :title="msg" type="success" show-icon style="margin-top:12px" />
      </el-card>
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuth } from '../stores/auth'
import { http } from '../api/http'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

const auth = useAuth()
const router = useRouter()
const msg = ref('')

const ping = async () => {
  const { data } = await http.get('/private/ping')
  msg.value = data.pong ? '受保护接口可用' : ''
}

const onLogout = async () => {
  await auth.logout()
  ElMessage.success('已退出')
  router.replace('/login')
}
</script>
