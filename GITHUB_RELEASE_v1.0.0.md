# 🎉 UPS Guard v1.0.0 - Initial Stable Release

**Release Date**: 2026-02-15  
**Developer**: 王.W

---

## 📋 Overview

UPS Guard v1.0.0 is the first stable release, production-ready with comprehensive security hardening and performance optimization.

首个正式发布版本，经过充分测试和优化，已达到生产就绪状态。

---

## ✨ Features

### 🔌 Real-time Monitoring
- WebSocket real-time push updates
- UPS status, battery info, power metrics monitoring
- ECharts data visualization with 24-hour trends
- Event-driven monitoring with NUT LISTEN protocol (88% less communication)

### 🔋 Smart Power Management
- Auto shutdown with 3-phase countdown
- Auto-cancel on power restore
- Pre-shutdown tasks support (gRPC)
- Wake-on-LAN integration

### 📱 Notification Channels (6 channels)
- Server酱 (ServerChan)
- PushPlus
- 钉钉 (DingTalk)
- Telegram
- Email (SMTP)
- Generic Webhook

### 🎨 Modern UI
- Vue 3 + TypeScript
- Dark/Light/System theme
- Mobile responsive design
- Drag & drop card layout

### 🔒 Security
- API Token authentication
- Sensitive data encryption (AES-256-GCM)
- CORS restrictions
- Parameter whitelist validation

### 🌍 Internationalization
- Chinese/English bilingual UI
- Bilingual notification messages
- Complete documentation in both languages

---

## 🐳 Deployment

Supports deployment on any Docker-enabled device:

| Platform | Config Location |
|----------|-----------------|
| Docker Compose | `deploy/docker/` |
| LazyCAT | `deploy/lazycat/` |
| Synology NAS | `deploy/synology/` |
| QNAP NAS | `deploy/qnap/` |

### Quick Start

```bash
git clone https://github.com/KingBoyAndGirl/ups-guard.git
cd ups-guard/deploy/docker
cp .env.example .env
docker-compose up -d
```

---

## 🧪 Tested Environment

- **OS**: Windows 11
- **Platform**: LazyCAT Micro Services (Docker)
- **UPS**: APC Back-UPS BK650M2-CH (650VA)
- **NUT Version**: 2.8.3

> ⚠️ Other OS and UPS models have not been tested. Compatibility feedback is welcome!

---

## 📚 Documentation

- [中文文档](https://github.com/KingBoyAndGirl/ups-guard/blob/main/docs/zh/README.md)
- [English Docs](https://github.com/KingBoyAndGirl/ups-guard/blob/main/docs/en/README.md)
- [Installation Guide](https://github.com/KingBoyAndGirl/ups-guard/blob/main/docs/zh/install.md)
- [Full Release Notes](https://github.com/KingBoyAndGirl/ups-guard/blob/main/RELEASE_NOTES_v1.0.0.md)

---

## 📄 License

AGPL-3.0 + Commercial License (dual licensing)

---

**Full Changelog**: https://github.com/KingBoyAndGirl/ups-guard/commits/v1.0.0

---

如果这个项目对您有帮助，请给个 ⭐️ Star 支持一下！
If this project helps you, please give it a ⭐️ Star!

