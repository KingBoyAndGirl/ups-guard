#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NUT UPS 参数测试脚本

此脚本用于测试 UPS 通过 NUT 协议提供的所有参数，
基于 NUT 官方 variables.txt 完整变量列表。

参考: https://github.com/networkupstools/nut/blob/master/docs/nut-names.txt

使用方法:
    python test_nut_parameters.py [--host HOST] [--port PORT] [--ups UPS_NAME]
    python test_nut_parameters.py --output report.md  # 输出到 Markdown 文件
    python test_nut_parameters.py --auto-filename     # 自动生成文件名并保存报告

默认连接: localhost:3493, UPS 名称: ups
"""

import asyncio
import argparse
import sys
import io
import os
from typing import Dict, Optional, Tuple, List
from datetime import datetime

# 设置标准输出为 UTF-8 编码
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# ============================================================================
# NUT 官方标准变量完整列表
# 来源: https://github.com/networkupstools/nut/blob/master/docs/nut-names.txt
# ============================================================================

NUT_ALL_VARIABLES = {
    # ========== device.* - 设备信息 ==========
    "device.mfr": "设备制造商",
    "device.model": "设备型号",
    "device.serial": "设备序列号",
    "device.type": "设备类型 (ups/pdu/scd/psu/ats)",
    "device.description": "设备描述",
    "device.contact": "联系人",
    "device.location": "设备位置",
    "device.part": "部件号",
    "device.macaddr": "MAC地址",
    "device.uptime": "设备运行时间(秒)",
    "device.count": "受管设备数量",

    # ========== ups.* - UPS 信息 ==========
    "ups.status": "UPS状态 (OL/OB/LB/HB/RB/CHRG/DISCHRG/BYPASS/CAL/OFF/OVER/TRIM/BOOST/FSD)",
    "ups.alarm": "UPS报警",
    "ups.time": "UPS内部时间",
    "ups.date": "UPS内部日期",
    "ups.model": "UPS型号",
    "ups.mfr": "UPS制造商",
    "ups.mfr.date": "UPS生产日期",
    "ups.serial": "UPS序列号",
    "ups.vendorid": "USB厂商ID",
    "ups.productid": "USB产品ID",
    "ups.firmware": "UPS固件版本",
    "ups.firmware.aux": "UPS辅助固件版本",
    "ups.temperature": "UPS温度(°C)",
    "ups.load": "UPS负载(%)",
    "ups.load.high": "高负载阈值(%)",
    "ups.id": "UPS标识符",
    "ups.delay.start": "启动延迟(秒)",
    "ups.delay.reboot": "重启延迟(秒)",
    "ups.delay.shutdown": "关机延迟(秒)",
    "ups.timer.start": "启动计时器(秒)",
    "ups.timer.reboot": "重启计时器(秒)",
    "ups.timer.shutdown": "关机计时器(秒)",
    "ups.test.interval": "自检间隔(秒)",
    "ups.test.result": "自检结果",
    "ups.test.date": "上次自检日期",
    "ups.display.language": "显示语言",
    "ups.contacts": "干接点状态",
    "ups.efficiency": "UPS效率(%)",
    "ups.power": "视在功率(VA)",
    "ups.power.nominal": "额定功率(VA)",
    "ups.realpower": "实际功率(W)",
    "ups.realpower.nominal": "额定实际功率(W)",
    "ups.beeper.status": "蜂鸣器状态",
    "ups.type": "UPS类型 (offline/line-int/online)",
    "ups.watchdog.status": "看门狗状态",
    "ups.start.auto": "自动启动",
    "ups.start.battery": "电池冷启动",
    "ups.start.reboot": "自动重启",
    "ups.shutdown": "关机类型",

    # ========== input.* - 输入电源 ==========
    "input.voltage": "输入电压(V)",
    "input.voltage.extended": "扩展输入电压",
    "input.voltage.fault": "故障输入电压(V)",
    "input.voltage.nominal": "额定输入电压(V)",
    "input.voltage.maximum": "最大输入电压(V)",
    "input.voltage.minimum": "最小输入电压(V)",
    "input.transfer.delay": "转换延迟(秒)",
    "input.transfer.reason": "转换原因",
    "input.transfer.low": "低压转换阈值(V)",
    "input.transfer.high": "高压转换阈值(V)",
    "input.transfer.low.min": "低压阈值最小值(V)",
    "input.transfer.low.max": "低压阈值最大值(V)",
    "input.transfer.high.min": "高压阈值最小值(V)",
    "input.transfer.high.max": "高压阈值最大值(V)",
    "input.transfer.boost.low": "升压低阈值(V)",
    "input.transfer.boost.high": "升压高阈值(V)",
    "input.transfer.trim.low": "降压低阈值(V)",
    "input.transfer.trim.high": "降压高阈值(V)",
    "input.sensitivity": "输入灵敏度",
    "input.quality": "电源质量",
    "input.current": "输入电流(A)",
    "input.current.nominal": "额定输入电流(A)",
    "input.current.status": "输入电流状态",
    "input.frequency": "输入频率(Hz)",
    "input.frequency.nominal": "额定输入频率(Hz)",
    "input.frequency.low": "最低输入频率(Hz)",
    "input.frequency.high": "最高输入频率(Hz)",
    "input.frequency.extended": "扩展输入频率",
    "input.frequency.status": "输入频率状态",
    "input.power": "输入功率(VA)",
    "input.realpower": "输入实际功率(W)",
    "input.phases": "输入相数",
    "input.source": "输入源",
    "input.source.preferred": "首选输入源",
    # 三相输入
    "input.L1.current": "L1相输入电流(A)",
    "input.L2.current": "L2相输入电流(A)",
    "input.L3.current": "L3相输入电流(A)",
    "input.L1.current.peak": "L1相峰值电流(A)",
    "input.L2.current.peak": "L2相峰值电流(A)",
    "input.L3.current.peak": "L3相峰值电流(A)",
    "input.L1.current.status": "L1相电流状态",
    "input.L2.current.status": "L2相电流状态",
    "input.L3.current.status": "L3相电流状态",
    "input.L1.voltage": "L1相输入电压(V)",
    "input.L2.voltage": "L2相输入电压(V)",
    "input.L3.voltage": "L3相输入电压(V)",
    "input.L1.voltage.status": "L1相电压状态",
    "input.L2.voltage.status": "L2相电压状态",
    "input.L3.voltage.status": "L3相电压状态",
    "input.L1-N.voltage": "L1-N电压(V)",
    "input.L2-N.voltage": "L2-N电压(V)",
    "input.L3-N.voltage": "L3-N电压(V)",
    "input.L1-L2.voltage": "L1-L2线电压(V)",
    "input.L2-L3.voltage": "L2-L3线电压(V)",
    "input.L3-L1.voltage": "L3-L1线电压(V)",
    "input.L1.frequency": "L1相频率(Hz)",
    "input.L2.frequency": "L2相频率(Hz)",
    "input.L3.frequency": "L3相频率(Hz)",
    "input.L1.power": "L1相功率(VA)",
    "input.L2.power": "L2相功率(VA)",
    "input.L3.power": "L3相功率(VA)",
    "input.L1.realpower": "L1相实际功率(W)",
    "input.L2.realpower": "L2相实际功率(W)",
    "input.L3.realpower": "L3相实际功率(W)",
    "input.L1.power.percent": "L1相功率百分比(%)",
    "input.L2.power.percent": "L2相功率百分比(%)",
    "input.L3.power.percent": "L3相功率百分比(%)",
    # 旁路输入
    "input.bypass.voltage": "旁路输入电压(V)",
    "input.bypass.current": "旁路输入电流(A)",
    "input.bypass.frequency": "旁路输入频率(Hz)",
    "input.bypass.phases": "旁路输入相数",
    "input.bypass.L1.voltage": "旁路L1相电压(V)",
    "input.bypass.L2.voltage": "旁路L2相电压(V)",
    "input.bypass.L3.voltage": "旁路L3相电压(V)",
    "input.bypass.L1.current": "旁路L1相电流(A)",
    "input.bypass.L2.current": "旁路L2相电流(A)",
    "input.bypass.L3.current": "旁路L3相电流(A)",
    "input.bypass.L1-N.voltage": "旁路L1-N电压(V)",
    "input.bypass.L2-N.voltage": "旁路L2-N电压(V)",
    "input.bypass.L3-N.voltage": "旁路L3-N电压(V)",

    # ========== output.* - 输出电源 ==========
    "output.voltage": "输出电压(V)",
    "output.voltage.nominal": "额定输出电压(V)",
    "output.frequency": "输出频率(Hz)",
    "output.frequency.nominal": "额定输出频率(Hz)",
    "output.current": "输出电流(A)",
    "output.current.nominal": "额定输出电流(A)",
    "output.power": "输出功率(VA)",
    "output.power.nominal": "额定输出功率(VA)",
    "output.realpower": "输出实际功率(W)",
    "output.realpower.nominal": "额定输出实际功率(W)",
    "output.phases": "输出相数",
    # 三相输出
    "output.L1.voltage": "L1相输出电压(V)",
    "output.L2.voltage": "L2相输出电压(V)",
    "output.L3.voltage": "L3相输出电压(V)",
    "output.L1-N.voltage": "L1-N输出电压(V)",
    "output.L2-N.voltage": "L2-N输出电压(V)",
    "output.L3-N.voltage": "L3-N输出电压(V)",
    "output.L1-L2.voltage": "L1-L2输出线电压(V)",
    "output.L2-L3.voltage": "L2-L3输出线电压(V)",
    "output.L3-L1.voltage": "L3-L1输出线电压(V)",
    "output.L1.current": "L1相输出电流(A)",
    "output.L2.current": "L2相输出电流(A)",
    "output.L3.current": "L3相输出电流(A)",
    "output.L1.current.peak": "L1相峰值输出电流(A)",
    "output.L2.current.peak": "L2相峰值输出电流(A)",
    "output.L3.current.peak": "L3相峰值输出电流(A)",
    "output.L1.power": "L1相输出功率(VA)",
    "output.L2.power": "L2相输出功率(VA)",
    "output.L3.power": "L3相输出功率(VA)",
    "output.L1.realpower": "L1相输出实际功率(W)",
    "output.L2.realpower": "L2相输出实际功率(W)",
    "output.L3.realpower": "L3相输出实际功率(W)",
    "output.L1.power.percent": "L1相功率百分比(%)",
    "output.L2.power.percent": "L2相功率百分比(%)",
    "output.L3.power.percent": "L3相功率百分比(%)",
    "output.L1.crestfactor": "L1相波峰因数",
    "output.L2.crestfactor": "L2相波峰因数",
    "output.L3.crestfactor": "L3相波峰因数",

    # ========== battery.* - 电池 ==========
    "battery.charge": "电池电量(%)",
    "battery.charge.low": "低电量阈值(%)",
    "battery.charge.warning": "警告电量阈值(%)",
    "battery.charge.restart": "重启电量阈值(%)",
    "battery.charger.status": "充电器状态",
    "battery.voltage": "电池电压(V)",
    "battery.voltage.nominal": "额定电池电压(V)",
    "battery.voltage.low": "电池低电压(V)",
    "battery.voltage.high": "电池高电压(V)",
    "battery.voltage.cell.min": "最小电芯电压(V)",
    "battery.voltage.cell.max": "最大电芯电压(V)",
    "battery.capacity": "电池容量(Ah)",
    "battery.current": "电池电流(A)",
    "battery.current.total": "电池总电流(A)",
    "battery.temperature": "电池温度(°C)",
    "battery.runtime": "剩余运行时间(秒)",
    "battery.runtime.low": "低运行时间阈值(秒)",
    "battery.runtime.restart": "重启运行时间阈值(秒)",
    "battery.alarm.threshold": "电池报警阈值",
    "battery.date": "电池安装日期",
    "battery.mfr.date": "电池生产日期",
    "battery.packs": "电池组数量",
    "battery.packs.bad": "损坏电池组数量",
    "battery.packs.external": "外部电池组数量",
    "battery.type": "电池类型",
    "battery.protection": "电池保护状态",
    "battery.energysave": "节能模式状态",
    "battery.energysave.delay": "节能延迟(秒)",
    "battery.energysave.load": "节能负载阈值(%)",
    "battery.energysave.realpower": "节能功率阈值(W)",

    # ========== ambient.* - 环境监控 ==========
    "ambient.temperature": "环境温度(°C)",
    "ambient.temperature.alarm": "温度报警",
    "ambient.temperature.alarm.enable": "温度报警使能",
    "ambient.temperature.high": "高温阈值(°C)",
    "ambient.temperature.high.warning": "高温警告阈值(°C)",
    "ambient.temperature.high.critical": "高温临界阈值(°C)",
    "ambient.temperature.low": "低温阈值(°C)",
    "ambient.temperature.low.warning": "低温警告阈值(°C)",
    "ambient.temperature.low.critical": "低温临界阈值(°C)",
    "ambient.humidity": "环境湿度(%)",
    "ambient.humidity.alarm": "湿度报警",
    "ambient.humidity.alarm.enable": "湿度报警使能",
    "ambient.humidity.high": "高湿阈值(%)",
    "ambient.humidity.high.warning": "高湿警告阈值(%)",
    "ambient.humidity.high.critical": "高湿临界阈值(%)",
    "ambient.humidity.low": "低湿阈值(%)",
    "ambient.humidity.low.warning": "低湿警告阈值(%)",
    "ambient.humidity.low.critical": "低湿临界阈值(%)",
    "ambient.present": "环境传感器存在",
    "ambient.1.temperature": "环境传感器1温度(°C)",
    "ambient.1.humidity": "环境传感器1湿度(%)",
    "ambient.2.temperature": "环境传感器2温度(°C)",
    "ambient.2.humidity": "环境传感器2湿度(%)",

    # ========== outlet.* - 可控插座/PDU ==========
    "outlet.id": "主插座ID",
    "outlet.desc": "主插座描述",
    "outlet.switch": "主插座开关状态",
    "outlet.switchable": "主插座是否可切换",
    "outlet.status": "主插座状态",
    "outlet.current": "主插座电流(A)",
    "outlet.current.maximum": "主插座最大电流(A)",
    "outlet.current.status": "主插座电流状态",
    "outlet.realpower": "主插座实际功率(W)",
    "outlet.voltage": "主插座电压(V)",
    "outlet.power": "主插座功率(VA)",
    "outlet.frequency": "主插座频率(Hz)",
    "outlet.powerfactor": "主插座功率因数",
    "outlet.crestfactor": "主插座波峰因数",
    "outlet.delay.shutdown": "主插座关机延迟(秒)",
    "outlet.delay.start": "主插座启动延迟(秒)",
    # 可扩展的编号插座 (outlet.1.*, outlet.2.*, ...)
    "outlet.group.count": "插座组数量",
    "outlet.count": "插座数量",

    # ========== driver.* - 驱动信息 ==========
    "driver.name": "驱动名称",
    "driver.version": "驱动版本",
    "driver.version.internal": "内部驱动版本",
    "driver.version.data": "数据版本",
    "driver.version.usb": "USB库版本",
    "driver.parameter.port": "驱动端口",
    "driver.parameter.pollfreq": "轮询频率",
    "driver.parameter.pollinterval": "轮询间隔",
    "driver.parameter.synchronous": "同步模式",
    "driver.parameter.vendorid": "厂商ID参数",
    "driver.parameter.productid": "产品ID参数",
    "driver.parameter.serial": "序列号参数",
    "driver.parameter.bus": "USB总线",
    "driver.parameter.product": "产品名称",
    "driver.parameter.vendor": "厂商名称",
    "driver.parameter.langid_fix": "语言ID修复",
    "driver.flag.allow_killpower": "允许killpower",
    "driver.debug": "调试级别",
    "driver.state": "驱动状态",

    # ========== server.* - NUT服务器信息 ==========
    "server.info": "服务器信息",
    "server.version": "服务器版本",

    # ========== bypass.* - 旁路 ==========
    "bypass.voltage": "旁路电压(V)",
    "bypass.voltage.nominal": "旁路额定电压(V)",
    "bypass.current": "旁路电流(A)",
    "bypass.current.nominal": "旁路额定电流(A)",
    "bypass.frequency": "旁路频率(Hz)",
    "bypass.frequency.nominal": "旁路额定频率(Hz)",
    "bypass.power": "旁路功率(VA)",
    "bypass.realpower": "旁路实际功率(W)",
    "bypass.phases": "旁路相数",
    "bypass.L1.voltage": "旁路L1相电压(V)",
    "bypass.L2.voltage": "旁路L2相电压(V)",
    "bypass.L3.voltage": "旁路L3相电压(V)",
    "bypass.L1.current": "旁路L1相电流(A)",
    "bypass.L2.current": "旁路L2相电流(A)",
    "bypass.L3.current": "旁路L3相电流(A)",

    # ========== experimental.* - 实验性 ==========
    "experimental.output.L1.crestfactor": "实验-L1波峰因数",
    "experimental.output.L2.crestfactor": "实验-L2波峰因数",
    "experimental.output.L3.crestfactor": "实验-L3波峰因数",
}

# 为带数字编号的变量添加模板 (outlet.1.*, outlet.2.*, ...)
OUTLET_NUMBERED_VARS = [
    "outlet.{n}.id",
    "outlet.{n}.desc",
    "outlet.{n}.switch",
    "outlet.{n}.switchable",
    "outlet.{n}.status",
    "outlet.{n}.alarm",
    "outlet.{n}.current",
    "outlet.{n}.current.maximum",
    "outlet.{n}.current.status",
    "outlet.{n}.realpower",
    "outlet.{n}.voltage",
    "outlet.{n}.power",
    "outlet.{n}.frequency",
    "outlet.{n}.powerfactor",
    "outlet.{n}.crestfactor",
    "outlet.{n}.delay.shutdown",
    "outlet.{n}.delay.start",
    "outlet.{n}.autoswitch.charge.low",
    "outlet.{n}.type",
    "outlet.{n}.load.off",
    "outlet.{n}.load.on",
]

# 扩展编号插座变量 (1-16)
for n in range(1, 17):
    for template in OUTLET_NUMBERED_VARS:
        var_name = template.format(n=n)
        desc = template.replace("{n}", f"{n}").replace("outlet.", "插座").replace(".", "-")
        NUT_ALL_VARIABLES[var_name] = f"插座{n}: {template.split('.')[-1]}"

# 项目中使用的 NUT 变量映射
# 格式: {NUT变量名: (字段名, 描述, 分类)}
PROJECT_NUT_VARIABLES = {
    # 核心状态
    "ups.status": ("status", "UPS 状态 (OL=在线, OB=电池, LB=低电)", "核心"),

    # 基础信息
    "ups.model": ("ups_model", "UPS 型号", "基础信息"),
    "ups.mfr": ("ups_manufacturer", "制造商", "基础信息"),

    # 电池相关
    "battery.charge": ("battery_charge", "电池电量 (%)", "电池"),
    "battery.runtime": ("battery_runtime", "剩余运行时间 (秒)", "电池"),
    "battery.voltage": ("battery_voltage", "电池电压 (V)", "电池"),
    "battery.voltage.nominal": ("battery_voltage_nominal", "电池额定电压 (V)", "电池"),
    "battery.temperature": ("battery_temperature", "电池温度 (°C)", "电池"),
    "battery.type": ("battery_type", "电池类型", "电池"),
    "battery.date": ("battery_date", "电池安装日期", "电池"),
    "battery.mfr.date": ("battery_mfr_date", "电池生产日期", "电池"),
    "battery.packs": ("battery_packs", "电池组数量", "电池"),
    "battery.packs.bad": ("battery_packs_bad", "损坏的电池组数量", "电池"),

    # 输入电源
    "input.voltage": ("input_voltage", "输入电压 (V)", "输入电源"),
    "input.frequency": ("input_frequency", "输入频率 (Hz)", "输入电源"),
    "input.voltage.minimum": ("input_voltage_min", "输入电压最小值 (V)", "输入电源"),
    "input.voltage.maximum": ("input_voltage_max", "输入电压最大值 (V)", "输入电源"),
    "input.transfer.low": ("input_transfer_low", "低压转换阈值 (V)", "输入电源"),
    "input.transfer.high": ("input_transfer_high", "高压转换阈值 (V)", "输入电源"),

    # 输出电源
    "output.voltage": ("output_voltage", "输出电压 (V)", "输出电源"),
    "output.frequency": ("output_frequency", "输出频率 (Hz)", "输出电源"),
    "output.current": ("output_current", "输出电流 (A)", "输出电源"),
    "output.current.nominal": ("output_current_nominal", "额定输出电流 (A)", "输出电源"),

    # 负载与功率
    "ups.load": ("load_percent", "负载百分比 (%)", "负载功率"),
    "ups.power.nominal": ("ups_power_nominal", "UPS 额定功率 (VA)", "负载功率"),
    "ups.realpower": ("ups_realpower", "实际功率 (W)", "负载功率"),
    "ups.efficiency": ("ups_efficiency", "UPS 效率 (%)", "负载功率"),

    # 温度
    "ups.temperature": ("temperature", "UPS 温度 (°C)", "温度"),

    # 环境监控
    "ambient.temperature": ("ambient_temperature", "环境温度 (°C)", "环境监控"),
    "ambient.humidity": ("ambient_humidity", "环境湿度 (%)", "环境监控"),
    "ambient.temperature.alarm": ("ambient_temperature_alarm", "温度报警", "环境监控"),
    "ambient.humidity.alarm": ("ambient_humidity_alarm", "湿度报警", "环境监控"),

    # 自检与报警
    "ups.test.result": ("ups_test_result", "自检结果", "自检报警"),
    "ups.test.date": ("ups_test_date", "上次自检时间", "自检报警"),
    "ups.alarm": ("ups_alarm", "当前报警信息", "自检报警"),
    "ups.beeper.status": ("ups_beeper_status", "蜂鸣器状态", "自检报警"),
}

def get_variable_category(var_name: str) -> str:
    """根据变量名前缀自动分类"""
    # 细粒度分类（先匹配更长的前缀）
    detailed_prefixes = {
        # 编号插座
        "outlet.group.": "插座组",
        # 三相输入
        "input.bypass.L": "旁路输入(三相)",
        "input.bypass.": "旁路输入",
        "input.L1-L2.": "输入L1-L2线",
        "input.L2-L3.": "输入L2-L3线",
        "input.L3-L1.": "输入L3-L1线",
        "input.L1-N.": "输入L1-N相",
        "input.L2-N.": "输入L2-N相",
        "input.L3-N.": "输入L3-N相",
        "input.L1.": "输入L1相",
        "input.L2.": "输入L2相",
        "input.L3.": "输入L3相",
        # 三相输出
        "output.L1-L2.": "输出L1-L2线",
        "output.L2-L3.": "输出L2-L3线",
        "output.L3-L1.": "输出L3-L1线",
        "output.L1-N.": "输出L1-N相",
        "output.L2-N.": "输出L2-N相",
        "output.L3-N.": "输出L3-N相",
        "output.L1.": "输出L1相",
        "output.L2.": "输出L2相",
        "output.L3.": "输出L3相",
        # 三相旁路
        "bypass.L1.": "旁路L1相",
        "bypass.L2.": "旁路L2相",
        "bypass.L3.": "旁路L3相",
        # 环境传感器编号
        "ambient.1.": "环境传感器1",
        "ambient.2.": "环境传感器2",
        # 驱动参数
        "driver.parameter.": "驱动参数",
        "driver.flag.": "驱动标志",
        "driver.version.": "驱动版本",
    }

    # 基础分类
    base_prefixes = {
        "device.": "设备信息",
        "ups.": "UPS信息",
        "battery.": "电池",
        "input.": "输入电源",
        "output.": "输出电源",
        "ambient.": "环境监控",
        "outlet.": "插座/PDU",
        "bypass.": "旁路",
        "driver.": "驱动信息",
        "server.": "服务器信息",
        "experimental.": "实验性",
    }

    # 先匹配更长的前缀
    for prefix in sorted(detailed_prefixes.keys(), key=len, reverse=True):
        if var_name.startswith(prefix):
            return detailed_prefixes[prefix]

    # 检查是否是编号插座 (outlet.1.*, outlet.2.*, ...)
    import re
    outlet_match = re.match(r'outlet\.(\d+)\.', var_name)
    if outlet_match:
        return f"插座{outlet_match.group(1)}"

    # 基础分类
    for prefix in sorted(base_prefixes.keys(), key=len, reverse=True):
        if var_name.startswith(prefix):
            return base_prefixes[prefix]

    return "其他"


class NutClient:
    """简单的 NUT 客户端"""

    def __init__(self, host: str = "localhost", port: int = 3493):
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

    async def connect(self) -> bool:
        """连接到 NUT 服务器"""
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=5.0
            )
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False

    async def close(self):
        """关闭连接"""
        if self.writer:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except:
                pass

    async def send_command(self, command: str) -> str:
        """发送命令并获取响应"""
        if not self.writer or not self.reader:
            return ""

        self.writer.write(f"{command}\n".encode())
        await self.writer.drain()

        response_lines = []
        while True:
            try:
                line = await asyncio.wait_for(self.reader.readline(), timeout=5.0)
                if not line:
                    break
                line_str = line.decode().strip()
                if line_str.startswith("END"):
                    break
                if line_str.startswith("ERR"):
                    return f"ERROR: {line_str}"
                response_lines.append(line_str)
            except asyncio.TimeoutError:
                break

        return "\n".join(response_lines)

    async def list_ups(self) -> List[str]:
        """列出所有 UPS"""
        response = await self.send_command("LIST UPS")
        ups_list = []
        for line in response.split("\n"):
            if line.startswith("UPS "):
                parts = line.split(" ", 2)
                if len(parts) >= 2:
                    ups_list.append(parts[1])
        return ups_list

    async def get_all_vars(self, ups_name: str) -> Dict[str, str]:
        """获取 UPS 的所有变量"""
        response = await self.send_command(f"LIST VAR {ups_name}")
        vars_dict = {}
        for line in response.split("\n"):
            if line.startswith("VAR "):
                # 格式: VAR ups_name var_name "value"
                parts = line.split(" ", 3)
                if len(parts) >= 4:
                    var_name = parts[2]
                    # 移除引号
                    value = parts[3].strip('"')
                    vars_dict[var_name] = value
        return vars_dict

    async def get_var(self, ups_name: str, var_name: str) -> Optional[str]:
        """获取单个变量"""
        response = await self.send_command(f"GET VAR {ups_name} {var_name}")
        if response.startswith("VAR "):
            parts = response.split(" ", 3)
            if len(parts) >= 4:
                return parts[3].strip('"')
        return None


# 全局变量，标记是否输出到 Markdown 文件
_output_markdown = False


def print_section(title: str, char: str = "=", level: int = 2):
    """打印分隔标题"""
    if _output_markdown:
        # Markdown 格式
        print(f"\n{'#' * level} {title}\n")
    else:
        # 控制台格式
        print(f"\n{char * 60}")
        print(f" {title}")
        print(f"{char * 60}")


def categorize_results(results: Dict[str, Tuple[bool, Optional[str]]], variables: Dict) -> Dict[str, List]:
    """按分类整理结果"""
    categories = {}
    for var_name, (available, value) in results.items():
        if var_name in variables:
            field_name, desc, category = variables[var_name]
            if category not in categories:
                categories[category] = []
            categories[category].append((var_name, field_name, desc, available, value))
    return categories


async def test_variables(client: NutClient, ups_name: str, variables: Dict) -> Dict[str, Tuple[bool, Optional[str]]]:
    """测试一组变量"""
    results = {}
    all_vars = await client.get_all_vars(ups_name)

    for var_name in variables:
        if var_name in all_vars:
            results[var_name] = (True, all_vars[var_name])
        else:
            results[var_name] = (False, None)

    return results


def print_results_table(categories: Dict[str, List], show_missing: bool = True):
    """打印结果表格"""
    available_count = 0
    missing_count = 0

    for category, items in sorted(categories.items()):
        print(f"\n📁 {category}:")
        print("-" * 55)

        for var_name, field_name, desc, available, value in items:
            if available:
                available_count += 1
                # 截断过长的值
                display_value = value if len(value) <= 30 else value[:27] + "..."
                print(f"  ✅ {var_name}")
                print(f"     └─ {desc}: {display_value}")
            else:
                missing_count += 1
                if show_missing:
                    print(f"  ❌ {var_name}")
                    print(f"     └─ {desc}: (不可用)")

    return available_count, missing_count


def get_default_output_dir() -> str:
    """获取默认输出目录（tools 目录下的 reports 文件夹）"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    reports_dir = os.path.join(script_dir, "reports")
    return reports_dir


async def main():
    parser = argparse.ArgumentParser(description="测试 NUT UPS 参数可用性")
    parser.add_argument("--host", default="localhost", help="NUT 服务器地址")
    parser.add_argument("--port", type=int, default=3493, help="NUT 服务器端口")
    parser.add_argument("--ups", default="ups", help="UPS 名称")
    parser.add_argument("--hide-missing", action="store_true", help="隐藏不可用的参数")
    parser.add_argument("--test-all", action="store_true", help="测试所有 NUT 标准变量 (约500+个)")
    parser.add_argument("--show-all-standard", action="store_true", help="显示所有 NUT 标准变量列表")
    parser.add_argument("--output", "-o", help="输出到 Markdown 文件")
    parser.add_argument("--auto-filename", "-a", action="store_true",
                        help="自动生成文件名并保存报告 (格式: ups-<品牌>-<型号>-<序列号>.md)")
    parser.add_argument("--output-dir", "-d", default=None,
                        help="输出目录 (配合 --auto-filename 使用，默认: ./reports)")
    args = parser.parse_args()

    # 如果使用自动文件名，需要先连接获取 UPS 信息
    if args.auto_filename:
        client = NutClient(args.host, args.port)
        if not await client.connect():
            print("❌ 无法连接到 NUT 服务器，无法自动生成文件名")
            return 1

        ups_list = await client.list_ups()
        ups_name = args.ups if args.ups in ups_list else (ups_list[0] if ups_list else None)
        if not ups_name:
            print("❌ 没有可用的 UPS 设备")
            await client.close()
            return 1

        all_vars = await client.get_all_vars(ups_name)
        await client.close()

        # 生成文件名：ups-<品牌>-<型号>-<序列号>.md
        ups_mfr = all_vars.get('ups.mfr', 'unknown')
        ups_model = all_vars.get('ups.model', 'unknown')
        ups_serial = all_vars.get('ups.serial', 'unknown')

        # 简化品牌名
        if 'American Power Conversion' in ups_mfr or 'APC' in ups_mfr.upper():
            brand = 'apc'
        elif 'CyberPower' in ups_mfr:
            brand = 'cyberpower'
        elif 'Eaton' in ups_mfr:
            brand = 'eaton'
        elif 'Schneider' in ups_mfr:
            brand = 'schneider'
        else:
            brand = ups_mfr.lower().replace(' ', '-')[:20]

        # 清理型号名（移除特殊字符）
        model_clean = ups_model.lower().replace(' ', '-').replace('_', '-')
        for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
            model_clean = model_clean.replace(char, '')

        filename = f"ups-{brand}-{model_clean}-{ups_serial}.md"

        # 确定输出目录
        output_dir = args.output_dir if args.output_dir else get_default_output_dir()

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        args.output = os.path.join(output_dir, filename)

    # 如果指定了输出文件，重定向输出
    output_file = None
    original_stdout = sys.stdout
    if args.output:
        # 确保输出目录存在
        output_dir = os.path.dirname(args.output)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        output_file = open(args.output, 'w', encoding='utf-8', newline='\n')
        sys.stdout = output_file
        # 打印生成信息到控制台
        original_stdout.write(f"📁 自动生成文件名: {args.output}\n")
        original_stdout.flush()

    try:
        return await _main_impl(args)
    finally:
        if output_file:
            output_file.close()
            # 恢复标准输出
            sys.stdout = original_stdout
            print(f"✅ 报告已保存到: {args.output}")


async def _main_impl(args):
    """主逻辑实现"""
    global _output_markdown
    _output_markdown = bool(args.output)

    # 显示所有标准变量列表
    if args.show_all_standard:
        print(f"\n📋 NUT 标准变量完整列表 (共 {len(NUT_ALL_VARIABLES)} 个):\n")
        categorized = {}
        for var_name, desc in NUT_ALL_VARIABLES.items():
            category = get_variable_category(var_name)
            if category not in categorized:
                categorized[category] = []
            categorized[category].append((var_name, desc))

        for category in sorted(categorized.keys()):
            items = categorized[category]
            print(f"\n📁 {category}: ({len(items)} 个)")
            print("-" * 60)
            for var_name, desc in sorted(items):
                print(f"  {var_name}")
                print(f"     └─ {desc}")
        return 0

    client = NutClient(args.host, args.port)

    if not await client.connect():
        print("\n❌ 无法连接到 NUT 服务器")
        print(f"   请确保 NUT 服务正在运行，并监听 {args.host}:{args.port}")
        return 1

    try:
        # 列出所有 UPS
        ups_list = await client.list_ups()

        ups_name = args.ups
        if args.ups not in ups_list:
            if ups_list:
                ups_name = ups_list[0]
            else:
                print("❌ 没有可用的 UPS 设备")
                return 1

        # 获取 UPS 提供的所有变量
        all_vars = await client.get_all_vars(ups_name)

        # 动态生成 UPS 名称：制造商简称 + UPS型号
        ups_mfr = all_vars.get('ups.mfr', '')
        ups_model = all_vars.get('ups.model', 'N/A')
        # 提取制造商简称
        mfr_abbr = ups_mfr
        if 'American Power Conversion' in ups_mfr or 'APC' in ups_mfr.upper():
            mfr_abbr = 'APC'
        elif 'CyberPower' in ups_mfr:
            mfr_abbr = 'CyberPower'
        elif 'Eaton' in ups_mfr:
            mfr_abbr = 'Eaton'
        elif 'Schneider' in ups_mfr:
            mfr_abbr = 'Schneider'
        elif 'Tripp' in ups_mfr:
            mfr_abbr = 'Tripp Lite'
        ups_full_name = f"{mfr_abbr} {ups_model}" if mfr_abbr else ups_model

        # 如果输出到文件，先生成 Markdown 报告头部
        if args.output:
            # 解析 UPS 状态
            ups_status = all_vars.get('ups.status', '')
            status_flags = ups_status.split()
            status_explanations = []
            status_flag_map = {
                'OL': '🟢 在线（市电供电）',
                'OB': '🔴 电池供电（市电断开）',
                'LB': '⚠️ 低电量',
                'HB': '🔋 高电量',
                'RB': '🔄 需要更换电池',
                'CHRG': '⚡ 充电中',
                'DISCHRG': '📉 放电中',
                'BYPASS': '🔀 旁路模式',
                'CAL': '📊 校准中',
                'OFF': '⭕ 关闭',
                'OVER': '🚨 过载',
                'TRIM': '📉 降压',
                'BOOST': '📈 升压',
                'FSD': '🛑 强制关机',
                'ALARM': '🚨 告警',
            }
            for flag in status_flags:
                if flag in status_flag_map:
                    status_explanations.append(f"  - **{flag}**: {status_flag_map[flag]}")

            # 计算运行时间显示
            runtime_sec = int(all_vars.get('battery.runtime', 0) or 0)
            runtime_min = runtime_sec // 60
            runtime_display = f"{runtime_min}分{runtime_sec % 60}秒" if runtime_sec else "N/A"

            # 状态解读文本
            status_text = '\n'.join(status_explanations) if status_explanations else '  - 状态正常'

            print(f"""# {ups_full_name} 参数测试报告

> 本报告由 `test_nut_parameters.py` 自动生成  
> 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
> NUT 驱动: {all_vars.get('driver.name', 'N/A')} {all_vars.get('driver.version', '')}

## 📊 测试概览

| 项目 | 数值 |
|------|------|
| UPS 名称 | {ups_full_name} |
| 制造商 | {ups_mfr} |
| 型号 | {ups_model} |
| 序列号 | {all_vars.get('ups.serial', 'N/A')} |
| 额定功率 | {all_vars.get('ups.realpower.nominal', 'N/A')}W |
| UPS 提供变量数 | {len(all_vars)} |
| NUT 标准变量库 | {len(NUT_ALL_VARIABLES)} |

---

## 📖 报告说明

### 图例说明

| 图标 | 含义 |
|:----:|------|
| 🔵 | **项目已使用** - 该变量已在 ups-guard 项目中使用 |
| 🆕 | **可添加** - 该变量 UPS 支持但项目尚未使用，可考虑添加 |
| ✅ | **可用** - NUT 标准变量在此 UPS 上可用 |
| ❌ | **不可用** - NUT 标准变量在此 UPS 上不支持 |

### 数据来源说明

本报告中的变量值分为两类：

1. **UPS 真实数据** ✅
   - 大部分变量（如 `battery.charge`, `input.voltage`, `ups.status` 等）是通过 USB HID 协议从 UPS 硬件实时读取的真实值
   - 这些值反映 UPS 的实际运行状态

2. **驱动配置覆盖** ⚙️
   - 以 `driver.parameter.override.*` 开头的变量是 NUT 驱动配置文件 (`ups.conf`) 中设置的覆盖值
   - 例如 `battery.charge.low` 和 `battery.runtime.low` 可能被覆盖以避免某些 UPS 的异常阈值导致误触发关机
   - `driver.flag.*` 和 `driver.parameter.*` 变量反映驱动配置，不是 UPS 硬件值

### 当前 UPS 状态解读

**状态码**: `{ups_status}`

{status_text}

**关键指标**:
- 输入电压: **{all_vars.get('input.voltage', 'N/A')}V** (额定 {all_vars.get('input.voltage.nominal', '220')}V)
- 电池电量: **{all_vars.get('battery.charge', 'N/A')}%**
- 电池电压: **{all_vars.get('battery.voltage', 'N/A')}V** (额定 {all_vars.get('battery.voltage.nominal', '12')}V)
- 剩余时间: **{runtime_display}**
- UPS 负载: **{all_vars.get('ups.load', 'N/A')}%**

---
""")
        else:
            # 控制台输出使用特殊字符框
            print(f"""
╔══════════════════════════════════════════════════════════╗
║         NUT UPS 参数测试脚本 - ups-guard         ║
╠══════════════════════════════════════════════════════════╣
║  测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<43} ║
║  UPS 名称: {ups_full_name:<45} ║
║  NUT标准变量库: {len(NUT_ALL_VARIABLES):<40} ║
╚══════════════════════════════════════════════════════════╝
""")

        if args.ups not in ups_list:
            if args.output:
                print(f"> ⚠️ 注意: 使用 UPS: `{ups_name}`\n")
            else:
                print(f"⚠️  警告: 指定的 UPS '{args.ups}' 不在列表中，使用: {ups_name}")


        # ============ 第一部分：UPS 实际提供的所有变量 ============
        print_section("UPS 实际提供的所有变量")

        # 按分类整理
        categorized_vars: Dict[str, List[Tuple[str, str, bool, str]]] = {}
        for var_name, value in all_vars.items():
            category = get_variable_category(var_name)
            if category not in categorized_vars:
                categorized_vars[category] = []
            in_project = var_name in PROJECT_NUT_VARIABLES
            # 获取标准描述
            standard_desc = NUT_ALL_VARIABLES.get(var_name, "")
            categorized_vars[category].append((var_name, value, in_project, standard_desc))

        # 打印各分类
        total_in_project = 0
        total_new = 0
        for category in sorted(categorized_vars.keys()):
            items = categorized_vars[category]
            if _output_markdown:
                print(f"\n### 📁 {category} ({len(items)} 个变量)\n")
                print("| 状态 | 变量名 | 值 | 描述 |")
                print("|:----:|--------|-----|------|")
                for var_name, value, in_project, standard_desc in sorted(items):
                    if in_project:
                        marker = "🔵"
                        total_in_project += 1
                    else:
                        marker = "🆕"
                        total_new += 1
                    display_value = value if len(str(value)) <= 30 else str(value)[:27] + "..."
                    desc = standard_desc if standard_desc else "-"
                    print(f"| {marker} | `{var_name}` | `{display_value}` | {desc} |")
            else:
                print(f"\n📁 {category}: ({len(items)} 个变量)")
                print("-" * 70)
                for var_name, value, in_project, standard_desc in sorted(items):
                    if in_project:
                        marker = "🔵"
                        total_in_project += 1
                    else:
                        marker = "🆕"
                        total_new += 1
                    display_value = value if len(str(value)) <= 35 else str(value)[:32] + "..."
                    print(f"  {marker} {var_name} = {display_value}")
                    if standard_desc:
                        print(f"     └─ {standard_desc}")

        if _output_markdown:
            print(f"\n> 📊 **UPS 提供的变量总数: {len(all_vars)}**  ")
            print(f"> 🔵 项目已使用: {total_in_project}  ")
            print(f"> 🆕 可添加到项目: {total_new}")
        else:
            print(f"\n📊 UPS 提供的变量总数: {len(all_vars)}")
            print(f"   🔵 项目已使用: {total_in_project}")
            print(f"   🆕 可添加到项目: {total_new}")

        # ============ 第二部分：测试 NUT 标准变量 ============
        if args.test_all:
            print_section("NUT 标准变量测试 (测试所有 {} 个标准变量)".format(len(NUT_ALL_VARIABLES)))

            # 按分类统计
            category_stats: Dict[str, Dict[str, int]] = {}
            available_standard = []
            missing_standard = []

            for var_name, desc in NUT_ALL_VARIABLES.items():
                category = get_variable_category(var_name)
                if category not in category_stats:
                    category_stats[category] = {"available": 0, "missing": 0}

                if var_name in all_vars:
                    category_stats[category]["available"] += 1
                    available_standard.append((var_name, all_vars[var_name], desc))
                else:
                    category_stats[category]["missing"] += 1
                    if not args.hide_missing:
                        missing_standard.append((var_name, desc))

            # 打印分类统计表
            if _output_markdown:
                print("\n### 📊 各分类支持情况\n")
                print("| 分类 | 可用 | 不可用 | 覆盖率 |")
                print("|------|-----:|-------:|-------:|")
                for category in sorted(category_stats.keys()):
                    stats = category_stats[category]
                    total = stats["available"] + stats["missing"]
                    rate = 100 * stats["available"] / total if total > 0 else 0
                    print(f"| {category} | {stats['available']} | {stats['missing']} | {rate:.1f}% |")
                total_available = sum(s["available"] for s in category_stats.values())
                total_missing = sum(s["missing"] for s in category_stats.values())
                total_rate = 100 * total_available / len(NUT_ALL_VARIABLES)
                print(f"| **总计** | **{total_available}** | **{total_missing}** | **{total_rate:.1f}%** |")
            else:
                print("\n📊 各分类支持情况:")
                print("-" * 70)
                print(f"{'分类':<20} {'可用':>8} {'不可用':>8} {'覆盖率':>10}")
                print("-" * 70)
                for category in sorted(category_stats.keys()):
                    stats = category_stats[category]
                    total = stats["available"] + stats["missing"]
                    rate = 100 * stats["available"] / total if total > 0 else 0
                    print(f"{category:<20} {stats['available']:>8} {stats['missing']:>8} {rate:>9.1f}%")
                total_available = sum(s["available"] for s in category_stats.values())
                total_missing = sum(s["missing"] for s in category_stats.values())
                total_rate = 100 * total_available / len(NUT_ALL_VARIABLES)
                print("-" * 70)
                print(f"{'总计':<20} {total_available:>8} {total_missing:>8} {total_rate:>9.1f}%")

            # 显示可用的标准变量
            if available_standard:
                if _output_markdown:
                    print(f"\n### ✅ 可用的 NUT 标准变量 ({len(available_standard)} 个)\n")
                    print("| 变量名 | 值 | 描述 |")
                    print("|--------|-----|------|")
                    for var_name, value, desc in sorted(available_standard):
                        display_value = value if len(str(value)) <= 25 else str(value)[:22] + "..."
                        print(f"| `{var_name}` | `{display_value}` | {desc or '-'} |")
                else:
                    print(f"\n✅ 可用的 NUT 标准变量 ({len(available_standard)} 个):")
                    for var_name, value, desc in sorted(available_standard):
                        display_value = value if len(str(value)) <= 30 else str(value)[:27] + "..."
                        print(f"  ✅ {var_name} = {display_value}")
                        if desc:
                            print(f"     └─ {desc}")

            # 显示不可用的标准变量（如果没有隐藏）
            if missing_standard and not args.hide_missing:
                if _output_markdown:
                    print(f"\n### ❌ 不可用的 NUT 标准变量 ({len(missing_standard)} 个)\n")
                    print("<details>")
                    print("<summary>点击展开查看不可用变量列表</summary>\n")
                    # 按分类分组显示
                    missing_by_cat: Dict[str, List] = {}
                    for var_name, desc in missing_standard:
                        cat = get_variable_category(var_name)
                        if cat not in missing_by_cat:
                            missing_by_cat[cat] = []
                        missing_by_cat[cat].append((var_name, desc))
                    for cat in sorted(missing_by_cat.keys()):
                        items = missing_by_cat[cat]
                        print(f"\n#### {cat} ({len(items)} 个不可用)\n")
                        print("| 变量名 | 描述 |")
                        print("|--------|------|")
                        for var_name, desc in sorted(items):
                            print(f"| `{var_name}` | {desc or '-'} |")
                    print("\n</details>")
                else:
                    print(f"\n❌ 不可用的 NUT 标准变量 ({len(missing_standard)} 个):")
                    missing_by_cat: Dict[str, List] = {}
                    for var_name, desc in missing_standard:
                        cat = get_variable_category(var_name)
                        if cat not in missing_by_cat:
                            missing_by_cat[cat] = []
                        missing_by_cat[cat].append((var_name, desc))
                    for cat in sorted(missing_by_cat.keys()):
                        items = missing_by_cat[cat]
                        print(f"\n  📁 {cat} ({len(items)} 个不可用):")
                        for var_name, desc in sorted(items)[:10]:
                            print(f"    ❌ {var_name}")
                            if desc:
                                print(f"       └─ {desc}")
                        if len(items) > 10:
                            print(f"    ... 还有 {len(items) - 10} 个")

        # ============ 第三部分：项目变量覆盖情况 ============
        print_section("项目变量覆盖情况")

        proj_available = 0
        proj_missing = 0
        proj_missing_list = []
        for var_name in PROJECT_NUT_VARIABLES:
            if var_name in all_vars:
                proj_available += 1
            else:
                proj_missing += 1
                proj_missing_list.append(var_name)

        if _output_markdown:
            print(f"\n| 指标 | 数值 |")
            print(f"|------|------|")
            print(f"| 项目定义变量 | {len(PROJECT_NUT_VARIABLES)} |")
            print(f"| ✅ 可用 | {proj_available} |")
            print(f"| ❌ 不可用 | {proj_missing} |")
            print(f"| 覆盖率 | {100*proj_available/len(PROJECT_NUT_VARIABLES):.1f}% |")

            if proj_missing > 0 and not args.hide_missing:
                print(f"\n#### ❌ 项目中不可用的变量\n")
                print("| 变量名 | 描述 |")
                print("|--------|------|")
                for var_name in proj_missing_list:
                    field_name, desc, category = PROJECT_NUT_VARIABLES[var_name]
                    print(f"| `{var_name}` | {desc} |")
        else:
            print(f"\n项目定义的变量: {len(PROJECT_NUT_VARIABLES)} 个")
            print(f"  ✅ 可用: {proj_available}")
            print(f"  ❌ 不可用: {proj_missing}")
            print(f"  覆盖率: {100*proj_available/len(PROJECT_NUT_VARIABLES):.1f}%")

            if proj_missing > 0 and not args.hide_missing:
                print("\n❌ 项目中不可用的变量:")
                for var_name in proj_missing_list:
                    field_name, desc, category = PROJECT_NUT_VARIABLES[var_name]
                    print(f"  ❌ {var_name} ({desc})")

        # ============ 总结 ============
        print_section("测试总结", "═", level=2)

        if _output_markdown:
            # 识别被覆盖的变量
            overridden_vars = []
            for var_name in all_vars:
                if 'override' in var_name.lower() or var_name.startswith('driver.parameter.'):
                    overridden_vars.append(var_name)

            print(f"""
| 项目 | 数值 |
|------|------|
| UPS 名称 | {ups_full_name} |
| 制造商 | {all_vars.get('ups.mfr', 'N/A')} |
| 型号 | {ups_model} |
| 驱动 | {all_vars.get('driver.name', 'N/A')} |
| UPS 提供变量数 | {len(all_vars)} |
| NUT 标准变量库 | {len(NUT_ALL_VARIABLES)} |
| 项目变量覆盖率 | {proj_available}/{len(PROJECT_NUT_VARIABLES)} ({100*proj_available/len(PROJECT_NUT_VARIABLES):.1f}%) |

---

## ⚙️ entrypoint.sh 配置覆盖说明

以下变量的值受到 NUT 驱动配置 (`ups.conf` / `entrypoint.sh`) 的影响，**不是 UPS 硬件的原始值**：

### 阈值覆盖变量（4个）

这些变量被 `entrypoint.sh` 通过 `override.*` 配置覆盖，目的是避免某些 UPS（如 APC）报告异常阈值导致误触发关机：

| 变量名 | 当前值 | 来源 | 说明 |
|--------|--------|------|------|
| `battery.charge.low` | {all_vars.get('battery.charge.low', 'N/A')} | ⚙️ entrypoint.sh | 低电量阈值(%)，由 `BATTERY_CHARGE_LOW` 环境变量设置 |
| `battery.runtime.low` | {all_vars.get('battery.runtime.low', 'N/A')} | ⚙️ entrypoint.sh | 低运行时间阈值(秒)，由 `BATTERY_RUNTIME_LOW` 环境变量设置 |
| `driver.parameter.override.battery.charge.low` | {all_vars.get('driver.parameter.override.battery.charge.low', 'N/A')} | ⚙️ entrypoint.sh | 记录覆盖值的驱动参数 |
| `driver.parameter.override.battery.runtime.low` | {all_vars.get('driver.parameter.override.battery.runtime.low', 'N/A')} | ⚙️ entrypoint.sh | 记录覆盖值的驱动参数 |

### 驱动配置变量（4个）

这些变量由 `entrypoint.sh` 在生成 `ups.conf` 时设置：

| 变量名 | 当前值 | 来源 | 说明 |
|--------|--------|------|------|
| `driver.flag.ignorelb` | {all_vars.get('driver.flag.ignorelb', 'N/A')} | ⚙️ entrypoint.sh | 忽略 UPS 硬件 LB 信号，使用软件阈值判断 |
| `driver.parameter.pollinterval` | {all_vars.get('driver.parameter.pollinterval', 'N/A')} | ⚙️ entrypoint.sh | USB 轮询间隔，减少通信压力 |
| `driver.parameter.subdriver` | {all_vars.get('driver.parameter.subdriver', 'N/A')} | ⚙️ entrypoint.sh | APC 专用子驱动配置 |
| `driver.parameter.vendorid` | {all_vars.get('driver.parameter.vendorid', 'N/A')} | ⚙️ entrypoint.sh | 从 nut-scanner 提取后写入配置 |

### 其他驱动参数

| 变量名 | 当前值 | 说明 |
|--------|--------|------|
| `driver.parameter.productid` | {all_vars.get('driver.parameter.productid', 'N/A')} | USB 产品 ID |
| `driver.parameter.port` | {all_vars.get('driver.parameter.port', 'N/A')} | 驱动端口 |
| `driver.parameter.pollfreq` | {all_vars.get('driver.parameter.pollfreq', 'N/A')} | 完整轮询频率 |
| `driver.parameter.synchronous` | {all_vars.get('driver.parameter.synchronous', 'N/A')} | 同步模式 |

> 💡 **提示**: 如果需要查看 UPS 的原始硬件阈值，可以临时移除 `ups.conf` 中的 `override.*` 和 `ignorelb` 配置后重新测试。
>
> ⚠️ **注意**: 原厂 `battery.charge.low` 可能是 **95%**，这会导致电量一低于 95% 就触发关机，因此需要覆盖为合理值（如 20%）。

---

## 📚 参考资料

- [NUT 官方变量文档](https://networkupstools.org/docs/developer-guide.chunked/apas01.html)
- [NUT 变量命名规范 (nut-names.txt)](https://github.com/networkupstools/nut/blob/master/docs/nut-names.txt)
- [ups-guard 项目](https://github.com/your-repo/ups-guard)

---

*报告生成完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
""")
        else:
            print(f"""
  UPS 名称: {ups_full_name}
  制造商:   {all_vars.get('ups.mfr', 'N/A')}
  型号:     {ups_model}
  驱动:     {all_vars.get('driver.name', 'N/A')}
  
  UPS 提供变量数: {len(all_vars)}
  NUT 标准变量库: {len(NUT_ALL_VARIABLES)} 个变量
  项目变量覆盖率: {proj_available}/{len(PROJECT_NUT_VARIABLES)} ({100*proj_available/len(PROJECT_NUT_VARIABLES):.1f}%)
""")

            print("\n💡 提示:")
            print("  --test-all          测试所有 NUT 标准变量")
            print("  --show-all-standard 显示完整 NUT 标准变量列表")
            print("  --hide-missing      隐藏不可用的变量")
            print("  --auto-filename     自动生成文件名并保存报告")
            print("  --output FILE       输出到指定的 Markdown 文件")

        return 0

    finally:
        await client.close()


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(1)

