/**
 * UPS 能力检测 composable
 *
 * 通过 NUT LIST CMD 查询 UPS 实际支持的命令，
 * 用于在前端禁用不支持的功能按钮。
 */
import { ref, onMounted } from 'vue'

export interface UpsCapabilities {
  quick_test: boolean
  deep_test: boolean
  test_stop: boolean
  beeper_toggle: boolean
  beeper_enable: boolean
  beeper_disable: boolean
  beeper_mute: boolean
}

const defaultCapabilities: UpsCapabilities = {
  quick_test: true,
  deep_test: true,
  test_stop: true,
  beeper_toggle: false,
  beeper_enable: true,
  beeper_disable: true,
  beeper_mute: true,
}

// 获取 API Token（与 useWebSocket 保持一致）
function getApiToken(): string {
  return (window as any).__UPS_GUARD_TOKEN__ || import.meta.env.VITE_API_TOKEN || ''
}

export function useUpsCapabilities() {
  const capabilities = ref<UpsCapabilities>({ ...defaultCapabilities })
  const supportedCommands = ref<string[]>([])
  const loading = ref(true)
  const error = ref<string | null>(null)

  const fetchCapabilities = async () => {
    loading.value = true
    error.value = null

    try {
      const token = getApiToken()
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      }
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      const res = await fetch('/api/ups/supported-commands', { headers })

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`)
      }

      const data = await res.json()

      if (data.capabilities) {
        capabilities.value = {
          ...defaultCapabilities,
          ...data.capabilities,
        }
      }

      if (data.supported_commands) {
        supportedCommands.value = data.supported_commands
      }

      console.log('[useUpsCapabilities] Loaded:', capabilities.value)
    } catch (e) {
      console.warn('[useUpsCapabilities] Failed to load:', e)
      error.value = e instanceof Error ? e.message : String(e)
      // 失败时保持默认值（假设所有功能可用）
    } finally {
      loading.value = false
    }
  }

  // 检查特定命令是否支持
  const isCommandSupported = (command: string): boolean => {
    return supportedCommands.value.includes(command)
  }

  // 获取蜂鸣器最佳操作方式
  const getBeeperAction = (desiredAction: 'enable' | 'disable' | 'mute'): string => {
    const commandMap: Record<string, string> = {
      enable: 'beeper.enable',
      disable: 'beeper.disable',
      mute: 'beeper.mute',
    }

    const targetCommand = commandMap[desiredAction]

    // 如果目标命令不支持但 toggle 支持，返回 toggle
    if (!isCommandSupported(targetCommand) && isCommandSupported('beeper.toggle')) {
      return 'toggle'
    }

    return desiredAction
  }

  onMounted(() => {
    fetchCapabilities()
  })

  return {
    capabilities,
    supportedCommands,
    loading,
    error,
    fetchCapabilities,
    isCommandSupported,
    getBeeperAction,
  }
}

