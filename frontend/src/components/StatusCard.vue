<template>
  <div class="status-card card">
    <div class="status-icon" :style="{ backgroundColor: iconColor }">
      <svg v-if="icon === 'power'" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <path d="M13 2L3 14h8l-2 8 10-12h-8l2-8z" />
      </svg>
      <svg v-else-if="icon === 'battery'" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <rect x="1" y="6" width="18" height="12" rx="2" ry="2" />
        <line x1="23" y1="10" x2="23" y2="14" />
      </svg>
      <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <circle cx="12" cy="12" r="10" />
      </svg>
    </div>
    <div class="status-content">
      <div class="status-label">{{ label }}</div>
      <div class="status-value">{{ value }}</div>
      <div v-if="subtitle" class="status-subtitle">{{ subtitle }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  subtitle?: string
  icon?: 'power' | 'battery' | 'default'
  iconColor?: string
}>()
</script>

<style scoped>
.status-card {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.status-icon {
  width: 3rem;
  height: 3rem;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.status-icon svg {
  width: 1.5rem;
  height: 1.5rem;
  color: white;
  stroke-width: 2;
}

.status-content {
  flex: 1;
}

.status-label {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-bottom: 0.25rem;
}

.status-value {
  font-size: 1.875rem;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
}

.status-subtitle {
  font-size: 0.75rem;
  color: var(--text-tertiary);
  margin-top: 0.25rem;
}
</style>
