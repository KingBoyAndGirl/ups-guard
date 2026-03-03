"""系统信息收集"""
import platform
import socket
import uuid
from typing import Dict, Any


def get_mac_address() -> str:
    """获取 MAC 地址"""
    mac = uuid.getnode()
    return ":".join(f"{(mac >> (i * 8)) & 0xFF:02X}" for i in reversed(range(6)))


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
    except Exception:
        memory_total_gb = 0.0

    return {
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "os_version": platform.version(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "mac_address": get_mac_address(),
        "ip_address": get_local_ip(),
        "memory_total_gb": memory_total_gb,
    }


def get_runtime_info() -> Dict[str, Any]:
    """获取运行时信息（心跳时发送）"""
    try:
        import psutil
        boot_time = psutil.boot_time()
        import time
        uptime = int(time.time() - boot_time)
        cpu_percent = psutil.cpu_percent(interval=None)
        memory_percent = psutil.virtual_memory().percent
    except Exception:
        uptime = 0
        cpu_percent = 0.0
        memory_percent = 0.0

    return {
        "uptime": uptime,
        "cpu_percent": cpu_percent,
        "memory_percent": memory_percent,
    }
