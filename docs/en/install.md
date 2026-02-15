# UPS Guard - Installation Guide

## System Requirements

- Device with Docker support (Windows, Linux, macOS, LazyCAT, Synology, QNAP, etc.)
- USB-capable UPS device
- At least 1GB available storage space

## Installation Methods

### Method 1: Docker Compose Deployment (Recommended)

Suitable for any device with Docker. For detailed steps, see [Docker Deployment Documentation](./DOCKER_DEPLOYMENT.md).

### Method 2: LazyCAT Deployment

Suitable for LazyCAT users, can install using native application package (.lpk format).

#### 1. Download Application Package

Download the latest `.lpk` installation package from GitHub Releases.

#### 2. Install Application

In LazyCAT control panel:

1. Go to "App Store"
2. Click "Local Install"
3. Select downloaded `.lpk` file
4. Wait for installation to complete

#### 3. Connect UPS Device

1. Connect UPS to LazyCAT host via USB cable
2. Ensure USB connection is stable
3. Application will auto-detect UPS device

#### 4. Access Application

After installation completes, access via:

```
http://your-lazycat-host/ups-guard/
```

Or use subdomain:

```
http://ups-guard.your-lazycat-host/
```

## Initial Configuration

1. **Check UPS Connection**
   - View UPS status in dashboard page
   - Confirm it shows "Online" status

2. **Configure Shutdown Policy**
   - Go to "Settings" page
   - Set wait time after power loss (recommend 5-10 minutes)
   - Set minimum battery percentage (recommend 20-30%)
   - Set final wait time (recommend 30-60 seconds)

3. **Configure Push Notifications** (Optional)
   - Add notification channel in "Settings" page
   - Supports ServerChan and PushPlus
   - Test if notifications work properly

## Verify Installation

Run these checks to ensure installation is successful:

1. ✅ Dashboard displays UPS real-time data
2. ✅ WebSocket connection status shows "Connected"
3. ✅ History page displays data charts
4. ✅ Event log records system startup event

## Troubleshooting

### UPS Shows Offline

1. Check if USB connection is normal
2. Confirm UPS device is powered on
3. View application logs: `docker logs ups-guard-nut-server`
4. Check if UPS driver is supported (see [Supported UPS Devices](./supported-ups.md))

### Cannot Access Application

1. Check if application is running properly: `docker ps | grep ups-guard`
2. Check if port is occupied
3. View application logs: `docker logs ups-guard-backend`

### Notification Send Failed

1. Check network connection
2. Verify notification channel configuration is correct
3. Use "Test Notification" function to troubleshoot

## Uninstall Application

### Docker Compose Deployment

```bash
docker-compose down -v  # -v will delete data volumes
```

### LazyCAT Deployment

In LazyCAT control panel:

1. Go to "App Management"
2. Find "UPS Guard"
3. Click "Uninstall"
4. Confirm uninstall operation

Note: Uninstalling will delete all historical data. If you need to keep data, backup database file `/data/ups_guard.db` first.

## Update Application

### Docker Compose Deployment

```bash
git pull
docker-compose down
docker-compose up -d --build
```

### LazyCAT Deployment

1. Download new version `.lpk` installation package
2. Click "Update" in app management
3. Select new version installation package
4. Wait for update to complete

Update process will preserve configuration and historical data.
