<template>
  <div class="dashboard">
    <!-- 布局重置按钮 -->
    <button
      class="layout-reset-btn"
      @click="resetDashboardLayout"
      title="重置卡片布局为默认"
    >
      🔄 重置布局
    </button>

    <!-- 连接状态 -->
    <div v-if="!wsConnected" class="alert alert-warning">
      <span>⚠️ WebSocket 未连接，正在尝试重新连接...</span>
    </div>

    <!-- 手动关机确认对话框 -->
    <div v-if="showShutdownConfirm" class="modal-overlay" @click.self="!isShuttingDown && (showShutdownConfirm = false)">
      <div class="modal-dialog modal-confirm">
        <div class="modal-icon">⚠️</div>
        <h3>确认立即关机？</h3>
        <p class="shutdown-scope-notice"><strong>关机范围：本机（UPS Guard所在系统）</strong></p>
        <p>系统将执行完整的关机流程：</p>
        <ol class="shutdown-steps">
          <li>执行所有纳管设备的关机前置任务（pre-shutdown hooks）</li>
          <li>关闭所有纳管设备（按优先级顺序）</li>
          <li>关闭本机（UPS Guard宿主机）</li>
        </ol>
        <p class="warning-text">请确保已保存所有工作！</p>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showShutdownConfirm = false" :disabled="isShuttingDown">取消</button>
          <button
            class="btn btn-danger"
            @click="confirmManualShutdown"
            :disabled="isShuttingDown"
            :class="{ 'btn-loading': isShuttingDown }"
          >
            {{ isShuttingDown ? '关机中...' : '确认关机本机' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 设备关机确认对话框 -->
    <div v-if="showDeviceShutdownConfirm" class="modal-overlay" @click.self="!deviceOperating && (showDeviceShutdownConfirm = false)">
      <div class="modal-dialog modal-confirm">
        <div class="modal-icon">⚠️</div>
        <h3>确认关闭设备？</h3>
        <p class="shutdown-scope-notice"><strong>关机范围：该纳管设备 "{{ currentDevice?.name }}"</strong></p>
        <p>将立即关闭该纳管设备，不影响本机（UPS Guard系统）及其他设备。</p>
        <p class="warning-text">请确保该设备已保存所有工作！</p>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showDeviceShutdownConfirm = false" :disabled="deviceOperating">取消</button>
          <button
            class="btn btn-danger"
            @click="confirmDeviceShutdown"
            :disabled="deviceOperating"
            :class="{ 'btn-loading': deviceOperating }"
          >
            {{ deviceOperating ? '关机中...' : '确认关机该设备' }}
          </button>
        </div>
      </div>
    </div>

    <!-- UPS 参数编辑确认对话框 -->
    <div v-if="showUpsParamConfirm" class="modal-overlay" @click.self="!paramEditLoading && (showUpsParamConfirm = false)">
      <div class="modal-dialog modal-confirm">
        <div class="modal-icon">⚠️</div>
        <h3>确认修改？</h3>
        <p class="param-change-info">
          将 <strong>{{ pendingParamChange.description }}</strong> 从 
          <code>{{ pendingParamChange.oldValue }}</code> 修改为 
          <code>{{ pendingParamChange.newValue }}</code>
        </p>
        <p class="warning-text">⚠️ 此操作将直接修改 UPS 硬件参数</p>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showUpsParamConfirm = false" :disabled="paramEditLoading">取消</button>
          <button
            class="btn btn-primary"
            @click="confirmUpsParamChange"
            :disabled="paramEditLoading"
            :class="{ 'btn-loading': paramEditLoading }"
          >
            {{ paramEditLoading ? '修改中...' : '确认修改' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 电压安全区间编辑对话框 -->
    <div v-if="showVoltageRangeEdit" class="modal-overlay" @click.self="showVoltageRangeEdit = false">
      <div class="modal-dialog modal-edit">
        <h3>编辑电压安全区间</h3>
        <div class="edit-form">
          <div class="form-group">
            <label>下限 (V)</label>
            <input
              type="number"
              v-model.number="editVoltageRange.low"
              class="form-input"
              step="1"
              min="0"
            />
          </div>
          <div class="form-group">
            <label>上限 (V)</label>
            <input
              type="number"
              v-model.number="editVoltageRange.high"
              class="form-input"
              step="1"
              min="0"
            />
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showVoltageRangeEdit = false">取消</button>
          <button class="btn btn-primary" @click="saveVoltageRange">保存</button>
        </div>
      </div>
    </div>

    <!-- 输入灵敏度编辑对话框 -->
    <div v-if="showSensitivityEdit" class="modal-overlay" @click.self="showSensitivityEdit = false">
      <div class="modal-dialog modal-edit">
        <h3>设置输入灵敏度</h3>
        <div class="sensitivity-options">
          <button
            class="sensitivity-btn"
            :class="{ active: editSensitivity === 'low' }"
            @click="editSensitivity = 'low'"
          >
            低
          </button>
          <button
            class="sensitivity-btn"
            :class="{ active: editSensitivity === 'medium' }"
            @click="editSensitivity = 'medium'"
          >
            中
          </button>
          <button
            class="sensitivity-btn"
            :class="{ active: editSensitivity === 'high' }"
            @click="editSensitivity = 'high'"
          >
            高
          </button>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showSensitivityEdit = false">取消</button>
          <button class="btn btn-primary" @click="saveSensitivity">保存</button>
        </div>
      </div>
    </div>

    <!-- 关机延迟编辑对话框 -->
    <div v-if="showShutdownDelayEdit" class="modal-overlay" @click.self="showShutdownDelayEdit = false">
      <div class="modal-dialog modal-edit">
        <h3>编辑关机延迟</h3>
        <div class="edit-form">
          <div class="form-group">
            <label>延迟时间 (秒)</label>
            <input
              type="number"
              v-model.number="editShutdownDelay"
              class="form-input"
              step="1"
              min="0"
            />
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showShutdownDelayEdit = false">取消</button>
          <button class="btn btn-primary" @click="saveShutdownDelay">保存</button>
        </div>
      </div>
    </div>

    <!-- 执行命令对话框 (改为日志查看器) -->
    <div v-if="showLogsDialog" class="modal-overlay" @click.self="!logsLoading && (showLogsDialog = false)">
      <div class="modal-dialog modal-logs">
        <div class="logs-header">
          <h3>📋 设备日志</h3>
          <div class="logs-header-actions">
            <button
              v-if="logsContent"
              class="btn btn-sm btn-secondary"
              @click="copyLogs"
              title="复制日志"
            >
              📋 复制
            </button>
            <button
              class="btn-close"
              @click="showLogsDialog = false"
              :disabled="logsLoading"
            >
              ✕
            </button>
          </div>
        </div>
        
        <div class="logs-info">
          <span class="logs-device">设备：<strong>{{ currentDevice?.name }}</strong></span>
          <span v-if="logsCommand" class="logs-command" :title="logsCommand">
            命令：<code>{{ logsCommand }}</code>
          </span>
        </div>
        
        <div class="logs-content">
          <div v-if="logsLoading" class="logs-loading">
            <div class="spinner"></div>
            <span>正在获取日志...</span>
          </div>
          <div v-else-if="logsError" class="logs-error">
            <span>❌ 获取日志失败</span>
            <p>{{ logsError }}</p>
          </div>
          <pre v-else-if="logsContent" class="logs-text">{{ logsContent }}</pre>
          <div v-else class="logs-empty">暂无日志</div>
        </div>
        
        <div class="modal-actions">
          <button
            class="btn btn-secondary"
            @click="showLogsDialog = false"
            :disabled="logsLoading"
          >
            关闭
          </button>
          <button
            class="btn btn-primary"
            @click="fetchDeviceLogs"
            :disabled="logsLoading"
            :class="{ 'btn-loading': logsLoading }"
          >
            {{ logsLoading ? '加载中...' : '🔄 刷新' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 设备配置查看对话框 -->
    <div v-if="showDeviceConfigDialog" class="modal-overlay" @click.self="showDeviceConfigDialog = false">
      <div class="modal-dialog modal-config">
        <div class="modal-header">
          <h3>⚙️ 设备配置</h3>
          <button
            class="btn-close"
            @click="showDeviceConfigDialog = false"
          >
            ✕
          </button>
        </div>
        
        <div v-if="currentDevice" class="config-content">
          <div class="config-section">
            <div class="config-field">
              <label>设备名称</label>
              <div class="config-value">{{ currentDevice.name }}</div>
            </div>
            
            <div class="config-field">
              <label>设备类型</label>
              <div class="config-value">{{ getHookTypeName(currentDevice.hook_id) }}</div>
            </div>
            
            <div class="config-field">
              <label>优先级</label>
              <div class="config-value">{{ currentDevice.priority }}</div>
            </div>
            
            <div class="config-field">
              <label>状态</label>
              <div class="config-value">
                <span :class="currentDevice.online ? 'status-online' : 'status-offline'">
                  {{ currentDevice.online ? '🟢 在线' : '🔴 离线' }}
                </span>
              </div>
            </div>
          </div>
          
          <div class="config-section">
            <h4>连接配置</h4>
            <div v-for="(value, key) in currentDevice.config" :key="key" class="config-field">
              <label>{{ formatConfigKey(key) }}</label>
              <div class="config-value">
                <span v-if="isSensitiveField(key)" class="sensitive-value">********</span>
                <span v-else>{{ value || '(未设置)' }}</span>
              </div>
            </div>
          </div>
        </div>
        
        <div class="modal-actions">
          <button
            class="btn btn-secondary"
            @click="showDeviceConfigDialog = false"
          >
            关闭
          </button>
          <button
            class="btn btn-primary"
            @click="goToSettings"
          >
            前往设置页编辑
          </button>
        </div>
      </div>
    </div>

    <!-- 事件详情对话框 -->
    <div v-if="showEventDetailDialog" class="modal-overlay" @click.self="showEventDetailDialog = false">
      <div class="modal-dialog modal-event-detail">
        <div class="modal-header">
          <h3>📋 事件详情</h3>
          <button class="btn-close" @click="showEventDetailDialog = false">✕</button>
        </div>

        <div v-if="currentEvent" class="event-detail-content">
          <!-- 事件类型和时间 -->
          <div class="event-detail-header">
            <span class="event-type-badge" :class="`event-${currentEvent.event_type.toLowerCase()}`">
              {{ getEventTypeIcon(currentEvent.event_type) }} {{ getEventTypeText(currentEvent.event_type) }}
            </span>
            <span class="event-timestamp">{{ formatDateTime(currentEvent.timestamp) }}</span>
          </div>

          <!-- 事件消息 -->
          <div class="event-detail-section">
            <h4>事件描述</h4>
            <p class="event-message-detail">{{ currentEvent.message }}</p>
          </div>

          <!-- 元数据详情 -->
          <div v-if="currentEvent.metadata && Object.keys(parsedEventMetadata).length > 0" class="event-detail-section">
            <h4>详细信息</h4>
            <div class="event-metadata">
              <div v-for="(value, key) in parsedEventMetadata" :key="String(key)" class="metadata-item">
                <span class="metadata-key">{{ formatMetadataKey(String(key)) }}</span>
                <span class="metadata-value">{{ formatMetadataValue(value) }}</span>
              </div>
            </div>
          </div>

          <!-- 事件 ID -->
          <div class="event-detail-footer">
            <span class="event-id">事件 ID: #{{ currentEvent.id }}</span>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showEventDetailDialog = false">关闭</button>
        </div>
      </div>
    </div>

    <!-- 电池测试确认对话框 -->
    <div v-if="showBatteryTestConfirm" class="modal-overlay" @click.self="showBatteryTestConfirm = false">
      <div class="modal-dialog modal-battery-test-confirm">
        <div class="modal-header">
          <h3>{{ pendingTestType === 'quick' ? '⚡ 快速电池测试' : '🔋 深度电池测试' }}</h3>
          <button class="btn-close" @click="showBatteryTestConfirm = false">✕</button>
        </div>

        <div class="modal-body">
          <!-- 快速测试说明 -->
          <div v-if="pendingTestType === 'quick'" class="test-info-section">
            <div class="test-description">
              <p>快速测试会让 UPS <strong>短暂切换到电池供电</strong>（约 10-30 秒），检测电池是否能正常工作。</p>
            </div>

            <div class="test-checklist">
              <h4>✅ 测试前请确认：</h4>
              <ul>
                <li>🔌 <strong>市电已连接</strong> - 测试完成后 UPS 会自动切回市电</li>
                <li>💻 负载设备可以承受短暂的电池供电</li>
              </ul>
            </div>

            <div class="test-duration">
              <span class="duration-label">预计时长：</span>
              <span class="duration-value">30-60 秒</span>
            </div>
          </div>

          <!-- 深度测试说明 -->
          <div v-else class="test-info-section">
            <div class="test-description warning">
              <p>⚠️ 深度测试会让 UPS <strong>持续使用电池供电</strong>，直到电池电量降到低电量阈值（约 20%），用于准确评估电池健康状态。</p>
            </div>

            <div class="test-checklist">
              <h4>✅ 测试前请确认：</h4>
              <ul>
                <li>🔌 <strong>市电已连接</strong> - 测试完成后 UPS 会自动切回市电充电</li>
                <li>⚠️ 测试期间保护能力会下降（电池在放电）</li>
                <li>📊 建议在<strong>负载较低</strong>时进行测试</li>
                <li>⏰ 测试可能需要 <strong>5-15 分钟</strong>（取决于负载和电池状态）</li>
                <li>⏱️ 系统会<strong>自动监控最多 30 分钟</strong>，超时后自动完成测试</li>
                <li>✋ 可随时点击"停止测试"按钮手动结束</li>
              </ul>
            </div>

            <div class="test-warning-box">
              <span class="warning-icon">⚠️</span>
              <span>深度测试期间，如果发生真实断电，续航时间将比平时短！</span>
            </div>

            <div class="test-info-box">
              <div class="info-icon">💡</div>
              <div class="info-content">
                <strong>大容量UPS（2000VA+）用户请注意：</strong>
                <p>如果您的UPS容量较大，建议<strong>增加测试负载</strong>（如连接电脑、显示器等设备），否则可能需要超过30分钟才能降到20%电量。</p>
                <p>推荐负载：UPS额定功率的30-50%，可将测试时间控制在15-25分钟内。</p>
              </div>
            </div>

            <div class="test-duration">
              <span class="duration-label">预计时长：</span>
              <span class="duration-value">5-15 分钟</span>
              <span class="duration-note">（最长 30 分钟）</span>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showBatteryTestConfirm = false">
            取消
          </button>
          <button
            class="btn"
            :class="pendingTestType === 'quick' ? 'btn-primary' : 'btn-warning'"
            @click="confirmBatteryTest"
            :disabled="upsCommandLoading"
          >
            {{ pendingTestType === 'quick' ? '⚡ 开始快速测试' : '🔋 开始深度测试' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 测试报告对话框 -->
    <div v-if="showTestReportDialog" class="modal-overlay" @click.self="showTestReportDialog = false">
      <div class="modal-dialog modal-test-report">
        <div class="modal-header">
          <h3>📋 UPS 测试报告</h3>
          <button class="btn-close" @click="showTestReportDialog = false">✕</button>
        </div>

        <div v-if="testReportLoading" class="report-loading">
          <div class="loading-spinner"></div>
          <p>正在生成报告...</p>
        </div>

        <div v-else-if="testReport" class="report-content">
          <!-- 测试结果概览 -->
          <div class="report-section report-summary">
            <div class="test-type-badge" v-if="testReport.test_info.type_label">
              {{ testReport.test_info.type === 'quick' ? '⚡' : '🔋' }} {{ testReport.test_info.type_label }}
            </div>
            <div class="test-result-large" :class="`test-${testReport.test_info.status}`">
              <span class="result-icon-large">{{ testReport.test_info.icon }}</span>
              <span class="result-text">{{ testReport.test_info.result }}</span>
            </div>
            <div class="test-meta">
              <div class="test-date" v-if="testReport.test_info.started_at">
                开始时间：{{ formatDateTime(testReport.test_info.started_at) }}
              </div>
              <div class="test-date" v-if="latestHistoryReport && latestHistoryReport.duration_seconds">
                测试时长：{{ formatDurationSimple(latestHistoryReport.duration_seconds) }}
              </div>
            </div>
          </div>

          <!-- 测试前后数据对比（来自历史报告） -->
          <div class="report-section" v-if="latestHistoryReport && latestHistoryReport.result !== 'in_progress'">
            <h4>📊 测试前后数据对比</h4>
            <div class="comparison-table">
              <div class="comparison-header">
                <span></span>
                <span>测试前</span>
                <span>测试后</span>
                <span>变化</span>
              </div>
              <div class="comparison-row">
                <span class="comp-label">电量</span>
                <span>{{ latestHistoryReport.start_data?.battery_charge?.toFixed(1) ?? 'N/A' }}%</span>
                <span>{{ latestHistoryReport.end_data?.battery_charge?.toFixed(1) ?? 'N/A' }}%</span>
                <span :class="getChangeClass(latestHistoryReport.charge_change)">
                  {{ latestHistoryReport.charge_change !== null ? (latestHistoryReport.charge_change > 0 ? '+' : '') + latestHistoryReport.charge_change.toFixed(1) + '%' : 'N/A' }}
                </span>
              </div>
              <div class="comparison-row">
                <span class="comp-label">电压</span>
                <span>{{ latestHistoryReport.start_data?.battery_voltage?.toFixed(2) ?? 'N/A' }}V</span>
                <span>{{ latestHistoryReport.end_data?.battery_voltage?.toFixed(2) ?? 'N/A' }}V</span>
                <span :class="getChangeClass(getVoltageChange(latestHistoryReport))">
                  {{ formatVoltageChange(latestHistoryReport) }}
                </span>
              </div>
              <div class="comparison-row">
                <span class="comp-label">续航时间</span>
                <span>{{ formatRuntimeMinutes(latestHistoryReport.start_data?.battery_runtime) }}</span>
                <span>{{ formatRuntimeMinutes(latestHistoryReport.end_data?.battery_runtime) }}</span>
                <span>-</span>
              </div>
            </div>
          </div>

          <!-- 采样数据图表 -->
          <div class="report-section" v-if="latestHistoryReport && latestHistoryReport.samples && latestHistoryReport.samples.length > 1">
            <h4>📈 电量变化曲线 ({{ latestHistoryReport.sample_count }} 个采样点)</h4>
            <div class="samples-chart-mini">
              <div class="chart-bars-mini">
                <div
                  v-for="(sample, index) in latestHistoryReport.samples"
                  :key="index"
                  class="chart-bar-mini"
                  :style="{ height: `${sample.battery_charge || 0}%` }"
                  :title="`${sample.battery_charge?.toFixed(1)}%`"
                ></div>
              </div>
              <div class="chart-labels-mini">
                <span>开始</span>
                <span>结束</span>
              </div>
            </div>
          </div>

          <!-- UPS 信息 -->
          <div class="report-section">
            <h4>🔌 UPS 信息</h4>
            <div class="report-grid">
              <div class="report-item">
                <span class="label">制造商</span>
                <span class="value">{{ testReport.ups_info.manufacturer }}</span>
              </div>
              <div class="report-item">
                <span class="label">型号</span>
                <span class="value">{{ testReport.ups_info.model }}</span>
              </div>
              <div class="report-item">
                <span class="label">序列号</span>
                <span class="value">{{ testReport.ups_info.serial }}</span>
              </div>
              <div class="report-item">
                <span class="label">额定功率</span>
                <span class="value">{{ testReport.ups_info.nominal_power }}W</span>
              </div>
            </div>
          </div>

          <!-- 当前状态 -->
          <div class="report-section">
            <h4>📊 当前状态</h4>
            <div class="status-flags">
              <span
                v-for="flag in testReport.current_status.status_flags"
                :key="flag.flag"
                class="status-flag-badge"
              >
                {{ flag.description }}
              </span>
            </div>
            <div class="report-grid">
              <div class="report-item">
                <span class="label">负载</span>
                <span class="value">{{ testReport.current_status.load_percent }}%</span>
              </div>
              <div class="report-item">
                <span class="label">输入电压</span>
                <span class="value">{{ testReport.current_status.input_voltage }}V</span>
              </div>
              <div class="report-item">
                <span class="label">输出电压</span>
                <span class="value">
                  {{ testReport.current_status.output_voltage }}V
                  <span v-if="testReport.current_status.output_voltage_estimated" class="voltage-source-badge estimated" title="根据输入电压和UPS状态推算">📊 推断</span>
                </span>
              </div>
            </div>
          </div>

          <!-- 电池信息 -->
          <div class="report-section">
            <h4>🔋 电池信息</h4>
            <div class="report-grid">
              <div class="report-item">
                <span class="label">电量</span>
                <span class="value">{{ testReport.battery_info.charge_percent }}%</span>
              </div>
              <div class="report-item">
                <span class="label">电压</span>
                <span class="value">{{ testReport.battery_info.voltage }}V / {{ testReport.battery_info.voltage_nominal }}V</span>
              </div>
              <div class="report-item">
                <span class="label">剩余时间</span>
                <span class="value">{{ testReport.battery_info.runtime_display }}</span>
              </div>
              <div class="report-item">
                <span class="label">电池类型</span>
                <span class="value">{{ testReport.battery_info.type }}</span>
              </div>
              <div class="report-item" v-if="testReport.battery_info.temperature !== 'N/A'">
                <span class="label">温度</span>
                <span class="value">{{ testReport.battery_info.temperature }}°C</span>
              </div>
            </div>
          </div>

          <!-- 蜂鸣器状态 -->
          <div class="report-section">
            <h4>🔔 蜂鸣器</h4>
            <div class="report-item">
              <span class="label">状态</span>
              <span class="value">{{ formatBeeperStatus(testReport.beeper.status) }}</span>
            </div>
          </div>

          <!-- 报告生成时间 -->
          <div class="report-footer">
            <span>报告生成时间：{{ formatDateTime(testReport.generated_at) }}</span>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn btn-primary" @click="downloadTestReport" :disabled="!testReport">
            📥 下载报告
          </button>
          <button class="btn btn-secondary" @click="showTestReportDialog = false">关闭</button>
        </div>
      </div>
    </div>

    <!-- 初始加载状态（骨架屏，最高优先级，3秒内显示） -->
    <div v-if="isInitialLoading" class="loading-panel">
      <div class="skeleton-container">
        <div class="skeleton-col">
          <div class="skeleton-card skeleton-card-status"></div>
          <div class="skeleton-card skeleton-card-predictions"></div>
          <div class="skeleton-card skeleton-card-short"></div>
        </div>
        <div class="skeleton-col">
          <div class="skeleton-card skeleton-card-voltage"></div>
          <div class="skeleton-card skeleton-card-battery"></div>
          <div class="skeleton-card skeleton-card-device"></div>
        </div>
        <div class="skeleton-col">
          <div class="skeleton-card skeleton-card-events"></div>
          <div class="skeleton-card skeleton-card-short"></div>
          <div class="skeleton-card skeleton-card-short"></div>
        </div>
      </div>
      <p class="loading-text">正在连接 UPS 服务...</p>
    </div>

    <!-- 核心数据区域：三列布局 - 有数据时显示 -->
    <div v-else-if="upsData" class="dashboard-core-grid">
      <!-- 动态渲染三列 -->
      <template v-for="colKey in (['col1', 'col2', 'col3'] as const)" :key="colKey">
        <div
          class="dashboard-col droppable-col"
          :class="[`dashboard-${colKey}`, { 'drag-over': dragState.targetCol === colKey }]"
          @dragover.prevent="(e) => handleColDragOver(e, colKey)"
          @drop="(e) => handleDrop(e, colKey)"
        >
          <!-- 根据卡片顺序渲染 -->
          <template v-for="(cardId, cardIndex) in userPrefs.dashboardCardOrder[colKey]" :key="cardId">
            <!-- 拖拽占位符 -->
            <div
              v-if="dragState.isDragging && dragState.targetCol === colKey && dragState.targetIndex === cardIndex"
              class="drop-placeholder"
            ></div>

            <!-- 主状态卡片 -->
            <div
              v-if="cardId === 'status'"
              class="card status-card-compact draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'status' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'status', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <div class="status-header-row">
                <div class="status-indicator" :style="{ backgroundColor: statusColor }"></div>
                <div class="status-info">
                  <h2 class="status-title">{{ statusText }}</h2>
                  <!-- 详细状态标志 -->
                  <div v-if="upsData.status_flags && upsData.status_flags.length > 0" class="status-flags">
                    <span
                      v-for="flag in upsData.status_flags"
                      :key="flag"
                      class="status-flag"
                      :class="getStatusFlagClass(flag)"
                      :title="getStatusFlagTooltip(flag)"
                    >
                      {{ getStatusFlagIcon(flag) }} {{ getStatusFlagLabel(flag) }}
                    </span>
                  </div>
                  <p class="status-subtitle">{{ upsData.ups_manufacturer }} {{ upsData.ups_model }}</p>
                  <p class="status-serial" v-if="upsData.ups_serial">
                    <small>S/N: {{ upsData.ups_serial }}</small>
                  </p>
                </div>
                <button
                  v-if="upsData.shutdown?.shutting_down"
                  class="btn btn-warning btn-sm"
                  @click="cancelShutdown"
                  :disabled="isCancelling"
                >
                  {{ isCancelling ? '取消中...' : '取消关机' }}
                </button>
                <button
                  v-else-if="devices.length > 0 && allDevicesOffline"
                  class="btn btn-success btn-sm"
                  @click="wakeAllDevices"
                  :disabled="deviceOperating"
                >
                  ⏻ 全部开机
                </button>
                <button
                  v-else-if="(upsData.status === 'ON_BATTERY' || upsData.status === 'LOW_BATTERY') && devices.length > 0 && !allDevicesOffline"
                  class="btn btn-danger btn-sm"
                  @click="showShutdownConfirm = true"
                >
                  🔌 立即关机
                </button>
              </div>
              <div class="battery-compact">
                <div class="battery-header">
                  <span class="battery-label">电池电量</span>
                  <span class="battery-percent" :style="{ color: getBatteryColor(upsData.battery_charge) }">
                    {{ upsData.battery_charge ?? 0 }}%
                  </span>
                </div>
                <div class="battery-progress-bar">
                  <div
                    class="battery-progress-fill"
                    :style="{
                      width: `${upsData.battery_charge ?? 0}%`,
                      backgroundColor: getBatteryColor(upsData.battery_charge)
                    }"
                  ></div>
                </div>
                <div class="battery-runtime">
                  <span class="runtime-icon">🕐</span>
                  <span v-if="upsData.battery_runtime">
                    {{ upsData.runtime_estimated ? '估算续航' : 'UPS 报告续航' }}: {{ formatRuntimeDetailed(upsData.battery_runtime) }}
                    <span v-if="upsData.runtime_estimated" class="runtime-source-badge estimated" title="由 NUT runtimecal 参数根据电池电量和负载估算，可能与实际有偏差">📐 估算</span>
                    <span v-else class="runtime-source-badge hardware" title="由 UPS 硬件直接报告">📡 硬件</span>
                  </span>
                  <span v-else>续航时间未知</span>
                </div>
              </div>
              <div class="status-time">
                <small :key="upsData?.last_update">更新于 {{ formattedLastUpdate }}</small>
              </div>
            </div>

            <!-- 能耗分析卡片 -->
            <div
              v-else-if="cardId === 'energy' && energyStats"
              class="card draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'energy' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'energy', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <div class="card-header-inline">
                <span class="card-icon">💰</span>
                <span class="card-title-inline">能耗分析</span>
              </div>
              <div class="energy-stats-grid">
                <div class="energy-stat-item">
                  <span class="stat-label">今日预估</span>
                  <span class="stat-value">{{ energyStats.todayKwh }} kWh</span>
                  <span class="stat-cost">≈ ¥{{ energyStats.todayCost }}</span>
                </div>
                <div class="energy-stat-item">
                  <span class="stat-label">月度预估</span>
                  <span class="stat-value">{{ energyStats.monthlyKwh }} kWh</span>
                  <span class="stat-cost">≈ ¥{{ energyStats.monthlyCost }}</span>
                </div>
              </div>
              <div class="efficiency-tip" v-if="energyStats.efficiencyTip">
                💡 {{ energyStats.efficiencyTip }}
              </div>
            </div>

            <!-- 电池详情卡片 -->
            <div
              v-else-if="cardId === 'battery-detail' && (upsData.battery_type || upsData.battery_date || upsData.battery_mfr_date || upsData.battery_packs || upsData.battery_charger_status)"
              class="card draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'battery-detail' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'battery-detail', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <div class="card-header-inline">
                <span class="card-icon">🔋</span>
                <span class="card-title-inline">电池详情</span>
              </div>
              <div class="battery-info-content">
                <div class="battery-info-row" v-if="upsData.battery_type">
                  <span class="info-label">类型</span>
                  <span class="info-value">{{ batteryTypeLabel }}</span>
                </div>
                
                <!-- 电池日期信息区域 -->
                <!-- 生产日期（如果有） -->
                <div class="battery-info-row" v-if="upsData.battery_mfr_date && !isPlaceholderDate(upsData.battery_mfr_date)">
                  <span class="info-label">🏭 生产日期</span>
                  <span class="info-value">
                    {{ upsData.battery_mfr_date }}
                    <span class="date-source">(UPS硬件)</span>
                  </span>
                </div>
                
                <!-- 安装日期 -->
                <div class="battery-info-row battery-date-section">
                  <span class="info-label">
                    {{ effectiveBatteryDate.icon }} {{ effectiveBatteryDate.label }}
                  </span>
                  
                  <template v-if="!editingBatteryDate">
                    <span class="info-value" v-if="effectiveBatteryDate.date">
                      {{ effectiveBatteryDate.date }}
                      <span class="date-source" v-if="effectiveBatteryDate.source === 'user'">
                        (用户设置)
                      </span>
                      <span class="date-source" v-else-if="effectiveBatteryDate.source === 'hardware'">
                        (使用生产日期)
                      </span>
                    </span>
                    <span class="info-value not-set" v-else>未设置</span>
                    <button 
                      class="edit-date-btn"
                      @click="startEditBatteryDate"
                      title="编辑电池安装日期"
                    >✏️</button>
                  </template>
                  
                  <template v-else>
                    <div class="date-edit-form">
                      <input 
                        type="date"
                        v-model="newBatteryDate"
                        class="date-input"
                        :max="new Date().toISOString().split('T')[0]"
                      />
                      <button class="save-btn" @click="saveBatteryDate">💾</button>
                      <button class="cancel-btn" @click="cancelEditBatteryDate">❌</button>
                    </div>
                  </template>
                </div>
                
                <!-- 电池使用时长 -->
                <div class="battery-info-row" v-if="batteryAge">
                  <span class="info-label">电池使用时长</span>
                  <span class="info-value" :class="batteryAgeClass">
                    {{ batteryAge }}
                  </span>
                </div>
                
                <div class="battery-info-row" v-if="upsData.battery_charger_status">
                  <span class="info-label">充电器</span>
                  <span class="info-value" :class="batteryChargerStatusClass">
                    {{ formatBatteryChargerStatus(upsData.battery_charger_status) }}
                  </span>
                </div>
                <div class="battery-info-row" v-if="upsData.battery_packs">
                  <span class="info-label">电池组</span>
                  <span class="info-value">
                    {{ (upsData.battery_packs - (upsData.battery_packs_bad || 0)) }} / {{ upsData.battery_packs }} 正常
                  </span>
                </div>
              </div>
            </div>

            <!-- 电压质量卡片 -->
            <div
              v-else-if="cardId === 'voltage-quality' && (upsData.input_transfer_low || upsData.input_transfer_high)"
              class="card draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'voltage-quality' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'voltage-quality', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <div class="card-header-inline">
                <span class="card-icon">⚡</span>
                <span class="card-title-inline">电压质量</span>
              </div>
              <div class="voltage-range-display">
                <div class="voltage-current-display">
                  <span class="voltage-current-label">当前电压</span>
                  <span class="voltage-current-value" :class="voltageQualityClass">
                    {{ upsData.input_voltage !== null && upsData.input_voltage !== undefined ? `${upsData.input_voltage} V` : 'N/A' }}
                  </span>
                </div>
                <div class="voltage-info-row" v-if="upsData.input_voltage_min || upsData.input_voltage_max">
                  <span class="voltage-label">波动范围</span>
                  <span class="voltage-value-small">
                    {{ upsData.input_voltage_min || 'N/A' }} - {{ upsData.input_voltage_max || 'N/A' }} V
                  </span>
                </div>
                <div class="voltage-info-row">
                  <span class="voltage-label">安全区间</span>
                  <span class="voltage-value-small voltage-editable" @click="openVoltageRangeEdit" title="点击编辑">
                    {{ upsData.input_transfer_low || 'N/A' }} - {{ upsData.input_transfer_high || 'N/A' }} V
                    <span class="edit-icon">✏️</span>
                  </span>
                </div>
                <div class="voltage-info-row" v-if="upsData.input_voltage_nominal || inferredNominalVoltage">
                  <span class="voltage-label">额定电压</span>
                  <span class="voltage-value-small">
                    {{ upsData.input_voltage_nominal || inferredNominalVoltage }} V
                    <span v-if="!upsData.input_voltage_nominal && inferredNominalVoltage" class="voltage-source-badge estimated" title="根据输入电压自动推断">📊 推断</span>
                  </span>
                </div>
                <div class="voltage-info-row" v-if="upsData.input_transfer_reason">
                  <span class="voltage-label">切换原因</span>
                  <span class="voltage-value-small">{{ formatTransferReason(upsData.input_transfer_reason) }}</span>
                </div>
                <div class="voltage-info-row" v-if="upsData.input_sensitivity">
                  <span class="voltage-label">灵敏度</span>
                  <span class="voltage-value-small">{{ formatSensitivity(upsData.input_sensitivity) }}</span>
                </div>
                <div class="voltage-status-bar">
                  <div class="voltage-marker" :style="voltageMarkerPosition"></div>
                </div>
              </div>
            </div>

            <!-- 最近事件卡片 -->
            <div
              v-else-if="cardId === 'events'"
              class="card events-card-compact draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'events' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'events', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title-compact">最近事件</h3>
              <div v-if="recentEvents.length === 0" class="empty-state-compact">
                暂无事件记录
              </div>
              <div v-else class="events-table-compact">
                <div
                  v-for="event in recentEvents.slice(0, 8)"
                  :key="event.id"
                  class="event-row-compact clickable"
                  @click="showEventDetail(event)"
                  title="点击查看详情"
                >
                  <span class="event-type-compact" :class="`event-${event.event_type.toLowerCase()}`">
                    {{ getEventTypeText(event.event_type) }}
                  </span>
                  <span class="event-message-compact">{{ event.message }}</span>
                  <span class="event-time-compact">{{ formatDateTime(event.timestamp) }}</span>
                </div>
              </div>
            </div>

            <!-- 电力指标卡片 -->
            <div
              v-else-if="cardId === 'power-metrics'"
              class="card draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'power-metrics' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'power-metrics', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title-compact">⚡ 电力指标</h3>
              <div class="metrics-grid-compact">
                <div class="metric-item-compact">
                  <span class="metric-label">输入电压</span>
                  <span class="metric-value">{{ upsData.input_voltage !== null && upsData.input_voltage !== undefined ? `${upsData.input_voltage} V` : 'N/A' }}</span>
                </div>
                <div class="metric-item-compact">
                  <span class="metric-label">输出电压</span>
                  <span class="metric-value">
                    {{ upsData.output_voltage ? `${upsData.output_voltage} V` : 'N/A' }}
                    <span v-if="upsData.output_voltage_estimated" class="voltage-source-badge estimated" title="根据输入电压和UPS状态推算">📊 推断</span>
                  </span>
                </div>
                <div class="metric-item-compact">
                  <span class="metric-label">负载</span>
                  <span class="metric-value">{{ upsData.load_percent !== null && upsData.load_percent !== undefined ? `${upsData.load_percent}%` : 'N/A' }}</span>
                </div>
                <div class="metric-item-compact">
                  <span class="metric-label">功率</span>
                  <span class="metric-value">{{ computedPower !== null ? `${computedPower} W` : 'N/A' }}</span>
                </div>
                <div class="metric-item-compact" v-if="upsData.input_frequency">
                  <span class="metric-label">输入频率</span>
                  <span class="metric-value" :class="{ 'freq-warning': frequencyDeviation > 1 }">
                    {{ upsData.input_frequency ? `${upsData.input_frequency.toFixed(1)} Hz` : 'N/A' }}
                  </span>
                </div>
                <div class="metric-item-compact" v-if="upsData.output_current">
                  <span class="metric-label">输出电流</span>
                  <span class="metric-value">
                    {{ upsData.output_current ? `${upsData.output_current.toFixed(2)} A` : 'N/A' }}
                  </span>
                </div>
                <div class="metric-item-compact" v-if="upsData.ups_efficiency">
                  <span class="metric-label">UPS 效率</span>
                  <span class="metric-value" :class="efficiencyClass">
                    {{ upsData.ups_efficiency ? `${upsData.ups_efficiency.toFixed(1)}%` : 'N/A' }}
                  </span>
                </div>
              </div>
            </div>

            <!-- 电池状态卡片 -->
            <div
              v-else-if="cardId === 'battery-status'"
              class="card draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'battery-status' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'battery-status', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title-compact">🔋 电池状态</h3>
              <div class="metrics-grid-compact">
                <div class="metric-item-compact">
                  <span class="metric-label">电池健康</span>
                  <span class="metric-value" :class="batteryHealthClass">
                    {{ batteryHealthPercent !== null ? `${batteryHealthPercent}%` : 'N/A' }}
                  </span>
                </div>
                <div class="metric-item-compact" v-if="showBothTemperatures">
                  <span class="metric-label">UPS温度</span>
                  <span class="metric-value">{{ upsData.temperature?.toFixed(1) }}°C</span>
                </div>
                <div class="metric-item-compact" v-if="showBothTemperatures">
                  <span class="metric-label">电池温度</span>
                  <span class="metric-value" :class="{ 'temp-warning': batteryTempHigh }">
                    {{ upsData.battery_temperature?.toFixed(1) }}°C
                  </span>
                </div>
                <div class="metric-item-compact" v-if="!showBothTemperatures && batteryTemp !== null">
                  <span class="metric-label">温度</span>
                  <span class="metric-value" :class="{ 'temp-warning': batteryTempHigh }">
                    {{ batteryTemp }}°C
                  </span>
                </div>
              </div>
              <div class="battery-sparkline" v-if="metrics.length > 0">
                <div class="sparkline-header">
                  <span class="sparkline-label">近期电量</span>
                  <span class="sparkline-value">{{ latestBatteryCharge }}%</span>
                </div>
                <div class="sparkline-chart">
                  <svg :viewBox="`0 0 ${sparklineWidth} ${sparklineHeight}`" class="sparkline-svg">
                    <polyline
                      :points="sparklinePoints"
                      fill="none"
                      :stroke="sparklineColor"
                      stroke-width="2"
                      stroke-linejoin="round"
                      stroke-linecap="round"
                    />
                    <polygon
                      :points="sparklineAreaPoints"
                      :fill="sparklineColor"
                      fill-opacity="0.1"
                    />
                  </svg>
                </div>
              </div>
            </div>

            <!-- 环境监控卡片 -->
            <div
              v-else-if="cardId === 'environment' && (upsData.ambient_temperature || upsData.ambient_humidity)"
              class="card draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'environment' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'environment', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <div class="card-header-inline">
                <span class="card-icon">🌡️</span>
                <span class="card-title-inline">环境监控</span>
              </div>
              <div class="environment-metrics">
                <div class="env-metric-item" v-if="upsData.ambient_temperature">
                  <span class="env-icon">🌡️</span>
                  <div class="env-details">
                    <span class="env-label">环境温度</span>
                    <span class="env-value" :class="ambientTempClass">
                      {{ upsData.ambient_temperature.toFixed(1) }}°C
                    </span>
                  </div>
                </div>
                <div class="env-metric-item" v-if="upsData.ambient_humidity">
                  <span class="env-icon">💧</span>
                  <div class="env-details">
                    <span class="env-label">湿度</span>
                    <span class="env-value" :class="ambientHumidityClass">
                      {{ upsData.ambient_humidity.toFixed(0) }}%
                    </span>
                  </div>
                </div>
              </div>
              <div class="comfort-index" v-if="environmentComfort">
                <span class="comfort-label">舒适度：</span>
                <span class="comfort-value" :class="environmentComfort.class">
                  {{ environmentComfort.label }}
                </span>
              </div>
            </div>

            <!-- 自检状态卡片 -->
            <div
              v-else-if="cardId === 'self-test' && (upsData.ups_test_result || upsData.ups_test_date || upsData.ups_beeper_status)"
              class="card draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'self-test' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'self-test', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <div class="card-header-inline">
                <span class="card-icon">🔍</span>
                <span class="card-title-inline">自检状态</span>
              </div>
              <div class="test-info">
                <div class="test-result" :class="testResultClass">
                  <span class="result-icon">{{ testResultIcon }}</span>
                  <span>{{ upsData.ups_test_result || '未测试' }}</span>
                </div>
                <div class="test-date" v-if="upsData.ups_test_date">
                  上次自检：{{ upsData.ups_test_date }}
                </div>
                <div class="test-date" v-if="upsData.ups_beeper_status">
                  蜂鸣器：{{ formatBeeperStatus(upsData.ups_beeper_status) }}
                </div>
              </div>
              <!-- UPS 控制区域 -->
              <div class="ups-controls" v-if="upsData">
                <!-- 蜂鸣器控制 -->
                <div class="control-group">
                  <span class="control-label">蜂鸣器</span>
                  <div class="control-actions">
                    <button
                      class="btn btn-sm"
                      :class="upsData.ups_beeper_status === 'enabled' ? 'btn-success' : 'btn-secondary'"
                      @click="toggleBeeper"
                      :disabled="beeperToggleLoading || beeperMuteLoading"
                      title="控制告警时蜂鸣器是否响起"
                    >
                      <span v-if="beeperToggleLoading" class="spinner-border spinner-border-sm me-1"></span>
                      {{ beeperToggleLoading ? '处理中...' : (upsData.ups_beeper_status === 'enabled' ? '🔔 已启用' : '🔕 已禁用') }}
                    </button>
                    <button
                      v-if="upsData.ups_beeper_status === 'enabled'"
                      class="btn btn-sm btn-secondary"
                      @click="muteBeeper"
                      :disabled="beeperToggleLoading || beeperMuteLoading"
                      title="临时静音当前告警"
                    >
                      <span v-if="beeperMuteLoading" class="spinner-border spinner-border-sm me-1"></span>
                      {{ beeperMuteLoading ? '处理中...' : '🔇 静音' }}
                    </button>
                  </div>
                </div>
                <!-- 电池测试 -->
                <div class="control-group">
                  <span class="control-label">电池测试</span>
                  <div class="control-actions">
                    <button
                      v-if="!isBatteryTesting"
                      class="btn btn-sm btn-primary"
                      @click="startBatteryTest('quick')"
                      :disabled="batteryTestLoading"
                    >
                      <span v-if="batteryTestLoading" class="spinner-border spinner-border-sm me-1"></span>
                      {{ batteryTestLoading ? '启动中...' : '⚡ 快速测试' }}
                    </button>
                    <button
                      v-if="!isBatteryTesting"
                      class="btn btn-sm btn-warning"
                      @click="startBatteryTest('deep')"
                      :disabled="batteryTestLoading"
                    >
                      <span v-if="batteryTestLoading" class="spinner-border spinner-border-sm me-1"></span>
                      {{ batteryTestLoading ? '启动中...' : '🔋 深度测试' }}
                    </button>
                    <button
                      v-if="isBatteryTesting"
                      class="btn btn-sm btn-danger"
                      @click="stopBatteryTest"
                      :disabled="batteryTestLoading"
                    >
                      <span v-if="batteryTestLoading" class="spinner-border spinner-border-sm me-1"></span>
                      {{ batteryTestLoading ? '停止中...' : '⏹ 停止测试' }}
                    </button>
                    <button
                      class="btn btn-sm btn-secondary"
                      @click="showTestReport"
                      :disabled="testReportLoading"
                    >
                      📋 查看报告
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 功率趋势图卡片 -->
            <div
              v-else-if="cardId === 'power-chart'"
              class="draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'power-chart' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'power-chart', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <PowerChart v-if="upsData" title="功率趋势" :metrics="metrics" />
            </div>

            <!-- 电池寿命预测卡片 -->
            <div
              v-else-if="cardId === 'battery-life' && batteryLifePrediction"
              class="card draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'battery-life' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'battery-life', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <div class="card-header-inline">
                <span class="card-icon">🔮</span>
                <span class="card-title-inline">寿命预测</span>
              </div>
              <div class="prediction-content">
                <div class="life-remaining-bar">
                  <div class="life-fill" :style="{ width: `${batteryLifePrediction.remainingPercent}%` }">
                  </div>
                </div>
                <div class="prediction-text">
                  预计剩余：{{ batteryLifePrediction.remainingMonths }} 个月
                </div>
                <div class="prediction-suggestion">
                  {{ batteryLifePrediction.suggestion }}
                </div>
              </div>
            </div>

            <!-- 智能预测卡片 -->
            <div
              v-else-if="cardId === 'predictions'"
              class="card predictions-card-compact draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'predictions' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'predictions', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title-compact">🔮 智能预测</h3>
              <div v-if="predictions && hasPredictions" class="predictions-compact-grid">
                <div class="prediction-item-compact" v-if="predictions.battery_health?.available">
                  <div class="prediction-compact-header">
                    <span class="prediction-compact-icon">🔋</span>
                    <span class="prediction-compact-title">健康度</span>
                  </div>
                  <div class="prediction-compact-value">{{ predictions.battery_health.health_percent }}%</div>
                  <div class="prediction-compact-meta">{{ predictions.battery_health.estimated_months_remaining }}月寿命</div>
                </div>
                <div class="prediction-item-compact" v-if="predictions.outage_duration?.available">
                  <div class="prediction-compact-header">
                    <span class="prediction-compact-icon">⚡</span>
                    <span class="prediction-compact-title">停电</span>
                  </div>
                  <div class="prediction-compact-value">{{ formatMinutes(predictions.outage_duration.predicted_duration_minutes) }}</div>
                  <div class="prediction-compact-meta">{{ predictions.outage_duration.confidence_percent }}% 置信</div>
                </div>
                <div class="prediction-item-compact" v-if="upsData?.battery_runtime">
                  <div class="prediction-compact-header">
                    <span class="prediction-compact-icon">🔋</span>
                    <span class="prediction-compact-title">AI 续航</span>
                  </div>
                  <div class="prediction-compact-value">{{ formatMinutes(Math.floor(upsData.battery_runtime / 60 * (upsData.load_percent && upsData.load_percent < 10 ? 1.2 : upsData.load_percent && upsData.load_percent < 30 ? 1.0 : upsData.load_percent && upsData.load_percent < 60 ? 0.95 : 0.85))) }}</div>
                  <div class="prediction-compact-meta">
                    {{ upsData?.runtime_estimated ? '📐 NUT估算' : '📡 UPS报告' }}: {{ formatMinutes(Math.floor(upsData.battery_runtime / 60)) }}
                  </div>
                </div>
                <div class="prediction-item-compact" v-if="predictions.anomalies?.available">
                  <div class="prediction-compact-header">
                    <span class="prediction-compact-icon">⚠️</span>
                    <span class="prediction-compact-title">异常</span>
                  </div>
                  <div v-if="predictions.anomalies.anomaly_count === 0" class="prediction-compact-value">✅</div>
                  <div v-else class="prediction-compact-value alert-value">{{ predictions.anomalies.anomaly_count }}</div>
                  <div class="prediction-compact-meta">
                    {{ predictions.anomalies.anomaly_count === 0 ? '一切正常' : '个异常' }}
                  </div>
                </div>
              </div>
              <div v-if="!hasPredictions" class="prediction-placeholder-compact">
                <span class="placeholder-icon-compact">📊</span>
                <p class="placeholder-text-compact">需要更多历史数据提供预测</p>
              </div>
            </div>

            <!-- 快捷操作卡片 -->
            <div
              v-else-if="cardId === 'quick-actions'"
              class="card quick-actions-card draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'quick-actions' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'quick-actions', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title-compact">⚡ 快捷操作</h3>
              <div class="quick-actions-grid">
                <button class="action-btn" @click="muteBeeper" title="静音蜂鸣器">
                  <span class="action-icon">🔇</span>
                  <span class="action-label">静音</span>
                </button>
                <button v-if="isShutdownPending" class="action-btn action-danger" @click="cancelShutdown" title="取消关机">
                  <span class="action-icon">⏹️</span>
                  <span class="action-label">取消关机</span>
                </button>
              </div>
            </div>

            <!-- 电池分析卡片 (内阻+续航预测) -->
            <div
              v-else-if="cardId === 'battery-analytics' && batteryAnalytics"
              class="card battery-analytics-card draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'battery-analytics' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'battery-analytics', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title-compact">🔋 电池分析</h3>
              <div class="analytics-grid">
                <div class="analytics-item">
                  <span class="an-label">估算内阻</span>
                  <span class="an-value" :class="resistance_class">{{ batteryAnalytics.estimated_resistance_mohm }} mΩ</span>
                  <span class="an-trend">{{ resistance_trend_label }}</span>
                </div>
                <div class="analytics-item">
                  <span class="an-label">AI 续航</span>
                  <span class="an-value">{{ batteryAnalytics.predicted_runtime_minutes ? formatMinutes(batteryAnalytics.predicted_runtime_minutes) : 'N/A' }}</span>
                  <span class="an-confidence">置信度: {{ batteryAnalytics.prediction_confidence }}</span>
                </div>
              </div>
            </div>

            <!-- 电压质量卡片 -->
            <div
              v-else-if="cardId === 'voltage-quality' && upsData.input_voltage"
              class="card voltage-quality-card draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'voltage-quality' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'voltage-quality', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title-compact">⚡ 电压质量</h3>
              <div class="voltage-quality-content">
                <div class="vq-score-circle" :class="'vq-grade-' + (upsData.voltage_quality_grade || 'F')">
                  <div class="vq-score">{{ upsData.voltage_quality_score !== null ? upsData.voltage_quality_score : '?' }}</div>
                  <div class="vq-grade">{{ upsData.voltage_quality_grade || 'N/A' }}</div>
                </div>
                <div class="vq-details">
                  <div class="vq-item" v-if="volt_deviation">
                    <span class="vq-label">偏差</span>
                    <span class="vq-value" :class="volt_deviation_class">{{ volt_deviation }}</span>
                  </div>
                  <div class="vq-item">
                    <span class="vq-label">当前</span>
                    <span class="vq-value">{{ upsData.input_voltage }}V</span>
                  </div>
                  <div class="vq-item">
                    <span class="vq-label">状态</span>
                    <span class="vq-value">{{ upsData.status_raw }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 设备铭牌卡片 -->
            <div
              v-else-if="cardId === 'device-info' && (upsData.ups_model || upsData.ups_manufacturer || upsData.ups_serial || upsData.ups_mfr_date || upsData.ups_realpower_nominal)"
              class="card device-info-card draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'device-info' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'device-info', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title-compact">📋 设备铭牌</h3>
              <div class="device-info-grid">
                <div v-if="upsData.ups_model" class="info-item">
                  <span class="info-label">型号</span>
                  <span class="info-value">{{ upsData.ups_model }}</span>
                </div>
                <div v-if="upsData.ups_manufacturer" class="info-item">
                  <span class="info-label">制造商</span>
                  <span class="info-value">{{ upsData.ups_manufacturer }}</span>
                </div>
                <div v-if="upsData.ups_serial" class="info-item">
                  <span class="info-label">序列号</span>
                  <span class="info-value monospace">{{ upsData.ups_serial }}</span>
                </div>
                <div v-if="upsData.ups_realpower_nominal" class="info-item">
                  <span class="info-label">额定功率</span>
                  <span class="info-value">{{ upsData.ups_realpower_nominal }}W</span>
                </div>
                <div v-if="upsData.ups_mfr_date" class="info-item">
                  <span class="info-label">生产日期</span>
                  <span class="info-value">{{ upsData.ups_mfr_date }}</span>
                </div>
                <div v-if="upsData.ups_vendorid && upsData.ups_productid" class="info-item">
                  <span class="info-label">USB ID</span>
                  <span class="info-value monospace">{{ upsData.ups_vendorid }}:{{ upsData.ups_productid }}</span>
                </div>
              </div>
            </div>

            <!-- 负载仪表盘卡片 -->
            <div
              v-else-if="cardId === 'load-gauge'"
              class="card load-gauge-card draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'load-gauge' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'load-gauge', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title-compact">🔌 负载仪表盘</h3>
              <div class="load-gauge-container">
                <svg class="load-gauge-svg" viewBox="0 0 200 120">
                  <path
                    class="gauge-bg"
                    :d="'M 20 100 A 80 80 0 0 1 180 100'"
                    fill="none"
                    stroke="var(--bg-tertiary)"
                    stroke-width="20"
                    stroke-linecap="round"
                  />
                  <path
                    class="gauge-fill"
                    :d="loadGaugeArc"
                    fill="none"
                    :stroke="loadGaugeColor"
                    stroke-width="20"
                    stroke-linecap="round"
                  />
                  <text x="100" y="85" text-anchor="middle" class="gauge-value">
                    {{ upsData.load_percent ?? 0 }}%
                  </text>
                  <text x="100" y="105" text-anchor="middle" class="gauge-label">
                    {{ computedLoadWatts }}W
                  </text>
                </svg>
                <div class="load-level-text" :style="{ color: loadGaugeColor }">
                  {{ loadLevelText }}
                </div>
              </div>
            </div>

            <!-- 电池电压健康卡片 -->
            <div
              v-else-if="cardId === 'battery-voltage' && (upsData.battery_voltage != null || upsData.battery_voltage_nominal != null)"
              class="card battery-voltage-card draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'battery-voltage' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'battery-voltage', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title-compact">🔋 电池电压健康</h3>
              <div class="battery-voltage-display">
                <div class="voltage-main">
                  <span class="voltage-value">{{ upsData.battery_voltage?.toFixed(2) ?? 'N/A' }}</span>
                  <span class="voltage-unit">V</span>
                </div>
                <div v-if="upsData.battery_voltage_nominal" class="voltage-nominal">
                  额定：{{ upsData.battery_voltage_nominal }}V
                </div>
                <div v-if="batteryVoltageDeviation !== null" class="voltage-deviation" :class="batteryVoltageHealthClass">
                  偏差：{{ batteryVoltageDeviation > 0 ? '+' : '' }}{{ batteryVoltageDeviation }}%
                </div>
              </div>
              <div v-if="upsData.battery_voltage != null && upsData.battery_voltage_nominal" class="voltage-scale">
                <div class="scale-bar">
                  <div class="scale-marker" :style="{ left: batteryVoltageScalePosition }"></div>
                </div>
                <div class="scale-labels">
                  <span>{{ (upsData.battery_voltage_nominal * 0.8).toFixed(1) }}V</span>
                  <span>{{ upsData.battery_voltage_nominal }}V</span>
                  <span>{{ (upsData.battery_voltage_nominal * 1.2).toFixed(1) }}V</span>
                </div>
              </div>
            </div>

            <!-- 关机时间线卡片 -->
            <div
              v-else-if="cardId === 'shutdown-timeline'"
              class="card shutdown-timeline-card draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'shutdown-timeline' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'shutdown-timeline', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title-compact">⏱ 关机时间线</h3>
              <div v-if="!isShuttingDown" class="shutdown-static-mode">
                <div class="protection-rules">
                  <div class="rule-item">
                    <span class="rule-icon">⏰</span>
                    <span class="rule-text">等待时间：触发后 <strong>5</strong> 分钟</span>
                  </div>
                  <div class="rule-item">
                    <span class="rule-icon">🔋</span>
                    <span class="rule-text">电量阈值：电池低于 <strong>20</strong>%</span>
                  </div>
                  <div class="rule-item">
                    <span class="rule-icon">⏱️</span>
                    <span class="rule-text">续航阈值：剩余低于 <strong>300</strong> 秒</span>
                  </div>
                  <div v-if="upsData.ups_delay_shutdown != null" class="rule-item rule-item-editable" @click="openShutdownDelayEdit" title="点击编辑">
                    <span class="rule-icon">⏲️</span>
                    <span class="rule-text">
                      UPS 关机延迟：<strong>{{ upsData.ups_delay_shutdown }}</strong> 秒
                      <span class="edit-icon">✏️</span>
                    </span>
                  </div>
                </div>
                <div class="shutdown-status-info">
                  <span class="status-badge status-safe">✅ 安全运行中</span>
                </div>
              </div>
              <div v-else class="shutdown-realtime-mode">
                <div class="shutdown-progress-bar" :class="shutdownProgressClass">
                  <div class="progress-fill" :style="{ width: shutdownProgress + '%' }"></div>
                </div>
                <div class="shutdown-time-info">
                  <span>已用：{{ formatDuration(0) }}</span>
                  <span>剩余：{{ formatDuration(300) }}</span>
                </div>
                <div class="shutdown-status-info">
                  <span class="status-badge status-warning">⚠️ 正在关机</span>
                </div>
              </div>
            </div>

            <!-- 保护状态总览卡片 -->
            <div
              v-else-if="cardId === 'protection-overview' && hasProtectionData"
              class="card protection-overview-card draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'protection-overview' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'protection-overview', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title-compact">🛡️ 保护状态总览</h3>
              <div class="protection-grid">
                <div v-if="upsData.input_sensitivity" class="protection-item">
                  <span class="protection-label">输入灵敏度</span>
                  <span class="protection-value protection-editable" @click="openSensitivityEdit" title="点击编辑">
                    {{ sensitivityText }}
                    <span class="edit-icon">✏️</span>
                  </span>
                </div>
                <div v-if="upsData.input_transfer_reason" class="protection-item">
                  <span class="protection-label">切换原因</span>
                  <span class="protection-value">{{ formatTransferReason(upsData.input_transfer_reason) }}</span>
                </div>
                <div v-if="upsData.battery_charge_low != null" class="protection-item">
                  <span class="protection-label">低电量阈值</span>
                  <span class="protection-value">{{ upsData.battery_charge_low }}%</span>
                </div>
              </div>
            </div>

            <!-- 状态标志位解析卡片 -->
            <div
              v-else-if="cardId === 'status-flags' && upsData.status_raw"
              class="card status-flags-card draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'status-flags' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'status-flags', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title-compact">📊 状态标志位解析</h3>
              <div class="status-flags-grid">
                <div
                  v-for="flag in allStatusFlags"
                  :key="flag"
                  class="flag-item"
                  :class="{ 'flag-active': activeFlags.includes(flag), 'flag-inactive': !activeFlags.includes(flag) }"
                  :title="getStatusFlagTooltip(flag)"
                >
                  <span class="flag-icon">{{ getStatusFlagIcon(flag) }}</span>
                  <span class="flag-code">{{ getStatusFlagLabel(flag) }}</span>
                </div>
              </div>
              <div class="flags-raw">
                原始状态：<code>{{ upsData.status_raw }}</code>
              </div>
            </div>

            <!-- 切换统计卡片（apcupsd 数据） -->
            <div
              v-else-if="cardId === 'transfer-stats' && hasTransferData"
              class="card transfer-stats-card draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'transfer-stats' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'transfer-stats', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title-compact">🔄 切换统计</h3>
              <div class="transfer-stats-grid">
                <div class="transfer-stat-item" v-if="upsData.transfer_count != null">
                  <span class="stat-icon">🔀</span>
                  <div class="stat-details">
                    <span class="stat-label">历史切换次数</span>
                    <span class="stat-value">{{ upsData.transfer_count }}</span>
                  </div>
                </div>
                <div class="transfer-stat-item" v-if="upsData.time_on_battery != null">
                  <span class="stat-icon">⏱️</span>
                  <div class="stat-details">
                    <span class="stat-label">本次电池时长</span>
                    <span class="stat-value">{{ formatDuration(upsData.time_on_battery) }}</span>
                  </div>
                </div>
                <div class="transfer-stat-item" v-if="upsData.cumulative_on_battery != null">
                  <span class="stat-icon">🔋</span>
                  <div class="stat-details">
                    <span class="stat-label">累计电池时长</span>
                    <span class="stat-value">{{ formatDuration(upsData.cumulative_on_battery) }}</span>
                  </div>
                </div>
                <div class="transfer-stat-item" v-if="upsData.ups_alarm_del">
                  <span class="stat-icon">🔔</span>
                  <div class="stat-details">
                    <span class="stat-label">蜂鸣器策略</span>
                    <span class="stat-value">{{ formatAlarmDel(upsData.ups_alarm_del) }}</span>
                  </div>
                </div>
                <div class="transfer-stat-item" v-if="upsData.ups_starttime">
                  <span class="stat-icon">🚀</span>
                  <div class="stat-details">
                    <span class="stat-label">守护进程启动</span>
                    <span class="stat-value">{{ upsData.ups_starttime }}</span>
                  </div>
                </div>
                <div class="transfer-stat-item" v-if="upsData.ups_backend">
                  <span class="stat-icon">🔌</span>
                  <div class="stat-details">
                    <span class="stat-label">通信后端</span>
                    <span class="stat-value backend-badge" :class="'backend-' + upsData.ups_backend">
                      {{ upsData.ups_backend === 'apcupsd' ? 'apcupsd' : 'NUT' }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 额定参数卡片 -->
            <div
              v-else-if="cardId === 'nominal-specs' && hasNominalSpecs"
              class="card nominal-specs-card draggable-card"
              :class="{ 'is-dragging': dragState.draggedCardId === 'nominal-specs' }"
              draggable="true"
              @dragstart="(e) => handleDragStart(e, 'nominal-specs', colKey)"
              @dragend="handleDragEnd"
              @dragover.prevent="(e) => handleCardDragOver(e, colKey, cardIndex)"
            >
              <div class="drag-handle" title="拖拽调整位置"><span class="drag-icon">⋮⋮</span></div>
              <h3 class="card-title-compact">📐 额定参数</h3>
              <div class="nominal-specs-grid">
                <div class="nominal-item" v-if="upsData.input_voltage_nominal">
                  <span class="nominal-label">额定输入电压</span>
                  <span class="nominal-value">{{ upsData.input_voltage_nominal }}V</span>
                </div>
                <div class="nominal-item" v-if="upsData.battery_voltage_nominal">
                  <span class="nominal-label">额定电池电压</span>
                  <span class="nominal-value">{{ upsData.battery_voltage_nominal }}V</span>
                </div>
                <div class="nominal-item" v-if="upsData.ups_realpower_nominal">
                  <span class="nominal-label">额定有功功率</span>
                  <span class="nominal-value">{{ upsData.ups_realpower_nominal }}W</span>
                </div>
                <div class="nominal-item" v-if="upsData.ups_power_nominal">
                  <span class="nominal-label">额定视在功率</span>
                  <span class="nominal-value">{{ upsData.ups_power_nominal }}VA</span>
                </div>
                <div class="nominal-item" v-if="upsData.output_current_nominal">
                  <span class="nominal-label">额定输出电流</span>
                  <span class="nominal-value">{{ upsData.output_current_nominal }}A</span>
                </div>
              </div>
            </div>
          </template>

          <!-- 列尾部拖拽占位符 -->
          <div
            v-if="dragState.isDragging && dragState.targetCol === colKey && dragState.targetIndex === userPrefs.dashboardCardOrder[colKey].length"
            class="drop-placeholder"
          ></div>
        </div>
      </template>
    </div>

    <!-- 纳管设备区域：独立区域，自适应布局 -->
    <div v-if="upsData && devices.length > 0" class="devices-section">
      <div class="devices-section-header">
        <h3 class="section-title">纳管设备</h3>
        <button
          class="btn btn-sm btn-secondary"
          @click="fetchDevicesStatus"
          :disabled="devicesLoading"
          title="刷新设备状态"
        >
          <span v-if="devicesLoading">⏳</span>
          <span v-else>🔄</span>
          刷新状态
        </button>
      </div>

      <div class="devices-grid">
        <DeviceCard
          v-for="device in devices"
          :key="`${device.index || 0}-${device.hook_id}-${device.name}`"
          :device="device"
          :testing="testingDevices.has(`${device.index}-${device.hook_id}-${device.name}`)"
          :execution-status="deviceExecutionStates.get(`${device.index}-${device.hook_id}-${device.name}`)?.status"
          :execution-duration="deviceExecutionStates.get(`${device.index}-${device.hook_id}-${device.name}`)?.duration"
          :execution-error="deviceExecutionStates.get(`${device.index}-${device.hook_id}-${device.name}`)?.error"
          @test-connection="testDeviceConnection"
          @shutdown="shutdownDevice"
          @wake="wakeDevice"
          @reboot="rebootDevice"
          @sleep="sleepDevice"
          @hibernate="hibernateDevice"
          @test-wol="testWOL"
          @view-logs="showLogsViewer"
          @edit-config="editDeviceConfig"
        />
      </div>
    </div>

    <!-- 无设备时的提示（在核心数据下方）-->
    <div v-else-if="upsData && devices.length === 0" class="devices-section">
      <div class="card devices-empty-card">
        <div class="card-header-compact">
          <h3 class="card-title-compact">纳管设备</h3>
        </div>
        <div class="empty-state-compact">
          暂未配置纳管设备
        </div>
        <div class="devices-footer">
          <router-link to="/settings" class="btn btn-sm btn-primary">
            前往配置
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, defineAsyncComponent } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useWebSocket } from '@/composables/useWebSocket'
import { useUpsStatus } from '@/composables/useUpsStatus'
import { useToast } from '@/composables/useToast'
import { useUserPreferencesStore } from '@/stores/userPreferences'
import { useDraggableCards } from '@/composables/useDraggableCards'
// 使用异步组件加载 ECharts，提升首屏加载速度
const PowerChart = defineAsyncComponent(() => import('@/components/PowerChart.vue'))
import DeviceCard from '@/components/DeviceCard.vue'
import type { Event, Metric, Device, HookExecutionState } from '@/types/ups'

// 用户偏好设置
const userPrefs = useUserPreferencesStore()

// Dashboard 卡片定义
type DashboardCol = 'col1' | 'col2' | 'col3'

// 拖拽功能
const {
  dragState,
  handleDragStart,
  handleDrop,
  handleDragEnd
} = useDraggableCards<DashboardCol>(
  () => userPrefs.dashboardCardOrder,
  (col, cards) => userPrefs.updateDashboardCardOrder(col, cards),
  (fromCol, toCol, cardId, toIndex) => userPrefs.moveDashboardCard(fromCol, toCol, cardId, toIndex)
)

// 列拖拽经过处理（用于拖到列末尾空白区域）
const handleColDragOver = (e: DragEvent, col: DashboardCol) => {
  e.preventDefault()
  if (!dragState.isDragging) return

  // 检查是否直接拖到了列容器（不是子元素）
  const target = e.target as HTMLElement
  if (target.classList.contains('droppable-col')) {
    dragState.targetCol = col
    dragState.targetIndex = userPrefs.dashboardCardOrder[col].length
  }
}

// 卡片拖拽经过处理（用于拖到卡片位置）
const handleCardDragOver = (e: DragEvent, col: DashboardCol, index: number) => {
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
const resetDashboardLayout = () => {
  userPrefs.resetDashboardLayout()
  toast.success('布局已重置为默认')
}

// 温度差异阈值 (°C) - 用于判断是否需要分别显示环境温度和电池温度
const TEMPERATURE_DIFFERENCE_THRESHOLD = 0.1

const { connected: wsConnected, data: wsData, latestHookProgress, connectionEvent } = useWebSocket()
const { getStatusText, getStatusColor } = useUpsStatus()
const toast = useToast()
const router = useRouter()

const upsData = computed(() => wsData.value)
const statusText = computed(() => upsData.value ? getStatusText(upsData.value.status) : '离线')
const statusColor = computed(() => upsData.value ? getStatusColor(upsData.value.status) : '#9CA3AF')


// NUT 状态标志映射
const STATUS_FLAG_MAP: Record<string, { icon: string; label: string; labelEn: string; type: 'success' | 'warning' | 'danger' | 'info' }> = {
  'OL': { icon: '✅', label: '市电供电', labelEn: 'Online', type: 'success' },
  'OB': { icon: '⚠️', label: '电池供电', labelEn: 'On Battery', type: 'warning' },
  'LB': { icon: '🔴', label: '低电量', labelEn: 'Low Battery', type: 'danger' },
  'HB': { icon: '🟢', label: '高电量', labelEn: 'High Battery', type: 'success' },
  'RB': { icon: '🔧', label: '需更换电池', labelEn: 'Replace Battery', type: 'danger' },
  'CHRG': { icon: '🔋', label: '充电中', labelEn: 'Charging', type: 'info' },
  'DISCHRG': { icon: '📉', label: '放电中', labelEn: 'Discharging', type: 'warning' },
  'BYPASS': { icon: '🔀', label: '旁路模式', labelEn: 'Bypass', type: 'info' },
  'CAL': { icon: '🔧', label: '校准中', labelEn: 'Calibrating', type: 'info' },
  'OFF': { icon: '⭕', label: 'UPS关闭', labelEn: 'Off', type: 'danger' },
  'OVER': { icon: '🚨', label: '过载', labelEn: 'Overload', type: 'danger' },
  'TRIM': { icon: '📉', label: '降压调节', labelEn: 'Trim', type: 'info' },
  'BOOST': { icon: '📈', label: '升压调节', labelEn: 'Boost', type: 'info' },
  'FSD': { icon: '🛑', label: '强制关机', labelEn: 'Forced Shutdown', type: 'danger' },
  'ALARM': { icon: '🚨', label: '报警', labelEn: 'Alarm', type: 'danger' },
}

// 所有可能的状态标志
const ALL_STATUS_FLAGS = ['OL', 'OB', 'LB', 'HB', 'RB', 'CHRG', 'DISCHRG', 'BYPASS', 'CAL', 'OFF', 'OVER', 'TRIM', 'BOOST', 'FSD'] as const

const getStatusFlagIcon = (flag: string): string => {
  return STATUS_FLAG_MAP[flag]?.icon || '❓'
}

// 悬浮显示英文
const getStatusFlagTooltip = (flag: string): string => {
  return STATUS_FLAG_MAP[flag]?.labelEn || flag
}

// 获取中文标签
const getStatusFlagLabel = (flag: string): string => {
  return STATUS_FLAG_MAP[flag]?.label || `未知状态: ${flag}`
}

const getStatusFlagClass = (flag: string): string => {
  const type = STATUS_FLAG_MAP[flag]?.type || 'info'
  return `status-flag-${type}`
}

// 格式化最后更新时间 - 使用computed确保响应式更新
const formattedLastUpdate = computed(() => {
  if (!upsData.value?.last_update) return '未知'
  return formatDateTime(upsData.value.last_update)
})

// 计算实际功率 (W)
const computedPower = computed(() => {
  if (!upsData.value) return null
  // 优先级1: 使用实时实际功率
  if (upsData.value.ups_realpower) return Math.round(upsData.value.ups_realpower)
  // 负载百分比必须是有效数值（包含0）
  const loadPercent = upsData.value.load_percent
  if (loadPercent === null || loadPercent === undefined) return null
  // 优先级2: 使用额定实际功率 (W) × 负载百分比
  if (upsData.value.ups_realpower_nominal) {
    return Math.round(upsData.value.ups_realpower_nominal * loadPercent / 100)
  }
  // 优先级3: 使用额定视在功率 (VA) × 功率因数 0.6 × 负载百分比
  if (upsData.value.ups_power_nominal) {
    return Math.round(upsData.value.ups_power_nominal * 0.6 * loadPercent / 100)
  }
  return null
})

// 电池温度
const batteryTemp = computed(() => {
  if (!upsData.value) return null
  // 优先使用电池温度，其次使用 UPS 温度
  return upsData.value.battery_temperature ?? upsData.value.temperature
})

const batteryTempHigh = computed(() => {
  const temp = batteryTemp.value
  return temp !== null && temp > 40
})

// 判断是否需要显示两个温度（只有当两个温度都存在且不同时才显示两个）
const showBothTemperatures = computed(() => {
  if (!upsData.value) return false
  const temp = upsData.value.temperature
  const battTemp = upsData.value.battery_temperature
  // 使用类型检查和容差比较避免浮点精度问题
  if (typeof temp !== 'number' || typeof battTemp !== 'number') return false
  return Math.abs(temp - battTemp) > TEMPERATURE_DIFFERENCE_THRESHOLD
})

// 电池健康度（基于电压的简单估算）
const batteryHealthPercent = computed(() => {
  if (!upsData.value) return null
  const voltage = upsData.value.battery_voltage
  const nominal = upsData.value.battery_voltage_nominal
  if (voltage && nominal && nominal > 0) {
    // 简单健康度估算：基于电压/额定电压的比值映射到 0-100%
    // 注意：这是基于电压的粗略估算，实际电池健康还受年龄、充放电次数、温度等因素影响
    // 假设：完全充满 ≈ 额定电压 * 1.1，低电 ≈ 额定电压 * 0.9
    const ratio = voltage / nominal
    return Math.min(100, Math.max(0, Math.round((ratio - 0.9) / 0.2 * 100)))
  }
  return null
})

const batteryHealthClass = computed(() => {
  const health = batteryHealthPercent.value
  if (health === null) return ''
  if (health >= 80) return 'health-good'
  if (health >= 50) return 'health-warning'
  return 'health-danger'
})

// 近期电量迷你图
const sparklineWidth = 200
const sparklineHeight = 40

const sparklinePoints = computed(() => {
  if (metrics.value.length === 0) return ''
  const data = metrics.value.slice(-30)  // 最近 30 个数据点
  const step = sparklineWidth / Math.max(data.length - 1, 1)
  return data.map((m, i) => {
    const charge = m.battery_charge ?? 100
    const y = sparklineHeight - (charge / 100 * sparklineHeight)
    return `${i * step},${y}`
  }).join(' ')
})

const sparklineAreaPoints = computed(() => {
  if (!sparklinePoints.value) return ''
  const data = metrics.value.slice(-30)
  const lastX = Math.max(data.length - 1, 1) * (sparklineWidth / Math.max(data.length - 1, 1))
  return `0,${sparklineHeight} ${sparklinePoints.value} ${lastX},${sparklineHeight}`
})

const sparklineColor = computed(() => {
  const charge = upsData.value?.battery_charge ?? 100
  if (charge > 60) return '#10B981'
  if (charge > 30) return '#F59E0B'
  return '#EF4444'
})

const latestBatteryCharge = computed(() => {
  return upsData.value?.battery_charge ?? 0
})

// AC/DC 电压判断阈值：低于此值认为是 DC UPS
const AC_DC_VOLTAGE_THRESHOLD = 48

// ========== 电池分析计算 ==========
const batteryAnalyticsData = computed(() => batteryAnalytics.value?.data || {})

const isShutdownPending = computed(() => {
  return !!shutdownManager.value?.pending_shutdown_time
})

const resistance_trend_label = computed(() => {
  const trend = batteryAnalytics.value?.resistance_trend
  if (!trend) return 'N/A'
  if (trend === 'stable') return '稳定'
  if (trend === 'increasing') return '上升 (老化)'
  if (trend === 'decreasing') return '下降'
  return trend
})

const resistance_class = computed(() => {
  const r = batteryAnalytics.value?.estimated_resistance_mohm
  if (!r) return ''
  if (r > 30) return 'text-danger'
  if (r > 20) return 'text-warning'
  return ''
})

// 推断额定电压（当 UPS 不报告 input.voltage.nominal 时）
const inferredNominalVoltage = computed(() => {
  // UPS 已报告额定电压，不需要推断
  if (upsData.value?.input_voltage_nominal) return null

  const voltage = upsData.value?.input_voltage
  if (!voltage) return null

  // DC UPS 常见额定电压推断
  if (voltage < AC_DC_VOLTAGE_THRESHOLD) {
    if (voltage >= 10 && voltage <= 14) return 12   // 12V DC UPS
    if (voltage >= 18 && voltage <= 21) return 19   // 19V DC UPS (笔记本)
    if (voltage >= 22 && voltage <= 26) return 24   // 24V DC UPS
    return null
  }
  // AC UPS 默认 220V
  return 220
})

// ========== 电压质量计算 ==========
const nominalVoltage = computed(() => {
  return upsData.value?.input_voltage_nominal || inferredNominalVoltage.value || 220
})

const input_transfer_low = computed(() => upsData.value?.input_transfer_low)
const input_transfer_high = computed(() => upsData.value?.input_transfer_high)

const volt_deviation = computed(() => {
  if (!upsData.value?.input_voltage || !nominalVoltage.value) return null
  const deviation = Math.abs(upsData.value.input_voltage - nominalVoltage.value) / nominalVoltage.value * 100
  return deviation.toFixed(1) + '%'
})

const volt_deviation_class = computed(() => {
  if (!upsData.value?.input_voltage || !nominalVoltage.value) return ''
  const deviation = Math.abs(upsData.value.input_voltage - nominalVoltage.value) / nominalVoltage.value * 100
  if (deviation > 15) return 'text-danger'
  if (deviation > 10) return 'text-warning'
  if (deviation > 5) return 'text-muted'
  return ''
})

// Phase 1 新增计算属性

// 频率偏差（用于警告）
const frequencyDeviation = computed(() => {
  if (!upsData.value?.input_frequency) return 0
  const nominal = 50 // 假设额定频率为 50Hz，实际应该从 input.frequency.nominal 获取
  return Math.abs(upsData.value.input_frequency - nominal)
})

// 效率分类样式
const efficiencyClass = computed(() => {
  const efficiency = upsData.value?.ups_efficiency
  if (!efficiency) return ''
  if (efficiency >= 90) return 'efficiency-excellent'
  if (efficiency >= 80) return 'efficiency-good'
  if (efficiency >= 70) return 'efficiency-warning'
  return 'efficiency-danger'
})

// 电池年龄计算
const batteryAge = computed(() => {
  const dateInfo = effectiveBatteryDate.value
  if (!dateInfo.date) return null
  
  try {
    const installDate = new Date(dateInfo.date)
    const now = new Date()
    const diffTime = Math.abs(now.getTime() - installDate.getTime())
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24))
    
    if (diffDays < 30) return `${diffDays} 天`
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} 个月`
    
    const years = Math.floor(diffDays / 365)
    const months = Math.floor((diffDays % 365) / 30)
    return months > 0 ? `${years} 年 ${months} 个月` : `${years} 年`
  } catch {
    return null
  }
})

// 电池年龄样式
const batteryAgeClass = computed(() => {
  const dateInfo = effectiveBatteryDate.value
  if (!dateInfo.date) return ''
  
  try {
    const installDate = new Date(dateInfo.date)
    const now = new Date()
    const years = (now.getTime() - installDate.getTime()) / (1000 * 60 * 60 * 24 * 365)
    
    if (years > 5) return 'age-critical'
    if (years > 3) return 'age-warning'
    return 'age-good'
  } catch {
    return ''
  }
})

// 电池类型标签
const batteryTypeLabel = computed(() => {
  const type = upsData.value?.battery_type
  if (!type) return 'N/A'
  const typeMap: Record<string, string> = {
    'PbAc': '铅酸电池',
    'Li-ion': '锂离子电池',
    'NiMH': '镍氢电池',
    'NiCd': '镍镉电池'
  }
  return typeMap[type] || type
})

// 格式化输入灵敏度
const formatSensitivity = (sensitivity: string | null | undefined): string => {
  if (!sensitivity) return ''
  const map: Record<string, string> = {
    'low': '低',
    'medium': '中',
    'high': '高',
    'auto': '自动'
  }
  return map[sensitivity.toLowerCase()] || sensitivity
}

// 格式化蜂鸣器状态
const formatBeeperStatus = (status: string | null | undefined): string => {
  if (!status) return ''
  const map: Record<string, string> = {
    'enabled': '🔔 已启用',
    'disabled': '🔕 已禁用',
    'muted': '🔇 已静音'
  }
  return map[status.toLowerCase()] || status
}

// 格式化电池充电器状态
const formatBatteryChargerStatus = (status: string | null | undefined): string => {
  if (!status) return ''
  const map: Record<string, string> = {
    'charging': '⚡ 充电中',
    'discharging': '🔋 放电中',
    'floating': '🔌 浮充中',
    'resting': '😴 休眠中'
  }
  return map[status.toLowerCase()] || status
}

// 电池充电器状态样式类
const batteryChargerStatusClass = computed(() => {
  const status = upsData.value?.battery_charger_status?.toLowerCase()
  if (!status) return ''
  if (status === 'charging' || status === 'floating' || status === 'resting') {
    return 'charger-status-good'
  } else if (status === 'discharging') {
    return 'charger-status-warning'
  }
  return ''
})

// 切换原因中文映射
const TRANSFER_REASON_MAP: Record<string, string> = {
  'input voltage out of range': '输入电压超出范围',
  'no transfer': '无切换',
  'high line voltage': '输入电压过高',
  'low line voltage': '输入电压过低',
  'self test': '自测切换',
  'forced': '强制切换',
}

// 格式化切换原因
const formatTransferReason = (reason: string | null | undefined): string => {
  if (!reason) return ''
  return TRANSFER_REASON_MAP[reason.toLowerCase()] || reason
}

// 检测是否为占位符日期（2001/01/01 等）
const isPlaceholderDate = (dateStr: string | null | undefined): boolean => {
  if (!dateStr) return false
  // 检测常见的占位符日期
  const placeholders = ['2001/01/01', '2001-01-01', '1970/01/01', '1970-01-01', '1980/01/01', '1980-01-01']
  return placeholders.includes(dateStr)
}

// 格式化电池生产日期
const formatBatteryMfrDate = (dateStr: string | null | undefined): string => {
  if (!dateStr) return ''
  if (isPlaceholderDate(dateStr)) {
    return '未设置（默认值）'
  }
  return dateStr
}

// 获取日期字段的工具提示
const getDateTooltip = (dateStr: string | null | undefined): string => {
  if (!dateStr) return ''
  if (isPlaceholderDate(dateStr)) {
    return '这是默认占位符值，表示 UPS 不支持记录此信息（正常现象）。请以购买日期为准。'
  }
  return '电池生产日期'
}

// 通用占位符检测函数
const isPlaceholderValue = (value: string | null | undefined, type: string): boolean => {
  if (!value) return true
  if (type === 'date') {
    return isPlaceholderDate(value)
  }
  return false
}

// 有效的电池日期（优先用户设置，次用硬件提供）
const effectiveBatteryDate = computed(() => {
  // 1. 用户手动设置的日期优先
  if (configData.value?.battery_install_date && 
      !isPlaceholderValue(configData.value.battery_install_date, 'date')) {
    return {
      date: configData.value.battery_install_date,
      source: 'user',
      label: '安装日期',
      editable: true,
      icon: '👤'
    }
  }
  
  // 2. UPS 硬件提供的日期（如果不是占位符）
  if (upsData.value?.battery_mfr_date && 
      !isPlaceholderValue(upsData.value.battery_mfr_date, 'date')) {
    return {
      date: upsData.value.battery_mfr_date,
      source: 'hardware',
      label: '生产日期',
      editable: false,
      icon: '🔌'
    }
  }
  
  // 3. 无可用日期
  return {
    date: null,
    source: null,
    label: '安装日期',
    editable: true,
    icon: ''
  }
})

// Phase 2: 电压质量相关计算属性

const voltageQualityClass = computed(() => {
  if (!upsData.value?.input_voltage) return ''
  const voltage = upsData.value.input_voltage
  const low = upsData.value.input_transfer_low || 180
  const high = upsData.value.input_transfer_high || 280

  // 计算安全范围的 20% 作为缓冲区
  const range = high - low
  const warningBuffer = range * 0.2

  if (voltage < low || voltage > high) {
    return 'voltage-danger'  // 超出安全区间
  } else if (voltage < low + warningBuffer || voltage > high - warningBuffer) {
    return 'voltage-warning'  // 接近安全区间边界
  } else {
    return 'voltage-good'  // 在安全区间内
  }
})

const voltageMarkerPosition = computed(() => {
  if (!upsData.value?.input_voltage) return { left: '50%' }
  const voltage = upsData.value.input_voltage
  const low = upsData.value.input_transfer_low || 180
  const high = upsData.value.input_transfer_high || 280
  const range = high - low
  const position = ((voltage - low) / range) * 100
  return { left: `${Math.max(0, Math.min(100, position))}%` }
})

// Phase 2: 环境监控相关计算属性
const ambientTempClass = computed(() => {
  const temp = upsData.value?.ambient_temperature
  if (!temp) return ''
  if (temp < 18 || temp > 27) return 'env-warning'
  return 'env-good'
})

const ambientHumidityClass = computed(() => {
  const humidity = upsData.value?.ambient_humidity
  if (!humidity) return ''
  if (humidity < 40 || humidity > 60) return 'env-warning'
  return 'env-good'
})

const environmentComfort = computed(() => {
  const temp = upsData.value?.ambient_temperature
  const humidity = upsData.value?.ambient_humidity
  if (!temp || !humidity) return null
  
  // 舒适度评估
  const tempOk = temp >= 18 && temp <= 27
  const humidityOk = humidity >= 40 && humidity <= 60
  
  if (tempOk && humidityOk) {
    return { label: '舒适', class: 'comfort-good' }
  } else if ((temp >= 15 && temp <= 30) && (humidity >= 30 && humidity <= 70)) {
    return { label: '可接受', class: 'comfort-acceptable' }
  } else {
    return { label: '不适', class: 'comfort-poor' }
  }
})

// Phase 3: 自检状态相关计算属性
const testResultClass = computed(() => {
  const result = upsData.value?.ups_test_result
  if (!result) return ''
  if (result.toLowerCase().includes('pass')) return 'test-pass'
  if (result.toLowerCase().includes('fail')) return 'test-fail'
  if (result.toLowerCase().includes('progress')) return 'test-progress'
  return ''
})

const testResultIcon = computed(() => {
  const result = upsData.value?.ups_test_result
  if (!result) return '❓'
  if (result.toLowerCase().includes('pass')) return '✅'
  if (result.toLowerCase().includes('fail')) return '❌'
  if (result.toLowerCase().includes('progress')) return '🔄'
  return '❓'
})

// Phase 4: 能耗统计计算属性
const energyStats = computed(() => {
  if (!upsData.value?.ups_realpower && !computedPower.value) return null
  
  const powerW = computedPower.value || 0
  const efficiency = upsData.value?.ups_efficiency || 90
  const actualPower = powerW / (efficiency / 100) // 实际消耗功率
  
  // 今日预估 (24小时)
  const todayKwh = (actualPower * 24 / 1000).toFixed(2)
  const todayCost = (parseFloat(todayKwh) * 0.6).toFixed(2) // 假设电费0.6元/kWh
  
  // 月度预估 (30天)
  const monthlyKwh = (actualPower * 24 * 30 / 1000).toFixed(2)
  const monthlyCost = (parseFloat(monthlyKwh) * 0.6).toFixed(2)
  
  // 效率提示
  let efficiencyTip = ''
  if (efficiency < 80) {
    efficiencyTip = `UPS效率偏低(${efficiency}%)，建议检查设备或考虑更换`
  } else if (efficiency < 90) {
    efficiencyTip = `提升效率至90%可每月节省约¥${((parseFloat(monthlyCost) * (90 - efficiency) / efficiency)).toFixed(2)}`
  }
  
  return {
    todayKwh,
    todayCost,
    monthlyKwh,
    monthlyCost,
    efficiencyTip
  }
})

// Phase 4: 电池寿命预测
const batteryLifePrediction = computed(() => {
  const age = batteryAge.value
  if (age === null) return null
  
  // 铅酸电池典型寿命3-5年，锂电池5-10年
  const type = upsData.value?.battery_type
  const expectedLife = type === 'Li-ion' ? 8 : 4 // 年
  
  const remainingYears = Math.max(0, expectedLife - age)
  const remainingMonths = Math.round(remainingYears * 12)
  const remainingPercent = Math.round((remainingYears / expectedLife) * 100)
  
  let suggestion: string
  if (remainingMonths < 6) {
    suggestion = '⚠️ 建议立即安排更换电池'
  } else if (remainingMonths < 12) {
    suggestion = '📅 建议在未来6个月内更换电池'
  } else if (remainingMonths < 24) {
    suggestion = '✅ 电池状态良好，可继续使用'
  } else {
    suggestion = '✅ 电池状态优秀'
  }
  
  return {
    remainingMonths,
    remainingPercent,
    suggestion
  }
})

// New card computed properties

// Load gauge card
const computedLoadWatts = computed(() => {
  if (!upsData.value) return 0
  const loadPercent = upsData.value.load_percent ?? 0
  if (upsData.value.ups_realpower_nominal) {
    return Math.round(upsData.value.ups_realpower_nominal * loadPercent / 100)
  }
  return 0
})

const loadGaugeColor = computed(() => {
  const load = upsData.value?.load_percent ?? 0
  if (load < 50) return '#10B981' // green
  if (load < 70) return '#F59E0B' // yellow
  if (load < 90) return '#F97316' // orange
  return '#EF4444' // red
})

const loadLevelText = computed(() => {
  const load = upsData.value?.load_percent ?? 0
  if (load === 0) return '空载'
  if (load < 50) return '轻负载'
  if (load < 70) return '中等负载'
  if (load < 90) return '高负载'
  return '过载危险'
})

const loadGaugeArc = computed(() => {
  const load = upsData.value?.load_percent ?? 0
  const percent = Math.min(100, Math.max(0, load)) / 100
  const angle = percent * 180
  const radians = (angle - 90) * (Math.PI / 180)
  const x = 100 + 80 * Math.cos(radians)
  const y = 100 + 80 * Math.sin(radians)
  const largeArc = angle > 90 ? 1 : 0
  return `M 20 100 A 80 80 0 ${largeArc} 1 ${x} ${y}`
})

// Battery voltage card
const batteryVoltageDeviation = computed(() => {
  if (!upsData.value?.battery_voltage || !upsData.value?.battery_voltage_nominal) return null
  const deviation = ((upsData.value.battery_voltage - upsData.value.battery_voltage_nominal) / upsData.value.battery_voltage_nominal) * 100
  return Math.round(deviation * 10) / 10
})

const batteryVoltageScalePosition = computed(() => {
  if (!upsData.value?.battery_voltage || !upsData.value?.battery_voltage_nominal) return '50%'
  const nominal = upsData.value.battery_voltage_nominal
  const voltage = upsData.value.battery_voltage
  const min = nominal * 0.8
  const max = nominal * 1.2
  const position = ((voltage - min) / (max - min)) * 100
  return Math.min(100, Math.max(0, position)) + '%'
})

const batteryVoltageHealthClass = computed(() => {
  const deviation = batteryVoltageDeviation.value
  if (deviation === null) return ''
  const abs = Math.abs(deviation)
  if (abs <= 5) return 'health-good'
  if (abs <= 10) return 'health-warning'
  return 'health-danger'
})

// Shutdown timeline card
const shutdownProgress = computed(() => {
  // This would be calculated based on actual shutdown start time
  // For now, return 0 when not shutting down
  return isShuttingDown.value ? 50 : 0
})

const shutdownProgressClass = computed(() => {
  const progress = shutdownProgress.value
  if (progress < 30) return 'progress-start'
  if (progress < 70) return 'progress-mid'
  return 'progress-end'
})

const formatDuration = (seconds: number): string => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

// Protection overview card
const hasProtectionData = computed(() => {
  if (!upsData.value) return false
  return !!(
    upsData.value.ups_test_result ||
    upsData.value.ups_beeper_status ||
    upsData.value.input_sensitivity ||
    upsData.value.input_transfer_reason ||
    upsData.value.battery_charge_low != null ||
    upsData.value.battery_runtime_low != null
  )
})

const beeperStatusText = computed(() => {
  const status = upsData.value?.ups_beeper_status
  if (!status) return ''
  if (status.toLowerCase() === 'enabled') return '启用'
  if (status.toLowerCase() === 'disabled') return '禁用'
  if (status.toLowerCase() === 'muted') return '静音'
  return status
})

const sensitivityText = computed(() => {
  const sensitivity = upsData.value?.input_sensitivity
  if (!sensitivity) return ''
  const map: Record<string, string> = {
    'low': '低',
    'medium': '中',
    'high': '高',
    'normal': '正常'
  }
  return map[sensitivity.toLowerCase()] || sensitivity
})

// Status flags card
const activeFlags = computed(() => {
  if (!upsData.value?.status_raw) return []
  return upsData.value.status_raw.split(' ').filter(f => f.length > 0)
})

const allStatusFlags = computed(() => {
  return [...ALL_STATUS_FLAGS]
})

// Transfer stats card (apcupsd data)
const hasTransferData = computed(() => {
  if (!upsData.value) return false
  return !!(
    upsData.value.transfer_count != null ||
    upsData.value.time_on_battery != null ||
    upsData.value.cumulative_on_battery != null ||
    upsData.value.ups_alarm_del ||
    upsData.value.ups_starttime ||
    upsData.value.ups_backend
  )
})

// Nominal specs card
const hasNominalSpecs = computed(() => {
  if (!upsData.value) return false
  return !!(
    upsData.value.input_voltage_nominal ||
    upsData.value.battery_voltage_nominal ||
    upsData.value.ups_realpower_nominal ||
    upsData.value.ups_power_nominal ||
    upsData.value.output_current_nominal ||
    upsData.value.battery_charge_low != null ||
    upsData.value.battery_runtime_low != null
  )
})

// Format alarm delay
const formatAlarmDel = (val: string | null | undefined): string => {
  if (!val) return 'N/A'
  const map: Record<string, string> = {
    'No alarm': '无报警延迟',
    '5sec': '5秒',
    '30sec': '30秒',
    '60sec': '60秒',
    'always': '始终报警'
  }
  return map[val] || val
}

const recentEvents = ref<Event[]>([])
const metrics = ref<Metric[]>([])
const showShutdownConfirm = ref(false)
const isShuttingDown = ref(false)
const isCancelling = ref(false)
const devices = ref<Device[]>([])
const devicesLoading = ref(false)
const testingDevices = ref<Set<string>>(new Set())
const deviceExecutionStates = ref<Map<string, HookExecutionState>>(new Map())
const lastDeviceRefresh = ref<Date | null>(null)
const deviceRefreshInterval = ref<number | null>(null)
const deviceRefreshIntervalSeconds = ref<number>(60) // 默认 60 秒

// 电池分析数据
const batteryAnalytics = ref<any>(null)

// 自检提醒消息
const selfTestReminderMessage = computed(() => {
  const data = batteryAnalytics.value
  if (!data?.needs_self_test) return ''
  const days = data.days_since_last_test || '?'
  const testType = data.recommended_test === 'deep' ? '深度' : '快速'
  return `建议进行${testType}自检（距上次已${days}天）`
})

// 快捷操作状态
const quickActionLoading = ref<Record<string, boolean>>({})

// 事件详情相关状态
const showEventDetailDialog = ref(false)
const currentEvent = ref<Event | null>(null)

// 初始加载状态
const isInitialLoading = ref(true)

// 定时器引用
let metricsRefreshTimer: number | null = null
let predictionsRefreshTimer: number | null = null
let analyticsRefreshTimer: number | null = null
let eventsRefreshTimer: number | null = null
let lastMetricsRefresh = 0  // 上次 metrics 刷新时间戳

// 智能预测相关状态
const predictions = ref<any>(null)

// 设备操作相关状态
const showDeviceShutdownConfirm = ref(false)
const showLogsDialog = ref(false)
const showDeviceConfigDialog = ref(false)
const currentDevice = ref<Device | null>(null)
const deviceOperating = ref(false)
const logsLoading = ref(false)
const logsContent = ref('')
const logsError = ref('')
const logsCommand = ref('')

// 电池安装日期相关状态
const configData = ref<any>(null)
const editingBatteryDate = ref(false)
const newBatteryDate = ref('')

const fetchRecentEvents = async () => {
  try {
    const response = await axios.get('/api/history/events?days=1')
    recentEvents.value = response.data.events.slice(0, 10)
  } catch (error) {
    console.error('Failed to fetch events:', error)
  }
}

const loadConfig = async () => {
  try {
    const response = await fetch('/api/config')
    if (response.ok) {
      configData.value = await response.json()
    }
  } catch (error) {
    console.error('加载配置失败:', error)
  }
}

const fetchMetrics = async () => {
  try {
    const response = await axios.get('/api/history/metrics?hours=1')
    metrics.value = response.data.metrics
    lastMetricsRefresh = Date.now()
  } catch (error) {
    console.error('Failed to fetch metrics:', error)
  }
}

const fetchPredictions = async () => {
  try {
    const response = await axios.get('/api/predictions')
    predictions.value = response.data
  } catch (error) {
    console.error('Failed to fetch predictions:', error)
    predictions.value = null
  }
}

// ========== 电池分析 ==========
const fetchAnalytics = async () => {
  try {
    const response = await axios.get('/api/analytics/battery')
    batteryAnalytics.value = response.data
  } catch (error) {
    console.error('Failed to fetch analytics:', error)
    batteryAnalytics.value = null
  }
}

// ========== 快捷操作 ==========
const runSelfTest = async (deep: boolean) => {
  setQuickActionLoading(deep ? 'deepTest' : 'quickTest', true)
  try {
    await axios.post(`/api/quick/test-battery?deep=${deep}`)
    toast.success(deep ? '深度自检已启动' : '快速自检已启动')
    await fetchMetrics()
  } catch (error: any) {
    toast.error('自检失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    setQuickActionLoading(deep ? 'deepTest' : 'quickTest', false)
  }
}

const cancelShutdown = async () => {
  setQuickActionLoading('cancelShutdown', true)
  try {
    await axios.post('/api/quick/cancel-shutdown')
    toast.success('关机已取消')
    await fetchMetrics()
    await fetchShutdownStatus()
  } catch (error: any) {
    toast.error('取消失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    setQuickActionLoading('cancelShutdown', false)
  }
}

const setQuickActionLoading = (key: string, loading: boolean) => {
  quickActionLoading.value[key] = loading
}

// 计算是否有可用的预测
const hasPredictions = computed(() => {
  if (!predictions.value) return false
  return predictions.value.battery_health?.available ||
         predictions.value.outage_duration?.available ||
         predictions.value.runtime_prediction?.available ||
         predictions.value.anomalies?.available
})

const fetchDevicesStatus = async () => {
  devicesLoading.value = true
  try {
    // Fetch devices list with full config
    const devicesResponse = await axios.get('/api/devices')
    const devicesList = devicesResponse.data.devices || []
    
    // Fetch status for all devices
    const statusResponse = await axios.get('/api/devices/status')
    const statusList = statusResponse.data.devices || []
    
    // Merge config and status by index
    devices.value = devicesList.map((device: any, index: number) => {
      const status = statusList.find((s: any) => s.index === index) || {}
      return {
        index,
        name: device.name,
        hook_id: device.hook_id,
        priority: device.priority,
        online: status.online || false,
        last_check: status.last_check || new Date().toISOString(),
        error: status.error || null,
        config: device.config || {},
        supported_actions: status.supported_actions || device.supported_actions || []
      }
    })
    
    // Update last refresh time
    lastDeviceRefresh.value = new Date()
  } catch (error) {
    console.error('[Dashboard.vue] ❌ Failed to fetch devices status:', error)
  } finally {
    devicesLoading.value = false
  }
}

// 加载配置并设置自动刷新
const loadConfigAndSetupRefresh = async () => {
  try {
    const response = await axios.get('/api/config')
    const config = response.data
    deviceRefreshIntervalSeconds.value = config.device_status_check_interval_seconds || 60
    
    // 设置自动刷新
    setupDeviceAutoRefresh()
  } catch (error) {
    console.error('Failed to load config:', error)
  }
}

// 设置设备状态自动刷新
const setupDeviceAutoRefresh = () => {
  // 清除已存在的定时器
  if (deviceRefreshInterval.value !== null) {
    clearInterval(deviceRefreshInterval.value)
    deviceRefreshInterval.value = null
  }
  
  const interval = deviceRefreshIntervalSeconds.value
  
  // 如果间隔为 0，表示禁用自动刷新
  if (interval === 0) {
    return
  }
  
  // 设置新的定时器
  deviceRefreshInterval.value = window.setInterval(() => {
    if (!devicesLoading.value) {
      fetchDevicesStatus()
    }
  }, interval * 1000)
}

const testDeviceConnection = async (device: Device) => {
  const deviceKey = `${device.index}-${device.hook_id}-${device.name}`
  testingDevices.value.add(deviceKey)
  
  try {
    const response = await axios.post(`/api/devices/${device.index}/check`)
    
    // 更新设备状态
    const index = devices.value.findIndex(d => d.index === device.index)
    if (index !== -1) {
      devices.value[index] = {
        ...devices.value[index],
        online: response.data.online,
        last_check: new Date().toISOString(),
        error: response.data.error
      }
    }
    
    // 显示成功提示
    if (response.data.online) {
      toast.success(`设备 ${device.name} 连接正常`)
    } else {
      toast.warning(`设备 ${device.name} 离线或无法连接`)
    }
  } catch (error: any) {
    console.error('Failed to test device connection:', error)
    const index = devices.value.findIndex(d => d.index === device.index)
    if (index !== -1) {
      devices.value[index] = {
        ...devices.value[index],
        online: false,
        last_check: new Date().toISOString(),
        error: error.response?.data?.detail || '测试失败'
      }
    }
    // 显示错误提示
    toast.error(`设备 ${device.name} 测试失败: ${error.response?.data?.detail || '连接错误'}`)
  } finally {
    testingDevices.value.delete(deviceKey)
  }
}

const confirmManualShutdown = async () => {
  if (isShuttingDown.value) return  // 防止重复点击

  isShuttingDown.value = true
  try {
    await axios.post('/api/actions/shutdown')
    showShutdownConfirm.value = false
    toast.success('关机命令已发送')
    
    // 立即更新前端状态，显示关机倒计时
    if (wsData.value) {
      wsData.value = {
        ...wsData.value,
        shutdown: {
          shutting_down: true,
          remaining_seconds: 0,
          in_final_countdown: false
        }
      }
    }
    
    // 将所有设备状态设为离线
    devices.value = devices.value.map(device => ({
      ...device,
      online: false,
      last_check: new Date().toISOString()
    }))
  } catch (error) {
    console.error('Failed to trigger shutdown:', error)
    toast.error('触发关机失败')
  } finally {
    isShuttingDown.value = false
  }
}

// UPS 命令执行相关
const upsCommandLoading = ref(false)
const beeperToggleLoading = ref(false)
const beeperMuteLoading = ref(false)
const batteryTestLoading = ref(false)

const isBatteryTesting = computed(() => {
  const result = upsData.value?.ups_test_result
  return result && result.toLowerCase().includes('progress')
})

const executeUpsCommand = async (command: string, successMsg: string) => {
  if (upsCommandLoading.value) return
  upsCommandLoading.value = true
  try {
    const response = await axios.post('/api/ups/command', { command })
    if (response.data.success) {
      toast.success(successMsg)
    } else {
      toast.error(response.data.message || '命令执行失败')
    }
  } catch (error: any) {
    toast.error(error.response?.data?.detail || '命令执行失败')
  } finally {
    upsCommandLoading.value = false
  }
}

const toggleBeeper = async () => {
  const current = upsData.value?.ups_beeper_status
  const targetStatus = current === 'enabled' ? 'disabled' : 'enabled'
  const action = current === 'enabled' ? 'disable' : 'enable'
  const successMsg = current === 'enabled' ? '蜂鸣器已禁用' : '蜂鸣器已启用'
  
  if (beeperToggleLoading.value) return
  beeperToggleLoading.value = true
  
  try {
    // 使用便捷端点，后端会自动回退到 beeper.toggle（如果 UPS 不支持 enable/disable）
    const response = await axios.post(`/api/ups/beeper/${action}`)
    if (response.data.success) {
      toast.success(successMsg)
      
      // 等待WebSocket更新或超时（最多10秒）
      const startTime = Date.now()
      const checkInterval = setInterval(() => {
        const elapsed = Date.now() - startTime
        if (upsData.value?.ups_beeper_status === targetStatus || elapsed > 10000) {
          clearInterval(checkInterval)
          beeperToggleLoading.value = false
        }
      }, 100)
    } else {
      toast.error(response.data.message || '命令执行失败')
      beeperToggleLoading.value = false
    }
  } catch (error: any) {
    toast.error(error.response?.data?.detail || '命令执行失败')
    beeperToggleLoading.value = false
  }
}

const muteBeeper = async () => {
  if (beeperMuteLoading.value) return
  beeperMuteLoading.value = true
  
  try {
    // 使用便捷端点，后端会自动回退到 beeper.toggle（如果 UPS 不支持 mute）
    const response = await axios.post('/api/ups/beeper/mute')
    if (response.data.success) {
      toast.success('蜂鸣器已临时静音')
    } else {
      toast.error(response.data.message || '命令执行失败')
    }
  } catch (error: any) {
    toast.error(error.response?.data?.detail || '命令执行失败')
  } finally {
    // 静音操作没有状态变化，直接在1秒后恢复
    setTimeout(() => {
      beeperMuteLoading.value = false
    }, 1000)
  }
}

// 电池测试确认对话框
const showBatteryTestConfirm = ref(false)
const pendingTestType = ref<string>('')

const startBatteryTest = (type: string) => {
  // 显示确认对话框
  pendingTestType.value = type
  showBatteryTestConfirm.value = true
}

const confirmBatteryTest = async () => {
  const type = pendingTestType.value
  showBatteryTestConfirm.value = false

  // 调用测试 API
  batteryTestLoading.value = true
  try {
    const response = await axios.post(`/api/ups/test-battery/${type}`)
    if (response.data.success) {
      const label = type === 'deep' ? '深度电池测试' : '快速电池测试'
      toast.success(`${label}已启动，请等待测试完成...`)
      
      // 等待WebSocket更新测试状态（最多10秒）
      const startTime = Date.now()
      const checkInterval = setInterval(() => {
        const elapsed = Date.now() - startTime
        const testResult = upsData.value?.ups_test_result
        const isInProgress = testResult && testResult.toLowerCase().includes('progress')
        
        if (isInProgress || elapsed > 10000) {
          clearInterval(checkInterval)
          batteryTestLoading.value = false
        }
      }, 100)
    } else {
      toast.error(response.data.message || '测试启动失败')
      batteryTestLoading.value = false
    }
  } catch (error: any) {
    toast.error(error.response?.data?.detail || '测试启动失败')
    batteryTestLoading.value = false
  }
}

const stopBatteryTest = async () => {
  batteryTestLoading.value = true
  try {
    const response = await axios.post('/api/ups/command', { command: 'test.battery.stop' })
    if (response.data.success) {
      toast.success('电池测试已停止')
      
      // 等待WebSocket更新测试状态（最多10秒）
      const startTime = Date.now()
      const checkInterval = setInterval(() => {
        const elapsed = Date.now() - startTime
        const testResult = upsData.value?.ups_test_result
        const isInProgress = testResult && testResult.toLowerCase().includes('progress')
        
        if (!isInProgress || elapsed > 10000) {
          clearInterval(checkInterval)
          batteryTestLoading.value = false
        }
      }, 100)
    } else {
      toast.error(response.data.message || '命令执行失败')
      batteryTestLoading.value = false
    }
  } catch (error: any) {
    toast.error(error.response?.data?.detail || '命令执行失败')
    batteryTestLoading.value = false
  }
}

// UPS 参数编辑相关
const showUpsParamConfirm = ref(false)
const paramEditLoading = ref(false)
const pendingParamChange = ref({
  varName: '',
  description: '',
  oldValue: '',
  newValue: '',
  onConfirm: null as (() => Promise<void>) | null
})

// 电压安全区间编辑
const showVoltageRangeEdit = ref(false)
const editVoltageRange = ref({ low: 0, high: 0 })

const openVoltageRangeEdit = () => {
  if (!upsData.value) return
  editVoltageRange.value = {
    low: upsData.value.input_transfer_low || 0,
    high: upsData.value.input_transfer_high || 0
  }
  showVoltageRangeEdit.value = true
}

const saveVoltageRange = async () => {
  if (!upsData.value) return
  const oldLow = upsData.value.input_transfer_low
  const oldHigh = upsData.value.input_transfer_high
  const newLow = editVoltageRange.value.low
  const newHigh = editVoltageRange.value.high

  showVoltageRangeEdit.value = false
  
  // 准备确认对话框
  pendingParamChange.value = {
    varName: 'input.transfer.low & input.transfer.high',
    description: '电压安全区间',
    oldValue: `${oldLow} - ${oldHigh} V`,
    newValue: `${newLow} - ${newHigh} V`,
    onConfirm: async () => {
      // 智能排序：如果新 low 值更高，先设置 high 再设置 low，避免临时冲突
      // 如果新 high 值更低，先设置 low 再设置 high
      if (newLow > (oldHigh || 0)) {
        // 先提高 high，再提高 low
        await setUpsVar('input.transfer.high', newHigh.toString())
        await setUpsVar('input.transfer.low', newLow.toString())
      } else if (newHigh < (oldLow || 999)) {
        // 先降低 low，再降低 high
        await setUpsVar('input.transfer.low', newLow.toString())
        await setUpsVar('input.transfer.high', newHigh.toString())
      } else {
        // 安全情况：按正常顺序设置
        await setUpsVar('input.transfer.low', newLow.toString())
        await setUpsVar('input.transfer.high', newHigh.toString())
      }
    }
  }
  showUpsParamConfirm.value = true
}

// 输入灵敏度编辑
const showSensitivityEdit = ref(false)
const editSensitivity = ref('')

const openSensitivityEdit = () => {
  if (!upsData.value) return
  editSensitivity.value = upsData.value.input_sensitivity || 'medium'
  showSensitivityEdit.value = true
}

const saveSensitivity = () => {
  if (!upsData.value) return
  const oldValue = upsData.value.input_sensitivity
  const newValue = editSensitivity.value
  
  showSensitivityEdit.value = false
  
  // 准备确认对话框
  pendingParamChange.value = {
    varName: 'input.sensitivity',
    description: '输入灵敏度',
    oldValue: formatSensitivity(oldValue),
    newValue: formatSensitivity(newValue),
    onConfirm: async () => {
      await setUpsVar('input.sensitivity', newValue)
    }
  }
  showUpsParamConfirm.value = true
}

// 关机延迟编辑
const showShutdownDelayEdit = ref(false)
const editShutdownDelay = ref(0)

const openShutdownDelayEdit = () => {
  if (!upsData.value) return
  editShutdownDelay.value = upsData.value.ups_delay_shutdown || 0
  showShutdownDelayEdit.value = true
}

const saveShutdownDelay = () => {
  if (!upsData.value) return
  const oldValue = upsData.value.ups_delay_shutdown
  const newValue = editShutdownDelay.value
  
  showShutdownDelayEdit.value = false
  
  // 准备确认对话框
  pendingParamChange.value = {
    varName: 'ups.delay.shutdown',
    description: 'UPS 关机延迟',
    oldValue: `${oldValue} 秒`,
    newValue: `${newValue} 秒`,
    onConfirm: async () => {
      await setUpsVar('ups.delay.shutdown', newValue.toString())
    }
  }
  showUpsParamConfirm.value = true
}

// 电池安装日期编辑
const startEditBatteryDate = () => {
  newBatteryDate.value = effectiveBatteryDate.value.date || ''
  editingBatteryDate.value = true
}

const cancelEditBatteryDate = () => {
  editingBatteryDate.value = false
  newBatteryDate.value = ''
}

const saveBatteryDate = async () => {
  try {
    const oldDate = effectiveBatteryDate.value.date
    
    // 验证日期
    if (newBatteryDate.value) {
      const dateObj = new Date(newBatteryDate.value)
      if (isNaN(dateObj.getTime())) {
        toast.error('无效的日期格式')
        return
      }
      if (dateObj > new Date()) {
        toast.error('日期不能是未来日期')
        return
      }
    }
    
    // 更新配置
    const response = await fetch('/api/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...configData.value,
        battery_install_date: newBatteryDate.value || null
      })
    })
    
    if (!response.ok) throw new Error('保存失败')
    
    // 如果是日期变更，记录事件
    if (oldDate && oldDate !== newBatteryDate.value) {
      await fetch('/api/history/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_type: 'BATTERY_REPLACED',
          message: `电池已更换 (从 ${oldDate} 更新为 ${newBatteryDate.value})`,
          metadata: {
            old_date: oldDate,
            new_date: newBatteryDate.value,
            timestamp: new Date().toISOString()
          }
        })
      })
    }
    
    await loadConfig()
    editingBatteryDate.value = false
    toast.success('电池日期已保存')
  } catch (error) {
    console.error('保存电池日期失败:', error)
    toast.error('保存失败，请重试')
  }
}

// 确认参数修改
const confirmUpsParamChange = async () => {
  if (!pendingParamChange.value.onConfirm) return
  
  paramEditLoading.value = true
  try {
    await pendingParamChange.value.onConfirm()
    showUpsParamConfirm.value = false
    toast.success('参数修改成功')
  } catch (error: any) {
    toast.error(error.response?.data?.detail || '参数修改失败')
  } finally {
    paramEditLoading.value = false
  }
}

// API 函数：获取可写变量（可用于未来动态显示可编辑参数）
const fetchWritableVars = async () => {
  try {
    const response = await axios.get('/api/ups/writable-vars')
    return response.data
  } catch (error: any) {
    toast.error(error.response?.data?.detail || '获取可写变量失败')
    throw error
  }
}

// API 函数：设置 UPS 变量
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

// 测试报告相关
const showTestReportDialog = ref(false)
const testReportLoading = ref(false)
const testReport = ref<any>(null)
const latestHistoryReport = ref<any>(null)

// 辅助函数
const formatDurationSimple = (seconds: number) => {
  if (!seconds) return 'N/A'
  if (seconds < 60) return `${seconds}秒`
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  return secs > 0 ? `${minutes}分${secs}秒` : `${minutes}分钟`
}

const formatRuntimeMinutes = (seconds: number | null | undefined) => {
  if (seconds === null || seconds === undefined) return 'N/A'
  const minutes = Math.floor(seconds / 60)
  return `${minutes}分钟`
}

const getVoltageChange = (report: any) => {
  if (!report?.start_data?.battery_voltage || !report?.end_data?.battery_voltage) return null
  return report.end_data.battery_voltage - report.start_data.battery_voltage
}

const formatVoltageChange = (report: any) => {
  const change = getVoltageChange(report)
  if (change === null) return 'N/A'
  return (change > 0 ? '+' : '') + change.toFixed(2) + 'V'
}

const getChangeClass = (change: number | null) => {
  if (change === null) return ''
  if (change < 0) return 'change-negative'
  if (change > 0) return 'change-positive'
  return ''
}

const showTestReport = async () => {
  showTestReportDialog.value = true
  testReportLoading.value = true
  testReport.value = null
  latestHistoryReport.value = null

  try {
    // 同时获取实时状态和历史报告
    const [statusResponse, historyResponse] = await Promise.all([
      axios.get('/api/ups/test-report'),
      axios.get('/api/ups/test-reports?limit=1')
    ])

    testReport.value = statusResponse.data

    // 获取最新的历史报告
    const reports = historyResponse.data.reports || []
    if (reports.length > 0) {
      latestHistoryReport.value = reports[0]
    }
  } catch (error: any) {
    console.error('Failed to get test report:', error)
    toast.error(error.response?.data?.detail || '获取测试报告失败')
  } finally {
    testReportLoading.value = false
  }
}

const downloadTestReport = () => {
  if (!testReport.value) return

  const report = testReport.value
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)

  // 测试类型文本
  const testTypeText = report.test_info.type_label
    ? `**测试类型**: ${report.test_info.type === 'quick' ? '⚡' : '🔋'} ${report.test_info.type_label}`
    : ''

  const startedAtText = report.test_info.started_at
    ? `**开始时间**: ${formatDateTime(report.test_info.started_at)}`
    : ''

  // 生成 Markdown 格式报告
  let markdown = `# UPS 测试报告

> 生成时间: ${formatDateTime(report.generated_at)}

## 📋 测试结果

${testTypeText}

**测试状态**: ${report.test_info.icon} ${report.test_info.result}

${startedAtText}

${report.test_info.date !== 'N/A' ? `**UPS 记录时间**: ${report.test_info.date}` : ''}

---

## 🔌 UPS 信息

| 项目 | 值 |
|------|-----|
| 制造商 | ${report.ups_info.manufacturer} |
| 型号 | ${report.ups_info.model} |
| 序列号 | ${report.ups_info.serial} |
| 额定功率 | ${report.ups_info.nominal_power}W |
| 固件版本 | ${report.ups_info.firmware} |

---

## 📊 当前状态

**状态标志**: ${report.current_status.status_raw}

${report.current_status.status_flags.map((f: any) => `- ${f.description}`).join('\n')}

| 项目 | 值 |
|------|-----|
| 负载 | ${report.current_status.load_percent}% |
| 输入电压 | ${report.current_status.input_voltage}V |
| 输出电压 | ${report.current_status.output_voltage}V |

---

## 🔋 电池信息

| 项目 | 值 |
|------|-----|
| 电量 | ${report.battery_info.charge_percent}% |
| 电压 | ${report.battery_info.voltage}V (额定 ${report.battery_info.voltage_nominal}V) |
| 剩余时间 | ${report.battery_info.runtime_display} |
| 电池类型 | ${report.battery_info.type} |
${report.battery_info.temperature !== 'N/A' ? `| 温度 | ${report.battery_info.temperature}°C |` : ''}

---

## 🔔 蜂鸣器

状态: ${report.beeper.status === 'enabled' ? '🔔 已启用' : report.beeper.status === 'disabled' ? '🔕 已禁用' : report.beeper.status}

---

## ℹ️ 驱动信息

- 驱动: ${report.driver_info.name}
- 版本: ${report.driver_info.version}

---

*报告由 UPS Guard 自动生成*
`

  // 创建下载
  const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `ups-test-report-${timestamp}.md`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)

  toast.success('报告已下载')
}


// 设备关机
const shutdownDevice = (device: Device) => {
  currentDevice.value = device
  showDeviceShutdownConfirm.value = true
}

const confirmDeviceShutdown = async () => {
  if (!currentDevice.value || deviceOperating.value) return

  deviceOperating.value = true
  try {
    const response = await axios.post(`/api/devices/${currentDevice.value.index}/shutdown`)
    if (response.data.success) {
      toast.success(`设备 ${currentDevice.value.name} 关机命令已发送`)
      showDeviceShutdownConfirm.value = false
      
      // 立即更新设备在线状态为 false
      const deviceIndex = devices.value.findIndex(d => d.index === currentDevice.value!.index)
      if (deviceIndex !== -1) {
        devices.value[deviceIndex] = {
          ...devices.value[deviceIndex],
          online: false,
          last_check: new Date().toISOString()
        }
      }
      
      // 通知全局导航按钮更新
      window.dispatchEvent(new CustomEvent('device-state-changed'))
      
      // 延迟刷新设备列表
      setTimeout(() => {
        fetchDevicesStatus()
      }, 2000)
    } else {
      toast.error(`设备关机失败: ${response.data.message}`)
    }
  } catch (error: any) {
    console.error('[Dashboard.vue] ❌ Failed to shutdown device:', error)
    toast.error(`设备关机失败: ${error.response?.data?.detail || error.message}`)
  } finally {
    deviceOperating.value = false
  }
}

// 唤醒设备
const wakeDevice = async (device: Device) => {
  if (deviceOperating.value) return

  deviceOperating.value = true
  try {
    const response = await axios.post(`/api/devices/${device.index}/wake`)
    if (response.data.success) {
      toast.success(`WOL 魔术包已发送到设备 ${device.name}`)
      
      // 通知全局导航按钮更新
      window.dispatchEvent(new CustomEvent('device-state-changed'))
    } else {
      toast.error(`唤醒失败: ${response.data.message}`)
    }
  } catch (error: any) {
    console.error('[Dashboard.vue] ❌ Failed to wake device:', error)
    toast.error(`唤醒失败: ${error.response?.data?.detail || error.message}`)
  } finally {
    deviceOperating.value = false
  }
}

// 重启设备
const rebootDevice = async (device: Device) => {
  if (deviceOperating.value) return
  
  if (!confirm(`确认要重启设备 ${device.name} 吗？`)) return

  deviceOperating.value = true
  try {
    const response = await axios.post(`/api/devices/${device.index}/reboot`)
    if (response.data.success) {
      toast.success(`设备 ${device.name} 重启命令已发送`)
      
      // 通知全局导航按钮更新
      window.dispatchEvent(new CustomEvent('device-state-changed'))
    } else {
      toast.error(`重启失败: ${response.data.message}`)
    }
  } catch (error: any) {
    console.error('[Dashboard.vue] ❌ Failed to reboot device:', error)
    toast.error(`重启失败: ${error.response?.data?.detail || error.message}`)
  } finally {
    deviceOperating.value = false
  }
}

// 睡眠设备
const sleepDevice = async (device: Device) => {
  if (deviceOperating.value) return
  
  if (!confirm(`确认要让设备 ${device.name} 进入睡眠模式吗？`)) return

  deviceOperating.value = true
  try {
    const response = await axios.post(`/api/devices/${device.index}/sleep`)
    if (response.data.success) {
      toast.success(`设备 ${device.name} 睡眠命令已发送`)
      
      // 通知全局导航按钮更新
      window.dispatchEvent(new CustomEvent('device-state-changed'))
    } else {
      toast.error(`睡眠失败: ${response.data.message}`)
    }
  } catch (error: any) {
    console.error('[Dashboard.vue] ❌ Failed to sleep device:', error)
    toast.error(`睡眠失败: ${error.response?.data?.detail || error.message}`)
  } finally {
    deviceOperating.value = false
  }
}

// 休眠设备
const hibernateDevice = async (device: Device) => {
  if (deviceOperating.value) return
  
  if (!confirm(`确认要让设备 ${device.name} 进入休眠模式吗？`)) return

  deviceOperating.value = true
  try {
    const response = await axios.post(`/api/devices/${device.index}/hibernate`)
    if (response.data.success) {
      toast.success(`设备 ${device.name} 休眠命令已发送`)
      
      // 通知全局导航按钮更新
      window.dispatchEvent(new CustomEvent('device-state-changed'))
    } else {
      toast.error(`休眠失败: ${response.data.message}`)
    }
  } catch (error: any) {
    console.error('[Dashboard.vue] ❌ Failed to hibernate device:', error)
    toast.error(`休眠失败: ${error.response?.data?.detail || error.message}`)
  } finally {
    deviceOperating.value = false
  }
}

// 测试 WOL（即使设备在线）
const testWOL = async (device: Device) => {
  if (deviceOperating.value) return

  deviceOperating.value = true
  try {
    const response = await axios.post(`/api/devices/${device.index}/wake`)
    if (response.data.success) {
      toast.success(`WOL 测试成功！魔术包已发送到设备 ${device.name} (${device.config?.mac_address})`)
    } else {
      toast.error(`WOL 测试失败: ${response.data.message}`)
    }
  } catch (error: any) {
    console.error('Failed to test WOL:', error)
    toast.error(`WOL 测试失败: ${error.response?.data?.detail || error.message}`)
  } finally {
    deviceOperating.value = false
  }
}

// 检查是否所有设备都已离线
const allDevicesOffline = computed(() => {
  return devices.value.length > 0 && devices.value.every(device => !device.online)
})

// 唤醒所有设备
const wakeAllDevices = async () => {
  if (deviceOperating.value) return
  
  // 获取所有有 MAC 地址的设备
  const devicesWithMAC = devices.value.filter(d => d.config?.mac_address)
  
  if (devicesWithMAC.length === 0) {
    toast.error('没有配置 MAC 地址的设备可以唤醒')
    return
  }
  
  deviceOperating.value = true
  let successCount = 0
  let failCount = 0
  
  try {
    // 逐一发送 WOL 到所有设备
    for (const device of devicesWithMAC) {
      try {
        const response = await axios.post(`/api/devices/${device.index}/wake`)
        if (response.data.success) {
          successCount++
        } else {
          failCount++
        }
      } catch (error) {
        console.error(`Failed to wake device ${device.name}:`, error)
        failCount++
      }
    }
    
    // 显示结果
    if (successCount > 0 && failCount === 0) {
      toast.success(`✅ 成功发送 WOL 到 ${successCount} 台设备`)
    } else if (successCount > 0) {
      toast.success(`部分成功：${successCount} 台成功，${failCount} 台失败`)
    } else {
      toast.error('全部唤醒失败')
    }
    
    // 通知全局导航按钮更新
    window.dispatchEvent(new CustomEvent('device-state-changed'))
    
    // 刷新设备状态
    setTimeout(() => {
      fetchDevicesStatus()
    }, 3000)
  } finally {
    deviceOperating.value = false
  }
}


// 查看日志
const showLogsViewer = (device: Device) => {
  currentDevice.value = device
  logsContent.value = ''
  logsError.value = ''
  logsCommand.value = ''
  showLogsDialog.value = true
  fetchDeviceLogs()
}

const fetchDeviceLogs = async () => {
  if (!currentDevice.value || logsLoading.value) return
  
  logsLoading.value = true
  logsError.value = ''
  logsContent.value = ''
  logsCommand.value = ''
  
  try {
    // 获取该设备的操作记录（从history events）
    const response = await axios.get('/api/history/events', {
      params: {
        days: 30  // 获取最近30天的事件
      }
    })
    
    if (response.data.events) {
      // 过滤该设备相关的事件
      const deviceEvents = response.data.events.filter((event: any) => {
        const metadata = event.metadata
        return metadata && 
               (metadata.device_index === currentDevice.value!.index ||
                metadata.device_name === currentDevice.value!.name)
      })
      
      if (deviceEvents.length === 0) {
        logsContent.value = `暂无设备 ${currentDevice.value.name} 的操作记录`
      } else {
        // 格式化事件为日志文本
        logsContent.value = deviceEvents.map((event: any) => {
          const timestamp = new Date(event.timestamp).toLocaleString('zh-CN')
          const eventTypeMap: Record<string, string> = {
            'DEVICE_SHUTDOWN': '关机',
            'DEVICE_WAKE': 'WOL唤醒',
            'DEVICE_REBOOT': '重启',
            'DEVICE_SLEEP': '睡眠',
            'DEVICE_HIBERNATE': '休眠',
            'DEVICE_TEST_CONNECTION': '连接测试'
          }
          const eventType = eventTypeMap[event.event_type] || event.event_type
          return `[${timestamp}] ${eventType}: ${event.message}`
        }).join('\n')
        
        logsCommand.value = '设备操作历史记录'
      }
    } else {
      logsError.value = '未获取到事件数据'
    }
  } catch (error: any) {
    console.error('Failed to fetch device logs:', error)
    logsError.value = error.response?.data?.detail || error.message
  } finally {
    logsLoading.value = false
  }
}

const copyLogs = async () => {
  if (!logsContent.value) return
  
  try {
    await navigator.clipboard.writeText(logsContent.value)
    toast.success('日志已复制到剪贴板')
  } catch (error) {
    console.error('Failed to copy logs:', error)
    toast.error('复制失败')
  }
}

// 编辑设备配置
const editDeviceConfig = (device: Device) => {
  // Show config modal instead of navigating
  currentDevice.value = device
  showDeviceConfigDialog.value = true
}

// 前往设置页编辑
const goToSettings = () => {
  if (!currentDevice.value || currentDevice.value.index === undefined) return
  router.push({
    path: '/settings',
    query: { device: currentDevice.value.index.toString() }
  })
}

// 格式化配置键名
const formatConfigKey = (key: string): string => {
  const keyMap: Record<string, string> = {
    'host': '主机地址',
    'port': 'SSH 端口',
    'username': '用户名',
    'auth_type': '认证方式',
    'password': '密码',
    'private_key': '私钥',
    'mac_address': 'MAC 地址',
    'broadcast_address': '广播地址',
    'shutdown_command': '关机命令',
    'pre_commands': '预执行命令',
    'timeout': '超时时间'
  }
  return keyMap[key] || key
}

// 判断是否为敏感字段
const isSensitiveField = (key: string): boolean => {
  return ['password', 'private_key', 'token', 'secret', 'api_key'].includes(key)
}

// 获取 Hook 类型名称
const getHookTypeName = (hookId: string): string => {
  const typeMap: Record<string, string> = {
    'ssh_shutdown': 'SSH 远程关机',
    'synology_shutdown': 'Synology NAS 关机',
    'qnap_shutdown': 'QNAP NAS 关机',
    'windows_shutdown': 'Windows 远程关机',
    'lazycat_shutdown': 'LazyCAT 关机',
    'http_api': 'HTTP API 调用',
    'custom_script': '自定义脚本'
  }
  return typeMap[hookId] || hookId
}


const formatRuntimeDetailed = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours > 0) {
    return `${hours} 小时 ${minutes} 分钟`
  }
  return `${minutes} 分钟`
}

const getBatteryColor = (charge: number | null): string => {
  if (charge === null) return '#9CA3AF'
  if (charge <= 20) return '#EF4444'  // 红色 - 危险
  if (charge <= 50) return '#F59E0B'  // 黄色 - 警告
  return '#10B981'  // 绿色 - 正常
}

const formatDateTime = (isoString: string): string => {
  // Backend sends naive datetime (no timezone info)
  // JavaScript Date() interprets ISO strings without 'Z' or offset as local time when using certain formats
  // But ISO 8601 format with 'T' is interpreted as UTC by some browsers
  // Solution: Parse as local time explicitly
  
  if (!isoString.endsWith('Z') && !isoString.match(/[+-]\d{2}:\d{2}$/)) {
    // No timezone info - treat as local time
    // Parse the ISO string and create date in local timezone
    const parts = isoString.split(/[-T:.]/)
    const year = parseInt(parts[0])
    const month = parseInt(parts[1]) - 1 // JavaScript months are 0-indexed
    const day = parseInt(parts[2])
    const hour = parseInt(parts[3] || '0')
    const minute = parseInt(parts[4] || '0')
    const second = parseInt(parts[5] || '0')
    
    const date = new Date(year, month, day, hour, minute, second)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    })
  }
  
  // Has timezone info - use as-is
  return new Date(isoString).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

// 格式化分钟数为易读格式
const formatMinutes = (minutes: number): string => {
  if (minutes < 60) {
    return `${minutes}分钟`
  } else if (minutes < 1440) {
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    return mins > 0 ? `${hours}小时${mins}分` : `${hours}小时`
  } else {
    const days = Math.floor(minutes / 1440)
    const hours = Math.floor((minutes % 1440) / 60)
    return hours > 0 ? `${days}天${hours}小时` : `${days}天`
  }
}

const getEventTypeText = (type: string): string => {
  const map: Record<string, string> = {
    'POWER_LOST': '断电',
    'POWER_RESTORED': '恢复供电',
    'LOW_BATTERY': '低电量',
    'SHUTDOWN': '关机',
    'STARTUP': '启动',
    'SHUTDOWN_CANCELLED': '取消关机',
    // 设备操作事件
    'DEVICE_SHUTDOWN': '设备关机',
    'DEVICE_WAKE': '设备唤醒',
    'DEVICE_REBOOT': '设备重启',
    'DEVICE_SLEEP': '设备睡眠',
    'DEVICE_HIBERNATE': '设备休眠',
    'DEVICE_TEST_CONNECTION': '测试连接',
    // NUT 连接事件
    'NUT_DISCONNECTED': 'NUT断开',
    'NUT_RECONNECTED': 'NUT重连',
    // 细化的诊断事件
    'BACKEND_ERROR': '后端异常',
    'BACKEND_RESTORED': '后端恢复',
    'NUT_SERVER_DISCONNECTED': 'NUT服务器断开',
    'NUT_SERVER_CONNECTED': 'NUT服务器连接',
    'UPS_DRIVER_ERROR': '驱动异常',
    'UPS_DRIVER_DUMMY': '驱动dummy',
    'UPS_DRIVER_CONNECTED': '驱动连接',
    // UPS 参数配置事件
    'UPS_PARAM_CHANGED': '参数修改',
    // 电池维护事件
    'BATTERY_REPLACED': '电池更换',
    // 兼容旧事件
    'CONNECTION_ISSUE': '连接问题',
    'CONNECTION_RESTORED': '连接恢复'
  }
  return map[type] || type
}

// 获取事件类型对应的图标
const getEventTypeIcon = (type: string): string => {
  const iconMap: Record<string, string> = {
    'POWER_LOST': '⚡',
    'POWER_RESTORED': '✅',
    'LOW_BATTERY': '🔋',
    'SHUTDOWN': '🔴',
    'STARTUP': '🟢',
    'SHUTDOWN_CANCELLED': '⏹️',
    // 设备操作事件
    'DEVICE_SHUTDOWN': '🔴',
    'DEVICE_WAKE': '⏰',
    'DEVICE_REBOOT': '🔄',
    'DEVICE_SLEEP': '😴',
    'DEVICE_HIBERNATE': '🐻',
    'DEVICE_TEST_CONNECTION': '🔍',
    // NUT 连接事件
    'NUT_DISCONNECTED': '🔌',
    'NUT_RECONNECTED': '🔗',
    // 诊断事件
    'BACKEND_ERROR': '⚠️',
    'BACKEND_RESTORED': '✅',
    'NUT_SERVER_DISCONNECTED': '🔌',
    'NUT_SERVER_CONNECTED': '🔗',
    'UPS_DRIVER_ERROR': '⚠️',
    'UPS_DRIVER_DUMMY': '🧪',
    'UPS_DRIVER_CONNECTED': '✅',
    // UPS 参数配置事件
    'UPS_PARAM_CHANGED': '🔧',
    // 电池维护事件
    'BATTERY_REPLACED': '🔋',
    'CONNECTION_ISSUE': '⚠️',
    'CONNECTION_RESTORED': '✅'
  }
  return iconMap[type] || '📋'
}

// 显示事件详情
const showEventDetail = (event: Event) => {
  currentEvent.value = event
  showEventDetailDialog.value = true
}

// 解析事件元数据
const parsedEventMetadata = computed(() => {
  if (!currentEvent.value?.metadata) return {}
  try {
    if (typeof currentEvent.value.metadata === 'string') {
      return JSON.parse(currentEvent.value.metadata)
    }
    return currentEvent.value.metadata
  } catch {
    return {}
  }
})

// 格式化元数据键名
const formatMetadataKey = (key: string): string => {
  const keyMap: Record<string, string> = {
    'battery_charge': '电池电量',
    'battery_runtime': '预计续航',
    'input_voltage': '输入电压',
    'output_voltage': '输出电压',
    'load_percent': '负载百分比',
    'temperature': '温度',
    'ups_name': 'UPS 名称',
    'ups_status': 'UPS 状态',
    'trigger_reason': '触发原因',
    'wait_minutes': '等待时间',
    'device_name': '设备名称',
    'device_type': '设备类型',
    'hook_result': '执行结果',
    'error_message': '错误信息',
    'nut_server': 'NUT 服务器',
    'driver': '驱动',
    'port': '端口'
  }
  return keyMap[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

// 格式化元数据值
const formatMetadataValue = (value: any): string => {
  if (value === null || value === undefined) return 'N/A'
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (typeof value === 'number') {
    // 如果是电压值
    if (String(value).includes('.') || value > 50) return `${value}`
    return String(value)
  }
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}

onMounted(async () => {
  // 设置初始加载超时，3秒后强制结束初始加载状态
  const initialLoadingTimeout = setTimeout(() => {
    console.log('Initial loading timeout reached, forcing end of loading state')
    if (isInitialLoading.value) {
      isInitialLoading.value = false
    }
  }, 3000)

  fetchRecentEvents()
  fetchMetrics()
  fetchPredictions()  // 获取预测数据
  fetchAnalytics()    // 获取电池分析数据
  loadConfigAndSetupRefresh()
  loadConfig()  // 加载配置数据（电池日期等）
  fetchDevicesStatus()
  
  // 如果 WebSocket 已连接且有数据（正常状态），立即结束初始加载
  if (wsConnected.value && upsData.value) {
    clearTimeout(initialLoadingTimeout)
    isInitialLoading.value = false
  }

  // 定期刷新事件列表（每15秒）
  eventsRefreshTimer = window.setInterval(fetchRecentEvents, 15000)

  // 定期刷新图表数据（每30秒）
  metricsRefreshTimer = window.setInterval(fetchMetrics, 30000)

  // 定期刷新预测（每3分钟）
  predictionsRefreshTimer = window.setInterval(fetchPredictions, 3 * 60 * 1000)

  // 定期刷新分析（每3分钟）
  analyticsRefreshTimer = window.setInterval(fetchAnalytics, 3 * 60 * 1000)

  // 监听来自App.vue的设备状态变更事件
  const handleDeviceStateChange = () => {
    // 如果正在关机中，不要立即刷新设备状态（等待关机完成后由wsData watcher处理）
    if (wsData.value?.shutdown?.shutting_down) {
      return
    }
    fetchDevicesStatus()
  }
  window.addEventListener('device-state-changed', handleDeviceStateChange)
  
  onUnmounted(() => {
    window.removeEventListener('device-state-changed', handleDeviceStateChange)
  })
})

onUnmounted(() => {
  // 清除所有定时器
  if (deviceRefreshInterval.value !== null) {
    clearInterval(deviceRefreshInterval.value)
  }
  if (metricsRefreshTimer !== null) {
    clearInterval(metricsRefreshTimer)
  }
  if (predictionsRefreshTimer !== null) {
    clearInterval(predictionsRefreshTimer)
  }
  if (analyticsRefreshTimer !== null) {
    clearInterval(analyticsRefreshTimer)
  }
  if (eventsRefreshTimer !== null) {
    clearInterval(eventsRefreshTimer)
  }
})

// 监听 upsData 变化，处理初始加载状态
watch(upsData, (newData) => {
  // 收到数据后，结束初始加载状态
  if (newData && isInitialLoading.value) {
    isInitialLoading.value = false
  }
}, { immediate: true })

// 监听 WebSocket 推送的 NUT 连接事件，刷新事件列表
watch(connectionEvent, (event) => {
  if (!event) return

  if (event.type === 'NUT_RECONNECTED') {
    // NUT 连接恢复，刷新事件列表
    console.log('[Dashboard] NUT reconnected, refreshing events...')
    fetchRecentEvents()
  }
})

watch(wsData, (newData, oldData) => {
  if (newData) {
    // 检查 UPS 状态是否发生变化
    const statusChanged = newData.status !== oldData?.status

    // 如果 UPS 状态发生变化，立即刷新事件列表和设备状态
    if (statusChanged) {
      fetchRecentEvents()
      fetchMetrics()  // 状态变化时立即刷新图表
      setTimeout(() => {
        fetchDevicesStatus()
      }, 1000)
    } else {
      // 状态未变化时，每 10 秒刷新一次 metrics（跟随 WebSocket 更新节奏）
      const now = Date.now()
      if (now - lastMetricsRefresh >= 10000) {
        fetchMetrics()
      }
    }

    // 如果关机状态发生变化，刷新设备状态
    const shutdownStateChanged = newData.shutdown?.shutting_down !== oldData?.shutdown?.shutting_down
    if (shutdownStateChanged && newData.shutdown?.shutting_down) {
      // 关机开始时，立即将所有设备标记为离线
      devices.value = devices.value.map(device => ({
        ...device,
        online: false,
        last_check: new Date().toISOString()
      }))
    }
  }
}, { deep: true })

// 监听 hook 执行进度
watch(latestHookProgress, (progress) => {
  if (progress) {
    const key = `${progress.hook_id}-${progress.hook_name}`
    deviceExecutionStates.value.set(key, {
      status: progress.status,
      duration: progress.duration,
      error: progress.error
    })
  }
})
</script>

<style scoped>
/* 初始加载状态 */
.loading-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: 16px;
  width: 100%;
  padding: 2rem;
}

.loading-text {
  color: var(--text-secondary);
  font-size: 14px;
  margin-top: 1rem;
}

/* 骨架屏样式 */
.skeleton-container {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--ups-card-gap, 1rem);
  width: 100%;
  max-width: 1400px;
  animation: skeleton-fade 1.5s ease-in-out infinite;
}

.skeleton-col {
  display: flex;
  flex-direction: column;
  gap: var(--ups-card-gap, 1rem);
}

.skeleton-card {
  background: var(--bg-secondary);
  border-radius: var(--ups-card-radius, 12px);
  border: 1px solid var(--border-color);
  opacity: 0.7;
}

.skeleton-card-status {
  height: 150px;
}

.skeleton-card-predictions {
  height: 120px;
}

.skeleton-card-voltage {
  height: 170px;
}

.skeleton-card-battery {
  height: 130px;
}

.skeleton-card-device {
  height: 180px;
}

.skeleton-card-events {
  height: 200px;
}

.skeleton-card-short {
  height: 100px;
}

@keyframes skeleton-fade {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 0.3; }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}


.dashboard {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--ups-card-gap);  /* 使用紧凑间距 */
}

/* === 核心数据区域：三列网格布局 === */
.dashboard-core-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: var(--ups-card-gap);
  align-items: start;
  margin-bottom: var(--ups-card-gap);
}

.dashboard-col {
  display: flex;
  flex-direction: column;
  gap: var(--ups-card-gap);
  /* 支持子元素使用 order 属性排序 */
  flex-wrap: nowrap;
}

/* === 纳管设备区域：独立区域，自适应布局 === */
.devices-section {
  margin-top: var(--ups-card-gap);
}

.devices-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--ups-card-gap);
  padding: 0 0.25rem;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.devices-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: var(--ups-card-gap);
  overflow: visible;
}

.devices-grid :deep(.device-card) {
  min-height: 260px;
}

.devices-empty-card {
  max-width: 600px;
  margin: 0 auto;
}

/* 设备列表滚动容器 */
.devices-scroll-container {
  max-height: none; /* 默认无限制 */
  overflow-y: auto;
}

.devices-scroll-container.has-more {
  max-height: 600px; /* 超过6个设备时限制高度 */
}

.devices-footer {
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--border-color);
  text-align: center;
}

.btn-secondary-outline {
  background: transparent !important;
  border: 1px solid var(--border-color) !important;
  color: var(--text-secondary) !important;
  text-decoration: none;
  display: inline-block;
  padding: 0.375rem 0.75rem;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  transition: all 0.2s;
}

.btn-secondary-outline:hover {
  background: var(--bg-tertiary) !important;
  color: var(--text-primary) !important;
  border-color: var(--border-hover) !important;
}

/* 主状态卡片 - 紧凑型 */
.status-card-compact {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.status-header-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.status-indicator {
  width: 1rem;
  height: 1rem;
  border-radius: 50%;
  animation: pulse 2s infinite;
  flex-shrink: 0;
}

.status-info {
  flex: 1;
}

.status-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.2;
}

/* 状态标志样式 */
.status-flags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
  margin-top: 0.375rem;
}

.status-flag {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.125rem 0.5rem;
  border-radius: 0.75rem;
  font-size: 0.6875rem;
  font-weight: 500;
  white-space: nowrap;
}

.status-flag-success {
  background-color: rgba(16, 185, 129, 0.15);
  color: #10B981;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.status-flag-warning {
  background-color: rgba(245, 158, 11, 0.15);
  color: #F59E0B;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.status-flag-danger {
  background-color: rgba(239, 68, 68, 0.15);
  color: #EF4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.status-flag-info {
  background-color: rgba(59, 130, 246, 0.15);
  color: #3B82F6;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.status-subtitle {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  margin: 0.125rem 0 0 0;
}

.status-serial {
  margin: 0;
  font-size: 0.75rem;
  color: var(--text-secondary, #6b7280);
  opacity: 0.7;
}

/* 电池紧凑版 */
.battery-compact {
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--border-color);
}

.battery-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.battery-label {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.battery-percent {
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 1;
}

.battery-progress-bar {
  height: 16px;
  background: var(--bg-tertiary);
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border-color);
  margin-bottom: 0.5rem;
}

.battery-progress-fill {
  height: 100%;
  border-radius: 7px;
  transition: width 0.5s ease, background-color 0.3s ease;
}

.battery-runtime {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  color: var(--text-secondary);
  font-size: 0.8125rem;
}

/* 续航时间来源标记 */
.runtime-source-badge {
  display: inline-flex;
  align-items: center;
  font-size: 0.625rem;
  padding: 0.0625rem 0.3rem;
  border-radius: 0.25rem;
  margin-left: 0.25rem;
  font-weight: 500;
  cursor: help;
  vertical-align: middle;
  line-height: 1;
}

.runtime-source-badge.estimated {
  background: rgba(245, 158, 11, 0.15);
  color: #D97706;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.runtime-source-badge.hardware {
  background: rgba(16, 185, 129, 0.15);
  color: #059669;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

/* 电压来源标记（与续航来源标记风格一致） */
.voltage-source-badge {
  display: inline-flex;
  align-items: center;
  font-size: 0.625rem;
  padding: 0.0625rem 0.3rem;
  border-radius: 0.25rem;
  margin-left: 0.25rem;
  font-weight: 500;
  cursor: help;
  vertical-align: middle;
  line-height: 1;
}

.voltage-source-badge.estimated {
  background: rgba(139, 92, 246, 0.15);
  color: #7C3AED;
  border: 1px solid rgba(139, 92, 246, 0.3);
}

.runtime-icon {
  font-size: 0.875rem;
}

.status-time {
  color: var(--text-tertiary);
  font-size: 0.75rem;
  text-align: right;
}

.card-title-compact {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
  color: var(--text-primary);
}

.metrics-grid-compact {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-sm);
}

.metric-item-compact {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: var(--spacing-sm);
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.metric-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-bottom: 0.25rem;
}

.metric-value {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
}

/* AI 预测摘要 */
.ai-summary-compact {
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--border-color);
}

.ai-summary-title {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
}

.ai-summary-items {
  display: flex;
  gap: var(--spacing-md);
}

.ai-summary-item {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.ai-summary-item strong {
  color: var(--color-primary);
  font-weight: 600;
}

/* 电池温度和健康度样式 */
.health-good {
  color: #10B981;
}

.health-warning {
  color: #F59E0B;
}

.health-danger {
  color: #EF4444;
}

.temp-warning {
  color: #EF4444;
}

/* 近期电量迷你图 */
.battery-sparkline {
  padding: 0.75rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  margin-top: 0.5rem;
}

.sparkline-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.25rem;
  font-size: 0.8rem;
}

.sparkline-label {
  color: var(--text-secondary);
}

.sparkline-value {
  font-weight: 600;
}

.sparkline-chart {
  width: 100%;
}

.sparkline-svg {
  width: 100%;
  height: 40px;
}

/* Phase 1 新增样式 */

/* 频率警告 */
.freq-warning {
  color: #F59E0B;
}

/* 效率分类样式 */
.efficiency-excellent {
  color: #10B981;
}

.efficiency-good {
  color: #34D399;
}

.efficiency-warning {
  color: #F59E0B;
}

.efficiency-danger {
  color: #EF4444;
}

/* 电池年龄样式 */
.age-good {
  color: #10B981;
}

.age-warning {
  color: #F59E0B;
}

.age-danger {
  color: #EF4444;
}

.age-critical {
  color: #ef4444;
  font-weight: bold;
}

.age-warning-icon {
  margin-left: 0.25rem;
}

/* 电池日期编辑样式 */
.battery-date-section {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.date-source {
  font-size: 0.8em;
  color: #999;
  margin-left: 4px;
}

.not-set {
  color: #999;
  font-style: italic;
}

.edit-date-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.9em;
  padding: 2px 4px;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.edit-date-btn:hover {
  opacity: 1;
}

.date-edit-form {
  display: flex;
  align-items: center;
  gap: 4px;
}

.date-input {
  padding: 4px 8px;
  border: 1px solid var(--border-color, #ddd);
  border-radius: 4px;
  font-size: 0.9em;
  background: var(--bg-primary, #fff);
  color: var(--text-primary, #333);
}

.save-btn, .cancel-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1em;
  padding: 2px 4px;
}

.save-btn:hover, .cancel-btn:hover {
  opacity: 0.7;
}

/* 电池充电器状态样式 */
.charger-status-good {
  color: #10B981;
  font-weight: 600;
}

.charger-status-warning {
  color: #F59E0B;
  font-weight: 600;
}

/* 电池详细信息卡片内容 */
.battery-info-content {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.battery-info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8125rem;
}

.info-label {
  color: var(--text-secondary);
}

.info-value {
  font-weight: 500;
  color: var(--text-primary);
}

.info-value.placeholder-value {
  color: var(--text-tertiary);
  font-style: italic;
  opacity: 0.7;
  cursor: help;
}

.battery-replacement-alert {
  margin-top: 0.75rem;
  padding: 0.5rem;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: var(--radius-sm);
  color: #EF4444;
  font-size: 0.75rem;
  text-align: center;
}

/* === 图表紧凑版 === */
.chart-compact :deep(.card) {
  padding: var(--ups-card-padding);
}

.chart-compact :deep(.chart-container) {
  height: 250px !important;  /* 压缩高度 */
}

/* 智能预测 - 横向紧凑 */
.predictions-card-compact {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.predictions-compact-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-sm);
}

.prediction-item-compact {
  padding: var(--spacing-sm);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.prediction-compact-header {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.prediction-compact-icon {
  font-size: 1rem;
}

.prediction-compact-title {
  font-size: 0.75rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.prediction-compact-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-primary);
  line-height: 1;
}

.prediction-compact-value.alert-value {
  color: var(--color-danger);
}

.prediction-compact-meta {
  font-size: 0.6875rem;
  color: var(--text-tertiary);
}

.prediction-placeholder-compact {
  text-align: center;
  padding: var(--spacing-md);
}

.placeholder-icon-compact {
  font-size: 2rem;
  opacity: 0.5;
  display: block;
  margin-bottom: 0.5rem;
}

.placeholder-text-compact {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  margin: 0;
}

/* 纳管设备 - 紧凑型 */
.devices-card-compact {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.card-header-compact {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.devices-grid-compact {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.devices-grid-compact :deep(.device-card) {
  padding: var(--spacing-sm) !important;
}

/* === 最近事件 - 紧凑表格 === */
.events-card-compact {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.events-table-compact {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.event-row-compact {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: var(--spacing-sm);
  padding: 0.5rem var(--spacing-sm);
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  align-items: center;
  font-size: 0.8125rem;
}

.event-type-compact {
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.6875rem;
  font-weight: 500;
}

.event-message-compact {
  color: var(--text-primary);
  font-size: 0.8125rem;
}

.event-time-compact {
  color: var(--text-tertiary);
  font-size: 0.75rem;
}

.empty-state-compact {
  text-align: center;
  padding: var(--spacing-md);
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}

/* 事件类型颜色 */
.event-power_lost {
  background: #FEF3C7;
  color: #92400E;
}

.event-power_restored {
  background: #D1FAE5;
  color: #065F46;
}

.event-low_battery,
.event-shutdown {
  background: #FEE2E2;
  color: #991B1B;
}

.event-startup,
.event-shutdown_cancelled {
  background: #DBEAFE;
  color: #1E40AF;
}

.event-connection_issue {
  background: #FEE2E2;
  color: #991B1B;
}

.event-connection_restored {
  background: #D1FAE5;
  color: #065F46;
}

/* 后端服务状态 */
.event-backend_error {
  background: #FEE2E2;
  color: #991B1B;
}

.event-backend_restored {
  background: #D1FAE5;
  color: #065F46;
}

/* NUT 服务器状态 */
.event-nut_server_disconnected {
  background: #FEF3C7;
  color: #92400E;
}

.event-nut_server_connected {
  background: #D1FAE5;
  color: #065F46;
}

/* UPS 驱动状态 */
.event-ups_driver_error {
  background: #FEE2E2;
  color: #991B1B;
}

.event-ups_driver_dummy {
  background: #FEF3C7;
  color: #92400E;
}

.event-ups_driver_connected {
  background: #D1FAE5;
  color: #065F46;
}

/* === 响应式布局 === */
/* 中屏：两列布局 (768px - 1200px) */
@media (max-width: 1200px) and (min-width: 768px) {
  .dashboard-core-grid {
    grid-template-columns: 1fr 1fr;
  }
  
  .dashboard-col-1 {
    grid-column: 1 / 2;
  }
  
  .dashboard-col-2 {
    grid-column: 2 / 3;
  }
  
  .devices-grid {
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  }
}

/* 小屏：单列布局 (<768px) */
@media (max-width: 767px) {
  .dashboard-core-grid {
    grid-template-columns: 1fr;
  }
  
  .devices-grid {
    grid-template-columns: 1fr;
  }
  
  .devices-section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }
  
  .predictions-compact-grid {
    grid-template-columns: 1fr;
  }
  
  .metrics-grid-compact {
    grid-template-columns: 1fr;
  }
}


.alert {
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-lg);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alert-warning {
  background: #FEF3C7;
  color: #92400E;
  border: 1px solid #FCD34D;
}

/* 关机警告全屏覆盖 */
.shutdown-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  0% { opacity: 0; }
  100% { opacity: 1; }
}

.shutdown-modal {
  background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
  border-radius: 20px;
  padding: 2.5rem;
  max-width: 420px;
  width: 90%;
  text-align: center;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5),
              0 0 0 1px rgba(255, 255, 255, 0.1);
  animation: slideUp 0.4s ease;
}

@keyframes slideUp {
  0% { transform: translateY(30px); opacity: 0; }
  100% { transform: translateY(0); opacity: 1; }
}

.shutdown-header {
  margin-bottom: 1.5rem;
}

.shutdown-icon-wrapper {
  margin-bottom: 1rem;
}

.shutdown-icon {
  font-size: 4rem;
  animation: pulse-icon 1.5s ease-in-out infinite;
}

@keyframes pulse-icon {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

.shutdown-header h2 {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 700;
  color: #f87171;
}

.shutdown-body {
  margin-bottom: 2rem;
}

.countdown-ring {
  position: relative;
  width: 160px;
  height: 160px;
  margin: 0 auto 1.5rem;
}

.countdown-ring svg {
  transform: rotate(-90deg);
  width: 100%;
  height: 100%;
}

.countdown-bg {
  fill: none;
  stroke: #374151;
  stroke-width: 8;
}

.countdown-progress {
  fill: none;
  stroke: #ef4444;
  stroke-width: 8;
  stroke-linecap: round;
  stroke-dasharray: 283;
  transition: stroke-dashoffset 1s linear;
}

.countdown-value {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.countdown-number {
  display: block;
  font-size: 2.5rem;
  font-weight: 700;
  font-family: 'Courier New', monospace;
  color: white;
}

.countdown-label {
  display: block;
  font-size: 0.875rem;
  color: #9ca3af;
  margin-top: 0.25rem;
}

.shutdown-info {
  color: #d1d5db;
}

.shutdown-reason {
  font-size: 1rem;
  margin: 0 0 0.5rem 0;
}

.shutdown-hint {
  font-size: 0.875rem;
  color: #9ca3af;
  margin: 0;
}

.shutdown-footer {
  margin-top: 1rem;
}

.btn-cancel-shutdown {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 2rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 14px rgba(220, 38, 38, 0.4);
}

.btn-cancel-shutdown:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(220, 38, 38, 0.5);
}

.btn-cancel-shutdown:active {
  transform: translateY(0);
}

.btn-icon {
  font-size: 1.25rem;
}

/* 确认对话框 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.modal-dialog {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  max-width: 400px;
  width: 90%;
  box-shadow: var(--shadow-lg);
}

.modal-confirm {
  text-align: center;
}

.modal-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.modal-confirm h3 {
  margin: 0 0 0.75rem 0;
  color: var(--text-primary);
}

.modal-confirm p {
  margin: 0 0 1rem 0;
  color: var(--text-secondary);
  font-size: 0.9375rem;
  line-height: 1.5;
}

.shutdown-steps {
  text-align: left;
  margin: 0 0 1rem 0;
  padding-left: 1.5rem;
  color: var(--text-primary);
  font-size: 0.875rem;
}

.shutdown-steps li {
  margin-bottom: 0.5rem;
}

.shutdown-scope-notice {
  color: #3b82f6;
  font-weight: 600;
  margin-bottom: 1rem !important;
  padding: 0.5rem 1rem;
  background: rgba(59, 130, 246, 0.1);
  border-radius: var(--radius-md);
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.warning-text {
  color: #dc2626;
  font-weight: 500;
  margin-bottom: 1.5rem !important;
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
}

.modal-actions .btn {
  flex: 1;
  padding: 0.75rem 1.25rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: var(--text-primary);
  font-weight: 500;
}

.form-control {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 0.9375rem;
}

.form-control:focus {
  outline: none;
  border-color: var(--color-primary);
}

.help-text {
  display: block;
  margin-top: 0.25rem;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  line-height: 1.4;
}

.command-result {
  margin: 1rem 0;
  padding: 1rem;
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
}

.result-success h4,
.result-error h4 {
  margin: 0 0 0.75rem 0;
  font-size: 1rem;
}

.command-result pre {
  margin: 0.5rem 0;
  padding: 0.75rem;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  overflow-x: auto;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--text-primary);
}

.command-result .stderr {
  background: #FEE2E2;
  color: #991B1B;
}

.result-error {
  color: #991B1B;
}

/* Logs Modal Styles */
.modal-logs {
  max-width: 900px;
  width: 90%;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.logs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.logs-header h3 {
  margin: 0;
  font-size: 1.25rem;
}

.logs-header-actions {
  display: flex;
  gap: var(--spacing-sm);
  align-items: center;
}

.btn-close {
  background: transparent;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: var(--text-secondary);
  padding: 0.25rem 0.5rem;
  line-height: 1;
  border-radius: var(--radius-sm);
}

.btn-close:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.logs-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: var(--spacing-md);
  font-size: 0.875rem;
}

.logs-device {
  color: var(--text-primary);
}

.logs-command {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}

.logs-command code {
  background: var(--bg-tertiary);
  padding: 0.125rem 0.375rem;
  border-radius: var(--radius-sm);
  font-family: 'Courier New', monospace;
  font-size: 0.8125rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: inline-block;
  max-width: 600px;
  vertical-align: middle;
}

.logs-content {
  flex: 1;
  min-height: 400px;
  max-height: 500px;
  background: #1e1e2e;
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  overflow-y: auto;
  margin-bottom: var(--spacing-md);
}

.logs-text {
  margin: 0;
  font-family: 'Courier New', 'Consolas', monospace;
  font-size: 0.875rem;
  line-height: 1.6;
  color: #e0e0e0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.logs-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #9ca3af;
}

.logs-loading .spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(255, 255, 255, 0.1);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: var(--spacing-md);
}

.logs-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #ef4444;
  text-align: center;
}

.logs-error span {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.logs-error p {
  color: #fca5a5;
  font-size: 0.875rem;
  margin: 0;
  white-space: pre-wrap;
}

.logs-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #6b7280;
  font-size: 1rem;
}

.alert-danger {
  background: #FEE2E2;
  color: #991B1B;
  border: 1px solid #FCA5A5;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Phase 2, 3, 4 新增样式 */

/* 报警横幅 */
.alarm-banner {
  background: linear-gradient(135deg, #FEE2E2 0%, #FCA5A5 100%);
  border: 2px solid #EF4444;
  border-radius: var(--radius-md);
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  animation: pulse 2s infinite;
}

.alarm-content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: #991B1B;
  font-weight: 600;
}

.alarm-icon {
  font-size: 1.5rem;
}

.alarm-message {
  flex: 1;
}

/* 电压质量卡片 */
/* Phase 2-4 卡片样式 (现在都是独立的 .card) */
.card-header-inline {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.card-icon {
  font-size: 1.25rem;
}

.card-title-inline {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
}

/* 电压质量 */
.voltage-range-display {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.voltage-current-display {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  margin-bottom: 0.25rem;
}

.voltage-current-label {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.voltage-current-value {
  font-size: 1.125rem;
  font-weight: 700;
}

.voltage-info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8125rem;
}

.voltage-label {
  color: var(--text-secondary);
}

.voltage-value {
  font-weight: 600;
  font-size: 0.9375rem;
}

.voltage-value-small {
  font-size: 0.8125rem;
  color: var(--text-primary);
}

.voltage-inferred {
  font-size: 0.6875rem;
  color: var(--text-tertiary);
  font-weight: normal;
  margin-left: 0.25rem;
}

.voltage-good { color: #10B981; }
.voltage-warning { color: #F59E0B; }
.voltage-danger { color: #EF4444; }

.voltage-status-bar {
  height: 8px;
  background: linear-gradient(to right, #EF4444 0%, #F59E0B 20%, #10B981 40%, #10B981 60%, #F59E0B 80%, #EF4444 100%);
  border-radius: 4px;
  position: relative;
  margin-top: 0.5rem;
}

.voltage-marker {
  position: absolute;
  top: -4px;
  width: 4px;
  height: 16px;
  background: #1F2937;
  border: 2px solid white;
  border-radius: 2px;
  transform: translateX(-50%);
}

/* 环境监控 */
.environment-metrics {
  display: flex;
  gap: 1rem;
}

.env-metric-item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}

.env-icon {
  font-size: 1.5rem;
}

.env-details {
  display: flex;
  flex-direction: column;
}

.env-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.env-value {
  font-size: 1rem;
  font-weight: 600;
}

.env-good { color: #10B981; }
.env-warning { color: #F59E0B; }

.comfort-index {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  text-align: center;
  font-size: 0.8125rem;
}

.comfort-label {
  color: var(--text-secondary);
}

.comfort-value {
  font-weight: 600;
  margin-left: 0.25rem;
}

.comfort-good { color: #10B981; }
.comfort-acceptable { color: #F59E0B; }
.comfort-poor { color: #EF4444; }

/* 自检状态 */
.test-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.test-result {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  font-size: 0.9375rem;
}

.result-icon {
  font-size: 1.25rem;
}

.test-pass { color: #10B981; }
.test-fail { color: #EF4444; }
.test-progress { color: #F59E0B; }

.test-date {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

/* UPS 控制区域 */
.ups-controls {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.control-group {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.control-label {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  min-width: 60px;
}

.control-actions {
  display: flex;
  gap: 0.375rem;
}

/* Spinner for loading buttons */
.spinner-border {
  display: inline-block;
  width: 0.875rem;
  height: 0.875rem;
  vertical-align: -0.125em;
  border: 0.125em solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spinner-border-animation 0.75s linear infinite;
}

.spinner-border-sm {
  width: 0.75rem;
  height: 0.75rem;
  border-width: 0.1em;
}

/* 电压质量卡片 */
.voltage-quality-card .voltage-quality-content {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.voltage-quality-card .vq-score-circle {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--bg-secondary);
  border: 3px solid var(--border-color);
}

.voltage-quality-card .vq-score-circle.vq-grade-A { border-color: #22c55e; }
.voltage-quality-card .vq-score-circle.vq-grade-B { border-color: #3b82f6; }
.voltage-quality-card .vq-score-circle.vq-grade-C { border-color: #f59e0b; }
.voltage-quality-card .vq-score-circle.vq-grade-D { border-color: #f97316; }
.voltage-quality-card .vq-score-circle.vq-grade-F { border-color: #ef4444; }

.voltage-quality-card .vq-score {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-primary);
}

.voltage-quality-card .vq-grade {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.voltage-quality-card .vq-details {
  flex: 1;
}

.voltage-quality-card .vq-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.25rem;
  font-size: 0.875rem;
}

.voltage-quality-card .vq-label {
  color: var(--text-secondary);
}

.voltage-quality-card .vq-value {
  font-weight: 600;
}

.voltage-quality-card .vq-value.small {
  font-size: 0.75rem;
}

.voltage-quality-card .text-danger { color: #ef4444; }
.voltage-quality-card .text-warning { color: #f59e0b; }
.voltage-quality-card .text-muted { color: var(--text-secondary); }

/* 快捷操作卡片 */
.quick-actions-card .quick-actions-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.5rem;
}

.quick-actions-card .action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0.75rem 0.5rem;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-actions-card .action-btn:hover:not(:disabled) {
  background: var(--primary-light);
  border-color: var(--primary-color);
}

.quick-actions-card .action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.quick-actions-card .action-btn.action-danger {
  border-color: #ef4444;
}

.quick-actions-card .action-btn.action-danger:hover:not(:disabled) {
  background: #fef2f2;
}

.quick-actions-card .action-icon {
  font-size: 1.5rem;
  margin-bottom: 0.25rem;
}

.quick-actions-card .action-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.quick-actions-card .quick-actions-footer {
  margin-top: 0.75rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border-color);
  font-size: 0.8125rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.quick-actions-card .reminder-icon {
  color: #f59e0b;
}

/* 电池分析卡片 */
.battery-analytics-card .analytics-grid {
  display: flex;
  gap: 1rem;
}

.battery-analytics-card .analytics-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.5rem;
  background: var(--bg-secondary);
  border-radius: 8px;
}

.battery-analytics-card .an-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-bottom: 0.25rem;
}

.battery-analytics-card .an-value {
  font-size: 1.25rem;
  font-weight: 700;
}

.battery-analytics-card .an-trend {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.battery-analytics-card .an-confidence {
  font-size: 0.7rem;
  color: var(--text-tertiary);
  margin-top: 0.25rem;
}

@keyframes spinner-border-animation {
  to {
    transform: rotate(360deg);
  }
}

.me-1 {
  margin-right: 0.25rem;
}

/* 能耗统计 */
.energy-stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.energy-stat-item {
  display: flex;
  flex-direction: column;
  padding: 0.5rem;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-bottom: 0.25rem;
}

.stat-value {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
}

.stat-cost {
  font-size: 0.8125rem;
  color: #10B981;
  margin-top: 0.125rem;
}

.efficiency-tip {
  padding: 0.5rem;
  background: rgba(59, 130, 246, 0.1);
  border-left: 3px solid #3B82F6;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  color: var(--text-secondary);
}

/* 电池寿命预测 */
.prediction-content {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.life-remaining-bar {
  height: 24px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  overflow: hidden;
  position: relative;
}

.life-fill {
  height: 100%;
  background: linear-gradient(90deg, #10B981 0%, #34D399 100%);
  transition: width 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
  color: white;
}

.prediction-text {
  text-align: center;
  font-weight: 600;
  color: var(--text-primary);
}

.prediction-suggestion {
  padding: 0.5rem;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  text-align: center;
  font-size: 0.8125rem;
  color: var(--text-secondary);
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
  0%, 100% {
    opacity: 0.6;
    border-color: var(--color-primary, #3b82f6);
  }
  50% {
    opacity: 1;
    border-color: #60a5fa;
  }
}

.droppable-col {
  min-height: 100px;
  transition: background 0.2s ease;
}

.droppable-col.drag-over {
  background: rgba(59, 130, 246, 0.05);
  border-radius: var(--radius-md);
}

/* 拖拽占位符 */
.drop-placeholder {
  height: 80px;
  border: 2px dashed var(--color-primary, #3b82f6);
  border-radius: var(--radius-md);
  background: rgba(59, 130, 246, 0.08);
  animation: placeholderPulse 1.5s ease-in-out infinite;
}

@keyframes placeholderPulse {
  0%, 100% {
    opacity: 0.6;
    border-color: var(--color-primary, #3b82f6);
  }
  50% {
    opacity: 1;
    border-color: #60a5fa;
  }
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

.dashboard:hover .layout-reset-btn {
  opacity: 0.6;
}

.layout-reset-btn:hover {
  opacity: 1 !important;
  background: var(--bg-tertiary);
}

/* Old styles removed - replaced with compact styles above */

/* === New Dashboard Cards === */

/* Device Info Card */
.device-info-card {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.device-info-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--spacing-sm);
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.info-label {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.info-value {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
}

.info-value.monospace {
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 0.8125rem;
}

/* Load Gauge Card */
.load-gauge-card {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.load-gauge-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-sm);
}

.load-gauge-svg {
  width: 100%;
  max-width: 200px;
  height: auto;
}

.gauge-value {
  font-size: 1.5rem;
  font-weight: 600;
  fill: var(--text-primary);
}

.gauge-label {
  font-size: 0.875rem;
  fill: var(--text-secondary);
}

.load-level-text {
  font-size: 0.875rem;
  font-weight: 500;
  text-align: center;
}

/* Battery Voltage Card */
.battery-voltage-card {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.battery-voltage-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-md);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.voltage-main {
  display: flex;
  align-items: baseline;
  gap: 0.25rem;
}

.voltage-value {
  font-size: 2rem;
  font-weight: 600;
  color: var(--text-primary);
}

.voltage-unit {
  font-size: 1rem;
  color: var(--text-secondary);
}

.voltage-nominal {
  font-size: 0.8125rem;
  color: var(--text-tertiary);
}

.voltage-deviation {
  font-size: 0.875rem;
  font-weight: 500;
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
}

.voltage-deviation.health-good {
  background: #D1FAE5;
  color: #065F46;
}

.voltage-deviation.health-warning {
  background: #FEF3C7;
  color: #92400E;
}

.voltage-deviation.health-danger {
  background: #FEE2E2;
  color: #991B1B;
}

.voltage-scale {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.scale-bar {
  position: relative;
  height: 8px;
  background: linear-gradient(to right, #EF4444, #F59E0B, #10B981, #F59E0B, #EF4444);
  border-radius: 4px;
}

.scale-marker {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 3px;
  height: 16px;
  background: var(--text-primary);
  border-radius: 2px;
  box-shadow: 0 0 4px rgba(0, 0, 0, 0.3);
}

.scale-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

/* Shutdown Timeline Card */
.shutdown-timeline-card {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.shutdown-static-mode,
.shutdown-realtime-mode {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.protection-rules {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.rule-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 0.5rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.rule-icon {
  font-size: 1.125rem;
}

.rule-text {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.rule-text strong {
  color: var(--text-primary);
  font-weight: 600;
}

.shutdown-progress-bar {
  height: 8px;
  background: var(--bg-tertiary);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3B82F6, #10B981);
  transition: width 1s ease;
}

.shutdown-progress-bar.progress-start .progress-fill {
  background: linear-gradient(90deg, #3B82F6, #10B981);
}

.shutdown-progress-bar.progress-mid .progress-fill {
  background: linear-gradient(90deg, #10B981, #F59E0B);
}

.shutdown-progress-bar.progress-end .progress-fill {
  background: linear-gradient(90deg, #F59E0B, #EF4444);
}

.shutdown-time-info {
  display: flex;
  justify-content: space-between;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.shutdown-status-info {
  display: flex;
  justify-content: center;
  padding-top: var(--spacing-sm);
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
}

.status-badge.status-safe {
  background: #D1FAE5;
  color: #065F46;
}

.status-badge.status-warning {
  background: #FEF3C7;
  color: #92400E;
}

/* Protection Overview Card */
.protection-overview-card {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.protection-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--spacing-sm);
}

.protection-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.protection-label {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.protection-value {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
}

.protection-value.test-pass {
  color: #10B981;
}

.protection-value.test-fail {
  color: #EF4444;
}

.protection-value.test-progress {
  color: #F59E0B;
}

/* Status Flags Card */
.status-flags-card {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.status-flags-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
  gap: var(--spacing-sm);
}

.flag-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  border: 2px solid transparent;
  transition: all 0.2s ease;
}

.flag-item.flag-active {
  border-color: #10B981;
  background: rgba(16, 185, 129, 0.1);
}

.flag-item.flag-inactive {
  opacity: 0.4;
}

.flag-icon {
  font-size: 1.125rem;
}

.flag-code {
  font-size: 0.6875rem;
  font-weight: 600;
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  color: var(--text-secondary);
}

.flag-item.flag-active .flag-code {
  color: var(--text-primary);
}

.flags-raw {
  padding: 0.5rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.flags-raw code {
  color: var(--text-secondary);
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
}

/* Transfer Stats Card */
.transfer-stats-card {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.transfer-stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-sm);
}

.transfer-stat-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.stat-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.stat-details {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.stat-details .stat-label {
  font-size: 0.6875rem;
  color: var(--text-secondary);
  white-space: nowrap;
}

.stat-details .stat-value {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
}

.backend-badge {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem !important;
  font-weight: 600 !important;
}

.backend-apcupsd {
  background: rgba(16, 185, 129, 0.15);
  color: #059669;
}

.backend-nut {
  background: rgba(59, 130, 246, 0.15);
  color: #2563eb;
}

/* Nominal Specs Card */
.nominal-specs-card {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.nominal-specs-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.375rem;
}

.nominal-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.375rem 0.5rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.nominal-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.nominal-value {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-primary);
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
}

/* Responsive Design for New Cards */
@media (max-width: 768px) {
  .device-info-grid,
  .protection-grid {
    grid-template-columns: 1fr;
  }

  .status-flags-grid {
    grid-template-columns: repeat(auto-fill, minmax(70px, 1fr));
  }

  .voltage-value {
    font-size: 1.5rem;
  }

  .gauge-value {
    font-size: 1.25rem;
  }

  .transfer-stats-grid {
    grid-template-columns: 1fr;
  }
}

/* 测试报告弹窗样式 */
.modal-test-report {
  max-width: 600px;
  width: 95%;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
}

.modal-test-report .modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
  padding-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--border-color);
}

.modal-test-report .modal-header h3 {
  margin: 0;
  font-size: 1.25rem;
}

.report-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: var(--text-secondary);
}

.report-content {
  flex: 1;
  overflow-y: auto;
  padding-right: var(--spacing-sm);
}

.report-section {
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
}

.report-section:last-of-type {
  border-bottom: none;
}

.report-section h4 {
  margin: 0 0 var(--spacing-sm) 0;
  font-size: 1rem;
  color: var(--text-primary);
}

.report-summary {
  text-align: center;
  padding: var(--spacing-lg);
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
}

.test-type-badge {
  display: inline-block;
  padding: 0.375rem 1rem;
  background: var(--bg-tertiary);
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: var(--spacing-sm);
}

.test-meta {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-top: var(--spacing-sm);
}

.test-result-large {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  font-size: 1.5rem;
  font-weight: 600;
  margin-bottom: var(--spacing-sm);
}

.test-result-large.test-passed {
  color: #10b981;
}

.test-result-large.test-warning {
  color: #f59e0b;
}

.test-result-large.test-failed {
  color: #ef4444;
}

.test-result-large.test-in_progress {
  color: #3b82f6;
}

.test-result-large.test-not_tested,
.test-result-large.test-unknown {
  color: var(--text-secondary);
}

.result-icon-large {
  font-size: 2rem;
}

.report-summary .test-date {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.report-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-sm);
}

.report-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.report-item .label {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.report-item .value {
  color: var(--text-primary);
  font-weight: 500;
  font-size: 0.9375rem;
}

.status-flags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-sm);
}

.status-flag-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  background: var(--bg-tertiary);
  border-radius: 9999px;
  font-size: 0.8125rem;
  color: var(--text-primary);
}

.report-footer {
  text-align: center;
  padding-top: var(--spacing-sm);
  color: var(--text-tertiary);
  font-size: 0.75rem;
}

/* 测试报告数据对比表格 */
.comparison-table {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.comparison-header,
.comparison-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 1fr;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: 0.8125rem;
}

.comparison-header {
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}

.comparison-row {
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.comparison-row .comp-label {
  color: var(--text-secondary);
}

.change-negative {
  color: #ef4444;
}

.change-positive {
  color: #10b981;
}

/* 迷你采样图表 */
.samples-chart-mini {
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
}

.chart-bars-mini {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 60px;
  margin-bottom: var(--spacing-sm);
}

.chart-bar-mini {
  flex: 1;
  background: linear-gradient(to top, var(--color-primary), #60a5fa);
  border-radius: 2px 2px 0 0;
  min-height: 2px;
}

.chart-labels-mini {
  display: flex;
  justify-content: space-between;
  font-size: 0.6875rem;
  color: var(--text-tertiary);
}

@media (max-width: 480px) {
  .report-grid {
    grid-template-columns: 1fr;
  }

  .test-result-large {
    font-size: 1.25rem;
  }

  .result-icon-large {
    font-size: 1.5rem;
  }
}

/* 电池测试确认对话框 */
.modal-battery-test-confirm {
  max-width: 500px;
}

.modal-battery-test-confirm .modal-body {
  padding: var(--spacing-lg);
}

.test-info-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.test-description {
  font-size: 0.9375rem;
  line-height: 1.6;
  color: var(--text-primary);
}

.test-description p {
  margin: 0;
}

.test-description.warning {
  padding: var(--spacing-sm) var(--spacing-md);
  background: rgba(245, 158, 11, 0.1);
  border-radius: var(--radius-md);
  border-left: 3px solid #f59e0b;
}

.test-checklist {
  background: var(--bg-secondary);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
}

.test-checklist h4 {
  margin: 0 0 var(--spacing-sm) 0;
  font-size: 0.875rem;
  color: var(--text-primary);
}

.test-checklist ul {
  margin: 0;
  padding-left: 0;
  list-style: none;
}

.test-checklist li {
  padding: var(--spacing-xs) 0;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.test-warning-box {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background: rgba(239, 68, 68, 0.1);
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  color: #dc2626;
}

.test-warning-box .warning-icon {
  font-size: 1.25rem;
}

.test-info-box {
  display: flex;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background: rgba(59, 130, 246, 0.1);
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  color: #2563eb;
  margin-top: var(--spacing-sm);
}

.test-info-box .info-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.test-info-box .info-content {
  flex: 1;
}

.test-info-box .info-content strong {
  display: block;
  margin-bottom: 0.25rem;
  font-weight: 600;
}

.test-info-box .info-content p {
  margin: 0.25rem 0;
  line-height: 1.5;
}

.test-duration {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--border-color);
}

.duration-label {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.duration-value {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-primary);
}

.duration-note {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  margin-left: 0.5rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  border-top: 1px solid var(--border-color);
}

/* UPS Parameter Editing Styles */
.voltage-editable,
.protection-editable {
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  transition: all 0.2s ease;
  position: relative;
}

.voltage-editable:hover,
.protection-editable:hover {
  background: var(--bg-tertiary);
}

.edit-icon {
  font-size: 0.75em;
  margin-left: 0.25rem;
  opacity: 0.6;
}

.voltage-editable:hover .edit-icon,
.protection-editable:hover .edit-icon {
  opacity: 1;
}

.rule-item-editable {
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  transition: all 0.2s ease;
  margin: -0.25rem -0.5rem;
}

.rule-item-editable:hover {
  background: var(--bg-tertiary);
}

.rule-item-editable .edit-icon {
  font-size: 0.75em;
  margin-left: 0.25rem;
  opacity: 0.6;
}

.rule-item-editable:hover .edit-icon {
  opacity: 1;
}

.modal-edit {
  min-width: 400px;
}

.modal-edit h3 {
  margin-bottom: var(--spacing-lg);
  color: var(--text-primary);
}

.edit-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.form-group label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.form-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 0.9375rem;
  transition: all 0.2s ease;
}

.form-input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.sensitivity-options {
  display: flex;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.sensitivity-btn {
  flex: 1;
  padding: 0.75rem 1.5rem;
  border: 2px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 0.9375rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.sensitivity-btn:hover {
  border-color: var(--primary-color);
  background: var(--bg-tertiary);
}

.sensitivity-btn.active {
  border-color: var(--primary-color);
  background: var(--primary-color);
  color: white;
}

.param-change-info {
  margin: var(--spacing-md) 0;
  padding: var(--spacing-md);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  line-height: 1.6;
}

.param-change-info code {
  padding: 0.125rem 0.375rem;
  background: var(--bg-tertiary);
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  color: var(--primary-color);
}

/* 估算值标识 */
.estimated-badge {
  font-size: 0.75rem;
  cursor: help;
  margin-left: 0.25rem;
  vertical-align: middle;
}
</style>
