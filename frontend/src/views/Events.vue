<template>
  <div class="events">
    <!-- 事件统计（带时间范围筛选和来源过滤） -->
    <div class="card stats-card">
      <div class="stats-header">
        <h3 class="card-title-compact">事件统计</h3>
        <div class="filter-controls">
          <!-- 来源过滤器 -->
          <div class="source-filter">
            <label class="filter-label">事件来源：</label>
            <div class="source-buttons">
              <button 
                class="source-btn"
                :class="{ active: filterSource === '' }"
                @click="filterSource = ''"
              >
                全部
              </button>
              <button 
                class="source-btn source-btn-frontend"
                :class="{ active: filterSource === 'frontend' }"
                @click="filterSource = 'frontend'"
              >
                前端
              </button>
              <button 
                class="source-btn source-btn-backend"
                :class="{ active: filterSource === 'backend' }"
                @click="filterSource = 'backend'"
              >
                后端
              </button>
              <button 
                class="source-btn source-btn-nut"
                :class="{ active: filterSource === 'nut' }"
                @click="filterSource = 'nut'"
              >
                NUT
              </button>
              <button 
                class="source-btn source-btn-ups"
                :class="{ active: filterSource === 'ups' }"
                @click="filterSource = 'ups'"
              >
                UPS
              </button>
            </div>
          </div>
          <!-- 时间范围选择器 -->
          <div class="time-range-buttons">
            <button 
              v-for="range in timeRanges" 
              :key="range.value"
              class="time-range-btn"
              :class="{ active: filterDays === range.value }"
              @click="changeTimeRange(range.value)"
            >
              {{ range.label }}
            </button>
          </div>
        </div>
      </div>
      <div class="stats-grid">
        <div 
          class="stat-item" 
          v-for="(count, type) in eventStats" 
          :key="type"
          :class="{ active: filterType === type }"
          @click="toggleFilter(type as string)"
        >
          <div class="stat-count" :class="`stat-${type.toLowerCase()}`">{{ count }}</div>
          <div class="stat-label">{{ getEventTypeText(type as string) }}</div>
        </div>
      </div>
    </div>
    
    <!-- 事件列表 (紧凑表格) -->
    <div class="card events-list-card">
      <div v-if="filteredEvents.length === 0" class="empty-state-compact">
        暂无事件记录
      </div>
      
      <div v-else class="events-table">
        <div v-for="event in filteredEvents" :key="event.id" class="event-row">
          <span class="event-type" :class="`event-${event.event_type.toLowerCase()}`">
            {{ getEventTypeText(event.event_type) }}
          </span>
          <span :class="['source-badge', getSourceBadgeClass(getEventSource(event.event_type))]">
            {{ getSourceText(getEventSource(event.event_type)) }}
          </span>
          <span class="event-message">{{ event.message }}</span>
          <span class="event-time">{{ formatDateTime(event.timestamp) }}</span>
          <button class="btn-view-detail" @click="showEventDetail(event)" title="查看事件详情">
            <span class="btn-icon">📄</span>
            <span class="btn-text">事件日志</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 事件详情弹窗 -->
    <div v-if="showDetailDialog" class="modal-overlay" @click.self="closeDetailDialog">
      <div class="modal-dialog modal-event-detail">
        <div class="modal-header">
          <h3>📋 事件详情</h3>
          <button class="btn-close" @click="closeDetailDialog">✕</button>
        </div>

        <div v-if="currentEvent" class="event-detail-content">
          <!-- 事件类型和时间 -->
          <div class="event-detail-header">
            <span class="event-type-badge" :class="`event-${currentEvent.event_type.toLowerCase()}`">
              {{ getEventTypeIcon(currentEvent.event_type) }} {{ getEventTypeText(currentEvent.event_type) }}
            </span>
            <span class="event-timestamp">{{ formatDateTime(currentEvent.timestamp) }}</span>
          </div>

          <!-- 事件消息 -->
          <div class="event-detail-section">
            <h4>事件描述</h4>
            <p class="event-message-detail">{{ currentEvent.message }}</p>
          </div>

          <!-- 元数据详情 -->
          <div v-if="currentEvent.metadata && Object.keys(parsedMetadata).length > 0" class="event-detail-section">
            <h4>详细信息</h4>
            <div class="event-metadata">
              <div v-for="(value, key) in parsedMetadata" :key="String(key)" class="metadata-item">
                <span class="metadata-key">{{ formatMetadataKey(String(key)) }}</span>
                <span class="metadata-value">{{ formatMetadataValue(value) }}</span>
              </div>
            </div>
          </div>

          <!-- NUT 容器日志 -->
          <div v-if="isNutRelatedEvent(currentEvent.event_type)" class="event-detail-section logs-section">
            <div class="logs-header">
              <h4>🐳 NUT 容器日志</h4>
              <div class="logs-header-right">
                <span v-if="logsFromPersisted" class="logs-source-badge persisted">📌 事件发生时的日志</span>
                <span v-else-if="nutLogs && !logsLoading" class="logs-source-badge realtime">⚡ 当前实时日志</span>
                <button v-if="!logsLoading && !logsFromPersisted" class="btn-refresh" @click="fetchNutLogs" title="刷新日志">
                  🔄
                </button>
              </div>
            </div>
            <div class="logs-content">
              <div v-if="logsLoading" class="logs-loading">
                <div class="spinner"></div>
                <span>正在获取日志...</span>
              </div>
              <pre v-else-if="nutLogs" class="logs-text">{{ nutLogs }}</pre>
              <div v-else class="logs-empty">暂无日志</div>
            </div>
          </div>

          <!-- 事件 ID -->
          <div class="event-detail-footer">
            <span class="event-id">事件 ID: #{{ currentEvent.id }}</span>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn btn-secondary" @click="closeDetailDialog">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import type { Event } from '@/types/ups'

const events = ref<Event[]>([])
const filterDays = ref(7)
const filterType = ref('')
const filterSource = ref('') // 事件来源过滤器

// 事件详情相关状态
const showDetailDialog = ref(false)
const currentEvent = ref<Event | null>(null)
const nutLogs = ref('')
const logsLoading = ref(false)
const logsFromPersisted = ref(false) // 标记日志是否来自持久化存储

const timeRanges = [
  { value: 1, label: '最近1天' },
  { value: 7, label: '最近7天' },
  { value: 30, label: '最近30天' }
]

const fetchEvents = async () => {
  try {
    const response = await axios.get(`/api/history/events?days=${filterDays.value}`)
    events.value = response.data.events
  } catch (error) {
    console.error('Failed to fetch events:', error)
  }
}

const changeTimeRange = (days: number) => {
  filterDays.value = days
  fetchEvents()
}

const toggleFilter = (type: string) => {
  // If clicking the same type, toggle off (show all)
  if (filterType.value === type) {
    filterType.value = ''
  } else {
    filterType.value = type
  }
}

const filteredEvents = computed(() => {
  let filtered = events.value
  
  // 按来源过滤
  if (filterSource.value) {
    filtered = filtered.filter(e => getEventSource(e.event_type) === filterSource.value)
  }
  
  // 按类型过滤
  if (filterType.value) {
    filtered = filtered.filter(e => e.event_type === filterType.value)
  }
  
  return filtered
})

const eventStats = computed(() => {
  const stats: Record<string, number> = {}
  events.value.forEach(event => {
    stats[event.event_type] = (stats[event.event_type] || 0) + 1
  })
  return stats
})

const formatDateTime = (isoString: string): string => {
  // Backend sends naive datetime (no timezone info)
  // Parse as local time to avoid UTC interpretation
  if (!isoString.endsWith('Z') && !isoString.match(/[+-]\d{2}:\d{2}$/)) {
    // No timezone info - treat as local time
    const parts = isoString.split(/[-T:.]/)
    const year = parseInt(parts[0])
    const month = parseInt(parts[1]) - 1 // JavaScript months are 0-indexed
    const day = parseInt(parts[2])
    const hour = parseInt(parts[3] || '0')
    const minute = parseInt(parts[4] || '0')
    const second = parseInt(parts[5] || '0')
    
    const date = new Date(year, month, day, hour, minute, second)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    })
  }
  
  // Has timezone info - use as-is
  return new Date(isoString).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

const getEventTypeText = (type: string): string => {
  const map: Record<string, string> = {
    'POWER_LOST': '断电',
    'POWER_RESTORED': '恢复供电',
    'LOW_BATTERY': '低电量',
    'SHUTDOWN': '关机',
    'STARTUP': '启动',
    'SHUTDOWN_CANCELLED': '取消关机',
    // 设备操作事件
    'DEVICE_SHUTDOWN': '设备关机',
    'DEVICE_WAKE': '设备唤醒',
    'DEVICE_REBOOT': '设备重启',
    'DEVICE_SLEEP': '设备睡眠',
    'DEVICE_HIBERNATE': '设备休眠',
    'DEVICE_TEST_CONNECTION': '测试连接',
    // NUT 连接事件
    'NUT_DISCONNECTED': 'NUT断开',
    'NUT_RECONNECTED': 'NUT重连',
    // 细化的诊断事件
    'BACKEND_ERROR': '后端异常',
    'BACKEND_RESTORED': '后端恢复',
    'NUT_SERVER_DISCONNECTED': 'NUT服务器断开',
    'NUT_SERVER_CONNECTED': 'NUT服务器连接',
    'UPS_DRIVER_ERROR': '驱动异常',
    'UPS_DRIVER_DUMMY': '驱动dummy',
    'UPS_DRIVER_CONNECTED': '驱动连接',
    // UPS 参数配置事件
    'UPS_PARAM_CHANGED': '参数修改',
    // 电池维护事件
    'BATTERY_REPLACED': '电池更换',
    // 前端事件
    'FRONTEND_ERROR': '前端错误',
    'FRONTEND_USER_ACTION': '用户操作',
    'FRONTEND_NETWORK_ERROR': '网络错误',
    // 兼容旧事件
    'CONNECTION_ISSUE': '连接问题',
    'CONNECTION_RESTORED': '连接恢复'
  }
  return map[type] || type
}

// 获取事件类型对应的图标
const getEventTypeIcon = (type: string): string => {
  const iconMap: Record<string, string> = {
    'POWER_LOST': '⚡',
    'POWER_RESTORED': '✅',
    'LOW_BATTERY': '🔋',
    'SHUTDOWN': '🔴',
    'STARTUP': '🟢',
    'SHUTDOWN_CANCELLED': '⏹️',
    // 设备操作事件
    'DEVICE_SHUTDOWN': '🔴',
    'DEVICE_WAKE': '⏰',
    'DEVICE_REBOOT': '🔄',
    'DEVICE_SLEEP': '😴',
    'DEVICE_HIBERNATE': '🐻',
    'DEVICE_TEST_CONNECTION': '🔍',
    // NUT 连接事件
    'NUT_DISCONNECTED': '🔌',
    'NUT_RECONNECTED': '🔗',
    // 诊断事件
    'BACKEND_ERROR': '⚠️',
    'BACKEND_RESTORED': '✅',
    'NUT_SERVER_DISCONNECTED': '🔌',
    'NUT_SERVER_CONNECTED': '🔗',
    'UPS_DRIVER_ERROR': '⚠️',
    'UPS_DRIVER_DUMMY': '🧪',
    'UPS_DRIVER_CONNECTED': '✅',
    // UPS 参数配置事件
    'UPS_PARAM_CHANGED': '🔧',
    // 电池维护事件
    'BATTERY_REPLACED': '🔋',
    // 前端事件
    'FRONTEND_ERROR': '❌',
    'FRONTEND_USER_ACTION': '👤',
    'FRONTEND_NETWORK_ERROR': '🌐',
    'CONNECTION_ISSUE': '⚠️',
    'CONNECTION_RESTORED': '✅'
  }
  return iconMap[type] || '📋'
}

// 获取事件来源
const getEventSource = (type: string): string => {
  if (type.startsWith('FRONTEND_')) {
    return 'frontend'
  } else if (type.startsWith('NUT_') || type.startsWith('UPS_DRIVER_')) {
    return 'nut'
  } else if (type.startsWith('POWER_') || type.startsWith('LOW_BATTERY') || type.startsWith('UPS_PARAM_') || type.startsWith('BATTERY_')) {
    return 'ups'
  } else {
    return 'backend'
  }
}

// 获取来源标签样式类
const getSourceBadgeClass = (source: string): string => {
  const classMap: Record<string, string> = {
    'frontend': 'source-badge-frontend',
    'backend': 'source-badge-backend',
    'nut': 'source-badge-nut',
    'ups': 'source-badge-ups'
  }
  return classMap[source] || 'source-badge-default'
}

// 获取来源显示文本
const getSourceText = (source: string): string => {
  const textMap: Record<string, string> = {
    'frontend': '前端',
    'backend': '后端',
    'nut': 'NUT',
    'ups': 'UPS'
  }
  return textMap[source] || source
}

// 判断是否是 NUT 相关事件（需要显示容器日志）
const isNutRelatedEvent = (type: string): boolean => {
  const nutEvents = [
    'NUT_SERVER_DISCONNECTED',
    'NUT_SERVER_CONNECTED',
    'UPS_DRIVER_ERROR',
    'UPS_DRIVER_DUMMY',
    'UPS_DRIVER_CONNECTED',
    'CONNECTION_ISSUE',
    'CONNECTION_RESTORED'
  ]
  return nutEvents.includes(type)
}

// 显示事件详情
const showEventDetail = async (event: Event) => {
  currentEvent.value = event
  showDetailDialog.value = true
  nutLogs.value = ''
  logsFromPersisted.value = false

  // 如果是 NUT 相关事件，尝试获取日志
  if (isNutRelatedEvent(event.event_type)) {
    // 先尝试从事件的 metadata 中获取持久化的日志
    const metadata = typeof event.metadata === 'string'
      ? JSON.parse(event.metadata)
      : event.metadata

    if (metadata?.nut_container_logs && Array.isArray(metadata.nut_container_logs)) {
      // 使用事件发生时保存的日志
      nutLogs.value = metadata.nut_container_logs.join('\n')
      logsFromPersisted.value = true
    } else {
      // 旧事件没有持久化日志，获取当前日志（仅供参考）
      await fetchNutLogs()
    }
  }
}

// 关闭详情弹窗
const closeDetailDialog = () => {
  showDetailDialog.value = false
  currentEvent.value = null
  nutLogs.value = ''
}

// 获取 NUT 容器日志
const fetchNutLogs = async () => {
  logsLoading.value = true
  try {
    const response = await axios.get('/api/diagnostics/connection-status')
    if (response.data.nut_container_logs) {
      nutLogs.value = response.data.nut_container_logs.join('\n')
    }
  } catch (error) {
    console.error('Failed to fetch NUT logs:', error)
    nutLogs.value = '获取日志失败'
  } finally {
    logsLoading.value = false
  }
}

// 解析事件元数据（排除 nut_container_logs，它会单独显示）
const parsedMetadata = computed(() => {
  if (!currentEvent.value?.metadata) return {}
  try {
    let metadata: Record<string, any>
    if (typeof currentEvent.value.metadata === 'string') {
      metadata = JSON.parse(currentEvent.value.metadata)
    } else {
      metadata = currentEvent.value.metadata
    }
    // 排除 nut_container_logs，它会在日志区域单独显示
    const { nut_container_logs, ...rest } = metadata
    return rest
  } catch {
    return {}
  }
})

// 格式化元数据键名
const formatMetadataKey = (key: string): string => {
  const keyMap: Record<string, string> = {
    'battery_charge': '电池电量',
    'battery_runtime': '预计续航',
    'input_voltage': '输入电压',
    'output_voltage': '输出电压',
    'load_percent': '负载百分比',
    'temperature': '温度',
    'ups_name': 'UPS 名称',
    'ups_status': 'UPS 状态',
    'trigger_reason': '触发原因',
    'trigger': '触发方式',
    'wait_minutes': '等待时间',
    'device_name': '设备名称',
    'device_type': '设备类型',
    'hook_result': '执行结果',
    'error_message': '错误信息',
    'nut_server': 'NUT 服务器',
    'driver': '驱动',
    'port': '端口',
    // 状态变化相关
    'old_status': '变化前状态',
    'new_status': '变化后状态',
    // 诊断相关
    'component': '组件',
    'status': '状态',
    'backend_status': '后端状态',
    'nut_server_status': 'NUT 服务器状态',
    'ups_driver_status': 'UPS 驱动状态',
    'overall_status': '整体状态'
  }
  return keyMap[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

// 格式化元数据值
const formatMetadataValue = (value: any): string => {
  if (value === null || value === undefined) return 'N/A'
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (typeof value === 'number') return String(value)
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}

onMounted(() => {
  fetchEvents()
})
</script>

<style scoped>
.events {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--ups-card-gap);
}

.events h2 {
  margin-bottom: var(--ups-card-gap);
}

/* 统计卡片 */
.stats-card {
  margin-bottom: var(--ups-card-gap);
}

.stats-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.card-title-compact {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
  color: var(--text-primary);
}

.time-range-buttons {
  display: flex;
  gap: 0.5rem;
}

.time-range-btn {
  padding: 0.4rem 0.8rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.time-range-btn:hover {
  background: var(--bg-hover);
  border-color: var(--color-primary);
}

.time-range-btn.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: var(--spacing-sm);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  cursor: pointer;
  padding: 0.75rem 0.5rem;
  border-radius: var(--radius-sm);
  transition: all 0.2s;
  border: 2px solid transparent;
}

.stat-item:hover {
  background: var(--bg-hover);
  border-color: var(--border-color);
}

.stat-item.active {
  background: var(--bg-hover);
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.stat-count {
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 1;
}

.stat-count.stat-power_lost {
  color: #F59E0B;
}

.stat-count.stat-power_restored {
  color: #10B981;
}

.stat-count.stat-low_battery,
.stat-count.stat-shutdown {
  color: #EF4444;
}

.stat-count.stat-startup,
.stat-count.stat-shutdown_cancelled {
  color: #3B82F6;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

/* 事件列表卡片 */
.events-list-card {
  display: flex;
  flex-direction: column;
}

.events-table {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.event-row {
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  gap: var(--spacing-sm);
  padding: 0.5rem var(--spacing-sm);
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  align-items: center;
}

.btn-view-detail {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-tertiary);
  cursor: pointer;
  font-size: 0.75rem;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.btn-view-detail:hover {
  background: var(--bg-hover);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.btn-view-detail .btn-icon {
  font-size: 0.8125rem;
}

.btn-view-detail .btn-text {
  font-weight: 500;
}

.event-type {
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.6875rem;
  font-weight: 500;
}

.event-power_lost {
  background: #FEF3C7;
  color: #92400E;
}

.event-power_restored {
  background: #D1FAE5;
  color: #065F46;
}

.event-low_battery,
.event-shutdown {
  background: #FEE2E2;
  color: #991B1B;
}

.event-startup,
.event-shutdown_cancelled {
  background: #DBEAFE;
  color: #1E40AF;
}

.event-connection_issue {
  background: #FEE2E2;
  color: #991B1B;
}

.event-connection_restored {
  background: #D1FAE5;
  color: #065F46;
}

/* 后端服务状态 */
.event-backend_error {
  background: #FEE2E2;
  color: #991B1B;
}

.event-backend_restored {
  background: #D1FAE5;
  color: #065F46;
}

/* NUT 服务器状态 */
.event-nut_server_disconnected {
  background: #FEF3C7;
  color: #92400E;
}

.event-nut_server_connected {
  background: #D1FAE5;
  color: #065F46;
}

/* UPS 驱动状态 */
.event-ups_driver_error {
  background: #FEE2E2;
  color: #991B1B;
}

.event-ups_driver_dummy {
  background: #FEF3C7;
  color: #92400E;
}

.event-ups_driver_connected {
  background: #D1FAE5;
  color: #065F46;
}

.event-message {
  color: var(--text-primary);
  font-size: 0.8125rem;
}

.event-time {
  color: var(--text-tertiary);
  font-size: 0.75rem;
}

.empty-state-compact {
  text-align: center;
  padding: var(--spacing-md);
  color: var(--text-tertiary);
}

/* 弹窗样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-dialog {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-event-detail {
  width: 90%;
  max-width: 600px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
  margin: 0;
  font-size: 1.125rem;
  color: var(--text-primary);
}

.btn-close {
  padding: 4px 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 1.25rem;
  color: var(--text-tertiary);
  border-radius: var(--radius-sm);
  transition: all 0.2s;
}

.btn-close:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.event-detail-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.event-detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--bg-tertiary);
  border-radius: 8px;
  margin-bottom: 16px;
}

.event-type-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: 600;
}

.event-type-badge.event-power_lost {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.event-type-badge.event-power_restored {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.event-type-badge.event-low_battery,
.event-type-badge.event-shutdown {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.event-type-badge.event-startup,
.event-type-badge.event-shutdown_cancelled {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.event-type-badge.event-nut_server_disconnected,
.event-type-badge.event-ups_driver_error,
.event-type-badge.event-ups_driver_dummy,
.event-type-badge.event-connection_issue {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.event-type-badge.event-nut_server_connected,
.event-type-badge.event-ups_driver_connected,
.event-type-badge.event-connection_restored {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.event-type-badge.event-backend_error {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.event-type-badge.event-backend_restored {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.event-timestamp {
  font-size: 0.8125rem;
  color: var(--text-tertiary);
}

.event-detail-section {
  margin-bottom: 16px;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.event-detail-section h4 {
  margin: 0 0 12px 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.event-message-detail {
  margin: 0;
  font-size: 0.9375rem;
  color: var(--text-primary);
  line-height: 1.6;
}

.event-metadata {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metadata-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
}

.metadata-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.metadata-key {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  font-weight: 500;
  min-width: 100px;
}

.metadata-value {
  font-size: 0.875rem;
  color: var(--text-primary);
  text-align: right;
  word-break: break-word;
  max-width: 300px;
}

/* 日志部分样式 */
.logs-section {
  padding: 0;
  overflow: hidden;
}

.logs-section .logs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.logs-section .logs-header h4 {
  margin: 0;
}

.logs-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.logs-source-badge {
  font-size: 0.6875rem;
  padding: 3px 8px;
  border-radius: 12px;
  font-weight: 500;
}

.logs-source-badge.persisted {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.logs-source-badge.realtime {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.btn-refresh {
  padding: 4px 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 0.875rem;
  border-radius: var(--radius-sm);
  transition: all 0.2s;
}

.btn-refresh:hover {
  background: var(--bg-hover);
}

.logs-content {
  max-height: 250px;
  overflow-y: auto;
  background: #1e1e2e;
  padding: 12px 16px;
}

.logs-text {
  margin: 0;
  font-family: 'Courier New', 'Consolas', monospace;
  font-size: 0.75rem;
  line-height: 1.5;
  color: #e0e0e0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.logs-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
  color: #9ca3af;
}

.logs-loading .spinner {
  width: 24px;
  height: 24px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 8px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.logs-empty {
  text-align: center;
  color: #6b7280;
  padding: 24px;
}

.event-detail-footer {
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
  margin-top: 8px;
}

.event-id {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid var(--border-color);
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-secondary:hover {
  background: var(--bg-hover);
}

/* 响应式: 移动端退回单列 */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* 事件来源过滤器样式 */
.filter-controls {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.source-filter {
  display: flex;
  align-items: center;
  gap: 10px;
}

.filter-label {
  font-size: 0.875rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.source-buttons {
  display: flex;
  gap: 8px;
}

.source-btn {
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
  color: var(--text-primary);
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.source-btn:hover {
  background: var(--bg-hover);
}

.source-btn.active {
  border-color: var(--primary-color);
  background: var(--primary-color);
  color: white;
}

.source-btn-frontend.active {
  background: #3b82f6;
  border-color: #3b82f6;
}

.source-btn-backend.active {
  background: #8b5cf6;
  border-color: #8b5cf6;
}

.source-btn-nut.active {
  background: #10b981;
  border-color: #10b981;
}

.source-btn-ups.active {
  background: #f59e0b;
  border-color: #f59e0b;
}

/* 事件来源标签样式 */
.source-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.source-badge-frontend {
  background: #dbeafe;
  color: #1e40af;
}

.source-badge-backend {
  background: #ede9fe;
  color: #6b21a8;
}

.source-badge-nut {
  background: #d1fae5;
  color: #065f46;
}

.source-badge-ups {
  background: #fef3c7;
  color: #92400e;
}

.source-badge-default {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}
</style>
