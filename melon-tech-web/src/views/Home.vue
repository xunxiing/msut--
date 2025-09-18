<template>
  <!-- 顶部英雄区 -->
  <section class="hero">
    <div class="hero-inner">
      <el-tag size="large" effect="dark" type="success" round>🍉 甜瓜联合科技</el-tag>
      <h1 class="hero-title">让「甜瓜游乐场」更好玩</h1>
      <p class="hero-subtitle">
        民间玩家组织，专注于为甜瓜游乐场提供丰富的第三方工具与攻略，帮助玩家更轻松地管理、创造和分享。
      </p>

      <div class="hero-actions">
        <el-button type="primary" size="large" @click="$router.push('/about')">
          了解我们
          <el-icon class="ml-6"><Right /></el-icon>
        </el-button>
        <el-button size="large" @click="$router.push('/register')">
          加入社区
        </el-button>
      </div>

      <div class="hero-stats">
        <el-card shadow="never" class="glass">
          <el-row :gutter="18" align="middle">
            <el-col :xs="12" :sm="8">
              <div class="stat">
                <div class="stat-number">{{ stats.tools }}</div>
                <div class="stat-label">可用工具</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="8">
              <div class="stat">
                <div class="stat-number">{{ stats.guides }}</div>
                <div class="stat-label">攻略教程</div>
              </div>
            </el-col>
            <el-col :xs="24" :sm="8">
              <div class="stat">
                <div class="stat-number">{{ stats.players }}+</div>
                <div class="stat-label">服务玩家</div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </div>
    </div>
    <div class="hero-gradient"></div>
  </section>

  <!-- 功能亮点 -->
  <section class="section container">
    <div class="section-header">
      <h2>我们在做什么</h2>
      <p>围绕甜瓜游乐场的创作、管理和分享，提供稳定、易用、持续更新的周边工具。</p>
    </div>

    <el-row :gutter="16">
      <el-col v-for="f in features" :key="f.title" :xs="24" :sm="12" :lg="6">
        <el-card class="feature-card" shadow="hover">
          <div class="feature-icon">
            <el-icon :size="24">
              <component :is="f.icon" />
            </el-icon>
          </div>
          <div class="feature-body">
            <h3>{{ f.title }}</h3>
            <p>{{ f.desc }}</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </section>

  <!-- 精选工具 -->
  <section class="section container">
    <div class="section-header">
      <h2>精选工具</h2>
      <p>上手即用的小而美工具，减少折腾，专心玩得更爽。</p>
    </div>

    <el-row :gutter="16">
      <el-col v-for="t in tools" :key="t.name" :xs="24" :md="12" :lg="8">
        <el-card class="tool-card" shadow="always">
          <div class="tool-head">
            <div class="tool-name">
              <el-icon class="mr-8" :size="18"><component :is="t.icon" /></el-icon>
              {{ t.name }}
            </div>
            <el-tag size="small" type="success" v-if="t.new">NEW</el-tag>
          </div>
          <p class="tool-desc">{{ t.desc }}</p>
          <div class="tool-tags">
            <el-tag v-for="tag in t.tags" :key="tag" size="small" class="mr-6 mb-6" effect="light">
              {{ tag }}
            </el-tag>
          </div>
          <div class="tool-actions">
            <el-button type="primary" @click="goto(t.to)">立即使用</el-button>
            <el-button text @click="goto(t.doc)">文档</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </section>

  <!-- 快速开始 -->
  <section class="section container">
    <div class="section-header">
      <h2>快速开始</h2>
      <p>三步完成，从安装到上手，不需要和电脑打仗。</p>
    </div>

    <el-steps :active="3" align-center finish-status="success" class="steps">
      <el-step title="注册登录" description="创建账号，云端同步你的工具配置" />
      <el-step title="选择工具" description="从工具库挑选需要的模块，一键安装" />
      <el-step title="开始游玩" description="打开甜瓜游乐场，体验更顺滑的玩法" />
    </el-steps>
  </section>

  <!-- FAQ -->
  <section class="section container">
    <div class="section-header">
      <h2>常见问题</h2>
      <p>两分钟读完，少走弯路。</p>
    </div>

    <el-collapse class="faq">
      <el-collapse-item name="1">
        <template #title>
          工具是官方的吗？
        </template>
        我们是玩家自发组织，与官方无从属关系。工具均为第三方扩展，强调安全与可控。
      </el-collapse-item>

      <el-collapse-item name="2">
        <template #title>
          需要复杂配置吗？
        </template>
        不需要。大多数工具支持一键安装与自动更新，必要参数会有可视化引导。
      </el-collapse-item>

      <el-collapse-item name="3">
        <template #title>
          是否收费？
        </template>
        基础功能对所有玩家免费开放。部分增值工具可能需要赞助，费用透明可选。
      </el-collapse-item>
    </el-collapse>
  </section>

  <!-- 页脚 -->
  <footer class="footer">
    <div class="container footer-inner">
      <div class="brand">
        <span class="logo">🍉</span>
        <span class="name">甜瓜联合科技</span>
      </div>
      <div class="links">
        <el-link @click="$router.push('/about')">关于</el-link>
        <el-link @click="$router.push('/register')">加入</el-link>
        <el-link @click="$router.push('/login')">登录</el-link>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
  Tools, MagicStick, Connection, Compass, Star, Link as LinkIcon, TrendCharts, Setting, Cpu, Right
} from '@element-plus/icons-vue'

const stats = ref({
  tools: 42,
  guides: 68,
  players: 1200
})

type Feature = { title: string; desc: string; icon: any }
const features = ref<Feature[]>([
  { title: '工具集成', desc: '常用功能一站式集成，减少切换与兼容问题。', icon: Tools },
  { title: '创作增强', desc: '编辑、预设与资源管理，让创作更顺手。', icon: MagicStick },
  { title: '兼容更新', desc: '跟踪游戏版本变化，工具持续适配与提醒。', icon: Connection },
  { title: '社区协作', desc: '玩家分享最佳实践与素材，灵感不再短缺。', icon: Compass }
])

type ToolItem = { name: string; desc: string; tags: string[]; icon: any; to: string; doc: string; new?: boolean }
const tools = ref<ToolItem[]>([
  {
    name: '模组管理器',
    desc: '一键安装/启用/停用模组，自动处理依赖与冲突。',
    tags: ['一键安装', '依赖解析', '冲突检测'],
    icon: Setting,
    to: '/dashboard', doc: '/about', new: true
  },
  {
    name: '场景预设库',
    desc: '常用场景与物理参数保存为预设，随时复用与分享。',
    tags: ['预设', '分享', '云同步'],
    icon: Star,
    to: '/dashboard', doc: '/about'
  },
  {
    name: '数据分析器',
    desc: '对战记录、物理参数与性能数据可视化，优化玩法体验。',
    tags: ['统计', '可视化', '性能'],
    icon: TrendCharts,
    to: '/dashboard', doc: '/about'
  }
])

function goto(path: string) {
  if (!path) return
  // 简单路由跳转占位，真实项目里替换为具体路由
  // 这里默认存在 /dashboard 与 /about，可按你路由实际改动
  // @ts-ignore
  if (path.startsWith('/')) return (window as any).$router?.push?.(path) ?? (location.href = path)
  location.href = path
}
</script>

<style scoped>
/* 容器 */
.container {
  max-width: 1160px;
  margin: 0 auto;
  padding: 0 16px;
}

/* 英雄区 */
.hero {
  position: relative;
  padding: 96px 0 64px;
  overflow: clip;
  background: radial-gradient(1200px 600px at 50% -200px, var(--el-color-success-light-7), transparent 70%),
              linear-gradient(180deg, rgba(16,185,129,.06), rgba(255,255,255,0));
}
.hero-gradient {
  position: absolute;
  inset: -20% -10% auto -10%;
  height: 360px;
  background:
    radial-gradient(400px 200px at 15% -30px, rgba(16,185,129,.12), transparent 70%),
    radial-gradient(400px 200px at 85% -30px, rgba(16,185,129,.12), transparent 70%);
  filter: blur(20px);
  pointer-events: none;
}
.hero-inner {
  max-width: 960px;
  margin: 0 auto;
  text-align: center;
  padding: 0 16px;
}
.hero-title {
  margin: 16px 0 8px;
  font-weight: 800;
  font-size: clamp(28px, 4.2vw, 44px);
  letter-spacing: .2px;
}
.hero-subtitle {
  color: var(--el-text-color-secondary);
  max-width: 720px;
  margin: 0 auto;
  line-height: 1.8;
}
.hero-actions {
  margin-top: 20px;
  display: inline-flex;
  gap: 12px;
}
.hero-stats {
  margin-top: 28px;
}
.glass {
  background: rgba(255,255,255,.65);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(255,255,255,.6);
}
.stat { text-align: center; }
.stat-number {
  font-size: 28px;
  font-weight: 800;
  line-height: 1.1;
}
.stat-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

/* 模块区 */
.section {
  padding: 48px 0;
}
.section-header {
  text-align: center;
  margin-bottom: 18px;
}
.section-header h2 {
  font-size: 24px;
  margin: 0 0 6px;
}
.section-header p {
  color: var(--el-text-color-secondary);
}

/* 功能卡片 */
.feature-card {
  height: 100%;
  border-radius: 16px;
}
.feature-icon {
  width: 44px; height: 44px;
  border-radius: 12px;
  display: grid; place-items: center;
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
  margin-bottom: 10px;
}
.feature-body h3 {
  margin: 0 0 6px;
  font-weight: 700;
}
.feature-body p {
  color: var(--el-text-color-secondary);
  margin: 0;
}

/* 工具卡片 */
.tool-card {
  border-radius: 18px;
}
.tool-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 6px;
}
.tool-name {
  display: flex; align-items: center;
  font-weight: 700;
}
.tool-desc {
  color: var(--el-text-color-regular);
  margin: 8px 0 10px;
}
.tool-tags {
  margin-bottom: 10px;
}
.tool-actions {
  display: flex; gap: 8px;
}

/* 步骤条 */
.steps {
  max-width: 860px;
  margin: 0 auto;
}

/* FAQ */
.faq :deep(.el-collapse-item__header) {
  font-weight: 600;
}

/* 页脚 */
.footer {
  border-top: 1px solid var(--el-border-color);
  margin-top: 24px;
  padding: 20px 0;
  background: linear-gradient(180deg, rgba(16,185,129,.03), rgba(255,255,255,0));
}
.footer-inner {
  display: flex; align-items: center; justify-content: space-between;
}
.brand { display: flex; align-items: center; gap: 8px; }
.logo { font-size: 20px; }
.name { font-weight: 700; }
.links > * + * { margin-left: 12px; }

/* 小工具 */
.ml-6 { margin-left: 6px; }
.mr-8 { margin-right: 8px; }
.mb-6 { margin-bottom: 6px; }
</style>
