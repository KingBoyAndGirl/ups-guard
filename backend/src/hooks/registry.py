"""Hook 插件注册和发现机制"""
import logging
from typing import Dict, Type, List, Any
from hooks.base import PreShutdownHook

logger = logging.getLogger(__name__)


class HookRegistry:
    """Hook 插件注册表"""
    
    def __init__(self):
        self._hooks: Dict[str, Type[PreShutdownHook]] = {}
        self._mock_mode = False
    
    def set_mock_mode(self, enabled: bool):
        """
        设置 Mock 模式
        
        Args:
            enabled: 是否启用 Mock 模式
        """
        self._mock_mode = enabled

    def register(self, hook_class: Type[PreShutdownHook]):
        """
        注册 hook 插件
        
        Args:
            hook_class: Hook 插件类
        """
        if not hook_class.hook_id:
            raise ValueError(f"Hook {hook_class.__name__} must define hook_id")
        
        self._hooks[hook_class.hook_id] = hook_class

    def get_hook(self, hook_id: str) -> Type[PreShutdownHook]:
        """
        获取 hook 插件类
        
        Args:
            hook_id: Hook ID
        
        Returns:
            Hook 插件类
        """
        if hook_id not in self._hooks:
            raise ValueError(f"Hook not found: {hook_id}")
        return self._hooks[hook_id]
    
    def list_hooks(self) -> List[Dict[str, Any]]:
        """
        列出所有已注册的 hook 插件
        
        Returns:
            Hook 插件信息列表
        """
        return [
            {
                "id": hook_id,
                "name": hook_class.hook_name,
                "description": hook_class.hook_description,
                "config_schema": hook_class.get_config_schema()
            }
            for hook_id, hook_class in self._hooks.items()
        ]
    
    def create_instance(self, hook_id: str, config: dict) -> PreShutdownHook:
        """
        创建 hook 插件实例
        
        Args:
            hook_id: Hook ID
            config: Hook 配置
        
        Returns:
            Hook 插件实例
        """
        # In mock mode, return a mock hook instead
        if self._mock_mode:
            from hooks.mock_hook import MockHook
            hook_class = self.get_hook(hook_id)
            return MockHook(hook_id, hook_class.hook_name, config)
        
        hook_class = self.get_hook(hook_id)
        return hook_class(config)


# 全局 hook 注册表
registry = HookRegistry()


def get_registry() -> HookRegistry:
    """获取 hook 注册表"""
    return registry
