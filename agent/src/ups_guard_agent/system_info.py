"""系统信息收集"""
import logging
import platform
import socket
import uuid
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def _get_mac_by_target_ip(target_ip: str) -> Optional[str]:
    """
    根据目标 IP 获取对应网卡的 MAC 地址。

    通过创建一个到目标 IP 的 UDP socket（不实际发送数据），
    然后根据 socket 绑定的本地 IP 找到对应的网卡 MAC 地址。
    """
    try:
        import psutil

        # 获取本机连接到目标的 IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((target_ip, 80))
        local_ip = s.getsockname()[0]
        s.close()

        # 遍历所有网卡，找到匹配这个 IP 的网卡
        for iface_name, addrs in psutil.net_if_addrs().items():
            has_target_ip = False
            mac_addr = None

            for addr in addrs:
                # 检查是否有我们要的 IPv4 地址
                if addr.family == socket.AF_INET and addr.address == local_ip:
                    has_target_ip = True
                # 获取 MAC 地址（family 值因平台而异）
                # Windows: -1 (psutil.AF_LINK 不存在), Linux/Mac: AF_PACKET/AF_LINK
                if addr.family in (-1, 17, 18):  # -1=Windows, 17=AF_PACKET(Linux), 18=AF_LINK(Mac)
                    mac_addr = addr.address

            if has_target_ip and mac_addr:
                # 标准化 MAC 地址格式（大写，冒号分隔）
                mac_addr = mac_addr.upper().replace("-", ":")
                logger.debug(f"Found MAC {mac_addr} for IP {local_ip} on interface {iface_name}")
                return mac_addr

        logger.debug(f"Could not find MAC for IP {local_ip}")
        return None
    except Exception as e:
        logger.debug(f"Failed to get MAC by target IP: {e}")
        return None


def get_mac_address() -> str:
    """
    获取 MAC 地址。

    优先获取连接到外网（8.8.8.8）的网卡 MAC 地址，
    这样能保证即使机器有多个网卡，也始终返回同一个稳定的 MAC 地址。
    如果失败，则回退到 uuid.getnode() 方式。
    """
    # 方法1：获取连接到外网的网卡 MAC
    mac = _get_mac_by_target_ip("8.8.8.8")
    if mac:
        return mac

    # 方法2：回退到 uuid.getnode()
    logger.debug("Falling back to uuid.getnode() for MAC address")
    mac_int = uuid.getnode()
    return ":".join(f"{(mac_int >> (i * 8)) & 0xFF:02X}" for i in reversed(range(6)))


def get_local_ip() -> str:
    """获取本机局域网 IP（UDP connect 方式）"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_system_info() -> Dict[str, Any]:
    """获取完整系统信息（注册时发送）"""
    try:
        import psutil
        memory_total_gb = round(psutil.virtual_memory().total / (1024 ** 3), 2)
    except Exception as e:
        logger.warning(f"Failed to get memory info: {e}")
        memory_total_gb = 0.0

    info = {
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "os_version": platform.version(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "mac_address": get_mac_address(),
        "ip_address": get_local_ip(),
        "memory_total_gb": memory_total_gb,
    }
    logger.info(
        f"System info: hostname={info['hostname']} os={info['os']} "
        f"ip={info['ip_address']} memory_gb={info['memory_total_gb']}"
    )
    return info


def get_runtime_info() -> Dict[str, Any]:
    """获取运行时信息（心跳时发送）"""
    try:
        import psutil
        boot_time = psutil.boot_time()
        import time
        uptime = int(time.time() - boot_time)
        cpu_percent = psutil.cpu_percent(interval=None)
        memory_percent = psutil.virtual_memory().percent
    except Exception as e:
        logger.warning(f"Failed to get runtime info: {e}")
        uptime = 0
        cpu_percent = 0.0
        memory_percent = 0.0

    info = {
        "uptime": uptime,
        "cpu_percent": cpu_percent,
        "memory_percent": memory_percent,
    }
    logger.debug(f"Runtime info: uptime={uptime}s cpu={cpu_percent}% memory={memory_percent}%")
    return info
