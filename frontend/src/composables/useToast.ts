import { reactive } from 'vue'

export interface Toast {
  id: number
  type: 'success' | 'error' | 'warning' | 'info'
  title?: string
  message: string
  duration: number
}

interface ToastState {
  toasts: Toast[]
  nextId: number
}

export const toastState = reactive<ToastState>({
  toasts: [],
  nextId: 1
})

export function removeToast(id: number) {
  const index = toastState.toasts.findIndex(t => t.id === id)
  if (index > -1) {
    toastState.toasts.splice(index, 1)
  }
}

export function useToast() {
  const showToast = (
    type: Toast['type'],
    message: string,
    title?: string,
    duration?: number
  ) => {
    // Default duration: success/info 3s, error 5s, warning 4s
    const defaultDuration = type === 'error' ? 5000 : type === 'warning' ? 4000 : 3000
    const actualDuration = duration !== undefined ? duration : defaultDuration

    const toast: Toast = {
      id: toastState.nextId++,
      type,
      title,
      message,
      duration: actualDuration
    }

    toastState.toasts.push(toast)

    // Auto remove after duration
    if (actualDuration > 0) {
      setTimeout(() => {
        removeToast(toast.id)
      }, actualDuration)
    }
  }

  const success = (message: string, title?: string, duration?: number) => {
    showToast('success', message, title, duration)
  }

  const error = (message: string, title?: string, duration?: number) => {
    showToast('error', message, title, duration)
  }

  const warning = (message: string, title?: string, duration?: number) => {
    showToast('warning', message, title, duration)
  }

  const info = (message: string, title?: string, duration?: number) => {
    showToast('info', message, title, duration)
  }

  return {
    success,
    error,
    warning,
    info
  }
}
