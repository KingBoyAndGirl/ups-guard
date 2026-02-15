# Push Notification Setup Guide

UPS Guard supports multiple push notification channels to notify you promptly when critical events occur (power loss, low battery, shutdown, etc.).

## ServerChan

ServerChan is a free WeChat push service with simple configuration.

### Get SendKey

1. Visit [ServerChan Official Site](https://sct.ftqq.com/)
2. Login with WeChat scan
3. Go to "SendKey" page
4. Copy your SendKey (format: `SCTxxxxx`)

### Configuration Steps

1. In UPS Guard "Settings" page, find "Push Notifications" area
2. Click "Add Notification Channel"
3. Select "ServerChan"
4. Enter SendKey
5. Click "Test Notification" to confirm configuration is correct
6. Save settings

### Notes

- ✅ Free version limited to 5 messages per day
- ✅ Paid version can send more messages
- ⚠️ Don't share SendKey with others

## PushPlus

PushPlus is another WeChat push service with richer features.

### Get Token

1. Visit [PushPlus Official Site](http://www.pushplus.plus/)
2. Login with WeChat scan
3. Go to "Send Message" page
4. Copy your Token

### Configuration Steps

1. In UPS Guard "Settings" page, find "Push Notifications" area
2. Click "Add Notification Channel"
3. Select "PushPlus"
4. Enter Token
5. (Optional) Enter group code
6. Click "Test Notification" to confirm configuration is correct
7. Save settings

### Group Push

If you created a PushPlus group, you can send notifications to the group:

1. Create group on PushPlus website
2. Copy group code
3. Fill in group code in configuration
4. Group members will all receive notifications

### Notes

- ✅ Free version limited to 200 messages per day
- ✅ Supports group push
- ⚠️ Don't share Token with others

## Notification Event Configuration

You can choose which events to receive notifications for:

- 🔌 **Power Loss** - When UPS switches to battery power
- ⚡ **Power Restored** - When mains power returns to normal
- 🔋 **Low Battery** - When battery charge falls below threshold
- 🔴 **Shutdown** - When system is about to shutdown
- ✅ **Startup** - When UPS Guard service starts
- 🔄 **Cancel Shutdown** - When shutdown operation is manually cancelled

Recommend enabling at least "Power Loss", "Low Battery" and "Shutdown" notifications.

## Notification Content Examples

### Power Loss Notification

```
Title: UPS Power Loss
Content: UPS switched to battery power, current charge: 95%
```

### Low Battery Notification

```
Title: UPS Battery Low
Content: Current charge: 18%, system will shutdown soon
```

### Shutdown Notification

```
Title: System Shutting Down
Content: UPS on battery power for over 5 minutes, system will shutdown in 30 seconds.
```

## Test Notification

After configuration, be sure to click "Test Notification" button to confirm configuration is correct.

Test notification example:

```
Title: UPS Guard Test Notification
Content: This is a test message. If you receive this, notification is configured correctly.
```

If test notification not received, check:

1. ✅ Is Token/SendKey correct
2. ✅ Is network connection normal
3. ✅ Has daily message limit been reached

## Multi-channel Configuration

You can configure multiple notification channels for redundant notifications:

```
Channel 1: ServerChan - Send to personal WeChat
Channel 2: PushPlus - Send to family group
```

All enabled channels will receive notifications simultaneously.

## Develop Custom Notification Plugin

If you need to integrate other push services (like Telegram, DingTalk, Enterprise WeChat, etc.), you can develop custom plugins.

See [Plugin Development Guide](./plugin-dev.md).

## Common Issues

### Q: Why no notifications received?

A: Please check:
1. Is notification channel enabled
2. Is event type checked
3. Is Token/SendKey correct
4. Is network connection normal
5. Has daily message limit been reached

### Q: How to disable certain notifications?

A: Uncheck corresponding event types in settings page.

### Q: Will notifications be delayed?

A: Under normal conditions, notifications are sent within 1-5 seconds of event occurrence. Network delays may affect reception time.

### Q: Are other push services supported?

A: Currently natively supports ServerChan and PushPlus. Other services can be extended via plugins. Welcome to contribute plugins!
