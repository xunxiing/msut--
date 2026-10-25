import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuth } from '../stores/auth'

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'home', meta: { title: '首页' }, component: () => import('../views/Home.vue') },
  { path: '/m', name: 'home-mobile', meta: { title: '首页' }, component: () => import('../views/HomeMobile.vue') },
  { path: '/about', name: 'about', meta: { title: '关于项目' }, component: () => import('../views/About.vue') },
  { path: '/dashboard', name: 'dashboard', meta: { title: '控制面板', requiresAuth: true }, component: () => import('../views/Dashboard.vue') },
  { path: '/my/resources', name: 'my-resources', meta: { title: '我的作品', requiresAuth: true }, component: () => import('../views/MyResources.vue') },
  { path: '/m/my/resources', name: 'my-resources-mobile', meta: { title: '我的作品', requiresAuth: true }, component: () => import('../views/MyResourcesMobile.vue') },
  { path: '/login', name: 'login', meta: { title: '登录' }, component: () => import('../views/Login.vue') },
  { path: '/register', name: 'register', meta: { title: '注册' }, component: () => import('../views/Register.vue') },
  { path: '/tutorials', name: 'tutorials', meta: { title: '教程问答' }, component: () => import('../views/TutorialRAG.vue') },
  { path: '/tutorials/library', name: 'tutorials-library', meta: { title: '教程知识库' }, component: () => import('../views/TutorialLibrary.vue') },
  { path: '/resources', name: 'resources', meta: { title: '免费模组库' }, component: () => import('../views/ResourceList.vue') },
  { path: '/m/resources', name: 'resources-mobile', meta: { title: '免费模组库' }, component: () => import('../views/ResourceListMobile.vue') },
  { path: '/external', name: 'external-resource', meta: { title: '站外资源' }, component: () => import('../views/ExternalResourceDetail.vue') },
  { path: '/upload', name: 'upload', meta: { title: '上传作品', requiresAuth: true }, component: () => import('../views/Upload.vue') },
  { path: '/dsl', name: 'dsl-tool', meta: { title: 'DSL 芯片代码生成器' }, component: () => import('../views/DSLTool.vue') },
  { path: '/watermark', name: 'watermark', meta: { title: '防盗水印检测' }, component: () => import('../views/Watermark.vue') },
  { path: '/share/:slug', name: 'resource-detail', meta: { title: '模组详情' }, component: () => import('../views/ResourceDetail.vue') },
  { path: '/creator/:username', name: 'creator-stats', meta: { title: '创作者主页' }, component: () => import('../views/CreatorStats.vue') },
  { path: '/tutorials/ai', name: 'tutorials-ai', meta: { title: 'AI 辅助创作' }, component: () => import('../views/TutorialAI.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuth()
  if (auth.user === null) {
    // 首次进入或刷新后尝试同步会话
    await auth.fetchMe().catch(() => { })
  }
  if (to.meta.requiresAuth && !auth.user) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
})

router.afterEach((to) => {
  if (to.meta && to.meta.title && to.name !== 'home' && to.name !== 'home-mobile') {
    document.title = `${to.meta.title} | MSUT 甜瓜联合科技`
  } else {
    document.title = 'MSUT 甜瓜联合科技 - 甜瓜游乐场模组下载_在线工具_存档创作社区'
  }
})

export default router
