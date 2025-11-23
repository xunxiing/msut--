<template>
  <div class="agent-right-panel">
    <div class="panel-header">
      <h3>任务状态</h3>
    </div>
    
    <div class="panel-content">
      <div v-if="!currentRunId" class="idle-state">
        <el-empty description="暂无进行中的任务" :image-size="80" />
      </div>
      
      <div v-else class="status-card">
        <div class="status-header">
          <span class="status-label">当前状态</span>
          <el-tag :type="getStatusType(status)">{{ getStatusText(status) }}</el-tag>
        </div>
        
        <div class="status-steps">
          <el-steps direction="vertical" :active="activeStep" finish-status="success">
            <el-step title="接收指令" />
            <el-step title="思考与规划" />
            <el-step title="执行工具" description="生成代码 / 检索信息" />
            <el-step title="完成任务" />
          </el-steps>
        </div>

        <div
          v-if="toolPreview && status !== 'idle'"
          class="tool-preview-card"
        >
          <h4>工具输入</h4>
          <div class="tool-preview-meta">
            <span class="tool-preview-label">工具：</span>
            <span class="tool-preview-name">{{ toolPreview.name }}</span>
          </div>
          <pre class="tool-preview-body">{{ toolPreview.arguments }}</pre>
        </div>

        <div v-if="resultUrl" class="result-card">
          <h4>生成结果</h4>
          <div class="file-item">
            <el-icon><Document /></el-icon>
            <span class="filename">{{ resultName || 'generated_file' }}</span>
            <DownloadButton
              :href="resultUrl"
              :download-name="resultName || ''"
              as="link"
              class="download-link"
            >
              下载
            </DownloadButton>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Document } from '@element-plus/icons-vue'
import DownloadButton from '../DownloadButton.vue'

const props = defineProps<{
  status: string
  currentRunId?: number
  resultUrl?: string
  resultName?: string
  toolPreview?: { name: string; arguments: string } | null
}>()

const activeStep = computed(() => {
  if (!props.currentRunId) return 0
  if (props.status === 'pending') return 1
  if (props.status === 'running') {
    // 当已经开始构造工具参数时，把步骤推进到“执行工具”。
    return props.toolPreview ? 3 : 2
  }
  if (props.status === 'succeeded' || props.status === 'failed') return 4
  return 0
})

function getStatusType(status: string) {
  switch (status) {
    case 'running': return 'primary'
    case 'succeeded': return 'success'
    case 'failed': return 'danger'
    default: return 'info'
  }
}

function getStatusText(status: string) {
  switch (status) {
    case 'pending': return '等待中'
    case 'running': return '执行中'
    case 'succeeded': return '已完成'
    case 'failed': return '失败'
    default: return '空闲'
  }
}
</script>

<style scoped>
.agent-right-panel {
  width: 100%;
  background: #ffffff;
  border-left: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow: hidden;
}

.panel-header {
  padding: 16px;
  border-bottom: 1px solid #f3f4f6;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.panel-content {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
}

.idle-state {
  padding-top: 40px;
}

.status-card {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-label {
  font-size: 14px;
  color: #6b7280;
}

.status-steps {
  margin-bottom: 8px;
}

.tool-preview-card {
  margin-top: 8px;
  background: #f9fafb;
  padding: 12px 14px;
  border-radius: 8px;
  border: 1px dashed #e5e7eb;
  font-size: 12px;
  color: #374151;
}

.tool-preview-card h4 {
  margin: 0 0 6px;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}

.tool-preview-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.tool-preview-label {
  color: #6b7280;
}

.tool-preview-name {
  font-weight: 500;
}

.tool-preview-body {
  margin: 0;
  padding: 8px;
  max-height: 220px;
  overflow-y: auto;
  border-radius: 6px;
  background: #111827;
  color: #e5e7eb;
  font-size: 12px;
  line-height: 1.4;
  white-space: pre-wrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
    "Liberation Mono", "Courier New", monospace;
}

.result-card {
  background: #f9fafb;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.result-card h4 {
  margin: 0 0 12px;
  font-size: 14px;
  color: #374151;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #4b5563;
}

.filename {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.download-link {
  color: #3b82f6;
  text-decoration: none;
  font-weight: 500;
}

.download-link:hover {
  text-decoration: underline;
}
</style>
