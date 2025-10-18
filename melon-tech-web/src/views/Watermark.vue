<template>
  <div class="page">
    <div class="header">
      <h2>水印检测</h2>
      <p class="desc">上传 .melsave 存档，计算其水印并在数据库中查找可能的匹配文件。</p>
    </div>

    <el-card class="card">
      <el-form @submit.prevent label-width="100px">
        <el-form-item label="选择文件">
          <input type="file" accept=".melsave,.zip" @change="onPick" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :disabled="!picked" :loading="loading" @click="onCheck">开始检测</el-button>
        </el-form-item>
      </el-form>
      <el-alert v-if="error" type="error" :closable="false" class="mt" :title="error" />

      <div v-if="result" class="result mt">
        <el-descriptions title="检测结果" :column="1" border>
          <el-descriptions-item label="Watermark (u64)">{{ result.watermark }}</el-descriptions-item>
          <el-descriptions-item label="序列长度">{{ result.length }}</el-descriptions-item>
          <el-descriptions-item label="内嵌水印">{{ result.embedded ?? '无' }}</el-descriptions-item>
        </el-descriptions>
        <el-divider />
        <h4>数据库匹配</h4>
        <el-empty v-if="!result.matches.length" description="未找到匹配" />
        <el-table v-else :data="result.matches" size="small" stripe>
          <el-table-column prop="originalName" label="文件名" min-width="140" />
          <el-table-column prop="resourceTitle" label="资源标题" min-width="160" />
          <el-table-column prop="resourceSlug" label="资源" min-width="120">
            <template #default="{ row }">
              <router-link v-if="row.resourceSlug" :to="`/share/${row.resourceSlug}`">{{ row.resourceSlug }}</router-link>
              <span v-else>—</span>
            </template>
          </el-table-column>
          <el-table-column label="下载" min-width="100">
            <template #default="{ row }">
              <a :href="row.urlPath" target="_blank">下载</a>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
  </div>
  
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { checkWatermark } from '../api/watermark'

const picked = ref<File | null>(null)
const loading = ref(false)
const error = ref('')
const result = ref<Awaited<ReturnType<typeof checkWatermark>> | null>(null)

function onPick(e: Event) {
  const input = e.target as HTMLInputElement
  picked.value = input.files && input.files[0] ? input.files[0] : null
}

async function onCheck() {
  if (!picked.value) return ElMessage.warning('请先选择 .melsave 文件')
  error.value = ''
  result.value = null
  loading.value = true
  try {
    result.value = await checkWatermark(picked.value)
  } catch (e: any) {
    error.value = e?.response?.data?.error || e?.message || '检测失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.page { padding: 20px; }
.header { margin-bottom: 12px; }
.desc { color: var(--el-text-color-secondary); margin: 6px 0 12px; }
.card { border-radius: 12px; }
.mt { margin-top: 12px; }
</style>

