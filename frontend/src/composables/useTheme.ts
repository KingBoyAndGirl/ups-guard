/**
 * 主题管理 Composable
 * 支持亮色、暗色和跟随系统三种模式
 */
import { ref, computed, watch, onMounted } from 'vue'

export type ThemeMode = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'ups-guard-theme'

// 全局状态
const theme = ref<ThemeMode>('system')
let initialized = false

// 检测系统主题偏好
const getSystemTheme = (): 'light' | 'dark' => {
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark'
  }
  return 'light'
}

// 计算实际应用的主题
const effectiveTheme = computed<'light' | 'dark'>(() => {
  if (theme.value === 'system') {
    return getSystemTheme()
  }
  return theme.value
})

// 应用主题到 DOM
const applyTheme = (themeValue: 'light' | 'dark') => {
  const html = document.documentElement
  if (themeValue === 'dark') {
    html.setAttribute('data-theme', 'dark')
  } else {
    html.removeAttribute('data-theme')
  }
}

// 保存到 localStorage
const saveTheme = (themeValue: ThemeMode) => {
  try {
    localStorage.setItem(STORAGE_KEY, themeValue)
  } catch (e) {
    console.warn('Failed to save theme to localStorage:', e)
  }
}

// 从 localStorage 加载
const loadTheme = (): ThemeMode => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'light' || saved === 'dark' || saved === 'system') {
      return saved
    }
  } catch (e) {
    console.warn('Failed to load theme from localStorage:', e)
  }
  return 'system'
}

// 初始化主题（立即执行，避免闪烁）
const initTheme = () => {
  if (!initialized) {
    theme.value = loadTheme()
    applyTheme(effectiveTheme.value)
    initialized = true
  }
}

// 切换主题
const toggleTheme = () => {
  const modes: ThemeMode[] = ['light', 'dark', 'system']
  const currentIndex = modes.indexOf(theme.value)
  const nextIndex = (currentIndex + 1) % modes.length
  setTheme(modes[nextIndex])
}

// 设置主题
const setTheme = (newTheme: ThemeMode) => {
  theme.value = newTheme
  saveTheme(newTheme)
}

// 主题名称（用于显示）
const themeName = computed(() => {
  const names: Record<ThemeMode, string> = {
    light: '亮色',
    dark: '暗色',
    system: '跟随系统'
  }
  return names[theme.value]
})

// 主题图标
const themeIcon = computed(() => {
  if (theme.value === 'system') {
    return '💻'
  }
  return effectiveTheme.value === 'dark' ? '🌙' : '☀️'
})

// 立即初始化（模块加载时）
initTheme()

export const useTheme = () => {
  // 监听主题变化
  watch(effectiveTheme, (newTheme) => {
    applyTheme(newTheme)
  })
  
  // 设置系统主题变化监听
  onMounted(() => {
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      const listener = () => {
        if (theme.value === 'system') {
          applyTheme(effectiveTheme.value)
        }
      }
      
      // 现代浏览器使用 addEventListener
      if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener('change', listener)
      } else {
        // 旧版浏览器使用 addListener
        mediaQuery.addListener(listener)
      }
    }
  })
  
  return {
    theme,
    effectiveTheme,
    themeName,
    themeIcon,
    toggleTheme,
    setTheme
  }
}
