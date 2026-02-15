"""Hook 管理 API"""
import asyncio
import logging
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, File, UploadFile
from pydantic import BaseModel
from typing import Dict, Any, List
from hooks.registry import get_registry
from config import get_config_manager

logger = logging.getLogger(__name__)

# 设备连接测试超时时间（秒）
DEVICE_CONNECTION_TIMEOUT = 5.0

router = APIRouter()


class HookTestRequest(BaseModel):
    """Hook 测试请求"""
    hook_id: str
    config: Dict[str, Any]


@router.get("/hooks/plugins")
async def list_hook_plugins():
    """列出所有可用的 hook 插件"""
    registry = get_registry()
    hooks = registry.list_hooks()
    
    return {"plugins": hooks}


@router.post("/hooks/test")
async def test_hook(request: HookTestRequest):
    """测试单个 hook 连接"""
    registry = get_registry()
    
    try:
        # 创建 hook 实例
        hook_instance = registry.create_instance(request.hook_id, request.config)
        
        # 测试连接
        success = await hook_instance.test_connection()
        
        if success:
            return {"success": True, "message": "Hook 测试成功"}
        else:
            return {"success": False, "message": "Hook 测试失败"}
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")


@router.get("/hooks/status")
async def get_hooks_status():
    """
    批量检测所有已配置 hook 设备的连接状态
    
    Returns:
        {
            "devices": [
                {
                    "name": "Ubuntu Server",
                    "hook_id": "ssh_shutdown",
                    "priority": 1,
                    "online": true,
                    "last_check": "2026-02-11T12:00:00",
                    "error": null
                }
            ]
        }
    """
    config_manager = await get_config_manager()
    config = await config_manager.get_config()
    hooks_config = config.pre_shutdown_hooks
    
    if not hooks_config:
        return {"devices": []}
    
    # 过滤出启用的 hook
    enabled_hooks = [h for h in hooks_config if h.get("enabled", True)]
    
    if not enabled_hooks:
        return {"devices": []}
    
    registry = get_registry()
    devices = []
    
    # 并行检测所有设备状态（带超时）
    async def check_device(hook_config: dict) -> dict:
        """检测单个设备状态"""
        hook_id = hook_config.get("hook_id")
        hook_name = hook_config.get("name", "Unknown")
        priority = hook_config.get("priority", 99)
        config = hook_config.get("config", {})
        
        device_status = {
            "name": hook_name,
            "hook_id": hook_id,
            "priority": priority,
            "online": False,
            "last_check": datetime.now().isoformat(),
            "error": None
        }
        
        try:
            # 创建 hook 实例
            hook_instance = registry.create_instance(hook_id, config)
            
            # 测试连接（带超时）
            success = await asyncio.wait_for(
                hook_instance.test_connection(),
                timeout=DEVICE_CONNECTION_TIMEOUT
            )
            
            device_status["online"] = success
            if not success:
                device_status["error"] = "连接测试失败"
        
        except asyncio.TimeoutError:
            device_status["error"] = f"连接超时（{DEVICE_CONNECTION_TIMEOUT}秒）"
            logger.warning(f"Device '{hook_name}' connection timeout")
        
        except ValueError as e:
            device_status["error"] = f"配置错误: {str(e)}"
            logger.error(f"Device '{hook_name}' config error: {e}")
        
        except Exception as e:
            device_status["error"] = str(e)
            logger.error(f"Device '{hook_name}' check failed: {e}")
        
        return device_status
    
    # 并行检测所有设备
    tasks = [check_device(hook_config) for hook_config in enabled_hooks]
    devices = await asyncio.gather(*tasks, return_exceptions=False)
    
    return {"devices": devices}


@router.post("/hooks/upload-script")
async def upload_script(file: UploadFile = File(...)):
    """
    上传脚本文件并解析内容
    
    Args:
        file: 上传的脚本文件
    
    Returns:
        {
            "success": true,
            "content": "#!/bin/bash\\necho 'Script content'",
            "filename": "script.sh",
            "size": 1234,
            "interpreter": "bash"
        }
    """
    try:
        # 读取文件内容
        content = await file.read()
        
        # 验证文件大小（最大100KB）
        if len(content) > 102400:
            raise HTTPException(
                status_code=400,
                detail="文件过大。最大支持 100KB"
            )
        
        # 验证文件扩展名
        allowed_extensions = ['.sh', '.bash', '.py', '.pl', '.rb']
        filename = file.filename or "script.sh"
        ext = os.path.splitext(filename)[1].lower()
        
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型。允许的扩展名: {', '.join(allowed_extensions)}"
            )
        
        # 尝试解码文件内容（支持多种编码）
        text_content = None
        for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'gbk']:
            try:
                text_content = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if text_content is None:
            raise HTTPException(
                status_code=400,
                detail="无法解码文件内容。请确保文件是文本格式"
            )
        
        # 根据扩展名推断解释器
        interpreter_map = {
            '.sh': 'bash',
            '.bash': 'bash',
            '.py': 'python3',
            '.pl': 'perl',
            '.rb': 'ruby'
        }
        interpreter = interpreter_map.get(ext, 'bash')
        

        return {
            "success": True,
            "content": text_content,
            "filename": filename,
            "size": len(content),
            "interpreter": interpreter
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process uploaded script: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"处理上传文件时出错: {str(e)}"
        )
