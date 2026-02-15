import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Vue 核心库单独打包
          'vendor-vue': ['vue', 'vue-router', 'pinia'],
          // ECharts 图表库单独打包（较大）
          'vendor-echarts': ['echarts', 'vue-echarts'],
          // Axios HTTP 客户端单独打包
          'vendor-axios': ['axios']
        }
      }
    },
    // 启用 CSS 代码分割
    cssCodeSplit: true,
    // 设置 chunk 大小警告限制为 600kb
    chunkSizeWarningLimit: 600
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      // WebSocket 代理（必须放在 /api 前面，更精确的路径优先匹配）
      '/api/ws': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true,  // ✅ 启用 WebSocket 代理
      },
      // REST API 代理
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    }
  }
})