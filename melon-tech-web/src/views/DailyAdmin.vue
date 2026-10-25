<template>
  <div class="admin-page-container">
    <div class="admin-card-wrap">
      <!-- Header -->
      <div class="admin-page-header">
        <div class="header-left">
          <h2 class="title">⚙️ 每日推荐管理后台</h2>
          <p class="subtitle">仅管理员可访问。用于手动锁定指定日期的推荐作品与主打星。</p>
        </div>
        <div class="header-right">
          <el-button @click="$router.push('/daily')">
            <el-icon class="mr-4"><View /></el-icon>
            <span>返回前台展示</span>
          </el-button>
          <el-button v-if="adminVerified" type="danger" plain @click="handleLogout">
            <span>退出管理</span>
          </el-button>
        </div>
      </div>

      <!-- Step 1: 密码认证 -->
      <el-card v-if="!adminVerified" class="auth-card" shadow="hover">
        <template #header>
          <div class="card-title">🔐 管理员身份验证</div>
        </template>
        <p class="auth-hint">
          此页面为内部管理地址。请输入配置于服务端 <code>.env</code> 中的 <code>DAILY_ADMIN_PASSWORD</code> 进行验证。
        </p>

        <el-form label-position="top" @submit.prevent="handleVerify">
          <el-form-item label="管理员密码">
            <el-input
              v-model="passwordInput"
              type="password"
              placeholder="请输入管理员密码"
              show-password
              size="large"
              @keyup.enter="handleVerify"
            />
          </el-form-item>
          <div class="form-actions">
            <el-button
              type="primary"
              size="large"
              :loading="verifying"
              class="w-100"
              @click="handleVerify"
            >
              验证并进入管理后台
            </el-button>
          </div>
        </el-form>
      </el-card>

      <!-- Step 2: 推荐管理主面板 -->
      <div v-else class="management-panel">
        <el-card class="panel-card" shadow="hover">
          <!-- 日期选择与状态 -->
          <div class="date-selector-row">
            <div class="date-select-group">
              <span class="label">管理日期：</span>
              <el-date-picker
                v-model="targetDate"
                type="date"
                placeholder="选择管理日期"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
                @change="loadDateConfig"
              />
              <el-button :loading="loadingData" @click="loadDateConfig">
                <el-icon><RefreshRight /></el-icon>
                <span>重新加载</span>
              </el-button>
            </div>

            <div class="status-group">
              <span class="label">当前模式：</span>
              <el-tag v-if="currentIsManual" type="warning" effect="dark" round>
                ✨ 人工特别指定
              </el-tag>
              <el-tag v-else type="success" effect="light" round>
                🎲 算法自动轮播
              </el-tag>
            </div>
          </div>

          <el-divider />

          <!-- 配置表单 -->
          <el-form label-position="top">
            <!-- 今日主打星 (Hero Spotlight) -->
            <el-form-item label="⭐ 今日主打星 (Hero Spotlight)">
              <div class="form-tip">置顶展示于每日推荐页面最上方的大图卡片中。留空则由算法自动推选今日最高分作品。</div>
              <el-select
                v-model="heroId"
                placeholder="搜索或选择模组作品作为主打星"
                filterable
                clearable
                class="w-100"
                size="large"
              >
                <el-option
                  v-for="res in resourceOptions"
                  :key="res.id"
                  :label="`#${res.id} - ${res.title} (作者: ${res.author_username || '未知'})`"
                  :value="res.id"
                />
              </el-select>
            </el-form-item>

            <!-- 精选模组流 (Picks) -->
            <el-form-item :label="`✨ 精选推荐模组列表 (已选 ${pickedIds.length} 项)`">
              <div class="form-tip">
                支持按选择顺序锁定今日推荐卡片流。如果所选不足，算法会自动用当天的轮播作品补齐。
              </div>
              <el-select
                v-model="pickedIds"
                placeholder="选择要加入今日精选的模组作品（可多选）"
                multiple
                filterable
                class="w-100"
                size="large"
              >
                <el-option
                  v-for="res in resourceOptions"
                  :key="res.id"
                  :label="`#${res.id} - ${res.title} (作者: ${res.author_username || '未知'})`"
                  :value="res.id"
                />
              </el-select>
            </el-form-item>
          </el-form>

          <!-- 操作按钮栏 -->
          <div class="panel-footer-actions">
            <el-popconfirm
              title="确定要恢复该日期的算法自动推荐吗？"
              confirm-button-text="确定恢复"
              cancel-button-text="取消"
              @confirm="handleReset"
            >
              <template #reference>
                <el-button type="danger" plain :loading="saving">
                  恢复算法自动推荐
                </el-button>
              </template>
            </el-popconfirm>

            <div class="spacer"></div>

            <el-button size="large" @click="$router.push('/daily')">
              查看前台页面
            </el-button>
            <el-button type="primary" size="large" :loading="saving" @click="handleSave">
              保存当前推荐配置
            </el-button>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { View, RefreshRight } from '@element-plus/icons-vue'
import {
  getDailyRecommendations,
  verifyDailyAdminPassword,
  overrideDailyRecommendations,
  resetDailyRecommendations,
  listResources,
  type ResourceItem
} from '../api/resources'

const adminVerified = ref(false)
const passwordInput = ref('')
const verifying = ref(false)
const saving = ref(false)
const loadingData = ref(false)

const targetDate = ref('')
const currentIsManual = ref(false)
const heroId = ref<number | null>(null)
const pickedIds = ref<number[]>([])
const resourceOptions = ref<ResourceItem[]>([])

function getTodayString() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function getSavedPassword() {
  return sessionStorage.getItem('msut_daily_admin_pwd') || ''
}

async function handleVerify() {
  const pwd = passwordInput.value.trim()
  if (!pwd) {
    ElMessage.warning('请输入管理员密码')
    return
  }
  verifying.value = true
  try {
    await verifyDailyAdminPassword(pwd)
    sessionStorage.setItem('msut_daily_admin_pwd', pwd)
    adminVerified.value = true
    ElMessage.success('管理员验证成功')
    await initAdmin()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || '密码错误，验证失败')
  } finally {
    verifying.value = false
  }
}

function handleLogout() {
  sessionStorage.removeItem('msut_daily_admin_pwd')
  adminVerified.value = false
  passwordInput.value = ''
  ElMessage.info('已退出管理后台')
}

async function initAdmin() {
  if (!targetDate.value) {
    targetDate.value = getTodayString()
  }
  await Promise.all([loadResourceOptions(), loadDateConfig()])
}

async function loadResourceOptions() {
  try {
    const res = await listResources({ pageSize: 200 })
    resourceOptions.value = res.items || []
  } catch {
    // quiet ignore
  }
}

async function loadDateConfig() {
  if (!targetDate.value) return
  loadingData.value = true
  try {
    const res = await getDailyRecommendations(targetDate.value)
    currentIsManual.value = !!res.is_manual
    heroId.value = res.hero?.id || null
    pickedIds.value = res.picks?.map(p => p.id) || []
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || '加载日期配置失败')
  } finally {
    loadingData.value = false
  }
}

async function handleSave() {
  const pwd = getSavedPassword()
  if (!pwd) {
    ElMessage.error('凭证已失效，请重新登录')
    adminVerified.value = false
    return
  }
  saving.value = true
  try {
    await overrideDailyRecommendations({
      date: targetDate.value,
      hero_id: heroId.value,
      picked_ids: pickedIds.value,
      password: pwd
    })
    ElMessage.success(`成功保存 ${targetDate.value} 的推荐配置！`)
    await loadDateConfig()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || '保存推荐失败')
  } finally {
    saving.value = false
  }
}

async function handleReset() {
  const pwd = getSavedPassword()
  if (!pwd) {
    ElMessage.error('凭证已失效，请重新登录')
    adminVerified.value = false
    return
  }
  saving.value = true
  try {
    await resetDailyRecommendations(targetDate.value, pwd)
    ElMessage.success(`已恢复 ${targetDate.value} 的算法自动推荐！`)
    await loadDateConfig()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || '恢复自动推荐失败')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  const cached = getSavedPassword()
  if (cached) {
    passwordInput.value = cached
    try {
      await verifyDailyAdminPassword(cached)
      adminVerified.value = true
      await initAdmin()
    } catch {
      sessionStorage.removeItem('msut_daily_admin_pwd')
      adminVerified.value = false
    }
  }
})
</script>

<style scoped>
.admin-page-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 32px 16px 80px;
}

.admin-page-header {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 24px;
}

@media (min-width: 768px) {
  .admin-page-header {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }
}

.title {
  margin: 0 0 6px;
  font-size: 24px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.subtitle {
  margin: 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.header-right {
  display: flex;
  gap: 8px;
}

.auth-card {
  max-width: 480px;
  margin: 40px auto;
  border-radius: 14px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
}

.auth-hint {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
  margin-bottom: 20px;
}

.auth-hint code {
  background: var(--el-fill-color-light);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--el-color-danger);
}

.panel-card {
  border-radius: 14px;
}

.date-selector-row {
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: flex-start;
}

@media (min-width: 768px) {
  .date-selector-row {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }
}

.date-select-group,
.status-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.label {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-regular);
}

.form-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
  line-height: 1.4;
}

.panel-footer-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 28px;
  padding-top: 20px;
  border-top: 1px solid var(--el-border-color-lighter);
  flex-wrap: wrap;
}

.spacer {
  flex: 1;
}

.w-100 {
  width: 100%;
}

.mr-4 {
  margin-right: 4px;
}
</style>
