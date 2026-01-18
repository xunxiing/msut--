<template>
  <div class="comment-list">
    <div class="comment-header">
      <h3 class="section-title">评论区</h3>
      <div class="comment-meta">{{ total }} 条评论</div>
    </div>

    <div class="comment-editor">
      <CommentForm @submit="handleCreate" placeholder="写下你的评论" />
    </div>

    <div v-if="loading" class="comment-loading">
      <el-skeleton animated :rows="3" />
    </div>

    <div v-else>
      <div v-if="items.length" class="comment-items">
        <CommentItem
          v-for="item in items"
          :key="item.id"
          :item="item"
          @reply="handleReply"
          @update="handleUpdate"
          @delete="handleDelete"
          @like="handleLike"
        />
      </div>
      <div v-else class="comment-empty">还没有评论，来聊聊吧。</div>
    </div>

    <div v-if="total > pageSize" class="comment-pagination">
      <el-pagination
        background
        layout="prev, pager, next"
        :page-size="pageSize"
        :current-page="page"
        :total="total"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createComment,
  deleteComment,
  likeComment,
  listResourceComments,
  unlikeComment,
  updateComment,
  type CommentItem as CommentItemType,
} from '../api/comments'
import { useAuth } from '../stores/auth'
import CommentForm from './CommentForm.vue'
import CommentItem from './CommentItem.vue'

const props = defineProps<{ resourceId: number }>()

const auth = useAuth()
const items = ref<CommentItemType[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)

const canInteract = computed(() => !!auth.user)

async function fetchComments() {
  if (!props.resourceId) return
  loading.value = true
  try {
    const data = await listResourceComments(props.resourceId, page.value, pageSize.value)
    items.value = data.items || []
    total.value = data.total || 0
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.error || '加载评论失败')
  } finally {
    loading.value = false
  }
}

async function handleCreate(content: string) {
  if (!canInteract.value) {
    ElMessage.warning('请先登录')
    return
  }
  try {
    await createComment(props.resourceId, { content })
    page.value = 1
    await fetchComments()
    ElMessage.success('评论已发布')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.error || '评论失败')
  }
}

async function handleReply(payload: { parentId: number; content: string }) {
  if (!canInteract.value) {
    ElMessage.warning('请先登录')
    return
  }
  try {
    await createComment(props.resourceId, { content: payload.content, parentId: payload.parentId })
    await fetchComments()
    ElMessage.success('回复已发布')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.error || '回复失败')
  }
}

async function handleUpdate(payload: { id: number; content: string }) {
  try {
    await updateComment(payload.id, { content: payload.content })
    await fetchComments()
    ElMessage.success('评论已更新')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.error || '更新失败')
  }
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确定删除这条评论吗？', '提示', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteComment(id)
    await fetchComments()
    ElMessage.success('评论已删除')
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e?.response?.data?.error || '删除失败')
    }
  }
}

async function handleLike(id: number) {
  if (!canInteract.value) {
    ElMessage.warning('请先登录')
    return
  }
  const target = findCommentById(items.value, id)
  if (!target) return
  try {
    if (target.liked) {
      const data = await unlikeComment(id)
      target.liked = data.liked
      target.likes = data.likes
    } else {
      const data = await likeComment(id)
      target.liked = data.liked
      target.likes = data.likes
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.error || '操作失败')
  }
}

function handlePageChange(value: number) {
  page.value = value
  fetchComments()
}

function findCommentById(list: CommentItemType[], id: number): CommentItemType | null {
  for (const item of list) {
    if (item.id === id) return item
    if (item.children?.length) {
      const found = findCommentById(item.children, id)
      if (found) return found
    }
  }
  return null
}

onMounted(fetchComments)

watch(
  () => props.resourceId,
  () => {
    page.value = 1
    fetchComments()
  }
)
</script>

<style scoped>
.comment-list {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  border: 1px solid #f1f5f9;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

.comment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.comment-meta {
  color: #94a3b8;
  font-size: 13px;
}

.comment-editor {
  margin-bottom: 24px;
}

.comment-items {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.comment-empty {
  text-align: center;
  color: #94a3b8;
  padding: 24px 0;
}

.comment-pagination {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}

@media (max-width: 768px) {
  .comment-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}
</style>
