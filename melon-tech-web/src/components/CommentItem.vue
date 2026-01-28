<template>
  <div class="comment-item" :class="{ 'is-reply': depth > 0 }">
    <div class="comment-header">
      <div class="comment-author">
        <el-avatar 
          :size="40" 
          :src="item.user.avatarUrl || undefined" 
          class="avatar-el"
        >
          {{ initials }}
        </el-avatar>
        <div class="author-info">
          <div class="author-name">{{ item.user.name || item.user.username || '用户' }}</div>
          <div class="comment-meta">{{ formatTime(item.created_at) }}</div>
        </div>
      </div>
      <div class="comment-actions">
        <el-button text size="small" @click="toggleReply">回复</el-button>
        <el-button v-if="isOwner" text size="small" @click="toggleEdit">编辑</el-button>
        <el-button v-if="isOwner" text size="small" @click="handleDelete">删除</el-button>
      </div>
    </div>

    <div class="comment-body" v-if="!isEditing">
      <p class="comment-content">{{ item.content }}</p>
    </div>

    <CommentForm
      v-else
      :content="item.content"
      placeholder="编辑评论"
      :rows="3"
      show-cancel
      @submit="handleUpdate"
      @cancel="toggleEdit(false)"
    />

    <div class="comment-footer">
      <el-button
        text
        size="small"
        :class="['like-btn', item.liked ? 'is-liked' : '']"
        @click="handleLike"
      >
        <span>👍</span>
        <span>{{ item.likes }}</span>
      </el-button>
      <span class="reply-hint" v-if="item.parent_id && replyTo">回复 {{ replyTo }}</span>
    </div>

    <div v-if="showReply" class="reply-form">
      <CommentForm
        placeholder="写下回复"
        :rows="2"
        show-cancel
        @submit="handleReply"
        @cancel="toggleReply(false)"
      />
    </div>

    <div v-if="item.children?.length" class="comment-children">
      <CommentItem
        v-for="child in item.children"
        :key="child.id"
        :item="child"
        :depth="depth + 1"
        @reply="emitReply"
        @update="emitUpdate"
        @delete="emitDelete"
        @like="emitLike"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAuth } from '../stores/auth'
import type { CommentItem as CommentItemType } from '../api/comments'
import CommentForm from './CommentForm.vue'

const props = defineProps<{
  item: CommentItemType
  depth?: number
}>()

const emit = defineEmits<{
  (e: 'reply', payload: { parentId: number; content: string }): void
  (e: 'update', payload: { id: number; content: string }): void
  (e: 'delete', id: number): void
  (e: 'like', id: number): void
}>()

const auth = useAuth()
const depth = computed(() => props.depth ?? 0)
const showReply = ref(false)
const isEditing = ref(false)

const isOwner = computed(() => {
  return auth.user?.id === props.item.user_id
})

const initials = computed(() => {
  const name = props.item.user.name || props.item.user.username || 'U'
  return name.slice(0, 1).toUpperCase()
})

const replyTo = computed(() => props.item.user.name || props.item.user.username)

function formatTime(value: string) {
  return value ? value.replace('T', ' ').replace('Z', '') : ''
}

function toggleReply(force?: boolean) {
  if (!auth.user) {
    showReply.value = false
    return
  }
  showReply.value = force ?? !showReply.value
}

function toggleEdit(force?: boolean) {
  isEditing.value = force ?? !isEditing.value
}

function handleReply(content: string) {
  emit('reply', { parentId: props.item.id, content })
  showReply.value = false
}

function handleUpdate(content: string) {
  emit('update', { id: props.item.id, content })
  isEditing.value = false
}

function handleDelete() {
  emit('delete', props.item.id)
}

function handleLike() {
  emit('like', props.item.id)
}

function emitReply(payload: { parentId: number; content: string }) {
  emit('reply', payload)
}

function emitUpdate(payload: { id: number; content: string }) {
  emit('update', payload)
}

function emitDelete(id: number) {
  emit('delete', id)
}

function emitLike(id: number) {
  emit('like', id)
}
</script>

<style scoped>
.comment-item {
  padding: 16px;
  border-radius: 14px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}

.comment-item.is-reply {
  background: #f8fafc;
}

.comment-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.comment-author {
  display: flex;
  gap: 12px;
  align-items: center;
}

.avatar-el {
  background: #e0f2fe;
  color: #0f172a;
  font-weight: 700;
  border: 1px solid #e0f2fe;
}

.author-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.author-name {
  font-weight: 600;
  color: #0f172a;
}

.comment-meta {
  font-size: 12px;
  color: #94a3b8;
}

.comment-actions {
  display: flex;
  gap: 6px;
}

.comment-body {
  margin-top: 12px;
  padding-left: 52px; /* Align with text start (40px avatar + 12px gap) */
}

.comment-content {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.6;
  color: #334155;
}

.comment-footer {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  color: #64748b;
  padding-left: 52px; /* Align with text start */
}

.like-btn.is-liked {
  color: #ef4444;
}

.reply-hint {
  font-size: 12px;
}

.reply-form {
  margin-top: 12px;
  padding-left: 52px;
}

.comment-children {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  border-left: 2px solid #e2e8f0;
  padding-left: 16px;
  margin-left: 20px; /* Slightly indented */
}

@media (max-width: 768px) {
  .comment-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .comment-actions {
    width: 100%;
    justify-content: flex-start;
    padding-left: 52px; /* Align with text */
    margin-top: -8px;
    margin-bottom: 8px;
  }
  
  .comment-body, .comment-footer, .reply-form {
    padding-left: 0; /* Reset indentation on mobile for space */
  }
}
</style>
