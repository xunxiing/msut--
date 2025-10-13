<template>
  <div class="container" v-if="data">
    <el-breadcrumb separator="/">
      <el-breadcrumb-item @click="$router.push('/resources')" style="cursor:pointer">文件</el-breadcrumb-item>
      <el-breadcrumb-item>{{ data.title }}</el-breadcrumb-item>
    </el-breadcrumb>

    <el-card class="header" shadow="never">
      <h2 class="title">{{ data.title }}</h2>
      <p class="desc" v-if="data.description">{{ data.description }}</p>

      <div class="share">
        <el-input v-model="data.shareUrl" readonly style="max-width: 520px" />
        <el-button @click="copy(data.shareUrl)">复制链接</el-button>
        <div class="likes-bar">
          <button class="like-btn" :class="{ liked: !!resourceLike?.liked }" @click="toggleResourceLike" :title="resourceLike?.liked ? '已赞' : '点赞'">
            <svg class="like-icon" viewBox="0 0 24 24" aria-hidden="true">
              <path :fill="resourceLike?.liked ? '#f44336' : 'currentColor'" d="M12.1 21.35l-1.1-1.02C5.14 14.88 2 12.06 2 8.5 2 6 4 4 6.5 4c1.54 0 3.04.81 3.9 2.09C11.46 4.81 12.96 4 14.5 4 17 4 19 6 19 8.5c0 3.56-3.14 6.38-8.9 11.83l-1.0 1.02z" />
            </svg>
            <span class="count">{{ resourceLike?.likes || 0 }}</span>
          </button>
          <el-button v-if="auth.user" size="large" class="like-action" @click="toggleResourceLike">{{ resourceLike?.liked ? '已赞' : '点赞' }}</el-button>
        </div>
      </div>
    </el-card>

    <el-row :gutter="16">
      <el-col :xs="24" :md="16">
        <el-card shadow="hover">
          <template #header>使用方法</template>
          <div class="usage" v-if="data.usage">{{ data.usage }}</div>
          <template v-else>
            <el-empty description="暂无使用说明" />
          </template>
          <template #footer>
            <small>创建时间：{{ data.created_at }} · 作者：{{ (data as any).author_name || '未知' }}</small>
          </template>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="8">
        <el-card shadow="hover">
          <template #header>文件</template>
          <el-empty v-if="!data.files?.length" description="暂无文件" />
          <el-space v-else direction="vertical" alignment="stretch" style="width:100%">
            <el-card v-for="f in data.files" :key="f.id" shadow="never" class="file">
              <div class="file-row">
                <div class="name" :title="f.original_name">{{ f.original_name }}</div>
                <el-button size="small" type="primary" @click="download(f.id)">下载</el-button>
              </div>
              <div class="meta">{{ prettySize(f.size) }} · {{ f.mime || 'unknown' }}</div>
            </el-card>
          </el-space>
        </el-card>
      </el-col>
    </el-row>

    <el-alert type="info" show-icon title="未登录也能下载" description="分享给任何人，对方打开此页即可自由下载" class="mt-16" />
  </div>

  <el-skeleton v-else animated :rows="6" class="container" />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getResource } from '../api/resources'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getResourceLikes, likeResource, unlikeResource, type LikeInfo } from '../api/likes'
import { useAuth } from '../stores/auth'

const route = useRoute()
const data = ref<any>(null)
const auth = useAuth()
const resourceLike = ref<LikeInfo | null>(null)

function prettySize(n: number) {
  if (!n && n !== 0) return ''
  const units = ['B','KB','MB','GB']
  let i = 0; let v = n
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++ }
  return `${v.toFixed(1)} ${units[i]}`
}

async function fetch() {
  data.value = await getResource(route.params.slug as string)
  if (data.value?.id) {
    const items = await getResourceLikes([data.value.id])
    resourceLike.value = items[0] || { id: data.value.id, likes: 0, liked: false }
  }
}
function copy(text: string) {
  navigator.clipboard.writeText(text).then(() => ElMessage.success('链接已复制'))
}
function download(fileId: number) {
  // 直接打开后端公开下载接口
  window.open(`/api/files/${fileId}/download`, '_blank')
}
async function toggleResourceLike() {
  try {
    if (!auth.user) {
      ElMessage.warning('请先登录')
      return
    }
    const current = resourceLike.value
    if (!current) return
    if (current.liked) {
      const r = await unlikeResource(current.id)
      resourceLike.value = { id: current.id, likes: r.likes, liked: r.liked }
    } else {
      const r = await likeResource(current.id)
      resourceLike.value = { id: current.id, likes: r.likes, liked: r.liked }
    }
  } catch (e: any) {
    const msg = e?.response?.data?.error || '操作失败'
    ElMessage.error(msg)
  }
}
onMounted(fetch)
</script>

<style scoped>
.container { max-width: 1160px; margin: 0 auto; padding: 16px; }
.header { margin: 10px 0 16px; border-radius: 14px; }
.title { margin: 0 0 6px; font-size: 22px; font-weight: 800; }
.desc { color: var(--el-text-color-secondary); }
.share { display: flex; gap: 8px; align-items: center; margin-top: 10px; }
.file { border-radius: 12px; }
.file-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 70%; }
.likes-bar { display: flex; align-items: center; gap: 10px; margin-left: auto; }
.like-btn { display: inline-flex; align-items: center; gap: 6px; background: transparent; border: none; cursor: pointer; padding: 2px 6px; color: var(--el-text-color-secondary); }
.like-btn .like-icon { width: 28px; height: 28px; }
.like-btn .count { font-size: 14px; }
.like-btn.liked { color: #f44336; }
.meta { color: var(--el-text-color-secondary); font-size: 12px; margin-top: 4px; }
.mt-16 { margin-top: 16px; }
.like-action { transform: scale(1.2); transform-origin: center left; }
</style>
