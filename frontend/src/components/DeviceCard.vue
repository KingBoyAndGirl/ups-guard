<template>
  <div class="device-card">
    <!-- 右上角操作按钮 -->
    <div class="device-quick-actions">
      <div class="dropdown-container">
        <button
          class="btn btn-sm btn-primary dropdown-toggle"
          @click="showActionsMenu = !showActionsMenu"
          :disabled="testing"
          title="电源和设备操作"
        >
          ⚡ 操作 ▾
        </button>
        <div v-if="showActionsMenu" class="dropdown-menu" @click.stop>
          <!-- Power operations -->
          <div class="dropdown-section">
            <span class="dropdown-section-title">电源操作</span>
            <button
              v-if="device.online"
              class="dropdown-item"
              @click="handleActionClick('shutdown')"
            >
              🔌 关机
            </button>
            <button
              v-if="!device.online && device.config?.mac_address"
              class="dropdown-item"
              @click="handleActionClick('wake')"
            >
              ⏻ 开机 (WOL)
            </button>
            <button
              v-if="device.online && supportsReboot"
              class="dropdown-item"
              @click="handleActionClick('reboot')"
            >
              🔄 重启
            </button>
            <button
              v-if="device.online && supportsSleep"
              class="dropdown-item"
              @click="handleActionClick('sleep')"
            >
              😴 睡眠
            </button>
            <button
              v-if="device.online && supportsHibernate"
              class="dropdown-item"
              @click="handleActionClick('hibernate')"
            >
              💤 休眠
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <div class="device-header">
      <div class="device-icon">{{ icon }}</div>
      <div class="device-info">
        <h4 class="device-name">{{ device.name }}</h4>
        <span class="device-priority">P:{{ device.priority }}</span>
      </div>
    </div>
    
    <div class="device-status">
      <span class="status-indicator" :class="statusClass">
        {{ statusIcon }} {{ statusText }}
      </span>
    </div>
    
    <div v-if="device.error" class="device-error">
      <span class="error-icon">⚠️</span>
      <span class="error-message">{{ device.error }}</span>
    </div>
    
    <div class="device-meta">
      <span class="last-check">最后检测: {{ formatTime(device.last_check) }}</span>
    </div>
    
    <div class="device-actions">
      <button 
        class="btn btn-sm btn-secondary" 
        @click="$emit('test-connection', device)"
        :disabled="testing"
        title="测试设备连接状态（SSH/API）"
      >
        {{ testing ? '测试中...' : '测试连接' }}
      </button>
      
      <button
        v-if="device.config?.mac_address && device.online"
        class="btn btn-sm btn-info" 
        @click="$emit('test-wol', device)"
        :disabled="testing"
        title="测试网络唤醒（发送WOL魔术包）"
      >
        🧪 测试WOL
      </button>
      <button
        v-if="isSSHDevice"
        class="btn btn-sm btn-primary" 
        @click="$emit('view-logs', device)"
        :disabled="testing"
        title="查看日志"
      >
        📋 日志
      </button>
      <button
        class="btn btn-sm btn-secondary" 
        @click="$emit('edit-config', device)"
        :disabled="testing"
        title="查看或编辑配置"
      >
        ⚙️ 配置
      </button>
    </div>
    
    <!-- Hook 执行进度显示 -->
    <div v-if="executionStatus" class="execution-status" :class="`status-${executionStatus}`">
      <div class="status-bar">
        <div class="status-label">
          <span v-if="executionStatus === 'pending'">⏳ 等待中</span>
          <span v-else-if="executionStatus === 'executing'">🔄 执行中</span>
          <span v-else-if="executionStatus === 'success'">✅ 已完成</span>
          <span v-else-if="executionStatus === 'failed'">❌ 失败</span>
          <span v-else-if="executionStatus === 'skipped'">⏭️ 已跳过</span>
        </div>
        <div v-if="executionDuration > 0" class="status-duration">
          {{ executionDuration.toFixed(1) }}s
        </div>
      </div>
      <div v-if="executionError" class="execution-error">
        {{ executionError }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

// 时间常量（毫秒）
const ONE_MINUTE = 60000
const ONE_HOUR = 3600000
const ONE_DAY = 86400000

interface Device {
  name: string
  hook_id: string
  priority: number
  online: boolean
  last_check: string
  error: string | null
  config?: Record<string, any>
  supported_actions?: string[]
}

interface Props {
  device: Device
  testing?: boolean
  executionStatus?: string | null
  executionDuration?: number
  executionError?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  testing: false,
  executionStatus: null,
  executionDuration: 0,
  executionError: null
})

const emit = defineEmits<{
  (e: 'test-connection', device: Device): void
  (e: 'shutdown', device: Device): void
  (e: 'wake', device: Device): void
  (e: 'reboot', device: Device): void
  (e: 'sleep', device: Device): void
  (e: 'hibernate', device: Device): void
  (e: 'execute-command', device: Device): void
  (e: 'view-logs', device: Device): void
  (e: 'edit-config', device: Device): void
  (e: 'test-wol', device: Device): void
}>()

// Dropdown state
const showActionsMenu = ref(false)

const isSSHDevice = computed(() => {
  const sshTypes = ['ssh_shutdown', 'windows_shutdown', 'synology_shutdown', 'qnap_shutdown', 'lazycat_shutdown']
  return sshTypes.includes(props.device.hook_id)
})

const supportsAction = (action: string) => {
  if (!props.device.supported_actions) return false
  return props.device.supported_actions.includes(action)
}

const supportsReboot = computed(() => supportsAction('reboot'))
const supportsSleep = computed(() => supportsAction('sleep'))
const supportsHibernate = computed(() => supportsAction('hibernate'))

const handleActionClick = (action: string) => {
  showActionsMenu.value = false
  if (action === 'shutdown') emit('shutdown', props.device)
  else if (action === 'wake') emit('wake', props.device)
  else if (action === 'reboot') emit('reboot', props.device)
  else if (action === 'sleep') emit('sleep', props.device)
  else if (action === 'hibernate') emit('hibernate', props.device)
}

const icon = computed(() => {
  const hookId = props.device.hook_id
  const iconMap: Record<string, string> = {
    'ssh_shutdown': '🖥️',
    'windows_shutdown': '💻',
    'synology_shutdown': '📦',
    'qnap_shutdown': '📦',
    'http_api': '🌐',
    'custom_script': '📜',
    'lazycat_shutdown': '🐱'
  }
  return iconMap[hookId] || '📦'
})

const statusClass = computed(() => {
  if (props.executionStatus) {
    return `status-execution status-${props.executionStatus}`
  }
  return props.device.online ? 'status-online' : 'status-offline'
})

const statusIcon = computed(() => {
  if (props.executionStatus) {
    const iconMap: Record<string, string> = {
      'pending': '⏳',
      'executing': '🔄',
      'success': '✅',
      'failed': '❌',
      'skipped': '⏭️'
    }
    return iconMap[props.executionStatus] || '❓'
  }
  return props.device.online ? '🟢' : '🔴'
})

const statusText = computed(() => {
  if (props.executionStatus) {
    const textMap: Record<string, string> = {
      'pending': '等待中',
      'executing': '执行中',
      'success': '已关机',
      'failed': '失败',
      'skipped': '已跳过'
    }
    return textMap[props.executionStatus] || '未知'
  }
  return props.device.online ? '在线' : '离线'
})

const formatTime = (isoString: string): string => {
  try {
    // Parse naive datetime as local time to avoid UTC interpretation
    let date: Date
    if (!isoString.endsWith('Z') && !isoString.match(/[+-]\d{2}:\d{2}$/)) {
      // No timezone info - parse as local time
      const parts = isoString.split(/[-T:.]/)
      const year = parseInt(parts[0])
      const month = parseInt(parts[1]) - 1
      const day = parseInt(parts[2])
      const hour = parseInt(parts[3] || '0')
      const minute = parseInt(parts[4] || '0')
      const second = parseInt(parts[5] || '0')
      date = new Date(year, month, day, hour, minute, second)
    } else {
      date = new Date(isoString)
    }
    
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    
    if (diff < ONE_MINUTE) {
      return '刚刚'
    } else if (diff < ONE_HOUR) {
      return `${Math.floor(diff / ONE_MINUTE)} 分钟前`
    } else if (diff < ONE_DAY) {
      return `${Math.floor(diff / ONE_HOUR)} 小时前`
    } else {
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
  } catch (e) {
    return isoString
  }
}
</script>

<style scoped>
.device-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: var(--spacing-md);
  transition: all 0.2s;
  position: relative;
  overflow: hidden;
  /* 增强背景可见度 */
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
}

.device-card:hover {
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.06);
  transform: translateY(-2px);
  border-color: var(--primary);
}

/* 右上角快捷操作按钮 */
.device-quick-actions {
  position: absolute;
  top: var(--spacing-sm);
  right: var(--spacing-sm);
  z-index: 10;
}

.device-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.device-icon {
  font-size: 2rem;
  line-height: 1;
}

.device-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.device-name {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.device-priority {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-tertiary);
  background: var(--bg-secondary);
  border-radius: 9999px;
  width: fit-content;
}

.device-status {
  margin-bottom: var(--spacing-sm);
}

.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-weight: 500;
}

.status-online {
  background: #D1FAE5;
  color: #065F46;
}

.status-offline {
  background: #FEE2E2;
  color: #991B1B;
}

.status-execution {
  animation: pulse-status 1.5s ease-in-out infinite;
}

.status-pending {
  background: #FEF3C7;
  color: #92400E;
}

.status-executing {
  background: #DBEAFE;
  color: #1E40AF;
}

.status-success {
  background: #D1FAE5;
  color: #065F46;
}

.status-failed {
  background: #FEE2E2;
  color: #991B1B;
}

.status-skipped {
  background: #F3F4F6;
  color: #6B7280;
}

@keyframes pulse-status {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.device-error {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.5rem;
  margin-bottom: var(--spacing-sm);
  background: #FEF3C7;
  border-left: 3px solid #F59E0B;
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
}

.error-icon {
  font-size: 1rem;
  line-height: 1;
}

.error-message {
  color: #92400E;
  flex: 1;
  word-break: break-word;
}

.device-meta {
  margin-bottom: var(--spacing-md);
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.device-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.8125rem;
}

.btn-secondary {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-tertiary);
}

.btn-primary {
  background: var(--color-primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-warning {
  background: #F59E0B;
  color: white;
}

.btn-warning:hover:not(:disabled) {
  background: #D97706;
}

.btn-success {
  background: #10B981;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: #059669;
}

.execution-status {
  margin-top: var(--spacing-md);
  padding: var(--spacing-sm);
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
}

.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.875rem;
  font-weight: 500;
}

.status-duration {
  color: var(--text-tertiary);
  font-family: monospace;
}

.execution-error {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: #FEE2E2;
  border-radius: var(--radius-sm);
  font-size: 0.8125rem;
  color: #991B1B;
  word-break: break-word;
}

/* Dropdown styles */
.dropdown-container {
  position: relative;
  display: inline-block;
}

.dropdown-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  z-index: 1000;
  min-width: 180px;
  margin-top: 0.25rem;
  padding: 0.5rem 0;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  animation: dropdown-fade-in 0.15s ease-out;
}

@keyframes dropdown-fade-in {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dropdown-section {
  padding: 0.25rem 0;
}

.dropdown-section:not(:last-child) {
  border-bottom: 1px solid var(--border-color);
}

.dropdown-section-title {
  display: block;
  padding: 0.375rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.dropdown-item {
  display: block;
  width: 100%;
  padding: 0.5rem 0.75rem;
  text-align: left;
  font-size: 0.875rem;
  color: var(--text-primary);
  background: none;
  border: none;
  cursor: pointer;
  transition: background 0.15s;
}

.dropdown-item:hover {
  background: var(--bg-secondary);
}

.dropdown-item:active {
  background: var(--bg-tertiary);
}

.btn-info {
  background: #0EA5E9;
  color: white;
}

.btn-info:hover:not(:disabled) {
  background: #0284C7;
}
</style>
