<template>
  <div>
    <el-menu
      mode="horizontal"
      :router="true"
      :default-active="$route.path"
      :ellipsis="false"
      :class="['topbar', { 'is-menu-open': menuOpen }]"
    >
      <el-menu-item index="/" class="brand">🍉 甜瓜联合科技</el-menu-item>
      <el-menu-item index="/about" class="nav-item">关于</el-menu-item>
      <el-menu-item index="/dsl" class="nav-item">DSL 工具</el-menu-item>
      <el-menu-item index="/watermark" class="nav-item">水印检测</el-menu-item>
      <el-menu-item index="/resources" class="nav-item">文件库</el-menu-item>
      <el-menu-item v-if="auth.user" index="/dashboard" class="nav-item">控制台</el-menu-item>
      <el-menu-item v-if="auth.user" index="/my/resources" class="nav-item">我的存档</el-menu-item>
      <el-menu-item v-if="auth.user" index="/upload" class="nav-item">上传文件</el-menu-item>
      <button class="menu-toggle" @click.stop="toggleMenu" aria-label="打开菜单" :aria-expanded="menuOpen ? 'true' : 'false'" title="菜单" v-show="!menuOpen">
        <span class="bars" aria-hidden="true"><i></i><i></i><i></i></span>
      </button>
      <div class="flex-spacer"></div>
      <template v-if="!auth.user">
        <el-menu-item index="/login" class="nav-item">登录</el-menu-item>
        <el-menu-item index="/register" class="nav-item">注册</el-menu-item>
      </template>
      <el-menu-item v-else @click="onLogout" class="nav-item">退出</el-menu-item>

      <!-- 顶栏内的折叠按钮已移除 -->
    </el-menu>

    <transition name="fade">
      <div v-if="menuOpen" :class="['menu-backdrop', isMobile ? 'mobile' : 'desktop']" @click.self="closeMenu">
        <div :class="['menu-panel', isMobile ? 'mobile' : 'desktop']">
          <div class="menu-panel-header">
            <div class="menu-title">导航菜单</div>
            <button class="menu-close" @click="closeMenu" aria-label="关闭">✕</button>
          </div>
          <div class="menu-grid">
            <div
              v-for="item in visibleItems"
              :key="item.path || item.key"
              class="menu-card"
              @click="onMenuCardClick(item)"
            >
              <div class="menu-card-icon">{{ item.icon }}</div>
              <div class="menu-card-text">{{ item.label }}</div>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <router-view />
  </div>
  
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useAuth } from './stores/auth'
import { useRouter } from 'vue-router'

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

// 菜单卡片项（按需根据登录态显示）
type MenuItem = { label: string; icon: string; path?: string; key?: string; action?: () => void }
const allItems = computed<MenuItem[]>(() => {
  const common: MenuItem[] = [
    { label: '首页', icon: '🏠', path: '/' },
    { label: '关于', icon: 'ℹ️', path: '/about' },
    { label: 'DSL 工具', icon: '🧩', path: '/dsl' },
    { label: '水印检测', icon: '💧', path: '/watermark' },
    { label: '文件库', icon: '📁', path: '/resources' },
  ]
  const authed: MenuItem[] = [
    { label: '控制台', icon: '📊', path: '/dashboard' },
    { label: '我的存档', icon: '📚', path: '/my/resources' },
    { label: '上传文件', icon: '⬆️', path: '/upload' },
    { label: '退出登录', icon: '🚪', key: 'logout', action: onLogout },
  ]
  const guest: MenuItem[] = [
    { label: '登录', icon: '🔑', path: '/login' },
    { label: '注册', icon: '📝', path: '/register' },
  ]
  return auth.user ? [...common, ...authed] : [...common, ...guest]
})

const visibleItems = computed(() => allItems.value)

const onMenuCardClick = async (item: MenuItem) => {
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
  padding: 0 20px;
  box-shadow: 0 2px 10px rgba(0,0,0,.04);
  align-items: center;
}
.topbar.is-menu-open { pointer-events: none; }
.brand { font-weight: 800; }
.flex-spacer { flex: 1; }

/* 右上角更明显的折叠按钮（移动端更醒目） */
.menu-toggle {
  margin-left: 10px;
  background: transparent;
  border: none;
  padding: 0;
  line-height: 1;
  font-size: 0; /* 由 bars 绘制图标 */
  cursor: pointer;
  transition: all .3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 38px;
  position: relative;
}
.menu-toggle:hover { 
  transform: scale(1.05);
}
.menu-toggle:active {
  transform: scale(0.95);
}
/* 三条横线图标 */
.menu-toggle .bars { 
  display: inline-flex; 
  flex-direction: column; 
  gap: 4px; 
  width: 22px;
  height: 16px;
}
.menu-toggle .bars i { 
  display: block; 
  width: 22px; 
  height: 2.5px; 
  background: #4fc08d; 
  border-radius: 3px;
  transition: all .3s ease;
}
/* 添加悬停效果 */
.menu-toggle:hover .bars i {
  background: #2ecc71;
}

/* 背景虚化与遮罩 */
.menu-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.18);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  z-index: 4000;
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
}

/* 桌面端：菜单占据上半屏，从顶部展开 */
.menu-backdrop.desktop { 
  align-items: flex-start; 
  justify-content: center; 
  padding-top: 60px;
}
/* 移动端：维持右上角弹出位置 */
.menu-backdrop.mobile { align-items: flex-start; justify-content: flex-end; }

/* 菜单卡片面板 */
.menu-panel {
  background: #fff;
  color: #222;
  border-radius: 16px;
  box-shadow: 0 12px 32px rgba(0,0,0,.12);
  margin: 16px;
  overflow: hidden;
  position: relative;
  z-index: 4001; /* 确保在顶栏之上，避免重合 */
}
.menu-panel.desktop { 
  width: 100%; 
  max-width: none;
  height: 50vh;
  margin: 0;
  margin-bottom: auto;
  transform: scale(1);
  border-radius: 0 0 24px 24px;
  left: 0;
  right: 0;
}
.menu-panel.mobile { width: 100%; height: calc(100% - 32px); }

.menu-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(0,0,0,.06);
}
.menu-title { font-weight: 700; }
.menu-close {
  border: none;
  background: transparent;
  font-size: 18px;
  cursor: pointer;
  color: #666;
}
.menu-close:hover { color: #000; }

.menu-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 2px;
  padding: 16px;
  padding-bottom: 20px;
}
@media (min-width: 480px) {
  .menu-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (min-width: 768px) {
  .menu-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0 2px; }
}
@media (min-width: 1200px) {
  .menu-grid { grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 0 2px; }
}

.menu-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 30px 22px;
  border-radius: 0;
  border: 1px solid rgba(0,0,0,.06);
  background: linear-gradient(to right, rgba(124, 227, 161, .15), rgba(124, 227, 161, .05), rgba(255, 255, 255, 0));
  cursor: pointer;
  transition: all .15s ease;
  text-align: left;
  margin-bottom: 8px;
}
.menu-card:hover, .menu-card:active {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(0,0,0,.08);
  border-color: rgba(34, 139, 34, .7);
  background: linear-gradient(to right, 
    rgba(34, 139, 34, .45) 0%, 
    rgba(34, 139, 34, .45) 15%,
    rgba(34, 139, 34, .35) 25%,
    rgba(34, 139, 34, .25) 35%,
    rgba(34, 139, 34, .15) 50%,
    rgba(34, 139, 34, .08) 70%,
    rgba(34, 139, 34, .05) 100%);
}
.menu-card:active {
  background: linear-gradient(to right, rgba(34, 139, 34, .85), rgba(34, 139, 34, .55), rgba(255, 255, 255, 0));
  border-color: rgba(34, 139, 34, .9);
  box-shadow: 0 8px 16px rgba(34, 139, 34, .2);
}
.menu-card-icon { 
  font-size: 24px; 
  line-height: 1;
  color: #4fc08d;
}
.menu-card-text { 
  font-weight: 600; 
  font-size: 17px;
  color: #555;
  margin-left: auto;
  text-align: right;
}

/* 移动端：隐藏顶栏大多数菜单项，仅保留品牌与折叠按钮，点击后全屏展开；增强按钮可见性 */
@media (max-width: 768px) {
  .topbar :deep(.el-menu-item).nav-item { display: none !important; }
  .menu-toggle { 
    margin-left: 4px; 
    width: 40px;
    height: 34px;
    background: transparent;
  }
  .menu-panel.mobile { height: calc(100% - 32px); }
}

/* 过渡动画 */
.fade-enter-active, .fade-leave-active { transition: opacity .15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* 隐藏 Element Plus 横向菜单的“更多(…)”溢出入口，避免出现三点按钮 */
.topbar :deep(.el-sub-menu) { display: none !important; }
</style>
