<template>
  <el-row justify="center" style="margin-top: 10vh">
    <el-col :xs="22" :sm="16" :md="10" :lg="8">
      <el-card>
        <template #header>登录</template>

        <el-form ref="formRef" :model="form" :rules="rules" label-width="80px" @submit.prevent="onSubmit">
          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" autocomplete="username" />
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
const form = reactive({ username: '', password: '' })
const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }, { min: 3, max: 32, message: '用户名长度为 3-32 位', trigger: 'blur' }],
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
