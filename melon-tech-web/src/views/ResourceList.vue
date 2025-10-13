<template>
  <div class="container">
    <div class="header">
      <h2>文件列表</h2>
      <div class="actions">
        <el-input v-model="q" placeholder="搜索主题内容" clearable @clear="fetch" @keyup.enter="fetch" style="max-width: 320px" />
        <el-button type="primary" @click="$router.push('/upload')">上传文件</el-button>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col v-for="r in items" :key="r.slug" :xs="24" :md="12" :lg="8">
        <el-card class="card" shadow="hover" @click="$router.push(`/share/${r.slug}`)" style="cursor:pointer">
          <div class="title">{{ r.title }}</div>
          <div class="desc">{{ r.description || '暂无描述' }}</div>
          <div class="meta">
            <el-tag size="small">{{ r.created_at }}</el-tag>
            <button
              class="like-btn"
              :class="{ liked: !!likesMap[r.id]?.liked }"
              title="点赞"
              @click.stop="toggleLike(r.id)"
            >
              <svg class="like-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path
                  :fill="likesMap[r.id]?.liked ? '#f44336' : 'currentColor'"
                  d="M12.1 21.35l-1.1-1.02C5.14 14.88 2 12.06 2 8.5 2 6 4 4 6.5 4c1.54 0 3.04.81 3.9 2.09C11.46 4.81 12.96 4 14.5 4 17 4 19 6 19 8.5c0 3.56-3.14 6.38-8.9 11.83l-1.0 1.02z"
                />
              </svg>
              <span class="count">{{ likesMap[r.id]?.likes || 0 }}</span>
            </button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <div class="pager">
      <el-pagination
        background
        layout="prev, pager, next"
        :page-size="pageSize"
        :current-page="page"
        :total="total"
        @current-change="(p: number) => { page = p; fetch() }"
      />
    </div>
  </div>
  </template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listResources, type ResourceItem } from '../api/resources'
import { getResourceLikes, likeResource, unlikeResource, type LikeInfo } from '../api/likes'
import { useAuth } from '../stores/auth'

const q = ref('')
const items = ref<ResourceItem[]>([])
const page = ref(1)
const pageSize = ref(12)
const total = ref(0)
const likesMap = ref<Record<number, LikeInfo>>({})
const auth = useAuth()

async function fetch() {
  const data = await listResources({ q: q.value, page: page.value, pageSize: pageSize.value })
  items.value = data.items
  total.value = data.total
  const ids = (items.value || []).map(r => r.id)
  const likes = await getResourceLikes(ids)
  const m: Record<number, LikeInfo> = {}
  likes.forEach(i => { m[i.id] = i })
  likesMap.value = m
}

async function toggleLike(id: number) {
  try {
    if (!auth.user) {
      ElMessage.warning('请先登录')
      return
    }
    const current = likesMap.value[id] || { id, likes: 0, liked: false }
    if (current.liked) {
      const r = await unlikeResource(id)
      likesMap.value = { ...likesMap.value, [id]: { id, likes: r.likes, liked: r.liked } }
    } else {
      const r = await likeResource(id)
      likesMap.value = { ...likesMap.value, [id]: { id, likes: r.likes, liked: r.liked } }
    }
  } catch (e: any) {
    const msg = e?.response?.data?.error || '操作失败'
    ElMessage.error(msg)
  }
}

onMounted(fetch)
</script>

<style scoped>
.container { 
  max-width: 1160px; 
  margin: 0 auto; 
  padding: 16px;
  position: relative;
  background: radial-gradient(1200px 600px at 50% -200px, var(--el-color-success-light-7), transparent 70%),
              linear-gradient(180deg, rgba(16,185,129,.06), rgba(255,255,255,0));
}
.container::after {
  content: '';
  position: absolute;
  inset: -20% -10% auto -10%;
  height: 360px;
  background:
    radial-gradient(400px 200px at 15% -30px, rgba(16,185,129,.12), transparent 70%),
    radial-gradient(400px 200px at 85% -30px, rgba(16,185,129,.12), transparent 70%);
  filter: blur(20px);
  pointer-events: none;
  z-index: -1;
}
.header { display: flex; align-items: center; justify-content: space-between; margin: 8px 0 16px; }
.title { font-weight: 700; font-size: 16px; margin-bottom: 6px; }
.desc { color: var(--el-text-color-secondary); min-height: 40px; }
.meta { margin-top: 8px; display: flex; align-items: center; gap: 10px; }
.card { border-radius: 14px; }
.pager { display: flex; justify-content: center; margin: 18px 0; }
.actions { display: flex; gap: 10px; align-items: center; }
.like-btn { display: inline-flex; align-items: center; gap: 6px; background: transparent; border: none; cursor: pointer; padding: 2px 6px; color: var(--el-text-color-secondary); }
.like-btn .like-icon { width: 24px; height: 24px; }
.like-btn .count { font-size: 14px; }
.like-btn.liked { color: #f44336; }
</style>

