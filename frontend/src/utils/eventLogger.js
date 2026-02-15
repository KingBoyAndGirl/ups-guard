/**
 * 前端事件记录工具
 * 用于将前端事件（错误、用户操作、网络问题）记录到后端
 */

/**
 * 记录事件到后端
 * @param {string} eventType - 事件类型 (FRONTEND_ERROR, FRONTEND_USER_ACTION, FRONTEND_NETWORK_ERROR)
 * @param {string} message - 事件消息
 * @param {object} metadata - 额外的元数据
 */
export async function logEvent(eventType, message, metadata = {}) {
  try {
    // 增强元数据
    const enrichedMetadata = {
      ...metadata,
      url: window.location.href,
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString(),
    }

    // 发送到后端（异步，不阻塞UI）
    await fetch('/api/history/events', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        event_type: eventType,
        message,
        metadata: enrichedMetadata,
      }),
    })
  } catch (error) {
    // 静默失败，不影响用户体验
    console.error('Failed to log event:', error)
  }
}

/**
 * 记录用户操作
 * @param {string} action - 操作名称
 * @param {object} details - 操作详情
 */
export function logUserAction(action, details = {}) {
  const message = `用户操作: ${action}`
  logEvent('FRONTEND_USER_ACTION', message, {
    action,
    ...details,
  })
}

/**
 * 记录前端错误
 * @param {Error} error - 错误对象
 * @param {string} context - 错误上下文
 */
export function logError(error, context = '') {
  const message = context 
    ? `前端错误 (${context}): ${error.message}`
    : `前端错误: ${error.message}`
  
  logEvent('FRONTEND_ERROR', message, {
    errorName: error.name,
    errorMessage: error.message,
    errorStack: error.stack,
    context,
  })
}

/**
 * 记录网络错误
 * @param {string} url - 请求URL
 * @param {number} status - HTTP状态码
 * @param {string} statusText - 状态文本
 */
export function logNetworkError(url, status, statusText) {
  const message = `网络请求失败: ${url} (${status} ${statusText})`
  
  logEvent('FRONTEND_NETWORK_ERROR', message, {
    url,
    status,
    statusText,
  })
}

/**
 * 设置全局错误处理器
 * 自动捕获未处理的错误和Promise拒绝
 */
export function setupGlobalErrorHandler() {
  // 捕获同步错误
  window.addEventListener('error', (event) => {
    logError(event.error, 'Global error handler')
  })

  // 捕获Promise拒绝
  window.addEventListener('unhandledrejection', (event) => {
    const error = event.reason instanceof Error 
      ? event.reason 
      : new Error(String(event.reason))
    
    logError(error, 'Unhandled promise rejection')
  })
}
