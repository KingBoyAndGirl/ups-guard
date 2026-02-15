/**
 * WebSocket 实时连接 - 单例模式
 * 确保全局只有一个 WebSocket 连接，所有组件共享同一个数据
 */
import { ref, onUnmounted } from 'vue'
import type { UpsData } from '@/types/ups'

// 全局单例状态
const connected = ref(false)
const data = ref<UpsData | null>(null)
const error = ref<string | null>(null)
const latestHookProgress = ref<any>(null)  // 最新的 Hook 执行进度更新
const connectionEvent = ref<{ type: string; message: string; timestamp: number } | null>(null)  // NUT 连接状态事件
const lastReceivedAt = ref<number>(0)  // 客户端最后收到数据的时间戳（用于判断数据是否过时）

let ws: WebSocket | null = null
let reconnectTimer: number | null = null
let heartbeatTimer: number | null = null
let connectionCount = 0  // 跟踪有多少组件正在使用

const connect = () => {
  // 如果已经连接或正在连接，不重复连接
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  // 添加 token 参数进行认证
  const apiToken = import.meta.env.VITE_API_TOKEN || 'dev-token-123'
  const wsUrl = `${protocol}//${window.location.host}/api/ws?token=${apiToken}`

  try {
    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      connected.value = true
      error.value = null

      // 启动心跳
      startHeartbeat()
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)

        if (message.type === 'status_update') {
          data.value = message.data
          lastReceivedAt.value = Date.now()  // 记录客户端收到数据的时间
        } else if (message.type === 'shutdown_countdown') {
          // 处理关机倒计时更新
          if (data.value) {
            data.value = {
              ...data.value,
              shutdown: {
                ...data.value.shutdown,
                remaining_seconds: message.data.remaining_seconds,
                in_final_countdown: message.data.in_final_countdown,
                shutting_down: true
              }
            }
            lastReceivedAt.value = Date.now()  // 记录客户端收到数据的时间
          }
        } else if (message.type === 'hook_progress') {
          // 处理 hook 执行进度
          latestHookProgress.value = message.data
        } else if (message.type === 'event') {
          // 处理服务端推送的事件（如 NUT 连接状态变化）
          const eventData = message.data
          if (eventData.event_type === 'NUT_DISCONNECTED' || eventData.event_type === 'NUT_RECONNECTED') {
            connectionEvent.value = {
              type: eventData.event_type,
              message: eventData.message,
              timestamp: Date.now()
            }
            console.log(`[WebSocket] Connection event: ${eventData.event_type} - ${eventData.message}`)
          }
        } else if (message.type === 'heartbeat') {
          // 心跳响应
          console.debug('Heartbeat received')
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }

    ws.onerror = (e) => {
      console.error('WebSocket error:', e)
      error.value = 'WebSocket 连接错误'
    }

    ws.onclose = () => {
      connected.value = false
      stopHeartbeat()

      // 如果还有组件在使用，自动重连
      if (connectionCount > 0) {
        reconnectTimer = window.setTimeout(() => {
          connect()
        }, 5000)
      }
    }
  } catch (e) {
    console.error('Failed to create WebSocket:', e)
    error.value = 'WebSocket 连接失败'
  }
}

const disconnect = () => {
  if (ws) {
    ws.close()
    ws = null
  }

  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }

  stopHeartbeat()
}

const startHeartbeat = () => {
  if (heartbeatTimer) return

  heartbeatTimer = window.setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send('ping')
    }
  }, 25000) // 每 25 秒发送心跳
}

const stopHeartbeat = () => {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
}

export function useWebSocket() {
  // 组件挂载时增加连接计数
  connectionCount++

  // 首次使用时建立连接
  if (connectionCount === 1) {
    connect()
  }

  // 组件卸载时减少计数
  onUnmounted(() => {
    connectionCount--

    // 所有组件都卸载后断开连接
    if (connectionCount === 0) {
      disconnect()
    }
  })
  
  return {
    connected,
    data,
    error,
    latestHookProgress,
    connectionEvent,
    lastReceivedAt,
    connect,
    disconnect
  }
}
