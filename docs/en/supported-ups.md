# Supported UPS Devices

UPS Guard uses Network UPS Tools (NUT) protocol, theoretically supporting all UPS devices that NUT supports.

## Recommended Brands

The following UPS device brands have been tested and have good compatibility:

### APC (American Power Conversion)

- ✅ Back-UPS series
- ✅ Smart-UPS series
- ✅ Back-UPS Pro series

Driver: `usbhid-ups`

### CyberPower

- ✅ CP series
- ✅ OR series
- ✅ PR series

Driver: `usbhid-ups`

### Eaton

- ✅ 5E series
- ✅ 5P series
- ✅ 5S series

Driver: `usbhid-ups`

### SANTAK

- ✅ TG-BOX series
- ✅ MT series
- ✅ C series

Driver: `usbhid-ups`

### Kstar

- ✅ YDE series
- ✅ EA series

Driver: `usbhid-ups`

## Driver Selection

UPS Guard uses `usbhid-ups` driver by default, which is the most universal USB HID protocol driver supporting most modern UPS devices.

If your UPS uses a different driver, please modify driver configuration in settings.

### Common Drivers

| Driver Name | Applicable Devices |
|---------|---------|
| `usbhid-ups` | USB HID UPS devices (Recommended) |
| `nutdrv_qx` | Q1/Megatec/Voltronic protocol |
| `blazer_usb` | Early USB UPS devices |
| `snmp-ups` | SNMP-capable network UPS |

## View Supported Devices

The NUT project maintains a complete [Compatible Device List](https://networkupstools.org/stable-hcl.html) containing over 2000 UPS devices.

## Test Your UPS

### Check Device Connection

After connecting UPS, execute in terminal:

```bash
lsusb
```

Should see output similar to:

```
Bus 001 Device 003: ID 051d:0002 American Power Conversion Uninterruptible Power Supply
```

### Test Driver

```bash
docker exec -it ups-guard-nut-server upsc ups
```

If UPS parameters list is output, driver is working properly.

## Unsupported Devices

The following situations may not work:

- ⚠️ Old UPS devices with only serial port (RS232) connection
- ⚠️ UPS using proprietary protocols without Linux drivers
- ⚠️ Special models using vendor-specific USB protocols

If your UPS is not on the support list, you can:

1. Check [NUT Compatible Device List](https://networkupstools.org/stable-hcl.html)
2. Ask in GitHub Issues
3. Try testing with generic driver

## Contribute Device Compatibility Information

If you tested other UPS devices, welcome to share via GitHub Issues or Pull Request:

- UPS brand and model
- Driver used
- Whether working properly
- Special configuration instructions

Help us improve the compatibility list!
