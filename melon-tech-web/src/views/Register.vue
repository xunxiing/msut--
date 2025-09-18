<template>
  <el-row justify="center" style="margin-top: 10vh">
    <el-col :xs="22" :sm="16" :md="10" :lg="8">
      <el-card>
        <template #header>注册</template>

        <el-form ref="formRef" :model="form" :rules="rules" label-width="80px" @submit.prevent="onSubmit">
          <el-form-item label="昵称" prop="name">
            <el-input v-model="form.name" autocomplete="nickname" />
          </el-form-item>
          <el-form-item label="邮箱" prop="email">
            <el-input v-model="form.email" autocomplete="email" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input v-model="form.password" type="password" show-password autocomplete="new-password" />
          </el-form-item>

          <el-space>
            <el-button type="primary" :loading="auth.loading" @click="onSubmit">注册并登录</el-button>
            <el-button link @click="$router.push('/login')">已有账号</el-button>
          </el-space>
        </el-form>

        <el-alert v-if="auth.error" :title="auth.error" type="error" show-icon style="margin-top:12px" />
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useAuth } from '../stores/auth'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

const auth = useAuth()
const router = useRouter()
const formRef = ref<FormInstance>()
const form = reactive({ name: '', email: '', password: '' })
const rules: FormRules = {
  name: [{ required: true, message: '请输入昵称', trigger: 'blur' }, { min: 1, max: 32, message: '1-32 个字符', trigger: 'blur' }],
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式不对', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, message: '至少 6 位', trigger: 'blur' }]
}

const onSubmit = async () => {
  await formRef.value?.validate()
  try {
    await auth.register(form)
    ElMessage.success('注册成功，已登录')
    router.replace('/dashboard')
  } catch {}
}
</script>
