# 插件开发指南

UPS Guard支持通过插件扩展通知功能。本指南将帮助您开发自定义通知插件。

## 插件架构

插件系统基于 Python，采用面向对象设计：

- `NotifierPlugin` - 插件基类
- `PluginRegistry` - 插件注册表
- 自动发现机制 - 放入 `plugins/` 目录即可自动注册

## 创建插件

### 1. 创建插件文件

在 `backend/src/plugins/` 目录创建新文件，例如 `telegram.py`。

### 2. 继承基类

```python
from plugins.base import NotifierPlugin
from plugins.registry import registry

class TelegramPlugin(NotifierPlugin):
    """Telegram 通知插件"""
    
    plugin_id = "telegram"  # 唯一标识符
    plugin_name = "Telegram"  # 显示名称
    plugin_description = "通过 Telegram Bot 发送通知"  # 描述
```

### 3. 定义配置 Schema

```python
@classmethod
def get_config_schema(cls) -> List[Dict[str, Any]]:
    """定义前端配置表单"""
    return [
        {
            "key": "bot_token",
            "label": "Bot Token",
            "type": "password",
            "required": True,
            "placeholder": "从 @BotFather 获取",
            "description": "Telegram Bot API Token"
        },
        {
            "key": "chat_id",
            "label": "Chat ID",
            "type": "text",
            "required": True,
            "placeholder": "从 @userinfobot 获取",
            "description": "接收消息的 Chat ID"
        }
    ]
```

配置项类型：
- `text` - 单行文本
- `password` - 密码（不显示明文）
- `number` - 数字
- `textarea` - 多行文本

### 4. 验证配置

```python
def validate_config(self):
    """验证配置有效性"""
    if "bot_token" not in self.config:
        raise ValueError("Bot Token 不能为空")
    
    if "chat_id" not in self.config:
        raise ValueError("Chat ID 不能为空")
```

### 5. 实现发送方法

```python
async def send(self, title: str, content: str, level: str = "info") -> bool:
    """
    发送通知
    
    Args:
        title: 通知标题
        content: 通知内容
        level: 通知级别 (info, warning, error)
    
    Returns:
        发送是否成功
    """
    bot_token = self.config["bot_token"]
    chat_id = self.config["chat_id"]
    
    # 构建消息
    icon_map = {
        "info": "ℹ️",
        "warning": "⚠️",
        "error": "❌"
    }
    icon = icon_map.get(level, "")
    
    # 使用 HTML 格式
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
                logger.error(f"Telegram 通知发送失败: {result.get('description')}")
                return False
    except Exception as e:
        logger.error(f"Telegram 通知发送异常: {e}")
        return False
```

### 6. 注册插件

```python
# 文件末尾添加
registry.register(TelegramPlugin)
```

## 完整示例

```python
"""Telegram 通知插件"""
import httpx
import logging
from typing import Dict, Any, List
from plugins.base import NotifierPlugin
from plugins.registry import registry

logger = logging.getLogger(__name__)


class TelegramPlugin(NotifierPlugin):
    """Telegram 通知插件"""
    
    plugin_id = "telegram"
    plugin_name = "Telegram"
    plugin_description = "通过 Telegram Bot 发送通知"
    
    @classmethod
    def get_config_schema(cls) -> List[Dict[str, Any]]:
        return [
            {
                "key": "bot_token",
                "label": "Bot Token",
                "type": "password",
                "required": True,
                "placeholder": "从 @BotFather 获取",
                "description": "Telegram Bot API Token"
            },
            {
                "key": "chat_id",
                "label": "Chat ID",
                "type": "text",
                "required": True,
                "placeholder": "从 @userinfobot 获取",
                "description": "接收消息的 Chat ID"
            }
        ]
    
    def validate_config(self):
        if "bot_token" not in self.config or not self.config["bot_token"]:
            raise ValueError("Bot Token 不能为空")
        
        if "chat_id" not in self.config or not self.config["chat_id"]:
            raise ValueError("Chat ID 不能为空")
    
    async def send(self, title: str, content: str, level: str = "info") -> bool:
        bot_token = self.config["bot_token"]
        chat_id = self.config["chat_id"]
        
        icon_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌"
        }
        icon = icon_map.get(level, "")
        message = f"{icon} *{title}*\n\n{content}"
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, json=data)
                result = response.json()
                
                if result.get("ok"):
                    return True
                else:
                    logger.error(f"Telegram 通知发送失败: {result}")
                    return False
        except Exception as e:
            logger.error(f"Telegram 通知发送异常: {e}")
            return False


# 注册插件
registry.register(TelegramPlugin)
```

## 测试插件

### 1. 导入插件

在 `backend/src/main.py` 中导入：

```python
import plugins.telegram
```

### 2. 重启后端

```bash
docker restart ups-guard-backend
```

### 3. 前端测试

1. 进入设置页面
2. 添加通知渠道，选择「Telegram」
3. 填写配置
4. 点击「测试通知」
5. 检查 Telegram 是否收到测试消息

## 最佳实践

### 错误处理

- ✅ 捕获所有异常，避免插件崩溃
- ✅ 记录详细的错误日志
- ✅ 返回明确的成功/失败状态

### 日志记录

```python
import logging

logger = logging.getLogger(__name__)

# 使用不同级别
logger.debug("调试信息")
logger.info("正常信息")
logger.warning("警告信息")
logger.error("错误信息")
```

### 超时设置

```python
async with httpx.AsyncClient(timeout=10) as client:
    # 设置 10 秒超时
    response = await client.post(url, json=data)
```

### 敏感信息

- ⚠️ 不要在日志中打印 Token、密码等敏感信息
- ⚠️ 使用 `password` 类型字段存储敏感配置

### 测试方法

实现 `test()` 方法用于配置测试：

```python
async def test(self) -> bool:
    """测试配置是否正确"""
    return await self.send(
        title="UPS Guard 测试通知",
        content="这是一条测试消息，如果您收到此消息，说明通知配置正确。",
        level="info"
    )
```

## 贡献插件

欢迎将您的插件贡献到项目中！

### 提交步骤

1. Fork 项目
2. 创建插件文件
3. 编写文档
4. 测试功能
5. 提交 Pull Request

### 文档要求

在 `docs/` 目录添加插件使用文档，包括：

- 获取 API Key/Token 的步骤
- 配置说明
- 注意事项
- 常见问题

### 代码规范

- 遵循 PEP 8 编码规范
- 添加类型注解
- 编写中文注释
- 圈复杂度不超过 20

## 支持的插件

已实现的通知插件：

| 插件 | 说明 | 配置项 | 文档 |
|-----|------|--------|------|
| Server酱 | 微信推送 | SendKey | [查看](./push-setup.md#server酱) |
| PushPlus | 微信推送（支持群组） | Token, Topic | [查看](./push-setup.md#pushplus) |
| 钉钉机器人 | 钉钉群通知（Markdown） | Webhook URL, Secret | [查看](./push-setup.md#钉钉) |
| Telegram Bot | Telegram 消息推送 | Bot Token, Chat ID, Proxy | 本指南 |
| 邮件 SMTP | 邮件通知（HTML） | SMTP 服务器配置 | [查看](./push-setup.md#邮件) |
| Webhook | 通用 HTTP 回调 | URL, Method, Template | [查看](./push-setup.md#webhook) |

欢迎贡献更多插件！

## 注意事项

### 安全性

1. **敏感信息保护**
   - 不在日志中打印 Token、密码等敏感信息
   - 使用 `password` 类型配置项隐藏输入
   - 建议使用环境变量存储敏感配置

2. **超时控制**
   - HTTP 请求必须设置合理超时（推荐 10 秒）
   - 避免阻塞主线程
   - 使用异步 HTTP 客户端（如 `httpx.AsyncClient`）

3. **错误处理**
   - 捕获所有可能的异常
   - 返回明确的成功/失败状态
   - 记录详细的错误日志

### 测试

为插件编写单元测试：

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
    # 使用 Mock 测试
    pass
```

### 依赖管理

如果插件需要额外的 Python 包，添加到 `backend/pyproject.toml`：

```toml
dependencies = [
    "httpx>=0.26.0",
    "aiosmtplib>=3.0.0",  # 邮件插件需要
    # 添加你的依赖
]
```
