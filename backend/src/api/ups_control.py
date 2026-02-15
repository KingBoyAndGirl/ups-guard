"""UPS 控制 API - 蜂鸣器、电池测试等"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import logging

from services.monitor import get_monitor
from services.history import get_history_service
from models import EventType

logger = logging.getLogger(__name__)
router = APIRouter()

# 安全白名单：只允许执行这些命令
ALLOWED_COMMANDS = {
    "beeper.enable": "启用蜂鸣器",
    "beeper.disable": "禁用蜂鸣器",
    "beeper.mute": "临时静音蜂鸣器",
    "beeper.on": "蜂鸣器响起（测试）",
    "beeper.off": "蜂鸣器停止",
    "test.battery.start.quick": "快速电池测试",
    "test.battery.start.deep": "深度电池测试",
    "test.battery.stop": "停止电池测试",
}

# 记录最后一次电池测试信息
_last_battery_test = {
    'type': None,  # 'quick' 或 'deep'
    'type_label': None,  # '快速测试' 或 '深度测试'
    'started_at': None,
    'command': None,
}

class CommandRequest(BaseModel):
    command: str

class CommandResponse(BaseModel):
    success: bool
    message: str
    command: str

@router.get("/ups/commands")
async def list_available_commands():
    """列出可用的 UPS 命令"""
    return {
        "commands": [
            {"id": cmd, "description": desc}
            for cmd, desc in ALLOWED_COMMANDS.items()
        ]
    }

@router.post("/ups/command", response_model=CommandResponse)
async def execute_ups_command(request: CommandRequest):
    """执行 UPS 命令（白名单限制）"""
    command = request.command
    
    if command not in ALLOWED_COMMANDS:
        raise HTTPException(
            status_code=400,
            detail=f"命令 '{command}' 不在允许列表中。可用命令: {list(ALLOWED_COMMANDS.keys())}"
        )
    
    monitor = get_monitor()
    if not monitor:
        raise HTTPException(status_code=503, detail="监控服务未初始化")
    
    nut_client = monitor.nut_client
    if not hasattr(nut_client, 'run_command'):
        raise HTTPException(status_code=501, detail="当前 NUT 客户端不支持命令执行")
    
    try:
        success = await nut_client.run_command(command)
        if success:
            logger.info(f"UPS command executed: {command}")
            # 命令执行成功后强制更新状态
            await monitor.force_update()
            return CommandResponse(
                success=True,
                message=f"命令 '{ALLOWED_COMMANDS[command]}' 执行成功",
                command=command
            )
        else:
            return CommandResponse(
                success=False,
                message=f"命令 '{ALLOWED_COMMANDS[command]}' 执行失败",
                command=command
            )
    except Exception as e:
        logger.error(f"Error executing UPS command {command}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 便捷端点
@router.post("/ups/beeper/{action}")
async def control_beeper(action: str):
    """蜂鸣器控制便捷端点
    
    action: enable | disable | mute
    """
    command_map = {
        "enable": "beeper.enable",
        "disable": "beeper.disable",
        "mute": "beeper.mute",
    }
    
    if action not in command_map:
        raise HTTPException(status_code=400, detail=f"无效操作: {action}。可用: enable, disable, mute")
    
    return await execute_ups_command(CommandRequest(command=command_map[action]))


def _safe_float(value) -> Optional[float]:
    """安全转换为浮点数"""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_int(value) -> Optional[int]:
    """安全转换为整数"""
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


async def monitor_test_completion(report_service, monitor, test_type: str):
    """后台任务：监控测试完成状态"""
    import asyncio

    # 根据测试类型设置参数
    if test_type == 'quick':
        timeout = 120  # 快速测试最多等 2 分钟
        interval = 2   # 每 2 秒采样一次
        min_wait = 15  # 至少等 15 秒（快速测试通常需要 10-30 秒）
    else:
        timeout = 1800  # 深度测试最多 30 分钟（电池放电到低电量需要时间）
        interval = 15   # 每 15 秒采样一次（深度测试时间长，不需要太频繁）
        min_wait = 60   # 至少等 60 秒（深度测试需要更长时间才开始有明显变化）

    start_time = datetime.now()
    sample_count = 0

    logger.info(f"[BatteryTest] Starting monitoring for {test_type} test, interval={interval}s, timeout={timeout}s, min_wait={min_wait}s")

    while True:
        await asyncio.sleep(interval)
        elapsed = (datetime.now() - start_time).total_seconds()

        # 检查测试是否还在进行（可能被取消）
        current_test = await report_service.get_current_test()
        if current_test is None:
            logger.info("[BatteryTest] Test was cancelled or already completed")
            break

        try:
            # 获取当前 UPS 状态
            all_vars = await monitor.nut_client.list_vars()
            if not all_vars:
                logger.warning("[BatteryTest] Failed to get UPS variables")
                continue

            ups_data = {
                'battery_charge': _safe_float(all_vars.get('battery.charge')),
                'battery_voltage': _safe_float(all_vars.get('battery.voltage')),
                'battery_runtime': _safe_int(all_vars.get('battery.runtime')),
                'load_percent': _safe_float(all_vars.get('ups.load')),
                'input_voltage': _safe_float(all_vars.get('input.voltage')),
            }

            # 添加采样
            await report_service.add_sample(ups_data)
            sample_count += 1
            logger.info(f"[BatteryTest] Sample #{sample_count}: charge={ups_data.get('battery_charge')}%, elapsed={elapsed:.1f}s")

            # 获取测试结果
            test_result = all_vars.get('ups.test.result', '')
            ups_status = all_vars.get('ups.status', '')

            # 检查是否正在测试（状态包含 CAL = 校准/测试）
            is_testing = 'CAL' in ups_status or 'progress' in test_result.lower()

            # 完成条件：
            # 1. 已过最小等待时间
            # 2. UPS 不在测试状态（没有 CAL 标志）
            # 3. 测试结果不是 "in progress"
            if elapsed >= min_wait and not is_testing:
                # 确定结果状态
                result_status = 'unknown'
                if 'passed' in test_result.lower():
                    result_status = 'passed'
                elif 'warning' in test_result.lower():
                    result_status = 'warning'
                elif 'error' in test_result.lower() or 'failed' in test_result.lower():
                    result_status = 'failed'

                logger.info(f"[BatteryTest] Test completed: {result_status} - {test_result}")
                await report_service.complete_test(result_status, test_result, ups_data)
                break

            # 超时处理
            if elapsed > timeout:
                logger.warning(f"[BatteryTest] Timeout after {elapsed:.1f}s")
                result_status = 'unknown'
                if 'passed' in test_result.lower():
                    result_status = 'passed'
                await report_service.complete_test(result_status, test_result or 'Timeout', ups_data)
                break

        except Exception as e:
            logger.error(f"[BatteryTest] Error: {e}")
            import traceback
            traceback.print_exc()
            # 继续监控，不要因为一次错误就停止

    logger.info(f"[BatteryTest] Monitoring ended, {sample_count} samples collected")


@router.post("/ups/test-battery/{test_type}")
async def test_battery(test_type: str, background_tasks: BackgroundTasks):
    """电池测试便捷端点
    
    test_type: quick | deep | stop
    """
    global _last_battery_test
    from services.battery_test_report import get_battery_test_report_service

    command_map = {
        "quick": "test.battery.start.quick",
        "deep": "test.battery.start.deep",
        "stop": "test.battery.stop",
    }
    
    type_labels = {
        "quick": "快速测试",
        "deep": "深度测试",
        "stop": "停止测试",
    }

    if test_type not in command_map:
        raise HTTPException(status_code=400, detail=f"无效测试类型: {test_type}。可用: quick, deep, stop")
    
    monitor = get_monitor()
    report_service = await get_battery_test_report_service()

    # 处理停止测试
    if test_type == 'stop':
        await report_service.cancel_test()
        return await execute_ups_command(CommandRequest(command=command_map[test_type]))

    # 获取当前 UPS 数据
    ups_data = {}
    if monitor:
        try:
            all_vars = await monitor.nut_client.list_vars()
            logger.info(f"Got {len(all_vars) if all_vars else 0} UPS variables for test report")
            if all_vars:
                ups_data = {
                    'battery_charge': _safe_float(all_vars.get('battery.charge')),
                    'battery_voltage': _safe_float(all_vars.get('battery.voltage')),
                    'battery_runtime': _safe_int(all_vars.get('battery.runtime')),
                    'load_percent': _safe_float(all_vars.get('ups.load')),
                    'input_voltage': _safe_float(all_vars.get('input.voltage')),
                    'ups_manufacturer': all_vars.get('ups.mfr'),
                    'ups_model': all_vars.get('ups.model'),
                    'ups_serial': all_vars.get('ups.serial'),
                }
                logger.info(f"UPS data for test: charge={ups_data.get('battery_charge')}%, voltage={ups_data.get('battery_voltage')}V")
        except Exception as e:
            logger.warning(f"Failed to get UPS data for test report: {e}")
            import traceback
            traceback.print_exc()
    else:
        logger.warning("Monitor not available for test report")

    # 开始测试报告
    report_id = await report_service.start_test(test_type, type_labels[test_type], ups_data)

    # 记录测试类型（兼容旧代码）
    _last_battery_test = {
        'type': test_type,
        'type_label': type_labels[test_type],
        'started_at': datetime.now().isoformat(),
        'command': command_map[test_type],
        'report_id': report_id,
    }

    # 启动后台任务监控测试状态
    background_tasks.add_task(monitor_test_completion, report_service, monitor, test_type)

    return await execute_ups_command(CommandRequest(command=command_map[test_type]))


@router.get("/ups/test-report")
async def get_test_report():
    """获取电池测试报告
    
    返回当前 UPS 的测试状态和详细信息
    """
    global _last_battery_test

    monitor = get_monitor()
    if not monitor:
        raise HTTPException(status_code=503, detail="监控服务未初始化")
    
    nut_client = monitor.nut_client
    
    try:
        # 获取所有 UPS 变量
        all_vars = await nut_client.list_vars()
        if not all_vars:
            raise HTTPException(status_code=503, detail="无法获取 UPS 变量")
        
        # 解析状态标志
        ups_status = all_vars.get('ups.status', '')
        status_flags = ups_status.split()
        status_explanations = []
        status_flag_map = {
            'OL': '🟢 在线（市电供电）',
            'OB': '🔴 电池供电（市电断开）',
            'LB': '⚠️ 低电量',
            'HB': '🔋 高电量',
            'RB': '🔄 需要更换电池',
            'CHRG': '⚡ 充电中',
            'DISCHRG': '📉 放电中',
            'BYPASS': '🔀 旁路模式',
            'CAL': '📊 校准/测试中',
            'OFF': '⭕ 关闭',
            'OVER': '🚨 过载',
            'TRIM': '📉 降压',
            'BOOST': '📈 升压',
            'FSD': '🛑 强制关机',
            'ALARM': '🚨 告警',
        }
        for flag in status_flags:
            if flag in status_flag_map:
                status_explanations.append({
                    'flag': flag,
                    'description': status_flag_map[flag]
                })
        
        # 计算运行时间显示
        runtime_sec = int(all_vars.get('battery.runtime', 0) or 0)
        runtime_min = runtime_sec // 60
        runtime_display = f"{runtime_min}分{runtime_sec % 60}秒" if runtime_sec else "N/A"
        
        # 测试结果解读
        test_result = all_vars.get('ups.test.result', '')
        test_status = 'unknown'
        test_icon = '❓'
        if 'passed' in test_result.lower():
            test_status = 'passed'
            test_icon = '✅'
        elif 'warning' in test_result.lower():
            test_status = 'warning'
            test_icon = '⚠️'
        elif 'error' in test_result.lower() or 'failed' in test_result.lower():
            test_status = 'failed'
            test_icon = '❌'
        elif 'progress' in test_result.lower():
            test_status = 'in_progress'
            test_icon = '🔄'
        elif test_result == '' or 'no test' in test_result.lower():
            test_status = 'not_tested'
            test_icon = '➖'
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'ups_info': {
                'manufacturer': all_vars.get('ups.mfr', 'N/A'),
                'model': all_vars.get('ups.model', 'N/A'),
                'serial': all_vars.get('ups.serial', 'N/A'),
                'firmware': all_vars.get('ups.firmware', 'N/A'),
                'nominal_power': all_vars.get('ups.realpower.nominal', 'N/A'),
            },
            'current_status': {
                'status_raw': ups_status,
                'status_flags': status_explanations,
                'load_percent': all_vars.get('ups.load', 'N/A'),
                'input_voltage': all_vars.get('input.voltage', 'N/A'),
                'output_voltage': all_vars.get('output.voltage', 'N/A'),
            },
            'battery_info': {
                'charge_percent': all_vars.get('battery.charge', 'N/A'),
                'voltage': all_vars.get('battery.voltage', 'N/A'),
                'voltage_nominal': all_vars.get('battery.voltage.nominal', 'N/A'),
                'runtime_seconds': runtime_sec,
                'runtime_display': runtime_display,
                'type': all_vars.get('battery.type', 'N/A'),
                'date': all_vars.get('battery.date', 'N/A'),
                'temperature': all_vars.get('battery.temperature', 'N/A'),
            },
            'test_info': {
                'result': test_result or '未测试',
                'status': test_status,
                'icon': test_icon,
                'date': all_vars.get('ups.test.date', 'N/A'),
                'type': _last_battery_test.get('type'),
                'type_label': _last_battery_test.get('type_label'),
                'started_at': _last_battery_test.get('started_at'),
            },
            'beeper': {
                'status': all_vars.get('ups.beeper.status', 'N/A'),
            },
            'driver_info': {
                'name': all_vars.get('driver.name', 'N/A'),
                'version': all_vars.get('driver.version', 'N/A'),
            },
        }
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating test report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ups/test-reports")
async def get_test_reports(
    limit: int = Query(20, ge=1, le=100, description="返回报告数量"),
    test_type: str = Query(None, description="测试类型筛选: quick, deep"),
    result: str = Query(None, description="结果筛选: passed, warning, failed, in_progress, cancelled"),
    start_date: str = Query(None, description="开始日期 (ISO 格式, 如 2026-02-01)"),
    end_date: str = Query(None, description="结束日期 (ISO 格式, 如 2026-02-14)")
):
    """获取历史电池测试报告列表，支持筛选"""
    from services.battery_test_report import get_battery_test_report_service

    try:
        report_service = await get_battery_test_report_service()
        reports = await report_service.get_reports(
            limit=limit,
            test_type=test_type,
            result=result,
            start_date=start_date,
            end_date=end_date
        )
        return {"reports": reports}
    except Exception as e:
        logger.error(f"Error getting test reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ups/test-reports/{report_id}")
async def get_test_report_by_id(report_id: int):
    """获取单个电池测试报告详情"""
    from services.battery_test_report import get_battery_test_report_service

    try:
        report_service = await get_battery_test_report_service()
        report = await report_service.get_report(report_id)

        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")

        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting test report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 可写变量安全白名单
# 基于 APC Back-UPS BK650M2_CH 规格，电压限制可能需要根据不同型号/地区调整
ALLOWED_SET_VARS = {
    "input.transfer.high": {
        "description": "高压切换阈值 (V)",
        "type": "number",
        "min": 220,
        "max": 300,
        "unit": "V",
    },
    "input.transfer.low": {
        "description": "低压切换阈值 (V)",
        "type": "number",
        "min": 100,
        "max": 200,
        "unit": "V",
    },
    "input.sensitivity": {
        "description": "输入电压灵敏度",
        "type": "enum",
        "options": ["low", "medium", "high"],
        "labels": {"low": "低", "medium": "中", "high": "高"},
    },
    "ups.delay.shutdown": {
        "description": "关机延迟时间 (秒)",
        "type": "number",
        "integer": True,  # 标记为整数类型
        "min": 0,
        "max": 600,
        "unit": "秒",
    },
}

# NUT 变量中文描述字典（用于显示，不影响白名单验证）
# 包含所有常见的 NUT 可写变量
NUT_VAR_DESCRIPTIONS = {
    # 电池相关
    "battery.mfr.date": "电池生产日期",
    "battery.date": "电池安装日期",
    "battery.charge.low": "低电量警告阈值 (%)",
    "battery.charge.warning": "电量警告阈值 (%)",
    "battery.runtime.low": "低运行时间警告阈值 (秒)",
    "battery.voltage.nominal": "电池标称电压 (V)",

    # 驱动相关
    "driver.debug": "驱动调试级别",
    "driver.flag.allow_killpower": "允许关闭 UPS 电源",

    # 输入相关
    "input.transfer.high": "高压切换阈值 (V)",
    "input.transfer.low": "低压切换阈值 (V)",
    "input.sensitivity": "输入电压灵敏度",
    "input.voltage.nominal": "输入标称电压 (V)",

    # 输出相关
    "output.voltage.nominal": "输出标称电压 (V)",

    # UPS 相关
    "ups.delay.shutdown": "关机延迟时间 (秒)",
    "ups.delay.start": "启动延迟时间 (秒)",
    "ups.delay.reboot": "重启延迟时间 (秒)",
    "ups.beeper.status": "蜂鸣器状态",
    "ups.id": "UPS 标识符",
    "ups.contacts": "联系信息",
}


class SetVarRequest(BaseModel):
    var_name: str
    value: str


class SetVarResponse(BaseModel):
    success: bool
    message: str
    var_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None


def _validate_var_value(var_name: str, value: str, meta: dict) -> Optional[str]:
    """验证变量值的合法性，返回错误信息或 None"""
    var_type = meta.get("type")
    
    if var_type == "number":
        try:
            num_val = float(value)
        except ValueError:
            return f"'{value}' 不是有效的数字"
        
        # 检查是否要求整数
        if meta.get("integer", False):
            if num_val != int(num_val):
                return f"'{value}' 必须是整数"
        
        min_val = meta.get("min")
        max_val = meta.get("max")
        if min_val is not None and num_val < min_val:
            return f"值 {num_val} 低于最小值 {min_val}"
        if max_val is not None and num_val > max_val:
            return f"值 {num_val} 超过最大值 {max_val}"
    
    elif var_type == "enum":
        options = meta.get("options", [])
        if value not in options:
            return f"值 '{value}' 不在允许的选项中: {options}"
    
    return None


@router.get("/ups/writable-vars")
async def list_writable_vars():
    """列出所有可写变量"""
    monitor = get_monitor()
    if not monitor:
        raise HTTPException(status_code=503, detail="监控服务未初始化")
    
    nut_client = monitor.nut_client
    if not hasattr(nut_client, 'list_rw'):
        raise HTTPException(status_code=501, detail="当前 NUT 客户端不支持列出可写变量")
    
    rw_vars = await nut_client.list_rw()
    
    # 合并白名单元数据和通用描述
    result = {}
    for var_name, var_info in rw_vars.items():
        meta = ALLOWED_SET_VARS.get(var_name, {})
        # 优先使用白名单中的描述，其次使用通用描述字典
        description = meta.get("description") or NUT_VAR_DESCRIPTIONS.get(var_name)
        result[var_name] = {
            **var_info,
            "configurable": var_name in ALLOWED_SET_VARS,
            "description": description,
            **{k: v for k, v in meta.items() if k != "description"},  # 其他白名单属性
        }
    
    return {"writable_vars": result}


@router.post("/ups/set-var", response_model=SetVarResponse)
async def set_ups_var(request: SetVarRequest):
    """设置 UPS 可写变量（白名单限制）"""
    var_name = request.var_name
    value = request.value
    
    if var_name not in ALLOWED_SET_VARS:
        raise HTTPException(
            status_code=400,
            detail=f"变量 '{var_name}' 不允许修改。可修改的变量: {list(ALLOWED_SET_VARS.keys())}"
        )
    
    # 验证值的合法性
    var_meta = ALLOWED_SET_VARS[var_name]
    validation_error = _validate_var_value(var_name, value, var_meta)
    if validation_error:
        raise HTTPException(status_code=400, detail=validation_error)
    
    monitor = get_monitor()
    if not monitor:
        raise HTTPException(status_code=503, detail="监控服务未初始化")
    
    nut_client = monitor.nut_client
    if not hasattr(nut_client, 'set_var'):
        raise HTTPException(status_code=501, detail="当前 NUT 客户端不支持设置变量")
    
    # 获取旧值
    old_value = await nut_client.get_var(var_name)
    
    # 设置新值
    success = await nut_client.set_var(var_name, value)
    
    if success:
        logger.info(f"UPS variable set: {var_name} = {value} (was: {old_value})")
        
        # 记录事件到历史
        try:
            history_service = await get_history_service()
            await history_service.add_event(
                event_type=EventType.UPS_PARAM_CHANGED,
                message=f"UPS 参数已修改: {var_meta.get('description', var_name)}",
                metadata={
                    "var_name": var_name,
                    "old_value": old_value,
                    "new_value": value,
                    "description": var_meta.get('description', var_name),
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Failed to record UPS_PARAM_CHANGED event: {e}")
        
        # 强制刷新状态
        await monitor.force_update()
        return SetVarResponse(
            success=True,
            message=f"已将 {var_meta.get('description', var_name)} 设置为 {value}",
            var_name=var_name,
            old_value=old_value,
            new_value=value,
        )
    else:
        return SetVarResponse(
            success=False,
            message=f"设置 {var_meta.get('description', var_name)} 失败，UPS 可能不支持此操作",
            var_name=var_name,
            old_value=old_value,
            new_value=None,
        )
