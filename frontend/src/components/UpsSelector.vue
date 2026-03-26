<template>
  <div v-if="upsList && upsList.length > 1" class="ups-selector">
    <label class="ups-selector-label">UPS 设备：</label>
    <select 
      v-model="selectedUpsId" 
      @change="onUpsChange"
      class="ups-selector-dropdown"
      title="选择 UPS 设备"
    >
      <option 
        v-for="ups in upsList" 
        :key="ups.id" 
        :value="ups.id"
      >
        {{ ups.name || `UPS ${ups.id}` }} ({{ ups.model || 'Unknown' }})
      </option>
    </select>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

// UPS 设备接口
interface UpsDevice {
  id: string
  name?: string
  model?: string
  manufacturer?: string
}

// Props
const props = defineProps<{
  upsList?: UpsDevice[]
  currentUpsId?: string
}>()

// Emits
const emit = defineEmits<{
  (e: 'change', upsId: string): void
}>()

// 当前选中的 UPS ID
const selectedUpsId = ref(props.currentUpsId || (props.upsList && props.upsList.length > 0 ? props.upsList[0].id : ''))

// 监听外部传入的 currentUpsId 变化
watch(() => props.currentUpsId, (newId) => {
  if (newId) {
    selectedUpsId.value = newId
  }
})

// UPS 切换事件
const onUpsChange = () => {
  emit('change', selectedUpsId.value)
}
</script>

<style scoped>
.ups-selector {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: var(--ups-spacing-sm);
  background: var(--ups-bg-secondary);
  border: 1px solid var(--ups-border-color);
  border-radius: var(--ups-radius-md);
  margin-bottom: var(--ups-card-gap);
}

.ups-selector-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--ups-text-primary);
  white-space: nowrap;
}

.ups-selector-dropdown {
  flex: 1;
  padding: 0.5rem 0.75rem;
  background: var(--ups-bg-primary);
  border: 1px solid var(--ups-border-color);
  border-radius: var(--ups-radius-sm);
  color: var(--ups-text-primary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.ups-selector-dropdown:hover {
  border-color: var(--ups-border-hover);
}

.ups-selector-dropdown:focus {
  outline: none;
  border-color: var(--ups-color-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* 深色模式优化 */
[data-theme="dark"] .ups-selector-dropdown {
  background: var(--ups-bg-tertiary);
}

/* 响应式 */
@media (max-width: 768px) {
  .ups-selector {
    flex-direction: column;
    align-items: stretch;
    gap: 0.5rem;
  }
  
  .ups-selector-label {
    text-align: left;
  }
}
</style>
