# 支持的 UPS 设备

UPS Guard使用 Network UPS Tools (NUT) 协议，理论上支持 NUT 支持的所有 UPS 设备。

## 推荐品牌

以下品牌的 UPS 设备经过测试，兼容性良好：

### APC（美国电力转换）

- ✅ Back-UPS 系列
- ✅ Smart-UPS 系列
- ✅ Back-UPS Pro 系列

驱动：`usbhid-ups`

### CyberPower（赛博威力）

- ✅ CP 系列
- ✅ OR 系列
- ✅ PR 系列

驱动：`usbhid-ups`

### Eaton（伊顿）

- ✅ 5E 系列
- ✅ 5P 系列
- ✅ 5S 系列

驱动：`usbhid-ups`

### 山特（SANTAK）

- ✅ TG-BOX 系列
- ✅ MT 系列
- ✅ C 系列

驱动：`usbhid-ups`

### 科士达（Kstar）

- ✅ YDE 系列
- ✅ EA 系列

驱动：`usbhid-ups`

## 驱动选择

UPS Guard默认使用 `usbhid-ups` 驱动，这是最通用的 USB HID 协议驱动，支持大多数现代 UPS 设备。

如果您的 UPS 使用其他驱动，请在设置中修改驱动配置。

### 常用驱动

| 驱动名称 | 适用设备 |
|---------|---------|
| `usbhid-ups` | USB HID UPS 设备（推荐） |
| `nutdrv_qx` | Q1/Megatec/Voltronic 协议 |
| `blazer_usb` | 早期 USB UPS 设备 |
| `snmp-ups` | 支持 SNMP 的网络 UPS |

## 查看支持的设备

NUT 项目维护了完整的[兼容设备列表](https://networkupstools.org/stable-hcl.html)，包含超过 2000 款 UPS 设备。

## 测试您的 UPS

### 检查设备连接

连接 UPS 后，在终端执行：

```bash
lsusb
```

应该能看到类似以下输出：

```
Bus 001 Device 003: ID 051d:0002 American Power Conversion Uninterruptible Power Supply
```

### 测试驱动

```bash
docker exec -it ups-guard-nut-server upsc ups
```

如果输出 UPS 参数列表，说明驱动工作正常。

## 不支持的设备

以下情况可能无法使用：

- ⚠️ 仅支持串口（RS232）连接的老式 UPS
- ⚠️ 使用专有协议且不提供 Linux 驱动的 UPS
- ⚠️ 使用厂商专用 USB 协议的特殊型号

如果您的 UPS 不在支持列表中，可以：

1. 查阅 [NUT 兼容设备列表](https://networkupstools.org/stable-hcl.html)
2. 在 GitHub Issues 中询问
3. 尝试使用通用驱动测试

## 贡献设备兼容性信息

如果您测试了其他 UPS 设备，欢迎通过 GitHub Issues 或 Pull Request 分享：

- UPS 品牌和型号
- 使用的驱动
- 是否工作正常
- 特殊配置说明

帮助我们完善兼容性列表！
