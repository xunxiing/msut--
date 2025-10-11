<template>
  <div>
    <el-menu mode="horizontal" :router="true" :default-active="$route.path" class="topbar">
      <el-menu-item index="/" class="brand">🍉 Melon Tech</el-menu-item>
      <el-menu-item index="/about">关于</el-menu-item>
      <el-menu-item index="/dsl">DSL 实验室</el-menu-item>
      <el-menu-item index="/resources">创意工坊</el-menu-item>
      <el-menu-item v-if="auth.user" index="/upload">上传文件</el-menu-item>
      <div style="flex: 1"></div>
      <template v-if="!auth.user">
        <el-menu-item index="/login">登录</el-menu-item>
        <el-menu-item index="/register">注册</el-menu-item>
      </template>
      <el-menu-item v-else @click="onLogout">退出登录</el-menu-item>
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

