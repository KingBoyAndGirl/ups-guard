<template>
  <div class="battery-gauge card">
    <div class="gauge-header">
      <span class="gauge-label">电池电量</span>
      <span class="gauge-value">{{ charge }}%</span>
    </div>
    <div class="gauge-bar">
      <div 
        class="gauge-fill" 
        :style="{ 
          width: `${charge}%`,
          backgroundColor: getColor(charge)
        }"
      />
    </div>
    <div v-if="runtime !== null" class="gauge-runtime">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
      <span>剩余约 {{ formatRuntime(runtime) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  charge: number
  runtime: number | null
}>()

const getColor = (charge: number): string => {
  if (charge > 50) return '#10B981'
  if (charge > 20) return '#F59E0B'
  return '#EF4444'
}

const formatRuntime = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  
  if (hours > 0) {
    return `${hours} 小时 ${minutes} 分钟`
  }
  return `${minutes} 分钟`
}
</script>

<style scoped>
.battery-gauge {
  padding: 1.5rem;
}

.gauge-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.gauge-label {
  font-size: 1rem;
  font-weight: 500;
  color: var(--text-primary);
}

.gauge-value {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
}

.gauge-bar {
  width: 100%;
  height: 2rem;
  background: var(--bg-tertiary);
  border-radius: 9999px;
  overflow: hidden;
  position: relative;
}

.gauge-fill {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.3s ease, background-color 0.3s ease;
}

.gauge-runtime {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.gauge-runtime svg {
  width: 1rem;
  height: 1rem;
  stroke-width: 2;
}
</style>
