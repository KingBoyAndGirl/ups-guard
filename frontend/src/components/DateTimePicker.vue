<template>
  <div class="datetime-picker" ref="pickerRef">
    <div class="datetime-input" @click="togglePicker">
      <input
        type="text"
        :value="displayValue"
        readonly
        :placeholder="placeholder"
        class="form-control"
      />
      <span class="datetime-icon">📅</span>
    </div>

    <div v-if="showPicker" class="datetime-dropdown">
      <div class="datetime-header">
        <button class="nav-btn" @click="prevMonth">&lt;</button>
        <span class="current-month" @click="showYearMonthSelector = !showYearMonthSelector">
          {{ currentYear }}年{{ currentMonth + 1 }}月
        </span>
        <button class="nav-btn" @click="nextMonth">&gt;</button>
      </div>

      <!-- 年月选择器 -->
      <div v-if="showYearMonthSelector" class="year-month-selector">
        <div class="year-selector">
          <button class="nav-btn" @click="currentYear--">&lt;</button>
          <span>{{ currentYear }}年</span>
          <button class="nav-btn" @click="currentYear++">&gt;</button>
        </div>
        <div class="month-grid">
          <button
            v-for="m in 12"
            :key="m"
            class="month-btn"
            :class="{ active: currentMonth === m - 1 }"
            @click="selectMonth(m - 1)"
          >
            {{ m }}月
          </button>
        </div>
      </div>

      <!-- 日历 -->
      <div v-else class="calendar">
        <div class="weekdays">
          <span v-for="day in weekDays" :key="day">{{ day }}</span>
        </div>
        <div class="days">
          <button
            v-for="(day, index) in calendarDays"
            :key="index"
            class="day-btn"
            :class="{
              'other-month': day.otherMonth,
              'today': day.isToday,
              'selected': day.isSelected,
              'disabled': day.disabled
            }"
            :disabled="day.disabled"
            @click="selectDate(day)"
            @dblclick="selectDateAndConfirm(day)"
          >
            {{ day.date }}
          </button>
        </div>
      </div>

      <!-- 时间选择 -->
      <div class="time-selector">
        <label>时间：</label>
        <select v-model="selectedHour" class="time-select">
          <option v-for="h in 24" :key="h - 1" :value="h - 1">
            {{ String(h - 1).padStart(2, '0') }}
          </option>
        </select>
        <span>:</span>
        <select v-model="selectedMinute" class="time-select">
          <option v-for="m in 60" :key="m - 1" :value="m - 1">
            {{ String(m - 1).padStart(2, '0') }}
          </option>
        </select>
      </div>

      <!-- 快捷操作 -->
      <div class="datetime-actions">
        <button class="btn btn-sm btn-secondary" @click="setNow">现在</button>
        <button class="btn btn-sm btn-primary" @click="confirmSelection">确定</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps<{
  modelValue: string
  placeholder?: string
  min?: string
  max?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const pickerRef = ref<HTMLElement>()
const showPicker = ref(false)
const showYearMonthSelector = ref(false)

const currentYear = ref(new Date().getFullYear())
const currentMonth = ref(new Date().getMonth())
const selectedDate = ref<Date | null>(null)
const selectedHour = ref(0)
const selectedMinute = ref(0)

const weekDays = ['日', '一', '二', '三', '四', '五', '六']

// 解析当前值
const parseValue = () => {
  if (props.modelValue) {
    const date = new Date(props.modelValue)
    if (!isNaN(date.getTime())) {
      selectedDate.value = date
      currentYear.value = date.getFullYear()
      currentMonth.value = date.getMonth()
      selectedHour.value = date.getHours()
      selectedMinute.value = date.getMinutes()
    }
  }
}

// 显示值
const displayValue = computed(() => {
  if (!props.modelValue) return ''
  const date = new Date(props.modelValue)
  if (isNaN(date.getTime())) return ''

  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')

  return `${year}-${month}-${day} ${hours}:${minutes}`
})

// 日历天数
const calendarDays = computed(() => {
  const days: Array<{
    date: number
    fullDate: Date
    otherMonth: boolean
    isToday: boolean
    isSelected: boolean
    disabled: boolean
  }> = []

  const firstDay = new Date(currentYear.value, currentMonth.value, 1)
  const lastDay = new Date(currentYear.value, currentMonth.value + 1, 0)
  const startDayOfWeek = firstDay.getDay()

  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const minDate = props.min ? new Date(props.min) : null
  const maxDate = props.max ? new Date(props.max) : null

  // 上月的天数
  const prevMonthLastDay = new Date(currentYear.value, currentMonth.value, 0).getDate()
  for (let i = startDayOfWeek - 1; i >= 0; i--) {
    const date = new Date(currentYear.value, currentMonth.value - 1, prevMonthLastDay - i)
    days.push({
      date: prevMonthLastDay - i,
      fullDate: date,
      otherMonth: true,
      isToday: false,
      isSelected: false,
      disabled: isDateDisabled(date, minDate, maxDate)
    })
  }

  // 当月的天数
  for (let i = 1; i <= lastDay.getDate(); i++) {
    const date = new Date(currentYear.value, currentMonth.value, i)
    date.setHours(0, 0, 0, 0)

    const isSelected = selectedDate.value &&
      date.getFullYear() === selectedDate.value.getFullYear() &&
      date.getMonth() === selectedDate.value.getMonth() &&
      date.getDate() === selectedDate.value.getDate()

    days.push({
      date: i,
      fullDate: date,
      otherMonth: false,
      isToday: date.getTime() === today.getTime(),
      isSelected: !!isSelected,
      disabled: isDateDisabled(date, minDate, maxDate)
    })
  }

  // 下月的天数（补齐6行）
  const remainingDays = 42 - days.length
  for (let i = 1; i <= remainingDays; i++) {
    const date = new Date(currentYear.value, currentMonth.value + 1, i)
    days.push({
      date: i,
      fullDate: date,
      otherMonth: true,
      isToday: false,
      isSelected: false,
      disabled: isDateDisabled(date, minDate, maxDate)
    })
  }

  return days
})

const isDateDisabled = (date: Date, minDate: Date | null, maxDate: Date | null): boolean => {
  if (minDate) {
    const min = new Date(minDate)
    min.setHours(0, 0, 0, 0)
    if (date < min) return true
  }
  if (maxDate) {
    const max = new Date(maxDate)
    max.setHours(23, 59, 59, 999)
    if (date > max) return true
  }
  return false
}

const togglePicker = () => {
  showPicker.value = !showPicker.value
  if (showPicker.value) {
    parseValue()
    showYearMonthSelector.value = false
  }
}

const prevMonth = () => {
  if (currentMonth.value === 0) {
    currentMonth.value = 11
    currentYear.value--
  } else {
    currentMonth.value--
  }
}

const nextMonth = () => {
  if (currentMonth.value === 11) {
    currentMonth.value = 0
    currentYear.value++
  } else {
    currentMonth.value++
  }
}

const selectMonth = (month: number) => {
  currentMonth.value = month
  showYearMonthSelector.value = false
}

const selectDate = (day: { fullDate: Date; disabled: boolean }) => {
  if (day.disabled) return
  selectedDate.value = day.fullDate
}

// 双击日期：选择并确认
const selectDateAndConfirm = (day: { fullDate: Date; disabled: boolean }) => {
  if (day.disabled) return
  selectedDate.value = day.fullDate
  confirmSelection()
}

const setNow = () => {
  const now = new Date()
  selectedDate.value = now
  selectedHour.value = now.getHours()
  selectedMinute.value = now.getMinutes()
  currentYear.value = now.getFullYear()
  currentMonth.value = now.getMonth()
}

const confirmSelection = () => {
  if (selectedDate.value) {
    const date = new Date(selectedDate.value)
    date.setHours(selectedHour.value, selectedMinute.value, 0, 0)

    // 格式化为 datetime-local 格式
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')

    emit('update:modelValue', `${year}-${month}-${day}T${hours}:${minutes}`)
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
  parseValue()
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

watch(() => props.modelValue, () => {
  parseValue()
})
</script>

<style scoped>
.datetime-picker {
  position: relative;
  width: 100%;
}

.datetime-input {
  position: relative;
  cursor: pointer;
}

.datetime-input input {
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

.datetime-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 1000;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  padding: 0.75rem;
  min-width: 280px;
  margin-top: 0.25rem;
}

.datetime-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
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
  gap: 0.5rem;
}

.month-btn {
  padding: 0.5rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  cursor: pointer;
  color: var(--text-primary);
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
  margin-bottom: 0.5rem;
}

.calendar .days {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}

.day-btn {
  aspect-ratio: 1;
  border: none;
  background: transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--text-primary);
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

.day-btn.selected {
  background: var(--color-primary);
  color: white;
}

.day-btn.disabled {
  color: var(--text-tertiary);
  cursor: not-allowed;
  opacity: 0.5;
}

.time-selector {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border-color);
}

.time-selector label {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.time-select {
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 0.875rem;
}

.datetime-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border-color);
}

.btn-sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.8125rem;
}
</style>

