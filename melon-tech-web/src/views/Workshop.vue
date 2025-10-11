<template>
  <div class="container">
    <div class="header">
      <h2>创意工坊</h2>
      <div class="actions">
        <el-input v-model="q" placeholder="搜索标题或描述" clearable @clear="fetch" @keyup.enter="fetch" style="max-width:320px" />
        <el-select v-model="sort" style="width:140px" @change="fetch">
          <el-option label="按热度" value="hot" />
          <el-option label="按时间" value="time" />
          <el-option label="按点赞" value="likes" />
        </el-select>
        <el-button type="primary" @click="$router.push('/upload')">发布作品</el-button>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col v-for="r in items" :key="r.slug" :xs="24" :sm="12" :lg="8">
        <el-card class="card" shadow="hover" @click="$router.push(`/share/${r.slug}`)" style="cursor:pointer">
          <div class="title">{{ r.title }}</div>
          <div class="desc">{{ r.description || '暂无简介' }}</div>
          <div class="meta">
            <el-tag size="small">{{ r.created_at }}</el-tag>
            <div class="stats">
              <span class="stat">👍 {{ r.likeCount || 0 }}</span>
              <span class="stat">⬇️ {{ r.downloadCount || 0 }}</span>
            </div>
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
  
  <el-backtop :right="20" :bottom="40" />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { advancedListResources } from '../api/resources'

const q = ref('')
const sort = ref<'hot' | 'time' | 'likes'>('hot')
const items = ref<any[]>([])
const page = ref(1)
const pageSize = ref(12)
const total = ref(0)

async function fetch() {
  const data = await advancedListResources({ q: q.value, page: page.value, pageSize: pageSize.value, sort: sort.value, days: 7 })
  items.value = data.items
  total.value = data.total
}

onMounted(fetch)
</script>

<style scoped>
.container { max-width: 1160px; margin: 0 auto; padding: 16px; }
.header { display: flex; align-items: center; justify-content: space-between; margin: 8px 0 16px; }
.actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.title { font-weight: 700; font-size: 16px; margin-bottom: 6px; }
.desc { color: var(--el-text-color-secondary); min-height: 40px; }
.meta { margin-top: 8px; display: flex; align-items: center; justify-content: space-between; }
.stats { display: flex; gap: 10px; font-size: 12px; color: var(--el-text-color-secondary); }
.card { border-radius: 14px; }
.pager { display: flex; justify-content: center; margin: 18px 0; }
@media (max-width: 600px) {
  .desc { min-height: auto; }
}
</style>
