"""插件注册和发现机制"""
import logging
from typing import Dict, Type, List
from plugins.base import NotifierPlugin

logger = logging.getLogger(__name__)


class PluginRegistry:
    """插件注册表"""
    
    def __init__(self):
        self._plugins: Dict[str, Type[NotifierPlugin]] = {}
    
    def register(self, plugin_class: Type[NotifierPlugin]):
        """
        注册插件
        
        Args:
            plugin_class: 插件类
        """
        if not plugin_class.plugin_id:
            raise ValueError(f"Plugin {plugin_class.__name__} must define plugin_id")
        
        self._plugins[plugin_class.plugin_id] = plugin_class

    def get_plugin(self, plugin_id: str) -> Type[NotifierPlugin]:
        """
        获取插件类
        
        Args:
            plugin_id: 插件 ID
        
        Returns:
            插件类
        """
        if plugin_id not in self._plugins:
            raise ValueError(f"Plugin not found: {plugin_id}")
        return self._plugins[plugin_id]
    
    def list_plugins(self) -> List[Dict[str, str]]:
        """
        列出所有已注册的插件
        
        Returns:
            插件信息列表
        """
        return [
            {
                "id": plugin_id,
                "name": plugin_class.plugin_name,
                "description": plugin_class.plugin_description,
                "config_schema": plugin_class.get_config_schema()
            }
            for plugin_id, plugin_class in self._plugins.items()
        ]
    
    def create_instance(self, plugin_id: str, config: dict) -> NotifierPlugin:
        """
        创建插件实例
        
        Args:
            plugin_id: 插件 ID
            config: 插件配置
        
        Returns:
            插件实例
        """
        plugin_class = self.get_plugin(plugin_id)
        return plugin_class(config)


# 全局插件注册表
registry = PluginRegistry()


def get_registry() -> PluginRegistry:
    """获取插件注册表"""
    return registry
