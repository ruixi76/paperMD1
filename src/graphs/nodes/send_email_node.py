"""
发送邮件节点

将个性化简报发送到用户邮箱（支持HTML格式）
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

        html_content = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.8; color: #2c3e50; background: #f8f9fa; margin: 0; padding: 0; }}
                .container {{ max-width: 900px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px 40px; color: white; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .header p {{ margin: 8px 0 0; opacity: 0.9; font-size: 14px; }}
                .content {{ padding: 30px 40px; }}
                .content h2 {{ color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 8px; margin-top: 30px; }}
                .paper-card {{ background: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; margin: 16px 0; border-radius: 0 8px 8px 0; }}
                .paper-card h3 {{ margin: 0 0 8px; color: #2c3e50; font-size: 16px; }}
                .priority-high {{ background: #fdecea; color: #c62828; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: bold; margin-right: 8px; }}
                .priority-recommended {{ background: #fff8e1; color: #e65100; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: bold; margin-right: 8px; }}
                .priority-watch {{ background: #e8f5e9; color: #2e7d32; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: bold; margin-right: 8px; }}
                .score {{ display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; margin-right: 6px; }}
                .score-innovation {{ background: #e3f2fd; color: #1565c0; }}
                .score-relevance {{ background: #e8f5e9; color: #2e7d32; }}
                .score-feasibility {{ background: #fff3e0; color: #e65100; }}
                .doi-badge {{ background: #f3e5f5; color: #7b1fa2; padding: 2px 8px; border-radius: 4px; font-size: 12px; }}
                .core-contribution {{ background: #e8eaf6; padding: 10px 14px; border-radius: 6px; margin: 8px 0; font-size: 14px; }}
                .recommend-reason {{ background: #fff3e0; padding: 10px 14px; border-radius: 6px; margin: 8px 0; font-size: 14px; }}
                .trend-section {{ background: linear-gradient(135deg, #e8eaf6 0%, #f3e5f5 100%); padding: 20px; border-radius: 8px; margin: 16px 0; }}
                .action-section {{ background: linear-gradient(135deg, #e8f5e9 0%, #e0f7fa 100%); padding: 20px; border-radius: 8px; margin: 16px 0; }}
                .footer {{ margin-top: 30px; padding: 20px 40px; border-top: 1px solid #eee; color: #999; font-size: 12px; background: #fafafa; }}
                a {{ color: #667eea; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📡 文献雷达 · 每日简报</h1>
                    <p>个性化科研文献推送 · {formatdate(localtime=True)}</p>
                </div>
                <div class="content">
                    {content}
                </div>
                <div class="footer">
                    <p>📡 此邮件由<b>文献雷达系统</b>自动发送 | 基于Agent的个性化科研伴侣</p>
                    <p>DOI溯源校验 · 三维评分体系 · 防幻觉Self-Check</p>
                </div>
            </div>
        </body>
        </html>
        """

        msg = MIMEText(html_content, "html", "utf-8")
        msg["From"] = formataddr(("文献雷达系统", config["account"]))
        msg["To"] = ", ".join(to_addrs) if to_addrs else ""
        msg["Subject"] = Header(subject, "utf-8")
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()

        if not to_addrs:
            return {"status": "error", "message": "收件人为空"}

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
    except Exception as e:
        return {"status": "error", "message": f"发送失败: {str(e)}"}


def send_email_node(
    state: SendEmailInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> SendEmailOutput:
    """
    title: 发送邮件
    desc: 将个性化科研简报以HTML格式发送到用户邮箱
    integrations: Email
    """
    ctx = runtime.context

    try:
        result = _send_html_email(
            subject=state.email_subject,
            content=state.content,
            to_addrs=[state.to_email]
        )

        if result.get("status") == "success":
            logger.info(f"邮件发送成功: {result.get('message')}")
            return SendEmailOutput(success=True, message=result.get("message", "发送成功"))
        else:
            logger.error(f"邮件发送失败: {result.get('message')}")
            return SendEmailOutput(success=False, message=result.get("message", "发送失败"))

    except Exception as e:
        logger.error(f"发送邮件异常: {e}")
        return SendEmailOutput(success=False, message=f"发送邮件异常: {str(e)}")
