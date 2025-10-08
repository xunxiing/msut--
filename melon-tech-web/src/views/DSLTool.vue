<template>
  <div class="dsl-page">
    <div class="header">
      <h2>DSL 工具 · 生成 .melsave</h2>
      <p class="desc">将甜瓜游乐场 DSL 粘贴到左侧，一键生成可下载的 .melsave 文件。</p>
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :md="16">
        <el-card shadow="always" class="card">
          <template #header>
            <div class="card-head">
              <span>DSL 输入</span>
              <el-button size="small" @click="dsl = ''" text>清空</el-button>
            </div>
          </template>
          <el-form @submit.prevent>
            <el-form-item label="DSL 代码">
              <el-input
                v-model="dsl"
                type="textarea"
                :rows="18"
                placeholder="# 在此粘贴或编写 DSL（等同 input.py 内容）\n# 例如：\n# OUTPUT(attrs={name: 'Result', data_type: 2})(ADD()(1, 2))"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="loading" @click="onGenerate">生成并下载</el-button>
            </el-form-item>
          </el-form>
          <el-alert v-if="error" type="error" :closable="false" class="mt" :title="error" />
        </el-card>
      </el-col>

      <el-col :xs="24" :md="8">
        <el-card shadow="hover" class="side card">
          <template #header>
            <div class="card-head">
              <span>芯片教程 · 下载</span>
            </div>
          </template>
          <p class="side-desc">下载《芯片教程.txt》，用 AI 一键生成你的 DSL。</p>
          <a :href="guideHref" download="芯片教程.txt">
            <el-button type="success" plain>下载芯片教程.txt</el-button>
          </a>
          <el-divider />
          <div class="steps">
            <h4>快速使用（以 Kimi 为例）</h4>
            <ol>
              <li>打开 Kimi AI：<a href="https://www.kimi.com/zh/" target="_blank" rel="noreferrer">https://www.kimi.com/zh/</a></li>
              <li>上传下载的《芯片教程.txt》文件。</li>
              <li>清晰描述你的需求，等待 AI 输出 DSL 代码。</li>
              <li>将 DSL 代码完整粘贴到左侧输入框，点击“生成并下载”。</li>
            </ol>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { generateMelsave } from '../api/melsave'

const dsl = ref<string>('')
const loading = ref(false)
const error = ref('')
const guideHref = '/芯片教程.txt'

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
.dsl-page { padding: 20px; }
.header { margin-bottom: 12px; }
.desc { color: var(--el-text-color-secondary); margin: 6px 0 12px; }
.card { border-radius: 12px; }
.card-head { display: flex; align-items: center; justify-content: space-between; font-weight: 600; }
.mt { margin: 12px 0; }
.side-desc { color: var(--el-text-color-regular); margin: 0 0 10px; }
.steps h4 { margin: 0 0 8px; }
.steps ol { padding-left: 18px; margin: 0; line-height: 1.8; }
</style>

