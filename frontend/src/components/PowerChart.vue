<template>
  <div class="power-chart card">
    <div class="card-header">
      <h3 class="card-title">{{ title }}</h3>
      <template v-if="props.showTodayEnergy">
        <span v-if="todayEnergy !== null" class="today-energy">今日用电: {{ todayEnergy }} 度</span>
        <span v-else-if="props.metrics.length" class="today-energy today-energy-warn">今日用电: 数据不足</span>
      </template>
    </div>
    <v-chart class="chart" :option="chartOption" autoresize />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent
} from 'echarts/components'
import type { Metric } from '@/types/ups'
import { useTheme } from '@/composables/useTheme'

use([
  CanvasRenderer,
  LineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent
])

const props = defineProps<{
  title: string
  metrics: Metric[]
  upsNominalPower?: number  // UPS 标称功率 (W)，用于在 power_watts 为 null 时估算
  showTodayEnergy?: boolean  // 是否显示今日用电（默认不显示）
}>()

const { effectiveTheme } = useTheme()

// 今日用电量（度）：用功率 × 时间积分计算
const todayEnergy = computed(() => {
  if (!props.metrics.length || !props.upsNominalPower) return null
  const pad = (n: number) => String(n).padStart(2, '0')
  const now = new Date()
  const midnightStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T00:00:00`

  // 只用今天 00:00 之后的数据
  const todayMetrics = props.metrics.filter(m => {
    const ts = m.timestamp.replace('Z', '').replace(/[+-]\d{2}:\d{2}$/, '')
    return ts >= midnightStr
  })

  if (todayMetrics.length < 2) return '0.00'

  let totalWh = 0
  for (let i = 1; i < todayMetrics.length; i++) {
    const prev = todayMetrics[i - 1]
    const curr = todayMetrics[i]
    // 解析时间差
    const prevTs = prev.timestamp.replace('Z', '').replace(/[+-]\d{2}:\d{2}$/, '')
    const currTs = curr.timestamp.replace('Z', '').replace(/[+-]\d{2}:\d{2}$/, '')
    const prevTime = new Date(prevTs.replace('T', ' '))
    const currTime = new Date(currTs.replace('T', ' '))
    const dtHours = (currTime.getTime() - prevTime.getTime()) / 3600000
    if (dtHours <= 0 || dtHours > 24) continue

    // 功率：优先 power_watts，否则用 load × 标称
    let watts = curr.power_watts
    if (watts == null && curr.load_percent != null) {
      watts = props.upsNominalPower * curr.load_percent / 100
    }
    if (watts != null) {
      totalWh += watts * dtHours
    }
  }

  return (totalWh / 1000).toFixed(2)  // Wh → kWh（度）
})

const chartOption = computed(() => {
  // Parse timestamps correctly - backend sends naive datetime (no timezone)
  const timestamps = props.metrics.map(m => {
    const isoString = m.timestamp
    // If no timezone info, parse as local time
    if (!isoString.endsWith('Z') && !isoString.match(/[+-]\d{2}:\d{2}$/)) {
      const parts = isoString.split(/[-T:.]/)
      const year = parseInt(parts[0])
      const month = parseInt(parts[1]) - 1
      const day = parseInt(parts[2])
      const hour = parseInt(parts[3] || '0')
      const minute = parseInt(parts[4] || '0')
      const second = parseInt(parts[5] || '0')
      const date = new Date(year, month, day, hour, minute, second)
      // 根据数据跨度选择格式
      return formatTimestamp(date, props.metrics)
    }
    const date = new Date(isoString.endsWith('Z') ? isoString : isoString + 'Z')
    return formatTimestamp(date, props.metrics)
  })

  // 格式化时间戳：跨天时显示日期+时间
  function formatTimestamp(date: Date, metrics: Metric[]) {
    if (metrics.length < 2) return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
    // 检查是否跨天
    const first = parseTimestamp(metrics[0].timestamp)
    const last = parseTimestamp(metrics[metrics.length - 1].timestamp)
    const spanHours = (last.getTime() - first.getTime()) / 3600000
    if (spanHours > 24) {
      // 跨天，显示 MM-DD HH:mm
      const pad = (n: number) => String(n).padStart(2, '0')
      return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
    }
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
  }

  function parseTimestamp(isoString: string): Date {
    if (!isoString.endsWith('Z') && !isoString.match(/[+-]\d{2}:\d{2}$/)) {
      const parts = isoString.split(/[-T:.]/)
      return new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]),
        parseInt(parts[3] || '0'), parseInt(parts[4] || '0'), parseInt(parts[5] || '0'))
    }
    return new Date(isoString.endsWith('Z') ? isoString : isoString + 'Z')
  }
  
  // 根据主题设置颜色
  const isDark = effectiveTheme.value === 'dark'
  const textColor = isDark ? '#D1D5DB' : '#6B7280'
  const axisLineColor = isDark ? '#374151' : '#E5E7EB'

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      backgroundColor: isDark ? '#1F2937' : '#FFFFFF',
      borderColor: isDark ? '#374151' : '#E5E7EB',
      textStyle: {
        color: textColor
      },
      formatter: (params: any) => {
        if (!params || !params.length) return ''
        const idx = params[0].dataIndex
        const m = props.metrics[idx]
        const nominal = props.upsNominalPower || 1000
        let html = `<b>${params[0].axisValueLabel}</b><br/>`
        for (const p of params) {
          if (p.seriesName === '功率(W)') {
            let watts = m.power_watts
            if (watts == null && m.load_percent != null) {
              watts = nominal * m.load_percent / 100
            }
            html += `${p.marker} 功率: <b>${watts != null ? (Math.round(watts * 10) / 10) + 'W' : 'N/A'}</b><br/>`
          } else if (p.seriesName === '用电量(kWh)') {
            html += `${p.marker} 今日用电: <b>${p.value != null ? p.value + ' 度' : 'N/A'}</b><br/>`
          } else {
            html += `${p.marker} ${p.seriesName}: <b>${p.value != null ? p.value : 'N/A'}</b><br/>`
          }
        }
        return html
      }
    },
    legend: {
      data: ['电池电量', '负载百分比', '输入电压', '输出电压(推算)', '功率(W)'],
      bottom: 8,
      textStyle: {
        color: textColor,
        fontSize: 12
      },
      itemGap: 20,
      itemWidth: 16,
      itemHeight: 10
    },
    grid: {
      left: '7%',
      right: '7%',
      bottom: '18%',
      top: '8%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: timestamps,
      axisLine: {
        lineStyle: {
          color: axisLineColor
        }
      },
      axisLabel: {
        color: textColor
      }
    },
    yAxis: [
      {
        type: 'value',
        name: '百分比',
        min: 0,
        max: 100,
        position: 'left',
        axisLine: {
          lineStyle: {
            color: axisLineColor
          }
        },
        axisLabel: {
          color: textColor,
          formatter: '{value}'
        },
        splitLine: {
          lineStyle: {
            color: axisLineColor,
            type: 'dashed'
          }
        },
        nameTextStyle: {
          color: textColor,
          fontSize: 11
        }
      },
      {
        type: 'value',
        name: '电压(V)',
        min: 200,
        max: 240,
        position: 'right',
        axisLine: {
          lineStyle: {
            color: '#3B82F6'
          }
        },
        axisLabel: {
          color: textColor,
          formatter: '{value}'
        },
        splitLine: {
          show: false
        },
        nameTextStyle: {
          color: textColor,
          fontSize: 11
        }
      }
    ],
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100
      }
    ],
    series: [
      {
        name: '电池电量',
        type: 'line',
        yAxisIndex: 0,
        data: props.metrics.map(m => m.battery_charge),
        smooth: true,
        lineStyle: { color: '#10B981' },
        itemStyle: { color: '#10B981' }
      },
      {
        name: '负载百分比',
        type: 'line',
        yAxisIndex: 0,
        data: props.metrics.map(m => m.load_percent),
        smooth: true,
        lineStyle: { color: '#F59E0B' },
        itemStyle: { color: '#F59E0B' }
      },
      {
        name: '输入电压',
        type: 'line',
        yAxisIndex: 1,
        data: props.metrics.map(m => m.input_voltage),
        smooth: true,
        lineStyle: { color: '#3B82F6' },
        itemStyle: { color: '#3B82F6' }
      },
      {
        name: '输出电压(推算)',
        type: 'line',
        yAxisIndex: 1,
        data: props.metrics.map(m => {
          // 后端有值直接用
          if (m.output_voltage != null) return Math.round(m.output_voltage * 10) / 10
          // 前端推算：输出电压 ≈ 输入电压（线路交互式 UPS 在线时压降可忽略）
          if (m.input_voltage != null) return Math.round(m.input_voltage * 10) / 10
          return null
        }),
        smooth: true,
        lineStyle: { color: '#8B5CF6', type: 'dashed' },
        itemStyle: { color: '#8B5CF6' }
      },
      {
        name: '功率(W)',
        type: 'line',
        yAxisIndex: 0,
        data: props.metrics.map(m => {
          const nominal = props.upsNominalPower || 1000
          let watts = m.power_watts
          if (watts == null && m.load_percent != null) {
            watts = nominal * m.load_percent / 100
          }
          // 归一化到百分比（占标称功率的%）
          return watts != null ? Math.round(watts / nominal * 100 * 10) / 10 : null
        }),
        smooth: true,
        lineStyle: { color: '#F472B6', width: 2 },
        itemStyle: { color: '#F472B6' },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(244,114,182,0.15)' },
              { offset: 1, color: 'rgba(244,114,182,0.02)' }
            ]
          }
        }
      },
      // 今日用电不在图表上显示（数值太小），只在标题和tooltip中展示
    ]
  }
})
</script>

<style scoped>
.power-chart {
  min-height: 480px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.today-energy {
  font-size: 13px;
  color: #06B6D4;
  font-weight: 500;
}

.chart {
  width: 100%;
  height: 430px;
}
</style>
