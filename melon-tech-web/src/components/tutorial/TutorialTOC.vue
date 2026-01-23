<template>
  <div class="doc-toc-sidebar">
    <h3 class="toc-title">内容导航</h3>
    <div class="toc-scroll-indicator-container">
      <div class="toc-scroll-indicator" :style="indicatorStyle"></div>
      <ul class="toc-list" ref="tocListRef">
        <li
          v-for="(item, idx) in items"
          :key="idx"
          class="toc-item"
          :class="{ active: activeSlug === item.slug }"
          @click="$emit('select', item.slug)"
        >
          <a
            :href="`#${item.slug}`"
            @click.prevent="$emit('select', item.slug)"
            :style="{ paddingLeft: (item.level - 1) * 12 + 10 + 'px' }"
          >
            {{ item.text }}
          </a>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  items: { text: string; level: number; slug: string }[]
  activeSlug: string | null
}>()

defineEmits(['select'])

const tocListRef = ref<HTMLElement | null>(null)

const indicatorStyle = computed(() => {
  if (!props.activeSlug || props.items.length === 0 || !tocListRef.value) {
    return { display: 'none' }
  }

  const activeIndex = props.items.findIndex(item => item.slug === props.activeSlug)
  if (activeIndex === -1) return { display: 'none' }

  const items = tocListRef.value.querySelectorAll<HTMLElement>('.toc-item')
  const activeEl = items[activeIndex]
  if (!activeEl) return { display: 'none' }

  const listRect = tocListRef.value.getBoundingClientRect()
  const itemRect = activeEl.getBoundingClientRect()
  
  return {
    transform: `translateY(${itemRect.top - listRect.top}px)`,
    height: `${itemRect.height}px`,
    display: 'block'
  }
})
</script>

<style scoped>
.doc-toc-sidebar {
  padding: 24px 16px;
  border-left: 1px solid #e2e8f0;
  overflow-y: auto;
  background: #f9fafb;
  position: relative;
  height: 100%;
}

.toc-title {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.toc-scroll-indicator-container {
  position: relative;
}

.toc-scroll-indicator {
  position: absolute;
  left: -16px;
  width: 3px;
  background: #10b981;
  border-radius: 0 3px 3px 0;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 1;
}

.toc-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.toc-item a {
  display: block;
  padding: 6px 10px;
  font-size: 13px;
  color: #64748b;
  text-decoration: none;
  border-radius: 6px;
  transition: background 0.2s, color 0.2s;
}

.toc-item a:hover {
  background: #ecfdf5;
  color: #10b981;
}

.toc-item.active a {
  background: #d1fae5;
  color: #059669;
  font-weight: 600;
}
</style>
