/**
 * UPS 状态管理
 */
import { ref } from 'vue'
import axios from 'axios'
import type { UpsData } from '@/types/ups'

export function useUpsStatus() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const data = ref<UpsData | null>(null)
  
  const fetchStatus = async () => {
    loading.value = true
    error.value = null
    
    try {
      const response = await axios.get('/api/status')
      data.value = response.data
    } catch (e: any) {
      error.value = e.message || '获取状态失败'
      console.error('Failed to fetch UPS status:', e)
    } finally {
      loading.value = false
    }
  }
  
  const getStatusText = (status: string): string => {
    const statusMap: Record<string, string> = {
      'ONLINE': '市电供电',
      'ON_BATTERY': '电池供电',
      'LOW_BATTERY': '低电量',
      'SHUTTING_DOWN': '正在关机',
      'POWER_OFF': '已关机',
      'OFFLINE': '离线'
    }
    return statusMap[status] || status
  }
  
  const getStatusColor = (status: string): string => {
    const colorMap: Record<string, string> = {
      'ONLINE': '#10B981',      // 绿色
      'ON_BATTERY': '#F59E0B',  // 黄色
      'LOW_BATTERY': '#EF4444', // 红色
      'SHUTTING_DOWN': '#EF4444',
      'POWER_OFF': '#6B7280',
      'OFFLINE': '#9CA3AF'      // 灰色
    }
    return colorMap[status] || '#9CA3AF'
  }
  
  return {
    loading,
    error,
    data,
    fetchStatus,
    getStatusText,
    getStatusColor
  }
}
