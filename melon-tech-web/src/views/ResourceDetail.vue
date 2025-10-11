<template>
  <div class="container" v-if="data">
    <el-breadcrumb separator="/">
      <el-breadcrumb-item @click="$router.push('/resources')" style="cursor:pointer">鍒涙剰宸ュ潑</el-breadcrumb-item>
      <el-breadcrumb-item>{{ data.title }}</el-breadcrumb-item>
    </el-breadcrumb>

    <el-card class="header" shadow="never">
      <h2 class="title">{{ data.title }}</h2>
      <p class="desc" v-if="data.description">{{ data.description }}</p>

      <div class="share">
        <el-input v-model="data.shareUrl" readonly style="max-width: 520px" />
        <el-button @click="copy(data.shareUrl)">澶嶅埗閾炬帴</el-button>
        <el-divider direction="vertical" />
        <el-button :type="stats.liked ? 'success' : 'default'" @click="toggleLike">馃憤 {{ stats.likes }}</el-button>
        <el-button :type="stats.favorited ? 'warning' : 'default'" @click="toggleFav">⭐ {{ stats.favorites }}</el-button>
        <span class="dl">猬囷笍 {{ stats.downloads }}</span>
      </div>
    </el-card>

    <el-row :gutter="16">
      <el-col :xs="24" :md="16">
        <el-card shadow="hover">
          <template #header>浣跨敤鏂规硶</template>
          <div class="usage" v-if="data.usage">{{ data.usage }}</div>
          <template v-else>
            <el-empty description="鏆傛棤浣跨敤璇存槑" />
          </template>
          <template #footer>
            <small>鍒涘缓鏃堕棿锛歿{ data.created_at }}</small>
          </template>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="8">
        <el-card shadow="hover">
          <template #header>鏂囦欢</template>
          <el-empty v-if="!data.files?.length" description="鏆傛棤鏂囦欢" />
          <el-space v-else direction="vertical" alignment="stretch" style="width:100%">
            <el-card v-for="f in data.files" :key="f.id" shadow="never" class="file">
              <div class="file-row">
                <div class="name" :title="f.original_name">{{ f.original_name }}</div>
                <el-button size="small" type="primary" @click="download(f.id)">涓嬭浇</el-button>
              </div>
              <div class="meta">{{ prettySize(f.size) }} 路 {{ f.mime || 'unknown' }}</div>
            </el-card>
          </el-space>
        </el-card>
      </el-col>
    </el-row>

    <el-alert type="info" show-icon title="鏈櫥褰曚篃鑳戒笅杞? description="鍒嗕韩缁欎换浣曚汉锛屽鏂规墦寮€姝ら〉鍗冲彲鑷敱涓嬭浇" class="mt-16" />
  </div>

  <el-skeleton v-else animated :rows="6" class="container" />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getResource, getResourceStats, likeResource, unlikeResource, favoriteResource, unfavoriteResource } from '../api/resources'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuth } from '../stores/auth'

const route = useRoute()
const auth = useAuth()
const data = ref<any>(null)
const stats = ref<{ likes: number; favorites: number; downloads: number; liked?: boolean; favorited?: boolean }>({ likes: 0, favorites: 0, downloads: 0, liked: false, favorited: false })

function prettySize(n: number) {
  if (!n && n !== 0) return ''
  const units = ['B','KB','MB','GB']
  let i = 0; let v = n
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++ }
  return `${v.toFixed(1)} ${units[i]}`
}

function cleanSlug(s: string): string {
  const m = (s || '').toLowerCase().match(/([a-z0-9\-]+)/)
  return (m && m[1]) ? m[1] : s
}

async function fetch() {
  const slug = cleanSlug(route.params.slug as string)
  data.value = await getResource(slug)
  try { stats.value = await getResourceStats(data.value.id) } catch {}
}
function copy(text?: string) {
  if (!text) return
  navigator.clipboard.writeText(text).then(() => ElMessage.success('链接已复制'))
}
function toggleLike() {
  if (!auth.user) { ElMessage.warning('璇峰厛鐧诲綍'); return }
  const fn = stats.value.liked ? unlikeResource : likeResource
  fn(data.value.id).then(async () => { stats.value = await getResourceStats(data.value.id) }).catch(() => ElMessage.error('鎿嶄綔澶辫触'))
}
function toggleFav() {
  if (!auth.user) { ElMessage.warning('璇峰厛鐧诲綍'); return }
  const fn = stats.value.favorited ? unfavoriteResource : favoriteResource
  fn(data.value.id).then(async () => { stats.value = await getResourceStats(data.value.id) }).catch(() => ElMessage.error('鎿嶄綔澶辫触'))
}
function download(fileId: number) {
  window.open(`/api/files/${fileId}/download`, '_blank')
  if (data.value?.id) { setTimeout(async () => { try { stats.value = await getResourceStats(data.value.id) } catch {} }, 800) }
}
onMounted(fetch)
</script>

<style scoped>
.container { max-width: 1160px; margin: 0 auto; padding: 16px; }
.header { margin: 10px 0 16px; border-radius: 14px; }
.title { margin: 0 0 6px; font-size: 22px; font-weight: 800; }
.desc { color: var(--el-text-color-secondary); }
.share { display: flex; gap: 8px; align-items: center; margin-top: 10px; flex-wrap: wrap; }
.file { border-radius: 12px; }
.file-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 70%; }
.meta { color: var(--el-text-color-secondary); font-size: 12px; margin-top: 4px; }
.mt-16 { margin-top: 16px; }
.dl { color: var(--el-text-color-secondary); margin-left: 6px; }
</style>





