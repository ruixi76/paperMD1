"""
发送邮件节点

将格式化后的新闻内容发送到用户邮箱
"""
import json
import logging
import smtplib
import ssl
import time
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr, formatdate, make_msgid
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_workload_identity import Client
from cozeloop.decorator import observe

from graphs.state import SendEmailInput, SendEmailOutput

logger = logging.getLogger(__name__)


def get_email_config():
    """获取邮件配置信息"""
    client = Client()
    email_credential = client.get_integration_credential("integration-email-imap-smtp")
    return json.loads(email_credential)


@observe
def _send_html_email(subject: str, content: str, to_addrs: list) -> dict:
    """
    内部函数：发送HTML格式邮件
    
    Args:
        subject: 邮件主题
        content: 邮件正文（HTML格式）
        to_addrs: 收件人列表
        
    Returns:
        发送结果字典
    """
    try:
        config = get_email_config()
        
        # 构建HTML内容
        html_content = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                h1 {{ color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 10px; }}
                h2 {{ color: #333; margin-top: 20px; }}
                h3 {{ color: #555; }}
                a {{ color: #1a73e8; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                {content}
                <div class="footer">
                    <p>📬 此邮件由AI新闻自动推送系统发送<br>
                    生成时间: {formatdate(localtime=True)}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg = MIMEText(html_content, "html", "utf-8")
        msg["From"] = formataddr(("AI新闻助手", config["account"]))
        msg["To"] = ", ".join(to_addrs) if to_addrs else ""
        msg["Subject"] = Header(subject, "utf-8")
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()
        
        if not to_addrs:
            return {"status": "error", "message": "收件人为空"}
        
        # 重试机制
        ctx = ssl.create_default_context()
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        attempts = 3
        last_err = None
        
        for i in range(attempts):
            try:
                with smtplib.SMTP_SSL(config["smtp_server"], config["smtp_port"], context=ctx, timeout=30) as server:
                    server.ehlo()
                    server.login(config["account"], config["auth_code"])
                    server.sendmail(config["account"], to_addrs, msg.as_string())
                    server.quit()
                return {"status": "success", "message": f"邮件成功发送给 {len(to_addrs)} 位收件人", "recipient_count": len(to_addrs)}
            except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, smtplib.SMTPDataError, 
                    smtplib.SMTPHeloError, ssl.SSLError, OSError) as e:
                last_err = e
                time.sleep(1 * (i + 1))
        
        if last_err:
            return {"status": "error", "message": "发送失败", "detail": {"type": last_err.__class__.__name__, "args": [a.hex() if isinstance(a, bytes) else str(a) for a in getattr(last_err, "args", [])]}}
        return {"status": "error", "message": "发送失败: 未知错误"}
        
    except smtplib.SMTPAuthenticationError as e:
        return {"status": "error", "message": f"认证失败: {str(e)}"}
    except smtplib.SMTPRecipientsRefused as e:
        return {"status": "error", "message": "收件人被拒绝", "detail": {k: str(v) for k, v in getattr(e, "recipients", {}).items()}}
    except smtplib.SMTPSenderRefused as e:
        return {"status": "error", "message": f"发件人被拒绝: {e.smtp_code} {e.smtp_error}"}
    except smtplib.SMTPDataError as e:
        return {"status": "error", "message": f"数据被拒绝: {e.smtp_code} {e.smtp_error}"}
    except smtplib.SMTPConnectError as e:
        return {"status": "error", "message": f"连接失败: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"发送失败: {str(e)}"}


def send_email_node(
    state: SendEmailInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> SendEmailOutput:
    """
    title: 发送邮件
    desc: 将格式化后的新闻内容发送到用户邮箱
    integrations: Email
    """
    ctx = runtime.context
    
    try:
        # 调用内部发送函数
        result = _send_html_email(
            subject=state.email_subject,
            content=state.content,
            to_addrs=[state.to_email]
        )
        
        if result.get("status") == "success":
            logger.info(f"邮件发送成功: {result.get('message')}")
            return SendEmailOutput(
                success=True,
                message=result.get("message", "发送成功")
            )
        else:
            logger.error(f"邮件发送失败: {result.get('message')}")
            return SendEmailOutput(
                success=False,
                message=result.get("message", "发送失败")
            )
            
    except Exception as e:
        logger.error(f"发送邮件异常: {str(e)}")
        return SendEmailOutput(
            success=False,
            message=f"发送邮件异常: {str(e)}"
        )
