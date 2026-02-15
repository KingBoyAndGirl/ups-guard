/**
 * UPS 状态类型定义
 */

export type UpsStatus = 'ONLINE' | 'ON_BATTERY' | 'LOW_BATTERY' | 'SHUTTING_DOWN' | 'POWER_OFF' | 'OFFLINE'

export interface UpsData {
  status: UpsStatus
  status_raw: string | null  // NUT 原始状态字符串，如 "OB DISCHRG LB"
  status_flags: string[] | null  // 原始 NUT 状态标志列表，如 ['OL', 'CHRG']
  battery_charge: number | null
  battery_runtime: number | null
  input_voltage: number | null
  output_voltage: number | null
  load_percent: number | null
  temperature: number | null
  ups_model: string | null
  ups_manufacturer: string | null
  last_update: string
  shutdown: ShutdownStatus
  // 新增字段
  ups_power_nominal: number | null
  ups_realpower: number | null
  battery_voltage: number | null
  battery_voltage_nominal: number | null
  battery_temperature: number | null
  // Phase 1 扩展字段
  input_frequency: number | null
  output_frequency: number | null
  output_current: number | null
  output_current_nominal: number | null
  ups_efficiency: number | null
  battery_type: string | null
  battery_date: string | null
  battery_mfr_date: string | null
  battery_packs: number | null
  battery_packs_bad: number | null
  // Phase 2 扩展字段
  input_voltage_min: number | null
  input_voltage_max: number | null
  input_transfer_low: number | null
  input_transfer_high: number | null
  ambient_temperature: number | null
  ambient_humidity: number | null
  ambient_temperature_alarm: string | null
  ambient_humidity_alarm: string | null
  // Phase 3 扩展字段
  ups_test_result: string | null
  ups_test_date: string | null
  ups_alarm: string | null
  ups_beeper_status: string | null
  // Phase 4 扩展字段
  ups_realpower_nominal: number | null
  input_voltage_nominal: number | null
  battery_charge_low: number | null
  battery_runtime_low: number | null
  input_transfer_reason: string | null
  input_sensitivity: string | null
  ups_delay_shutdown: number | null  // 关机延迟时间 (秒)
  ups_serial: string | null
  ups_mfr_date: string | null
  ups_productid: string | null
  ups_vendorid: string | null
  // 电池充电器状态 (NUT 标准)
  battery_charger_status: string | null
}

export interface ShutdownStatus {
  shutting_down: boolean
  power_lost_time?: string
  elapsed_seconds?: number
  remaining_seconds?: number
  in_final_countdown?: boolean
}

export interface Event {
  id: number
  event_type: string
  message: string
  timestamp: string
  metadata?: any
}

export interface Metric {
  timestamp: string
  battery_charge: number | null
  battery_runtime: number | null
  input_voltage: number | null
  output_voltage: number | null
  load_percent: number | null
  temperature: number | null
  // Phase 1 扩展字段
  input_frequency: number | null
  output_current: number | null
  ups_efficiency: number | null
  // Phase 2 扩展字段
  ambient_temperature: number | null
  ambient_humidity: number | null
}

export interface Config {
  shutdown_wait_minutes: number
  shutdown_battery_percent: number
  shutdown_final_wait_seconds: number
  estimated_runtime_threshold: number
  notify_channels: NotifyChannel[]
  notify_events: string[]
  notification_enabled: boolean
  sample_interval_seconds: number
  history_retention_days: number
  poll_interval_seconds: number
  cleanup_interval_hours: number
  pre_shutdown_hooks: PreShutdownHook[]
  test_mode: string  // 测试模式：production / dry_run / mock
  shutdown_method: string  // 关机方式：lzc_grpc / system_command / mock
  wol_on_power_restore: boolean  // 来电后自动 WOL
  wol_delay_seconds: number  // WOL 延迟秒数
  device_status_check_interval_seconds: number  // 设备状态检测间隔（秒），0 表示禁用
}

export interface NotifyChannel {
  id?: string  // 唯一标识符，由系统自动生成
  enabled: boolean
  plugin_id: string
  name: string
  config: Record<string, any>
}

export interface NotifyPlugin {
  id: string
  name: string
  description: string
  config_schema: ConfigField[]
}

export interface PreShutdownHook {
  enabled: boolean
  hook_id: string
  name: string
  priority: number
  timeout: number
  on_failure: 'continue' | 'abort'
  config: Record<string, any>
}

export interface HookPlugin {
  id: string
  name: string
  description: string
  config_schema: ConfigField[]
}

export interface ConfigField {
  key: string
  label: string
  type: 'text' | 'password' | 'number' | 'textarea' | 'select'
  required: boolean
  default?: any
  placeholder?: string
  description?: string
  options?: Array<{value: string, label: string}>
  rows?: number
}

export interface Device {
  index?: number
  name: string
  hook_id: string
  priority: number
  online: boolean
  last_check: string
  error: string | null
  config?: Record<string, any>
  supported_actions?: string[]
}

export interface HookExecutionState {
  status: string
  duration: number
  error: string | null
}

export interface CommandExecuteResponse {
  success: boolean
  stdout?: string
  stderr?: string
  exit_code?: number
  error?: string
}
