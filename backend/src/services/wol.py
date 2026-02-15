"""Wake On LAN 服务"""
import socket
import logging
import asyncio
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from services.monitor import UpsMonitor

logger = logging.getLogger(__name__)


def create_magic_packet(mac_address: str) -> bytes:
    """
    创建 WOL 魔术包
    
    Args:
        mac_address: MAC 地址，格式如 "AA:BB:CC:DD:EE:FF" 或 "AABBCCDDEEFF"
    
    Returns:
        魔术包字节数组
    """
    # 移除分隔符，转为纯十六进制字符串
    mac_clean = mac_address.replace(":", "").replace("-", "").replace(".", "").upper()
    
    if len(mac_clean) != 12:
        raise ValueError(f"Invalid MAC address format: {mac_address}")
    
    try:
        # 将十六进制字符串转为字节
        mac_bytes = bytes.fromhex(mac_clean)
    except ValueError:
        raise ValueError(f"Invalid MAC address: {mac_address}")
    
    # 魔术包格式：6 bytes 0xFF + 16 次重复的 MAC 地址
    magic_packet = b'\xFF' * 6 + mac_bytes * 16
    
    return magic_packet


async def send_wol(
    mac_address: str, 
    broadcast_address: str = "255.255.255.255", 
    port: int = 9,
    retry_count: int = 3,
    retry_delay: float = 2.0
) -> bool:
    """
    发送 WOL 魔术包（带重试，UDP 协议不可靠）
    
    Args:
        mac_address: MAC 地址
        broadcast_address: 广播地址，默认 255.255.255.255
        port: UDP 端口，默认 9
        retry_count: 重试次数，默认 3 次（UDP 不可靠，需要多次发送）
        retry_delay: 重试间隔（秒），默认 2 秒
    
    Returns:
        是否发送成功
    """
    try:
        # 创建魔术包
        magic_packet = create_magic_packet(mac_address)
    except Exception as e:
        logger.error(f"Failed to create WOL magic packet for {mac_address}: {e}")
        return False
    
    # 多次发送 WOL 包以提高可靠性
    loop = asyncio.get_event_loop()
    success_count = 0
    
    for attempt in range(1, retry_count + 1):
        try:
            # 在线程池中执行 socket 操作（避免阻塞事件循环）
            await loop.run_in_executor(None, _send_packet, magic_packet, broadcast_address, port)
            success_count += 1
            logger.info(f"WOL packet sent to {mac_address} (attempt {attempt}/{retry_count})")
            
            # 如果不是最后一次，等待后再发送
            if attempt < retry_count:
                await asyncio.sleep(retry_delay)
        except Exception as e:
            logger.warning(f"Failed to send WOL packet (attempt {attempt}/{retry_count}): {e}")
    
    if success_count > 0:
        logger.info(f"WOL transmission completed: {success_count}/{retry_count} packets sent successfully to {mac_address}")
        return True
    else:
        logger.error(f"All {retry_count} WOL transmission attempts failed for {mac_address}")
        return False


def _send_packet(magic_packet: bytes, broadcast_address: str, port: int):
    """
    实际发送 UDP 包（同步函数）
    
    Args:
        magic_packet: 魔术包
        broadcast_address: 广播地址
        port: UDP 端口
    """
    # 创建 UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # 允许广播
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # 发送魔术包
        sock.sendto(magic_packet, (broadcast_address, port))
    finally:
        sock.close()


async def check_voltage_stable(
    monitor: Optional['UpsMonitor'],
    checks: int = 3,
    interval: int = 5,
    min_voltage: float = 190,
    max_voltage: float = 250
) -> bool:
    """
    检查输入电压是否稳定
    
    Args:
        monitor: UPS 监控器实例（用于读取 UPS 数据）
        checks: 连续检查次数，默认 3 次
        interval: 每次检查间隔（秒），默认 5 秒
        min_voltage: 最小可接受电压，默认 190V
        max_voltage: 最大可接受电压，默认 250V
    
    Returns:
        电压是否稳定（连续 checks 次都在正常范围内）
    """
    if not monitor:
        logger.warning("No monitor available for voltage check, assuming stable")
        return True
    
    stable_count = 0
    
    for i in range(checks):
        try:
            ups_data = await monitor.get_current_status()
            
            if ups_data and ups_data.input_voltage:
                voltage = ups_data.input_voltage
                
                if min_voltage <= voltage <= max_voltage:
                    stable_count += 1
                    logger.debug(f"Voltage check {i+1}/{checks}: {voltage}V - OK (stable count: {stable_count})")
                else:
                    stable_count = 0
                    logger.warning(f"Voltage check {i+1}/{checks}: {voltage}V - Out of range [{min_voltage}V-{max_voltage}V]")
            else:
                logger.warning(f"Voltage check {i+1}/{checks}: No voltage data available")
                stable_count = 0
        
        except Exception as e:
            logger.error(f"Error checking voltage: {e}")
            stable_count = 0
        
        # 如果还没完成所有检查，等待下一次检查
        if i < checks - 1:
            await asyncio.sleep(interval)
    
    is_stable = stable_count >= checks
    if not is_stable:
        logger.warning(f"Voltage not stable: only {stable_count}/{checks} checks passed")
    
    return is_stable


async def send_wol_to_devices(
    hooks_config: list,
    delay_seconds: int = 0,
    monitor: Optional['UpsMonitor'] = None,
    check_voltage_stability: bool = True,
    voltage_check_attempts: int = 3,
    voltage_check_interval: int = 5
) -> dict:
    """
    向所有配置了 MAC 地址的设备发送 WOL
    
    Args:
        hooks_config: Hook 配置列表
        delay_seconds: 延迟发送的秒数（全局延迟，用于网络稳定性）
        monitor: UPS 监控器实例（用于电压稳定性检查）
        check_voltage_stability: 是否检查电压稳定性，默认 True
        voltage_check_attempts: 电压检查次数，默认 3 次
        voltage_check_interval: 电压检查间隔（秒），默认 5 秒
    
    Returns:
        发送结果统计 {"sent": 2, "failed": 0, "skipped": 1, "voltage_stable": true}
    
    Note:
        延迟是全局的，所有设备在延迟后统一发送 WOL。
        这是为了确保网络和电源稳定后再唤醒设备。
        如果启用电压稳定性检查，会在延迟后检查电压是否稳定再发送 WOL。
    """
    if delay_seconds > 0:
        await asyncio.sleep(delay_seconds)
    
    result = {"sent": 0, "failed": 0, "skipped": 0, "voltage_stable": True}
    
    # 收集需要发送 WOL 的设备
    devices_to_wake = []
    for hook_config in hooks_config:
        if not hook_config.get("enabled", True):
            continue
        
        config = hook_config.get("config", {})
        mac_address = config.get("mac_address")
        
        if mac_address:
            devices_to_wake.append({
                "mac_address": mac_address,
                "broadcast_address": config.get("broadcast_address", "255.255.255.255")
            })
    
    # 检查电压稳定性
    if check_voltage_stability:
        voltage_stable = await check_voltage_stable(
            monitor,
            checks=voltage_check_attempts,
            interval=voltage_check_interval
        )
        result["voltage_stable"] = voltage_stable
        
        if not voltage_stable:
            logger.warning("Voltage not stable, skipping WOL transmission to protect devices")
            result["skipped"] = len(devices_to_wake)
            return result
    
    # 发送 WOL 到所有设备
    for device in devices_to_wake:
        success = await send_wol(device["mac_address"], device["broadcast_address"])
        
        if success:
            result["sent"] += 1
        else:
            result["failed"] += 1
    
    # 计算没有 MAC 地址的设备
    total_hooks = sum(1 for h in hooks_config if h.get("enabled", True))
    result["skipped"] = total_hooks - len(devices_to_wake)
    
    return result
