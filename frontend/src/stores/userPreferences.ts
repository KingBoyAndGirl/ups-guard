/**
 * 用户个性化设置 Store
 * 保存用户的卡片布局顺序等个性化配置
 * 数据持久化到后端数据库
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

// 默认卡片顺序
export const DEFAULT_DASHBOARD_CARDS = {
  col1: ['status', 'shutdown-timeline', 'energy', 'battery-detail', 'voltage-quality', 'events'],
  col2: ['power-metrics', 'load-gauge', 'battery-voltage', 'battery-status', 'environment', 'self-test'],
  col3: ['power-chart', 'device-info', 'battery-life', 'protection-overview', 'status-flags', 'predictions']
}

export const DEFAULT_SETTINGS_CARDS = {
  col1: ['shutdown-policy', 'data-management'],
  col2: ['notifications', 'config-io'],
  col3: ['monitoring', 'hooks'],
  col4: ['ups-config', 'ups-advanced-config', 'security', 'docs']
}

export interface UserPreferences {
  dashboardCardOrder: {
    col1: string[]
    col2: string[]
    col3: string[]
  }
  settingsCardOrder: {
    col1: string[]
    col2: string[]
    col3: string[]
    col4: string[]
  }
}

export const useUserPreferencesStore = defineStore('userPreferences', () => {
  /**
   * Dashboard 卡片顺序
   * @description 仪表板页面各列的卡片排列顺序，col1/col2/col3 分别对应三列
   */
  const dashboardCardOrder = ref<UserPreferences['dashboardCardOrder']>({
    col1: [...DEFAULT_DASHBOARD_CARDS.col1],
    col2: [...DEFAULT_DASHBOARD_CARDS.col2],
    col3: [...DEFAULT_DASHBOARD_CARDS.col3]
  })

  /**
   * Settings 卡片顺序
   * @description 设置页面各列的卡片排列顺序，col1/col2/col3/col4 分别对应四列
   */
  const settingsCardOrder = ref<UserPreferences['settingsCardOrder']>({
    col1: [...DEFAULT_SETTINGS_CARDS.col1],
    col2: [...DEFAULT_SETTINGS_CARDS.col2],
    col3: [...DEFAULT_SETTINGS_CARDS.col3],
    col4: [...DEFAULT_SETTINGS_CARDS.col4]
  })

  /**
   * 加载中状态
   * @description 表示是否正在从服务器加载用户偏好设置
   */
  const loading = ref(false)

  /**
   * 已加载状态
   * @description 表示用户偏好设置是否已从服务器成功加载
   */
  const loaded = ref(false)

  // 从后端加载
  const loadFromServer = async () => {
    if (loading.value) return
    loading.value = true

    try {
      const response = await axios.get('/api/preferences')
      const data = response.data

      if (data.dashboardCardOrder) {
        // 合并用户偏好和默认卡片，确保新添加的卡片不会丢失
        dashboardCardOrder.value = mergeDashboardCards(data.dashboardCardOrder)
      }

      if (data.settingsCardOrder) {
        // Settings 页面也需要合并
        settingsCardOrder.value = mergeSettingsCards(data.settingsCardOrder)
      }

      loaded.value = true
    } catch (error) {
      console.error('Failed to load user preferences:', error)
      // 使用默认值
    } finally {
      loading.value = false
    }
  }

  // 合并 Dashboard 卡片：保留用户排序，添加缺失的新卡片
  const mergeDashboardCards = (savedOrder: { col1?: string[], col2?: string[], col3?: string[] }) => {
    const result = {
      col1: savedOrder.col1 || [...DEFAULT_DASHBOARD_CARDS.col1],
      col2: savedOrder.col2 || [...DEFAULT_DASHBOARD_CARDS.col2],
      col3: savedOrder.col3 || [...DEFAULT_DASHBOARD_CARDS.col3]
    }

    // 获取所有已保存的卡片 ID
    const savedCardIds = new Set([...result.col1, ...result.col2, ...result.col3])

    // 获取所有默认卡片 ID
    const allDefaultCards = [
      ...DEFAULT_DASHBOARD_CARDS.col1,
      ...DEFAULT_DASHBOARD_CARDS.col2,
      ...DEFAULT_DASHBOARD_CARDS.col3
    ]

    // 找出缺失的卡片（新添加的卡片）
    const missingCards: string[] = []
    for (const cardId of allDefaultCards) {
      if (!savedCardIds.has(cardId)) {
        missingCards.push(cardId)
      }
    }

    // 将缺失的卡片添加到对应的默认列
    for (const cardId of missingCards) {
      if (DEFAULT_DASHBOARD_CARDS.col1.includes(cardId)) {
        result.col1.push(cardId)
      } else if (DEFAULT_DASHBOARD_CARDS.col2.includes(cardId)) {
        result.col2.push(cardId)
      } else if (DEFAULT_DASHBOARD_CARDS.col3.includes(cardId)) {
        result.col3.push(cardId)
      }
    }

    return result
  }

  // 合并 Settings 卡片
  const mergeSettingsCards = (savedOrder: { col1?: string[], col2?: string[], col3?: string[], col4?: string[] }) => {
    const result = {
      col1: savedOrder.col1 || [...DEFAULT_SETTINGS_CARDS.col1],
      col2: savedOrder.col2 || [...DEFAULT_SETTINGS_CARDS.col2],
      col3: savedOrder.col3 || [...DEFAULT_SETTINGS_CARDS.col3],
      col4: savedOrder.col4 || [...DEFAULT_SETTINGS_CARDS.col4]
    }

    const savedCardIds = new Set([...result.col1, ...result.col2, ...result.col3, ...result.col4])
    const allDefaultCards = [
      ...DEFAULT_SETTINGS_CARDS.col1,
      ...DEFAULT_SETTINGS_CARDS.col2,
      ...DEFAULT_SETTINGS_CARDS.col3,
      ...DEFAULT_SETTINGS_CARDS.col4
    ]

    for (const cardId of allDefaultCards) {
      if (!savedCardIds.has(cardId)) {
        if (DEFAULT_SETTINGS_CARDS.col1.includes(cardId)) {
          result.col1.push(cardId)
        } else if (DEFAULT_SETTINGS_CARDS.col2.includes(cardId)) {
          result.col2.push(cardId)
        } else if (DEFAULT_SETTINGS_CARDS.col3.includes(cardId)) {
          result.col3.push(cardId)
        } else if (DEFAULT_SETTINGS_CARDS.col4.includes(cardId)) {
          result.col4.push(cardId)
        }
      }
    }

    return result
  }

  // 更新 Dashboard 卡片顺序
  const updateDashboardCardOrder = async (col: 'col1' | 'col2' | 'col3', cards: string[]) => {
    dashboardCardOrder.value[col] = cards

    try {
      await axios.post('/api/preferences/card-order', {
        page: 'dashboard',
        col,
        cards
      })
    } catch (error) {
      console.error('Failed to save dashboard card order:', error)
    }
  }

  // 更新 Settings 卡片顺序
  const updateSettingsCardOrder = async (col: 'col1' | 'col2' | 'col3' | 'col4', cards: string[]) => {
    settingsCardOrder.value[col] = cards

    try {
      await axios.post('/api/preferences/card-order', {
        page: 'settings',
        col,
        cards
      })
    } catch (error) {
      console.error('Failed to save settings card order:', error)
    }
  }

  // 移动卡片（跨列）
  const moveDashboardCard = async (
    fromCol: 'col1' | 'col2' | 'col3',
    toCol: 'col1' | 'col2' | 'col3',
    cardId: string,
    toIndex: number
  ) => {
    // 检查卡片是否存在于源列
    const fromCards = dashboardCardOrder.value[fromCol]
    const fromIndex = fromCards.indexOf(cardId)

    // 防止重复添加：检查卡片是否已经在目标列中
    const toCards = dashboardCardOrder.value[toCol]
    const existingInTarget = toCards.indexOf(cardId)

    // 如果卡片在目标列中已存在，先移除
    if (existingInTarget > -1) {
      toCards.splice(existingInTarget, 1)
    }

    // 从源列移除
    if (fromIndex > -1) {
      fromCards.splice(fromIndex, 1)
    }

    // 计算安全的插入索引
    const safeIndex = Math.min(Math.max(0, toIndex), toCards.length)

    // 插入到目标列
    dashboardCardOrder.value[toCol].splice(safeIndex, 0, cardId)

    // 保存到后端
    try {
      await axios.post('/api/preferences/card-move', {
        page: 'dashboard',
        fromCol,
        toCol,
        cardId,
        toIndex: safeIndex
      })
    } catch (error) {
      console.error('Failed to move dashboard card:', error)
    }
  }

  const moveSettingsCard = async (
    fromCol: 'col1' | 'col2' | 'col3' | 'col4',
    toCol: 'col1' | 'col2' | 'col3' | 'col4',
    cardId: string,
    toIndex: number
  ) => {
    // 检查卡片是否存在于源列
    const fromCards = settingsCardOrder.value[fromCol]
    const fromIndex = fromCards.indexOf(cardId)

    // 防止重复添加：检查卡片是否已经在目标列中
    const toCards = settingsCardOrder.value[toCol]
    const existingInTarget = toCards.indexOf(cardId)

    // 如果卡片在目标列中已存在，先移除
    if (existingInTarget > -1) {
      toCards.splice(existingInTarget, 1)
    }

    // 从源列移除
    if (fromIndex > -1) {
      fromCards.splice(fromIndex, 1)
    }

    // 计算安全的插入索引
    const safeIndex = Math.min(Math.max(0, toIndex), toCards.length)

    // 插入到目标列
    settingsCardOrder.value[toCol].splice(safeIndex, 0, cardId)

    // 保存到后端
    try {
      await axios.post('/api/preferences/card-move', {
        page: 'settings',
        fromCol,
        toCol,
        cardId,
        toIndex: safeIndex
      })
    } catch (error) {
      console.error('Failed to move settings card:', error)
    }
  }

  // 重置为默认布局
  const resetDashboardLayout = async () => {
    dashboardCardOrder.value = {
      col1: [...DEFAULT_DASHBOARD_CARDS.col1],
      col2: [...DEFAULT_DASHBOARD_CARDS.col2],
      col3: [...DEFAULT_DASHBOARD_CARDS.col3]
    }

    try {
      await axios.post('/api/preferences/reset?page=dashboard')
    } catch (error) {
      console.error('Failed to reset dashboard layout:', error)
    }
  }

  const resetSettingsLayout = async () => {
    settingsCardOrder.value = {
      col1: [...DEFAULT_SETTINGS_CARDS.col1],
      col2: [...DEFAULT_SETTINGS_CARDS.col2],
      col3: [...DEFAULT_SETTINGS_CARDS.col3],
      col4: [...DEFAULT_SETTINGS_CARDS.col4]
    }

    try {
      await axios.post('/api/preferences/reset?page=settings')
    } catch (error) {
      console.error('Failed to reset settings layout:', error)
    }
  }

  // 初始化时从服务器加载
  loadFromServer()

  return {
    dashboardCardOrder,
    settingsCardOrder,
    loading,
    loaded,
    loadFromServer,
    updateDashboardCardOrder,
    updateSettingsCardOrder,
    moveDashboardCard,
    moveSettingsCard,
    resetDashboardLayout,
    resetSettingsLayout
  }
})
