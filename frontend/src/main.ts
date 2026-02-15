import { createApp } from 'vue'
import { createPinia } from 'pinia'
import axios from 'axios'
import App from './App.vue'
import router from './router'

// 配置 axios 默认设置
axios.defaults.timeout = 10000  // 10秒超时
axios.defaults.headers.common['Content-Type'] = 'application/json'

// 配置 API Token 认证
// 开发模式从环境变量或使用默认值
const apiToken = import.meta.env.VITE_API_TOKEN || 'dev-token-123'
axios.defaults.headers.common['Authorization'] = `Bearer ${apiToken}`

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
