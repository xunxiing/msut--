<template>
  <div class="comment-form">
    <el-input
      v-model="localContent"
      type="textarea"
      :rows="rows"
      :placeholder="placeholder"
      maxlength="500"
      show-word-limit
    />
    <div class="form-actions">
      <span class="login-hint" v-if="!auth.user">请先登录后发表评论</span>
      <div class="action-buttons">
        <el-button v-if="showCancel" text @click="handleCancel">取消</el-button>
        <el-button type="primary" :disabled="!canSubmit" @click="handleSubmit">发布</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useAuth } from '../stores/auth'

const props = withDefaults(
  defineProps<{
    content?: string
    placeholder?: string
    rows?: number
    showCancel?: boolean
  }>(),
  {
    content: '',
    placeholder: '写下你的想法吧…',
    rows: 3,
    showCancel: false,
  }
)

const emit = defineEmits<{
  (e: 'submit', content: string): void
  (e: 'cancel'): void
}>()

const auth = useAuth()
const localContent = ref(props.content)

watch(
  () => props.content,
  value => {
    localContent.value = value
  }
)

const canSubmit = computed(() => {
  return !!auth.user && localContent.value.trim().length > 0
})

function handleSubmit() {
  if (!canSubmit.value) return
  emit('submit', localContent.value.trim())
  localContent.value = ''
}

function handleCancel() {
  localContent.value = props.content || ''
  emit('cancel')
}
</script>

<style scoped>
.comment-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.login-hint {
  font-size: 13px;
  color: #94a3b8;
}

.action-buttons {
  display: flex;
  gap: 12px;
}

@media (max-width: 768px) {
  .form-actions {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .action-buttons {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
