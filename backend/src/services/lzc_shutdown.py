"""关机客户端模块 - 支持多种关机方式"""
import grpc
import logging
import asyncio
import socket
import os
import platform
import shutil
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


def _is_running_in_docker() -> bool:
    """检测是否运行在 Docker 容器中"""
    if os.path.exists('/.dockerenv'):
        return True
    try:
        with open('/proc/1/cgroup', 'r') as f:
            content = f.read()
            if 'docker' in content or 'containerd' in content:
                return True
    except (FileNotFoundError, PermissionError):
        pass
    if os.environ.get('DOCKER_CONTAINER') or os.environ.get('container'):
        return True
    return False


def _find_shutdown_command() -> str | None:
    """查找系统中可用的 shutdown 命令路径"""
    # 尝试多个常见路径
    candidates = [
        '/sbin/shutdown',
        '/usr/sbin/shutdown',
        '/bin/shutdown',
        '/usr/bin/shutdown',
    ]
    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            logger.debug(f"Found shutdown command at: {path}")
            return path

    # 最后尝试 PATH 搜索
    found = shutil.which('shutdown')
    if found:
        logger.debug(f"Found shutdown command via PATH: {found}")
    return found


def _find_poweroff_command() -> str | None:
    """查找 poweroff/reboot 命令路径"""
    candidates = [
        '/sbin/poweroff',
        '/usr/sbin/poweroff',
        '/bin/poweroff',
    ]
    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return shutil.which('poweroff')


class SystemCommandShutdown:
    """
    系统命令关机实现（通用跨平台）

    支持多种运行环境：
    - Docker 容器内（需要 --pid=host + --privileged）
    - 原生 Linux/macOS
    - Windows
    """

    def __init__(self):
        self.os_type = platform.system()
        self.in_docker = _is_running_in_docker()
        if self.in_docker:
            logger.info("Detected Docker environment, will use nsenter for host shutdown")
        else:
            logger.info(f"Detected native {self.os_type} environment")

    def _build_shutdown_commands(self) -> list[list[str]]:
        """
        构建关机命令候选列表（按优先级排列）。
        返回多个候选命令，依次尝试直到成功。
        """
        if self.os_type == "Windows":
            return [["shutdown", "/s", "/t", "0", "/f"]]

        if self.os_type not in ("Linux", "Darwin"):
            raise RuntimeError(f"Unsupported OS: {self.os_type}")

        commands: list[list[str]] = []

        if self.in_docker:
            # 策略 1: nsenter 进入宿主机 PID 1 命名空间执行关机
            # 需要容器以 --pid=host --privileged 启动
            nsenter_path = shutil.which('nsenter')
            if nsenter_path:
                shutdown_in_host = '/sbin/shutdown'  # 宿主机上的路径
                commands.append([
                    nsenter_path, '-t', '1', '-m', '-u', '-i', '-n', '-p',
                    '--', shutdown_in_host, '-h', 'now'
                ])
                logger.debug("Strategy 1 (nsenter) available")

            # 策略 2: 容器内直接使用 poweroff -f
            poff = _find_poweroff_command()
            if poff:
                commands.append([poff, '-f'])
                logger.debug(f"Strategy 2 (poweroff) available at {poff}")

            # 策略 3: 容器内直接使用 shutdown（如果容器中安装了）
            shutdown_cmd = _find_shutdown_command()
            if shutdown_cmd:
                commands.append([shutdown_cmd, '-h', 'now'])
                logger.debug(f"Strategy 3 (shutdown in container) available at {shutdown_cmd}")
        else:
            # 非 Docker：直接使用 shutdown
            shutdown_cmd = _find_shutdown_command()
            if shutdown_cmd:
                commands.append([shutdown_cmd, '-h', 'now'])
            else:
                # 退而求其次用 poweroff
                poff = _find_poweroff_command()
                if poff:
                    commands.append([poff, '-f'])

        if not commands:
            logger.error(
                "No shutdown command found! "
                "In Docker, ensure the container runs with --pid=host --privileged "
                "and nsenter is installed."
            )

        return commands

    def _build_reboot_commands(self) -> list[list[str]]:
        """构建重启命令候选列表"""
        if self.os_type == "Windows":
            return [["shutdown", "/r", "/t", "0", "/f"]]

        if self.os_type not in ("Linux", "Darwin"):
            raise RuntimeError(f"Unsupported OS: {self.os_type}")

        commands: list[list[str]] = []

        if self.in_docker:
            nsenter_path = shutil.which('nsenter')
            if nsenter_path:
                commands.append([
                    nsenter_path, '-t', '1', '-m', '-u', '-i', '-n', '-p',
                    '--', '/sbin/shutdown', '-r', 'now'
                ])

            shutdown_cmd = _find_shutdown_command()
            if shutdown_cmd:
                commands.append([shutdown_cmd, '-r', 'now'])
        else:
            shutdown_cmd = _find_shutdown_command()
            if shutdown_cmd:
                commands.append([shutdown_cmd, '-r', 'now'])

        return commands

    async def _execute_command(self, command: list[str], operation: str) -> bool:
        """执行系统命令"""
        try:
            logger.info(f"Executing {operation}: {' '.join(command)}")
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    command, capture_output=True, text=True, timeout=10
                )
            )

            if result.returncode == 0:
                logger.info(f"{operation} command succeeded")
                return True
            else:
                logger.warning(
                    f"{operation} command exited with code {result.returncode}, "
                    f"stderr: {result.stderr.strip()}"
                )
                return False

        except FileNotFoundError as e:
            logger.warning(f"{operation} command not found: {e}")
            return False
        except subprocess.TimeoutExpired:
            logger.error(f"{operation} command timed out")
            return False
        except Exception as e:
            logger.warning(f"{operation} command failed: {type(e).__name__}: {e}")
            return False

    async def _execute_with_fallback(
        self, commands: list[list[str]], operation: str
    ) -> bool:
        """依次尝试多个命令，直到有一个成功"""
        if not commands:
            logger.error(
                f"No {operation.lower()} commands available. "
                f"Docker={self.in_docker}, OS={self.os_type}. "
                f"If running in Docker, add 'pid: host' and 'privileged: true' "
                f"to docker-compose.yml for the backend service."
            )
            return False

        for i, cmd in enumerate(commands, 1):
            logger.info(
                f"Trying {operation} strategy {i}/{len(commands)}: "
                f"{' '.join(cmd)}"
            )
            success = await self._execute_command(cmd, operation)
            if success:
                return True
            logger.warning(
                f"Strategy {i} failed, "
                f"{'trying next...' if i < len(commands) else 'no more strategies.'}"
            )

        logger.error(f"All {operation.lower()} strategies exhausted")
        return False

    async def shutdown(self) -> bool:
        """执行关机"""
        commands = self._build_shutdown_commands()
        return await self._execute_with_fallback(commands, "Shutdown")

    async def reboot(self) -> bool:
        """执行重启"""
        commands = self._build_reboot_commands()
        return await self._execute_with_fallback(commands, "Reboot")


def create_shutdown_client(
    socket_path: str,
    mock_mode: bool = False,
    shutdown_method: str = "lzc_grpc",
) -> ShutdownInterface:
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
        logger.warning(
            f"Unknown shutdown_method '{shutdown_method}', defaulting to lzc_grpc"
        )
        return LzcGrpcShutdown(socket_path)
