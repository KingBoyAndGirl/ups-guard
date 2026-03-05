# N/A 参数测试报告

> 本报告由 `test_nut_parameters.py` 自动生成  
> 测试时间: 2026-03-05 19:48:20  
> NUT 驱动: N/A 

## 📊 测试概览

| 项目 | 数值 |
|------|------|
| UPS 名称 | N/A |
| 制造商 |  |
| 型号 | N/A |
| 序列号 | N/A |
| 额定功率 | N/AW |
| UPS 提供变量数 | 0 |
| NUT 标准变量库 | 614 |

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

**状态码**: ``

  - 状态正常

**关键指标**:
- 输入电压: **N/AV** (额定 220V)
- 电池电量: **N/A%**
- 电池电压: **N/AV** (额定 12V)
- 剩余时间: **N/A**
- UPS 负载: **N/A%**

---

> ⚠️ 注意: 使用 UPS: `Wali_8888`


## UPS 实际提供的所有变量


> 📊 **UPS 提供的变量总数: 0**  
> 🔵 项目已使用: 0  
> 🆕 可添加到项目: 0

## NUT 标准变量测试 (测试所有 614 个标准变量)


### 📊 各分类支持情况

| 分类 | 可用 | 不可用 | 覆盖率 |
|------|-----:|-------:|-------:|
| UPS信息 | 0 | 39 | 0.0% |
| 实验性 | 0 | 3 | 0.0% |
| 插座/PDU | 0 | 17 | 0.0% |
| 插座1 | 0 | 21 | 0.0% |
| 插座10 | 0 | 21 | 0.0% |
| 插座11 | 0 | 21 | 0.0% |
| 插座12 | 0 | 21 | 0.0% |
| 插座13 | 0 | 21 | 0.0% |
| 插座14 | 0 | 21 | 0.0% |
| 插座15 | 0 | 21 | 0.0% |
| 插座16 | 0 | 21 | 0.0% |
| 插座2 | 0 | 21 | 0.0% |
| 插座3 | 0 | 21 | 0.0% |
| 插座4 | 0 | 21 | 0.0% |
| 插座5 | 0 | 21 | 0.0% |
| 插座6 | 0 | 21 | 0.0% |
| 插座7 | 0 | 21 | 0.0% |
| 插座8 | 0 | 21 | 0.0% |
| 插座9 | 0 | 21 | 0.0% |
| 插座组 | 0 | 1 | 0.0% |
| 旁路 | 0 | 9 | 0.0% |
| 旁路L1相 | 0 | 2 | 0.0% |
| 旁路L2相 | 0 | 2 | 0.0% |
| 旁路L3相 | 0 | 2 | 0.0% |
| 旁路输入 | 0 | 4 | 0.0% |
| 旁路输入(三相) | 0 | 9 | 0.0% |
| 服务器信息 | 0 | 2 | 0.0% |
| 环境传感器1 | 0 | 2 | 0.0% |
| 环境传感器2 | 0 | 2 | 0.0% |
| 环境监控 | 0 | 19 | 0.0% |
| 电池 | 0 | 30 | 0.0% |
| 设备信息 | 0 | 11 | 0.0% |
| 输入L1-L2线 | 0 | 1 | 0.0% |
| 输入L1-N相 | 0 | 1 | 0.0% |
| 输入L1相 | 0 | 9 | 0.0% |
| 输入L2-L3线 | 0 | 1 | 0.0% |
| 输入L2-N相 | 0 | 1 | 0.0% |
| 输入L2相 | 0 | 9 | 0.0% |
| 输入L3-L1线 | 0 | 1 | 0.0% |
| 输入L3-N相 | 0 | 1 | 0.0% |
| 输入L3相 | 0 | 9 | 0.0% |
| 输入电源 | 0 | 34 | 0.0% |
| 输出L1-L2线 | 0 | 1 | 0.0% |
| 输出L1-N相 | 0 | 1 | 0.0% |
| 输出L1相 | 0 | 7 | 0.0% |
| 输出L2-L3线 | 0 | 1 | 0.0% |
| 输出L2-N相 | 0 | 1 | 0.0% |
| 输出L2相 | 0 | 7 | 0.0% |
| 输出L3-L1线 | 0 | 1 | 0.0% |
| 输出L3-N相 | 0 | 1 | 0.0% |
| 输出L3相 | 0 | 7 | 0.0% |
| 输出电源 | 0 | 11 | 0.0% |
| 驱动信息 | 0 | 4 | 0.0% |
| 驱动参数 | 0 | 11 | 0.0% |
| 驱动标志 | 0 | 1 | 0.0% |
| 驱动版本 | 0 | 3 | 0.0% |
| **总计** | **0** | **614** | **0.0%** |

### ❌ 不可用的 NUT 标准变量 (614 个)

<details>
<summary>点击展开查看不可用变量列表</summary>


#### UPS信息 (39 个不可用)

| 变量名 | 描述 |
|--------|------|
| `ups.alarm` | UPS报警 |
| `ups.beeper.status` | 蜂鸣器状态 |
| `ups.contacts` | 干接点状态 |
| `ups.date` | UPS内部日期 |
| `ups.delay.reboot` | 重启延迟(秒) |
| `ups.delay.shutdown` | 关机延迟(秒) |
| `ups.delay.start` | 启动延迟(秒) |
| `ups.display.language` | 显示语言 |
| `ups.efficiency` | UPS效率(%) |
| `ups.firmware` | UPS固件版本 |
| `ups.firmware.aux` | UPS辅助固件版本 |
| `ups.id` | UPS标识符 |
| `ups.load` | UPS负载(%) |
| `ups.load.high` | 高负载阈值(%) |
| `ups.mfr` | UPS制造商 |
| `ups.mfr.date` | UPS生产日期 |
| `ups.model` | UPS型号 |
| `ups.power` | 视在功率(VA) |
| `ups.power.nominal` | 额定功率(VA) |
| `ups.productid` | USB产品ID |
| `ups.realpower` | 实际功率(W) |
| `ups.realpower.nominal` | 额定实际功率(W) |
| `ups.serial` | UPS序列号 |
| `ups.shutdown` | 关机类型 |
| `ups.start.auto` | 自动启动 |
| `ups.start.battery` | 电池冷启动 |
| `ups.start.reboot` | 自动重启 |
| `ups.status` | UPS状态 (OL/OB/LB/HB/RB/CHRG/DISCHRG/BYPASS/CAL/OFF/OVER/TRIM/BOOST/FSD) |
| `ups.temperature` | UPS温度(°C) |
| `ups.test.date` | 上次自检日期 |
| `ups.test.interval` | 自检间隔(秒) |
| `ups.test.result` | 自检结果 |
| `ups.time` | UPS内部时间 |
| `ups.timer.reboot` | 重启计时器(秒) |
| `ups.timer.shutdown` | 关机计时器(秒) |
| `ups.timer.start` | 启动计时器(秒) |
| `ups.type` | UPS类型 (offline/line-int/online) |
| `ups.vendorid` | USB厂商ID |
| `ups.watchdog.status` | 看门狗状态 |

#### 实验性 (3 个不可用)

| 变量名 | 描述 |
|--------|------|
| `experimental.output.L1.crestfactor` | 实验-L1波峰因数 |
| `experimental.output.L2.crestfactor` | 实验-L2波峰因数 |
| `experimental.output.L3.crestfactor` | 实验-L3波峰因数 |

#### 插座/PDU (17 个不可用)

| 变量名 | 描述 |
|--------|------|
| `outlet.count` | 插座数量 |
| `outlet.crestfactor` | 主插座波峰因数 |
| `outlet.current` | 主插座电流(A) |
| `outlet.current.maximum` | 主插座最大电流(A) |
| `outlet.current.status` | 主插座电流状态 |
| `outlet.delay.shutdown` | 主插座关机延迟(秒) |
| `outlet.delay.start` | 主插座启动延迟(秒) |
| `outlet.desc` | 主插座描述 |
| `outlet.frequency` | 主插座频率(Hz) |
| `outlet.id` | 主插座ID |
| `outlet.power` | 主插座功率(VA) |
| `outlet.powerfactor` | 主插座功率因数 |
| `outlet.realpower` | 主插座实际功率(W) |
| `outlet.status` | 主插座状态 |
| `outlet.switch` | 主插座开关状态 |
| `outlet.switchable` | 主插座是否可切换 |
| `outlet.voltage` | 主插座电压(V) |

#### 插座1 (21 个不可用)

| 变量名 | 描述 |
|--------|------|
| `outlet.1.alarm` | 插座1: alarm |
| `outlet.1.autoswitch.charge.low` | 插座1: low |
| `outlet.1.crestfactor` | 插座1: crestfactor |
| `outlet.1.current` | 插座1: current |
| `outlet.1.current.maximum` | 插座1: maximum |
| `outlet.1.current.status` | 插座1: status |
| `outlet.1.delay.shutdown` | 插座1: shutdown |
| `outlet.1.delay.start` | 插座1: start |
| `outlet.1.desc` | 插座1: desc |
| `outlet.1.frequency` | 插座1: frequency |
| `outlet.1.id` | 插座1: id |
| `outlet.1.load.off` | 插座1: off |
| `outlet.1.load.on` | 插座1: on |
| `outlet.1.power` | 插座1: power |
| `outlet.1.powerfactor` | 插座1: powerfactor |
| `outlet.1.realpower` | 插座1: realpower |
| `outlet.1.status` | 插座1: status |
| `outlet.1.switch` | 插座1: switch |
| `outlet.1.switchable` | 插座1: switchable |
| `outlet.1.type` | 插座1: type |
| `outlet.1.voltage` | 插座1: voltage |

#### 插座10 (21 个不可用)

| 变量名 | 描述 |
|--------|------|
| `outlet.10.alarm` | 插座10: alarm |
| `outlet.10.autoswitch.charge.low` | 插座10: low |
| `outlet.10.crestfactor` | 插座10: crestfactor |
| `outlet.10.current` | 插座10: current |
| `outlet.10.current.maximum` | 插座10: maximum |
| `outlet.10.current.status` | 插座10: status |
| `outlet.10.delay.shutdown` | 插座10: shutdown |
| `outlet.10.delay.start` | 插座10: start |
| `outlet.10.desc` | 插座10: desc |
| `outlet.10.frequency` | 插座10: frequency |
| `outlet.10.id` | 插座10: id |
| `outlet.10.load.off` | 插座10: off |
| `outlet.10.load.on` | 插座10: on |
| `outlet.10.power` | 插座10: power |
| `outlet.10.powerfactor` | 插座10: powerfactor |
| `outlet.10.realpower` | 插座10: realpower |
| `outlet.10.status` | 插座10: status |
| `outlet.10.switch` | 插座10: switch |
| `outlet.10.switchable` | 插座10: switchable |
| `outlet.10.type` | 插座10: type |
| `outlet.10.voltage` | 插座10: voltage |

#### 插座11 (21 个不可用)

| 变量名 | 描述 |
|--------|------|
| `outlet.11.alarm` | 插座11: alarm |
| `outlet.11.autoswitch.charge.low` | 插座11: low |
| `outlet.11.crestfactor` | 插座11: crestfactor |
| `outlet.11.current` | 插座11: current |
| `outlet.11.current.maximum` | 插座11: maximum |
| `outlet.11.current.status` | 插座11: status |
| `outlet.11.delay.shutdown` | 插座11: shutdown |
| `outlet.11.delay.start` | 插座11: start |
| `outlet.11.desc` | 插座11: desc |
| `outlet.11.frequency` | 插座11: frequency |
| `outlet.11.id` | 插座11: id |
| `outlet.11.load.off` | 插座11: off |
| `outlet.11.load.on` | 插座11: on |
| `outlet.11.power` | 插座11: power |
| `outlet.11.powerfactor` | 插座11: powerfactor |
| `outlet.11.realpower` | 插座11: realpower |
| `outlet.11.status` | 插座11: status |
| `outlet.11.switch` | 插座11: switch |
| `outlet.11.switchable` | 插座11: switchable |
| `outlet.11.type` | 插座11: type |
| `outlet.11.voltage` | 插座11: voltage |

#### 插座12 (21 个不可用)

| 变量名 | 描述 |
|--------|------|
| `outlet.12.alarm` | 插座12: alarm |
| `outlet.12.autoswitch.charge.low` | 插座12: low |
| `outlet.12.crestfactor` | 插座12: crestfactor |
| `outlet.12.current` | 插座12: current |
| `outlet.12.current.maximum` | 插座12: maximum |
| `outlet.12.current.status` | 插座12: status |
| `outlet.12.delay.shutdown` | 插座12: shutdown |
| `outlet.12.delay.start` | 插座12: start |
| `outlet.12.desc` | 插座12: desc |
| `outlet.12.frequency` | 插座12: frequency |
| `outlet.12.id` | 插座12: id |
| `outlet.12.load.off` | 插座12: off |
| `outlet.12.load.on` | 插座12: on |
| `outlet.12.power` | 插座12: power |
| `outlet.12.powerfactor` | 插座12: powerfactor |
| `outlet.12.realpower` | 插座12: realpower |
| `outlet.12.status` | 插座12: status |
| `outlet.12.switch` | 插座12: switch |
| `outlet.12.switchable` | 插座12: switchable |
| `outlet.12.type` | 插座12: type |
| `outlet.12.voltage` | 插座12: voltage |

#### 插座13 (21 个不可用)

| 变量名 | 描述 |
|--------|------|
| `outlet.13.alarm` | 插座13: alarm |
| `outlet.13.autoswitch.charge.low` | 插座13: low |
| `outlet.13.crestfactor` | 插座13: crestfactor |
| `outlet.13.current` | 插座13: current |
| `outlet.13.current.maximum` | 插座13: maximum |
| `outlet.13.current.status` | 插座13: status |
| `outlet.13.delay.shutdown` | 插座13: shutdown |
| `outlet.13.delay.start` | 插座13: start |
| `outlet.13.desc` | 插座13: desc |
| `outlet.13.frequency` | 插座13: frequency |
| `outlet.13.id` | 插座13: id |
| `outlet.13.load.off` | 插座13: off |
| `outlet.13.load.on` | 插座13: on |
| `outlet.13.power` | 插座13: power |
| `outlet.13.powerfactor` | 插座13: powerfactor |
| `outlet.13.realpower` | 插座13: realpower |
| `outlet.13.status` | 插座13: status |
| `outlet.13.switch` | 插座13: switch |
| `outlet.13.switchable` | 插座13: switchable |
| `outlet.13.type` | 插座13: type |
| `outlet.13.voltage` | 插座13: voltage |

#### 插座14 (21 个不可用)

| 变量名 | 描述 |
|--------|------|
| `outlet.14.alarm` | 插座14: alarm |
| `outlet.14.autoswitch.charge.low` | 插座14: low |
| `outlet.14.crestfactor` | 插座14: crestfactor |
| `outlet.14.current` | 插座14: current |
| `outlet.14.current.maximum` | 插座14: maximum |
| `outlet.14.current.status` | 插座14: status |
| `outlet.14.delay.shutdown` | 插座14: shutdown |
| `outlet.14.delay.start` | 插座14: start |
| `outlet.14.desc` | 插座14: desc |
| `outlet.14.frequency` | 插座14: frequency |
| `outlet.14.id` | 插座14: id |
| `outlet.14.load.off` | 插座14: off |
| `outlet.14.load.on` | 插座14: on |
| `outlet.14.power` | 插座14: power |
| `outlet.14.powerfactor` | 插座14: powerfactor |
| `outlet.14.realpower` | 插座14: realpower |
| `outlet.14.status` | 插座14: status |
| `outlet.14.switch` | 插座14: switch |
| `outlet.14.switchable` | 插座14: switchable |
| `outlet.14.type` | 插座14: type |
| `outlet.14.voltage` | 插座14: voltage |

#### 插座15 (21 个不可用)

| 变量名 | 描述 |
|--------|------|
| `outlet.15.alarm` | 插座15: alarm |
| `outlet.15.autoswitch.charge.low` | 插座15: low |
| `outlet.15.crestfactor` | 插座15: crestfactor |
| `outlet.15.current` | 插座15: current |
| `outlet.15.current.maximum` | 插座15: maximum |
| `outlet.15.current.status` | 插座15: status |
| `outlet.15.delay.shutdown` | 插座15: shutdown |
| `outlet.15.delay.start` | 插座15: start |
| `outlet.15.desc` | 插座15: desc |
| `outlet.15.frequency` | 插座15: frequency |
| `outlet.15.id` | 插座15: id |
| `outlet.15.load.off` | 插座15: off |
| `outlet.15.load.on` | 插座15: on |
| `outlet.15.power` | 插座15: power |
| `outlet.15.powerfactor` | 插座15: powerfactor |
| `outlet.15.realpower` | 插座15: realpower |
| `outlet.15.status` | 插座15: status |
| `outlet.15.switch` | 插座15: switch |
| `outlet.15.switchable` | 插座15: switchable |
| `outlet.15.type` | 插座15: type |
| `outlet.15.voltage` | 插座15: voltage |

#### 插座16 (21 个不可用)

| 变量名 | 描述 |
|--------|------|
| `outlet.16.alarm` | 插座16: alarm |
| `outlet.16.autoswitch.charge.low` | 插座16: low |
| `outlet.16.crestfactor` | 插座16: crestfactor |
| `outlet.16.current` | 插座16: current |
| `outlet.16.current.maximum` | 插座16: maximum |
| `outlet.16.current.status` | 插座16: status |
| `outlet.16.delay.shutdown` | 插座16: shutdown |
| `outlet.16.delay.start` | 插座16: start |
| `outlet.16.desc` | 插座16: desc |
| `outlet.16.frequency` | 插座16: frequency |
| `outlet.16.id` | 插座16: id |
| `outlet.16.load.off` | 插座16: off |
| `outlet.16.load.on` | 插座16: on |
| `outlet.16.power` | 插座16: power |
| `outlet.16.powerfactor` | 插座16: powerfactor |
| `outlet.16.realpower` | 插座16: realpower |
| `outlet.16.status` | 插座16: status |
| `outlet.16.switch` | 插座16: switch |
| `outlet.16.switchable` | 插座16: switchable |
| `outlet.16.type` | 插座16: type |
| `outlet.16.voltage` | 插座16: voltage |

#### 插座2 (21 个不可用)

| 变量名 | 描述 |
|--------|------|
| `outlet.2.alarm` | 插座2: alarm |
| `outlet.2.autoswitch.charge.low` | 插座2: low |
| `outlet.2.crestfactor` | 插座2: crestfactor |
| `outlet.2.current` | 插座2: current |
| `outlet.2.current.maximum` | 插座2: maximum |
| `outlet.2.current.status` | 插座2: status |
| `outlet.2.delay.shutdown` | 插座2: shutdown |
| `outlet.2.delay.start` | 插座2: start |
| `outlet.2.desc` | 插座2: desc |
| `outlet.2.frequency` | 插座2: frequency |
| `outlet.2.id` | 插座2: id |
| `outlet.2.load.off` | 插座2: off |
| `outlet.2.load.on` | 插座2: on |
| `outlet.2.power` | 插座2: power |
| `outlet.2.powerfactor` | 插座2: powerfactor |
| `outlet.2.realpower` | 插座2: realpower |
| `outlet.2.status` | 插座2: status |
| `outlet.2.switch` | 插座2: switch |
| `outlet.2.switchable` | 插座2: switchable |
| `outlet.2.type` | 插座2: type |
| `outlet.2.voltage` | 插座2: voltage |

#### 插座3 (21 个不可用)

| 变量名 | 描述 |
|--------|------|
| `outlet.3.alarm` | 插座3: alarm |
| `outlet.3.autoswitch.charge.low` | 插座3: low |
| `outlet.3.crestfactor` | 插座3: crestfactor |
| `outlet.3.current` | 插座3: current |
| `outlet.3.current.maximum` | 插座3: maximum |
| `outlet.3.current.status` | 插座3: status |
| `outlet.3.delay.shutdown` | 插座3: shutdown |
| `outlet.3.delay.start` | 插座3: start |
| `outlet.3.desc` | 插座3: desc |
| `outlet.3.frequency` | 插座3: frequency |
| `outlet.3.id` | 插座3: id |
| `outlet.3.load.off` | 插座3: off |
| `outlet.3.load.on` | 插座3: on |
| `outlet.3.power` | 插座3: power |
| `outlet.3.powerfactor` | 插座3: powerfactor |
| `outlet.3.realpower` | 插座3: realpower |
| `outlet.3.status` | 插座3: status |
| `outlet.3.switch` | 插座3: switch |
| `outlet.3.switchable` | 插座3: switchable |
| `outlet.3.type` | 插座3: type |
| `outlet.3.voltage` | 插座3: voltage |

#### 插座4 (21 个不可用)

| 变量名 | 描述 |
|--------|------|
| `outlet.4.alarm` | 插座4: alarm |
| `outlet.4.autoswitch.charge.low` | 插座4: low |
| `outlet.4.crestfactor` | 插座4: crestfactor |
| `outlet.4.current` | 插座4: current |
| `outlet.4.current.maximum` | 插座4: maximum |
| `outlet.4.current.status` | 插座4: status |
| `outlet.4.delay.shutdown` | 插座4: shutdown |
| `outlet.4.delay.start` | 插座4: start |
| `outlet.4.desc` | 插座4: desc |
| `outlet.4.frequency` | 插座4: frequency |
| `outlet.4.id` | 插座4: id |
| `outlet.4.load.off` | 插座4: off |
| `outlet.4.load.on` | 插座4: on |
| `outlet.4.power` | 插座4: power |
| `outlet.4.powerfactor` | 插座4: powerfactor |
| `outlet.4.realpower` | 插座4: realpower |
| `outlet.4.status` | 插座4: status |
| `outlet.4.switch` | 插座4: switch |
| `outlet.4.switchable` | 插座4: switchable |
| `outlet.4.type` | 插座4: type |
| `outlet.4.voltage` | 插座4: voltage |

#### 插座5 (21 个不可用)

| 变量名 | 描述 |
|--------|------|
| `outlet.5.alarm` | 插座5: alarm |
| `outlet.5.autoswitch.charge.low` | 插座5: low |
| `outlet.5.crestfactor` | 插座5: crestfactor |
| `outlet.5.current` | 插座5: current |
| `outlet.5.current.maximum` | 插座5: maximum |
| `outlet.5.current.status` | 插座5: status |
| `outlet.5.delay.shutdown` | 插座5: shutdown |
| `outlet.5.delay.start` | 插座5: start |
| `outlet.5.desc` | 插座5: desc |
| `outlet.5.frequency` | 插座5: frequency |
| `outlet.5.id` | 插座5: id |
| `outlet.5.load.off` | 插座5: off |
| `outlet.5.load.on` | 插座5: on |
| `outlet.5.power` | 插座5: power |
| `outlet.5.powerfactor` | 插座5: powerfactor |
| `outlet.5.realpower` | 插座5: realpower |
| `outlet.5.status` | 插座5: status |
| `outlet.5.switch` | 插座5: switch |
| `outlet.5.switchable` | 插座5: switchable |
| `outlet.5.type` | 插座5: type |
| `outlet.5.voltage` | 插座5: voltage |

#### 插座6 (21 个不可用)

| 变量名 | 描述 |
|--------|------|
| `outlet.6.alarm` | 插座6: alarm |
| `outlet.6.autoswitch.charge.low` | 插座6: low |
| `outlet.6.crestfactor` | 插座6: crestfactor |
| `outlet.6.current` | 插座6: current |
| `outlet.6.current.maximum` | 插座6: maximum |
| `outlet.6.current.status` | 插座6: status |
| `outlet.6.delay.shutdown` | 插座6: shutdown |
| `outlet.6.delay.start` | 插座6: start |
| `outlet.6.desc` | 插座6: desc |
| `outlet.6.frequency` | 插座6: frequency |
| `outlet.6.id` | 插座6: id |
| `outlet.6.load.off` | 插座6: off |
| `outlet.6.load.on` | 插座6: on |
| `outlet.6.power` | 插座6: power |
| `outlet.6.powerfactor` | 插座6: powerfactor |
| `outlet.6.realpower` | 插座6: realpower |
| `outlet.6.status` | 插座6: status |
| `outlet.6.switch` | 插座6: switch |
| `outlet.6.switchable` | 插座6: switchable |
| `outlet.6.type` | 插座6: type |
| `outlet.6.voltage` | 插座6: voltage |

#### 插座7 (21 个不可用)

| 变量名 | 描述 |
|--------|------|
| `outlet.7.alarm` | 插座7: alarm |
| `outlet.7.autoswitch.charge.low` | 插座7: low |
| `outlet.7.crestfactor` | 插座7: crestfactor |
| `outlet.7.current` | 插座7: current |
| `outlet.7.current.maximum` | 插座7: maximum |
| `outlet.7.current.status` | 插座7: status |
| `outlet.7.delay.shutdown` | 插座7: shutdown |
| `outlet.7.delay.start` | 插座7: start |
| `outlet.7.desc` | 插座7: desc |
| `outlet.7.frequency` | 插座7: frequency |
| `outlet.7.id` | 插座7: id |
| `outlet.7.load.off` | 插座7: off |
| `outlet.7.load.on` | 插座7: on |
| `outlet.7.power` | 插座7: power |
| `outlet.7.powerfactor` | 插座7: powerfactor |
| `outlet.7.realpower` | 插座7: realpower |
| `outlet.7.status` | 插座7: status |
| `outlet.7.switch` | 插座7: switch |
| `outlet.7.switchable` | 插座7: switchable |
| `outlet.7.type` | 插座7: type |
| `outlet.7.voltage` | 插座7: voltage |

#### 插座8 (21 个不可用)

| 变量名 | 描述 |
|--------|------|
| `outlet.8.alarm` | 插座8: alarm |
| `outlet.8.autoswitch.charge.low` | 插座8: low |
| `outlet.8.crestfactor` | 插座8: crestfactor |
| `outlet.8.current` | 插座8: current |
| `outlet.8.current.maximum` | 插座8: maximum |
| `outlet.8.current.status` | 插座8: status |
| `outlet.8.delay.shutdown` | 插座8: shutdown |
| `outlet.8.delay.start` | 插座8: start |
| `outlet.8.desc` | 插座8: desc |
| `outlet.8.frequency` | 插座8: frequency |
| `outlet.8.id` | 插座8: id |
| `outlet.8.load.off` | 插座8: off |
| `outlet.8.load.on` | 插座8: on |
| `outlet.8.power` | 插座8: power |
| `outlet.8.powerfactor` | 插座8: powerfactor |
| `outlet.8.realpower` | 插座8: realpower |
| `outlet.8.status` | 插座8: status |
| `outlet.8.switch` | 插座8: switch |
| `outlet.8.switchable` | 插座8: switchable |
| `outlet.8.type` | 插座8: type |
| `outlet.8.voltage` | 插座8: voltage |

#### 插座9 (21 个不可用)

| 变量名 | 描述 |
|--------|------|
| `outlet.9.alarm` | 插座9: alarm |
| `outlet.9.autoswitch.charge.low` | 插座9: low |
| `outlet.9.crestfactor` | 插座9: crestfactor |
| `outlet.9.current` | 插座9: current |
| `outlet.9.current.maximum` | 插座9: maximum |
| `outlet.9.current.status` | 插座9: status |
| `outlet.9.delay.shutdown` | 插座9: shutdown |
| `outlet.9.delay.start` | 插座9: start |
| `outlet.9.desc` | 插座9: desc |
| `outlet.9.frequency` | 插座9: frequency |
| `outlet.9.id` | 插座9: id |
| `outlet.9.load.off` | 插座9: off |
| `outlet.9.load.on` | 插座9: on |
| `outlet.9.power` | 插座9: power |
| `outlet.9.powerfactor` | 插座9: powerfactor |
| `outlet.9.realpower` | 插座9: realpower |
| `outlet.9.status` | 插座9: status |
| `outlet.9.switch` | 插座9: switch |
| `outlet.9.switchable` | 插座9: switchable |
| `outlet.9.type` | 插座9: type |
| `outlet.9.voltage` | 插座9: voltage |

#### 插座组 (1 个不可用)

| 变量名 | 描述 |
|--------|------|
| `outlet.group.count` | 插座组数量 |

#### 旁路 (9 个不可用)

| 变量名 | 描述 |
|--------|------|
| `bypass.current` | 旁路电流(A) |
| `bypass.current.nominal` | 旁路额定电流(A) |
| `bypass.frequency` | 旁路频率(Hz) |
| `bypass.frequency.nominal` | 旁路额定频率(Hz) |
| `bypass.phases` | 旁路相数 |
| `bypass.power` | 旁路功率(VA) |
| `bypass.realpower` | 旁路实际功率(W) |
| `bypass.voltage` | 旁路电压(V) |
| `bypass.voltage.nominal` | 旁路额定电压(V) |

#### 旁路L1相 (2 个不可用)

| 变量名 | 描述 |
|--------|------|
| `bypass.L1.current` | 旁路L1相电流(A) |
| `bypass.L1.voltage` | 旁路L1相电压(V) |

#### 旁路L2相 (2 个不可用)

| 变量名 | 描述 |
|--------|------|
| `bypass.L2.current` | 旁路L2相电流(A) |
| `bypass.L2.voltage` | 旁路L2相电压(V) |

#### 旁路L3相 (2 个不可用)

| 变量名 | 描述 |
|--------|------|
| `bypass.L3.current` | 旁路L3相电流(A) |
| `bypass.L3.voltage` | 旁路L3相电压(V) |

#### 旁路输入 (4 个不可用)

| 变量名 | 描述 |
|--------|------|
| `input.bypass.current` | 旁路输入电流(A) |
| `input.bypass.frequency` | 旁路输入频率(Hz) |
| `input.bypass.phases` | 旁路输入相数 |
| `input.bypass.voltage` | 旁路输入电压(V) |

#### 旁路输入(三相) (9 个不可用)

| 变量名 | 描述 |
|--------|------|
| `input.bypass.L1-N.voltage` | 旁路L1-N电压(V) |
| `input.bypass.L1.current` | 旁路L1相电流(A) |
| `input.bypass.L1.voltage` | 旁路L1相电压(V) |
| `input.bypass.L2-N.voltage` | 旁路L2-N电压(V) |
| `input.bypass.L2.current` | 旁路L2相电流(A) |
| `input.bypass.L2.voltage` | 旁路L2相电压(V) |
| `input.bypass.L3-N.voltage` | 旁路L3-N电压(V) |
| `input.bypass.L3.current` | 旁路L3相电流(A) |
| `input.bypass.L3.voltage` | 旁路L3相电压(V) |

#### 服务器信息 (2 个不可用)

| 变量名 | 描述 |
|--------|------|
| `server.info` | 服务器信息 |
| `server.version` | 服务器版本 |

#### 环境传感器1 (2 个不可用)

| 变量名 | 描述 |
|--------|------|
| `ambient.1.humidity` | 环境传感器1湿度(%) |
| `ambient.1.temperature` | 环境传感器1温度(°C) |

#### 环境传感器2 (2 个不可用)

| 变量名 | 描述 |
|--------|------|
| `ambient.2.humidity` | 环境传感器2湿度(%) |
| `ambient.2.temperature` | 环境传感器2温度(°C) |

#### 环境监控 (19 个不可用)

| 变量名 | 描述 |
|--------|------|
| `ambient.humidity` | 环境湿度(%) |
| `ambient.humidity.alarm` | 湿度报警 |
| `ambient.humidity.alarm.enable` | 湿度报警使能 |
| `ambient.humidity.high` | 高湿阈值(%) |
| `ambient.humidity.high.critical` | 高湿临界阈值(%) |
| `ambient.humidity.high.warning` | 高湿警告阈值(%) |
| `ambient.humidity.low` | 低湿阈值(%) |
| `ambient.humidity.low.critical` | 低湿临界阈值(%) |
| `ambient.humidity.low.warning` | 低湿警告阈值(%) |
| `ambient.present` | 环境传感器存在 |
| `ambient.temperature` | 环境温度(°C) |
| `ambient.temperature.alarm` | 温度报警 |
| `ambient.temperature.alarm.enable` | 温度报警使能 |
| `ambient.temperature.high` | 高温阈值(°C) |
| `ambient.temperature.high.critical` | 高温临界阈值(°C) |
| `ambient.temperature.high.warning` | 高温警告阈值(°C) |
| `ambient.temperature.low` | 低温阈值(°C) |
| `ambient.temperature.low.critical` | 低温临界阈值(°C) |
| `ambient.temperature.low.warning` | 低温警告阈值(°C) |

#### 电池 (30 个不可用)

| 变量名 | 描述 |
|--------|------|
| `battery.alarm.threshold` | 电池报警阈值 |
| `battery.capacity` | 电池容量(Ah) |
| `battery.charge` | 电池电量(%) |
| `battery.charge.low` | 低电量阈值(%) |
| `battery.charge.restart` | 重启电量阈值(%) |
| `battery.charge.warning` | 警告电量阈值(%) |
| `battery.charger.status` | 充电器状态 |
| `battery.current` | 电池电流(A) |
| `battery.current.total` | 电池总电流(A) |
| `battery.date` | 电池安装日期 |
| `battery.energysave` | 节能模式状态 |
| `battery.energysave.delay` | 节能延迟(秒) |
| `battery.energysave.load` | 节能负载阈值(%) |
| `battery.energysave.realpower` | 节能功率阈值(W) |
| `battery.mfr.date` | 电池生产日期 |
| `battery.packs` | 电池组数量 |
| `battery.packs.bad` | 损坏电池组数量 |
| `battery.packs.external` | 外部电池组数量 |
| `battery.protection` | 电池保护状态 |
| `battery.runtime` | 剩余运行时间(秒) |
| `battery.runtime.low` | 低运行时间阈值(秒) |
| `battery.runtime.restart` | 重启运行时间阈值(秒) |
| `battery.temperature` | 电池温度(°C) |
| `battery.type` | 电池类型 |
| `battery.voltage` | 电池电压(V) |
| `battery.voltage.cell.max` | 最大电芯电压(V) |
| `battery.voltage.cell.min` | 最小电芯电压(V) |
| `battery.voltage.high` | 电池高电压(V) |
| `battery.voltage.low` | 电池低电压(V) |
| `battery.voltage.nominal` | 额定电池电压(V) |

#### 设备信息 (11 个不可用)

| 变量名 | 描述 |
|--------|------|
| `device.contact` | 联系人 |
| `device.count` | 受管设备数量 |
| `device.description` | 设备描述 |
| `device.location` | 设备位置 |
| `device.macaddr` | MAC地址 |
| `device.mfr` | 设备制造商 |
| `device.model` | 设备型号 |
| `device.part` | 部件号 |
| `device.serial` | 设备序列号 |
| `device.type` | 设备类型 (ups/pdu/scd/psu/ats) |
| `device.uptime` | 设备运行时间(秒) |

#### 输入L1-L2线 (1 个不可用)

| 变量名 | 描述 |
|--------|------|
| `input.L1-L2.voltage` | L1-L2线电压(V) |

#### 输入L1-N相 (1 个不可用)

| 变量名 | 描述 |
|--------|------|
| `input.L1-N.voltage` | L1-N电压(V) |

#### 输入L1相 (9 个不可用)

| 变量名 | 描述 |
|--------|------|
| `input.L1.current` | L1相输入电流(A) |
| `input.L1.current.peak` | L1相峰值电流(A) |
| `input.L1.current.status` | L1相电流状态 |
| `input.L1.frequency` | L1相频率(Hz) |
| `input.L1.power` | L1相功率(VA) |
| `input.L1.power.percent` | L1相功率百分比(%) |
| `input.L1.realpower` | L1相实际功率(W) |
| `input.L1.voltage` | L1相输入电压(V) |
| `input.L1.voltage.status` | L1相电压状态 |

#### 输入L2-L3线 (1 个不可用)

| 变量名 | 描述 |
|--------|------|
| `input.L2-L3.voltage` | L2-L3线电压(V) |

#### 输入L2-N相 (1 个不可用)

| 变量名 | 描述 |
|--------|------|
| `input.L2-N.voltage` | L2-N电压(V) |

#### 输入L2相 (9 个不可用)

| 变量名 | 描述 |
|--------|------|
| `input.L2.current` | L2相输入电流(A) |
| `input.L2.current.peak` | L2相峰值电流(A) |
| `input.L2.current.status` | L2相电流状态 |
| `input.L2.frequency` | L2相频率(Hz) |
| `input.L2.power` | L2相功率(VA) |
| `input.L2.power.percent` | L2相功率百分比(%) |
| `input.L2.realpower` | L2相实际功率(W) |
| `input.L2.voltage` | L2相输入电压(V) |
| `input.L2.voltage.status` | L2相电压状态 |

#### 输入L3-L1线 (1 个不可用)

| 变量名 | 描述 |
|--------|------|
| `input.L3-L1.voltage` | L3-L1线电压(V) |

#### 输入L3-N相 (1 个不可用)

| 变量名 | 描述 |
|--------|------|
| `input.L3-N.voltage` | L3-N电压(V) |

#### 输入L3相 (9 个不可用)

| 变量名 | 描述 |
|--------|------|
| `input.L3.current` | L3相输入电流(A) |
| `input.L3.current.peak` | L3相峰值电流(A) |
| `input.L3.current.status` | L3相电流状态 |
| `input.L3.frequency` | L3相频率(Hz) |
| `input.L3.power` | L3相功率(VA) |
| `input.L3.power.percent` | L3相功率百分比(%) |
| `input.L3.realpower` | L3相实际功率(W) |
| `input.L3.voltage` | L3相输入电压(V) |
| `input.L3.voltage.status` | L3相电压状态 |

#### 输入电源 (34 个不可用)

| 变量名 | 描述 |
|--------|------|
| `input.current` | 输入电流(A) |
| `input.current.nominal` | 额定输入电流(A) |
| `input.current.status` | 输入电流状态 |
| `input.frequency` | 输入频率(Hz) |
| `input.frequency.extended` | 扩展输入频率 |
| `input.frequency.high` | 最高输入频率(Hz) |
| `input.frequency.low` | 最低输入频率(Hz) |
| `input.frequency.nominal` | 额定输入频率(Hz) |
| `input.frequency.status` | 输入频率状态 |
| `input.phases` | 输入相数 |
| `input.power` | 输入功率(VA) |
| `input.quality` | 电源质量 |
| `input.realpower` | 输入实际功率(W) |
| `input.sensitivity` | 输入灵敏度 |
| `input.source` | 输入源 |
| `input.source.preferred` | 首选输入源 |
| `input.transfer.boost.high` | 升压高阈值(V) |
| `input.transfer.boost.low` | 升压低阈值(V) |
| `input.transfer.delay` | 转换延迟(秒) |
| `input.transfer.high` | 高压转换阈值(V) |
| `input.transfer.high.max` | 高压阈值最大值(V) |
| `input.transfer.high.min` | 高压阈值最小值(V) |
| `input.transfer.low` | 低压转换阈值(V) |
| `input.transfer.low.max` | 低压阈值最大值(V) |
| `input.transfer.low.min` | 低压阈值最小值(V) |
| `input.transfer.reason` | 转换原因 |
| `input.transfer.trim.high` | 降压高阈值(V) |
| `input.transfer.trim.low` | 降压低阈值(V) |
| `input.voltage` | 输入电压(V) |
| `input.voltage.extended` | 扩展输入电压 |
| `input.voltage.fault` | 故障输入电压(V) |
| `input.voltage.maximum` | 最大输入电压(V) |
| `input.voltage.minimum` | 最小输入电压(V) |
| `input.voltage.nominal` | 额定输入电压(V) |

#### 输出L1-L2线 (1 个不可用)

| 变量名 | 描述 |
|--------|------|
| `output.L1-L2.voltage` | L1-L2输出线电压(V) |

#### 输出L1-N相 (1 个不可用)

| 变量名 | 描述 |
|--------|------|
| `output.L1-N.voltage` | L1-N输出电压(V) |

#### 输出L1相 (7 个不可用)

| 变量名 | 描述 |
|--------|------|
| `output.L1.crestfactor` | L1相波峰因数 |
| `output.L1.current` | L1相输出电流(A) |
| `output.L1.current.peak` | L1相峰值输出电流(A) |
| `output.L1.power` | L1相输出功率(VA) |
| `output.L1.power.percent` | L1相功率百分比(%) |
| `output.L1.realpower` | L1相输出实际功率(W) |
| `output.L1.voltage` | L1相输出电压(V) |

#### 输出L2-L3线 (1 个不可用)

| 变量名 | 描述 |
|--------|------|
| `output.L2-L3.voltage` | L2-L3输出线电压(V) |

#### 输出L2-N相 (1 个不可用)

| 变量名 | 描述 |
|--------|------|
| `output.L2-N.voltage` | L2-N输出电压(V) |

#### 输出L2相 (7 个不可用)

| 变量名 | 描述 |
|--------|------|
| `output.L2.crestfactor` | L2相波峰因数 |
| `output.L2.current` | L2相输出电流(A) |
| `output.L2.current.peak` | L2相峰值输出电流(A) |
| `output.L2.power` | L2相输出功率(VA) |
| `output.L2.power.percent` | L2相功率百分比(%) |
| `output.L2.realpower` | L2相输出实际功率(W) |
| `output.L2.voltage` | L2相输出电压(V) |

#### 输出L3-L1线 (1 个不可用)

| 变量名 | 描述 |
|--------|------|
| `output.L3-L1.voltage` | L3-L1输出线电压(V) |

#### 输出L3-N相 (1 个不可用)

| 变量名 | 描述 |
|--------|------|
| `output.L3-N.voltage` | L3-N输出电压(V) |

#### 输出L3相 (7 个不可用)

| 变量名 | 描述 |
|--------|------|
| `output.L3.crestfactor` | L3相波峰因数 |
| `output.L3.current` | L3相输出电流(A) |
| `output.L3.current.peak` | L3相峰值输出电流(A) |
| `output.L3.power` | L3相输出功率(VA) |
| `output.L3.power.percent` | L3相功率百分比(%) |
| `output.L3.realpower` | L3相输出实际功率(W) |
| `output.L3.voltage` | L3相输出电压(V) |

#### 输出电源 (11 个不可用)

| 变量名 | 描述 |
|--------|------|
| `output.current` | 输出电流(A) |
| `output.current.nominal` | 额定输出电流(A) |
| `output.frequency` | 输出频率(Hz) |
| `output.frequency.nominal` | 额定输出频率(Hz) |
| `output.phases` | 输出相数 |
| `output.power` | 输出功率(VA) |
| `output.power.nominal` | 额定输出功率(VA) |
| `output.realpower` | 输出实际功率(W) |
| `output.realpower.nominal` | 额定输出实际功率(W) |
| `output.voltage` | 输出电压(V) |
| `output.voltage.nominal` | 额定输出电压(V) |

#### 驱动信息 (4 个不可用)

| 变量名 | 描述 |
|--------|------|
| `driver.debug` | 调试级别 |
| `driver.name` | 驱动名称 |
| `driver.state` | 驱动状态 |
| `driver.version` | 驱动版本 |

#### 驱动参数 (11 个不可用)

| 变量名 | 描述 |
|--------|------|
| `driver.parameter.bus` | USB总线 |
| `driver.parameter.langid_fix` | 语言ID修复 |
| `driver.parameter.pollfreq` | 轮询频率 |
| `driver.parameter.pollinterval` | 轮询间隔 |
| `driver.parameter.port` | 驱动端口 |
| `driver.parameter.product` | 产品名称 |
| `driver.parameter.productid` | 产品ID参数 |
| `driver.parameter.serial` | 序列号参数 |
| `driver.parameter.synchronous` | 同步模式 |
| `driver.parameter.vendor` | 厂商名称 |
| `driver.parameter.vendorid` | 厂商ID参数 |

#### 驱动标志 (1 个不可用)

| 变量名 | 描述 |
|--------|------|
| `driver.flag.allow_killpower` | 允许killpower |

#### 驱动版本 (3 个不可用)

| 变量名 | 描述 |
|--------|------|
| `driver.version.data` | 数据版本 |
| `driver.version.internal` | 内部驱动版本 |
| `driver.version.usb` | USB库版本 |

</details>

## 项目变量覆盖情况


| 指标 | 数值 |
|------|------|
| 项目定义变量 | 36 |
| ✅ 可用 | 0 |
| ❌ 不可用 | 36 |
| 覆盖率 | 0.0% |

#### ❌ 项目中不可用的变量

| 变量名 | 描述 |
|--------|------|
| `ups.status` | UPS 状态 (OL=在线, OB=电池, LB=低电) |
| `ups.model` | UPS 型号 |
| `ups.mfr` | 制造商 |
| `battery.charge` | 电池电量 (%) |
| `battery.runtime` | 剩余运行时间 (秒) |
| `battery.voltage` | 电池电压 (V) |
| `battery.voltage.nominal` | 电池额定电压 (V) |
| `battery.temperature` | 电池温度 (°C) |
| `battery.type` | 电池类型 |
| `battery.date` | 电池安装日期 |
| `battery.mfr.date` | 电池生产日期 |
| `battery.packs` | 电池组数量 |
| `battery.packs.bad` | 损坏的电池组数量 |
| `input.voltage` | 输入电压 (V) |
| `input.frequency` | 输入频率 (Hz) |
| `input.voltage.minimum` | 输入电压最小值 (V) |
| `input.voltage.maximum` | 输入电压最大值 (V) |
| `input.transfer.low` | 低压转换阈值 (V) |
| `input.transfer.high` | 高压转换阈值 (V) |
| `output.voltage` | 输出电压 (V) |
| `output.frequency` | 输出频率 (Hz) |
| `output.current` | 输出电流 (A) |
| `output.current.nominal` | 额定输出电流 (A) |
| `ups.load` | 负载百分比 (%) |
| `ups.power.nominal` | UPS 额定功率 (VA) |
| `ups.realpower` | 实际功率 (W) |
| `ups.efficiency` | UPS 效率 (%) |
| `ups.temperature` | UPS 温度 (°C) |
| `ambient.temperature` | 环境温度 (°C) |
| `ambient.humidity` | 环境湿度 (%) |
| `ambient.temperature.alarm` | 温度报警 |
| `ambient.humidity.alarm` | 湿度报警 |
| `ups.test.result` | 自检结果 |
| `ups.test.date` | 上次自检时间 |
| `ups.alarm` | 当前报警信息 |
| `ups.beeper.status` | 蜂鸣器状态 |

## 测试总结


| 项目 | 数值 |
|------|------|
| UPS 名称 | N/A |
| 制造商 | N/A |
| 型号 | N/A |
| 驱动 | N/A |
| UPS 提供变量数 | 0 |
| NUT 标准变量库 | 614 |
| 项目变量覆盖率 | 0/36 (0.0%) |

---

## ⚙️ entrypoint.sh 配置覆盖说明

以下变量的值受到 NUT 驱动配置 (`ups.conf` / `entrypoint.sh`) 的影响，**不是 UPS 硬件的原始值**：

### 阈值覆盖变量（4个）

这些变量被 `entrypoint.sh` 通过 `override.*` 配置覆盖，目的是避免某些 UPS（如 APC）报告异常阈值导致误触发关机：

| 变量名 | 当前值 | 来源 | 说明 |
|--------|--------|------|------|
| `battery.charge.low` | N/A | ⚙️ entrypoint.sh | 低电量阈值(%)，由 `BATTERY_CHARGE_LOW` 环境变量设置 |
| `battery.runtime.low` | N/A | ⚙️ entrypoint.sh | 低运行时间阈值(秒)，由 `BATTERY_RUNTIME_LOW` 环境变量设置 |
| `driver.parameter.override.battery.charge.low` | N/A | ⚙️ entrypoint.sh | 记录覆盖值的驱动参数 |
| `driver.parameter.override.battery.runtime.low` | N/A | ⚙️ entrypoint.sh | 记录覆盖值的驱动参数 |

### 驱动配置变量（4个）

这些变量由 `entrypoint.sh` 在生成 `ups.conf` 时设置：

| 变量名 | 当前值 | 来源 | 说明 |
|--------|--------|------|------|
| `driver.flag.ignorelb` | N/A | ⚙️ entrypoint.sh | 忽略 UPS 硬件 LB 信号，使用软件阈值判断 |
| `driver.parameter.pollinterval` | N/A | ⚙️ entrypoint.sh | USB 轮询间隔，减少通信压力 |
| `driver.parameter.subdriver` | N/A | ⚙️ entrypoint.sh | APC 专用子驱动配置 |
| `driver.parameter.vendorid` | N/A | ⚙️ entrypoint.sh | 从 nut-scanner 提取后写入配置 |

### 其他驱动参数

| 变量名 | 当前值 | 说明 |
|--------|--------|------|
| `driver.parameter.productid` | N/A | USB 产品 ID |
| `driver.parameter.port` | N/A | 驱动端口 |
| `driver.parameter.pollfreq` | N/A | 完整轮询频率 |
| `driver.parameter.synchronous` | N/A | 同步模式 |

> 💡 **提示**: 如果需要查看 UPS 的原始硬件阈值，可以临时移除 `ups.conf` 中的 `override.*` 和 `ignorelb` 配置后重新测试。
>
> ⚠️ **注意**: APC BK650M2 的原厂 `battery.charge.low` 可能是 **95%**，这会导致电量一低于 95% 就触发关机，因此需要覆盖为合理值（如 20%）。

---

## 📚 参考资料

- [NUT 官方变量文档](https://networkupstools.org/docs/developer-guide.chunked/apas01.html)
- [NUT 变量命名规范 (nut-names.txt)](https://github.com/networkupstools/nut/blob/master/docs/nut-names.txt)
- [ups-guard 项目](https://github.com/your-repo/ups-guard)

---

*报告生成完成 - 2026-03-05 19:48:20*


----