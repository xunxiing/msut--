<template>
  <section class="m-hero">
    <el-tag size="small" effect="dark" type="success" round>🍉 甜瓜联合科技</el-tag>
    <h1 class="m-hero-title">让甜瓜游乐场更好玩</h1>
    <p class="m-hero-sub">免费模组 · 在线工具 · AI创作</p>
    <el-button type="primary" size="large" class="m-hero-btn" @click="$router.push('/resources')">
      浏览免费模组
    </el-button>
  </section>

  <!-- 快捷入口 -->
  <div class="m-grid">
    <div class="m-grid-item" v-for="f in features" :key="f.title" @click="$router.push(f.to)">
      <div class="m-grid-icon"><el-icon :size="22"><component :is="f.icon" /></el-icon></div>
      <span class="m-grid-label">{{ f.title }}</span>
    </div>
  </div>

  <!-- 免费模组横幅 -->
  <div class="m-banner" @click="$router.push('/resources')">
    <div class="m-banner-text">
      <el-tag type="danger" effect="dark" round size="small">🔥 免费</el-tag>
      <span class="m-banner-title">模组文件库</span>
      <span class="m-banner-desc">海量 .melsave 模组免费下载</span>
    </div>
    <el-icon :size="28" color="var(--el-color-success)"><FolderOpened /></el-icon>
  </div>

  <!-- 工具列表 -->
  <div class="m-section">
    <h3 class="m-section-title">在线工具</h3>
    <div class="m-tool-list">
      <div class="m-tool-item" v-for="t in tools" :key="t.name" @click="$router.push(t.to)">
        <el-icon :size="20"><component :is="t.icon" /></el-icon>
        <div class="m-tool-info">
          <span class="m-tool-name">{{ t.name }}</span>
          <span class="m-tool-desc">{{ t.desc }}</span>
        </div>
        <el-icon class="m-tool-arrow"><ArrowRight /></el-icon>
      </div>
    </div>
  </div>

  <!-- 快速开始 -->
  <div class="m-section">
    <h3 class="m-section-title">快速开始</h3>
    <div class="m-steps">
      <div class="m-step" v-for="(s, i) in steps" :key="i">
        <div class="m-step-num">{{ i + 1 }}</div>
        <div class="m-step-text">{{ s }}</div>
      </div>
    </div>
  </div>

  <footer class="m-footer">
    <span>🍉 甜瓜联合科技 · 玩家社区</span>
  </footer>
</template>

<script setup lang="ts">
import {
  FolderOpened, MagicStick, Reading, ChatLineRound, Cpu, ArrowRight
} from '@element-plus/icons-vue'

const features = [
  { title: '模组库', icon: FolderOpened, to: '/resources' },
  { title: 'AI生成', icon: MagicStick, to: '/tutorials/ai' },
  { title: '教程', icon: Reading, to: '/tutorials' },
  { title: 'Lua沙盒', icon: Cpu, to: '/dsl' },
]

const tools = [
  { name: 'DSL 生成器', desc: '快速生成 .melsave', icon: MagicStick, to: '/dsl' },
  { name: 'AI 对话助手', desc: '自然语言生成存档', icon: ChatLineRound, to: '/tutorials/ai' },
  { name: '水印检测', desc: '验证文件来源', icon: Reading, to: '/watermark' },
]

const steps = ['注册账号，管理你的作品', '从文件库下载模组', '导入甜瓜游乐场']
</script>

<style scoped>
.m-hero {
  text-align: center;
  padding: 48px 20px 32px;
  background: radial-gradient(800px 400px at 50% -100px, var(--el-color-success-light-7), transparent 70%);
}
.m-hero-title {
  font-size: 26px;
  font-weight: 800;
  margin: 14px 0 6px;
}
.m-hero-sub {
  color: var(--el-text-color-secondary);
  font-size: 15px;
  margin: 0 0 20px;
}
.m-hero-btn {
  width: 80%;
  max-width: 300px;
}

/* 快捷入口网格 */
.m-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  padding: 0 16px 20px;
}
.m-grid-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 4px;
  background: var(--el-fill-color-light);
  border-radius: 14px;
  cursor: pointer;
}
.m-grid-icon {
  width: 38px; height: 38px;
  border-radius: 10px;
  display: grid; place-items: center;
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
}
.m-grid-label {
  font-size: 12px;
  font-weight: 600;
}

/* 横幅 */
.m-banner {
  margin: 0 16px 20px;
  padding: 16px;
  border-radius: 16px;
  background: linear-gradient(135deg, var(--el-color-success-light-9), var(--el-color-success-light-8));
  border: 1px solid var(--el-color-success-light-7);
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
}
.m-banner-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.m-banner-title {
  font-weight: 800;
  font-size: 18px;
  margin-top: 2px;
}
.m-banner-desc {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

/* 工具列表 */
.m-section {
  padding: 0 16px 20px;
}
.m-section-title {
  font-size: 17px;
  font-weight: 700;
  margin: 0 0 12px;
}
.m-tool-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.m-tool-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  background: var(--el-fill-color-light);
  border-radius: 14px;
  cursor: pointer;
}
.m-tool-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.m-tool-name {
  font-weight: 600;
  font-size: 15px;
}
.m-tool-desc {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.m-tool-arrow {
  color: var(--el-text-color-placeholder);
}

/* 步骤 */
.m-steps {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.m-step {
  display: flex;
  align-items: center;
  gap: 12px;
}
.m-step-num {
  width: 24px; height: 24px;
  border-radius: 50%;
  background: var(--el-color-success);
  color: #fff;
  display: grid; place-items: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}
.m-step-text {
  font-size: 14px;
}

/* 页脚 */
.m-footer {
  text-align: center;
  padding: 20px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  border-top: 1px solid var(--el-border-color);
}
</style>
