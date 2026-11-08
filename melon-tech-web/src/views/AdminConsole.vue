<template>
  <div class="admin-console-page">
    <!-- 未登录锁定状态 -->
    <div v-if="!isLoggedIn" class="lock-wrapper">
      <div class="lock-card">
        <div class="lock-badge">
          <el-icon :size="32"><Lock /></el-icon>
        </div>
        <h2 class="lock-title">MSUT 控制台管理中台</h2>
        <p class="lock-desc">当前入口受专属管理员口令保护，请输入访问密钥</p>

        <el-form class="lock-form" @submit.prevent="handleLogin">
          <el-form-item>
            <el-input
              v-model="passwordInput"
              type="password"
              show-password
              size="large"
              placeholder="请输入 ADMIN_PASSWORD 管理口令..."
              :prefix-icon="Key"
              @keyup.enter="handleLogin"
            />
          </el-form-item>

          <el-button
            type="primary"
            size="large"
            class="submit-btn"
            :loading="loggingIn"
            @click="handleLogin"
          >
            解 锁 进 入
          </el-button>
        </el-form>

        <div class="lock-tips">
          <span>提示：后台隐蔽路径与管理密码可在根目录 <code>.env</code> 中随意定制</span>
        </div>
      </div>
    </div>

    <!-- 已登录控制台中台 -->
    <div v-else class="console-wrapper">
      <!-- 顶部控制栏 -->
      <header class="console-header">
        <div class="header-left">
          <div class="console-logo">
            <el-icon :size="24"><Monitor /></el-icon>
            <span class="logo-text">MSUT 管理控制中台</span>
          </div>
          <el-tag type="danger" effect="dark" size="small" class="admin-tag">超级管理鉴权通过</el-tag>
          <el-tag type="info" size="small" class="path-tag">
            当前安全路径: {{ currentAdminPath }}
          </el-tag>
        </div>

        <div class="header-right">
          <el-button size="small" @click="refreshAll" :loading="refreshing">
            <el-icon><Refresh /></el-icon>
            刷新数据
          </el-button>
          <el-button size="small" @click="goToFront">
            <el-icon><View /></el-icon>
            前往网站前台
          </el-button>
          <el-button size="small" type="danger" plain @click="handleLogout">
            <el-icon><SwitchButton /></el-icon>
            退出管理
          </el-button>
        </div>
      </header>

      <!-- 中间主工作区 -->
      <main class="console-main">
        <el-tabs v-model="activeTab" class="console-tabs" @tab-change="onTabChange">
          <!-- TAB 1: 运行大盘 (lazy 加载，提升切换流畅度) -->
          <el-tab-pane name="dashboard" lazy>
            <template #label>
              <span class="tab-label">
                <el-icon><Monitor /></el-icon> 运行大盘
              </span>
            </template>

            <div v-if="loadingStats" class="loading-box">
              <el-skeleton :rows="6" animated />
            </div>

            <div v-else-if="stats" class="dashboard-content">
              <!-- 四大核心指标卡片 -->
              <div class="metric-grid">
                <div class="metric-card card-users">
                  <div class="card-icon"><el-icon><User /></el-icon></div>
                  <div class="card-info">
                    <div class="label">注册用户总量</div>
                    <div class="value">{{ stats.metrics.usersCount.toLocaleString() }}</div>
                  </div>
                </div>

                <div class="metric-card card-mods">
                  <div class="card-icon"><el-icon><Box /></el-icon></div>
                  <div class="card-info">
                    <div class="label">模组作品总数</div>
                    <div class="value">{{ stats.metrics.resourcesCount.toLocaleString() }}</div>
                  </div>
                </div>

                <div class="metric-card card-files">
                  <div class="card-icon"><el-icon><Files /></el-icon></div>
                  <div class="card-info">
                    <div class="label">资源文件 / 体积</div>
                    <div class="value">
                      {{ stats.metrics.filesCount }} 份 / {{ formatBytes(stats.metrics.filesSizeBytes) }}
                    </div>
                  </div>
                </div>

                <div class="metric-card card-interactions">
                  <div class="card-icon"><el-icon><Star /></el-icon></div>
                  <div class="card-info">
                    <div class="label">全站获赞 / 评论</div>
                    <div class="value">
                      {{ stats.metrics.likesCount }} 赞 · {{ stats.metrics.commentsCount }} 评
                    </div>
                  </div>
                </div>
              </div>

              <!-- 系统环境状态检测面板 -->
              <el-card class="sys-health-card" shadow="never">
                <template #header>
                  <div class="card-header-flex">
                    <span class="title">⚡ 系统环境与核心服务监测</span>
                    <el-tag size="small" type="success">服务运行正常</el-tag>
                  </div>
                </template>
                <div class="health-grid">
                  <div class="health-item">
                    <div class="item-title">Cloudflare R2 存储</div>
                    <div class="item-desc">
                      <el-tag v-if="stats.systemInfo.r2Configured" type="success" size="small">已就绪</el-tag>
                      <el-tag v-else type="warning" size="small">未配置</el-tag>
                      <span class="sub-text">Bucket: {{ stats.systemInfo.r2Bucket || '本地临时模拟' }}</span>
                    </div>
                  </div>

                  <div class="health-item">
                    <div class="item-title">AI / RAG 知识网关</div>
                    <div class="item-desc">
                      <el-tag v-if="stats.systemInfo.ragConfigured" type="success" size="small">已连接</el-tag>
                      <el-tag v-else type="info" size="small">未开启</el-tag>
                      <span class="sub-text">Model: {{ stats.systemInfo.ragModel || '未设定' }}</span>
                    </div>
                  </div>

                  <div class="health-item">
                    <div class="item-title">SQLite 数据库体积</div>
                    <div class="item-desc">
                      <el-tag type="primary" size="small">WAL 模式</el-tag>
                      <span class="sub-text">{{ formatBytes(stats.systemInfo.dbSizeBytes) }}</span>
                    </div>
                  </div>

                  <div class="health-item">
                    <div class="item-title">HTTPS / 安全通道</div>
                    <div class="item-desc">
                      <el-tag :type="stats.systemInfo.httpsEnabled ? 'success' : 'info'" size="small">
                        {{ stats.systemInfo.httpsEnabled ? 'HTTPS 启用' : 'HTTP 模式' }}
                      </el-tag>
                    </div>
                  </div>
                </div>
              </el-card>

              <!-- 最新动态双栏 -->
              <div class="activity-row">
                <!-- 最新注册用户 -->
                <el-card class="activity-card" shadow="never">
                  <template #header>
                    <div class="card-header-flex">
                      <span class="title">👥 最新注册成员</span>
                      <el-button text size="small" @click="activeTab = 'users'">查看全部</el-button>
                    </div>
                  </template>
                  <div class="feed-list">
                    <div v-for="u in stats.recentUsers" :key="u.id" class="feed-item">
                      <el-avatar :size="36" :src="u.avatarUrl || undefined">
                        {{ (u.username || 'U').slice(0, 1).toUpperCase() }}
                      </el-avatar>
                      <div class="feed-info">
                        <div class="feed-name">{{ u.username }}</div>
                        <div class="feed-sub">注册时间: {{ formatTime(u.createdAt) }} · 发布作品: {{ u.resourceCount }} 个</div>
                      </div>
                    </div>
                  </div>
                </el-card>

                <!-- 最新发布作品 -->
                <el-card class="activity-card" shadow="never">
                  <template #header>
                    <div class="card-header-flex">
                      <span class="title">📦 最新上传模组</span>
                      <el-button text size="small" @click="activeTab = 'resources'">查看全部</el-button>
                    </div>
                  </template>
                  <div class="feed-list">
                    <div v-for="r in stats.recentResources" :key="r.id" class="feed-item">
                      <img
                        :src="r.coverUrl || '/placeholder.png'"
                        class="mod-thumb"
                        loading="lazy"
                        @error="handleImgError"
                      />
                      <div class="feed-info">
                        <div class="feed-name-row">
                          <span class="feed-name">{{ r.title }}</span>
                          <span class="feed-author">作者: {{ r.authorName }}</span>
                        </div>
                        <div class="feed-sub">
                          {{ formatTime(r.createdAt) }} · {{ r.likes }} 获赞 · {{ r.downloadCount }} 下载
                        </div>
                      </div>
                      <el-button text size="small" @click="openExternal(r.shareUrl)">查看</el-button>
                    </div>
                  </div>
                </el-card>
              </div>
            </div>
          </el-tab-pane>

          <!-- TAB 2: 每日推荐调度 (lazy 加载) -->
          <el-tab-pane name="daily" lazy>
            <template #label>
              <span class="tab-label">
                <el-icon><Star /></el-icon> 每日推荐调度
              </span>
            </template>

            <div class="daily-panel">
              <!-- 工具栏 -->
              <div class="daily-toolbar">
                <div class="toolbar-left">
                  <span class="label">调度目标日期:</span>
                  <el-date-picker
                    v-model="targetDate"
                    type="date"
                    value-format="YYYY-MM-DD"
                    placeholder="选择日期"
                    :clearable="false"
                    @change="loadDailyData"
                  />
                  <el-tag v-if="dailyData?.isManual" type="warning" effect="dark">
                    ⚠️ 当前日期已启用人工定制调度
                  </el-tag>
                  <el-tag v-else type="success" effect="plain">
                    ✨ 当前生效算法伪随机自然轮播
                  </el-tag>
                </div>

                <div class="toolbar-right">
                  <el-button
                    v-if="dailyData?.isManual"
                    type="danger"
                    plain
                    :loading="savingDaily"
                    @click="handleResetDaily"
                  >
                    恢复算法自然轮播
                  </el-button>
                  <el-button
                    type="primary"
                    :loading="savingDaily"
                    @click="handleSaveDaily"
                  >
                    保存今日调度配置
                  </el-button>
                </div>
              </div>

              <div v-if="loadingDaily" class="loading-box">
                <el-skeleton :rows="8" animated />
              </div>

              <div v-else-if="dailyData" class="daily-layout">
                <!-- 左侧：今日设定区域 (Hero + 精选) -->
                <div class="daily-left">
                  <!-- 镇站之宝区 -->
                  <div class="section-box">
                    <div class="section-header">
                      <span class="sec-title">👑 今日镇站之宝 (Hero Mod)</span>
                      <span class="sec-hint">居中大卡片推荐，全天唯一重点展示</span>
                    </div>

                    <div v-if="selectedHero" class="hero-selected-card">
                      <img
                        :src="selectedHero.coverUrl || '/placeholder.png'"
                        class="hero-img"
                        @error="handleImgError"
                      />
                      <div class="hero-body">
                        <div class="hero-title">{{ selectedHero.title }}</div>
                        <div class="hero-meta">
                          作者: {{ selectedHero.author }} · 今日算法评分: {{ selectedHero.dailyScore }}
                        </div>
                        <div class="hero-actions">
                          <el-button size="small" type="danger" text @click="clearHero">移除镇站</el-button>
                        </div>
                      </div>
                    </div>
                    <div v-else class="hero-empty-box">
                      <span>尚未手动指定镇站之宝，系统将自动按最高算力排序选取第一名</span>
                    </div>
                  </div>

                  <!-- 12 精选列表区 -->
                  <div class="section-box">
                    <div class="section-header">
                      <div class="sec-title-row">
                        <span class="sec-title">🎯 今日 12 精选列表</span>
                        <el-tag size="small" type="info">{{ selectedPicks.length }} / 12</el-tag>
                      </div>
                      <span class="sec-hint">若未选满 12 个，系统将按每日种子算法自动补足</span>
                    </div>

                    <div v-if="selectedPicks.length === 0" class="picks-empty">
                      暂未手动指定精选，目前完全由算法轮播生成
                    </div>
                    <div v-else class="picks-grid">
                      <div
                        v-for="item in selectedPicks"
                        :key="item.id"
                        class="pick-item-card"
                      >
                        <img
                          :src="item.coverUrl || '/placeholder.png'"
                          class="pick-img"
                          @error="handleImgError"
                        />
                        <div class="pick-info">
                          <div class="pick-title" :title="item.title">{{ item.title }}</div>
                          <div class="pick-sub">评分: {{ item.dailyScore }}</div>
                        </div>
                        <el-button
                          type="danger"
                          text
                          circle
                          size="small"
                          @click="removePick(item.id)"
                        >
                          ✕
                        </el-button>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 右侧：候选作品池 (分页展示，避免 150+ 个 DOM 同时渲染导致掉帧) -->
                <div class="daily-right">
                  <div class="section-box full-height">
                    <div class="section-header">
                      <span class="sec-title">📚 候选作品池 (共 {{ filteredCandidates.length }} 款)</span>
                      <el-input
                        v-model="candidateSearch"
                        size="small"
                        placeholder="搜索标题或作者..."
                        clearable
                        style="width: 180px;"
                        @input="candPage = 1"
                      />
                    </div>

                    <div class="candidate-scroll-list">
                      <div
                        v-for="item in pagedCandidates"
                        :key="item.id"
                        class="candidate-row"
                      >
                        <img
                          :src="item.coverUrl || '/placeholder.png'"
                          class="cand-thumb"
                          loading="lazy"
                          @error="handleImgError"
                        />
                        <div class="cand-details">
                          <div class="cand-name" :title="item.title">{{ item.title }}</div>
                          <div class="cand-sub">
                            {{ item.author }} · 获赞: {{ item.likes }} · 评分: {{ item.dailyScore }}
                          </div>
                        </div>
                        <div class="cand-btns">
                          <el-button
                            size="small"
                            type="primary"
                            plain
                            @click="setAsHero(item)"
                          >
                            设为镇站
                          </el-button>
                          <el-button
                            size="small"
                            :disabled="isPickSelected(item.id)"
                            @click="addToPicks(item)"
                          >
                            {{ isPickSelected(item.id) ? '已在精选' : '+ 加入精选' }}
                          </el-button>
                        </div>
                      </div>
                    </div>

                    <!-- 候选池分页 -->
                    <div v-if="filteredCandidates.length > candPageSize" class="cand-pagination">
                      <el-pagination
                        v-model:current-page="candPage"
                        :page-size="candPageSize"
                        :total="filteredCandidates.length"
                        layout="prev, pager, next"
                        small
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- TAB 3: 全站模组管理 (lazy 加载) -->
          <el-tab-pane name="resources" lazy>
            <template #label>
              <span class="tab-label">
                <el-icon><Box /></el-icon> 模组资源管理
              </span>
            </template>

            <div class="res-manage-panel">
              <!-- 筛选工具栏 -->
              <div class="table-toolbar">
                <div class="filter-left">
                  <el-input
                    v-model="resSearch"
                    placeholder="输入模组标题、作者或描述搜索..."
                    clearable
                    style="width: 260px;"
                    @keyup.enter="loadResources(1)"
                    @clear="loadResources(1)"
                  />
                  <el-select v-model="resSort" style="width: 140px;" @change="loadResources(1)">
                    <el-option label="最新发布" value="latest" />
                    <el-option label="最多点赞" value="likes" />
                    <el-option label="最多下载" value="downloads" />
                    <el-option label="最多文件" value="files" />
                  </el-select>
                  <el-button type="primary" @click="loadResources(1)">
                    搜索
                  </el-button>
                </div>
                <div class="filter-right">
                  <span class="total-text">共 {{ resTotal }} 项作品</span>
                </div>
              </div>

              <!-- 表格 -->
              <el-table
                v-loading="loadingRes"
                :data="resItems"
                stripe
                style="width: 100%"
                class="mod-table"
              >
                <el-table-column prop="id" label="ID" width="70" />
                <el-table-column label="封面" width="90">
                  <template #default="{ row }">
                    <img
                      :src="row.coverUrl || '/placeholder.png'"
                      class="table-cover"
                      loading="lazy"
                      @error="handleImgError"
                    />
                  </template>
                </el-table-column>
                <el-table-column prop="title" label="模组标题" min-width="160">
                  <template #default="{ row }">
                    <div class="table-title">{{ row.title }}</div>
                    <div class="table-slug">/share/{{ row.slug }}</div>
                  </template>
                </el-table-column>
                <el-table-column prop="authorName" label="创作者" width="120" />
                <el-table-column label="数据" width="130">
                  <template #default="{ row }">
                    <div class="data-tag">❤️ {{ row.likesCount }} 赞</div>
                    <div class="data-tag">⬇️ {{ row.downloadCount }} 次下载</div>
                  </template>
                </el-table-column>
                <el-table-column label="文件/体积" width="130">
                  <template #default="{ row }">
                    <div>{{ row.filesCount }} 个文件</div>
                    <div class="sub-text">{{ formatBytes(row.totalSizeBytes) }}</div>
                  </template>
                </el-table-column>
                <el-table-column label="发布时间" width="160">
                  <template #default="{ row }">
                    {{ formatTime(row.createdAt) }}
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="160" fixed="right">
                  <template #default="{ row }">
                    <el-button text size="small" type="primary" @click="openExternal(row.shareUrl)">
                      查看
                    </el-button>
                    <el-button text size="small" type="danger" @click="confirmDeleteResource(row)">
                      下架删除
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>

              <!-- 分页 -->
              <div class="pagination-bar">
                <el-pagination
                  v-model:current-page="resPage"
                  v-model:page-size="resPageSize"
                  :total="resTotal"
                  layout="prev, pager, next, sizes"
                  :page-sizes="[15, 30, 50]"
                  @current-change="loadResources"
                  @size-change="loadResources(1)"
                />
              </div>
            </div>
          </el-tab-pane>

          <!-- TAB 4: 注册用户管理 (lazy 加载) -->
          <el-tab-pane name="users" lazy>
            <template #label>
              <span class="tab-label">
                <el-icon><User /></el-icon> 注册用户管理
              </span>
            </template>

            <div class="users-panel">
              <div class="table-toolbar">
                <div class="filter-left">
                  <el-input
                    v-model="userSearch"
                    placeholder="搜索用户名或个性签名..."
                    clearable
                    style="width: 260px;"
                    @keyup.enter="loadUsers(1)"
                    @clear="loadUsers(1)"
                  />
                  <el-button type="primary" @click="loadUsers(1)">搜索</el-button>
                </div>
                <div class="filter-right">
                  <span class="total-text">共 {{ userTotal }} 位用户</span>
                </div>
              </div>

              <el-table
                v-loading="loadingUsers"
                :data="userItems"
                stripe
                style="width: 100%"
              >
                <el-table-column prop="id" label="UID" width="80" />
                <el-table-column label="头像" width="70">
                  <template #default="{ row }">
                    <el-avatar :size="32" :src="row.avatarUrl || undefined">
                      {{ (row.username || 'U').slice(0, 1).toUpperCase() }}
                    </el-avatar>
                  </template>
                </el-table-column>
                <el-table-column prop="username" label="用户名" min-width="140" />
                <el-table-column prop="signature" label="个性签名" min-width="200">
                  <template #default="{ row }">
                    <span v-if="row.signature">{{ row.signature }}</span>
                    <span v-else class="sub-text">(未填写)</span>
                  </template>
                </el-table-column>
                <el-table-column prop="resourceCount" label="已发布作品" width="110" />
                <el-table-column label="注册时间" width="160">
                  <template #default="{ row }">
                    {{ formatTime(row.createdAt) }}
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="120" fixed="right">
                  <template #default="{ row }">
                    <el-button text size="small" type="danger" @click="confirmDeleteUser(row)">
                      注销用户
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>

              <div class="pagination-bar">
                <el-pagination
                  v-model:current-page="userPage"
                  v-model:page-size="userPageSize"
                  :total="userTotal"
                  layout="prev, pager, next, sizes"
                  :page-sizes="[20, 50, 100]"
                  @current-change="loadUsers"
                  @size-change="loadUsers(1)"
                />
              </div>
            </div>
          </el-tab-pane>

          <!-- TAB 5: 安全与配置说明 (lazy 加载) -->
          <el-tab-pane name="config" lazy>
            <template #label>
              <span class="tab-label">
                <el-icon><Setting /></el-icon> 安全与配置指南
              </span>
            </template>

            <div class="config-guide">
              <el-card class="guide-card" shadow="never">
                <template #header>
                  <span class="title">🔐 隐蔽管理路径与密钥配置方法</span>
                </template>
                <div class="guide-body">
                  <p>本管理后台具备极高隐蔽性，全站前台任何链接均不包含此路径，且支持随时在服务端配置文件中自定义：</p>
                  
                  <div class="code-block">
                    <div class="block-label">服务端根目录 .env 文件示例</div>
                    <pre><code># 设定您的专属隐蔽后台路径（支持自由命名）
ADMIN_PATH=/my-secret-console-99
VITE_ADMIN_PATH=/my-secret-console-99

# 设定超级管理员访问口令
ADMIN_PASSWORD=your-super-strong-password-here</code></pre>
                  </div>

                  <h4>安全最佳实践：</h4>
                  <ul>
                    <li><strong>不要向外界公开或分享此路径</strong>：该路径是防恶意扫描的第一道防线。</li>
                    <li><strong>修改口令立即生效</strong>：修改 <code>ADMIN_PASSWORD</code> 后，旧的管理员会话将在下次校验时自动失效。</li>
                    <li><strong>退出登录自动销毁 Session</strong>：点击右上角“退出管理”可立即抹除本地所有管理员 Token。</li>
                  </ul>
                </div>
              </el-card>
            </div>
          </el-tab-pane>
        </el-tabs>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Lock,
  Key,
  Monitor,
  User,
  Files,
  Star,
  Refresh,
  View,
  SwitchButton,
  Box,
  Setting,
} from '@element-plus/icons-vue'
import {
  getAdminToken,
  clearAdminToken,
  adminLogin,
  adminCheck,
  fetchAdminStats,
  fetchAdminResources,
  deleteAdminResource,
  fetchAdminUsers,
  deleteAdminUser,
  fetchAdminDaily,
  overrideAdminDaily,
  resetAdminDaily,
  type AdminStatsResponse,
  type AdminResourceItem,
  type AdminUserItem,
  type AdminDailyStatus,
  type AdminDailyCandidate,
} from '../api/admin'

const router = useRouter()

// 状态
const isLoggedIn = ref(false)
const passwordInput = ref('')
const loggingIn = ref(false)
const currentAdminPath = ref(import.meta.env.VITE_ADMIN_PATH || '/msut-manage-console')

const activeTab = ref('dashboard')
const refreshing = ref(false)

// Dashboard Stats
const loadingStats = ref(false)
const stats = ref<AdminStatsResponse | null>(null)

// Daily Recommendations
const targetDate = ref(new Date().toISOString().slice(0, 10))
const loadingDaily = ref(false)
const savingDaily = ref(false)
const dailyData = ref<AdminDailyStatus | null>(null)
const selectedHeroId = ref<number | null>(null)
const selectedPickedIds = ref<number[]>([])
const candidateSearch = ref('')
const candPage = ref(1)
const candPageSize = ref(20)

// Resources
const loadingRes = ref(false)
const resItems = ref<AdminResourceItem[]>([])
const resTotal = ref(0)
const resPage = ref(1)
const resPageSize = ref(15)
const resSearch = ref('')
const resSort = ref('latest')

// Users
const loadingUsers = ref(false)
const userItems = ref<AdminUserItem[]>([])
const userTotal = ref(0)
const userPage = ref(1)
const userPageSize = ref(20)
const userSearch = ref('')

// 安全的图片防崩兜底函数（防止 404 死循环造成浏览器卡死）
const FALLBACK_IMG = '/placeholder.png'
function handleImgError(e: Event) {
  const target = e.target as HTMLImageElement
  if (target) {
    target.onerror = null // 关键：彻底解除监听，避免触发死循环
    if (target.src !== window.location.origin + FALLBACK_IMG) {
      target.src = FALLBACK_IMG
    }
  }
}

// 初始化验证
onMounted(async () => {
  const token = getAdminToken()
  if (token) {
    try {
      const res = await adminCheck()
      if (res.ok) {
        isLoggedIn.value = true
        currentAdminPath.value = res.adminPath || currentAdminPath.value
        loadStats()
      }
    } catch {
      clearAdminToken()
      isLoggedIn.value = false
    }
  }
})

// 登录
async function handleLogin() {
  if (!passwordInput.value.trim()) {
    ElMessage.warning('请输入管理口令')
    return
  }
  loggingIn.value = true
  try {
    const res = await adminLogin(passwordInput.value.trim())
    if (res.ok) {
      ElMessage.success('管理员认证成功！')
      isLoggedIn.value = true
      currentAdminPath.value = res.adminPath || currentAdminPath.value
      passwordInput.value = ''
      loadStats()
    }
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || '管理口令验证失败')
  } finally {
    loggingIn.value = false
  }
}

// 退出
function handleLogout() {
  clearAdminToken()
  isLoggedIn.value = false
  ElMessage.info('已退出管理后台')
}

function goToFront() {
  router.push('/')
}

async function refreshAll() {
  refreshing.value = true
  try {
    if (activeTab.value === 'dashboard') await loadStats()
    else if (activeTab.value === 'daily') await loadDailyData()
    else if (activeTab.value === 'resources') await loadResources()
    else if (activeTab.value === 'users') await loadUsers()
    ElMessage.success('数据已更新')
  } finally {
    refreshing.value = false
  }
}

function onTabChange(tab: any) {
  if (tab === 'dashboard' && !stats.value) loadStats()
  else if (tab === 'daily' && !dailyData.value) loadDailyData()
  else if (tab === 'resources' && resItems.value.length === 0) loadResources(1)
  else if (tab === 'users' && userItems.value.length === 0) loadUsers(1)
}

// 1. 加载 Dashboard Stats
async function loadStats() {
  loadingStats.value = true
  try {
    const res = await fetchAdminStats()
    stats.value = res
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || '加载统计数据失败')
  } finally {
    loadingStats.value = false
  }
}

// 2. 加载 Daily Data
async function loadDailyData() {
  loadingDaily.value = true
  try {
    const res = await fetchAdminDaily(targetDate.value)
    dailyData.value = res
    selectedHeroId.value = res.heroId
    selectedPickedIds.value = [...res.pickedIds]
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || '加载每日推荐数据失败')
  } finally {
    loadingDaily.value = false
  }
}

const selectedHero = computed<AdminDailyCandidate | null>(() => {
  if (!dailyData.value || !selectedHeroId.value) return null
  return dailyData.value.candidates.find(c => c.id === selectedHeroId.value) || null
})

const selectedPicks = computed<AdminDailyCandidate[]>(() => {
  if (!dailyData.value) return []
  return selectedPickedIds.value
    .map(id => dailyData.value!.candidates.find(c => c.id === id))
    .filter((c): c is AdminDailyCandidate => !!c)
})

const filteredCandidates = computed<AdminDailyCandidate[]>(() => {
  if (!dailyData.value) return []
  const q = candidateSearch.value.trim().toLowerCase()
  if (!q) return dailyData.value.candidates
  return dailyData.value.candidates.filter(c =>
    c.title.toLowerCase().includes(q) || c.author.toLowerCase().includes(q)
  )
})

// 分页切片候选池
const pagedCandidates = computed<AdminDailyCandidate[]>(() => {
  const list = filteredCandidates.value
  const start = (candPage.value - 1) * candPageSize.value
  return list.slice(start, start + candPageSize.value)
})

function isPickSelected(id: number) {
  return selectedPickedIds.value.includes(id)
}

function setAsHero(item: AdminDailyCandidate) {
  selectedHeroId.value = item.id
  selectedPickedIds.value = selectedPickedIds.value.filter(id => id !== item.id)
  ElMessage.success(`已将《${item.title}》设为镇站之宝`)
}

function clearHero() {
  selectedHeroId.value = null
}

function addToPicks(item: AdminDailyCandidate) {
  if (selectedHeroId.value === item.id) {
    ElMessage.warning('该模组已被设为镇站之宝')
    return
  }
  if (selectedPickedIds.value.length >= 12) {
    ElMessage.warning('精选列表上限为 12 个')
    return
  }
  if (!selectedPickedIds.value.includes(item.id)) {
    selectedPickedIds.value.push(item.id)
  }
}

function removePick(id: number) {
  selectedPickedIds.value = selectedPickedIds.value.filter(pid => pid !== id)
}

async function handleSaveDaily() {
  savingDaily.value = true
  try {
    const res = await overrideAdminDaily({
      date: targetDate.value,
      hero_id: selectedHeroId.value,
      picked_ids: selectedPickedIds.value,
    })
    ElMessage.success(res.message || '调度保存成功！')
    await loadDailyData()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || '保存推荐调度失败')
  } finally {
    savingDaily.value = false
  }
}

async function handleResetDaily() {
  try {
    await ElMessageBox.confirm('确定恢复当前日期的算法自然轮播吗？', '确认重置', {
      type: 'warning',
    })
  } catch {
    return
  }
  savingDaily.value = true
  try {
    const res = await resetAdminDaily(targetDate.value)
    ElMessage.success(res.message || '已恢复算法自然轮播')
    await loadDailyData()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || '重置失败')
  } finally {
    savingDaily.value = false
  }
}

// 3. 加载 Resources
async function loadResources(page = resPage.value) {
  resPage.value = page
  loadingRes.value = true
  try {
    const res = await fetchAdminResources({
      page: resPage.value,
      page_size: resPageSize.value,
      q: resSearch.value.trim() || undefined,
      sort_by: resSort.value,
    })
    resItems.value = res.items
    resTotal.value = res.total
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || '加载模组列表失败')
  } finally {
    loadingRes.value = false
  }
}

async function confirmDeleteResource(row: AdminResourceItem) {
  try {
    await ElMessageBox.confirm(
      `确定要下架并永久删除模组《${row.title}》吗？这将同步清理所有文件与互动数据！`,
      '高危操作确认',
      { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'error' }
    )
  } catch {
    return
  }
  try {
    const res = await deleteAdminResource(row.id)
    ElMessage.success(res.message || '已删除模组')
    loadResources()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || '删除失败')
  }
}

// 4. 加载 Users
async function loadUsers(page = userPage.value) {
  userPage.value = page
  loadingUsers.value = true
  try {
    const res = await fetchAdminUsers({
      page: userPage.value,
      page_size: userPageSize.value,
      q: userSearch.value.trim() || undefined,
    })
    userItems.value = res.items
    userTotal.value = res.total
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || '加载用户列表失败')
  } finally {
    loadingUsers.value = false
  }
}

async function confirmDeleteUser(row: AdminUserItem) {
  try {
    await ElMessageBox.confirm(
      `确定要注销用户【${row.username}】吗？该操作不可撤销！`,
      '确认注销',
      { type: 'warning' }
    )
  } catch {
    return
  }
  try {
    const res = await deleteAdminUser(row.id)
    ElMessage.success(res.message || '用户已注销')
    loadUsers()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || '注销失败')
  }
}

// 通用格式化
function formatBytes(bytes: number): string {
  if (!bytes || bytes <= 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
}

function formatTime(iso: string): string {
  if (!iso) return ''
  return iso.replace('T', ' ').slice(0, 16)
}

function openExternal(url: string) {
  window.open(url, '_blank')
}
</script>

<style scoped>
.admin-console-page {
  min-height: 100vh;
  background-color: #0f172a;
  color: #f1f5f9;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

/* 锁定卡片 */
.lock-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 80vh;
  padding: 24px;
}

.lock-card {
  width: 100%;
  max-width: 440px;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 16px;
  padding: 36px 32px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
  text-align: center;
}

.lock-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  margin-bottom: 16px;
}

.lock-title {
  margin: 0 0 8px 0;
  font-size: 22px;
  font-weight: 700;
  color: #f8fafc;
}

.lock-desc {
  margin: 0 0 24px 0;
  font-size: 13px;
  color: #94a3b8;
  line-height: 1.5;
}

.lock-form {
  margin-bottom: 20px;
}

.submit-btn {
  width: 100%;
  font-weight: 600;
  letter-spacing: 2px;
}

.lock-tips {
  font-size: 12px;
  color: #64748b;
  line-height: 1.6;
}

.lock-tips code {
  color: #38bdf8;
  background: #0f172a;
  padding: 2px 6px;
  border-radius: 4px;
}

/* 控制台主框架 */
.console-wrapper {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.console-header {
  height: 64px;
  background: #1e293b;
  border-bottom: 1px solid #334155;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.console-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #38bdf8;
  font-size: 18px;
  font-weight: 700;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.console-main {
  flex: 1;
  padding: 20px 24px 40px;
}

.console-tabs :deep(.el-tabs__item) {
  color: #94a3b8;
  font-size: 15px;
  font-weight: 500;
}

.console-tabs :deep(.el-tabs__item.is-active) {
  color: #38bdf8;
  font-weight: 700;
}

.console-tabs :deep(.el-tabs__active-bar) {
  background-color: #38bdf8;
}

.tab-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

/* Metric Cards */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.metric-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border-radius: 12px;
  background: #1e293b;
  border: 1px solid #334155;
}

.card-icon {
  width: 52px;
  height: 52px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.card-users .card-icon { background: rgba(56, 189, 248, 0.15); color: #38bdf8; }
.card-mods .card-icon { background: rgba(34, 197, 94, 0.15); color: #22c55e; }
.card-files .card-icon { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
.card-interactions .card-icon { background: rgba(236, 72, 153, 0.15); color: #ec4899; }

.card-info .label {
  font-size: 13px;
  color: #94a3b8;
  margin-bottom: 4px;
}

.card-info .value {
  font-size: 20px;
  font-weight: 700;
  color: #f8fafc;
}

/* System Health Card */
.sys-health-card {
  background: #1e293b !important;
  border: 1px solid #334155 !important;
  border-radius: 12px;
  margin-bottom: 24px;
  color: #f8fafc;
}

.card-header-flex {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-header-flex .title {
  font-weight: 600;
  font-size: 15px;
  color: #f8fafc;
}

.health-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.health-item .item-title {
  font-size: 13px;
  color: #94a3b8;
  margin-bottom: 6px;
}

.health-item .item-desc {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sub-text {
  font-size: 12px;
  color: #64748b;
}

/* Activity Row */
.activity-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 900px) {
  .activity-row {
    grid-template-columns: 1fr;
  }
}

.activity-card {
  background: #1e293b !important;
  border: 1px solid #334155 !important;
  border-radius: 12px;
}

.feed-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.feed-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #334155;
}

.feed-item:last-child {
  border-bottom: none;
}

.feed-info {
  flex: 1;
  min-width: 0;
}

.feed-name {
  font-size: 14px;
  font-weight: 600;
  color: #f1f5f9;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.feed-name-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.feed-author {
  font-size: 12px;
  color: #94a3b8;
}

.feed-sub {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
}

.mod-thumb {
  width: 44px;
  height: 44px;
  border-radius: 6px;
  object-fit: cover;
  background: #0f172a;
}

/* Daily Panel */
.daily-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 10px;
  margin-bottom: 20px;
}

.toolbar-left, .toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-left .label {
  font-size: 14px;
  color: #94a3b8;
}

.daily-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 1024px) {
  .daily-layout {
    grid-template-columns: 1fr;
  }
}

.section-box {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 18px;
  margin-bottom: 20px;
}

.section-box.full-height {
  height: calc(100% - 20px);
  margin-bottom: 0;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.sec-title {
  font-size: 15px;
  font-weight: 600;
  color: #f8fafc;
}

.sec-hint {
  font-size: 12px;
  color: #64748b;
}

.hero-selected-card {
  display: flex;
  gap: 16px;
  background: #0f172a;
  border: 1px solid #38bdf8;
  border-radius: 10px;
  padding: 14px;
}

.hero-img {
  width: 110px;
  height: 75px;
  border-radius: 8px;
  object-fit: cover;
}

.hero-body {
  flex: 1;
}

.hero-title {
  font-size: 16px;
  font-weight: 700;
  color: #f8fafc;
}

.hero-meta {
  font-size: 13px;
  color: #94a3b8;
  margin: 4px 0 10px 0;
}

.hero-empty-box, .picks-empty {
  padding: 24px;
  text-align: center;
  color: #64748b;
  font-size: 13px;
  background: #0f172a;
  border-radius: 8px;
}

.picks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}

.pick-item-card {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 8px;
}

.pick-img {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  object-fit: cover;
}

.pick-info {
  flex: 1;
  min-width: 0;
}

.pick-title {
  font-size: 13px;
  font-weight: 600;
  color: #f1f5f9;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pick-sub {
  font-size: 11px;
  color: #64748b;
}

.candidate-scroll-list {
  max-height: 520px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.candidate-row {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 8px 12px;
}

.cand-thumb {
  width: 44px;
  height: 44px;
  border-radius: 6px;
  object-fit: cover;
}

.cand-details {
  flex: 1;
  min-width: 0;
}

.cand-name {
  font-size: 13px;
  font-weight: 600;
  color: #f1f5f9;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cand-sub {
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
}

.cand-btns {
  display: flex;
  gap: 6px;
}

.cand-pagination {
  margin-top: 12px;
  display: flex;
  justify-content: center;
}

/* Resources & Users Tables */
.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.filter-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.total-text {
  font-size: 13px;
  color: #94a3b8;
}

.table-cover {
  width: 50px;
  height: 50px;
  border-radius: 6px;
  object-fit: cover;
  background: #0f172a;
}

.table-title {
  font-weight: 600;
  color: #f1f5f9;
}

.table-slug {
  font-size: 11px;
  color: #64748b;
}

.data-tag {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.5;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

/* Config Guide */
.guide-card {
  background: #1e293b !important;
  border: 1px solid #334155 !important;
  border-radius: 12px;
  color: #f8fafc;
}

.guide-body {
  line-height: 1.7;
  font-size: 14px;
  color: #cbd5e1;
}

.code-block {
  margin: 16px 0;
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 16px;
}

.block-label {
  font-size: 12px;
  color: #38bdf8;
  margin-bottom: 8px;
  font-weight: 600;
}

.code-block pre {
  margin: 0;
  font-family: Consolas, monospace;
  color: #a5f3fc;
}

.guide-body ul {
  padding-left: 20px;
}

.guide-body li {
  margin-bottom: 8px;
}

.loading-box {
  padding: 40px;
}
</style>
