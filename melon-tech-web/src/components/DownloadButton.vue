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
import { triggerFileDownload } from '../utils/fileDownload'

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

function handleClick(event: MouseEvent) {
  event.preventDefault()
  if (!props.href || props.disabled) return
  // 未显式传入 downloadName 时，也设置 download 属性，
  // 让浏览器按服务端 Content-Disposition 或 URL 文件名下载，避免页面跳转
  const resolvedName = props.downloadName === undefined ? '' : props.downloadName
  triggerFileDownload(props.href, resolvedName)
  emit('downloaded')
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
