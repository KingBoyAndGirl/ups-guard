"""关机前置任务插件基类"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List


class PreShutdownHook(ABC):
    """关机前置任务插件基类"""
    
    # 插件 ID，子类必须定义
    hook_id: str = ""
    
    # 插件名称，子类必须定义
    hook_name: str = ""
    
    # 插件描述
    hook_description: str = ""
    
    # 支持的操作列表（子类可以覆盖）
    supported_actions: List[str] = ["shutdown"]
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化插件
        
        Args:
            config: 插件配置字典
        """
        self.config = config
        self.validate_config()
    
    @classmethod
    @abstractmethod
    def get_config_schema(cls) -> List[Dict[str, Any]]:
        """
        获取配置表单 schema，前端将根据此 schema 自动渲染配置表单
        
        Returns:
            配置项列表，每个配置项包含:
            - key: 配置键名
            - label: 显示标签
            - type: 类型 (text, password, number, textarea, select)
            - required: 是否必填
            - default: 默认值
            - placeholder: 占位符
            - description: 说明文字
            - options: 选项列表（仅 select 类型）
        """
        pass
    
    @abstractmethod
    def validate_config(self):
        """
        验证配置是否有效，无效时抛出 ValueError
        """
        pass
    
    @abstractmethod
    async def execute(self) -> bool:
        """
        执行关机前置任务
        
        Returns:
            是否成功执行
        """
        pass
    
    async def test_connection(self) -> bool:
        """
        测试连接（子类可覆盖）
        
        Returns:
            是否连接成功
        """
        return await self.execute()
