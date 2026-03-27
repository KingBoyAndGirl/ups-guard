<template>
  <div class="history">
    <!-- 双列布局: 历史图表 | 数据导出面板 -->
    <div class="history-main-row">
      <!-- 左侧: 历史数据图表 -->
      <div class="card chart-section">
        <div class="chart-header">
          <h3 class="card-title">历史趋势</h3>
          <div class="time-range-selector">
            <button
              v-for="range in timeRanges"
              :key="range.value"
              class="time-range-btn"
              :class="{ active: selectedTimeRange === range.value }"
              @click="changeTimeRange(range.value)"
            >
              {{ range.label }}
            </button>
          </div>
        </div>
        <div v-if="loadingMetrics" class="loading-state">
          <span>加载中...</span>
        </div>
        <template v-else-if="metrics.length > 0">
          <PowerChart
            title=""
            :metrics="metrics"
          />
          <DailyEnergyChart
            :metrics="metrics"
            :upsNominalPower="undefined"
          />
        </template>
        <p v-else class="empty-state">暂无历史数据</p>
      </div>

      <!-- 右侧: 数据导出面板 -->
      <div class="card export-section">
        <h3 class="card-title">数据导出</h3>
        
        <div class="export-form">
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">导出格式</label>
              <select v-model="exportFormat" class="form-control">
                <option value="csv">CSV</option>
                <option value="xlsx">Excel (XLSX)</option>
              </select>
            </div>
            
            <div class="form-group">
              <label class="form-label">数据类型</label>
              <select v-model="exportType" class="form-control">
                <option value="all">全部数据</option>
                <option value="events">仅事件</option>
                <option value="metrics">仅指标</option>
              </select>
            </div>
          </div>

          <div class="form-group full-width">
            <label class="form-label">时间范围</label>
            <DateRangePicker
              v-model:startDate="startDate"
              v-model:endDate="endDate"
              placeholder="选择时间范围"
            />
          </div>

          <div class="form-actions">
            <button
              class="btn btn-primary"
              @click="exportData"
              :disabled="exporting || !startDate || !endDate"
            >
              {{ exporting ? '导出中...' : '📥 导出数据' }}
            </button>
            <small class="help-text">选择日期后自动查询，支持导出最近90天的数据</small>
          </div>

          <!-- 导出结果提示 -->
          <div v-if="exportResult" class="export-result" :class="{ 'success': exportResult.success, 'error': !exportResult.success }">
            {{ exportResult.message }}
          </div>
        </div>
      </div>
    </div>

    <!-- 电池测试报告历史 -->
    <div class="card test-reports-section">
      <div class="section-header">
        <h3 class="card-title">🔋 电池测试报告</h3>
        <div class="section-actions">
          <button
            class="btn btn-sm btn-primary"
            @click="exportAllReports"
            :disabled="exportingReports || testReports.length === 0"
            title="导出当前筛选条件下的所有报告"
          >
            {{ exportingReports ? '导出中...' : '📥 导出报告' }}
          </button>
          <button class="btn btn-sm btn-secondary" @click="fetchTestReports" :disabled="loadingReports">
            {{ loadingReports ? '加载中...' : '🔄 刷新' }}
          </button>
        </div>
      </div>

      <!-- 筛选区域 -->
      <div class="report-filters">
        <div class="filter-group">
          <label class="filter-label">测试类型</label>
          <select v-model="reportFilterType" class="filter-control" @change="fetchTestReports">
            <option value="">全部类型</option>
            <option value="quick">⚡ 快速测试</option>
            <option value="deep">🔋 深度测试</option>
          </select>
        </div>

        <div class="filter-group">
          <label class="filter-label">测试结果</label>
          <select v-model="reportFilterResult" class="filter-control" @change="fetchTestReports">
            <option value="">全部结果</option>
            <option value="passed">✅ 通过</option>
            <option value="warning">⚠️ 警告</option>
            <option value="failed">❌ 失败</option>
            <option value="in_progress">🔄 进行中</option>
            <option value="cancelled">🚫 已取消</option>
          </select>
        </div>

        <div class="filter-group filter-date-range">
          <label class="filter-label">时间范围</label>
          <DateRangePicker
            v-model:startDate="reportFilterStartDate"
            v-model:endDate="reportFilterEndDate"
            placeholder="选择时间范围"
          />
        </div>

        <button
          v-if="hasActiveFilters"
          class="btn btn-sm btn-link"
          @click="clearReportFilters"
        >
          清除筛选
        </button>
      </div>

      <div v-if="loadingReports" class="loading-state">
        <span>加载中...</span>
      </div>

      <div v-else-if="testReports.length === 0" class="empty-state">
        <p v-if="hasActiveFilters">没有符合筛选条件的报告</p>
        <p v-else>暂无电池测试报告</p>
        <small v-if="!hasActiveFilters">在仪表盘执行「快速测试」或「深度测试」后，报告将显示在这里</small>
      </div>

      <div v-else class="test-reports-grid">
        <div
          v-for="report in testReports"
          :key="report.id"
          class="test-report-card"
          :class="`result-${report.result}`"
          @click="showReportDetail(report)"
        >
          <div class="report-header">
            <span class="test-type-badge">
              {{ report.test_type === 'quick' ? '⚡' : '🔋' }} {{ report.test_type_label }}
            </span>
            <span class="result-badge" :class="`result-${report.result}`">
              {{ getResultIcon(report.result) }} {{ getResultText(report.result) }}
            </span>
          </div>

          <div class="report-time">
            {{ formatDateTime(report.started_at) }}
          </div>

          <div class="report-stats">
            <div class="stat-item" v-if="report.duration_seconds">
              <span class="stat-label">时长</span>
              <span class="stat-value">{{ formatDuration(report.duration_seconds) }}</span>
            </div>
            <div class="stat-item" v-if="report.charge_change !== null">
              <span class="stat-label">电量变化</span>
              <span class="stat-value" :class="report.charge_change < 0 ? 'negative' : 'positive'">
                {{ report.charge_change > 0 ? '+' : '' }}{{ report.charge_change?.toFixed(1) }}%
              </span>
            </div>
            <div class="stat-item" v-if="report.sample_count > 0">
              <span class="stat-label">采样点</span>
              <span class="stat-value">{{ report.sample_count }}</span>
            </div>
          </div>

          <div class="report-footer">
            <span class="ups-model">{{ report.ups_info?.model || 'N/A' }}</span>
            <span class="view-detail">查看详情 →</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 报告详情弹窗 -->
    <div v-if="showReportDialog" class="modal-overlay" @click.self="showReportDialog = false">
      <div class="modal-dialog modal-report-detail">
        <div class="modal-header">
          <h3>📋 测试报告详情</h3>
          <button class="btn-close" @click="showReportDialog = false">✕</button>
        </div>

        <div v-if="currentReport" class="report-detail-content">
          <!-- 测试概要 -->
          <div class="detail-section summary-section">
            <div class="test-type-large">
              {{ currentReport.test_type === 'quick' ? '⚡' : '🔋' }} {{ currentReport.test_type_label }}
            </div>
            <div class="result-large" :class="`result-${currentReport.result}`">
              {{ getResultIcon(currentReport.result) }} {{ currentReport.result_text || getResultText(currentReport.result) }}
            </div>
          </div>

          <!-- 时间信息 -->
          <div class="detail-section">
            <h4>⏱️ 时间信息</h4>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="label">开始时间</span>
                <span class="value">{{ formatDateTime(currentReport.started_at) }}</span>
              </div>
              <div class="detail-item" v-if="currentReport.completed_at">
                <span class="label">结束时间</span>
                <span class="value">{{ formatDateTime(currentReport.completed_at) }}</span>
              </div>
              <div class="detail-item" v-if="currentReport.duration_seconds">
                <span class="label">测试时长</span>
                <span class="value">{{ formatDuration(currentReport.duration_seconds) }}</span>
              </div>
            </div>
          </div>

          <!-- 电池数据对比 -->
          <div class="detail-section">
            <h4>🔋 电池数据对比</h4>
            <div class="comparison-table">
              <div class="comparison-header">
                <span></span>
                <span>测试前</span>
                <span>测试后</span>
                <span>变化</span>
              </div>
              <div class="comparison-row">
                <span class="label">电量</span>
                <span>{{ currentReport.start_data?.battery_charge?.toFixed(1) ?? 'N/A' }}%</span>
                <span>{{ currentReport.end_data?.battery_charge?.toFixed(1) ?? 'N/A' }}%</span>
                <span :class="getChangeClass(currentReport.charge_change)">
                  {{ currentReport.charge_change !== null ? (currentReport.charge_change > 0 ? '+' : '') + currentReport.charge_change.toFixed(1) + '%' : 'N/A' }}
                </span>
              </div>
              <div class="comparison-row">
                <span class="label">电压</span>
                <span>{{ currentReport.start_data?.battery_voltage?.toFixed(2) ?? 'N/A' }}V</span>
                <span>{{ currentReport.end_data?.battery_voltage?.toFixed(2) ?? 'N/A' }}V</span>
                <span :class="getChangeClass(getVoltageChange(currentReport))">
                  {{ formatVoltageChange(currentReport) }}
                </span>
              </div>
              <div class="comparison-row">
                <span class="label">预计续航</span>
                <span>{{ formatRuntime(currentReport.start_data?.battery_runtime) }}</span>
                <span>{{ formatRuntime(currentReport.end_data?.battery_runtime) }}</span>
                <span>-</span>
              </div>
            </div>
          </div>

          <!-- 采样数据图表 -->
          <div class="detail-section" v-if="currentReport.samples && currentReport.samples.length > 1">
            <h4>📊 电量变化曲线 ({{ currentReport.sample_count }} 个采样点)</h4>
            <div class="samples-chart">
              <div class="chart-bars">
                <div
                  v-for="(sample, index) in currentReport.samples"
                  :key="index"
                  class="chart-bar"
                  :style="{ height: `${sample.battery_charge || 0}%` }"
                  :title="`${formatDateTime(sample.timestamp)}: ${sample.battery_charge?.toFixed(1)}%`"
                ></div>
              </div>
              <div class="chart-labels">
                <span>开始</span>
                <span>结束</span>
              </div>
            </div>
          </div>

          <!-- UPS 信息 -->
          <div class="detail-section">
            <h4>🔌 UPS 信息</h4>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="label">制造商</span>
                <span class="value">{{ currentReport.ups_info?.manufacturer || 'N/A' }}</span>
              </div>
              <div class="detail-item">
                <span class="label">型号</span>
                <span class="value">{{ currentReport.ups_info?.model || 'N/A' }}</span>
              </div>
              <div class="detail-item">
                <span class="label">序列号</span>
                <span class="value">{{ currentReport.ups_info?.serial || 'N/A' }}</span>
              </div>
            </div>
          </div>

          <!-- 报告 ID -->
          <div class="detail-footer">
            <span>报告 ID: #{{ currentReport.id }}</span>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn btn-primary" @click="downloadReport(currentReport)">
            📥 下载报告
          </button>
          <button class="btn btn-secondary" @click="showReportDialog = false">关闭</button>
        </div>
      </div>
    </div>

    <!-- 监控统计卡片 -->
    <div class="card monitoring-stats-section">
      <div class="section-header">
        <h3 class="card-title">📊 监控统计</h3>
        <div class="section-actions">
          <button class="btn btn-sm btn-secondary" @click="fetchMonitoringStats" :disabled="loadingMonitoringStats">
            {{ loadingMonitoringStats ? '加载中...' : '🔄 刷新' }}
          </button>
        </div>
      </div>

      <!-- 日期范围选择器 -->
      <div class="date-range-selector">
        <button
          v-for="range in monitoringRanges"
          :key="range.value"
          class="range-btn"
          :class="{ active: selectedMonitoringRange === range.value }"
          @click="changeMonitoringRange(range.value)"
        >
          {{ range.label }}
        </button>
      </div>

      <!-- 实时统计 -->
      <div v-if="currentMonitoringStats" class="monitoring-current">
        <h4 class="subsection-title">📈 实时统计</h4>
        <div class="stats-grid-monitoring">
          <div class="stat-box">
            <div class="stat-label">今日通信次数</div>
            <div class="stat-value">{{ currentMonitoringStats.today_communications || 0 }}</div>
          </div>
          <div class="stat-box">
            <div class="stat-label">平均响应时间</div>
            <div class="stat-value">
              {{ currentMonitoringStats.response_time?.avg_ms?.toFixed(1) || 'N/A' }} ms
            </div>
          </div>
          <div class="stat-box">
            <div class="stat-label">当前监控模式</div>
            <div class="stat-value mode-badge" :class="`mode-${currentMonitoringStats.config_mode || 'unknown'}`">
              {{ currentMonitoringStats.current_mode || 'Unknown' }}
            </div>
          </div>
          <div class="stat-box">
            <div class="stat-label">事件驱动状态</div>
            <div class="stat-value">
              <span :class="currentMonitoringStats.event_mode_active ? 'status-active' : 'status-inactive'">
                {{ currentMonitoringStats.event_mode_active ? '✅ 活跃' : '⚠️ 未激活' }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 历史统计表格 -->
      <div v-if="monitoringHistory.length > 0" class="monitoring-history">
        <h4 class="subsection-title">📅 历史统计</h4>
        <div class="monitoring-table">
          <table>
            <thead>
              <tr>
                <th>日期</th>
                <th>监控模式</th>
                <th>事件驱动</th>
                <th>通信次数</th>
                <th>平均响应</th>
                <th>运行时长</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="stat in monitoringHistory" :key="stat.date">
                <td>{{ stat.date }}</td>
                <td>
                  <span class="mode-badge-small" :class="`mode-${stat.monitoring_mode || 'unknown'}`">
                    {{ getModeName(stat.monitoring_mode) }}
                  </span>
                </td>
                <td>
                  <span :class="stat.event_driven_active ? 'status-yes' : 'status-no'">
                    {{ stat.event_driven_active ? '✓' : '✗' }}
                  </span>
                </td>
                <td>{{ stat.communication_count || 0 }}</td>
                <td>{{ stat.avg_response_time_ms?.toFixed(1) || 'N/A' }} ms</td>
                <td>{{ formatUptime(stat.uptime_seconds) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-else-if="!loadingMonitoringStats" class="empty-state">
        暂无监控统计数据
      </div>

      <div v-if="loadingMonitoringStats" class="loading-state">
        加载中...
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, defineAsyncComponent, watch, computed } from 'vue'
import axios from 'axios'
// 使用异步组件加载 ECharts，提升首屏加载速度
const PowerChart = defineAsyncComponent(() => import('@/components/PowerChart.vue'))
import DateRangePicker from '@/components/DateRangePicker.vue'
import DailyEnergyChart from '@/components/DailyEnergyChart.vue'
import type { Metric } from '@/types/ups'
import { useToast } from '@/composables/useToast'

const toast = useToast()
const metrics = ref<Metric[]>([])
const loadingMetrics = ref(false)

// 导出相关状态
const exportFormat = ref('csv')
const exportType = ref('all')
const startDate = ref('')
const endDate = ref('')
const exporting = ref(false)
const exportResult = ref<{ success: boolean; message: string } | null>(null)

// 时间范围选择
const selectedTimeRange = ref(24) // 默认24小时
const timeRanges = [
  { label: '5分钟', value: 5 / 60 },
  { label: '1小时', value: 1 },
  { label: '24小时', value: 24 }
]

// 电池测试报告相关
const testReports = ref<any[]>([])
const loadingReports = ref(false)
const showReportDialog = ref(false)
const currentReport = ref<any>(null)
const exportingReports = ref(false)

// 筛选相关
const reportFilterType = ref('')
const reportFilterResult = ref('')
const reportFilterStartDate = ref('')
const reportFilterEndDate = ref('')

// 是否有激活的筛选
const hasActiveFilters = computed(() => {
  return reportFilterType.value || reportFilterResult.value ||
         reportFilterStartDate.value || reportFilterEndDate.value
})

// 清除筛选
const clearReportFilters = () => {
  reportFilterType.value = ''
  reportFilterResult.value = ''
  reportFilterStartDate.value = ''
  reportFilterEndDate.value = ''
  fetchTestReports()
}

// 获取测试报告列表
const fetchTestReports = async () => {
  loadingReports.value = true
  try {
    // 构建查询参数
    const params = new URLSearchParams()
    params.append('limit', '50')

    if (reportFilterType.value) {
      params.append('test_type', reportFilterType.value)
    }
    if (reportFilterResult.value) {
      params.append('result', reportFilterResult.value)
    }
    // DateRangePicker 返回 datetime-local 格式 (如 "2026-02-14T00:00")
    // 后端需要 ISO 日期格式 (如 "2026-02-14")
    if (reportFilterStartDate.value) {
      const dateOnly = reportFilterStartDate.value.split('T')[0]
      params.append('start_date', dateOnly)
    }
    if (reportFilterEndDate.value) {
      const dateOnly = reportFilterEndDate.value.split('T')[0]
      params.append('end_date', dateOnly)
    }

    const response = await axios.get(`/api/ups/test-reports?${params.toString()}`)
    testReports.value = response.data.reports || []
  } catch (error) {
    console.error('Failed to fetch test reports:', error)
  } finally {
    loadingReports.value = false
  }
}

// 显示报告详情
const showReportDetail = (report: any) => {
  currentReport.value = report
  showReportDialog.value = true
}

// 获取结果图标
const getResultIcon = (result: string) => {
  const icons: Record<string, string> = {
    'passed': '✅',
    'warning': '⚠️',
    'failed': '❌',
    'in_progress': '🔄',
    'cancelled': '⏹️',
    'unknown': '❓',
  }
  return icons[result] || '❓'
}

// 获取结果文本
const getResultText = (result: string) => {
  const texts: Record<string, string> = {
    'passed': '通过',
    'warning': '警告',
    'failed': '失败',
    'in_progress': '进行中',
    'cancelled': '已取消',
    'unknown': '未知',
  }
  return texts[result] || '未知'
}

// 获取监控模式中文名称
const getModeName = (mode: string | null): string => {
  if (!mode) return 'N/A'
  const modeLabels: Record<string, string> = {
    'polling': '轮询模式',
    'event_driven': '事件驱动',
    'hybrid': '混合模式',
  }
  return modeLabels[mode] || mode
}

// 格式化时间
const formatDateTime = (timestamp: string) => {
  if (!timestamp) return 'N/A'
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

// 格式化持续时间
const formatDuration = (seconds: number) => {
  if (!seconds) return 'N/A'
  if (seconds < 60) return `${seconds}秒`
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (minutes < 60) return secs > 0 ? `${minutes}分${secs}秒` : `${minutes}分钟`
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return mins > 0 ? `${hours}小时${mins}分` : `${hours}小时`
}

// 格式化运行时间
const formatRuntime = (seconds: number | null | undefined) => {
  if (seconds === null || seconds === undefined) return 'N/A'
  const minutes = Math.floor(seconds / 60)
  return `${minutes}分钟`
}

// 获取电压变化
const getVoltageChange = (report: any) => {
  if (!report.start_data?.battery_voltage || !report.end_data?.battery_voltage) return null
  return report.end_data.battery_voltage - report.start_data.battery_voltage
}

// 格式化电压变化
const formatVoltageChange = (report: any) => {
  const change = getVoltageChange(report)
  if (change === null) return 'N/A'
  return (change > 0 ? '+' : '') + change.toFixed(2) + 'V'
}

// 获取变化的样式类
const getChangeClass = (change: number | null) => {
  if (change === null) return ''
  if (change < 0) return 'negative'
  if (change > 0) return 'positive'
  return ''
}

// 下载报告
const downloadReport = (report: any) => {
  if (!report) return

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)

  let markdown = `# 电池测试报告 #${report.id}

> 生成时间: ${formatDateTime(new Date().toISOString())}

## 📋 测试概要

- **测试类型**: ${report.test_type === 'quick' ? '⚡ 快速测试' : '🔋 深度测试'}
- **测试结果**: ${getResultIcon(report.result)} ${report.result_text || getResultText(report.result)}
- **开始时间**: ${formatDateTime(report.started_at)}
- **结束时间**: ${report.completed_at ? formatDateTime(report.completed_at) : 'N/A'}
- **测试时长**: ${report.duration_seconds ? formatDuration(report.duration_seconds) : 'N/A'}

---

## 🔋 电池数据对比

| 项目 | 测试前 | 测试后 | 变化 |
|------|--------|--------|------|
| 电量 | ${report.start_data?.battery_charge?.toFixed(1) ?? 'N/A'}% | ${report.end_data?.battery_charge?.toFixed(1) ?? 'N/A'}% | ${report.charge_change !== null ? (report.charge_change > 0 ? '+' : '') + report.charge_change.toFixed(1) + '%' : 'N/A'} |
| 电压 | ${report.start_data?.battery_voltage?.toFixed(2) ?? 'N/A'}V | ${report.end_data?.battery_voltage?.toFixed(2) ?? 'N/A'}V | ${formatVoltageChange(report)} |
| 预计续航 | ${formatRuntime(report.start_data?.battery_runtime)} | ${formatRuntime(report.end_data?.battery_runtime)} | - |
| 负载 | ${report.start_data?.load_percent?.toFixed(1) ?? 'N/A'}% | ${report.end_data?.load_percent?.toFixed(1) ?? 'N/A'}% | - |

---

## 🔌 UPS 信息

| 项目 | 值 |
|------|-----|
| 制造商 | ${report.ups_info?.manufacturer || 'N/A'} |
| 型号 | ${report.ups_info?.model || 'N/A'} |
| 序列号 | ${report.ups_info?.serial || 'N/A'} |

---

## 📊 采样数据

共 ${report.sample_count || 0} 个采样点

${report.samples && report.samples.length > 0 ? `
| 时间 | 电量 | 电压 |
|------|------|------|
${report.samples.map((s: any) => `| ${formatDateTime(s.timestamp)} | ${s.battery_charge?.toFixed(1) ?? 'N/A'}% | ${s.battery_voltage?.toFixed(2) ?? 'N/A'}V |`).join('\n')}
` : '无采样数据'}

---

*报告由 UPS Guard 自动生成*
`

  const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `battery-test-report-${report.id}-${timestamp}.md`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)

  toast.success('报告已下载')
}

// 批量导出测试报告
const exportAllReports = async () => {
  if (testReports.value.length === 0) {
    toast.error('没有可导出的报告')
    return
  }

  exportingReports.value = true

  try {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)

    // 生成 CSV 格式
    let csv = 'ID,测试类型,测试结果,开始时间,结束时间,时长(秒),起始电量(%),结束电量(%),电量变化(%),起始电压(V),结束电压(V),采样点数,UPS型号,UPS序列号\n'

    for (const report of testReports.value) {
      const row = [
        report.id,
        report.test_type === 'quick' ? '快速测试' : '深度测试',
        getResultText(report.result),
        report.started_at || '',
        report.completed_at || '',
        report.duration_seconds || '',
        report.start_data?.battery_charge?.toFixed(1) || '',
        report.end_data?.battery_charge?.toFixed(1) || '',
        report.charge_change?.toFixed(1) || '',
        report.start_data?.battery_voltage?.toFixed(2) || '',
        report.end_data?.battery_voltage?.toFixed(2) || '',
        report.sample_count || 0,
        report.ups_info?.model || '',
        report.ups_info?.serial || ''
      ]
      csv += row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',') + '\n'
    }

    // 创建并下载文件
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `battery-test-reports-${timestamp}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    toast.success(`已导出 ${testReports.value.length} 份测试报告`)
  } catch (error) {
    console.error('Failed to export reports:', error)
    toast.error('导出失败')
  } finally {
    exportingReports.value = false
  }
}

// 防抖定时器
let queryDebounceTimer: ReturnType<typeof setTimeout> | null = null

// 监听日期变化，自动查询
watch([startDate, endDate], ([newStart, newEnd]) => {
  if (newStart && newEnd) {
    // 取消预设时间范围按钮选中状态
    selectedTimeRange.value = -1

    // 防抖：延迟300ms执行查询，避免频繁请求
    if (queryDebounceTimer) {
      clearTimeout(queryDebounceTimer)
    }
    queryDebounceTimer = setTimeout(() => {
      queryDataSilent()
    }, 300)
  }
})

// 静默查询（不显示toast提示，用于自动查询）
const queryDataSilent = async () => {
  if (!startDate.value || !endDate.value) return

  // Parse datetime-local values as local time
  const start = new Date(startDate.value)
  const end = new Date(endDate.value)
  const now = new Date()
  
  // Calculate hours from now to the start date to ensure we fetch enough data
  const hoursFromNowToStart = Math.ceil((now.getTime() - start.getTime()) / (1000 * 60 * 60))
  
  // Ensure we request at least the hours needed to cover the date range
  const hoursToRequest = Math.max(hoursFromNowToStart, 1)
  
  if (hoursToRequest > 720) {
    toast.error('查询范围不能超过30天')
    return
  }

  loadingMetrics.value = true

  try {
    const queryParam = hoursToRequest < 1 ? `minutes=${Math.round(hoursToRequest * 60)}` : `hours=${hoursToRequest}`
    const response = await axios.get(`/api/history/metrics?${queryParam}`)

    // Filter results to only include data within the selected date range
    // 前端发的是本地时间字符串，后端返回UTC时间戳，统一按UTC比较
    const startTime = start.getTime()
    const endTime = end.getTime()

    metrics.value = response.data.metrics.filter((m: Metric) => {
      // 后端时间戳是无时区格式 "2026-03-27 08:00:00"，按本地时间解析
      const ts = m.timestamp.replace('T', ' ').replace('Z', '').replace(/[+-]\d{2}:\d{2}$/, '')
      const parts = ts.split(/[-T:. ]/)
      const date = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]),
        parseInt(parts[3] || '0'), parseInt(parts[4] || '0'), parseInt(parts[5] || '0'))
      return date.getTime() >= startTime && date.getTime() <= endTime
    })
  } catch (error) {
    console.error('Failed to query metrics:', error)
  } finally {
    loadingMetrics.value = false
  }
}


// 格式化为 datetime-local 输入框所需的格式
const formatDateTimeLocal = (date: Date): string => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day}T${hours}:${minutes}`
}

// 初始化日期范围（默认最近7天）
const initializeDates = () => {
  const today = new Date()
  const sevenDaysAgo = new Date(today)
  sevenDaysAgo.setDate(today.getDate() - 7)
  
  endDate.value = formatDateTimeLocal(today)
  startDate.value = formatDateTimeLocal(sevenDaysAgo)
}

// 同步日期范围到选择框
const syncDatesToTimeRange = (hours: number) => {
  const now = new Date()
  const start = new Date(now)

  if (hours < 1) {
    // 分钟级别
    start.setMinutes(now.getMinutes() - Math.round(hours * 60))
  } else {
    start.setHours(now.getHours() - hours)
  }

  endDate.value = formatDateTimeLocal(now)
  startDate.value = formatDateTimeLocal(start)
}

const fetchMetrics = async (hours: number = 24) => {
  loadingMetrics.value = true
  try {
    // 对于小于1小时的请求，使用分钟参数
    const queryParam = hours < 1 ? `minutes=${Math.round(hours * 60)}` : `hours=${Math.round(hours)}`
    const response = await axios.get(`/api/history/metrics?${queryParam}`)
    metrics.value = response.data.metrics
  } catch (error) {
    console.error('Failed to fetch metrics:', error)
    toast.error('获取历史数据失败')
  } finally {
    loadingMetrics.value = false
  }
}

// 切换时间范围
const changeTimeRange = (hours: number) => {
  selectedTimeRange.value = hours
  syncDatesToTimeRange(hours)
  fetchMetrics(hours)
}


// 导出数据
const exportData = async () => {
  if (!startDate.value || !endDate.value) {
    toast.error('请选择日期范围')
    return
  }

  // 检查日期范围
  const start = new Date(startDate.value)
  const end = new Date(endDate.value)
  const daysDiff = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
  
  if (daysDiff > 90) {
    toast.error('导出时间范围不能超过90天')
    return
  }

  exporting.value = true
  exportResult.value = null

  try {
    // 构建查询参数
    const params = new URLSearchParams({
      format: exportFormat.value,
      type: exportType.value,
      start_date: new Date(startDate.value).toISOString(),
      end_date: new Date(endDate.value).toISOString()
    })

    const response = await axios.get(`/api/history/export?${params.toString()}`, {
      responseType: 'blob',
      timeout: 60000, // 导出大数据量需要更长时间
      validateStatus: (status) => status < 500 // 允许 4xx 状态码不抛出异常
    })

    // 检查响应状态
    if (response.status >= 400) {
      // 尝试解析错误信息
      try {
        const text = await response.data.text()
        const errorData = JSON.parse(text)
        throw new Error(errorData.detail || `服务器错误 (${response.status})`)
      } catch (parseErr) {
        if (parseErr instanceof SyntaxError) {
          throw new Error(`服务器响应格式错误 (${response.status})`)
        }
        throw parseErr
      }
    }

    // 检查响应是否为 JSON 错误（有些服务器返回 200 但内容是错误信息）
    const contentType = response.headers['content-type'] || ''
    if (contentType.includes('application/json')) {
      try {
        const text = await response.data.text()
        const errorData = JSON.parse(text)
        throw new Error(errorData.detail || '导出失败')
      } catch {
        throw new Error('服务器返回了意外的响应格式')
      }
    }

    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url

    // 从响应头获取文件名
    const contentDisposition = response.headers['content-disposition']
    let filename = `ups-guard-${exportType.value}.${exportFormat.value}`
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/)
      if (filenameMatch) {
        filename = filenameMatch[1]
      }
    }

    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)

    exportResult.value = {
      success: true,
      message: '数据导出成功'
    }
    toast.success('数据导出成功')

    // 3秒后清除结果提示
    setTimeout(() => {
      exportResult.value = null
    }, 3000)
  } catch (error: any) {
    console.error('Export failed:', error)
    let errorMsg = '导出失败'

    // 处理超时
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      errorMsg = '导出超时，请缩小日期范围后重试'
    }
    // 处理 blob 响应中的错误
    else if (error.response?.data instanceof Blob) {
      try {
        const text = await error.response.data.text()
        const errorData = JSON.parse(text)
        errorMsg = errorData.detail || `服务器错误 (${error.response.status})`
      } catch {
        errorMsg = `导出失败 (HTTP ${error.response.status || '未知'})`
      }
    } else if (error.response?.data?.detail) {
      errorMsg = error.response.data.detail
    } else if (error.message) {
      errorMsg = error.message
    }

    exportResult.value = {
      success: false,
      message: errorMsg
    }
    toast.error(errorMsg)
  } finally {
    exporting.value = false
  }
}

// ==================== 监控统计相关 ====================
const loadingMonitoringStats = ref(false)
const currentMonitoringStats = ref<any>(null)
const monitoringHistory = ref<any[]>([])
const selectedMonitoringRange = ref(7)

const monitoringRanges = [
  { value: 7, label: '最近7天' },
  { value: 14, label: '最近14天' },
  { value: 30, label: '最近30天' },
  { value: 60, label: '最近60天' },
  { value: 90, label: '最近90天' }
]

// 获取监控统计数据
const fetchMonitoringStats = async () => {
  loadingMonitoringStats.value = true
  try {
    // 获取实时统计
    const currentResponse = await axios.get('/api/system/monitoring-stats')
    currentMonitoringStats.value = currentResponse.data

    // 获取历史统计
    const historyResponse = await axios.get(`/api/system/monitoring-stats/history?days=${selectedMonitoringRange.value}`)
    monitoringHistory.value = historyResponse.data.stats || []
  } catch (error) {
    console.error('Failed to fetch monitoring stats:', error)
  } finally {
    loadingMonitoringStats.value = false
  }
}

// 切换监控统计日期范围
const changeMonitoringRange = (days: number) => {
  selectedMonitoringRange.value = days
  fetchMonitoringStats()
}

// 格式化运行时长
const formatUptime = (seconds: number | null): string => {
  if (!seconds) return 'N/A'
  
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  
  if (hours > 24) {
    const days = Math.floor(hours / 24)
    const remainingHours = hours % 24
    return `${days}天${remainingHours}小时`
  } else if (hours > 0) {
    return `${hours}小时${minutes}分钟`
  } else {
    return `${minutes}分钟`
  }
}

onMounted(() => {
  fetchMetrics(selectedTimeRange.value)
  initializeDates()
  fetchTestReports()
  fetchMonitoringStats()
  
  // 每30秒刷新监控统计
  setInterval(() => {
    fetchMonitoringStats()
  }, 30000)
})
</script>

<style scoped>
.history {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--ups-card-gap);
}

.history h2 {
  margin-bottom: var(--ups-card-gap);
}

/* 双列布局: 历史图表 | 数据导出面板 */
.history-main-row {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: var(--ups-card-gap);
  margin-bottom: var(--ups-card-gap);
}

/* 图表卡片 - 限制高度 */
.chart-section {
  display: flex;
  flex-direction: column;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-sm);
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.card-title {
  margin: 0;
  font-size: 1.1rem;
  color: var(--text-primary);
  font-weight: 600;
}

.time-range-selector {
  display: flex;
  gap: 0.375rem;
}

.time-range-btn {
  padding: 0.25rem 0.625rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  color: var(--text-secondary);
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}

.time-range-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.time-range-btn.active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: white;
}

.loading-state,
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  flex: 1;
  color: var(--text-secondary);
  font-size: 0.875rem;
}

/* 导出面板 - 紧凑型 */
.export-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.export-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.form-group.full-width {
  grid-column: 1 / -1;
}

.form-label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-primary);
}

.form-control {
  padding: 0.5rem 0.625rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 0.8125rem;
}

.form-control:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.btn {
  padding: 0.5rem 0.875rem;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--color-primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}


.help-text {
  font-size: 0.6875rem;
  color: var(--text-secondary);
}

.export-result {
  padding: var(--spacing-sm);
  border-radius: var(--radius-sm);
  font-size: 0.8125rem;
}

.export-result.success {
  background: #d1fae5;
  color: #065f46;
}

.export-result.error {
  background: #fee2e2;
  color: #991b1b;
}

/* 响应式: 移动端退回单列 */
@media (max-width: 768px) {
  .history-main-row {
    grid-template-columns: 1fr;
  }
  
  .chart-section {
    height: 300px;
  }
}

/* 电池测试报告区域 */
.test-reports-section {
  margin-top: var(--ups-card-gap);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.section-actions {
  display: flex;
  gap: var(--spacing-xs);
  align-items: center;
}

.btn-sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.75rem;
}

.btn-secondary {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-tertiary);
}

.test-reports-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--spacing-md);
}

.test-report-card {
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid var(--border-color);
}

.test-report-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--color-primary);
}

.test-report-card.result-passed {
  border-left: 3px solid #10b981;
}

.test-report-card.result-warning {
  border-left: 3px solid #f59e0b;
}

.test-report-card.result-failed {
  border-left: 3px solid #ef4444;
}

.test-report-card.result-in_progress {
  border-left: 3px solid #3b82f6;
}

.test-report-card.result-cancelled {
  border-left: 3px solid #6b7280;
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-sm);
}

.test-type-badge {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-primary);
  background: var(--bg-tertiary);
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
}

.result-badge {
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
}

.result-badge.result-passed {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.result-badge.result-warning {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.result-badge.result-failed {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.result-badge.result-in_progress {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.result-badge.result-cancelled {
  background: rgba(107, 114, 128, 0.1);
  color: #6b7280;
}

.report-time {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  margin-bottom: var(--spacing-sm);
}

.report-stats {
  display: flex;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-sm);
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.stat-label {
  font-size: 0.6875rem;
  color: var(--text-tertiary);
}

.stat-value {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
}

.stat-value.negative {
  color: #ef4444;
}

.stat-value.positive {
  color: #10b981;
}

.report-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--border-color);
}

.ups-model {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.view-detail {
  font-size: 0.75rem;
  color: var(--color-primary);
}

/* 报告详情弹窗 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.modal-dialog {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  max-width: 600px;
  width: 95%;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
  margin: 0;
  font-size: 1.125rem;
}

.btn-close {
  background: transparent;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  color: var(--text-secondary);
  padding: 0.25rem 0.5rem;
  line-height: 1;
  border-radius: var(--radius-sm);
}

.btn-close:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.report-detail-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-md);
}

.detail-section {
  margin-bottom: var(--spacing-lg);
}

.detail-section h4 {
  margin: 0 0 var(--spacing-sm) 0;
  font-size: 0.9375rem;
  color: var(--text-primary);
}

.summary-section {
  text-align: center;
  padding: var(--spacing-lg);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.test-type-large {
  font-size: 1rem;
  font-weight: 500;
  margin-bottom: var(--spacing-sm);
}

.result-large {
  font-size: 1.25rem;
  font-weight: 600;
}

.result-large.result-passed { color: #10b981; }
.result-large.result-warning { color: #f59e0b; }
.result-large.result-failed { color: #ef4444; }
.result-large.result-in_progress { color: #3b82f6; }
.result-large.result-cancelled { color: #6b7280; }

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-sm);
}

.detail-item {
  display: flex;
  justify-content: space-between;
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.detail-item .label {
  color: var(--text-secondary);
  font-size: 0.8125rem;
}

.detail-item .value {
  color: var(--text-primary);
  font-weight: 500;
  font-size: 0.875rem;
}

/* 数据对比表格 */
.comparison-table {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.comparison-header,
.comparison-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 1fr;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
}

.comparison-header {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}

.comparison-row {
  font-size: 0.8125rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.comparison-row .label {
  color: var(--text-secondary);
}

.comparison-row .negative {
  color: #ef4444;
}

.comparison-row .positive {
  color: #10b981;
}

/* 采样数据图表 */
.samples-chart {
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
}

.chart-bars {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 100px;
  margin-bottom: var(--spacing-sm);
}

.chart-bar {
  flex: 1;
  background: linear-gradient(to top, var(--color-primary), #60a5fa);
  border-radius: 2px 2px 0 0;
  min-height: 2px;
  transition: height 0.2s;
}

.chart-bar:hover {
  opacity: 0.8;
}

.chart-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.6875rem;
  color: var(--text-tertiary);
}

.detail-footer {
  text-align: center;
  padding-top: var(--spacing-sm);
  color: var(--text-tertiary);
  font-size: 0.75rem;
}

.modal-actions {
  display: flex;
  gap: var(--spacing-sm);
  justify-content: flex-end;
  padding: var(--spacing-md);
  border-top: 1px solid var(--border-color);
}

@media (max-width: 480px) {
  .test-reports-grid {
    grid-template-columns: 1fr;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }

  .comparison-header,
  .comparison-row {
    grid-template-columns: 1fr 1fr;
    font-size: 0.75rem;
  }

  .report-filters {
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  .filter-group {
    width: 100%;
  }
}

/* 报告筛选区域 */
.report-filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-md);
  align-items: flex-end;
  padding: var(--spacing-md);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-md);
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.filter-group.filter-date-range {
  flex: 1;
  min-width: 280px;
  max-width: 400px;
}

.filter-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.filter-control {
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 0.875rem;
  min-width: 140px;
}

.filter-control:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

.btn-link {
  background: none;
  border: none;
  color: var(--color-primary);
  cursor: pointer;
  font-size: 0.875rem;
  padding: 0.375rem 0.5rem;
}

.btn-link:hover {
  text-decoration: underline;
}

/* ==================== 监控统计卡片样式 ==================== */
.monitoring-stats-section {
  margin-top: 24px;
}

.date-range-selector {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.range-btn {
  padding: 8px 16px;
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
  color: var(--text-primary);
  border-radius: 6px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.range-btn:hover {
  background: var(--bg-hover);
  border-color: var(--color-primary);
}

.range-btn.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.monitoring-current {
  margin-bottom: 24px;
}

.subsection-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--border-color);
}

.stats-grid-monitoring {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.stat-box {
  background: var(--bg-secondary);
  padding: 16px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.stat-box .stat-label {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.stat-box .stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
}

.mode-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 0.875rem !important;
  font-weight: 600 !important;
  text-transform: lowercase;
}

.mode-badge.mode-polling {
  background: #dbeafe;
  color: #1e40af;
}

.mode-badge.mode-event_driven {
  background: #d1fae5;
  color: #065f46;
}

.mode-badge.mode-hybrid {
  background: #fef3c7;
  color: #92400e;
}

.mode-badge.mode-unknown {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.status-active {
  color: #10b981;
  font-weight: 600;
}

.status-inactive {
  color: #f59e0b;
  font-weight: 600;
}

.monitoring-history {
  margin-top: 24px;
}

.monitoring-table {
  overflow-x: auto;
}

.monitoring-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.monitoring-table thead {
  background: var(--bg-secondary);
  border-bottom: 2px solid var(--border-color);
}

.monitoring-table th {
  padding: 12px 16px;
  text-align: left;
  font-weight: 600;
  color: var(--text-secondary);
  white-space: nowrap;
}

.monitoring-table td {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.monitoring-table tbody tr:hover {
  background: var(--bg-hover);
}

.mode-badge-small {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: lowercase;
}

.mode-badge-small.mode-polling {
  background: #dbeafe;
  color: #1e40af;
}

.mode-badge-small.mode-event_driven {
  background: #d1fae5;
  color: #065f46;
}

.mode-badge-small.mode-hybrid {
  background: #fef3c7;
  color: #92400e;
}

.mode-badge-small.mode-unknown {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.status-yes {
  color: #10b981;
  font-weight: 600;
}

.status-no {
  color: #6b7280;
}
</style>
