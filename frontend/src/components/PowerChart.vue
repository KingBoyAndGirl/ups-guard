<template>
  <div class="power-chart card">
    <h3 class="card-title">{{ title }}</h3>
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
}>()

const { effectiveTheme } = useTheme()

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
      return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
    }
    return new Date(isoString).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
  })
  
  // 根据主题设置颜色
  const isDark = effectiveTheme.value === 'dark'
  const textColor = isDark ? '#D1D5DB' : '#6B7280'
  const axisLineColor = isDark ? '#374151' : '#E5E7EB'

  // 今日用电基准：找到今天 00:00 的 energy_kwh 读数
  // 以当前最新数据的日期来确定"今天"
  const now = new Date()
  const midnight = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0)
  const midnightStr = midnight.toISOString().slice(0, 19)  // "2026-03-27T00:00:00"

  // 找今天 00:00 之后最早的一条数据作为基准
  const todayMetrics = props.metrics.filter(m => {
    const ts = m.timestamp.replace('Z', '').replace(/[+-]\d{2}:\d{2}$/, '')
    return ts >= midnightStr
  })
  // 也找今天 00:00 之前最后一条数据（如果今天没有零点记录）
  const beforeMidnight = [...props.metrics].reverse().find(m => {
    const ts = m.timestamp.replace('Z', '').replace(/[+-]\d{2}:\d{2}$/, '')
    return ts < midnightStr && m.energy_kwh != null
  })

  const baselineEnergy = (todayMetrics.find(m => m.energy_kwh != null)?.energy_kwh)
    ?? (beforeMidnight?.energy_kwh)
    ?? 0
  
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
      }
    },
    legend: {
      data: ['电池电量', '负载百分比', '输入电压', '输出电压(推算)', '功率(W)', '今日用电(度)'],
      bottom: 8,
      textStyle: {
        color: textColor,
        fontSize: 12
      },
      itemGap: 20,
      itemWidth: 16,
      itemHeight: 10,
      selectedMode: false
    },
    grid: {
      left: '10%',
      right: '10%',
      bottom: '18%',
      top: '4%',
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
        },
        tooltip: {
          // 实际功率值显示在 tooltip
          formatter: (params: any) => {
            const idx = params.dataIndex
            const m = props.metrics[idx]
            const nominal = props.upsNominalPower || 1000
            let watts = m.power_watts
            if (watts == null && m.load_percent != null) {
              watts = nominal * m.load_percent / 100
            }
            return watts != null ? `${params.marker} 功率: <b>${Math.round(watts * 10) / 10}W</b>` : ''
          }
        }
      },
      {
        name: '今日用电(度)',
        type: 'line',
        yAxisIndex: 0,
        data: props.metrics.map(m => {
          if (m.energy_kwh == null) return null
          const todayKwh = m.energy_kwh - baselineEnergy
          return Math.round(todayKwh * 100) / 100  // 两位小数，单位：度
        }),
        smooth: true,
        lineStyle: { color: '#06B6D4', width: 2, type: 'dashed' },
        itemStyle: { color: '#06B6D4' },
        tooltip: {
          formatter: (params: any) => {
            const idx = params.dataIndex
            const m = props.metrics[idx]
            if (m.energy_kwh == null) return ''
            const todayKwh = Math.round((m.energy_kwh - baselineEnergy) * 100) / 100
            return `${params.marker} 今日用电(度): <b>${todayKwh}</b>`
          }
        }
      }
    ]
  }
})
</script>

<style scoped>
.power-chart {
  min-height: 480px;
}

.chart {
  width: 100%;
  height: 430px;
}
</style>
