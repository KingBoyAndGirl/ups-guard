/**
 * 卡片拖拽排序 Composable
 * 提供类似手机桌面的拖拽排序功能
 */
import { computed, reactive } from 'vue'

export interface DragState {
  isDragging: boolean
  draggedCardId: string | null
  sourceCol: string | null
  targetCol: string | null
  targetIndex: number
}

export function useDraggableCards<T extends string>(
  getColumns: () => Record<T, string[]>,
  onOrderChange: (col: T, cards: string[]) => void,
  onCardMove?: (fromCol: T, toCol: T, cardId: string, toIndex: number) => void
) {
  const dragState = reactive<DragState>({
    isDragging: false,
    draggedCardId: null,
    sourceCol: null,
    targetCol: null,
    targetIndex: -1
  })

  // 当前是否正在拖拽
  const isDragging = computed(() => dragState.isDragging)

  // 开始拖拽
  const handleDragStart = (e: DragEvent, cardId: string, col: T) => {
    if (!e.dataTransfer) return

    dragState.isDragging = true
    dragState.draggedCardId = cardId
    dragState.sourceCol = col
    dragState.targetCol = null
    dragState.targetIndex = -1

    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', JSON.stringify({ cardId, col }))

    // 添加拖拽样式
    const target = e.target as HTMLElement
    setTimeout(() => {
      target.classList.add('dragging')
    }, 0)
  }

  // 拖拽经过
  const handleDragOver = (e: DragEvent, col: T, index: number) => {
    e.preventDefault()
    if (!e.dataTransfer) return

    e.dataTransfer.dropEffect = 'move'
    dragState.targetCol = col
    dragState.targetIndex = index
  }

  // 拖拽进入列
  const handleDragEnterCol = (e: DragEvent, col: T) => {
    e.preventDefault()
    dragState.targetCol = col
  }

  // 拖拽离开列
  const handleDragLeaveCol = (e: DragEvent) => {
    // 只在真正离开列时重置
    const relatedTarget = e.relatedTarget as HTMLElement
    if (!relatedTarget?.closest('.droppable-col')) {
      dragState.targetCol = null
    }
  }

  // 放置
  const handleDrop = (e: DragEvent, col: T) => {
    e.preventDefault()

    const { draggedCardId, sourceCol, targetCol, targetIndex: stateTargetIndex } = dragState
    if (!draggedCardId || !sourceCol) {
      resetDragState()
      return
    }

    // 优先使用 dragState 记录的目标列（由 dragover 事件设置），否则使用 drop 事件的列
    const actualTargetCol = (targetCol as T) || col
    const columns = getColumns()
    // 使用 dragState 中记录的目标位置
    const targetIndex = stateTargetIndex >= 0 ? stateTargetIndex : columns[actualTargetCol]?.length || 0

    if (sourceCol === actualTargetCol) {
      // 同列内排序
      const cards = [...(columns[actualTargetCol] || [])]
      const fromIndex = cards.indexOf(draggedCardId)
      if (fromIndex > -1 && fromIndex !== targetIndex) {
        cards.splice(fromIndex, 1)
        // 计算正确的插入位置：如果从前往后移动，需要减1
        const insertIndex = fromIndex < targetIndex ? targetIndex - 1 : targetIndex
        cards.splice(Math.max(0, insertIndex), 0, draggedCardId)
        onOrderChange(actualTargetCol, cards)
      }
    } else if (onCardMove) {
      // 跨列移动
      onCardMove(sourceCol as T, actualTargetCol, draggedCardId, targetIndex)
    }

    resetDragState()
  }

  // 拖拽结束
  const handleDragEnd = (e: DragEvent) => {
    const target = e.target as HTMLElement
    target.classList.remove('dragging')
    resetDragState()
  }

  // 重置拖拽状态
  const resetDragState = () => {
    dragState.isDragging = false
    dragState.draggedCardId = null
    dragState.sourceCol = null
    dragState.targetCol = null
    dragState.targetIndex = -1
  }

  // 判断是否为拖拽目标位置
  const isDropTarget = (col: T, index: number) => {
    return dragState.isDragging &&
           dragState.targetCol === col &&
           dragState.targetIndex === index
  }

  // 判断列是否为拖拽目标
  const isColDropTarget = (col: T) => {
    return dragState.isDragging && dragState.targetCol === col
  }

  // 获取卡片在指定列中的排序后位置
  const getCardOrder = (col: T, cardId: string): number => {
    const columns = getColumns()
    const cards = columns[col] || []
    return cards.indexOf(cardId)
  }

  // 判断卡片是否在指定列中
  const isCardInCol = (col: T, cardId: string): boolean => {
    const columns = getColumns()
    return (columns[col] || []).includes(cardId)
  }

  return {
    dragState,
    isDragging,
    handleDragStart,
    handleDragOver,
    handleDragEnterCol,
    handleDragLeaveCol,
    handleDrop,
    handleDragEnd,
    isDropTarget,
    isColDropTarget,
    getCardOrder,
    isCardInCol,
    resetDragState
  }
}