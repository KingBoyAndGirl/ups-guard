"""Mock Hook for testing - simulates hook execution without real operations"""
import asyncio
import logging
from typing import Dict, Any
from hooks.base import PreShutdownHook

logger = logging.getLogger(__name__)


class MockHook(PreShutdownHook):
    """Mock hook that simulates execution without performing real operations"""
    
    def __init__(self, hook_id: str, hook_name: str, config: Dict[str, Any]):
        """
        Initialize mock hook
        
        Args:
            hook_id: The hook ID being mocked
            hook_name: The hook name being mocked
            config: Hook configuration
        """
        self.hook_id = hook_id
        self.hook_name = hook_name
        self.hook_description = f"Mock implementation of {hook_name}"
        super().__init__(config)
    
    @classmethod
    def get_config_schema(cls):
        """Mock hooks accept any config"""
        return []
    
    def validate_config(self):
        """Mock hooks accept any config"""
        pass
    
    async def execute(self) -> bool:
        """Simulate hook execution"""
        await asyncio.sleep(0.1)  # Simulate some work
        return True
    
    async def test_connection(self) -> bool:
        """Simulate connection test"""
        await asyncio.sleep(0.05)  # Simulate quick test
        return True
