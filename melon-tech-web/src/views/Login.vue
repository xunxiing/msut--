<template>
  <el-row justify="center" style="margin-top: 10vh">
    <el-col :xs="22" :sm="16" :md="10" :lg="8">
      <el-card>
        <template #header>登录</template>

        <el-form ref="formRef" :model="form" :rules="rules" label-width="80px" @submit.prevent="onSubmit">
          <el-form-item label="邮箱" prop="email">
            <el-input v-model="form.email" autocomplete="email" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input v-model="form.password" type="password" show-password autocomplete="current-password" />
          </el-form-item>

          <el-space>
            <el-button type="primary" :loading="auth.loading" @click="onSubmit">登录</el-button>
            <el-button link @click="$router.push('/register')">去注册</el-button>
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
import { useRoute, useRouter } from 'vue-router'

const auth = useAuth()
const router = useRouter()
const route = useRoute()
const formRef = ref<FormInstance>()
const form = reactive({ email: '', password: '' })
const rules: FormRules = {
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式不对', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, message: '至少 6 位', trigger: 'blur' }]
}

const onSubmit = async () => {
  await formRef.value?.validate()
  try {
    await auth.login(form)
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.replace(redirect)
  } catch {}
}
</script>
