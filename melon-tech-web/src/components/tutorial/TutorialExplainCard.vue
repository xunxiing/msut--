<template>
  <div class="inline-explain-card" :class="{ 'is-explaining': loading }">
    <div class="ie-header">
      <div class="ie-title">
        <el-icon class="ie-icon" :class="{ rotating: loading }">
          <MagicStick v-if="!loading" />
          <Loading v-else />
        </el-icon>
        <span>AI 深度解读</span>
      </div>
      <button class="ie-close" @click="$emit('close')" title="关闭解释">
        <el-icon><Close /></el-icon>
      </button>
    </div>
    <div class="ie-content" v-html="renderedContent"></div>
    <div v-if="!loading" class="ie-footer">
      <span>内容由 AI 生成，仅供参考</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { MagicStick, Loading, Close } from '@element-plus/icons-vue'
import { marked } from 'marked'

const props = defineProps<{
  content: string
  loading: boolean
}>()

defineEmits(['close'])

const renderedContent = computed(() => {
  if (!props.content) return ''
  return marked.parse(props.content)
})
</script>

<style scoped>
.inline-explain-card {
  background: #f8fafc; /* 换成更淡雅的背景色 */
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  margin: 20px 0;
  padding: 18px;
  animation: slideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  position: relative;
  overflow: hidden;
}

.inline-explain-card::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
  background: #3b82f6; /* 改为蓝色装饰条，视觉上更沉稳 */
}

.ie-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.ie-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 700;
  color: #334155;
}

.ie-icon {
  font-size: 16px;
}

.ie-icon.rotating {
  animation: rotate 1.5s linear infinite;
}

.ie-close {
  background: transparent;
  border: none;
  color: #166534;
  padding: 4px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: background 0.2s;
}

.ie-close:hover {
  background: #dcfce7;
}

.ie-content {
  font-size: 14.5px;
  line-height: 1.7;
  color: #1e293b;
}

.ie-content :deep(p) {
  margin: 0 0 8px;
}

.ie-content :deep(p:last-child) {
  margin-bottom: 0;
}

.ie-content :deep(code) {
  background: #dcfce7;
  color: #166534;
  padding: 2px 4px;
  border-radius: 4px;
}

.ie-footer {
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px solid #dcfce7;
  font-size: 11px;
  color: #86efac;
  text-align: right;
}

@keyframes slideIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
