"""数据模型定义"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class UpsStatus(str, Enum):
    """UPS 状态枚举"""
    ONLINE = "ONLINE"
    ON_BATTERY = "ON_BATTERY"
    LOW_BATTERY = "LOW_BATTERY"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    POWER_OFF = "POWER_OFF"
    OFFLINE = "OFFLINE"


class EventType(str, Enum):
    """事件类型枚举"""
    POWER_LOST = "POWER_LOST"
    POWER_RESTORED = "POWER_RESTORED"
    LOW_BATTERY = "LOW_BATTERY"
    SHUTDOWN = "SHUTDOWN"
    STARTUP = "STARTUP"
    SHUTDOWN_CANCELLED = "SHUTDOWN_CANCELLED"
    # 设备操作事件
    DEVICE_SHUTDOWN = "DEVICE_SHUTDOWN"
    DEVICE_WAKE = "DEVICE_WAKE"
    DEVICE_REBOOT = "DEVICE_REBOOT"
    DEVICE_SLEEP = "DEVICE_SLEEP"
    DEVICE_HIBERNATE = "DEVICE_HIBERNATE"
    DEVICE_TEST_CONNECTION = "DEVICE_TEST_CONNECTION"
    # NUT 连接事件
    NUT_DISCONNECTED = "NUT_DISCONNECTED"
    NUT_RECONNECTED = "NUT_RECONNECTED"
    # 诊断事件 - 后端服务
    BACKEND_ERROR = "BACKEND_ERROR"
    BACKEND_RESTORED = "BACKEND_RESTORED"
    # 诊断事件 - NUT 服务器
    NUT_SERVER_DISCONNECTED = "NUT_SERVER_DISCONNECTED"
    NUT_SERVER_CONNECTED = "NUT_SERVER_CONNECTED"
    # 诊断事件 - UPS 驱动
    UPS_DRIVER_ERROR = "UPS_DRIVER_ERROR"
    UPS_DRIVER_DUMMY = "UPS_DRIVER_DUMMY"
    UPS_DRIVER_CONNECTED = "UPS_DRIVER_CONNECTED"
    # UPS 参数配置事件
    UPS_PARAM_CHANGED = "UPS_PARAM_CHANGED"
    # 电池维护事件
    BATTERY_REPLACED = "BATTERY_REPLACED"
    # 前端事件
    FRONTEND_ERROR = "FRONTEND_ERROR"
    FRONTEND_USER_ACTION = "FRONTEND_USER_ACTION"
    FRONTEND_NETWORK_ERROR = "FRONTEND_NETWORK_ERROR"
    # 兼容旧事件
    CONNECTION_ISSUE = "CONNECTION_ISSUE"
    CONNECTION_RESTORED = "CONNECTION_RESTORED"


class UpsData(BaseModel):
    """UPS 实时数据"""
    status: UpsStatus
    status_raw: Optional[str] = None  # NUT 原始状态字符串，如 "OB DISCHRG LB"
    status_flags: Optional[List[str]] = None  # 原始 NUT 状态标志列表，如 ['OL', 'CHRG']
    battery_charge: Optional[float] = None  # 电池电量百分比
    battery_runtime: Optional[int] = None  # 剩余运行时间（秒）
    input_voltage: Optional[float] = None  # 输入电压
    output_voltage: Optional[float] = None  # 输出电压
    load_percent: Optional[float] = None  # 负载百分比
    temperature: Optional[float] = None  # 温度
    ups_model: Optional[str] = None  # UPS 型号
    ups_manufacturer: Optional[str] = None  # 制造商
    last_update: datetime = Field(default_factory=datetime.now)
    # 新增字段
    ups_power_nominal: Optional[float] = None  # UPS 额定功率 (VA)
    ups_realpower: Optional[float] = None  # 实际功率 (W)
    battery_voltage: Optional[float] = None  # 电池电压 (V)
    battery_voltage_nominal: Optional[float] = None  # 电池额定电压 (V)
    battery_temperature: Optional[float] = None  # 电池温度 (°C) - 与 UPS 温度区分
    # Phase 1 扩展字段
    input_frequency: Optional[float] = None  # 输入频率 (Hz)
    output_frequency: Optional[float] = None  # 输出频率 (Hz)
    output_current: Optional[float] = None  # 输出电流 (A)
    output_current_nominal: Optional[float] = None  # 额定输出电流 (A)
    ups_efficiency: Optional[float] = None  # UPS 效率 (%)
    battery_type: Optional[str] = None  # 电池类型 (e.g., PbAc, Li-ion)
    battery_date: Optional[str] = None  # 电池安装日期
    battery_mfr_date: Optional[str] = None  # 电池生产日期
    battery_packs: Optional[int] = None  # 电池组数量
    battery_packs_bad: Optional[int] = None  # 损坏的电池组数量
    # Phase 2 扩展字段 - 电压质量
    input_voltage_min: Optional[float] = None  # 输入电压最小值 (V)
    input_voltage_max: Optional[float] = None  # 输入电压最大值 (V)
    input_transfer_low: Optional[float] = None  # 低压转换阈值 (V)
    input_transfer_high: Optional[float] = None  # 高压转换阈值 (V)
    # Phase 2 扩展字段 - 环境监控
    ambient_temperature: Optional[float] = None  # 环境温度 (°C)
    ambient_humidity: Optional[float] = None  # 环境湿度 (%)
    ambient_temperature_alarm: Optional[str] = None  # 温度报警
    ambient_humidity_alarm: Optional[str] = None  # 湿度报警
    # Phase 3 扩展字段 - 自检和报警
    ups_test_result: Optional[str] = None  # 自检结果 (Pass/Failed/In Progress)
    ups_test_date: Optional[str] = None  # 上次自检时间
    ups_alarm: Optional[str] = None  # 当前报警信息
    ups_beeper_status: Optional[str] = None  # 蜂鸣器状态
    # Phase 4 扩展字段 - 基于 APC Back-UPS BK650M2_CH 真实测试
    ups_realpower_nominal: Optional[float] = None  # 额定实际功率 (W) - ups.realpower.nominal
    input_voltage_nominal: Optional[float] = None  # 输入额定电压 (V) - input.voltage.nominal
    battery_charge_low: Optional[float] = None  # 低电量阈值 (%) - battery.charge.low
    battery_runtime_low: Optional[int] = None  # 低运行时间阈值 (秒) - battery.runtime.low
    input_transfer_reason: Optional[str] = None  # 最近一次切换原因 - input.transfer.reason
    input_sensitivity: Optional[str] = None  # 输入灵敏度 - input.sensitivity
    ups_delay_shutdown: Optional[int] = None  # 关机延迟时间 (秒) - ups.delay.shutdown
    # 设备信息字段
    ups_serial: Optional[str] = None  # UPS 序列号 - ups.serial
    ups_mfr_date: Optional[str] = None  # UPS 生产日期 - ups.mfr.date
    ups_productid: Optional[str] = None  # USB 产品 ID - ups.productid
    ups_vendorid: Optional[str] = None  # USB 厂商 ID - ups.vendorid
    # 电池充电器状态 (NUT 标准，替代 ups.status 中的 CHRG/DISCHRG 标志)
    battery_charger_status: Optional[str] = None  # battery.charger.status: charging/discharging/floating/resting
    # 连接状态
    nut_reconnect_count: Optional[int] = None  # NUT 连接重连次数（用于前端显示）


class Event(BaseModel):
    """事件记录"""
    id: Optional[int] = None
    event_type: EventType
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[dict] = None


class Metric(BaseModel):
    """指标采样"""
    id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    battery_charge: Optional[float] = None
    battery_runtime: Optional[int] = None
    input_voltage: Optional[float] = None
    output_voltage: Optional[float] = None
    load_percent: Optional[float] = None
    temperature: Optional[float] = None
    # Phase 1 扩展采样字段
    input_frequency: Optional[float] = None
    output_current: Optional[float] = None
    ups_efficiency: Optional[float] = None
    # Phase 2 扩展采样字段
    ambient_temperature: Optional[float] = None
    ambient_humidity: Optional[float] = None


class Config(BaseModel):
    """系统配置"""
    shutdown_wait_minutes: int = 5
    shutdown_battery_percent: int = 20
    shutdown_final_wait_seconds: int = 30
    estimated_runtime_threshold: int = 3  # 预计续航阈值（分钟）
    notify_channels: List[dict] = []
    notify_events: List[str] = ["POWER_LOST", "POWER_RESTORED", "LOW_BATTERY", "SHUTDOWN"]
    notification_enabled: bool = True  # 通知总开关
    sample_interval_seconds: int = 60
    history_retention_days: int = 30
    poll_interval_seconds: int = 5  # NUT 状态轮询间隔（秒）
    cleanup_interval_hours: int = 24  # 历史数据清理间隔（小时）
    pre_shutdown_hooks: List[dict] = []  # 关机前置任务配置列表
    test_mode: str = "production"  # 测试模式：production（生产）/ dry_run（演练）/ mock（完全模拟）
    shutdown_method: str = "lzc_grpc"  # 宿主关机方式：lzc_grpc（懒猫）/ system_command（通用）/ mock（测试）
    wol_on_power_restore: bool = False  # 来电后自动发送 WOL
    wol_delay_seconds: int = 60  # 来电后等待多少秒再发 WOL
    device_status_check_interval_seconds: int = 60  # 设备状态检测间隔（秒），0 表示禁用
    
    # 电池信息（用户自定义）
    battery_install_date: Optional[str] = None  # 电池安装/更换日期（YYYY-MM-DD 格式），用户手动设置
    
    # UPS 监控模式配置
    monitoring_mode: str = "hybrid"  # "polling" | "event_driven" | "hybrid"
    event_driven_enabled: bool = True  # 是否启用事件驱动
    event_driven_heartbeat: int = 30  # 心跳间隔（秒）
    event_driven_fallback: bool = True  # 失败时降级到轮询
    poll_interval_fallback: int = 60  # 事件驱动失败后的轮询间隔（秒）
    
    # 重试配置
    retry_notification_max: int = 2  # 通知重试次数
    retry_notification_delay: float = 1.0  # 通知重试延迟（秒）
    retry_hook_max: int = 2  # Hook 重试次数
    retry_hook_delay: float = 5.0  # Hook 重试延迟（秒）
    retry_http_max: int = 2  # HTTP 请求重试次数
    retry_http_exponential: bool = True  # HTTP 使用指数退避
    retry_wol_count: int = 3  # WOL 发送次数
    retry_wol_delay: float = 2.0  # WOL 发送间隔（秒）
    retry_db_max: int = 3  # 数据库重试次数
    retry_db_delay: float = 0.5  # 数据库重试延迟（秒）


class NotifierConfig(BaseModel):
    """通知渠道配置"""
    id: Optional[str] = None  # 唯一标识符，由系统自动生成
    enabled: bool = True
    plugin_id: str
    name: str
    config: dict = {}


class MonitoringStats(BaseModel):
    """监控统计"""
    id: Optional[int] = None
    date: str  # 统计日期 YYYY-MM-DD
    monitoring_mode: str  # 监控模式: polling/event_driven/hybrid
    event_mode_active: bool = False  # 事件驱动是否激活
    communication_count: int = 0  # 通信次数
    avg_response_time_ms: Optional[float] = None  # 平均响应时间
    min_response_time_ms: Optional[float] = None  # 最小响应时间
    max_response_time_ms: Optional[float] = None  # 最大响应时间
    uptime_seconds: int = 0  # 运行时长
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
