<template>
  <div v-if="visible" class="welcome-guide-overlay">
    <div class="guide-container">
      <div class="guide-content">
        <div class="animation-stage">
          <div class="icon-box">
            <el-icon :size="64" color="#409EFF"><FolderOpened /></el-icon>
          </div>
          <h2>欢迎来到作品管理中心</h2>
          <p>在这里，您可以轻松管理您的所有存档文件和教程文档。</p>
          <ul class="features-list">
            <li>
              <el-icon><Document /></el-icon>
              <span>存档文件：上传、下载、分享您的游戏存档</span>
            </li>
            <li>
              <el-icon><Reading /></el-icon>
              <span>教程文档：创建和编辑您的专属教程</span>
            </li>
          </ul>
        </div>
        <div class="actions">
          <el-button type="primary" size="large" @click="finishGuide">开始体验</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { FolderOpened, Document, Reading } from '@element-plus/icons-vue'

const visible = ref(false)
const STORAGE_KEY = 'msut_works_guide_seen'

onMounted(() => {
  const seen = localStorage.getItem(STORAGE_KEY)
  if (!seen) {
    visible.value = true
  }
})

function finishGuide() {
  visible.value = false
  localStorage.setItem(STORAGE_KEY, 'true')
}
</script>

<style scoped>
.welcome-guide-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 0.3s ease-out;
}

.guide-container {
  background: white;
  border-radius: 24px;
  padding: 40px;
  width: 90%;
  max-width: 480px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
  animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  text-align: center;
}

.animation-stage {
  margin-bottom: 32px;
}

.icon-box {
  background: var(--el-color-primary-light-9);
  width: 120px;
  height: 120px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24px;
  animation: bounce 2s infinite ease-in-out;
}

h2 {
  font-size: 24px;
  color: #303133;
  margin-bottom: 12px;
}

p {
  color: #606266;
  margin-bottom: 24px;
  line-height: 1.6;
}

.features-list {
  list-style: none;
  padding: 0;
  margin: 0;
  text-align: left;
  background: #f5f7fa;
  border-radius: 12px;
  padding: 16px;
}

.features-list li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  color: #606266;
}

.features-list li .el-icon {
  color: var(--el-color-primary);
}

.actions {
  display: flex;
  justify-content: center;
}

.actions .el-button {
  width: 100%;
  border-radius: 12px;
  font-weight: 600;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}
</style>
