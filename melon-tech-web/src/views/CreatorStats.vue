<template>
  <div class="creator-page" v-if="stats">
    <div class="creator-header">
      <el-avatar :size="64" :src="stats.user.avatar_url || undefined" class="creator-avatar">
        {{ stats.user.username.charAt(0).toUpperCase() }}
      </el-avatar>
      <div class="creator-info">
        <h2 class="creator-name">{{ stats.user.username }}</h2>
        <p class="creator-signature" v-if="stats.user.signature">{{ stats.user.signature }}</p>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{{ stats.resource_count }}</div>
        <div class="stat-label">模组作品</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_downloads }}</div>
        <div class="stat-label">总下载量</div>
      </div>
    </div>

    <div class="top-section" v-if="stats.top_resources.length">
      <h3 class="section-title">热门作品</h3>
      <div class="top-list">
        <router-link
          v-for="(r, i) in stats.top_resources"
          :key="r.id"
          :to="`/share/${r.slug}`"
          class="top-item"
        >
          <span class="top-rank">{{ i + 1 }}</span>
          <div class="top-info">
            <div class="top-title">{{ r.title }}</div>
            <div class="top-meta">
              <span>⬇ {{ r.download_count }} 次下载</span>
              <span>·</span>
              <span>{{ r.created_at }}</span>
            </div>
          </div>
          <el-icon class="top-arrow"><ArrowRight /></el-icon>
        </router-link>
      </div>
    </div>
  </div>

  <div v-else-if="loading" class="creator-loading">加载中...</div>
  <div v-else class="creator-loading">用户不存在</div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowRight } from '@element-plus/icons-vue'
import { getCreatorStats, type CreatorStats } from '../api/resources'

const route = useRoute()
const stats = ref<CreatorStats | null>(null)
const loading = ref(true)

async function load(username: string) {
  loading.value = true
  stats.value = null
  try {
    stats.value = await getCreatorStats(username)
  } catch {
    stats.value = null
  } finally {
    loading.value = false
  }
}

watch(() => route.params.username as string, (u) => {
  if (u) load(u)
}, { immediate: true })
</script>

<style scoped>
.creator-page {
  max-width: 640px;
  margin: 0 auto;
  padding: 24px 16px;
}

.creator-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 28px;
}

.creator-avatar {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  font-size: 24px;
  font-weight: 700;
  flex-shrink: 0;
}

.creator-name {
  font-size: 22px;
  font-weight: 700;
  margin: 0;
  color: #1e293b;
}

.creator-signature {
  font-size: 14px;
  color: #64748b;
  margin: 4px 0 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 32px;
}

.stat-card {
  background: #f8fafc;
  border-radius: 14px;
  padding: 24px;
  text-align: center;
  border: 1px solid #e2e8f0;
}

.stat-value {
  font-size: 32px;
  font-weight: 800;
  color: #6366f1;
}

.stat-label {
  font-size: 14px;
  color: #64748b;
  margin-top: 4px;
}

.section-title {
  font-size: 16px;
  font-weight: 700;
  margin: 0 0 12px;
  color: #1e293b;
}

.top-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.top-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 10px;
  text-decoration: none;
  transition: background .2s;
}

.top-item:hover {
  background: #eef2ff;
}

.top-rank {
  font-size: 18px;
  font-weight: 800;
  color: #94a3b8;
  width: 28px;
  text-align: center;
  flex-shrink: 0;
}

.top-info {
  flex: 1;
  min-width: 0;
}

.top-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.top-meta {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
  display: flex;
  gap: 4px;
}

.top-arrow {
  color: #cbd5e1;
  flex-shrink: 0;
}

.creator-loading {
  text-align: center;
  padding: 60px 0;
  color: #94a3b8;
  font-size: 15px;
}

@media (max-width: 768px) {
  .creator-page {
    padding: 16px 12px;
  }
  .stat-value {
    font-size: 26px;
  }
}
</style>
