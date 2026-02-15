/**
 * UPS 状态 Store
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { UpsData } from '@/types/ups'

export const useUpsStore = defineStore('ups', () => {
  const currentData = ref<UpsData | null>(null)
  
  const updateData = (data: UpsData) => {
    currentData.value = data
  }
  
  return {
    currentData,
    updateData
  }
})
