<template>
  <div class="settings">
    <!-- 布局重置按钮 -->
    <button
      class="layout-reset-btn"
      @click="resetSettingsLayout"
      title="重置卡片布局为默认"
    >
      🔄 重置布局
    </button>

    <!-- 四列网格布局 -->
    <div class="settings-grid">
      <!-- 使用 v-for 遍历所有列 -->
      <template v-for="colKey in (['col1', 'col2', 'col3', 'col4'] as const)" :key="colKey">
        <div
          :class="['settings-col', `settings-col-${colKey.slice(-1)}`, 'droppable-col', { 'drag-over': dragState.targetCol === colKey }]"
          @dragover.prevent="(e) => handleColDragOver(e, colKey)"
          @drop="(e) => handleDrop(e, colKey)"
        >
          <!-- 遍历当前列的卡片 -->
          <template v-for="(cardId, cardIndex) in userPrefs.settingsCardOrder[colKey]" :key="cardId">

            <!-- 关机策略卡片 -->
            <div
              v-if="cardId === 'shutdown-policy'"
              class="card settings-shutdown-policy draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'shutdown-policy' }"
              :style="{ order: cardIndex }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'shutdown-policy', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title">关机策略</h3>
              <p class="help-text" style="margin-bottom: 1rem;">
                断电后，如果续航时间充足，系统会等待指定时间再关机；如果续航时间不足，则立即关机。</p>

              <div class="form-group">
                <label class="form-label">
                  停电后等待时间（分钟）
                  <span class="help-icon" title="续航时间充足时，等待市电恢复的最长时间">ℹ️</span>
                </label>
                <input
                    v-model.number="config.shutdown_wait_minutes"
                    type="number"
                    min="1"
                    max="60"
                    class="form-control"
                    :class="{ 'error': errors.shutdown_wait_minutes }"
                />
                <span v-if="errors.shutdown_wait_minutes" class="error-text">{{ errors.shutdown_wait_minutes }}</span>
                <small class="help-text">续航时间充足时的最长等待时间</small>
              </div>

              <div class="form-group">
                <label class="form-label">
                  最低电量百分比（%）
                  <span class="help-icon" title="低于此值时发送低电量警告（不影响关机时机）">ℹ️</span>
                </label>
                <input
                    v-model.number="config.shutdown_battery_percent"
                    type="number"
                    min="5"
                    max="50"
                    class="form-control"
                    :class="{ 'error': errors.shutdown_battery_percent }"
                />
                <span v-if="errors.shutdown_battery_percent" class="error-text">{{ errors.shutdown_battery_percent }}</span>
                <small class="help-text">低于此值时发送低电量警告通知</small>
              </div>

              <div class="form-group">
                <label class="form-label">
                  预计续航阈值（分钟）
                  <span class="help-icon" title="UPS 预计续航时间低于此值时立即触发关机（跳过等待时间）">ℹ️</span>
                </label>
                <input
                    v-model.number="config.estimated_runtime_threshold"
                    type="number"
                    min="1"
                    max="30"
                    class="form-control"
                    :class="{ 'error': errors.estimated_runtime_threshold }"
                />
                <span v-if="errors.estimated_runtime_threshold" class="error-text">{{
                    errors.estimated_runtime_threshold
                  }}</span>
                <small class="help-text">低于此值时立即进入关机倒计时，不等待上方设置的等待时间</small>
              </div>

              <div class="form-group">
                <label class="form-label">
                  最终等待时间（秒）
                  <span class="help-icon" title="确认关机前的最后等待窗口">ℹ️</span>
                </label>
                <input
                    v-model.number="config.shutdown_final_wait_seconds"
                    type="number"
                    min="10"
                    max="120"
                    class="form-control"
                    :class="{ 'error': errors.shutdown_final_wait_seconds }"
                />
                <span v-if="errors.shutdown_final_wait_seconds" class="error-text">{{
                    errors.shutdown_final_wait_seconds
                  }}</span>
                <small class="help-text">建议：30-60 秒</small>
              </div>
            </div>

            <!-- 数据管理卡片 -->
            <div
              v-else-if="cardId === 'data-management'"
              class="card settings-data draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'data-management', 'is-drop-target': dragState.targetCol === colKey && dragState.targetIndex === cardIndex }"
              :style="{ order: cardIndex }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'data-management', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title">数据管理</h3>

              <!-- 数据统计 -->
              <div v-if="storageInfo" class="storage-info">
                <div class="storage-item">
                  <span class="storage-label">数据库大小：</span>
                  <span class="storage-value">{{ storageInfo.db_size_mb }} MB</span>
                </div>
                <div class="storage-item">
                  <span class="storage-label">事件记录：</span>
                  <span class="storage-value">{{ storageInfo.event_count }} 条</span>
                </div>
                <div class="storage-item">
                  <span class="storage-label">指标记录：</span>
                  <span class="storage-value">{{ storageInfo.metric_count }} 条</span>
                </div>
              </div>

              <!-- 数据保留设置 -->
              <div class="form-group" style="margin-top: 0.75rem;">
                <label class="form-label">历史数据保留天数</label>
                <input
                    v-model.number="config.history_retention_days"
                    type="number"
                    min="1"
                    max="90"
                    class="form-control"
                    :class="{ 'error': errors.history_retention_days }"
                />
              </div>

              <!-- 手动清理 -->
              <div class="form-group">
                <button
                    class="btn btn-sm btn-danger"
                    @click="showCleanupConfirm = true"
                    :disabled="cleaningUp"
                >
                  {{ cleaningUp ? '清理中...' : '🗑️ 清空数据' }}
                </button>
              </div>

              <!-- 清理确认对话框 -->
              <div v-if="showCleanupConfirm" class="modal-overlay"
                   @click.self="!cleaningUp && (showCleanupConfirm = false)">
                <div class="modal-dialog" @click.stop>
                  <h3>⚠️ 确认清空数据</h3>
                  <p>确定要删除<strong>所有</strong>历史数据吗？包括：</p>
                  <ul class="help-text">
                    <li>事件记录</li>
                    <li>指标采样</li>
                    <li>电池测试报告</li>
                    <li>监控统计</li>
                  </ul>
                  <p class="help-text warning-text">此操作不可撤销！</p>
                  <div class="modal-actions">
                    <button class="btn btn-secondary" @click="showCleanupConfirm = false" :disabled="cleaningUp">取消
                    </button>
                    <button
                        class="btn btn-danger"
                        @click="cleanupAllHistory"
                        :disabled="cleaningUp"
                    >
                      {{ cleaningUp ? '清理中...' : '确认清空' }}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 通知设置卡片 -->
            <div
              v-else-if="cardId === 'notifications'"
              class="card settings-notifications draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'notifications' }"
              :style="{ order: cardIndex }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'notifications', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title">通知设置</h3>

              <!-- 通知总开关 -->
              <div class="notification-header">
                <div class="notification-toggle">
                  <label class="switch">
                    <input type="checkbox" v-model="config.notification_enabled"/>
                    <span class="slider"></span>
                  </label>
                  <span class="toggle-label">{{ config.notification_enabled ? '通知已启用' : '通知已禁用' }}</span>
                </div>
                <div class="notification-status" v-if="config.notification_enabled">
                  <span class="status-dot" :class="{ 'active': config.notify_channels.filter(c => c.enabled).length > 0 }"></span>
                  <span class="status-text">{{ config.notify_channels.filter(c => c.enabled).length }} 个渠道已启用</span>
                </div>
              </div>

              <p class="help-text">配置推送通知渠道，在关键事件发生时接收通知。</p>

              <!-- 已配置的通知渠道列表 -->
              <div class="notify-channels">
                <div v-if="config.notify_channels.length === 0" class="empty-state">暂未配置通知渠道</div>
                <div v-for="(channel, index) in config.notify_channels" :key="index" class="notify-channel-item" :class="{ 'channel-disabled': !channel.enabled, 'channel-error': channelErrors[index] }">
                  <div class="channel-left">
                    <label class="switch switch-sm">
                      <input type="checkbox" v-model="channel.enabled"/>
                      <span class="slider"></span>
                    </label>
                    <div class="channel-info">
                      <div class="channel-name-row">
                        <span class="channel-name">{{ channel.name || getPluginName(channel.plugin_id) }}</span>
                        <span class="channel-type-badge">{{ getPluginName(channel.plugin_id) }}</span>
                      </div>
                      <div class="channel-status-row">
                        <span v-if="channelErrors[index]" class="channel-error-msg">❌ {{ channelErrors[index] }}</span>
                        <span v-else-if="!channel.enabled" class="channel-status-text disabled">已禁用</span>
                        <span v-else class="channel-status-text ok">✓ 正常</span>
                      </div>
                    </div>
                  </div>
                  <div class="channel-actions">
                    <button class="btn-icon" @click="testChannel(channel, index)" :disabled="testingChannelIndex === index || !channel.enabled" :title="testingChannelIndex === index ? '测试中...' : '测试发送'">{{ testingChannelIndex === index ? '⏳' : '▶️' }}</button>
                    <button class="btn-icon" @click="editChannel(index)" :disabled="testingChannelIndex !== -1" title="编辑">✏️</button>
                    <button class="btn-icon btn-icon-danger" @click="removeChannel(index)" :disabled="testingChannelIndex !== -1" title="删除">🗑️</button>
                  </div>
                </div>
              </div>

              <!-- 添加新渠道 -->
              <div class="add-channel">
                <label class="form-label">添加通知渠道</label>
                <div class="add-channel-row">
                  <select v-model="selectedPlugin" class="form-control">
                    <option value="">-- 选择通知类型 --</option>
                    <option v-for="plugin in availablePlugins" :key="plugin.id" :value="plugin.id">{{ plugin.name }}</option>
                  </select>
                  <button class="btn btn-secondary" @click="addChannel" :disabled="!selectedPlugin">添加</button>
                </div>
              </div>

              <!-- 通知事件选择 -->
              <div class="form-group" style="margin-top: 1.5rem;">
                <label class="form-label">通知事件类型</label>
                <div class="info-box" style="margin-bottom: 1rem;">
                  <strong>💡 提示：</strong>勾选您想要接收通知的事件类型。未勾选的事件仅会记录到事件日志中，不会发送通知到渠道。
                </div>
                <div class="event-section">
                  <div class="event-section-title">UPS 事件</div>
                  <div class="checkbox-group">
                    <label class="checkbox-label"><input type="checkbox" value="POWER_LOST" v-model="config.notify_events"/>断电</label>
                    <label class="checkbox-label"><input type="checkbox" value="POWER_RESTORED" v-model="config.notify_events"/>恢复供电</label>
                    <label class="checkbox-label"><input type="checkbox" value="LOW_BATTERY" v-model="config.notify_events"/>低电量</label>
                    <label class="checkbox-label"><input type="checkbox" value="SHUTDOWN" v-model="config.notify_events"/>系统关机</label>
                    <label class="checkbox-label"><input type="checkbox" value="SHUTDOWN_CANCELLED" v-model="config.notify_events"/>取消关机</label>
                  </div>
                </div>
                <div class="event-section">
                  <div class="event-section-title">设备操作事件</div>
                  <div class="checkbox-group">
                    <label class="checkbox-label"><input type="checkbox" value="DEVICE_SHUTDOWN" v-model="config.notify_events"/>🔌 设备关机</label>
                    <label class="checkbox-label"><input type="checkbox" value="DEVICE_WAKE" v-model="config.notify_events"/>⏻ 设备唤醒(WOL)</label>
                    <label class="checkbox-label"><input type="checkbox" value="DEVICE_REBOOT" v-model="config.notify_events"/>🔄 设备重启</label>
                    <label class="checkbox-label"><input type="checkbox" value="DEVICE_SLEEP" v-model="config.notify_events"/>😴 设备睡眠</label>
                    <label class="checkbox-label"><input type="checkbox" value="DEVICE_HIBERNATE" v-model="config.notify_events"/>💤 设备休眠</label>
                    <label class="checkbox-label"><input type="checkbox" value="DEVICE_TEST_CONNECTION" v-model="config.notify_events"/>🔍 设备连接测试</label>
                  </div>
                </div>
              </div>

              <div v-if="notificationTestResult" class="test-result" :class="notificationTestResult.success ? 'success' : 'error'">{{ notificationTestResult.message }}</div>
            </div>

            <!-- 配置导入/导出卡片 -->
            <div
              v-else-if="cardId === 'config-io'"
              class="card settings-config-io draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'config-io' }"
              :style="{ order: cardIndex }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'config-io', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title">配置导入/导出</h3>
              <div class="config-io-section">
                <div class="form-group">
                  <button class="btn btn-sm btn-primary" @click="exportConfig" :disabled="exporting">{{ exporting ? '导出中...' : '📥 导出配置' }}</button>
                </div>
                <div class="form-group">
                  <input ref="importFileInput" type="file" accept=".json" @change="handleImportFile" style="display: none"/>
                  <button class="btn btn-sm btn-secondary" @click="triggerFileInput" :disabled="importing || validating || comparing">{{ importing ? '导入中...' : validating ? '验证中...' : '📤 导入配置' }}</button>
                  <div v-if="importPreview" class="import-preview">
                    <h4>配置预览</h4>
                    <div class="preview-info">
                      <div class="preview-item"><span class="preview-label">配置项数：</span><span class="preview-value">{{ importPreview.field_count }}</span></div>
                    </div>
                    <div class="import-mode-select">
                      <label class="form-label">导入模式：</label>
                      <div class="radio-group">
                        <label class="radio-label"><input type="radio" v-model="importMode" value="merge"/><span>合并</span></label>
                        <label class="radio-label"><input type="radio" v-model="importMode" value="replace"/><span>替换</span></label>
                      </div>
                    </div>
                    <div class="import-actions">
                      <button class="btn btn-sm btn-secondary" @click="cancelImport">取消</button>
                      <button class="btn btn-sm btn-secondary" @click="showConfigComparison" :disabled="comparing">{{ comparing ? '比较中...' : '🔍 差异' }}</button>
                      <button class="btn btn-sm btn-primary" @click="confirmImport" :disabled="importing">{{ importing ? '导入中...' : '确认' }}</button>
                    </div>
                    <div v-if="importResult" class="import-result" :class="{ 'success': importResult.success, 'error': !importResult.success }">{{ importResult.message }}</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 监控参数卡片 -->
            <div
              v-else-if="cardId === 'monitoring'"
              class="card settings-monitoring draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'monitoring' }"
              :style="{ order: cardIndex }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'monitoring', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title">监控参数</h3>
              <div class="form-group">
                <label class="form-label">NUT 轮询间隔（秒）<span class="help-icon" title="从 NUT 服务器读取 UPS 状态的频率">ℹ️</span></label>
                <input v-model.number="config.poll_interval_seconds" type="number" min="1" max="60" class="form-control" :class="{ 'error': errors.poll_interval_seconds }"/>
                <span v-if="errors.poll_interval_seconds" class="error-text">{{ errors.poll_interval_seconds }}</span>
                <small class="help-text">建议：3-10 秒</small>
              </div>
              <div class="form-group">
                <label class="form-label">指标采样间隔（秒）<span class="help-icon" title="记录 UPS 电量、电压等指标到数据库的频率">ℹ️</span></label>
                <input v-model.number="config.sample_interval_seconds" type="number" min="10" max="3600" class="form-control" :class="{ 'error': errors.sample_interval_seconds }"/>
                <span v-if="errors.sample_interval_seconds" class="error-text">{{ errors.sample_interval_seconds }}</span>
                <small class="help-text">建议：30-120 秒</small>
              </div>
              <div class="form-group">
                <label class="form-label">设备状态刷新间隔（秒）<span class="help-icon" title="纳管设备状态自动刷新的间隔时间">ℹ️</span></label>
                <input v-model.number="config.device_status_check_interval_seconds" type="number" min="0" max="600" class="form-control" :class="{ 'error': errors.device_status_check_interval_seconds }"/>
                <span v-if="errors.device_status_check_interval_seconds" class="error-text">{{ errors.device_status_check_interval_seconds }}</span>
                <small class="help-text">建议：30-120 秒，设为 0 禁用自动刷新</small>
              </div>
              
              <hr class="section-divider" />
              
              <!-- 监控模式配置 -->
              <h4 class="subsection-title">📡 监控模式</h4>
              <div class="form-group">
                <label class="form-label">监控模式<span class="help-icon" title="选择 UPS 状态监控方式">ℹ️</span></label>
                <select v-model="config.monitoring_mode" class="form-control">
                  <option value="polling">轮询模式（传统）</option>
                  <option value="event_driven">事件驱动（实时）</option>
                  <option value="hybrid">混合模式（推荐）</option>
                </select>
                <small class="help-text">混合模式：事件驱动 + 低频轮询，兼具实时性和稳定性</small>
              </div>
              
              <div class="form-group">
                <label class="switch-label">
                  <input type="checkbox" v-model="config.event_driven_enabled" class="form-checkbox"/>
                  <span>启用事件驱动</span>
                </label>
                <small class="help-text">尝试使用 NUT LISTEN 命令实现实时状态更新</small>
              </div>
              
              <div class="form-group">
                <label class="form-label">心跳间隔（秒）<span class="help-icon" title="保持事件驱动连接活跃的心跳频率">ℹ️</span></label>
                <input v-model.number="config.event_driven_heartbeat" type="number" min="10" max="120" class="form-control"/>
                <small class="help-text">建议：20-60 秒</small>
              </div>
              
              <div class="form-group">
                <label class="switch-label">
                  <input type="checkbox" v-model="config.event_driven_fallback" class="form-checkbox"/>
                  <span>自动降级</span>
                </label>
                <small class="help-text">事件驱动失败时自动切换到轮询模式</small>
              </div>
              
              <div class="form-group">
                <label class="form-label">降级轮询间隔（秒）<span class="help-icon" title="事件驱动失败后的轮询间隔">ℹ️</span></label>
                <input v-model.number="config.poll_interval_fallback" type="number" min="30" max="300" class="form-control"/>
                <small class="help-text">建议：60-120 秒</small>
              </div>
              
              <hr class="section-divider" />
              
              <!-- 监控统计信息 -->
              <h4 class="subsection-title">📊 监控统计</h4>
              <div class="monitoring-stats" v-if="monitoringStats">
                <div class="stat-item">
                  <div class="stat-label">当前模式</div>
                  <div class="stat-value">{{ monitoringStats.current_mode || '加载中...' }}</div>
                </div>
                <div class="stat-item">
                  <div class="stat-label">今日通信次数</div>
                  <div class="stat-value">{{ monitoringStats.today_communications || 0 }}</div>
                </div>
                <div class="stat-item">
                  <div class="stat-label">事件驱动状态</div>
                  <div class="stat-value">
                    <span :class="monitoringStats.event_mode_active ? 'status-ok' : 'status-warning'">
                      {{ monitoringStats.event_mode_active ? '✅ 活跃' : '⚠️ 未激活' }}
                    </span>
                  </div>
                </div>
                <div class="stat-item">
                  <div class="stat-label">最后更新</div>
                  <div class="stat-value">{{ formatLastUpdate(monitoringStats.last_update) }}</div>
                </div>
              </div>
              <div v-else class="monitoring-stats-loading">
                <span>加载统计信息中...</span>
              </div>
            </div>

            <!-- 关机前置任务卡片 -->
            <div
              v-else-if="cardId === 'hooks'"
              class="card settings-hooks draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'hooks' }"
              :style="{ order: cardIndex }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'hooks', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title">关机前置任务</h3>
              <p class="help-text">在宿主关机之前，按优先级依次关闭其他设备</p>
              <div class="pre-shutdown-hooks">
                <div v-if="config.pre_shutdown_hooks.length === 0" class="empty-state">暂未配置关机前置任务</div>
                <div v-for="(hook, index) in config.pre_shutdown_hooks" :key="index" class="hook-item" :class="{ 'hook-disabled': !hook.enabled }">
                  <div class="hook-left">
                    <label class="switch switch-sm"><input type="checkbox" v-model="hook.enabled"/><span class="slider"></span></label>
                    <div class="hook-info">
                      <div class="hook-name-row">
                        <span class="hook-name">{{ hook.name }}</span>
                        <span class="hook-type-badge">{{ getHookPluginName(hook.hook_id) }}</span>
                        <span class="hook-priority-badge">优先级 {{ hook.priority }}</span>
                      </div>
                      <div class="hook-status-row">
                        <span v-if="!hook.enabled" class="hook-status-text disabled">已禁用</span>
                        <span v-else class="hook-status-text ok">✓ 启用 (超时: {{ hook.timeout }}s)</span>
                      </div>
                    </div>
                  </div>
                  <div class="hook-actions">
                    <button class="btn-icon" @click="testHook(hook, index)" :disabled="testingHookIndex === index || !hook.enabled">{{ testingHookIndex === index ? '⏳' : '▶️' }}</button>
                    <button class="btn-icon" @click="editHook(index)" :disabled="testingHookIndex !== -1">✏️</button>
                    <button class="btn-icon btn-icon-danger" @click="removeHook(index)" :disabled="testingHookIndex !== -1">🗑️</button>
                  </div>
                </div>
              </div>
              <div class="add-hook">
                <label class="form-label">添加关机前置任务</label>
                <div class="add-hook-row">
                  <select v-model="selectedHookPlugin" class="form-control">
                    <option value="">-- 选择任务类型 --</option>
                    <option v-for="plugin in availableHookPlugins" :key="plugin.id" :value="plugin.id">{{ plugin.name }}</option>
                  </select>
                  <button class="btn btn-secondary" @click="addHook" :disabled="!selectedHookPlugin">添加</button>
                </div>
              </div>
              <div v-if="hookTestResult" class="test-result" :class="hookTestResult.success ? 'success' : 'error'">{{ hookTestResult.message }}</div>
            </div>

            <!-- 系统配置卡片 -->
            <div
              v-else-if="cardId === 'ups-config'"
              class="card settings-system draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'ups-config' }"
              :style="{ order: cardIndex }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'ups-config', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title">系统配置</h3>
              <div class="form-group">
                <label class="form-label"><span class="label-text">测试模式</span></label>
                <select v-model="config.test_mode" class="form-control" @change="onTestModeChange">
                  <option value="production">生产模式（Production）</option>
                  <option value="dry_run">演练模式（Dry-Run）</option>
                  <option value="mock">完全模拟（Mock）</option>
                </select>
                <small class="help-text"><strong>生产模式</strong>：正常运行；<strong>演练模式</strong>：执行流程但不关机；<strong>完全模拟</strong>：不连接 UPS</small>
              </div>
              <div class="form-group">
                <label class="form-label"><span class="label-text">宿主关机方式</span></label>
                <select v-model="config.shutdown_method" class="form-control">
                  <option value="system_command">系统命令（System Command）- 推荐</option>
                  <option value="mock">测试模式（Mock）</option>
                </select>
              </div>
              <div class="form-group">
                <label class="checkbox-label"><input v-model="config.wol_on_power_restore" type="checkbox" class="checkbox-input"/><span class="checkbox-text">来电后自动唤醒（Wake On LAN）</span></label>
                <small class="help-text">市电恢复后自动向配置了 MAC 地址的设备发送 WOL 魔术包</small>
              </div>
              <div class="form-group" v-if="config.wol_on_power_restore">
                <label class="form-label"><span class="label-text">WOL 延迟时间（秒）</span></label>
                <input v-model.number="config.wol_delay_seconds" type="number" min="0" max="600" class="form-control" :class="{ 'error': errors.wol_delay_seconds }"/>
                <span v-if="errors.wol_delay_seconds" class="error-text">{{ errors.wol_delay_seconds }}</span>
                <small class="help-text">建议 60-120 秒</small>
              </div>
            </div>

            <!-- UPS 高级配置卡片 -->
            <div
              v-else-if="cardId === 'ups-advanced-config'"
              class="card settings-ups-advanced draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'ups-advanced-config' }"
              :style="{ order: cardIndex }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'ups-advanced-config', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title">🔧 UPS 高级配置</h3>
              <p class="help-text" style="margin-bottom: 1rem;">直接修改 UPS 硬件参数，修改后自动保存</p>
              <div class="ups-advanced-section">
                <h4 class="section-title">⚡ 电压保护配置</h4>
                <div class="form-group">
                  <label class="form-label">高压切换阈值（V）</label>
                  <div class="value-comparison">
                    <div class="current-value"><span class="label">当前值：</span><span class="value">{{ currentVoltageHigh || '-' }}</span></div>
                    <div class="default-value"><span class="label">默认值：</span><span class="value">{{ UPS_PARAM_DEFAULTS['input.transfer.high'] }} V</span></div>
                    <input v-model.number="newVoltageHigh" type="number" :min="VOLTAGE_LIMITS.HIGH_MIN" :max="VOLTAGE_LIMITS.HIGH_MAX" class="form-control" :placeholder="`${VOLTAGE_LIMITS.HIGH_MIN}-${VOLTAGE_LIMITS.HIGH_MAX}`" @change="onVoltageChange"/>
                  </div>
                </div>
                <div class="form-group">
                  <label class="form-label">低压切换阈值（V）</label>
                  <div class="value-comparison">
                    <div class="current-value"><span class="label">当前值：</span><span class="value">{{ currentVoltageLow || '-' }}</span></div>
                    <div class="default-value"><span class="label">默认值：</span><span class="value">{{ UPS_PARAM_DEFAULTS['input.transfer.low'] }} V</span></div>
                    <input v-model.number="newVoltageLow" type="number" :min="VOLTAGE_LIMITS.LOW_MIN" :max="VOLTAGE_LIMITS.LOW_MAX" class="form-control" :placeholder="`${VOLTAGE_LIMITS.LOW_MIN}-${VOLTAGE_LIMITS.LOW_MAX}`" @change="onVoltageChange"/>
                  </div>
                </div>
                <div v-if="savingVoltage" class="saving-indicator">保存中...</div>
              </div>
              <div class="ups-advanced-section">
                <h4 class="section-title">🎚️ 灵敏度配置</h4>
                <div class="form-group">
                  <label class="form-label">输入灵敏度</label>
                  <div class="current-value" style="margin-bottom: 0.5rem;"><span class="label">当前值：</span><span class="value">{{ currentSensitivity || '-' }}</span></div>
                  <div class="default-value" style="margin-bottom: 0.5rem;"><span class="label">默认值：</span><span class="value">{{ UPS_PARAM_DEFAULTS['input.sensitivity'] }} (Low - UPS出厂值)</span></div>
                  <select v-model="newSensitivity" class="form-control" @change="onSensitivityChange">
                    <option value="">-- 选择灵敏度 --</option>
                    <option value="low">低 (Low) - APC出厂默认</option>
                    <option value="medium">中 (Medium)</option>
                    <option value="high">高 (High)</option>
                  </select>
                </div>
                <div v-if="savingSensitivity" class="saving-indicator">保存中...</div>
              </div>
              <div class="ups-advanced-section">
                <h4 class="section-title">⏱️ 关机延迟配置</h4>
                <div class="form-group">
                  <label class="form-label">关机延迟时间（秒）</label>
                  <div class="value-comparison">
                    <div class="current-value"><span class="label">当前值：</span><span class="value">{{ currentShutdownDelay || '-' }}</span></div>
                    <div class="default-value"><span class="label">默认值：</span><span class="value">{{ UPS_PARAM_DEFAULTS['ups.delay.shutdown'] }} 秒</span></div>
                    <input v-model.number="newShutdownDelay" type="number" :min="SHUTDOWN_DELAY_LIMITS.MIN" :max="SHUTDOWN_DELAY_LIMITS.MAX" class="form-control" @change="onShutdownDelayChange"/>
                  </div>
                </div>
                <div v-if="savingShutdownDelay" class="saving-indicator">保存中...</div>
              </div>
              <div class="ups-advanced-section">
                <h4 class="section-title">📋 所有可写变量</h4>
                <div v-if="loadingWritableVars" class="loading-text">加载中...</div>
                <div v-else-if="writableVarsError" class="error-text">{{ writableVarsError }}</div>
                <div v-else-if="writableVars && Object.keys(writableVars).length > 0" class="writable-vars-table">
                  <table class="data-table">
                    <thead><tr><th>变量名</th><th>当前值</th><th>可配置</th></tr></thead>
                    <tbody>
                      <tr v-for="(varInfo, varName) in writableVars" :key="varName">
                        <td>
                          <code :title="varInfo.description || varName">{{ varName }}</code>
                          <div v-if="varInfo.description" class="var-description">{{ varInfo.description }}</div>
                        </td>
                        <td>{{ varInfo.value || '-' }}</td>
                        <td><span v-if="varInfo.configurable" class="badge badge-success">可通过界面修改</span><span v-else class="badge badge-warning">仅命令行可修改</span></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <button class="btn btn-secondary" @click="loadWritableVars" :disabled="loadingWritableVars" style="margin-top: 1rem;">{{ loadingWritableVars ? '刷新中...' : '🔄 刷新列表' }}</button>
              </div>
            </div>

            <!-- 诊断工具卡片 -->
            <div
              v-else-if="cardId === 'security'"
              class="card settings-diagnostics draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'security' }"
              :style="{ order: cardIndex }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'security', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title">🔧 诊断工具</h3>
              <p class="help-text" style="margin-bottom: 1rem;">导出系统诊断报告，包含系统信息、UPS 状态、完整配置、最近事件等。报告已自动脱敏。</p>
              <button class="btn btn-secondary" @click="downloadDiagnostics" :disabled="exportingDiagnostics">{{ exportingDiagnostics ? '导出中...' : '📥 导出诊断报告' }}</button>
            </div>

            <!-- 帮助文档卡片 -->
            <div
              v-else-if="cardId === 'docs'"
              class="card settings-docs draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'docs' }"
              :style="{ order: cardIndex }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'docs', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title">📚 帮助</h3>
              <div class="docs-links">
                <a href="https://github.com/KingBoyAndGirl/ups-guard/blob/main/docs/zh/README.md" target="_blank" class="doc-link"><span class="doc-icon">📖</span><span class="doc-text">项目介绍</span></a>
                <a href="https://github.com/KingBoyAndGirl/ups-guard/blob/main/docs/zh/user-guide.md" target="_blank" class="doc-link"><span class="doc-icon">📝</span><span class="doc-text">用户指南</span></a>
                <a href="https://github.com/KingBoyAndGirl/ups-guard/blob/main/docs/zh/push-setup.md" target="_blank" class="doc-link"><span class="doc-icon">🔔</span><span class="doc-text">推送配置</span></a>
                <a href="https://github.com/KingBoyAndGirl/ups-guard/blob/main/docs/zh/faq.md" target="_blank" class="doc-link"><span class="doc-icon">❓</span><span class="doc-text">常见问题</span></a>
                <a href="https://github.com/KingBoyAndGirl/ups-guard/issues" target="_blank" class="doc-link"><span class="doc-icon">🐛</span><span class="doc-text">问题反馈</span></a>
              </div>
            </div>

          </template>
        </div>
      </template>
    </div>
    <!-- End of settings-grid -->

    <!-- 导出确认弹窗 -->
    <div v-if="showExportConfirm" class="modal-overlay" @click.self="showExportConfirm = false">
      <div class="modal-dialog" @click.stop>
        <h3>⚠️ 导出配置确认</h3>
        <p>导出的配置文件将包含<strong>敏感信息</strong>：</p>
        <ul class="warning-list">
          <li>🔑 API Token、密码</li>
          <li>🔐 SSH 私钥</li>
          <li>📧 邮箱账号密码</li>
          <li>🤖 Bot Token</li>
        </ul>
        <p class="help-text warning-text">请妥善保管导出的文件，不要分享给他人或上传到公开平台！</p>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showExportConfirm = false">取消</button>
          <button class="btn btn-primary" @click="confirmExportConfig">确认导出</button>
        </div>
      </div>
    </div>

    <!-- 删除Hook确认对话框 -->
    <div v-if="showDeleteHookConfirm" class="modal-overlay" @click.self="showDeleteHookConfirm = false">
      <div class="modal-dialog modal-confirm">
        <div class="modal-icon">⚠️</div>
        <h3>确认删除关机前置任务？</h3>
        <p v-if="deletingHookIndex >= 0">
          将删除任务：<strong>{{ config.pre_shutdown_hooks[deletingHookIndex]?.name }}</strong>
        </p>
        <p class="warning-text">此操作无法撤销！</p>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showDeleteHookConfirm = false">取消</button>
          <button class="btn btn-danger" @click="confirmDeleteHook">确认删除</button>
        </div>
      </div>
    </div>

    <!-- 删除Channel确认对话框 -->
    <div v-if="showDeleteChannelConfirm" class="modal-overlay" @click.self="showDeleteChannelConfirm = false">
      <div class="modal-dialog modal-confirm">
        <div class="modal-icon">⚠️</div>
        <h3>确认删除通知渠道？</h3>
        <p v-if="deletingChannelIndex >= 0">
          将删除渠道：<strong>{{ config.notify_channels[deletingChannelIndex]?.name }}</strong>
        </p>
        <p class="warning-text">此操作无法撤销！</p>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showDeleteChannelConfirm = false">取消</button>
          <button class="btn btn-danger" @click="confirmDeleteChannel">确认删除</button>
        </div>
      </div>
    </div>

    <!-- 编辑关机前置任务对话框 -->
    <div v-if="showHookEditor" class="modal-overlay" @click.self="!testingEditingHook && !savingHook && closeHookEditor()">
      <div class="modal-dialog modal-lg" @click.stop>
        <h3>{{ editingHookIndex >= 0 ? '编辑关机前置任务' : '添加关机前置任务' }}</h3>
        <div v-if="editingHook" class="hook-editor">
          <div class="form-group">
            <label class="form-label">任务名称 <span class="required">*</span></label>
            <input
                v-model="editingHook.name"
                type="text"
                class="form-control"
                placeholder="例如：关闭 Ubuntu 服务器"
            />
            <small class="help-text">用于标识此任务</small>
          </div>

          <div class="form-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="editingHook.enabled"/>
              启用此任务
            </label>
          </div>

          <div class="form-group">
            <label class="form-label">优先级 <span class="required">*</span></label>
            <input
                v-model.number="editingHook.priority"
                type="number"
                class="form-control"
                placeholder="1-99"
                min="1"
                max="99"
            />
            <small class="help-text">数字越小优先级越高，同优先级的任务并行执行</small>
          </div>

          <div class="form-group">
            <label class="form-label">超时时间（秒） <span class="required">*</span></label>
            <input
                v-model.number="editingHook.timeout"
                type="number"
                class="form-control"
                placeholder="120"
                min="10"
                max="600"
            />
            <small class="help-text">任务执行的最长等待时间</small>
          </div>

          <div class="form-group">
            <label class="form-label">失败策略 <span class="required">*</span></label>
            <select v-model="editingHook.on_failure" class="form-control">
              <option value="continue">继续执行后续任务</option>
              <option value="abort">终止所有任务</option>
            </select>
            <small class="help-text">当此任务失败时的处理策略</small>
          </div>

          <!-- 动态配置字段 -->
          <div
              v-for="field in getHookPluginSchema(editingHook.hook_id)"
              :key="field.key"
              class="form-group"
          >
            <label class="form-label">
              {{ field.label }}
              <span v-if="field.required" class="required">*</span>
            </label>
            <input
                v-if="field.type === 'text' || field.type === 'password'"
                v-model="editingHook.config[field.key]"
                :type="field.type"
                class="form-control"
                :placeholder="field.placeholder"
            />
            <input
                v-else-if="field.type === 'number'"
                v-model.number="editingHook.config[field.key]"
                type="number"
                class="form-control"
                :placeholder="field.placeholder"
            />
            <textarea
                v-else-if="field.type === 'textarea'"
                v-model="editingHook.config[field.key]"
                class="form-control"
                :placeholder="field.placeholder"
                :rows="field.rows || 3"
            ></textarea>
            <div v-if="field.type === 'textarea' && field.key === 'private_key'" class="file-upload-hint">
              <input
                  type="file"
                  :id="'hook-file-' + field.key"
                  accept="*"
                  @change="(e) => handlePrivateKeyFileUpload(e, 'hook')"
                  style="display: none"
              />
              <button
                  type="button"
                  class="btn btn-sm btn-secondary"
                  @click="triggerPrivateKeyFileInput('hook-file-' + field.key)"
              >
                📁 从文件导入
              </button>
            </div>
            <div v-if="field.type === 'textarea' && field.key === 'script_content'" class="file-upload-hint">
              <input
                  type="file"
                  :id="'hook-script-file-' + field.key"
                  accept=".sh,.bash,.py,.pl,.rb"
                  @change="(e) => handleScriptFileUpload(e)"
                  style="display: none"
              />
              <button
                  type="button"
                  class="btn btn-sm btn-secondary"
                  @click="triggerScriptFileInput('hook-script-file-' + field.key)"
              >
                📁 从文件上传脚本
              </button>
              <small class="help-text" style="margin-left: 10px;">支持 .sh, .bash, .py, .pl, .rb 文件</small>
            </div>
            <select
                v-else-if="field.type === 'select'"
                v-model="editingHook.config[field.key]"
                class="form-control"
            >
              <option v-for="option in field.options" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
            <small v-if="field.description" class="help-text">{{ field.description }}</small>
            <!-- WOL Test Button for MAC address field -->
            <button
                v-if="field.key === 'mac_address' && editingHook.config[field.key]"
                type="button"
                class="btn btn-sm btn-info"
                @click="testWOLInHookEditor"
                :disabled="testingWOL"
                style="margin-top: 0.5rem"
            >
              {{ testingWOL ? '测试中...' : '🧪 测试 WOL' }}
            </button>
          </div>

          <div class="modal-actions">
            <button class="btn btn-secondary" @click="closeHookEditor" :disabled="testingEditingHook || savingHook">
              取消
            </button>
            <button
                class="btn btn-secondary"
                @click="testEditingHook"
                :disabled="testingEditingHook || savingHook"
                :class="{ 'btn-loading': testingEditingHook }"
            >
              {{ testingEditingHook ? '测试中' : '测试配置' }}
            </button>
            <button
                class="btn btn-primary"
                @click="saveHook"
                :disabled="testingEditingHook || savingHook"
                :class="{ 'btn-loading': savingHook }"
            >
              {{ savingHook ? '保存中' : '保存' }}
            </button>
          </div>

          <div v-if="hookEditorTestResult" class="test-result"
               :class="hookEditorTestResult.success ? 'success' : 'error'">
            {{ hookEditorTestResult.message }}
          </div>
        </div>
      </div>
    </div>

    <!-- 配置比较对话框 -->
    <div v-if="showComparisonModal" class="modal-overlay" @click.self="showComparisonModal = false">
      <div class="modal-dialog modal-xl" @click.stop>
        <div class="modal-header">
          <h3>配置差异对比</h3>
          <button class="modal-close" @click="showComparisonModal = false">&times;</button>
        </div>

        <div v-if="comparisonData" class="comparison-content">
          <!-- 统计摘要 -->
          <div class="comparison-summary">
            <span class="summary-item">
              <span class="summary-label">总计：</span>
              <span class="summary-value">{{ comparisonData.summary.total }} 项</span>
            </span>
            <span class="summary-item modified">
              <span class="summary-label">将修改：</span>
              <span class="summary-value">{{ selectedFieldsCount }}/{{ comparisonData.summary.modified }} 项</span>
            </span>
            <span class="summary-item">
              <label class="checkbox-label select-all-label">
                <input type="checkbox" v-model="selectAllFields" @change="toggleSelectAll"/>
                全选/全不选
              </label>
            </span>
          </div>

          <!-- 差异列表 -->
          <div class="comparison-list">
            <div
                v-for="change in comparisonData.changes"
                :key="change.field"
                class="comparison-item"
                :class="[change.type, { 'selected': selectedFields[change.field] }]"
            >
              <div class="comparison-field">
                <!-- 只有修改项才显示复选框 -->
                <label v-if="change.type === 'modified'" class="checkbox-label field-checkbox">
                  <input type="checkbox" v-model="selectedFields[change.field]"/>
                </label>
                <span class="field-label">{{ change.label }}</span>
                <span class="field-key">({{ change.field }})</span>
                <span
                    class="field-badge"
                    :class="change.type"
                >
                  {{ change.type === 'modified' ? (selectedFields[change.field] ? '将修改' : '跳过') : '不变' }}
                </span>
              </div>

              <div v-if="change.type === 'modified'" class="comparison-values">
                <div class="value-row current">
                  <span class="value-label">当前值：</span>
                  <span class="value-content">{{ formatComparisonValue(change.current) }}</span>
                </div>
                <div class="value-row imported">
                  <span class="value-label">导入值：</span>
                  <span class="value-content">{{ formatComparisonValue(change.imported) }}</span>
                </div>

                <!-- 列表项详情 -->
                <div v-if="change.details && change.details.length > 0" class="value-details">
                  <div
                      v-for="(detail, idx) in change.details"
                      :key="idx"
                      class="detail-item"
                      :class="detail.action"
                  >
                    <span class="detail-action">
                      {{ detail.action === 'add' ? '➕ 新增' : detail.action === 'remove' ? '➖ 删除' : '✏️ 修改' }}
                    </span>
                    <span class="detail-name">{{ detail.name }}</span>
                  </div>
                </div>
              </div>

              <div v-else class="comparison-reason">
                {{ change.reason }}
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showComparisonModal = false">关闭</button>
          <button
              class="btn btn-primary"
              @click="confirmSelectiveImport"
              :disabled="importing || selectedFieldsCount === 0"
          >
            {{ importing ? '导入中...' : `导入选中 (${selectedFieldsCount}项)` }}
          </button>
        </div>
      </div>
    </div>

    <!-- 编辑通知渠道对话框 -->
    <div v-if="showChannelEditor" class="modal-overlay" @click.self="!testingEditingChannel && !savingChannel && closeChannelEditor()">
      <div class="modal-dialog modal-lg" @click.stop>
        <h3>{{ editingChannelIndex >= 0 ? '编辑通知渠道' : '添加通知渠道' }}</h3>
        <div v-if="editingChannel" class="channel-editor">
          <div class="form-group">
            <label class="form-label">渠道名称</label>
            <input
                v-model="editingChannel.name"
                type="text"
                class="form-control"
                :placeholder="getPluginName(editingChannel.plugin_id)"
            />
            <small class="help-text">可选，用于区分同类型的多个渠道</small>
          </div>

          <div class="form-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="editingChannel.enabled"/>
              启用此通知渠道
            </label>
          </div>

          <!-- 动态配置字段 -->
          <div
              v-for="field in getPluginSchema(editingChannel.plugin_id)"
              :key="field.key"
              class="form-group"
          >
            <label class="form-label">
              {{ field.label }}
              <span v-if="field.required" class="required">*</span>
            </label>
            <input
                v-if="field.type === 'text' || field.type === 'password'"
                v-model="editingChannel.config[field.key]"
                :type="field.type"
                class="form-control"
                :placeholder="field.placeholder"
            />
            <input
                v-else-if="field.type === 'number'"
                v-model.number="editingChannel.config[field.key]"
                type="number"
                class="form-control"
                :placeholder="field.placeholder"
            />
            <textarea
                v-else-if="field.type === 'textarea'"
                v-model="editingChannel.config[field.key]"
                class="form-control"
                :placeholder="field.placeholder"
                rows="3"
            ></textarea>
            <small v-if="field.description" class="help-text">{{ field.description }}</small>
          </div>

          <div class="modal-actions">
            <button class="btn btn-secondary" @click="closeChannelEditor"
                    :disabled="testingEditingChannel || savingChannel">取消
            </button>
            <button
                class="btn btn-secondary"
                @click="testEditingChannel"
                :disabled="testingEditingChannel || savingChannel"
                :class="{ 'btn-loading': testingEditingChannel }"
            >
              {{ testingEditingChannel ? '测试中' : '测试配置' }}
            </button>
            <button
                class="btn btn-primary"
                @click="saveChannel"
                :disabled="testingEditingChannel || savingChannel"
                :class="{ 'btn-loading': savingChannel }"
            >
              {{ savingChannel ? '保存中' : '保存' }}
            </button>
          </div>

          <div v-if="channelTestResult" class="test-result" :class="channelTestResult.success ? 'success' : 'error'">
            {{ channelTestResult.message }}
          </div>
        </div>
      </div>
    </div>

    <!-- UPS 变量修改确认对话框 -->
    <div v-if="showUpsVarConfirm" class="modal-overlay" @click.self="showUpsVarConfirm = false">
      <div class="modal-dialog modal-confirm">
        <div class="modal-icon">⚠️</div>
        <h3>确认修改 UPS 参数？</h3>
        <p>
          将修改变量：<strong><code>{{ pendingUpsVar.varName }}</code></strong><br>
          新值：<strong>{{ pendingUpsVar.value }}</strong>
        </p>
        <p class="warning-text">此操作将直接修改 UPS 硬件参数，请确认您了解该参数的作用！</p>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showUpsVarConfirm = false">取消</button>
          <button class="btn btn-primary" @click="confirmSetUpsVar">确认修改</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {ref, onMounted, onUnmounted, watch, computed} from 'vue'
import axios from 'axios'
import {useToast} from '@/composables/useToast'
import {useConfigStore} from '@/stores/config'
import {useUserPreferencesStore} from '@/stores/userPreferences'
import {useDraggableCards} from '@/composables/useDraggableCards'
import type {Config, NotifyChannel, NotifyPlugin, ConfigField, PreShutdownHook, HookPlugin} from '@/types/ups'

const toast = useToast()
const configStore = useConfigStore()

// 用户偏好设置
const userPrefs = useUserPreferencesStore()

// Settings 卡片定义
type SettingsCol = 'col1' | 'col2' | 'col3' | 'col4'

// 拖拽功能
const {
  dragState,
  handleDragStart,
  handleDrop,
  handleDragEnd
} = useDraggableCards<SettingsCol>(
  () => userPrefs.settingsCardOrder,
  (col, cards) => userPrefs.updateSettingsCardOrder(col, cards),
  (fromCol, toCol, cardId, toIndex) => userPrefs.moveSettingsCard(fromCol, toCol, cardId, toIndex)
)

// 列拖拽经过处理（用于拖到列末尾空白区域）
const handleColDragOver = (e: DragEvent, col: SettingsCol) => {
  e.preventDefault()
  if (!dragState.isDragging) return

  // 检查是否直接拖到了列容器（不是子元素）
  const target = e.target as HTMLElement
  if (target.classList.contains('droppable-col')) {
    dragState.targetCol = col
    dragState.targetIndex = userPrefs.settingsCardOrder[col].length
  }
}

// 卡片拖拽经过处理（用于拖到卡片位置）
const handleCardDragOver = (e: DragEvent, col: SettingsCol, index: number) => {
  e.preventDefault()
  e.stopPropagation()
  if (!dragState.isDragging) return

  // 获取卡片元素
  const cardElement = (e.currentTarget as HTMLElement)
  const rect = cardElement.getBoundingClientRect()
  const mouseY = e.clientY

  // 判断鼠标在卡片的上半部分还是下半部分
  const middleY = rect.top + rect.height / 2

  dragState.targetCol = col
  // 如果鼠标在卡片上半部分，插入到当前位置；否则插入到下一个位置
  if (mouseY < middleY) {
    dragState.targetIndex = index
  } else {
    dragState.targetIndex = index + 1
  }
}


// 重置布局
const resetSettingsLayout = () => {
  userPrefs.resetSettingsLayout()
  toast.success('布局已重置为默认')
}

const config = ref<Config>({
  shutdown_wait_minutes: 5,
  shutdown_battery_percent: 20,
  shutdown_final_wait_seconds: 30,
  estimated_runtime_threshold: 3,
  notify_channels: [],
  notify_events: [],
  notification_enabled: true,
  sample_interval_seconds: 60,
  history_retention_days: 30,
  poll_interval_seconds: 5,
  cleanup_interval_hours: 24,
  pre_shutdown_hooks: [],
  test_mode: 'production',
  shutdown_method: 'lzc_grpc',
  wol_on_power_restore: false,
  wol_delay_seconds: 60,
  device_status_check_interval_seconds: 60
})

const errors = ref<Record<string, string>>({})
const saving = ref(false) // 自动保存状态
const notificationTestResult = ref<{ success: boolean; message: string } | null>(null)

// 自动保存防抖定时器
let autoSaveTimer: ReturnType<typeof setTimeout> | null = null
const configLoaded = ref(false) // 标记配置是否已加载完成

// 存储信息
interface StorageInfo {
  db_size_bytes: number
  db_size_mb: number
  event_count: number
  metric_count: number
  earliest_record_time: string | null
}

const storageInfo = ref<StorageInfo | null>(null)
const showCleanupConfirm = ref(false)
const cleaningUp = ref(false)

// 监控统计相关
interface MonitoringStats {
  current_mode: string
  event_mode_active: boolean
  today_communications: number
  last_update: string | null
  uptime_seconds: number
}

const monitoringStats = ref<MonitoringStats | null>(null)

// 通知渠道相关
const availablePlugins = ref<NotifyPlugin[]>([])
const selectedPlugin = ref('')
const showChannelEditor = ref(false)
const editingChannel = ref<NotifyChannel | null>(null)
const editingChannelIndex = ref(-1)
const testingChannelIndex = ref(-1)
const testingEditingChannel = ref(false)
const savingChannel = ref(false)
const channelTestResult = ref<{ success: boolean; message: string } | null>(null)
const channelErrors = ref<Record<number, string>>({})  // 渠道错误状态

// UPS 高级配置相关
const VOLTAGE_LIMITS = {
  HIGH_MIN: 220,
  HIGH_MAX: 300,
  LOW_MIN: 100,
  LOW_MAX: 200
}

// UPS参数默认值（基于APC Back-UPS BK650M2_CH实际出厂设置）
const UPS_PARAM_DEFAULTS = {
  'input.transfer.high': '278',  // 高压切换阈值默认值（实际UPS出厂值）
  'input.transfer.low': '160',   // 低压切换阈值默认值
  'input.sensitivity': 'low',    // 灵敏度默认值（实际UPS出厂值：低）
  'ups.delay.shutdown': '20'     // 关机延迟默认值
}

const SHUTDOWN_DELAY_LIMITS = {
  MIN: 0,
  MAX: 600
}

const writableVars = ref<Record<string, any> | null>(null)
const loadingWritableVars = ref(false)
const writableVarsError = ref<string | null>(null)

// 电压配置
const currentVoltageHigh = ref<string | null>(null)
const currentVoltageLow = ref<string | null>(null)
const newVoltageHigh = ref<number | null>(null)
const newVoltageLow = ref<number | null>(null)
const savingVoltage = ref(false)

// 灵敏度配置
const currentSensitivity = ref<string | null>(null)
const newSensitivity = ref<string>('')
const savingSensitivity = ref(false)

// 关机延迟配置
const currentShutdownDelay = ref<string | null>(null)
const newShutdownDelay = ref<number | null>(null)
const savingShutdownDelay = ref(false)

// UPS 变量修改确认对话框
const showUpsVarConfirm = ref(false)
const pendingUpsVar = ref<{ varName: string; value: string; callback?: () => void }>({
  varName: '',
  value: ''
})


const loadConfig = async () => {
  try {
    const response = await axios.get('/api/config')
    config.value = response.data
  } catch (error) {
    console.error('Failed to load config:', error)
  }
}

const loadStorageInfo = async () => {
  try {
    const response = await axios.get('/api/system/storage')
    storageInfo.value = response.data
  } catch (error) {
    console.error('Failed to load storage info:', error)
  }
}

const loadMonitoringStats = async () => {
  try {
    const response = await axios.get('/api/system/monitoring-stats')
    monitoringStats.value = response.data
  } catch (error) {
    console.error('Failed to load monitoring stats:', error)
  }
}

const formatLastUpdate = (isoTime: string | null): string => {
  if (!isoTime) return '-'
  try {
    const date = new Date(isoTime)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffSec = Math.floor(diffMs / 1000)
    
    if (diffSec < 60) return `${diffSec} 秒前`
    const diffMin = Math.floor(diffSec / 60)
    if (diffMin < 60) return `${diffMin} 分钟前`
    const diffHour = Math.floor(diffMin / 60)
    if (diffHour < 24) return `${diffHour} 小时前`
    return `${Math.floor(diffHour / 24)} 天前`
  } catch {
    return '-'
  }
}

const validateConfig = (): boolean => {
  errors.value = {}
  let isValid = true

  if (config.value.shutdown_wait_minutes < 1 || config.value.shutdown_wait_minutes > 60) {
    errors.value.shutdown_wait_minutes = '请输入 1-60 之间的值'
    isValid = false
  }

  if (config.value.shutdown_battery_percent < 5 || config.value.shutdown_battery_percent > 50) {
    errors.value.shutdown_battery_percent = '请输入 5-50 之间的值'
    isValid = false
  }

  if (config.value.estimated_runtime_threshold < 1 || config.value.estimated_runtime_threshold > 30) {
    errors.value.estimated_runtime_threshold = '请输入 1-30 之间的值'
    isValid = false
  }

  if (config.value.shutdown_final_wait_seconds < 10 || config.value.shutdown_final_wait_seconds > 120) {
    errors.value.shutdown_final_wait_seconds = '请输入 10-120 之间的值'
    isValid = false
  }

  if (config.value.history_retention_days < 1 || config.value.history_retention_days > 90) {
    errors.value.history_retention_days = '请输入 1-90 之间的值'
    isValid = false
  }

  if (config.value.poll_interval_seconds < 1 || config.value.poll_interval_seconds > 60) {
    errors.value.poll_interval_seconds = '请输入 1-60 之间的值'
    isValid = false
  }

  if (config.value.cleanup_interval_hours < 1 || config.value.cleanup_interval_hours > 168) {
    errors.value.cleanup_interval_hours = '请输入 1-168 之间的值'
    isValid = false
  }

  if (config.value.sample_interval_seconds < 10 || config.value.sample_interval_seconds > 3600) {
    errors.value.sample_interval_seconds = '请输入 10-3600 之间的值'
    isValid = false
  }

  if (config.value.wol_delay_seconds < 0 || config.value.wol_delay_seconds > 600) {
    errors.value.wol_delay_seconds = '请输入 0-600 之间的值'
    isValid = false
  }

  if (config.value.device_status_check_interval_seconds < 0 || config.value.device_status_check_interval_seconds > 600) {
    errors.value.device_status_check_interval_seconds = '请输入 0-600 之间的值'
    isValid = false
  }

  return isValid
}


// 测试模式变更时自动保存
const onTestModeChange = async () => {
  try {
    await axios.put('/api/config', config.value)
    // 立即更新全局状态
    configStore.setTestMode(config.value.test_mode || 'production')
    toast.success('测试模式已更新')
  } catch (error) {
    console.error('Failed to save test mode:', error)
    toast.error('保存失败')
  }
}
const cleanupAllHistory = async () => {
  showCleanupConfirm.value = false
  cleaningUp.value = true

  try {
    const response = await axios.post('/api/actions/cleanup-all')
    toast.success(`清空完成\n删除事件: ${response.data.events_deleted} 条\n删除指标: ${response.data.metrics_deleted} 条\n删除测试报告: ${response.data.reports_deleted} 条\n删除监控统计: ${response.data.stats_deleted} 条`)

    // 刷新存储信息
    await loadStorageInfo()
  } catch (error) {
    console.error('Failed to cleanup all history:', error)
    toast.error('清空失败')
  } finally {
    cleaningUp.value = false
  }
}
// 加载可用的通知插件
const loadPlugins = async () => {
  try {
    const response = await axios.get('/api/config/notify-plugins')
    availablePlugins.value = response.data.plugins
  } catch (error) {
    console.error('Failed to load plugins:', error)
  }
}

// 加载渠道错误状态
const loadChannelErrors = async () => {
  try {
    const response = await axios.get('/api/config/channel-errors')
    const errors = response.data.errors
    // 后端返回的 errors 是 {索引: 错误信息} 格式
    channelErrors.value = {}
    for (const [index, errorMsg] of Object.entries(errors)) {
      channelErrors.value[parseInt(index)] = errorMsg as string
    }
  } catch (error) {
    console.error('Failed to load channel errors:', error)
  }
}

// 获取插件名称
const getPluginName = (pluginId: string): string => {
  const plugin = availablePlugins.value.find(p => p.id === pluginId)
  return plugin?.name || pluginId
}

// 获取插件配置模式
const getPluginSchema = (pluginId: string): ConfigField[] => {
  const plugin = availablePlugins.value.find(p => p.id === pluginId)
  return plugin?.config_schema || []
}

// 生成 UUID
const generateUUID = (): string => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

// 添加新渠道
const addChannel = () => {
  if (!selectedPlugin.value) return

  const plugin = availablePlugins.value.find(p => p.id === selectedPlugin.value)
  if (!plugin) return

  // 创建默认配置
  const defaultConfig: Record<string, any> = {}
  plugin.config_schema.forEach(field => {
    if (field.default !== undefined) {
      defaultConfig[field.key] = field.default
    } else {
      defaultConfig[field.key] = ''
    }
  })

  editingChannel.value = {
    id: generateUUID(),  // 生成唯一 ID
    enabled: true,
    plugin_id: selectedPlugin.value,
    name: '',
    config: defaultConfig
  }
  editingChannelIndex.value = -1
  showChannelEditor.value = true
  selectedPlugin.value = ''
}

// Hook 相关变量
const availableHookPlugins = ref<HookPlugin[]>([])
const selectedHookPlugin = ref('')
const showHookEditor = ref(false)
const editingHook = ref<PreShutdownHook | null>(null)
const editingHookIndex = ref(-1)
const testingHookIndex = ref(-1)
const testingEditingHook = ref(false)
const savingHook = ref(false)
const testingWOL = ref(false)
const hookTestResult = ref<{ success: boolean; message: string } | null>(null)
const hookEditorTestResult = ref<{ success: boolean; message: string } | null>(null)

// Delete confirmation modals
const showDeleteHookConfirm = ref(false)
const deletingHookIndex = ref(-1)
const showDeleteChannelConfirm = ref(false)
const deletingChannelIndex = ref(-1)

// 加载可用的 hook 插件
const loadHookPlugins = async () => {
  try {
    const response = await axios.get('/api/hooks/plugins')
    availableHookPlugins.value = response.data.plugins
  } catch (error) {
    console.error('Failed to load hook plugins:', error)
  }
}

// 获取 hook 插件名称
const getHookPluginName = (hookId: string): string => {
  const plugin = availableHookPlugins.value.find(p => p.id === hookId)
  return plugin?.name || hookId
}

// 获取 hook 插件配置模式
const getHookPluginSchema = (hookId: string): ConfigField[] => {
  const plugin = availableHookPlugins.value.find(p => p.id === hookId)
  return plugin?.config_schema || []
}

// 添加新 hook
const addHook = () => {
  if (!selectedHookPlugin.value) return

  const plugin = availableHookPlugins.value.find(p => p.id === selectedHookPlugin.value)
  if (!plugin) return

  // 创建默认配置
  const defaultConfig: Record<string, any> = {}
  plugin.config_schema.forEach(field => {
    if (field.default !== undefined) {
      defaultConfig[field.key] = field.default
    } else {
      defaultConfig[field.key] = ''
    }
  })

  editingHook.value = {
    enabled: true,
    hook_id: selectedHookPlugin.value,
    name: '',
    priority: 10,
    timeout: 120,
    on_failure: 'continue',
    config: defaultConfig
  }
  editingHookIndex.value = -1
  showHookEditor.value = true
  selectedHookPlugin.value = ''
}

// 编辑 hook
const editHook = (index: number) => {
  editingHook.value = JSON.parse(JSON.stringify(config.value.pre_shutdown_hooks[index]))
  editingHookIndex.value = index
  showHookEditor.value = true
}

// 删除 hook
const removeHook = (index: number) => {
  deletingHookIndex.value = index
  showDeleteHookConfirm.value = true
}

const confirmDeleteHook = () => {
  if (deletingHookIndex.value >= 0) {
    config.value.pre_shutdown_hooks.splice(deletingHookIndex.value, 1)
  }
  showDeleteHookConfirm.value = false
  deletingHookIndex.value = -1
}

// 保存 hook
const saveHook = () => {
  if (!editingHook.value) return

  if (editingHookIndex.value >= 0) {
    // 更新现有 hook
    config.value.pre_shutdown_hooks[editingHookIndex.value] = editingHook.value
  } else {
    // 添加新 hook
    config.value.pre_shutdown_hooks.push(editingHook.value)
  }

  closeHookEditor()
}

// 关闭 hook 编辑器
const closeHookEditor = () => {
  showHookEditor.value = false
  editingHook.value = null
  editingHookIndex.value = -1
  hookEditorTestResult.value = null
}

// 测试 hook
const testHook = async (hook: PreShutdownHook, index: number) => {
  testingHookIndex.value = index
  hookTestResult.value = null

  try {
    const response = await axios.post('/api/hooks/test', {
      hook_id: hook.hook_id,
      config: hook.config
    })

    hookTestResult.value = {
      success: response.data.success,
      message: response.data.message
    }

    setTimeout(() => {
      hookTestResult.value = null
    }, 3000)
  } catch (error: any) {
    hookTestResult.value = {
      success: false,
      message: error.response?.data?.detail || '测试失败'
    }
  } finally {
    testingHookIndex.value = -1
  }
}

// 测试编辑中的 hook
// 测试 WOL（在 Hook 编辑器中）
const testWOLInHookEditor = async () => {
  if (!editingHook.value) return

  const macAddress = editingHook.value.config.mac_address
  const broadcastAddress = editingHook.value.config.broadcast_address || '255.255.255.255'

  if (!macAddress) {
    toast.error('请先填写 MAC 地址')
    return
  }

  testingWOL.value = true

  try {
    const response = await axios.post('/api/wol/send', {
      mac_address: macAddress,
      broadcast_address: broadcastAddress
    })

    if (response.data.success) {
      toast.success(`✅ WOL 测试成功！魔术包已发送到 ${macAddress}`)
    } else {
      toast.error(`WOL 测试失败: ${response.data.message}`)
    }
  } catch (error: any) {
    console.error('WOL test failed:', error)
    toast.error(`WOL 测试失败: ${error.response?.data?.detail || error.message}`)
  } finally {
    testingWOL.value = false
  }
}

const testEditingHook = async () => {
  if (!editingHook.value) return

  testingEditingHook.value = true
  hookEditorTestResult.value = null

  try {
    const response = await axios.post('/api/hooks/test', {
      hook_id: editingHook.value.hook_id,
      config: editingHook.value.config
    })

    hookEditorTestResult.value = {
      success: response.data.success,
      message: response.data.message
    }
  } catch (error: any) {
    hookEditorTestResult.value = {
      success: false,
      message: error.response?.data?.detail || '测试失败'
    }
  } finally {
    testingEditingHook.value = false
  }
}

// 编辑渠道
const editChannel = (index: number) => {
  const channel = config.value.notify_channels[index]
  editingChannel.value = JSON.parse(JSON.stringify(channel)) // 深拷贝
  editingChannelIndex.value = index
  showChannelEditor.value = true
  channelTestResult.value = null
}

// 删除渠道
const removeChannel = (index: number) => {
  deletingChannelIndex.value = index
  showDeleteChannelConfirm.value = true
}

const confirmDeleteChannel = () => {
  if (deletingChannelIndex.value >= 0) {
    config.value.notify_channels.splice(deletingChannelIndex.value, 1)
  }
  showDeleteChannelConfirm.value = false
  deletingChannelIndex.value = -1
}

// 保存渠道编辑
const saveChannel = () => {
  if (!editingChannel.value) return

  if (editingChannelIndex.value >= 0) {
    // 编辑现有渠道
    config.value.notify_channels[editingChannelIndex.value] = editingChannel.value
  } else {
    // 添加新渠道
    config.value.notify_channels.push(editingChannel.value)
  }

  closeChannelEditor()
}

// 关闭编辑器
const closeChannelEditor = () => {
  showChannelEditor.value = false
  editingChannel.value = null
  editingChannelIndex.value = -1
  channelTestResult.value = null
}

// 测试正在编辑的渠道
const testEditingChannel = async () => {
  if (!editingChannel.value) return

  testingEditingChannel.value = true
  channelTestResult.value = null

  try {
    const response = await axios.post('/api/config/test-notify', {
      plugin_id: editingChannel.value.plugin_id,
      config: editingChannel.value.config
    })
    channelTestResult.value = {
      success: response.data.success,
      message: response.data.success ? '✓ 测试通知发送成功！' : '✗ 测试通知发送失败'
    }
  } catch (error: any) {
    console.error('Failed to test channel:', error)
    channelTestResult.value = {
      success: false,
      message: '✗ 测试失败: ' + (error.response?.data?.detail || error.message)
    }
  } finally {
    testingEditingChannel.value = false
  }
}

// 测试已保存的渠道
const testChannel = async (channel: NotifyChannel, index: number) => {
  testingChannelIndex.value = index

  try {
    const response = await axios.post('/api/config/test-notify', {
      plugin_id: channel.plugin_id,
      config: channel.config
    })
    if (response.data.success) {
      // 测试成功，清除错误状态
      delete channelErrors.value[index]
      notificationTestResult.value = {
        success: true,
        message: '✓ 测试通知发送成功！'
      }
    } else {
      // 测试失败，记录错误
      channelErrors.value[index] = '发送失败'
      notificationTestResult.value = {
        success: false,
        message: '✗ 测试通知发送失败'
      }
    }
    setTimeout(() => {
      notificationTestResult.value = null
    }, 5000)
  } catch (error: any) {
    console.error('Failed to test channel:', error)
    const errorMsg = error.response?.data?.detail || error.message
    channelErrors.value[index] = errorMsg
    notificationTestResult.value = {
      success: false,
      message: '✗ 测试失败: ' + errorMsg
    }
  } finally {
    testingChannelIndex.value = -1
  }
}

// 配置导入/导出相关
const exporting = ref(false)
const importing = ref(false)
const validating = ref(false)
const comparing = ref(false)
const exportingDiagnostics = ref(false)
const importFileInput = ref<HTMLInputElement | null>(null)
const importPreview = ref<any>(null)
const importMode = ref('merge')
const importResult = ref<{ success: boolean; message: string; affected_count?: number } | null>(null)
const selectedImportFile = ref<File | null>(null)
const showComparisonModal = ref(false)
const comparisonData = ref<any>(null)
const showExportConfirm = ref(false)
const selectedFields = ref<Record<string, boolean>>({})
const selectAllFields = ref(true)

// 计算选中的字段数
const selectedFieldsCount = computed(() => {
  return Object.values(selectedFields.value).filter(v => v).length
})

// 全选/全不选
const toggleSelectAll = () => {
  if (comparisonData.value) {
    comparisonData.value.changes.forEach((change: any) => {
      if (change.type === 'modified') {
        selectedFields.value[change.field] = selectAllFields.value
      }
    })
  }
}

// 格式化比较值显示
const formatComparisonValue = (value: any): string => {
  if (value === null || value === undefined) return '(空)'
  if (typeof value === 'object') {
    if (Array.isArray(value)) return `[${value.length}项]`
    return JSON.stringify(value).substring(0, 50) + '...'
  }
  const str = String(value)
  return str.length > 50 ? str.substring(0, 50) + '...' : str
}

// 显示导出确认弹窗
const exportConfig = () => {
  showExportConfirm.value = true
}

// 确认导出配置
const confirmExportConfig = async () => {
  showExportConfirm.value = false
  exporting.value = true
  try {
    const response = await axios.get('/api/config/export', {
      responseType: 'blob'
    })

    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url

    // 从响应头获取文件名
    const contentDisposition = response.headers['content-disposition']
    let filename = 'ups-guard-config.json'
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?(.+)"?/)
      if (filenameMatch) {
        filename = filenameMatch[1]
      }
    }

    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)

    toast.success('配置导出成功')
  } catch (error: any) {
    console.error('Export failed:', error)
    toast.error(error.response?.data?.detail || '导出失败')
  } finally {
    exporting.value = false
  }
}

// 触发文件选择
const triggerFileInput = () => {
  importFileInput.value?.click()
}

// 触发私钥文件选择
const triggerPrivateKeyFileInput = (inputId: string) => {
  const input = document.getElementById(inputId) as HTMLInputElement
  input?.click()
}

// 处理私钥文件上传
const handlePrivateKeyFileUpload = async (event: Event, target: 'hook' | 'channel') => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]

  if (!file) return

  try {
    const content = await file.text()

    // 验证是否为有效的私钥格式
    if (!content.includes('-----BEGIN') || !content.includes('-----END')) {
      toast.error('无效的私钥文件格式')
      return
    }

    if (target === 'hook' && editingHook.value) {
      editingHook.value.config.private_key = content.trim()
    } else if (target === 'channel' && editingChannel.value) {
      editingChannel.value.config.private_key = content.trim()
    }

    toast.success('私钥文件导入成功')
  } catch (error) {
    console.error('Failed to read private key file:', error)
    toast.error('读取私钥文件失败')
  }

  // 清空文件选择，允许重复选择同一文件
  input.value = ''
}

// 触发脚本文件选择
const triggerScriptFileInput = (inputId: string) => {
  const input = document.getElementById(inputId) as HTMLInputElement
  input?.click()
}

// 处理脚本文件上传
const handleScriptFileUpload = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]

  if (!file) return

  try {
    // 创建 FormData 并上传到后端API
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch('/api/hooks/upload-script', {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      const error = await response.json()
      toast.error(error.error || '上传脚本失败')
      return
    }

    const result = await response.json()

    if (result.success && editingHook.value) {
      // 填充脚本内容
      editingHook.value.config.script_content = result.content
      
      // 如果返回了解释器建议，自动设置
      if (result.interpreter && editingHook.value.config.interpreter !== undefined) {
        editingHook.value.config.interpreter = result.interpreter
      }

      toast.success(`脚本文件已上传：${result.filename} (${result.size} 字节)`)
    } else {
      toast.error('上传脚本失败')
    }
  } catch (error) {
    console.error('Failed to upload script file:', error)
    toast.error('上传脚本文件时出错')
  }

  // 清空文件选择，允许重复选择同一文件
  input.value = ''
}

// 处理文件选择
const handleImportFile = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]

  if (!file) return

  selectedImportFile.value = file
  validating.value = true
  importResult.value = null

  try {
    // 验证配置文件
    const formData = new FormData()
    formData.append('file', file)

    const response = await axios.post('/api/config/validate', formData, {
      headers: {'Content-Type': 'multipart/form-data'}
    })

    if (response.data.valid) {
      // 读取文件内容以显示预览
      const text = await file.text()
      const data = JSON.parse(text)

      importPreview.value = {
        field_count: response.data.field_count,
        export_time: data.export_time,
        version: data.version,
        fields: response.data.fields
      }

      toast.success('配置文件验证通过')
    } else {
      toast.error('配置文件验证失败: ' + response.data.message)
      importPreview.value = null
    }
  } catch (error: any) {
    console.error('Validation failed:', error)
    toast.error(error.response?.data?.detail || '文件验证失败')
    importPreview.value = null
  } finally {
    validating.value = false
    // 清空 input 以允许重新选择同一文件
    target.value = ''
  }
}

// 确认导入
const confirmImport = async () => {
  if (!selectedImportFile.value) return

  importing.value = true
  importResult.value = null

  try {
    const formData = new FormData()
    formData.append('file', selectedImportFile.value)
    formData.append('mode', importMode.value)

    const response = await axios.post('/api/config/import', formData, {
      headers: {'Content-Type': 'multipart/form-data'}
    })

    importResult.value = {
      success: true,
      message: response.data.message,
      affected_count: response.data.affected_count
    }

    toast.success('配置导入成功')

    // 重新加载配置
    await loadConfig()

    // 3秒后自动关闭预览
    setTimeout(() => {
      cancelImport()
    }, 3000)
  } catch (error: any) {
    console.error('Import failed:', error)
    const errorMsg = error.response?.data?.detail || '导入失败'
    importResult.value = {
      success: false,
      message: errorMsg
    }
    toast.error(errorMsg)
  } finally {
    importing.value = false
  }
}

// 取消导入
const cancelImport = () => {
  importPreview.value = null
  importResult.value = null
  selectedImportFile.value = null
  importMode.value = 'merge'
  showComparisonModal.value = false
  comparisonData.value = null
}

// 显示配置比较
const showConfigComparison = async () => {
  if (!selectedImportFile.value) return

  comparing.value = true

  try {
    const formData = new FormData()
    formData.append('file', selectedImportFile.value)
    formData.append('mode', importMode.value)

    const response = await axios.post('/api/config/compare', formData, {
      headers: {'Content-Type': 'multipart/form-data'}
    })

    comparisonData.value = response.data
    showComparisonModal.value = true
  } catch (error: any) {
    console.error('Comparison failed:', error)
    toast.error(error.response?.data?.detail || '比较失败')
  } finally {
    comparing.value = false
  }
}

// 确认选择性导入（从对比弹窗）
const confirmSelectiveImport = async () => {
  if (!selectedImportFile.value) return

  importing.value = true

  try {
    // 获取选中的字段列表
    const selectedFieldsList = Object.keys(selectedFields.value).filter(
        key => selectedFields.value[key]
    )

    if (selectedFieldsList.length === 0) {
      toast.error('请至少选择一个字段')
      return
    }

    const formData = new FormData()
    formData.append('file', selectedImportFile.value)
    formData.append('mode', importMode.value)
    formData.append('selected_fields', JSON.stringify(selectedFieldsList))

    const response = await axios.post('/api/config/import', formData, {
      headers: {'Content-Type': 'multipart/form-data'}
    })

    toast.success(`配置导入成功，已更新 ${response.data.affected_count} 项`)

    // 关闭弹窗
    showComparisonModal.value = false

    // 重新加载配置
    await loadConfig()

    // 清理导入状态
    setTimeout(() => {
      cancelImport()
    }, 1000)
  } catch (error: any) {
    console.error('Selective import failed:', error)
    const errorMsg = error.response?.data?.detail || '导入失败'
    toast.error(errorMsg)
  } finally {
    importing.value = false
  }
}

// 下载诊断报告
const downloadDiagnostics = async () => {
  exportingDiagnostics.value = true

  try {
    const response = await axios.get('/api/system/diagnostics/download', {
      responseType: 'blob'
    })

    // 从响应头获取文件名
    const contentDisposition = response.headers['content-disposition']
    let filename = 'diagnostics.json'
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename=(.+)/)
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1]
      }
    }

    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    toast.success('✅ 诊断报告已导出')
  } catch (error: any) {
    console.error('Export diagnostics failed:', error)
    const errorMsg = error.response?.data?.detail || '导出失败'
    toast.error(errorMsg)
  } finally {
    exportingDiagnostics.value = false
  }
}

// ========== UPS 高级配置功能 ==========

// 加载所有可写变量
const loadWritableVars = async () => {
  loadingWritableVars.value = true
  writableVarsError.value = null
  try {
    const response = await axios.get('/api/ups/writable-vars')
    writableVars.value = response.data.writable_vars

    // 提取当前值
    if (writableVars.value) {
      currentVoltageHigh.value = writableVars.value['input.transfer.high']?.value || null
      currentVoltageLow.value = writableVars.value['input.transfer.low']?.value || null
      currentSensitivity.value = writableVars.value['input.sensitivity']?.value || null
      currentShutdownDelay.value = writableVars.value['ups.delay.shutdown']?.value || null
    }
  } catch (error: any) {
    writableVarsError.value = error.response?.data?.detail || '加载可写变量失败'
    console.error('Failed to load writable vars:', error)
  } finally {
    loadingWritableVars.value = false
  }
}

// 设置 UPS 变量（内部函数）
const setUpsVar = async (varName: string, value: string) => {
  try {
    const response = await axios.post('/api/ups/set-var', {
      var_name: varName,
      value: value
    })
    if (!response.data.success) {
      throw new Error(response.data.message || '设置失败')
    }
    return response.data
  } catch (error: any) {
    throw error
  }
}

// 显示确认对话框并设置变量
const confirmAndSetUpsVar = (varName: string, value: string, onSuccess?: () => void) => {
  pendingUpsVar.value = {
    varName,
    value,
    callback: onSuccess
  }
  showUpsVarConfirm.value = true
}

// 确认设置 UPS 变量
const confirmSetUpsVar = async () => {
  showUpsVarConfirm.value = false
  
  // 如果有回调，说明调用方会处理整个流程
  if (pendingUpsVar.value.callback) {
    pendingUpsVar.value.callback()
    return
  }
  
  // 否则，这里处理标准的设置流程（用于将来可能的简单调用）
  try {
    await setUpsVar(pendingUpsVar.value.varName, pendingUpsVar.value.value)
    toast.success(`参数 ${pendingUpsVar.value.varName} 已成功修改`)
    // 重新加载可写变量以更新当前值
    await loadWritableVars()
  } catch (error: any) {
    const errorMsg = error.response?.data?.detail || error.message || '设置失败'
    toast.error(`设置失败: ${errorMsg}`)
  }
}

// 保存电压配置
const saveVoltageThresholds = async () => {
  if (newVoltageHigh.value === null || newVoltageHigh.value === undefined || 
      newVoltageLow.value === null || newVoltageLow.value === undefined) {
    toast.error('请输入高压和低压阈值')
    return
  }

  if (newVoltageLow.value >= newVoltageHigh.value) {
    toast.error('低压阈值必须小于高压阈值')
    return
  }

  const currentLow = writableVars.value?.['input.transfer.low']?.value
  const currentHigh = writableVars.value?.['input.transfer.high']?.value

  // 显示确认对话框
  pendingUpsVar.value = {
    varName: 'input.transfer.low & input.transfer.high',
    value: `低压=${newVoltageLow.value}V, 高压=${newVoltageHigh.value}V`,
    callback: async () => {
      savingVoltage.value = true
      try {
        // 智能排序：如果新 low 值更高，先设置 high 再设置 low，避免临时冲突
        // 如果新 high 值更低，先设置 low 再设置 high
        const oldLow = parseFloat(currentLow || '0')
        const oldHigh = parseFloat(currentHigh || '999')
        
        if (newVoltageLow.value! > oldHigh) {
          // 先提高 high，再提高 low
          await setUpsVar('input.transfer.high', newVoltageHigh.value!.toString())
          await setUpsVar('input.transfer.low', newVoltageLow.value!.toString())
        } else if (newVoltageHigh.value! < oldLow) {
          // 先降低 low，再降低 high
          await setUpsVar('input.transfer.low', newVoltageLow.value!.toString())
          await setUpsVar('input.transfer.high', newVoltageHigh.value!.toString())
        } else {
          // 安全情况：按正常顺序设置
          await setUpsVar('input.transfer.low', newVoltageLow.value!.toString())
          await setUpsVar('input.transfer.high', newVoltageHigh.value!.toString())
        }
        
        toast.success('电压配置已成功保存')
        // 重新加载以更新当前值
        await loadWritableVars()
        // 清空输入
        newVoltageHigh.value = null
        newVoltageLow.value = null
      } catch (error: any) {
        const errorMsg = error.response?.data?.detail || error.message || '保存失败'
        toast.error(`保存电压配置失败: ${errorMsg}`)
      } finally {
        savingVoltage.value = false
      }
    }
  }
  showUpsVarConfirm.value = true
}

// 保存灵敏度配置
const saveSensitivity = async () => {
  if (!newSensitivity.value) {
    toast.error('请选择灵敏度')
    return
  }

  confirmAndSetUpsVar('input.sensitivity', newSensitivity.value, async () => {
    savingSensitivity.value = true
    try {
      await setUpsVar('input.sensitivity', newSensitivity.value)
      toast.success('灵敏度配置已成功保存')
      // 重新加载以更新当前值
      await loadWritableVars()
      // 清空选择
      newSensitivity.value = ''
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '保存失败'
      toast.error(`保存灵敏度失败: ${errorMsg}`)
    } finally {
      savingSensitivity.value = false
    }
  })
}

// 保存关机延迟配置
const saveShutdownDelay = async () => {
  if (newShutdownDelay.value === null || newShutdownDelay.value === undefined) {
    toast.error('请输入关机延迟时间')
    return
  }

  confirmAndSetUpsVar('ups.delay.shutdown', newShutdownDelay.value.toString(), async () => {
    savingShutdownDelay.value = true
    try {
      await setUpsVar('ups.delay.shutdown', newShutdownDelay.value!.toString())
      toast.success('关机延迟配置已成功保存')
      // 重新加载以更新当前值
      await loadWritableVars()
      // 清空输入
      newShutdownDelay.value = null
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '保存失败'
      toast.error(`保存关机延迟失败: ${errorMsg}`)
    } finally {
      savingShutdownDelay.value = false
    }
  })
}

// ========== UPS 高级配置自动保存（onChange 触发） ==========

// 电压配置变化时自动保存
const onVoltageChange = () => {
  // 延迟检查，确保两个值都有机会输入
  setTimeout(() => {
    if (newVoltageHigh.value === null || newVoltageHigh.value === undefined ||
        newVoltageLow.value === null || newVoltageLow.value === undefined) {
      // 两个值未都填写完，不触发保存
      return
    }
    saveVoltageThresholds()
  }, 100)
}

// 灵敏度变化时自动保存
const onSensitivityChange = () => {
  if (newSensitivity.value) {
    saveSensitivity()
  }
}

// 关机延迟变化时自动保存
const onShutdownDelayChange = () => {
  if (newShutdownDelay.value !== null && newShutdownDelay.value !== undefined) {
    saveShutdownDelay()
  }
}

let errorRefreshTimer: number | null = null

onMounted(async () => {
  await loadConfig()
  configLoaded.value = true  // 标记配置已加载
  loadStorageInfo()
  loadPlugins()
  loadHookPlugins()
  // 加载配置后获取渠道错误状态
  await loadChannelErrors()
  // 加载 UPS 可写变量
  await loadWritableVars()
  // 加载监控统计
  loadMonitoringStats()

  // 每 10 秒刷新渠道错误状态和监控统计
  errorRefreshTimer = window.setInterval(() => {
    loadChannelErrors()
    loadMonitoringStats()
  }, 10000)
})

onUnmounted(() => {
  if (errorRefreshTimer) {
    clearInterval(errorRefreshTimer)
  }
  // 清除自动保存定时器
  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer)
  }
})

// 监听配置变化，自动保存
watch(
    config,
    () => {
      // 只有配置加载完成后才自动保存
      if (!configLoaded.value) return

      // 防抖：延迟 800ms 执行保存
      if (autoSaveTimer) {
        clearTimeout(autoSaveTimer)
      }
      autoSaveTimer = setTimeout(async () => {
        if (!validateConfig()) {
          // 验证失败不保存，但不显示 toast（错误已经显示在字段下方）
          return
        }

        saving.value = true
        try {
          await axios.put('/api/config', config.value)
          // 更新全局配置 store 的测试模式状态
          configStore.setTestMode(config.value.test_mode || 'production')
          // 显示保存成功提示
          toast.success('✅ 配置已自动保存')
        } catch (error) {
          console.error('Auto-save failed:', error)
          toast.error('自动保存失败')
        } finally {
          saving.value = false
        }
      }, 800)
    },
    {deep: true}
)
</script>

<style scoped>
.settings {
  max-width: 1800px;
  margin: 0 auto;
  padding: var(--ups-card-gap);
}

.settings h2 {
  margin-bottom: var(--ups-card-gap);
}

/* 四列网格布局 */
.settings-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--ups-card-gap);
  margin-bottom: var(--ups-card-gap);
}

/* 列容器 */
.settings-col {
  display: flex;
  flex-direction: column;
  gap: var(--ups-card-gap);
  min-width: 0;
  /* 支持子元素使用 order 属性排序 */
  flex-wrap: nowrap;
}

.card {
  margin-bottom: 0; /* 移除 margin，使用 grid gap */
}


/* 响应式: 中等屏幕（2列）*/
@media (max-width: 1199px) and (min-width: 768px) {
  .settings-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* 响应式: 移动端（1列）*/
@media (max-width: 767px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}

.file-upload-hint {
  margin-top: 0.5rem;
}

.file-upload-hint .btn-sm {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
}

/* 文档链接卡片 */
.settings-docs .card-title {
  margin-bottom: 0.75rem;
}

.docs-links {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
}

.doc-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 0.75rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  text-decoration: none;
  color: var(--text-primary);
  transition: all 0.2s;
  font-size: 0.875rem;
}

.doc-link:hover {
  background: var(--bg-tertiary);
  transform: translateX(2px);
}

.doc-icon {
  font-size: 1rem;
}

.doc-text {
  flex: 1;
}

.help-text {
  color: var(--text-secondary);
  font-size: 0.875rem;
  margin-top: 0.25rem;
  display: block;
}

.help-text.warning-text {
  color: #dc2626;
  font-weight: 500;
}

.warning-list {
  margin: 0.75rem 0;
  padding-left: 1.25rem;
  font-size: 0.875rem;
  color: var(--text-primary);
}

.warning-list li {
  margin-bottom: 0.375rem;
}

.help-icon {
  cursor: help;
  color: var(--text-tertiary);
  margin-left: 0.25rem;
}

.form-group {
  margin-bottom: var(--spacing-md);
}

.form-label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-control {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid var(--border-color, #ddd);
  border-radius: var(--radius-md);
  font-size: 1rem;
}

.form-control.error {
  border-color: #ef4444;
}

.error-text {
  color: #ef4444;
  font-size: 0.875rem;
  display: block;
  margin-top: 0.25rem;
}


.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: var(--radius-md);
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--color-primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-secondary {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-tertiary);
}

.btn-danger {
  background: var(--color-danger);
  color: white;
}

.btn-danger:hover:not(:disabled) {
  opacity: 0.9;
}

.storage-info {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1rem;
  padding: 1rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.storage-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.storage-label {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.storage-value {
  font-weight: 600;
  color: var(--text-primary);
}

/* 监控统计样式 */
.monitoring-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
  padding: 1rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.monitoring-stats-loading {
  padding: 1rem;
  text-align: center;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  margin-top: 1rem;
}

.stat-item {
  text-align: center;
  padding: 0.75rem;
  background: var(--bg-primary);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-bottom: 0.25rem;
  display: block;
}

.stat-value {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.status-ok {
  color: #10b981;
}

.status-warning {
  color: #f59e0b;
}

.subsection-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 1rem 0 0.75rem 0;
}

.section-divider {
  border: none;
  border-top: 1px solid var(--border-color);
  margin: 1.5rem 0;
}

.switch-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.form-checkbox {
  width: 1rem;
  height: 1rem;
  cursor: pointer;
}

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-dialog {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  max-width: 400px;
  width: 90%;
  box-shadow: var(--shadow-lg);
}

.modal-dialog.modal-lg {
  max-width: 600px;
}

.modal-dialog.modal-xl {
  max-width: 800px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
  padding-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: var(--text-secondary);
  padding: 0;
  line-height: 1;
}

.modal-close:hover {
  color: var(--text-primary);
}

.modal-footer {
  display: flex;
  gap: var(--spacing-md);
  justify-content: flex-end;
  margin-top: var(--spacing-lg);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--border-color);
}

/* 配置比较样式 */
.comparison-content {
  flex: 1;
  overflow-y: auto;
  max-height: 60vh;
}

.comparison-summary {
  display: flex;
  gap: 1.5rem;
  padding: 0.75rem 1rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  margin-bottom: 1rem;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.summary-label {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.summary-value {
  font-weight: 600;
}

.summary-item.modified .summary-value {
  color: #f59e0b;
}

.summary-item.unchanged .summary-value {
  color: #10b981;
}

.comparison-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.comparison-item {
  padding: 0.75rem 1rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--border-color);
}

.comparison-item.modified {
  border-left-color: #f59e0b;
}

.comparison-item.unchanged {
  border-left-color: #10b981;
  opacity: 0.7;
}

.comparison-field {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.field-label {
  font-weight: 600;
  color: var(--text-primary);
}

.field-key {
  font-size: 0.75rem;
  color: var(--text-tertiary);
  font-family: monospace;
}

.field-badge {
  font-size: 0.7rem;
  padding: 0.125rem 0.5rem;
  border-radius: 999px;
  margin-left: auto;
}

.field-badge.modified {
  background: #fef3c7;
  color: #92400e;
}

.field-badge.unchanged {
  background: #d1fae5;
  color: #065f46;
}

.comparison-values {
  margin-top: 0.5rem;
  font-size: 0.875rem;
}

.value-row {
  display: flex;
  gap: 0.5rem;
  padding: 0.25rem 0;
}

.value-label {
  color: var(--text-secondary);
  min-width: 60px;
}

.value-content {
  color: var(--text-primary);
  word-break: break-all;
}

.value-row.current .value-content {
  color: #dc2626;
  text-decoration: line-through;
}

.value-row.imported .value-content {
  color: #16a34a;
}

.value-details {
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px dashed var(--border-color);
}

.detail-item {
  display: flex;
  gap: 0.5rem;
  padding: 0.25rem 0;
  font-size: 0.8125rem;
}

.detail-action {
  min-width: 60px;
}

.detail-item.add .detail-action {
  color: #16a34a;
}

.detail-item.remove .detail-action {
  color: #dc2626;
}

.detail-item.modify .detail-action {
  color: #f59e0b;
}

.comparison-reason {
  font-size: 0.8125rem;
  color: var(--text-tertiary);
}

.modal-dialog h3 {
  margin-bottom: var(--spacing-md);
  color: var(--text-primary);
}

.modal-dialog p {
  margin-bottom: var(--spacing-sm);
  color: var(--text-secondary);
}

.modal-actions {
  display: flex;
  gap: var(--spacing-md);
  justify-content: flex-end;
  margin-top: var(--spacing-lg);
}

/* 通知渠道样式 */
.notify-channels {
  margin: 1rem 0;
}

.notify-channel-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  margin-bottom: 0.75rem;
  border: 1px solid transparent;
  transition: all 0.2s;
}

.notify-channel-item.channel-disabled {
  opacity: 0.6;
}

.notify-channel-item.channel-error {
  border-color: #ef4444;
  background: rgba(239, 68, 68, 0.05);
}

.channel-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.channel-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.channel-name-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.channel-name {
  font-weight: 500;
  color: var(--text-primary);
}

.channel-type-badge {
  font-size: 0.75rem;
  color: var(--text-secondary);
  padding: 0.125rem 0.5rem;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}

.channel-status-row {
  font-size: 0.8125rem;
}

.channel-status-text {
  color: var(--text-tertiary);
}

.channel-status-text.ok {
  color: #10b981;
}

.channel-status-text.disabled {
  color: var(--text-tertiary);
}

.channel-error-msg {
  color: #ef4444;
  font-size: 0.8125rem;
}

.channel-actions {
  display: flex;
  gap: 0.25rem;
}

/* 图标按钮样式 */
.btn-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.15s;
}

.btn-icon:hover:not(:disabled) {
  background: var(--bg-tertiary);
  transform: scale(1.1);
}

.btn-icon:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-icon-danger:hover:not(:disabled) {
  background: #fee2e2;
}

.btn-sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
}

/* 小尺寸开关 */
.switch-sm {
  width: 36px;
  height: 20px;
}

.switch-sm .slider:before {
  height: 14px;
  width: 14px;
  left: 3px;
  bottom: 3px;
}

.switch-sm input:checked + .slider:before {
  transform: translateX(16px);
}

.add-channel {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color);
}

.add-channel-row {
  display: flex;
  gap: 0.5rem;
}


.checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  color: var(--text-primary);
}

.checkbox-label input[type="checkbox"] {
  width: 1rem;
  height: 1rem;
}

.event-section {
  margin-top: 1rem;
  padding: 1rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.event-section:first-child {
  margin-top: 0.5rem;
}

.event-section-title {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-bottom: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.event-hint {
  font-size: 0.75rem;
  color: var(--text-tertiary);
  font-weight: normal;
  margin-left: 0.25rem;
}

.required {
  color: #ef4444;
}

.modal-lg {
  max-width: 500px;
}

.channel-editor {
  margin-top: 1rem;
}

.test-result {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
}

.test-result.success {
  background: #d1fae5;
  color: #065f46;
}

.test-result.error {
  background: #fee2e2;
  color: #991b1b;
}

.info-box {
  padding: 0.75rem 1rem;
  background: #dbeafe;
  border-left: 4px solid #3b82f6;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  color: #1e40af;
}

.empty-state {
  text-align: center;
  padding: 1.5rem;
  color: var(--text-tertiary);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

/* 通知开关样式 */
.notification-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding: 1rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.notification-toggle {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.toggle-label {
  font-weight: 500;
  color: var(--text-primary);
}

.notification-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-tertiary);
}

.status-dot.active {
  background: #10b981;
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.5);
}

.status-text {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

/* 开关按钮样式 */
.switch {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 26px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: 0.3s;
  border-radius: 26px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 20px;
  width: 20px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
}

.switch input:checked + .slider {
  background-color: var(--color-primary, #3b82f6);
}

.switch input:checked + .slider:before {
  transform: translateX(22px);
}

.switch input:disabled + .slider {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Hook 相关样式 */
.pre-shutdown-hooks {
  margin-top: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.hook-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-sm);
  border: 1px solid transparent;
  transition: all 0.2s;
}

.hook-item.hook-disabled {
  opacity: 0.6;
}

.hook-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  flex: 1;
}

.hook-info {
  flex: 1;
}

.hook-name-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.hook-name {
  font-weight: 500;
  color: var(--text-primary);
}

.hook-type-badge {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  background: var(--color-primary);
  color: white;
  border-radius: 12px;
  font-size: 0.75rem;
}

.hook-priority-badge {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border-radius: 12px;
  font-size: 0.75rem;
}

.hook-status-row {
  font-size: 0.8125rem;
}

.hook-status-text.ok {
  color: #10b981;
}

.hook-status-text.disabled {
  color: var(--text-tertiary);
}

.hook-actions {
  display: flex;
  gap: 0.25rem;
}

.add-hook {
  margin-top: var(--spacing-lg);
}

.add-hook-row {
  display: flex;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-sm);
}

.add-hook-row .form-control {
  flex: 1;
}

.hook-editor {
  max-height: calc(100vh - 200px);
  overflow-y: auto;
  padding-right: 0.5rem;
}

/* 配置导入/导出样式 */
.config-io-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.import-preview {
  margin-top: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.import-preview h4 {
  margin: 0 0 var(--spacing-md) 0;
  color: var(--text-primary);
  font-size: 1rem;
}

.preview-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: var(--spacing-md);
}

.preview-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.875rem;
}

.preview-label {
  color: var(--text-secondary);
}

.preview-value {
  font-weight: 500;
  color: var(--text-primary);
}

.import-mode-select {
  margin: var(--spacing-md) 0;
  padding: var(--spacing-md);
  background: var(--bg-primary);
  border-radius: var(--radius-md);
}

.radio-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  margin-top: 0.5rem;
}

.radio-label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: var(--spacing-sm);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: background-color 0.2s;
}

.radio-label:hover {
  background: var(--bg-secondary);
}

.radio-label input[type="radio"] {
  margin-right: 0.5rem;
}

.radio-label > span {
  display: flex;
  align-items: center;
  color: var(--text-primary);
}

.radio-label .help-text {
  margin-left: 1.5rem;
  font-size: 0.75rem;
}

.import-actions {
  display: flex;
  gap: var(--spacing-sm);
  justify-content: flex-end;
  margin-top: var(--spacing-md);
}

.import-result {
  margin-top: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
}

.import-result.success {
  background: #d1fae5;
  color: #065f46;
}

.import-result.error {
  background: #fee2e2;
  color: #991b1b;
}

/* 拖拽卡片样式 */
.draggable-card {
  position: relative;
  transition: transform 0.2s ease, opacity 0.2s ease, box-shadow 0.2s ease;
}

.draggable-card:hover .drag-handle {
  opacity: 1;
}

.drag-handle {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: grab;
  opacity: 0;
  transition: opacity 0.2s ease;
  z-index: 10;
  border-radius: 4px;
  background: var(--bg-secondary);
}

.drag-handle:hover {
  background: var(--bg-hover, var(--bg-tertiary));
}

.drag-handle:active {
  cursor: grabbing;
}

.drag-icon {
  font-size: 12px;
  color: var(--text-secondary);
  letter-spacing: 1px;
}

.draggable-card.is-dragging {
  opacity: 0.5;
  transform: scale(1.02);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}

.draggable-card.is-drop-target::before {
  content: '';
  position: absolute;
  top: -4px;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--color-primary, #3b82f6);
  border-radius: 2px;
  animation: dropPulse 1s ease-in-out infinite;
}

@keyframes dropPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.droppable-col {
  min-height: 100px;
  transition: background 0.2s ease;
}

.droppable-col.drag-over {
  background: rgba(59, 130, 246, 0.05);
  border-radius: var(--radius-md);
}

/* 布局重置按钮 */
.layout-reset-btn {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  z-index: 100;
  padding: 0.5rem 1rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-size: 0.75rem;
  color: var(--text-secondary);
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s ease, background 0.2s ease;
}

.settings:hover .layout-reset-btn {
  opacity: 0.6;
}

.layout-reset-btn:hover {
  opacity: 1 !important;
  background: var(--bg-tertiary);
}

/* UPS 高级配置样式 */
.ups-advanced-section {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--border-color);
}

.ups-advanced-section:first-child {
  margin-top: 0;
  padding-top: 0;
  border-top: none;
}

.section-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 1rem;
}

.value-comparison {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.current-value {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
}

.current-value .label {
  color: var(--text-secondary);
  font-weight: 500;
}

.current-value .value {
  color: var(--text-primary);
  font-weight: 600;
  font-family: 'Courier New', monospace;
}

.default-value {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: var(--bg-tertiary, #f0f0f0);
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
  border-left: 3px solid var(--color-info, #3b82f6);
}

.default-value .label {
  color: var(--text-secondary);
  font-weight: 500;
}

.default-value .value {
  color: var(--color-info, #3b82f6);
  font-weight: 600;
  font-family: 'Courier New', monospace;
}

.writable-vars-table {
  overflow-x: auto;
  margin-top: 1rem;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.data-table th,
.data-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.data-table th {
  background: var(--bg-secondary);
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.05em;
}

.data-table tbody tr:hover {
  background: var(--bg-secondary);
}

.data-table code {
  padding: 0.125rem 0.375rem;
  background: var(--bg-secondary);
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 0.813rem;
  color: var(--color-primary);
}

.var-description {
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: var(--text-secondary);
  line-height: 1.3;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.badge-success {
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
}

.badge-warning {
  background: rgba(251, 146, 60, 0.1);
  color: #fb923c;
}

.loading-text {
  padding: 1rem;
  text-align: center;
  color: var(--text-secondary);
  font-style: italic;
}

.saving-indicator {
  margin-top: 0.5rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  color: var(--color-primary);
  font-style: italic;
}
</style>
