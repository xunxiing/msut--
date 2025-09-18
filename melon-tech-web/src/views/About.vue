<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">关于本项目</div>
    </template>
    <el-descriptions :column="1" border>
      <el-descriptions-item label="框架">Vue 3</el-descriptions-item>
      <el-descriptions-item label="构建">Vite</el-descriptions-item>
      <el-descriptions-item label="语言">TypeScript</el-descriptions-item>
      <el-descriptions-item label="组件库">Element Plus</el-descriptions-item>
    </el-descriptions>
  </el-card>
</template>

<script setup lang="ts">
</script>

<style scoped>
.card-header { font-weight: 600; }
</style>
