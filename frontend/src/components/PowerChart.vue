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
  GridComponent
} from 'echarts/components'
import type { Metric } from '@/types/ups'
import { useTheme } from '@/composables/useTheme'

use([
  CanvasRenderer,
  LineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
])

const props = defineProps<{
  title: string
  metrics: Metric[]
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
      data: ['电池电量', '负载百分比', '输入电压', '输出电压'],
      textStyle: {
        color: textColor
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
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
        name: '百分比 (%)',
        min: 0,
        max: 100,
        position: 'left',
        axisLine: {
          lineStyle: {
            color: axisLineColor
          }
        },
        axisLabel: {
          color: textColor
        },
        splitLine: {
          lineStyle: {
            color: axisLineColor
          }
        },
        nameTextStyle: {
          color: textColor
        }
      },
      {
        type: 'value',
        name: '电压 (V)',
        min: 0,
        max: 250,
        position: 'right',
        axisLine: {
          lineStyle: {
            color: axisLineColor
          }
        },
        axisLabel: {
          color: textColor
        },
        splitLine: {
          lineStyle: {
            color: axisLineColor
          }
        },
        nameTextStyle: {
          color: textColor
        }
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
        name: '输出电压',
        type: 'line',
        yAxisIndex: 1,
        data: props.metrics.map(m => m.output_voltage),
        smooth: true,
        lineStyle: { color: '#8B5CF6' },
        itemStyle: { color: '#8B5CF6' }
      }
    ]
  }
})
</script>

<style scoped>
.power-chart {
  min-height: 400px;
}

.chart {
  width: 100%;
  height: 350px;
}
</style>
