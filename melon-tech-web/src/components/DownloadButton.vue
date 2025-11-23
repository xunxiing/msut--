<template>
  <component
    :is="rootTag"
    v-bind="rootProps"
    @click="handleClick"
  >
    <slot>下载</slot>
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElButton } from 'element-plus'

const props = defineProps<{
  href: string
  downloadName?: string
  /**
   * 渲染模式：按钮或链接样式
   * - button：使用 ElButton
   * - link：使用 a 标签（用于行内“下载”链接）
   */
  as?: 'button' | 'link'
  /** ElButton type，as=button 时生效 */
  type?: '' | 'primary' | 'success' | 'warning' | 'danger' | 'info'
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'downloaded'): void
}>()

const rootTag = computed(() => (props.as === 'link' ? 'a' : ElButton))

const rootProps = computed(() => {
  if (props.as === 'link') {
    return {
      href: props.href || '#',
      role: 'button',
    }
  }
  return {
    type: props.type || 'primary',
    disabled: props.disabled,
  }
})

function triggerDownload() {
  if (!props.href || props.disabled) return

  const link = document.createElement('a')
  link.href = props.href
  if (props.downloadName !== undefined) {
    // 为空字符串也显式设置，意味着“使用后端 Content-Disposition 的文件名”
    link.download = props.downloadName || ''
  }
  link.style.display = 'none'
  document.body.appendChild(link)
  try {
    link.click()
  } finally {
    document.body.removeChild(link)
  }

  emit('downloaded')
}

function handleClick(event: MouseEvent) {
  // 阻止 a 标签默认跳转 / 新开页面
  event.preventDefault()
  triggerDownload()
}
</script>

<style scoped>
/* 默认不强制样式，把外层传入的 class 交给使用方控制。
   这里仅确保 as="link" 时看起来像文本链接。 */

a[role='button'] {
  cursor: pointer;
  color: #3b82f6;
  text-decoration: none;
}

a[role='button']:hover {
  text-decoration: underline;
}
</style>

