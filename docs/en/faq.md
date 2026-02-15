# Frequently Asked Questions (FAQ)

## Installation and Configuration

### Q: What hardware is needed?

A: You need:
1. USB-capable UPS device
2. Device running Docker (Windows, Linux, macOS, LazyCAT, Synology, QNAP, etc.)
3. USB data cable

### Q: Which UPS brands are supported?

A: Theoretically supports all UPS compatible with NUT protocol. Tested brands include:
- APC (American Power Conversion)
- CyberPower
- Eaton
- SANTAK
- Kstar

See [Supported UPS Devices](./supported-ups.md) for details.

### Q: How to confirm UPS is connected?

A: View UPS status in dashboard page. If it shows "Offline", check:
1. Is USB connection normal
2. Is UPS powered on
3. Does driver support your device

### Q: Can it be used without connecting UPS?

A: Yes. Set `MOCK_MODE=true` to enable Mock mode for development testing or experiencing features. But cannot provide real UPS monitoring and protection.

### Q: What's the difference between MOCK_MODE and Test Mode in settings?

A: These are two different levels of configuration, each serving different purposes:

**MOCK_MODE (Environment Variable)**:
- **Scope**: Controls **low-level connection method** at application startup
- **How to Set**: Environment variable, Docker Compose configuration
- **What it Controls**:
  - ✅ Whether to connect to real UPS hardware (NUT server)
  - ✅ Use simulated data or real UPS data
- **Use Cases**:
  - Development/testing (without UPS hardware)
  - Demo environment
  - Feature exploration
- **Restart Required**: Yes, must restart application

**Test Mode (Settings → System Configuration → Test Mode)**:
- **Scope**: Controls **runtime behavior** of application
- **How to Set**: Web settings interface, takes effect immediately
- **What it Controls**:
  - ✅ Whether to execute real shutdown commands
  - ✅ Whether to send WOL wake-up
  - ✅ How shutdown flow is executed
- **Three Modes**:
  - **Production**: Normal operation, execute actual shutdowns
  - **Dry-Run**: Connect to real UPS, test flow without actual shutdown
  - **Mock**: Simulate all operations, don't execute any actual actions
- **Use Cases**:
  - Test shutdown flow
  - Verify configuration correctness
  - Safety drill
- **Restart Required**: No, takes effect immediately

**Common Combinations**:
| MOCK_MODE | Test Mode | Description |
|-----------|-----------|-------------|
| false | production | **Production**: Connect to real UPS, execute real shutdowns ✅ |
| false | dry_run | **Rehearsal**: Connect to real UPS, but don't actually shutdown (recommended for testing) |
| true | production | **Development**: Use simulated UPS data, execute simulated shutdown |
| true | mock | **Full Simulation**: Simulate all operations (safest test environment) |

**Summary**:
- `MOCK_MODE` determines "where data comes from" (real UPS vs simulated)
- `test_mode` determines "how to use data" (actual operations vs simulated operations)
- Both can be configured independently without conflict

## Feature Usage

### Q: How does shutdown policy work?

A: After power loss:
1. Wait specified time (default 5 minutes)
2. Check battery charge, immediate shutdown if below threshold
3. Final wait 30 seconds
4. Execute shutdown

Power restoration cancels shutdown at any time.

### Q: Can shutdown be manually cancelled?

A: Yes. Click "Cancel Shutdown" button in dashboard page, or call API:

```bash
curl -X POST http://your-host/api/actions/cancel-shutdown
```

### Q: Does manually shutting down a single managed device execute pre-shutdown hooks?

A: **No**. Shutting down a single managed device and full system shutdown are two different operations:

**Single Device Shutdown** (via device card shutdown button or `/api/devices/{index}/shutdown` API):
- ✅ Only executes that device's own shutdown command (e.g., SSH shutdown)
- ❌ **Does NOT** execute all pre-shutdown hooks
- Purpose: Temporarily shut down one device without affecting others

**Full System Shutdown** (following methods execute complete pre-shutdown hooks):
- ✅ Automatic shutdown: Triggered by UPS power loss
- ✅ Manual global shutdown: Click "Immediate Shutdown" button or call `/api/actions/shutdown` API
- ✅ Dry-Run test: Call `/api/actions/dry-run-shutdown` API

**Pre-shutdown Hook Execution Order** (only during full system shutdown):
1. Execute all configured pre-shutdown hooks (by priority)
2. Shut down all managed devices
3. Shut down host machine (UPS Guard host)

**Example Scenarios**:
- Scenario 1: Temporarily shut down a test server → Use device card shutdown button (only that device)
- Scenario 2: UPS power loss, need to protect all devices → Auto-trigger full shutdown (executes all pre-shutdown hooks)
- Scenario 3: Manual emergency shutdown of all devices → Click "Immediate Shutdown" button (executes all pre-shutdown hooks)

### Q: What's the difference between LazyCAT microservice shutdown and SSH remote shutdown?

A: Both shutdown plugins connect via SSH, but their execution flows are different:

**⚠️ Important Notice**: LazyCAT microservice remote shutdown plugin and LZC gRPC host shutdown method are deprecated. Recommend using the more universal and flexible SSH approach.

**LazyCAT Microservice Remote Shutdown** (`lazycat_shutdown`) - **Deprecated**:
- 🐱 **Specifically designed for LazyCAT microservices**
- **Shutdown Flow**:
  1. SSH connect to LazyCAT microservice
  2. Stop all Docker containers with "lzc" in name
  3. Execute `poweroff` command
- **Limitations**:
  - ⚠️ Only stops containers with "lzc" in name
  - ⚠️ LazyCAT microservice has 3 containers: docker, pg-docker, lzc-docker - this plugin **only stops lzc-docker**
- **Reason for Deprecation**: Incomplete functionality, less flexible than SSH approach
- **Status**: Kept for backward compatibility, not recommended for new deployments

**SSH Remote Shutdown (Linux/macOS)** (`ssh_shutdown`) - **Recommended**:
- 🖥️ **General Linux/macOS systems**
- **Shutdown Flow**:
  1. SSH connect to target device
  2. Execute pre-shutdown commands (optional, e.g., stop containers/services)
  3. Execute shutdown command (`shutdown -h now` or `poweroff`)
- **Use Case**: Shut down regular Linux servers, macOS devices, NAS, etc.
- **Feature**: Flexible configuration, can achieve same functionality as LazyCAT shutdown via pre-commands
- **Pre-shutdown Command Examples**:
  ```bash
  # LazyCAT microservice (stop 3 containers):
  docker stop docker pg-docker lzc-docker
  
  # Or stop all containers:
  docker stop $(docker ps -q)
  
  # Stop system services:
  systemctl stop nginx
  systemctl stop postgresql
  ```

**Selection Guide**:
- ✅ **LazyCAT microservice devices** → **Strongly recommend "SSH Remote Shutdown" + pre-commands** (flexible control of all 3 containers)
- ⚠️ ~~LazyCAT microservice devices (old way) → "LazyCAT Microservice Remote Shutdown"~~ (deprecated, only stops lzc container)
- ✅ Other Linux/macOS devices → Use "SSH Remote Shutdown (Linux/macOS)"
- ✅ Synology NAS → Use "Synology DSM Shutdown"
- ✅ QNAP NAS → Use "QNAP QTS Shutdown"
- ✅ Windows devices → Use "Windows Remote Shutdown"

**Core Difference**:
- LazyCAT shutdown plugin: Fixed behavior - stops containers with "lzc" in name
- SSH remote shutdown + pre-commands: Flexible configuration - stop any containers/services

**💡 Tip**: LazyCAT microservice has 3 Docker containers (docker, pg-docker, lzc-docker). Using SSH shutdown's pre-commands allows more precise control over which containers to stop.

### Q: What if push notification fails?

A: Please check:
1. Is Token/SendKey correct
2. Is network connection normal
3. Has daily message limit been reached
4. Use "Test Notification" function to troubleshoot

See [Push Notification Setup Guide](./push-setup.md) for details.

### Q: How long is historical data retained?

A: Default retention is 30 days. Can be modified in settings, range 1-365 days.

### Q: How to export historical data?

A: Data is stored in SQLite database:

```bash
# Copy database file
docker cp ups-guard-backend:/data/ups_guard.db ./backup.db

# Export as CSV
sqlite3 backup.db "SELECT * FROM events" -csv > events.csv
sqlite3 backup.db "SELECT * FROM metrics" -csv > metrics.csv
```

## Performance and Resources

### Q: How much resources does the application use?

A: Typical usage:
- CPU: < 5% (idle)
- Memory: < 200MB
- Storage: < 100MB (30 days data)

### Q: Will it affect system performance?

A: No. Application is designed for low resource usage, background operation doesn't affect other services.

### Q: Will database grow infinitely?

A: No. Application automatically cleans data beyond retention period.

## Security and Reliability

### Q: What if shutdown is triggered by mistake?

A: Won't trigger by mistake. Shutdown requires simultaneously:
1. Power loss state
2. Exceeded wait time or battery too low
3. Final wait window confirmation

You have multiple chances to cancel.

### Q: What happens if shutdown fails?

A: If gRPC call fails, error is logged. But UPS itself has protection mechanism, will automatically cut output when battery depleted.

### Q: Can application crash lead to failure to shutdown?

A: No. NUT Server runs independently, configured with `upsmon` daemon, can execute shutdown even if application crashes.

### Q: Are notification Tokens secure?

A: Tokens stored in database, recommend:
1. Regularly change Token
2. Don't share publicly
3. Use dedicated Token (don't reuse from other services)

## Troubleshooting

### Q: UPS status shows offline

A: Check steps:
1. View USB connection: `lsusb`
2. View NUT logs: `docker logs ups-guard-nut-server`
3. Test driver: `docker exec ups-guard-nut-server upsc ups`
4. Change USB port or cable

### Q: WebSocket connection failed

A: Possible causes:
1. Network connection issue
2. Backend service not started
3. Firewall blocking WebSocket

Check:
```bash
docker ps | grep ups-guard
docker logs ups-guard-backend
```

### Q: Charts not displaying data

A: Possible causes:
1. Data sampling not started (need to wait at least 1 minute)
2. Time range selection issue
3. Browser compatibility

Try:
1. Refresh page
2. Change browser
3. Check browser console errors

### Q: Configuration save failed

A: Check:
1. Database file permissions
2. Is storage space sufficient
3. View backend logs

```bash
docker logs ups-guard-backend | grep ERROR
```

## Development and Extension

### Q: How to develop custom notification plugin?

A: See [Plugin Development Guide](./plugin-dev.md).

Main steps:
1. Inherit `NotifierPlugin` base class
2. Define configuration Schema
3. Implement `send()` method
4. Register plugin

### Q: Where is API documentation?

A: Visit `http://your-host:8000/docs` to view auto-generated OpenAPI documentation.

### Q: Does it support multiple UPS?

A: Current version only supports single UPS. If need to monitor multiple UPS, install multiple application instances.

### Q: Can it integrate with other systems?

A: Yes. Provides complete REST API and WebSocket interface, can integrate with other systems.

## Updates and Maintenance

### Q: How to update application?

A: 
**Docker Compose Deployment**:
```bash
git pull
docker-compose down
docker-compose up -d --build
```

**LazyCAT Deployment**:
1. Download new version `.lpk`
2. Click "Update" in control panel
3. Select installation package
4. Wait for completion

Configuration and data will be preserved.

### Q: Will update lose data?

A: No. Data stored in independent Docker Volume, update doesn't affect data.

Recommend backup before update:
```bash
docker cp ups-guard-backend:/data/ups_guard.db ./backup.db
```

### Q: How to uninstall application?

A: Uninstall in application management. Note:
- ⚠️ Will delete all data
- ⚠️ Operation is irreversible
- ✅ Recommend backup database first

## Commercial Support

### Q: Is personal use free?

A: Yes. This project uses AGPL-3.0 open source license, personal use is completely free.

### Q: Does commercial use require authorization?

A: If you want to:
- Use in closed-source commercial products
- Not disclose source code
- Get technical support

Please contact us for commercial authorization. See [Commercial License Agreement](../COMMERCIAL_LICENSE.md) for details.

### Q: How to get technical support?

A: 
- 📖 Check documentation
- 🐛 Submit GitHub Issue
- 💬 Join GitHub Discussions
- 📧 Commercial license users can get email support

## Contributing

### Q: How to contribute code?

A: Welcome contributions! Steps:
1. Fork project
2. Create feature branch
3. Submit code
4. Write tests
5. Submit Pull Request

### Q: How to report bugs?

A: Submit in GitHub Issues, include:
- Bug description
- Reproduction steps
- Expected behavior
- Actual behavior
- Environment information
- Log output

### Q: How to make suggestions?

A: Propose in GitHub Discussions or Issues. We seriously consider every suggestion.

---

**Didn't find an answer?**

Please ask in GitHub Issues or join our community discussion.
