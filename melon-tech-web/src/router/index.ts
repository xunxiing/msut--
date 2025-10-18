import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuth } from '../stores/auth'

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'home', component: () => import('../views/Home.vue') },
  { path: '/about', name: 'about', component: () => import('../views/About.vue') },
  { path: '/dashboard', name: 'dashboard', meta: { requiresAuth: true }, component: () => import('../views/Dashboard.vue') },
  { path: '/my/resources', name: 'my-resources', meta: { requiresAuth: true }, component: () => import('../views/MyResources.vue') },
  { path: '/login', name: 'login', component: () => import('../views/Login.vue') },
  { path: '/register', name: 'register', component: () => import('../views/Register.vue') },
  { path: '/resources', name: 'resources', component: () => import('../views/ResourceList.vue') },
  { path: '/upload', name: 'upload', meta: { requiresAuth: true }, component: () => import('../views/Upload.vue') },
  { path: '/dsl', name: 'dsl-tool', component: () => import('../views/DSLTool.vue') },
  { path: '/watermark', name: 'watermark', component: () => import('../views/Watermark.vue') },
  { path: '/share/:slug', name: 'resource-detail', component: () => import('../views/ResourceDetail.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuth()
  if (auth.user === null) {
    // 首次进入或刷新后尝试同步会话
    await auth.fetchMe().catch(() => {})
  }
  if (to.meta.requiresAuth && !auth.user) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
})

export default router
