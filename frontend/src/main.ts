import { createApp } from 'vue'
import { createPinia } from 'pinia'
import axios from 'axios'
import App from './App.vue'
import router from './router'

// 配置 axios 默认设置
axios.defaults.timeout = 10000  // 10秒超时
axios.defaults.headers.common['Content-Type'] = 'application/json'

async function bootstrap() {
  // 1. 从后端获取 API Token（bootstrap 接口免认证）
  let apiToken = ''
  try {
    const resp = await axios.get('/api/bootstrap')
    apiToken = resp.data.token
  } catch (e) {
    console.error('Failed to bootstrap API token:', e)
    // 降级：尝试环境变量（开发环境）
    apiToken = import.meta.env.VITE_API_TOKEN || ''
  }

  // 2. 配置 axios 全局认证头
  if (apiToken) {
    axios.defaults.headers.common['Authorization'] = `Bearer ${apiToken}`
  }

  // 3. 将 Token 存储在全局变量中，供 WebSocket 连接使用
  ;(window as any).__UPS_GUARD_TOKEN__ = apiToken

  // 4. 创建并挂载 Vue 应用
  const app = createApp(App)
  app.use(createPinia())
  app.use(router)
  app.mount('#app')
}

bootstrap()
