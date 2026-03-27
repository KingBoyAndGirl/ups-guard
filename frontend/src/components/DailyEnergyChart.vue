<template>
  <div class="daily-energy-card card" v-if="stats">
    <div class="card-header">
      <h3 class="card-title">📊 选中范围统计</h3>
      <span class="stats-badge">共 {{ dailyData.length }} 天</span>
    </div>
    <div class="stats-grid">
      <div class="stat-item main">
        <span class="stat-label">总用电</span>
        <span class="stat-value">{{ stats.totalKwh }} <small>度</small></span>
      </div>
      <div class="stat-item">
        <span class="stat-label">日均</span>
        <span class="stat-value">{{ stats.avgKwh }} <small>度/天</small></span>
      </div>
      <div class="stat-item">
        <span class="stat-label">预估月费</span>
        <span class="stat-value cost">¥{{ stats.monthlyCost }}</span>
      </div>
      <div class="stat-item highlight">
        <span class="stat-label">最高日</span>
        <span class="stat-value">{{ stats.maxKwh }} 度 <span class="date">({{ stats.maxDate }})</span></span>
      </div>
      <div class="stat-item">
        <span class="stat-label">最低日</span>
        <span class="stat-value">{{ stats.minKwh }} 度 <span class="date">({{ stats.minDate }})</span></span>
      </div>
    </div>
    <v-chart class="bar-chart" :option="chartOption" autoresize />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useTheme } from '@/composables/useTheme'

use([BarChart, TitleComponent, TooltipComponent, GridComponent, CanvasRenderer])

interface Metric {
  timestamp: string
  power_watts: number | null
  load_percent: number | null
}

const props = defineProps<{
  metrics: Metric[]
  upsNominalPower?: number
}>()

const { effectiveTheme } = useTheme()

function parseTimestamp(isoString: string): Date {
  if (!isoString.endsWith('Z') && !isoString.match(/[+-]\d{2}:\d{2}$/)) {
    const parts = isoString.split(/[-T:.]/)
    return new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]),
      parseInt(parts[3] || '0'), parseInt(parts[4] || '0'), parseInt(parts[5] || '0'))
  }
  return new Date(isoString.endsWith('Z') ? isoString : isoString + 'Z')
}

function formatDate(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function formatDateFull(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

const dailyData = computed(() => {
  if (!props.metrics || props.metrics.length < 2) return []
  
  const nominal = props.upsNominalPower || 1024
  const dailyMap = new Map<string, number>()
  const dailyWh = new Map<string, number>()  // 存Wh用于计算时长
  
  for (let i = 1; i < props.metrics.length; i++) {
    const m = props.metrics[i]
    const prev = props.metrics[i - 1]
    const currTime = parseTimestamp(m.timestamp)
    const prevTime = parseTimestamp(prev.timestamp)
    const dtHours = (currTime.getTime() - prevTime.getTime()) / 3600000
    
    if (dtHours > 0 && dtHours < 2) {
      let watts = m.power_watts
      if (watts == null && m.load_percent != null) {
        watts = nominal * m.load_percent / 100
      }
      if (watts != null) {
        const dateKey = formatDateFull(currTime)
        const dayWh = (dailyWh.get(dateKey) || 0) + watts * dtHours
        dailyWh.set(dateKey, dayWh)
      }
    }
  }
  
  // 转换为数组并排序
  const result: { date: string; dateShort: string; kwh: number }[] = []
  for (const [date, wh] of dailyWh) {
    const d = new Date(date)
    result.push({
      date,
      dateShort: formatDate(d),
      kwh: Math.round(wh) / 1000
    })
  }
  result.sort((a, b) => a.date.localeCompare(b.date))
  return result
})

const stats = computed(() => {
  if (dailyData.value.length === 0) return null
  
  const total = dailyData.value.reduce((sum, d) => sum + d.kwh, 0)
  const avg = total / dailyData.value.length
  let max = dailyData.value[0]
  let min = dailyData.value[0]
  
  for (const d of dailyData.value) {
    if (d.kwh > max.kwh) max = d
    if (d.kwh < min.kwh) min = d
  }
  
  return {
    totalKwh: total.toFixed(2),
    avgKwh: avg.toFixed(2),
    monthlyCost: (total / dailyData.value.length * 30 * 0.6).toFixed(2),
    maxKwh: max.kwh.toFixed(2),
    maxDate: max.dateShort,
    minKwh: min.kwh.toFixed(2),
    minDate: min.dateShort
  }
})

const chartOption = computed(() => {
  const isDark = effectiveTheme.value === 'dark'
  const textColor = isDark ? '#D1D5DB' : '#6B7280'
  const axisLineColor = isDark ? '#374151' : '#E5E7EB'
  const barColor = '#3B82F6'
  
  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: isDark ? '#1F2937' : '#FFFFFF',
      borderColor: isDark ? '#374151' : '#E5E7EB',
      textStyle: { color: textColor },
      formatter: (params: any) => {
        const p = params[0]
        return `<b>${p.name}</b><br/>${p.marker} 用电量: <b>${p.value.toFixed(3)} 度</b>`
      }
    },
    grid: {
      left: '8%',
      right: '5%',
      top: '12%',
      bottom: '18%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dailyData.value.map(d => d.dateShort),
      axisLabel: {
        color: textColor,
        rotate: dailyData.value.length > 14 ? 45 : 0,
        fontSize: 11
      },
      axisLine: { lineStyle: { color: axisLineColor } }
    },
    yAxis: {
      type: 'value',
      name: '度',
      nameTextStyle: { color: textColor, fontSize: 11 },
      axisLabel: { color: textColor },
      splitLine: { lineStyle: { color: axisLineColor, type: 'dashed' } }
    },
    series: [{
      type: 'bar',
      data: dailyData.value.map(d => d.kwh),
      itemStyle: {
        color: barColor,
        borderRadius: [4, 4, 0, 0]
      },
      emphasis: {
        itemStyle: { color: '#2563EB' }
      },
      barMaxWidth: 40
    }]
  }
})
</script>

<style scoped>
.daily-energy-card {
  padding: 16px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.card-title {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
}
.stats-badge {
  font-size: 0.75rem;
  color: #9CA3AF;
  background: rgba(156, 163, 175, 0.1);
  padding: 2px 8px;
  border-radius: 10px;
}
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.stat-item {
  text-align: center;
  padding: 10px 8px;
  background: rgba(59, 130, 246, 0.05);
  border-radius: 8px;
}
.stat-item.main {
  grid-column: span 1;
  background: rgba(59, 130, 246, 0.1);
}
.stat-item.highlight {
  background: rgba(245, 158, 11, 0.1);
}
.stat-label {
  display: block;
  font-size: 0.75rem;
  color: #9CA3AF;
  margin-bottom: 4px;
}
.stat-value {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1F2937;
}
.stat-value small {
  font-size: 0.75rem;
  font-weight: 400;
  color: #9CA3AF;
}
.stat-value.cost {
  color: #10B981;
}
.stat-value .date {
  font-size: 0.75rem;
  font-weight: 400;
  color: #9CA3AF;
}
.bar-chart {
  height: 240px;
}

:root.dark .stat-value {
  color: #F3F4F6;
}
:root.dark .stat-value small,
:root.dark .stat-value .date {
  color: #9CA3AF;
}
</style>
