<template>
  <section class="hero">
    <div class="hero-gradient"></div>
    <div class="hero-inner">
      <el-tag size="large" effect="dark" type="success" round>🍉 甜瓜联合科技</el-tag>
      <h1 class="hero-title">让「甜瓜游乐场」更好玩</h1>
      <p class="hero-subtitle">
        免费模组、在线工具、AI 辅助创作、教程百科——甜瓜游乐场玩家的一站式社区平台。
      </p>
      <div class="hero-actions">
        <el-button type="primary" size="large" @click="$router.push('/resources')">
          浏览免费模组
          <el-icon class="ml-6"><Right /></el-icon>
        </el-button>
        <el-button size="large" @click="$router.push('/register')">
          加入社区
        </el-button>
      </div>
    </div>
  </section>

  <!-- 核心功能区 -->
  <section class="section container">
    <div class="section-header">
      <h2>核心功能</h2>
      <p>围绕甜瓜游乐场的创作、管理和分享，提供免费在线工具。</p>
    </div>

    <el-row :gutter="16">
      <el-col v-for="f in features" :key="f.title" :xs="24" :sm="12" :lg="6">
        <el-card class="feature-card" shadow="hover" @click="$router.push(f.to)">
          <div class="feature-icon">
            <el-icon :size="24"><component :is="f.icon" /></el-icon>
          </div>
          <div class="feature-body">
            <h3>{{ f.title }}</h3>
            <p>{{ f.desc }}</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </section>

  <!-- 免费模组文件库 -->
  <section class="section container highlight-section">
    <el-card shadow="never" class="highlight-card">
      <el-row :gutter="24" align="middle">
        <el-col :xs="24" :md="14">
          <el-tag type="danger" effect="dark" round size="small">🔥 免费模组</el-tag>
          <h2 class="highlight-title">海量模组文件库</h2>
          <p class="highlight-desc">
            站内玩家上传 + 站外资源聚合，一站式浏览、搜索、下载甜瓜游乐场模组文件（.melsave）。
            支持预览图片、按分类筛选，全部免费下载。
          </p>
          <div class="highlight-tags">
            <el-tag v-for="tag in resourceTags" :key="tag" size="small" effect="light" class="mr-6 mb-6">
              {{ tag }}
            </el-tag>
          </div>
          <div class="highlight-actions">
            <el-button type="primary" size="large" @click="$router.push('/resources')">
              进入文件库
              <el-icon class="ml-6"><Right /></el-icon>
            </el-button>
            <el-button size="large" @click="$router.push('/upload')" v-if="auth.user">上传我的作品</el-button>
            <el-button size="large" @click="$router.push('/register')" v-else>注册后上传</el-button>
          </div>
        </el-col>
        <el-col :xs="24" :md="10">
          <div class="highlight-visual">
            <el-icon :size="120" color="var(--el-color-success)"><FolderOpened /></el-icon>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </section>

  <!-- 在线工具 -->
  <section class="section container">
    <div class="section-header">
      <h2>在线工具</h2>
      <p>无需安装，浏览器直接使用，帮助你在甜瓜游乐场中更高效地创作。</p>
    </div>

    <el-row :gutter="16">
      <el-col v-for="t in tools" :key="t.name" :xs="24" :md="12" :lg="8">
        <el-card class="tool-card" shadow="always" @click="$router.push(t.to)">
          <div class="tool-head">
            <div class="tool-name">
              <el-icon class="mr-8" :size="18"><component :is="t.icon" /></el-icon>
              {{ t.name }}
            </div>
            <el-tag v-if="t.tag" :type="t.tagType" size="small" effect="dark">{{ t.tag }}</el-tag>
          </div>
          <p class="tool-desc">{{ t.desc }}</p>
        </el-card>
      </el-col>
    </el-row>
  </section>

  <!-- 快速开始 -->
  <section class="section container">
    <div class="section-header">
      <h2>快速开始</h2>
      <p>三步上手，从浏览到创作。</p>
    </div>
    <el-steps :active="3" align-center finish-status="success" class="steps">
      <el-step title="注册账号" description="创建账号，管理你的作品与收藏" />
      <el-step title="浏览模组" description="从文件库挑选感兴趣的 .melsave 文件" />
      <el-step title="下载游玩" description="导入甜瓜游乐场，或用 AI 生成你自己的作品" />
    </el-steps>
  </section>

  <!-- FAQ -->
  <section class="section container">
    <div class="section-header">
      <h2>常见问题</h2>
    </div>
    <el-collapse class="faq">
      <el-collapse-item name="1">
        <template #title>这些工具是官方的吗？</template>
        我们是玩家自发组织，与甜瓜游乐场官方无从属关系。所有工具和模组均为第三方创作，强调安全与可控。
      </el-collapse-item>
      <el-collapse-item name="2">
        <template #title>模组收费吗？</template>
        文件库中所有模组均免费下载。注册登录后即可上传和下载，无任何付费墙。
      </el-collapse-item>
      <el-collapse-item name="3">
        <template #title>AI 生成是什么？</template>
        通过自然语言描述，AI 自动生成 .melsave 存档文件。你只需要描述想要的场景或机关，AI 帮你编写 Lua 芯片并打包成可导入的文件。
      </el-collapse-item>
      <el-collapse-item name="4">
        <template #title>什么是水印检测？</template>
        上传的 .melsave 文件会嵌入水印信息。通过水印检测工具可以验证文件来源，保护创作者权益。
      </el-collapse-item>
    </el-collapse>
  </section>

  <footer class="footer">
    <div class="container footer-inner">
      <div class="brand">
        <span class="logo">🍉</span>
        <span class="name">甜瓜联合科技</span>
      </div>
      <div class="links">
        <el-link @click="$router.push('/about')">关于</el-link>
        <el-link @click="$router.push('/resources')">文件库</el-link>
        <el-link @click="$router.push('/tutorials')">教程</el-link>
        <el-link @click="$router.push('/register')">加入</el-link>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../stores/auth'
import {
  FolderOpened, MagicStick, Reading, Lock, ChatLineRound, Cpu, Right
} from '@element-plus/icons-vue'

const router = useRouter()
const auth = useAuth()

onMounted(() => {
  if (window.innerWidth < 768) {
    router.replace('/m')
  }
})

const resourceTags = ['站内上传', '站外聚合', '.melsave', '免费下载', '图片预览', '分类筛选']

type Feature = { title: string; desc: string; icon: any; to: string }
const features = ref<Feature[]>([
  { title: '免费模组库', desc: '站内 + 站外资源聚合，一站式浏览下载 .melsave 文件。', icon: FolderOpened, to: '/resources' },
  { title: 'AI 生成', desc: '自然语言描述场景，AI 自动生成存档文件与 Lua 芯片。', icon: MagicStick, to: '/tutorials/ai' },
  { title: '教程百科', desc: 'RAG 驱动的智能教程搜索，AI 问答随时解决疑问。', icon: Reading, to: '/tutorials' },
  { title: 'Lua 沙盒', desc: '在线运行甜瓜游乐场 Lua 芯片，调试输出与物理模拟。', icon: Cpu, to: '/dsl' },
])

type ToolItem = { name: string; desc: string; icon: any; to: string; tag?: string; tagType?: string }
const tools = ref<ToolItem[]>([
  {
    name: 'DSL 生成器',
    desc: '通过 DSL 描述语法快速生成 .melsave 存档文件，无需手动编辑。',
    icon: MagicStick, to: '/dsl'
  },
  {
    name: 'AI 对话助手',
    desc: '与 AI 对话，描述你想要的场景或机关，自动生成可导入的存档。',
    icon: ChatLineRound, to: '/tutorials/ai', tag: 'AI', tagType: 'success'
  },
  {
    name: '水印检测',
    desc: '验证 .melsave 文件的水印信息，追溯文件来源，保护创作者权益。',
    icon: Lock, to: '/watermark'
  },
])
</script>

<style scoped>
.container {
  max-width: 1160px;
  margin: 0 auto;
  padding: 0 16px;
}

/* 英雄区 */
.hero {
  position: relative;
  padding: 80px 0 56px;
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
  position: relative;
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
  margin-top: 24px;
  display: inline-flex;
  gap: 12px;
}

/* 模块区 */
.section {
  padding: 40px 0;
}
.section-header {
  text-align: center;
  margin-bottom: 20px;
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
  cursor: pointer;
  transition: transform .2s;
}
.feature-card:hover {
  transform: translateY(-4px);
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

/* 高亮区：免费模组文件库 */
.highlight-section {
  padding: 24px 0;
}
.highlight-card {
  border-radius: 20px;
  background: linear-gradient(135deg, var(--el-color-success-light-9), var(--el-color-success-light-8));
  border: 1px solid var(--el-color-success-light-7);
}
.highlight-title {
  font-size: 26px;
  font-weight: 800;
  margin: 12px 0 8px;
}
.highlight-desc {
  color: var(--el-text-color-regular);
  line-height: 1.8;
  margin: 0 0 16px;
}
.highlight-tags {
  margin-bottom: 20px;
}
.highlight-actions {
  display: flex; gap: 8px; flex-wrap: wrap;
}
.highlight-visual {
  display: flex; align-items: center; justify-content: center;
  opacity: .8;
}

/* 工具卡片 */
.tool-card {
  border-radius: 18px;
  cursor: pointer;
  transition: transform .2s;
}
.tool-card:hover {
  transform: translateY(-4px);
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
  margin: 8px 0 0;
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
.mr-6 { margin-right: 6px; }
.mb-6 { margin-bottom: 6px; }
</style>
