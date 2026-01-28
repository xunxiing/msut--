<template>
  <div class="comment-form-wrapper">
    <!-- 当前用户头像 -->
    <div class="user-avatar-col" v-if="auth.user">
      <el-avatar 
        :size="40" 
        :src="auth.user.avatarUrl || undefined"
        class="current-avatar"
      >
        {{ auth.user.name?.[0]?.toUpperCase() || '?' }}
      </el-avatar>
    </div>
    
    <div class="comment-form-main">
      <div class="custom-textarea-wrapper">
        <el-input
          v-model="localContent"
          type="textarea"
          :rows="rows"
          :placeholder="placeholder"
          maxlength="500"
          show-word-limit
          class="custom-textarea"
        />
      </div>
      <div class="form-actions">
        <span class="login-hint" v-if="!auth.user">请先登录后发表评论</span>
        <div class="action-buttons">
          <el-button v-if="showCancel" text @click="handleCancel" class="cancel-btn">取消</el-button>
          <el-button type="primary" :disabled="!canSubmit" @click="handleSubmit" round class="submit-btn">发布</el-button>
        </div>
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
.comment-form-wrapper {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.user-avatar-col {
  flex-shrink: 0;
  padding-top: 2px;
}

.current-avatar {
  background-color: var(--el-color-primary-light-8);
  color: var(--el-color-primary);
  border: 1px solid var(--el-color-primary-light-5);
}

.comment-form-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0; /* Fix flex child overflow */
}

.custom-textarea-wrapper {
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,0.03);
  transition: box-shadow 0.2s;
}

.custom-textarea-wrapper:focus-within {
  box-shadow: 0 4px 16px rgba(var(--el-color-primary-rgb), 0.15);
}

:deep(.custom-textarea .el-textarea__inner) {
  border-radius: 12px;
  padding: 12px;
  background-color: #f9fafb;
  border: 1px solid #e5e7eb;
  font-size: 15px;
  line-height: 1.6;
  transition: all 0.2s;
  box-shadow: none !important;
}

:deep(.custom-textarea .el-textarea__inner:focus) {
  background-color: #fff;
  border-color: var(--el-color-primary);
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
  margin-left: auto;
}

.submit-btn {
  padding: 8px 24px;
  font-weight: 600;
}

@media (max-width: 768px) {
  .comment-form-wrapper {
    gap: 12px;
  }
  
  .user-avatar-col {
    display: none; /* Mobile optimization: hide avatar if space is tight, OR keep it but smaller. 
                     The user ASKED for avatar, so keeping it is safer. 
                     But typical mobile chat apps show avatar.
                     Let's Keep it. */
    display: block; 
  }
  
  .form-actions {
    flex-direction: column;
    align-items: flex-end; /* Align right */
    gap: 12px;
  }

  .action-buttons {
    width: 100%;
    justify-content: flex-end;
  }
  
  .submit-btn {
    flex: 1; 
  }
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  :deep(.custom-textarea .el-textarea__inner) {
    background-color: #2d2d2d;
    border-color: #404040;
    color: #e5e7eb;
  }
  
  :deep(.custom-textarea .el-textarea__inner:focus) {
    background-color: #1a1a1a;
  }
  
  .current-avatar {
    background-color: #1e293b;
    border-color: #334155;
  }
}
</style>
