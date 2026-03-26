"""通知插件基类"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional


class NotifierPlugin(ABC):
    """通知插件抽象基类"""
    
    # 插件 ID，子类必须定义
    plugin_id: str = ""
    
    # 插件名称，子类必须定义
    plugin_name: str = ""
    
    # 插件描述
    plugin_description: str = ""
    
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
            - type: 类型 (text, password, number, textarea)
            - required: 是否必填
            - default: 默认值
            - placeholder: 占位符
            - description: 说明文字
        """
        pass
    
    @abstractmethod
    def validate_config(self):
        """
        验证配置是否有效，无效时抛出 ValueError
        """
        pass
    
    @abstractmethod
    async def send(self, title: str, content: str, level: str = "info", timestamp: str = "") -> Tuple[bool, Optional[str]]:
        """
        发送通知
        
        Args:
            title: 通知标题
            content: 通知内容
            level: 通知级别 (info, warning, error)
            timestamp: 通知时间戳
        
        Returns:
            元组 (是否成功, 错误信息)，成功时错误信息为 None
        """
        pass
    
    async def test(self) -> Tuple[bool, Optional[str]]:
        """
        测试通知配置是否正确
        
        Returns:
            元组 (是否成功, 错误信息)
        """
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return await self.send(
            title="UPS Guard 测试通知",
            content="这是一条测试消息，如果您收到此消息，说明通知配置正确。",
            level="info",
            timestamp=timestamp
        )
