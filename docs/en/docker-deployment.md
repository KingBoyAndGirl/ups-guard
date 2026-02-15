# Docker Deployment Guide

This document describes how to deploy UPS Guard system using Docker Compose on any device that supports Docker.

## System Requirements

- Docker Engine 20.10+
- Docker Compose 2.0+
- Hardware: At least 512MB RAM, 1GB disk space
- USB interface (for connecting UPS device)

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/KingBoyAndGirl/ups-guard.git
cd ups-guard
```

### 2. Configure Environment Variables

Copy environment variable example file and modify as needed:

```bash
cp .env.example .env
nano .env  # or use other editor
```

Key configuration items:

```bash
# UPS device configuration
UPS_NAME=ups
UPS_DRIVER=usbhid-ups  # Choose driver based on UPS brand
UPS_PORT=auto

# NUT user password (recommend changing)
UPSD_USER=admin
UPSD_PASSWORD=your_secure_password
UPSMON_USER=monuser
UPSMON_PASSWORD=your_secure_password

# API Token (recommend manual setting)
API_TOKEN=your_random_secure_token

# HTTP port
HTTP_PORT=80
```

### 3. Start Services

```bash
docker-compose up -d
```

First startup will automatically:
- Build all service images
- Create data volumes
- Start NUT Server, Backend and Frontend services
- Auto-detect USB-connected UPS device

### 4. Access Web Interface

Open browser and visit: `http://localhost` or `http://<your-server-ip>`

### 5. View Logs

```bash
# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f nut-server
docker-compose logs -f frontend
```

## UPS Driver Configuration

### Auto Detection

On startup, NUT Server will automatically scan USB devices and try to identify UPS brand:

```bash
docker-compose logs nut-server | grep "UPS Brand Recognition"
```

### Manual Configuration

If auto-detection fails, manually specify driver in `.env` file:

#### Common UPS Brand Driver Reference

| Brand | USB Vendor ID | Recommended Driver |
|------|---------------|----------|
| APC (Schneider) | 051d | `usbhid-ups` |
| SANTAK | 0463 | `blazer_usb` |
| CyberPower | 0665 | `usbhid-ups` |
| Eaton | 06da | `usbhid-ups` |
| Huawei | 0764 | `nutdrv_qx` |
| SANTAK Castle | 0001 | `nutdrv_qx` |

#### View USB Vendor/Product ID

```bash
docker exec ups-guard-nut nut-scanner -U
```

Example output:

```
[nutdev1]
    driver = "usbhid-ups"
    port = "auto"
    vendorid = "051D"
    productid = "0002"
    product = "Back-UPS XS 1000M"
    vendor = "American Power Conversion"
```

Modify `UPS_DRIVER` in `.env` based on output.

## Development Mode

Development/test mode uses Mock data, no need to connect real UPS device.

### 1. Create Development Configuration

```bash
cp docker-compose.override.yml.example docker-compose.override.yml
```

### 2. Start Development Mode

```bash
docker-compose up -d
```

Docker Compose will automatically merge `docker-compose.yml` and `docker-compose.override.yml`, enabling Mock mode.

### 3. Development Mode Features

- Uses `dummy-ups` driver (no real UPS needed)
- Backend uses Mock data
- Frontend supports hot reload (auto-refresh on code change)
- Detailed log output (LOG_LEVEL=DEBUG)

## Managed Devices Configuration

UPS Guard supports automatic shutdown of multiple devices during power outage.

### 1. Access Settings Page

Open Web UI → Settings → Pre-shutdown Tasks

### 2. Add Devices

Supported device types:

- **SSH Remote Shutdown**: Linux/macOS servers
- **Windows Remote Shutdown**: Windows systems
- **Synology Shutdown**: Synology NAS
- **QNAP Shutdown**: QNAP NAS
- **HTTP API**: Custom REST API
- **Custom Script**: Shell/Python script

### 3. View Device Status

In Dashboard page's "Managed Devices" area you can:
- View all devices' online status
- Test device connection
- View last detection time
- Real-time view of shutdown execution progress

### 4. Shutdown Execution Flow

When power outage triggers shutdown:
1. Group by priority (lower numbers execute first)
2. Same priority devices shutdown in parallel
3. Real-time display of each device's execution status
4. After all devices shutdown complete, shutdown local machine

## Common Issues

### Q1: Cannot Detect UPS Device

**Solutions:**

1. Check USB connection:
   ```bash
   lsusb | grep -i ups
   ```

2. Check NUT Server logs:
   ```bash
   docker-compose logs nut-server
   ```

3. Try manually specifying driver:
   Modify `UPS_DRIVER` and `UPS_PORT` in `.env`

### Q2: Insufficient Permission to Access USB Device

**Solutions:**

Ensure Docker container has USB device access permission:

```bash
# Add current user to dialout group
sudo usermod -aG dialout $USER

# Restart Docker service
sudo systemctl restart docker

# Restart container
docker-compose restart nut-server
```

### Q3: Frontend Cannot Connect to Backend

**Solutions:**

1. Check if Backend is running properly:
   ```bash
   docker-compose logs backend
   curl http://localhost:8000/health
   ```

2. Check API Token configuration:
   Ensure `API_TOKEN` is set in `.env`

3. Check firewall:
   Ensure ports 80 and 3493 are not occupied or blocked by firewall

### Q4: WebSocket Connection Failed

**Solutions:**

1. Check Nginx configuration:
   ```bash
   docker exec ups-guard-frontend cat /etc/nginx/conf.d/default.conf
   ```

2. Check browser console errors

3. Try using HTTP instead of HTTPS (development environment)

## Data Backup and Restore

### Backup

```bash
# Backup configuration and historical data
docker run --rm -v ups-data:/data -v $(pwd):/backup alpine \
  tar czf /backup/ups-guard-backup.tar.gz /data
```

### Restore

```bash
# Restore data
docker run --rm -v ups-data:/data -v $(pwd):/backup alpine \
  tar xzf /backup/ups-guard-backup.tar.gz -C /
```

## Upgrade

```bash
# Pull latest code
git pull

# Rebuild and start
docker-compose up -d --build
```

## Uninstall

```bash
# Stop and remove all containers
docker-compose down

# Delete data volumes (Note: will delete all configuration and historical data)
docker-compose down -v

# Delete images
docker rmi $(docker images | grep ups-guard | awk '{print $3}')
```

## Security Recommendations

1. **Change Default Passwords**: Change all passwords in `.env`
2. **Set API Token**: Don't use auto-generated Token, manually set a strong password
3. **Limit Network Access**: Use firewall to limit Web interface access
4. **Regular Backups**: Regularly backup configuration and historical data
5. **Update System**: Regularly update Docker images and system

## Technical Support

- GitHub Issues: https://github.com/KingBoyAndGirl/ups-guard/issues
- Documentation: See other documents in `docs/` directory

## License

This project uses GPL-3.0 license. See [LICENSE](../LICENSE) file for details.
