<template>
  <div class="tutorial-list-column">
    <div class="search-box">
      <el-input
        v-model="searchTerm"
        placeholder="搜索教程标题或简介"
        clearable
        :prefix-icon="SearchIcon"
        class="modern-search"
      />
    </div>
    <div class="tutorial-menu-wrap" ref="listScrollRef" @scroll="$emit('scroll', $event)">
      <el-skeleton v-if="loading && !items.length" :rows="6" animated class="list-skeleton" />
      <div v-else class="tutorial-card-list">
        <div
          v-for="tutorial in items"
          :key="tutorial.id"
          class="tutorial-card"
          :class="{ active: selectedId === tutorial.id }"
          @click="$emit('select', tutorial.id)"
        >
          <div class="card-content">
            <h3 class="card-title">{{ tutorial.title }}</h3>
            <p class="card-desc">{{ tutorial.description || '暂无简介' }}</p>
          </div>
          <el-icon class="card-arrow"><ArrowRight /></el-icon>
        </div>
        <div v-if="!items.length" class="empty-hint">
          未找到相关教程
        </div>
      </div>
      <div v-if="loadingMore" class="list-loading-more">
        <el-icon class="loading-icon-small"><Loading /></el-icon>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Search as SearchIcon, Loading, ArrowRight } from '@element-plus/icons-vue'
import type { TutorialItem } from '../../api/tutorials'

const props = defineProps<{
  items: TutorialItem[]
  selectedId?: number
  loading: boolean
  loadingMore: boolean
  modelValue: string
}>()

const emit = defineEmits(['update:modelValue', 'select', 'scroll'])

const searchTerm = ref(props.modelValue)
watch(searchTerm, (val) => emit('update:modelValue', val))
watch(() => props.modelValue, (val) => searchTerm.value = val)

const listScrollRef = ref<HTMLElement | null>(null)
defineExpose({ listScrollRef })
</script>

<style scoped>
.tutorial-list-column {
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
  min-height: 0;
  height: 100%;
}

@media (max-width: 900px) {
  .tutorial-list-column {
    border-radius: 0;
    border: none;
    box-shadow: none;
  }
}

.search-box {
  padding: 16px;
  background: #fff;
  z-index: 10;
}

.modern-search :deep(.el-input__wrapper) {
  border-radius: 10px;
  box-shadow: 0 0 0 1px #e2e8f0 inset;
  padding: 4px 12px;
}

.tutorial-menu-wrap {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px 16px;
}

.tutorial-card-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 4px;
}

.tutorial-card {
  padding: 16px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #f1f5f9;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.tutorial-card:hover {
  background: #f8fafc;
  border-color: #e2e8f0;
  transform: translateY(-1px);
}

.tutorial-card.active {
  background: #eff6ff;
  border-color: #bfdbfe;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.08);
}

.card-title {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-desc {
  margin: 0;
  font-size: 13px;
  color: #64748b;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
  word-break: break-all;
}

.card-arrow {
  color: #cbd5e1;
  transition: transform 0.2s;
}

.tutorial-card:hover .card-arrow {
  transform: translateX(3px);
  color: var(--el-color-primary);
}

.empty-hint {
  text-align: center;
  padding: 40px 20px;
  color: #94a3b8;
}

.list-loading-more {
  display: flex;
  justify-content: center;
  padding: 12px;
}
</style>
