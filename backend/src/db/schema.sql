-- 配置表
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 事件记录表
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,  -- POWER_LOST, POWER_RESTORED, LOW_BATTERY, SHUTDOWN, STARTUP
    message TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,  -- JSON格式存储额外信息
    test_mode TEXT DEFAULT 'production'  -- 测试模式: production, mock, dry_run
);

-- 指标采样表
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    battery_charge REAL,
    battery_runtime INTEGER,
    input_voltage REAL,
    output_voltage REAL,
    load_percent REAL,
    temperature REAL,
    test_mode TEXT DEFAULT 'production'  -- 测试模式: production, mock, dry_run
);

-- 电池测试报告表
CREATE TABLE IF NOT EXISTS battery_test_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_type TEXT NOT NULL,  -- 'quick' 或 'deep'
    test_type_label TEXT NOT NULL,  -- '快速测试' 或 '深度测试'
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    result TEXT,  -- 'passed', 'warning', 'failed', 'in_progress', 'cancelled'
    result_text TEXT,  -- UPS 返回的原始结果文本
    -- 测试开始时的状态
    start_battery_charge REAL,
    start_battery_voltage REAL,
    start_battery_runtime INTEGER,
    start_load_percent REAL,
    start_input_voltage REAL,
    -- 测试结束时的状态
    end_battery_charge REAL,
    end_battery_voltage REAL,
    end_battery_runtime INTEGER,
    end_load_percent REAL,
    end_input_voltage REAL,
    -- UPS 信息
    ups_manufacturer TEXT,
    ups_model TEXT,
    ups_serial TEXT,
    -- 采样数据（JSON 格式）
    samples TEXT,  -- 测试期间的电池数据采样点
    -- 元数据
    metadata TEXT
);

-- 监控统计表
CREATE TABLE IF NOT EXISTS monitoring_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL UNIQUE,  -- 统计日期 (YYYY-MM-DD)
    monitoring_mode TEXT NOT NULL,  -- 监控模式: polling/event_driven/hybrid
    event_mode_active BOOLEAN DEFAULT 0,  -- 事件驱动是否激活
    communication_count INTEGER DEFAULT 0,  -- 通信次数
    avg_response_time_ms REAL,  -- 平均响应时间(毫秒)
    min_response_time_ms REAL,  -- 最小响应时间(毫秒)
    max_response_time_ms REAL,  -- 最大响应时间(毫秒)
    uptime_seconds INTEGER,  -- 运行时长(秒)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
-- Note: idx_events_test_mode is created by migration after ensuring column exists
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);
-- Note: idx_metrics_test_mode is created by migration after ensuring column exists
CREATE INDEX IF NOT EXISTS idx_monitoring_stats_date ON monitoring_stats(date);

-- 插入默认配置
INSERT OR IGNORE INTO config (key, value) VALUES 
    ('shutdown_wait_minutes', '5'),
    ('shutdown_battery_percent', '20'),
    ('shutdown_final_wait_seconds', '30'),
    ('estimated_runtime_threshold', '3'),
    ('notify_channels', '[]'),
    ('notify_events', '["POWER_LOST", "POWER_RESTORED", "LOW_BATTERY", "SHUTDOWN"]'),
    ('notification_enabled', 'true'),
    ('sample_interval_seconds', '60'),
    ('history_retention_days', '30'),
    ('poll_interval_seconds', '5'),
    ('cleanup_interval_hours', '24'),
    ('pre_shutdown_hooks', '[]'),
    ('test_mode', 'production'),
    ('shutdown_method', 'lzc_grpc'),
    ('wol_on_power_restore', 'false'),
    ('wol_delay_seconds', '60'),
    ('device_status_check_interval_seconds', '60'),
    ('user_preferences', '{}');
