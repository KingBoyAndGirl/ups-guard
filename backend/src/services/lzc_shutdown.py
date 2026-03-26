"""关机客户端模块 - 支持多种关机方式"""
import grpc
import logging
import asyncio
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


class LzcApiGatewayShutdown:
    """
    通过懒猫 lzcinit sidecar 的 API Gateway 执行 gRPC 关机。

    懒猫微服架构：
      ups-guard 容器 --> API Gateway (lzcinit sidecar :81) --> lzc-apis.socket (mTLS)
    应用容器通过 insecure gRPC 连接 API Gateway，由 sidecar 代理 mTLS 认证。

    Gateway 地址格式: app.<LAZYCAT_APP_ID>.lzcapp:81
    """

    def __init__(
        self,
        gateway_address: str = "",
        timeout: float = 10.0,
        max_retries: int = 3,
    ):
        self.gateway_address = gateway_address or self._detect_gateway_address()
        self.timeout = timeout
        self.max_retries = max_retries
        logger.info(f"LzcApiGatewayShutdown initialized, gateway={self.gateway_address}")

    @staticmethod
    def _detect_gateway_address() -> str:
        """
        自动检测 API Gateway 地址。

        优先级：
        1. LZCAPP_API_GATEWAY_ADDRESS 环境变量（懒猫平台注入到 app sidecar）
        2. 根据 LAZYCAT_APP_ID 构造
        3. 默认值
        """
        gateway = os.environ.get("LZCAPP_API_GATEWAY_ADDRESS", "")
        if gateway:
            logger.info(f"Using API Gateway from LZCAPP_API_GATEWAY_ADDRESS: {gateway}")
            return gateway

        app_id = os.environ.get("LAZYCAT_APP_ID", "")
        if app_id:
            gateway = f"app.{app_id}.lzcapp:81"
            logger.info(f"Constructed API Gateway from LAZYCAT_APP_ID: {gateway}")
            return gateway

        default = "app.cloud.lazycat.app.ups-guard.lzcapp:81"
        logger.warning(
            f"No LZCAPP_API_GATEWAY_ADDRESS or LAZYCAT_APP_ID found, "
            f"using default: {default}"
        )
        return default

    async def _execute_grpc_call(self, request: bytes, operation: str) -> bool:
        """执行 gRPC 调用（带重试和指数退避）"""
        for attempt in range(1, self.max_retries + 1):
            channel: grpc.aio.Channel | None = None
            try:
                channel = grpc.aio.insecure_channel(self.gateway_address)

                stub = channel.unary_unary(
                    "/cloud.lazycat.apis.common.BoxService/Shutdown",
                    request_serializer=lambda x: x,
                    response_deserializer=lambda x: x,
                )

                await asyncio.wait_for(stub(request), timeout=self.timeout)
                logger.info(f"{operation} via API Gateway succeeded")
                return True

            except asyncio.TimeoutError:
                logger.error(
                    f"{operation} gRPC call timed out after {self.timeout}s "
                    f"(attempt {attempt}/{self.max_retries})"
                )
            except grpc.RpcError as e:
                code = e.code()
                details = e.details()
                logger.error(
                    f"{operation} gRPC error: {code} - {details} "
                    f"(attempt {attempt}/{self.max_retries})"
                )
                # UNIMPLEMENTED 说明连接成功但方法不存在，不需要重试
                if code == grpc.StatusCode.UNIMPLEMENTED:
                    logger.error(f"{operation}: BoxService/Shutdown not found on gateway")
                    return False
            except Exception as e:
                logger.error(
                    f"{operation} unexpected error: {type(e).__name__}: {e} "
                    f"(attempt {attempt}/{self.max_retries})"
                )
            finally:
                if channel is not None:
                    await channel.close()

            if attempt < self.max_retries:
                wait_time = 2 ** (attempt - 1)
                logger.info(f"Retrying {operation} in {wait_time}s...")
                await asyncio.sleep(wait_time)

        logger.error(f"{operation} failed after {self.max_retries} attempts")
        return False

    async def shutdown(self) -> bool:
        """通过 API Gateway 执行关机（graceful shutdown）"""
        # protobuf ShutdownRequest { Action action = 1; }
        # Action: POWER_OFF = 0
        # Tag = (1 << 3) | 0 = 0x08, Value = 0x00
        shutdown_request = bytes([0x08, 0x00])
        return await self._execute_grpc_call(shutdown_request, "Shutdown")

    async def reboot(self) -> bool:
        """通过 API Gateway 执行重启"""
        # Action: REBOOT = 1
        reboot_request = bytes([0x08, 0x01])
        return await self._execute_grpc_call(reboot_request, "Reboot")


class MockShutdown:
    """Mock 关机实现，用于开发测试"""

    def __init__(self):
        pass

    async def shutdown(self) -> bool:
        """模拟关机"""
        logger.warning("MOCK MODE: Shutdown command received (not executed)")
        return True

    async def reboot(self) -> bool:
        """模拟重启"""
        logger.warning("MOCK MODE: Reboot command received (not executed)")
        return True


def _is_running_in_docker() -> bool:
    """检测是否运行在 Docker 容器中"""
    if os.path.exists("/.dockerenv"):
        return True
    try:
        with open("/proc/1/cgroup", "r") as f:
            content = f.read()
            if "docker" in content or "containerd" in content:
                return True
    except (FileNotFoundError, PermissionError):
        pass
    if os.environ.get("DOCKER_CONTAINER") or os.environ.get("container"):
        return True
    return False


def _find_shutdown_command() -> str | None:
    """查找系统中可用的 shutdown 命令路径"""
    candidates = [
        "/sbin/shutdown",
        "/usr/sbin/shutdown",
        "/bin/shutdown",
        "/usr/bin/shutdown",
    ]
    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            logger.debug(f"Found shutdown command at: {path}")
            return path

    found = shutil.which("shutdown")
    if found:
        logger.debug(f"Found shutdown command via PATH: {found}")
    return found


def _find_poweroff_command() -> str | None:
    """查找 poweroff/reboot 命令路径"""
    candidates = [
        "/sbin/poweroff",
        "/usr/sbin/poweroff",
        "/bin/poweroff",
    ]
    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return shutil.which("poweroff")


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
        """构建关机命令候选列表（按优先级排列）"""
        if self.os_type == "Windows":
            return [["shutdown", "/s", "/t", "0", "/f"]]

        if self.os_type not in ("Linux", "Darwin"):
            raise RuntimeError(f"Unsupported OS: {self.os_type}")

        commands: list[list[str]] = []

        if self.in_docker:
            nsenter_path = shutil.which("nsenter")
            if nsenter_path:
                commands.append([
                    nsenter_path, "-t", "1", "-m", "-u", "-i", "-n", "-p",
                    "--", "/sbin/shutdown", "-h", "now",
                ])
                logger.debug("Strategy 1 (nsenter) available")

            poff = _find_poweroff_command()
            if poff:
                commands.append([poff, "-f"])
                logger.debug(f"Strategy 2 (poweroff) available at {poff}")

            shutdown_cmd = _find_shutdown_command()
            if shutdown_cmd:
                commands.append([shutdown_cmd, "-h", "now"])
                logger.debug(f"Strategy 3 (shutdown in container) available at {shutdown_cmd}")
        else:
            shutdown_cmd = _find_shutdown_command()
            if shutdown_cmd:
                commands.append([shutdown_cmd, "-h", "now"])
            else:
                poff = _find_poweroff_command()
                if poff:
                    commands.append([poff, "-f"])

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
            nsenter_path = shutil.which("nsenter")
            if nsenter_path:
                commands.append([
                    nsenter_path, "-t", "1", "-m", "-u", "-i", "-n", "-p",
                    "--", "/sbin/shutdown", "-r", "now",
                ])

            shutdown_cmd = _find_shutdown_command()
            if shutdown_cmd:
                commands.append([shutdown_cmd, "-r", "now"])
        else:
            shutdown_cmd = _find_shutdown_command()
            if shutdown_cmd:
                commands.append([shutdown_cmd, "-r", "now"])

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
                ),
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
    mock_mode: bool = False,
    shutdown_method: str = "lzc_api_gateway",
    gateway_address: str = "",
) -> ShutdownInterface:
    """
    创建关机客户端实例。

    shutdown_method 可选值：
    - "lzc_api_gateway" : 通过 lzcinit API Gateway 连接（推荐，懒猫微服默认）
    - "system_command"  : 系统命令关机（Docker/原生通用）
    - "mock"            : 模拟关机（开发测试）
    """
    if mock_mode:
        return MockShutdown()

    if shutdown_method == "lzc_api_gateway":
        return LzcApiGatewayShutdown(gateway_address=gateway_address)
    elif shutdown_method == "system_command":
        return SystemCommandShutdown()
    elif shutdown_method == "mock":
        return MockShutdown()
    else:
        # 兼容旧配置 "lzc_grpc"，fallback 到 API Gateway
        logger.warning(
            f"Unknown shutdown_method '{shutdown_method}', "
            f"defaulting to lzc_api_gateway"
        )
        return LzcApiGatewayShutdown(gateway_address=gateway_address)
