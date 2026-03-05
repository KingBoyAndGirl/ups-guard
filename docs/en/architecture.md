# UPS Guard - Architecture Documentation

## System Overview

UPS Guard is a container-based distributed application consisting of three main services:

```
┌─────────────────────────────────────────────┐
│  Docker Host (Supports Windows/Linux/macOS/ │
│    LazyCAT/Synology/QNAP, etc.)             │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────┐  ┌──────────────────┐   │
│  │  NUT Server  │  │    Frontend      │   │
│  │              │  │   (Vue 3 + NG)   │   │
│  │  ┌────────┐  │  └──────────────────┘   │
│  │  │ upsd   │  │           │              │
│  │  └────────┘  │           │              │
│  │  ┌────────┐  │           ↓              │
│  │  │usbhid  │  │  ┌──────────────────┐   │
│  │  │  ups   │  │  │    Backend       │   │
│  │  └────────┘  │  │  (FastAPI + WS)  │   │
│  │      ↕       │  │                  │   │
│  │  USB UPS     │←─┤  ┌────────────┐  │   │
│  └──────────────┘  │  │NUT Client  │  │   │
│                    │  └────────────┘  │   │
│                    │  ┌────────────┐  │   │
│                    │  │ Monitor    │  │   │
│                    │  └────────────┘  │   │
│                    │  ┌────────────┐  │   │
│                    │  │Shutdown Mgr│  │   │
│                    │  └────────────┘  │   │
│                    │  ┌────────────┐  │   │
│                    │  │  Notifier  │  │   │
│                    │  └────────────┘  │   │
│                    │  ┌────────────┐  │   │
│                    │  │  Database  │  │   │
│                    │  └────────────┘  │   │
│                    └──────────────────┘   │
│                            │               │
│                    ┌───────┴────────┐      │
│                    │ gRPC Shutdown  │      │
│                    │   (LZCOS API)  │      │
│                    └────────────────┘      │
└─────────────────────────────────────────────┘
```

## Core Components

### 1. NUT Server Container

**Responsibilities:**
- Communicate with UPS device via USB
- Run NUT daemon (upsd)
- Provide NUT protocol interface

**Tech Stack:**
- Alpine Linux
- NUT (Network UPS Tools)
- usbhid-ups driver

**Configuration:**
- Dynamically generate NUT config files
- Environment variable-driven configuration
- USB device passthrough (`usb_accel: true`)

### 2. Backend Container

**Responsibilities:**
- Monitor UPS status
- Manage shutdown policies
- Provide REST API and WebSocket
- Handle push notifications
- Record historical data

**Tech Stack:**
- Python 3.11+
- FastAPI + Uvicorn
- aiosqlite
- grpcio

**Core Modules:**

#### NUT Client (`services/nut_client.py`)
```python
RealNutClient    # Production environment, connects to NUT Server
MockNutClient    # Development environment, simulated data
```

Features:
- Async TCP connection
- NUT text protocol implementation
- Variable queries (GET VAR, LIST VAR)

#### Monitor Engine (`services/monitor.py`)
```python
UpsMonitor       # State machine pattern
```

State transitions:
```
OFFLINE → ONLINE → ON_BATTERY → LOW_BATTERY → SHUTTING_DOWN
                     ↑               ↑
                     └───────────────┘
                    (Power restored)
```

Features:
- 5-second polling of UPS status
- State change detection
- Event recording
- Metrics sampling
- WebSocket broadcasting

#### Shutdown Manager (`services/shutdown_manager.py`)
```python
ShutdownManager  # Safe shutdown policy
```

Flow:
1. Power loss detection → Start countdown
2. Wait N minutes (configurable)
3. Battery check (immediate shutdown if below threshold)
4. Final wait window (30 seconds)
5. Execute shutdown

Features:
- Power restoration cancels at any time
- Multiple confirmation mechanisms
- Manual cancel support

#### LZCOS gRPC Client (`services/lzc_shutdown.py`) (LazyCAT exclusive feature)
```python
LzcApiGatewayShutdown  # Production environment (via API Gateway)
MockShutdown           # Development environment
```

Implementation:
- Manual protobuf message encoding
- API Gateway connection (insecure gRPC)
- No proto file compilation dependency
- **Note**: This feature is only for LazyCAT systems

#### Notification System (`services/notifier.py`, `plugins/`)
```python
NotifierPlugin   # Plugin base class
PluginRegistry   # Registry
```

Built-in plugins:
- ServerChan
- PushPlus

Extension mechanism:
- Config Schema auto-renders forms
- Auto-discovery and registration
- Independent configuration and testing

#### History Service (`services/history.py`)
```python
HistoryService   # Event and metrics storage
```

Data tables:
- `events` - Event records (power loss, restoration, shutdown, etc.)
- `metrics` - Metrics sampling (battery, voltage, load, etc.)
- `config` - Configuration storage

### 3. Frontend Container

**Responsibilities:**
- User interface
- Real-time data display
- Configuration management
- History queries

**Tech Stack:**
- Vue 3 (Composition API)
- TypeScript
- Vite
- ECharts
- Nginx

**Page Structure:**
```
Dashboard.vue    # Dashboard - Real-time status
├─ StatusCard    # Status card
├─ BatteryGauge  # Battery gauge
├─ PowerChart    # Real-time chart
└─ EventList     # Recent events

Settings.vue     # Settings - Configuration management
├─ Shutdown      # Shutdown policy
├─ Notifier      # Push notifications
└─ Advanced      # Advanced settings

History.vue      # History - Long-term trends
└─ MetricChart   # Historical charts

Events.vue       # Logs - Event list
└─ EventTable    # Event table
```

## Data Flow

### Real-time Status Flow

```
UPS Device
  ↓ USB
NUT Server (upsd)
  ↓ TCP :3493
Backend (NUT Client)
  ↓ 5-second polling
Monitor (State machine)
  ↓ State change
WebSocket
  ↓ Real-time push
Frontend (Vue)
  ↓ Render
User Interface
```

### Shutdown Flow

```
Power loss detection
  ↓
Monitor trigger
  ↓
Shutdown Manager
  ├─ Wait timer
  ├─ Battery check
  └─ Power monitoring
  ↓
Final wait window
  ↓
LZCOS gRPC
  ↓
System shutdown
```

### Notification Flow

```
Event occurs
  ↓
History Service (record)
  ↓
Notifier Service
  ├─ ServerChan → WeChat
  ├─ PushPlus → WeChat/Groups
  └─ Custom plugin → ...
```

## Configuration Management

### Environment Variable Configuration

```bash
# NUT configuration
NUT_HOST=nut-server
NUT_PORT=3493
NUT_USERNAME=monuser
NUT_PASSWORD=secret
NUT_UPS_NAME=ups

# Database
DATABASE_PATH=/data/ups_guard.db

# Mode
MOCK_MODE=false

# LazyCAT API Gateway
LZC_API_GATEWAY_ADDRESS=app.cloud.lazycat.app.ups-guard.lzcapp:81
```

### Database Configuration

Stored in SQLite `config` table:
- Shutdown policy parameters
- Notification channel configuration
- Sampling and retention parameters

Can be modified dynamically via API.

## Security Mechanisms

### 1. Shutdown Safety

- ✅ Multiple confirmations (time + battery)
- ✅ Final wait window
- ✅ Power restoration auto-cancels
- ✅ Manual cancel support
- ✅ Mock mode doesn't execute real shutdown

### 2. Sensitive Information

- ⚠️ Notification Tokens use `password` type
- ⚠️ Logs don't print sensitive information
- ⚠️ Config database file permission protection

### 3. Permission Control

- 🔒 NUT Server needs `privileged` for USB access
- 🔒 gRPC socket needs read-only mount
- 🔒 Data directory independent persistence

## Performance Characteristics

### Polling Intervals

- UPS status: 5 seconds
- Metrics sampling: 60 seconds (configurable)
- WebSocket heartbeat: 25 seconds

### Data Retention

- Historical events: 30 days (configurable)
- Metrics sampling: 30 days (configurable)
- Automatic cleanup of expired data

### Resource Usage

Expected resource consumption:
- CPU: < 5% (idle)
- Memory: < 200MB
- Storage: < 100MB (30 days data)

## Extensibility

### Plugin System

- 📦 Dynamic loading of notification plugins
- 📦 Config Schema-driven forms
- 📦 Auto-registration and discovery

### API Extension

- 🔌 RESTful API
- 🔌 WebSocket real-time push
- 🔌 CORS support

### Containerization

- 🐳 Three services independent deployment
- 🐳 Environment variable configuration
- 🐳 Data volume persistence
- 🐳 Horizontal scaling support (Frontend)

## Development Mode

### Mock Mode

Set `MOCK_MODE=true` to enable:
- Use `MockNutClient` to simulate UPS data
- Use `MockShutdown` to avoid real shutdown
- Provide Mock API to control state

Mock API:
```
POST /api/dev/mock/power-lost      # Simulate power loss
POST /api/dev/mock/power-restored  # Simulate restoration
POST /api/dev/mock/low-battery     # Simulate low battery
```

### Local Development

```bash
# Backend
cd backend
uv sync
uvicorn src.main:app --reload

# Frontend
cd frontend
pnpm install
pnpm dev
```

## Monitoring and Debugging

### Logs

```bash
# View NUT Server logs
docker logs ups-guard-nut-server

# View Backend logs
docker logs ups-guard-backend

# View Frontend logs
docker logs ups-guard-frontend
```

### Health Check

```bash
# Check backend health
curl http://localhost:8000/health

# Check NUT connection
curl http://localhost:8000/api/ups/list
```

### WebSocket Test

```bash
# Using websocat
websocat ws://localhost:8000/api/ws
```

## Deployment Architecture

### Docker Deployment (Universal)

Suitable for any Docker environment (Windows, Linux, macOS, Synology, QNAP, LazyCAT, etc.).

```yaml
services:
  nut-server:    ports: 3493
  backend:       ports: 8000
  frontend:      ports: 80 (main entry)
```

Access: `http://your-host-ip/`

**LazyCAT Exclusive Features**:
- In LazyCAT environment, can access via `http://ups-guard.your-host/` (subdomain access)
- Supports gRPC shutdown (via `/lzcapp/run/sys/lzc-apis.socket`)
- Supports `deploy/lazycat/lzc-manifest.yml` and `deploy/lazycat/lzc-build.yml` for application packaging

### Development Environment

```yaml
services:
  backend:       ports: 8000 → localhost:8000
  frontend:      ports: 5173 → localhost:5173
```

Frontend proxies `/api` → `http://localhost:8000`

## Failure Recovery

### Container Restart

All containers configured with `restart: always`, auto-restart on abnormal exit.

### Data Recovery

Data stored in Docker Volume `ups-data`:
- Database: `/data/ups_guard.db`
- Regular backup recommended

### State Recovery

After application restart:
- Auto-connect to NUT Server
- Load configuration
- Resume monitoring
- Record startup event

## References

- [NUT Documentation](https://networkupstools.org/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vue 3 Documentation](https://vuejs.org/)
- [ECharts Documentation](https://echarts.apache.org/)
