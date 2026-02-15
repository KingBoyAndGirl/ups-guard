"""配置 API"""
import uuid
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from models import Config, NotifierConfig
from config import get_config_manager
from services.notifier import get_notifier_service
import io

router = APIRouter()


class ConfigUpdate(BaseModel):
    """配置更新请求"""
    shutdown_wait_minutes: int
    shutdown_battery_percent: int
    shutdown_final_wait_seconds: int
    estimated_runtime_threshold: int
    notify_channels: List[Dict[str, Any]]
    notify_events: List[str]
    notification_enabled: bool = True
    sample_interval_seconds: int
    history_retention_days: int
    poll_interval_seconds: int
    cleanup_interval_hours: int
    pre_shutdown_hooks: List[Dict[str, Any]] = []
    test_mode: str = "production"
    shutdown_method: str = "lzc_grpc"
    wol_on_power_restore: bool = False
    wol_delay_seconds: int = 60
    device_status_check_interval_seconds: int = 60
    battery_install_date: Optional[str] = None
    # UPS 监控模式配置
    monitoring_mode: Optional[str] = None
    event_driven_enabled: Optional[bool] = None
    event_driven_heartbeat: Optional[int] = None
    event_driven_fallback: Optional[bool] = None
    poll_interval_fallback: Optional[int] = None


class NotifyTestRequest(BaseModel):
    """通知测试请求"""
    plugin_id: str
    config: Dict[str, Any]


@router.get("/config")
async def get_config():
    """获取配置"""
    config_manager = await get_config_manager()
    config = await config_manager.get_config()
    
    return config.dict()


@router.put("/config")
async def update_config(config_update: ConfigUpdate):
    """更新配置"""
    config_manager = await get_config_manager()
    
    # 为没有 ID 的渠道生成唯一 ID
    for channel in config_update.notify_channels:
        if not channel.get("id"):
            channel["id"] = str(uuid.uuid4())

    # 转换为 Config 对象
    config = Config(**config_update.dict())
    
    # 更新配置
    await config_manager.update_config(config)
    
    # 重新配置通知服务
    notifier_service = get_notifier_service()
    notify_channels = [NotifierConfig(**ch) for ch in config.notify_channels]
    notifier_service.configure(notify_channels, config.notify_events, config.notification_enabled)

    return {"success": True, "message": "配置已更新"}


@router.post("/config/test-notify")
async def test_notify(request: NotifyTestRequest):
    """测试通知配置"""
    notifier_service = get_notifier_service()
    
    try:
        success = await notifier_service.test_notifier(
            request.plugin_id,
            request.config
        )
        
        if success:
            return {"success": True, "message": "通知发送成功"}
        else:
            return {"success": False, "message": "通知发送失败"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/config/notify-plugins")
async def list_notify_plugins():
    """列出所有可用的通知插件"""
    notifier_service = get_notifier_service()
    plugins = notifier_service.list_available_plugins()
    
    return {"plugins": plugins}


@router.get("/config/channel-errors")
async def get_channel_errors():
    """获取通知渠道错误状态"""
    notifier_service = get_notifier_service()
    config_manager = await get_config_manager()
    config = await config_manager.get_config()

    # 获取错误状态（按 channel_id 存储）
    channel_errors = notifier_service.get_channel_errors()

    # 转换为按索引组织的格式
    errors_by_index = {}
    for index, channel in enumerate(config.notify_channels):
        # 使用渠道的 id 字段
        channel_id = channel.get("id")
        if channel_id and channel_id in channel_errors:
            errors_by_index[index] = channel_errors[channel_id]

    return {"errors": errors_by_index}


class ConfigImportRequest(BaseModel):
    """配置导入请求"""
    mode: str = "merge"  # merge or replace


# 敏感字段列表 - 用于脱敏处理
SENSITIVE_FIELDS = {
    'password', 'token', 'secret', 'key', 'api_key', 
    'api_secret', 'private_key', 'smtp_password', 
    'webhook_token', 'nut_password'
}


def mask_sensitive_fields(obj: Any, parent_key: str = '') -> Any:
    """递归脱敏处理敏感字段"""
    if isinstance(obj, dict):
        masked = {}
        for key, value in obj.items():
            full_key = f"{parent_key}.{key}" if parent_key else key
            # 检查键名是否包含敏感词
            is_sensitive = any(sensitive in key.lower() for sensitive in SENSITIVE_FIELDS)
            if is_sensitive and isinstance(value, str) and value:
                masked[key] = "***"
            else:
                masked[key] = mask_sensitive_fields(value, full_key)
        return masked
    elif isinstance(obj, list):
        return [mask_sensitive_fields(item, parent_key) for item in obj]
    else:
        return obj


def merge_configs(current: dict, imported: dict) -> dict:
    """合并配置，保留当前配置中的敏感字段值"""
    merged = current.copy()
    
    for key, value in imported.items():
        if isinstance(value, dict):
            # 递归合并字典（包括嵌套的 config 对象）
            if key in merged and isinstance(merged[key], dict):
                merged[key] = merge_configs(merged[key], value)
            else:
                # 当前没有这个字段，清理脱敏值后添加
                merged[key] = clean_masked_values(value)
        elif isinstance(value, list):
            # 处理列表（如 notify_channels, pre_shutdown_hooks）
            if key in merged and isinstance(merged[key], list):
                # 对于配置列表，需要智能合并
                merged[key] = merge_config_list(merged[key], value)
            else:
                merged[key] = clean_masked_values(value)
        elif value == "***" or (isinstance(value, str) and value.startswith("***")):
            # 如果导入值是脱敏标记，保留当前值
            if key in merged:
                # 保留原值
                pass
            else:
                # 如果当前配置中没有这个字段，设为空字符串
                merged[key] = ""
        else:
            merged[key] = value
    
    return merged


def clean_masked_values(obj):
    """递归清理对象中的脱敏值"""
    if isinstance(obj, dict):
        return {k: clean_masked_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_masked_values(item) for item in obj]
    elif obj == "***" or (isinstance(obj, str) and obj.startswith("***")):
        return ""
    else:
        return obj


def merge_config_list(current_list: list, imported_list: list) -> list:
    """智能合并配置列表（如通知渠道、hooks）"""
    result = []
    
    for imported_item in imported_list:
        if not isinstance(imported_item, dict):
            result.append(imported_item)
            continue
        
        # 查找匹配的当前配置项（通过 id 或 name + plugin_id/hook_id）
        item_id = imported_item.get('id')
        plugin_id = imported_item.get('plugin_id') or imported_item.get('hook_id')
        item_name = imported_item.get('name')
        matching_current = None
        
        for current_item in current_list:
            if not isinstance(current_item, dict):
                continue

            # 优先通过 ID 匹配
            if item_id and current_item.get('id') == item_id:
                matching_current = current_item
                break

            # 其次通过 plugin_id/hook_id + name 匹配
            current_plugin_id = current_item.get('plugin_id') or current_item.get('hook_id')
            if plugin_id and current_plugin_id == plugin_id:
                if item_name and current_item.get('name') == item_name:
                    matching_current = current_item
                    break
                elif not item_name and not current_item.get('name'):
                    matching_current = current_item
                    break

        if matching_current:
            # 合并找到的项，保留敏感字段
            merged_item = merge_configs(matching_current, imported_item)
            result.append(merged_item)
        else:
            # 新增项，递归清理脱敏标记
            cleaned_item = clean_masked_values(imported_item)
            result.append(cleaned_item)
    
    return result


def validate_config_structure(config_dict: dict) -> tuple[bool, str]:
    """验证配置结构是否合法"""
    required_fields = [
        'shutdown_wait_minutes',
        'shutdown_battery_percent', 
        'shutdown_final_wait_seconds',
        'sample_interval_seconds',
        'history_retention_days'
    ]
    
    # 检查必要字段
    for field in required_fields:
        if field not in config_dict:
            return False, f"缺少必要字段: {field}"
    
    # 检查数值类型字段
    int_fields = [
        'shutdown_wait_minutes', 'shutdown_battery_percent',
        'shutdown_final_wait_seconds', 'estimated_runtime_threshold',
        'sample_interval_seconds', 'history_retention_days',
        'poll_interval_seconds', 'cleanup_interval_hours',
        'wol_delay_seconds', 'device_status_check_interval_seconds'
    ]
    
    for field in int_fields:
        if field in config_dict:
            try:
                int(config_dict[field])
            except (ValueError, TypeError):
                return False, f"字段 {field} 必须是整数"
    
    # 检查列表类型字段
    list_fields = ['notify_channels', 'notify_events', 'pre_shutdown_hooks']
    for field in list_fields:
        if field in config_dict and not isinstance(config_dict[field], list):
            return False, f"字段 {field} 必须是列表"
    
    # 检查布尔类型字段
    bool_fields = ['notification_enabled', 'wol_on_power_restore']
    for field in bool_fields:
        if field in config_dict and not isinstance(config_dict[field], bool):
            return False, f"字段 {field} 必须是布尔值"
    
    return True, "配置结构验证通过"


@router.get("/config/export")
async def export_config():
    """导出当前配置为 JSON（包含敏感信息，请妥善保管）"""
    config_manager = await get_config_manager()
    config = await config_manager.get_config()
    
    # 转换为字典（不脱敏，保留原始值）
    config_dict = config.dict()
    
    # 添加元数据
    export_data = {
        "export_time": datetime.now().isoformat(),
        "version": "1.0.0",
        "config": config_dict
    }
    
    # 生成 JSON 字符串
    json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
    
    # 创建文件流
    file_stream = io.BytesIO(json_str.encode('utf-8'))
    
    # 生成文件名
    filename = f"ups-guard-config-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    
    return StreamingResponse(
        file_stream,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.post("/config/import")
async def import_config(
    file: UploadFile = File(...),
    mode: str = "merge",
    selected_fields: Optional[str] = None
):
    """
    导入配置 JSON
    
    Args:
        file: 配置文件
        mode: 导入模式 (merge/replace)
        selected_fields: 选中的字段列表，JSON字符串格式 (如: '["field1","field2"]')
                        如果为None，则导入所有字段
    """
    if mode not in ["merge", "replace"]:
        raise HTTPException(status_code=400, detail="mode 必须是 'merge' 或 'replace'")
    
    try:
        # 读取上传的文件
        content = await file.read()
        import_data = json.loads(content.decode('utf-8'))
        
        # 提取配置数据 - 支持多种格式
        config_dict = None
        
        # 格式1：标准配置导出格式 {export_time, version, config: {...}}
        if "config" in import_data:
            config_dict = import_data["config"]
        # 格式2：诊断报告格式 {generated_at, full_config: {...}, ...}
        elif "full_config" in import_data:
            config_dict = import_data["full_config"]
        # 格式3：直接是配置字典
        else:
            config_dict = import_data
        
        # 解析选中的字段列表
        selected_fields_list = None
        if selected_fields:
            try:
                selected_fields_list = json.loads(selected_fields)
                if not isinstance(selected_fields_list, list):
                    raise HTTPException(status_code=400, detail="selected_fields 必须是字符串列表")
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="selected_fields JSON 解析失败")
        
        # 如果指定了选中字段，只保留选中的字段
        if selected_fields_list:
            filtered_dict = {k: v for k, v in config_dict.items() if k in selected_fields_list}
            config_dict = filtered_dict
        
        # 验证配置结构（仅验证要导入的字段）
        if config_dict:  # 只有在有字段要导入时才验证
            is_valid, message = validate_config_structure(config_dict)
            if not is_valid:
                # 对于选择性导入，允许缺少某些必需字段
                if not selected_fields_list:
                    raise HTTPException(status_code=400, detail=f"配置验证失败: {message}")
        
        # 获取当前配置
        config_manager = await get_config_manager()
        current_config = await config_manager.get_config()
        current_dict = current_config.dict()
        
        # 根据模式处理
        if mode == "merge":
            # 合并模式：保留敏感字段
            final_dict = merge_configs(current_dict, config_dict)
        else:
            # 替换模式：只替换选中的字段
            final_dict = current_dict.copy()
            for key, value in config_dict.items():
                if value != "***":
                    final_dict[key] = value
                # 如果导入值是脱敏标记，保留当前值（不做任何操作）
        
        # 为没有 ID 的渠道生成唯一 ID
        if 'notify_channels' in final_dict:
            for channel in final_dict['notify_channels']:
                if isinstance(channel, dict) and not channel.get("id"):
                    channel["id"] = str(uuid.uuid4())
        
        # 创建新的 Config 对象
        new_config = Config(**final_dict)
        
        # 更新配置
        await config_manager.update_config(new_config)
        
        # 重新配置通知服务
        notifier_service = get_notifier_service()
        notify_channels = [NotifierConfig(**ch) for ch in new_config.notify_channels]
        notifier_service.configure(notify_channels, new_config.notify_events, new_config.notification_enabled)
        
        # 统计受影响的配置项
        affected_count = len(config_dict.keys())
        
        return {
            "success": True,
            "message": f"配置导入成功 ({mode} 模式，{affected_count} 项)",
            "affected_count": affected_count,
            "mode": mode
        }
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON 解析失败: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.post("/config/validate")
async def validate_config(file: UploadFile = File(...)):
    """验证配置文件但不导入"""
    try:
        # 读取上传的文件
        content = await file.read()
        import_data = json.loads(content.decode('utf-8'))
        
        # 提取配置数据 - 支持多种格式
        config_dict = None
        
        # 格式1：标准配置导出格式 {export_time, version, config: {...}}
        if "config" in import_data:
            config_dict = import_data["config"]
        # 格式2：诊断报告格式 {generated_at, full_config: {...}, ...}
        elif "full_config" in import_data:
            config_dict = import_data["full_config"]
        # 格式3：直接是配置字典
        else:
            config_dict = import_data
        
        # 验证配置结构
        is_valid, message = validate_config_structure(config_dict)
        
        if is_valid:
            # 尝试创建 Config 对象以验证完整性
            try:
                # 清除脱敏标记以便验证
                test_dict = {k: ('' if v == "***MASKED***" else v) for k, v in config_dict.items()}
                Config(**test_dict)
                
                return {
                    "valid": True,
                    "message": "配置文件验证通过",
                    "fields": list(config_dict.keys()),
                    "field_count": len(config_dict)
                }
            except Exception as e:
                return {
                    "valid": False,
                    "message": f"配置对象创建失败: {str(e)}"
                }
        else:
            return {
                "valid": False,
                "message": message
            }
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON 解析失败: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"验证失败: {str(e)}")


@router.post("/config/compare")
async def compare_config(file: UploadFile = File(...), mode: str = "merge"):
    """比较导入配置与当前配置的差异"""
    try:
        # 读取上传的文件
        content = await file.read()
        import_data = json.loads(content.decode('utf-8'))

        # 提取配置数据 - 支持多种格式
        config_dict = None
        
        # 格式1：标准配置导出格式 {export_time, version, config: {...}}
        if "config" in import_data:
            config_dict = import_data["config"]
        # 格式2：诊断报告格式 {generated_at, full_config: {...}, ...}
        elif "full_config" in import_data:
            config_dict = import_data["full_config"]
        # 格式3：直接是配置字典
        else:
            config_dict = import_data

        # 获取当前配置
        config_manager = await get_config_manager()
        current_config = await config_manager.get_config()
        current_dict = current_config.dict()

        # 配置字段的中文名称映射
        field_labels = {
            'nut_host': 'NUT 服务器地址',
            'nut_port': 'NUT 服务器端口',
            'nut_username': 'NUT 用户名',
            'nut_password': 'NUT 密码',
            'ups_name': 'UPS 名称',
            'shutdown_wait_minutes': '电池供电等待时间(分钟)',
            'shutdown_battery_percent': '低电量关机阈值(%)',
            'shutdown_final_wait_seconds': '关机后等待时间(秒)',
            'estimated_runtime_threshold': '预计运行时间阈值(秒)',
            'sample_interval_seconds': '数据采样间隔(秒)',
            'history_retention_days': '历史数据保留天数',
            'poll_interval_seconds': '轮询间隔(秒)',
            'cleanup_interval_hours': '清理间隔(小时)',
            'wol_delay_seconds': 'WOL 延迟时间(秒)',
            'wol_on_power_restore': '电源恢复后 WOL 唤醒',
            'device_status_check_interval_seconds': '设备状态检查间隔(秒)',
            'notification_enabled': '启用通知',
            'notify_events': '通知事件类型',
            'notify_channels': '通知渠道',
            'pre_shutdown_hooks': '关机前钩子',
            'managed_devices': '纳管设备'
        }

        # 比较差异
        changes = []

        for key, imported_value in config_dict.items():
            if key not in current_dict:
                continue

            current_value = current_dict[key]
            label = field_labels.get(key, key)

            # 跳过脱敏的值
            if imported_value == "***":
                changes.append({
                    'field': key,
                    'label': label,
                    'type': 'unchanged',
                    'reason': '保留原值（导入值已脱敏）'
                })
                continue

            # 处理列表类型（通知渠道、hooks等）
            if isinstance(current_value, list) and isinstance(imported_value, list):
                current_count = len(current_value)
                imported_count = len(imported_value)

                if current_count != imported_count:
                    changes.append({
                        'field': key,
                        'label': label,
                        'type': 'modified',
                        'current': f'{current_count} 项',
                        'imported': f'{imported_count} 项',
                        'details': compare_list_items(current_value, imported_value, key)
                    })
                else:
                    # 检查内容是否有变化
                    has_diff = False
                    for i, (curr, imp) in enumerate(zip(current_value, imported_value)):
                        if isinstance(curr, dict) and isinstance(imp, dict):
                            for k, v in imp.items():
                                if v != "***" and curr.get(k) != v:
                                    has_diff = True
                                    break
                        elif curr != imp:
                            has_diff = True
                        if has_diff:
                            break

                    if has_diff:
                        changes.append({
                            'field': key,
                            'label': label,
                            'type': 'modified',
                            'current': f'{current_count} 项',
                            'imported': f'{imported_count} 项',
                            'details': compare_list_items(current_value, imported_value, key)
                        })
                    else:
                        changes.append({
                            'field': key,
                            'label': label,
                            'type': 'unchanged',
                            'reason': '内容相同'
                        })
            # 处理简单值
            elif current_value != imported_value:
                # 格式化显示值
                current_display = format_value_for_display(current_value, key)
                imported_display = format_value_for_display(imported_value, key)

                changes.append({
                    'field': key,
                    'label': label,
                    'type': 'modified',
                    'current': current_display,
                    'imported': imported_display
                })
            else:
                changes.append({
                    'field': key,
                    'label': label,
                    'type': 'unchanged',
                    'reason': '值相同'
                })

        # 统计
        modified_count = len([c for c in changes if c['type'] == 'modified'])
        unchanged_count = len([c for c in changes if c['type'] == 'unchanged'])

        return {
            'success': True,
            'changes': changes,
            'summary': {
                'total': len(changes),
                'modified': modified_count,
                'unchanged': unchanged_count
            }
        }

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON 解析失败: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"比较失败: {str(e)}")


def compare_list_items(current_list: list, imported_list: list, field_name: str) -> list:
    """比较列表项的详细差异"""
    details = []

    # 获取名称字段
    name_field = 'name'

    current_names = set()
    for item in current_list:
        if isinstance(item, dict):
            current_names.add(item.get(name_field, str(item)))

    imported_names = set()
    for item in imported_list:
        if isinstance(item, dict):
            imported_names.add(item.get(name_field, str(item)))

    # 新增的
    for name in imported_names - current_names:
        details.append({'action': 'add', 'name': name})

    # 删除的
    for name in current_names - imported_names:
        details.append({'action': 'remove', 'name': name})

    # 修改的
    for name in current_names & imported_names:
        details.append({'action': 'modify', 'name': name})

    return details


def format_value_for_display(value: any, field: str) -> str:
    """格式化值用于显示"""
    if isinstance(value, bool):
        return '是' if value else '否'
    if isinstance(value, list):
        return f'{len(value)} 项'
    if field in ['nut_password'] and value:
        return '******'
    if value is None:
        return '(空)'
    return str(value)


