import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'  // 样式很关键，别漏
import { createPinia } from 'pinia'
import { useAuth } from './stores/auth'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')

// 启动时拉取登录状态
const auth = useAuth()
auth.fetchMe().catch(() => {})
