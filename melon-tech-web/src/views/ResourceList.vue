<template>
  <div class="container">
    <div class="header">
      <h2>文件集</h2>
      <div class="actions">
        <el-input v-model="q" placeholder="搜索标题或描述" clearable @clear="fetch" @keyup.enter="fetch" style="max-width: 320px" />
        <el-button type="primary" @click="$router.push('/upload')">上传文件</el-button>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col v-for="r in items" :key="r.slug" :xs="24" :md="12" :lg="8">
        <el-card class="card" shadow="hover" @click="$router.push(`/share/${r.slug}`)" style="cursor:pointer">
          <div class="title">{{ r.title }}</div>
          <div class="desc">{{ r.description || '暂无简介' }}</div>
          <div class="meta">
            <el-tag size="small">{{ r.created_at }}</el-tag>
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
        @current-change="p => { page = p; fetch() }"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listResources } from '../api/resources'

const q = ref('')
const items = ref<any[]>([])
const page = ref(1)
const pageSize = ref(12)
const total = ref(0)

async function fetch() {
  const data = await listResources({ q: q.value, page: page.value, pageSize: pageSize.value })
  items.value = data.items
  total.value = data.total
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
</style>
