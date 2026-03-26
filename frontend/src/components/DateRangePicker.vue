<template>
  <div class="date-range-picker" ref="pickerRef">
    <div class="date-range-input" @click="togglePicker">
      <input
        type="text"
        :value="displayValue"
        readonly
        :placeholder="placeholder || '选择日期范围'"
        class="form-control"
      />
      <span class="datetime-icon">📅</span>
    </div>

    <div v-if="showPicker" class="date-range-dropdown">
      <!-- 双日历头部 -->
      <div class="calendars-container">
        <!-- 左侧日历（开始日期） -->
        <div class="calendar-panel">
          <div class="calendar-header">
            <button class="nav-btn" @click="prevMonth('start')">&lt;</button>
            <span class="current-month" @click="showStartYearMonth = !showStartYearMonth">
              {{ startYear }}年{{ startMonth + 1 }}月
            </span>
            <button class="nav-btn" @click="nextMonth('start')">&gt;</button>
          </div>

          <!-- 年月选择器 -->
          <div v-if="showStartYearMonth" class="year-month-selector">
            <div class="year-selector">
              <button class="nav-btn" @click="startYear--">&lt;</button>
              <span>{{ startYear }}年</span>
              <button class="nav-btn" @click="startYear++">&gt;</button>
            </div>
            <div class="month-grid">
              <button
                v-for="m in 12"
                :key="m"
                class="month-btn"
                :class="{ active: startMonth === m - 1 }"
                @click="selectStartMonth(m - 1)"
              >
                {{ m }}月
              </button>
            </div>
          </div>

          <div v-else class="calendar">
            <div class="weekdays">
              <span v-for="day in weekDays" :key="day">{{ day }}</span>
            </div>
            <div class="days">
              <button
                v-for="(day, index) in startCalendarDays"
                :key="index"
                class="day-btn"
                :class="getDayClass(day)"
                :disabled="day.disabled"
                @click="selectDate(day)"
                @dblclick="selectDateAndConfirm(day)"
              >
                {{ day.date }}
              </button>
            </div>
          </div>
        </div>

        <!-- 右侧日历（结束日期） -->
        <div class="calendar-panel">
          <div class="calendar-header">
            <button class="nav-btn" @click="prevMonth('end')">&lt;</button>
            <span class="current-month" @click="showEndYearMonth = !showEndYearMonth">
              {{ endYear }}年{{ endMonth + 1 }}月
            </span>
            <button class="nav-btn" @click="nextMonth('end')">&gt;</button>
          </div>

          <!-- 年月选择器 -->
          <div v-if="showEndYearMonth" class="year-month-selector">
            <div class="year-selector">
              <button class="nav-btn" @click="endYear--">&lt;</button>
              <span>{{ endYear }}年</span>
              <button class="nav-btn" @click="endYear++">&gt;</button>
            </div>
            <div class="month-grid">
              <button
                v-for="m in 12"
                :key="m"
                class="month-btn"
                :class="{ active: endMonth === m - 1 }"
                @click="selectEndMonth(m - 1)"
              >
                {{ m }}月
              </button>
            </div>
          </div>

          <div v-else class="calendar">
            <div class="weekdays">
              <span v-for="day in weekDays" :key="day">{{ day }}</span>
            </div>
            <div class="days">
              <button
                v-for="(day, index) in endCalendarDays"
                :key="index"
                class="day-btn"
                :class="getDayClass(day)"
                :disabled="day.disabled"
                @click="selectDate(day)"
                @dblclick="selectDateAndConfirm(day)"
              >
                {{ day.date }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 时间选择 -->
      <div class="time-selectors">
        <div class="time-group">
          <label>开始时间：</label>
          <select v-model="startHour" class="time-select">
            <option v-for="h in 24" :key="h - 1" :value="h - 1">
              {{ String(h - 1).padStart(2, '0') }}
            </option>
          </select>
          <span>:</span>
          <select v-model="startMinute" class="time-select">
            <option v-for="m in 60" :key="m - 1" :value="m - 1">
              {{ String(m - 1).padStart(2, '0') }}
            </option>
          </select>
        </div>
        <div class="time-group">
          <label>结束时间：</label>
          <select v-model="endHour" class="time-select">
            <option v-for="h in 24" :key="h - 1" :value="h - 1">
              {{ String(h - 1).padStart(2, '0') }}
            </option>
          </select>
          <span>:</span>
          <select v-model="endMinute" class="time-select">
            <option v-for="m in 60" :key="m - 1" :value="m - 1">
              {{ String(m - 1).padStart(2, '0') }}
            </option>
          </select>
        </div>
      </div>

      <!-- 快捷选项和操作按钮 -->
      <div class="picker-footer">
        <div class="quick-ranges">
          <button class="quick-btn" @click="setQuickRange(5/60)">5分钟</button>
          <button class="quick-btn" @click="setQuickRange(1)">1小时</button>
          <button class="quick-btn" @click="setQuickRange(24)">24小时</button>
          <button class="quick-btn" @click="setQuickRange(24*7)">7天</button>
        </div>
        <div class="action-buttons">
          <button class="btn btn-sm btn-secondary" @click="showPicker = false">取消</button>
          <button class="btn btn-sm btn-primary" @click="confirmSelection">确定</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps<{
  startDate: string
  endDate: string
  placeholder?: string
  maxDays?: number
}>()

const emit = defineEmits<{
  (e: 'update:startDate', value: string): void
  (e: 'update:endDate', value: string): void
}>()

const pickerRef = ref<HTMLElement>()
const showPicker = ref(false)
const showStartYearMonth = ref(false)
const showEndYearMonth = ref(false)

// 选择状态：'start' 或 'end'
const selectingTarget = ref<'start' | 'end'>('start')

// 日历显示的年月
const startYear = ref(new Date().getFullYear())
const startMonth = ref(new Date().getMonth())
const endYear = ref(new Date().getFullYear())
const endMonth = ref(new Date().getMonth())

// 选中的日期
const selectedStartDate = ref<Date | null>(null)
const selectedEndDate = ref<Date | null>(null)

// 时间
const startHour = ref(0)
const startMinute = ref(0)
const endHour = ref(23)
const endMinute = ref(59)

const weekDays = ['日', '一', '二', '三', '四', '五', '六']

// 解析传入的值
const parseValues = () => {
  if (props.startDate) {
    const date = new Date(props.startDate)
    if (!isNaN(date.getTime())) {
      selectedStartDate.value = date
      startYear.value = date.getFullYear()
      startMonth.value = date.getMonth()
      startHour.value = date.getHours()
      startMinute.value = date.getMinutes()
    }
  }
  if (props.endDate) {
    const date = new Date(props.endDate)
    if (!isNaN(date.getTime())) {
      selectedEndDate.value = date
      endYear.value = date.getFullYear()
      endMonth.value = date.getMonth()
      endHour.value = date.getHours()
      endMinute.value = date.getMinutes()
    }
  }
}

// 显示值
const displayValue = computed(() => {
  if (!props.startDate || !props.endDate) return ''

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    if (isNaN(date.getTime())) return ''
    const y = date.getFullYear()
    const m = String(date.getMonth() + 1).padStart(2, '0')
    const d = String(date.getDate()).padStart(2, '0')
    const h = String(date.getHours()).padStart(2, '0')
    const min = String(date.getMinutes()).padStart(2, '0')
    return `${y}-${m}-${d} ${h}:${min}`
  }

  return `${formatDate(props.startDate)} 至 ${formatDate(props.endDate)}`
})

// 生成日历天数
const generateCalendarDays = (year: number, month: number) => {
  const days: Array<{
    date: number
    fullDate: Date
    otherMonth: boolean
    isToday: boolean
    disabled: boolean
  }> = []

  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  const startDayOfWeek = firstDay.getDay()

  const today = new Date()
  today.setHours(0, 0, 0, 0)

  // 上月的天数
  const prevMonthLastDay = new Date(year, month, 0).getDate()
  for (let i = startDayOfWeek - 1; i >= 0; i--) {
    const date = new Date(year, month - 1, prevMonthLastDay - i)
    days.push({
      date: prevMonthLastDay - i,
      fullDate: date,
      otherMonth: true,
      isToday: false,
      disabled: false
    })
  }

  // 当月的天数
  for (let i = 1; i <= lastDay.getDate(); i++) {
    const date = new Date(year, month, i)
    date.setHours(0, 0, 0, 0)
    days.push({
      date: i,
      fullDate: date,
      otherMonth: false,
      isToday: date.getTime() === today.getTime(),
      disabled: false
    })
  }

  // 下月的天数（补齐6行）
  const remainingDays = 42 - days.length
  for (let i = 1; i <= remainingDays; i++) {
    const date = new Date(year, month + 1, i)
    days.push({
      date: i,
      fullDate: date,
      otherMonth: true,
      isToday: false,
      disabled: false
    })
  }

  return days
}

const startCalendarDays = computed(() => generateCalendarDays(startYear.value, startMonth.value))
const endCalendarDays = computed(() => generateCalendarDays(endYear.value, endMonth.value))

// 获取日期样式类
const getDayClass = (day: { fullDate: Date; otherMonth: boolean; isToday: boolean; disabled: boolean }) => {
  const classes: string[] = []

  if (day.otherMonth) classes.push('other-month')
  if (day.isToday) classes.push('today')
  if (day.disabled) classes.push('disabled')

  const dayTime = day.fullDate.getTime()
  const hasRange = selectedStartDate.value && selectedEndDate.value

  // 检查是否是开始日期
  if (selectedStartDate.value) {
    const startTime = new Date(selectedStartDate.value)
    startTime.setHours(0, 0, 0, 0)
    if (dayTime === startTime.getTime()) {
      classes.push('range-start')
      // 如果有范围（开始和结束日期都有），添加 has-range 类
      if (hasRange) {
        classes.push('has-range')
      }
    }
  }

  // 检查是否是结束日期
  if (selectedEndDate.value) {
    const endTime = new Date(selectedEndDate.value)
    endTime.setHours(0, 0, 0, 0)
    if (dayTime === endTime.getTime()) {
      classes.push('range-end')
    }
  }

  // 检查是否在范围内
  if (hasRange) {
    const startTime = new Date(selectedStartDate.value!)
    startTime.setHours(0, 0, 0, 0)
    const endTime = new Date(selectedEndDate.value!)
    endTime.setHours(0, 0, 0, 0)

    if (dayTime > startTime.getTime() && dayTime < endTime.getTime()) {
      classes.push('in-range')
    }
  }

  return classes
}

const togglePicker = () => {
  showPicker.value = !showPicker.value
  if (showPicker.value) {
    parseValues()
    showStartYearMonth.value = false
    showEndYearMonth.value = false
    selectingTarget.value = 'start'
  }
}

const prevMonth = (panel: 'start' | 'end') => {
  if (panel === 'start') {
    if (startMonth.value === 0) {
      startMonth.value = 11
      startYear.value--
    } else {
      startMonth.value--
    }
  } else {
    if (endMonth.value === 0) {
      endMonth.value = 11
      endYear.value--
    } else {
      endMonth.value--
    }
  }
}

const nextMonth = (panel: 'start' | 'end') => {
  if (panel === 'start') {
    if (startMonth.value === 11) {
      startMonth.value = 0
      startYear.value++
    } else {
      startMonth.value++
    }
  } else {
    if (endMonth.value === 11) {
      endMonth.value = 0
      endYear.value++
    } else {
      endMonth.value++
    }
  }
}

const selectStartMonth = (month: number) => {
  startMonth.value = month
  showStartYearMonth.value = false
}

const selectEndMonth = (month: number) => {
  endMonth.value = month
  showEndYearMonth.value = false
}

const selectDate = (day: { fullDate: Date; disabled: boolean }) => {
  if (day.disabled) return

  // 智能选择逻辑
  if (!selectedStartDate.value || (selectedStartDate.value && selectedEndDate.value)) {
    // 如果没有开始日期，或者两个日期都已选择，重新开始选择
    selectedStartDate.value = day.fullDate
    selectedEndDate.value = null
    selectingTarget.value = 'end'
  } else if (!selectedEndDate.value) {
    // 已有开始日期，选择结束日期
    if (day.fullDate >= selectedStartDate.value) {
      selectedEndDate.value = day.fullDate
    } else {
      // 如果选择的日期比开始日期早，交换
      selectedEndDate.value = selectedStartDate.value
      selectedStartDate.value = day.fullDate
    }
    selectingTarget.value = 'start'
  }
}

// 双击日期：选择并确认
const selectDateAndConfirm = (day: { fullDate: Date; disabled: boolean }) => {
  if (day.disabled) return
  selectDate(day)
  // 如果两个日期都已选择，确认
  if (selectedStartDate.value && selectedEndDate.value) {
    confirmSelection()
  }
}

// 快捷范围选择
const setQuickRange = (hours: number) => {
  const now = new Date()
  const start = new Date(now.getTime() - hours * 60 * 60 * 1000)

  selectedStartDate.value = start
  selectedEndDate.value = now
  startHour.value = start.getHours()
  startMinute.value = start.getMinutes()
  endHour.value = now.getHours()
  endMinute.value = now.getMinutes()

  // 更新日历显示
  startYear.value = start.getFullYear()
  startMonth.value = start.getMonth()
  endYear.value = now.getFullYear()
  endMonth.value = now.getMonth()

  confirmSelection()
}

const confirmSelection = () => {
  if (selectedStartDate.value && selectedEndDate.value) {
    const formatDateTime = (date: Date, hour: number, minute: number) => {
      const y = date.getFullYear()
      const m = String(date.getMonth() + 1).padStart(2, '0')
      const d = String(date.getDate()).padStart(2, '0')
      const h = String(hour).padStart(2, '0')
      const min = String(minute).padStart(2, '0')
      return `${y}-${m}-${d}T${h}:${min}`
    }

    emit('update:startDate', formatDateTime(selectedStartDate.value, startHour.value, startMinute.value))
    emit('update:endDate', formatDateTime(selectedEndDate.value, endHour.value, endMinute.value))
  }
  showPicker.value = false
}

// 点击外部关闭
const handleClickOutside = (event: MouseEvent) => {
  if (pickerRef.value && !pickerRef.value.contains(event.target as Node)) {
    showPicker.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  parseValues()
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

watch([() => props.startDate, () => props.endDate], () => {
  parseValues()
})
</script>

<style scoped>
.date-range-picker {
  position: relative;
  width: 100%;
}

.date-range-input {
  position: relative;
  cursor: pointer;
}

.date-range-input input {
  cursor: pointer;
  padding-right: 2.5rem;
}

.datetime-icon {
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
}

.date-range-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 1000;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  padding: 0.75rem;
  margin-top: 0.25rem;
}

.calendars-container {
  display: flex;
  gap: 1rem;
}

.calendar-panel {
  min-width: 240px;
}

.calendar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.nav-btn {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 0.25rem 0.5rem;
  cursor: pointer;
  color: var(--text-primary);
}

.nav-btn:hover {
  background: var(--bg-tertiary);
}

.current-month {
  font-weight: 600;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
}

.current-month:hover {
  background: var(--bg-secondary);
}

.year-month-selector {
  padding: 0.5rem 0;
}

.year-selector {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.month-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.25rem;
}

.month-btn {
  padding: 0.375rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  cursor: pointer;
  color: var(--text-primary);
  font-size: 0.8125rem;
}

.month-btn:hover {
  background: var(--bg-secondary);
}

.month-btn.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.calendar .weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-bottom: 0.25rem;
}

.calendar .days {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 1px;
}

.day-btn {
  aspect-ratio: 1;
  border: none;
  background: transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.8125rem;
  color: var(--text-primary);
  transition: all 0.15s;
}

.day-btn:hover:not(.disabled) {
  background: var(--bg-secondary);
}

.day-btn.other-month {
  color: var(--text-tertiary);
}

.day-btn.today {
  border: 1px solid var(--color-primary);
}

/* 开始日期 - 绿色 */
.day-btn.range-start {
  background: #a2c3fb;
  color: chocolate;
  border-radius: var(--radius-sm);
}

/* 开始日期有范围时的圆角 */
.day-btn.range-start.has-range {
  border-radius: var(--radius-sm) 0 0 var(--radius-sm);
}

/* 结束日期 - 蓝色 */
.day-btn.range-end {
  background: var(--color-primary);
  color: chocolate;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

/* 开始和结束是同一天 */
.day-btn.range-start.range-end {
  background: linear-gradient(135deg, #a2c3fb 50%, var(--color-primary) 50%);
  border-radius: var(--radius-sm);
}

.day-btn.in-range {
  background: rgba(59, 130, 246, 0.15);
  border-radius: 0;
}

.day-btn.disabled {
  color: var(--text-tertiary);
  cursor: not-allowed;
  opacity: 0.5;
}

.time-selectors {
  display: flex;
  gap: 1.5rem;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border-color);
}

.time-group {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.time-group label {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  white-space: nowrap;
}

.time-select {
  padding: 0.25rem 0.375rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 0.8125rem;
}

.picker-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border-color);
}

.quick-ranges {
  display: flex;
  gap: 0.375rem;
}

.quick-btn {
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  color: var(--text-secondary);
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.15s;
}

.quick-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
}

.btn-sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.8125rem;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.btn-secondary {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.btn-primary {
  background: var(--color-primary);
  color: white;
}

/* 响应式：移动端堆叠显示 */
@media (max-width: 560px) {
  .calendars-container {
    flex-direction: column;
  }

  .time-selectors {
    flex-direction: column;
    gap: 0.5rem;
  }

  .picker-footer {
    flex-direction: column;
    gap: 0.75rem;
  }

  .quick-ranges {
    width: 100%;
    justify-content: center;
  }

  .action-buttons {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>

