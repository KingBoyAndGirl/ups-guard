"""apcupsd 异步客户端 - 通过 NIS 协议与 apcupsd 通信"""
import asyncio
import logging
from typing import Dict, Optional, Protocol
from datetime import datetime

logger = logging.getLogger(__name__)


# apcupsd KEY -> NUT 变量名映射
APCUPSD_TO_NUT_MAP = {
    "STATUS": "ups.status",
    "LINEV": "input.voltage",
    "OUTPUTV": "output.voltage",
    "LOADPCT": "ups.load",
    "BCHARGE": "battery.charge",
    "TIMELEFT": "battery.runtime",  # 分钟 -> 秒
    "BATTV": "battery.voltage",
    "NOMPOWER": "ups.realpower.nominal",
    "NOMINV": "input.voltage.nominal",
    "NOMBATTV": "battery.voltage.nominal",
    "BATTDATE": "battery.date",
    "LOTRANS": "input.transfer.low",
    "HITRANS": "input.transfer.high",
    "SENSE": "input.sensitivity",
    "LASTXFER": "input.transfer.reason",
    "NUMXFERS": "ups.transfer.count",
    "TONBATT": "ups.time.on_battery",
    "CUMONBATT": "ups.cumulative.on_battery",
    "SELFTEST": "ups.test.result",
    "ITEMP": "ups.temperature",
    "ALARMDEL": "ups.alarm.delay",
    "MODEL": "device.model",
    "SERIALNO": "device.serial",
    "FIRMWARE": "driver.version",
    "MFR": "device.mfr",
    "VERSION": "apcupsd.version",
    "STARTTIME": "ups.starttime",
    "MBATTCHG": "battery.charge.low",
    "MINTIMEL": "battery.runtime.low",
    "MAXTIME": "ups.max.time",
    "CABLE": "ups.cable.type",
    "DRIVER": "ups.driver.type",
    "UPSMODE": "ups.mode",
}

# apcupsd STATUS -> NUT status 映射
STATUS_MAP = {
    "ONLINE": "OL",
    "ONBATT": "OB",
    "LOWBATT": "LB",
    "CHARGING": "CHRG",
    "ONLINE BOOST": "OL BOOST",
    "ONLINE TRIM": "OL TRIM",
    "COMMLOST": "OFF",
}


class ApcupsdClient:
    """apcupsd NIS 协议异步客户端"""

    def __init__(self, host: str, port: int = 3551):
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_delay = 60
        self._last_connection_error: Optional[str] = None
        self._raw_data: Dict[str, str] = {}  # 原始 apcupsd 数据

    async def connect(self) -> None:
        """连接到 apcupsd NIS 服务器"""
        try:
            logger.info(f"Connecting to apcupsd at {self.host}:{self.port}...")
            self.reader, self.writer = await asyncio.open_connection(
                self.host, self.port
            )
            self._connected = True
            self._reconnect_attempts = 0
            self._last_connection_error = None
            logger.info("Successfully connected to apcupsd")
        except Exception as e:
            error_msg = f"Failed to connect to apcupsd: {e}"
            logger.error(error_msg)
            self._connected = False
            self._last_connection_error = error_msg
            raise

    async def disconnect(self) -> None:
        """断开连接"""
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                logger.error(f"Error disconnecting from apcupsd: {e}")
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
            "backend": "apcupsd",
        }

    async def _reconnect(self) -> bool:
        """自动重连（指数退避）"""
        self._reconnect_attempts += 1

        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
            self.writer = None
            self.reader = None

        delay = min(2 ** (self._reconnect_attempts - 1), self._max_reconnect_delay)
        logger.warning(
            f"Attempting to reconnect to apcupsd "
            f"(attempt {self._reconnect_attempts}, waiting {delay}s)..."
        )
        await asyncio.sleep(delay)

        try:
            await self.connect()
            # 验证连接
            data = await self._fetch_status()
            if data:
                logger.info("Reconnection successful")
                return True
            else:
                self._connected = False
                return False
        except Exception as e:
            logger.error(
                f"Reconnection attempt {self._reconnect_attempts} failed: {e}"
            )
            return False

    async def _fetch_status(self, timeout: float = 10.0) -> Dict[str, str]:
        """获取 apcupsd 状态数据"""
        if not self._connected:
            if not await self._reconnect():
                raise RuntimeError("Not connected to apcupsd and reconnection failed")

        try:
            self.writer.write(b"status\n")
            await self.writer.drain()

            data: Dict[str, str] = {}
            while True:
                line = await asyncio.wait_for(
                    self.reader.readline(), timeout=timeout
                )
                if not line:
                    break

                line_str = line.decode("utf-8", errors="replace").strip()

                if line_str.startswith("END APC"):
                    break
                if not line_str or line_str.startswith("BEGIN APC"):
                    continue

                # 解析 KEY : VALUE 格式
                if " : " in line_str:
                    key, value = line_str.split(" : ", 1)
                    data[key.strip()] = value.strip()
                elif ":" in line_str:
                    key, value = line_str.split(":", 1)
                    data[key.strip()] = value.strip()

            self._raw_data = data
            return data

        except asyncio.TimeoutError:
            logger.error("Timeout reading from apcupsd")
            self._connected = False
            raise
        except Exception as e:
            logger.error(f"Error fetching apcupsd status: {e}")
            self._connected = False
            raise

    async def get_var(self, var_name: str) -> Optional[str]:
        """获取单个变量值（使用 NUT 风格的变量名）"""
        try:
            data = await self._fetch_status()
            # 先尝试 NUT -> apcupsd 反向映射
            nut_to_apc = {v: k for k, v in APCUPSD_TO_NUT_MAP.items()}
            apc_key = nut_to_apc.get(var_name)
            if apc_key and apc_key in data:
                value = data[apc_key]
                # 特殊处理：TIMELEFT 分钟 -> 秒
                if apc_key == "TIMELEFT":
                    return str(int(float(value.replace(" Minutes", "")) * 60))
                # 特殊处理：LOADPCT 去掉 %
                if apc_key == "LOADPCT":
                    return value.replace(" Percent", "").replace("%", "")
                # 特殊处理：BCHARGE 去掉 %
                if apc_key == "BCHARGE":
                    return value.replace(" Percent", "").replace("%", "")
                return value

            # 尝试直接匹配（可能是 apc_ 前缀的原始 key）
            if var_name.startswith("apc_"):
                raw_key = var_name[4:].upper()
                return data.get(raw_key)

            return data.get(var_name)
        except Exception as e:
            logger.error(f"Error getting variable {var_name}: {e}")
            self._connected = False
            return None

    async def list_vars(self) -> Dict[str, str]:
        """列出所有变量（返回 NUT 风格的 key + 原始 apc_ key）"""
        try:
            raw_data = await self._fetch_status()

            if not raw_data:
                logger.warning("No data received from apcupsd")
                self._connected = False
                return {}

            # 构建统一格式的变量字典
            vars_dict: Dict[str, str] = {}

            for apc_key, value in raw_data.items():
                # 保存原始 key（加 apc_ 前缀）
                vars_dict[f"apc_{apc_key.lower()}"] = value

                # 映射到 NUT 风格 key
                nut_key = APCUPSD_TO_NUT_MAP.get(apc_key)
                if nut_key:
                    processed = self._process_value(apc_key, value)
                    vars_dict[nut_key] = processed

            return vars_dict

        except Exception as e:
            logger.error(f"Error listing variables: {e}")
            self._connected = False
            return {}

    def _process_value(self, apc_key: str, value: str) -> str:
        """处理 apcupsd 值，转换为 NUT 兼容格式"""
        # 去掉单位后缀
        value = value.strip()

        if apc_key == "STATUS":
            return STATUS_MAP.get(value, value)
        elif apc_key in ("BCHARGE", "LOADPCT"):
            return value.replace(" Percent", "").replace("%", "").strip()
        elif apc_key == "TIMELEFT":
            minutes = value.replace(" Minutes", "").strip()
            try:
                return str(int(float(minutes) * 60))
            except ValueError:
                return minutes
        elif apc_key == "TONBATT" or apc_key == "CUMONBATT":
            return value.replace(" Seconds", "").strip()
        elif apc_key in ("LINEV", "OUTPUTV", "BATTV", "LOTRANS", "HITRANS",
                         "NOMINV", "NOMBATTV"):
            return value.replace(" Volts", "").strip()
        elif apc_key == "NOMPOWER":
            return value.replace(" Watts", "").strip()
        elif apc_key == "ITEMP":
            return value.replace(" C", "").strip()
        elif apc_key == "NUMXFERS":
            return value.strip()
        elif apc_key == "MBATTCHG" or apc_key == "MINTIMEL":
            return value.replace(" Percent", "").replace(" Minutes", "").strip()
        elif apc_key == "MAXTIME":
            return value.replace(" Seconds", "").strip()

        return value

    async def list_ups(self) -> list:
        """列出 UPS 设备（apcupsd 只管理一个 UPS）"""
        try:
            data = await self._fetch_status()
            model = data.get("MODEL", "Unknown UPS")
            serial = data.get("SERIALNO", "")
            return [{"name": "ups", "description": f"{model} ({serial})"}]
        except Exception as e:
            logger.error(f"Error listing UPS: {e}")
            return []

    async def run_command(self, command: str) -> bool:
        """执行 UPS 命令（apcupsd NIS 不支持即时命令）"""
        logger.warning(
            f"apcupsd NIS protocol does not support instant commands: {command}"
        )
        return False

    async def set_var(self, var_name: str, value: str) -> bool:
        """设置 UPS 变量（apcupsd NIS 不支持远程设置）"""
        logger.warning(
            f"apcupsd NIS protocol does not support remote variable setting: {var_name}={value}"
        )
        return False

    async def list_rw(self) -> Dict[str, dict]:
        """列出可写变量（apcupsd NIS 不支持）"""
        return {}

    async def list_commands(self) -> list[str]:
        """列出支持的命令（apcupsd NIS 不支持）"""
        return []


def create_ups_client(
    backend: str,
    host: str,
    port: int,
    username: str = "",
    password: str = "",
    ups_name: str = "",
    mock_mode: bool = False,
):
    """创建 UPS 客户端工厂函数"""
    if mock_mode:
        from services.nut_client import MockNutClient
        return MockNutClient(host, port, username, password, ups_name)
    elif backend == "apcupsd":
        return ApcupsdClient(host, port)
    else:
        from services.nut_client import RealNutClient
        return RealNutClient(host, port, username, password, ups_name)
