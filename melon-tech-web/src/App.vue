<template>
  <div class="app-root">
    <el-menu
      mode="horizontal"
      :router="true"
      :default-active="$route.path"
      :ellipsis="false"
      :class="['topbar', { 'drawer-open': menuOpen }]"
    >
      <button
        v-if="!menuOpen"
        class="menu-toggle start"
        @click.stop="toggleMenu"
        aria-label="打开菜单"
        title="菜单"
      >
        <span class="bars" aria-hidden="true"><i></i><i></i><i></i></span>
      </button>

      <el-menu-item index="/" class="brand">🍉 甜瓜联合科技</el-menu-item>
      <el-menu-item index="/daily" class="nav-item">🔥 每日推荐</el-menu-item>
      <el-menu-item index="/resources" class="nav-item">文件库</el-menu-item>
      <el-menu-item index="/tutorials" class="nav-item">教程中心 <span class="ai-badge">AI+</span></el-menu-item>
      <el-menu-item index="/dsl" class="nav-item">DSL 工具</el-menu-item>
      <el-menu-item index="/watermark" class="nav-item">水印检测</el-menu-item>
      <el-menu-item index="/about" class="nav-item">关于</el-menu-item>
      <el-menu-item v-if="auth.user" index="/dashboard" class="nav-item">设置</el-menu-item>
      <el-menu-item v-if="auth.user" index="/my/resources" class="nav-item">作品管理</el-menu-item>
      <el-menu-item v-if="auth.user" index="/upload" class="nav-item">上传文件</el-menu-item>

      <div class="flex-spacer"></div>
      <NotificationBell v-if="auth.user" class="nav-item" />
      <template v-if="!auth.user">
        <el-menu-item index="/login" class="nav-item">登录</el-menu-item>
        <el-menu-item index="/register" class="nav-item">注册</el-menu-item>
      </template>
      <el-menu-item v-else @click="onLogout" class="nav-item logout-btn">退出</el-menu-item>

    </el-menu>

    <transition name="drawer">
      <div v-if="menuOpen" class="menu-backdrop" @click.self="closeMenu">
        <aside class="menu-drawer" role="dialog" aria-label="导航菜单">
          <div class="menu-drawer-header">
            <div class="menu-title">导航菜单</div>
            <button class="menu-toggle close" @click="closeMenu" aria-label="关闭">
              <span class="bars" aria-hidden="true"><i></i><i></i><i></i></span>
            </button>
          </div>

          <nav class="menu-list">
            <div class="menu-section">
              <div class="menu-section-title">通用</div>
              <button
                v-for="item in commonItems"
                :key="'c-' + (item.path || item.key)"
                class="menu-item"
                @click="onMenuItemClick(item)"
              >
                <component v-if="item.icon" :is="item.icon" class="mi-icon" aria-hidden="true" />
                <span class="mi-label">{{ item.label }}</span>
                <span v-if="item.badge" class="ai-badge">{{ item.badge }}</span>
              </button>
            </div>

            <div class="menu-section">
              <div class="menu-section-title">我的</div>
              <button
                v-for="item in myItems"
                :key="'m-' + (item.path || item.key)"
                class="menu-item"
                @click="onMenuItemClick(item)"
              >
                <component v-if="item.icon" :is="item.icon" class="mi-icon" aria-hidden="true" />
                <span class="mi-label">{{ item.label }}</span>
                <span v-if="item.badge" class="ai-badge">{{ item.badge }}</span>
              </button>
            </div>
          </nav>
        </aside>
      </div>
    </transition>

    <router-view />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, type Component } from 'vue'
import { useAuth } from './stores/auth'
import { useRouter } from 'vue-router'
import { House, InfoFilled, Connection, Watermelon, Folder, DataAnalysis, Collection, Upload, User, EditPen, SwitchButton, Star } from '@element-plus/icons-vue'
import NotificationBell from './components/NotificationBell.vue'


const auth = useAuth()
const router = useRouter()

const onLogout = async () => {
  await auth.logout()
  router.replace('/login')
}

// 折叠菜单状态与响应式断点
const menuOpen = ref(false)
const isMobile = ref(false)

const updateIsMobile = () => {
  isMobile.value = window.innerWidth <= 768
}

onMounted(() => {
  updateIsMobile()
  window.addEventListener('resize', updateIsMobile)
  window.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', updateIsMobile)
  window.removeEventListener('keydown', onKeydown)
})

const toggleMenu = () => { menuOpen.value = !menuOpen.value }
const closeMenu = () => { menuOpen.value = false }
const onKeydown = (e: KeyboardEvent) => { if (e.key === 'Escape') closeMenu() }

type MenuItem = { label: string; icon?: Component; path?: string; key?: string; action?: () => void; badge?: string }

const commonItems = computed<MenuItem[]>(() => [
  { label: '首页', icon: House, path: '/' },
  { label: '每日推荐', icon: Star, path: '/daily', badge: 'HOT' },
  { label: '文件库', icon: Folder, path: '/resources' },
  { label: '教程中心', icon: Collection, path: '/tutorials', badge: 'AI+' },
  { label: 'DSL 工具', icon: Connection, path: '/dsl' },
  { label: '水印检测', icon: Watermelon, path: '/watermark' },
  { label: '关于', icon: InfoFilled, path: '/about' },
])

const myItems = computed<MenuItem[]>(() => {
  if (auth.user) {
    return [
      { label: '设置', icon: DataAnalysis, path: '/dashboard' },
      { label: '作品管理', icon: Collection, path: '/my/resources' },
      { label: '上传文件', icon: Upload, path: '/upload' },
      { label: '退出登录', icon: SwitchButton, key: 'logout', action: onLogout },
    ]
  }
  return [
    { label: '登录', icon: User, path: '/login' },
    { label: '注册', icon: EditPen, path: '/register' },
  ]
})

const onMenuItemClick = async (item: MenuItem) => {
  if (item.action) {
    await item.action()
    menuOpen.value = false
    return
  }
  if (item.path) {
    router.push(item.path)
    menuOpen.value = false
  }
}
</script>

<style scoped>
.topbar {
  position: sticky;
  top: 0;
  z-index: 100;
  height: 56px;
  line-height: 56px;
  padding: 0 16px;
  box-shadow: 0 2px 10px rgba(0,0,0,.04);
  align-items: center;
  width: 100%; /* Changed from 100vw to 100% to prevent scrollbar overflow */
  max-width: 100vw;
  box-sizing: border-box;
  transition: padding-left 0.2s ease;
}
@media (min-width: 769px) {
  .topbar.drawer-open {
    padding-left: 340px;
  }
}
.brand { font-weight: 800; }
.flex-spacer { flex: 1; }
.logout-btn {
  transition: transform .2s ease;
}

/* 左上角汉堡按钮 */
.menu-toggle {
  margin-left: 10px;
  background: transparent;
  border: none;
  padding: 0;
  line-height: 1;
  font-size: 0;
  cursor: pointer;
  transition: all .2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 38px;
}
.menu-toggle.start { margin-left: 8px; margin-right: 8px; }
.menu-toggle .bars { display: inline-flex; flex-direction: column; gap: 4px; width: 22px; height: 16px; }
.menu-toggle .bars i { display: block; width: 22px; height: 2.5px; background: #4fc08d; border-radius: 3px; transition: all .2s ease; }
.menu-toggle:hover .bars i { background: #2ecc71; }
.menu-toggle.close { margin-left: auto; width: 38px; height: 34px; }

/* 抽屉容器与过渡 */
.menu-backdrop {
  position: fixed; inset: 0; background: rgba(33, 150, 243, 0.04);
  z-index: 4000; display: flex; align-items: flex-start; justify-content: flex-start;
  padding-top: 8px; padding-left: 4px;
}
.menu-drawer {
  background: #fff; color: #222; border-radius: 16px;
  box-shadow: 0 12px 32px rgba(0,0,0,.12);
  width: 320px; max-width: calc(100% - 16px);
  height: calc(100% - 16px);
  overflow: hidden; position: relative; z-index: 4001;
  transition: transform .2s ease;
}
.menu-drawer-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 12px 12px 8px; border-bottom: 1px solid rgba(0,0,0,.06); }
.menu-title { font-weight: 700; }

/* 进入/离开时抽屉从左滑入/滑出 */
.drawer-enter-from .menu-drawer { transform: translateX(-340px); }
.drawer-leave-to .menu-drawer { transform: translateX(-340px); }

/* 列表与组标题 */
.menu-list { padding: 8px 8px 16px; overflow-y: auto; max-height: calc(100% - 48px); }
.menu-section { margin-top: 8px; }
.menu-section-title { margin: 8px 8px 6px; font-size: 12px; font-weight: 700; color: #6b7280; letter-spacing: .04em; text-transform: uppercase; }
.menu-item {
  width: 100%; display: flex; align-items: center; gap: 12px;
  padding: 8px 10px; border-radius: 10px; border: 1px solid transparent;
  background: transparent; cursor: pointer; min-height: 36px;
}
.menu-item:hover { background: #f5faf7; border-color: rgba(76,175,80,.25); }
.menu-item:active { background: #e8f5e9; border-color: rgba(46,125,50,.35); }
.menu-item:active .mi-icon { color: #2e7d32; }
.menu-item:active .mi-label { color: #111827; }
.menu-list :deep(.mi-icon) { width: 18px; height: 18px; font-size: 18px; color: #4CAF50; flex: none; }
.mi-label { font-size: 17px; color: #1f2937; }
.ai-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  background: linear-gradient(135deg, rgba(30, 58, 138, 0.9), rgba(59, 130, 246, 0.8));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  padding: 2px 0;
  margin-left: 5px;
  position: relative;
  animation: twinkle 2.5s infinite ease-in-out;
  line-height: 1.4;
  letter-spacing: 0.5px;
  transform: translateY(-1px);
}
.ai-badge::before {
  content: "★";
  position: absolute;
  top: -7px;
  right: -9px;
  font-size: 10px;
  color: rgba(147, 197, 253, 0.9);
  animation: pulse 2s infinite ease-in-out;
  text-shadow: 0 0 4px rgba(147, 197, 253, 0.6);
}
.ai-badge::after {
  content: "";
  position: absolute;
  width: 120%;
  height: 140%;
  top: -20%;
  left: -10%;
  background: radial-gradient(circle, rgba(30, 58, 138, 0.25) 0%, rgba(59, 130, 246, 0.15) 50%, transparent 70%);
  border-radius: 50%;
  z-index: -1;
  animation: glow 3.5s infinite ease-in-out;
}
@keyframes twinkle {
  0%, 100% { opacity: 0.7; transform: scale(0.98); }
  25% { opacity: 0.9; transform: scale(1.02); }
  50% { opacity: 1; transform: scale(1.05); }
  75% { opacity: 0.9; transform: scale(1.02); }
}
@keyframes pulse {
  0%, 100% { opacity: 0.5; transform: scale(0.95); text-shadow: 0 0 3px rgba(147, 197, 253, 0.3); }
  25% { opacity: 0.8; transform: scale(1.05); text-shadow: 0 0 5px rgba(147, 197, 253, 0.6); }
  50% { opacity: 1; transform: scale(1.15); text-shadow: 0 0 8px rgba(147, 197, 253, 0.9); }
  75% { opacity: 0.8; transform: scale(1.05); text-shadow: 0 0 5px rgba(147, 197, 253, 0.6); }
}
@keyframes glow {
  0% { opacity: 0.2; transform: scale(0.7); }
  25% { opacity: 0.4; transform: scale(0.9); }
  50% { opacity: 0.7; transform: scale(1.2); }
  75% { opacity: 0.4; transform: scale(0.9); }
  100% { opacity: 0.2; transform: scale(0.7); }
}

/* 移动端仅保留品牌与汉堡按钮 */
@media (max-width: 768px) {
  .topbar :deep(.el-menu-item).nav-item { display: none !important; }
  
  /* Make brand smaller on mobile */
  .brand {
    padding: 0 12px !important;
    font-size: 14px !important;
    margin-right: auto !important; /* Push everything else to right */
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

/* 隐藏 Element Plus 横向菜单的“更多”入口（...） */
.topbar :deep(.el-sub-menu) { display: none !important; }

.topbar :deep(.bell-button) {
  color: #475569;
}

.topbar :deep(.bell-button:hover) {
  color: #0f172a;
}


/* 抽屉淡入背景整体过渡（仅用于透明背景下的轻微渐显） */
.drawer-enter-active, .drawer-leave-active { transition: opacity .15s ease; }
.drawer-enter-from, .drawer-leave-to { opacity: 0; }
</style>
