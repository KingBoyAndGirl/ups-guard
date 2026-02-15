"""自定义脚本执行插件"""
import asyncio
import logging
import os
from typing import Dict, Any, List
from hooks.base import PreShutdownHook
from hooks.registry import registry

logger = logging.getLogger(__name__)


class CustomScriptHook(PreShutdownHook):
    """自定义脚本执行插件"""
    
    hook_id = "custom_script"
    hook_name = "自定义脚本"
    hook_description = "执行本地自定义脚本（Shell/Python）"
    supported_actions = ["shutdown"]
    
    @classmethod
    def get_config_schema(cls) -> List[Dict[str, Any]]:
        return [
            {
                "key": "script_path",
                "label": "脚本路径（可选）",
                "type": "text",
                "required": False,
                "placeholder": "/path/to/your/script.sh",
                "description": "脚本文件的绝对路径。如果提供了脚本内容，则忽略此路径"
            },
            {
                "key": "script_content",
                "label": "脚本内容（可选）",
                "type": "textarea",
                "required": False,
                "rows": 15,
                "placeholder": "#!/bin/bash\necho 'Shutting down device...'\nssh admin@192.168.1.100 'sudo shutdown -h now'\necho 'Done'",
                "description": "直接在此编写脚本内容。如果提供了脚本内容，将优先使用内容而非脚本路径。支持 bash、sh、python 等脚本"
            },
            {
                "key": "interpreter",
                "label": "解释器",
                "type": "select",
                "required": False,
                "default": "bash",
                "options": [
                    {"value": "bash", "label": "Bash"},
                    {"value": "sh", "label": "Shell"},
                    {"value": "python3", "label": "Python 3"}
                ],
                "description": "脚本解释器"
            },
            {
                "key": "args",
                "label": "参数",
                "type": "text",
                "required": False,
                "placeholder": "--mode shutdown --timeout 60",
                "description": "传递给脚本的参数（空格分隔，不支持引号内空格）"
            },
            {
                "key": "timeout",
                "label": "超时时间（秒）",
                "type": "number",
                "required": False,
                "default": 120,
                "placeholder": "120",
                "description": "脚本执行超时时间"
            }
        ]
    
    def validate_config(self):
        script_path = self.config.get("script_path", "").strip()
        script_content = self.config.get("script_content", "").strip()
        
        # 必须提供脚本路径或脚本内容之一
        if not script_path and not script_content:
            raise ValueError("必须提供脚本路径或脚本内容")
        
        # 如果提供了脚本路径，进行安全检查
        if script_path:
            # 安全检查：禁止路径穿越
            if ".." in script_path:
                raise ValueError("脚本路径不能包含 '..'（禁止路径穿越）")
            
            # 必须是绝对路径
            if not script_path.startswith("/"):
                raise ValueError("脚本路径必须是绝对路径")
            
            # 检查文件是否存在（仅在验证时检查，执行时再次检查）
            if not os.path.isfile(script_path):
                logger.warning(f"Script file not found: {script_path}")
        
        # 如果提供了脚本内容，进行基本验证
        if script_content:
            if len(script_content) > 100000:  # 100KB limit
                raise ValueError("脚本内容过大（超过100KB）")
            
            # 检查是否包含危险命令（基本安全检查）
            dangerous_patterns = ["rm -rf /", "dd if=", "mkfs", "> /dev/"]
            for pattern in dangerous_patterns:
                if pattern in script_content.lower():
                    logger.warning(f"Script content contains potentially dangerous pattern: {pattern}")
    
    async def execute(self) -> bool:
        """执行自定义脚本"""
        script_path = self.config.get("script_path", "").strip()
        script_content = self.config.get("script_content", "").strip()
        interpreter = self.config.get("interpreter", "bash")
        args_str = self.config.get("args", "").strip()
        timeout = self.config.get("timeout", 120)
        
        # 必须提供脚本路径或内容之一
        if not script_path and not script_content:
            logger.error("Neither script_path nor script_content provided")
            return False
        
        temp_file = None
        try:
            # 如果提供了脚本内容，创建临时文件
            if script_content:
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.sh' if interpreter in ['bash', 'sh'] else '.py',
                    delete=False,
                    prefix='custom_script_'
                )
                temp_file.write(script_content)
                temp_file.close()
                
                # 设置可执行权限
                os.chmod(temp_file.name, 0o755)
                script_path = temp_file.name
            else:
                # 使用提供的脚本路径
                # 再次安全检查
                if ".." in script_path or not script_path.startswith("/"):
                    logger.error(f"Invalid script path: {script_path}")
                    return False
                
                # 检查文件是否存在
                if not os.path.isfile(script_path):
                    logger.error(f"Script file not found: {script_path}")
                    return False
                
                # 检查文件是否可执行
                if not os.access(script_path, os.X_OK):
                    logger.warning(f"Script file is not executable, attempting to execute with interpreter")
            
            # 构建命令
            if args_str:
                # 简单分割参数（不支持引号内的空格）
                args = args_str.split()
                cmd = [interpreter, script_path] + args
            else:
                cmd = [interpreter, script_path]
            

            # 执行脚本
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                # 检查退出码
                if process.returncode == 0:
                    return True
                else:
                    logger.error(f"Custom script failed with exit code {process.returncode}")
                    return False
            
            except asyncio.TimeoutError:
                logger.error(f"Custom script timed out after {timeout} seconds")
                # 尝试终止进程
                try:
                    process.kill()
                    await process.wait()
                except Exception as e:
                    logger.warning(f"Failed to kill timed-out process: {e}")
                return False
        
        except FileNotFoundError:
            logger.error(f"Interpreter not found: {interpreter}")
            return False
        except Exception as e:
            logger.error(f"Failed to execute custom script: {e}")
            return False
        finally:
            # 清理临时文件
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file: {e}")
    
    async def test_connection(self) -> bool:
        """测试脚本是否可执行"""
        script_path = self.config.get("script_path", "").strip()
        script_content = self.config.get("script_content", "").strip()
        
        # 如果提供了脚本内容，认为测试通过（实际执行时会创建临时文件）
        if script_content:
            return True
        
        # 如果提供了脚本路径，检查文件
        if script_path:
            # 安全检查
            if ".." in script_path or not script_path.startswith("/"):
                logger.error(f"Invalid script path: {script_path}")
                return False
            
            # 检查文件是否存在
            if not os.path.isfile(script_path):
                logger.error(f"Script file not found: {script_path}")
                return False
            
            return True
        
        logger.error("Neither script_path nor script_content provided")
        return False


# 自动注册插件
registry.register(CustomScriptHook)
