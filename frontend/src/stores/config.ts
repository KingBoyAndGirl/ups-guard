/**
 * 配置状态 Store
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export const useConfigStore = defineStore('config', () => {
  // 测试模式状态
  const testMode = ref('production')
  const mockMode = ref(false)

  // 是否处于测试模式
  const isTestMode = computed(() => {
    // Always show badge unless BOTH are in production mode
    return testMode.value !== 'production' || mockMode.value === true
  })

  // 测试模式标签
  const testModeLabel = computed(() => {
    if (mockMode.value) return 'Mock Mode'
    if (testMode.value === 'dry_run') return '演练模式'
    if (testMode.value === 'mock') return 'Mock 模式'
    return ''
  })

  // 加载配置
  const loadConfig = async () => {
    try {
      const response = await axios.get('/api/config')
      testMode.value = response.data.test_mode || 'production'
    } catch (error) {
      console.error('Failed to load config:', error)
    }
  }

  // 检查 Mock 模式
  const checkMockMode = async () => {
    try {
      const response = await axios.get('/health')
      mockMode.value = response.data.mock_mode || false
    } catch (error) {
      console.error('Failed to check mock mode:', error)
    }
  }

  // 更新测试模式（保存配置后调用）
  const setTestMode = (mode: string) => {
    testMode.value = mode
  }

  // 初始化
  const init = async () => {
    await Promise.all([loadConfig(), checkMockMode()])
  }

  return {
    testMode,
    mockMode,
    isTestMode,
    testModeLabel,
    loadConfig,
    checkMockMode,
    setTestMode,
    init
  }
})

