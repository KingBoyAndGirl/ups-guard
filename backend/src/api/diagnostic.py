"""UPS 诊断报告 API"""
import platform
import logging
from datetime import datetime
from fastapi import APIRouter
from config import settings, APP_VERSION
from services.monitor import get_monitor

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/ups/diagnostic")
async def export_diagnostic_report():
    """导出完整 UPS 诊断报告"""
    monitor = get_monitor()
    
    # 基本信息
    report = {
        "generated_at": datetime.now().isoformat(),
        "app_version": APP_VERSION,
        "system": await _get_system_info(),
        "backend_config": {
            "ups_backend": settings.ups_backend,
            "nut_host": settings.nut_host if settings.ups_backend == "nut" else None,
            "nut_port": settings.nut_port if settings.ups_backend == "nut" else None,
            "apcupsd_host": settings.apcupsd_host if settings.ups_backend == "apcupsd" else None,
            "apcupsd_port": settings.apcupsd_port if settings.ups_backend == "apcupsd" else None,
            "mock_mode": settings.mock_mode,
        },
        "connection": {},
        "ups_variables": {},
        "ups_summary": {},
        "recent_events": [],
    }
    
    # 连接状态
    if monitor and hasattr(monitor, 'nut_client'):
        client = monitor.nut_client
        if hasattr(client, 'get_connection_status'):
            report["connection"] = client.get_connection_status()
    
    # UPS 数据
    if monitor:
        current_data = monitor.get_current_data()
        if current_data:
            report["ups_summary"] = {
                "status": current_data.status.value,
                "status_raw": current_data.status_raw,
                "status_flags": current_data.status_flags,
                "battery_charge": current_data.battery_charge,
                "battery_runtime": current_data.battery_runtime,
                "input_voltage": current_data.input_voltage,
                "output_voltage": current_data.output_voltage,
                "load_percent": current_data.load_percent,
                "temperature": current_data.temperature,
                "ups_model": current_data.ups_model,
                "ups_manufacturer": current_data.ups_manufacturer,
                "ups_serial": current_data.ups_serial,
                "battery_type": current_data.battery_type,
                "battery_voltage": current_data.battery_voltage,
                "battery_voltage_nominal": current_data.battery_voltage_nominal,
                "ups_realpower_nominal": current_data.ups_realpower_nominal,
                "input_voltage_nominal": current_data.input_voltage_nominal,
                "input_sensitivity": current_data.input_sensitivity,
                "input_transfer_low": current_data.input_transfer_low,
                "input_transfer_high": current_data.input_transfer_high,
                "input_transfer_reason": current_data.input_transfer_reason,
                "battery_charge_low": current_data.battery_charge_low,
                "battery_runtime_low": current_data.battery_runtime_low,
                "ups_beeper_status": current_data.ups_beeper_status,
                "ups_test_result": current_data.ups_test_result,
                "battery_charger_status": current_data.battery_charger_status,
                "runtime_estimated": current_data.runtime_estimated,
                "ups_backend": current_data.ups_backend,
                "transfer_count": current_data.transfer_count,
                "time_on_battery": current_data.time_on_battery,
                "cumulative_on_battery": current_data.cumulative_on_battery,
                "ups_alarm_del": current_data.ups_alarm_del,
                "last_update": current_data.last_update.isoformat() if current_data.last_update else None,
            }
    
    # 原始 UPS 变量（尽量获取全部）
    try:
        if monitor and hasattr(monitor, 'nut_client'):
            client = monitor.nut_client
            if hasattr(client, 'list_vars'):
                raw_vars = await client.list_vars()
                report["ups_variables"] = raw_vars
    except Exception as e:
        report["ups_variables_error"] = str(e)
    
    # 可写变量
    try:
        if monitor and hasattr(monitor, 'nut_client'):
            client = monitor.nut_client
            if hasattr(client, 'list_rw'):
                rw_vars = await client.list_rw()
                report["writable_variables"] = rw_vars
    except Exception as e:
        report["writable_variables_error"] = str(e)
    
    # 支持的命令
    try:
        if monitor and hasattr(monitor, 'nut_client'):
            client = monitor.nut_client
            if hasattr(client, 'list_commands'):
                commands = await client.list_commands()
                report["supported_commands"] = commands
    except Exception as e:
        report["supported_commands_error"] = str(e)
    
    # 最近事件
    try:
        from db.database import get_db
        db = await get_db()
        rows = await db.fetch_all(
            "SELECT * FROM events ORDER BY timestamp DESC LIMIT 20"
        )
        report["recent_events"] = [
            {
                "id": r["id"],
                "event_type": r["event_type"],
                "message": r["message"],
                "timestamp": r["timestamp"],
                "metadata": r["metadata"],
            }
            for r in rows
        ]
    except Exception as e:
        report["recent_events_error"] = str(e)
    
    # 数据库统计
    try:
        db = await get_db()
        stats = {}
        for table in ["events", "metrics", "config", "battery_test_reports", "monitoring_stats"]:
            count = await db.fetch_one(f"SELECT COUNT(*) as cnt FROM {table}")
            stats[table] = count["cnt"] if count else 0
        report["database_stats"] = stats
    except Exception as e:
        report["database_stats_error"] = str(e)
    
    return report


@router.get("/ups/diagnostic/markdown")
async def export_diagnostic_markdown():
    """导出 Markdown 格式的诊断报告"""
    data = await export_diagnostic_report()
    
    md = []
    md.append("# UPS Guard 诊断报告")
    md.append(f"\n> 生成时间: {data['generated_at']}")
    md.append(f"> 版本: {data['app_version']}")
    
    # 系统信息
    sys_info = data.get("system", {})
    md.append("\n## 🖥️ 系统信息")
    md.append("\n| 项目 | 值 |")
    md.append("|------|-----|")
    md.append(f"| 操作系统 | {sys_info.get('os', 'N/A')} |")
    md.append(f"| Python | {sys_info.get('python_version', 'N/A')} |")
    md.append(f"| 架构 | {sys_info.get('machine', 'N/A')} |")
    md.append(f"| 主机名 | {sys_info.get('hostname', 'N/A')} |")
    md.append(f"| 容器 | {sys_info.get('container', 'N/A')} |")
    
    # 后端配置
    backend = data.get("backend_config", {})
    md.append("\n## ⚙️ 后端配置")
    md.append("\n| 项目 | 值 |")
    md.append("|------|-----|")
    md.append(f"| UPS 后端 | {backend.get('ups_backend', 'N/A')} |")
    if backend.get('ups_backend') == 'nut':
        md.append(f"| NUT 主机 | {backend.get('nut_host', 'N/A')}:{backend.get('nut_port', 'N/A')} |")
    else:
        md.append(f"| apcupsd 主机 | {backend.get('apcupsd_host', 'N/A')}:{backend.get('apcupsd_port', 'N/A')} |")
    md.append(f"| Mock 模式 | {backend.get('mock_mode', False)} |")
    
    # 连接状态
    conn = data.get("connection", {})
    md.append("\n## 🔌 连接状态")
    md.append("\n| 项目 | 值 |")
    md.append("|------|-----|")
    md.append(f"| 已连接 | {'✅' if conn.get('connected') else '❌'} |")
    md.append(f"| 重连次数 | {conn.get('reconnect_attempts', 0)} |")
    if conn.get('last_error'):
        md.append(f"| 最后错误 | {conn.get('last_error')} |")
    md.append(f"| 后端类型 | {conn.get('backend', 'N/A')} |")
    
    # UPS 摘要
    ups = data.get("ups_summary", {})
    if ups:
        md.append("\n## ⚡ UPS 状态摘要")
        md.append("\n| 项目 | 值 |")
        md.append("|------|-----|")
        md.append(f"| 状态 | {ups.get('status', 'N/A')} |")
        md.append(f"| 原始状态 | `{ups.get('status_raw', 'N/A')}` |")
        md.append(f"| 制造商 | {ups.get('ups_manufacturer', 'N/A')} |")
        md.append(f"| 型号 | {ups.get('ups_model', 'N/A')} |")
        md.append(f"| 序列号 | {ups.get('ups_serial', 'N/A')} |")
        md.append(f"| 电池电量 | {ups.get('battery_charge', 'N/A')}% |")
        md.append(f"| 电池电压 | {ups.get('battery_voltage', 'N/A')}V (额定 {ups.get('battery_voltage_nominal', 'N/A')}V) |")
        md.append(f"| 剩余续航 | {ups.get('battery_runtime', 'N/A')}s |")
        md.append(f"| 电池类型 | {ups.get('battery_type', 'N/A')} |")
        md.append(f"| 输入电压 | {ups.get('input_voltage', 'N/A')}V |")
        md.append(f"| 输出电压 | {ups.get('output_voltage', 'N/A') or 'N/A'}V |")
        md.append(f"| 负载 | {ups.get('load_percent', 'N/A')}% |")
        md.append(f"| 温度 | {ups.get('temperature', 'N/A')}°C |")
        md.append(f"| 额定功率 | {ups.get('ups_realpower_nominal', 'N/A')}W |")
        md.append(f"| 额定输入电压 | {ups.get('input_voltage_nominal', 'N/A')}V |")
        md.append(f"| 灵敏度 | {ups.get('input_sensitivity', 'N/A')} |")
        md.append(f"| 低压切换点 | {ups.get('input_transfer_low', 'N/A')}V |")
        md.append(f"| 高压切换点 | {ups.get('input_transfer_high', 'N/A')}V |")
        md.append(f"| 切换原因 | {ups.get('input_transfer_reason', 'N/A')} |")
        md.append(f"| 低电量阈值 | {ups.get('battery_charge_low', 'N/A')}% |")
        md.append(f"| 低续航阈值 | {ups.get('battery_runtime_low', 'N/A')}s |")
        md.append(f"| 蜂鸣器 | {ups.get('ups_beeper_status', 'N/A')} |")
        md.append(f"| 自检结果 | {ups.get('ups_test_result', 'N/A')} |")
        md.append(f"| 充电器状态 | {ups.get('battery_charger_status', 'N/A')} |")
        md.append(f"| 续航来源 | {'软件估算' if ups.get('runtime_estimated') else '硬件直报'} |")
        md.append(f"| 通信后端 | {ups.get('ups_backend', 'N/A')} |")
        if ups.get('transfer_count') is not None:
            md.append(f"| 切换次数 | {ups.get('transfer_count')} |")
        if ups.get('time_on_battery') is not None:
            md.append(f"| 本次电池时长 | {ups.get('time_on_battery')}s |")
        if ups.get('cumulative_on_battery') is not None:
            md.append(f"| 累计电池时长 | {ups.get('cumulative_on_battery')}s |")
        md.append(f"| 最后更新 | {ups.get('last_update', 'N/A')} |")
    
    # 所有 UPS 变量
    variables = data.get("ups_variables", {})
    if variables:
        md.append(f"\n## 📋 全部 UPS 变量 ({len(variables)} 个)")
        md.append("\n| 变量名 | 值 |")
        md.append("|--------|-----|")
        for key in sorted(variables.keys()):
            value = str(variables[key])
            # 截断过长的值
            if len(value) > 100:
                value = value[:100] + "..."
            md.append(f"| `{key}` | {value} |")
    
    # 可写变量
    rw_vars = data.get("writable_variables", {})
    if rw_vars:
        md.append(f"\n## ✏️ 可写变量 ({len(rw_vars)} 个)")
        md.append("\n| 变量名 | 当前值 |")
        md.append("|--------|--------|")
        for key in sorted(rw_vars.keys()):
            info = rw_vars[key]
            md.append(f"| `{key}` | {info.get('value', 'N/A')} |")
    
    # 支持的命令
    commands = data.get("supported_commands", [])
    if commands:
        md.append(f"\n## 🎮 支持的命令 ({len(commands)} 个)")
        md.append("\n```")
        for cmd in commands:
            md.append(f"- {cmd}")
        md.append("```")
    
    # 最近事件
    events = data.get("recent_events", [])
    if events:
        md.append(f"\n## 📝 最近事件 ({len(events)} 条)")
        md.append("\n| 时间 | 类型 | 消息 |")
        md.append("|------|------|------|")
        for evt in events:
            ts = evt.get("timestamp", "")[:19].replace("T", " ")
            md.append(f"| {ts} | {evt.get('event_type', '')} | {evt.get('message', '')} |")
    
    # 数据库统计
    db_stats = data.get("database_stats", {})
    if db_stats:
        md.append("\n## 💾 数据库统计")
        md.append("\n| 表名 | 记录数 |")
        md.append("|------|--------|")
        for table, count in db_stats.items():
            md.append(f"| {table} | {count} |")
    
    md.append("\n---")
    md.append(f"\n*报告由 UPS Guard v{data['app_version']} 自动生成*")
    
    return "\n".join(md)


async def _get_system_info() -> dict:
    """获取系统信息"""
    import os
    info = {
        "os": f"{platform.system()} {platform.release()}",
        "python_version": platform.python_version(),
        "machine": platform.machine(),
        "hostname": platform.node(),
        "container": "Docker" if os.path.exists("/.dockerenv") else "Native",
    }
    
    # NUT 版本
    try:
        import subprocess
        result = subprocess.run(["upsdrvctl", "-V"], capture_output=True, text=True, timeout=5)
        info["nut_version"] = result.stdout.strip().split("\n")[0] if result.stdout else "N/A"
    except Exception:
        info["nut_version"] = "N/A"
    
    # apcupsd 版本
    try:
        import subprocess
        result = subprocess.run(["apcupsd", "--version"], capture_output=True, text=True, timeout=5)
        info["apcupsd_version"] = result.stderr.strip().split("\n")[0] if result.stderr else "N/A"
    except Exception:
        info["apcupsd_version"] = "N/A"
    
    # USB 设备
    try:
        import subprocess
        result = subprocess.run(["lsusb"], capture_output=True, text=True, timeout=5)
        info["usb_devices"] = result.stdout.strip().split("\n") if result.stdout else []
    except Exception:
        info["usb_devices"] = []
    
    return info
