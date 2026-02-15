"""LZCOS gRPC 关机客户端"""
import grpc
import logging
import asyncio
import socket
import os
import platform
import subprocess
from typing import Protocol

logger = logging.getLogger(__name__)


class ShutdownInterface(Protocol):
    """关机接口"""
    
    async def shutdown(self) -> bool:
        """执行关机"""
        ...
    
    async def reboot(self) -> bool:
        """执行重启"""
        ...


class LzcGrpcShutdown:
    """LZCOS gRPC 关机实现"""
    
    def __init__(self, socket_path: str, timeout: float = 5.0, max_retries: int = 3):
        self.socket_path = socket_path
        self.timeout = timeout
        self.max_retries = max_retries
    
    async def _check_socket_reachable(self) -> bool:
        """检查 socket 是否可达"""
        try:
            # Check if socket file exists
            if not os.path.exists(self.socket_path):
                logger.error(f"Socket file does not exist: {self.socket_path}")
                return False
            
            # Try to connect to the socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            try:
                sock.connect(self.socket_path)
                sock.close()
                return True
            except Exception as e:
                logger.error(f"Socket connection test failed: {e}")
                return False
        except Exception as e:
            logger.error(f"Error checking socket reachability: {e}")
            return False
    
    async def _execute_grpc_call(self, request: bytes, operation: str) -> bool:
        """执行 gRPC 调用（带重试和超时）"""
        for attempt in range(1, self.max_retries + 1):
            try:

                # Check socket reachability first
                if not await self._check_socket_reachable():
                    logger.error(f"Socket {self.socket_path} is not reachable")
                    if attempt < self.max_retries:
                        # Exponential backoff
                        wait_time = 2 ** (attempt - 1)
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        return False
                
                # Create Unix socket connection with timeout
                channel = grpc.aio.insecure_channel(
                    f'unix://{self.socket_path}',
                    options=[
                        ('grpc.keepalive_timeout_ms', int(self.timeout * 1000)),
                    ]
                )
                
                try:
                    # Call gRPC method with timeout
                    stub = channel.unary_unary(
                        '/cloud.lazycat.apis.common.BoxService/Shutdown',
                        request_serializer=lambda x: x,
                        response_deserializer=lambda x: x,
                    )
                    
                    await asyncio.wait_for(stub(request), timeout=self.timeout)
                    return True
                finally:
                    await channel.close()
                    
            except asyncio.TimeoutError:
                logger.error(f"{operation} gRPC call timed out after {self.timeout} seconds (attempt {attempt})")
            except grpc.RpcError as e:
                logger.error(f"{operation} gRPC call failed: {e.code()} - {e.details()} (attempt {attempt})")
            except Exception as e:
                logger.error(f"{operation} failed with unexpected error: {type(e).__name__}: {e} (attempt {attempt})")
            
            # Retry with exponential backoff
            if attempt < self.max_retries:
                wait_time = 2 ** (attempt - 1)
                await asyncio.sleep(wait_time)
        
        logger.error(f"{operation} failed after {self.max_retries} attempts")
        return False
    
    async def shutdown(self) -> bool:
        """通过 gRPC 执行关机"""
        # 手动编码 protobuf ShutdownRequest { Action action = 1; }
        # Action: POWER_OFF = 0, REBOOT = 1
        # Wire format: field_number=1, wire_type=0 (varint), value=0
        # Tag = (field_number << 3) | wire_type = (1 << 3) | 0 = 0x08
        shutdown_request = bytes([0x08, 0x00])  # Field 1, value 0 (POWER_OFF)
        return await self._execute_grpc_call(shutdown_request, "Shutdown")
    
    async def reboot(self) -> bool:
        """通过 gRPC 执行重启"""
        # Protobuf: Action = 1 (REBOOT)
        reboot_request = bytes([0x08, 0x01])  # Field 1, value 1 (REBOOT)
        return await self._execute_grpc_call(reboot_request, "Reboot")


class MockShutdown:
    """Mock 关机实现，用于开发测试"""
    
    def __init__(self, socket_path: str = None):
        pass
    
    async def shutdown(self) -> bool:
        """模拟关机"""
        logger.warning("MOCK MODE: Shutdown command received (not executed)")
        logger.warning("In production, this would shut down the system via gRPC")
        return True
    
    async def reboot(self) -> bool:
        """模拟重启"""
        logger.warning("MOCK MODE: Reboot command received (not executed)")
        logger.warning("In production, this would reboot the system via gRPC")
        return True


class SystemCommandShutdown:
    """系统命令关机实现（通用跨平台）"""
    
    def __init__(self):
        self.os_type = platform.system()

    def _get_shutdown_command(self) -> list:
        """获取关机命令"""
        if self.os_type == "Windows":
            # Windows: shutdown /s /t 0 /f
            return ["shutdown", "/s", "/t", "0", "/f"]
        elif self.os_type in ("Linux", "Darwin"):
            # Linux/macOS: shutdown -h now (需要 root 权限)
            return ["shutdown", "-h", "now"]
        else:
            raise RuntimeError(f"Unsupported OS: {self.os_type}")
    
    def _get_reboot_command(self) -> list:
        """获取重启命令"""
        if self.os_type == "Windows":
            # Windows: shutdown /r /t 0 /f
            return ["shutdown", "/r", "/t", "0", "/f"]
        elif self.os_type in ("Linux", "Darwin"):
            # Linux/macOS: shutdown -r now
            return ["shutdown", "-r", "now"]
        else:
            raise RuntimeError(f"Unsupported OS: {self.os_type}")
    
    async def _execute_command(self, command: list, operation: str) -> bool:
        """执行系统命令"""
        try:

            # 在线程池中执行命令（避免阻塞事件循环）
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(command, capture_output=True, text=True, timeout=10)
            )
            
            if result.returncode == 0:
                return True
            else:
                logger.error(f"{operation} command failed with code {result.returncode}")
                logger.error(f"stderr: {result.stderr}")
                return False
        
        except subprocess.TimeoutExpired:
            logger.error(f"{operation} command timed out")
            return False
        except Exception as e:
            logger.error(f"{operation} command failed: {e}")
            return False
    
    async def shutdown(self) -> bool:
        """执行关机"""
        command = self._get_shutdown_command()
        return await self._execute_command(command, "Shutdown")
    
    async def reboot(self) -> bool:
        """执行重启"""
        command = self._get_reboot_command()
        return await self._execute_command(command, "Reboot")


def create_shutdown_client(socket_path: str, mock_mode: bool = False, shutdown_method: str = "lzc_grpc") -> ShutdownInterface:
    """创建关机客户端实例"""
    if mock_mode:
        return MockShutdown()
    
    if shutdown_method == "system_command":
        return SystemCommandShutdown()
    elif shutdown_method == "lzc_grpc":
        return LzcGrpcShutdown(socket_path)
    elif shutdown_method == "mock":
        return MockShutdown()
    else:
        logger.warning(f"Unknown shutdown_method '{shutdown_method}', defaulting to lzc_grpc")
        return LzcGrpcShutdown(socket_path)
