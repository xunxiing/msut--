<template>
  <div class="container">
    <div class="header">
      <h2>文件列表</h2>
      <div class="actions">
        <el-input v-model="q" placeholder="搜索主题内容" clearable @clear="fetch" @keyup.enter="fetch" style="max-width: 320px" />
        <el-button type="primary" @click="$router.push('/upload')">涓婁紶鏂囦欢</el-button>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col v-for="r in items" :key="r.slug" :xs="24" :md="12" :lg="8">
        <el-card class="card" shadow="hover" @click="$router.push(`/share/${r.slug}`)" style="cursor:pointer">
          <div class="title">{{ r.title }}</div>
          <div class="desc">{{ r.description || '暂无描述' }}</div>
          <div class="meta">`r`n            <el-tag size="small">{{ r.created_at }}</el-tag>`r`n            <span class="likes">❤ {{ likesMap[r.id]?.likes || 0 }}</span>`r`n          </div>
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
import { listResources, type ResourceItem } from '../api/resources'
import { getResourceLikes, type LikeInfo } from '../api/likes'

const q = ref('')
const items = ref<ResourceItem[]>([])
const page = ref(1)
const pageSize = ref(12)
const total = ref(0)
const likesMap = ref<Record<number, LikeInfo>>({})

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

onMounted(fetch)
</script>

<style scoped>
.container { max-width: 1160px; margin: 0 auto; padding: 16px; }
.header { display: flex; align-items: center; justify-content: space-between; margin: 8px 0 16px; }
.title { font-weight: 700; font-size: 16px; margin-bottom: 6px; }
.desc { color: var(--el-text-color-secondary); min-height: 40px; }
.meta { margin-top: 8px; }
.card { border-radius: 14px; }
.pager { display: flex; justify-content: center; margin: 18px 0; }
.actions { display: flex; gap: 10px; align-items: center; }
.likes { margin-left: 8px; color: var(--el-text-color-secondary); font-size: 12px; }
</style>


