"""邮件 SMTP 通知插件"""
import aiosmtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List
from plugins.base import NotifierPlugin
from plugins.registry import registry

logger = logging.getLogger(__name__)


class EmailSMTPPlugin(NotifierPlugin):
    """邮件 SMTP 通知插件"""
    
    plugin_id = "email_smtp"
    plugin_name = "邮件 (SMTP)"
    plugin_description = "通过 SMTP 协议发送邮件通知"
    
    @classmethod
    def get_config_schema(cls) -> List[Dict[str, Any]]:
        return [
            {
                "key": "smtp_host",
                "label": "SMTP 服务器",
                "type": "text",
                "required": True,
                "placeholder": "smtp.example.com",
                "description": "SMTP 服务器地址"
            },
            {
                "key": "smtp_port",
                "label": "SMTP 端口",
                "type": "number",
                "required": False,
                "default": 587,
                "placeholder": "587",
                "description": "SMTP 端口 (默认 587)"
            },
            {
                "key": "username",
                "label": "用户名",
                "type": "text",
                "required": True,
                "placeholder": "user@example.com",
                "description": "SMTP 认证用户名"
            },
            {
                "key": "password",
                "label": "密码",
                "type": "password",
                "required": True,
                "placeholder": "密码或授权码",
                "description": "SMTP 认证密码"
            },
            {
                "key": "sender",
                "label": "发件人地址",
                "type": "text",
                "required": True,
                "placeholder": "noreply@example.com",
                "description": "显示的发件人邮箱地址"
            },
            {
                "key": "recipients",
                "label": "收件人",
                "type": "text",
                "required": True,
                "placeholder": "admin@example.com, user@example.com",
                "description": "收件人邮箱，多个用逗号分隔"
            },
            {
                "key": "use_tls",
                "label": "使用 TLS",
                "type": "select",
                "required": False,
                "default": "true",
                "options": [
                    {"value": "true", "label": "是"},
                    {"value": "false", "label": "否"}
                ],
                "description": "是否使用 TLS 加密连接 (推荐)"
            }
        ]
    
    def validate_config(self):
        required_fields = ["smtp_host", "username", "password", "sender", "recipients"]
        for field in required_fields:
            if field not in self.config or not self.config[field]:
                raise ValueError(f"邮件 SMTP 配置项 {field} 不能为空")
        
        # 验证邮箱格式
        sender = self.config["sender"]
        if "@" not in sender:
            raise ValueError("发件人邮箱格式不正确")
        
        recipients = self.config["recipients"]
        for recipient in recipients.split(","):
            if "@" not in recipient.strip():
                raise ValueError(f"收件人邮箱格式不正确: {recipient}")
    
    async def send(self, title: str, content: str, level: str = "info", timestamp: str = ""):
        """
        发送邮件通知
        """
        smtp_host = self.config["smtp_host"]
        smtp_port = self.config.get("smtp_port", 587)
        username = self.config["username"]
        password = self.config["password"]
        sender = self.config["sender"]
        recipients_str = self.config["recipients"]
        use_tls = self.config.get("use_tls", "true") == "true"
        
        # 解析收件人列表
        recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]
        
        # 根据级别添加图标（与其他插件保持一致）
        icon_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌"
        }
        icon = icon_map.get(level, "")
        
        # 根据级别设置邮件样式
        level_colors = {
            "info": "#3B82F6",
            "warning": "#F59E0B",
            "error": "#EF4444"
        }
        level_names = {
            "info": "信息",
            "warning": "警告",
            "error": "错误"
        }
        color = level_colors.get(level, "#3B82F6")
        level_name = level_names.get(level, "通知")
        
        # 构建结构化 HTML 邮件
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: {color}; color: white; padding: 15px; border-radius: 5px 5px 0 0;">
                    <h2 style="margin: 0;">UPS Guard 通知</h2>
                </div>
                <div style="background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 5px 5px;">
                    <div style="margin-bottom: 15px;">
                        <strong>标题:</strong> {title}
                    </div>
                    <div style="margin-bottom: 15px;">
                        <strong>内容:</strong><br/>
                        <div style="white-space: pre-wrap; margin-top: 5px;">{content}</div>
                    </div>
                    <div style="margin-bottom: 15px;">
                        <strong>级别:</strong> {icon} {level_name}
                    </div>
                    <div>
                        <strong>时间:</strong> {timestamp}
                    </div>
                </div>
                <div style="margin-top: 20px; padding: 10px; background-color: #f0f0f0; border-radius: 5px; font-size: 12px; color: #666;">
                    <p style="margin: 0;">此邮件由 UPS Guard 系统自动发送，请勿直接回复。</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # 构建纯文本版本
        text_content = f"标题: {title}\n内容: {content}\n级别: {icon} {level_name}\n时间: {timestamp}"
        
        # 创建邮件
        message = MIMEMultipart("alternative")
        message["Subject"] = f"[UPS Guard] {title}"
        message["From"] = sender
        message["To"] = ", ".join(recipients)
        
        # 添加纯文本和 HTML 版本
        text_part = MIMEText(text_content, "plain", "utf-8")
        html_part = MIMEText(html_content, "html", "utf-8")
        message.attach(text_part)
        message.attach(html_part)
        
        try:
            # 发送邮件
            async with aiosmtplib.SMTP(
                hostname=smtp_host,
                port=smtp_port,
                timeout=10
            ) as smtp:
                if use_tls:
                    await smtp.starttls()
                
                await smtp.login(username, password)
                await smtp.send_message(message)
            
            return True, None
        except Exception as e:
            logger.error(f"邮件通知发送异常: {e}")
            return False, str(e)


# 自动注册插件
registry.register(EmailSMTPPlugin)
