<template>
  <div>
    <el-menu mode="horizontal" :router="true" :default-active="$route.path" class="topbar">
      <el-menu-item index="/" class="brand">🍉 甜瓜联合科技</el-menu-item>
      <el-menu-item index="/about">关于</el-menu-item>
      <el-menu-item index="/dsl">DSL 工具</el-menu-item>
      <el-menu-item index="/watermark">水印检测</el-menu-item>
      <el-menu-item index="/resources">文件集</el-menu-item>
      <el-menu-item v-if="auth.user" index="/dashboard">控制台</el-menu-item>
      <el-menu-item v-if="auth.user" index="/my/resources">我的存档</el-menu-item>
      <el-menu-item v-if="auth.user" index="/upload">上传文件</el-menu-item>
      <div style="flex: 1"></div>
      <template v-if="!auth.user">
        <el-menu-item index="/login">登录</el-menu-item>
        <el-menu-item index="/register">注册</el-menu-item>
      </template>
      <el-menu-item v-else @click="onLogout">退出</el-menu-item>
    </el-menu>
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { useAuth } from './stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuth()
const router = useRouter()

const onLogout = async () => {
  await auth.logout()
  router.replace('/login')
}
</script>

<style scoped>
.topbar {
  position: sticky;
  top: 0;
  z-index: 100;
  padding: 0 20px;
  box-shadow: 0 2px 10px rgba(0,0,0,.04);
}
.brand {
  font-weight: 800;
}
</style>
