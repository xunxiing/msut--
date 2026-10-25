<template>
  <div class="daily-container">
    <!-- Header Section -->
    <div class="daily-header">
      <div class="header-inner">
        <div class="header-badge-row">
          <el-tag type="danger" effect="dark" round class="fire-tag">🔥 每日精选推荐</el-tag>
          <el-tag v-if="dailyData?.is_manual" type="warning" effect="light" round>✨ 人工特别精选</el-tag>
          <el-tag v-else type="success" effect="light" round>🎲 每日算法轮播</el-tag>
          <span class="refresh-tip">每日 00:00 自动轮换</span>
        </div>
        <h1 class="header-title">让优秀的甜瓜作品被更多人看见</h1>
        <p class="header-desc">
          基于每日伪随机种子与质量加权算法，每天为您挑选最出色的甜瓜游乐场模组与存档。
        </p>
      </div>

      <div class="header-toolbar">
        <div class="date-picker-wrap">
          <el-date-picker
            v-model="selectedDate"
            type="date"
            placeholder="选择日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            :disabled-date="disableFutureDates"
            @change="loadDaily"
            class="custom-date-picker"
          />
        </div>
        <el-button class="refresh-btn" :loading="loading" @click="loadDaily">
          <el-icon><RefreshRight /></el-icon>
          <span>刷新</span>
        </el-button>
      </div>
    </div>

    <!-- Loading Skeleton -->
    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="8" animated />
    </div>

    <div v-else-if="dailyData" class="daily-content">
      <!-- 今日主打星 (Hero Spotlight) -->
      <section v-if="dailyData.hero" class="hero-spotlight-section">
        <div class="section-title-row">
          <div class="section-title">
            <span class="star-icon">⭐</span> 今日之星 · 特别主推
          </div>
          <div class="score-tag" v-if="dailyData.hero.dailyScore">
            今日综合指数: {{ dailyData.hero.dailyScore }}
          </div>
        </div>

        <el-card class="hero-card" shadow="hover" @click="goToDetail(dailyData.hero.slug)">
          <div class="hero-card-grid">
            <div class="hero-cover-col">
              <div class="hero-cover-box" :class="{ 'has-cover': dailyData.hero.coverUrlPath }">
                <img
                  v-if="dailyData.hero.coverUrlPath"
                  :src="toImageUrl(dailyData.hero.coverUrlPath)"
                  alt="cover"
                  class="hero-cover-img"
                  loading="lazy"
                />
                <el-icon v-else class="hero-no-cover"><Document /></el-icon>
                <div class="hero-badge">今日主推</div>
              </div>
            </div>

            <div class="hero-info-col">
              <div class="hero-title-row">
                <h2 class="hero-resource-title">{{ dailyData.hero.title }}</h2>
              </div>

              <div class="hero-author-meta">
                <el-avatar :size="24" class="hero-avatar">
                  {{ dailyData.hero.author_username?.[0]?.toUpperCase() || 'U' }}
                </el-avatar>
                <span class="hero-author-name">{{ dailyData.hero.author_username || '匿名作者' }}</span>
                <span class="hero-date">发布于 {{ formatDate(dailyData.hero.created_at) }}</span>
              </div>

              <p class="hero-desc">
                {{ dailyData.hero.description || '作者很懒，暂未留下详细介绍。' }}
              </p>

              <div v-if="dailyData.hero.tags?.length" class="hero-tags">
                <el-tag
                  v-for="t in dailyData.hero.tags"
                  :key="t"
                  size="small"
                  effect="light"
                  round
                  class="hero-tag-item"
                >
                  {{ t }}
                </el-tag>
              </div>

              <div class="hero-bottom-actions">
                <div class="hero-stats">
                  <div
                    class="like-btn"
                    :class="{ 'is-liked': likesMap[dailyData.hero.id]?.liked }"
                    @click.stop="toggleLike(dailyData.hero.id)"
                  >
                    <el-icon>
                      <component :is="likesMap[dailyData.hero.id]?.liked ? StarFilled : Star" />
                    </el-icon>
                    <span>{{ likesMap[dailyData.hero.id]?.likes || dailyData.hero.likes || 0 }} 赞</span>
                  </div>
                  <span class="download-badge">
                    <el-icon><Download /></el-icon>
                    {{ dailyData.hero.downloadCount || 0 }} 次下载
                  </span>
                </div>

                <div class="hero-cta">
                  <el-button type="primary" size="large" round @click.stop="goToDetail(dailyData.hero.slug)">
                    <span>查看作品详情</span>
                    <el-icon class="ml-4"><Right /></el-icon>
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </section>

      <!-- 今日精选模组流 (Picks Grid) -->
      <section class="picks-section">
        <div class="section-title-row">
          <div class="section-title">
            <span class="spark-icon">✨</span> 今日精选模组 ({{ dailyData.picks.length }})
          </div>
          <span class="section-subtext">基于算法日更，每日都有不同惊喜</span>
        </div>

        <el-empty v-if="dailyData.picks.length === 0" description="暂无精选模组" />

        <div v-else class="picks-grid">
          <el-card
            v-for="(item, idx) in dailyData.picks"
            :key="item.id"
            class="pick-card"
            shadow="hover"
            @click="goToDetail(item.slug)"
          >
            <div class="pick-rank-badge">#{{ idx + 1 }}</div>
            <div class="pick-cover-wrap" :class="{ 'has-cover': item.coverUrlPath }">
              <img
                v-if="item.coverUrlPath"
                :src="toImageUrl(item.coverUrlPath)"
                alt="cover"
                class="pick-cover-img"
                loading="lazy"
              />
              <el-icon v-else class="pick-no-cover"><Document /></el-icon>
            </div>

            <div class="pick-body">
              <h3 class="pick-title" :title="item.title">{{ item.title }}</h3>
              
              <div class="pick-author-row">
                <el-avatar :size="18" class="pick-avatar">
                  {{ item.author_username?.[0]?.toUpperCase() || 'U' }}
                </el-avatar>
                <span class="pick-author">{{ item.author_username || '未知' }}</span>
              </div>

              <p class="pick-desc">{{ item.description || '暂无介绍' }}</p>

              <div v-if="item.tags?.length" class="pick-tags">
                <el-tag v-for="t in item.tags.slice(0, 3)" :key="t" size="small" effect="plain" round>
                  {{ t }}
                </el-tag>
              </div>

              <div class="pick-footer">
                <div
                  class="pick-like"
                  :class="{ 'is-liked': likesMap[item.id]?.liked }"
                  @click.stop="toggleLike(item.id)"
                >
                  <el-icon>
                    <component :is="likesMap[item.id]?.liked ? StarFilled : Star" />
                  </el-icon>
                  <span>{{ likesMap[item.id]?.likes || item.likes || 0 }}</span>
                </div>
                <span class="pick-downloads">
                  <el-icon><Download /></el-icon>
                  {{ item.downloadCount || 0 }}
                </span>
              </div>
            </div>
          </el-card>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  RefreshRight,
  Document,
  Star,
  StarFilled,
  Download,
  Right
} from '@element-plus/icons-vue'
import {
  getDailyRecommendations,
  type DailyRecommendationResponse
} from '../api/resources'
import { getResourceLikes, likeResource, unlikeResource, type LikeInfo } from '../api/likes'

const router = useRouter()

const loading = ref(false)
const selectedDate = ref('')
const dailyData = ref<DailyRecommendationResponse | null>(null)
const likesMap = ref<Record<number, LikeInfo>>({})

function getTodayString() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function disableFutureDates(time: Date) {
  return time.getTime() > Date.now()
}

function toImageUrl(path?: string | null) {
  if (!path) return ''
  return path
}

function formatDate(s?: string) {
  if (!s) return '-'
  return s.split(' ')[0]
}

function goToDetail(slug: string) {
  router.push(`/share/${slug}`)
}

async function loadDaily() {
  loading.value = true
  try {
    const data = await getDailyRecommendations(selectedDate.value || undefined)
    dailyData.value = data
    if (!selectedDate.value) {
      selectedDate.value = data.date
    }

    // Load likes
    const ids: number[] = []
    if (data.hero) ids.push(data.hero.id)
    if (data.picks) data.picks.forEach(p => ids.push(p.id))
    if (ids.length) {
      try {
        const likesRes = await getResourceLikes(ids)
        const map: Record<number, LikeInfo> = {}
        likesRes.forEach(it => { map[it.id] = it })
        likesMap.value = map
      } catch {
        // quiet ignore
      }
    }
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || '加载每日推荐失败')
  } finally {
    loading.value = false
  }
}

async function toggleLike(id: number) {
  const cur = likesMap.value[id]
  const liked = !!cur?.liked
  try {
    if (liked) {
      const res = await unlikeResource(id)
      likesMap.value = { ...likesMap.value, [id]: { id, likes: res.likes, liked: false } }
    } else {
      const res = await likeResource(id)
      likesMap.value = { ...likesMap.value, [id]: { id, likes: res.likes, liked: true } }
    }
  } catch (e: any) {
    ElMessage.warning(e.response?.data?.error || '请先登录后点赞')
  }
}

onMounted(() => {
  selectedDate.value = getTodayString()
  loadDaily()
})
</script>

<style scoped>
.daily-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 16px 80px;
}

/* Header */
.daily-header {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 28px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

@media (min-width: 768px) {
  .daily-header {
    flex-direction: row;
    align-items: flex-end;
    justify-content: space-between;
  }
}

.header-badge-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.fire-tag {
  font-weight: bold;
}

.refresh-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-left: 4px;
}

.header-title {
  margin: 0 0 6px;
  font-size: 26px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.header-desc {
  margin: 0;
  font-size: 14px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
}

.header-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.custom-date-picker {
  width: 140px;
}

/* Hero Spotlight Section */
.hero-spotlight-section {
  margin-bottom: 36px;
}

.section-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.section-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.star-icon {
  font-size: 22px;
}

.spark-icon {
  font-size: 20px;
}

.section-subtext {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.score-tag {
  font-size: 12px;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  padding: 3px 8px;
  border-radius: 12px;
  font-weight: 600;
}

.hero-card {
  border-radius: 16px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.25s ease;
  border: 1px solid var(--el-border-color-lighter);
}

.hero-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.08);
}

.hero-card-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
}

@media (min-width: 768px) {
  .hero-card-grid {
    grid-template-columns: 340px 1fr;
    gap: 28px;
  }
}

.hero-cover-box {
  width: 100%;
  height: 220px;
  border-radius: 12px;
  background: var(--el-fill-color-light);
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (min-width: 768px) {
  .hero-cover-box {
    height: 100%;
    min-height: 220px;
  }
}

.hero-cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.hero-card:hover .hero-cover-img {
  transform: scale(1.03);
}

.hero-no-cover {
  font-size: 64px;
  color: var(--el-text-color-placeholder);
}

.hero-badge {
  position: absolute;
  top: 10px;
  left: 10px;
  background: linear-gradient(135deg, #ff416c, #ff4b2b);
  color: #fff;
  font-size: 12px;
  font-weight: bold;
  padding: 3px 10px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(255, 75, 43, 0.4);
}

.hero-info-col {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 4px 0;
}

.hero-resource-title {
  margin: 0 0 10px;
  font-size: 22px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  line-height: 1.3;
}

.hero-author-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.hero-author-name {
  font-weight: 500;
  color: var(--el-text-color-regular);
}

.hero-desc {
  font-size: 14px;
  color: var(--el-text-color-regular);
  line-height: 1.6;
  margin: 0 0 16px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.hero-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 18px;
}

.hero-bottom-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px dashed var(--el-border-color-lighter);
}

.hero-stats {
  display: flex;
  align-items: center;
  gap: 16px;
}

.like-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  transition: color 0.2s;
  padding: 4px 8px;
  border-radius: 6px;
}

.like-btn:hover,
.like-btn.is-liked {
  color: #ff9800;
  background: rgba(255, 152, 0, 0.1);
}

.download-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

/* Picks Grid Section */
.picks-section {
  margin-top: 24px;
}

.picks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 20px;
}

.pick-card {
  border-radius: 14px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.25s ease;
  position: relative;
  display: flex;
  flex-direction: column;
}

.pick-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.pick-rank-badge {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 2;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(4px);
  color: #fff;
  font-size: 12px;
  font-weight: bold;
  padding: 2px 8px;
  border-radius: 8px;
}

.pick-cover-wrap {
  width: 100%;
  height: 140px;
  background: var(--el-fill-color-light);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pick-cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.pick-card:hover .pick-cover-img {
  transform: scale(1.05);
}

.pick-no-cover {
  font-size: 40px;
  color: var(--el-text-color-placeholder);
}

.pick-body {
  padding: 14px;
  display: flex;
  flex-direction: column;
  flex: 1;
}

.pick-title {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pick-author-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.pick-author {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pick-desc {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
  margin: 0 0 10px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.pick-tags {
  display: flex;
  gap: 4px;
  margin-bottom: 12px;
}

.pick-footer {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 8px;
  border-top: 1px solid var(--el-border-color-lighter);
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.pick-like {
  display: flex;
  align-items: center;
  gap: 3px;
  cursor: pointer;
}

.pick-like:hover,
.pick-like.is-liked {
  color: #ff9800;
}

.pick-downloads {
  display: flex;
  align-items: center;
  gap: 3px;
}

.w-100 {
  width: 100%;
}

.ml-4 {
  margin-left: 4px;
}
</style>
