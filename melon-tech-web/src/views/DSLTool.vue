<template>
  <div class="page">
    <h2>DSL 生成 .melsave</h2>
    <p class="desc">输入甜瓜游乐场 DSL 代码，直接生成并下载 .melsave 文件。无需登录。</p>
    <el-form @submit.prevent>
      <el-form-item label="DSL 代码">
        <el-input
          v-model="dsl"
          type="textarea"
          :rows="16"
          placeholder="# 在此粘贴或编写 DSL（对应 input.py 内容）"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="onGenerate">生成并下载</el-button>
      </el-form-item>
    </el-form>
  </div>
  <el-alert v-if="error" type="error" :closable="false" class="mt" :title="error" />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { generateMelsave } from '../api/melsave'

const dsl = ref<string>('')
const loading = ref(false)
const error = ref('')

function parseFilenameFromHeader(disposition?: string | null): string {
  if (!disposition) return `output.melsave`
  // Expect: attachment; filename*=UTF-8''<percent-encoded>
  const m = /filename\*=UTF-8''([^;]+)/i.exec(disposition)
  if (m && m[1]) {
    try {
      return decodeURIComponent(m[1])
    } catch {}
  }
  return 'output.melsave'
}

const onGenerate = async () => {
  error.value = ''
  if (!dsl.value.trim()) {
    error.value = '请输入 DSL 内容'
    return
  }
  loading.value = true
  try {
    const resp = await generateMelsave(dsl.value)
    const blob = resp.data
    const filename = parseFilenameFromHeader(resp.headers['content-disposition'])
    const url = URL.createObjectURL(blob)
    try {
      const a = document.createElement('a')
      a.href = url
      a.download = filename || 'output.melsave'
      document.body.appendChild(a)
      a.click()
      a.remove()
    } finally {
      URL.revokeObjectURL(url)
    }
  } catch (e: any) {
    try {
      // Try to parse error JSON
      if (e?.response?.data && e.response.headers['content-type']?.includes('application/json')) {
        const reader = new FileReader()
        reader.onload = () => {
          try {
            const obj = JSON.parse(String(reader.result || '{}'))
            error.value = obj?.error || '生成失败'
          } catch {
            error.value = '生成失败'
          }
        }
        reader.readAsText(e.response.data)
      } else {
        error.value = e?.message || '生成失败'
      }
    } catch {
      error.value = '生成失败'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.page { padding: 20px; }
.desc { color: #666; margin: 10px 0 20px; }
.mt { margin: 12px 0; }
</style>

