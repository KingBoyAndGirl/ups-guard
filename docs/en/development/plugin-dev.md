# Plugin Development Guide

UPS Guard supports extending notification functionality through plugins. This guide will help you develop custom notification plugins.

## Plugin Architecture

The plugin system is based on Python with object-oriented design:

- `NotifierPlugin` - Plugin base class
- `PluginRegistry` - Plugin registry
- Auto-discovery mechanism - Place in `plugins/` directory for auto-registration

## Create Plugin

### 1. Create Plugin File

Create a new file in `backend/src/plugins/` directory, for example `telegram.py`.

### 2. Inherit Base Class

```python
from plugins.base import NotifierPlugin
from plugins.registry import registry

class TelegramPlugin(NotifierPlugin):
    """Telegram notification plugin"""
    
    plugin_id = "telegram"  # Unique identifier
    plugin_name = "Telegram"  # Display name
    plugin_description = "Send notifications via Telegram Bot"  # Description
```

### 3. Define Configuration Schema

```python
@classmethod
def get_config_schema(cls) -> List[Dict[str, Any]]:
    """Define frontend configuration form"""
    return [
        {
            "key": "bot_token",
            "label": "Bot Token",
            "type": "password",
            "required": True,
            "placeholder": "Get from @BotFather",
            "description": "Telegram Bot API Token"
        },
        {
            "key": "chat_id",
            "label": "Chat ID",
            "type": "text",
            "required": True,
            "placeholder": "Get from @userinfobot",
            "description": "Chat ID to receive messages"
        }
    ]
```

Configuration item types:
- `text` - Single-line text
- `password` - Password (hidden text)
- `number` - Number
- `textarea` - Multi-line text

### 4. Validate Configuration

```python
def validate_config(self):
    """Validate configuration validity"""
    if "bot_token" not in self.config:
        raise ValueError("Bot Token cannot be empty")
    
    if "chat_id" not in self.config:
        raise ValueError("Chat ID cannot be empty")
```

### 5. Implement Send Method

```python
async def send(self, title: str, content: str, level: str = "info") -> bool:
    """
    Send notification
    
    Args:
        title: Notification title
        content: Notification content
        level: Notification level (info, warning, error)
    
    Returns:
        Whether sending succeeded
    """
    bot_token = self.config["bot_token"]
    chat_id = self.config["chat_id"]
    
    # Build message
    icon_map = {
        "info": "ℹ️",
        "warning": "⚠️",
        "error": "❌"
    }
    icon = icon_map.get(level, "")
    
    # Use HTML format
    message = f"<b>{icon} {title}</b>\n\n{content}"
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        import httpx
        import logging
        
        logger = logging.getLogger(__name__)
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=data)
            result = response.json()
            
            if result.get("ok"):
                return True
            else:
                logger.error(f"Telegram notification send failed: {result.get('description')}")
                return False
    except Exception as e:
        logger.error(f"Telegram notification exception: {e}")
        return False
```

### 6. Register Plugin

```python
# Add at end of file
registry.register(TelegramPlugin)
```

## Complete Example

```python
"""Telegram notification plugin"""
import httpx
import logging
from typing import Dict, Any, List
from plugins.base import NotifierPlugin
from plugins.registry import registry

logger = logging.getLogger(__name__)


class TelegramPlugin(NotifierPlugin):
    """Telegram notification plugin"""
    
    plugin_id = "telegram"
    plugin_name = "Telegram"
    plugin_description = "Send notifications via Telegram Bot"
    
    @classmethod
    def get_config_schema(cls) -> List[Dict[str, Any]]:
        return [
            {
                "key": "bot_token",
                "label": "Bot Token",
                "type": "password",
                "required": True,
                "placeholder": "Get from @BotFather",
                "description": "Telegram Bot API Token"
            },
            {
                "key": "chat_id",
                "label": "Chat ID",
                "type": "text",
                "required": True,
                "placeholder": "Get from @userinfobot",
                "description": "Chat ID to receive messages"
            }
        ]
    
    def validate_config(self):
        if "bot_token" not in self.config or not self.config["bot_token"]:
            raise ValueError("Bot Token cannot be empty")
        
        if "chat_id" not in self.config or not self.config["chat_id"]:
            raise ValueError("Chat ID cannot be empty")
    
    async def send(self, title: str, content: str, level: str = "info") -> bool:
        bot_token = self.config["bot_token"]
        chat_id = self.config["chat_id"]
        
        icon_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌"
        }
        icon = icon_map.get(level, "")
        message = f"<b>{icon} {title}</b>\n\n{content}"
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, json=data)
                result = response.json()
                
                if result.get("ok"):
                    return True
                else:
                    logger.error(f"Telegram notification send failed: {result}")
                    return False
        except Exception as e:
            logger.error(f"Telegram notification exception: {e}")
            return False


# Register plugin
registry.register(TelegramPlugin)
```

## Test Plugin

### 1. Import Plugin

Import in `backend/src/main.py`:

```python
import plugins.telegram
```

### 2. Restart Backend

```bash
docker restart ups-guard-backend
```

### 3. Frontend Test

1. Go to settings page
2. Add notification channel, select "Telegram"
3. Fill in configuration
4. Click "Test Notification"
5. Check if Telegram receives test message

## Best Practices

### Error Handling

- ✅ Catch all exceptions to avoid plugin crashes
- ✅ Log detailed error messages
- ✅ Return clear success/failure status

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Use different levels
logger.debug("Debug info")
logger.info("Normal info")
logger.warning("Warning info")
logger.error("Error info")
```

### Timeout Settings

```python
async with httpx.AsyncClient(timeout=10) as client:
    # Set 10 second timeout
    response = await client.post(url, json=data)
```

### Sensitive Information

- ⚠️ Don't print Tokens, passwords in logs
- ⚠️ Use `password` type fields to store sensitive config

### Test Method

Implement `test()` method for configuration testing:

```python
async def test(self) -> bool:
    """Test if configuration is correct"""
    return await self.send(
        title="UPS Guard Test Notification",
        content="This is a test message. If you receive this, notification is configured correctly.",
        level="info"
    )
```

## Contribute Plugin

Welcome to contribute your plugin to the project!

### Submission Steps

1. Fork project
2. Create plugin file
3. Write documentation
4. Test functionality
5. Submit Pull Request

### Documentation Requirements

Add plugin usage documentation in `docs/` directory, including:

- Steps to get API Key/Token
- Configuration instructions
- Notes
- Common issues

### Code Standards

- Follow PEP 8 coding standards
- Add type annotations
- Write comments
- Cyclomatic complexity not exceeding 20

## Supported Plugins

Implemented notification plugins:

| Plugin | Description | Config Items | Documentation |
|-----|------|--------|------|
| ServerChan | WeChat push | SendKey | [View](./push-setup.md#serverchan) |
| PushPlus | WeChat push (supports groups) | Token, Topic | [View](./push-setup.md#pushplus) |
| DingTalk Bot | DingTalk group notification (Markdown) | Webhook URL, Secret | [View](./push-setup.md#dingtalk) |
| Telegram Bot | Telegram message push | Bot Token, Chat ID, Proxy | This guide |
| Email SMTP | Email notification (HTML) | SMTP server config | [View](./push-setup.md#email) |
| Webhook | Generic HTTP callback | URL, Method, Template | [View](./push-setup.md#webhook) |

Welcome to contribute more plugins!

## Notes

### Security

1. **Sensitive Information Protection**
   - Don't print Tokens, passwords in logs
   - Use `password` type config items to hide input
   - Recommend using environment variables to store sensitive config

2. **Timeout Control**
   - HTTP requests must set reasonable timeout (recommend 10 seconds)
   - Avoid blocking main thread
   - Use async HTTP client (e.g., `httpx.AsyncClient`)

3. **Error Handling**
   - Catch all possible exceptions
   - Return clear success/failure status
   - Log detailed error messages

### Testing

Write unit tests for plugin:

```python
import pytest
from plugins.telegram import TelegramPlugin

def test_plugin_initialization():
    config = {
        "bot_token": "123456:ABC-DEF",
        "chat_id": "123456789"
    }
    plugin = TelegramPlugin(config)
    assert plugin.config == config

@pytest.mark.asyncio
async def test_send_message():
    # Use Mock for testing
    pass
```

### Dependency Management

If plugin requires additional Python packages, add to `backend/pyproject.toml`:

```toml
dependencies = [
    "httpx>=0.26.0",
    "aiosmtplib>=3.0.0",  # Email plugin needs
    # Add your dependencies
]
```
