"""NUT (Network UPS Tools) 异步客户端"""
import asyncio
import logging
from typing import Dict, Optional, Protocol, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class NutClientInterface(Protocol):
    """NUT 客户端接口"""
    
    async def connect(self):
        """连接到 NUT 服务器"""
        ...
    
    async def disconnect(self):
        """断开连接"""
        ...
    
    async def get_var(self, var_name: str) -> Optional[str]:
        """获取单个变量值"""
        ...
    
    async def list_vars(self) -> Dict[str, str]:
        """列出所有变量"""
        ...
    
    async def list_ups(self) -> list:
        """列出所有 UPS 设备"""
        ...
    
    async def run_command(self, command: str) -> bool:
        """执行 UPS 即时命令 (INSTCMD)"""
        ...
    
    async def set_var(self, var_name: str, value: str) -> bool:
        """设置 UPS 可写变量"""
        ...
    
    async def list_rw(self) -> Dict[str, dict]:
        """列出所有可写变量及其元数据"""
        ...


class RealNutClient:
    """真实的 NUT 客户端实现"""
    
    def __init__(self, host: str, port: int, username: str, password: str, ups_name: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.ups_name = ups_name  # 可以为空，连接后自动发现
        self._auto_discovered = False  # 标记是否已自动发现
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_delay = 60  # Maximum 60 seconds between reconnect attempts
        self._last_connection_error: Optional[str] = None
        # 连接状态变化回调
        self._on_disconnected_callback = None
        self._on_reconnected_callback = None

    def set_connection_callbacks(self, on_disconnected=None, on_reconnected=None):
        """设置连接状态变化回调"""
        self._on_disconnected_callback = on_disconnected
        self._on_reconnected_callback = on_reconnected

    async def _notify_disconnected(self):
        """通知连接断开"""
        logger.info(f"_notify_disconnected() called, callback={self._on_disconnected_callback is not None}")
        if self._on_disconnected_callback:
            try:
                logger.info("Calling disconnected callback...")
                await self._on_disconnected_callback()
                logger.info("Disconnected callback completed")
            except Exception as e:
                logger.error(f"Error in disconnected callback: {e}")

    async def _notify_reconnected(self):
        """通知连接恢复"""
        logger.info(f"_notify_reconnected() called, callback={self._on_reconnected_callback is not None}")
        if self._on_reconnected_callback:
            try:
                logger.info("Calling reconnected callback...")
                await self._on_reconnected_callback()
                logger.info("Reconnected callback completed")
            except Exception as e:
                logger.error(f"Error in reconnected callback: {e}")

    async def connect(self):
        """连接到 NUT 服务器"""
        try:
            logger.info(f"Connecting to NUT server at {self.host}:{self.port}...")
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)

            # 登录 - 使用 _send_raw_command 避免连接状态检查
            response = await self._send_raw_command(f"USERNAME {self.username}")
            logger.debug(f"USERNAME response: {response}")

            response = await self._send_raw_command(f"PASSWORD {self.password}")
            logger.debug(f"PASSWORD response: {response}")

            self._connected = True
            self._reconnect_attempts = 0
            self._last_connection_error = None

            # 如果需要自动发现 UPS（首次连接或重连时需要重新发现）
            if not self._auto_discovered:
                await self._auto_discover_ups()

            logger.info(f"Successfully connected to NUT server, UPS: {self.ups_name}")
        except Exception as e:
            error_msg = f"Failed to connect to NUT server: {e}"
            logger.error(error_msg)
            self._connected = False
            self._last_connection_error = error_msg
            raise
    
    async def _auto_discover_ups(self):
        """自动发现 UPS 名称"""
        old_ups_name = self.ups_name
        try:
            # 发送 LIST UPS 命令
            self.writer.write(b"LIST UPS\n")
            await self.writer.drain()

            # 读取响应，直到收到 END LIST UPS
            # NUT 协议响应格式:
            # BEGIN LIST UPS
            # UPS <upsname> "<description>"
            # ...
            # END LIST UPS
            ups_list = []
            while True:
                line = await asyncio.wait_for(self.reader.readline(), timeout=5.0)
                if not line:
                    break
                line_str = line.decode().strip()

                # 跳过 BEGIN 行
                if line_str.startswith("BEGIN LIST"):
                    continue

                # 检查结束标记
                if line_str.startswith("END LIST"):
                    break

                # 检查错误
                if line_str.startswith("ERR"):
                    logger.warning(f"NUT server error during auto-discover: {line_str}")
                    break

                # 解析 UPS 名称
                # 格式: UPS <upsname> "<description>"
                if line_str.startswith("UPS "):
                    parts = line_str.split()
                    if len(parts) >= 2:
                        ups_list.append(parts[1])

            if ups_list:
                new_ups_name = ups_list[0]
                if old_ups_name and old_ups_name != new_ups_name:
                    logger.info(f"UPS name changed: '{old_ups_name}' -> '{new_ups_name}'")
                self.ups_name = new_ups_name
                self._auto_discovered = True
                logger.info(f"Auto-discovered UPS: {self.ups_name}")
            else:
                # 没有发现 UPS，保留旧名称或使用默认值
                if not self.ups_name:
                    self.ups_name = "ups"
                    logger.warning("No UPS devices found, using default name 'ups'")
                else:
                    logger.warning(f"No UPS devices found, keeping previous name '{self.ups_name}'")
                # 不设置 _auto_discovered = True，下次重连时继续尝试发现
        except asyncio.TimeoutError:
            if not self.ups_name:
                self.ups_name = "ups"
                logger.warning("Timeout during auto-discover UPS, using default name 'ups'")
            else:
                logger.warning(f"Timeout during auto-discover UPS, keeping previous name '{self.ups_name}'")
        except Exception as e:
            if not self.ups_name:
                self.ups_name = "ups"
                logger.warning(f"Failed to auto-discover UPS: {e}, using default name 'ups'")
            else:
                logger.warning(f"Failed to auto-discover UPS: {e}, keeping previous name '{self.ups_name}'")

    async def _send_raw_command(self, command: str) -> str:
        """发送原始命令（不检查连接状态，用于初始化）"""
        self.writer.write(f"{command}\n".encode())
        await self.writer.drain()
        response = await self.reader.readline()
        return response.decode().strip()

    async def _reconnect(self):
        """自动重连（带指数退避）"""
        self._reconnect_attempts += 1
        
        # 先关闭旧连接
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
            self.writer = None
            self.reader = None

        # Calculate exponential backoff delay (capped at max_reconnect_delay)
        delay = min(2 ** (self._reconnect_attempts - 1), self._max_reconnect_delay)
        
        logger.warning(f"Attempting to reconnect to NUT server (attempt {self._reconnect_attempts}, waiting {delay}s)...")
        await asyncio.sleep(delay)
        
        try:
            # 每次重连时重新发现 UPS（因为 NUT 容器可能已经重新配置了新的 UPS）
            old_ups_name = self.ups_name
            self._auto_discovered = False  # 重置自动发现标记，允许重新发现

            await self.connect()

            # 如果 UPS 名称改变了，记录日志
            if old_ups_name and old_ups_name != self.ups_name:
                logger.info(f"UPS name changed from '{old_ups_name}' to '{self.ups_name}'")

            logger.info("Reconnection successful")
            # 注意：不在这里触发重连回调，由 monitor 统一管理
            # monitor 会在下次成功读取数据时发送恢复通知
            return True
        except Exception as e:
            logger.error(f"Reconnection attempt {self._reconnect_attempts} failed: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                logger.error(f"Error disconnecting from NUT server: {e}")
        self._connected = False

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected
    
    def get_connection_status(self) -> dict:
        """获取连接状态信息"""
        return {
            "connected": self._connected,
            "reconnect_attempts": self._reconnect_attempts,
            "last_error": self._last_connection_error,
        }
    
    async def _send_command(self, command: str, timeout: float = 10.0) -> str:
        """发送命令并获取响应（带超时）"""
        if not self._connected:
            # Try to reconnect
            if not await self._reconnect():
                raise RuntimeError("Not connected to NUT server and reconnection failed")
        
        try:
            self.writer.write(f"{command}\n".encode())
            await self.writer.drain()
            
            response = await asyncio.wait_for(self.reader.readline(), timeout=timeout)
            return response.decode().strip()
        except asyncio.TimeoutError:
            logger.error(f"Timeout sending command '{command}'")
            self._connected = False
            raise
        except Exception as e:
            logger.error(f"Error sending command '{command}': {e}")
            self._connected = False
            raise
    
    async def _read_until(self, end_marker: str, timeout: float = 15.0) -> list:
        """读取多行响应直到结束标记（带超时）

        NUT 协议响应格式:
        BEGIN LIST VAR <upsname>
        VAR <upsname> <varname> "<value>"
        ...
        END LIST VAR <upsname>
        """
        lines = []
        try:
            while True:
                line = await asyncio.wait_for(self.reader.readline(), timeout=timeout)
                if not line:
                    logger.warning("Connection closed while reading response")
                    break
                line = line.decode().strip()

                # 跳过 BEGIN 行
                if line.startswith("BEGIN LIST"):
                    continue

                # 检查结束标记（可能包含 UPS 名称，如 "END LIST VAR ups"）
                if line.startswith(end_marker.split()[0]) and "END" in line:
                    break

                # 检查错误
                if line.startswith("ERR"):
                    logger.error(f"NUT server error: {line}")
                    break

                lines.append(line)
        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for {end_marker}")
        return lines
    
    async def get_var(self, var_name: str) -> Optional[str]:
        """获取单个变量值"""
        try:
            response = await self._send_command(f"GET VAR {self.ups_name} {var_name}")
            # 响应格式: VAR <upsname> <varname> "<value>"
            if response.startswith("VAR"):
                parts = response.split('"')
                if len(parts) >= 2:
                    return parts[1]
            return None
        except Exception as e:
            logger.error(f"Error getting variable {var_name}: {e}")
            # Try to reconnect on next call
            self._connected = False
            return None
    
    async def list_vars(self) -> Dict[str, str]:
        """列出所有变量"""
        was_connected = self._connected
        logger.debug(f"list_vars() called, was_connected={was_connected}")
        try:
            await self._send_command(f"LIST VAR {self.ups_name}")
            lines = await self._read_until("END LIST VAR")
            
            # 如果没有收到任何数据，标记断开连接并重置自动发现
            if not lines:
                logger.warning(f"No data received from NUT server, marking as disconnected. was_connected={was_connected}")
                self._connected = False
                # 重置自动发现标记，下次重连时会重新发现 UPS
                # （可能是 NUT 容器已经从 dummy 模式切换到真实 UPS）
                self._auto_discovered = False
                # 注意：不在这里触发断开回调，由 monitor 统一管理
                # 避免与 monitor._monitor_loop 中的通知逻辑重复
                return {}

            vars_dict = {}
            for line in lines:
                # 响应格式: VAR <upsname> <varname> "<value>"
                if line.startswith("VAR"):
                    parts = line.split('"')
                    if len(parts) >= 2:
                        var_parts = line.split()
                        if len(var_parts) >= 3:
                            var_name = var_parts[2]
                            var_value = parts[1]
                            vars_dict[var_name] = var_value
            
            return vars_dict
        except Exception as e:
            logger.error(f"Error listing variables: {e}")
            self._connected = False  # 标记断开，下次调用会触发重连
            self._auto_discovered = False  # 重置自动发现标记
            # 注意：不在这里触发断开回调，由 monitor 统一管理
            return {}
    
    async def list_ups(self) -> list:
        """列出所有 UPS 设备"""
        try:
            await self._send_command("LIST UPS")
            lines = await self._read_until("END LIST UPS")
            
            ups_list = []
            for line in lines:
                # 响应格式: UPS <upsname> "<description>"
                if line.startswith("UPS"):
                    parts = line.split('"')
                    if len(parts) >= 2:
                        ups_parts = line.split()
                        if len(ups_parts) >= 2:
                            ups_name = ups_parts[1]
                            description = parts[1] if len(parts) >= 2 else ""
                            ups_list.append({"name": ups_name, "description": description})
            
            return ups_list
        except Exception as e:
            logger.error(f"Error listing UPS devices: {e}")
            return []
    
    async def run_command(self, command: str) -> bool:
        """执行 UPS 即时命令"""
        try:
            response = await self._send_command(f"INSTCMD {self.ups_name} {command}")
            if response.startswith("OK"):
                logger.info(f"UPS command '{command}' executed successfully")
                return True
            else:
                logger.error(f"UPS command '{command}' failed: {response}")
                return False
        except Exception as e:
            logger.error(f"Error executing UPS command '{command}': {e}")
            return False
    
    async def set_var(self, var_name: str, value: str) -> bool:
        """设置 UPS 可写变量值
        
        NUT 协议: SET VAR <upsname> <varname> "<value>"
        响应: OK 或 ERR <message>
        """
        try:
            response = await self._send_command(
                f'SET VAR {self.ups_name} {var_name} "{value}"'
            )
            if response.startswith("OK"):
                logger.info(f"Successfully set {var_name} = {value}")
                return True
            else:
                logger.error(f"Failed to set {var_name}: {response}")
                return False
        except Exception as e:
            logger.error(f"Error setting variable {var_name}: {e}")
            return False
    
    async def list_rw(self) -> Dict[str, dict]:
        """列出所有可写变量
        
        NUT 协议: LIST RW <upsname>
        响应格式:
        BEGIN LIST RW <upsname>
        RW <upsname> <varname> "<value>"
        END LIST RW <upsname>
        """
        try:
            await self._send_command(f"LIST RW {self.ups_name}")
            lines = await self._read_until("END LIST RW")
            
            rw_vars = {}
            for line in lines:
                # 解析 NUT RW 响应格式: RW <upsname> <varname> "<value>"
                # 例如: RW ups input.transfer.high "278"
                if line.startswith("RW"):
                    parts = line.split('"')  # 按引号分割以获取值
                    if len(parts) >= 2:
                        var_parts = line.split()  # 按空格分割以获取变量名
                        if len(var_parts) >= 3:
                            var_name = var_parts[2]  # 变量名在第3个位置
                            var_value = parts[1]  # 值在第一对引号之间
                            rw_vars[var_name] = {
                                "value": var_value,
                                "writable": True
                            }
            return rw_vars
        except Exception as e:
            logger.error(f"Error listing RW variables: {e}")
            return {}


class EventDrivenNutClient(RealNutClient):
    """
    事件驱动的 NUT 客户端
    支持 NUT LISTEN 机制，实现实时状态更新
    """
    
    def __init__(self, host: str, port: int, username: str, password: str, ups_name: str):
        super().__init__(host, port, username, password, ups_name)
        self._listen_mode = False
        self._listen_task: Optional[asyncio.Task] = None
        self._on_data_changed: Optional[Callable] = None
        self._heartbeat_interval = 30  # 秒
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._last_heartbeat = datetime.now()
        
    async def start_listen(self, ups_name: str, on_data_changed: Callable) -> bool:
        """
        开始监听 UPS 状态变化
        
        Args:
            ups_name: UPS 名称
            on_data_changed: 数据变化时的回调函数
            
        Returns:
            bool: 是否成功启动监听
        """
        try:
            # 连接到 NUT 服务器
            await self.connect()
            
            # 发送 LISTEN 命令
            response = await self._send_command(f"LISTEN {ups_name}")
            
            if not response.startswith("OK"):
                logger.warning(f"NUT LISTEN not supported: {response}")
                return False
            
            self._listen_mode = True
            self._on_data_changed = on_data_changed
            
            # 启动监听循环
            self._listen_task = asyncio.create_task(self._listen_loop(ups_name))
            
            # 启动心跳
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            logger.info(f"Started event-driven listening for UPS: {ups_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start event-driven mode: {e}")
            return False
    
    async def stop_listen(self):
        """停止监听"""
        self._listen_mode = False
        
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
        
        await self.disconnect()
        logger.info("Stopped event-driven listening")
    
    async def _listen_loop(self, ups_name: str):
        """监听循环，等待 DATACHANGED 通知"""
        try:
            while self._listen_mode:
                try:
                    line = await asyncio.wait_for(
                        self.reader.readline(),
                        timeout=60.0
                    )
                    
                    if not line:
                        logger.warning("NUT connection closed, attempting reconnect...")
                        await self._reconnect_and_relisten(ups_name)
                        continue
                    
                    message = line.decode().strip()
                    logger.debug(f"Event received: {message}")
                    
                    if message.startswith("DATACHANGED"):
                        logger.info(f"Data changed notification for {ups_name}")
                        if self._on_data_changed:
                            await self._on_data_changed()
                    elif message.startswith("DATASTALE"):
                        logger.warning(f"Data stale for {ups_name}")
                    
                except asyncio.TimeoutError:
                    logger.debug("Listen timeout, sending heartbeat...")
                    continue
                    
        except asyncio.CancelledError:
            logger.info("Listen loop cancelled")
        except Exception as e:
            logger.error(f"Listen loop error: {e}")
    
    async def _heartbeat_loop(self):
        """心跳循环，保持连接活跃"""
        try:
            while self._listen_mode:
                await asyncio.sleep(self._heartbeat_interval)
                try:
                    response = await self._send_command("VER")
                    self._last_heartbeat = datetime.now()
                    logger.debug(f"Heartbeat OK: {response}")
                except Exception as e:
                    logger.warning(f"Heartbeat failed: {e}")
                    self._listen_mode = False
        except asyncio.CancelledError:
            pass
    
    async def _reconnect_and_relisten(self, ups_name: str):
        """重连并重新监听"""
        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                delay = min(2 ** attempt, 30)
                logger.info(f"Reconnect attempt {attempt}/{max_retries}, waiting {delay}s...")
                await asyncio.sleep(delay)
                
                await self.connect()
                response = await self._send_command(f"LISTEN {ups_name}")
                
                if response.startswith("OK"):
                    logger.info("Reconnected and re-listening successfully")
                    return
                    
            except Exception as e:
                logger.error(f"Reconnect attempt {attempt} failed: {e}")
        
        logger.error("All reconnect attempts failed, stopping listen mode")
        self._listen_mode = False


class MockNutClient:
    """Mock NUT 客户端，用于开发测试"""
    
    def __init__(self, host: str, port: int, username: str, password: str, ups_name: str):
        self.ups_name = ups_name or "MockUPS"  # 空值使用默认名称
        self._connected = False
        self._mock_data = {
            "ups.status": "OL",  # OL = Online, OB = On Battery, LB = Low Battery
            "battery.charge": "100",
            "battery.runtime": "3600",
            "input.voltage": "220.0",
            "output.voltage": "220.0",
            "ups.load": "25",
            "ups.temperature": "25.0",
            "ups.model": "Mock UPS Model",
            "ups.mfr": "Mock Manufacturer",
            # 新增字段
            "ups.power.nominal": "1000",  # 额定 1000VA
            "ups.realpower": "250",  # 实际 250W
            "battery.voltage": "13.2",
            "battery.voltage.nominal": "12.0",
            "battery.temperature": "28.0",
            # Phase 1 扩展字段
            "input.frequency": "50.0",  # 输入频率 50Hz
            "output.frequency": "50.0",  # 输出频率 50Hz
            "output.current": "1.2",  # 输出电流 1.2A
            "output.current.nominal": "4.5",  # 额定电流 4.5A
            "ups.efficiency": "92.0",  # 效率 92%
            "battery.type": "PbAc",  # 铅酸电池
            "battery.date": "2022-03-15",  # 安装日期
            "battery.mfr.date": "2022-02-01",  # 生产日期
            "battery.packs": "1",  # 1组电池
            "battery.packs.bad": "0",  # 0组损坏
            # Phase 2 扩展字段 - 电压质量
            "input.voltage.minimum": "210.0",  # 最小输入电压
            "input.voltage.maximum": "230.0",  # 最大输入电压
            "input.transfer.low": "180.0",  # 低压转换阈值
            "input.transfer.high": "280.0",  # 高压转换阈值
            # Phase 2 扩展字段 - 环境监控
            "ambient.temperature": "24.0",  # 环境温度
            "ambient.humidity": "55.0",  # 环境湿度
            # Phase 3 扩展字段 - 自检和报警
            "ups.test.result": "Pass",  # 自检结果
            "ups.test.date": "2024-01-15",  # 自检日期
            "ups.alarm": "",  # 报警信息（空表示无报警）
            "ups.beeper.status": "enabled",  # 蜂鸣器状态
            # Phase 4 扩展字段 - 基于 APC Back-UPS BK650M2_CH 真实测试
            "ups.realpower.nominal": "390",  # 额定实际功率 390W
            "input.voltage.nominal": "220",  # 额定输入电压 220V
            "battery.charge.low": "90",  # 低电量阈值 90%
            "battery.runtime.low": "120",  # 低运行时间阈值 120秒
            "input.transfer.reason": "input voltage out of range",  # 转换原因
            "input.sensitivity": "low",  # 输入灵敏度
            "ups.serial": "9B2543A10629",  # UPS 序列号
            "ups.mfr.date": "2025/10/28",  # UPS 生产日期
            "ups.productid": "0002",  # USB 产品 ID
            "ups.vendorid": "051d",  # USB 厂商 ID
            # 电池充电器状态 (NUT 标准)
            "battery.charger.status": "floating",  # 充电器状态: charging/discharging/floating/resting
            # 可写变量
            "ups.delay.shutdown": "20",  # 关机延迟时间 (秒)
        }
        # 可写变量列表（用于 list_rw）
        self._mock_rw_vars = {
            "input.transfer.high": "278",
            "input.transfer.low": "160",
            "input.sensitivity": "low",
            "ups.delay.shutdown": "20",
            "battery.mfr.date": "2001/01/01",
        }
    
    async def connect(self):
        """连接（模拟）"""
        await asyncio.sleep(0.1)  # 模拟网络延迟
        self._connected = True

    async def disconnect(self):
        """断开连接（模拟）"""
        self._connected = False

    async def get_var(self, var_name: str) -> Optional[str]:
        """获取单个变量值（模拟）"""
        await asyncio.sleep(0.01)  # 模拟网络延迟
        return self._mock_data.get(var_name)
    
    async def list_vars(self) -> Dict[str, str]:
        """列出所有变量（模拟）"""
        await asyncio.sleep(0.05)
        return self._mock_data.copy()
    
    async def list_ups(self) -> list:
        """列出所有 UPS 设备（模拟）"""
        await asyncio.sleep(0.05)
        return [{"name": self.ups_name, "description": "Mock UPS Device"}]
    
    async def run_command(self, command: str) -> bool:
        """执行 UPS 命令（模拟）"""
        await asyncio.sleep(0.1)
        logger.info(f"[Mock] UPS command '{command}' executed")
        # 模拟蜂鸣器状态变化
        if command == "beeper.enable":
            self._mock_data["ups.beeper.status"] = "enabled"
        elif command == "beeper.disable":
            self._mock_data["ups.beeper.status"] = "disabled"
        elif command == "beeper.mute":
            self._mock_data["ups.beeper.status"] = "muted"
        return True
    
    async def set_var(self, var_name: str, value: str) -> bool:
        """设置变量（模拟）"""
        await asyncio.sleep(0.1)
        logger.info(f"[Mock] Set {var_name} = {value}")
        if var_name in self._mock_rw_vars:
            self._mock_rw_vars[var_name] = value
            # 同步更新 mock_data
            if var_name in self._mock_data:
                self._mock_data[var_name] = value
        return True
    
    async def list_rw(self) -> Dict[str, dict]:
        """列出可写变量（模拟）"""
        await asyncio.sleep(0.05)
        return {
            name: {"value": val, "writable": True}
            for name, val in self._mock_rw_vars.items()
        }
    
    # Mock 测试辅助方法
    def set_power_lost(self):
        """模拟断电"""
        self._mock_data["ups.status"] = "OB"

    def set_power_restored(self):
        """模拟恢复供电"""
        self._mock_data["ups.status"] = "OL"
        self._mock_data["battery.charge"] = "100"

    def set_low_battery(self, charge: int = 15):
        """模拟低电量"""
        self._mock_data["ups.status"] = "OB LB"
        self._mock_data["battery.charge"] = str(charge)

    def set_battery_charge(self, charge: int):
        """设置电池电量"""
        self._mock_data["battery.charge"] = str(charge)


def create_nut_client(host: str, port: int, username: str, password: str, 
                     ups_name: str, mock_mode: bool = False) -> NutClientInterface:
    """创建 NUT 客户端实例"""
    if mock_mode:
        return MockNutClient(host, port, username, password, ups_name)
    else:
        return RealNutClient(host, port, username, password, ups_name)
