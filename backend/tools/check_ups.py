#!/usr/bin/env python3
"""
UPS 状态检查脚本

用于诊断 UPS 连接状态和数据获取问题
"""
import asyncio
import sys
import os

# 添加父目录到 path 以支持导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_nut_parameters import NutClient

async def main():
    c = NutClient()

    print("=" * 50)
    print("  UPS 状态诊断工具")
    print("=" * 50)
    print()

    print("=== 步骤 1: 连接 NUT 服务器 ===")
    connected = await c.connect()
    if not connected:
        print("❌ 无法连接到 NUT 服务器 (localhost:3493)")
        print()
        print("可能原因:")
        print("  1. NUT 容器未运行")
        print("  2. 端口 3493 未映射")
        print()
        print("解决方案:")
        print("  docker restart ups-guard-nut")
        return

    print("✅ NUT 服务器连接正常")
    print()

    print("=== 步骤 2: 查询 UPS 设备列表 ===")
    ups_list = await c.list_ups()
    print(f"📋 发现的 UPS: {ups_list}")

    if not ups_list:
        print()
        print("❌ 没有发现任何 UPS 设备")
        print()
        print("可能原因:")
        print("  1. UPS USB 线断开")
        print("  2. UPS 电源关闭（电池耗尽）")
        print("  3. USB 设备未传递到容器")
        print()
        print("解决方案:")
        print("  1. 检查 UPS 的 USB 线是否连接")
        print("  2. 接通 UPS 的市电电源")
        print("  3. 重启 NUT 容器: docker restart ups-guard-nut")
        await c.close()
        return

    print()

    print("=== 步骤 3: 获取 UPS 变量 ===")
    ups_name = ups_list[0]
    print(f"📡 正在查询 UPS: {ups_name}")

    v = await c.get_all_vars(ups_name)

    if not v:
        print()
        print("❌ 无法获取 UPS 变量")
        print()
        print("可能原因:")
        print("  1. UPS 驱动程序失去与设备的通信")
        print("  2. UPS 电池耗尽后关机")
        print("  3. USB 通信中断")
        print()
        print("解决方案:")
        print("  1. 接通 UPS 市电电源")
        print("  2. 等待 30 秒让 UPS 启动")
        print("  3. 重启 NUT 容器: docker restart ups-guard-nut")
        await c.close()
        return

    print(f"✅ 获取到 {len(v)} 个变量")
    print()

    print("=== UPS 状态分析 ===")
    status = v.get('ups.status', 'N/A')
    alarm = v.get('ups.alarm', '')
    print(f"ups.status: {status}")
    if alarm:
        print(f"ups.alarm: ⚠️ {alarm}")
    else:
        print(f"ups.alarm: 无报警")

    # 状态解析
    print()
    print("状态解析:")
    # 将状态字符串分割为独立的状态标志
    status_flags = status.split()

    # NUT UPS 状态标志完整列表
    # 参考: https://networkupstools.org/docs/developer-guide.chunked/ar01s04.html
    status_map = {
        'OL':      ('✅', 'OL - Online (市电供电)'),
        'OB':      ('⚠️', 'OB - On Battery (电池供电)'),
        'LB':      ('🔴', 'LB - Low Battery (低电量)'),
        'HB':      ('🟢', 'HB - High Battery (高电量)'),
        'RB':      ('🔧', 'RB - Replace Battery (需更换电池)'),
        'CHRG':    ('🔋', 'CHRG - Charging (正在充电)'),
        'DISCHRG': ('📉', 'DISCHRG - Discharging (正在放电)'),
        'BYPASS':  ('🔀', 'BYPASS - 旁路模式'),
        'CAL':     ('🔧', 'CAL - Calibrating (校准中)'),
        'OFF':     ('⭕', 'OFF - UPS 关闭'),
        'OVER':    ('🚨', 'OVER - Overload (过载)'),
        'TRIM':    ('📉', 'TRIM - 降压调节 (输入电压过高)'),
        'BOOST':   ('📈', 'BOOST - 升压调节 (输入电压过低)'),
        'FSD':     ('🛑', 'FSD - Forced Shutdown (强制关机中)'),
        'ALARM':   ('🚨', 'ALARM - 有报警'),
    }

    found_status = False
    for flag in status_flags:
        if flag in status_map:
            icon, desc = status_map[flag]
            print(f"  {icon} {desc}")
            found_status = True
        elif flag:  # 未知状态
            print(f"  ❓ {flag} - 未知状态")
            found_status = True

    if not found_status:
        print("  ❓ 无法解析状态")

    print()
    print("=== 电池状态 ===")
    charge = v.get('battery.charge', 'N/A')
    runtime = v.get('battery.runtime', 'N/A')
    voltage = v.get('battery.voltage', 'N/A')
    voltage_nom = v.get('battery.voltage.nominal', 'N/A')
    charge_low = v.get('battery.charge.low', 'N/A')

    print(f"battery.charge: {charge}%")
    print(f"battery.runtime: {runtime} 秒")
    print(f"battery.voltage: {voltage} V (额定: {voltage_nom} V)")
    print(f"battery.charge.low: {charge_low}% (低电量阈值)")

    # 电池状态分析
    try:
        charge_val = float(charge) if charge != 'N/A' else None
        charge_low_val = float(charge_low) if charge_low != 'N/A' else None

        if charge_val is not None and charge_low_val is not None:
            if charge_low_val > 50:
                print()
                print(f"⚠️ 警告: 低电量阈值设置过高 ({charge_low_val}%)")
                print("   建议设置为 20-30%")
    except:
        pass

    print()
    print("=== 电源状态 ===")
    input_v = v.get('input.voltage', 'N/A')
    load = v.get('ups.load', 'N/A')
    print(f"input.voltage: {input_v} V")
    print(f"ups.load: {load}%")

    # 电源状态分析
    try:
        input_val = float(input_v) if input_v != 'N/A' else None
        if input_val is not None and input_val < 1:
            print()
            print("🔴 警告: 市电电压为 0，UPS 未接通市电！")
            print("   请检查 UPS 的电源线是否插好")
    except:
        pass

    print()
    print("=" * 50)
    await c.close()

if __name__ == "__main__":
    asyncio.run(main())

